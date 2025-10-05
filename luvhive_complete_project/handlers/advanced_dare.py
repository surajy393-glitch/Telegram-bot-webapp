# handlers/advanced_dare.py
# Complete 60-Second Dare System with Community Submissions, Timer & Reminders

import datetime, random, time
import asyncio
import pytz
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from registration import _conn
from utils.daily_prompts import get_daily_dare
from utils.feature_texts import DARE_TEXT
from handlers.text_framework import FEATURE_KEY, claim_or_reject, requires_state, clear_state
from admin import ADMIN_IDS

IST = pytz.timezone("Asia/Kolkata")

# --------- Database Schema Creation ---------
def _ensure_dare_schema():
    """Create tables for advanced dare system"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Community dare submissions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dare_submissions(
                    id SERIAL PRIMARY KEY,
                    submitter_id BIGINT NOT NULL,
                    dare_text TEXT NOT NULL,
                    category VARCHAR(20) DEFAULT 'general',
                    difficulty VARCHAR(10) DEFAULT 'medium',
                    approved BOOLEAN DEFAULT FALSE,
                    admin_approved_by BIGINT,
                    submission_date DATE DEFAULT CURRENT_DATE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            # Daily dare selection table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_dare_selection(
                    dare_date DATE PRIMARY KEY,
                    dare_text TEXT NOT NULL,
                    dare_source VARCHAR(20) DEFAULT 'community',
                    source_id INTEGER,
                    submitter_id BIGINT,
                    category VARCHAR(20) DEFAULT 'general',
                    difficulty VARCHAR(10) DEFAULT 'medium',
                    creator_notified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            # User dare responses table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dare_responses(
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    dare_date DATE NOT NULL,
                    response VARCHAR(10) CHECK (response IN ('accepted', 'declined', 'expired', 'pending')),
                    dare_text TEXT,
                    difficulty_selected VARCHAR(10) DEFAULT 'medium',
                    response_time TIMESTAMPTZ DEFAULT NOW(),
                    completion_claimed BOOLEAN DEFAULT FALSE,
                    UNIQUE (user_id, dare_date)
                )
            """)
            
            # Add dare_text column if it doesn't exist (for existing tables)
            cur.execute("""
                ALTER TABLE dare_responses 
                ADD COLUMN IF NOT EXISTS dare_text TEXT
            """)
            
            # Dare streaks and stats table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dare_stats(
                    user_id BIGINT PRIMARY KEY,
                    current_streak INTEGER DEFAULT 0,
                    longest_streak INTEGER DEFAULT 0,
                    total_accepted INTEGER DEFAULT 0,
                    total_declined INTEGER DEFAULT 0,
                    total_expired INTEGER DEFAULT 0,
                    last_dare_date DATE,
                    badges TEXT[] DEFAULT '{}',
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            # Submitter feedback tracking table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dare_feedback(
                    id SERIAL PRIMARY KEY,
                    submission_id INTEGER REFERENCES dare_submissions(id),
                    event_type VARCHAR(20) CHECK (event_type IN ('selected', 'accepted', 'completed')),
                    user_id BIGINT,
                    dare_date DATE,
                    notified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            # Add dare streak columns to users table if not exists
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS dare_streak INT DEFAULT 0")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS dare_last_date DATE")
            
            # Add new columns to existing tables
            cur.execute("ALTER TABLE daily_dare_selection ADD COLUMN IF NOT EXISTS submitter_id BIGINT")
            cur.execute("ALTER TABLE daily_dare_selection ADD COLUMN IF NOT EXISTS category VARCHAR(20) DEFAULT 'general'")
            cur.execute("ALTER TABLE daily_dare_selection ADD COLUMN IF NOT EXISTS difficulty VARCHAR(10) DEFAULT 'medium'")
            cur.execute("ALTER TABLE daily_dare_selection ADD COLUMN IF NOT EXISTS creator_notified BOOLEAN DEFAULT FALSE")
            cur.execute("ALTER TABLE dare_responses ADD COLUMN IF NOT EXISTS difficulty_selected VARCHAR(10) DEFAULT 'medium'")
            
            # Create indexes for performance
            cur.execute("CREATE INDEX IF NOT EXISTS idx_dare_submissions_approved ON dare_submissions(approved, submission_date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_dare_responses_date ON dare_responses(dare_date, response)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_dare_stats_streak ON dare_stats(current_streak DESC)")
            
            con.commit()
    except Exception as e:
        print(f"[dare-schema] Error creating schema: {e}")

# --------- Time Window Functions ---------
def _now_ist() -> datetime.datetime:
    return datetime.datetime.now(IST)

def _in_dare_window(t: datetime.datetime) -> bool:
    """11:00 PM - 11:55 PM IST"""
    s = t.replace(hour=23, minute=0, second=0, microsecond=0)   # 11:00 PM
    e = t.replace(hour=23, minute=55, second=0, microsecond=0)  # 11:55 PM
    return s <= t <= e

def _minutes_remaining() -> int:
    """Minutes until dare expires (11:55 PM)"""
    now = _now_ist()
    expire_time = now.replace(hour=23, minute=55, second=0, microsecond=0)
    if now > expire_time:
        return 0
    return int((expire_time - now).total_seconds() / 60)

def _next_ist_time(h: int, m: int) -> datetime.datetime:
    """Get next occurrence of specified time in IST"""
    now = datetime.datetime.now(IST)
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return t if t > now else (t + datetime.timedelta(days=1))

# --------- Community Dare Submissions ---------
async def cmd_submitdare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interactive dare submission with category and difficulty selection"""
    _ensure_dare_schema()
    
    user_id = update.effective_user.id
    
    # Check if user has submitted today
    today = datetime.date.today()
    with _conn() as con, con.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM dare_submissions WHERE submitter_id=%s AND submission_date=%s",
            (user_id, today)
        )
        count = cur.fetchone()[0]
        
        # Check daily limit (skip for admins)
        if user_id not in ADMIN_IDS and count >= 3:  # Max 3 submissions per day for non-admins
            return await update.message.reply_text(
                "🚫 आज की limit पूरी हो गई! कल फिर try करना।\n"
                "Daily submission limit reached! Try again tomorrow."
            )
    
    # Start interactive submission flow
    text = (
        "🎯 **Create Community Dare**\n\n"
        "Let's make an awesome dare for the community! Your submission will be reviewed and could be featured for thousands of users.\n\n"
        "**Step 1:** Choose a category for your dare:"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😂 Funny", callback_data="submit:cat:funny"),
            InlineKeyboardButton("💖 Romantic", callback_data="submit:cat:romantic")
        ],
        [
            InlineKeyboardButton("🌶️ Spicy", callback_data="submit:cat:spicy"),
            InlineKeyboardButton("🏋️ Adventurous", callback_data="submit:cat:adventurous")
        ]
    ])
    
    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

# --------- Daily Dare Selection ---------
def _get_or_select_today_dare(user_id: int = None) -> str:
    """Get today's dare or select one from community submissions - different for each user"""
    today = datetime.date.today()
    _ensure_dare_schema()
    
    with _conn() as con, con.cursor() as cur:
        # If user_id provided, try to get user-specific dare first
        if user_id:
            cur.execute("""
                SELECT dare_text FROM dare_responses 
                WHERE user_id=%s AND dare_date=%s AND dare_text IS NOT NULL
            """, (user_id, today))
            user_dare = cur.fetchone()
            if user_dare:
                return user_dare[0]
        
        # Get available dares pool (community + system)
        dare_pool = []
        
        # Get approved community dares
        cur.execute("""
            SELECT id, dare_text, submitter_id FROM dare_submissions 
            WHERE approved=TRUE AND submission_date >= %s - INTERVAL '30 days'
        """, (today,))
        community_dares = cur.fetchall()
        dare_pool.extend([(f"community_{d[0]}", d[1], d[2]) for d in community_dares])
        
        # Add system dares using different seeds for variety
        from utils.daily_prompts import get_daily_dare
        import random
        
        for i in range(20):  # Generate 20 different system dares
            seed_date = today + datetime.timedelta(days=i)
            system_dare = get_daily_dare(seed_date) 
            dare_pool.append((f"system_{i}", system_dare, None))
        
        # Select random dare from pool
        if dare_pool:
            # Use user_id as additional randomization if available
            if user_id:
                random.seed(int(str(today.strftime('%Y%m%d')) + str(user_id)[-4:]))
            else:
                random.seed(int(today.strftime('%Y%m%d')))
            
            selected = random.choice(dare_pool)
            dare_text = selected[1]
            submitter_id = selected[2]
            
            # Store the selected dare for this user if user_id provided
            if user_id:
                cur.execute("""
                    INSERT INTO dare_responses(user_id, dare_date, dare_text, response)
                    VALUES(%s, %s, %s, 'pending')
                    ON CONFLICT(user_id, dare_date) DO UPDATE SET dare_text=%s
                """, (user_id, today, dare_text, dare_text))
                con.commit()
            
            return dare_text
        else:
            # Final fallback
            dare_text = get_daily_dare(today)
            if user_id:
                cur.execute("""
                    INSERT INTO dare_responses(user_id, dare_date, dare_text, response)
                    VALUES(%s, %s, %s, 'pending')
                    ON CONFLICT(user_id, dare_date) DO UPDATE SET dare_text=%s
                """, (user_id, today, dare_text, dare_text))
                con.commit()
            return dare_text

