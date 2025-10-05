# handlers/privacy_handler.py - Privacy policy command (ChatGPT Final Polish)
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

async def cmd_privacy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /privacy command - transparency for users"""
    privacy_text = """🔒 **Privacy Policy - LuvHive**

**Data We Collect:**
• Basic profile info (gender, age, location)
• Chat interactions and preferences  
• Usage metrics for improvement
• Payment data (for premium features)

**How We Use Your Data:**
• Matching you with compatible users
• Personalizing your experience
• Preventing abuse and ensuring safety
• Processing premium subscriptions

**Your Rights:**
• **Access**: View your data anytime via /settings
• **Deletion**: Complete removal via /delete_me 
• **Control**: Block/report users, manage preferences
• **Transparency**: This policy and our terms

**Data Security:**
• All data encrypted in transit and storage
• No data sold to third parties
• Regular security audits and monitoring
• GDPR compliant data handling

**Data Retention:**
• Profile data: Until account deletion
• Chat logs: 90 days maximum
• Reports/moderation: 90 days  
• Backups: 14 days for recovery

**Contact:**
Questions about privacy? Contact our support team.

**Last Updated:** September 2025

Type /delete_me to permanently delete all your data.
Type /terms to see our full terms of service."""

    await update.effective_message.reply_text(
        privacy_text,
        parse_mode='Markdown'
    )

def register_privacy_handler(app):
    """Register privacy command handler"""
    app.add_handler(CommandHandler("privacy", cmd_privacy), group=0)