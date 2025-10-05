from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, InputMediaVideo
)
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from telegram.error import TelegramError
import re, time, asyncio, logging
from datetime import datetime, timedelta, timezone
import registration as reg
import chat # Import chat module for busy check
from utils.cb import cb_match, CBError
from utils.val import clip, MAX_POST, MAX_COMMENT
from utils.input_validation import validate_and_sanitize_input

log = logging.getLogger("luvbot.posts")

# Global utility for auto-delete messages
async def send_and_delete_notification(bot, chat_id, text, delay=5):
    """Send a notification and delete it after delay seconds"""
    try:
        msg = await bot.send_message(chat_id, text)
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id, msg.message_id)
    except Exception:
        pass

def nz(text: str) -> str:
    """
    Ensure caption/text is 'different' for Telegram edits.
    Appends a zero-width char if needed.
    """
    if not text:
        return "\u2063"
    return text if text.endswith("\u2063") else (text + "\u2063")

# --- Notification Helpers ---
def _display_name(uid: int) -> str:
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT COALESCE(NULLIF(feed_username,''),'') FROM users WHERE tg_user_id=%s", (uid,))
            row = cur.fetchone()
        name = (row[0] or "").strip()
        return name if name else "User"
    except Exception:
        return "User"

def _list_blocked(uid: int, limit: int = 30) -> list[tuple[int, str]]:
    """Return [(blocked_uid, display_name)]"""
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute(
                "SELECT blocked_uid FROM blocked_users WHERE user_id=%s ORDER BY added_at DESC LIMIT %s",
                (uid, limit)
            )
            rows = cur.fetchall()
        ids = [int(r[0]) for r in rows] if rows else []
        return [(bid, _display_name(bid)) for bid in ids]
    except Exception:
        return []



# --- Views (seen) helpers ---
async def _track_view(post_id: int, viewer_id: int):
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute(
                "INSERT INTO feed_views(post_id,viewer_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (post_id, viewer_id)
            )
            con.commit()
    except Exception as e:
        print(f"track_view error: {e}")

def _seen_count(pid: int) -> int:
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM feed_views WHERE post_id=%s", (pid,))
            row = cur.fetchone()
            return int(row[0] or 0)
    except Exception as e:
        print(f"seen_count error: {e}")
        return 0

# --- Reactions helper ---
def _rx_counts(pid: int) -> dict:
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute(
                "SELECT emoji, COUNT(*) FROM feed_reactions WHERE post_id=%s GROUP BY emoji",
                (pid,)
            )
            return {row[0]: int(row[1]) for row in cur.fetchall()}
    except Exception as e:
        print(f"rx_counts error: {e}")
        return {}

# ---- display helpers ----
def safe_display_name(uid: int) -> str:
    try:
        # Ensure ensure_profile is available in this scope or imported
        # If ensure_profile is defined in another file, import it.
        # For now, assuming it's available or will be defined.
        # Placeholder for now:
        # prof = ensure_profile(uid)
        # if prof and prof.get("username"):
        #     return prof["username"]
        # return "User"

        # Fallback if ensure_profile is not directly available or fails
        return _display_name(uid)

    except Exception:
        return "User"
# -------------------------

# --- Helpers: username & friendship ---------------------------------
def get_username(db, uid: int) -> str:
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT username FROM profiles WHERE uid=%s", (uid,))
            row = cur.fetchone()
            uname = row[0] if row and row[0] else None
            return uname or f"User{uid}"
    except Exception:
        return f"User{uid}"

def is_friend(db, a: int, b: int) -> bool:
    """
    Return True if a and b are friends (approved).
    """
    try:
        return reg.is_friends(a, b)
    except Exception:
        return False

# --- Delayed menu helper ---
def menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 My Feed", callback_data="pf:myfeed")],
        [InlineKeyboardButton("🌍 Public Feed", callback_data="pf:public")],
        [InlineKeyboardButton("📖 Sensual Stories", callback_data="pf:sensual")],
        [InlineKeyboardButton("🔎 Find User", callback_data="pf:findopen")],
    ])

async def delayed_menu_buttons(bot, chat_id, message_id, current_post_id, has_prev, has_next, own):
    await asyncio.sleep(5)  # 5 sec wait
    try:
        # Get current nav buttons
        nav_kb = build_nav_kb(current_post_id, has_prev, has_next, own)
        # Add menu buttons below nav buttons
        combined_buttons = nav_kb.inline_keyboard + menu_kb().inline_keyboard
        combined_kb = InlineKeyboardMarkup(combined_buttons)

        await bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=combined_kb
        )
    except Exception as e:
        print("Menu button update failed:", e)

# -----------------------------
# Database-backed storage
# -----------------------------
def ensure_feed_posts_table():
    """Create feed_posts table if it doesn't exist"""
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feed_posts (
                    id BIGSERIAL PRIMARY KEY,
                    author_id BIGINT NOT NULL,
                    text TEXT,
                    photo TEXT,
                    video TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feed_comments (
                    id BIGSERIAL PRIMARY KEY,
                    post_id BIGINT REFERENCES feed_posts(id) ON DELETE CASCADE,
                    author_id BIGINT NOT NULL,
                    author_name TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feed_likes (
                    post_id BIGINT REFERENCES feed_posts(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (post_id, user_id)
                );
            """)
            # Create feed_views table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feed_views (
                  post_id BIGINT,
                  viewer_id BIGINT,
                  viewed_at TIMESTAMPTZ DEFAULT NOW(),
                  PRIMARY KEY(post_id, viewer_id)
                );
            """)
            # Create blocked_users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS blocked_users (
                  user_id BIGINT,
                  blocked_uid BIGINT,
                  added_at TIMESTAMPTZ DEFAULT NOW(),
                  PRIMARY KEY(user_id, blocked_uid)
                );
            """)
            # Ensure friend_msg_requests table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS friend_msg_requests (
                    id BIGSERIAL PRIMARY KEY,
                    sender   BIGINT NOT NULL,
                    receiver BIGINT NOT NULL,
                    text     TEXT   NOT NULL,
                    status   TEXT   NOT NULL DEFAULT 'pending',  -- pending|accepted|declined|busy
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            # Create feed_reactions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feed_reactions (
                    post_id BIGINT REFERENCES feed_posts(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    emoji TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (post_id, user_id, emoji)
                );
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS feed_reactions_post_user_idx
                ON feed_reactions (post_id, user_id);
            """)
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS feed_reactions_user_post_idx
                ON feed_reactions (user_id, post_id);
            """)
            # Add secret_crush table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS secret_crush (
                  user_id BIGINT, target_id BIGINT, created_at TIMESTAMPTZ DEFAULT NOW(),
                  PRIMARY KEY(user_id, target_id)
                );
            """)
            # Add stories table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id BIGSERIAL PRIMARY KEY,
                    author_id BIGINT NOT NULL,
                    kind TEXT NOT NULL, -- 'photo', 'video', 'text'
                    text TEXT,
                    media_id TEXT, -- file_id for photo/video
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    expires_at TIMESTAMPTZ NOT NULL
                );
            """)
            # Add story_views table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS story_views (
                    story_id BIGINT REFERENCES stories(id) ON DELETE CASCADE,
                    viewer_id BIGINT NOT NULL,
                    viewed_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (story_id, viewer_id)
                );
            """)
            con.commit()
    except Exception as e:
        print(f"Table creation error: {e}")

# Initialize tables at startup
ensure_feed_posts_table()

USER_STATE = {}       # uid -> state string (e.g. set_uname, set_bio, set_privacy, comment:<pid>, search)

# Story constants
STORY_STATE = "awaiting_story"    # expecting story content

# --- robust post count helper (DB → fallback to memory) ---
def _posts_count(uid: int) -> int:
    # try DB (if you later add feed_posts)
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM feed_posts WHERE author_id=%s", (uid,))
            row = cur.fetchone()
            if row is not None:
                return int(row[0])
    except Exception:
        pass
    # fallback to in-memory dict (if present)
    posts_dict = globals().get("USER_POSTS", {})
    return len(posts_dict.get(uid, []))

# --- FEED NAV STATE ---
POST_INDEX: dict[int, int] = {}     # user_id -> current index within FEED_LIST
FEED_LIST: dict[int, list[int]] = {}  # user_id -> list of post IDs (current feed)

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
UNAME_COOLDOWN = timedelta(days=30)

# ==== helpers ====
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

BTN_MY_FEED      = "pf:myfeed"
BTN_PUBLIC_FEED  = "pf:public"
BTN_SEARCH       = "pf:search"
BTN_MY_POSTS     = "pf:myposts"
BTN_EDIT         = "pf:edit"
BTN_TOGGLE_PRIV  = "pf:toggle"

def ensure_profile(uid):
    """Get user profile (feed + core info) from database"""
    try:
        with reg._conn() as con, con.cursor() as cur:
            # bring feed fields + core profile fields
            cur.execute("""
                SELECT
                    COALESCE(NULLIF(feed_username,''), NULL) AS feed_username,
                    COALESCE(feed_is_public, TRUE)          AS feed_public,
                    feed_photo,
                    gender, age, country, city
                FROM users
                WHERE tg_user_id=%s
            """, (uid,))
            row = cur.fetchone()

            if not row:
                # create a minimal row if missing
                cur.execute("""
                    INSERT INTO users (tg_user_id, feed_is_public)
                    VALUES (%s, TRUE)
                    RETURNING
                      NULL::TEXT      AS feed_username,
                      TRUE            AS feed_public,
                      NULL::TEXT      AS feed_photo,
                      NULL::TEXT      AS gender,
                      NULL::INT       AS age,
                      ''::TEXT        AS country,
                      ''::TEXT        AS city
                """, (uid,))
                row = cur.fetchone()
                con.commit()

        feed_username, feed_public, feed_photo, gender, age, country, city = row
        return {
            "username": feed_username,
            "is_public": bool(feed_public),
            "photo": feed_photo,
            "bio": reg.get_bio(uid) or "No bio set",
            # 👉 add core fields too
            "gender": gender,
            "age": age,
            "country": (country or "").strip(),
            "city": (city or "").strip(),
        }
    except Exception as e:
        print(f"Profile fetch error: {e}")
        return {
            "username": None,
            "bio": "No bio set",
            "is_public": True,
            "photo": None,
            "gender": None,
            "age": None,
            "country": "",
            "city": "",
        }

def profile_text(p, uid=None):
    uname = p.get("username") or "—"
    bio = p.get("bio") or "No bio set"
    privacy = "🔓 Public" if p.get("is_public") else "🔒 Private"
    
    # Get posts count from database using correct column name
    posts_count = 0
    try:
        if uid:  # Pass uid explicitly to this function
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM feed_posts WHERE author_id=%s", (uid,))
                row = cur.fetchone()
                posts_count = int(row[0] or 0)
    except Exception:
        posts_count = 0
    
    return (f"👤 **My Profile**\n"
            f"🪪 Username: {uname}\n"
            f"📖 Bio: {bio}\n"
            f"🌍 Privacy: {privacy}\n"
            f"📝 Posts: {posts_count}").replace("**", "")

def username_taken(uname, except_uid=None):
    """Check if username is already taken in database"""
    if not uname:
        return False
    try:
        with reg._conn() as con, con.cursor() as cur:
            if except_uid:
                cur.execute(
                    "SELECT 1 FROM users WHERE LOWER(feed_username)=LOWER(%s) AND tg_user_id != %s",
                    (uname, except_uid)
                )
            else:
                cur.execute(
                    "SELECT 1 FROM users WHERE LOWER(feed_username)=LOWER(%s)",
                    (uname,)
                )
            return cur.fetchone() is not None
    except Exception:
        return False

# -----------------------------
# Small helpers
# -----------------------------
async def _safe_edit_or_send(q, text, **kwargs):
    """Try to edit the button message; if that fails, send a fresh message."""
    try:
        await q.edit_message_text(text, **kwargs)
    except Exception:
        await q.message.reply_text(text, **kwargs)

def cap_invisible():
    return "\u2063"

async def safe_edit(target, text, kb=None, **kwargs):
    """
    Works for BOTH CallbackQuery (target=CallbackQuery) and Message (target=Message).
    - If it's a CallbackQuery: edit text/caption in-place.
    - If it's a Message: reply with a new message.
    """
    from telegram.error import BadRequest
    try:
        # CallbackQuery case
        if hasattr(target, "message") and target.message:
            msg = target.message
            if msg.text is not None:
                return await target.edit_message_text(text=text, reply_markup=kb, **kwargs)
            else:
                return await target.edit_message_caption(caption=text, reply_markup=kb, **kwargs)

        # Message case
        else:
            return await target.reply_text(text, reply_markup=kb, **kwargs)

    except BadRequest as e:
        if "message is not modified" in str(e).lower():
            return  # Ignore duplicate edits
        # Fallbacks for other errors
        try:
            if hasattr(target, "message") and target.message:
                return await target.message.reply_text(text, reply_markup=kb, **kwargs)
            else:
                return await target.reply_text(text, reply_markup=kb, **kwargs)
        except Exception:
            return
    except Exception:
        # Fallbacks (never use .bot on Message)
        try:
            if hasattr(target, "message") and target.message:
                return await target.message.reply_text(text, reply_markup=kb, **kwargs)
            else:
                return await target.reply_text(text, reply_markup=kb, **kwargs)
        except Exception:
            return