# --------- Advanced Dare Interface ---------
async def cmd_advanced_dare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Advanced dare system with timer and social pressure"""
    _ensure_dare_schema()
    now = _now_ist()
    user_id = update.effective_user.id
    
    if not _in_dare_window(now):
        return await _send_dare_locked_message(update)
    
    # Check if user already responded today
    today = datetime.date.today()
    with _conn() as con, con.cursor() as cur:
        cur.execute(
            "SELECT response FROM dare_responses WHERE user_id=%s AND dare_date=%s",
            (user_id, today)
        )
        existing = cur.fetchone()
        
        if existing:
            response = existing[0]
            if response == 'accepted':
                return await update.message.reply_text(
                    "✅ आपने आज का dare accept कर लिया है!\n"
                    "You've already accepted today's dare!\n\n"
                    "Complete it before midnight for streak points! 🔥"
                )
            elif response == 'declined':
                return await update.message.reply_text(
                    "❌ आपने आज का dare decline कर दिया था।\n"
                    "You declined today's dare.\n\n"
                    "कल फिर try करना — streak break हो गया! 💔\n"
                    "Try again tomorrow — your streak is broken! 💔"
                )
    
    # Show difficulty selection first (instead of showing dare directly)
    minutes_left = _minutes_remaining()
    
    # Get user's current streak
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT current_streak FROM dare_stats WHERE user_id=%s", (user_id,))
        streak_row = cur.fetchone()
        current_streak = streak_row[0] if streak_row else 0
    
    # Get social stats
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE response='accepted') as accepted,
                COUNT(*) FILTER (WHERE response='declined') as declined,
                COUNT(*) as total
            FROM dare_responses WHERE dare_date=%s
        """, (today,))
        stats = cur.fetchone()
        accepted, declined, total = stats if stats else (0, 0, 0)
    
    text = (
        f"🎯 **ADVANCED DARE SYSTEM** ({minutes_left} min left)\n\n"
        f"📊 **Live Stats:**\n"
        f"✅ Accepted: {accepted} users\n"
        f"❌ Declined: {declined} users\n"
        f"🔥 Your Streak: {current_streak} days\n\n"
        f"⚡ **Choose your difficulty level:**\n"
        f"Each level gives you different dares!\n\n"
        f"⏰ **{minutes_left} minutes remaining!**\n"
        f"Choose now or lose your streak! 💀"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Easy", callback_data="dare:level:easy"),
            InlineKeyboardButton("🟡 Medium", callback_data="dare:level:medium")
        ],
        [
            InlineKeyboardButton("🔴 Extreme", callback_data="dare:level:extreme")
        ],
        [
            InlineKeyboardButton("📊 Leaderboard", callback_data="dare:leaderboard"),
            InlineKeyboardButton("ℹ️ How it works", callback_data="dare:info")
        ]
    ])
    
    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

async def _send_dare_locked_message(update: Update):
    """Show message when dare is not live"""
    next_dare = datetime.datetime.now(IST).replace(hour=23, minute=0, second=0, microsecond=0)
    if next_dare <= datetime.datetime.now(IST):
        next_dare += datetime.timedelta(days=1)
    
    text = (
        "🔒 **Dare Gate Locked**\n\n"
        "अभी dare time नहीं है! Gate खुलता है:\n"
        "Not dare time yet! Gate opens at:\n\n"
        "⏰ **11:00 PM - 11:55 PM IST**\n"
        "📅 **Active Days:** Mon Wed Fri Sat Sun\n"
        "📅 Next: " + next_dare.strftime("%I:%M %p IST") + "\n\n"
        "🔔 Reminder set? Wait for tonight's notification!"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔔 Set Reminder", callback_data="dare:remind"),
            InlineKeyboardButton("📊 Yesterday's Stats", callback_data="dare:yesterday")
        ],
        [
            InlineKeyboardButton("📝 Submit Dare", callback_data="dare:submit")
        ]
    ])
    
    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

# --------- Callback Handlers ---------
async def handle_dare_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all dare-related button callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    today = datetime.date.today()
    
    await query.answer()
    
    if query.data.startswith("dare:select:"):
        difficulty = query.data.split(":")[2]
        return await _show_difficulty_dare(query, user_id, today, difficulty)
    elif query.data.startswith("dare:accept:"):
        difficulty = query.data.split(":")[2]
        return await _handle_dare_accept(query, user_id, today, difficulty)
    elif query.data.startswith("dare:decline:"):
        difficulty = query.data.split(":")[2]
        return await _handle_dare_decline(query, user_id, today, difficulty)
    elif query.data == "dare:leaderboard":
        return await _show_dare_leaderboard(query)
    elif query.data == "dare:info":
        return await _show_dare_info(query)
    elif query.data == "dare:open":
        return await _handle_dare_open(query, context)
    elif query.data == "dare:stats":
        return await _show_live_stats(query)
    elif query.data == "dare:back_to_levels":
        return await _show_difficulty_selection(query)
    elif query.data == "dare:other_level":
        return await _show_difficulty_selection(query)
    elif query.data == "dare:submit":
        return await _handle_submit_dare_redirect(query)
    elif query.data.startswith("submit:"):
        return await handle_submission_callbacks(update, context)
    # Legacy support for old callbacks
    elif query.data == "dare:accept":
        return await _handle_dare_accept(query, user_id, today, "medium")
    elif query.data == "dare:decline":
        return await _handle_dare_decline(query, user_id, today, "medium")

