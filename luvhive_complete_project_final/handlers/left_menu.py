
# handlers/left_menu.py
from __future__ import annotations
from typing import List, Tuple, Dict
from telegram import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from telegram.ext import Application

# ---------- Command text (EN + HI) ----------
EN_CMDS: List[Tuple[str, str]] = [
    ("search",     "🔎 Finds a random user"),
    ("next",       "➡️ Ends the current chat and finds a new match"),
    ("quit",       "🛑 Ends the conversation"),
    ("link",       "🔗 Send Telegram profile URL to your partner"),
    ("lang",       "🌐 Bot language"),
    ("cancel",     "🗑️ Cancel operation"),
    ("settings",   "⚙️ Change your gender, age and other settings"),
    ("friends",    "👥 Show friends & invite"),
    ("help",       "❓ To know about the bot"),
    ("rules",      "📜 Do and don't of the bot"),
    ("terms",      "📄 Terms and conditions of the bot"),
    ("premium",    "💎 Buy/Manage VIP"),
    ("myid",       "🪪 View your telegram account ID"),
    ("paysupport", "💰 Payment support"),
    ("game",       "🎮 Play mini games (Truth, Dare, WYR, NHIE, KMK, This/That)"),
    ("truth",      "🤔 Receive a Truth question"),
    ("dare",       "🎲 Receive a Dare challenge"),
    ("wyr",        "🌀 Would You Rather prompt"),
    ("nhie",       "🙅 Never Have I Ever"),
    ("kmk",        "💋 Kiss, Marry, Kill"),
    ("tot",        "⚖️ This or That"),
    ("promocode",  "🎫 Use a promo code for premium packages"),
    ("privacy",    "🔒 Privacy policy and data handling"),
    ("my_data",    "📊 View your stored data summary"),
]

HI_CMDS: List[Tuple[str, str]] = [
    ("search",     "🔎 यादृच्छिक उपयोगकर्ता खोजें"),
    ("next",       "➡️ वर्तमान चैट समाप्त कर नई जोड़ी ढूँढें"),
    ("quit",       "🛑 बातचीत समाप्त करें"),
    ("link",       "🔗 अपना टेलीग्राम प्रोफ़ाइल लिंक पार्टनर को भेजें"),
    ("lang",       "🌐 बॉट भाषा"),
    ("cancel",     "🗑️ सभी क्रियाएँ रद्द करें"),
    ("settings",   "⚙️ अपना लिंग, उम्र और अन्य सेटिंग्स बदलें"),
    ("friends",    "👥 मित्र सूची और आमंत्रण"),
    ("help",       "❓ बॉट के बारे में जानें"),
    ("rules",      "📜 बॉट के करने/न करने योग्य नियम"),
    ("terms",      "📄 बॉट की शर्तें और नियम"),
    ("premium",    "💎 VIP खरीदें/प्रबंधित करें"),
    ("myid",       "🪪 अपना टेलीग्राम अकाउंट ID देखें"),
    ("paysupport", "💰 भुगतान सहायता"),
    ("game",       "🎮 मिनी गेम (सच, डेयर, WYR, NHIE, KMK, This/That)"),
    ("truth",      "🤔 सच (Truth) प्रश्न"),
    ("dare",       "🎲 डेयर (Dare) चुनौती"),
    ("wyr",        "🌀 'Would You Rather' प्रश्न"),
    ("nhie",       "🙅 कभी मैंने नहीं किया"),
    ("kmk",        "💋 किस, मैरी, किल"),
    ("tot",        "⚖️ यह या वह"),
    ("promocode",  "🎫 प्रीमियम पैकेज के लिए प्रोमो कोड उपयोग करें"),
    ("privacy",    "🔒 गोपनीयता नीति और डेटा प्रबंधन"),
    ("my_data",    "📊 अपना संग्रहीत डेटा सारांश देखें"),
]

LANG_MAP: Dict[str, List[Tuple[str, str]]] = {"en": EN_CMDS, "hi": HI_CMDS}

# ---------- internal helpers ----------
async def _apply_default(app: Application) -> None:
    cmds = [BotCommand(c, d) for c, d in EN_CMDS]
    await app.bot.set_my_commands(cmds, scope=BotCommandScopeDefault())

async def _apply_for_user(app: Application, chat_id: int, lang: str) -> None:
    items = LANG_MAP.get(lang, EN_CMDS)
    cmds = [BotCommand(c, d) for c, d in items]
    await app.bot.set_my_commands(cmds, scope=BotCommandScopeChat(chat_id))

# ---------- public API ----------
def register_left_menu(app: Application) -> None:
    """
    Safe: do not touch the event loop here (prevents 'no running loop' error).
    We hook into post_init *when available*, otherwise we do nothing and let
    /fixmenu (left_menu_handlers) refresh on demand.
    """
    async def _on_startup(_app: Application) -> None:
        await _apply_default(_app)

    hook = getattr(app, "post_init", None)
    if isinstance(hook, list):
        hook.append(_on_startup)   # will run after Application starts

async def set_user_lang_menu(app: Application, chat_id: int, lang: str) -> None:
    await _apply_for_user(app, chat_id, lang)

async def set_default_menu(app: Application) -> None:
    await _apply_default(app)

def register(app: Application) -> None:
    """Wrapper function for main.py import compatibility."""
    return register_left_menu(app)
