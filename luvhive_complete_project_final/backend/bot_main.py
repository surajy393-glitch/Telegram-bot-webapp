import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv
import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in environment")

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/instagram_platform")
DB_NAME = os.environ.get("DB_NAME", "instagram_platform")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Bot commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler."""
    user = update.effective_user
    user_id = user.id
    
    # Check if user exists in database
    existing_user = await db.users.find_one({"tg_user_id": user_id})
    
    keyboard = [
        [InlineKeyboardButton("🌐 Open Web App", web_app={"url": "https://tg-bot-profile-debug.preview.emergentagent.com"})],
        [InlineKeyboardButton("👤 My Profile", callback_data="profile")],
        [InlineKeyboardButton("📱 Features", callback_data="features")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🎉 Welcome to Instagram-Style Social Platform!

👋 Hi {user.first_name}!

This is your social media platform with:
🏠 Feed with posts and stories
📸 Photo and video sharing  
💬 Comments and likes
👥 Follow friends
📲 Stories that disappear in 24h

Click "Open Web App" to start using the platform!
"""
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    # Log user interaction
    if not existing_user:
        await db.users.insert_one({
            "tg_user_id": user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "joined_at": datetime.datetime.utcnow(),
            "is_onboarded": False
        })

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Profile command handler."""
    user_id = update.effective_user.id
    
    user_data = await db.users.find_one({"tg_user_id": user_id})
    
    if not user_data or not user_data.get("is_onboarded"):
        keyboard = [[InlineKeyboardButton("🌐 Complete Setup", web_app={"url": "https://tg-bot-profile-debug.preview.emergentagent.com"})]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚀 Complete your profile setup in the web app first!",
            reply_markup=reply_markup
        )
        return
    
    posts_count = user_data.get("posts_count", 0)
    followers_count = user_data.get("followers_count", 0)
    following_count = user_data.get("following_count", 0)
    
    profile_text = f"""
👤 **{user_data.get('display_name', 'User')}**
@{user_data.get('username', 'username')}

📊 Stats:
📸 Posts: {posts_count}
👥 Followers: {followers_count}
➕ Following: {following_count}

Age: {user_data.get('age', 'Not set')}
Joined: {user_data.get('joined_at', datetime.datetime.utcnow()).strftime('%B %Y')}
"""
    
    keyboard = [[InlineKeyboardButton("🌐 Open Profile", web_app={"url": "https://tg-bot-profile-debug.preview.emergentagent.com"})]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistics command handler."""
    
    # Get platform statistics
    total_users = await db.users.count_documents({})
    total_posts = await db.posts.count_documents({})
    total_stories = await db.stories.count_documents({})
    
    # Active stories (last 24 hours)
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    active_stories = await db.stories.count_documents({"created_at": {"$gt": cutoff}})
    
    stats_text = f"""
📊 **Platform Statistics**

👥 Total Users: {total_users:,}
📸 Total Posts: {total_posts:,}  
📱 Total Stories: {total_stories:,}
🔥 Active Stories (24h): {active_stories:,}

🎉 Join the community and start sharing!
"""
    
    keyboard = [[InlineKeyboardButton("🌐 Open App", web_app={"url": "https://tg-bot-profile-debug.preview.emergentagent.com"})]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "profile":
        await profile_command(update, context)
    elif query.data == "features":
        features_text = """
🚀 **Platform Features**

📸 **Posts & Media**
- Share photos and videos
- Write captions and add hashtags
- Get likes and comments from friends

📱 **Stories**
- Share moments that disappear in 24h  
- See who viewed your stories
- Interactive story features

👥 **Social Features**
- Follow friends and discover new people
- Like and comment on posts
- Real-time notifications

🎨 **Rich Experience**  
- Beautiful Instagram-style interface
- Dark/light theme support
- Smooth animations and interactions

Click "Open Web App" to explore all features!
"""
        keyboard = [[InlineKeyboardButton("🌐 Open Web App", web_app={"url": "https://tg-bot-profile-debug.preview.emergentagent.com"})]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(features_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler."""
    help_text = """
🤖 **Bot Commands**

/start - Welcome message and web app access
/profile - View your profile stats  
/stats - Platform statistics
/help - Show this help message

🌐 **Web App Features**
- Open the web app to access all features
- Create posts with photos/videos
- Share stories that disappear in 24h
- Follow friends and discover content
- Like, comment, and interact

💡 **Tips**
- Complete your profile setup for the best experience
- Use the web app for full functionality
- Stories disappear after 24 hours

Need more help? Just ask! 😊
"""
    
    keyboard = [[InlineKeyboardButton("🌐 Open Web App", web_app={"url": "https://tg-bot-profile-debug.preview.emergentagent.com"})]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    keyboard = [[InlineKeyboardButton("🌐 Open Web App", web_app={"url": "https://tg-bot-profile-debug.preview.emergentagent.com"})]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 I'm a bot for the Instagram-style social platform!\n\n" +
        "Use the web app for posting, stories, and social features.\n" +
        "Or try /help for available commands.",
        reply_markup=reply_markup
    )

def main():
    """Run the bot."""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Run with polling
    logger.info("Starting Instagram-Style Social Platform Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")