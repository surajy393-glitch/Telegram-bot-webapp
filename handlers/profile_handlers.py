from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone

from telegram import Update, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, ContextTypes, CallbackQueryHandler, MessageHandler, filters, PreCheckoutQueryHandler
from telegram.constants import ParseMode
from telegram.error import TelegramError, BadRequest

import registration as reg
from profile import (
    profile_text, profile_keyboard, language_keyboard,
    set_language, reset_ratings_for, _conn,
    CB_PROFILE, CB_LANG, CB_RESET, CB_COINS,
    CB_BIO, CB_PHOTO_SET, CB_PHOTO_DEL,
)
# REMOVED: gender_keyboard, set_gender, set_age, CB_GENDER, CB_AGE 
# Gender and age changes no longer allowed for security
from menu import BTN_MY_PROFILE as BTN_PROFILE

# Stars purchase for "Reset ratings"
RESET_PAYLOAD = "reset_ratings_10stars"
RESET_PRICE_STARS = 10  # stars

# ---------------- Admin parsing (robust) ----------------
RAW_ADMINS = os.getenv("ADMIN_IDS", "1437934486 647778438")
ADMIN_IDS = {int(x) for x in re.findall(r"\d+", RAW_ADMINS)}

def _is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

# ---------------- Safe edit helper ----------------
async def _safe_edit_or_send(q, text, **kwargs):
    """Try to edit the button message; if that fails, send a fresh message."""
    try:
        # prefer editing when possible (keeps UI compact)
        await q.edit_message_text(text, **kwargs)
    except Exception:
        # no editable text (e.g., previous was photo/caption) OR same text -> just send
        await q.message.reply_text(text, **kwargs)

# ---------------- Cooldown helper ----------------
def _too_soon(ts) -> tuple[bool, str]:
    """Return (True, remaining_text) if next change not allowed yet."""
    if not ts:
        return (False, "")
    now = datetime.now(timezone.utc)
    if getattr(ts, "tzinfo", None) is None:
        ts = ts.replace(tzinfo=timezone.utc)
    next_ok = ts + timedelta(days=7)
    if now >= next_ok:
        return (False, "")
    left = next_ok - now
    days = left.days
    hours = (left.seconds // 3600)
    if days > 0:
        return (True, f"{days}d {hours}h")
    return (True, f"{hours}h")

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile with photo if exists."""
    uid = update.effective_user.id
    username = update.effective_user.username

    # Get profile text and keyboard
    text = profile_text(uid, username)
    keyboard = profile_keyboard()

    # Check if user has photo
    photo_file = reg.get_photo_file(uid)

    if update.callback_query:
        # From inline button
        q = update.callback_query
        
        try:
            if photo_file:
                # Try to edit caption if message has photo
                await q.message.edit_caption(
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                # Try to edit text if no photo
                await q.message.edit_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
        except Exception:
            # If editing fails, send new message
            if photo_file:
                try:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=photo_file,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
                except Exception:
                    await q.message.reply_text(
                        text=text,
                        reply_markup=keyboard,
                        parse_mode=ParseMode.HTML
                    )
            else:
                await q.message.reply_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
        
        await q.answer()
    else:
        # From menu button
        if photo_file:
            try:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=photo_file,
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                await update.message.reply_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )

# REMOVED: on_gender_open() - Gender changes no longer allowed for security

# REMOVED: on_gender_set() - Gender changes no longer allowed for security

# REMOVED: on_age_open() - Age changes no longer allowed for security

# REMOVED: on_age_text() - Age changes no longer allowed for security

async def on_lang_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open language selection (works for photo+caption or plain text)."""
    q = update.callback_query
    kb = language_keyboard()

    # Try editing caption first (if the message is a photo), then text; else send new.
    try:
        await q.message.edit_caption(
            caption="Choose your language:",
            reply_markup=kb,
            parse_mode=None
        )
    except BadRequest:
        try:
            await q.message.edit_text(
                "Choose your language:",
                reply_markup=kb,
                parse_mode=None
            )
        except BadRequest:
            # If neither can be edited (e.g., previous was not editable), send a fresh message
            await q.message.reply_text("Choose your language:", reply_markup=kb)

    await q.answer()

async def on_lang_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user language."""
    uid = update.effective_user.id
    lang_value = update.callback_query.data.split(":", 1)[1]

    try:
        set_language(uid, lang_value)
        await update.callback_query.answer("✅ Language updated!")
        await show_profile(update, context)
    except Exception as e:
        await update.callback_query.answer(f"❌ Error: {e}")

async def on_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset ratings for stars."""
    uid = update.effective_user.id

    # Create invoice for 10 stars
    title = "Reset Your Ratings"
    description = "Clear all ratings received from other users"
    payload = RESET_PAYLOAD
    currency = "XTR"  # Telegram Stars
    prices = [LabeledPrice("Reset Ratings", RESET_PRICE_STARS)]

    await update.callback_query.answer()
    await context.bot.send_invoice(
        chat_id=uid,
        title=title,
        description=description,
        payload=payload,
        provider_token="",  # Empty for stars
        currency=currency,
        prices=prices,
    )

async def on_precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pre-checkout query."""
    query = update.pre_checkout_query
    if query.invoice_payload == RESET_PAYLOAD:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Invalid payment")

async def on_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment."""
    payment = update.message.successful_payment
    if payment.invoice_payload == RESET_PAYLOAD:
        uid = update.effective_user.id
        reset_ratings_for(uid)
        await update.message.reply_text("✅ Ratings reset successfully!")

async def on_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show coins panel with balance and earning instructions."""
    uid = update.effective_user.id
    bal = reg.get_coins(uid)
    text = (
        f"💰 *Coins Panel*\n\n"
        f"Balance: {bal}\n\n"
        "⭐ *Buy Coins*\n"
        "Use Stars to purchase bundles (coming soon).\n\n"
        "🎁 *Earn Free Coins*\n"
        "• Login daily → `/daily` = +10 coins\n"
        "• Invite friends → `/ref` = +50 coins each\n"
        "• Feedback / events\n\n"
        "✨ *500 coins = 3 days Premium*\n\n"
        "📖 *Commands*\n"
        "`/tip <amount>` → gift coins to partner\n"
        "`/love` → send Flowers (10), Dessert (20), Teddy (30)\n\n"
        "Flowers 🌹 = 10 coins\n"
        "Dessert 🍰 = 20 coins\n"
        "Teddy 🧸 = 30 coins"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟 Redeem 3 days (500 coins)", callback_data="prem:redeem3")],
        [InlineKeyboardButton("⬅ Back", callback_data=CB_PROFILE)]
    ])

    if update.callback_query:
        await update.callback_query.answer()
        q = update.callback_query
        await _safe_edit_or_send(q, text, reply_markup=kb, parse_mode=None)
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode=None)

async def on_bio_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start bio editing process."""
    # Use text framework to claim text input
    from handlers.text_framework import claim_or_reject, make_cancel_kb
    ok = await claim_or_reject(update, context, "profile", "bio_edit", ttl_minutes=5)
    if not ok:
        return
        
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "✏️ Please send your new bio (up to 200 characters):",
        reply_markup=make_cancel_kb()
    )

