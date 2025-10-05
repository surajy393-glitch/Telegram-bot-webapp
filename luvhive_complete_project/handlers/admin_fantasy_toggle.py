
# handlers/admin_fantasy_toggle.py
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from handlers.fantasy_prompts import get_prompt_mode, set_prompt_mode

# Replace with your admin IDs check
def _is_admin(uid: int) -> bool:
    try:
        from admin import ADMIN_IDS
        return uid in ADMIN_IDS
    except Exception:
        return False

def _mode_kb(context):
    mode = get_prompt_mode(context)
    def mark(x): return f"✅ {x}" if x == mode else x
    row1 = [
        InlineKeyboardButton(mark("auto"),    callback_data="adm:fantpm:auto"),
        InlineKeyboardButton(mark("weekday"), callback_data="adm:fantpm:weekday"),
        InlineKeyboardButton(mark("weekend"), callback_data="adm:fantpm:weekend"),
    ]
    return InlineKeyboardMarkup([row1])

async def cmd_fantasy_prompt_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    mode = get_prompt_mode(context)
    text = (
        "🛠️ *Fantasy Prompt Mode*\n\n"
        "Current: *{m}*\n\n"
        "• *auto*: weekdays=normal, weekends=spicy pool\n"
        "• *weekday*: always normal pool\n"
        "• *weekend*: always spicy pool"
    ).format(m=mode)
    await update.message.reply_text(text, reply_markup=_mode_kb(context), parse_mode="Markdown")

async def on_fantasy_prompt_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not _is_admin(q.from_user.id):
        return await q.answer("Admin only")
    try:
        mode = q.data.split(":")[2]  # auto|weekday|weekend
    except Exception:
        return await q.answer("Invalid")
    set_prompt_mode(context, mode)
    await q.answer(f"Set to {mode}")
    # Refresh panel
    mode_now = get_prompt_mode(context)
    text = (
        "🛠️ *Fantasy Prompt Mode*\n\n"
        "Current: *{m}*\n\n"
        "• *auto*: weekdays=normal, weekends=spicy pool\n"
        "• *weekday*: always normal pool\n"
        "• *weekend*: always spicy pool"
    ).format(m=mode_now)
    try:
        await q.edit_message_text(text, reply_markup=_mode_kb(context), parse_mode="Markdown")
    except Exception:
        # if edit fails (e.g., message too old), just send a new one
        await q.message.reply_text(text, reply_markup=_mode_kb(context), parse_mode="Markdown")

async def cmd_fantasy_prompt_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    await update.message.reply_text(f"Fantasy Prompt Mode: {get_prompt_mode(context)}")

def register(app):
    app.add_handler(CommandHandler("fantasy_prompt_panel", cmd_fantasy_prompt_panel), group=0)
    app.add_handler(CommandHandler("fantasy_prompt_status", cmd_fantasy_prompt_status), group=0)
    app.add_handler(CallbackQueryHandler(on_fantasy_prompt_toggle, pattern=r"^adm:fantpm:(auto|weekday|weekend)$"), group=0)
