
# handlers/utils/safe_telegram.py - Safe wrappers for Telegram API calls

from typing import Optional
from telegram import Update, Message
from telegram.ext import ContextTypes

def get_chat_id(update: Update) -> Optional[int]:
    """Safely get chat ID from update"""
    chat = getattr(update, "effective_chat", None)
    return getattr(chat, "id", None)

def get_message(update: Update) -> Optional[Message]:
    """Safely get message from update (direct or callback)"""
    if getattr(update, "message", None):
        return update.message
    q = getattr(update, "callback_query", None)
    if q and getattr(q, "message", None):
        return q.message
    return None

async def reply_any(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kw):
    """Reply to any update type safely"""
    msg = get_message(update)
    if msg:
        return await msg.reply_text(text, **kw)
    chat_id = get_chat_id(update)
    if chat_id:
        return await context.bot.send_message(chat_id, text, **kw)
    return None

async def edit_or_send(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kw):
    """Try to edit callback message, fallback to send new message"""
    q = getattr(update, "callback_query", None)
    if q and getattr(q, "message", None):
        try:
            return await q.edit_message_text(text, **kw)
        except Exception:
            pass
    return await reply_any(update, context, text, **kw)

def safe_user_id(update: Update) -> Optional[int]:
    """Safely get user ID from update"""
    user = getattr(update, "effective_user", None)
    return getattr(user, "id", None) if user else None

def safe_user_name(update: Update) -> str:
    """Safely get user name with fallback"""
    user = getattr(update, "effective_user", None)
    if not user:
        return "Someone"
    return getattr(user, "first_name", None) or getattr(user, "username", None) or "Someone"
