# handlers/funhub.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from utils.feature_texts import NAUGHTY_WYR_TEXT, DARE_TEXT, VAULT_TEXT, FANTASY_TEXT
import re

# Button text ko central source se lo (menu.py)
try:
    from menu import BTN_FUN_GAMES
except Exception:
    BTN_FUN_GAMES = "💃🎮 Fun & Games"

async def funhub_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main Fun & Games menu - high priority handler"""
    kb = [
        [InlineKeyboardButton("🌀 Confession Roulette", callback_data="fun:open:conf")],
        [InlineKeyboardButton("🤭 Naughty WYR (18+)", callback_data="fun:open:nwyr")],
        [InlineKeyboardButton("🚨 Advanced Dare System", callback_data="fun:open:dare")],
        [InlineKeyboardButton("😏 Blur-Reveal Vault", callback_data="fun:open:vault")],
        [InlineKeyboardButton("🔥 Fantasy Match (Premium)", callback_data="fun:open:fant")],
        [InlineKeyboardButton("📖 Midnight University", callback_data="fun:open:muc")],
    ]

    text = "🎮 *Fun & Games Hub*\nChoose your adventure from 6 thrilling experiences!"

    # Handle both message and callback query
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        await q.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def show_confession_main_menu_with_time_context(query, context, user_id: int):
    """Show the main confession menu with time-appropriate messaging (no 'evening' for button clicks)"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from handlers.confession_roulette import get_confession_stats, get_live_activity_stats

    keyboard = [
        [
            InlineKeyboardButton("📝 Confess", callback_data="confession_menu:confess"),
            InlineKeyboardButton("📊 My Stats", callback_data="confession_menu:stats")
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="confession_menu:leaderboard")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Get quick stats for the header
    user_stats = get_confession_stats(user_id)
    activity = get_live_activity_stats()

    # Time-neutral message (no "evening" reference for button clicks)
    message = f"""🏠 **YOUR ANONYMOUS HOME** 🏠
📖 Welcome to your safe space for secrets & daily diary!

🔥 **LIVE NOW:**
• {activity['active_players']} people sharing their hearts
• {activity['confessions_today']} stories shared today
• Your current streak: {user_stats['current_streak']} days

💫 **What would you like to do?**
Choose below to confess, check your stats, or see the leaderboard!"""

    await query.message.reply_text(message, reply_markup=reply_markup)

async def get_tempting_confession_interface(user_id: int) -> str:
    """Create an exciting, tempting confession interface for button clicks"""
    try:
        # Import here to avoid circular imports
        from handlers.confession_roulette import get_live_activity_stats, get_confession_stats

        activity = get_live_activity_stats()
        user_stats = get_confession_stats(user_id)

        # Create mysterious, tempting interface
        messages = [
            f"🎰 CONFESSION ROULETTE JACKPOT! 🎰\n🔥 {activity['active_players']} players are IN THE GAME right now!\n\n💀 Tonight someone will receive your darkest secret...\n🎯 Will it be your crush? Ex? Boss? Random stranger?\n\n🚨 DANGER ZONE:\n• Your confession vanishes into the void\n• No name, no trace, no evidence\n• Someone WILL read your deepest thoughts\n• They can reply back anonymously...\n\n💣 What's eating you inside? What would you NEVER say out loud?\n\n⚡ Ready? Type /confess to see live stats & drop your confession! 🎯",

            f"🌪️ CONFESSION TORNADO IS SPINNING! 🌪️\n\n👀 {activity['active_players']} people are watching... waiting...\n\n🔮 TONIGHT'S MYSTERY:\n• Someone will get your secret in their DM\n• They'll know your thoughts but not YOU\n• Your confession might blow their mind\n• Or break their heart... 💔\n\n🎭 ANONYMOUS POWER:\n• Say what you've NEVER said\n• Confess what you've hidden for years\n• Let out what's burning inside you\n\n🔥 Your secret is safe but your impact is REAL\n\n💥 Type /confess to enter the arena & drop your truth! ⚡",

            f"🎪 CONFESSION CARNIVAL IS OPEN! 🎪\n\n🎭 {activity['active_players']} masked players online NOW!\n\n🌙 TONIGHT'S THRILL:\n• Your words will haunt someone's dreams\n• They'll screenshot your confession\n• Wonder who you are for DAYS\n• Maybe fall in love with your mystery...\n\n💀 FORBIDDEN ZONE:\n• No filters, no limits\n• Pure raw truth only\n• What happens here stays anonymous\n• But someone WILL remember forever\n\n🎯 Type /confess to see leaderboards & drop your wildest confession! 🔥",

            f"🚨 CONFESSION EMERGENCY! 🚨\n\n⚡ {activity['active_players']} people need to hear YOUR truth!\n\n🌊 CONFESSION WAVE:\n• Your secret will create ripples\n• Someone will relate to your pain\n• Your words might save someone tonight\n• Or completely shock them...\n\n🔥 ANONYMOUS IMPACT:\n• Be the voice they needed to hear\n• Share what you've never shared\n• Your confession could go VIRAL\n• (but you'll stay invisible)\n\n💣 Type /confess to check your rank & drop your truth bomb! 🚀"
        ]

        # Rotate based on user ID for variety
        selected_message = messages[user_id % len(messages)]

        # Add personal touch if user has stats
        if user_stats['total_confessions'] > 0:
            selected_message += f"\n\n🏆 Your confession power: {user_stats['current_streak']} day streak"
        else:
            selected_message += f"\n\n✨ Your first confession could change everything..."

        return selected_message

    except Exception as e:
        print(f"❌ Error creating tempting interface: {e}")
        # Fallback exciting message
        return """🎰 CONFESSION ROULETTE IS SPINNING! 🎰

🌪️ Your deepest secret will land in someone's DM tonight...
🎭 They'll read it, react to it, maybe even reply...
💀 But they'll NEVER know it was you

🔥 What's burning inside you?
💣 What would you never say out loud?
🌙 What keeps you awake at night?

⚡ Type /confess to see your stats & drop your confession! 🎯"""

async def on_funhub_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "fun:open:conf":
        # Use new 3-button menu system for confession roulette
        user_id = q.from_user.id
        await show_confession_main_menu_with_time_context(q, context, user_id)
    
    elif q.data == "fun:open:fant":
        # Show the detailed Fantasy Match introduction (different from /fantasy command)
        await q.message.reply_text(FANTASY_TEXT, parse_mode="Markdown")
    
    elif q.data == "fun:open:muc":
        # Open Midnight University Chronicles main menu
        from handlers.midnight_university import muc_menu
        await muc_menu(update, context)

    else:
        # Other features use original texts
        mapping = {
            "fun:open:nwyr": NAUGHTY_WYR_TEXT,
            "fun:open:dare": DARE_TEXT,
            "fun:open:vault": VAULT_TEXT,
        }
        if q.data in mapping:
            await q.message.reply_text(mapping[q.data], parse_mode="Markdown")

def register(app):
    """
    Register Fun & Games handlers with HIGH PRIORITY (group=-10)
    Sabse pehle ye handler run hoga, koi firewall/middleware block nahi kar sakta
    """

    # CRITICAL FIX: Menu buttons MUST have HIGHEST PRIORITY to work before text framework handlers
    btn_pattern = rf"^\s*{re.escape(BTN_FUN_GAMES)}\s*$"
    app.add_handler(MessageHandler(filters.Regex(btn_pattern), funhub_menu), group=-25)

    # Command handlers for /fun and /funhub (debugging/quick access)
    app.add_handler(CommandHandler("fun", funhub_menu), group=-10)
    app.add_handler(CommandHandler("funhub", funhub_menu), group=-10)

    # Callback handlers for sub-menus
    app.add_handler(CallbackQueryHandler(on_funhub_cb, pattern="^fun:open:", block=False), group=-1)