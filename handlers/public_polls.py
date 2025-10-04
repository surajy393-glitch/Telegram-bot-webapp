
from telegram import Update
from telegram.ext import (CommandHandler, MessageHandler, filters, ContextTypes)
from handlers.text_framework import claim_or_reject, requires_state, clear_state

async def poll_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await claim_or_reject(update, context, "polls", "create", ttl_minutes=3):
        return
    await update.message.reply_text("🗳 Type your poll question:")

@requires_state("polls", "create")
async def poll_create_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = (update.message.text or "").strip()
    if not q:
        return
    # TODO: create poll row
    clear_state(context)
    await update.message.reply_text("✅ Poll created.")

def register(app):
    # Legacy handlers disabled - poll functionality moved to poll_handlers.py
    # app.add_handler(CommandHandler("poll_create", poll_create_start), group=-5)
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, poll_create_text), group=-5)
    pass
