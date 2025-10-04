
# handlers/settings_handlers.py
import re
import random
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from menu import BTN_SETTINGS  # uses your existing constant
from settings import (
    CB_SETTINGS, CB_INT, CB_AGE, PREMIUM_POPUP,
    settings_text, settings_keyboard,
    age_keyboard, parse_age_range
)
from registration import open_interests_editor_from_settings, is_premium_user
import registration as reg

log = logging.getLogger("luvbot.verify")

# --- Helpers -------------------------------------------------

def _is_premium(ud, uid: int) -> bool:
    from registration import has_active_premium
    return has_active_premium(uid)

def _has_premium(uid: int) -> bool:
    # project में जो भी मौजूद हो उसे इस्तेमाल करे
    if hasattr(reg, "has_active_premium"):
        return reg.has_active_premium(uid)
    if hasattr(reg, "is_premium"):
        return reg.is_premium(uid)
    # fallback: premium_until > now
    try:
        until, _, _ = reg.get_ban_info(-1)  # dummy to import datetime if needed
    except Exception:
        pass
    try:
        pu = reg.get_premium_until(uid)
        from datetime import datetime, timezone
        return bool(pu and pu > datetime.utcnow().replace(tzinfo=timezone.utc))
    except Exception:
        return False

def _blocked_by_cooldown(uid: int) -> bool:
    """Check if user is in 3-day cooldown after rejection."""
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT verify_status, verify_at FROM users WHERE tg_user_id=%s", (uid,))
        row = cur.fetchone()
    if not row:
        return False
    status, ts = row
    if status == "rejected" and ts:
        return (datetime.utcnow() - ts) < timedelta(days=3)
    return False

async def _send_or_edit_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = settings_text(context.user_data)
    kb = settings_keyboard(context.user_data)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN
        )

# --- Public entry (used by Menu button) ----------------------

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    # Load current profile data from database
    from registration import get_profile
    profile = get_profile(uid)
    # Populate context.user_data with current profile data
    context.user_data["interests"] = profile.get("interests", set())
    context.user_data["is_verified"] = bool(profile.get("is_verified", False))
    context.user_data["is_premium"] = reg.has_active_premium(uid)
    # NEW:
    context.user_data["match_verified_only"] = reg.get_match_verified_only(uid)
    context.user_data["incognito"] = reg.get_incognito(uid)
    context.user_data["feed_notify"] = reg.get_feed_notify(uid)
    # ✅ CRITICAL: let Settings read DB
    context.user_data["user_id"] = uid
    # Add other settings defaults if needed
    context.user_data.setdefault("show_media", False)
    context.user_data.setdefault("age_pref", (18, 99))
    context.user_data.setdefault("allow_forward", False)
    
    await _send_or_edit_settings(update, context)

async def on_voice_verif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice verification submission."""
    if not update.message or not update.message.voice:
        return
    uid = update.effective_user.id

    # Read DB state
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT verify_status, verify_method FROM users WHERE tg_user_id=%s;", (uid,))
        row = cur.fetchone()

    if not row:
        return  # Silent: not in verification flow

    status, method = (row[0] or ""), (row[1] or "")
    log.info(f"[verify] on_voice uid={uid} status={status} method={method}")

    # Accept only if awaiting voice
    if status.lower() != "awaiting" or method.lower() != "voice":
        return  # Silent: let normal chat flow/relay handle the voice

    file_id = update.message.voice.file_id
    src_chat = update.effective_chat.id
    src_mid  = update.message.message_id

    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            UPDATE users
               SET verify_audio_file=%s,
                   verify_status='pending',
                   verify_src_chat=%s,
                   verify_src_msg=%s,
                   verify_at=NOW()
             WHERE tg_user_id=%s
        """, (file_id, src_chat, src_mid, uid))
        con.commit()

    try:
        del context.user_data["awaiting_voice_verif"]
    except KeyError:
        pass

    log.info(f"[verify] saved voice uid={uid} fid={file_id}")
    
    # Send success message and schedule auto-deletion after 5 seconds
    sent_message = await update.message.reply_text("✅ Voice submitted. We'll notify you after review.")
    
    # Schedule automatic deletion after 5 seconds
    import asyncio
    async def delete_voice_message():
        try:
            await asyncio.sleep(5)
            await context.bot.delete_message(
                chat_id=sent_message.chat_id,
                message_id=sent_message.message_id
            )
        except Exception as e:
            # Ignore errors (message might already be deleted by user)
            pass
    
    # Create background task for deletion
    asyncio.create_task(delete_voice_message())

