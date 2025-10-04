
# handlers/premium_open.py
from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

# We reuse your existing premium screen (already used in /premium button)
# Fallback text in case import path changes.
DEFAULT_TEXT = (
    "💎 Premium\n\n"
    "Unlock age filters, stealth mode, blur-reveals, After Dark Lounge & more.\n"
    "Choose a plan below."
)

async def _send_premium_screen(update_or_msg, context: ContextTypes.DEFAULT_TYPE):
    # Try to use your existing premium page (text + keyboard)
    try:
        # these imports match your earlier main.py usage
        from premium import premium_text, premium_kb
        txt = premium_text()
        kb  = premium_kb()
        # update_or_msg can be a Message or a CallbackQuery.message
        await update_or_msg.reply_text(txt, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        # Fallback simple screen (no break if import fails)
        try:
            await update_or_msg.reply_text(DEFAULT_TEXT)
        except Exception:
            pass

# Callback from lock screens (callback_data="premium:open")
async def on_premium_open_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await _send_premium_screen(q.message, context)

# Optional: /upgrade alias (beside your /premium)
async def cmd_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_premium_screen(update.message, context)

def register(app):
    # callback first so it never gets swallowed
    app.add_handler(CallbackQueryHandler(on_premium_open_cb, pattern=r"^premium:open$"), group=-2)
    app.add_handler(CommandHandler("upgrade", cmd_upgrade), group=-1)
