# menu.py
from telegram import ReplyKeyboardMarkup, KeyboardButton

# Labels
BTN_FIND_PARTNER = "💕⚡ Find a Partner"
BTN_MATCH_GIRLS  = "💖👩 Match with girls"
BTN_MATCH_BOYS   = "💙👨 Match with boys"
BTN_MY_PROFILE   = "✨👤 My Profile"
BTN_SETTINGS     = "💫⚙️ Settings"
BTN_PREMIUM      = "💎✨ Premium"
BTN_FRIENDS      = "💞👥 Friends"
BTN_PUBLIC_FEED  = "🌹🌍 Public Feed"
BTN_FUN_GAMES    = "💃🎮 Fun & Games"

# Backward-compatibility aliases
BTN_FIND    = BTN_FIND_PARTNER
BTN_PROFILE = BTN_MY_PROFILE

# Home menu callback constants
CB_HOME_PREFIX  = "home"
CB_HOME_FRIENDS = f"{CB_HOME_PREFIX}:friends"
CB_HOME_BACK    = f"{CB_HOME_PREFIX}:back"
CB_HOME_FHELP   = f"{CB_HOME_PREFIX}:friends_help"

def main_menu_kb() -> ReplyKeyboardMarkup:
    """Bottom reply keyboard with all buttons (5x2 layout)."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_FIND_PARTNER), KeyboardButton(BTN_MATCH_GIRLS)],
            [KeyboardButton(BTN_MATCH_BOYS),   KeyboardButton(BTN_FRIENDS)],
            [KeyboardButton(BTN_PUBLIC_FEED),  KeyboardButton(BTN_MY_PROFILE)],
            [KeyboardButton(BTN_SETTINGS),     KeyboardButton(BTN_PREMIUM)],
            [KeyboardButton(BTN_FUN_GAMES)],
        ],
        resize_keyboard=True
    )