def build_post_caption(post):
    likes = len(post["likes"])
    author_id = post["author_id"]
    disp = safe_display_name(author_id)
    # show comment count
    cc = len(post["comments"])
    text = post["text"] or ""
    # show seen count
    seen = _seen_count(post["id"])
    # Add reaction counts
    rx = _rx_counts(post["id"])
    rx_line = " ".join([f"{e} {rx.get(e,0)}" for e in ["😍","🔥","😂","😢","👏"] if rx.get(e)])
    return f"👤 {disp}\n{text}\n\n❤️ {likes}   💬 {cc}   👁 {seen}\n{rx_line}\n{cap_invisible()}".strip()

def build_post_caption_with_clickable_user(post):
    """Post caption with clickable username button"""
    likes = len(post["likes"])
    author_id = post["author_id"]
    prof = ensure_profile(author_id)
    disp = prof["username"] if prof["username"] else f"ID {author_id}"
    # show comment count
    cc = len(post["comments"])
    text = post["text"] or ""
    # show seen count
    seen = _seen_count(post["id"])
    # Add reaction counts
    rx = _rx_counts(post["id"])
    rx_line = " ".join([f"{e} {rx.get(e,0)}" for e in ["😍","🔥","😂","😢","👏"] if rx.get(e)])
    return f"👤 {disp}\n{text}\n\n❤️ {likes}   💬 {cc}   👁 {seen}\n{rx_line}\n{cap_invisible()}".strip()

def build_nav_kb(pid: int, has_prev: bool, has_next: bool, own: bool) -> InlineKeyboardMarkup:
    # Find post to get author info
    post = find_post(pid)

    row1 = [
        InlineKeyboardButton("❤️ Like", callback_data=f"like:{pid}"),
        InlineKeyboardButton("💬 Comment", callback_data=f"cmt:{pid}"),
        InlineKeyboardButton("💬 View Comments", callback_data=f"viewc:{pid}")
    ]
    if own:
        row1.append(InlineKeyboardButton("🗑 Delete", callback_data=f"del:{pid}"))

    # Row of reactions
    rx_row = [
        InlineKeyboardButton("😍", callback_data=f"rx:😍:{pid}"),
        InlineKeyboardButton("🔥", callback_data=f"rx:🔥:{pid}"),
        InlineKeyboardButton("😂", callback_data=f"rx:😂:{pid}"),
        InlineKeyboardButton("😢", callback_data=f"rx:😢:{pid}"),
        InlineKeyboardButton("👏", callback_data=f"rx:👏:{pid}"),
    ]

    # Add clickable username row if post exists and not own post
    username_row = []
    if post and not own:
        author_id = post["author_id"]
        prof = ensure_profile(author_id)
        username = prof.get("username") or get_username(None, author_id)
        name = safe_display_name(author_id)
        username_row = [InlineKeyboardButton(f"👤 View {name}", callback_data=f"uprof:{author_id}")]

    row2 = []
    if has_prev:
        row2.append(InlineKeyboardButton("⬅️ Back", callback_data="prev"))
    if has_next:
        row2.append(InlineKeyboardButton("➡️ Next", callback_data="next"))

    # Build rows dynamically
    rows = [row1, rx_row]
    if username_row:
        rows.append(username_row)
    if row2:
        rows.append(row2)

    # Extra 3 menu buttons always present
    rows.append([InlineKeyboardButton("📂 My Feed", callback_data="pf:myfeed")])
    rows.append([InlineKeyboardButton("🌍 Public Feed", callback_data="pf:public")])
    rows.append([InlineKeyboardButton("🔍 Find User", callback_data="pf:findopen")])

    return InlineKeyboardMarkup(rows)

def kb_public_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Stories", callback_data="pf:stories"),
         InlineKeyboardButton("📁 My Feed", callback_data=BTN_MY_FEED),
         InlineKeyboardButton("🌍 Public Feed", callback_data=BTN_PUBLIC_FEED)],
        [InlineKeyboardButton("🔎 Find User", callback_data="pf:findopen"),
         InlineKeyboardButton("❓ Q/A Board", callback_data="qa:board"),
         InlineKeyboardButton("📊 Public Polls", callback_data="poll:board")],
        [InlineKeyboardButton("📖 Sensual Stories", callback_data="pf:sensual")],
    ])

def myfeed_text(uid):
    p = ensure_profile(uid)
    uname = p.get("username") or "—"
    bio = p.get("bio") or "No bio set"
    privacy = "🔓 Public" if p.get("is_public") else "🔒 Private"

    # Get posts count and user details
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM feed_posts WHERE author_id=%s", (uid,))
            posts_count = cur.fetchone()[0] or 0
            # Get gender/age/location from users
            cur.execute("SELECT gender, age, country, city FROM users WHERE tg_user_id=%s", (uid,))
            row = cur.fetchone()
            gender, age, country, city = (row or (None, None, "", ""))
    except Exception:
        posts_count = 0
        gender, age, country, city = (None, None, "", "")

    loc = (country or "—") + (", " + city if city else "")
    gender_txt = (gender or "—")
    age_txt = (str(age) if age is not None else "—")

    return (f"👤 <b>My Profile</b>\n"
            f"🪪 <b>Username:</b> {uname}\n"
            f"🧑 <b>Gender:</b> {gender_txt}\n"
            f"🎂 <b>Age:</b> {age_txt}\n"
            f"📍 <b>Location:</b> {loc or '—'}\n"
            f"📖 <b>Bio:</b> {bio}\n"
            f"🌍 <b>Privacy:</b> {privacy}\n"
            f"📝 <b>Posts:</b> {posts_count}")

def myfeed_keyboard(p):
    rows = [
        [InlineKeyboardButton("✏️ Edit Username", callback_data="pf:edit_uname")],
        [InlineKeyboardButton("📖 Edit Bio", callback_data="pf:edit_bio")],
        [InlineKeyboardButton("🔓 Make Public", callback_data=BTN_TOGGLE_PRIV)]
        if not p.get("is_public") else
        [InlineKeyboardButton("🔒 Make Private", callback_data=BTN_TOGGLE_PRIV)],
        [InlineKeyboardButton("📂 My Posts", callback_data=BTN_MY_POSTS)],

        # 👇 ADD THIS
        [InlineKeyboardButton("📚 My Stories", callback_data="pf:mystories")],

        # 👇 NEW: Blocked Users list
        [InlineKeyboardButton("🚫 Blocked Users", callback_data="pf:blocked")],

        [InlineKeyboardButton("⬅️ Back", callback_data="pf:menu")]
    ]
    return InlineKeyboardMarkup(rows)

# -----------------------------
# Create Post
# -----------------------------
async def cmd_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ensure_profile(uid)
    context.user_data["state"] = "awaiting_post"
    await update.message.reply_text("✍️ Send your post text **or** photo (with caption).", parse_mode="Markdown")

async def cmd_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    # gate: block posting if user is blocked/globally muted? (optional)
    context.user_data["state"] = STORY_STATE
    await update.message.reply_text(
        "📸 Send your *Story* now (text **or** one photo/video).\n"
        "It will auto-vanish in 24 hours.",
        parse_mode="Markdown"
    )

def _blocked_by_framework(context) -> bool:
    # Agar koi aur feature text own kar raha hai to posts text ko skip karo
    from handlers.text_framework import FEATURE_KEY
    af = context.user_data.get(FEATURE_KEY)
    return bool(af) and af not in ("posts",)

async def handle_post_guarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _blocked_by_framework(context):
        return
    return await handle_post(update, context)

