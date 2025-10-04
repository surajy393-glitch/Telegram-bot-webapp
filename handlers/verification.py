
from telegram.ext import (CommandHandler, CallbackQueryHandler, MessageHandler,
                          filters, ContextTypes)
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from handlers.text_framework import claim_or_reject, requires_state, clear_state

GROUP_HIGH  = -16   # capture media first
GROUP_LOBBY = -10

async def cmd_verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎙️ Verify Voice",  callback_data="ver:start:voice")],
        [InlineKeyboardButton("📸 Verify Selfie", callback_data="ver:start:selfie")]
    ])
    await update.message.reply_text("Choose verification:", reply_markup=kb)

async def ver_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    mode = "await_voice" if q.data.endswith(":voice") else "await_selfie"
    if not await claim_or_reject(update, context, "verify", mode, ttl_minutes=2):
        return
    await q.message.reply_text("🎙️ Send a short VOICE now." if mode=="await_voice"
                               else "📸 Send a clear SELFIE (no filters).")

@requires_state("verify","await_voice")
async def on_verify_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not (update.effective_message.voice or update.effective_message.audio): return
    # TODO: save file_id, mark verified
    clear_state(context); await update.message.reply_text("✅ Voice verified.")

@requires_state("verify","await_selfie")
async def on_verify_selfie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message.photo: return
    # TODO: save largest photo file_id, mark verified
    clear_state(context); await update.message.reply_text("✅ Selfie verified.")

def register(app):
    app.add_handler(CommandHandler("verify", cmd_verify), group=GROUP_LOBBY)
    app.add_handler(CallbackQueryHandler(ver_start_cb, pattern=r"^ver:start:(voice|selfie)$"), group=GROUP_LOBBY)
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_verify_voice), group=GROUP_HIGH)
    app.add_handler(MessageHandler(filters.PHOTO, on_verify_selfie), group=GROUP_HIGH)
