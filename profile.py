"""
Profile module for bot user profiles
"""
import registration as reg
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def init_profile_db():
    """Initialize profile database tables"""
    # Profile functionality is handled by registration module
    pass

def profile_text(uid, uname):
    """Generate profile text for user"""
    user_data = reg.get_user_data(uid)
    
    if not user_data:
        return "👤 Please complete registration first using /start"
    
    name = user_data.get('name', 'User')
    age = user_data.get('age', 'Not set')
    gender = user_data.get('gender', 'Not set')
    
    text = f"👤 **Your Profile**\n\n"
    text += f"👋 Name: {name}\n"
    text += f"🎂 Age: {age}\n"
    text += f"⚧ Gender: {gender}\n"
    
    if uname:
        text += f"📱 Username: @{uname}\n"
    
    return text

def profile_keyboard():
    """Generate profile keyboard"""
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Profile", callback_data="edit_profile")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("« Back to Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)
