#!/usr/bin/env python3
"""
Complete Social Platform Telegram Bot
Advanced bot with matching, profiles, stories, games, and social features
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
DB_NAME = os.environ.get("DB_NAME", "social_platform")

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Constants for conversation states
(
    AWAITING_NAME, AWAITING_AGE, AWAITING_GENDER, AWAITING_COUNTRY, AWAITING_CITY, 
    AWAITING_INTERESTS, AWAITING_BIO, AWAITING_PHOTO, PARTNER_SEARCH, CHAT_MODE,
    POST_CONTENT, STORY_CONTENT, COMMENT_MODE
) = range(13)

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

# Interest system with premium interests
INTERESTS = [
    # Free interests
    ("chatting", "💬 Chatting", False),
    ("friends", "🌈 Friends", False), 
    ("relationship", "💞 Relationship", False),
    ("love", "❤️ Love", False),
    ("games", "🎮 Games", False),
    ("anime", "⚡ Anime", False),
    # Premium interests  
    ("intimate", "🚫 Intimate ⭐", True),
    ("vsex", "😈 Virtual Sex ⭐", True),
    ("exchange", "🍓 Exchange ⭐", True),
]

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
            [InlineKeyboardButton("👤 My Profile", callback_data="profile"),
             InlineKeyboardButton("💕 Find Partner", callback_data="find_partner")],
            [InlineKeyboardButton("🎮 Fun & Games", callback_data="fun_games"),
             InlineKeyboardButton("💎 Premium", callback_data="premium")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
🎉 Welcome to LuvHive!

👋 Hi {existing_user.get('display_name', user.first_name)}!

Your social platform is ready:

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

Use the menu buttons below to navigate!
"""
        
        await update.message.reply_text(welcome_text, 
                                      reply_markup=reply_markup,
                                      reply_keyboard=main_menu_kb())
        return
    
    # New user registration
    keyboard = [
        [InlineKeyboardButton("🚀 Start Registration", callback_data="start_registration")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🎉 Welcome to LuvHive!

👋 Hi {user.first_name}!

This is your comprehensive social media platform featuring:

📱 **Social Features:**
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
             InlineKeyboardButton("👩 Female", callback_data="gender_female")]
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

async def handle_country_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country input"""
    country = update.message.text.strip()
    
    if len(country) < 2 or len(country) > 50:
        await update.message.reply_text(
            "❌ Please enter a valid country name (2-50 characters)."
        )
        return AWAITING_COUNTRY
    
    context.user_data['country'] = country.title()
    
    text = f"""
✅ Country: **{country.title()}**

🏙️ **What's your city?**
(Please enter your city name)
"""
    
    await update.message.reply_text(text)
    return AWAITING_CITY

async def handle_city_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle city input"""
    city = update.message.text.strip()
    
    if len(city) < 2 or len(city) > 50:
        await update.message.reply_text(
            "❌ Please enter a valid city name (2-50 characters)."
        )
        return AWAITING_CITY
    
    context.user_data['city'] = city.title()
    
    # Initialize selected interests
    if not context.user_data.get('selected_interests'):
        context.user_data['selected_interests'] = set()
    
    # Move to interests selection
    await handle_gender_selection_direct(update, context)
    return AWAITING_INTERESTS

async def handle_gender_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gender selection"""
    query = update.callback_query
    await query.answer()
    
    gender_map = {
        "gender_male": "male",
        "gender_female": "female"
    }
    
    gender = gender_map.get(query.data)
    context.user_data['gender'] = gender
    
    text = f"""
✅ Gender: **{gender.title()}**

🌍 **What's your country?**
(Please enter your country name)
"""
    
    await query.edit_message_text(text)
    return AWAITING_COUNTRY

async def handle_gender_selection_direct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show interest selector after city"""
    # Initialize selected interests
    if not context.user_data.get('selected_interests'):
        context.user_data['selected_interests'] = set()
    
    # Create interests keyboard in 3x3 layout
    keyboard = []
    selected = context.user_data['selected_interests']
    
    # Create 3 rows of 3 interests each
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            if i + j < len(INTERESTS):
                interest_key, interest_label, is_premium = INTERESTS[i + j]
                display_label = f"✅ {interest_label}" if interest_key in selected else interest_label
                row.append(InlineKeyboardButton(display_label, callback_data=f"int:{interest_key}"))
        keyboard.append(row)
    
    # Add control buttons
    keyboard.extend([
        [InlineKeyboardButton("✅ Select All", callback_data="select_all"),
         InlineKeyboardButton("❌ Remove All", callback_data="remove_all")],
        [InlineKeyboardButton("💾 Save Changes", callback_data="interests_done")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    selected_text = ", ".join([label for key, label, _ in INTERESTS if key in context.user_data.get('selected_interests', set())]) or "None yet"
    
    text = f"""
✅ Gender: **{gender.title()}**

💫 **Select your interests** (toggle & Save):

Selected: **{selected_text}**
"""
    
    await query.edit_message_text(text, reply_markup=reply_markup)
    return AWAITING_INTERESTS

async def handle_interests_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interests selection with premium logic"""
    query = update.callback_query
    await query.answer()
    
    # Initialize selected interests if not exists
    if not context.user_data.get('selected_interests'):
        context.user_data['selected_interests'] = set()
    
    selected = context.user_data['selected_interests']
    
    if query.data == "interests_done":
        # Save interests and continue
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
    
    elif query.data == "select_all":
        # Select all non-premium interests
        for interest_key, _, is_premium in INTERESTS:
            if not is_premium:  # Only select free interests
                selected.add(interest_key)
    
    elif query.data == "remove_all":
        # Remove all interests
        selected.clear()
    
    elif query.data.startswith("int:"):
        # Handle individual interest toggle
        interest_key = query.data[4:]  # Remove "int:" prefix
        
        # DEBUG: Log callback received
        logger.info(f"DEBUG: Interest callback received - interest_key={interest_key}")
        
        # Check if it's a premium interest using the EXACT logic from registration.py
        PREMIUM_KEYS = {"intimate", "vsex", "exchange"}
        
        if interest_key in PREMIUM_KEYS:
            logger.info(f"DEBUG: Premium interest {interest_key} clicked - showing popup")
            # ALWAYS show popup for premium interests (non-premium users)
            await query.answer("⚡⭐ To use this feature you must have a premium subscription.", show_alert=True)
            logger.info(f"DEBUG: Premium popup shown for {interest_key}")
            return AWAITING_INTERESTS
        
        # Toggle interest
        if interest_key in selected:
            selected.remove(interest_key)
        else:
            selected.add(interest_key)
    
    # Update keyboard with current selections in 3x3 layout
    keyboard = []
    
    # Create 3 rows of 3 interests each
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            if i + j < len(INTERESTS):
                interest_key, interest_label, is_premium = INTERESTS[i + j]
                display_label = f"✅ {interest_label}" if interest_key in selected else interest_label
                row.append(InlineKeyboardButton(display_label, callback_data=f"int:{interest_key}"))
        keyboard.append(row)
    
    # Add control buttons
    keyboard.extend([
        [InlineKeyboardButton("✅ Select All", callback_data="select_all"),
         InlineKeyboardButton("❌ Remove All", callback_data="remove_all")],
        [InlineKeyboardButton("💾 Save Changes", callback_data="interests_done")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update selected text
    selected_labels = [label for key, label, _ in INTERESTS if key in selected]
    selected_text = ", ".join(selected_labels) or "None yet"
    
    gender = context.user_data.get('gender', 'Unknown')
    text = f"""
✅ Gender: **{gender.title()}**

💫 **Select your interests** (toggle & Save):

Selected: **{selected_text}**
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
        "country": context.user_data['country'],
        "city": context.user_data['city'],
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
            [InlineKeyboardButton("💕 Find Partner", callback_data="find_partner"),
             InlineKeyboardButton("👤 My Profile", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🎉 **Registration Complete!**

✅ **Your Profile:**
👤 Name: {context.user_data['display_name']}
🎂 Age: {context.user_data['age']}
🌍 Location: {context.user_data['city']}, {context.user_data['country']}
👤 Gender: {context.user_data['gender'].title()}
💫 Interests: {', '.join([label for key, label, _ in INTERESTS if key in context.user_data['interests']])}
📝 Bio: {bio}

🚀 **What's Next?**
• Start finding partners and making connections
• Share posts and stories
• Play fun games with the community

Welcome to LuvHive! 🌟
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

# Enhanced menu handlers
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
        # Open webapp when Public Feed is clicked
        keyboard = [[InlineKeyboardButton("🌐 Open Social Feed", 
            web_app=WebAppInfo(url="https://bot-web-interface.preview.emergentagent.com"))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        feed_text = """
🌹 **Public Feed**

📸 **Discover & Share:**
• Browse community posts and stories
• Share your own content
• Like and comment on posts
• Follow interesting people

🔥 **What's Trending:**
• Latest posts from your network
• Popular stories and content
• Community highlights
• New members to follow

Ready to explore the social feed?
"""
        await update.message.reply_text(feed_text, reply_markup=reply_markup)
        
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
            "Or use the menu to explore! 🌟",
            reply_markup=reply_markup
        )

# Additional command functions (simplified versions)
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
    
    # Get interest labels
    user_interests = user_data.get('interests', [])
    interest_labels = [label for key, label, _ in INTERESTS if key in user_interests]
    
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

💫 **Interests:** {', '.join(interest_labels) if interest_labels else 'None set'}
📝 **Bio:** {user_data.get('bio', 'No bio set')}

🌟 **Status:** {'💎 Premium' if user_data.get('is_premium') else '⭐ Regular'}
📅 **Joined:** {user_data.get('created_at', datetime.datetime.utcnow()).strftime('%B %Y')}
"""
    
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile"),
         InlineKeyboardButton("📸 Add Photo", callback_data="add_photo")],
        [InlineKeyboardButton("💎 Upgrade Premium", callback_data="premium")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(stats_text, reply_markup=reply_markup)

async def find_partner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Partner matching system"""
    await update.message.reply_text(
        "💕 **Finding Partners...**\n\nThis feature is being enhanced! Use the web app for full matching experience.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🌐 Open Matching", 
                web_app=WebAppInfo(url="https://bot-web-interface.preview.emergentagent.com"))
        ]])
    )

async def fun_games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fun & Games hub"""
    games_text = """
🎮 **Fun & Games Hub**

Choose your entertainment:

🎲 **Interactive Games:**
• Truth or Dare challenges
• Would You Rather questions  
• Personality quizzes
• Community polls

🏆 **Competitions:**
• Weekly contests
• Leaderboards
• Achievement badges
• Special rewards

What would you like to try?
"""
    
    keyboard = [
        [InlineKeyboardButton("🎲 Truth or Dare", callback_data="game_truth_dare"),
         InlineKeyboardButton("🤔 Would You Rather", callback_data="game_wyr")],
        [InlineKeyboardButton("📊 Community Polls", callback_data="game_polls")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(games_text, reply_markup=reply_markup)

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Premium features"""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    is_premium = user_data.get('is_premium', False) if user_data else False
    
    if is_premium:
        text = "💎 **Premium Member** ✨\n\nYou're enjoying all premium benefits!"
        keyboard = [[InlineKeyboardButton("👑 Premium Games", callback_data="game_premium")]]
    else:
        text = """
💎 **Upgrade to Premium**

Unlock amazing features! ✨

🌟 **Premium Benefits:**
• ♾️ Unlimited likes and matches
• 🔍 Advanced search filters
• ⚡ Priority matching queue
• 🎮 Exclusive premium games
• 🚫 Ad-free experience
• 👑 Premium badge on profile
• 💫 Access to premium interests
• 📞 Priority customer support

💰 **Pricing:**
• Monthly: $9.99/month
• Yearly: $99.99/year (Save 17%!)

Ready to upgrade?
"""
        keyboard = [
            [InlineKeyboardButton("💳 Monthly $9.99", callback_data="premium_monthly"),
             InlineKeyboardButton("📅 Yearly $99.99", callback_data="premium_yearly")],
            [InlineKeyboardButton("🎁 Start Free Trial", callback_data="premium_trial")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

async def friends_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Friends system"""
    text = """
💞 **Friends & Connections**

👥 **Your Network:**
• Connect with matches
• Chat with friends
• Share experiences
• Play games together

Ready to expand your social circle?
"""
    
    keyboard = [[InlineKeyboardButton("🌐 Open Social Network", 
        web_app=WebAppInfo(url="https://bot-web-interface.preview.emergentagent.com"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Settings command"""
    text = """
⚙️ **Settings & Preferences**

Manage your account settings and preferences.

Use the web app for full settings control.
"""
    
    keyboard = [[InlineKeyboardButton("🌐 Open Settings", 
        web_app=WebAppInfo(url="https://bot-web-interface.preview.emergentagent.com"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup)

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
    elif data.startswith("int:") or data in ["interests_done", "select_all", "remove_all"]:
        return await handle_interests_selection(update, context)
    
    # Profile callbacks
    elif data == "profile":
        await profile_command(update, context)
    
    # Other callbacks
    elif data == "find_partner":
        await find_partner_command(update, context)
    elif data == "fun_games":
        await fun_games_command(update, context)
    elif data == "premium":
        await premium_command(update, context)
    elif data.startswith("game_"):
        await query.edit_message_text("🎮 Game feature coming soon! Use web app for games.")
    elif data.startswith("premium_"):
        await query.edit_message_text("💎 Premium subscription coming soon!")
    
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """
🤖 **Social Platform Bot**

🚀 **Getting Started:**
/start - Register and set up your profile
/profile - View and manage your profile
/help - Show this help message

💕 **Features:**
• Smart partner matching system
• Interactive social feed
• Fun games and challenges
• Premium features available

🌐 **Web App:**
Use menu buttons to access the full web application with all features!

Ready to start your social journey? 🌟
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Get Started", callback_data="start_registration")],
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
            AWAITING_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_country_input)],
            AWAITING_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_city_input)],
            AWAITING_GENDER: [CallbackQueryHandler(handle_gender_selection, pattern="^gender_")],
            AWAITING_INTERESTS: [CallbackQueryHandler(handle_interests_selection, pattern="^int:|^interests_done$|^select_all$|^remove_all$")],
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
    logger.info("🚀 Starting Enhanced Social Platform Bot...")
    logger.info("💕 Features: Matching, Stories, Games, Premium, Social Feed")
    logger.info("🌐 Web App: https://bot-web-interface.preview.emergentagent.com")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Bot crashed: {e}")