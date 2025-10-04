# handlers/afterdark_admin.py
from telegram.ext import CommandHandler, ContextTypes
from telegram import Update
import registration as reg
from handlers.after_dark import _exec, _get_live_session
from admin import ADMIN_IDS

async def ad_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    live = _get_live_session()
    if not live:
        return await update.message.reply_text("No live After Dark session.")
    sid, started_at, ends_at, vibe, status = live
    row = _exec("SELECT COUNT(*) FROM ad_participants WHERE session_id=%s AND left_at IS NULL", (sid,))
    count = int(row[0][0]) if row else 0
    await update.message.reply_text(
        f"AD Session #{sid}\nStatus: {status}\nVibe: {vibe or '-'}\n"
        f"Started: {started_at}\nEnds: {ends_at}\nParticipants: {count}"
    )

async def ad_end_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    live = _get_live_session()
    if not live:
        return await update.message.reply_text("No live session.")
    sid = live[0]
    _exec("UPDATE ad_sessions SET status='expired', ends_at=NOW() WHERE id=%s", (sid,))
    await update.message.reply_text(f"Ended AD session #{sid}")

def register(app):
    app.add_handler(CommandHandler("ad_status", ad_status), group=0)
    app.add_handler(CommandHandler("ad_end_now", ad_end_now), group=0)