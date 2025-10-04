# handlers/naughty_wyr.py
# Naughty WYR — sync DB (registration._conn), time windows, suspense, streaks

import datetime, random, time
import asyncio  # FIX 1: Added missing asyncio import
import pytz
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from registration import _conn

IST = pytz.timezone("Asia/Kolkata")

# --------- Windows ---------
def _now_ist() -> datetime.datetime:
    return datetime.datetime.now(IST)

def _in_live_window(t: datetime.datetime) -> bool:
    s = t.replace(hour=20, minute=15, second=0, microsecond=0)  # 8:15 pm
    e = (t + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)  # 12:00 am
    return s <= t <= e

def _in_results_only(t: datetime.datetime) -> bool:
    # Results only: 00:00 (midnight) to 08:15 AM same day
    start_of_day = t.replace(hour=0, minute=0, second=0, microsecond=0)  # 00:00 am today
    results_end = t.replace(hour=8, minute=15, second=0, microsecond=0)  # 8:15 am today
    return start_of_day <= t < results_end

# --------- Bars ---------
def _bar(p: int) -> str:
    fill = max(0, min(10, round(p/10)))
    return "█"*fill + "░"*(10-fill)

# --------- EXPLICIT 18+ NAUGHTY WYR PAIRS ---------
NAUGHTY_WYR_PAIRS = [
    ("Never have an orgasm again", "Orgasm every hour on the hour"),
    ("Only have sex in bed for life", "Never be able to have sex in bed again"),
    ("Publish your porn search history", "Read all your texts aloud to your hometown"),
    ("Have a one-night stand", "Have a bubble bath with a stranger"),
    ("Sex with someone you hate but amazing", "Sex with someone you love but terrible"),
    ("Always have sex with lights on", "Always have sex in pitch-black room"),
    ("Never have good food again", "Never have good sex again"),
    ("Never have foreplay again", "Only have foreplay, no penetrative sex"),
    ("Cry every time you climax", "Orgasm every time you cry"),
    ("Threesome with someone you know", "Threesome with complete strangers"),
    ("Sex with a co-worker", "Sex with a high school friend"),
    ("Be blindfolded during sex", "Blindfold your partner during sex"),
    ("Only have kinky sex", "Only have romantic sex"),
    ("Only have morning sex", "Only have late-night sex"),
    ("Give up oral sex forever", "Give up anal sex forever"),
    ("Always be dominant in bed", "Always be submissive in bed"),
    ("Have sex in the bathroom", "Have sex in the kitchen"),
    ("Always be on top", "Always be on the bottom"),
    ("Be a bad kisser", "Be bad at giving oral sex"),
    ("Only give pleasure", "Only receive pleasure"),
    ("Be tied up during sex", "Be blindfolded during sex"),
    ("Sex in a secluded forest", "Sex on a secluded beach"),
    ("Use whipped cream in foreplay", "Use chocolate syrup in foreplay"),
    ("Quickie where you might get caught", "Planned intimate night at home"),
    ("Incorporate food into sex life", "Keep food strictly for dining"),
    ("Passionate sex after a fight", "Make love softly to resolve conflict"),
    ("Talk dirty over text all day", "Save dirty talk for when together"),
    ("Wear provocative lingerie under clothes", "Wear nothing under clothes for date"),
    ("Sensual massage with oil", "Stimulating massage with feather"),
    ("Role-play as strangers", "Role-play as historical figures"),
    ("Incorporate music into lovemaking", "Prefer sounds of nature during sex"),
    ("Steamy session in hot tub", "Steamy session under waterfall"),
    ("Have your hair pulled", "Have your back scratched"),
    ("End dates with sensual dance", "End dates with striptease"),
    ("Sex while watching steamy movie", "Sex while listening to seductive music"),
    ("Hushed quickie with guests nearby", "Wait until everyone leaves"),
    ("Partner speaks in accent during foreplay", "Partner stays silent but expressive"),
    ("Shower together every day", "Bubble baths only on special occasions"),
    ("Explore with body paint", "Explore with blindfolds and sensation play"),
    ("Make out in the rain", "Make out in backseat of car"),
    ("Be teased with feather", "Be teased with ice cubes"),
    ("Wake up to oral sex", "Wake up to full-body massage"),
    ("Skinny dip at midnight", "Sunbathe nude during day"),
    ("Playfully wrestle in bed", "Have tickle fight in bed"),
    ("Send naughty photos", "Receive naughty photos"),
    ("Have sex somewhere risky", "Have sex somewhere comfortable"),
    ("Be spanked lightly", "Be kissed all over"),
    ("Use handcuffs", "Use silk ties"),
    ("Have a secret affair", "Have an open relationship"),
    ("Make a sex tape", "Take intimate photos"),
    ("Have sex in public place", "Have sex in complete privacy"),
    ("Be with someone experienced", "Be with someone innocent"),
    ("Have rough passionate sex", "Have slow sensual sex"),
    ("Use adult toys", "Use only hands and mouth"),
    ("Have sex with lights on", "Have sex with candles only"),
    ("Be seduced slowly", "Be taken spontaneously"),
    ("Have multiple partners in life", "Have only one soulmate"),
    ("Experiment with new positions", "Stick to favorite positions"),
    ("Have sex outdoors", "Have sex in luxury hotel"),
    ("Be desired for your body", "Be desired for your mind"),
    ("Have amazing sex once a month", "Have good sex every day"),
    ("Be the seducer", "Be the one seduced"),
    ("Have steamy shower sex", "Have romantic bathtub sex"),
    ("Use food during sex", "Use massage oils during sex"),
    ("Have a forbidden romance", "Have a perfect relationship"),
    ("Be sexually adventurous", "Be emotionally intimate"),
    ("Have passionate but short relationship", "Have loving but platonic relationship"),
    ("Be irresistible to others", "Find others irresistible"),
    ("Have wild honeymoon", "Have romantic honeymoon"),
    ("Be experienced lover", "Be someone's first love"),
    ("Have chemistry with everyone", "Have deep connection with one person"),
    ("Be remembered for passion", "Be remembered for tenderness"),
    ("Have steamy long-distance relationship", "Have comfortable live-in relationship"),
    ("Be desired by many", "Be loved deeply by one"),
    ("Have exciting secret relationship", "Have stable public relationship"),
    ("Be the fantasy of others", "Have your fantasies fulfilled"),
    ("Have amazing first kiss", "Have amazing last kiss"),
    ("Be seduced with words", "Be seduced with touch"),
    ("Have relationship full of surprises", "Have relationship full of comfort"),
    ("Be the one who gives pleasure", "Be the one who receives pleasure"),
    ("Have steamy vacation romance", "Have cozy home relationship"),
    ("Be with someone who challenges you", "Be with someone who comforts you"),
    ("Have passionate arguments that lead to makeup sex", "Have peaceful relationship with gentle intimacy"),
    ("Be desired for being mysterious", "Be loved for being open"),
    ("Have relationship with lots of physical chemistry", "Have relationship with deep emotional bond"),
    ("Be the one who initiates", "Be the one who responds"),
    ("Have wild party lifestyle with partner", "Have quiet intimate lifestyle with partner"),
    ("Be with someone who's your opposite", "Be with someone who's your match"),
    ("Have relationship that's all passion", "Have relationship that's all romance"),
    ("Be remembered as someone's greatest love", "Be remembered as someone's best friend"),
    ("Have love that burns bright and fast", "Have love that grows slowly and lasts"),
    ("Be with someone who worships your body", "Be with someone who adores your soul"),
    ("Have relationship full of adventure", "Have relationship full of peace"),
    ("Be the one who's chased", "Be the one who chases"),
    ("Have love that's like a drug", "Have love that's like a warm embrace"),
    ("Be with someone who's your addiction", "Be with someone who's your cure"),
    ("Have relationship that's your weakness", "Have relationship that's your strength"),
    ("Be loved for your wild side", "Be loved for your gentle side"),
    ("Have partner who's your perfect match in bed", "Have partner who's your perfect match in life"),
    ("Be with someone who makes you lose control", "Be with someone who makes you feel safe"),
    ("Have love that's your beautiful disaster", "Have love that's your perfect peace"),
    ("Be desired beyond reason", "Be loved beyond measure"),
    ("Have relationship that's your sweet sin", "Have relationship that's your salvation"),
    ("Be with someone who's your temptation", "Be with someone who's your inspiration"),
    ("Have love that's dangerously addictive", "Have love that's beautifully healing")
]

