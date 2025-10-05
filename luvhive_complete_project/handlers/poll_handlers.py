# handlers/poll_handlers.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CallbackQueryHandler, MessageHandler, ContextTypes, filters, CommandHandler
)
import registration as reg
import os
from utils.cb import cb_match, CBError
from handlers.text_framework import FEATURE_KEY, requires_state, clear_state, claim_or_reject, make_cancel_kb
from state import set_poll, get_poll, clear_poll
from typing import List

# Admin system
def _parse_admins(s: str) -> set[int]:
    out = set()
    for x in (s or "").replace(",", " ").split():
        if x.isdigit():
            out.add(int(x))
    return out

ADMIN_IDS = _parse_admins(os.getenv("ADMIN_IDS", "")) or {1437934486, 647778438}

def _is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

def _uid(update: Update) -> int:
    u = update.effective_user
    return u.id if u else 0

# ---- state keys
# ASK_Q   = "poll:askq"     # waiting for question
# ASK_OPS = "poll:askops"   # waiting for options for last draft poll

# ---- DB ensure ----
def ensure_poll_tables():
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS polls(
            id BIGSERIAL PRIMARY KEY,
            author_id BIGINT NOT NULL,
            question TEXT NOT NULL,
            options TEXT[] NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS poll_options(
            id BIGSERIAL PRIMARY KEY,
            poll_id BIGINT NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
            text TEXT NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS poll_votes(
            poll_id BIGINT NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
            voter_id BIGINT NOT NULL,
            option_idx INTEGER NOT NULL,
            voted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY(poll_id, voter_id)
        );
        """)
        con.commit()

# ---- UI helpers ----
def _board_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Create Poll", callback_data="poll:new")],
        [InlineKeyboardButton("⬅️ Back", callback_data="pf:menu")]
    ])

def _poll_kb(pid:int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗳 Vote", callback_data=f"poll:vote:{pid}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="poll:board")]
    ])

# ---- Board ----
async def on_board(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""SELECT id, question
                       FROM polls WHERE deleted_at IS NULL
                       ORDER BY created_at DESC LIMIT 10""")
        rows = cur.fetchall()
    if not rows:
        return await q.edit_message_text("📊 Public Polls\n\nNo polls yet.", reply_markup=_board_kb())
    text = "📊 <b>Public Polls</b>\n"
    for pid, qt in rows:
        qt = (qt[:110] + "…") if len(qt) > 111 else qt
        text += f"\n• {qt}\n   ➜ Open: /poll{pid}\n"
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=_board_kb())

