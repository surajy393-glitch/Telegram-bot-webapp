# Thin wrapper; the real logic lives in chat.py
import chat
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
import registration as reg
from utils.display import safe_display_name

# Re-match invitation helpers
async def send_rematch_invite(context, uid, other_uid):
    """Send re-match invitation with safe display name"""
    name = safe_display_name(other_uid)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept", callback_data=f"rm:acc:{other_uid}"),
         InlineKeyboardButton("❌ Decline", callback_data=f"rm:dec:{other_uid}")]
    ])
    try:
        await context.bot.send_message(
            chat_id=uid,
            text=f"🔁 {name} invites you to re-match. Accept?",
            reply_markup=kb
        )
    except Exception:
        pass

async def send_secret_chat_invite(context, user_uid, partner_uid, minutes, sd):
    """Send secret chat invitation with safe display name"""
    name = safe_display_name(partner_uid)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept", callback_data=f"sc:acc:{partner_uid}"),
         InlineKeyboardButton("❌ Decline", callback_data=f"sc:dec:{partner_uid}")]
    ])
    try:
        await context.bot.send_message(
            chat_id=user_uid,
            text=f"🔐 {name} invited you to Secret Chat.\n"
                 f"Timer: {minutes} min | Self-destruct: {sd}s\nAccept?",
            reply_markup=kb
        )
    except Exception:
        pass

def _fmt_hms(sec: int) -> str:
    h = sec // 3600; m = (sec % 3600) // 60; s = sec % 60
    return f"{h:02d}h:{m:02d}m:{s:02d}s"

async def cmd_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ok, left = reg.can_spin(uid)
    if not ok:
        return await update.message.reply_text(f"⏳ Next spin in { _fmt_hms(left) }.")
    # fun message
    msg = await update.message.reply_text("🎰 Spinning the wheel...")
    reward, bal = reg.apply_spin(uid)
    txt = f"➡️ You won *{reward}* coins!\n💰 Balance: {bal}"
    await msg.edit_text(txt, parse_mode="Markdown")

LB_CB_PREFIX = "lb"
LB_CB_COINS = f"{LB_CB_PREFIX}:coins"
LB_CB_GAMES = f"{LB_CB_PREFIX}:games"
LB_CB_REF = f"{LB_CB_PREFIX}:referrals"

def _lb_keyboard(active: str) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(("🏅 Coins" if active=="coins" else "Coins"),
                             callback_data=LB_CB_COINS),
        InlineKeyboardButton(("🏅 Games" if active=="games" else "Games"),
                             callback_data=LB_CB_GAMES),
        InlineKeyboardButton(("🏅 Referrals" if active=="referrals" else "Referrals"),
                             callback_data=LB_CB_REF),
    ]]
    return InlineKeyboardMarkup(rows)

def _fmt_list(title: str, rows: list[tuple[int,int]], unit: str) -> str:
    if not rows:
        return f"🏆 *{title}*\nNo data yet."
    lines = [f"🏆 *{title}*"]
    for i,(uid,val) in enumerate(rows, start=1):
        lines.append(f"{i}. `{uid}` — {val} {unit}")
    return "\n".join(lines)

async def _render_lb(update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str, is_cb: bool):
    if kind == "coins":
        rows = reg.get_top_coins(10)
        text = _fmt_list("Top by Coins", rows, "coins")
    elif kind == "games":
        rows = reg.get_top_games(10)
        text = _fmt_list("Top by Games Played", rows, "games")
    elif kind == "referrals":
        rows = reg.get_top_referrals(10)
        text = _fmt_list("Top by Referrals", rows, "invites")
    else:
        text = "Invalid leaderboard."
        rows = []
    kb = _lb_keyboard(kind)
    if is_cb:
        q = update.callback_query
        try:
            await q.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        finally:
            try: await q.answer()
            except Exception:
                import logging
                log = logging.getLogger("luvbot.chat_handlers")  
                log.exception("Failed to send secret media notification")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _render_lb(update, context, "coins", is_cb=False)

async def on_lb_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == LB_CB_COINS:
        await _render_lb(update, context, "coins", True)
    elif data == LB_CB_GAMES:
        await _render_lb(update, context, "games", True)
    elif data == LB_CB_REF:
        await _render_lb(update, context, "referrals", True)

def register(app):
    chat.register_handlers(app)  # adds /find /search /next /stop + rating/report + relay

    # Add spin and leaderboard handlers
    app.add_handler(CommandHandler("spin",         cmd_spin),        group=0)
    app.add_handler(CommandHandler("leaderboard",  cmd_leaderboard), group=0)
    app.add_handler(CallbackQueryHandler(on_lb_cb, pattern=r"^lb:(coins|games|referrals)$"), group=0)