# --------- Ensure schema (idempotent) ---------
def _ensure_schema():
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS wyr_streak INT DEFAULT 0")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS wyr_last_voted DATE")
            cur.execute("""
              CREATE TABLE IF NOT EXISTS wyr_question_of_day(
                vote_date DATE PRIMARY KEY,
                a_text    TEXT NOT NULL,
                b_text    TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
              )
            """)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS wyr_votes(
                tg_user_id BIGINT NOT NULL,
                vote_date  DATE   NOT NULL,
                side       CHAR(1) NOT NULL CHECK (side IN ('A','B')),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (tg_user_id, vote_date)
              )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_wyr_votes_date_side ON wyr_votes(vote_date, side)")

            # Anonymous group chat tables
            cur.execute("""
              CREATE TABLE IF NOT EXISTS wyr_group_chats (
                vote_date DATE PRIMARY KEY,
                total_voters INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '1 day')
              )
            """)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS wyr_anonymous_users (
                id BIGSERIAL PRIMARY KEY,
                vote_date DATE NOT NULL,
                tg_user_id BIGINT NOT NULL,
                anonymous_name TEXT NOT NULL,
                assigned_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (vote_date, tg_user_id),
                UNIQUE (vote_date, anonymous_name)
              )
            """)
            cur.execute("""
              CREATE TABLE IF NOT EXISTS wyr_group_messages (
                id BIGSERIAL PRIMARY KEY,
                vote_date DATE NOT NULL,
                anonymous_user_id BIGINT REFERENCES wyr_anonymous_users(id) ON DELETE CASCADE,
                message_type TEXT DEFAULT 'comment' CHECK (message_type IN ('comment', 'reaction', 'reply')),
                content TEXT NOT NULL,
                reply_to_message_id BIGINT REFERENCES wyr_group_messages(id) ON DELETE SET NULL,
                is_deleted BOOLEAN DEFAULT FALSE,
                deleted_by_admin BIGINT DEFAULT NULL,
                deleted_at TIMESTAMPTZ DEFAULT NULL,
                reaction_count INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                hearts INTEGER DEFAULT 0,
                laughs INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
              )
            """)

            # Permanent username system table
            cur.execute("""
              CREATE TABLE IF NOT EXISTS wyr_permanent_users (
                tg_user_id BIGINT PRIMARY KEY,
                permanent_username TEXT UNIQUE NOT NULL,
                assigned_at TIMESTAMPTZ DEFAULT NOW(),
                total_comments INTEGER DEFAULT 0,
                total_likes INTEGER DEFAULT 0,
                weekly_comments INTEGER DEFAULT 0,
                weekly_likes INTEGER DEFAULT 0,
                last_reset TIMESTAMPTZ DEFAULT NOW()
              )
            """)

            # Reactions table
            cur.execute("""
              CREATE TABLE IF NOT EXISTS wyr_message_reactions (
                id BIGSERIAL PRIMARY KEY,
                message_id BIGINT REFERENCES wyr_group_messages(id) ON DELETE CASCADE,
                tg_user_id BIGINT NOT NULL,
                reaction_type TEXT NOT NULL CHECK (reaction_type IN ('like', 'heart', 'laugh')),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE (message_id, tg_user_id, reaction_type)
              )
            """)

            # Create indexes for anonymous group chat
            cur.execute("CREATE INDEX IF NOT EXISTS idx_wyr_anonymous_users_date ON wyr_anonymous_users(vote_date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_wyr_anonymous_users_tg_id ON wyr_anonymous_users(tg_user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_wyr_group_messages_date ON wyr_group_messages(vote_date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_wyr_group_messages_created ON wyr_group_messages(created_at DESC)")

            con.commit()
    except Exception:
        pass

# --------- Question helpers ---------
def _get_or_seed_today_question() -> tuple[str, str]:
    today = datetime.date.today()
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT a_text, b_text FROM wyr_question_of_day WHERE vote_date=%s", (today,))
        row = cur.fetchone()
        if row:
            return row[0], row[1]

        # Use explicit 18+ naughty questions with daily seed
        seed = int(today.strftime("%Y%m%d"))
        rnd = random.Random(seed)
        a, b = rnd.choice(NAUGHTY_WYR_PAIRS)

        cur.execute(
            "INSERT INTO wyr_question_of_day(vote_date, a_text, b_text) VALUES(%s,%s,%s) ON CONFLICT(vote_date) DO NOTHING",
            (today, a, b)
        )
        con.commit()
        return a, b

def _counts_today() -> tuple[int,int,int]:
    today = datetime.date.today()
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM wyr_votes WHERE vote_date=%s AND side='A'", (today,))
        a = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM wyr_votes WHERE vote_date=%s AND side='B'", (today,))
        b = int(cur.fetchone()[0])
    return a, b, a+b

def _hybrid_live(eligible_today: int, total_votes: int) -> int:
    """Calculate hybrid live count based on eligible users and actual votes"""
    return max(total_votes, (eligible_today // 10) + random.randint(5, 25))

# --------- Admin Functions --------
def _is_admin(tg_user_id: int) -> bool:
    """Check if user is admin"""
    import os
    import re
    admin_ids_str = os.getenv('ADMIN_IDS', '647778438 1437934486')
    admin_ids = {int(x) for x in re.findall(r'\d+', admin_ids_str)}
    return tg_user_id in admin_ids

def _delete_comment(message_id: int, admin_id: int) -> bool:
    """Delete comment by admin"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                UPDATE wyr_group_messages 
                SET is_deleted = TRUE, deleted_by_admin = %s, deleted_at = NOW()
                WHERE id = %s AND is_deleted = FALSE
            """, (admin_id, message_id))

            con.commit()
            return cur.rowcount > 0
    except Exception:
        return False

def _add_reaction(tg_user_id: int, message_id: int, reaction_type: str) -> bool:
    """Add reaction to message"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Add reaction (will ignore if already exists)
            cur.execute("""
                INSERT INTO wyr_message_reactions (message_id, tg_user_id, reaction_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (message_id, tg_user_id, reaction_type) DO NOTHING
            """, (message_id, tg_user_id, reaction_type))

            # Update reaction counts on message
            cur.execute("""
                UPDATE wyr_group_messages 
                SET 
                    likes = (SELECT COUNT(*) FROM wyr_message_reactions WHERE message_id = %s AND reaction_type = 'like'),
                    hearts = (SELECT COUNT(*) FROM wyr_message_reactions WHERE message_id = %s AND reaction_type = 'heart'),
                    laughs = (SELECT COUNT(*) FROM wyr_message_reactions WHERE message_id = %s AND reaction_type = 'laugh')
                WHERE id = %s
            """, (message_id, message_id, message_id, message_id))

            # Update reaction_count
            cur.execute("""
                UPDATE wyr_group_messages 
                SET reaction_count = likes + hearts + laughs
                WHERE id = %s
            """, (message_id,))

            con.commit()
            return cur.rowcount > 0
    except Exception:
        return False