# ---- Create Poll flow ----
async def poll_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start poll creation flow"""
    q = update.callback_query
    if q:
        await q.answer()
    
    # CRITICAL FIX: Claim text_framework state to prevent other handlers from intercepting
    from handlers.text_framework import claim_or_reject
    ok = await claim_or_reject(update, context, feature="poll", mode="question", ttl_minutes=5)
    if not ok:
        return  # Another feature owns text input
    
    clear_poll(_uid(update))
    set_poll(_uid(update), mode="question")
    
    message = q.message if q else update.message
    await message.reply_text(
        "📝 Send your poll question (one line):\n\nType ⛔ /cancel to abort."
    )

# HIGH-PRIORITY TEXT CAPTURE (BEFORE FIREWALL)
async def poll_text_sink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture poll text input with high priority"""
    from telegram.ext import ApplicationHandlerStop
    from handlers.text_framework import set_state, clear_state, is_in_feature
    
    m = update.effective_message
    if not m or not m.text:
        return
    uid = _uid(update)
    st = get_poll(uid)
    
    # CRITICAL: Only handle if we're in poll mode OR text_framework shows poll feature
    if not st and not is_in_feature(context, "poll"):
        return  # not in poll mode; let others handle
        
    # If in poll mode, BLOCK all downstream handlers
    if st or is_in_feature(context, "poll"):
        text = (m.text or "").strip()
        if not text:
            await m.reply_text("⚠️ Empty. Type some text or /cancel.")
            raise ApplicationHandlerStop  # BLOCK downstream handlers
            
        # If we don't have poll state but text_framework shows poll, something is wrong
        if not st:
            clear_state(context) 
            await m.reply_text("❌ Poll session expired. Please start again.")
            raise ApplicationHandlerStop

        # Step 1: capture question -> ask options
        if st["mode"] == "question":
            if len(text) > 200:
                await m.reply_text("⚠️ Question too long (max 200 chars). Try again.")
                raise ApplicationHandlerStop
            set_poll(uid, mode="options", question=text)
            set_state(context, feature="poll", mode="options", ttl_minutes=5)  # Update text_framework state
            await m.reply_text(
                "🧩 Now send options separated by comma (min 2, max 6).\n"
                "Example: Apple, Banana, Grapes\n\nType ⛔ /cancel to abort."
            )
            raise ApplicationHandlerStop  # BLOCK downstream handlers

        # Step 2: capture options -> validate -> create poll -> clear
        elif st["mode"] == "options":
            # split by comma
            opts: List[str] = [o.strip() for o in text.split(",")]
            opts = [o for o in opts if o]  # remove empties
            # dedupe preserving order
            seen = set()
            uniq: List[str] = []
            for o in opts:
                if o.lower() in seen: 
                    continue
                seen.add(o.lower())
                uniq.append(o)

            if not (2 <= len(uniq) <= 6):
                await m.reply_text("⚠️ Please send 2 to 6 options, comma-separated.")
                raise ApplicationHandlerStop

            # length guard per option
            if any(len(o) > 50 for o in uniq):
                await m.reply_text("⚠️ Each option must be ≤ 50 chars.")
                raise ApplicationHandlerStop

            question = st.get("question") or "Poll"
            # Create poll in DB
            with reg._conn() as con, con.cursor() as cur:
                cur.execute(
                    "INSERT INTO polls(author_id, question, options) VALUES (%s,%s,%s) RETURNING id", 
                    (uid, question, uniq)
                )
                pid = cur.fetchone()[0]
                for opt in uniq:
                    cur.execute("INSERT INTO poll_options(poll_id, text) VALUES (%s,%s)", (pid, opt))
                con.commit()

            # CRITICAL: Clear both poll state AND text_framework state
            clear_poll(uid)
            clear_state(context)
            
            # Success + open button
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 View Poll", callback_data=f"polls:open:{pid}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="poll:board")]
            ])
            await m.reply_text(
                f"✅ Poll created! Open with /poll{pid}",
                reply_markup=kb
            )
            raise ApplicationHandlerStop  # BLOCK downstream handlers
async def poll_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel poll creation"""
    from handlers.text_framework import clear_state
    clear_poll(_uid(update))
    clear_state(context)  # CRITICAL: Also clear text_framework state
    await update.effective_message.reply_text("❌ Poll creation cancelled.")

# Legacy handlers - keeping for compatibility but removing old text handling
@requires_state(feature="polls", mode="options")
async def on_poll_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle poll options input"""
    txt = (update.message.text or "").strip()
    if not txt:
        return

    parts = [p.strip() for p in txt.split(",") if p.strip()]
    if len(parts) < 2:
        return await update.message.reply_text("❗ Please send at least 2 comma-separated options.")
    if len(parts) > 6:
        return await update.message.reply_text("❗ Max 6 options allowed.")

    question = context.user_data.get("poll_buf", {}).get("question", "Poll")
    uid = update.effective_user.id

    # Save to DB
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("INSERT INTO polls(author_id, question, options) VALUES (%s,%s,%s) RETURNING id", (uid, question, parts))
        pid = cur.fetchone()[0]
        for opt in parts:
            cur.execute("INSERT INTO poll_options(poll_id, text) VALUES (%s,%s)", (pid, opt))
        con.commit()

    # Clear all state
    clear_state(context)
    context.user_data["poll_buf"] = {}

    # Success + open button
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Open Poll", callback_data=f"polls:open:{pid}")],
        [InlineKeyboardButton("⬅️ Back",  callback_data="poll:board")]
    ])
    await update.message.reply_text("✅ Poll created!", reply_markup=kb)

