"""
Mini App Commands for LuvHive
Telegram Bot commands to open and manage the LuvHive social webapp
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
import registration as reg
import os


async def cmd_feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open the LuvHive social feed webapp"""
    user = update.effective_user
    if not user:
        return
    
    # Ensure user is registered
    if not reg.is_registered(user.id):
        await update.effective_message.reply_text(
            "🚫 Please complete registration first using /start"
        )
        return
    
    # Get the webapp URL - use the preview URL for now
    webapp_url = "https://content-flow-fix-2.preview.emergentagent.com"
    
    # Create WebApp button
    keyboard = [
        [InlineKeyboardButton(
            "🌍 Open LuvHive Feed", 
            web_app=WebAppInfo(url=f"{webapp_url}/")
        )],
        [InlineKeyboardButton("✨ What's New?", callback_data="miniapp:info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "🎉 **Welcome to LuvHive Social!**\n\n"
        "💕 Experience our new social platform:\n"
        "• 🌟 Share your moments with VibeFeed technology\n"
        "• ✨ Spark connections with mood-based matching\n"
        "• 💫 Glow system - express appreciation uniquely\n"
        "• 🎭 Anonymous confessions & authentic connections\n"
        "• 🔮 AI-powered emotional compatibility matching\n"
        "• 🌈 Dynamic mood indicators & aura profiles\n\n"
        "🚀 Tap the button below to enter your feed!"
    )
    
    await update.effective_message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def cmd_publicfeed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Legacy command - redirect to new feed"""
    await cmd_feed(update, context)


async def cb_miniapp_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mini app information"""
    query = update.callback_query
    await query.answer()
    
    info_text = (
        "✨ **What's New in LuvHive?**\n\n"
        "**🌟 Unique Social Features:**\n"
        "• LuvConnect: AI-powered emotional matching\n"
        "• VibeFeed: Mood-based content discovery\n"
        "• MoodSync: Dynamic emotional indicators\n"
        "• SparkChats: 24-hour authentic conversations\n"
        "• AuraMatch: Personality compatibility scoring\n\n"
        
        "**🎯 Smart Discovery:**\n"
        "• Following: Connect with your tribe\n"
        "• Vibes: Find people who match your energy\n"
        "• Sparks: Discover trending conversations\n"
        "• Discover: AI-curated compatible profiles\n\n"
        
        "**💫 Interaction System:**\n"
        "• Spark posts (✨): Show appreciation\n"
        "• Glow reactions (💫): Express deeper connection\n"
        "• Memory Capsules: Time-locked messages\n"
        "• Anonymous confessions for authentic sharing\n\n"
        
        "**🔮 Advanced Features:**\n"
        "• Real-time emotional analysis\n"
        "• Compatibility percentage scoring\n"
        "• Virtual hangout spaces\n"
        "• End-to-end privacy protection\n\n"
        
        "💕 Experience authentic connections like never before!"
    )
    
    keyboard = [
        [InlineKeyboardButton(
            "🚀 Enter LuvHive Now", 
            web_app=WebAppInfo(url="https://content-flow-fix-2.preview.emergentagent.com/")
        )],
        [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        info_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def cmd_miniapp_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show mini app usage statistics (admin only)"""
    user = update.effective_user
    if not user:
        return
    
    # Check if user is admin
    admin_ids = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]
    if user.id not in admin_ids:
        await update.effective_message.reply_text("⛔ Admin only command.")
        return
    
    try:
        # Get mini app statistics
        from api.miniapp_handlers import reg
        
        with reg._conn() as con, con.cursor() as cur:
            # Get various stats
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM miniapp_posts) as total_posts,
                    (SELECT COUNT(*) FROM miniapp_posts WHERE created_at > NOW() - INTERVAL '24 hours') as posts_today,
                    (SELECT COUNT(*) FROM miniapp_likes) as total_likes,
                    (SELECT COUNT(*) FROM miniapp_comments) as total_comments,
                    (SELECT COUNT(*) FROM miniapp_follows) as total_follows,
                    (SELECT COUNT(*) FROM miniapp_saves WHERE expires_at > NOW()) as active_saves,
                    (SELECT COUNT(DISTINCT user_id) FROM miniapp_post_views WHERE viewed_at > NOW() - INTERVAL '24 hours') as active_users_today
            """)
            
            result = cur.fetchone()
            if result:
                total_posts, posts_today, total_likes, total_comments, total_follows, active_saves, active_users_today = result
                
                stats_text = (
                    "📊 **LuvHive Mini App Statistics**\n\n"
                    f"📝 **Posts:** {total_posts:,} total • {posts_today:,} today\n"
                    f"❤️ **Likes:** {total_likes:,} total\n"
                    f"💬 **Comments:** {total_comments:,} total\n"
                    f"👥 **Follows:** {total_follows:,} connections\n"
                    f"💾 **Active Saves:** {active_saves:,}\n"
                    f"🎯 **Active Users Today:** {active_users_today:,}\n\n"
                    
                    "📈 **Engagement Metrics:**\n"
                    f"• Avg likes per post: {(total_likes / max(total_posts, 1)):.1f}\n"
                    f"• Avg comments per post: {(total_comments / max(total_posts, 1)):.1f}\n"
                    f"• Posts per active user: {(posts_today / max(active_users_today, 1)):.1f}\n"
                )
                
                await update.effective_message.reply_text(stats_text, parse_mode='Markdown')
            else:
                await update.effective_message.reply_text("❌ Failed to get statistics.")
                
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error getting stats: {e}")


# Register handlers
def register_miniapp_handlers(app):
    """Register mini app command handlers"""
    app.add_handler(CommandHandler("feed", cmd_feed))
    app.add_handler(CommandHandler("publicfeed", cmd_publicfeed))  # Legacy support
    app.add_handler(CommandHandler("miniappstats", cmd_miniapp_stats))
    app.add_handler(CallbackQueryHandler(cb_miniapp_info, pattern="^miniapp:info$"))
    
    print("✅ Mini app handlers registered")