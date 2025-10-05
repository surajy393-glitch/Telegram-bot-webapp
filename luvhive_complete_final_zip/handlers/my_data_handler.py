# handlers/my_data_handler.py - User data summary command
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import html

log = logging.getLogger(__name__)

async def cmd_my_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /my_data command - show user's data summary"""
    user_id = update.effective_user.id
    
    try:
        from utils.privacy_compliance import privacy_manager
        
        # Get user data summary
        result = privacy_manager.get_user_data_summary(user_id)
        
        if result.get("success"):
            data_breakdown = result.get("data_breakdown", {})
            total_records = result.get("total_records", 0)
            checked_at = result.get('checked_at', 'Unknown')
            
            # Clean the checked_at timestamp to avoid parsing issues
            if checked_at != 'Unknown':
                # Keep only the first 16 characters (date + time without microseconds)
                checked_at = str(checked_at)[:16]
            
            # Build data breakdown safely
            breakdown_text = ""
            if data_breakdown:
                for description, count in data_breakdown.items():
                    # Clean description to avoid markdown issues
                    clean_desc = str(description).replace('_', ' ').title()
                    breakdown_text += f"• {clean_desc}: {count}\n"
            else:
                breakdown_text = "• No significant data stored\n"
            
            # Use HTML formatting instead of Markdown (more forgiving)
            data_text = f"""📊 <b>Your Data Summary</b>

🆔 <b>User ID:</b> {user_id}
📈 <b>Total Records:</b> {total_records}

<b>Data Breakdown:</b>
{breakdown_text}
🕐 <b>Checked:</b> {checked_at}

<b>Your Rights:</b>
• Access: This summary (via /my_data)
• Deletion: Complete removal (via /delete_me)
• Control: Block users, manage preferences
• Portability: Contact support for data export

<b>Data Retention:</b>
• Profile data: Until account deletion
• Chat logs: 90 days maximum
• Reports: 90 days for safety
• Backups: 14 days for recovery

Type /privacy for full privacy policy.
Type /delete_me to request data deletion."""
            
            # Add action buttons
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔒 Privacy Policy", callback_data="privacy:policy")],
                [InlineKeyboardButton("🗑️ Delete My Data", callback_data="privacy:delete")]
            ])
            
            await update.effective_message.reply_text(
                data_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
        else:
            error_msg = str(result.get('error', 'Unknown error'))
            error_text = f"""❌ <b>Data Summary Failed</b>

Could not retrieve your data summary: {error_msg}

Please try again later or contact support if the problem persists.

<b>Alternative options:</b>
• Use /privacy for privacy policy
• Use /delete_me for data deletion"""
            
            await update.effective_message.reply_text(
                error_text,
                parse_mode='HTML'
            )
            
    except Exception as e:
        log.error(f"My data command failed for user {user_id}: {e}")
        
        error_text = """❌ <b>Service Temporarily Unavailable</b>

The data summary feature is temporarily unavailable. Please try again later.

<b>What you can do:</b>
• Check your profile with /settings
• View privacy policy with /privacy
• Request data deletion with /delete_me"""
        
        await update.effective_message.reply_text(
            error_text,
            parse_mode='HTML'
        )