# --------- Leaderboard Functions --------
def _get_top_comments(limit: int = 5) -> list:
    """Get most liked comments this week"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT 
                    m.content,
                    COALESCE(p.permanent_username, a.anonymous_name) as username,
                    COALESCE(like_counts.likes, 0) + COALESCE(heart_counts.hearts, 0) + COALESCE(laugh_counts.laughs, 0) as total_reactions,
                    COALESCE(like_counts.likes, 0) as likes,
                    COALESCE(heart_counts.hearts, 0) as hearts, 
                    COALESCE(laugh_counts.laughs, 0) as laughs
                FROM wyr_group_messages m
                JOIN wyr_anonymous_users a ON m.anonymous_user_id = a.id
                LEFT JOIN wyr_permanent_users p ON a.tg_user_id = p.tg_user_id
                LEFT JOIN (
                    SELECT message_id, COUNT(*) as likes 
                    FROM wyr_message_reactions 
                    WHERE reaction_type = 'like' 
                    GROUP BY message_id
                ) like_counts ON m.id = like_counts.message_id
                LEFT JOIN (
                    SELECT message_id, COUNT(*) as hearts 
                    FROM wyr_message_reactions 
                    WHERE reaction_type = 'heart' 
                    GROUP BY message_id
                ) heart_counts ON m.id = heart_counts.message_id
                LEFT JOIN (
                    SELECT message_id, COUNT(*) as laughs 
                    FROM wyr_message_reactions 
                    WHERE reaction_type = 'laugh' 
                    GROUP BY message_id
                ) laugh_counts ON m.id = laugh_counts.message_id
                WHERE m.vote_date >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY total_reactions DESC, m.created_at DESC
                LIMIT %s
            """, (limit,))

            return cur.fetchall()
    except Exception:
        return []

def _get_top_users(limit: int = 5) -> list:
    """Get most active users this week"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT 
                    permanent_username,
                    weekly_comments,
                    weekly_likes,
                    weekly_comments + weekly_likes as activity_score
                FROM wyr_permanent_users
                WHERE weekly_comments > 0 OR weekly_likes > 0
                ORDER BY activity_score DESC, weekly_comments DESC
                LIMIT %s
            """, (limit,))

            return cur.fetchall()
    except Exception:
        return []

