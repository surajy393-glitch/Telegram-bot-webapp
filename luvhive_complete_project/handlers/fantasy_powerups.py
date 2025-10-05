# handlers/fantasy_powerups.py - POWER FEATURES FOR ULTIMATE ENGAGEMENT!
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
import registration as reg
from .fantasy_match import _exec
import random

log = logging.getLogger("fantasy_powerups")

# ACHIEVEMENT SYSTEM (MY ADDITION!)
FANTASY_ACHIEVEMENTS = {
    "heartbreaker": {
        "name": "💔 Heartbreaker",
        "description": "Get 50+ reactions on a single fantasy",
        "requirement": 50,
        "reward_stars": 100,
        "emoji": "💔"
    },
    "conversation_master": {
        "name": "💬 Conversation Master", 
        "description": "Complete 10 successful fantasy chats",
        "requirement": 10,
        "reward_stars": 200,
        "emoji": "💬"
    },
    "five_star_fantasy": {
        "name": "⭐ Five Star Fantasy",
        "description": "Maintain 5.0 rating across 5+ chats",
        "requirement": 5.0,
        "reward_stars": 300,
        "emoji": "⭐"
    },
    "fantasy_royalty": {
        "name": "👑 Fantasy Royalty",
        "description": "Reach #1 on weekly leaderboard",
        "requirement": 1,
        "reward_stars": 500,
        "emoji": "👑"
    },
    "midnight_dreamer": {
        "name": "🌙 Midnight Dreamer",
        "description": "Complete 5 chats after midnight",
        "requirement": 5,
        "reward_stars": 150,
        "emoji": "🌙"
    },
    "fantasy_explorer": {
        "name": "🗺️ Fantasy Explorer",
        "description": "Try all 5 fantasy categories",
        "requirement": 5,
        "reward_stars": 250,
        "emoji": "🗺️"
    }
}

# FANTASY EVENTS (MY ADDITION!)
FANTASY_EVENTS = {
    "full_moon": {
        "name": "🌕 Full Moon Fantasy Night",
        "description": "Extra mysterious and magical fantasies!",
        "bonus": "2x compatibility matching",
        "duration_hours": 6
    },
    "valentine_special": {
        "name": "💕 Valentine's Fantasy Festival", 
        "description": "Romance is in the air!",
        "bonus": "Free chat extensions",
        "duration_hours": 24
    },
    "halloween_spooky": {
        "name": "🎃 Halloween Horror Fantasies",
        "description": "Spooky, scary, supernatural fantasies!",
        "bonus": "Exclusive spooky categories",
        "duration_hours": 48
    },
    "summer_nights": {
        "name": "🏖️ Summer Fantasy Nights",
        "description": "Hot summer fantasy adventures!",
        "bonus": "Extended 45-minute chats",
        "duration_hours": 72
    }
}

# FANTASY TREASURE HUNT (MY ADDITION!)
TREASURE_HUNT_CLUES = [
    {
        "clue": "Find a fantasy with 'moonlight' in the description",
        "reward": 25,
        "hint": "Look for romantic evening fantasies"
    },
    {
        "clue": "Match with someone from a different continent", 
        "reward": 50,
        "hint": "Check user profiles for location hints"
    },
    {
        "clue": "Complete a 30-minute chat without extensions",
        "reward": 75,
        "hint": "Focus on deep conversation"
    },
    {
        "clue": "Get 5 'amazing' reactions in one day",
        "reward": 100,
        "hint": "Post high-quality fantasies"
    }
]

