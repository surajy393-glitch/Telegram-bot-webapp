#!/usr/bin/env python3
"""
Complete Instagram-Style Social Platform Telegram Bot
Comprehensive bot with matching, profiles, stories, games, and social features
"""

import os
import logging
import asyncio
import datetime
import pytz
from typing import Optional, List, Dict, Any
import json
import uuid

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, 
    ContextTypes, filters, ConversationHandler
)
from telegram.error import TelegramError, TimedOut, RetryAfter, NetworkError, Forbidden

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

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

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "instagram_platform")

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Constants for conversation states
(
    AWAITING_NAME, AWAITING_AGE, AWAITING_GENDER, AWAITING_INTERESTS, 
    AWAITING_BIO, AWAITING_PHOTO, PARTNER_SEARCH, CHAT_MODE,
    POST_CONTENT, STORY_CONTENT, COMMENT_MODE
) = range(11)

# Menu button labels
BTN_FIND_PARTNER = "💕⚡ Find a Partner"
BTN_MATCH_GIRLS = "💖👩 Match with girls"
BTN_MATCH_BOYS = "💙👨 Match with boys"
BTN_MY_PROFILE = "✨👤 My Profile"
BTN_SETTINGS = "💫⚙️ Settings"
BTN_PREMIUM = "💎✨ Premium"
BTN_FRIENDS = "💞👥 Friends"
BTN_PUBLIC_FEED = "🌹🌍 Public Feed"
BTN_FUN_GAMES = "💃🎮 Fun & Games"

def main_menu_kb() -> ReplyKeyboardMarkup:
    """Main menu keyboard layout"""
    return ReplyKeyboardMarkup([
        [KeyboardButton(BTN_FIND_PARTNER), KeyboardButton(BTN_MATCH_GIRLS)],
        [KeyboardButton(BTN_MATCH_BOYS), KeyboardButton(BTN_FRIENDS)],
        [KeyboardButton(BTN_PUBLIC_FEED), KeyboardButton(BTN_MY_PROFILE)],
        [KeyboardButton(BTN_SETTINGS), KeyboardButton(BTN_PREMIUM)],
        [KeyboardButton(BTN_FUN_GAMES)],
    ], resize_keyboard=True)

