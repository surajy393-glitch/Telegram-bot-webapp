
from telegram.ext import MessageHandler, filters, ContextTypes, ApplicationHandlerStop
from telegram import Update
from handlers.text_framework import FEATURE_KEY, MODE_KEY
from state import get_qa, get_poll

try:
    from menu import (
        BTN_FIND_PARTNER, BTN_MATCH_GIRLS, BTN_MATCH_BOYS, BTN_MY_PROFILE,
        BTN_SETTINGS, BTN_PREMIUM, BTN_FRIENDS, BTN_PUBLIC_FEED, BTN_FUN_GAMES
    )
except Exception:
    BTN_FIND_PARTNER = "💕⚡ Find a Partner"
    BTN_MATCH_GIRLS  = "💖👩 Match with girls"
    BTN_MATCH_BOYS   = "💙👨 Match with boys"
    BTN_MY_PROFILE   = "✨👤 My Profile"
    BTN_SETTINGS     = "💫⚙️ Settings"
    BTN_PREMIUM      = "💎✨ Premium"
    BTN_FRIENDS      = "💞👥 Friends"
    BTN_PUBLIC_FEED  = "🌹🌍 Public Feed"
    BTN_FUN_GAMES    = "💃🎮 Fun & Games"

GROUP = 0  # run before legacy

ALLOW_TEXTS = {
    BTN_FIND_PARTNER, BTN_MATCH_GIRLS, BTN_MATCH_BOYS, BTN_MY_PROFILE,
    BTN_SETTINGS, BTN_PREMIUM, BTN_FRIENDS, BTN_PUBLIC_FEED, BTN_FUN_GAMES,
    "❌ Cancel", "Cancel", "⬅ Back", "⬅️ Back", "⬅ Back to Menu", "⬅️ Back to Menu"
}

# Flags that should bypass firewall blocking
DONT_BLOCK_FLAGS = (
    "awaiting_dare_submission", "awaiting_dare_text",
    "awaiting_confession_text", "awaiting_confession_reply_text"
)

def _is_allowed_text(t: str) -> bool:
    if not t:
        return False
    return t.strip() in ALLOW_TEXTS

async def _stop_if_owned(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    
    # Check if dare submission is active - allow it to pass
    if any(context.user_data.get(f) for f in DONT_BLOCK_FLAGS):
        return  # Dare submission text expected - allow it to pass
    
    # CRITICAL FIX: Check if any text framework feature is expecting text input
    # This includes advanced_dare, vault, profile bio, confession, etc.
    current_feature = context.user_data.get(FEATURE_KEY)
    current_mode = context.user_data.get(MODE_KEY)
    if current_feature and current_mode:
        # Text framework system is active and expecting input - allow it to pass
        return
    
    # Check if QA mode is active - allow it to pass to qa_text_sink
    if msg and msg.from_user:
        st = get_qa(msg.from_user.id)
        if st and st.get("feature") == "qa":
            return  # QA is expecting text -> allow it to pass to qa_text_sink
        
        # Check if POLL mode is active - allow it to pass to poll_text_sink
        stp = get_poll(msg.from_user.id)
        if stp and stp.get("feature") == "poll":
            return  # Poll is expecting text -> allow it to pass to poll_text_sink
    
    # If some feature owns input, only block non-whitelisted text/media
    if not context.user_data.get(FEATURE_KEY):
        return
    if msg and (msg.text or msg.caption):
        if _is_allowed_text(msg.text or msg.caption):
            return  # let menu/navigation texts pass
    raise ApplicationHandlerStop

def register(app):
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _stop_if_owned), group=GROUP)
    media = (filters.PHOTO | filters.VIDEO | filters.VOICE |
             filters.AUDIO | filters.ANIMATION | filters.Document.ALL)
    app.add_handler(MessageHandler(media, _stop_if_owned), group=GROUP)