# ---- open one via command like /poll12 ----
import re
async def cmd_open(update:Update, context:ContextTypes.DEFAULT_TYPE):
    m = re.match(r"^/poll(\d+)", (update.message.text or ""))
    if not m: return
    pid = int(m.group(1))
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT question FROM polls WHERE id=%s AND deleted_at IS NULL",(pid,))
        row = cur.fetchone()
        if not row: return await update.message.reply_text("❌ Poll not found.")
        q = row[0]
        cur.execute("SELECT id, text FROM poll_options WHERE poll_id=%s ORDER BY id",(pid,))
        ops = cur.fetchall()
        # current totals
        cur.execute("""
            SELECT option_idx, COUNT(*) FROM poll_votes WHERE poll_id=%s
            GROUP BY option_idx
        """,(pid,))
        tallies = dict(cur.fetchall() or [])
    text = f"📊 <b>{q}</b>\n\n"
    for idx, (oid, label) in enumerate(ops):
        c = tallies.get(idx,0)
        text += f"• {label} — <b>{c}</b>\n"

    # Build keyboard with vote buttons + admin delete button if admin
    vote_buttons = [[InlineKeyboardButton(ops[i][1], callback_data=f"poll:pick:{pid}:{i}")] for i in range(len(ops))]
    back_row = [InlineKeyboardButton("⬅️ Back", callback_data="poll:board")]

    # Add delete button for admins
    if _is_admin(update.effective_user.id):
        back_row.append(InlineKeyboardButton("🗑️ Delete", callback_data=f"poll:delete:{pid}"))

    kb = InlineKeyboardMarkup(vote_buttons + [back_row])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)