# User management functions
async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user from database"""
    return await db.users.find_one({"tg_user_id": user_id})

async def create_user(user_data: Dict[str, Any]) -> bool:
    """Create new user in database"""
    try:
        await db.users.insert_one(user_data)
        return True
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False

async def update_user(user_id: int, update_data: Dict[str, Any]) -> bool:
    """Update user in database"""
    try:
        result = await db.users.update_one(
            {"tg_user_id": user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return False

# Registration system
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start command with registration flow"""
    user = update.effective_user
    user_id = user.id
    
    # Check if user exists
    existing_user = await get_user(user_id)
    
    if existing_user and existing_user.get("registration_complete"):
        # Welcome back existing user
        keyboard = [
            [InlineKeyboardButton("🌐 Open Web App", 
                web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com"))],
            [InlineKeyboardButton("👤 My Profile", callback_data="profile"),
             InlineKeyboardButton("💕 Find Partner", callback_data="find_partner")],
            [InlineKeyboardButton("🎮 Fun & Games", callback_data="fun_games"),
             InlineKeyboardButton("💎 Premium", callback_data="premium")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
🎉 Welcome back, {existing_user.get('display_name', user.first_name)}!

Your Instagram-style social platform is ready:

✨ **Your Stats:**
📸 Posts: {existing_user.get('posts_count', 0)}
👥 Followers: {existing_user.get('followers_count', 0)}
💌 Matches: {existing_user.get('matches_count', 0)}

🌟 **Available Features:**
🏠 Feed with posts and stories
💕 Partner matching system
🎮 Fun games and activities
💬 Chat with matches
📲 Stories and media sharing

Click "Open Web App" for the full experience!
"""
        
        await update.message.reply_text(welcome_text, 
                                      reply_markup=reply_markup,
                                      reply_keyboard=main_menu_kb())
        return
    
    # New user registration
    keyboard = [
        [InlineKeyboardButton("🚀 Start Registration", callback_data="start_registration")],
        [InlineKeyboardButton("🌐 Open Web App", 
            web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🎉 Welcome to Instagram-Style Social Platform!

👋 Hi {user.first_name}!

This is your comprehensive social media platform featuring:

📱 **Instagram-Style Features:**
🏠 Beautiful feed with posts and stories
📸 Photo and video sharing
💬 Comments, likes, and social interactions
👥 Follow friends and discover new people

💕 **Dating & Matching:**
⚡ Smart partner matching system
💖 Match with girls or boys
💞 Chat with your matches
🎯 Interest-based connections

🎮 **Fun & Games:**
🎲 Interactive games and activities
🏆 Challenges and competitions
🎪 Community events
💎 Premium features and rewards

🚀 **Get Started:**
1. Complete your profile registration
2. Set your preferences and interests  
3. Start matching and socializing!

Ready to join our community? 🌟
"""
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    # Create basic user entry if doesn't exist
    if not existing_user:
        user_data = {
            "tg_user_id": user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "joined_at": datetime.datetime.utcnow(),
            "registration_complete": False,
            "is_onboarded": False
        }
        await create_user(user_data)

async def start_registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start registration process"""
    query = update.callback_query
    await query.answer()
    
    text = """
🌟 **Profile Registration**

Let's create your amazing profile! This will help you:
💕 Find better matches
👥 Connect with like-minded people
🎯 Get personalized recommendations

📝 **What's your display name?**
(This is how others will see you)
"""
    
    await query.edit_message_text(text)
    return AWAITING_NAME

async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle display name input"""
    display_name = update.message.text.strip()
    
    if len(display_name) < 2 or len(display_name) > 30:
        await update.message.reply_text(
            "❌ Please enter a name between 2-30 characters."
        )
        return AWAITING_NAME
    
    # Store in context
    context.user_data['display_name'] = display_name
    
    text = f"""
✅ Great! Your name is **{display_name}**

🎂 **How old are you?**
(Must be 18+ to use this platform)
"""
    
    await update.message.reply_text(text)
    return AWAITING_AGE

async def handle_age_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle age input"""
    try:
        age = int(update.message.text.strip())
        
        if age < 18 or age > 80:
            await update.message.reply_text(
                "❌ You must be between 18-80 years old to use this platform."
            )
            return AWAITING_AGE
        
        context.user_data['age'] = age
        
        # Gender selection keyboard
        keyboard = [
            [InlineKeyboardButton("👨 Male", callback_data="gender_male"),
             InlineKeyboardButton("👩 Female", callback_data="gender_female")],
            [InlineKeyboardButton("🌈 Non-binary", callback_data="gender_nonbinary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
✅ Age: **{age}** years old

👤 **What's your gender?**
"""
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return AWAITING_GENDER
        
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid age (number only).")
        return AWAITING_AGE

async def handle_gender_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gender selection"""
    query = update.callback_query
    await query.answer()
    
    gender_map = {
        "gender_male": "male",
        "gender_female": "female", 
        "gender_nonbinary": "non-binary"
    }
    
    gender = gender_map.get(query.data)
    context.user_data['gender'] = gender
    
    # Interests selection keyboard
    keyboard = [
        [InlineKeyboardButton("💬 Chatting", callback_data="int_chatting"),
         InlineKeyboardButton("🌈 Friends", callback_data="int_friends")],
        [InlineKeyboardButton("💞 Relationship", callback_data="int_relationship"),
         InlineKeyboardButton("❤️ Love", callback_data="int_love")],
        [InlineKeyboardButton("🎮 Games", callback_data="int_games"),
         InlineKeyboardButton("⚡ Anime", callback_data="int_anime")],
        [InlineKeyboardButton("✅ Continue", callback_data="interests_done")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
✅ Gender: **{gender.title()}**

💫 **What are you interested in?**
(Select all that apply, then click Continue)

Selected interests: None yet
"""
    
    if not context.user_data.get('selected_interests'):
        context.user_data['selected_interests'] = set()
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    return AWAITING_INTERESTS

async def handle_interests_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interests selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "interests_done":
        selected = context.user_data.get('selected_interests', set())
        if not selected:
            await query.answer("Please select at least one interest!", show_alert=True)
            return AWAITING_INTERESTS
        
        context.user_data['interests'] = list(selected)
        
        text = f"""
🎯 **Almost done!**

Write a short bio about yourself:
(This helps others know more about you)

Example: "Love traveling and meeting new people! 🌍✈️"
"""
        
        await query.edit_message_text(text)
        return AWAITING_BIO
    
    # Handle interest toggle
    interest_map = {
        "int_chatting": "Chatting",
        "int_friends": "Friends",
        "int_relationship": "Relationship", 
        "int_love": "Love",
        "int_games": "Games",
        "int_anime": "Anime"
    }
    
    selected = context.user_data.get('selected_interests', set())
    interest = interest_map.get(query.data)
    
    if interest in selected:
        selected.remove(interest)
    else:
        selected.add(interest)
    
    context.user_data['selected_interests'] = selected
    
    # Update keyboard with selections
    keyboard = [
        [InlineKeyboardButton(f"{'✅' if 'Chatting' in selected else '💬'} Chatting", callback_data="int_chatting"),
         InlineKeyboardButton(f"{'✅' if 'Friends' in selected else '🌈'} Friends", callback_data="int_friends")],
        [InlineKeyboardButton(f"{'✅' if 'Relationship' in selected else '💞'} Relationship", callback_data="int_relationship"),
         InlineKeyboardButton(f"{'✅' if 'Love' in selected else '❤️'} Love", callback_data="int_love")],
        [InlineKeyboardButton(f"{'✅' if 'Games' in selected else '🎮'} Games", callback_data="int_games"),
         InlineKeyboardButton(f"{'✅' if 'Anime' in selected else '⚡'} Anime", callback_data="int_anime")],
        [InlineKeyboardButton("✅ Continue", callback_data="interests_done")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    selected_text = ", ".join(selected) if selected else "None yet"
    text = f"""
💫 **What are you interested in?**
(Select all that apply, then click Continue)

Selected interests: **{selected_text}**
"""
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    return AWAITING_INTERESTS

async def handle_bio_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bio input"""
    bio = update.message.text.strip()
    
    if len(bio) < 10 or len(bio) > 200:
        await update.message.reply_text(
            "❌ Bio must be between 10-200 characters."
        )
        return AWAITING_BIO
    
    context.user_data['bio'] = bio
    
    # Complete registration
    user_id = update.effective_user.id
    user_data = {
        "display_name": context.user_data['display_name'],
        "age": context.user_data['age'],
        "gender": context.user_data['gender'],
        "interests": context.user_data['interests'],
        "bio": bio,
        "registration_complete": True,
        "is_onboarded": True,
        "created_at": datetime.datetime.utcnow(),
        "posts_count": 0,
        "followers_count": 0,
        "following_count": 0,
        "matches_count": 0,
        "is_premium": False,
        "last_active": datetime.datetime.utcnow()
    }
    
    success = await update_user(user_id, user_data)
    
    if success:
        keyboard = [
            [InlineKeyboardButton("🌐 Open Web App", 
                web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com"))],
            [InlineKeyboardButton("💕 Find Partner", callback_data="find_partner"),
             InlineKeyboardButton("👤 My Profile", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🎉 **Registration Complete!**

✅ **Your Profile:**
👤 Name: {context.user_data['display_name']}
🎂 Age: {context.user_data['age']}
👤 Gender: {context.user_data['gender'].title()}
💫 Interests: {', '.join(context.user_data['interests'])}
📝 Bio: {bio}

🚀 **What's Next?**
• Open the web app for the full Instagram experience
• Start finding partners and making connections
• Share posts and stories
• Play fun games with the community

Welcome to our amazing platform! 🌟
"""
        
        await update.message.reply_text(text, reply_markup=reply_markup, 
                                      reply_keyboard=main_menu_kb())
        
        # Clear registration data
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "❌ Registration failed. Please try again later."
        )
        return ConversationHandler.END

# Profile management
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced profile command"""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data or not user_data.get("registration_complete"):
        keyboard = [[InlineKeyboardButton("🚀 Complete Registration", callback_data="start_registration")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚀 Complete your profile registration first!",
            reply_markup=reply_markup
        )
        return
    
    # Profile stats and info
    stats_text = f"""
👤 **{user_data.get('display_name')}**
🎂 Age: {user_data.get('age')}
👤 Gender: {user_data.get('gender', 'Not set').title()}

📊 **Your Stats:**
📸 Posts: {user_data.get('posts_count', 0)}
👥 Followers: {user_data.get('followers_count', 0)}
➕ Following: {user_data.get('following_count', 0)}
💌 Matches: {user_data.get('matches_count', 0)}

💫 **Interests:** {', '.join(user_data.get('interests', []))}
📝 **Bio:** {user_data.get('bio', 'No bio set')}

🌟 **Status:** {'💎 Premium' if user_data.get('is_premium') else '⭐ Regular'}
📅 **Joined:** {user_data.get('created_at', datetime.datetime.utcnow()).strftime('%B %Y')}
"""
    
    keyboard = [
        [InlineKeyboardButton("🌐 Open Profile", 
            web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com/profile"))],
        [InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile"),
         InlineKeyboardButton("📸 Add Photo", callback_data="add_photo")],
        [InlineKeyboardButton("💎 Upgrade Premium", callback_data="upgrade_premium")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(stats_text, reply_markup=reply_markup)

# Partner matching system
async def find_partner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced partner matching system"""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data or not user_data.get("registration_complete"):
        await update.message.reply_text("❌ Complete registration first! Use /start")
        return
    
    # Find potential matches based on preferences
    match_filter = {
        "tg_user_id": {"$ne": user_id},
        "registration_complete": True
    }
    
    # Add age preferences if set
    if user_data.get('preferred_min_age'):
        match_filter['age'] = {"$gte": user_data['preferred_min_age']}
    if user_data.get('preferred_max_age'):
        if 'age' in match_filter:
            match_filter['age']['$lte'] = user_data['preferred_max_age']
        else:
            match_filter['age'] = {"$lte": user_data['preferred_max_age']}
    
    potential_matches = await db.users.find(match_filter).limit(10).to_list(10)
    
    if not potential_matches:
        keyboard = [
            [InlineKeyboardButton("⚙️ Adjust Preferences", callback_data="adjust_preferences")],
            [InlineKeyboardButton("🌐 Browse Web App", 
                web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com"))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤔 No matches found right now. Try adjusting your preferences or check back later!",
            reply_markup=reply_markup
        )
        return
    
    # Show first match
    match = potential_matches[0]
    match_text = f"""
💕 **Potential Match Found!**

👤 **{match.get('display_name')}**
🎂 Age: {match.get('age')}
👤 Gender: {match.get('gender', 'Not specified').title()}

💫 **Interests:** {', '.join(match.get('interests', []))}
📝 **About:** {match.get('bio', 'No bio available')}

💌 **What would you like to do?**
"""
    
    keyboard = [
        [InlineKeyboardButton("💖 Like", callback_data=f"like_{match['tg_user_id']}"),
         InlineKeyboardButton("👎 Pass", callback_data=f"pass_{match['tg_user_id']}")],
        [InlineKeyboardButton("💬 Send Message", callback_data=f"message_{match['tg_user_id']}")],
        [InlineKeyboardButton("🔄 Next Match", callback_data="next_match")],
        [InlineKeyboardButton("🌐 View on Web", 
            web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['current_matches'] = potential_matches
    context.user_data['match_index'] = 0
    
    await update.message.reply_text(match_text, reply_markup=reply_markup)

# Fun & Games system
async def fun_games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fun & Games hub"""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data or not user_data.get("registration_complete"):
        await update.message.reply_text("❌ Complete registration first! Use /start")
        return
    
    games_text = """
🎮 **Fun & Games Hub**

Welcome to our entertainment zone! Choose your adventure:

🎲 **Games & Activities:**
• Truth or Dare challenges
• Would You Rather questions  
• Personality quizzes
• Community polls
• Photo challenges

🏆 **Competitions:**
• Weekly contests
• Leaderboards
• Achievement badges
• Special rewards

🎪 **Community Events:**
• Group games
• Themed discussions
• Story sharing sessions
• Live events

💎 **Premium Games:**
• Exclusive challenges
• Premium rewards
• VIP access
• Special features

What would you like to try?
"""
    
    keyboard = [
        [InlineKeyboardButton("🎲 Truth or Dare", callback_data="game_truth_dare"),
         InlineKeyboardButton("🤔 Would You Rather", callback_data="game_wyr")],
        [InlineKeyboardButton("📊 Community Polls", callback_data="game_polls"),
         InlineKeyboardButton("🏆 Challenges", callback_data="game_challenges")],
        [InlineKeyboardButton("🎪 Live Events", callback_data="game_events"),
         InlineKeyboardButton("💎 Premium Games", callback_data="game_premium")],
        [InlineKeyboardButton("🌐 Play on Web", 
            web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(games_text, reply_markup=reply_markup)

# Public feed system
async def public_feed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Public feed with posts and stories"""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data or not user_data.get("registration_complete"):
        await update.message.reply_text("❌ Complete registration first! Use /start")
        return
    
    # Get recent posts
    posts = await db.posts.find().sort("created_at", -1).limit(5).to_list(5)
    
    # Get active stories (last 24 hours)
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    stories_count = await db.stories.count_documents({"created_at": {"$gt": cutoff}})
    
    feed_text = f"""
🌹 **Public Feed**

📸 **Recent Activity:**
• {len(posts)} new posts today
• {stories_count} active stories
• {await db.users.count_documents({'registration_complete': True})} community members

🔥 **Trending:**
• Photo challenges
• Community discussions
• Story highlights
• User spotlights

💫 **What's New:**
• Enhanced story features
• Better matching algorithm
• New games and challenges
• Premium rewards system

Ready to explore the community?
"""
    
    keyboard = [
        [InlineKeyboardButton("🌐 Open Full Feed", 
            web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com"))],
        [InlineKeyboardButton("📸 Share Post", callback_data="create_post"),
         InlineKeyboardButton("📱 Add Story", callback_data="create_story")],
        [InlineKeyboardButton("👀 Browse Stories", callback_data="browse_stories"),
         InlineKeyboardButton("🔥 Trending", callback_data="trending")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(feed_text, reply_markup=reply_markup)

# Callback query handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Registration callbacks
    if data == "start_registration":
        return await start_registration_callback(update, context)
    elif data.startswith("gender_"):
        return await handle_gender_selection(update, context)
    elif data.startswith("int_") or data == "interests_done":
        return await handle_interests_selection(update, context)
    
    # Profile callbacks
    elif data == "profile":
        await profile_command(update, context)
    
    # Matching callbacks
    elif data == "find_partner":
        await find_partner_command(update, context)
    elif data.startswith("like_"):
        partner_id = int(data.split("_")[1])
        await handle_like_action(update, context, partner_id)
    elif data.startswith("pass_"):
        await handle_pass_action(update, context)
    elif data == "next_match":
        await show_next_match(update, context)
    
    # Games callbacks  
    elif data == "fun_games":
        await fun_games_command(update, context)
    elif data.startswith("game_"):
        await handle_game_selection(update, context, data)
    
    # Premium callbacks
    elif data == "premium":
        await premium_command(update, context)
    
    return ConversationHandler.END

# Additional helper functions
async def handle_like_action(update: Update, context: ContextTypes.DEFAULT_TYPE, partner_id: int):
    """Handle like action on a potential match"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Record the like
    like_data = {
        "from_user": user_id,
        "to_user": partner_id,
        "created_at": datetime.datetime.utcnow(),
        "type": "like"
    }
    await db.likes.insert_one(like_data)
    
    # Check if it's a mutual match
    existing_like = await db.likes.find_one({
        "from_user": partner_id,
        "to_user": user_id,
        "type": "like"
    })
    
    if existing_like:
        # It's a match!
        match_data = {
            "user1": user_id,
            "user2": partner_id,
            "created_at": datetime.datetime.utcnow(),
            "status": "active"
        }
        await db.matches.insert_one(match_data)
        
        # Update match counts
        await db.users.update_one(
            {"tg_user_id": user_id},
            {"$inc": {"matches_count": 1}}
        )
        await db.users.update_one(
            {"tg_user_id": partner_id},
            {"$inc": {"matches_count": 1}}
        )
        
        keyboard = [
            [InlineKeyboardButton("💬 Start Chat", callback_data=f"chat_{partner_id}")],
            [InlineKeyboardButton("🔄 Find More", callback_data="find_partner")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎉 **IT'S A MATCH!** 💕\n\nYou both liked each other! Start chatting now.",
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text("💖 Like sent! If they like you back, it's a match!")
        # Show next match if available
        await show_next_match(update, context)

async def handle_pass_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pass action on a potential match"""
    await show_next_match(update, context)

async def show_next_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show next potential match"""
    query = update.callback_query
    
    matches = context.user_data.get('current_matches', [])
    current_index = context.user_data.get('match_index', 0) + 1
    
    if current_index >= len(matches):
        keyboard = [[InlineKeyboardButton("🔄 Find More Matches", callback_data="find_partner")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🤔 No more matches right now. Check back later for new people!",
            reply_markup=reply_markup
        )
        return
    
    match = matches[current_index]
    context.user_data['match_index'] = current_index
    
    match_text = f"""
💕 **Potential Match Found!**

👤 **{match.get('display_name')}**
🎂 Age: {match.get('age')}
👤 Gender: {match.get('gender', 'Not specified').title()}

💫 **Interests:** {', '.join(match.get('interests', []))}
📝 **About:** {match.get('bio', 'No bio available')}

💌 **What would you like to do?**
"""
    
    keyboard = [
        [InlineKeyboardButton("💖 Like", callback_data=f"like_{match['tg_user_id']}"),
         InlineKeyboardButton("👎 Pass", callback_data=f"pass_{match['tg_user_id']}")],
        [InlineKeyboardButton("🔄 Next Match", callback_data="next_match")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(match_text, reply_markup=reply_markup)

async def handle_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, game_type: str):
    """Handle game selection"""
    query = update.callback_query
    
    game_responses = {
        "game_truth_dare": {
            "title": "🎲 Truth or Dare",
            "text": "Choose your challenge level:",
            "buttons": [
                [InlineKeyboardButton("😇 Innocent", callback_data="td_innocent"),
                 InlineKeyboardButton("😏 Spicy", callback_data="td_spicy")],
                [InlineKeyboardButton("🔥 Wild", callback_data="td_wild")]
            ]
        },
        "game_wyr": {
            "title": "🤔 Would You Rather",
            "text": "Pick a dilemma and see what others choose!",
            "buttons": [
                [InlineKeyboardButton("💭 Random Question", callback_data="wyr_random")],
                [InlineKeyboardButton("💕 Relationship", callback_data="wyr_love")]
            ]
        },
        "game_polls": {
            "title": "📊 Community Polls",  
            "text": "Vote on community questions and see live results!",
            "buttons": [
                [InlineKeyboardButton("🗳️ Latest Poll", callback_data="poll_latest")],
                [InlineKeyboardButton("📈 Results", callback_data="poll_results")]
            ]
        }
    }
    
    game = game_responses.get(game_type)
    if game:
        keyboard = game["buttons"] + [[InlineKeyboardButton("🔙 Back to Games", callback_data="fun_games")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{game['title']}\n\n{game['text']}",
            reply_markup=reply_markup
        )

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Premium features and upgrade"""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ Complete registration first! Use /start")
        return
    
    is_premium = user_data.get('is_premium', False)
    
    if is_premium:
        premium_text = """
💎 **Premium Member**

You're already enjoying premium benefits! ✨

🌟 **Your Premium Features:**
• Unlimited likes and matches
• Advanced search filters  
• Priority in matching queue
• Exclusive premium games
• No ads in web app
• Premium badge on profile
• Access to premium content
• Priority customer support

💫 **Premium Stats:**
• Premium since: Member
• Features used this month: Active
• Exclusive content accessed: Available

Thank you for being a premium member! 🎉
"""
        
        keyboard = [
            [InlineKeyboardButton("🌐 Premium Web Features", 
                web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com"))],
            [InlineKeyboardButton("👑 Premium Games", callback_data="game_premium")],
            [InlineKeyboardButton("📞 Premium Support", callback_data="premium_support")]
        ]
    else:
        premium_text = """
💎 **Upgrade to Premium**

Unlock amazing features and enhance your experience! ✨

🌟 **Premium Benefits:**
• ♾️ Unlimited likes and matches
• 🔍 Advanced search filters
• ⚡ Priority matching queue
• 🎮 Exclusive premium games
• 🚫 Ad-free web experience
• 👑 Premium badge on profile
• 💫 Access to premium content
• 📞 Priority customer support

💰 **Pricing:**
• Monthly: $9.99/month
• Yearly: $99.99/year (Save 17%!)
• Lifetime: $199.99 (Best Value!)

🎁 **Special Offer:**
First month FREE for new premium users!

Ready to upgrade your social experience?
"""
        
        keyboard = [
            [InlineKeyboardButton("💳 Monthly $9.99", callback_data="premium_monthly"),
             InlineKeyboardButton("📅 Yearly $99.99", callback_data="premium_yearly")],
            [InlineKeyboardButton("♾️ Lifetime $199.99", callback_data="premium_lifetime")],
            [InlineKeyboardButton("🎁 Start Free Trial", callback_data="premium_trial")],
            [InlineKeyboardButton("❓ Learn More", callback_data="premium_info")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(premium_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(premium_text, reply_markup=reply_markup)

# Message handlers for different states
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages and menu buttons"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Check if user is registered
    user_data = await get_user(user_id)
    if not user_data or not user_data.get("registration_complete"):
        keyboard = [[InlineKeyboardButton("🚀 Start Registration", callback_data="start_registration")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👋 Welcome! Please complete registration first to use all features.",
            reply_markup=reply_markup
        )
        return
    
    # Handle menu buttons
    if text == BTN_FIND_PARTNER:
        await find_partner_command(update, context)
    elif text == BTN_MY_PROFILE:
        await profile_command(update, context)
    elif text == BTN_PUBLIC_FEED:
        await public_feed_command(update, context)
    elif text == BTN_FUN_GAMES:
        await fun_games_command(update, context)
    elif text == BTN_PREMIUM:
        await premium_command(update, context)
    elif text in [BTN_MATCH_GIRLS, BTN_MATCH_BOYS]:
        # Set gender preference and find matches
        preferred_gender = "female" if text == BTN_MATCH_GIRLS else "male"
        await update_user(user_id, {"preferred_gender": preferred_gender})
        await find_partner_command(update, context)
    elif text == BTN_FRIENDS:
        await friends_command(update, context)
    elif text == BTN_SETTINGS:
        await settings_command(update, context)
    else:
        # Default response with quick actions
        keyboard = [
            [InlineKeyboardButton("🌐 Open Web App", 
                web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com"))],
            [InlineKeyboardButton("💕 Find Partner", callback_data="find_partner"),
             InlineKeyboardButton("👤 My Profile", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 I'm here to help you connect and have fun!\n\n" +
            "Use the menu buttons below or try:\n" +
            "• /help - See all commands\n" +
            "• /profile - View your profile\n" +
            "• /premium - Upgrade features\n\n" +
            "Or open the web app for the full experience! 🌟",
            reply_markup=reply_markup
        )

async def friends_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Friends and connections management"""
    user_id = update.effective_user.id
    
    # Get user's matches and friends
    matches_count = await db.matches.count_documents({
        "$or": [{"user1": user_id}, {"user2": user_id}],
        "status": "active"
    })
    
    friends_text = f"""
💞 **Friends & Connections**

👥 **Your Network:**
• {matches_count} active matches
• Chat with your connections
• Share posts and stories
• Play games together

🔍 **Discover:**
• Find new friends
• Join community groups
• Connect based on interests
• Meet people nearby

💬 **Activities:**
• Group chats
• Share experiences
• Collaborative games
• Community events

Ready to expand your social circle?
"""
    
    keyboard = [
        [InlineKeyboardButton("💬 My Matches", callback_data="view_matches"),
         InlineKeyboardButton("🔍 Find Friends", callback_data="find_friends")],
        [InlineKeyboardButton("🌐 Social Web App", 
            web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com"))],
        [InlineKeyboardButton("👥 Community", callback_data="community")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(friends_text, reply_markup=reply_markup)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User settings and preferences"""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ Complete registration first! Use /start")
        return
    
    settings_text = f"""
⚙️ **Settings & Preferences**

👤 **Profile Settings:**
• Name: {user_data.get('display_name', 'Not set')}
• Age: {user_data.get('age', 'Not set')}
• Gender: {user_data.get('gender', 'Not set').title()}

🔍 **Matching Preferences:**
• Looking for: {user_data.get('preferred_gender', 'Anyone').title()}
• Age range: {user_data.get('preferred_min_age', 18)}-{user_data.get('preferred_max_age', 80)}
• Distance: {user_data.get('max_distance', 'Unlimited')}

💫 **Interests:** {', '.join(user_data.get('interests', []))}

🔔 **Notifications:**
• New matches: {'✅' if user_data.get('notify_matches', True) else '❌'}
• Messages: {'✅' if user_data.get('notify_messages', True) else '❌'}
• Games: {'✅' if user_data.get('notify_games', True) else '❌'}

🔒 **Privacy:**
• Profile visible: {'✅' if user_data.get('profile_visible', True) else '❌'}
• Show online status: {'✅' if user_data.get('show_online', True) else '❌'}
"""
    
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile"),
         InlineKeyboardButton("🎯 Matching Prefs", callback_data="edit_preferences")],
        [InlineKeyboardButton("🔔 Notifications", callback_data="edit_notifications"),
         InlineKeyboardButton("🔒 Privacy", callback_data="edit_privacy")],
        [InlineKeyboardButton("🌐 Web Settings", 
            web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com/settings"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(settings_text, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comprehensive help system"""
    help_text = """
🤖 **Instagram-Style Social Platform Bot**

🚀 **Getting Started:**
/start - Register and set up your profile
/profile - View and manage your profile
/help - Show this help message

💕 **Dating & Matching:**
• Find Partner - Discover potential matches
• Like/Pass system for connections
• Chat with your matches
• Set preferences for better matches

📱 **Social Features:**
• Share posts and stories
• Like and comment on content
• Follow friends and discover people
• Browse the public feed

🎮 **Fun & Games:**
• Truth or Dare challenges
• Would You Rather questions
• Community polls and quizzes
• Interactive games and contests

💎 **Premium Features:**
• Unlimited likes and matches
• Advanced search filters
• Priority matching
• Exclusive games and content

🌐 **Web Application:**
• Full Instagram-style interface
• Create posts with photos/videos
• Stories with 24-hour expiry
• Advanced social features

📞 **Support:**
• Use /help for guidance
• Check /settings for preferences
• Visit web app for full features
• Premium support available

🎯 **Tips:**
• Complete your profile for better matches
• Be active to increase visibility
• Use interests to find like-minded people
• Try different games to meet people

Ready to start your social journey? Use /start! 🌟
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Get Started", callback_data="start_registration")],
        [InlineKeyboardButton("🌐 Open Web App", 
            web_app=WebAppInfo(url="https://telegram-dating-4.preview.emergentagent.com"))],
        [InlineKeyboardButton("💎 Try Premium", callback_data="premium")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_text, reply_markup=reply_markup)

def main():
    """Run the enhanced bot with all features"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Registration conversation handler
    registration_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_registration_callback, pattern="^start_registration$")],
        states={
            AWAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input)],
            AWAITING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age_input)],
            AWAITING_GENDER: [CallbackQueryHandler(handle_gender_selection, pattern="^gender_")],
            AWAITING_INTERESTS: [CallbackQueryHandler(handle_interests_selection, pattern="^int_|^interests_done$")],
            AWAITING_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bio_input)],
        },
        fallbacks=[CommandHandler("start", start_command)],
    )
    
    # Add handlers
    application.add_handler(registration_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run with polling
    logger.info("🚀 Starting Enhanced Instagram-Style Social Platform Bot...")
    logger.info("💕 Features: Matching, Stories, Games, Premium, Social Feed")
    logger.info("🌐 Web App: https://telegram-dating-4.preview.emergentagent.com")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Bot crashed: {e}")