def ensure_powerup_tables():
    """Create power-up database tables"""
    # User achievements
    _exec("""
      CREATE TABLE IF NOT EXISTS fantasy_achievements (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        achievement_key TEXT NOT NULL,
        earned_at TIMESTAMPTZ DEFAULT NOW(),
        stars_earned INTEGER DEFAULT 0,
        UNIQUE(user_id, achievement_key)
      )
    """)
    
    # Weekly leaderboards
    _exec("""
      CREATE TABLE IF NOT EXISTS fantasy_leaderboard (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        week_start DATE NOT NULL,
        total_reactions INTEGER DEFAULT 0,
        total_matches INTEGER DEFAULT 0,
        total_chats INTEGER DEFAULT 0,
        success_rate DECIMAL(5,2) DEFAULT 0.0,
        rank_position INTEGER DEFAULT 999,
        UNIQUE(user_id, week_start)
      )
    """)
    
    # Fantasy events
    _exec("""
      CREATE TABLE IF NOT EXISTS fantasy_events (
        id SERIAL PRIMARY KEY,
        event_key TEXT NOT NULL,
        start_time TIMESTAMPTZ NOT NULL,
        end_time TIMESTAMPTZ NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        participants_count INTEGER DEFAULT 0
      )
    """)
    
    # Treasure hunt progress
    _exec("""
      CREATE TABLE IF NOT EXISTS fantasy_treasure_hunt (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        clue_index INTEGER NOT NULL,
        completed_at TIMESTAMPTZ DEFAULT NOW(),
        stars_earned INTEGER DEFAULT 0,
        UNIQUE(user_id, clue_index)
      )
    """)