async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global POST_COUNTER
    uid = update.effective_user.id

    # Don't swallow the text if we are collecting a comment
    state = context.user_data.get("state", "")
    if not (isinstance(state, str) and state.startswith("comment:")):
        if context.user_data.pop("_ignore_text_once", False):
            return

    user_state = context.user_data.get("state")

    # --- story creation flow ---
    if user_state == STORY_STATE:
        context.user_data["state"] = None

        kind, text, media_id = None, None, None
        msg = update.message

        if msg.photo:
            kind = "photo"
            media_id = msg.photo[-1].file_id
            text = (msg.caption or "").strip()
        elif msg.video:
            kind = "video"
            media_id = msg.video.file_id
            text = (msg.caption or "").strip()
        else:
            kind = "text"
            text = (msg.text or "").strip()
            if not text:
                await msg.reply_text("❌ Please send text or a photo/video for your Story.")
                context.user_data["state"] = STORY_STATE
                return

        exp = datetime.now(timezone.utc) + timedelta(hours=24)

        try:
            with reg._conn() as con, con.cursor() as cur:
                cur.execute(
                    "INSERT INTO stories(author_id, kind, text, media_id, expires_at) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (uid, kind, text, media_id, exp)
                )
                con.commit()
        except Exception as e:
            await msg.reply_text(f"❌ Could not save story: {e}")
            return

        # Show preview of story (photo/video/text) → delete after 2s
        sent = None
        if kind == "photo":
            sent = await msg.reply_photo(media_id, caption=text or "📸 Story")
        elif kind == "video":
            sent = await msg.reply_video(media_id, caption=text or "🎥 Story")
        else:
            sent = await msg.reply_text(text or "📝 Story")

        # Schedule deletion of preview
        async def cleanup_and_feed():
            import asyncio
            await asyncio.sleep(2)
            try:
                if sent: await sent.delete()
            except Exception:
                import logging
                log = logging.getLogger("luvbot.posts")
                log.exception("Failed to delete story preview message")
            try:
                # Open My Feed after cleanup
                from handlers.posts_handlers import on_myfeed
                class _FakeCB:
                    def __init__(self, msg, uid):
                        self.from_user = type("U", (), {"id": uid})()
                        self.message = msg
                        self.data = "pf:myfeed"
                    async def answer(self,*a,**k): pass
                fake_update = type("U", (), {"callback_query": _FakeCB(msg, uid)})()
                await on_myfeed(fake_update, context)
            except Exception as e:
                print("Error opening feed after story:", e)

        asyncio.create_task(cleanup_and_feed())

        # Green success msg (stay visible)
        p = ensure_profile(uid)
        await msg.reply_text(
            "✅ Story posted successfully!\n\n" + myfeed_text(uid),
            reply_markup=myfeed_keyboard(p),
            parse_mode="HTML"
        )
        return

    # --- standard post creation flow ---
    if user_state == "awaiting_post":
        # Create post in database
        ensure_profile(uid)

        text = update.message.caption or update.message.text
        photo = update.message.photo[-1].file_id if update.message.photo else None
        video = update.message.video.file_id if update.message.video else None

        try:

            with reg._conn() as con, con.cursor() as cur:
                cur.execute(
                    "INSERT INTO feed_posts (author_id, text, photo, video) VALUES (%s,%s,%s,%s) RETURNING id",
                    (uid, text, photo, video)
                )
                post_id = cur.fetchone()[0]
                con.commit()

                # Build post object for preview
                post = {
                    "id": post_id,
                    "author_id": uid,
                    "text": text,
                    "photo": photo,
                    "video": video,
                    "likes": set(),
                    "comments": []
                }
        except Exception as e:
            await update.message.reply_text(f"❌ Error creating post: {e}")
            return

        context.user_data["state"] = None

        # preview bhejo
        sent = None
        if video:
            sent = await update.message.reply_video(
                video,
                caption=build_post_caption(post),
                reply_markup=build_nav_kb(post["id"], False, False, True)
            )
        elif photo:
            sent = await update.message.reply_photo(
                photo,
                caption=build_post_caption(post),
                reply_markup=build_nav_kb(post["id"], False, False, True)
            )
        else:
            sent = await update.message.reply_text(
                build_post_caption(post),
                reply_markup=build_nav_kb(post["id"], False, False, True)
            )

        # delete preview after 5 sec
        async def delete_preview():
            await asyncio.sleep(5)
            try:
                await sent.delete()
            except Exception:
                pass

        asyncio.create_task(delete_preview())

        # Menu buttons are already included in build_nav_kb
        # asyncio.create_task(delayed_menu_buttons(
        #     context.bot, sent.chat_id, sent.message_id,
        #     post["id"], False, False, True
        # ))

        p = ensure_profile(uid)
        success_msg = await update.message.reply_text(
            f"✅ Post created successfully!\n\n{myfeed_text(uid)}",
            reply_markup=myfeed_keyboard(p),
            parse_mode="HTML"
        )

        # ✅ Success message ko delete mat karo - stable rehne do
        return

    elif context.user_data.get("pf_state") == "awaiting_bio":
        uid = update.effective_user.id
        bio = (update.message.text or "").strip()[:150]

        # 1) persist bio (use your existing setter)

        reg.set_bio(uid, bio)

        # 2) clear state so it doesn't keep asking again
        context.user_data.pop("pf_state", None)

        # 3) rebuild profile + keyboard (define p before using)
        p = ensure_profile(uid)
        text = myfeed_text(uid)
        kb   = myfeed_keyboard(p)

        # 4) safe edit-or-send
        if update.callback_query:
            q = update.callback_query
            try:
                await q.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await q.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
            await q.answer()
        else:
            try:
                await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                # last resort
                await update.effective_chat.send_message(text, reply_markup=kb, parse_mode="HTML")
        return

    elif user_state == "set_uname":
        uname = (update.message.text or "").strip()

        if not USERNAME_RE.match(uname):
            await update.message.reply_text("❌ Invalid username. Use 3–20 chars: a-z, 0-9, _")
            return

        if username_taken(uname, except_uid=uid):
            await update.message.reply_text("❌ Username already taken. Try another.")
            return

        # Save username to database
        try:

            with reg._conn() as con, con.cursor() as cur:
                cur.execute("UPDATE users SET feed_username=%s WHERE tg_user_id=%s", (uname, uid))
                con.commit()
        except Exception as e:
            await update.message.reply_text(f"❌ Error saving username: {e}")
            return

        context.user_data["state"] = None
        p = ensure_profile(uid)  # Refresh profile

        # Show updated profile in a new message with HTML formatting
        await update.message.reply_text(
            myfeed_text(uid),
            reply_markup=myfeed_keyboard(p),
            parse_mode="HTML"
        )
        return

    elif user_state == "set_bio":
        bio = (update.message.text or "").strip()[:150]

        # 1) persist to DB
        try:

            reg.set_bio(uid, bio)
        except Exception as e:
            await update.message.reply_text(f"❌ Error saving bio: {e}")
            return

        # 2) clear state
        context.user_data["state"] = None

        # 3) refresh panel from DB
        p = ensure_profile(uid)  # this reads get_bio(uid) again
        await update.message.reply_text(
            myfeed_text(uid),
            reply_markup=myfeed_keyboard(p),
            parse_mode="HTML"
        )
        return

    elif isinstance(user_state, str) and user_state.startswith("comment:"):
        # add comment
        try:
            pid = int(user_state.split(":")[1])
            comment_text = update.message.text or ""
            author_name = _display_name(uid)

            # Save comment to database

            with reg._conn() as con, con.cursor() as cur:
                cur.execute(
                    "INSERT INTO feed_comments (post_id, author_id, author_name, text) VALUES (%s,%s,%s,%s)",
                    (pid, uid, author_name, comment_text)
                )
                con.commit()

            context.user_data["state"] = None

            # Get stored prompt message id
            prompt_id = context.user_data.get('comment_prompt_id')
            context.user_data.pop('comment_prompt_id', None)  # clean up

            # Send "Comment added!" notification
            confirmation = await update.message.reply_text("💬 Comment added!")

            # Delete both prompt and confirmation messages after 2 seconds
            async def delete_msgs():
                await asyncio.sleep(2)
                try:
                    if prompt_id:
                        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=prompt_id)
                    await context.bot.delete_message(chat_id=update.message.chat_id, message_id=confirmation.message_id)
                    await update.message.delete()  # Also delete user's comment message
                except Exception as e:
                    print("Delete error:", e)

            asyncio.create_task(delete_msgs())

            # Send notification for comment
            post = find_post(pid)
            if post:
                author = post.get("author_id")
                actor = uid
                if author and author != actor and _wants_feed_notify(author):
                    preview = (comment_text or "").strip()
                    if len(preview) > 80:
                        preview = preview[:77] + "..."
                    title = f"💬 {_display_name(actor)} commented on your post"
                    body = f'"{preview}"'
                    await _send_post_notify(context.bot, recipient_uid=author, actor_uid=actor,
                                            title=title, body=body, kind="comment", pid=pid)

            # Update all instances of this post in currently active feeds
            await update_post_everywhere(context.bot, pid)
            return
        except Exception as e:
            print(f"Comment error: {e}")
        context.user_data["state"] = None
        return

    elif context.user_data.get("pf_state") == "awaiting_lookup":
        context.user_data["pf_state"] = None
        query = (update.message.text or "").strip()
        target = None

        try:

            with reg._conn() as con, con.cursor() as cur:
                # Try numeric ID first
                if query.isdigit():
                    tid = int(query)
                    cur.execute("""
                        SELECT tg_user_id FROM users u
                        WHERE u.tg_user_id=%s AND u.feed_is_public=TRUE
                          AND NOT EXISTS (
                              SELECT 1 FROM blocked_users bu
                              WHERE (bu.user_id=%s AND bu.blocked_uid=u.tg_user_id)
                                 OR (bu.user_id=u.tg_user_id AND bu.blocked_uid=%s)
                          )
                    """, (tid, uid, uid))
                    if cur.fetchone():
                        target = tid

                # If not found by ID, try username (case-insensitive)
                if not target:
                    cur.execute("""
                        SELECT tg_user_id FROM users u
                        WHERE LOWER(u.feed_username)=LOWER(%s) AND u.feed_is_public=TRUE
                          AND NOT EXISTS (
                              SELECT 1 FROM blocked_users bu
                              WHERE (bu.user_id=%s AND bu.blocked_uid=u.tg_user_id)
                                 OR (bu.user_id=u.tg_user_id AND bu.blocked_uid=%s)
                          )
                    """, (query, uid, uid))
                    row = cur.fetchone()
                    if row:
                        target = row[0]

                if not target:
                    await update.message.reply_text("❌ User not found or profile is private.")
                    return

                # Get user's posts
                cur.execute(
                    "SELECT id FROM feed_posts WHERE author_id=%s ORDER BY created_at DESC",
                    (target,)
                )
                post_rows = cur.fetchall()

                if not post_rows:
                    # Open the user's profile instead of just saying no posts
                    try:
                        await update.message.reply_text("📭 No posts found. Opening profile…")
                        # Simulate a CallbackQuery for view_profile
                        class _FakeCB:
                            def __init__(self, msg, uid):
                                self.data = f"uprof:{uid}"
                                self.from_user = type("U", (), {"id": update.effective_user.id})()
                                self.message = msg
                            async def answer(self, *a, **k): pass
                        fake_update = type("U", (), {"callback_query": _FakeCB(update.message, target)})()
                        return await view_profile(fake_update, context)
                    except Exception:
                        # Fallback text profile if the above path fails
                        p = ensure_profile(target)
                        name = safe_display_name(target)
                        gender = p.get("gender") or "—"
                        age = p.get("age"); age_txt = str(age) if age is not None else "—"
                        loc = f"{p.get('country') or '—'}, {p.get('city') or '—'}"
                        try:
                            bio = reg.get_bio(target) or "No bio yet"
                        except Exception:
                            bio = "No bio yet"
                        txt = (f"👤 {name}\n\n"
                               f"🧑 Gender: {gender}\n"
                               f"🎂 Age: {age_txt}\n"
                               f"📍 Location: {loc}\n"
                               f"💬 Bio: {bio}")
                        await update.message.reply_text(txt)
                    return

                post_ids = [r[0] for r in post_rows]
                FEED_LIST[uid] = post_ids
                POST_INDEX[uid] = 0

                p0 = find_post(post_ids[0])
                if not p0:
                    await update.message.reply_text("❌ Error loading posts.")
                    return

                has_prev = False
                has_next = len(post_ids) > 1
                own = (p0["author_id"] == uid)

                # Track view
                await _track_view(p0["id"], uid)

                # FIX: Use p0 instead of post
                if p0.get("video"):
                    sent = await update.message.reply_video(
                        p0["video"], caption=build_post_caption(p0),
                        reply_markup=build_nav_kb(p0["id"], has_prev, has_next, own)
                    )
                elif p0.get("photo"):
                    sent = await update.message.reply_photo(
                        p0["photo"], caption=build_post_caption(p0),
                        reply_markup=build_nav_kb(p0["id"], has_prev, has_next, own)
                    )
                else:
                    sent = await update.message.reply_text(
                        build_post_caption(p0),
                        reply_markup=build_nav_kb(p0["id"], has_prev, has_next, own)
                    )
        except Exception as e:
            await update.message.reply_text(f"❌ Error searching: {e}")

                # Menu buttons are already included in build_nav_kb
                # asyncio.create_task(delayed_menu_buttons(
                #     context.bot, sent.chat_id, sent.message_id, p0["id"], has_prev, has_next, own
                # ))
        return

