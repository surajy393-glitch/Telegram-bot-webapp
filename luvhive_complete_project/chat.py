# chat.py — instant-intro version (drop-in full file)
# - Sends a quick intro immediately (no DB) when FAST_INTRO=1
# - Posts premium details (gender/age/ratings/shared) AFTER the quick intro (async)
# - Keeps queue logic, girls/boys filters, /next, /stop, rating, relay, reports unchanged

from __future__ import annotations

import os
import time
import asyncio
import logging
import random
import re
from collections import deque
from typing import Set

import psycopg2
from psycopg2.pool import SimpleConnectionPool

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ApplicationHandlerStop,
)

from menu import main_menu_kb
import registration as reg
from admin import ADMIN_IDS # Importing ADMIN_IDS
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from utils.display import safe_display_name
from utils.cb import cb_match, CBError
from utils.input_validation import validate_and_sanitize_input
from handlers.text_framework import FEATURE_KEY, MODE_KEY

log = logging.getLogger("luvbot.chat")

# Enhanced send wrapper with rate limiting and network resilience  
async def send_safe(bot, *args, **kwargs):
    from telegram.error import TimedOut, NetworkError, RetryAfter
    from utils.rate_limiter import allow_send
    import asyncio, random
    
    # Extract user_id for rate limiting (from chat_id or first positional arg)
    user_id = kwargs.get('chat_id') or (args[0] if args else None)
    
    # Apply rate limiting if user_id available
    if user_id and not allow_send(user_id):
        log.warning(f"Rate limit prevented send to user {user_id}")
        return None  # Silently drop rate-limited messages
    
    # Retry with exponential backoff and jitter
    for attempt in range(3):
        try:
            return await bot.send_message(*args, **kwargs)
        except RetryAfter as e:
            # Telegram flood control - respect the retry_after
            log.warning(f"FloodWait: sleeping {e.retry_after}s for user {user_id}")
            await asyncio.sleep(e.retry_after + 0.5)
        except (TimedOut, NetworkError) as e:
            # Transient network errors - retry with backoff
            delay = 0.5 * (attempt + 1) + random.random() / 3
            log.warning(f"Network error on attempt {attempt+1}: {e}, retrying in {delay:.1f}s")
            await asyncio.sleep(delay)
    
    # Final attempt (let it raise if still failing)
    try:
        return await bot.send_message(*args, **kwargs)
    except Exception as e:
        log.error(f"send_safe final failure for user {user_id}: {e}")
        raise

# exact button texts (reply keyboard) ko skip karne ke liye
MENU_RE = re.compile(
    r"^(⚡ Find a Partner|👧 Match with girls|👨 Match with boys|👤 My Profile|⚙️ Settings|💎 Premium)$"
)

# Refined content moderation for dating platform
# ChatGPT recommendation: Allow sexual language, block actual harassment
from utils.content_moderation import moderate_message

def _check_content_moderation(text: str, user_id: int) -> dict:
    """Check content with dating-platform appropriate moderation."""
    return moderate_message(text, user_id)

# ------------------------------------------------------------------------------
# Config / Flags
# ------------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL", "")
FAST_INTRO = os.getenv("FAST_INTRO", "0") == "1"  # set FAST_INTRO=1 for instant first message

# ------------------------------------------------------------------------------
# Runtime state (search queue + active pairs)
# ------------------------------------------------------------------------------

queue: deque[int] = deque()
queue_lock = asyncio.Lock()
peers: dict[int, int] = {}

# uid -> target_uid (mutual rematch intent)
REMATCH_TARGET: dict[int, int] = {}

def in_chat(user_id: int) -> bool:
    return user_id in peers

def partner_of(user_id: int) -> int | None:
    return peers.get(user_id)

# --- Secret Chat runtime state -----------------------------------------------
import datetime

# uid -> {"partner": int, "expires_at": datetime, "ttl": int, "inviter": int}
secret_sessions: dict[int, dict] = {}

# (uid, sender_msg_id) -> stored media awaiting approval
pending_secret_media: dict[tuple[int, int], dict] = {}

# Boost cooldown tracking
_last_boost_at: dict[int, float] = {}

def _seconds_until(dt: datetime.datetime) -> float:
    """UTC aware seconds from now until dt (never negative)."""
    now = datetime.datetime.utcnow()
    return max(0.0, (dt - now).total_seconds())

async def _auto_end_secret(uid_a: int, uid_b: int, expires_at: datetime.datetime, app):
    """
    Sleep until expiry, then end secret for both sides and notify.
    Safe if already ended manually (checks session state).
    """
    await asyncio.sleep(_seconds_until(expires_at))

    # both still in secret session and paired to each other?
    s_a = secret_sessions.get(uid_a)
    s_b = secret_sessions.get(uid_b)
    if not (s_a and s_b):  # already ended
        return
    if s_a.get("partner") != uid_b or s_b.get("partner") != uid_a:
        return

    # pop both
    secret_sessions.pop(uid_a, None)
    secret_sessions.pop(uid_b, None)

    text = ("⏳ Secret Chat ended. Back to normal chat.\n"
            "🛡️ To report a user type /report")
    try:
        await app.bot.send_message(uid_a, text)
    except Exception as e:
        log.warning(f"Failed to send secret end notification to {uid_a}: {e}")
    try:
        await app.bot.send_message(uid_b, text)
    except Exception as e:
        log.warning(f"Failed to send secret end notification to {uid_b}: {e}")

# --- Last chat partner tracking (for post-chat reports) ---
# uid -> {"partner": int, "in_secret": bool, "ts": datetime}
last_chat_partner: dict[int, dict] = {}

def _remember_last_partner(a: int, b: int, in_secret: bool):
    now = datetime.datetime.utcnow()
    last_chat_partner[a] = {"partner": b, "in_secret": in_secret, "ts": now}
    last_chat_partner[b] = {"partner": a, "in_secret": in_secret, "ts": now}

# utility: auto delete after X sec
async def send_and_delete(bot, chat_id, text, delay=5):
    msg = await bot.send_message(chat_id, text)
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, msg.message_id)
    except:
        pass

# Invite composer state (choices before sending)
pending_secret_invites: dict[int, dict] = {} # inviter_uid -> {"ttl": int|None, "dur": int|None}

def _secret_active(uid: int) -> bool:
    s = secret_sessions.get(uid)
    if not s:
        return False
    if datetime.datetime.utcnow() >= s["expires_at"]:
        # auto-expire both sides
        partner = s["partner"]
        secret_sessions.pop(uid, None)
        secret_sessions.pop(partner, None)
        return False
    return True

def _secret_partner(uid: int) -> int | None:
    s = secret_sessions.get(uid)
    return s["partner"] if s else None

# ------------------------------------------------------------------------------
# Small Postgres connection pool (kills connect latency on Replit)
# ------------------------------------------------------------------------------

DB_POOL: SimpleConnectionPool | None = None
if DATABASE_URL:
    try:
        DB_POOL = SimpleConnectionPool(1, 5, dsn=DATABASE_URL, connect_timeout=3)
    except Exception as e:
        DB_POOL = None
        log.warning(f"DB pool not created: {e}")

def _exec_noresult(sql: str, params: tuple):
    """Execute a write query fast via pool (ignore result)."""
    if not DATABASE_URL:
        return
    conn = None
    try:
        conn = DB_POOL.getconn() if DB_POOL else psycopg2.connect(DATABASE_URL, connect_timeout=3)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql, params)
    finally:
        try:
            if DB_POOL and conn:
                DB_POOL.putconn(conn)
            elif conn:
                conn.close()
        except Exception as e:
            log.warning(f"Failed to close DB connection: {e}")

# ------------------------------------------------------------------------------
# DB setup for ratings/reports (safe if already exists)
# ------------------------------------------------------------------------------

def init_db():
    if not DATABASE_URL:
        log.warning("No DATABASE_URL; ratings/reports tables skipped")
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_ratings (
            id SERIAL PRIMARY KEY,
            rater_id  BIGINT NOT NULL,
            ratee_id  BIGINT NOT NULL,
            value     SMALLINT NOT NULL,      -- +1 / -1
            reason    TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id BIGSERIAL PRIMARY KEY,
            reporter BIGINT NOT NULL,
            target   BIGINT NOT NULL,
            reason   TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
        conn.commit()
        cur.close()
        conn.close()
        log.info("✅ chat_ratings and reports tables ensured")
    except Exception as e:
        log.error(f"❌ DB tables error: {e}")

# ------------------------------------------------------------------------------
# Metrics helpers (pooled; never block user-visible sends)
# ------------------------------------------------------------------------------

def increment_sent(user_id: int):
    _exec_noresult(
        "UPDATE users SET messages_sent = COALESCE(messages_sent,0)+1 WHERE tg_user_id=%s",
        (user_id,),
    )

def increment_received(user_id: int):
    _exec_noresult(
        "UPDATE users SET messages_recv = COALESCE(messages_recv,0)+1 WHERE tg_user_id=%s",
        (user_id,),
    )

def increment_dialogs(user_id: int):
    _exec_noresult(
        "UPDATE users "
        "SET dialogs_total = COALESCE(dialogs_total,0)+1, dialogs_today = COALESCE(dialogs_today,0)+1 "
        "WHERE tg_user_id=%s",
        (user_id,),
    )

def bump_rating_counters(ratee_id: int, value: int):
    up = 1 if value > 0 else 0
    down = 1 if value < 0 else 0
    if not up and not down:
        return
    _exec_noresult(
        "UPDATE users "
        "SET rating_up = COALESCE(rating_up,0)+%s, rating_down = COALESCE(rating_down,0)+%s "
        "WHERE tg_user_id=%s",
        (up, down, ratee_id),
    )

def bump_report_counter(target_id: int):
    _exec_noresult(
        "UPDATE users SET report_count = COALESCE(report_count,0)+1 WHERE tg_user_id=%s",
        (target_id,),
    )

# ------------------------------------------------------------------------------
# Menu deduplication helper
# ------------------------------------------------------------------------------

# --- de-duplicate "What would you like to do next?" across flows ---
_last_menu_at: dict[int, float] = {}

def _menu_recent(chat_id: int, ttl: float = 60.0) -> bool:
    """
    Return True if we already sent a menu to this chat within ttl seconds.
    If not recent, mark now and return False.
    """
    import time
    now = time.time()
    last = _last_menu_at.get(chat_id, 0.0)
    if now - last < ttl:
        return True
    _last_menu_at[chat_id] = now
    return False

async def _send_menu_once(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str = "What would you like to do next?",
    ttl: float = 60.0,
):
    if _menu_recent(chat_id, ttl):
        return
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=main_menu_kb())