async def on_photo_verif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle selfie verification submission."""
    if not update.message or not update.message.photo:
        return
    uid = update.effective_user.id

    # Read DB state
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT verify_status, verify_method FROM users WHERE tg_user_id=%s;", (uid,))
        row = cur.fetchone()

    if not row:
        return  # Silent: not in verification flow

    status, method = (row[0] or ""), (row[1] or "")
    log.info(f"[verify] on_photo uid={uid} status={status} method={method}")

    # Accept only if awaiting selfie
    if status.lower() != "awaiting" or method.lower() != "selfie":
        return  # Silent: this is a normal photo for chat; let relay handle it

    file_id = update.message.photo[-1].file_id
    src_chat = update.effective_chat.id
    src_mid  = update.message.message_id

    with reg._conn() as con, con.cursor() as cur:
        cur.execute("""
            UPDATE users
               SET verify_photo_file=%s,
                   verify_status='pending',
                   verify_src_chat=%s,
                   verify_src_msg=%s,
                   verify_at=NOW()
             WHERE tg_user_id=%s
        """, (file_id, src_chat, src_mid, uid))
        con.commit()

    try:
        del context.user_data["awaiting_selfie_verif"]
    except KeyError:
        pass

    log.info(f"[verify] saved selfie uid={uid} fid={file_id}")
    
    # Send success message and schedule auto-deletion after 5 seconds
    sent_message = await update.message.reply_text("✅ Selfie submitted. We'll notify you after review.")
    
    # Schedule automatic deletion after 5 seconds
    import asyncio
    async def delete_selfie_message():
        try:
            await asyncio.sleep(5)
            await context.bot.delete_message(
                chat_id=sent_message.chat_id,
                message_id=sent_message.message_id
            )
        except Exception as e:
            # Ignore errors (message might already be deleted by user)
            pass
    
    # Create background task for deletion
    asyncio.create_task(delete_selfie_message())

# --- Callback router -----------------------------------------

async def on_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    data = q.data or ""
    ud = context.user_data

    # --- Premium: toggle media ---
    if data == f"{CB_SETTINGS}:toggle_media":
        if not _is_premium(ud, q.from_user.id):
            return await q.answer(PREMIUM_POPUP, show_alert=True)
        ud["show_media"] = not ud.get("show_media", False)
        await q.answer("Updated.")
        return await _send_or_edit_settings(update, context)

    # --- Free: interests editor ---
    if data == f"{CB_SETTINGS}:edit_interests":
        return await open_interests_editor_from_settings(update, context)

    # --- Back to main Settings ---
    if data == f"{CB_SETTINGS}:back":
        return await _send_or_edit_settings(update, context)

    # --- Premium: partner age ---
    if data == f"{CB_SETTINGS}:choose_age":
        if not _is_premium(ud, q.from_user.id):
            return await q.answer(PREMIUM_POPUP, show_alert=True)
        return await q.edit_message_text(
            "👥 *Choose preferred partner age*:",
            reply_markup=age_keyboard(ud),
            parse_mode=ParseMode.MARKDOWN,
        )

    if data.startswith(f"{CB_AGE}:"):
        if not _is_premium(ud, q.from_user.id):
            return await q.answer(PREMIUM_POPUP, show_alert=True)

        # ✅ take only the last segment ("18-25")
        age_s = data.rsplit(":", 1)[1]
        lo, hi = parse_age_range(age_s)
        uid = q.from_user.id

        # Robust save (UPSERT)
        reg.set_age_pref(uid, lo, hi)

        # Optional: read-back verify
        saved_lo, saved_hi = reg.get_age_pref(uid)
        if (saved_lo, saved_hi) != (lo, hi):
            await q.answer(f"⚠️ Mismatch: tried {lo}-{hi}, saved {saved_lo}-{saved_hi}.", show_alert=True)
        else:
            await q.answer(f"✅ Age preference saved: {lo}-{hi}")

        ud["age_pref"] = (saved_lo, saved_hi)
        return await _send_or_edit_settings(update, context)

    # --- Premium: allow forwarding ---
    if data == f"{CB_SETTINGS}:toggle_forward":
        if not _is_premium(ud, q.from_user.id):
            return await q.answer(PREMIUM_POPUP, show_alert=True)
        uid = q.from_user.id
        new_val = not ud.get("allow_forward", False)
        reg.set_allow_forward(uid, new_val)
        ud["allow_forward"] = new_val
        await q.answer("Updated.")
        return await _send_or_edit_settings(update, context)

    # --- Verification menu ---
    if data == f"{CB_SETTINGS}:verify_menu":
        uid = q.from_user.id
        if _blocked_by_cooldown(uid):
            return await q.answer("⏳ You can retry verification after 3 days.", show_alert=True)
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎙 Verify by Voice",  callback_data=f"{CB_SETTINGS}:verify_voice"),
            InlineKeyboardButton("🤳 Verify by Selfie", callback_data=f"{CB_SETTINGS}:verify_selfie"),
        ]])
        await q.answer()
        return await q.edit_message_text("Choose a verification method:", reply_markup=kb)

    # --- Verified badge (read-only) ---
    if data == f"{CB_SETTINGS}:noop":
        return await q.answer("✔ You are already verified!")

    # --- Start Voice verification ---
    if data == f"{CB_SETTINGS}:verify_voice":
        uid = q.from_user.id
        if _blocked_by_cooldown(uid):
            return await q.answer("⏳ You can retry verification after 3 days.", show_alert=True)
        phrase = f"Today is {datetime.utcnow().day}, code {random.randint(1000,9999)}"
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                UPDATE users
                   SET verify_phrase=%s,
                       verify_status='awaiting',
                       verify_method='voice',
                       verify_audio_file=NULL,
                       verify_photo_file=NULL
                 WHERE tg_user_id=%s
            """, (phrase, uid))
            con.commit()
        context.user_data["awaiting_voice_verif"] = True
        await q.answer()
        return await q.edit_message_text(
            "🎙 Please send a short *voice note* saying exactly this line:\n\n"
            f"`{phrase}`\n\n"
            "_Tip: speak clearly._",
            parse_mode="Markdown"
        )

    # --- Start Selfie verification ---
    if data == f"{CB_SETTINGS}:verify_selfie":
        uid = q.from_user.id
        if _blocked_by_cooldown(uid):
            return await q.answer("⏳ You can retry verification after 3 days.", show_alert=True)
        phrase = f"Today is {datetime.utcnow().day}, code {random.randint(1000,9999)}"
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                UPDATE users
                   SET verify_phrase=%s,
                       verify_status='awaiting',
                       verify_method='selfie',
                       verify_audio_file=NULL,
                       verify_photo_file=NULL
                 WHERE tg_user_id=%s
            """, (phrase, uid))
            con.commit()
        context.user_data["awaiting_selfie_verif"] = True
        await q.answer()
        return await q.edit_message_text(
            "🤳 Please send a *selfie photo* holding a paper that shows:\n\n"
            f"`{phrase}`\n\n"
            "_Use the front camera. No gallery photos. Your face and the code must be clearly visible._",
            parse_mode="Markdown"
        )

    # --- Verified-only toggle ---
    if data == f"{CB_SETTINGS}:toggle_verifiedonly":
        uid = q.from_user.id
        
        # ✅ PREMIUM GATE
        if not _has_premium(uid):
            # वही popup जैसा 2nd screenshot में है
            return await q.answer("⚡⭐ To use this feature you must have a premium subscription.", show_alert=True)
        
        val = not bool(context.user_data.get("match_verified_only"))
        reg.set_match_verified_only(uid, val)
        context.user_data["match_verified_only"] = val
        await q.answer("Updated.")
        return await _send_or_edit_settings(update, context)

    # --- Incognito toggle ---
    if data == f"{CB_SETTINGS}:toggle_incognito":
        uid = q.from_user.id
        val = not bool(context.user_data.get("incognito"))
        reg.set_incognito(uid, val)
        context.user_data["incognito"] = val
        await q.answer("Updated.")
        return await _send_or_edit_settings(update, context)

    # --- Feed notifications toggle ---
    if data == f"{CB_SETTINGS}:toggle_feednotify":
        uid = q.from_user.id
        val = not bool(context.user_data.get("feed_notify", True))
        reg.set_feed_notify(uid, val)
        context.user_data["feed_notify"] = val
        await q.answer("Updated.")
        return await _send_or_edit_settings(update, context)

    # default: ignore
    await q.answer()

async def cmd_verifystate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to show current verification state."""
    uid = update.effective_user.id
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT verify_status, verify_method, verify_audio_file, verify_photo_file FROM users WHERE tg_user_id=%s;", (uid,))
        row = cur.fetchone()
    await update.message.reply_text(f"state={row}")

# --- Registration --------------------------------------------

def register(application):
    # Settings button (reply-keyboard text)
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_SETTINGS)}$"), show_settings), group=-1)
    # All inline callbacks for settings
    application.add_handler(CallbackQueryHandler(on_settings_callback, pattern=rf"^{CB_SETTINGS}:"))
    # Verification handlers - HIGHEST PRIORITY to prevent chat relay from swallowing them
    application.add_handler(MessageHandler(filters.VOICE, on_voice_verif), group=-1)
    application.add_handler(MessageHandler(filters.PHOTO, on_photo_verif), group=-1)
    # Debug command for verification state
    application.add_handler(CommandHandler("verifystate", cmd_verifystate), group=0)