async def _show_difficulty_dare(query, user_id: int, today: datetime.date, difficulty: str):
    """Show dare content with difficulty-specific accept/decline buttons"""
    # Validate difficulty
    if difficulty not in {"easy", "medium", "extreme"}:
        difficulty = "medium"
    
    # Get today's dare and remaining time (personalized for this user)
    dare_text = _get_or_select_today_dare(user_id)
    minutes_left = _minutes_remaining()
    
    # Get user's current streak
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT current_streak FROM dare_stats WHERE user_id=%s", (user_id,))
        streak_row = cur.fetchone()
        current_streak = streak_row[0] if streak_row else 0
    
    difficulty_emojis = {
        'easy': '🟢',
        'medium': '🟡', 
        'extreme': '🔴'
    }
    
    difficulty_descriptions = {
        'easy': 'Quick & Fun',
        'medium': 'Push yourself',
        'extreme': 'For the brave'
    }
    
    text = (
        f"🎯 **TODAY'S DARE** ({minutes_left} min left)\n\n"
        f"**{dare_text}**\n\n"
        f"⚡ **Selected Level:** {difficulty_emojis.get(difficulty, '🟡')} {difficulty.upper()} ({difficulty_descriptions.get(difficulty, 'Push yourself')})\n\n"
        f"🔥 **Your Streak:** {current_streak} days\n\n"
        f"⏰ **{minutes_left} minutes remaining!**\n"
        f"Accept now or lose your streak! 💀"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅ Accept ({difficulty.upper()})", callback_data=f"dare:accept:{difficulty}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"dare:decline:{difficulty}")
        ],
        [
            InlineKeyboardButton("« Change Level", callback_data="dare:other_level"),
            InlineKeyboardButton("📊 Live Stats", callback_data="dare:stats")
        ]
    ])
    
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def _handle_dare_accept(query, user_id: int, today: datetime.date, difficulty: str = "medium"):
    """Handle dare acceptance"""
    _ensure_dare_schema()
    
    # Check if still in window
    if not _in_dare_window(_now_ist()):
        return await query.edit_message_text(
            "⏰ समय समाप्त! Dare window close हो गया।\n"
            "Time's up! Dare window is closed.\n\n"
            "कल फिर try करना! 💔"
        )
    
    with _conn() as con, con.cursor() as cur:
        # Record acceptance with difficulty
        cur.execute("""
            INSERT INTO dare_responses(user_id, dare_date, response, difficulty_selected)
            VALUES(%s, %s, 'accepted', %s)
            ON CONFLICT(user_id, dare_date) DO NOTHING
        """, (user_id, today, difficulty))
        
        if cur.rowcount == 0:
            return await query.edit_message_text("आपने पहले ही respond कर दिया है!")
        
        # Update streak
        cur.execute("""
            INSERT INTO dare_stats(user_id, current_streak, total_accepted, last_dare_date)
            VALUES(%s, 1, 1, %s)
            ON CONFLICT(user_id) DO UPDATE SET
                current_streak = dare_stats.current_streak + 1,
                longest_streak = GREATEST(dare_stats.longest_streak, dare_stats.current_streak + 1),
                total_accepted = dare_stats.total_accepted + 1,
                last_dare_date = %s,
                updated_at = NOW()
        """, (user_id, today, today))
        
        # Get new streak
        cur.execute("SELECT current_streak FROM dare_stats WHERE user_id=%s", (user_id,))
        new_streak = cur.fetchone()[0]
        
        con.commit()
    
    # Check if this is a community dare and notify creator
    today = datetime.date.today()
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT dare_source, source_id FROM daily_dare_selection 
            WHERE dare_date=%s
        """, (today,))
        dare_info = cur.fetchone()
        
        if dare_info and dare_info[0] == 'community':
            # Get submitter info and notify them
            cur.execute("SELECT submitter_id FROM dare_submissions WHERE id=%s", (dare_info[1],))
            submitter_row = cur.fetchone()
            if submitter_row:
                submitter_id = submitter_row[0]
                # Notify creator that someone accepted their dare
                await _notify_dare_creator_accepted(query.get_bot(), submitter_id, user_id)
    
    social_message = ""
    if dare_info and dare_info[0] == 'community':
        social_message = "\n🎭 **The creator has been notified - make them proud!** 🏆"
    
    text = (
        f"🔥 **DARE ACCEPTED!** 🔥\n\n"
        f"💪 Your streak: **{new_streak} days**\n{social_message}\n"
        f"अब complete करो और photo/video share करो!\n"
        f"Now complete it and share proof!\n\n"
        f"⏰ You have until midnight to complete!\n"
        f"💎 Premium users get bonus points!"
    )
    
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📸 Share Completion", callback_data="dare:share"),
        InlineKeyboardButton("📊 My Stats", callback_data="dare:mystats")
    ]])
    
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def _handle_submit_dare_redirect(query):
    """Handle submit dare button from locked gate"""
    text = (
        "🎯 **Create Community Dare**\n\n"
        "Let's make an awesome dare for the community! Your submission will be reviewed and could be featured for thousands of users.\n\n"
        "**Step 1:** Choose a category for your dare:"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😂 Funny", callback_data="submit:cat:funny"),
            InlineKeyboardButton("💖 Romantic", callback_data="submit:cat:romantic")
        ],
        [
            InlineKeyboardButton("🌶️ Spicy", callback_data="submit:cat:spicy"),
            InlineKeyboardButton("🏋️ Adventurous", callback_data="submit:cat:adventurous")
        ]
    ])
    
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def _handle_dare_decline(query, user_id: int, today: datetime.date, difficulty: str = "medium"):
    """Handle dare decline with shame"""
    _ensure_dare_schema()
    
    with _conn() as con, con.cursor() as cur:
        # Record decline with difficulty
        cur.execute("""
            INSERT INTO dare_responses(user_id, dare_date, response, difficulty_selected)
            VALUES(%s, %s, 'declined', %s)
            ON CONFLICT(user_id, dare_date) DO NOTHING
        """, (user_id, today, difficulty))
        
        # Break streak
        cur.execute("""
            INSERT INTO dare_stats(user_id, current_streak, total_declined)
            VALUES(%s, 0, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                current_streak = 0,
                total_declined = dare_stats.total_declined + 1,
                updated_at = NOW()
        """, (user_id,))
        
        # Get how many others accepted
        cur.execute("""
            SELECT COUNT(*) FROM dare_responses 
            WHERE dare_date=%s AND response='accepted'
        """, (today,))
        brave_count = cur.fetchone()[0]
        
        con.commit()
    
    shame_messages = [
        f"💔 Streak टूट गया! {brave_count} लोग आपसे ज्यादा brave थे।",
        f"😱 डर गए? {brave_count} users ने हिम्मत दिखाई!",
        f"🐔 Chicken! {brave_count} others were braver than you.",
        f"💸 मौका चूक गए! {brave_count} people seized the day!"
    ]
    
    text = f"❌ **DARE DECLINED** ❌\n\n{random.choice(shame_messages)}\n\n" \
           f"कल फिर मौका है brave बनने का!\n" \
           f"Tomorrow is another chance to be brave!"
    
    await query.edit_message_text(text, parse_mode="Markdown")

async def _show_dare_leaderboard(query):
    """Show dare leaderboard"""
    _ensure_dare_schema()
    
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT u.tg_user_id, ds.current_streak, ds.longest_streak, ds.total_accepted
            FROM dare_stats ds
            JOIN users u ON u.tg_user_id = ds.user_id
            ORDER BY ds.current_streak DESC, ds.total_accepted DESC
            LIMIT 10
        """)
        
        top_users = cur.fetchall()
    
    if not top_users:
        text = "📊 **Dare Leaderboard**\n\nNo daredevils yet! Be the first!"
    else:
        text = "📊 **Top Daredevils** 🔥\n\n"
        for i, (user_id, current, longest, total) in enumerate(top_users):
            rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            try:
                user = await query.bot.get_chat_member(user_id, user_id)
                name = user.user.first_name[:10]
            except:
                name = f"User{str(user_id)[-4:]}"
            
            text += f"{rank_emoji} **{name}**\n"
            text += f"   🔥 Streak: {current} | 🏆 Best: {longest} | ✅ Total: {total}\n\n"
    
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("« Back to Dare", callback_data="dare:back")
    ]])
    
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def _show_dare_info(query):
    """Show how dare system works"""
    text = (
        "ℹ️ **How 60-Second Dare Works**\n\n"
        "⏰ **Timing:** 11:00-11:55 PM daily\n"
        "🎯 **Goal:** Accept community dares to build streaks\n\n"
        "📈 **Rewards:**\n"
        "• 🔥 Daily streak points\n"
        "• 🏆 Leaderboard rankings\n"
        "• 💎 Premium bonus rewards\n"
        "• 🏅 Achievement badges\n\n"
        "🚨 **Rules:**\n"
        "• Accept = +1 streak, Decline = break streak\n"
        "• Complete before midnight for full points\n"
        "• Submit your own dares with /submitdare\n\n"
        "💡 **Tips:**\n"
        "• Earlier acceptance = higher social pressure\n"
        "• Share completion proof for bonus points\n"
        "• Premium users get easier alternatives"
    )
    
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("« Back to Dare", callback_data="dare:back")
    ]])
    
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

# --------- Enhanced Notification System ---------
async def push_advanced_dare_notification(context: ContextTypes.DEFAULT_TYPE):
    """Push advanced dare notification at 11 PM"""
    _ensure_dare_schema()
    
    # Get today's dare (random for notification - no specific user)
    dare_text = _get_or_select_today_dare()
    
    # Get all active users for notification
    from handlers.notifications import _nudge_users
    users = await _nudge_users()
    
    # Create dramatic notification
    text = (
        "🚨 **Advanced Dare System is LIVE!** 🚨\n\n"
        f"👉 **Your Dare:** {dare_text}\n\n"
        "⚡ **55 minutes to decide your fate!**\n"
        "💪 Accept = Build streak & earn respect\n"
        "🐔 Decline = Break streak & face shame\n\n"
        "📅 **Active Days:** Mon Wed Fri Sat Sun\n"
        "👥 Community is watching... what will you choose?\n\n"
        "(Type /timedare to accept)"
    )
    
    # No inline keyboard - users must use /timedare command
    kb = None
    
    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(
                uid, text, parse_mode="Markdown"
            )
            sent += 1
            # Add small delay to avoid rate limits
            await asyncio.sleep(0.1)
        except Exception:
            pass
    
    print(f"[advanced-dare] Sent to {sent}/{len(users)} users")