# -----------------------------
# Public Feed Menu
# -----------------------------
async def cmd_public(update, context):
    """Launch Mini App directly instead of old public feed menu"""
    import os
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    
    uid = update.effective_user.id
    
    # Check if user is registered (keep the check)
    if not reg.is_registered(uid):
        await update.message.reply_text(
            "🚫 Please complete registration first using /start"
        )
        return
    
    # Get the webapp URL for Mini App
    webapp_url = os.environ.get("WEBAPP_URL", "https://80b36b2d-922c-49ab-bd43-31b478351840-00-1xprbvjyuj6eq.sisko.replit.dev")
    
    # Create WebApp button for direct launch
    keyboard = [
        [InlineKeyboardButton(
            "🌍 Open LuvHive Feed", 
            web_app=WebAppInfo(url=f"{webapp_url}/")
        )],
        [InlineKeyboardButton("📱 What's New?", callback_data="miniapp:info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "🎉 **Welcome to LuvHive Social!**\n\n"
        "💕 Experience our revolutionary social platform:\n"
        "• 🌟 Share your moments with VibeFeed technology\n"
        "• ✨ Spark connections with mood-based matching\n"
        "• 💫 Glow system - express appreciation uniquely\n"
        "• 🎭 Anonymous confessions & authentic connections\n"
        "• 🔮 AI-powered emotional compatibility matching\n"
        "• 🌈 Dynamic mood indicators & aura profiles\n\n"
        "🚀 Tap the button below to enter your feed!"
    )
    
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def on_myfeed(update, context):
    q = update.callback_query
    uid = q.from_user.id
    p = ensure_profile(uid)
    await q.answer()
    # Send a new clean message without any background image/media
    await q.message.reply_text(text=myfeed_text(uid), reply_markup=myfeed_keyboard(p), parse_mode="HTML")

async def on_public_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show public feed with posts from all users"""
    q = update.callback_query
    await q.answer()  # answer once, early

    viewer_uid = q.from_user.id

    # gate: username required
    need_uname = False
    try:

        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT COALESCE(NULLIF(feed_username,''), '') FROM users WHERE tg_user_id=%s", (viewer_uid,))
            row = cur.fetchone()
            need_uname = (not row) or (row[0] == "")
    except Exception:
        pass

    if need_uname:
        context.user_data["state"] = "set_uname"
        context.user_data["_ignore_text_once"] = True
        await safe_edit(q, "📝 Set a username first (3–20 chars: a–z, 0–9, _). Send it now:")
        return

    try:

        with reg._conn() as con, con.cursor() as cur:
            # Get posts from public profiles OR friends (excluding blocked users)
            cur.execute("""
                SELECT fp.id, fp.author_id, fp.text, fp.photo, fp.video, fp.created_at
                FROM feed_posts fp
                JOIN users u ON fp.author_id = u.tg_user_id
                WHERE (u.feed_is_public = TRUE OR EXISTS (
                           SELECT 1 FROM friends f
                           WHERE f.user_id = %s AND f.friend_id = fp.author_id
                       ))
                  AND fp.author_id <> %s
                  AND NOT EXISTS (
                           SELECT 1 FROM blocked_users bu
                           WHERE (bu.user_id = %s AND bu.blocked_uid = fp.author_id)
                              OR (bu.user_id = fp.author_id AND bu.blocked_uid = %s)
                       )
                  -- Filter out shadow banned users' posts (unless viewing own posts)
                  AND (COALESCE(u.shadow_banned, FALSE) = FALSE OR fp.author_id = %s)
                ORDER BY fp.created_at DESC
                LIMIT 50
            """, (viewer_uid, viewer_uid, viewer_uid, viewer_uid, viewer_uid))
            rows = cur.fetchall()

        if not rows:
            await q.message.reply_text("No public posts yet.", reply_markup=kb_public_menu())
            return

        post_ids = [r[0] for r in rows]
        FEED_LIST[viewer_uid] = post_ids
        POST_INDEX[viewer_uid] = 0
        pid = post_ids[0]
        post = find_post(pid)

        if not post:
            await q.message.reply_text("❌ Error loading posts.", reply_markup=kb_public_menu())
            return

        has_prev = False
        has_next = len(post_ids) > 1
        own = (post["author_id"] == viewer_uid)

        # Track view
        try:
            await _track_view(pid, viewer_uid)
        except Exception:
            pass

        # small ephemeral header
        hdr = await q.message.reply_text("📣 Opening Public Feed…")
        async def _del_hdr():
            import asyncio
            try:
                await asyncio.sleep(2)
                await hdr.delete()
            except Exception:
                pass
        import asyncio; asyncio.create_task(_del_hdr())

        if post.get("video"):
            await q.message.reply_video(
                post["video"],
                caption=build_post_caption(post),
                reply_markup=build_nav_kb(pid, has_prev, has_next, own)
            )
        elif post.get("photo"):
            await q.message.reply_photo(
                post["photo"],
                caption=build_post_caption(post),
                reply_markup=build_nav_kb(pid, has_prev, has_next, own)
            )
        else:
            await q.message.reply_text(
                build_post_caption(post),
                reply_markup=build_nav_kb(pid, has_prev, has_next, own)
            )
    except Exception as e:
        await q.message.reply_text(f"❌ Error loading feed: {e}", reply_markup=kb_public_menu())
    return

    if data == "pf:findopen":
        context.user_data["pf_state"] = "awaiting_lookup"
        await q.answer()
        # Send a new clean message without any background image/media
        await q.message.reply_text("🔎 Send username or numeric ID to search.")
        return

    if data == BTN_TOGGLE_PRIV:
        # Toggle privacy setting in database
        try:

            with reg._conn() as con, con.cursor() as cur:
                cur.execute(
                    "UPDATE users SET feed_is_public = NOT COALESCE(feed_is_public, TRUE) WHERE tg_user_id=%s RETURNING feed_is_public",
                    (uid,)
                )
                new_status = cur.fetchone()[0]
                con.commit()
                privacy_status = "Public" if new_status else "Private"
        except Exception as e:
            await q.answer(f"❌ Error updating privacy: {e}", show_alert=True)
            return

        await q.answer(f"Privacy updated to {privacy_status}!")
        p = ensure_profile(uid)  # Refresh profile

        # Edit the current message with updated profile
        try:
            if q.message.text is not None:
                await q.edit_message_text(text=myfeed_text(uid), reply_markup=myfeed_keyboard(p), parse_mode="HTML")
            else:
                await q.edit_message_caption(caption=myfeed_text(uid), reply_markup=myfeed_keyboard(p), parse_mode="HTML")
        except Exception:
            chat_id = q.message.chat_id
            await q.message.bot.send_message(chat_id, myfeed_text(uid), reply_markup=myfeed_keyboard(p), parse_mode="HTML")
        return



    if data == "pf:edit_uname":
        context.user_data["state"] = "set_uname"
        await q.answer()
        # Edit current message to show prompt only
        await safe_edit(q, "📝 Send your username (3–20 chars: a-z, 0-9, _)")
        return

    if data == "pf:edit_bio":
        context.user_data["state"] = "set_bio"
        await q.answer()
        # Edit current message to show prompt only
        await safe_edit(q, "📖 Send your bio (up to 150 chars)")
        return

    if data == "pf:newpost":
        context.user_data["state"] = "awaiting_post"
        await q.answer()
        await safe_edit(q, "✍️ Send me your post text or photo (with caption).")
        return

    if data == "pf:menu":
        await safe_edit(q, "🌍 Public Feed Menu", kb_public_menu())
        await q.answer()
        return

# -----------------------------
# Post callbacks: like / comment / next / delete
# -----------------------------
def find_post(pid):
    """Find post by ID in database"""
    try:

        with reg._conn() as con, con.cursor() as cur:
            cur.execute(
                "SELECT id, author_id, text, photo, video, created_at FROM feed_posts WHERE id=%s",
                (pid,)
            )
            row = cur.fetchone()
            if not row:
                return None

            # Get likes count
            cur.execute("SELECT COUNT(*) FROM feed_likes WHERE post_id=%s", (pid,))
            likes_count = cur.fetchone()[0] or 0

            # Get likes set (for current user check)
            cur.execute("SELECT user_id FROM feed_likes WHERE post_id=%s", (pid,))
            likes = {r[0] for r in cur.fetchall()}

            # Get comments
            cur.execute(
                "SELECT author_id, author_name, text FROM feed_comments WHERE post_id=%s ORDER BY created_at",
                (pid,)
            )
            comments = [{"uid": r[0], "user": r[1], "text": r[2]} for r in cur.fetchall()]

            return {
                "id": row[0],
                "author_id": row[1],
                "text": row[2],
                "photo": row[3],
                "video": row[4],
                "created_at": row[5],
                "likes": likes,
                "comments": comments
            }
    except Exception as e:
        print(f"Find post error: {e}")
        return None

async def update_post_everywhere(bot, pid):
    """Update all instances of a post across all active feeds when comments/likes change"""
    post = find_post(pid)
    if not post:
        return

    # Find all users who might have this post in their current feed
    for user_id, feed_ids in FEED_LIST.items():
        if pid in feed_ids:
            current_idx = POST_INDEX.get(user_id, 0)
            if current_idx < len(feed_ids) and feed_ids[current_idx] == pid:
                # This user is currently viewing this post
                has_prev = current_idx > 0
                has_next = current_idx + 1 < len(feed_ids)
                own = (post.get("author_id") == user_id)

                # We need to find their current message to update it
                # Since we don't store message IDs, this is a limitation
                # In a real app, you'd store message_id with each post view
                pass

async def handle_feed_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle feed navigation callbacks (next/prev)"""
    q = update.callback_query
    data = q.data or ""
    uid = q.from_user.id

    if data == "next":
        ids = FEED_LIST.get(uid, [])
        idx = POST_INDEX.get(uid, 0)
        if not ids:
            await q.answer("No feed state", show_alert=True)
            return
        if idx + 1 >= len(ids):
            await q.answer("⚠️ This is the last post.", show_alert=True)
            return

        await q.answer()
        idx += 1
        POST_INDEX[uid] = idx
        pid = ids[idx]
        post = find_post(pid)
        if not post:
            return

        has_prev = idx > 0
        has_next = idx + 1 < len(ids)
        own = (post.get("author_id") == uid)

        await _track_view(pid, uid)

        if post.get("video"):
            media = InputMediaVideo(media=post["video"], caption=nz(build_post_caption(post)))
            await q.edit_message_media(media=media, reply_markup=build_nav_kb(pid, has_prev, has_next, own))
        elif post.get("photo"):
            media = InputMediaPhoto(media=post["photo"], caption=nz(build_post_caption(post)))
            await q.edit_message_media(media=media, reply_markup=build_nav_kb(pid, has_prev, has_next, own))
        else:
            await q.edit_message_text(nz(build_post_caption(post)), reply_markup=build_nav_kb(pid, has_prev, has_next, own))
        return

    elif data == "prev":
        ids = FEED_LIST.get(uid, [])
        idx = POST_INDEX.get(uid, 0)
        if not ids:
            await q.answer("No feed state", show_alert=True)
            return
        if idx == 0:
            await q.answer("⚠️ This is the first post.", show_alert=True)
            return

        await q.answer()
        idx -= 1
        POST_INDEX[uid] = idx
        pid = ids[idx]
        post = find_post(pid)
        if not post:
            return

        has_prev = idx > 0
        has_next = idx + 1 < len(ids)
        own = (post.get("author_id") == uid)

        await _track_view(pid, uid)

        if post.get("video"):
            media = InputMediaVideo(media=post["video"], caption=nz(build_post_caption(post)))
            await q.edit_message_media(media=media, reply_markup=build_nav_kb(pid, has_prev, has_next, own))
        elif post.get("photo"):
            media = InputMediaPhoto(media=post["photo"], caption=nz(build_post_caption(post)))
            await q.edit_message_media(media=media, reply_markup=build_nav_kb(pid, has_prev, has_next, own))
        else:
            await q.edit_message_text(nz(build_post_caption(post)), reply_markup=build_nav_kb(pid, has_prev, has_next, own))
        return

async def view_profile_friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View other user's friends list with posts/add friend actions."""
    q = update.callback_query
    await q.answer()
    try:
        m = cb_match(q.data or "", r"^uprof:friends:(?P<target>\d+)$")
        target_uid = int(m["target"])
    except (CBError, ValueError):
        return

    viewer_uid = q.from_user.id

    # fetch up to 50 friends
    try:

        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT friend_id FROM friends WHERE user_id=%s ORDER BY added_at DESC LIMIT 50", (target_uid,))
            rows = cur.fetchall()
        friend_ids = [int(r[0]) for r in rows] if rows else []
    except Exception:
        friend_ids = []

    if not friend_ids:
        return await q.message.reply_text("👥 No friends to show.")

    # Build list: each row shows friend name + action buttons
    rows = []
    for fid in friend_ids:
        name = safe_display_name(fid)

        # check privacy of friend for viewer
        can_view_posts = False
        try:

            with reg._conn() as con, con.cursor() as cur:
                cur.execute("SELECT COALESCE(feed_is_public, TRUE) FROM users WHERE tg_user_id=%s", (fid,))
                row = cur.fetchone()
                is_public = bool(row[0]) if row else True
            can_view_posts = is_public or reg.is_friends(viewer_uid, fid)
        except Exception:
            can_view_posts = True

        # left: "View Posts" or "View Profile" (if private)
        left_btn = InlineKeyboardButton(
            "🖼 View Posts" if can_view_posts else "👤 View Profile",
            callback_data=(f"feed:user:{fid}" if can_view_posts else f"uprof:{fid}")
        )
        # right: Add Friend (if not already)
        if not reg.is_friends(viewer_uid, fid) and viewer_uid != fid:
            right_btn = InlineKeyboardButton("➕ Add Friend", callback_data=f"fr:req:{fid}")
            rows.append([InlineKeyboardButton(name, callback_data=f"uprof:{fid}")])
            rows.append([left_btn, right_btn])
        else:
            rows.append([InlineKeyboardButton(name, callback_data=f"uprof:{fid}")])
            rows.append([left_btn])

    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=f"uprof:{target_uid}")])
    await q.message.reply_text(f"👥 Friends of {safe_display_name(target_uid)}", reply_markup=InlineKeyboardMarkup(rows))

async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View other user's profile with posts + actions."""
    q = update.callback_query
    data = q.data or ""

    if not data.startswith("uprof:"):
        return

    parts = data.split(":")
    target_uid = int(parts[1])
    return_pid = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
    viewer_uid = q.from_user.id

    if target_uid == viewer_uid:
        # Redirect to own profile
        from handlers.profile_handlers import show_profile
        return await show_profile(update, context)

    # Ban/block checks with improved error handling
    import logging
    log = logging.getLogger("luvbot.posts")
    
    if reg.is_banned(viewer_uid):
        log.warning(f"[PROFILE_DEBUG] Viewer {viewer_uid} is banned")
        await q.answer("🚫 You are banned and cannot view profiles.", show_alert=True)
        try:
            await q.edit_message_text("🚫 You are banned and cannot view profiles.")
        except Exception:
            await q.message.reply_text("🚫 You are banned and cannot view profiles.")
        return

    if reg.is_blocked(viewer_uid, target_uid):
        log.warning(f"[PROFILE_DEBUG] Viewer {viewer_uid} has blocked target {target_uid}")
        await q.answer("❌ You have blocked this user.", show_alert=True)
        try:
            await q.edit_message_text("❌ You have blocked this user. Go to your profile → Blocked Users to unblock them.")
        except Exception:
            await q.message.reply_text("❌ You have blocked this user. Go to your profile → Blocked Users to unblock them.")
        return

    if reg.is_blocked(target_uid, viewer_uid):
        log.warning(f"[PROFILE_DEBUG] Target {target_uid} has blocked viewer {viewer_uid}")
        await q.answer("❌ This user has blocked you.", show_alert=True)
        try:
            await q.edit_message_text("❌ This user has blocked you. You cannot view their profile.")
        except Exception:
            await q.message.reply_text("❌ This user has blocked you. You cannot view their profile.")
        return

    # Build profile text
    prof = ensure_profile(target_uid)
    name = safe_display_name(target_uid)

    # Basic info
    gender   = prof.get("gender")  or "—"
    age      = prof.get("age")
    age_txt  = str(age) if age is not None else "—"
    country  = prof.get("country") or "—"
    city     = prof.get("city")    or "—"
    location = f"{country}, {city}"
    try:
        bio = reg.get_bio(target_uid) or "No bio yet"
    except Exception:
        bio = "No bio yet"

    # Friends count
    try:

        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM friends WHERE user_id=%s", (target_uid,))
            friends_cnt = int(cur.fetchone()[0] or 0)
    except Exception:
        friends_cnt = 0

    # Mutual friends count
    mutual_friends_cnt = 0
    try:
        mutual_friends_cnt = reg.get_mutual_friends_count(viewer_uid, target_uid)
    except Exception:
        pass

    text  = f"👤 **{name}**\n\n"
    text += f"🧑 Gender: {gender}\n"
    text += f"🎂 Age: {age_txt}\n"
    text += f"📍 Location: {location}\n"
    text += f"👥 Friends: {friends_cnt}\n"
    if mutual_friends_cnt > 0:
        text += f"🤝 Mutual Friends: {mutual_friends_cnt}\n"
    text += f"💬 Bio: {bio}\n\n"

    # Buttons
    buttons = []

    # View Posts
    buttons.append([InlineKeyboardButton("🖼 View Posts", callback_data=f"feed:user:{target_uid}")])

    # Friend actions
    if reg.is_friends(viewer_uid, target_uid):
        buttons.append([InlineKeyboardButton("❌ Remove Friend", callback_data=f"friend:remove:{target_uid}")])
    elif reg.has_sent_request(viewer_uid, target_uid):
        buttons.append([InlineKeyboardButton("⏳ Request Sent (Cancel)", callback_data=f"fr:cancel:{target_uid}")])
    elif reg.has_incoming_request(viewer_uid, target_uid):
        buttons.append([
            InlineKeyboardButton("✅ Accept", callback_data=f"fr:accept:{target_uid}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"fr:decline:{target_uid}")
        ])
    else:
        buttons.append([InlineKeyboardButton("➕ Add Friend", callback_data=f"friend:add:{target_uid}")])

    # Secret Crush button
    buttons.append([InlineKeyboardButton("💘 Secret Crush", callback_data=f"crush:add:{target_uid}")])

    # Block action
    buttons.append([InlineKeyboardButton("🚫 Block User", callback_data=f"blk:add:{target_uid}")])

    # Friends list button
    buttons.append([InlineKeyboardButton("👥 Friends", callback_data=f"uprof:friends:{target_uid}")])

    # Back button - go to public feed posts instead of menu for better UX
    back_cb = f"backto:{return_pid}" if return_pid else "pf:public"
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=back_cb)])

    kb = InlineKeyboardMarkup(buttons)

    await q.answer()

    # Try to show with photo first
    photo_file = reg.get_photo_file(target_uid)
    if photo_file:
        try:
            # Use None parse_mode to avoid entity parsing errors with emojis
            await q.edit_message_media(
                media=InputMediaPhoto(photo_file, caption=text, parse_mode=None),
                reply_markup=kb
            )
            return
        except Exception:
            pass

    # Use existing safe edit utility from profile_handlers
    from handlers.profile_handlers import _safe_edit_or_send
    
    # Add invisible character to avoid "Message is not modified"
    def nz(text):
        """Add zero-width space to prevent identical content"""
        return text + "\u200B"
    
    # Use None parse_mode to prevent emoji entity parsing errors
    await _safe_edit_or_send(q, nz(text), reply_markup=kb, parse_mode=None)

