# handlers/qa_handlers.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (CommandHandler, CallbackQueryHandler, MessageHandler, 
                          filters, ContextTypes, ApplicationHandlerStop)
import registration as reg
import re, logging
from html import escape
from utils.cb import cb_match, CBError
from state import set_qa, get_qa, clear_qa
from typing import Optional

# --- permissions & metadata helpers ---

try:
    from utils.auth import is_admin  # your project may already have this
except Exception:
    def is_admin(user_id: int) -> bool:
        return user_id in ADMIN_IDS

def _question_scope(qid: int) -> str | None:
    # returns "public" or "admin" (admin-only)
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT scope FROM qa_questions WHERE id=%s AND deleted_at IS NULL", (qid,))
        row = cur.fetchone()
        return (row[0] if row else None)

def can_user_answer(user_id: int, qid: int) -> bool:
    scope = _question_scope(qid)
    if scope is None:
        return False
    if scope == "admin":
        return is_admin(user_id)  # only admins may answer
    # scope == "public"
    return True                  # anyone may answer public

def _question_author(qid: int) -> Optional[int]:
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT author_id FROM qa_questions WHERE id=%s", (qid,))
        row = cur.fetchone()
        return (row[0] if row else None)

def _can_delete(qid: int, user_id: int) -> bool:
    if not user_id:
        return False
    if is_admin(user_id):
        return True
    return _question_author(qid) == user_id

def _uid(update) -> int:
    u = getattr(update, "effective_user", None)
    return u.id if u else 0

log = logging.getLogger("luvbot.qa")


# ---- CONFIG ----
ADMIN_IDS = {647778438, 1437934486}   # <- tumhare admin IDs
ADMIN_DISPLAY = "Admin"
PAGE = 8                               # board page size


# ---- STATE KEYS ----
QA_ASK  = "qa:ask"    # state = qa:ask:<scope>   scope in {"public","admin"}
QA_ANS  = "qa:ans"    # state = qa:ans:<qid>


# =============== HELPER FUNCTIONS ==========
async def _render_question_body(qid: int):
    """Helper to render question body with answers"""
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT text, scope FROM qa_questions WHERE id=%s AND deleted_at IS NULL", (qid,))
        row = cur.fetchone()
        if not row:
            return None, None
        qtxt, scope = row
        cur.execute("""SELECT id, author_id, text, is_admin, created_at
                       FROM qa_answers
                       WHERE question_id=%s AND deleted_at IS NULL
                       ORDER BY created_at ASC""", (qid,))
        answers = cur.fetchall()

    # Safe HTML rendering
    body = f"👤 <b>User</b>\n❓ {escape(qtxt)}\n\n"
    if answers:
        body += "<b>Answers</b>:\n"
        for _aid, _au, at, is_admin, _ in answers:
            label = ADMIN_DISPLAY if is_admin else "User"
            body += f"• <b>{label}</b>: {escape(at)}\n"
    else:
        body += "(No answers yet)\n"
    return body, scope


# =============== DB ENSURE =================
def ensure_qa_tables():
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS qa_questions(
              id BIGSERIAL PRIMARY KEY,
              text TEXT NOT NULL,
              scope TEXT NOT NULL,           -- 'public' | 'admin'
              author_id BIGINT,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              deleted_at TIMESTAMPTZ
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS qa_answers(
              id BIGSERIAL PRIMARY KEY,
              question_id BIGINT NOT NULL REFERENCES qa_questions(id) ON DELETE CASCADE,
              author_id BIGINT NOT NULL,
              text TEXT NOT NULL,
              is_admin BOOLEAN NOT NULL DEFAULT FALSE,
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              deleted_at TIMESTAMPTZ
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_qa_q ON qa_questions(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_qa_a ON qa_answers(question_id, created_at)")
        con.commit()


# =============== HELPERS ===================
def _is_admin(uid:int)->bool: return uid in ADMIN_IDS


def _board_kb(page:int, has_more:bool):
    rows = [[InlineKeyboardButton("➕ Ask a Question", callback_data="qa:new")]]
    nav  = []
    if page>0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"qa:page:{page-1}"))
    if has_more: nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"qa:page:{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="pf:menu")])
    return InlineKeyboardMarkup(rows)


def _q_kb(qid: int, scope: str, viewer_id: int) -> InlineKeyboardMarkup:
    rows = []
    if can_user_answer(viewer_id, qid):
        rows.append([InlineKeyboardButton("💬 Answer", callback_data=f"qa:answer:{qid}")])
    else:
        if scope == "admin":
            rows.append([InlineKeyboardButton("🔒 Admin-only", callback_data="qa:noop")])
    if _can_delete(qid, viewer_id):
        rows.append([InlineKeyboardButton("🗑 Delete Question", callback_data=f"qa:del:{qid}")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="qa:board")])
    return InlineKeyboardMarkup(rows)