# --------- Handle Text Submissions ---------
@requires_state("dare", "submit")
async def handle_dare_submission_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle dare submission text input using proper text framework integration"""
    
    user_id = update.effective_user.id
    dare_text = update.message.text.strip()
    
    # Validate submission
    if len(dare_text) < 10:
        return await update.message.reply_text(
            "🚫 Dare बहुत छोटा है! कम से कम 10 characters चाहिए।\n"
            "Dare too short! Minimum 10 characters required."
        )
    
    if len(dare_text) > 200:
        return await update.message.reply_text(
            "🚫 Dare बहुत लंबा है! Maximum 200 characters allowed."
        )
    
    # Store text and show preview for submission
    context.user_data['submission_text'] = dare_text
    
    category = context.user_data.get('submission_category', 'general')
    difficulty = context.user_data.get('submission_difficulty', 'medium')
    
    category_emojis = {
        'funny': '😂',
        'romantic': '💖', 
        'spicy': '🌶️',
        'adventurous': '🏋️',
        'general': '🎯'
    }
    
    difficulty_emojis = {
        'easy': '🟢',
        'medium': '🟡',
        'extreme': '🔴'
    }
    
    text = (
        f"🎯 **Preview Your Dare**\n\n"
        f"Category: {category_emojis.get(category, '🎯')} **{category.title()}**\n"
        f"Difficulty: {difficulty_emojis.get(difficulty, '🎯')} **{difficulty.title()}**\n\n"
        f"📝 **Your Dare:**\n"
        f"*{dare_text}*\n\n"
        f"✨ **Ready to submit?** This will be reviewed by our team and could be featured for thousands of users!"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Submit", callback_data="submit:confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="submit:cancel")
        ],
        [InlineKeyboardButton("← Edit Text", callback_data="submit:back:difficulty")]
    ])
    
    return await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

# --------- Admin Approval System ---------
async def _notify_admin_new_submission(context: ContextTypes.DEFAULT_TYPE, submission_id: int, user_id: int, submission_data):
    """Notify admin about new dare submission for approval"""
    # Admin IDs from environment or fallback
    import os, re
    admin_ids_str = os.getenv("ADMIN_IDS", "1437934486,647778438")
    # Bulletproof cleaning: remove all quotes, extract only numbers
    clean_ids = re.findall(r'\d+', admin_ids_str)
    admin_ids = [int(x) for x in clean_ids if x]
    
    try:
        # Get submitter info
        user_info = await context.bot.get_chat(user_id)
        user_name = user_info.first_name or f"User{str(user_id)[-4:]}"
    except:
        user_name = f"User{str(user_id)[-4:]}"
    
    # Handle both old format (string) and new format (dict)
    if isinstance(submission_data, dict):
        dare_text = submission_data['text']
        category = submission_data.get('category', 'general')
        difficulty = submission_data.get('difficulty', 'medium')
        extra_info = f"\n🏷️ **Category:** {category.title()}\n⚡ **Difficulty:** {difficulty.title()}"
    else:
        dare_text = submission_data
        extra_info = ""
    
    text = (
        f"🎯 **New Dare Submission #{submission_id}**\n\n"
        f"👤 **Submitter:** {user_name} (`{user_id}`)\n"
        f"📝 **Dare:** {dare_text}{extra_info}\n\n"
        f"⚡ **Actions:**"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"admin_dare_approve:{submission_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_dare_reject:{submission_id}")
        ],
        [InlineKeyboardButton("📊 View All Pending", callback_data="admin_dare_pending")]
    ])
    
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(
                admin_id, text, reply_markup=kb, parse_mode="Markdown"
            )
        except Exception as e:
            print(f"[admin-notify] Failed to send to {admin_id}: {e}")

async def cmd_admin_approve_dares(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view pending dare submissions"""
    user_id = update.effective_user.id
    
    # Check admin permissions
    import os, re
    admin_ids_str = os.getenv("ADMIN_IDS", "1437934486,647778438")
    # Bulletproof cleaning: remove all quotes, extract only numbers
    clean_ids = re.findall(r'\d+', admin_ids_str)
    admin_ids = [int(x) for x in clean_ids if x]
    
    if user_id not in admin_ids:
        return await update.message.reply_text("❌ Admin access required.")
    
    _ensure_dare_schema()
    
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT id, submitter_id, dare_text, submission_date 
            FROM dare_submissions 
            WHERE approved=FALSE 
            ORDER BY submission_date DESC, id DESC
            LIMIT 10
        """)
        
        pending = cur.fetchall()
    
    if not pending:
        return await update.message.reply_text("✅ No pending dare submissions!")
    
    text = "🎯 **Pending Dare Submissions**\n\n"
    
    buttons = []
    for sub_id, submitter_id, dare_text, sub_date in pending:
        text += f"**#{sub_id}** (User {str(submitter_id)[-4:]})\n"
        text += f"📝 {dare_text[:60]}{'...' if len(dare_text) > 60 else ''}\n"
        text += f"📅 {sub_date}\n\n"
        
        # Add approve/decline buttons for each dare
        buttons.append([
            InlineKeyboardButton(f"✅ Approve #{sub_id}", callback_data=f"admin_dare_approve:{sub_id}"),
            InlineKeyboardButton(f"❌ Decline #{sub_id}", callback_data=f"admin_dare_reject:{sub_id}")
        ])
    
    # Add refresh button at the end
    buttons.append([InlineKeyboardButton("📊 Refresh", callback_data="admin_dare_pending")])
    
    kb = InlineKeyboardMarkup(buttons)
    
    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

async def handle_admin_dare_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin approval/rejection callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Check admin permissions
    import os, re
    admin_ids_str = os.getenv("ADMIN_IDS", "1437934486,647778438")
    # Bulletproof cleaning: remove all quotes, extract only numbers
    clean_ids = re.findall(r'\d+', admin_ids_str)
    admin_ids = [int(x) for x in clean_ids if x]
    
    if user_id not in admin_ids:
        return await query.answer("❌ Admin access required.")
    
    await query.answer()
    
    if query.data.startswith("admin_dare_approve:"):
        submission_id = int(query.data.split(":")[1])
        await _approve_dare_submission(query, submission_id)
    elif query.data.startswith("admin_dare_reject:"):
        submission_id = int(query.data.split(":")[1])
        await _reject_dare_submission(query, submission_id)
    elif query.data == "admin_dare_pending":
        await _show_pending_submissions(query)

async def _approve_dare_submission(query, submission_id: int):
    """Approve a dare submission"""
    _ensure_dare_schema()
    
    with _conn() as con, con.cursor() as cur:
        # Get submitter info before approval
        cur.execute("""
            SELECT submitter_id, dare_text, category, difficulty 
            FROM dare_submissions 
            WHERE id=%s AND approved=FALSE
        """, (submission_id,))
        submission_data = cur.fetchone()
        
        if not submission_data:
            return await query.edit_message_text("❌ Submission not found or already processed.")
        
        submitter_id, dare_text, category, difficulty = submission_data
        
        # Approve the submission
        cur.execute("""
            UPDATE dare_submissions 
            SET approved=TRUE, admin_approved_by=%s 
            WHERE id=%s AND approved=FALSE
        """, (query.from_user.id, submission_id))
        
        con.commit()
    
    # Notify dare creator about approval
    await _notify_dare_creator_approval(query.get_bot(), submitter_id, submission_id, dare_text, category, difficulty)
    
    await query.edit_message_text(
        f"✅ **Dare #{submission_id} Approved!**\n\n"
        f"The dare is now available for community challenges.\n"
        f"Creator has been notified! 🎯"
    )

async def _reject_dare_submission(query, submission_id: int):
    """Reject a dare submission"""
    _ensure_dare_schema()
    
    with _conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM dare_submissions WHERE id=%s AND approved=FALSE", (submission_id,))
        
        if cur.rowcount == 0:
            return await query.edit_message_text("❌ Submission not found or already processed.")
        
        con.commit()
    
    await query.edit_message_text(
        f"❌ **Dare #{submission_id} Rejected!**\n\n"
        f"The submission has been removed from the system."
    )

async def _show_pending_submissions(query):
    """Show pending submissions in callback"""
    _ensure_dare_schema()
    
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT id, submitter_id, dare_text, submission_date 
            FROM dare_submissions 
            WHERE approved=FALSE 
            ORDER BY submission_date DESC, id DESC
            LIMIT 5
        """)
        
        pending = cur.fetchall()
    
    if not pending:
        return await query.edit_message_text("✅ No pending dare submissions!")
    
    text = "🎯 **Pending Dare Submissions**\n\n"
    buttons = []
    
    for sub_id, submitter_id, dare_text, sub_date in pending:
        text += f"**#{sub_id}** (User {str(submitter_id)[-4:]})\n"
        text += f"📝 {dare_text[:50]}{'...' if len(dare_text) > 50 else ''}\n\n"
        
        buttons.append([
            InlineKeyboardButton(f"✅ #{sub_id}", callback_data=f"admin_dare_approve:{sub_id}"),
            InlineKeyboardButton(f"❌ #{sub_id}", callback_data=f"admin_dare_reject:{sub_id}")
        ])
    
    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="admin_dare_pending")])
    kb = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def _show_difficulty_selection(query):
    """Show difficulty selection screen"""
    minutes_left = _minutes_remaining()
    
    # Get user's current streak
    user_id = query.from_user.id
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT current_streak FROM dare_stats WHERE user_id=%s", (user_id,))
        streak_row = cur.fetchone()
        current_streak = streak_row[0] if streak_row else 0
        
        # Check if today's dare is from community (has a creator waiting)
        today = datetime.date.today()
        cur.execute("""
            SELECT dare_source, source_id FROM daily_dare_selection 
            WHERE dare_date=%s
        """, (today,))
        dare_info = cur.fetchone()
    
    # Add social pressure message if community dare
    social_message = ""
    if dare_info and dare_info[0] == 'community':
        social_message = (
            "\n💝 **Special**: Someone from the community created this dare!\n"
            "🎭 They're waiting to see who gets their challenge.\n"
            "🏆 Don't disappoint them - be sporty! 💪\n"
        )
    
    text = (
        f"🎯 **DARE TIME!** ({minutes_left} min left)\n\n"
        f"Choose your challenge level:\n{social_message}\n"
        f"🔥 Your current streak: **{current_streak} days**\n\n"
        f"⏰ **{minutes_left} minutes remaining!**\n"
        f"Pick your comfort zone or push your limits! 💪"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Easy (Quick & Fun)", callback_data="dare:select:easy")],
        [InlineKeyboardButton("🟡 Medium (Push yourself)", callback_data="dare:select:medium")],
        [InlineKeyboardButton("🔴 Extreme (For the brave)", callback_data="dare:select:extreme")],
        [
            InlineKeyboardButton("📊 Leaderboard", callback_data="dare:leaderboard"),
            InlineKeyboardButton("ℹ️ How it works", callback_data="dare:info")
        ]
    ])
    
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def _handle_dare_open(query, context: ContextTypes.DEFAULT_TYPE):
    """Handle dare open callback from notification"""
    user_id = query.from_user.id
    now = _now_ist()
    
    if not _in_dare_window(now):
        return await query.edit_message_text(
            "⏰ समय समाप्त! Dare window close हो गया।\n"
            "Time's up! Dare window is closed.\n\n"
            "कल फिर try करना! 💔"
        )
    
    # Show difficulty selection
    return await _show_difficulty_selection(query)

