
# premium.py
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, Update
from telegram.ext import ContextTypes

# Callbacks
CB_PREMIUM        = "prem:home"
CB_PREM_REF       = "prem:ref"
CB_PREM_PAY_PREFIX = "prem:pay:"   # <- important: a colon at the end
CB_PREM_REDEEM3   = "prem:redeem3"

# Product catalog (pack_id -> title, description, stars, duration_days)
STAR_PACKS = {
    "w1": ("LuvHive Premium — 1 week",   "1 week of Premium",   100,   7),
    "m1": ("LuvHive Premium — 1 month",  "1 month of Premium",  250,  30),
    "m6": ("LuvHive Premium — 6 months", "6 months of Premium", 600, 180),
    "y1": ("LuvHive Premium — 12 months","12 months of Premium",1000, 365),
}

def premium_text() -> str:
    return (
        "🔥 *Premium Plan Benefits*\n\n"
        "Unlock the full experience with our Premium Plan! Here's what you get:\n\n"
        "1. 🎯 *Search Based on Partner's Age:* Find partners within your preferred age range.\n"
        "2. 🧲 *Interest-Based Matching:* Get matched with people who share similar interests.\n"
        "3. 💞 *Gender-Based Matching:* Choose whether you want to match with boys or girls.\n"
        "4. ❌ *Ad-Free Experience:* Enjoy uninterrupted conversations without any ads.\n"
        "5. 📸 *Send Photos, GIFs, and Videos:* Share rich media to make chats more expressive and fun.\n"
        "6. 🚀 *Priority Matching Channel:* Matching efficiency ×10.\n"
        "7. 🔐 *Secret Chat:* Start private conversations with a timer and self-destructing messages.\n"
        "   • To start Secret Chat, type /secret in chat.\n"
        "   • Your partner must *accept* the invite.\n"
        "   • If they *decline*, normal chat will continue.\n\n"
        "👇 *Please select the duration to purchase.* The longer the duration, the greater the discount!"
    )

def premium_kb() -> InlineKeyboardMarkup:
    # Labels to match your screen
    rows = [
        [InlineKeyboardButton("100 Stars / $1.99 — 1 week",  callback_data=f"{CB_PREM_PAY_PREFIX}w1")],
        [InlineKeyboardButton("250 Stars / $3.99 — 1 month", callback_data=f"{CB_PREM_PAY_PREFIX}m1")],
        [InlineKeyboardButton("600 Stars / $9.99 — 6 months",callback_data=f"{CB_PREM_PAY_PREFIX}m6")],
        [InlineKeyboardButton("1000 Stars / $19.99 — 12 months", callback_data=f"{CB_PREM_PAY_PREFIX}y1")],
        [InlineKeyboardButton("🎟 Redeem 3 days (500 coins)", callback_data=CB_PREM_REDEEM3)],
        [InlineKeyboardButton("ℹ️ Learn more about Secret Chat", callback_data="prem:secretinfo")],
        [InlineKeyboardButton("🎁 Earn VIP for free", callback_data=CB_PREM_REF)],
    ]
    return InlineKeyboardMarkup(rows)

def referral_text(uid: int, bot_username: str) -> str:
    link = f"https://t.me/{bot_username}?start=ref_{uid}"
    return (
        "Invite friends and get free ⭐ Premium!\n\n"
        f"Your personal link:\n{link}"
    )

def referral_kb(uid: int, bot_username: str) -> InlineKeyboardMarkup:
    link = f"https://t.me/{bot_username}?start=ref_{uid}"
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Share link", url=link)]])

def stars_invoice_data(pack_id: str, uid: int):
    """
    Build invoice parameters for Telegram Stars.
    """
    title, desc, stars, _days = STAR_PACKS[pack_id]
    payload = f"stars-premium:{pack_id}:{uid}"     # will be read on payment success
    prices = [LabeledPrice("Premium", stars)]      # amount in Stars (XTR)
    return title, desc, payload, prices

# -------- Secret Chat Info Handler --------
async def on_secret_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🔐 *Secret Chat (Premium Feature)*\n\n"
        "• Start with `/secret` inside any active chat.\n"
        "• Your partner must accept the invite.\n"
        "• If they decline, normal chat continues.\n"
        "• Secret Chat comes with:\n"
        "   – ⏱ Timer (15/30/45/60 minutes)\n"
        "   – 💣 Self-destruct for messages (5/10/15/20 sec)\n"
        "   – 🚫 Forwarding disabled\n"
        "   – 📷 Media sending only if you have Premium\n"
        "   – ⚠️ Screenshots cannot be blocked — share responsibly\n\n"
        "End options:\n"
        "• `/endsecret` – end Secret Chat only (return to normal)\n"
        "• `/stop` – end chat completely\n"
        "• `/report` – report your partner anytime\n\n"
        "Stay safe & enjoy private chats!",
        parse_mode="Markdown"
    )