# ------------------------------------------------------------------------------
# Ratings & reports persistence
# ------------------------------------------------------------------------------

def _norm(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKC", s).replace("\uFE0F", "").strip().lower()

def _is_menu_text(s: str) -> bool:
    from menu import (
        BTN_FIND, BTN_FIND_PARTNER, BTN_MATCH_GIRLS, BTN_MATCH_BOYS,
        BTN_MY_PROFILE, BTN_SETTINGS, BTN_PREMIUM
    )
    candidates = [
        BTN_FIND, BTN_FIND_PARTNER, BTN_MATCH_GIRLS, BTN_MATCH_BOYS,
        BTN_MY_PROFILE, BTN_SETTINGS, BTN_PREMIUM,
        "⚡ Find a Partner", "Find a Partner",
    ]
    sN = _norm(s or "")
    return any(_norm(x) == sN for x in candidates if x)

def save_rating(rater: int, ratee: int, value: int, reason: str | None = None):
    if not DATABASE_URL:
        return
    conn = None
    try:
        conn = DB_POOL.getconn() if DB_POOL else psycopg2.connect(DATABASE_URL, connect_timeout=3)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_ratings (rater_id, ratee_id, value, reason) VALUES (%s,%s,%s,%s)",
                (rater, ratee, value, reason),
            )
        bump_rating_counters(ratee, value)
    except Exception as e:
        log.error(f"rating save failed: {e}")
    finally:
        try:
            if DB_POOL and conn:
                DB_POOL.putconn(conn)
            elif conn:
                conn.close()
        except Exception as e:
            log.warning(f"Failed to close DB connection: {e}")

def save_report(reporter: int, target: int, reason: str):
    if not DATABASE_URL:
        return
    conn = None
    try:
        conn = DB_POOL.getconn() if DB_POOL else psycopg2.connect(DATABASE_URL, connect_timeout=3)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO reports (reporter, target, reason) VALUES (%s,%s,%s)",
                (reporter, target, reason),
            )
        bump_report_counter(target)
    except Exception as e:
        log.error(f"report save failed: {e}")
    finally:
        try:
            if DB_POOL and conn:
                DB_POOL.putconn(conn)
            elif conn:
                conn.close()
        except Exception as e:
            log.warning(f"Failed to close DB connection: {e}")

# ------------------------------------------------------------------------------
# Keyboards
# ------------------------------------------------------------------------------

def rating_kb(target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("👍", callback_data=f"rate:good:{target_id}"),
                InlineKeyboardButton("👎", callback_data=f"rate:bad:{target_id}"),
            ],
            [InlineKeyboardButton("⚠️ Report", callback_data="report:start")],
        ]
    )



# ------------------------------------------------------------------------------
# Premium intro helpers
# ------------------------------------------------------------------------------

def _rating_counts_for(user_id: int) -> tuple[int, int]:
    """Count +1 / -1 from chat_ratings quickly via pool."""
    if not DATABASE_URL:
        return (0, 0)
    conn = None
    try:
        conn = DB_POOL.getconn() if DB_POOL else psycopg2.connect(DATABASE_URL, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT "
                "COALESCE(SUM(CASE WHEN value=1 THEN 1 ELSE 0 END),0), "
                "COALESCE(SUM(CASE WHEN value=-1 THEN 1 ELSE 0 END),0) "
                "FROM chat_ratings WHERE ratee_id=%s",
                (user_id,),
            )
            row = cur.fetchone() or (0, 0)
            return int(row[0] or 0), int(row[1] or 0)
    except Exception:
        return (0, 0)
    finally:
        try:
            if DB_POOL and conn:
                DB_POOL.putconn(conn)
            elif conn:
                conn.close()
        except Exception as e:
            log.warning(f"Failed to close DB connection: {e}")

def _shared_interests_text(viewer_id: int, partner_id: int) -> str:
    try:
        v = reg.get_profile(viewer_id)
        p = reg.get_profile(partner_id)
        vset: Set[str] = set(v.get("interests", set()) or set())
        pset: Set[str] = set(p.get("interests", set()) or set())
        shared = list(vset & pset)
        if not shared:
            return "—"
        label_map = {k: f"{e} {n}" for (k, n, e, _prem) in getattr(reg, "INTERESTS", [])}
        pretty = [label_map.get(k, k) for k in shared]
        return ", ".join(pretty[:6])
    except Exception:
        return "—"

def _intro_text_for(viewer_id: int, partner_id: int, ice: str) -> str:
    """Build the first intro text. FAST_INTRO avoids DB for instant send."""
    # Free users: simple intro (no DB)
    if not reg.has_active_premium(viewer_id):
        p = reg.get_profile(partner_id) or {}
        verified = "Yes" if p.get("is_verified") else "No"
        return (
            "✨💕 A mysterious soul awaits you... 💕✨\n"
            "🌹 Your anonymous heart-to-heart begins now 🌹\n\n"
            f"💫 Icebreaker: {ice} 💫\n\n"
            f"✅ Verified: {verified}\n\n"
            "💞 /next - Seek another destiny\n"
            "🔮 /stop - End this magical moment"
        )

    # Premium users
    if FAST_INTRO:
        # Do NOT hit DB here; placeholders. Details sent later.
        gender, age = "—", "—"
        up, down = (0, 0)
        shared = "—"
    else:
        # Rich path with DB
        p = reg.get_profile(partner_id) or {}
        gender = (p.get("gender") or "—").capitalize()
        age = p.get("age") or "—"
        up, down = _rating_counts_for(partner_id)
        shared = _shared_interests_text(viewer_id, partner_id)

    # Get verification status
    verified = "Yes" if FAST_INTRO else ("Yes" if p.get("is_verified") else "No")

    return (
        "✨💕 The stars have aligned... a soul connection awaits 💕✨\n"
        "🌹 Two hearts, anonymous yet destined to meet 🌹\n\n"
        f"💫 Conversation spark: {ice} 💫\n\n"
        "💖 Begin your romantic journey...\n\n"
        f"🎭 Mystery profile: {gender}, {age}\n"
        f"💎 Community trust: {up}👍  {down}👎\n"
        f"✅ Verified soul: {verified}\n"
        f"💞 Shared passions: {shared}\n\n"
        "🔮 /next - Seek another destiny\n"
        "💫 /stop - End this magical encounter"
    )

# Quick intro (no DB) for truly instant UX
def _intro_text_quick(viewer_id: int, partner_id: int, ice: str) -> str:
    # Minimal DB: fetch only 'is_verified' for safety to show to everyone
    try:
        p = reg.get_profile(partner_id) or {}
        verified = "Yes" if p.get("is_verified") else "No"
    except Exception:
        verified = "—"
    return (
        "✨💕 A mysterious soul awaits you... 💕✨\n"
        "🌹 Your anonymous heart-to-heart begins now 🌹\n\n"
        f"💫 Icebreaker: {ice} 💫\n\n"
        "💖 Let the magic unfold...\n\n"
        f"✅ Verified: {verified}\n\n"
        "💞 /next - Seek another destiny\n"
        "🔮 /stop - End this magical moment"
    )