async def _show_live_stats(query):
    """Show live statistics for all difficulty levels"""
    today = datetime.date.today()
    
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT 
                difficulty_selected,
                COUNT(*) FILTER (WHERE response='accepted') as accepted,
                COUNT(*) FILTER (WHERE response='declined') as declined,
                COUNT(*) as total
            FROM dare_responses 
            WHERE dare_date=%s 
            GROUP BY difficulty_selected
        """, (today,))
        
        stats = {}
        for row in cur.fetchall():
            diff, acc, dec, total = row
            stats[diff] = {'accepted': acc, 'declined': dec, 'total': total}
    
    text = "📊 **Live Dare Statistics**\n\n"
    
    difficulty_emojis = {
        'easy': '🟢',
        'medium': '🟡',
        'extreme': '🔴'
    }
    
    for diff in ['easy', 'medium', 'extreme']:
        emoji = difficulty_emojis.get(diff, '🎯')
        if diff in stats:
            acc = stats[diff]['accepted']
            dec = stats[diff]['declined']
            total = stats[diff]['total']
            acceptance_rate = (acc / total * 100) if total > 0 else 0
            text += f"{emoji} **{diff.title()}:**\n"
            text += f"   ✅ Accepted: {acc}\n"
            text += f"   ❌ Declined: {dec}\n"
            text += f"   📈 Rate: {acceptance_rate:.1f}%\n\n"
        else:
            text += f"{emoji} **{diff.title()}:** No responses yet\n\n"
    
    text += f"⏰ **{_minutes_remaining()} minutes remaining!**"
    
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("« Back to Dare", callback_data="dare:open")
    ]])
    
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

# --------- Interactive Submission Callbacks ---------
async def handle_submission_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interactive dare submission flow callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    await query.answer()
    
    if data.startswith("submit:cat:"):
        # Category selection
        category = data.split(":")[2]
        context.user_data['submission_category'] = category
        
        category_emojis = {
            'funny': '😂',
            'romantic': '💖', 
            'spicy': '🌶️',
            'adventurous': '🏋️'
        }
        
        text = (
            f"🎯 **Create Community Dare**\n\n"
            f"Category: {category_emojis.get(category, '🎯')} **{category.title()}**\n\n"
            f"**Step 2:** Choose difficulty level:"
        )
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 Easy", callback_data="submit:diff:easy")],
            [InlineKeyboardButton("🟡 Medium", callback_data="submit:diff:medium")],
            [InlineKeyboardButton("🔴 Extreme", callback_data="submit:diff:extreme")],
            [InlineKeyboardButton("← Back", callback_data="submit:back:category")]
        ])
        
        return await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    
    elif data.startswith("submit:diff:"):
        # Difficulty selection
        difficulty = data.split(":")[2]
        context.user_data['submission_difficulty'] = difficulty
        
        category = context.user_data.get('submission_category', 'general')
        category_emojis = {
            'funny': '😂',
            'romantic': '💖', 
            'spicy': '🌶️',
            'adventurous': '🏋️',
            'general': '🎯'
        }
        
        difficulty_emojis = {
            'easy': '🟢',
            'medium': '🟡',
            'extreme': '🔴'
        }
        
        text = (
            f"🎯 **Create Community Dare**\n\n"
            f"Category: {category_emojis.get(category, '🎯')} **{category.title()}**\n"
            f"Difficulty: {difficulty_emojis.get(difficulty, '🎯')} **{difficulty.title()}**\n\n"
            f"**Step 3:** Write your dare text:\n\n"
            f"💡 **Guidelines:**\n"
            f"• Keep it fun and engaging\n"
            f"• Be creative but respectful\n"
            f"• Consider the difficulty level\n"
            f"• Make it doable for most people\n\n"
            f"📝 **Type your dare below:**"
        )
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("← Back", callback_data="submit:back:difficulty")]
        ])
        
        # Claim text input state using proper text framework
        if not await claim_or_reject(update, context, "dare", "submit", ttl_minutes=3):
            return
        
        # Add cancel keyboard with text input
        from handlers.text_framework import make_cancel_kb
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("← Back", callback_data="submit:back:difficulty")],
            [InlineKeyboardButton("❌ Cancel", callback_data="textfw:cancel")]
        ])
        
        return await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    
    elif data.startswith("submit:back:"):
        # Handle back navigation
        step = data.split(":")[2]
        
        if step == "category":
            # Go back to category selection
            text = (
                "🎯 **Create Community Dare**\n\n"
                "Let's make an awesome dare for the community! Your submission will be reviewed and could be featured for thousands of users.\n\n"
                "**Step 1:** Choose a category for your dare:"
            )
            
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("😂 Funny", callback_data="submit:cat:funny"),
                    InlineKeyboardButton("💖 Romantic", callback_data="submit:cat:romantic")
                ],
                [
                    InlineKeyboardButton("🌶️ Spicy", callback_data="submit:cat:spicy"),
                    InlineKeyboardButton("🏋️ Adventurous", callback_data="submit:cat:adventurous")
                ]
            ])
            
            return await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
        
        elif step == "difficulty":
            # Go back to difficulty selection - clear text state if active
            clear_state(context)
            category = context.user_data.get('submission_category', 'general')
            category_emojis = {
                'funny': '😂',
                'romantic': '💖', 
                'spicy': '🌶️',
                'adventurous': '🏋️',
                'general': '🎯'
            }
            
            text = (
                f"🎯 **Create Community Dare**\n\n"
                f"Category: {category_emojis.get(category, '🎯')} **{category.title()}**\n\n"
                f"**Step 2:** Choose difficulty level:"
            )
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🟢 Easy", callback_data="submit:diff:easy")],
                [InlineKeyboardButton("🟡 Medium", callback_data="submit:diff:medium")],
                [InlineKeyboardButton("🔴 Extreme", callback_data="submit:diff:extreme")],
                [InlineKeyboardButton("← Back", callback_data="submit:back:category")]
            ])
            
            return await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    
    elif data.startswith("submit:confirm"):
        # Final submission - clear state when processing
        result = await _process_dare_submission(query, context)
        clear_state(context)  # Clear state after successful submission
        return result
    
    elif data.startswith("submit:cancel"):
        # Cancel submission
        await query.edit_message_text(
            "❌ **Submission Cancelled**\n\n"
            "No worries! You can submit a dare anytime using /submitdare",
            parse_mode="Markdown"
        )
        # Clear submission data and text framework state
        for key in list(context.user_data.keys()):
            if key.startswith('submission_'):
                del context.user_data[key]
        clear_state(context)

async def _process_dare_submission(query, context: ContextTypes.DEFAULT_TYPE):
    """Process final dare submission"""
    user_id = query.from_user.id
    
    category = context.user_data.get('submission_category', 'general')
    difficulty = context.user_data.get('submission_difficulty', 'medium') 
    dare_text = context.user_data.get('submission_text', '')
    
    if not dare_text:
        return await query.edit_message_text(
            "❌ **Error:** No dare text found. Please try again with /submitdare",
            parse_mode="Markdown"
        )
    
    _ensure_dare_schema()
    today = datetime.date.today()
    
    with _conn() as con, con.cursor() as cur:
        # Insert submission
        cur.execute("""
            INSERT INTO dare_submissions(submitter_id, dare_text, category, difficulty, submission_date)
            VALUES(%s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, dare_text, category, difficulty, today))
        
        submission_id = cur.fetchone()[0]
        con.commit()
    
    text = (
        "🎉 **Dare Submitted Successfully!**\n\n"
        f"📝 **Your {difficulty} {category} dare:**\n"
        f"*{dare_text}*\n\n"
        "⏳ **Under Review:** Our team will review your submission\n"
        "🔔 **Get Notified:** You'll be notified if it's selected for daily use\n"
        "📊 **Track Stats:** Use /mydares to see your submission history\n\n"
        "🚀 Thanks for contributing to the community!"
    )
    
    # Send success message and schedule auto-deletion after 30 seconds
    sent_message = await query.edit_message_text(text, parse_mode="Markdown")
    
    # Schedule automatic deletion after 30 seconds
    import asyncio
    async def delete_message():
        try:
            await asyncio.sleep(30)
            await query.bot.delete_message(
                chat_id=sent_message.chat_id,
                message_id=sent_message.message_id
            )
        except Exception as e:
            # Ignore errors (message might already be deleted by user)
            pass
    
    # Create background task for deletion
    asyncio.create_task(delete_message())
    
    # Send admin notification with proper data format
    submission_data = {
        'text': dare_text,
        'category': category,
        'difficulty': difficulty
    }
    await _notify_admin_new_submission(context, submission_id, user_id, submission_data)
    
    # Clear submission data and text framework state
    for key in list(context.user_data.keys()):
        if key.startswith('submission_'):
            del context.user_data[key]
    clear_state(context)

