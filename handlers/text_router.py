# handlers/text_router.py
from telegram.ext import MessageHandler, filters, ContextTypes
from telegram import Update
from .text_framework import FEATURE_KEY
import logging

log = logging.getLogger("text_router")

async def fallback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Last-resort text handler - only processes unclaimed text"""
    # only run if nobody claimed state
    if context.user_data and context.user_data.get(FEATURE_KEY):
        return  # another feature owns input; do nothing
    
    # Optional: ignore or show guidance
    # For now, we'll silently ignore unclaimed text to avoid spam
    # await update.message.reply_text("🤖 Not expecting text right now. Use menu buttons.")
    log.debug(f"[text_router] Unclaimed text ignored: {update.message.text[:50]}...")
    return

def register(app):
    """Register fallback text router with lowest priority"""
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text), group=9)
    log.info("[text_router] Fallback handler registered at group=9")

__all__ = ['register']