async def _send_details_async(viewer_id: int, partner_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Post rich details AFTER the quick intro without blocking the first message."""
    try:
        p = reg.get_profile(partner_id) or {}
        gender = (p.get("gender") or "—").capitalize()
        age = p.get("age") or "—"
        verified = "Yes" if p.get("is_verified") else "No"
        up, down = _rating_counts_for(partner_id)
        shared = _shared_interests_text(viewer_id, partner_id)
        txt = (
            f"ℹ️ Details:\n"
            f"Info: {gender}, {age}\n"
            f"Ratings: {up}👍  {down}👎\n"
            f"Verified: {verified}\n"
            f"Shared interests: {shared}"
        )
        await context.bot.send_message(chat_id=viewer_id, text=txt)
    except Exception:
        pass

# ------------------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------------------

async def _remove_from_queue(uid: int):
    try:
        queue.remove(uid)
    except ValueError:
        pass

async def _end_pair(uid: int, context: ContextTypes.DEFAULT_TYPE, notify_partner=True):
    async with queue_lock:
        await _remove_from_queue(uid)
        partner = peers.pop(uid, None)
        if partner is not None:
            peers.pop(partner, None)
            # Remember last partner for post-chat reports
            _remember_last_partner(uid, partner, bool(secret_sessions.get(uid)))
    if partner and notify_partner:
        try:
            await context.bot.send_message(partner, "⚠️ Your partner left.")
        except Exception:
            pass
    return partner

# ------------------------------------------------------------------------------
# Search / Matching
# ------------------------------------------------------------------------------

MODE_RANDOM = "random"
MODE_GIRLS  = "girls"
MODE_BOYS   = "boys"
_last_mode: dict[int, str] = {}

# --- NEW HELPERS: mutual preference checks ---
def _user_mode(uid: int) -> str:
    return _last_mode.get(uid, MODE_RANDOM)

def _gender_of(uid: int) -> str:
    try:
        p = reg.get_profile(uid) or {}
        g = (p.get("gender") or "").strip().lower()
        return g[:1] if g else ""
    except Exception:
        return ""

def _candidate_verified(uid: int) -> bool:
    try:
        p = reg.get_profile(uid) or {}
        return bool(p.get("is_verified"))
    except Exception:
        return False

def _viewer_wants_verified_only(uid: int) -> bool:
    try:
        return reg.get_match_verified_only(uid)
    except Exception:
        return False

def _age_pref(uid: int) -> tuple[int, int]:
    try:
        return reg.get_age_pref(uid)
    except Exception:
        return (18, 99)

def _allows(viewer_id: int, cand_id: int) -> bool:
    """
    Does *viewer* accept *candidate* based on viewer's mode and (if premium) age window?
    """
    # sticky re-match bypass — if both want each other, bypass filters
    if REMATCH_TARGET.get(viewer_id) == cand_id and REMATCH_TARGET.get(cand_id) == viewer_id:
        return True

    mode = _user_mode(viewer_id)

    # gender filter from viewer mode (STRICT)
    if mode in (MODE_GIRLS, MODE_BOYS):
        need = "f" if mode == MODE_GIRLS else "m"
        g = (reg.get_profile(cand_id) or {}).get("gender", "")
        gkey = (g or "").strip().lower()[:1]
        if gkey != need:
            return False

    # premium viewer age window
    try:
        if reg.has_active_premium(viewer_id):
            lo, hi = _age_pref(viewer_id)
            if (lo, hi) != (18, 99):
                cp = reg.get_profile(cand_id) or {}
                a = cp.get("age")
                if a is None or not (int(lo) <= int(a) <= int(hi)):
                    return False
    except Exception:
        # fail open if profile lookup fails
        pass

    # Viewer wants only verified?
    if _viewer_wants_verified_only(viewer_id) and not _candidate_verified(cand_id):
        return False

    return True

def _mutual_ok(a: int, b: int) -> bool:
    """Both sides accept each other."""
    return _allows(a, b) and _allows(b, a)

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str | None = None):
    uid = update.effective_user.id

    if in_chat(uid):
        await context.bot.send_message(chat_id=uid, text="You're in a chat. Use /next or /stop first.")
        return

    # Resolve mode
    if mode in (MODE_RANDOM, MODE_GIRLS, MODE_BOYS):
        _last_mode[uid] = mode
    mode = _last_mode.get(uid, MODE_RANDOM)

    is_premium = reg.has_active_premium(uid)

    # Viewer age window 
    min_age, max_age = reg.get_age_pref(uid)
    has_custom_age = (min_age, max_age) != (18, 99)

    def _ok(cand_id: int) -> bool:
        """Whether candidate satisfies viewer filters."""
        if mode == MODE_RANDOM:
            return True
        try:
            cp = reg.get_profile(cand_id) or {}
            g = (cp.get("gender") or "").strip().lower()
            gkey = g[0] if g else ""
            need = "f" if mode == MODE_GIRLS else "m"
            if gkey != need:
                return False
            if is_premium and has_custom_age:
                a = cp.get("age")
                if a is None or not (min_age <= int(a) <= max_age):
                    return False
        except Exception:
            return False
        return True

    async with queue_lock:
        # Priority to sticky re-match target
        target = REMATCH_TARGET.get(uid)
        if target:
            if target in queue and not in_chat(target):
                # Directly match with the sticky target
                queue.remove(target)
                candidate_id = target
                # Remove sticky mapping
                REMATCH_TARGET.pop(uid, None)
                REMATCH_TARGET.pop(target, None)

                # Proceed with pairing logic
                partner = candidate_id
                peers[uid] = partner
                peers[partner] = uid
                _last_menu_at.pop(uid, None)
                _last_menu_at.pop(partner, None)

                ice = random.choice([
                    "Two truths and a lie?",
                    "Go-to comfort food?",
                    "Teleport once today — where?",
                    "What tiny thing made you smile this week?"
                ])

                t0 = time.time()
                if FAST_INTRO:
                    quick_u = _intro_text_quick(uid, partner, ice)
                    quick_p = _intro_text_quick(partner, uid, ice)
                    await context.bot.send_message(chat_id=uid, text=quick_u, reply_markup=ReplyKeyboardRemove())
                    await context.bot.send_message(chat_id=partner, text=quick_p, reply_markup=ReplyKeyboardRemove())
                    if reg.has_active_premium(uid): asyncio.create_task(_send_details_async(uid, partner, context))
                    if reg.has_active_premium(partner): asyncio.create_task(_send_details_async(partner, uid, context))
                else:
                    txt_u1 = _intro_text_for(uid, partner, ice)
                    txt_u2 = _intro_text_for(partner, uid, ice)
                    for who, text in ((uid, txt_u1), (partner, txt_u2)):
                        await context.bot.send_message(chat_id=who, text=text, reply_markup=ReplyKeyboardRemove())
                log.info(f"Intro sent in {time.time() - t0:.3f}s")
                log.info(f"Matched {uid} <-> {partner} (sticky re-match)")

                async def _bump_dialogs_async(a: int, b: int):
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, increment_dialogs, a)
                    await loop.run_in_executor(None, increment_dialogs, b)
                asyncio.create_task(_bump_dialogs_async(uid, partner))
                return # Early return after sticky match


        # If no sticky target or target not in queue, proceed with normal queue scan
        if uid in queue:
            await send_safe(context.bot, chat_id=uid, text="🔎 Still searching…")
            return

        partner = None
        qn = len(queue)
        for _ in range(qn):
            cand = queue.popleft()
            if cand == uid or cand in peers:
                continue
            if _mutual_ok(uid, cand):
                partner = cand
                break
            queue.append(cand)

        if partner is None:
            queue.append(uid)
            if mode == MODE_GIRLS:
                msg = "🔎 Finding a girl partner soon...\nIf the search takes too long, try changing your settings (/settings)."
            elif mode == MODE_BOYS:
                msg = "🔎 Finding a boy partner soon...\nIf the search takes too long, try changing your settings (/settings)."
            else:
                msg = "💫🔮 Seeking your mysterious soulmate... 🔮💫"
            await send_safe(context.bot, chat_id=uid, text=msg)
            log.info(f"{uid} queued (mode={mode}, age={min_age}-{max_age})")
            return

        peers[uid] = partner
        peers[partner] = uid

        # reset menu guard for both sides for this new chat
        _last_menu_at.pop(uid, None)
        _last_menu_at.pop(partner, None)

    # Announce match to both; hide bottom menu while chatting
    ice = random.choice([
        "🌅 If you could wake up anywhere tomorrow, where would your heart choose?",
        "✨ What's one small moment today that made your soul sparkle?",
        "🌙 Share a truth, a dream, and a beautiful lie about yourself...",
        "💫 What's your secret comfort that makes everything feel magical?",
        "🌹 If we met in a different universe, what do you think we'd be doing?",
        "💭 What's a feeling you've never quite found the words for?",
        "🎭 If you could whisper one secret to the stars, what would it be?",
        "🌸 What's something that makes you feel alive and completely yourself?"
    ])

    t0 = time.time()

    if FAST_INTRO:
        # Send per-viewer quick intro (includes Verified for everyone)
        quick_u = _intro_text_quick(uid, partner, ice)
        quick_p = _intro_text_quick(partner, uid, ice)
        await context.bot.send_message(chat_id=uid,     text=quick_u, reply_markup=ReplyKeyboardRemove())
        await context.bot.send_message(chat_id=partner, text=quick_p, reply_markup=ReplyKeyboardRemove())

        # Enrich premium users later (gender/age/ratings/shared) without blocking
        if reg.has_active_premium(uid):
            asyncio.create_task(_send_details_async(uid, partner, context))
        if reg.has_active_premium(partner):
            asyncio.create_task(_send_details_async(partner, uid, context))
    else:
        # Rich intro path (with DB)
        txt_u1 = _intro_text_for(uid, partner, ice)
        txt_u2 = _intro_text_for(partner, uid, ice)
        for who, text in ((uid, txt_u1), (partner, txt_u2)):
            await context.bot.send_message(
                chat_id=who,
                text=text,
                reply_markup=ReplyKeyboardRemove(),  # hide bottom menu during chat
            )

    log.info(f"Intro sent in {time.time() - t0:.3f}s")
    log.info(f"Matched {uid} <-> {partner} (mode={mode})")

    # Bump dialog counters AFTER sending (non-blocking)
    async def _bump_dialogs_async(a: int, b: int):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, increment_dialogs, a)
        await loop.run_in_executor(None, increment_dialogs, b)
    asyncio.create_task(_bump_dialogs_async(uid, partner))

# ------------------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------------------

async def cmd_find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if reg.is_banned(update.effective_user.id):
        until, reason, _ = reg.get_ban_info(update.effective_user.id)
        pretty = "lifetime" if until.year >= 9999 else until.strftime("%Y-%m-%d %H:%M UTC")
        await update.message.reply_text(f"🚫 You are banned till {pretty}.\nReason: {reason or '—'}")
        return
    await start_search(update, context, mode=MODE_RANDOM)

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if reg.is_banned(update.effective_user.id):
        until, reason, _ = reg.get_ban_info(update.effective_user.id)
        pretty = "lifetime" if until.year >= 9999 else until.strftime("%Y-%m-%d %H:%M UTC")
        await update.message.reply_text(f"🚫 You are banned till {pretty}.\nReason: {reason or '—'}")
        return
    await start_search(update, context, mode=MODE_RANDOM)

async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if reg.is_banned(update.effective_user.id):
        until, reason, _ = reg.get_ban_info(update.effective_user.id)
        pretty = "lifetime" if until.year >= 9999 else until.strftime("%Y-%m-%d %H:%M UTC")
        await update.message.reply_text(f"🚫 You are banned till {pretty}.\nReason: {reason or '—'}")
        return
    uid = update.effective_user.id
    await _end_pair(uid, context, notify_partner=True)
    await start_search(update, context)  # reuse last mode
    log.info(f"{uid} ran /next")

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if reg.is_banned(update.effective_user.id):
        until, reason, _ = reg.get_ban_info(update.effective_user.id)
        pretty = "lifetime" if until.year >= 9999 else until.strftime("%Y-%m-%d %H:%M UTC")
        await update.message.reply_text(f"🚫 You are banned till {pretty}.\nReason: {reason or '—'}")
        return
    uid = update.effective_user.id
    partner = await _end_pair(uid, context, notify_partner=False)
    await update.message.reply_text("✋ You left the chat")

    if partner:
        await update.message.reply_text(
            "⭐ Rate your partner so I can find better matches for you.",
            reply_markup=rating_kb(partner)
        )
        # user's menu (guarded)
        await _send_menu_once(context, update.effective_chat.id)

        try:
            await context.bot.send_message(
                chat_id=partner,
                text="✋ Chat ended by your partner.\n\n⭐ Rate your partner so I can find better matches for you.",
                reply_markup=rating_kb(uid)
            )
            # partner's menu (guarded) – this is the one that was
            # duplicating later after they rate
            await _send_menu_once(context, partner)
        except Exception:
            pass
    else:
        # not in a chat – still show menu, but guarded
        await _send_menu_once(context, update.effective_chat.id)

    log.info(f"{uid} ran /stop")

async def cmd_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End friend chat specifically"""
    if reg.is_banned(update.effective_user.id):
        until, reason, _ = reg.get_ban_info(update.effective_user.id)
        pretty = "lifetime" if until.year >= 9999 else until.strftime("%Y-%m-%d %H:%M UTC")
        await update.message.reply_text(f"🚫 You are banned till {pretty}.\nReason: {reason or '—'}")
        return
    
    uid = update.effective_user.id
    partner = partner_of(uid)
    
    if not partner:
        return await update.message.reply_text("ℹ️ You're not in a chat.")
    
    # Check if this is a friend chat
    chat_id = reg.get_active_friend_chat(uid, partner)
    if chat_id:
        # Close friend chat
        reg.close_friend_chat(chat_id)
        
        # Remove from chat infrastructure
        await _end_pair(uid, context, notify_partner=False)
        
        await update.message.reply_text("✋ Friend chat ended.")
        
        try:
            await context.bot.send_message(
                partner,
                "✋ Friend chat ended by your friend."
            )
            await _send_menu_once(context, partner)
        except Exception:
            pass
        
        await _send_menu_once(context, update.effective_chat.id)
    else:
        # Regular random chat - use normal /stop flow
        await cmd_stop(update, context)

# /secret — start chooser (ONLY inviter must be Premium)
async def cmd_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if reg.is_banned(update.effective_user.id):
        until, reason, _ = reg.get_ban_info(update.effective_user.id)
        pretty = "lifetime" if until.year >= 9999 else until.strftime("%Y-%m-%d %H:%M UTC")
        await update.message.reply_text(f"🚫 You are banned till {pretty}.\nReason: {reason or '—'}")
        return
    uid = update.effective_user.id
    partner = partner_of(uid)
    if not partner:
        return await update.message.reply_text("ℹ️ Start a normal chat first, then use /secret.")

    # only inviter must be premium
    if not reg.has_active_premium(uid):
        return await update.message.reply_text("⭐ Secret Chat invite requires Premium on your account.")

    # reset choices
    pending_secret_invites[uid] = {"ttl": None, "dur": None}

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("⏱ Timer", callback_data="secret:pick_timer"),
        InlineKeyboardButton("💣 Self-destruct", callback_data="secret:pick_ttl")
    ],[
        InlineKeyboardButton("✅ Send invite", callback_data="secret:send")
    ]])
    await update.message.reply_text(
        "🔐 Secret Chat — choose options first:\n• Timer (15/30/45/60 min)\n• Self-destruct (5/10/15/20 sec)",
        reply_markup=kb
    )