async def handle_friend_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle fr:req:<user_id> callback - send friend request from profile"""
    q = update.callback_query
    await q.answer()

    viewer_uid = q.from_user.id

    try:
        target_uid = int(q.data.split(":")[2])
    except Exception:
        return await q.answer("Invalid request.", show_alert=True)

    if viewer_uid == target_uid:
        return await q.answer("That's you!", show_alert=True)

    # Already friends?
    if reg.is_friends(viewer_uid, target_uid):
        return await q.answer("Already friends.", show_alert=True)

    # Reverse pending? Auto-accept
    if reg.has_incoming_request(viewer_uid, target_uid):
        reg.delete_friend_request(target_uid, viewer_uid)
        reg.add_friend(viewer_uid, target_uid)
        try:
            await q.edit_message_text("✅ Request accepted. You're now friends!")
        except Exception:
            pass
        try:
            viewer_username = get_username(None, viewer_uid)
            await context.bot.send_message(target_uid, f"✅ @{viewer_username} accepted your friend request.")
        except Exception:
            pass
        return

    # Already sent request?
    if reg.has_sent_request(viewer_uid, target_uid):
        return await q.answer("Request already sent.", show_alert=True)

    # Create new friend request
    ok = reg.create_friend_request(viewer_uid, target_uid)
    if not ok:
        return await q.answer("Could not send request. Try later.", show_alert=True)

    # Notify target with approve/decline buttons
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"fr:acc:{viewer_uid}"),
         InlineKeyboardButton("❌ Decline", callback_data=f"fr:dec:{viewer_uid}")]
    ])

    try:
        name = safe_display_name(viewer_uid)
        await context.bot.send_message(
            chat_id=target_uid,
            text=f"👥 {name} sent you a friend request.",
            reply_markup=kb
        )
    except Exception:
        pass

    # Ephemeral notification (popup + temporary chat message)
    try:
        # Popup notification
        await q.answer("✅ Friend request sent!")

        # Temporary chat message that auto-deletes
        msg = await context.bot.send_message(
            chat_id=q.message.chat_id,
            text="✅ Friend request sent!"
        )

        import asyncio
        async def delete_temp():
            await asyncio.sleep(3)
            try:
                await msg.delete()
            except Exception:
                pass

        asyncio.create_task(delete_temp())

    except Exception:
        pass

    # Update profile to show "Request Sent" button
    return await view_profile(update, context)

async def show_user_feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle feed:user:<user_id> callback - show specific user's posts (DB-backed)"""
    q = update.callback_query
    await q.answer()

    try:
        target_uid = int(q.data.split(":")[2])
    except Exception:
        return

    viewer_uid = q.from_user.id
    profile = ensure_profile(target_uid)

    # Privacy: allow if public, own profile, or friends
    if not profile.get("is_public") and viewer_uid != target_uid and not is_friend(None, viewer_uid, target_uid):
        return

    # Block checks
    if reg.is_blocked(viewer_uid, target_uid):
        return

    # Fetch posts from DB
    try:

        with reg._conn() as con, con.cursor() as cur:
            cur.execute(
                "SELECT id FROM feed_posts WHERE author_id=%s ORDER BY created_at DESC",
                (target_uid,)
            )
            rows = cur.fetchall()
        if not rows:
            await q.message.reply_text("📭 No posts found for this user.")
            return
        post_ids = [r[0] for r in rows]
    except Exception as e:
        await q.message.reply_text(f"❌ Error loading posts: {e}")
        return

    # Set up feed state for viewer
    FEED_LIST[viewer_uid] = post_ids
    POST_INDEX[viewer_uid] = 0

    pid = post_ids[0]
    post = find_post(pid)
    if not post:
        await q.message.reply_text("❌ Error loading post.")
        return

    has_prev = False
    has_next = len(post_ids) > 1
    own = (target_uid == viewer_uid)

    # Count a view
    await _track_view(pid, viewer_uid)

    # Render first post
    if post.get("video"):
        await q.message.reply_video(
            post["video"],
            caption=build_post_caption(post),
            reply_markup=build_nav_kb(pid, has_prev, has_next, own)
        )
    elif post.get("photo"):
        await q.message.reply_photo(
            post["photo"],
            caption=build_post_caption(post),
            reply_markup=build_nav_kb(pid, has_prev, has_next, own)
        )
    else:
        await q.message.reply_text(
            build_post_caption(post),
            reply_markup=build_nav_kb(pid, has_prev, has_next, own)
        )

async def view_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle view_posts:<user_id>:<index> callback - legacy support"""
    q = update.callback_query
    await q.answer()

    try:
        m = cb_match(q.data or "", r"^view_posts:(?P<uid>\d+):(?P<index>\d+)$")
        target_uid = int(m["uid"])
        post_index = int(m["index"])
    except (CBError, ValueError):
        return

    # Get posts from database using correct column names
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute(
                """SELECT id, text, photo, video, created_at 
                   FROM feed_posts WHERE author_id=%s ORDER BY created_at DESC""", 
                (target_uid,)
            )
            rows = cur.fetchall()
            posts = []
            for row in rows:
                posts.append({
                    "id": row[0],
                    "text": row[1] or "",
                    "photo": row[2],
                    "video": row[3], 
                    "created_at": row[4]
                })
    except Exception:
        posts = []
    
    if not posts or post_index >= len(posts):
        await q.answer("❌ No posts found", show_alert=True)
        return

    viewer_uid = q.from_user.id
    profile = ensure_profile(target_uid)

    # Check if profile is public
    if not profile.get("is_public") and viewer_uid != target_uid:
        await q.answer("❌ This profile is private", show_alert=True)
        return

    # Set up feed for this user's posts
    post_ids = [p["id"] for p in posts]
    FEED_LIST[viewer_uid] = post_ids
    POST_INDEX[viewer_uid] = post_index

    post = posts[post_index]
    pid = post["id"]

    has_prev = post_index > 0
    has_next = post_index + 1 < len(posts)
    own = (target_uid == viewer_uid)

    # Show the post
    if post.get("video"):
        await q.message.reply_video(
            post["video"],
            caption=build_post_caption(post),
            reply_markup=build_nav_kb(pid, has_prev, has_next, own)
        )
    elif post.get("photo"):
        await q.message.reply_photo(
            post["photo"],
            caption=build_post_caption(post),
            reply_markup=build_nav_kb(pid, has_prev, has_next, own)
        )
    else:
        await q.message.reply_text(
            build_post_caption(post),
            reply_markup=build_nav_kb(pid, has_prev, has_next, own)
        )

# --- Friend Requests ---

async def on_friend_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel a sent friend request."""
    q = update.callback_query
    uid = q.from_user.id
    try:
        tid = int(q.data.split(":")[2])
    except Exception:
        return await q.answer("Invalid request.", show_alert=True)

    # remove pending request
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM friend_requests WHERE requester_id=%s AND target_id=%s", (uid, tid))
        con.commit()

    await q.answer("❌ Request cancelled.")
    return await view_profile(update, context)


