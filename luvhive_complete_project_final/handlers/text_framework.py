# handlers/text_framework.py
from telegram.ext import ContextTypes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from functools import wraps
import logging
from datetime import timedelta

log = logging.getLogger("textfw")

FEATURE_KEY = "active_feature"
MODE_KEY    = "active_mode"
TIMEOUT_JOB = "active_text_timeout"

def make_cancel_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="textfw:cancel")]])

def set_state(context: ContextTypes.DEFAULT_TYPE, feature: str, mode: str, ttl_minutes: int = 5):
    """Claim text input state for a feature, with an auto-timeout."""
    ud = context.user_data
    ud[FEATURE_KEY] = feature
    ud[MODE_KEY]    = mode

    # cancel any previous timeout job
    j = ud.get(TIMEOUT_JOB)
    if j:
        try: 
            j.schedule_removal()
        except Exception: 
            pass

    jq = getattr(context, "job_queue", None)
    if jq:
        ud[TIMEOUT_JOB] = jq.run_once(_auto_clear_state, when=ttl_minutes * 60)

def clear_state(context: ContextTypes.DEFAULT_TYPE):
    """Release state and cancel timeout."""
    ud = context.user_data
    if not ud:  # Handle case where user_data is None
        return
    try:
        j = ud.get(TIMEOUT_JOB)
        if j:
            j.schedule_removal()
    except Exception:
        pass
    ud.pop(FEATURE_KEY, None)
    ud.pop(MODE_KEY, None)
    ud.pop(TIMEOUT_JOB, None)

async def handle_text_cancel(update, context):
    """Central cancel handler for textfw:cancel"""
    clear_state(context)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Text input cancelled.")
    else:
        await update.message.reply_text("❌ Text input cancelled.")

async def _auto_clear_state(context: ContextTypes.DEFAULT_TYPE):
    """Internal: timeout handler resets state."""
    try:
        chat_id = context.job.chat_id if context.job else None
    except Exception:
        chat_id = None
    
    # Safely clear state even if user_data is None
    try:
        clear_state(context)
    except Exception as e:
        log.warning(f"[textfw] clear_state failed in timeout: {e}")
        
    if chat_id:
        try:
            await context.bot.send_message(chat_id, "⌛ Text session expired. Start again if needed.")
        except Exception as e:
            log.warning(f"[textfw] timeout notify failed: {e}")

def requires_state(feature: str = None, mode: str = None):
    """Decorator: only run handler if user_data matches feature+mode."""
    def deco(func):
        @wraps(func)
        async def wrapper(update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            ud = context.user_data
            if feature and ud.get(FEATURE_KEY) != feature:
                return
            if mode and ud.get(MODE_KEY) != mode:
                return
            return await func(update, context, *args, **kwargs)
        return wrapper
    return deco

def is_in_feature(context: ContextTypes.DEFAULT_TYPE, feature: str) -> bool:
    return context.user_data.get(FEATURE_KEY) == feature

async def claim_or_reject(update, context, feature: str, mode: str, ttl_minutes: int = 5):
    """Try to claim input; if someone else holds it, gently reject."""
    ud = context.user_data
    current = ud.get(FEATURE_KEY)
    if current and current != feature:
        # someone else holds input (e.g., vault), reject to prevent swallowing
        try:
            msg = f"⚠ You are in another input flow. Tap Cancel there first."
            if update and update.effective_message:
                await update.effective_message.reply_text(msg, reply_markup=make_cancel_kb())
        except Exception: 
            pass
        return False
    set_state(context, feature, mode, ttl_minutes)
    return True