# ---- voting buttons ----
async def on_pick(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    try:
        m = cb_match(q.data or "", r"^poll:pick:(?P<pid>\d+):(?P<option>\d+)$")
        pid, option_idx = int(m["pid"]), int(m["option"])
    except (CBError, ValueError):
        return
    uid = q.from_user.id

    with reg._conn() as con, con.cursor() as cur:
        # upsert vote
        cur.execute("""
            INSERT INTO poll_votes(poll_id,voter_id,option_idx)
            VALUES (%s,%s,%s)
            ON CONFLICT (poll_id, voter_id) DO UPDATE SET option_idx=EXCLUDED.option_idx
        """,(pid,uid,option_idx))
        con.commit()

        # Get updated poll data to show real-time results
        cur.execute("SELECT question FROM polls WHERE id=%s AND deleted_at IS NULL", (pid,))
        row = cur.fetchone()
        if not row:
            return await q.answer("❌ Poll not found.")
        question = row[0]
        cur.execute("SELECT id, text FROM poll_options WHERE poll_id=%s ORDER BY id", (pid,))
        ops = cur.fetchall()
        # current totals
        cur.execute("""
            SELECT option_idx, COUNT(*) FROM poll_votes WHERE poll_id=%s
            GROUP BY option_idx
        """, (pid,))
        tallies = dict(cur.fetchall() or [])

    # Build updated poll display
    text = f"📊 <b>{question}</b>\n\n"
    for idx, (oid, label) in enumerate(ops):
        c = tallies.get(idx, 0)
        text += f"• {label} — <b>{c}</b>\n"

    # Build keyboard with vote buttons + admin delete button if admin
    vote_buttons = [[InlineKeyboardButton(ops[i][1], callback_data=f"poll:pick:{pid}:{i}")] for i in range(len(ops))]
    back_row = [InlineKeyboardButton("⬅️ Back", callback_data="poll:board")]

    # Add delete button for admins
    if _is_admin(uid):
        back_row.append(InlineKeyboardButton("🗑️ Delete", callback_data=f"poll:delete:{pid}"))

    kb = InlineKeyboardMarkup(vote_buttons + [back_row])

    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    await q.answer("Vote saved ✅")

# Handle opening polls from success message
async def on_polls_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        m = cb_match(q.data or "", r"^polls:open:(?P<pid>\d+)$")
        pid = int(m["pid"])
    except (CBError, ValueError):
        return

    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT question FROM polls WHERE id=%s AND deleted_at IS NULL", (pid,))
        row = cur.fetchone()
        if not row:
            return await q.edit_message_text("❌ Poll not found.")
        question = row[0]
        cur.execute("SELECT id, text FROM poll_options WHERE poll_id=%s ORDER BY id", (pid,))
        ops = cur.fetchall()
        # current totals
        cur.execute("""
            SELECT option_idx, COUNT(*) FROM poll_votes WHERE poll_id=%s
            GROUP BY option_idx
        """, (pid,))
        tallies = dict(cur.fetchall() or [])

    text = f"📊 <b>{question}</b>\n\n"
    for idx, (oid, label) in enumerate(ops):
        c = tallies.get(idx, 0)
        text += f"• {label} — <b>{c}</b>\n"

    # Build keyboard with vote buttons + admin delete button if admin
    vote_buttons = [[InlineKeyboardButton(ops[i][1], callback_data=f"poll:pick:{pid}:{i}")] for i in range(len(ops))]
    back_row = [InlineKeyboardButton("⬅️ Back", callback_data="poll:board")]

    # Add delete button for admins
    if _is_admin(q.from_user.id):
        back_row.append(InlineKeyboardButton("🗑️ Delete", callback_data=f"poll:delete:{pid}"))

    kb = InlineKeyboardMarkup(vote_buttons + [back_row])
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

# ---- Admin poll deletion ----
async def on_poll_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    # Check if user is admin
    if not _is_admin(q.from_user.id):
        await q.answer("❌ Access denied.")
        return

    try:
        _, _, pid_s = q.data.split(":")
        pid = int(pid_s)
    except:
        return

    # Delete the poll (soft delete by setting deleted_at)
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("UPDATE polls SET deleted_at=NOW() WHERE id=%s", (pid,))
        con.commit()

    await q.edit_message_text("🗑️ <b>Poll deleted by admin.</b>", parse_mode="HTML")

# Dummy handlers for registration compatibility, will be replaced by framework handlers
async def cmd_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

# Removed handle_poll_text - this was causing text swallowing conflicts
# Text routing now handled by text_router using @requires_state decorators


def register(app):
    """Register poll handlers"""
    ensure_poll_tables()

    # HIGHEST PRIORITY: Poll text capture (runs BEFORE all other text handlers to prevent swallowing)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, poll_text_sink), group=-9)
    app.add_handler(CommandHandler("cancel", poll_cancel), group=-10)

    app.add_handler(CommandHandler("poll", cmd_open), group=-5)
    app.add_handler(CommandHandler("poll_create", poll_create_start), group=-5)
    app.add_handler(CallbackQueryHandler(on_board, pattern=r"^poll:board$"), group=0)
    app.add_handler(CallbackQueryHandler(poll_create_start, pattern=r"^poll:new$"), group=0)
    app.add_handler(CallbackQueryHandler(on_pick,  pattern=r"^poll:pick:\d+:\d+$"), group=0)
    app.add_handler(CallbackQueryHandler(on_polls_open, pattern=r"^polls:open:\d+$"), group=-1)
    app.add_handler(CallbackQueryHandler(on_poll_delete, pattern=r"^poll:delete:\d+$"), group=0)
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r"^/poll\d+$"), cmd_open), group=0)
    # Removed old conflicting text handler - was causing text swallowing with poll_text_sink