# --------- MyDares Callback Handlers ---------
async def handle_mydares_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mydares button callbacks"""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()
    
    if query.data == "mydares:detailed":
        return await _show_detailed_dare_stats(query, user_id)
    elif query.data == "mydares:submit":
        return await _redirect_to_submit_dare(query)
    elif query.data == "mydares:back":
        # Go back to main mydares view
        return await cmd_mydares(update, context)

async def _show_detailed_dare_stats(query, user_id: int):
    """Show detailed statistics for user's dare submissions"""
    _ensure_dare_schema()
    
    with _conn() as con, con.cursor() as cur:
        # Get detailed stats
        cur.execute("""
            SELECT 
                ds.id, ds.dare_text, ds.category, ds.difficulty, ds.approved, ds.submission_date,
                COUNT(df.id) FILTER (WHERE df.event_type='selected') as times_selected,
                COUNT(df.id) FILTER (WHERE df.event_type='accepted') as times_accepted,
                COUNT(df.id) FILTER (WHERE df.event_type='completed') as times_completed
            FROM dare_submissions ds
            LEFT JOIN dare_feedback df ON ds.id = df.submission_id
            WHERE ds.submitter_id=%s
            GROUP BY ds.id, ds.dare_text, ds.category, ds.difficulty, ds.approved, ds.submission_date
            ORDER BY ds.submission_date DESC
            LIMIT 20
        """, (user_id,))
        
        submissions = cur.fetchall()
        
        if not submissions:
            text = (
                "📊 **Detailed Dare Statistics**\n\n"
                "No submissions found yet!\n\n"
                "🎯 Start creating dares with /submitdare"
            )
        else:
            total_submitted = len(submissions)
            approved_count = sum(1 for s in submissions if s[4])  # approved column
            total_selected = sum(s[6] for s in submissions)  # times_selected
            total_accepted = sum(s[7] for s in submissions)  # times_accepted
            total_completed = sum(s[8] for s in submissions)  # times_completed
            
            text = (
                f"📊 **Detailed Dare Statistics**\n\n"
                f"📈 **Overall Performance:**\n"
                f"🎯 Total Submitted: {total_submitted}\n"
                f"✅ Approved: {approved_count}\n"
                f"⭐ Times Featured: {total_selected}\n"
                f"🔥 Times Accepted: {total_accepted}\n"
                f"🏆 Times Completed: {total_completed}\n\n"
            )
            
            if approved_count > 0:
                success_rate = (total_accepted / max(total_selected, 1)) * 100
                text += f"📊 **Acceptance Rate:** {success_rate:.1f}%\n"
                
                if total_selected > 0:
                    text += f"🎖️ **Impact Score:** {total_selected * 10 + total_accepted * 5 + total_completed * 15}\n"
            
            text += f"\n💡 **Keep creating!** Quality submissions get featured more often."
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("← Back to History", callback_data="mydares:back")],
            [InlineKeyboardButton("🆕 Submit New Dare", callback_data="mydares:submit")]
        ])
        
        return await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

async def _redirect_to_submit_dare(query):
    """Redirect to submit dare flow"""
    text = (
        "🎯 **Create Community Dare**\n\n"
        "Let's make an awesome dare for the community! Your submission will be reviewed and could be featured for thousands of users.\n\n"
        "**Step 1:** Choose a category for your dare:"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😂 Funny", callback_data="submit:cat:funny"),
            InlineKeyboardButton("💖 Romantic", callback_data="submit:cat:romantic")
        ],
        [
            InlineKeyboardButton("🌶️ Spicy", callback_data="submit:cat:spicy"),
            InlineKeyboardButton("🏋️ Adventurous", callback_data="submit:cat:adventurous")
        ]
    ])
    
    return await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

# --------- Global notification tracking ---------
_pending_creator_notification = None

# --------- Social Feedback & Creator Attribution System ---------

async def _notify_dare_creator_approval(bot, submitter_id: int, submission_id: int, dare_text: str, category: str, difficulty: str):
    """Notify dare creator when their submission is approved"""
    try:
        text = (
            f"🎉 **आपका Dare Approve हो गया!** 🎉\n\n"
            f"**#{submission_id}** ✅ Approved\n"
            f"📝 **Dare:** {dare_text}\n"
            f"🏷️ **Category:** {category.title()}\n"
            f"⚡ **Difficulty:** {difficulty.title()}\n\n"
            f"🎯 **अब देखते हैं कौन करता है आपका dare randomly!**\n"
            f"Wait and watch who gets your challenge!\n\n"
            f"🔥 You'll be notified when someone accepts it!"
        )
        
        await bot.send_message(submitter_id, text, parse_mode="Markdown")
    except Exception as e:
        print(f"[notify-approval] Failed to notify {submitter_id}: {e}")