from handlers.text_framework import requires_state, clear_state

@requires_state(feature="profile", mode="bio_edit")
async def on_bio_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bio text input."""
    uid = update.effective_user.id
    raw_bio = (update.message.text or "").strip()
    
    # Use comprehensive input validation
    from utils.input_validation import validate_and_sanitize_input
    is_valid, error_msg, bio_text = validate_and_sanitize_input(raw_bio, 'bio')
    if not is_valid:
        return await update.message.reply_text(f"❌ {error_msg}")

    reg.set_bio(uid, bio_text)
    clear_state(context)

    await update.message.reply_text("✅ Bio saved!")
    await show_profile(update, context)

async def on_photo_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start photo setting process - FIXED VERSION."""
    uid = update.effective_user.id
    context.user_data["prof_awaiting_photo"] = True

    await update.callback_query.answer()
    await update.callback_query.message.reply_text("📷 Please send a photo for your profile:")

async def on_photo_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo upload - FIXED VERSION."""
    if not context.user_data.get("prof_awaiting_photo"):
        return

    if not update.message.photo:
        return await update.message.reply_text("⚠️ Please send a valid photo.")

    uid = update.effective_user.id
    photo = update.message.photo[-1]  # Get highest resolution
    file_id = photo.file_id

    # Save to DB
    reg.set_photo_file(uid, file_id)
    context.user_data["prof_awaiting_photo"] = False

    await update.message.reply_text("✅ Profile photo saved!")

    # Show preview of saved photo
    try:
        await context.bot.send_photo(
            chat_id=uid,
            photo=file_id,
            caption="👤 This is your current profile photo."
        )
    except Exception:
        pass

    # Show updated profile
    await show_profile(update, context)

async def on_photo_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete profile photo."""
    uid = update.effective_user.id
    reg.clear_photo_file(uid)

    await update.callback_query.answer("✅ Profile photo removed!")
    await show_profile(update, context)

# ---------------- Entry router from profile keyboard ----------------
async def on_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data or ""
    uid = q.from_user.id

    if data == CB_PROFILE:
        return await show_profile(update, context)
    # REMOVED: Gender and age callback handlers - no longer allowed for security
    if data == CB_LANG:
        return await on_lang_open(update, context)
    if data.startswith(f"{CB_LANG}:"):
        return await on_lang_set(update, context)
    if data == CB_RESET:
        return await on_reset(update, context)
    if data == CB_COINS or data.endswith(":coins"):
        return await on_coins(update, context)
    if data == CB_PHOTO_SET:
        return await on_photo_set(update, context)
    if data == CB_PHOTO_DEL:
        return await on_photo_delete(update, context)

# ---------------- Register into Application ----------------
def register(app: Application):
    # REMOVED: Age text handler - age changes no longer allowed for security

    # Profile photo handler with highest priority to catch photos meant for profile
    app.add_handler(MessageHandler(filters.PHOTO, on_photo_receive), group=-2)

    # Bio handler removed - bio editing no longer available in profile

    # Open via button
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_PROFILE}$"), show_profile), group=-1)

    # Profile callbacks with high priority pattern matching - handles ALL prof* patterns
    app.add_handler(CallbackQueryHandler(on_profile_callback, pattern=r"^prof"), group=-1)

    # Payment handlers
    app.add_handler(PreCheckoutQueryHandler(on_precheckout), group=0)
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment), group=0)