def _ans_kb(qid:int, aid:int, viewer:int):
    rows=[]
    if _is_admin(viewer):
        rows.append([InlineKeyboardButton("🗑️ Delete Answer", callback_data=f"qa:adel:{aid}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data=f"qa:open:{qid}")])
    return InlineKeyboardMarkup(rows)


# =============== BOARD =====================
async def on_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_qa(_uid(update))  # release input if some QA mode was active
    q = update.callback_query; await q.answer()
    page = 0
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""SELECT id, text, scope FROM qa_questions
                       WHERE deleted_at IS NULL
                       ORDER BY created_at DESC
                       LIMIT %s OFFSET %s""", (PAGE+1, page*PAGE))
        rows = cur.fetchall()
    more = len(rows) > PAGE
    rows = rows[:PAGE]
    if not rows:
        return await q.edit_message_text("❓ <b>Q/A Board</b>\n\nNo questions yet.",
                                         parse_mode="HTML", reply_markup=_board_kb(page, False))
    text = "❓ <b>Q/A Board</b>\n"
    for qid, qtxt, scope in rows:
        tag = " (public)" if scope == "public" else " (admin only)"
        if len(qtxt) > 140:
            qtxt = qtxt[:137] + "…"
        text += f"\n• <b>User</b>: {qtxt}{tag}\n   ➜ Open: /qa{qid}\n"
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=_board_kb(page, more))


async def on_board_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_qa(_uid(update))
    q = update.callback_query; await q.answer()
    try:
        m = cb_match(q.data or "", r"^qa:page:(?P<page>\d+)$")
        page = int(m["page"])
    except (CBError, ValueError):
        page = 0
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""SELECT id, text, scope FROM qa_questions
                       WHERE deleted_at IS NULL
                       ORDER BY created_at DESC
                       LIMIT %s OFFSET %s""", (PAGE+1, page*PAGE))
        rows = cur.fetchall()
    more = len(rows) > PAGE
    rows = rows[:PAGE]
    if not rows:
        return await q.edit_message_text("❓ <b>Q/A Board</b>\n\nNo questions.",
                                         parse_mode="HTML", reply_markup=_board_kb(page, False))
    text = "❓ <b>Q/A Board</b>\n"
    for qid, qtxt, scope in rows:
        tag = " (public)" if scope == "public" else " (admin only)"
        if len(qtxt) > 140:
            qtxt = qtxt[:137] + "…"
        text += f"\n• <b>User</b>: {qtxt}{tag}\n   ➜ Open: /qa{qid}\n"
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=_board_kb(page, more))


# open one question (via inline)
async def on_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_qa(_uid(update))
    q = update.callback_query; await q.answer()
    viewer = q.from_user.id
    try:
        m = cb_match(q.data or "", r"^qa:open:(?P<qid>\d+)$")
        qid = int(m["qid"])
    except (CBError, ValueError):
        return
    
    body, scope = await _render_question_body(qid)
    if body is None:
        return await q.edit_message_text("❌ Question not found.")
    
    await q.edit_message_text(body, parse_mode="HTML", reply_markup=_q_kb(qid, scope, viewer))


# command handler for /qa<number>
async def cmd_open_qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open specific question by ID from command like /qa123"""
    # Clear any active QA state to prevent text swallowing
    clear_qa(_uid(update))
    
    cmd_text = update.message.text or ""
    match = re.match(r'^/qa(\d+)$', cmd_text.strip())
    if not match:
        return await update.message.reply_text("❌ Use format: /qa123 (question ID)")
    
    qid = int(match.group(1))
    body, scope = await _render_question_body(qid)
    if body is None:
        return await update.message.reply_text("❌ Question not found.")
    
    viewer = update.effective_user.id
    await update.message.reply_text(body, parse_mode="HTML", reply_markup=_q_kb(qid, scope, viewer))


# =============== ASK FLOW ==================
async def on_new(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Public (anyone can answer)", callback_data="qa:scope:public")],
        [InlineKeyboardButton("🛡️ Admin only",                callback_data="qa:scope:admin")],
        [InlineKeyboardButton("⬅️ Back",                      callback_data="qa:board")]
    ])
    await q.message.reply_text("Choose question type:", reply_markup=kb)


async def on_scope(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    try:
        m = cb_match(q.data or "", r"^qa:scope:(?P<scope>\w+)$")
        scope = m["scope"]
    except:
        return

    clear_qa(q.from_user.id)                 # fresh
    set_qa(q.from_user.id, mode="ask")       # next text belongs to QA
    context.user_data['qa_scope'] = scope    # store scope for later
    await q.edit_message_text("📝 <b>Send your question text (anonymous):</b>\n\nType ⛔ /cancel to abort.", parse_mode="HTML")


# Answer start: set QA mode, prompt user
async def qa_answer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()  # IMPORTANT: always answer the callback

    m = re.match(r"^qa:answer:(\d+)$", q.data or "")
    if not m:
        return
    qid = int(m.group(1))
    uid = update.effective_user.id if update.effective_user else 0

    # 🚫 permission gate
    if not can_user_answer(uid, qid):
        return await q.answer("Only admins can answer this question.", show_alert=True)

    # fresh state -> capture next text as answer for this qid
    clear_qa(uid)
    set_qa(uid, mode="answer", qid=qid)

    # prompt to send the answer
    await q.message.reply_text("✍️ <b>Send your answer:</b>\n\nType ⛔ /cancel to abort.", parse_mode="HTML")


# moderation - removed old qdel handler, replaced with new delete system


async def on_adel(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id not in ADMIN_IDS: return
    try:
        m = cb_match(q.data or "", r"^qa:adel:(?P<aid>\d+)$")
        aid = int(m["aid"])
    except:
        return
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("UPDATE qa_answers SET deleted_at=NOW() WHERE id=%s", (aid,))
        con.commit()
    await q.message.reply_text("🗑️ Answer deleted.")


# Step 1: show confirm
async def qa_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    m = re.match(r"^qa:(?:del|delete|remove):(\d+)$", q.data or "")
    if not m:
        return
    qid = int(m.group(1))
    uid = update.effective_user.id if update.effective_user else 0
    if not _can_delete(qid, uid):
        return await q.answer("You are not allowed to delete this question.", show_alert=True)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, delete", callback_data=f"qa:del:yes:{qid}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"qa:open:{qid}")],
    ])
    await q.message.reply_text(f"⚠️ Delete question #{qid}?", reply_markup=kb)

# Step 2: perform soft delete
async def qa_delete_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    m = re.match(r"^qa:del:yes:(\d+)$", q.data or "")
    if not m:
        return
    qid = int(m.group(1))

    with reg._conn() as con, con.cursor() as cur:
        cur.execute(
            "UPDATE qa_questions SET deleted_at = NOW() WHERE id = %s AND deleted_at IS NULL",
            (qid,),
        )
        affected = cur.rowcount
        con.commit()

    if affected == 0:
        return await q.message.edit_text("⚠️ Already deleted or not found.")

    await q.message.edit_text("🗑 Question deleted.")
    # Optional: show board again (simple)
    await q.message.reply_text("❓ Q/A Board", reply_markup=_board_kb(0, False), parse_mode="HTML")


# =============== TEXT HANDLERS =================
# High priority text sink - runs BEFORE firewall (group -5)
async def qa_text_sink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture QA text before firewall blocks it"""
    m = update.effective_message
    if not m or not m.text:
        return
    
    st = get_qa(_uid(update))
    if not st:
        return  # not our text; let others handle

    text = m.text.strip()
    if not text:
        return await m.reply_text("⚠️ Empty message. Type some text or /cancel.")

    # Persist depending on mode
    if st["mode"] == "ask":
        # Get scope from context
        scope = context.user_data.get('qa_scope', 'public')
        
        # INSERT question
        with reg._conn() as con, con.cursor() as cur:
            author_id = m.from_user.id if m.from_user else None
            cur.execute("INSERT INTO qa_questions (text, scope, author_id) VALUES (%s, %s, %s) RETURNING id", (text, scope, author_id))
            qid = cur.fetchone()[0]
            con.commit()
        
        clear_qa(_uid(update))
        context.user_data.pop('qa_scope', None)  # cleanup
        return await m.reply_text(f"✅ Question submitted! View it with /qa{qid}")

    if st["mode"] == "answer":
        qid = st.get("qid")
        uid = m.from_user.id if m.from_user else 0
        if not qid:
            clear_qa(_uid(update))
            return await m.reply_text("⚠️ No question in context. Try again from the board.")
        # 🚫 second gate (race-safety)
        if not can_user_answer(uid, qid):
            clear_qa(_uid(update))
            return await m.reply_text("🔒 Only admins can answer this question.")
        
        is_admin_user = is_admin(uid) if uid else False
        
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""INSERT INTO qa_answers (question_id, author_id, text, is_admin)
                           VALUES (%s, %s, %s, %s)""",
                        (qid, uid, text, is_admin_user))
            con.commit()
        
        clear_qa(_uid(update))
        return await m.reply_text(f"✅ Answer saved for /qa{qid}")

# Cancel command (safe exit)
async def qa_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_qa(_uid(update))
    await update.effective_message.reply_text("❌ Cancelled.")


# register all
def register(app):
    ensure_qa_tables()
    
    # HIGH PRIORITY: QA text capture (runs BEFORE firewall)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, qa_text_sink), group=-6)
    app.add_handler(CommandHandler("cancel", qa_cancel), group=-10)
    
    # Handle /qa<number> commands with regex
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^/qa\d+$'), cmd_open_qa), group=-20)
    
    # Register all callback handlers
    app.add_handler(CallbackQueryHandler(on_board, pattern=r"^qa:board$"), group=0)
    app.add_handler(CallbackQueryHandler(on_board_page, pattern=r"^qa:page:\d+$"), group=0)
    app.add_handler(CallbackQueryHandler(on_open, pattern=r"^qa:open:\d+$"), group=0)
    app.add_handler(CallbackQueryHandler(on_new, pattern=r"^qa:new$"), group=0)
    app.add_handler(CallbackQueryHandler(on_scope, pattern=r"^qa:scope:\w+$"), group=0)
    app.add_handler(CallbackQueryHandler(qa_answer_start, pattern=r"^qa:answer:\d+$"), group=-10)
    app.add_handler(CallbackQueryHandler(on_adel, pattern=r"^qa:adel:\d+$"), group=0)
    
    # New delete handlers with higher priority
    app.add_handler(CallbackQueryHandler(qa_delete_confirm, pattern=r"^qa:(?:del|delete|remove):\d+$"), group=-10)
    app.add_handler(CallbackQueryHandler(qa_delete_execute, pattern=r"^qa:del:yes:\d+$"), group=-10)