async def on_friend_accept(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Accept an incoming friend request."""
    q = update.callback_query
    uid = q.from_user.id
    try:
        rid = int(q.data.split(":")[2])  # requester
    except Exception:
        return await q.answer("Invalid.", show_alert=True)

    # delete pending + insert friendship both sides
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM friend_requests WHERE requester_id=%s AND target_id=%s", (rid, uid))
        cur.execute("INSERT INTO friends(user_id, friend_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (uid, rid))
        cur.execute("INSERT INTO friends(user_id, friend_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (rid, uid))
        con.commit()

    await q.answer("✅ Accepted.")
    # notify both
    name_u = safe_display_name(uid)
    name_r = safe_display_name(rid)
    try:
        asyncio.create_task(send_and_delete_notification(context.bot, rid, f"✅ {name_u} accepted your friend request!", delay=5))
    except Exception:
        pass
    try:
        asyncio.create_task(send_and_delete_notification(context.bot, uid, f"🤝 You are now friends with {name_r}.", delay=5))
    except Exception:
        pass

    return await view_profile(update, context)


async def on_friend_decline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Decline an incoming friend request."""
    q = update.callback_query
    uid = q.from_user.id
    try:
        rid = int(q.data.split(":")[2])  # requester
    except Exception:
        return await q.answer("Invalid.", show_alert=True)

    with reg._conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM friend_requests WHERE requester_id=%s AND target_id=%s", (rid, uid))
        con.commit()

    await q.answer("❌ Declined.")
    # notify requester with auto-delete
    name_u = safe_display_name(uid)
    try:
        asyncio.create_task(send_and_delete_notification(context.bot, rid, f"❌ {name_u} declined your friend request.", delay=5))
    except Exception:
        pass

    return await view_profile(update, context)


async def on_post_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    data = q.data

    # Handle reactions: rx:<emoji>:<post_id>
    if data.startswith("rx:"):
        try:
            _, emoji, s_pid = data.split(":")
            pid = int(s_pid)
        except Exception:
            return await q.answer("Invalid reaction", show_alert=True)

        # persist reaction (replace user reaction)
        try:

            with reg._conn() as con, con.cursor() as cur:
                # Delete any prior reaction by this user for this post
                cur.execute("DELETE FROM feed_reactions WHERE post_id=%s AND user_id=%s", (pid, uid))
                # Add new one
                cur.execute("INSERT INTO feed_reactions(post_id,user_id,emoji) VALUES (%s,%s,%s)", (pid, uid, emoji))
                con.commit()
        except Exception as e:
            print(f"rx error: {e}")

        # send notification for reactions (all emojis)
        post = find_post(pid)
        if post:
            author_uid = post.get("author_id")
            actor_uid  = uid
            if author_uid and author_uid != actor_uid and _wants_feed_notify(author_uid):
                # Map emojis to nice titles
                titles = {
                    "😍": "😍 reacted to your post",
                    "🔥": "🔥 reacted to your post",
                    "😂": "😂 reacted to your post",
                    "😢": "😢 reacted to your post",
                    "❤️": "❤️ reacted to your post",
                }
                title = f"{_display_name(actor_uid)} {titles.get(emoji, 'reacted to your post')}"
                await _send_post_notify(context.bot,
                                        recipient_uid=author_uid,
                                        actor_uid=actor_uid,
                                        title=title,
                                        kind="like",
                                        pid=pid)

        # refresh caption
        post = find_post(pid)
        if not post:
            return
        ids = FEED_LIST.get(uid, [])
        idx = POST_INDEX.get(uid, 0)
        has_prev = idx > 0 if ids else False
        has_next = idx + 1 < len(ids) if ids else False
        own = (post.get("author_id") == uid)

        await q.answer()

        if post.get("video"):
            await q.edit_message_caption(caption=nz(build_post_caption(post)),
                                         reply_markup=build_nav_kb(pid, has_prev, has_next, own))
        elif post.get("photo"):
            await q.edit_message_caption(caption=nz(build_post_caption(post)),
                                         reply_markup=build_nav_kb(pid, has_prev, has_next, own))
        else:
            await q.edit_message_text(text=nz(build_post_caption(post)),
                                      reply_markup=build_nav_kb(pid, has_prev, has_next, own))
        return

    # Handle user profile viewing
    if data.startswith("uprof:"):
        return await view_profile(update, context)

    # Handle friend requests from profile
    if data.startswith("fr:req:"): # Specifically for friend requests
        return await handle_friend_request(update, context)

    # Handle friend add (reuse the same request flow)
    if data.startswith("friend:add:"):
        return await handle_friend_request(update, context)

    # Handle friend remove (bidirectional delete, then refresh profile)
    if data.startswith("friend:remove:"):
        q = update.callback_query
        uid = q.from_user.id
        try:
            tid = int(data.split(":")[2])
        except Exception:
            return await q.answer("Invalid.", show_alert=True)

        # Remove friendship both directions
        try:
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("DELETE FROM friends WHERE user_id=%s AND friend_id=%s", (uid, tid))
                cur.execute("DELETE FROM friends WHERE user_id=%s AND friend_id=%s", (tid, uid))
                con.commit()
            await q.answer("✅ Friend removed successfully.")
        except Exception as e:
            return await q.answer(f"Error: {e}", show_alert=True)

        # Create a mock callback query with the correct data to refresh profile
        class MockCallbackQuery:
            def __init__(self, original_q, target_uid):
                self.data = f"uprof:{target_uid}"
                self.from_user = original_q.from_user
                self.message = original_q.message
                self.original_q = original_q  # Store reference for answer method
                
            async def answer(self, *args, **kwargs):
                return await self.original_q.answer(*args, **kwargs)
        
        # Create mock update with new callback query
        mock_q = MockCallbackQuery(q, tid)
        mock_update = type('Update', (), {'callback_query': mock_q, 'effective_user': update.effective_user})()
        
        # Refresh the viewed profile - this will now show "Add Friend" button
        return await view_profile(mock_update, context)

    # Handle user-specific feed viewing
    if data.startswith("feed:user:"):
        return await show_user_feed(update, context)

    # Handle view_posts callback (legacy)
    if data.startswith("view_posts:"):
        return await view_posts(update, context)

    # Handle block/unblock
    if data.startswith("blk:add:"):
        tid = int(data.split(":")[2])
        with reg._conn() as con, con.cursor() as cur:
            # 1) Block the user (idempotent)
            cur.execute(
                "INSERT INTO blocked_users(user_id,blocked_uid) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (uid, tid)
            )

            # 2) Remove friendship both directions (if any)
            cur.execute("DELETE FROM friends WHERE user_id=%s AND friend_id=%s", (uid, tid))
            cur.execute("DELETE FROM friends WHERE user_id=%s AND friend_id=%s", (tid, uid))

            # 3) Remove any pending friend requests either way
            cur.execute("DELETE FROM friend_requests WHERE requester_id=%s AND target_id=%s", (uid, tid))
            cur.execute("DELETE FROM friend_requests WHERE requester_id=%s AND target_id=%s", (tid, uid))

            con.commit()

        await q.answer("Blocked & removed from friends.")
        # Optional: refresh viewed profile if you want the button state to update instantly
        return await view_profile(update, context)

    elif data.startswith("blk:del:"):
        tid = int(data.split(":")[2])
        reg.unblock_user(uid, tid)
        await q.answer("Unblocked.")
        return await view_profile(update, context)

    # Handle Secret Crush
    elif data.startswith("crush:add:"):
        tid = int(data.split(":")[2])
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("INSERT INTO secret_crush(user_id,target_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (uid, tid))
            # check reverse (did they already like me?)
            cur.execute("SELECT 1 FROM secret_crush WHERE user_id=%s AND target_id=%s", (tid, uid))
            rev = cur.fetchone() is not None
            con.commit()

        # Update crush leaderboard for the target
        reg.update_crush_leaderboard(tid)

        if rev:
            you  = safe_display_name(uid)
            them = safe_display_name(tid)
            
            # Current user gets auto-delete message (10 seconds) - they're online
            async def send_and_delete_current():
                try:
                    msg = await context.bot.send_message(uid, f"💘 Secret Crush matched with {them}! You both like each other.")
                    await asyncio.sleep(10)
                    await context.bot.delete_message(uid, msg.message_id)
                except Exception:
                    pass
            asyncio.create_task(send_and_delete_current())
            
            # Target user gets permanent message (might be offline)
            await context.bot.send_message(tid, f"💘 Secret Crush matched with {you}! You both like each other.")
        else:
            await q.answer("💘 Saved. We'll let you know if it's mutual!")
        return

    # Handle feed navigation
    if data == "next":
        return await handle_feed_nav(update, context)
    elif data == "prev":
        return await handle_feed_nav(update, context)

    # Handle post-specific actions
    data_parts = data.split(":")
    if len(data_parts) != 2:
        await q.answer()
        return

    action, pid = data_parts[0], int(data_parts[1])
    post = find_post(pid)
    if not post:
        await q.answer()
        return

    if action == "like":
        await q.answer()

        try:

            with reg._conn() as con, con.cursor() as cur:
                # Check if already liked
                cur.execute("SELECT 1 FROM feed_likes WHERE post_id=%s AND user_id=%s", (pid, uid))
                already_liked = cur.fetchone() is not None

                if already_liked:
                    # Remove like
                    cur.execute("DELETE FROM feed_likes WHERE post_id=%s AND user_id=%s", (pid, uid))
                else:
                    # Add like
                    cur.execute("INSERT INTO feed_likes (post_id, user_id) VALUES (%s,%s)", (pid, uid))
                con.commit()
        except Exception as e:
            print(f"Like error: {e}")

        # Refresh post data
        post = find_post(pid)
        if not post:
            return

        # Get current nav state
        ids = FEED_LIST.get(uid, [])
        idx = POST_INDEX.get(uid, 0)
        has_prev = idx > 0 if ids else False
        has_next = idx + 1 < len(ids) if ids else False
        own = (post.get("author_id") == uid)

        if post.get("video"):
            await q.edit_message_caption(caption=nz(build_post_caption(post)), reply_markup=build_nav_kb(pid, has_prev, has_next, own))
        elif post.get("photo"):
            await q.edit_message_caption(caption=nz(build_post_caption(post)), reply_markup=build_nav_kb(pid, has_prev, has_next, own))
        else:
            await q.edit_message_text(text=nz(build_post_caption(post)), reply_markup=build_nav_kb(pid, has_prev, has_next, own))

        # Send notification for like
        author_uid = post.get("author_id")
        actor_uid = uid
        if author_uid and author_uid != actor_uid and _wants_feed_notify(author_uid):
            title = f"❤️ {_display_name(actor_uid)} liked your post"
            await _send_post_notify(context.bot, recipient_uid=author_uid, actor_uid=actor_uid,
                                    title=title, kind="like", pid=pid)
        return

    if action == "cmt":
        context.user_data["state"] = f"comment:{pid}"
        await q.answer()
        msg = await q.message.reply_text("💬 Send your comment:")
        context.user_data['comment_prompt_id'] = msg.message_id  # store prompt message id
        return

    if action == "viewc":
        post = find_post(pid)
        if not post or not post["comments"]:
            await q.answer("No comments yet.", show_alert=True)
            return

        await q.answer()

        # Show all comments with proper formatting
        text = "💬 **Comments:**\n\n"
        for c in post["comments"]:
            text += f"👤 {c['user']}: {c['text']}\n"

        # Add back button to return to post
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Post", callback_data=f"backto:{pid}")]
        ])

        await q.message.reply_text(text, parse_mode=None, reply_markup=back_kb)
        return

    if action == "backto":
        # Return to post from comments view
        post = find_post(pid)
        if not post:
            await q.answer("Post not found.", show_alert=True)
            return

        await q.answer()

        # Get current nav state
        ids = FEED_LIST.get(uid, [])
        idx = POST_INDEX.get(uid, 0)
        has_prev = idx > 0 if ids else False
        has_next = idx + 1 < len(ids) if ids else False
        own = (post.get("author_id") == uid)

        # Track view when returning to post
        await _track_view(pid, uid)

        # Show the post again
        if post.get("video"):
            await q.message.reply_video(
                post["video"],
                caption=build_post_caption(post),
                reply_markup=build_nav_kb(pid, has_prev, has_next, own)
            )
        elif post["photo"]:
            await q.message.reply_photo(
                post["photo"],
                caption=build_post_caption(post),
                reply_markup=build_nav_kb(pid, has_prev, has_next, own)
            )
        else:
            await q.message.reply_text(
                build_post_caption(post),
                reply_markup=build_nav_kb(pid, has_prev, has_next, own)
            )
        return

    if action == "del":
        await q.answer()
        if post["author_id"] != uid:
            await q.answer("Not your post.", show_alert=True)
            return

        # Delete from database
        try:

            with reg._conn() as con, con.cursor() as cur:
                cur.execute("DELETE FROM feed_posts WHERE id=%s AND author_id=%s", (pid, uid))
                con.commit()
        except Exception as e:
            await q.answer(f"❌ Error deleting post: {e}", show_alert=True)
            return

        ids = FEED_LIST.get(uid, [])
        if post["id"] in ids:
            pos = ids.index(post["id"])
            ids.pop(pos)
            FEED_LIST[uid] = ids

        # If posts still left, show next/previous
        if ids:
            POST_INDEX[uid] = max(0, min(pos, len(ids) - 1))
            new_pid = ids[POST_INDEX[uid]]
            new_post = find_post(new_pid)
            if new_post:
                has_prev = POST_INDEX[uid] > 0
                has_next = POST_INDEX[uid] + 1 < len(ids)
                own = True
                if new_post.get("video"):
                    media = InputMediaVideo(media=new_post["video"], caption=nz(build_post_caption(new_post)))
                    await q.edit_message_media(media=media, reply_markup=build_nav_kb(new_pid, has_prev, has_next, own))
                elif new_post["photo"]:
                    media = InputMediaPhoto(media=new_post["photo"], caption=nz(build_post_caption(new_post)))
                    await q.edit_message_media(media=media, reply_markup=build_nav_kb(new_pid, has_prev, has_next, own))
                else:
                    await q.edit_message_text(nz(build_post_caption(new_post)), reply_markup=build_nav_kb(new_pid, has_prev, has_next, own))
            else:
                await safe_edit(q, "❌ Post not found. Use /post to create a new one!", kb_public_menu())
        else:
            # No posts left → remove the photo/text message and show a clean guide
            guide_text = "📭 You have no posts left.\n\n✍️ Use /post to create your first post!"
            guide_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Create Post", callback_data="pf:newpost")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="pf:myfeed")]
            ])

            # Photo posts ko text me edit nahi kar sakte; isliye delete karke fresh msg bhejte hai
            try:
                await q.message.delete()
            except Exception:
                pass

            await q.message.bot.send_message(
                chat_id=q.message.chat_id,
                text=guide_text,
                reply_markup=guide_kb
            )
        return

# --- My Feed actions (profile edit) ---

async def on_pf_edit_uname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["state"] = "set_uname"
    await safe_edit(q, "📝 Send your username (3–20 chars: a–z, 0–9, _)")
    # No more work here; the next TEXT goes to handle_post → user_state=="set_uname"

async def on_pf_edit_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["state"] = "set_bio"
    await safe_edit(q, "📖 Send your bio (up to 150 chars)")
    # Next TEXT → handle_post → user_state=="set_bio"

async def on_pf_toggle_priv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    try:

        with reg._conn() as con, con.cursor() as cur:
            cur.execute(
                "UPDATE users SET feed_is_public = NOT COALESCE(feed_is_public, TRUE) "
                "WHERE tg_user_id=%s RETURNING feed_is_public",
                (uid,)
            )
            new_status = bool(cur.fetchone()[0])
            con.commit()
        await q.answer(f"Privacy updated to {'Public' if new_status else 'Private'}!")
    except Exception as e:
        return await q.answer(f"❌ Error updating privacy: {e}", show_alert=True)

    # Refresh My Feed panel
    p = ensure_profile(uid)
    try:
        if q.message.text is not None:
            await q.edit_message_text(text=myfeed_text(uid), reply_markup=myfeed_keyboard(p), parse_mode="HTML")
        else:
            await q.edit_message_caption(caption=myfeed_text(uid), reply_markup=myfeed_keyboard(p), parse_mode="HTML")
    except Exception:
        await q.message.reply_text(myfeed_text(uid), reply_markup=myfeed_keyboard(p), parse_mode="HTML")