# /endsecret — manual end
async def cmd_endsecret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if reg.is_banned(update.effective_user.id):
        until, reason, _ = reg.get_ban_info(update.effective_user.id)
        pretty = "lifetime" if until.year >= 9999 else until.strftime("%Y-%m-%d %H:%M UTC")
        await update.message.reply_text(f"🚫 You are banned till {pretty}.\nReason: {reason or '—'}")
        return
    uid = update.effective_user.id
    s = secret_sessions.pop(uid, None)
    partner = s["partner"] if s else None
    if partner:
        secret_sessions.pop(partner, None)
        try: 
            await context.bot.send_message(partner, "⏳ Secret Chat ended by your partner.")
        except Exception:
            log.exception("Failed to notify partner of secret chat end")
    await update.message.reply_text("⏳ Secret Chat ended. Back to normal chat.")

async def cmd_boost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not reg.has_active_premium(uid):
        return await update.message.reply_text("⭐ /boost is a Premium feature.")
    if in_chat(uid):
        return await update.message.reply_text("ℹ️ You are already in a chat.")
    import time
    now = time.time()
    if now - _last_boost_at.get(uid, 0) < 300:  # 5 min cooldown
        return await update.message.reply_text("⏳ Please wait a few minutes before boosting again.")

    # put at front of queue
    async with queue_lock:
        try:
            queue.remove(uid)
        except ValueError:
            pass
        queue.appendleft(uid)
    _last_boost_at[uid] = now
    await update.message.reply_text("🚀 Boost activated! You have been moved to the front of the queue.")

async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    claimed, balance, left = reg.give_daily(uid, reward=10)
    if claimed:
        return await update.message.reply_text(f"✅ Daily reward claimed: +10 coins.\n💰 Balance: {balance}")
    h = left // 3600; m = (left % 3600) // 60; s = left % 60
    await update.message.reply_text(f"⏳ Next claim in {h:02d}h:{m:02d}m:{s:02d}s.\n💰 Balance: {balance}")

async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    bal = reg.get_coins(uid)
    await update.message.reply_text(f"💰 Your coin balance: {bal}")

async def cmd_crushleaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the weekly secret crush leaderboard."""
    uid = update.effective_user.id
    
    leaderboard = reg.get_crush_leaderboard(limit=3)
    
    if not leaderboard:
        await update.message.reply_text("💘 No one on the crush leaderboard this week yet!\nBe someone's secret crush to appear here.")
        return
    
    lines = ["💘 <b>Secret Crush Leaderboard</b> (This Week)", ""]
    
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, count) in enumerate(leaderboard):
        try:
            user_name = safe_display_name(user_id)
            medal = medals[i] if i < len(medals) else f"{i+1}."
            plural = "crush" if count == 1 else "crushes"
            lines.append(f"{medal} {user_name} — {count} secret {plural}")
        except Exception:
            continue
    
    lines.extend(["", "🔄 Leaderboard resets every Monday!"])
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_horoscope(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show daily horoscope based on user's date of birth."""
    uid = update.effective_user.id
    
    # Get user's date of birth
    dob = reg.get_date_of_birth(uid)
    
    if not dob:
        await update.message.reply_text(
            "🔮 <b>Daily Horoscope</b>\n\n"
            "Set your birthday first to get personalized horoscope!\n\n"
            "Use: <code>/setbirthday YYYY-MM-DD</code>\n"
            "Example: <code>/setbirthday 1995-06-15</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        from datetime import datetime
        birth_date = datetime.strptime(dob, '%Y-%m-%d')
        zodiac_sign = reg.get_zodiac_sign(birth_date.month, birth_date.day)
        horoscope = reg.get_daily_horoscope(zodiac_sign)
        
        today = datetime.now().strftime('%B %d, %Y')
        
        await update.message.reply_text(
            f"🔮 <b>Daily Horoscope</b>\n"
            f"📅 {today}\n\n"
            f"{zodiac_sign}\n\n"
            f"{horoscope}",
            parse_mode="HTML"
        )
    except Exception:
        await update.message.reply_text("❌ Error reading your horoscope. Please try again.")

async def cmd_setbirthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user's date of birth for horoscope feature."""
    uid = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "🎂 <b>Set Your Birthday</b>\n\n"
            "Usage: <code>/setbirthday YYYY-MM-DD</code>\n"
            "Example: <code>/setbirthday 1995-06-15</code>\n\n"
            "This enables personalized daily horoscopes!",
            parse_mode="HTML"
        )
        return
    
    birthday = context.args[0]
    
    if reg.set_date_of_birth(uid, birthday):
        try:
            from datetime import datetime
            birth_date = datetime.strptime(birthday, '%Y-%m-%d')
            zodiac_sign = reg.get_zodiac_sign(birth_date.month, birth_date.day)
            
            await update.message.reply_text(
                f"✅ <b>Birthday Set!</b>\n\n"
                f"🎂 Your birthday: {birth_date.strftime('%B %d, %Y')}\n"
                f"⭐ Your zodiac sign: {zodiac_sign}\n\n"
                f"Use /horoscope to get your daily horoscope!",
                parse_mode="HTML"
            )
        except Exception:
            await update.message.reply_text("✅ Birthday set successfully! Use /horoscope for your daily reading.")
    else:
        await update.message.reply_text(
            "❌ Invalid date format!\n\n"
            "Please use: <code>/setbirthday YYYY-MM-DD</code>\n"
            "Example: <code>/setbirthday 1995-06-15</code>",
            parse_mode="HTML"
        )

async def cmd_funfact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show daily fun fact."""
    fun_fact = reg.get_daily_fun_fact()
    
    from datetime import datetime
    today = datetime.now().strftime('%B %d, %Y')
    
    await update.message.reply_text(
        f"🎭 <b>Daily Fun Fact</b>\n"
        f"📅 {today}\n\n"
        f"{fun_fact}\n\n"
        f"💡 Come back tomorrow for a new fact!",
        parse_mode="HTML"
    )

async def cmd_badges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's badges and available badges."""
    uid = update.effective_user.id
    
    # Check and award badges first
    reg.check_and_award_badges(uid)
    
    user_badges = reg.get_user_badges(uid)
    available_badges = reg.get_available_badges()
    
    lines = ["🏆 <b>Your Badges</b>\n"]
    
    if user_badges:
        lines.append("<b>Earned Badges:</b>")
        for badge in user_badges:
            lines.append(f"{badge['emoji']} <b>{badge['name']}</b> — {badge['description']}")
        lines.append("")
    
    lines.append("<b>Available Badges:</b>")
    earned_badge_ids = {badge['badge_id'] for badge in user_badges}
    
    for badge_id, badge_info in available_badges.items():
        if badge_id not in earned_badge_ids:
            lines.append(f"{badge_info['emoji']} <b>{badge_info['name']}</b> — {badge_info['description']}")
            lines.append(f"   <i>How to earn: {badge_info['criteria']}</i>")
    
    if len(earned_badge_ids) == len(available_badges):
        lines.append("🎉 You've earned all available badges!")
    
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_shadowban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to shadow ban a user."""
    uid = update.effective_user.id
    
    # Check if user is admin (you may need to adjust this check)
    if uid not in [1437934486, 647778438]:  # Replace with your admin IDs
        await update.message.reply_text("❌ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "🔨 <b>Shadow Ban</b>\n\n"
            "Usage: <code>/shadowban [user_id]</code>\n"
            "Example: <code>/shadowban 123456789</code>\n\n"
            "Shadow banned users' posts will only be visible to themselves.",
            parse_mode="HTML"
        )
        return
    
    try:
        target_id = int(context.args[0])
        if reg.set_shadow_ban(target_id, True):
            await update.message.reply_text(f"✅ User {target_id} has been shadow banned.")
        else:
            await update.message.reply_text("❌ Failed to shadow ban user.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")

async def cmd_unshadowban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to remove shadow ban from a user."""
    uid = update.effective_user.id
    
    # Check if user is admin
    if uid not in [1437934486, 647778438]:  # Replace with your admin IDs
        await update.message.reply_text("❌ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "🔓 <b>Remove Shadow Ban</b>\n\n"
            "Usage: <code>/unshadowban [user_id]</code>\n"
            "Example: <code>/unshadowban 123456789</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        target_id = int(context.args[0])
        if reg.set_shadow_ban(target_id, False):
            await update.message.reply_text(f"✅ Shadow ban removed from user {target_id}.")
        else:
            await update.message.reply_text("❌ Failed to remove shadow ban.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")

async def cmd_addfriend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    partner = partner_of(uid)
    if not partner:
        return await update.message.reply_text("ℹ️ You can only add friend while chatting.")

    # already friends?
    if reg.is_friends(uid, partner):
        return await update.message.reply_text("✅ Already in your friend list.")

    # अगर सामने वाले ने पहले से तुम्हें request भेज रखी है → auto accept
    if reg.has_incoming_request(uid, partner):
        reg.delete_friend_request(partner, uid)
        reg.add_friend(uid, partner)
        asyncio.create_task(send_and_delete(context.bot, uid, "✅ Request accepted. Added to your friend list.", delay=10))
        try:
            name = safe_display_name(uid)
            asyncio.create_task(send_and_delete(context.bot, partner, f"✅ {name} accepted your friend request.", delay=10))
        except Exception:
            pass
        return

    # अगर तुम already request भेज चुके हो
    if reg.has_sent_request(uid, partner):
        return await update.message.reply_text("⏳ Friend request already sent. Waiting for approval.")

    # नयी request create
    if not reg.create_friend_request(uid, partner):
        return await update.message.reply_text("⚠️ Couldn't send request. Try again later.")

    # partner को approve/decline buttons भेजो
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"fr:acc:{uid}"),
         InlineKeyboardButton("❌ Decline", callback_data=f"fr:dec:{uid}")]
    ])
    try:
        # Get display name (prioritizes feed_username, then username, then first_name, fallback to "A user")
        requester_name = safe_display_name(uid)
        if requester_name == "User":  # If no proper name found, use generic message
            requester_name = "A user"
        
        await context.bot.send_message(
            chat_id=partner,
            text=f"👥 {requester_name} wants to add you to their friend list.\nApprove?",
            reply_markup=kb
        )
    except Exception:
        pass

    await send_and_delete(context.bot, uid, "✅ Friend request sent!", delay=10)

