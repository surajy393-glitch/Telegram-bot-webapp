# handlers/vault_text.py
from telegram.ext import CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from .text_framework import claim_or_reject, clear_state, requires_state, make_cancel_kb
import logging

log = logging.getLogger("vault_text")

FEATURE = "vault"

async def start_vault_text_input(update, context: ContextTypes.DEFAULT_TYPE, category_id: int):
    """Start vault text collection with proper state management"""
    ok = await claim_or_reject(update, context, FEATURE, "await_text", ttl_minutes=5)
    if not ok: 
        return False

    # Store the category ID
    context.user_data['vault_category_id'] = category_id
    
    text = "📝 **SUBMIT YOUR TEXT**\n\n"
    text += "Send your text content now (one message):\n\n"
    text += "📝 Keep it engaging and creative\n"
    text += "🔍 Content will be reviewed by admins\n"
    text += "💰 You'll earn 1 coin for submission"
    
    try:
        await update.callback_query.edit_message_text(
            text, reply_markup=make_cancel_kb()
        )
    except Exception:
        # Fallback if edit fails
        await update.callback_query.message.reply_text(
            text, reply_markup=make_cancel_kb()
        )
    
    return True

@requires_state(feature=FEATURE, mode="await_text")
async def on_vault_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle vault text input with proper validation"""
    txt = (update.message.text or "").strip()
    
    if not txt:
        await update.message.reply_text("❌ Empty text. Please send some content.")
        return
    
    if len(txt) < 10:
        await update.message.reply_text("❌ Text too short. Please send at least 10 characters.")
        return
    
    user_id = update.effective_user.id
    category_id = context.user_data.get('vault_category_id')
    
    if not category_id:
        clear_state(context)
        await update.message.reply_text("❌ Submission session expired. Please start over.")
        return
    
    # Store text submission in database using existing vault functionality
    try:
        # Import vault functions
        from . import blur_vault
        
        # Create blurred version for text content
        blurred_content = blur_vault.create_smart_blur(txt, 70) if txt else "**Blurred Text** Reveal to read"
        
        # Store in database using existing connection method
        import registration as reg
        with reg._conn() as con, con.cursor() as cur:
            # Store in database
            cur.execute("""
                INSERT INTO vault_content (submitter_id, category_id, content_text, blurred_text, media_type, approval_status)
                VALUES (%s, %s, %s, %s, 'text', 'pending')
                RETURNING id
            """, (user_id, category_id, txt, blurred_content))
            
            content_id = cur.fetchone()[0]
            con.commit()
            
            # Clear state first
            clear_state(context)
            
            # Send success message and schedule auto-deletion after 20 seconds
            sent_message = await update.message.reply_text(
                "✅ **Your text has been submitted!**\n\n"
                f"📝 **Content:** {txt[:100]}{'...' if len(txt) > 100 else ''}\n\n"
                "💰 **Coin Reward System:**\n"
                "• You'll earn 1 coin when your content gets approved\n"
                "• No coins awarded for rejected submissions\n"
                "• Help us grow with new content daily\n"
                "• More quality submissions = More rewards\n\n"
                "🔍 Your submission will be reviewed by admins within 24 hours.\n"
                "Once approved, it will appear in the vault with blur effects!\n\n"
                "🔥 **Together we can create the hottest content library!**"
            )
            
            # Schedule automatic deletion after 20 seconds
            import asyncio
            async def delete_vault_success_message():
                try:
                    await asyncio.sleep(20)
                    await context.bot.delete_message(
                        chat_id=sent_message.chat_id,
                        message_id=sent_message.message_id
                    )
                except Exception as e:
                    # Ignore errors (message might already be deleted by user)
                    pass
            
            # Create background task for deletion
            asyncio.create_task(delete_vault_success_message())
            
            # Notify admins using existing function
            await blur_vault.notify_admins_new_submission(context, user_id, content_id, 'text', str(category_id))
            
    except Exception as e:
        log.error(f"Vault text submission error: {e}")
        clear_state(context)
        await update.message.reply_text("❌ Submission failed. Please try again.")

async def cancel_vault_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancellation of vault text input"""
    query = update.callback_query
    await query.answer()
    clear_state(context)
    
    # Go back to vault main menu
    try:
        from . import blur_vault
        await blur_vault.cmd_vault(update, context)
    except Exception:
        await query.edit_message_text("❌ Input cancelled. Use /vault to start again.")

def register(app):
    """Register vault text handlers with proper priorities"""
    
    # Vault text input handler - MEDIUM PRIORITY (after fantasy)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_vault_text_input), group=-11)
    
    log.info("[vault_text] Handlers registered successfully")

# Export functions for use in main blur_vault module
__all__ = ['start_vault_text_input', 'cancel_vault_input', 'register']