async def check_and_award_achievements(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check and award achievements to user (MY ADDITION!)"""
    ensure_powerup_tables()
    
    # Get user stats for achievement checking
    stats_query = """
        SELECT 
            COUNT(DISTINCT f.id) as total_fantasies,
            COALESCE(SUM(fs.reactions_count), 0) as total_reactions,
            COALESCE(SUM(fs.matches_count), 0) as total_matches,
            COALESCE(AVG(fs.success_rate), 0) as avg_success_rate,
            MAX(fs.reactions_count) as max_reactions_single
        FROM fantasy_submissions f
        LEFT JOIN fantasy_stats fs ON f.id = fs.fantasy_id
        WHERE f.user_id = %s AND f.active = TRUE
    """
    
    stats_row = _exec(stats_query, (user_id,))
    if not stats_row or stats_row is True:
        return
    
    stats = stats_row[0]
    total_fantasies, total_reactions, total_matches, avg_success_rate, max_reactions = stats
    
    new_achievements = []
    
    # Check Heartbreaker achievement
    if max_reactions >= 50:
        if await award_achievement(user_id, "heartbreaker"):
            new_achievements.append("heartbreaker")
    
    # Check Conversation Master
    if total_matches >= 10:
        if await award_achievement(user_id, "conversation_master"):
            new_achievements.append("conversation_master")
    
    # Check Five Star Fantasy  
    if avg_success_rate >= 5.0 and total_matches >= 5:
        if await award_achievement(user_id, "five_star_fantasy"):
            new_achievements.append("five_star_fantasy")
    
    # Check Fantasy Explorer (all categories)
    category_count = _exec("SELECT COUNT(DISTINCT vibe) FROM fantasy_submissions WHERE user_id=%s", (user_id,))
    if category_count and category_count is not True and category_count[0][0] >= 5:
        if await award_achievement(user_id, "fantasy_explorer"):
            new_achievements.append("fantasy_explorer")
    
    # Notify user of new achievements
    if new_achievements:
        await notify_new_achievements(user_id, new_achievements, context)

async def award_achievement(user_id: int, achievement_key: str) -> bool:
    """Award achievement to user and return True if new"""
    try:
        achievement = FANTASY_ACHIEVEMENTS[achievement_key]
        
        result = _exec("""
            INSERT INTO fantasy_achievements (user_id, achievement_key, stars_earned, earned_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (user_id, achievement_key) DO NOTHING
            RETURNING id
        """, (user_id, achievement_key, achievement["reward_stars"]))
        
        return result and result is not True
    except Exception as e:
        log.error(f"Failed to award achievement {achievement_key}: {e}")
        return False

async def notify_new_achievements(user_id: int, achievement_keys: list, context: ContextTypes.DEFAULT_TYPE):
    """Notify user of new achievements (MY ADDITION!)"""
    text = "🏆 **NEW ACHIEVEMENTS UNLOCKED!** 🏆\n\n"
    total_stars = 0
    
    for key in achievement_keys:
        achievement = FANTASY_ACHIEVEMENTS[key]
        text += f"{achievement['emoji']} **{achievement['name']}**\n"
        text += f"   {achievement['description']}\n"
        text += f"   💰 Reward: {achievement['reward_stars']} Stars\n\n"
        total_stars += achievement["reward_stars"]
    
    text += f"🌟 **Total Earned: {total_stars} Stars!** 🌟\n\n"
    text += "Keep creating amazing fantasies to unlock more achievements!"
    
    keyboard = [[InlineKeyboardButton("🏆 View All Achievements", callback_data="powerups:achievements")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(user_id, text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    except Exception as e:
        log.error(f"Failed to notify achievements: {e}")

async def cmd_fantasy_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show weekly fantasy leaderboard (MY ADDITION!)"""
    if not update.effective_user or not update.message:
        return
    
    ensure_powerup_tables()
    
    # Get current week's leaderboard
    week_start = datetime.utcnow().date() - timedelta(days=datetime.utcnow().weekday())
    
    leaderboard_query = """
        SELECT l.user_id, l.total_reactions, l.total_matches, l.success_rate, l.rank_position
        FROM fantasy_leaderboard l
        WHERE l.week_start = %s
        ORDER BY l.rank_position ASC
        LIMIT 10
    """
    
    rows = _exec(leaderboard_query, (week_start,))
    
    text = "👑 **WEEKLY FANTASY KINGS & QUEENS** 👑\n\n"
    text += f"Week of {week_start.strftime('%B %d, %Y')}\n\n"
    
    if not rows or rows is True:
        text += "No rankings yet this week!\nBe the first to dominate the Fantasy Board! 🔥"
    else:
        rank_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i, row in enumerate(rows):
            user_id, reactions, matches, success_rate, rank = row
            emoji = rank_emojis[i] if i < len(rank_emojis) else "🏅"
            
            # Get username (simplified)
            username = f"User{str(user_id)[-4:]}"  # Last 4 digits for anonymity
            
            text += f"{emoji} **{username}**\n"
            text += f"   ❤️ {reactions} reactions | 💬 {matches} matches | ⭐ {success_rate:.1f}%\n\n"
    
    text += "\n🎁 **Weekly Prizes:**\n"
    text += "🥇 Winner: FREE Premium Week!\n"
    text += "🥈 2nd: 500 Free Stars\n"
    text += "🥉 3rd: 250 Free Stars\n\n"
    text += "💪 Keep posting amazing fantasies to climb the ranks!"
    
    keyboard = [
        [InlineKeyboardButton("📊 My Ranking", callback_data="powerups:my_rank")],
        [InlineKeyboardButton("🏆 Achievements", callback_data="powerups:achievements")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def cmd_fantasy_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active fantasy events (MY ADDITION!)"""
    if not update.effective_user or not update.message:
        return
    
    ensure_powerup_tables()
    
    # Get active events
    active_events = _exec("""
        SELECT event_key, start_time, end_time, participants_count
        FROM fantasy_events 
        WHERE is_active = TRUE AND end_time > NOW()
        ORDER BY start_time ASC
    """)
    
    text = "🎉 **FANTASY EVENTS** 🎉\n\n"
    
    if not active_events or active_events is True:
        text += "No active events right now.\nCheck back soon for amazing fantasy events! ✨\n\n"
        
        # Show upcoming event preview
        text += "🗓️ **UPCOMING EVENTS:**\n"
        text += "🌕 Full Moon Fantasy Night - This Friday\n"
        text += "💕 Valentine's Special - February 14th\n"
        text += "🎃 Halloween Horror Night - October 31st\n"
    else:
        for row in active_events:
            event_key, start_time, end_time, participants = row
            event = FANTASY_EVENTS.get(event_key, {"name": "Mystery Event", "description": "Special event!", "bonus": "Unknown"})
            
            time_left = end_time - datetime.utcnow()
            hours_left = int(time_left.total_seconds() / 3600)
            
            text += f"🎯 **{event['name']}**\n"
            text += f"   {event['description']}\n"
            text += f"   💫 Bonus: {event['bonus']}\n"
            text += f"   👥 {participants} participants\n"
            text += f"   ⏰ {hours_left}h remaining\n\n"
    
    # Show current treasure hunt
    text += "🗺️ **FANTASY TREASURE HUNT** 🗺️\n"
    text += "Complete daily challenges to earn bonus stars!\n\n"
    
    # Get user's current treasure hunt progress
    user_progress = _exec("SELECT COUNT(*) FROM fantasy_treasure_hunt WHERE user_id=%s", (update.effective_user.id,))
    completed_clues = user_progress[0][0] if user_progress and user_progress is not True else 0
    
    if completed_clues < len(TREASURE_HUNT_CLUES):
        current_clue = TREASURE_HUNT_CLUES[completed_clues]
        text += f"🎯 **Current Challenge:**\n"
        text += f"   {current_clue['clue']}\n"
        text += f"   💰 Reward: {current_clue['reward']} Stars\n"
        text += f"   💡 Hint: {current_clue['hint']}\n\n"
    else:
        text += "🏆 All challenges completed! Check back tomorrow for new ones.\n\n"
    
    text += f"📈 Your Progress: {completed_clues}/{len(TREASURE_HUNT_CLUES)} completed"
    
    keyboard = [
        [InlineKeyboardButton("🎯 Join Event", callback_data="powerups:join_event")],
        [InlineKeyboardButton("🗺️ Treasure Progress", callback_data="powerups:treasure_hunt")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def start_fantasy_event(event_key: str, duration_hours: int = 24):
    """Start a fantasy event (MY ADDITION!)"""
    ensure_powerup_tables()
    
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=duration_hours)
    
    _exec("""
        INSERT INTO fantasy_events (event_key, start_time, end_time, is_active, participants_count)
        VALUES (%s, %s, %s, TRUE, 0)
        ON CONFLICT (event_key) DO UPDATE SET
        start_time = EXCLUDED.start_time,
        end_time = EXCLUDED.end_time,
        is_active = TRUE
    """, (event_key, start_time, end_time))

# Command handlers
async def cmd_fantasy_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user achievements (MY ADDITION!)"""
    if not update.effective_user or not update.message:
        return
    
    user_id = update.effective_user.id
    ensure_powerup_tables()
    
    # Get user's achievements
    user_achievements = _exec("""
        SELECT achievement_key, earned_at, stars_earned
        FROM fantasy_achievements 
        WHERE user_id = %s
        ORDER BY earned_at DESC
    """, (user_id,))
    
    text = "🏆 **YOUR FANTASY ACHIEVEMENTS** 🏆\n\n"
    
    if not user_achievements or user_achievements is True:
        text += "No achievements yet!\nStart creating amazing fantasies to unlock rewards! 🌟\n\n"
    else:
        total_stars = sum(row[2] for row in user_achievements)
        text += f"⭐ **Total Stars Earned: {total_stars}** ⭐\n\n"
        
        text += "🎖️ **UNLOCKED:**\n"
        for row in user_achievements:
            key, earned_at, stars = row
            achievement = FANTASY_ACHIEVEMENTS[key]
            text += f"{achievement['emoji']} {achievement['name']} - {stars} Stars\n"
        
        text += "\n"
    
    # Show available achievements
    text += "🎯 **AVAILABLE ACHIEVEMENTS:**\n"
    earned_keys = [row[0] for row in user_achievements] if user_achievements and user_achievements is not True else []
    
    for key, achievement in FANTASY_ACHIEVEMENTS.items():
        if key not in earned_keys:
            text += f"🔒 {achievement['emoji']} {achievement['name']}\n"
            text += f"   {achievement['description']}\n"
            text += f"   Reward: {achievement['reward_stars']} Stars\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Board", callback_data="board:page:0:all:all")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# Callback handlers
async def on_powerups_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle power-ups callbacks"""
    query = update.callback_query
    if not query or not query.data:
        return
        
    data_parts = query.data.split(":")
    action = data_parts[1] if len(data_parts) > 1 else ""
    
    if action == "achievements":
        # Show achievements as message instead of editing
        await cmd_fantasy_achievements(update, context)
    
    elif action == "my_rank":
        await query.answer("My ranking feature coming soon!", show_alert=True)
    
    elif action == "join_event":
        await query.answer("Event joining coming soon!", show_alert=True)
    
    elif action == "treasure_hunt":
        await query.answer("Treasure hunt progress coming soon!", show_alert=True)