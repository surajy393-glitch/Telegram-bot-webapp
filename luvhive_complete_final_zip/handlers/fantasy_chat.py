# handlers/fantasy_chat.py
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from .text_framework import claim_or_reject, clear_state, requires_state, make_cancel_kb
import logging

log = logging.getLogger("fantasy_chat")

FEATURE = "fantasy"

# Import the vibe categories and functions from main fantasy_match module
from . import fantasy_match
from .fantasy_match import _exec, _arr, normalize_gender, _normalize_keywords

async def start_fantasy_keywords(update, context: ContextTypes.DEFAULT_TYPE, vibe: str):
    """Start fantasy keyword collection with proper state management"""
    ok = await claim_or_reject(update, context, FEATURE, mode="await_keywords", ttl_minutes=5)
    if not ok: 
        return

    # Store the selected vibe
    context.user_data['selected_vibe'] = vibe
    
    vibe_info = fantasy_match.VIBE_CATEGORIES.get(vibe, fantasy_match.VIBE_CATEGORIES.get('romantic', {'emoji': '💕', 'title': 'Romantic', 'desc': 'Sweet, passionate connections'}))
    
    text = f"✍️ **DESCRIBE YOUR {vibe_info['title'].upper()} FANTASY**\n\n"
    text += f"{vibe_info['emoji']} *{vibe_info['desc']}*\n\n"
    text += "Type your fantasy description (10-300 characters):\n\n"
    text += "📝 Be specific about what you want\n"
    text += "🔥 Our AI will find someone with the EXACT same desires\n"
    text += "💫 Make your dreams become reality\n"
    text += "🔒 This stays completely anonymous"
    
    try:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=make_cancel_kb()
        )
    except Exception:
        await update.callback_query.edit_message_text(
            text.replace('*', ''),
            reply_markup=make_cancel_kb()
        )

@requires_state(feature=FEATURE, mode="await_keywords")
async def on_fantasy_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle fantasy keyword input with robust TEXT[] casting"""
    if not update.effective_user or not update.message:
        return
    uid     = update.effective_user.id
    text_in = (update.message.text or "").strip()
    if len(text_in) < 10 or len(text_in) > 300:
        return await update.message.reply_text("⚠️ Please write 10–300 characters.")

    vibe = context.user_data.get('selected_vibe') if context.user_data else None
    if not vibe:
        return await update.message.reply_text("⚠️ Pick a vibe first, then send your description.")

    # derive keywords (your normalizer)
    kws = _normalize_keywords(text_in)

    # limit slots
    rows   = _exec("SELECT COUNT(*) FROM fantasy_submissions WHERE user_id=%s AND active=TRUE", (uid,))
    # Handle different _exec return types
    if isinstance(rows, (list, tuple)) and len(rows) > 0:
        active = rows[0][0] if isinstance(rows[0], (list, tuple)) else rows[0]
    elif isinstance(rows, int):
        active = rows
    else:
        active = 0
    if active >= 3:
        return await update.message.reply_text("⚠️ You already have 3 active fantasies. Disable one before adding new.")

    # normalized gender from profile
    import registration as reg
    profile = reg.get_profile(uid) or {}
    gender  = normalize_gender(profile.get("gender"))

    ok = _exec("""
      INSERT INTO fantasy_submissions
        (user_id, gender, fantasy_text, vibe, keywords, active)
      VALUES
        (%s,      %s,      %s,           %s,   %s::TEXT[], TRUE)
    """, (uid, gender, text_in, vibe, _arr(kws)))

    if ok is None or ok is False:
        return await update.message.reply_text("❌ Failed to save fantasy. Try again.")

    clear_state(context)
    
    success_message = ("✅ **Fantasy Saved Successfully!** ✅\n\n"
                      "🔮 Now go check the **Fantasy Board** to browse other fantasies you might like and connect with that person directly!\n\n"
                      "💡 You can also wait for someone to discover and like your fantasy.\n\n"
                      "🎯 Use /fantasy and tap **'🔮 Fantasy Board'** to explore amazing connections!")
    
    await update.message.reply_text(success_message, parse_mode=ParseMode.MARKDOWN)

async def handle_fantasy_vibe_selection(update, context, vibe: str):
    """Handle vibe selection and start keyword input"""
    await start_fantasy_keywords(update, context, vibe)

async def cancel_fantasy_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancellation of fantasy input"""
    query = update.callback_query
    if not query:
        return
    await query.answer()
    clear_state(context)
    
    # Go back to fantasy main menu
    from . import fantasy_match
    await fantasy_match.cmd_fantasy(update, context)

async def handle_global_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle global textfw:cancel callback (REMOVED - use main text framework)"""
    # This is now handled by the main text framework in text_framework.py
    # to avoid conflicts with other features like WYR comments
    pass

def register(app):
    """Register fantasy chat handlers with proper priorities"""
    
    # REMOVED: Global cancel handler - now using main text framework to fix WYR cancel conflicts
    # app.add_handler(CallbackQueryHandler(handle_global_cancel, pattern=r"^textfw:cancel$"), group=-20)
    
    # Fantasy-specific text input handler - HIGH PRIORITY to avoid swallowing
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_fantasy_keywords), group=-12)
    
    log.info("[fantasy_chat] Handlers registered successfully")

# Export the function for use in main fantasy_match module
__all__ = ['start_fantasy_keywords', 'handle_fantasy_vibe_selection', 'cancel_fantasy_input', 'register']