async def cmd_friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    friends = reg.list_friends(uid, 20)
    if not friends:
        return await update.message.reply_text("👥 Your friend list is empty. Use /addfriend during a chat.")
    
    # Create friends text with levels
    friends_text = "👥 <b>Your Friends</b>\n\n"
    for friend_id in friends[:10]:
        name = safe_display_name(friend_id)
        level, count, emoji = reg.get_friendship_level(uid, friend_id)
        level_name = reg.get_level_name(level)
        friends_text += f"{emoji} {name} — {level_name} ({count} interactions)\n"
    
    friends_text += "\n🌱→🌿→🌳 Level up by chatting more!"
    
    rows = [[InlineKeyboardButton(f"Invite {safe_display_name(f)}", callback_data=f"rm:ask:{f}") ] for f in friends[:10]]
    await update.message.reply_text(friends_text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML")

async def cmd_love(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show gift selection menu during chat."""
    uid = update.effective_user.id
    partner = partner_of(uid)
    if not partner:
        return await update.message.reply_text("ℹ️ Use this during a chat.")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌹 Flowers (10)", callback_data=f"gift:flowers:10:{partner}")],
        [InlineKeyboardButton("🍰 Dessert (20)", callback_data=f"gift:dessert:20:{partner}")],
        [InlineKeyboardButton("🧸 Teddy (30)", callback_data=f"gift:teddy:30:{partner}")]
    ])
    await update.message.reply_text("🎁 Choose a gift:", reply_markup=kb)

async def on_gift_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gift selection and coin transfer."""
    q = update.callback_query
    await q.answer()
    try:
        m = cb_match(q.data or "", r"^gift:(?P<kind>flowers|dessert|teddy):(?P<amount>\d+):(?P<partner>\d+)$")
        kind = m["kind"]
        amount = int(m["amount"])
        partner = int(m["partner"])
        uid = q.from_user.id
    except (CBError, ValueError):
        log.warning(f"Invalid gift callback: {q.data}")
        return

    ok, bal_s, bal_r = reg.transfer_coins(uid, partner, amount)
    if not ok:
        return await q.edit_message_text(f"❌ Not enough coins. Balance: {bal_s}")

    label = {"flowers":"🌹 Flowers", "dessert":"🍰 Dessert", "teddy":"🧸 Teddy"}.get(kind, "🎁 Gift")
    try:
        await q.edit_message_text(f"✅ Sent {label} ({amount} coins). Your balance: {bal_s}")
    except Exception:
        pass
    try:
        await context.bot.send_message(partner, f"{label} received from {uid}! Your balance: {bal_r}")
    except Exception:
        pass

    try:
        await context.bot.send_message(partner, f"{label} Gift received from {uid}! Your balance: {bal_r}")
    except Exception:
        pass

async def cmd_tip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    partner = partner_of(uid)
    if not partner:
        return await update.message.reply_text("ℹ️ You can tip only during a chat.")
    if not context.args:
        return await update.message.reply_text("Usage: /tip <amount> (e.g., /tip 10)")
    try:
        amount = int(context.args[0])
    except:
        return await update.message.reply_text("Amount must be a whole number.")
    if amount <= 0:
        return await update.message.reply_text("Amount must be positive.")

    # confirm buttons
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ Tip {amount} coins", callback_data=f"tip:ok:{amount}:{partner}"),
        InlineKeyboardButton("❌ Cancel", callback_data="tip:cancel")
    ]])
    await update.message.reply_text(
        f"💸 Tip {amount} coins to {partner}?", reply_markup=kb
    )

async def cmd_love(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    partner = partner_of(uid)
    if not partner:
        return await update.message.reply_text("ℹ️ Use this during a chat.")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌹 Send Flowers (10 coins)", callback_data=f"gift:flowers:10:{partner}")],
        [InlineKeyboardButton("🍰 Send Dessert (20 coins)", callback_data=f"gift:dessert:20:{partner}")],
        [InlineKeyboardButton("🧸 Send Teddy (30 coins)",   callback_data=f"gift:teddy:30:{partner}")]
    ])
    await update.message.reply_text("🎁 Send a small gift:", reply_markup=kb)

async def start_search_for_uid(uid: int, context: ContextTypes.DEFAULT_TYPE):
    """Auto-trigger search for a specific user ID (for re-match)."""
    if in_chat(uid):
        return  # already in chat

    # Try instant pairing first (for sticky re-match)
    await _try_pair_instant(uid, context)

    # If not paired instantly, normal queue flow
    if not in_chat(uid):
        async with queue_lock:
            if uid not in queue:
                queue.append(uid)
        try:
            await context.bot.send_message(chat_id=uid, text="💫🔮 Seeking your mysterious soulmate... 🔮💫")
        except Exception:
            pass

async def _try_pair_instant(uid: int, context: ContextTypes.DEFAULT_TYPE):
    """Try to instantly pair with sticky re-match target."""
    target = REMATCH_TARGET.get(uid)
    if not target:
        return

    async with queue_lock:
        if target in queue and not in_chat(target) and not in_chat(uid):
            # Remove both from queue
            try:
                queue.remove(uid)
            except Exception:
                pass
            try:
                queue.remove(target)
            except Exception:
                pass

            # Create the pair
            peers[uid] = target
            peers[target] = uid

            # Clear sticky intent
            REMATCH_TARGET.pop(uid, None)
            REMATCH_TARGET.pop(target, None)

            # Reset menu guard for both sides
            _last_menu_at.pop(uid, None)
            _last_menu_at.pop(target, None)

            # Send intro messages
            ice = random.choice([
                "Two truths and a lie?",
                "Go-to comfort food?",
                "Teleport once today — where?",
                "What tiny thing made you smile this week?"
            ])

            t0 = time.time()

            if FAST_INTRO:
                quick_u = _intro_text_quick(uid, target, ice)
                quick_p = _intro_text_quick(target, uid, ice)
                await context.bot.send_message(chat_id=uid, text=quick_u, reply_markup=ReplyKeyboardRemove())
                await context.bot.send_message(chat_id=target, text=quick_p, reply_markup=ReplyKeyboardRemove())
                if reg.has_active_premium(uid):
                    asyncio.create_task(_send_details_async(uid, target, context))
                if reg.has_active_premium(target):
                    asyncio.create_task(_send_details_async(target, uid, context))
            else:
                txt_u1 = _intro_text_for(uid, target, ice)
                txt_u2 = _intro_text_for(target, uid, ice)
                await context.bot.send_message(chat_id=uid, text=txt_u1, reply_markup=ReplyKeyboardRemove())
                await context.bot.send_message(chat_id=target, text=txt_u2, reply_markup=ReplyKeyboardRemove())

            log.info(f"Intro sent in {time.time() - t0:.3f}s")
            log.info(f"Matched {uid} <-> {target} (auto re-match)")

            # Bump dialog counters
            async def _bump_dialogs_async(a: int, b: int):
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, increment_dialogs, a)
                await loop.run_in_executor(None, increment_dialogs, b)
            asyncio.create_task(_bump_dialogs_async(uid, target))

async def on_rm_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    try:
        m = cb_match(q.data or "", r"^rm:ask:(?P<target>\d+)$")
        target = int(m["target"])
    except (CBError, ValueError):
        log.warning(f"Invalid rm:ask callback: {q.data}")
        return await q.answer("Invalid.", show_alert=True)
    await q.answer("Invite sent.")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept", callback_data=f"rm:acc:{uid}"),
         InlineKeyboardButton("❌ Decline", callback_data=f"rm:dec:{uid}")]
    ])
    try:
        await context.bot.send_message(chat_id=target, text=f"🔄 {safe_display_name(uid)} invites you to re-match. Accept?", reply_markup=kb)
    except Exception:
        pass

async def on_rm_decide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    me = q.from_user.id
    try:
        m = cb_match(q.data or "", r"^rm:(?P<action>acc|dec):(?P<other>\d+)$")
        action = m["action"]
        other = int(m["other"])
    except (CBError, ValueError):
        log.warning(f"Invalid rm:decide callback: {q.data}")
        return
    await q.answer()
    if action == "dec":
        try:
            await q.edit_message_text(f"❌ Request from {safe_display_name(other)} was declined.")
        except Exception:
            pass
        try:
            await context.bot.send_message(other, f"❌ {safe_display_name(me)} declined your re-match request.")
        except Exception:
            pass
        return

    # accept → set sticky intent + auto-search
    try:
        await q.edit_message_text("✅ Re-match accepted. Connecting…")
    except Exception:
        pass

    # 1) Set sticky re-match intent
    REMATCH_TARGET[me] = other
    REMATCH_TARGET[other] = me

    # 2) Put both at front of queue
    async with queue_lock:
        try:
            queue.remove(me)
        except Exception:
            pass
        try:
            queue.remove(other)
        except Exception:
            pass
        queue.appendleft(me)
        queue.appendleft(other)

    # 3) Auto-trigger search for both users
    try:
        await start_search_for_uid(me, context)
        await start_search_for_uid(other, context)
        
        # Check if match was successful and delete message accordingly
        async def check_and_delete():
            await asyncio.sleep(2)
            match_successful = me in peers and peers.get(me) == other
            
            if match_successful:
                # Match successful - delete immediately
                try:
                    await q.message.delete()
                except:
                    pass
            else:
                # Match not successful - delete after 2 more seconds
                await asyncio.sleep(2)
                try:
                    await q.message.delete()
                except:
                    pass
        
        asyncio.create_task(check_and_delete())
    except Exception:
        pass