# === Back to menu handler ===
async def on_pf_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await safe_edit(q, "🌍 Public Feed Menu", kb_public_menu())

# === Clean back to menu handler (for stories) ===
async def on_pf_menu_clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    # Delete the story message and send clean menu
    try:
        await q.message.delete()
    except Exception:
        pass
    
    await context.bot.send_message(
        chat_id=q.message.chat_id,
        text="🌍 Public Feed Menu",
        reply_markup=kb_public_menu()
    )

# === Create post handler ===
async def on_pf_newpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["state"] = "awaiting_post"
    await safe_edit(q, "✍️ Send your post text **or** photo (with caption).", parse_mode="Markdown")

# === handle the 3 menu buttons (My Feed / Public Feed / Find User) ===
async def on_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data

    if data == "pf:myfeed":
        return await on_myfeed(update, context)

    elif data == "pf:public":
        # same code-path जो तुम on_public_menu में use करते हो:
        return await on_public_menu(update, context)

    elif data == "pf:findopen":
        context.user_data["pf_state"] = "awaiting_lookup"
        await q.answer()
        # Send a new clean message without any background image/media
        return await q.message.reply_text("🔎 Send username or numeric ID to search.")

async def on_blocked_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's blocked list with Unblock buttons."""
    q = update.callback_query
    uid = q.from_user.id
    context.user_data["blocked_menu"] = True

    blocked = _list_blocked(uid)
    if not blocked:
        p = ensure_profile(uid)
        await safe_edit(q, "✅ You haven't blocked anyone.", myfeed_keyboard(p))
        await q.answer()
        return

    rows = [
        [InlineKeyboardButton(f"✅ Unblock {safe_display_name(bid)}",
                              callback_data=f"blk:del:{bid}")]
        for (bid, _) in blocked
    ]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="pf:myfeed")])
    from telegram.constants import ParseMode
    await safe_edit(q, "🚫 <b>Blocked Users</b>", InlineKeyboardMarkup(rows), parse_mode=ParseMode.HTML)
    await q.answer()

async def on_stories_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open stories reel; show first author's latest story."""
    q = update.callback_query
    await q.answer()
    viewer = q.from_user.id

    # Collect ALL individual stories (not grouped by author)
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT s.id, s.author_id, s.created_at
                FROM stories s
                JOIN users u ON u.tg_user_id = s.author_id
                WHERE s.expires_at > NOW()
                  AND s.author_id <> %s
                  AND NOT EXISTS (
                      SELECT 1 FROM blocked_users bu
                       WHERE (bu.user_id=%s AND bu.blocked_uid=s.author_id)
                          OR (bu.user_id=s.author_id AND bu.blocked_uid=%s)
                  )
                  AND (
                        u.feed_is_public = TRUE
                        OR EXISTS (SELECT 1 FROM friends f
                                    WHERE f.user_id=%s AND f.friend_id=s.author_id)
                      )
                ORDER BY s.created_at DESC
            """, (viewer, viewer, viewer, viewer))
            rows = cur.fetchall()
    except Exception as e:
        return await safe_edit(q, f"❌ Error loading stories: {e}")

    stories = [(r[0], r[1]) for r in rows] if rows else []  # (story_id, author_id) pairs
    if not stories:
        return await safe_edit(q, "📭 No stories right now.", kb_public_menu())

    context.user_data["stories_list"] = stories
    context.user_data["stories_idx"] = 0
    return await _show_story_author(update, context)

async def _show_story_author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    viewer = q.from_user.id
    stories = context.user_data.get("stories_list", [])
    idx = context.user_data.get("stories_idx", 0)
    if idx < 0 or idx >= len(stories):
        # Acknowledge the callback query first
        await q.answer()
        
        # Delete the story message and send clean "End of stories" message
        try:
            await q.message.delete()
        except Exception:
            pass
        
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text="🏁 End of stories.",
            reply_markup=kb_public_menu()
        )
        return
    sid, au = stories[idx]  # Get story ID and author ID

    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT s.id, s.kind, s.text, s.media_id, s.created_at
            FROM stories s
            WHERE s.id=%s AND s.expires_at > NOW()
        """, (sid,))
        row = cur.fetchone()

    if not row:
        # skip if expired between loads
        context.user_data["stories_idx"] = idx + 1
        return await _show_story_author(update, context)

    story_id, kind, text, media, created = row
    name = safe_display_name(au)

    # compute views (unique)
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM story_views WHERE story_id=%s", (story_id,))
        vcount = int(cur.fetchone()[0] or 0)

    cap = f"📚 <b>{name}</b>\n{(text or '').strip()}\n\n👀 {vcount} views"
    
    # Only show Prev/Next buttons if there are multiple stories
    kb_rows = []
    if len(stories) > 1:
        kb_rows.append([
            InlineKeyboardButton("⬅️ Prev", callback_data="st:prev"),
            InlineKeyboardButton("➡️ Next", callback_data="st:next")
        ])
    
    kb_rows.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="pf:menu:clean")])
    kb = InlineKeyboardMarkup(kb_rows)

    # mark view (unique)
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute(
                "INSERT INTO story_views(story_id, viewer_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (story_id, viewer)
            )
            con.commit()
    except Exception as e:
        print("story view err", e)

    try:
        if kind == "photo":
            await q.edit_message_media(
                media=InputMediaPhoto(media=media, caption=cap, parse_mode="HTML"),
                reply_markup=kb
            )
        elif kind == "video":
            await q.edit_message_media(
                media=InputMediaVideo(media=media, caption=cap, parse_mode="HTML"),
                reply_markup=kb
            )
        else:
            await q.edit_message_text(cap, reply_markup=kb, parse_mode="HTML")
    except Exception:
        # fall back to sending new message
        if kind == "photo":
            await q.message.reply_photo(media, caption=cap, parse_mode="HTML", reply_markup=kb)
        elif kind == "video":
            await q.message.reply_video(media, caption=cap, parse_mode="HTML", reply_markup=kb)
        else:
            await q.message.reply_text(cap, parse_mode="HTML", reply_markup=kb)

async def on_stories_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "st:next":
        context.user_data["stories_idx"] = context.user_data.get("stories_idx", 0) + 1
    else:
        context.user_data["stories_idx"] = max(0, context.user_data.get("stories_idx", 0) - 1)
    return await _show_story_author(update, context)

# Removed handle_friend_dm_text and its related handlers as they are no longer needed.
# Removed the following lines from the register function:
#     # DM text must win over other text handlers
#     app.add_handler(
#         MessageHandler(filters.TEXT & ~filters.COMMAND, handle_friend_dm_text),
#         group=-4
#     )
#
#     # Direct friend messaging
#     app.add_handler(CallbackQueryHandler(on_friend_msg_start, pattern=r"^fm:msg:\d+$"))
#     app.add_handler(CallbackQueryHandler(on_friend_msg_cancel, pattern=r"^fm:cancel$"))
#     app.add_handler(CallbackQueryHandler(on_friend_msg_decide, pattern=r"^fm:(acc|dec):\d+$"))
# -------------------------------------------------------


# ---------- My Stories (author = viewer) ----------

async def on_my_stories_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open viewer's own stories (active ones)."""
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    # fetch this user's active stories
    try:
        import registration as reg
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT id
                FROM stories
                WHERE author_id=%s AND expires_at > NOW()
                ORDER BY created_at DESC
            """, (uid,))
            rows = cur.fetchall()
    except Exception as e:
        return await safe_edit(q, f"❌ Error loading your stories: {e}")

    sids = [r[0] for r in rows] if rows else []
    if not sids:
        return await q.message.reply_text("📭 You have no active stories.\n\nUse /story to post one!")

    context.user_data["my_stories"] = sids
    context.user_data["my_stories_idx"] = 0
    return await _show_my_story(update, context)


async def _show_my_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Render one of my stories (by index) with views count and viewers button."""
    q = update.callback_query
    uid = q.from_user.id
    sids = context.user_data.get("my_stories", [])
    idx = context.user_data.get("my_stories_idx", 0)

    if not sids:
        return await q.message.reply_text("📭 You have no active stories.\n\nUse /story to post one!")
    if idx < 0 or idx >= len(sids):
        # Acknowledge the callback query first
        await q.answer()
        
        # Delete the story message and send clean "End of your stories" message
        try:
            await q.message.delete()
        except Exception:
            pass
        
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text="🏁 End of your stories.",
            reply_markup=kb_public_menu()
        )
        return

    sid = sids[idx]

    try:
        import registration as reg
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT kind, text, media_id, created_at, expires_at
                FROM stories
                WHERE id=%s
            """, (sid,))
            row = cur.fetchone()
            if not row:
                # removed/expired between navigation; skip forward
                context.user_data["my_stories_idx"] = idx + 1
                return await _show_my_story(update, context)

            kind, text, media, created, expires = row

            cur.execute("SELECT COUNT(*) FROM story_views WHERE story_id=%s", (sid,))
            vcount = int(cur.fetchone()[0] or 0)
    except Exception as e:
        return await safe_edit(q, f"❌ Error: {e}", kb_public_menu())

    # caption
    left_min = int(max(0, (expires - datetime.now(timezone.utc)).total_seconds() // 60))
    cap = (f"📚 <b>My Story</b>\n"
           f"{(text or '').strip()}\n\n"
           f"👀 <b>{vcount}</b> views • ⏳ {left_min} min left")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Prev", callback_data="stmy:prev"),
         InlineKeyboardButton("➡️ Next", callback_data="stmy:next")],
        [InlineKeyboardButton("👤 Viewers", callback_data=f"stmy:viewers:{sid}")],
        [InlineKeyboardButton("🗑️ Delete",  callback_data=f"stmy:del:{sid}")],
        [InlineKeyboardButton("⬅️ Back",    callback_data="pf:myfeed")]
    ])

    try:
        if kind == "photo":
            await q.edit_message_media(InputMediaPhoto(media=media, caption=cap, parse_mode="HTML"), reply_markup=kb)
        elif kind == "video":
            await q.edit_message_media(InputMediaVideo(media=media, caption=cap, parse_mode="HTML"), reply_markup=kb)
        else:
            await q.edit_message_text(cap, parse_mode="HTML", reply_markup=kb)
    except Exception:
        # send new if edit fails
        if kind == "photo":
            await q.message.reply_photo(media, caption=cap, parse_mode="HTML", reply_markup=kb)
        elif kind == "video":
            await q.message.reply_video(media, caption=cap, parse_mode="HTML", reply_markup=kb)
        else:
            await q.message.reply_text(cap, parse_mode="HTML", reply_markup=kb)


async def on_my_stories_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "stmy:next":
        context.user_data["my_stories_idx"] = context.user_data.get("my_stories_idx", 0) + 1
    else:
        context.user_data["my_stories_idx"] = max(0, context.user_data.get("my_stories_idx", 0) - 1)
    return await _show_my_story(update, context)


async def on_my_story_viewers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show up to 20 latest viewers for my story."""
    q = update.callback_query
    await q.answer()
    try:
        sid = int(q.data.split(":")[2])
    except Exception:
        return

    try:
        import registration as reg
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT viewer_id, viewed_at
                FROM story_views
                WHERE story_id=%s
                ORDER BY viewed_at DESC
                LIMIT 20
            """, (sid,))
            rows = cur.fetchall()
    except Exception as e:
        return await q.message.reply_text(f"❌ Error loading viewers: {e}")

    if not rows:
        return await q.message.reply_text("👀 No viewers yet.")

    lines = []
    for vid, vat in rows:
        nm = safe_display_name(vid)
        lines.append(f"• {nm}")
    txt = "👀 <b>Recent viewers</b>\n" + "\n".join(lines)
    await q.message.reply_text(txt, parse_mode="HTML")

async def on_my_story_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete my story and move to the next one (or show empty state)."""
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    try:
        sid = int(q.data.split(":")[2])
    except Exception:
        return await q.answer("Invalid story.", show_alert=True)

    # verify ownership & delete
    try:
        import registration as reg
        with reg._conn() as con, con.cursor() as cur:
            # ensure it's my story
            cur.execute("SELECT author_id FROM stories WHERE id=%s", (sid,))
            row = cur.fetchone()
            if not row:
                return await q.answer("Already removed.", show_alert=False)
            if int(row[0]) != uid:
                return await q.answer("Not your story.", show_alert=True)

            # delete views first then story
            cur.execute("DELETE FROM story_views WHERE story_id=%s", (sid,))
            cur.execute("DELETE FROM stories WHERE id=%s", (sid,))
            con.commit()
    except Exception as e:
        return await q.answer(f"Delete failed: {e}", show_alert=True)

    # Update the in-memory list & index
    sids = context.user_data.get("my_stories", [])
    idx  = context.user_data.get("my_stories_idx", 0)
    if sid in sids:
        pos = sids.index(sid)
        sids.pop(pos)
        # keep index at the same position (which now points to next item)
        if pos < idx:
            idx -= 1
        context.user_data["my_stories_idx"] = min(idx, max(0, len(sids)-1))
        context.user_data["my_stories"] = sids

    await q.answer("🗑️ Deleted.")
    if not sids:
        return await q.message.reply_text("📭 You have no active stories.\n\nUse /story to post one!")
    # Show next/remaining
    return await _show_my_story(update, context)

