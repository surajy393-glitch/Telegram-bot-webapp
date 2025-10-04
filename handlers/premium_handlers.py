
# handlers/premium_handlers.py
from __future__ import annotations

from telegram import Update, LabeledPrice
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes, CallbackQueryHandler, MessageHandler,
    PreCheckoutQueryHandler, filters,
)

from premium import (
    CB_PREMIUM, CB_PREM_REF, CB_PREM_PAY_PREFIX, CB_PREM_REDEEM3,
    premium_text, premium_kb, referral_text, referral_kb,
    stars_invoice_data, STAR_PACKS
)
from registration import set_is_premium, set_premium_until, redeem_premium_with_coins

# Map pack_id -> (title, price_stars, days)
GIFT_PACKS = {
    "w1": ("LuvHive Premium — 1 week (gift)", 100, 7),
    "m1": ("LuvHive Premium — 1 month (gift)", 250, 30),
}

async def send_gift_invoice(update, context, payer_id: int, target_id: int, pack_id: str):
    if pack_id not in GIFT_PACKS:
        raise ValueError("Invalid pack")

    title, stars, days = GIFT_PACKS[pack_id]
    payload = f"gift-premium:{pack_id}:{target_id}"

    prices = [LabeledPrice(label=title, amount=stars)]  # PTB v20+

    await context.bot.send_invoice(
        chat_id=payer_id,
        title=title,
        description=f"Gift Premium to user {target_id}",
        payload=payload,
        provider_token="",   # Telegram Stars → empty string
        currency="XTR",      # Stars currency code
        prices=prices,
    )
from datetime import datetime, timedelta, timezone

# ---------- NEW: payment click -> send Stars invoice ----------

async def handle_payment_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback from premium buttons → send a Stars invoice for the correct pack.
    """
    q = update.callback_query
    data = q.data or ""
    # data looks like "prem:pay:w1" or "prem:pay:m1" etc.
    if not data.startswith(CB_PREM_PAY_PREFIX):
        await q.answer("Unknown product", show_alert=True)
        return

    pack_id = data[len(CB_PREM_PAY_PREFIX):]   # -> "w1" / "m1" / "m6" / "y1"
    if pack_id not in STAR_PACKS:
        await q.answer("Unknown plan", show_alert=True)
        return

    await q.answer()
    title, desc, payload, prices = stars_invoice_data(pack_id, update.effective_user.id)

    await context.bot.send_invoice(
        chat_id=q.message.chat_id,
        title=title,
        description=desc,
        payload=payload,          # checked in on_successful_payment
        provider_token="",        # Stars do not need provider token
        currency="XTR",
        prices=prices,
        start_parameter=f"prem_{pack_id}",
    )

# ---------- REQUIRED BY TELEGRAM PAYMENTS ----------

async def precheckout_ok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # must always answer pre_checkout_query
    await update.pre_checkout_query.answer(ok=True)

async def on_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Fired after Telegram confirms the payment.
    Here we mark the user as premium in your DB.
    """
    sp = update.message.successful_payment
    payload = (sp.invoice_payload or "").strip()

    # GIFT flow
    if payload.startswith("gift-premium:"):
        _, pack_id, target_str = payload.split(":")
        target_id = int(target_str)
        # days from GIFT_PACKS (fallback reasonable default)
        days = GIFT_PACKS.get(pack_id, ("", 0, 7))[2]
        try:
            # ✅ boolean flag for back-compat
            set_is_premium(target_id, True)
            
            # ✅ time-bound expiry
            expires_at = datetime.now(timezone.utc) + timedelta(days=days)
            set_premium_until(target_id, expires_at)
            
            await update.message.reply_text("🎁 Gift successful! Premium delivered.", quote=True)
            # Notify recipient
            try:
                await context.bot.send_message(target_id, f"🎁 You were gifted Premium for {days} days! Enjoy ❤️")
            except Exception:
                pass
        except Exception as e:
            await update.message.reply_text(f"⚠️ Payment received but gift failed: {e}", quote=True)
        return

    # Default (existing SELF purchase flow)
    uid = update.effective_user.id

    # Parse our payload: "stars-premium:{pack_id}:{uid}"
    if payload.startswith("stars-premium:"):
        parts = payload.split(":")
        if len(parts) >= 3 and parts[2].isdigit():
            uid = int(parts[2])

    try:
        # ✅ boolean flag for back-compat
        set_is_premium(uid, True)

        # ✅ time-bound expiry
        if payload.startswith("stars-premium:"):
            parts = payload.split(":")
            if len(parts) >= 2:
                pack_id = parts[1]
                if pack_id in STAR_PACKS:
                    duration_days = STAR_PACKS[pack_id][3]
                    expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
                    set_premium_until(uid, expires_at)
        
        await update.message.reply_text("✨ Premium activated! Enjoy ❤️", quote=True)
    except Exception:
        # last resort: still try current user
        try:
            set_is_premium(update.effective_user.id, True)
            await update.message.reply_text("✨ Premium activated! Enjoy ❤️", quote=True)
        except Exception:
            await update.message.reply_text("Payment received but activation failed. Please contact support.", quote=True)

# ---------- UI HANDLERS ----------

async def show_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show premium options when user clicks Premium button from main menu."""
    try:
        await update.message.reply_text(
            premium_text(), 
            reply_markup=premium_kb(), 
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        await update.message.reply_text(
            "💎 Premium features include interest/gender matching and more.\n\n"
            "Contact @Luvhivehelpbot for premium subscription."
        )

async def open_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        premium_text(),
        reply_markup=premium_kb(),
        parse_mode=ParseMode.MARKDOWN,
    )

async def open_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = update.effective_user.id
    bot_username = getattr(context.bot, "username", None) or "Luvhivebot"
    await q.edit_message_text(
        referral_text(uid, bot_username),
        reply_markup=referral_kb(uid, bot_username),
        parse_mode=ParseMode.HTML,
    )

async def on_prem_redeem3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    ok, new_bal, new_until = redeem_premium_with_coins(uid, need=500, days=3)
    if not ok:
        try:
            await q.edit_message_text("❌ Not enough coins. You need 500 coins to redeem 3 days Premium.")
        except Exception:
            pass
        return

    # success
    txt = "✅ Premium unlocked for 3 days!\n"
    if new_until:
        txt += f"🗓 Active until: {new_until:%Y-%m-%d %H:%M} UTC\n"
    txt += f"💰 New balance: {new_bal}"
    try:
        await q.edit_message_text(txt)
    except Exception:
        pass


# ---------- REGISTER ----------

def register(app):
    # premium UI
    app.add_handler(CallbackQueryHandler(open_premium, pattern=f"^{CB_PREMIUM}$"))
    app.add_handler(CallbackQueryHandler(handle_payment_click, pattern=f"^{CB_PREM_PAY_PREFIX}.+"))
    app.add_handler(CallbackQueryHandler(open_referral, pattern=f"^{CB_PREM_REF}$"))
    app.add_handler(CallbackQueryHandler(on_prem_redeem3, pattern=f"^{CB_PREM_REDEEM3}$"), group=-1)

    # Secret Chat info handler
    from premium import on_secret_info
    app.add_handler(CallbackQueryHandler(on_secret_info, pattern="^prem:secretinfo$"), group=0)

    # payments (Stars) MUST run first
    app.add_handler(PreCheckoutQueryHandler(precheckout_ok), group=-1)
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment), group=-1)
