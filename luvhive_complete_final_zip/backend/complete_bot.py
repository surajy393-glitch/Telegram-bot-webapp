#!/usr/bin/env python3
"""
Complete Social Platform Telegram Bot - Exact Match to Original
Registration: GENDER → AGE → COUNTRY → CITY → INTERESTS  
Premium popup from settings.py, exact registration flow
"""

import os
import logging
import asyncio
import datetime
from typing import Optional, List, Dict, Any
import json

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, 
    ContextTypes, filters, ConversationHandler
)

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

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

# Constants - Exact match from registration.py
INTERESTS = [
    ("chatting",     "Chatting",     "💬", False),
    ("friends",      "Friends",      "🌈", False), 
    ("relationship", "Relationship", "💞", False),
    ("love",         "Love",         "❤️", False),
    ("games",        "Games",        "🎮", False),
    ("anime",        "Anime",        "⚡", False),
    ("intimate",     "Intimate",     "🚫", True),
    ("vsex",         "Virtual Sex",  "😈", True),
    ("exchange",     "Exchange",     "🍓", True),
]

PREMIUM_KEYS = {"intimate", "vsex", "exchange"}
PREMIUM_POPUP = "⚡⭐ To use this feature you must have a premium subscription."

# Menu buttons
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

# Database helpers
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

def is_registered(user_id: int) -> bool:
    """Check if user is registered - simplified for demo"""
    # In real implementation, this would check database
    return False  # Force registration for demo

# Registration system - EXACT match to original
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - leads to registration or main menu"""
    user = update.effective_user
    user_id = user.id
    
    # Check if user exists and is registered
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
        
        welcome_text = f"🎉 Welcome back to Social Platform!\n\n👋 Hi {existing_user.get('display_name', user.first_name)}!"
        
        await update.message.reply_text(welcome_text, 
                                      reply_markup=reply_markup,
                                      reply_keyboard=main_menu_kb())
        return
    
    # Start registration for new/incomplete users
    await start_registration(update, context)

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start registration flow - EXACT match to registration.py"""
    uid = update.effective_user.id
    
    # Initialize registration data
    context.user_data["premium"] = False  # Default non-premium
    context.user_data["sel_interests"] = set()
    context.user_data["reg_state"] = "GENDER" 
    context.user_data["reg"] = {"gender": None, "age": None, "country": None, "city": None}
    
    # Hide menu keyboard during registration
    await update.message.reply_text("…", reply_markup=ReplyKeyboardRemove())
    
    logger.info(f"{uid} REG:start")
    
    # Ask gender with inline buttons - NO NON-BINARY (as requested)
    await update.message.reply_text(
        "👋 Let's set up your profile.\n\n"
        "🔒 **IMPORTANT NOTICE:**\n"
        "Gender selection is **PERMANENT** and cannot be changed later.\n"
        "This policy ensures security and matching accuracy.\n"
        "Please choose carefully.\n\n"
        "What's your **gender**?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("I'm Male", callback_data="gender_male"),
             InlineKeyboardButton("I'm Female", callback_data="gender_female")]
        ]),
        parse_mode="Markdown"
    )