async def on_friend_decide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    try:
        from utils.cb import cb_match
        m = cb_match(data, r"^fr:(?P<action>acc|dec):(?P<requester>\d+)$")
        action = m["action"]
        requester = int(m["requester"])
    except Exception:
        return

    target = q.from_user.id  # jisne approve/decline दबाया

    # request still exists?
    if not reg.has_sent_request(requester, target):
        try:
            await q.edit_message_text(f"❌ Request from {safe_display_name(requester)} was already processed/expired.")
        except Exception:
            pass
        return

    if action == "dec":
        reg.delete_friend_request(requester, target)
        try:
            await q.edit_message_text("❌ Declined.")
        except Exception:
            pass
        try:
            await context.bot.send_message(requester, f"❌ {safe_display_name(target)} declined your friend request.")
        except Exception:
            pass
        return

    # approve
    reg.delete_friend_request(requester, target)
    reg.add_friend(requester, target)
    try:
        await q.edit_message_text("✅ Approved. Added to friends.")
    except Exception:
        pass
    try:
        name = safe_display_name(target)
        await send_and_delete(context.bot, requester, f"✅ {name} accepted your friend request.", delay=5)
    except Exception:
        pass

async def on_tip_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data == "tip:cancel":
        try:
            await q.edit_message_text("❌ Tip cancelled.")
        except Exception:
            pass
        return
    # tip:ok:amount:partner
    try:
        m = cb_match(data, r"^tip:ok:(?P<amount>\d+):(?P<partner>\d+)$")
        amount = int(m["amount"])
        partner = int(m["partner"])
        uid = q.from_user.id
    except (CBError, ValueError):
        log.warning(f"Invalid tip callback: {data}")
        return
    ok, bal_sender, bal_recv = reg.transfer_coins(uid, partner, amount)
    if not ok:
        return await q.edit_message_text(f"❗ Insufficient balance. Your balance: {bal_sender}")
    try:
        await q.edit_message_text(f"✅ Tipped {amount} coins. New balance: {bal_sender}")
    except Exception:
        pass
    try:
        await context.bot.send_message(partner, f"🎁 You received {amount} coins from {safe_display_name(uid)}! New balance: {bal_recv}")
    except Exception:
        pass

async def on_love_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        m = cb_match(q.data or "", r"^love:(?P<kind>heart|flowers):(?P<amount>\d+):(?P<partner>\d+)$")
        kind = m["kind"]
        amount = int(m["amount"])
        partner = int(m["partner"])
        uid = q.from_user.id
    except (CBError, ValueError):
        log.warning(f"Invalid love callback: {q.data}")
        return
    ok, bal_sender, bal_rec = reg.transfer_coins(uid, partner, amount)
    if not ok:
        return await q.edit_message_text(f"❗ Not enough coins. Balance: {bal_sender}")
    label = "❤️" if kind == "heart" else "🌹"
    try:
        await q.edit_message_text(f"✅ Sent {label} for {amount} coins. Balance: {bal_sender}")
    except Exception:
        pass
    try:
        await context.bot.send_message(partner, f"{label} from {safe_display_name(uid)}! (+{amount} coins) New balance: {bal_rec}")
    except Exception:
        pass

# ------------------------------------------------------------------------------
# Callbacks: rating/report
# ------------------------------------------------------------------------------

async def on_rate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    try:
        m = cb_match(q.data or "", r"^(?P<action>rate):(?P<value>good|bad):(?P<target>\d+)$")
        action = m["action"]
        value_str = m["value"]
        target_id_str = m["target"]
    except (CBError, ValueError):
        log.warning(f"Invalid rate callback: {q.data}")
        return
    target_id = int(target_id_str)

    if action == "rate":
        value = 0
        if value_str == "good":
            value = 1
        elif value_str == "bad":
            value = -1

        if value != 0:
            save_rating(uid, target_id, value)
            await q.answer(f"Thanks for rating!")

            # Remove the original rating panel
            try:
                await q.message.delete()
            except Exception:
                try:
                    # Fallback: edit to plain text so buttons vanish
                    await q.message.edit_text("✅ Feedback received, thank you!")
                except Exception:
                    pass

            # Send ephemeral "Thanks" that auto-deletes
            m = await context.bot.send_message(chat_id=q.message.chat_id, text="Thank you for your feedback ✅")
            await asyncio.sleep(2)
            try:
                await m.delete()
            except Exception:
                pass

            # show menu only if not sent recently
            await _send_menu_once(context, q.message.chat_id)



async def on_pref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    try:
        m = cb_match(q.data or "", r"^pref:(?P<mode>\w+)")
        mode = m["mode"]
    except (CBError, ValueError):
        log.warning(f"Invalid pref callback: {q.data}")
        return
    await start_search(update, context, mode=mode)

# Callback router for choices + send
async def on_secret_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    data = q.data or ""

    # pick timer
    if data == "secret:pick_timer":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("15 min", callback_data="secret:set_dur:15"),
            InlineKeyboardButton("30 min", callback_data="secret:set_dur:30"),
            InlineKeyboardButton("45 min", callback_data="secret:set_dur:45"),
            InlineKeyboardButton("60 min", callback_data="secret:set_dur:60"),
        ]])
        await q.answer()
        return await q.edit_message_text("Choose Secret Chat timer:", reply_markup=kb)

    # set timer
    if data.startswith("secret:set_dur:"):
        from utils.cb import cb_match
        try:
            m = cb_match(data, r"^secret:set_dur:(?P<dur>\d+)$")
            dur = int(m["dur"])
        except:
            return
        pending_secret_invites.setdefault(uid, {})["dur"] = dur
        await q.answer("Timer selected.")
        return await q.edit_message_text(f"⏱ Timer = {dur} min\nNow pick Self-destruct:", reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("5s",  callback_data="secret:set_ttl:5"),
            InlineKeyboardButton("10s", callback_data="secret:set_ttl:10"),
            InlineKeyboardButton("15s", callback_data="secret:set_ttl:15"),
            InlineKeyboardButton("20s", callback_data="secret:set_ttl:20"),
        ],[
            InlineKeyboardButton("✅ Send invite", callback_data="secret:send")
        ]]))

    # pick TTL directly
    if data == "secret:pick_ttl":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("5s",  callback_data="secret:set_ttl:5"),
            InlineKeyboardButton("10s", callback_data="secret:set_ttl:10"),
            InlineKeyboardButton("15s", callback_data="secret:set_ttl:15"),
            InlineKeyboardButton("20s", callback_data="secret:set_ttl:20"),
        ]])
        await q.answer()
        return await q.edit_message_text("Choose Self-destruct:", reply_markup=kb)

    # set TTL
    if data.startswith("secret:set_ttl:"):
        from utils.cb import cb_match
        try:
            m = cb_match(data, r"^secret:set_ttl:(?P<ttl>\d+)$")
            ttl = int(m["ttl"])
        except:
            return
        pending_secret_invites.setdefault(uid, {})["ttl"] = ttl
        await q.answer("Self-destruct selected.")
        sel = pending_secret_invites[uid]
        return await q.edit_message_text(
            f"💣 Self-destruct = {ttl}s\n⏱ Timer = {sel.get('dur') or 'not set'} min\nSend invite?",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Send invite", callback_data="secret:send")]])
        )

    # SEND invite
    if data == "secret:send":
        partner = partner_of(uid)
        if not partner:
            await q.answer("No partner."); return
        if not reg.has_active_premium(uid):
            await q.answer("Premium required."); return

        sel = pending_secret_invites.get(uid, {})
        dur = sel.get("dur") or 60
        ttl = sel.get("ttl") or 30
        pending_secret_invites.pop(uid, None)

        await q.answer()
        await q.edit_message_text(f"🔐 Secret Chat invite sent.\nTimer: {dur} min | Self-destruct: {ttl}s")

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Accept",  callback_data=f"secret:accept:{uid}:{ttl}:{dur}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"secret:decline:{uid}")
        ]])
        try:
            await context.bot.send_message(
                chat_id=partner,
                text=(f"Your partner invited you to Secret Chat.\nTimer: {dur} min | Self-destruct: {ttl}s\nAccept?"),
                reply_markup=kb
            )
        except Exception:
            pass
        return

    # DECLINE
    if data.startswith("secret:decline:"):
        from utils.cb import cb_match
        try:
            m = cb_match(data, r"^secret:decline:(?P<inviter>\d+)$")
            inviter = int(m["inviter"])
        except:
            return
        decliner = q.from_user.id

        await q.answer("Declined.")

        # 1) Replace the invite card for the decliner
        try:
            await q.edit_message_text("❌ You declined Secret Chat.\n💬 Continuing normal chat.\n🛡️ To report a user type /report")
        except Exception:
            # fallback if edit not possible (e.g., message already edited)
            try:
                await context.bot.send_message(
                    decliner,
                    "❌ You declined Secret Chat.\n💬 Continuing normal chat.\n🛡️ To report a user type /report"
                )
            except Exception:
                pass

        # 2) Notify inviter as well
        try:
            await context.bot.send_message(
                inviter,
                "❌ Your partner declined Secret Chat.\n💬 Continuing normal chat.\n🛡️ To report a user type /report"
            )
        except Exception:
            pass

        return

    # ACCEPT
    if data.startswith("secret:accept:"):
        from utils.cb import cb_match
        try:
            m = cb_match(data, r"^secret:accept:(?P<inviter>\d+):(?P<ttl>\d+):(?P<dur>\d+)$")
            inviter = int(m["inviter"])
            ttl = int(m["ttl"]) 
            dur = int(m["dur"])
        except:
            return await q.answer("Invalid invite.")
        uid = q.from_user.id
        if partner_of(uid) != inviter:
            return await q.answer("Invite expired.")

        now = datetime.datetime.utcnow()
        expires = now + datetime.timedelta(minutes=dur)
        secret_sessions[uid] = {"partner": inviter, "expires_at": expires, "ttl": ttl, "inviter": inviter}
        secret_sessions[inviter] = {"partner": uid, "expires_at": expires, "ttl": ttl, "inviter": inviter}

        # SCHEDULE auto end notification at expiry
        try:
            asyncio.create_task(_auto_end_secret(uid, inviter, expires, context.application))
        except Exception:
            pass

        await q.answer("Accepted.")
        await q.edit_message_text("🔐 Secret Chat started. Messages will auto-delete.")
        rules = (
            "🔐 Secret Chat rules:\n"
            "⛔ Screenshots not allowed\n"
            "⛔ Forwarding disabled\n"
            "⭐ Photos/Videos only if sender has Premium\n"
            "💣 Messages auto-delete after a few seconds\n"
            "⚠️ WARNING: The bot cannot block screenshots. Do not share risky content.\n"
            "To end the chat type /stop\n"
            "To end the secret chat type /endsecret\n"
            "🛡️ To report a user type /report"
        )
        try: 
            await context.bot.send_message(inviter, "🔐 Secret Chat started. Messages will auto-delete.")
        except Exception:
            log.exception("Failed to notify inviter of secret chat start")
        try: 
            await context.bot.send_message(uid, rules)
        except Exception:
            log.exception("Failed to send rules to accepter")
        try: 
            await context.bot.send_message(inviter, rules)
        except Exception:
            log.exception("Failed to send rules to inviter")
        return