# --------- Anonymous Group Chat Helper Functions ---------
def _get_or_assign_permanent_username(tg_user_id: int) -> str:
    """Get or assign PERMANENT username (User1 stays User1 forever!)"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Check if user already has permanent username
            cur.execute("""
                SELECT permanent_username FROM wyr_permanent_users 
                WHERE tg_user_id = %s
            """, (tg_user_id,))

            row = cur.fetchone()
            if row:
                return row[0]

            # Find next available username globally
            cur.execute("""
                SELECT MAX(CAST(SUBSTRING(permanent_username FROM 5) AS INTEGER))
                FROM wyr_permanent_users 
                WHERE permanent_username ~ '^User[0-9]+$'
            """)

            max_num = cur.fetchone()[0] or 0
            new_name = f"User{max_num + 1}"

            # Insert new permanent user
            cur.execute("""
                INSERT INTO wyr_permanent_users (tg_user_id, permanent_username)
                VALUES (%s, %s)
                ON CONFLICT (tg_user_id) DO UPDATE SET 
                permanent_username = EXCLUDED.permanent_username
                RETURNING permanent_username
            """, (tg_user_id, new_name))

            result = cur.fetchone()
            if result:
                con.commit()
                return result[0]
            else:
                return f"User{random.randint(1, 999)}"

    except Exception:
        return f"User{random.randint(1, 999)}"

def _get_or_assign_anonymous_name(tg_user_id: int, vote_date: datetime.date) -> str:
    """Get permanent username AND ensure wyr_anonymous_users entry exists for vote_date"""
    # First get or create permanent username
    permanent_username = _get_or_assign_permanent_username(tg_user_id)
    
    # Now ensure entry exists in wyr_anonymous_users for this vote_date
    try:
        with _conn() as con, con.cursor() as cur:
            # Check if entry already exists
            cur.execute("""
                SELECT id FROM wyr_anonymous_users 
                WHERE tg_user_id = %s AND vote_date = %s
            """, (tg_user_id, vote_date))
            
            if not cur.fetchone():
                # Create entry in wyr_anonymous_users with permanent username
                cur.execute("""
                    INSERT INTO wyr_anonymous_users (vote_date, tg_user_id, anonymous_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (vote_date, tg_user_id) DO NOTHING
                """, (vote_date, tg_user_id, permanent_username))
                con.commit()
    except Exception as e:
        print(f"[wyr] Failed to create anonymous user entry: {e}")
    
    return permanent_username

def _create_or_get_group_chat(vote_date: datetime.date) -> bool:
    """Create or get group chat for the day"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                INSERT INTO wyr_group_chats (vote_date, is_active)
                VALUES (%s, TRUE)
                ON CONFLICT (vote_date) DO NOTHING
            """, (vote_date,))
            con.commit()
            return True
    except Exception:
        return False


def _get_group_messages(vote_date: datetime.date, limit: int = 50) -> list:
    """Get recent messages from group chat"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT 
                    m.id,
                    COALESCE(p.permanent_username, a.anonymous_name) as username,
                    m.content,
                    m.message_type,
                    m.created_at,
                    m.reply_to_message_id,
                    COALESCE(like_counts.likes, 0) as likes,
                    COALESCE(heart_counts.hearts, 0) as hearts,
                    COALESCE(laugh_counts.laughs, 0) as laughs,
                    a.tg_user_id
                FROM wyr_group_messages m
                JOIN wyr_anonymous_users a ON m.anonymous_user_id = a.id
                LEFT JOIN wyr_permanent_users p ON a.tg_user_id = p.tg_user_id
                LEFT JOIN (
                    SELECT message_id, COUNT(*) as likes 
                    FROM wyr_message_reactions 
                    WHERE reaction_type = 'like' 
                    GROUP BY message_id
                ) like_counts ON m.id = like_counts.message_id
                LEFT JOIN (
                    SELECT message_id, COUNT(*) as hearts 
                    FROM wyr_message_reactions 
                    WHERE reaction_type = 'heart' 
                    GROUP BY message_id
                ) heart_counts ON m.id = heart_counts.message_id
                LEFT JOIN (
                    SELECT message_id, COUNT(*) as laughs 
                    FROM wyr_message_reactions 
                    WHERE reaction_type = 'laugh' 
                    GROUP BY message_id
                ) laugh_counts ON m.id = laugh_counts.message_id
                WHERE m.vote_date = %s AND (m.is_deleted IS NULL OR m.is_deleted = FALSE)
                ORDER BY m.created_at DESC
                LIMIT %s
            """, (vote_date, limit))

            messages = []
            for row in cur.fetchall():
                messages.append({
                    'id': row[0],
                    'anonymous_name': row[1],  # Now permanent username
                    'content': row[2],
                    'message_type': row[3],
                    'created_at': row[4],
                    'reply_to_message_id': row[5],
                    'likes': row[6] or 0,
                    'hearts': row[7] or 0,
                    'laughs': row[8] or 0,
                    'tg_user_id': row[9]
                })

            return list(reversed(messages))  # Show oldest first
    except Exception:
        return []

def _add_group_message(tg_user_id: int, vote_date: datetime.date, content: str, message_type: str = 'comment') -> bool:
    """Add message to group chat"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Get anonymous user ID
            cur.execute("""
                SELECT id FROM wyr_anonymous_users 
                WHERE tg_user_id=%s AND vote_date=%s
            """, (tg_user_id, vote_date))
            row = cur.fetchone()
            if not row:
                return False

            anonymous_user_id = row[0]

            # Add message
            cur.execute("""
                INSERT INTO wyr_group_messages (vote_date, anonymous_user_id, message_type, content)
                VALUES (%s, %s, %s, %s)
            """, (vote_date, anonymous_user_id, message_type, content))

            # Update message count
            cur.execute("""
                UPDATE wyr_group_chats 
                SET total_messages = total_messages + 1
                WHERE vote_date = %s
            """, (vote_date,))

            # Update weekly stats for permanent user
            cur.execute("""
                UPDATE wyr_permanent_users 
                SET weekly_comments = weekly_comments + 1,
                    total_comments = total_comments + 1
                WHERE tg_user_id = %s
            """, (tg_user_id,))

            con.commit()
            return True
    except Exception:
        return False


def _delete_comment(msg_id: int, admin_uid: int = None) -> bool:
    """Delete a comment (admin only)"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Mark message as deleted instead of actually deleting
            cur.execute("""
                UPDATE wyr_group_messages 
                SET is_deleted = TRUE 
                WHERE id = %s
            """, (msg_id,))

            con.commit()
            return True
    except Exception:
        return False

# --------- Locked info copy (before 8:15 / after midnight) ---------
FINAL_INFO_COPY = (
    "⚠️ Don't be in such a hurry 😉\n"
    "Tonight's Naughty WYR drops only at 8:15 PM ⏰\n\n"
    "ℹ️ In order to receive your daily question:\n"
    "- You must press /start at least once a day ✅\n"
    "- Stay active for a few minutes around 8:15 PM 👀\n"
    "- If you miss a day, you'll miss that day's question ❌\n\n"
    "🔥 Be ready… or regret it till tomorrow 😈"
)

# --------- Helper Functions for Vote Checking ---------
def _has_user_voted_today(uid: int, today: datetime.date) -> tuple:
    """Check if user has voted today and return (bool, choice)"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT side FROM wyr_votes 
                WHERE tg_user_id = %s AND vote_date = %s
            """, (uid, today))
            row = cur.fetchone()
            if row:
                return True, row[0]  # Return (True, 'A' or 'B')
            return False, None
    except Exception:
        return False, None

async def _show_post_vote_interface(update: Update, user_choice: str):
    """Show direct group chat interface for users who have already voted"""
    today = datetime.date.today()
    uid = update.effective_user.id
    
    # Create group chat and get anonymous name
    _create_or_get_group_chat(today)
    anonymous_name = _get_or_assign_anonymous_name(uid, today)
    messages = _get_group_messages(today, limit=10)
    
    # Build direct group chat interface (same as on_nwyr_chat)
    chat_text = "🎭 **ANONYMOUS GROUP CHAT**\n\n"
    
    if messages:
        chat_text += "💬 **Recent Messages:**\n\n"
        for i, msg in enumerate(messages[-10:]):  # Show last 10 messages
            # Convert UTC timestamp to IST before displaying
            utc_time = msg['created_at'].replace(tzinfo=pytz.UTC) if msg['created_at'].tzinfo is None else msg['created_at']
            ist_time = utc_time.astimezone(IST)
            time_str = ist_time.strftime("%H:%M")
            username = msg['anonymous_name']  # This now uses permanent usernames

            # Add reactions display
            reactions = ""
            if msg.get('likes', 0) > 0:
                reactions += f"👍{msg['likes']} "
            if msg.get('hearts', 0) > 0:
                reactions += f"❤️{msg['hearts']} "
            if msg.get('laughs', 0) > 0:
                reactions += f"😂{msg['laughs']} "

            # Add admin tag if user is admin
            admin_tag = ""
            if _is_admin(uid):
                admin_tag = f" [ID:{msg['id']}]"

            chat_text += f"👤 **{username}** ({time_str}){admin_tag}:\n{msg['content']}\n\n"
    else:
        chat_text += "💭 **No messages yet. Be the first to comment!**\n\n"

    chat_text += f"\n👤 **You are:** {anonymous_name}\n"
    chat_text += "🔒 **Complete anonymity guaranteed**\n\n"
    chat_text += "💡 *Tap 'Add Comment' to share your thoughts!*"

    # Create keyboard with simple controls (same as group chat)
    keyboard = [
        [InlineKeyboardButton("🎯 Add Comment", callback_data="nwyr:comment")],
        [InlineKeyboardButton("🔄 Refresh Chat", callback_data="nwyr:chat"),
         InlineKeyboardButton("📊 View Results", callback_data="nwyr:results")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="nwyr:leaderboard")]
    ]

    # Add admin button if user is admin and has messages
    if _is_admin(uid) and messages:
        keyboard.append([InlineKeyboardButton("🗑️ Admin: Delete Comment", callback_data="nwyr:admin_mode")])

    kb = InlineKeyboardMarkup(keyboard)
    
    return await update.message.reply_text(chat_text, reply_markup=kb, parse_mode="Markdown")

# --------- /naughtywyr command ---------
async def cmd_naughtywyr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_schema()
    now = _now_ist()

    if _in_live_window(now):
        # During live window (8:15 PM - 12:00 AM), check if user has voted
        today = datetime.date.today()
        uid = update.effective_user.id
        
        # Check if user has already voted today
        has_voted, user_choice = _has_user_voted_today(uid, today)
        
        if has_voted:
            # User has voted - show post-vote results interface
            return await _show_post_vote_interface(update, user_choice)
        else:
            # User hasn't voted - show voting interface
            a_text, b_text = _get_or_seed_today_question()
            a_votes, b_votes, total_votes = _counts_today()

            # Get eligible users count for live calculation
            with _conn() as con, con.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users WHERE last_seen::date = CURRENT_DATE")
                eligible_today = cur.fetchone()[0] or 0

            # Calculate hybrid live count
            live = _hybrid_live(eligible_today, total_votes)

            text = (f"🤭 Naughty Would You Rather (18+)\n\n"
                    f"💋 {a_text}\n"
                    f"🔥 {b_text}\n\n"
                    f"⚡ LIVE NOW: {live} have voted so far!")

            # Create voting keyboard based on user's premium status
            from registration import has_active_premium

            if has_active_premium(uid):
                premium_btn = InlineKeyboardButton("💎 See who voted", callback_data="nwyr:who")
            else:
                premium_btn = InlineKeyboardButton("💎 See who voted", callback_data="premium:open")

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💋 Option A", callback_data="nwyr:vote:A"),
                 InlineKeyboardButton("🔥 Option B", callback_data="nwyr:vote:B")],
                [premium_btn]
            ])

            return await update.message.reply_text(text, reply_markup=kb)

    if _in_results_only(now):
        a_text, b_text = _get_or_seed_today_question()
        a_votes, b_votes, total = _counts_today()
        a_pct = int((a_votes / max(1,total)) * 100); b_pct = 100 - a_pct
        txt = (
            "🕘 Voting Closed — Results only\n\n"
            f"💋 A: {a_pct}%  [{_bar(a_pct)}]  ({a_votes})\n"
            f"🔥 B: {b_pct}%  [{_bar(b_pct)}]  ({b_votes})\n\n"
            "⚠️ Come back tomorrow at 8:15 PM."
        )
        return await update.message.reply_text(txt)

    # Before 8:15 or after expiry -> info rules
    return await update.message.reply_text(FINAL_INFO_COPY)

# --------- Scheduler push at 8:15 PM (notifications.job_wyr_push calls this) ---------
async def push_naughty_wyr_question(context: ContextTypes.DEFAULT_TYPE):
    _ensure_schema()
    today = datetime.date.today()
    a_text, b_text = _get_or_seed_today_question()

    # Eligible users = /start today AND notify ON
    with _conn() as con, con.cursor() as cur:
        try:
            cur.execute("""
              SELECT tg_user_id
              FROM users
              WHERE COALESCE(feed_notify, TRUE)=TRUE
                AND last_seen::date = CURRENT_DATE
            """)
            recipients = [int(r[0]) for r in (cur.fetchall() or [])]
        except Exception:
            recipients = []

    # Get eligible users count (who pressed /start today)
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM users WHERE last_seen::date = CURRENT_DATE")
        eligible_today = cur.fetchone()[0] or 0

    # Get total votes so far
    a_votes, b_votes, total_votes = _counts_today()

    # Calculate hybrid live count
    live = _hybrid_live(eligible_today, total_votes)

    text = (f"🤭 Naughty Would You Rather (18+)\n\n"
            f"💋 {a_text}\n"
            f"🔥 {b_text}\n\n"
            f"⚡ LIVE NOW: {live} have voted so far!")

    sent = 0
    for uid in recipients:
        try:
            # Create dynamic keyboard based on user's premium status
            from registration import has_active_premium

            if has_active_premium(uid):
                premium_btn = InlineKeyboardButton("💎 See who voted", callback_data="nwyr:who")
            else:
                premium_btn = InlineKeyboardButton("💎 See who voted", callback_data="premium:open")

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💋 Option A", callback_data="nwyr:vote:A"),
                 InlineKeyboardButton("🔥 Option B", callback_data="nwyr:vote:B")],
                [premium_btn]
            ])

            await context.bot.send_message(uid, text, reply_markup=kb)
            sent += 1
        except Exception:
            pass
    print(f"[nwyr-push] sent={sent}/{len(recipients)}")

# --------- Vote handler ---------
async def on_nwyr_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_schema()
    q = update.callback_query
    await q.answer()

    now = _now_ist()
    if not _in_live_window(now):
        if _in_results_only(now):
            a_votes, b_votes, total = _counts_today()
            a_pct = int((a_votes / max(1,total)) * 100); b_pct = 100 - a_pct
            return await q.edit_message_text(
                "🕘 Voting Closed — Results only\n\n"
                f"💋 A: {a_pct}%  [{_bar(a_pct)}]  ({a_votes})\n"
                f"🔥 B: {b_pct}%  [{_bar(b_pct)}]  ({b_votes})\n\n"
                "⚠️ Come back tomorrow at 8:15 PM."
            )
        return await q.edit_message_text("⚠️ Expired. Wait for tonight 8:15 PM.")

    side = 'A' if q.data.endswith(":A") else 'B'
    uid  = q.from_user.id
    today = datetime.date.today()

    # Save / update vote
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
              INSERT INTO wyr_votes(tg_user_id, vote_date, side)
              VALUES(%s,%s,%s)
              ON CONFLICT (tg_user_id, vote_date)
              DO UPDATE SET side=EXCLUDED.side
            """, (uid, today, side))
            con.commit()
    except Exception:
        pass

    # Streak update
    new_streak = 1
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("SELECT wyr_last_voted, wyr_streak FROM users WHERE tg_user_id=%s", (uid,))
            row = cur.fetchone()
            last = row[0] if row else None
            streak = int(row[1] or 0) if row else 0
            new_streak = streak + 1 if (last is None or last != today) else streak
            cur.execute("""
              UPDATE users SET wyr_streak=%s, wyr_last_voted=%s WHERE tg_user_id=%s
            """, (new_streak, today, uid))
            con.commit()
    except Exception:
        pass

    # Suspense
    try:
        await q.edit_message_text("Vote saved! Taking you to anonymous group chat... 🔥")
        await asyncio.sleep(2)
    except Exception:
        pass

    # Create group chat and assign anonymous name
    _create_or_get_group_chat(today)
    anonymous_name = _get_or_assign_anonymous_name(uid, today)

    # Get question text for context
    a_text, b_text = _get_or_seed_today_question()
    choice_display = "💋 Option A" if side=='A' else "🔥 Option B"

    # Show anonymous group chat interface
    txt = (
        "🎭 **ANONYMOUS GROUP CHAT**\n\n"
        f"**Today's Question:**\n"
        f"💋 A: {a_text}\n"
        f"🔥 B: {b_text}\n\n"
        f"✅ **You chose:** {choice_display}\n"
        f"👤 **Your anonymous name:** {anonymous_name}\n"
        f"🔥 **Streak:** {new_streak} days\n\n"
        "💬 **Share your thoughts anonymously!**\n"
        "Others who voted can see and comment.\n"
        "Complete anonymity - no one knows your real identity!\n\n"
        "🕘 **Group active until 8:15 PM tomorrow**"
    )

    # Create group chat keyboard
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Join Group Chat", callback_data="nwyr:chat")],
        [InlineKeyboardButton("📊 View Results", callback_data="nwyr:results"),
         InlineKeyboardButton("🎯 Comment Now", callback_data="nwyr:comment")]
    ])

    try:
        await q.edit_message_text(txt, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        try:
            await q.message.reply_text(txt, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            pass
    
    # Send a small navigation message to bring focus to bottom of chat
    try:
        nav_msg = await context.bot.send_message(
            uid, 
            "🎯 Scroll down for latest updates!"
        )
        # Auto-delete navigation message after 3 seconds
        async def delete_nav_after_delay():
            await asyncio.sleep(3)
            try:
                await context.bot.delete_message(uid, nav_msg.message_id)
            except Exception:
                pass
        asyncio.create_task(delete_nav_after_delay())
    except Exception:
        pass

# --------- Who voted (Premium tease) ---------
async def on_nwyr_who(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    from registration import has_active_premium

    if not has_active_premium(uid):
        return await q.message.reply_text(
            "💎 Premium Feature\nSee who picked what.\nUpgrade to unlock.",
            parse_mode="Markdown"
        )

    # Get today's voters with safe display names
    today = datetime.date.today()
    a_voters = []
    b_voters = []

    try:
        with _conn() as con, con.cursor() as cur:
            # Get A voters
            cur.execute("""
                SELECT tg_user_id FROM wyr_votes 
                WHERE vote_date=%s AND side='A' 
                ORDER BY created_at DESC LIMIT 10
            """, (today,))
            a_voter_ids = [r[0] for r in cur.fetchall()]

            # Get B voters  
            cur.execute("""
                SELECT tg_user_id FROM wyr_votes 
                WHERE vote_date=%s AND side='B' 
                ORDER BY created_at DESC LIMIT 10
            """, (today,))
            b_voter_ids = [r[0] for r in cur.fetchall()]

        # Get safe display names
        from utils.display import safe_display_name
        a_voters = [safe_display_name(vid) for vid in a_voter_ids]
        b_voters = [safe_display_name(vid) for vid in b_voter_ids]

    except Exception:
        pass

    # Build response
    a_text = ", ".join(a_voters[:5]) if a_voters else "None yet"
    b_text = ", ".join(b_voters[:5]) if b_voters else "None yet"

    if len(a_voters) > 5:
        a_text += f" (+{len(a_voters)-5} more)"
    if len(b_voters) > 5:
        b_text += f" (+{len(b_voters)-5} more)"

    response = (
        "👀 **Who Voted** (Premium)\n\n"
        f"💋 **Option A:** {a_text}\n\n"
        f"🔥 **Option B:** {b_text}\n\n"
        "🔒 Only recent voters shown for privacy"
    )

    try:
        await q.edit_message_text(response, parse_mode="Markdown")
    except Exception:
        await q.message.reply_text(response, parse_mode="Markdown")

# --------- Group Chat Handlers ---------
async def on_nwyr_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show anonymous group chat interface"""
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    today = datetime.date.today()

    # Get anonymous name and messages
    anonymous_name = _get_or_assign_anonymous_name(uid, today)
    messages = _get_group_messages(today, limit=10)

    # Build message display
    chat_text = "🎭 **ANONYMOUS GROUP CHAT**\n\n"

    if messages:
        chat_text += "💬 **Recent Messages:**\n\n"
        for i, msg in enumerate(messages[-10:]):  # Show last 10 messages
            # Convert UTC timestamp to IST before displaying
            utc_time = msg['created_at'].replace(tzinfo=pytz.UTC) if msg['created_at'].tzinfo is None else msg['created_at']
            ist_time = utc_time.astimezone(IST)
            time_str = ist_time.strftime("%H:%M")
            username = msg['anonymous_name']  # This now uses permanent usernames

            # Add reactions display
            reactions = ""
            if msg.get('likes', 0) > 0:
                reactions += f"👍{msg['likes']} "
            if msg.get('hearts', 0) > 0:
                reactions += f"❤️{msg['hearts']} "
            if msg.get('laughs', 0) > 0:
                reactions += f"😂{msg['laughs']} "

            # Add admin tag if user is admin
            admin_tag = ""
            if _is_admin(uid):
                admin_tag = f" [ID:{msg['id']}]"

            chat_text += f"👤 **{username}** ({time_str}){admin_tag}:\n{msg['content']}\n\n"
    else:
        chat_text += "💭 **No messages yet. Be the first to comment!**\n\n"

    chat_text += f"\n👤 **You are:** {anonymous_name}\n"
    chat_text += "🔒 **Complete anonymity guaranteed**\n\n"
    chat_text += "💡 *Tap 'Add Comment' to share your thoughts!*"

    # Create keyboard with simple controls
    keyboard = [
        [InlineKeyboardButton("🎯 Add Comment", callback_data="nwyr:comment")],
        [InlineKeyboardButton("🔄 Refresh Chat", callback_data="nwyr:chat"),
         InlineKeyboardButton("📊 View Results", callback_data="nwyr:results")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="nwyr:leaderboard")]
    ]

    # Add admin button if user is admin and has messages
    if _is_admin(uid) and messages:
        keyboard.append([InlineKeyboardButton("🗑️ Admin: Delete Comment", callback_data="nwyr:admin_mode")])

    kb = InlineKeyboardMarkup(keyboard)

    try:
        await q.edit_message_text(chat_text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await q.message.reply_text(chat_text, reply_markup=kb, parse_mode="Markdown")


async def cmd_delete_wyr_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to delete WYR comments"""
    uid = update.effective_user.id

    # Check if user is admin
    if not _is_admin(uid):
        await update.message.reply_text("❌ Access denied! Admin only command.")
        return

    # Get recent comments to delete
    today = datetime.date.today()
    messages = _get_group_messages(today, limit=10)

    if not messages:
        await update.message.reply_text("❌ No comments found to delete!")
        return

    txt = "🗑️ **ADMIN: DELETE WYR COMMENTS**\n\n"
    txt += "⚠️ *Choose comment to delete:*\n\n"

    keyboard = []
    for msg in messages[-10:]:  # Show last 10 messages
        content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
        username = msg.get('anonymous_name', 'Unknown')

        keyboard.append([InlineKeyboardButton(
            f"🗑️ Delete: {username} - {content}",
            callback_data=f"nwyr:delete:{msg['id']}"
        )])

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="nwyr:cancel_admin")])
    kb = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(txt, reply_markup=kb, parse_mode="Markdown")