async def _notify_dare_creator_accepted(bot, submitter_id: int, accepter_id: int):
    """Notify dare creator when someone accepts their dare"""
    try:
        # Get accepter's bot display name from database
        from registration import _conn
        
        try:
            with _conn() as con, con.cursor() as cur:
                cur.execute("SELECT name FROM users WHERE user_id = %s", (accepter_id,))
                result = cur.fetchone()
                if result and result[0]:
                    user_name = result[0]  # Use bot display name
                else:
                    user_name = "User"  # Anonymous user if no name set
        except:
            user_name = "User"  # Fallback to anonymous
        
        text = (
            f"🔥 **कोई आपका Dare Accept किया!** 🔥\n\n"
            f"👤 **User:** {user_name} (`{str(accepter_id)[-4:]}`)\n"
            f"🎯 **Your dare** has been accepted!\n\n"
            f"🏆 **They're now working on your challenge!**\n"
            f"💪 Let's see if they complete it - fingers crossed! 🤞\n\n"
            f"📊 Use /mydares to track all your submissions."
        )
        
        await bot.send_message(submitter_id, text, parse_mode="Markdown")
    except Exception as e:
        print(f"[notify-accepted] Failed to notify {submitter_id}: {e}")

async def _notify_dare_creator_selected(bot, submitter_id: int, dare_text: str, date):
    """Notify dare creator when their dare is selected for daily challenge"""
    try:
        text = (
            f"🎯 **आपका Dare आज Selected हुआ है!** 🎯\n\n"
            f"📅 **Date:** {date}\n"
            f"📝 **Your Dare:** {dare_text}\n\n"
            f"🎲 **Randomly selected** for today's community challenge!\n"
            f"🌟 **Thousands of users** will see your creation!\n\n"
            f"⏰ **11 PM** तक देखते हैं कितने लोग accept करते हैं!\n"
            f"You'll get notifications when people accept it! 🔥"
        )
        
        await bot.send_message(submitter_id, text, parse_mode="Markdown")
    except Exception as e:
        print(f"[notify-selected] Failed to notify {submitter_id}: {e}")
async def notify_dare_creator_when_selected(context: ContextTypes.DEFAULT_TYPE, submission_id: int, submitter_id: int):
    """Notify dare creator when their dare is selected for today"""
    if not submitter_id:
        return
    
    try:
        # Record feedback event
        today = datetime.date.today()
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                INSERT INTO dare_feedback(submission_id, event_type, dare_date)
                VALUES(%s, 'selected', %s)
            """, (submission_id, today))
            con.commit()
        
        # Send notification to creator
        text = (
            "🎉 **Your dare was selected!**\n\n"
            "Congratulations! Your community dare has been chosen for today's challenge.\n\n"
            "⏰ People will see it during tonight's 11:00-11:55 PM dare window.\n"
            "📊 You'll get updates when people accept/complete your dare!\n\n"
            "🔥 Keep creating amazing content!"
        )
        
        await context.bot.send_message(submitter_id, text, parse_mode="Markdown")
        
        # Mark as notified
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                UPDATE dare_feedback SET notified=TRUE 
                WHERE submission_id=%s AND event_type='selected'
            """, (submission_id,))
            con.commit()
            
    except Exception as e:
        print(f"[social-feedback] Error notifying creator {submitter_id}: {e}")

async def notify_dare_creator_when_accepted(context: ContextTypes.DEFAULT_TYPE, user_id: int, difficulty: str):
    """Notify dare creator when someone accepts their dare"""
    today = datetime.date.today()
    
    try:
        with _conn() as con, con.cursor() as cur:
            # Find the creator of today's dare for this difficulty
            cur.execute("""
                SELECT submitter_id, source_id FROM daily_dare_selection 
                WHERE dare_date=%s AND difficulty=%s AND submitter_id IS NOT NULL
            """, (today, difficulty))
            
            result = cur.fetchone()
            if not result or not result[0]:
                return
            
            submitter_id, submission_id = result
            
            # Record feedback event
            cur.execute("""
                INSERT INTO dare_feedback(submission_id, event_type, user_id, dare_date)
                VALUES(%s, 'accepted', %s, %s)
            """, (submission_id, user_id, today))
            con.commit()
        
        # Get accepter info
        try:
            user_info = await context.bot.get_chat(user_id)
            user_name = user_info.first_name or f"User{str(user_id)[-4:]}"
        except:
            user_name = "Someone"
        
        # Send notification to creator
        text = (
            f"🔥 **Someone accepted your dare!**\n\n"
            f"👤 **{user_name}** just accepted your {difficulty.upper()} dare!\n\n"
            f"📊 Track all your dare stats with /mydares\n"
            f"🎉 You're building the community with great content!"
        )
        
        await context.bot.send_message(submitter_id, text, parse_mode="Markdown")
        
    except Exception as e:
        print(f"[social-feedback] Error notifying acceptance: {e}")

# --------- /mydares Command ---------
async def cmd_mydares(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's dare submission history and stats"""
    user_id = update.effective_user.id
    _ensure_dare_schema()
    
    with _conn() as con, con.cursor() as cur:
        # Get user's submissions
        cur.execute("""
            SELECT id, dare_text, category, difficulty, approved, submission_date, created_at
            FROM dare_submissions 
            WHERE submitter_id=%s
            ORDER BY created_at DESC
            LIMIT 10
        """, (user_id,))
        
        submissions = cur.fetchall()
        
        if not submissions:
            text = (
                "📝 **Your Dare History**\n\n"
                "You haven't submitted any dares yet!\n\n"
                "🎯 Use /submitdare to create your first community dare\n"
                "💡 Help build an amazing collection of challenges!"
            )
            return await update.message.reply_text(text, parse_mode="Markdown")
        
        # Get usage statistics
        cur.execute("""
            SELECT 
                ds.id,
                COUNT(df.id) FILTER (WHERE df.event_type='selected') as times_selected,
                COUNT(df.id) FILTER (WHERE df.event_type='accepted') as times_accepted,
                COUNT(df.id) FILTER (WHERE df.event_type='completed') as times_completed
            FROM dare_submissions ds
            LEFT JOIN dare_feedback df ON ds.id = df.submission_id
            WHERE ds.submitter_id=%s
            GROUP BY ds.id
        """, (user_id,))
        
        stats = {row[0]: {'selected': row[1], 'accepted': row[2], 'completed': row[3]} 
                for row in cur.fetchall()}
    
    text = "📝 **Your Dare History**\n\n"
    
    category_emojis = {
        'funny': '😂',
        'romantic': '💖',
        'spicy': '🌶️',
        'adventurous': '🏋️',
        'general': '🎯'
    }
    
    difficulty_emojis = {
        'easy': '🟢',
        'medium': '🟡',
        'extreme': '🔴'
    }
    
    for i, (sub_id, dare_text, category, difficulty, approved, sub_date, created_at) in enumerate(submissions[:5]):
        dare_stats = stats.get(sub_id, {'selected': 0, 'accepted': 0, 'completed': 0})
        
        status = "✅ Approved" if approved else "⏳ Under Review"
        cat_emoji = category_emojis.get(category, '🎯')
        diff_emoji = difficulty_emojis.get(difficulty, '🎯')
        
        text += f"**{i+1}.** {cat_emoji} {diff_emoji} {status}\n"
        text += f"*{dare_text[:50]}{'...' if len(dare_text) > 50 else ''}*\n"
        
        if approved and dare_stats['selected'] > 0:
            text += f"📊 Used {dare_stats['selected']}x | {dare_stats['accepted']} accepts\n"
        
        text += f"📅 {sub_date.strftime('%b %d')}\n\n"
    
    # Summary stats
    total_submitted = len(submissions)
    approved_count = sum(1 for s in submissions if s[4])  # approved column
    total_usage = sum(stats[s[0]]['selected'] for s in submissions)
    
    text += f"📈 **Your Impact:**\n"
    text += f"🎯 Total Submitted: {total_submitted}\n"
    text += f"✅ Approved: {approved_count}\n"
    text += f"🔥 Times Used: {total_usage}\n\n"
    text += f"💡 Keep creating! Use /submitdare for more."
    
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 Detailed Stats", callback_data="mydares:detailed"),
        InlineKeyboardButton("🆕 Submit New", callback_data="mydares:submit")
    ]])
    
    await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")