# -------------------------------------------------------

async def on_my_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show ONLY the current user's posts (no public feed header)."""
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    try:
        # Fetch user's own posts (DB-based)

        with reg._conn() as con, con.cursor() as cur:
            cur.execute(
                "SELECT id FROM feed_posts WHERE author_id=%s ORDER BY created_at DESC",
                (uid,)
            )
            rows = cur.fetchall()

        if not rows:
            guide_text = "📭 You have no posts yet.\n\n✍️ Use /post to create your first post!"
            guide_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Create Post", callback_data="pf:newpost")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="pf:myfeed")]
            ])
            await safe_edit(q, guide_text, guide_kb)
            return

        post_ids = [r[0] for r in rows]
        FEED_LIST[uid] = post_ids
        POST_INDEX[uid] = 0

        pid = post_ids[0]
        post = find_post(pid)
        if not post:
            await safe_edit(q, "❌ Error loading posts.", kb_public_menu())
            return

        has_prev = False
        has_next = len(post_ids) > 1
        own = True  # "My Posts" are always the user's

        # Track view
        await _track_view(pid, uid)

        # NO public-feed header here
        if post.get("video"):
            await q.message.reply_video(
                post["video"],
                caption=build_post_caption(post),
                reply_markup=build_nav_kb(pid, has_prev, has_next, own)
            )
        elif post.get("photo"):
            await q.message.reply_photo(
                post["photo"],
                caption=build_post_caption(post),
                reply_markup=build_nav_kb(pid, has_prev, has_next, own)
            )
        else:
            await q.message.reply_text(
                build_post_caption(post),
                reply_markup=build_nav_kb(pid, has_prev, has_next, own)
            )
    except Exception as e:
        await safe_edit(q, f"❌ Error loading posts: {e}", kb_public_menu())

# --- Sensual Stories callback ---
async def on_sensual_stories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle sensual stories button click"""
    query = update.callback_query
    await query.answer()
    
    try:
        from handlers.sensual_stories import get_admin_ids
        from registration import is_premium_user
        from datetime import datetime, timedelta
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        import registration as reg
        
        user_id = query.from_user.id
        admin_ids = get_admin_ids()
        is_admin = user_id in admin_ids
        is_premium = is_premium_user(user_id)

        # Show admin panel for admins
        if is_admin:
            admin_menu = InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Post New Story", callback_data="sensual:admin:new")],
                [InlineKeyboardButton("📋 Manage Stories", callback_data="sensual:admin:manage")],
                [InlineKeyboardButton("📖 View Stories", callback_data="sensual:admin:view")],
                [InlineKeyboardButton("⬅️ Back to Feed", callback_data="pf:menu")]
            ])
            await query.edit_message_text(
                "🔧 **Admin Panel - Sensual Stories**\n\n"
                "Choose an action:",
                parse_mode='Markdown',
                reply_markup=admin_menu
            )
            return

        # Regular user flow - get stories from database  
        with reg._conn() as con, con.cursor() as cur:
            # Completely free access - no premium restrictions!
            cur.execute("""
                SELECT id, title, content, created_at 
                FROM sensual_stories 
                ORDER BY created_at DESC
            """)
            
            stories = cur.fetchall()

        if not stories:
            await query.edit_message_text(
                "📭 **No stories available right now!**\n\n"
                "🔥 **New stories every weekend!**\n"
                "📅 Fresh content drops every Friday, Saturday & Sunday\n"
                "💫 Enjoy your weekend with sensual stories!\n\n"
                "🌟 Check back this weekend for exciting new content...",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back to Feed", callback_data="pf:menu")
                ]])
            )
            return

        # Use pagination system - show first story only
        from handlers.sensual_stories import _show_story_by_index_public
        await _show_story_by_index_public(query, 0, stories, user_id)

    except Exception as e:
        await query.edit_message_text(
            "❌ Sensual Stories are temporarily unavailable. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Feed", callback_data="pf:menu")
            ]])
        )

# --- Register handlers ---
def register(app):
    app.add_handler(CommandHandler("post", cmd_post))
    app.add_handler(CommandHandler("story", cmd_story))
    app.add_handler(CommandHandler("public", cmd_public))     # /public -> menu


    app.add_handler(CallbackQueryHandler(on_myfeed,       pattern=r"^pf:myfeed$"))
    app.add_handler(CallbackQueryHandler(on_public_menu,  pattern=r"^pf:public$"))
    app.add_handler(CallbackQueryHandler(on_my_posts,     pattern=r"^pf:myposts$"))
    app.add_handler(CallbackQueryHandler(on_blocked_menu, pattern=r"^pf:blocked$"))
    app.add_handler(CallbackQueryHandler(on_stories_open, pattern=r"^pf:stories$"))
    app.add_handler(CallbackQueryHandler(on_stories_nav,  pattern=r"^st:(next|prev)$"))
    app.add_handler(CallbackQueryHandler(on_my_stories_open,  pattern=r"^pf:mystories$"))
    app.add_handler(CallbackQueryHandler(on_my_stories_nav,   pattern=r"^stmy:(next|prev)$"))
    app.add_handler(CallbackQueryHandler(on_my_story_viewers, pattern=r"^stmy:viewers:\d+$"))
    app.add_handler(CallbackQueryHandler(on_my_story_delete,  pattern=r"^stmy:del:\d+$"))
    app.add_handler(CallbackQueryHandler(on_sensual_stories, pattern=r"^pf:sensual$"))
    app.add_handler(CallbackQueryHandler(on_menu_buttons, pattern=r"^pf:findopen$"))
    app.add_handler(CallbackQueryHandler(on_pf_menu,      pattern=r"^pf:menu$"))
    app.add_handler(CallbackQueryHandler(on_pf_menu_clean, pattern=r"^pf:menu:clean$"))
    app.add_handler(CallbackQueryHandler(on_pf_newpost,   pattern=r"^pf:newpost$"))

    # My Feed edit actions
    app.add_handler(CallbackQueryHandler(on_pf_edit_uname,  pattern=r"^pf:edit_uname$"))
    app.add_handler(CallbackQueryHandler(on_pf_edit_bio,   pattern=r"^pf:edit_bio$"))
    app.add_handler(CallbackQueryHandler(on_pf_toggle_priv, pattern=r"^pf:toggle$"))
    
    # Add missing Fun & Games handler
    from handlers.funhub import funhub_menu
    async def on_pf_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.callback_query.answer()
        await funhub_menu(update, context)
    app.add_handler(CallbackQueryHandler(on_pf_games, pattern=r"^pf:games$"))


    # Enhanced callback patterns for profile, friend, and block functionality
    app.add_handler(CallbackQueryHandler(on_post_cb, pattern=r"^(like|cmt|viewc|backto|del):\d+$|^(next|prev)$|^uprof:\d+(?::\d+)?$|^friend:(add|remove):\d+$|^feed:user:\d+$|^view_posts:\d+:\d+$|^blk:(add|del):\d+$"))

    # Friend request handlers
    app.add_handler(CallbackQueryHandler(on_friend_cancel,  pattern=r"^fr:cancel:\d+$"))
    app.add_handler(CallbackQueryHandler(on_friend_accept,  pattern=r"^fr:accept:\d+$"))
    app.add_handler(CallbackQueryHandler(on_friend_decline, pattern=r"^fr:decline:\d+$"))

    # Friends list handler
    app.add_handler(CallbackQueryHandler(view_profile_friends, pattern=r"^uprof:friends:\d+$"))

    # Register reaction handler
    app.add_handler(CallbackQueryHandler(on_post_cb, pattern=r"^rx:.+$"))
    # Secret crush callbacks
    app.add_handler(CallbackQueryHandler(on_post_cb, pattern=r"^crush:(add|del):\d+$"))

    # Add handler for settings callback
    app.add_handler(CallbackQueryHandler(set_feed_notify, pattern=r"^set:feednotify:(on|off)$"))

    # Message handlers for post creation
    app.add_handler(
        MessageHandler((filters.PHOTO | filters.VIDEO) & (~filters.COMMAND), handle_post),
        group=9
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_post_guarded, block=False),
        group=10
    )


# Note: The database alteration `ALTER TABLE users ADD COLUMN IF NOT EXISTS feed_notify BOOLEAN DEFAULT TRUE;`
# should be run separately, ideally via a migration script. This Python code assumes the column exists.

async def set_feed_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    data = q.data

    if data.startswith("set:feednotify:"):
        val_str = data.split(":")[-1]
        val = val_str == "on"

        try:
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("UPDATE users SET feed_notify=%s WHERE tg_user_id=%s", (val, uid))
                con.commit()
            await q.answer(f"Feed notifications are now: {val_str.capitalize()}!")
        except Exception as e:
            await q.answer(f"Error updating notification settings: {e}", show_alert=True)

        # Re-show settings menu or a confirmation message
        return await show_settings(update, context) # Assuming show_settings exists and displays the relevant panel




# --- Notification Gate Function ---
def _wants_feed_notify(uid:int)->bool:
    """Checks if a user wants to receive feed notifications."""
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT COALESCE(feed_notify, TRUE) FROM users WHERE tg_user_id=%s",(uid,))
            row = cur.fetchone()
            return bool(row[0]) if row is not None else True
    except Exception as e:
        print(f"feed_notify check error for {uid}: {e}")
        return True

async def _send_post_notify(bot, *, recipient_uid: int, actor_uid: int,
                            title: str, body: str = "", kind: str = "like", pid: int):
    """
    kind: 'like' or 'comment' – affects button text.
    Sends the ACTOR's photo if available, otherwise plain text.
    """
    # respect mute
    if not (recipient_uid and recipient_uid != actor_uid and _wants_feed_notify(recipient_uid)):
        return

    btn_text = "👣 See who likes you" if kind == "like" else "💬 See who commented"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, callback_data=f"uprof:{actor_uid}:{pid}")]])

    # ✅ use actor's photo (the person who liked/commented)
    photo_id = None
    try:
        photo_id = reg.get_photo_file(actor_uid)
    except Exception:
        photo_id = None

    caption = (title + ("\n" + body if body else "")).strip()
    try:
        if photo_id:
            await bot.send_photo(recipient_uid, photo=photo_id, caption=caption, reply_markup=kb)
        else:
            await bot.send_message(recipient_uid, text=caption, reply_markup=kb)
    except Exception:
        await bot.send_message(recipient_uid, text=caption, reply_markup=kb)

# --- Maybe add a show_settings function here if it's not already defined elsewhere ---
# Example placeholder:
async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for showing settings menu."""
    q = update.callback_query
    uid = q.from_user.id

    # Fetch notification setting
    notify_setting = "on" # Default or fetched from DB
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT feed_notify FROM users WHERE tg_user_id=%s", (uid,))
            row = cur.fetchone()
            if row:
                notify_setting = "on" if row[0] else "off"
    except Exception:
        pass # Use default if DB error

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔔 Feed Notifications: {'ON' if notify_setting == 'on' else 'OFF'}", callback_data=f"set:feednotify:{'off' if notify_setting == 'on' else 'on'}")]
        # Add other settings here
    ])
    await safe_edit(q, "⚙️ Settings", kb)


# --- My Feed actions (profile edit) ---

# The functions on_pf_edit_uname, on_pf_edit_bio, on_pf_toggle_priv are already defined above.

# The function on_pf_menu is already defined above.
# The function on_pf_newpost is already defined above.
# The function on_menu_buttons is already defined above.
# The function on_blocked_menu is already defined above.
# The functions on_stories_open and on_stories_nav are already defined above.
# The function on_my_posts is already defined above.
# The register function is already defined above.
# The set_feed_notify function is already defined above.
# The _wants_feed_notify and _send_post_notify functions are already defined above.
# The show_settings function is a placeholder and needs to be fully implemented if used.

# Removed handle_friend_dm_text and its related handlers as they are no longer needed.
# Removed the following lines from the register function:
#     # DM text must win over other text handlers
#     app.add_handler(
#         MessageHandler(filters.TEXT & ~filters.COMMAND, handle_friend_dm_text),
#         group=-4
#     )
#
#     # Direct friend messaging
#     app.add_handler(CallbackQueryHandler(on_friend_msg_start, pattern=r"^fm:msg:\d+$"))
#     app.add_handler(CallbackQueryHandler(on_friend_msg_cancel, pattern=r"^fm:cancel$"))
#     app.add_handler(CallbackQueryHandler(on_friend_msg_decide, pattern=r"^fm:(acc|dec):\d+$"))