async def on_nwyr_delete_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin comment deletion"""
    q = update.callback_query
    await q.answer("Processing deletion...", show_alert=False)

    uid = q.from_user.id
    if not _is_admin(uid):
        await q.answer("Access denied!", show_alert=True)
        return

    # Parse callback: nwyr:delete:{msg_id}
    try:
        _, _, msg_id = q.data.split(':')
        msg_id = int(msg_id)
    except:
        await q.answer("Invalid delete request!", show_alert=True)
        return

    # Delete the comment
    if _delete_comment(msg_id, uid):
        await q.edit_message_text("✅ **Comment deleted successfully!**\n\nThe inappropriate comment has been removed from the group chat.")
    else:
        await q.edit_message_text("❌ **Failed to delete comment!**\n\nThere was an error removing the comment.")

async def on_nwyr_cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel admin action"""
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("❌ **Action cancelled**")

async def on_nwyr_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show voting results (old style)"""
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    today = datetime.date.today()

    # Get voting results
    a_votes, b_votes, total = _counts_today()
    a_pct = int((a_votes / max(1,total)) * 100); b_pct = 100 - a_pct

    # Get user's choice
    user_choice = "Not voted"
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("SELECT side FROM wyr_votes WHERE tg_user_id=%s AND vote_date=%s", (uid, today))
            row = cur.fetchone()
            if row:
                user_choice = "💋 Option A" if row[0] == 'A' else "🔥 Option B"
    except Exception:
        pass

    txt = (
        "📊 **VOTING RESULTS**\n\n"
        f"💋 A: {a_pct}%  [{_bar(a_pct)}]  ({a_votes})\n"
        f"🔥 B: {b_pct}%  [{_bar(b_pct)}]  ({b_votes})\n\n"
        f"✅ **You chose:** {user_choice}\n"
        f"👥 **Total voters:** {total}\n\n"
        "💬 Join the anonymous chat to discuss!"
    )

    # Create keyboard
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Join Group Chat", callback_data="nwyr:chat")],
        [InlineKeyboardButton("🎯 Add Comment", callback_data="nwyr:comment")]
    ])

    try:
        await q.edit_message_text(txt, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await q.message.reply_text(txt, reply_markup=kb, parse_mode="Markdown")

async def on_nwyr_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to add comment"""
    q = update.callback_query
    await q.answer()

    # Use text framework to claim text input
    from handlers.text_framework import claim_or_reject, make_cancel_kb
    ok = await claim_or_reject(update, context, "wyr", "comment", ttl_minutes=3)
    if not ok:
        return

    uid = q.from_user.id
    today = datetime.date.today()
    anonymous_name = _get_or_assign_anonymous_name(uid, today)

    txt = (
        "🎯 **ADD ANONYMOUS COMMENT**\n\n"
        f"👤 **You will post as:** {anonymous_name}\n"
        "🔒 **Your identity stays completely anonymous**\n\n"
        "💭 **What are your thoughts on today's question?**\n"
        "Share your opinion, experience, or reaction!\n\n"
        "📝 **Just type your message and send it.**\n"
    )

    # Store additional data needed for comment processing
    context.user_data['nwyr_vote_date'] = today
    # Set legacy state for relay compatibility
    context.user_data["state"] = "comment:wyr"

    kb = make_cancel_kb()

    try:
        await q.edit_message_text(txt, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await q.message.reply_text(txt, reply_markup=kb, parse_mode="Markdown")

# --------- Comment Input Handler ---------
from handlers.text_framework import requires_state, clear_state, FEATURE_KEY

@requires_state(feature="wyr", mode="comment")
async def handle_comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle comment input from users"""
    # Defensive 2-liner FEATURE_KEY guard:
    af = context.user_data.get(FEATURE_KEY)
    if af and af not in ("wyr",):
        return

    uid = update.effective_user.id
    message_text = update.message.text if update.message else None

    print(f"[nwyr-comment] Handler triggered for user {uid}, message: {message_text}")
    print(f"[nwyr-comment] User data: {context.user_data}")

    if not message_text:
        print(f"[nwyr-comment] No message text received")
        return

    print(f"[nwyr-comment] Processing comment from user {uid}: {message_text[:50]}...")

    # Cancel handling is now done by text framework automatically
    # No need for manual /cancel checking

    # Validate comment
    if len(message_text) > 500:
        await update.message.reply_text("❌ Comment too long! Please keep it under 500 characters.")
        return

    if len(message_text) < 3:
        await update.message.reply_text("❌ Comment too short! Please write at least 3 characters.")
        return

    # Add comment to group chat
    vote_date = context.user_data.get('nwyr_vote_date', datetime.date.today())
    success = _add_group_message(uid, vote_date, message_text, 'comment')

    print(f"[nwyr-comment] Comment addition result: {success}")

    # Clear text framework state and vote date
    clear_state(context)
    context.user_data.pop('nwyr_vote_date', None)
    context.user_data.pop("state", None)  # Clear legacy state marker

    if success:
        anonymous_name = _get_or_assign_anonymous_name(uid, vote_date)
        txt = (
            "✅ **Comment Added Successfully!**\n\n"
            f"👤 **Posted as:** {anonymous_name}\n"
            f"💬 **Your comment:** {message_text}\n\n"
            "🎉 Others can now see and react to your comment!\n"
            "Join the group chat to see responses."
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 View Group Chat", callback_data="nwyr:chat")]
        ])

        await update.message.reply_text(txt, reply_markup=kb, parse_mode="Markdown")
        print(f"[nwyr-comment] Successfully processed comment from user {uid}")
    else:
        await update.message.reply_text("❌ Failed to add comment. Please try again.")
        print(f"[nwyr-comment] Failed to add comment from user {uid}")

# --------- NEW CALLBACK HANDLERS ---------
async def on_nwyr_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show weekly leaderboard"""
    q = update.callback_query
    await q.answer()

    # Get top comments and users
    top_comments = _get_top_comments(5)
    top_users = _get_top_users(5)

    txt = (
        "🏆 **WEEKLY LEADERBOARD**\n"
        "🎯 *Making anonymous chat addictive!*\n\n"
    )

    # Removed "most liked comments" section as requested

    if top_users:
        txt += "🔥 **MOST ACTIVE USERS:**\n"
        for i, user in enumerate(top_users, 1):
            username = user[0]
            comments = user[1] 
            # likes_received = user[2]  # No longer used - removed to prevent NameError
            activity_score = user[3]

            txt += f"{i}. **{username}** (Score: {activity_score})\n"
            txt += f"   💬 {comments} comments\n\n"
    else:
        txt += "🔥 **No active users yet this week!**\n\n"

    txt += "🎭 *Comment and react to climb the leaderboard!*"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Back to Chat", callback_data="nwyr:chat")],
        [InlineKeyboardButton("🔄 Refresh Leaderboard", callback_data="nwyr:leaderboard")]
    ])

    try:
        await q.edit_message_text(txt, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await q.message.reply_text(txt, reply_markup=kb, parse_mode="Markdown")

async def on_nwyr_admin_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin mode for deleting comments"""
    q = update.callback_query
    await q.answer()

    uid = update.effective_user.id
    if not _is_admin(uid):
        await q.answer("❌ Admin access required!", show_alert=True)
        return

    today = datetime.date.today()
    messages = _get_group_messages(today, limit=10)

    txt = "🗑️ **ADMIN DELETE MODE**\n👑 Select comment to delete:\n\n"

    keyboard = []
    for msg in messages[-10:]:  # Last 10 messages
        content = msg['content'][:40] + "..." if len(msg['content']) > 40 else msg['content']
        # Convert UTC timestamp to IST before displaying
        utc_time = msg['created_at'].replace(tzinfo=pytz.UTC) if msg['created_at'].tzinfo is None else msg['created_at']
        ist_time = utc_time.astimezone(IST)
        time_str = ist_time.strftime('%H:%M')

        button_text = f"🗑️ {msg['anonymous_name']} ({time_str}): {content}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"nwyr:delete:{msg['id']}")])

    keyboard.append([InlineKeyboardButton("◀️ Back to Chat", callback_data="nwyr:chat")])
    kb = InlineKeyboardMarkup(keyboard)

    try:
        await q.edit_message_text(txt, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await q.message.reply_text(txt, reply_markup=kb, parse_mode="Markdown")


async def on_nwyr_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add reaction to comment"""
    q = update.callback_query
    await q.answer()

    uid = update.effective_user.id

    # Extract message ID and reaction type from callback data
    # Format: nwyr:react:{message_id}:{reaction_type}
    parts = q.data.split(":")
    message_id = int(parts[2])
    reaction_type = parts[3]  # 'like', 'heart', 'laugh'

    success = _add_reaction(uid, message_id, reaction_type)

    if success:
        reaction_emoji = {"like": "👍", "heart": "❤️", "laugh": "😂"}[reaction_type]
        await q.answer(f"{reaction_emoji} Reaction added!", show_alert=False)
        # Refresh chat to show updated reactions
        context.user_data['callback_data'] = 'nwyr:chat' 
        await on_nwyr_chat(update, context)
    else:
        await q.answer("❌ Couldn't add reaction!", show_alert=True)

def register(app):
    from telegram.ext import MessageHandler, filters

    app.add_handler(CommandHandler("naughtywyr", cmd_naughtywyr), group=-1)
    app.add_handler(CallbackQueryHandler(on_nwyr_vote, pattern=r"^nwyr:vote:(A|B)$"), group=-2)
    app.add_handler(CallbackQueryHandler(on_nwyr_who,  pattern=r"^nwyr:who$"), group=-2)
    app.add_handler(CallbackQueryHandler(on_nwyr_chat, pattern=r"^nwyr:chat$"), group=-2)
    app.add_handler(CallbackQueryHandler(on_nwyr_results, pattern=r"^nwyr:results$"), group=-2)
    app.add_handler(CallbackQueryHandler(on_nwyr_comment, pattern=r"^nwyr:comment$"), group=-2)

    # NEW AMAZING FEATURES
    app.add_handler(CallbackQueryHandler(on_nwyr_leaderboard, pattern=r"^nwyr:leaderboard$"), group=-2)
    app.add_handler(CallbackQueryHandler(on_nwyr_admin_mode, pattern=r"^nwyr:admin_mode$"), group=-2)
    app.add_handler(CallbackQueryHandler(on_nwyr_delete_comment, pattern=r"^nwyr:delete:\d+$"), group=-2)
    app.add_handler(CallbackQueryHandler(on_nwyr_cancel_admin, pattern=r"^nwyr:cancel_admin$"), group=-2)
    app.add_handler(CallbackQueryHandler(on_nwyr_react, pattern=r"^nwyr:react:\d+:(like|heart|laugh)$"), group=-2)

    # Framework-aware: Higher priority to prevent text swallowing
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_comment_input, block=False), group=-3)