# --------- Enhanced Engagement Features ---------
async def send_morning_dare_recap(context: ContextTypes.DEFAULT_TYPE):
    """Send morning recap of last night's dare activity"""
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    
    # Get all active users
    from handlers.notifications import _nudge_users
    users = await _nudge_users()
    
    with _conn() as con, con.cursor() as cur:
        # Get yesterday's stats by difficulty
        cur.execute("""
            SELECT 
                difficulty_selected,
                COUNT(*) FILTER (WHERE response='accepted') as accepted,
                COUNT(*) FILTER (WHERE response='declined') as declined,
                COUNT(*) FILTER (WHERE response='expired') as expired
            FROM dare_responses 
            WHERE dare_date=%s 
            GROUP BY difficulty_selected
        """, (yesterday,))
        
        yesterday_stats = {}
        for row in cur.fetchall():
            diff, acc, dec, exp = row
            yesterday_stats[diff] = {'accepted': acc, 'declined': dec, 'expired': exp}
    
    if not yesterday_stats:
        return  # No activity yesterday
    
    text = "🌅 **Good Morning! Last Night's Dare Recap**\n\n"
    
    difficulty_emojis = {
        'easy': '🟢',
        'medium': '🟡',
        'extreme': '🔴'
    }
    
    total_brave = 0
    total_scared = 0
    
    for diff in ['easy', 'medium', 'extreme']:
        if diff in yesterday_stats:
            stats = yesterday_stats[diff]
            acc, dec, exp = stats['accepted'], stats['declined'], stats['expired']
            total = acc + dec + exp
            
            if total > 0:
                emoji = difficulty_emojis.get(diff, '🎯')
                text += f"{emoji} **{diff.title()}:** {acc} brave, {dec} scared, {exp} missed\n"
                total_brave += acc
                total_scared += dec
    
    if total_brave + total_scared > 0:
        text += f"\n🔥 **{total_brave} people were brave last night!**\n"
        text += f"🐔 **{total_scared} chickened out**\n\n"
        text += f"Tonight's dares drop at 11:00 PM. Will you be brave?\n"
        text += f"⚡ Type /timedare when it's time!"
        
        # Send to random sample of users to avoid spam
        import random
        sample_users = random.sample(users, min(len(users), 200))
        
        sent = 0
        for uid in sample_users:
            try:
                await context.bot.send_message(uid, text, parse_mode="Markdown")
                sent += 1
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception:
                pass
        
        print(f"[morning-recap] Sent to {sent}/{len(sample_users)} users")

# --------- Main Command Entry Points ---------
async def cmd_timedare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main entry point for timed dare system (consolidated from dare_60s.py)"""
    try:
        _ensure_dare_schema()  # Ensure tables exist
        return await cmd_advanced_dare(update, context)
    except Exception as e:
        print(f"[timedare] Advanced system error: {e}")
        # Fallback to basic system
        now_ist = datetime.datetime.now(IST).time()
        if now_ist.hour == 23:   # live window
            try:
                await update.message.reply_text(DARE_TEXT, parse_mode="Markdown")
            except Exception:
                pass
            await update.message.reply_text(f"⚡ Dare is LIVE:\n{get_daily_dare()}")
        else:
            await _send_not_live_dare(update, context)

async def _send_not_live_dare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show locked gate message with reminder option"""
    next_drop = _next_ist_time(23, 0).strftime("%I:%M %p")
    text = (
        "🚨 Advanced 60-Second Dare System 🚨\n\n"
        "🔒 Advanced Dare Gate Locked! 11:00-11:55 PM IST pe khulta hai — 55 minutes decision time!\n"
        "🔒 Advanced Dare Gate Locked! Opens 11:00-11:55 PM IST — 55 minutes to decide!\n\n"
        "📅 **Active Days:** Mon Wed Fri Sat Sun\n"
        f"⏰ Next drop: {next_drop} IST\n\n"
        "🔔 \"Remind me\" dabao, 10:59 pm pe ping milega.\n"
        "Tap \"Remind me\" and we'll ping you at 10:59 pm."
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔔 Set Reminder", callback_data="dare:remind"),
            InlineKeyboardButton("📊 Yesterday's Stats", callback_data="dare:yesterday_stats")
        ],
        [
            InlineKeyboardButton("📝 Submit Dare", callback_data="dare:submit")
        ]
    ])
    await update.effective_message.reply_text(text, reply_markup=kb)

# --------- Reminder System (consolidated from dare_60s.py) ---------
async def handle_dare_reminder_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reminder and yesterday stats callbacks"""
    query = update.callback_query
    await query.answer()
    
    
    if query.data == "dare:yesterday":
        # Get yesterday's dare stats
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        _ensure_dare_schema()
        
        with _conn() as con, con.cursor() as cur:
            # Get yesterday's stats
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE response='accepted') as accepted,
                    COUNT(*) FILTER (WHERE response='declined') as declined,
                    COUNT(*) FILTER (WHERE response='expired') as expired,
                    COUNT(*) as total
                FROM dare_responses WHERE dare_date=%s
            """, (yesterday,))
            stats = cur.fetchone()
            accepted, declined, expired, total = stats if stats else (0, 0, 0, 0)
            
            # Get top performers
            cur.execute("""
                SELECT COUNT(*) as streak_count
                FROM dare_responses 
                WHERE response='accepted' AND dare_date=%s
                ORDER BY streak_count DESC
                LIMIT 3
            """, (yesterday,))
            top_performers = cur.fetchall()
        
        if total == 0:
            return await query.edit_message_text(
                f"📊 **Yesterday's Dare Stats** ({yesterday.strftime('%b %d')})\n\n"
                "🚫 No dare activity yesterday!\n"
                "Either it was a rest day or no one participated.\n\n"
                "💪 Tonight's your chance to be brave!"
            )
        
        brave_percentage = round((accepted / total) * 100) if total > 0 else 0
        
        text = (
            f"📊 **Yesterday's Dare Stats** ({yesterday.strftime('%b %d')})\n\n"
            f"👥 **Total Participants:** {total}\n"
            f"💪 **Brave Souls:** {accepted} ({brave_percentage}%)\n"
            f"🐔 **Chickened Out:** {declined}\n"
            f"⏰ **Missed Deadline:** {expired}\n\n"
            f"🔥 **Community Courage:** {brave_percentage}%\n"
            f"💡 Will you be braver tonight?"
        )
        
        return await query.edit_message_text(text)
    
    if query.data == "dare:remind":
        # cancel previous reminder if any
        job_name = f"dare-remind-{query.from_user.id}"
        for j in context.job_queue.get_jobs_by_name(job_name):
            j.schedule_removal()

        # schedule 10:59 pm IST reminder
        when = _next_ist_time(22, 59)   # 10:59 pm IST
        context.job_queue.run_once(send_dare_reminder, when=when, chat_id=query.message.chat_id, name=job_name)
        return await query.edit_message_text("🔔 Reminder set for 10:59 pm IST. We'll ping you before the gate opens.")

async def send_dare_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send reminder notification at 10:59 PM"""
    try:
        await context.bot.send_message(
            context.job.chat_id,
            "🚨 Advanced Dare Gate opens in 1 minute! Type /timedare and face community challenge with 55-min timer!"
        )
    except Exception:
        pass

# --------- Registration ---------
def register_advanced_dare_handlers(app):
    """Register all advanced dare handlers (consolidated from dare_60s.py)"""
    import logging
    log = logging.getLogger("advanced_dare")
    
    # Main commands - use group -7 to run before text_firewall (group 0)
    app.add_handler(CommandHandler("timedare", cmd_timedare), group=-7)
    app.add_handler(CommandHandler("submitdare", cmd_submitdare), group=-7)
    app.add_handler(CommandHandler("mydares", cmd_mydares), group=-7)
    # /dare is reserved for original left menu questions
    
    # CRITICAL FIX: Text handler for dare submissions - HIGH PRIORITY
    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dare_submission_text), group=-7)
    
    # Reminder and stats callbacks - HIGHEST PRIORITY (must come first)
    app.add_handler(CallbackQueryHandler(handle_dare_reminder_callbacks, pattern="^dare:(remind|yesterday)$"), group=-7)
    
    # Dare interaction callbacks - HIGH PRIORITY (excludes remind/stats)
    app.add_handler(CallbackQueryHandler(handle_dare_callbacks, pattern="^dare:(?!remind$|yesterday$)"), group=-7)
    
    # Submission flow callbacks - HIGH PRIORITY
    app.add_handler(CallbackQueryHandler(handle_submission_callbacks, pattern="^submit:"), group=-7)
    
    # MyDares callbacks - HIGH PRIORITY
    app.add_handler(CallbackQueryHandler(handle_mydares_callbacks, pattern="^mydares:"), group=-7)
    
    # Admin approval system - HIGH PRIORITY
    app.add_handler(CommandHandler("approvepending", cmd_admin_approve_dares), group=-7)
    app.add_handler(CallbackQueryHandler(handle_admin_dare_callbacks, pattern="^admin_dare_"), group=-7)
    
    # SUCCESS LOG
    log.info("[advanced_dare] ✅ Handlers registered successfully at group -7 (high priority)")