async def handle_registration_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle registration text inputs - EXACT flow: GENDER → AGE → COUNTRY → CITY → INTERESTS"""
    txt = (update.message.text or "").strip()
    state = context.user_data.get("reg_state")
    
    if not state:
        return await start_registration(update, context)
    
    data = context.user_data.setdefault(
        "reg",
        {"gender": None, "age": None, "country": None, "city": None},
    )
    
    # ---- AGE ----
    if state == "AGE":
        if not txt.isdigit():
            return await update.message.reply_text("Please send your age as a number (13–99).")
        age = int(txt)
        if age < 13 or age > 99:
            return await update.message.reply_text("Please send an age between 13 and 99.")
        
        data["age"] = age
        context.user_data["reg_state"] = "COUNTRY"
        return await update.message.reply_text("Great! What's your **country**?", parse_mode="Markdown")
    
    # ---- COUNTRY ----
    if state == "COUNTRY":
        if len(txt) < 2:
            return await update.message.reply_text("Please enter a valid country.")
        data["country"] = txt.title()
        
        context.user_data["reg_state"] = "CITY"
        return await update.message.reply_text("And your **city**?", parse_mode="Markdown")
    
    # ---- CITY ----
    if state == "CITY":
        if len(txt) < 2:
            return await update.message.reply_text("Please enter a valid city.")
        data["city"] = txt.title()
        
        # Move to INTERESTS
        context.user_data["reg_state"] = "INTERESTS"
        context.user_data["sel_interests"] = set()
        return await show_interest_selector(update, context)
    
    # ---- INTERESTS ----
    # Text is ignored while selecting interests (buttons handle it)
    if state == "INTERESTS":
        return
    
    # Fallback
    return await start_registration(update, context)

async def show_interest_selector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show interest selection with 3x3 layout and premium handling"""
    selected = context.user_data.get("sel_interests", set())
    premium_user = context.user_data.get("premium", False)
    
    # Create 3x3 keyboard layout
    keyboard = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            if i + j < len(INTERESTS):
                key, label, emoji, is_premium = INTERESTS[i + j]
                # Show checkmark if selected
                display_emoji = "✅" if key in selected else emoji
                display_text = f"{display_emoji} {label}"
                if is_premium:
                    display_text += " ⭐"
                row.append(InlineKeyboardButton(display_text, callback_data=f"int:{key}"))
        keyboard.append(row)
    
    # Add control buttons
    keyboard.extend([
        [InlineKeyboardButton("✅ Select All", callback_data="select_all"),
         InlineKeyboardButton("❌ Remove All", callback_data="remove_all")],
        [InlineKeyboardButton("💾 Save Changes", callback_data="interests_done")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Create selected text
    selected_labels = []
    for key, label, emoji, is_premium in INTERESTS:
        if key in selected:
            selected_labels.append(f"{emoji} {label}")
    
    selected_text = ", ".join(selected_labels) if selected_labels else "None yet"
    
    text = f"⭐ Select your interests (toggle & Save):\n\nSelected: **{selected_text}**"
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# Callback handlers
async def handle_gender_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gender selection callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = context.user_data.get("reg", {})
    
    if query.data == "gender_male":
        data["gender"] = "male"
    elif query.data == "gender_female":
        data["gender"] = "female"
    
    context.user_data["reg_state"] = "AGE"
    await query.edit_message_text("✅ Gender saved.\n\nHow old are you? (Enter a number)")

async def handle_interests_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interest selection callbacks with premium logic"""
    query = update.callback_query
    data = query.data
    
    logger.info(f"DEBUG: Interest callback received - data={data}")
    
    selected = context.user_data.get("sel_interests", set())
    premium_user = context.user_data.get("premium", False)
    
    if data == "interests_done":
        # Complete registration
        if not selected:
            await query.answer("Please select at least one interest!", show_alert=True)
            return
        
        await query.answer()
        return await complete_registration(update, context)
    
    elif data == "select_all":
        # Select all non-premium interests only
        for key, _, _, is_premium in INTERESTS:
            if not is_premium:
                selected.add(key)
        await query.answer()
    
    elif data == "remove_all":
        # Remove all interests
        selected.clear()
        await query.answer()
    
    elif data.startswith("int:"):
        # Handle individual interest toggle
        interest_key = data[4:]  # Remove "int:" prefix
        
        logger.info(f"DEBUG: Interest key={interest_key}, Premium user={premium_user}")
        
        # PREMIUM CHECK - EXACT match to settings_handlers.py line 366
        if interest_key in PREMIUM_KEYS and not premium_user:
            logger.info(f"DEBUG: Showing premium popup for {interest_key}")
            await query.answer(PREMIUM_POPUP, show_alert=True)
            return
        
        # Toggle interest
        await query.answer()
        if interest_key in selected:
            selected.remove(interest_key)
        else:
            selected.add(interest_key)
    
    # Update the keyboard
    context.user_data["sel_interests"] = selected
    await show_interest_selector(update, context)

async def complete_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Complete registration and save to database"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    reg_data = context.user_data.get("reg", {})
    interests = list(context.user_data.get("sel_interests", set()))
    
    # Create user document
    user_doc = {
        "tg_user_id": user_id,
        "first_name": update.effective_user.first_name,
        "last_name": update.effective_user.last_name,
        "username": update.effective_user.username,
        "gender": reg_data.get("gender"),
        "age": reg_data.get("age"),
        "country": reg_data.get("country"),
        "city": reg_data.get("city"),
        "interests": interests,
        "registration_complete": True,
        "created_at": datetime.datetime.utcnow(),
        "posts_count": 0,
        "followers_count": 0,
        "following_count": 0,
        "matches_count": 0,
        "is_premium": False,
        "last_active": datetime.datetime.utcnow()
    }
    
    success = await update_user(user_id, user_doc) or await create_user(user_doc)
    
    if success:
        # Clear registration data
        context.user_data.clear()
        
        keyboard = [
            [InlineKeyboardButton("💕 Find Partner", callback_data="find_partner"),
             InlineKeyboardButton("👤 My Profile", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Registration completed 🎉\nWelcome To Social Platform 💞",
            reply_markup=reply_markup
        )
        
        # Send main menu
        await query.message.reply_text(
            "🎉 **Registration Complete!**\n\n"
            "Use the menu buttons below to explore:",
            reply_keyboard=main_menu_kb(),
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text("❌ Registration failed. Please try again later.")

# Menu handlers  
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu buttons and messages"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Check if in registration flow
    if context.user_data.get("reg_state"):
        return await handle_registration_text(update, context)
    
    # Check if user is registered
    user_data = await get_user(user_id)
    if not user_data or not user_data.get("registration_complete"):
        return await start_registration(update, context)
    
    # Handle menu buttons
    if text == BTN_PUBLIC_FEED:
        keyboard = [[InlineKeyboardButton("🌐 Open Social Feed", 
            web_app=WebAppInfo(url="https://tg-bot-profile-debug.preview.emergentagent.com"))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🌹 **Public Feed**\n\n"
            "📸 **Discover & Share:**\n"
            "• Browse community posts and stories\n"
            "• Share your own content\n"
            "• Like and comment on posts\n\n"
            "Ready to explore the social feed?",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif text == BTN_MY_PROFILE:
        await show_profile(update, context)
    
    elif text == BTN_PREMIUM:
        await show_premium(update, context)
    
    else:
        # Default response
        keyboard = [
            [InlineKeyboardButton("💕 Find Partner", callback_data="find_partner"),
             InlineKeyboardButton("👤 My Profile", callback_data="profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 I'm here to help you connect and have fun!\n\n"
            "Use the menu buttons below to explore! 🌟",
            reply_markup=reply_markup
        )

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile"""
    user_id = update.effective_user.id
    user_data = await get_user(user_id)
    
    if not user_data:
        return await update.message.reply_text("❌ Profile not found. Please register first.")
    
    interests_text = ", ".join([f"{emoji} {label}" for key, label, emoji, _ in INTERESTS if key in user_data.get("interests", [])])
    
    profile_text = f"""
👤 **{update.effective_user.first_name}**
🎂 Age: {user_data.get('age')}
👤 Gender: {user_data.get('gender', 'Not set').title()}
🌍 Location: {user_data.get('city', 'Unknown')}, {user_data.get('country', 'Unknown')}

📊 **Stats:**
📸 Posts: {user_data.get('posts_count', 0)}
👥 Followers: {user_data.get('followers_count', 0)}
💌 Matches: {user_data.get('matches_count', 0)}

💫 **Interests:** {interests_text or 'None set'}

🌟 **Status:** {'💎 Premium' if user_data.get('is_premium') else '⭐ Regular'}
"""
    
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile")],
        [InlineKeyboardButton("💎 Upgrade Premium", callback_data="premium")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(profile_text, reply_markup=reply_markup, parse_mode="Markdown")

async def show_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show premium features"""
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
        [InlineKeyboardButton("💳 Monthly $9.99", callback_data="premium_monthly")],
        [InlineKeyboardButton("📅 Yearly $99.99", callback_data="premium_yearly")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# Main callback router
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    data = query.data
    
    logger.info(f"DEBUG: Callback received - {data}")
    
    # Gender callbacks
    if data.startswith("gender_"):
        return await handle_gender_callback(update, context)
    
    # Interest callbacks
    elif data.startswith("int:") or data in ["interests_done", "select_all", "remove_all"]:
        return await handle_interests_callback(update, context)
    
    # Other callbacks
    elif data == "profile":
        await query.answer()
        await show_profile(update, context)
    
    elif data == "premium":
        await query.answer()
        await show_premium(update, context)
    
    else:
        await query.answer("Feature coming soon!")

def main():
    """Run the complete bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_callbacks))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Run with polling
    logger.info("🚀 Starting Complete Social Platform Bot...")
    logger.info("💕 Features: Registration, Matching, Premium, Social Feed")
    logger.info("🌐 Web App: https://tg-bot-profile-debug.preview.emergentagent.com")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Bot crashed: {e}")