async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Relay messages between chat partners."""

    # 🛡️ HARD STOP: if /report flow is active, never relay
    r = context.user_data.get("report") or {}
    if r.get("awaiting"):
        return  # on_report_input will handle + ApplicationHandlerStop later

    # ✅ TEXT-FRAMEWORK GUARD: if any feature owns text, relay must NOT run
    af = context.user_data.get(FEATURE_KEY)
    if af:   # e.g., "fantasy", "vault", "confession", "profile", etc.
        return

    uid = update.effective_user.id

    # Don't intercept comment text, poll text, or Q&A text - let their handlers process it
    state = (context.user_data.get("state") or "")
    if isinstance(state, str) and (
        state.startswith("comment:") or
        state.startswith("qa:") or
        state.startswith("poll:")
    ):
        return

    # Respect dedicated poll_state so relay doesn't eat poll creation text
    pstate = str(context.user_data.get("poll_state") or "")
    if pstate.startswith("poll:"):
        return

    # Registration check - let registration handlers process text first
    if not reg.is_registered(uid):
        return

    # Ban gate - silent drop for banned users
    if reg.is_banned(uid):
        try:
            await update.message.reply_text("🚫 You are banned. Chat disabled.")
        except Exception:
            log.exception("Failed to send ban message to user")
        return

    partner = partner_of(uid)
    if not partner:
        return

    try:
        msg = update.message

        # --- Secret Chat hook ---
        s = secret_sessions.get(uid)
        if s and not _secret_active(uid):
            s = None
        secret_mode = bool(s)
        ttl = s["ttl"] if s else None
        if secret_mode:
            partner = s["partner"]   # force correct partner ONLY in secret mode

        log.info(f"[relay] uid={uid} secret={secret_mode}")

        # Secret: block forwarded/quoted (PTB v20+ compatible)
        is_fwd = False
        try:
            # v20: forwarded? -> forward_origin not None (or automatic forward)
            is_fwd = (msg.forward_origin is not None) or getattr(msg, "is_automatic_forward", False)
        except Exception:
            is_fwd = False

        if secret_mode and is_fwd:
            return await update.message.reply_text("⛔ Forwarding is disabled in Secret Chat.")

        # Check user's forwarding preference for normal chat
        allow_forward = reg.get_allow_forward(uid)  # DB truth
        if is_fwd and not allow_forward and not secret_mode:
            return await update.message.reply_text("⛔ Forwarding is disabled by your settings.")

        # Media rule (applies in Secret AND normal): only premium sender may send media
        is_media = any([msg.photo, msg.video, msg.animation, msg.document, msg.voice, msg.sticker])
        if is_media and not reg.has_active_premium(uid):
            # offer Ask-for-Premium
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("🎁 Ask for Premium", callback_data=f"giftreq:ask")
            ]])
            return await update.message.reply_text("⭐ Sending photos/videos is a Premium feature.", reply_markup=kb)

        # Secret Chat: pre-send approval for any media
        if secret_mode and is_media:
            # Capture file_id/type/caption and ask approval
            media_type, file_id, caption = None, None, msg.caption

            if msg.photo:
                media_type, file_id = "photo", msg.photo[-1].file_id
            elif msg.video:
                media_type, file_id = "video", msg.video.file_id
            elif msg.document:
                media_type, file_id = "document", msg.document.file_id
            elif msg.voice:
                media_type, file_id = "voice", msg.voice.file_id
            elif msg.animation:
                media_type, file_id = "animation", msg.animation.file_id
            elif msg.sticker:
                media_type, file_id = "sticker", msg.sticker.file_id

            pending_secret_media[(uid, msg.message_id)] = {
                "partner": partner,
                "ttl": ttl,
                "type": media_type,
                "file_id": file_id,
                "caption": caption or ""
            }

            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"scm:ok:{msg.message_id}")],
                [InlineKeyboardButton("❌ Decline", callback_data=f"scm:no:{msg.message_id}")]
            ])

            warn = (
                "⚠️ You are in Secret Chat.\n"
                "The bot cannot block screenshots. Only send if you are comfortable.\n"
                "Proceed to send this media?"
            )
            return await update.message.reply_text(warn, reply_markup=kb)

        sent_msg = None
        if msg.text:
            # *** skip bottom-menu taps ***
            if _is_menu_text(msg.text):
                return

            # Refined content moderation check
            moderation_result = _check_content_moderation(msg.text, uid)
            if moderation_result["action"] == "block":
                strikes = reg.add_strike(uid)
                await msg.reply_text(f"⚠️ {moderation_result.get('message', 'Content not allowed')}")
                if strikes >= 3:
                    # 24h temp ban
                    until = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                    reg.set_ban(uid, until, "Auto-moderation (harassment)", by_admin=0)
                    reg.reset_strikes(uid)
                    try:
                        await update.message.reply_text("🚫 You are temporarily banned for 24 hours due to repeated abuse.")
                    except Exception:
                        pass
                    return
                left = 3 - strikes
                return await update.message.reply_text(f"⚠️ Mind your language. ({strikes}/3) — {left} warning(s) left.")

            sent_msg = await context.bot.send_message(chat_id=partner, text=msg.text)
        elif msg.photo:
            sent_msg = await context.bot.send_photo(chat_id=partner, photo=msg.photo[-1].file_id, caption=msg.caption)
        elif msg.video:
            sent_msg = await context.bot.send_video(chat_id=partner, video=msg.video.file_id, caption=msg.caption)
        elif msg.document:
            sent_msg = await context.bot.send_document(chat_id=partner, document=msg.document.file_id, caption=msg.caption)
        elif msg.sticker:
            sent_msg = await context.bot.send_sticker(chat_id=partner, sticker=msg.sticker.file_id)
        elif msg.animation:
            sent_msg = await context.bot.send_animation(chat_id=partner, animation=msg.animation.file_id, caption=msg.caption)
        elif msg.voice:
            sent_msg = await context.bot.send_voice(chat_id=partner, voice=msg.voice.file_id)
        else:
            return  # unsupported message type

        # Self-destruct in Secret mode
        if secret_mode and sent_msg and ttl:
            async def _erase(mid, chat_id):
                try:
                    await asyncio.sleep(ttl)
                    await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                except Exception:
                    pass
            # recipient & sender both
            asyncio.create_task(_erase(sent_msg.message_id, partner))
            try:
                asyncio.create_task(_erase(msg.message_id, update.effective_chat.id))
            except Exception:
                pass

        try:
            increment_sent(uid)
            increment_received(partner)
        except Exception as e:
            log.warning(f"metrics bump failed: {e}")
        
        # Update friendship level if they are friends
        try:
            if reg.is_friends(uid, partner):
                reg.update_friendship_level(uid, partner)
        except Exception as e:
            log.warning(f"friendship level update failed: {e}")
        
        # Check and award badges for message activity
        try:
            reg.check_and_award_badges(uid)
        except Exception as e:
            log.warning(f"badge check failed: {e}")
            
    except Exception as e:
        log.error(f"Relay failed: {e}")
        await update.message.reply_text("⚠️ Failed to send message.")

# --- Gift request handlers ---

# requester tapped "Ask for Premium"
async def on_giftreq_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    partner = partner_of(uid)
    if not partner:
        return await q.answer("Not in chat.", show_alert=True)

    await q.answer("Request sent ✅")

    # Send request to partner with YES/NO
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Gift 1 week",  callback_data=f"gift:pay:w1:{uid}"),
         InlineKeyboardButton("🎁 Gift 1 month", callback_data=f"gift:pay:m1:{uid}")],
        [InlineKeyboardButton("❌ No", callback_data=f"gift:no:{uid}")]
    ])
    text = (f"🎁 Your partner ({safe_display_name(uid)}) is asking Premium to send photos/videos.\n"
            f"Would you like to gift Premium?")
    try:
        await context.bot.send_message(chat_id=partner, text=text, reply_markup=kb)
    except Exception:
        pass

# partner pressed NO
async def on_gift_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        m = cb_match(q.data or "", r"^gift:no:(?P<requester>\d+)$")
        target = int(m["requester"])
    except (CBError, ValueError):
        log.warning(f"Invalid gift:no callback: {q.data}")
        return
    await q.answer("Declined")
    try:
        await context.bot.send_message(chat_id=target, text="❌ Your partner declined to gift Premium.")
    except Exception:
        pass
    try:
        await q.edit_message_text("❌ You declined to gift Premium.")
    except Exception:
        pass

# partner chose a plan -> create invoice (gift)
async def on_gift_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        m = cb_match(q.data or "", r"^gift:pay:(?P<pack_id>\w+):(?P<target>\d+)$")
        pack_id = m["pack_id"]
        target_id = int(m["target"])  # requester to receive premium
    except (CBError, ValueError):
        log.warning(f"Invalid gift:pay callback: {q.data}")
        return
    payer_id  = q.from_user.id
    await q.answer()

    # delegate invoice creation to premium_handlers (new helper below)
    from handlers.premium_handlers import send_gift_invoice
    try:
        await send_gift_invoice(update, context, payer_id, target_id, pack_id)
    except Exception as e:
        try:
            await context.bot.send_message(payer_id, f"⚠️ Could not start gift: {e}")
        except Exception:
            pass

# -------- registration to application --------
def register_handlers(app: Application):
    app.add_handler(CallbackQueryHandler(on_pref, pattern=r"^pref:(any|f|m)$"), group=1)

    app.add_handler(CallbackQueryHandler(on_giftreq_ask, pattern=r"^giftreq:ask$"), group=0)
    app.add_handler(CallbackQueryHandler(on_gift_no,     pattern=r"^gift:no:\d+$"), group=0)
    app.add_handler(CallbackQueryHandler(on_gift_pay,    pattern=r"^gift:pay:(w1|m1):\d+$"), group=0)

    app.add_handler(CommandHandler("find",   cmd_find))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("next",   cmd_next))
    app.add_handler(CommandHandler("stop",   cmd_stop))
    app.add_handler(CommandHandler("end",    cmd_end))

    app.add_handler(CommandHandler("secret", cmd_secret), group=0)
    app.add_handler(CallbackQueryHandler(on_secret_callback, pattern=r"^secret:(pick_timer|pick_ttl|set_dur:\d+|set_ttl:\d+|send|accept:\d+:\d+:\d+|decline:\d+)$"), group=0)
    app.add_handler(CommandHandler("endsecret", cmd_endsecret), group=0)
    app.add_handler(CommandHandler("boost", cmd_boost), group=0)

    app.add_handler(CommandHandler("daily", cmd_daily), group=0)
    app.add_handler(CommandHandler("balance", cmd_balance), group=0)
    app.add_handler(CommandHandler("coins", cmd_balance), group=0)  # alias

    app.add_handler(CommandHandler("addfriend", cmd_addfriend), group=0)
    app.add_handler(CommandHandler("friends", cmd_friends), group=0)
    app.add_handler(CallbackQueryHandler(on_rm_ask, pattern=r"^rm:ask:\d+$"), group=0)
    app.add_handler(CallbackQueryHandler(on_rm_decide, pattern=r"^rm:(acc|dec):\d+$"), group=0)
    # Friend handlers moved to friends_handlers.py to avoid conflicts

    app.add_handler(CommandHandler("tip", cmd_tip), group=0)
    app.add_handler(CommandHandler("love", cmd_love), group=0)
    app.add_handler(CallbackQueryHandler(on_gift_cb, pattern=r"^gift:(flowers|dessert|teddy):\d+:\d+$"), group=0)
    app.add_handler(CallbackQueryHandler(on_tip_cb, pattern=r"^tip:(ok|cancel)"), group=0)

    app.add_handler(CallbackQueryHandler(on_secret_media_decide, pattern=r"^scm:(ok|no):\d+$"), group=0)



    app.add_handler(CallbackQueryHandler(on_rate_callback,
        pattern=r"^rate:(good|bad|report):\d+$"), group=1)

    # Report button callback
    app.add_handler(CallbackQueryHandler(on_report_button, pattern=r"^report:start$"), group=0)

    # 1) NORMAL RELAY — run before report-catcher
    app.add_handler(
        MessageHandler((filters.ALL & ~filters.COMMAND & ~filters.StatusUpdate.ALL), relay),
        group=1
    )

    # 2) /report and /cancel commands
    app.add_handler(CommandHandler("report", cmd_report), group=0)
    app.add_handler(CommandHandler("cancel", cmd_cancel), group=0)

    # 3) REPORT CATCHER — run with highest priority to prevent other handlers from intercepting
    app.add_handler(
        MessageHandler(
            ~filters.COMMAND & (
                (filters.TEXT & ~filters.Regex(MENU_RE))
                | filters.PHOTO
                | filters.Document.ALL
                | filters.VIDEO
                | filters.ANIMATION
            ),
            on_report_input
        ),
        group=-20  # HIGHEST PRIORITY: beats fantasy(-12), vault(-11), confession(-8), firewall(0), relay(1)
    )

# --- NEW HANDLERS FOR /report ---

# /report : start capture
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # 1) Try active partner
    partner = partner_of(uid)
    in_secret = bool(secret_sessions.get(uid))

    # 2) Fallback: last partner within 15 minutes
    if not partner:
        ent = last_chat_partner.get(uid)
        if ent:
            age = (datetime.datetime.utcnow() - ent["ts"]).total_seconds()
            if age <= 15 * 60:
                partner = ent["partner"]
                in_secret = bool(ent["in_secret"])

    if not partner:
        # Check if user is in fantasy chat (fantasy handler will handle it)
        from handlers.text_framework import get_state
        state = get_state(context)
        if state and state.get("feature") in ["fantasy_relay", "fantasy_chat", "fantasy"]:
            return  # Let fantasy report handler handle this
        
        return await update.message.reply_text(
            "ℹ️ You can report your most recent chat within 15 minutes. "
            "Please use /report right after the chat ends."
        )

    # claim text input state to prevent other handlers from interfering
    from handlers.text_framework import set_state
    set_state(context, "report", "text", ttl_minutes=2)  # claim text input for 2 mins
    
    # start capture state
    context.user_data["report"] = {"partner": partner, "in_secret": in_secret, "awaiting": True}
    await update.message.reply_text(
        "🛡️ Please type your reason and (optional) attach ONE screenshot/photo.\n"
        "Send within 2 minutes. Type /cancel to abort."
    )

# message catcher after /report (text or photo/doc)
async def on_report_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ⚡ SAFETY OVERRIDE: Reports have highest priority - check report mode first
    r = context.user_data.get("report")
    if not r or not r.get("awaiting"):
        # NOT in reporting mode: defer to text framework if active
        af = context.user_data.get(FEATURE_KEY)
        if af:   # e.g., "fantasy", "vault", "confession", "profile", ...
            return
        return  # NOT in reporting mode: let other handlers (relay) do the work
    
    # ✅ WE ARE IN REPORT MODE: Override any active text framework state
    # Clear text framework state temporarily to ensure report gets processed
    af = context.user_data.get(FEATURE_KEY)
    if af:
        # Temporarily clear text framework state for safety
        temp_feature = context.user_data.pop(FEATURE_KEY, None)
        temp_mode = context.user_data.pop(MODE_KEY, None)
        log.info(f"Report override: temporarily cleared text framework state {temp_feature}/{temp_mode} for user {update.effective_user.id}")
        # Note: We don't restore the state after because the report flow will complete
        # and the user will be returned to the main menu

    uid = update.effective_user.id
    partner = r["partner"]
    in_secret = r["in_secret"]

    # Validate and sanitize report text
    raw_text = update.message.caption or update.message.text or ""
    is_valid, error_msg, text = validate_and_sanitize_input(raw_text, 'comment')
    if not is_valid:
        await update.message.reply_text(f"❌ {error_msg}")
        raise ApplicationHandlerStop  # Prevent invalid report from being sent to chat partner
    media_file_id, media_type = None, None

    if update.message.photo:
        media_file_id = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.document:
        media_file_id = update.message.document.file_id
        media_type = "document"

    # persist to DB
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                INSERT INTO chat_reports (reporter_tg_id, reported_tg_id, in_secret, text, media_file_id, media_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (uid, partner, in_secret, text, media_file_id, media_type))
            row = cur.fetchone()
            con.commit()
        report_id, created_at = row[0], row[1]
    except Exception as e:
        context.user_data["report"] = None
        await update.message.reply_text(f"❗ Could not save report: {e}")
        raise ApplicationHandlerStop  # Prevent failed report from being sent to chat partner

    # ack to reporter
    await update.message.reply_text("✅ Thanks. Your report has been submitted.")

    # notify admins
    from_name = safe_display_name(uid)
    to_name   = safe_display_name(partner)

    summary = (
        f"🧾 Report #{report_id}\n"
        f"From: {uid} ({from_name})\n"
        f"Against: {partner} ({to_name})\n"
        f"Secret: {'Yes' if in_secret else 'No'}\n"
        f"Text: {text[:400] or '—'}"
    )
    for admin_id in ADMIN_IDS:
        try:
            if media_file_id and media_type == "photo":
                await context.bot.send_photo(admin_id, media_file_id, caption=summary)
            elif media_file_id and media_type == "document":
                await context.bot.send_document(admin_id, media_file_id, caption=summary)
            else:
                await context.bot.send_message(admin_id, summary)
        except Exception:
            pass

    # clear state
    context.user_data["report"] = None
    
    # CRITICAL: Stop handler chain to prevent report text from being relayed to chat partner
    raise ApplicationHandlerStop

# Cancel (optional):
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("report"):
        context.user_data["report"] = None
        return await update.message.reply_text("❌ Report cancelled.")

# Approve/Decline secret media sending
async def on_secret_media_decide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data or ""
    try:
        from utils.cb import cb_match
        m = cb_match(data, r"^scm:(?P<dec>ok|no):(?P<mid>\d+)$")
        action = m["dec"]
        sender_mid = int(m["mid"])
    except:
        return await q.answer("Invalid.", show_alert=True)

    uid = q.from_user.id
    key = (uid, sender_mid)
    pack = pending_secret_media.get(key)

    if not pack:
        await q.answer("Expired.", show_alert=True)
        try:
            await q.edit_message_text("⚠️ This media request has expired.")
        except Exception:
            pass
        return

    if action == "no":
        pending_secret_media.pop(key, None)
        await q.answer("Cancelled.")
        try:
            await q.edit_message_text("❌ Media sending cancelled.")
        except Exception:
            pass
        return

    if action != "ok":
        return await q.answer()

    # OK → forward with protect_content=True and apply TTL
    partner = pack["partner"]
    ttl     = pack["ttl"]
    mtype   = pack["type"]
    fid     = pack["file_id"]
    caption = pack["caption"]

    await q.answer("Sending…")
    try:
        sent_msg = None
        if mtype == "photo":
            sent_msg = await context.bot.send_photo(partner, fid, caption=caption, protect_content=True)
        elif mtype == "video":
            sent_msg = await context.bot.send_video(partner, fid, caption=caption, protect_content=True)
        elif mtype == "document":
            sent_msg = await context.bot.send_document(partner, fid, caption=caption, protect_content=True)
        elif mtype == "animation":
            sent_msg = await context.bot.send_animation(partner, fid, caption=caption, protect_content=True)
        elif mtype == "voice":
            sent_msg = await context.bot.send_voice(partner, fid, protect_content=True)
        elif mtype == "sticker":
            sent_msg = await context.bot.send_sticker(partner, fid, protect_content=True)

        # TTL: delete both sides if active
        if sent_msg and ttl:
            async def _erase(mid, chat_id):
                try:
                    await asyncio.sleep(ttl)
                    await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                except Exception:
                    pass
            asyncio.create_task(_erase(sent_msg.message_id, partner))
            # delete sender's original too (optional; keep it consistent with your session policy)
            try:
                asyncio.create_task(_erase(sender_mid, uid))
            except Exception:
                pass

        pending_secret_media.pop(key, None)
        try:
            await q.edit_message_text("✅ Media sent.")
        except Exception:
            pass
    except Exception as e:
        pending_secret_media.pop(key, None)
        try:
            await q.edit_message_text(f"⚠️ Failed to send media: {e}")
        except Exception:
            pass

# "Report" button callback handler
async def on_report_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    partner = partner_of(uid)
    in_secret = bool(secret_sessions.get(uid))

    if not partner:
        ent = last_chat_partner.get(uid)
        if ent:
            age = (datetime.datetime.utcnow() - ent["ts"]).total_seconds()
            if age <= 15 * 60:
                partner = ent["partner"]
                in_secret = bool(ent["in_secret"])

    if not partner:
        await q.answer("No recent chat to report.", show_alert=True)
        return

    context.user_data["report"] = {"partner": partner, "in_secret": in_secret, "awaiting": True}
    await q.answer()
    await q.edit_message_text(
        "🛡️ Please type your reason and (optional) attach ONE screenshot/photo.\n"
        "Send within 2 minutes. Type /cancel to abort."
    )