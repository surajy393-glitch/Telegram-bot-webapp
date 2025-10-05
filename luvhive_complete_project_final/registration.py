# registration.py
# Fast Postgres-backed registration for LuvHive

import os
import logging
from typing import Optional, List, Set, Tuple
import time
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

import psycopg2
from psycopg2.pool import SimpleConnectionPool
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import ContextTypes

from menu import main_menu_kb  # shared reply keyboard for the app
import chat # imported for in_chat check

DB_URL = os.environ.get("DATABASE_URL")
log = logging.getLogger("luvbot")

# --- SSL-enforced canonical connection pool ---
_POOL: SimpleConnectionPool | None = None

def _dsn_with_ssl(url: str) -> str:
    """Ensure SSL is enforced in connection string"""
    if not url:
        raise RuntimeError("DATABASE_URL missing")
    # add sslmode=require if absent
    if "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url

def _get_pool() -> SimpleConnectionPool:
    """Get or create connection pool with SSL enforcement"""
    global _POOL
    if _POOL is None:
        dsn = _dsn_with_ssl(DB_URL)
        _POOL = SimpleConnectionPool(
            minconn=2, maxconn=15, dsn=dsn,
            keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5,
            connect_timeout=3, application_name="luvhive-bot"
        )
        log.info("✅ SSL-enabled connection pool created")
    return _POOL

# --- tiny retry wrapper for transient DB hiccups ---
def _exec_with_retry(fn, retries: int = 2, delay: float = 0.5):
    for i in range(retries + 1):
        try:
            return fn()
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            log.warning(f"DB retry {i+1}/{retries+1}: {e}")
            if i == retries:
                raise
            time.sleep(delay * (i + 1))

# Removed _PooledConn class - using context manager approach instead

# ---------- Interests ----------
# key, label, emoji, premium_only
INTERESTS: List[Tuple[str, str, str, bool]] = [
    ("chatting",     "Chatting",     "🐵", False),
    ("friends",      "Friends",      "🌈", False),
    ("relationship", "Relationship", "💞", False),
    ("love",         "Love",         "❤️", False),
    ("games",        "Games",        "🎮", False),
    ("anime",        "Anime",        "⚡", False),
    ("intimate",     "Intimate",     "🚫", True),
    ("vsex",         "Virtual Sex",  "😈", True),
    ("exchange",     "Exchange",     "🍓", True),
]
NON_PREMIUM_KEYS = {k for k, _, _, p in INTERESTS if not p}
PREMIUM_KEYS     = {k for k, _, _, p in INTERESTS if p}

# Labels for Settings preview
INTEREST_LABELS = {
    "chatting": "🐵 Chatting",
    "friends": "🌈 Friends",
    "relationship": "💞 Relationship",
    "love": "❤️ Love",
    "games": "🎮 Games",
    "anime": "⚡ Anime",
    "intimate": "🚫 Intimate",
    "vsex": "😈 Virtual Sex",
    "exchange": "🍓 Exchange",
}
def _settings_interests_text(ud: dict) -> str:
    v = ud.get("interests")
    if not v: return "None"
    if isinstance(v, str): return v
    keys = list(v) if isinstance(v, (list, set, tuple)) else []
    if not keys: return "None"
    labels = [INTEREST_LABELS.get(str(k).lower(), str(k).title()) for k in keys]
    return ", ".join(labels)

# ---------- DB helpers ----------
@contextmanager
def _conn():
    """
    Canonical SSL-enforced pooled connection with proper cleanup and validation.
    Usage: with _conn() as con, con.cursor() as cur: ...
    """
    pool = _get_pool()
    conn = None
    max_retries = 3

    for attempt in range(max_retries):
        try:
            conn = pool.getconn()

            # CRITICAL: Validate connection before using
            if conn.closed:
                log.warning(f"🔄 Got closed connection from pool, retrying ({attempt+1}/{max_retries})")
                pool.putconn(conn, close=True)  # Force close the bad connection
                conn = None
                continue

            # Test connection with a simple query
            with conn.cursor() as test_cur:
                test_cur.execute("SELECT 1")
                test_cur.fetchone()

            yield conn
            return  # Success, exit the retry loop

        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            if "SSL connection has been closed" in str(e) or "connection is closed" in str(e):
                log.warning(f"🔄 Stale connection detected, retrying ({attempt+1}/{max_retries}): {e}")
                if conn:
                    try:
                        pool.putconn(conn, close=True)  # Force close the stale connection
                    except:
                        pass
                    conn = None

                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    log.error(f"🚨 DB connection failed after {max_retries} attempts: {e}")
                    raise
            else:
                log.error(f"🚨 DB connection error: {e}")
                raise
        finally:
            if conn and not conn.closed:
                try:
                    # rollback any open txn to avoid 'idle in transaction'
                    try:
                        conn.rollback()
                    except:
                        pass
                    pool.putconn(conn)
                except:
                    try:
                        pool.putconn(conn, close=True)
                    except:
                        pass

def init_db():
    if not DB_URL:
        log.warning("No DATABASE_URL; skipping table creation")
        return
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    tg_user_id BIGINT UNIQUE NOT NULL,
                    gender TEXT,
                    age INTEGER,
                    country TEXT,
                    city TEXT,
                    is_premium BOOLEAN DEFAULT FALSE,
                    premium_until TIMESTAMPTZ,
                    search_pref TEXT DEFAULT 'any',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_interests (
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    interest_key TEXT NOT NULL
                );
            """)
            # keep schemas consistent with profile/admin
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS language TEXT;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN DEFAULT FALSE;")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_until TIMESTAMPTZ;")
            conn.commit()
        log.info("✅ users & user_interests ensured")
    except Exception as e:
        log.error(f"❌ DB table error: {e}")

def is_premium_user(tg_user_id: int) -> bool:
    if not DB_URL: return False
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT COALESCE(is_premium, FALSE) FROM users WHERE tg_user_id=%s", (tg_user_id,))
            row = cur.fetchone()
            return bool(row[0]) if row else False
    except Exception:
        return False

def set_search_pref(tg_user_id: int, pref: str):
    if not DB_URL: return
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute("UPDATE users SET search_pref=%s WHERE tg_user_id=%s", (pref, tg_user_id))
            conn.commit()
    except Exception as e:
        log.error(f"Failed to set search preference: {e}")

def get_search_pref(tg_user_id: int) -> str:
    if not DB_URL: return 'any'
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT COALESCE(search_pref, 'any') FROM users WHERE tg_user_id=%s", (tg_user_id,))
            row = cur.fetchone()
            return row[0] if row else 'any'
    except Exception:
        return 'any'

def set_is_premium(tg_id: int, value: bool) -> None:
    """Upsert premium flag for a user (TRUE/FALSE)."""
    with _conn() as con, con.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (tg_user_id, is_premium)
            VALUES (%s, %s)
            ON CONFLICT (tg_user_id)
            DO UPDATE SET is_premium = EXCLUDED.is_premium;
            """,
            (tg_id, value),
        )
        con.commit()  # ← REQUIRED to persist the change

def has_active_premium(tg_user_id: int) -> bool:
    """True if premium_until in future OR legacy is_premium True."""
    if not DB_URL:
        return False
    def _q():
        with _conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(is_premium, FALSE),
                       COALESCE(premium_until, TIMESTAMPTZ 'epoch')
                FROM users
                WHERE tg_user_id=%s
            """, (tg_user_id,))
            row = cur.fetchone()
            return row
    row = _exec_with_retry(_q)
    if not row:
        return False
    flag, until = row
    return bool(flag) or (until and until > datetime.now(timezone.utc))

def set_premium_until(tg_id: int, dt: datetime) -> None:
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO users (tg_user_id, is_premium, premium_until)
            VALUES (%s, TRUE, %s)
            ON CONFLICT (tg_user_id)
            DO UPDATE SET is_premium=TRUE, premium_until=EXCLUDED.premium_until;
        """, (tg_id, dt))
        con.commit()

def ensure_verification_columns():
    """Add verification columns to users table if they don't exist."""
    with _conn() as con, con.cursor() as cur:
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_status TEXT DEFAULT 'none';")  # none|awaiting|pending|approved|rejected
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_method TEXT;")                  # 'voice'|'selfie'
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_audio_file TEXT;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_photo_file TEXT;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_phrase TEXT;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_at TIMESTAMP;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_src_chat BIGINT;")  # NEW
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verify_src_msg BIGINT;")   # NEW
        con.commit()

def ensure_reports_table():
    """Add reports table for chat reporting system."""
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_reports (
                id BIGSERIAL PRIMARY KEY,
                reporter_tg_id BIGINT NOT NULL,
                reported_tg_id BIGINT NOT NULL,
                in_secret BOOLEAN NOT NULL DEFAULT FALSE,
                text TEXT,
                media_file_id TEXT,
                media_type TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        con.commit()

def ensure_ban_columns():
    """Add ban-related columns to users table."""
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS banned_until TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS banned_reason TEXT,
            ADD COLUMN IF NOT EXISTS banned_by BIGINT
        """)
        con.commit()

def ensure_feature_columns():
    """Add columns and tables for new features."""
    with _conn() as con, con.cursor() as cur:
        # Verified-only toggle
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS match_verified_only BOOLEAN DEFAULT FALSE")
        # Profile incognito toggle
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS incognito BOOLEAN DEFAULT FALSE")
        # Coins system
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS coins INT DEFAULT 0")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_daily TIMESTAMPTZ")
        # Friend list table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS friends (
                user_id BIGINT,
                friend_id BIGINT,
                added_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (user_id, friend_id)
            )
        """)
        # Referrals table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                inviter_id BIGINT,
                invitee_id BIGINT,
                rewarded BOOLEAN DEFAULT FALSE,
                added_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (inviter_id, invitee_id)
            )
        """)
        con.commit()

def ensure_questions_table():
    """Create game questions table for storing custom questions."""
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_questions (
                game TEXT,
                question TEXT,
                added_by BIGINT,
                added_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        con.commit()

def ensure_friend_requests_table():
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS friend_requests (
                requester_id BIGINT NOT NULL,
                target_id    BIGINT NOT NULL,
                created_at   TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (requester_id, target_id)
            )
        """)
        con.commit()

def ensure_blocked_users_table():
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS blocked_users (
                user_id BIGINT,
                blocked_uid BIGINT,
                added_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY(user_id, blocked_uid)
            )
        """)
        con.commit()

def ensure_age_pref_columns():
    with _conn() as con, con.cursor() as cur:
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS min_age_pref INT DEFAULT 18;")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS max_age_pref INT DEFAULT 99;")
        con.commit()

def ensure_forward_column():
    with _conn() as con, con.cursor() as cur:
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS allow_forward BOOLEAN DEFAULT FALSE;")
        con.commit()

def set_age_pref(tg_user_id: int, lo: int, hi: int):
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO users (tg_user_id, min_age_pref, max_age_pref)
            VALUES (%s, %s, %s)
            ON CONFLICT (tg_user_id)
            DO UPDATE SET min_age_pref = EXCLUDED.min_age_pref,
                          max_age_pref = EXCLUDED.max_age_pref
        """, (tg_user_id, lo, hi))
        con.commit()

def get_age_pref(tg_user_id: int) -> tuple[int,int]:
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(min_age_pref,18), COALESCE(max_age_pref,99)
            FROM users WHERE tg_user_id=%s
        """, (tg_user_id,))
        row = cur.fetchone()
    return (int(row[0]), int(row[1])) if row else (18,99)

def set_allow_forward(tg_user_id: int, value: bool):
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO users (tg_user_id, allow_forward)
            VALUES (%s, %s)
            ON CONFLICT (tg_user_id)
            DO UPDATE SET allow_forward = EXCLUDED.allow_forward
        """, (tg_user_id, value))
        con.commit()

def get_allow_forward(tg_user_id: int) -> bool:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT COALESCE(allow_forward, FALSE) FROM users WHERE tg_user_id=%s", (tg_user_id,))
        row = cur.fetchone()
    return bool(row[0]) if row else False

def ensure_secret_crush_table():
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS secret_crush (
                user_id BIGINT,
                target_id BIGINT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY(user_id, target_id)
            )
        """)
        # Create crush leaderboard table for weekly tracking
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crush_leaderboard (
                user_id BIGINT PRIMARY KEY,
                crush_count INTEGER DEFAULT 0,
                week_start DATE DEFAULT CURRENT_DATE,
                last_updated TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        # Create friendship levels table for gamification
        cur.execute("""
            CREATE TABLE IF NOT EXISTS friendship_levels (
                user1_id BIGINT,
                user2_id BIGINT,
                interaction_count INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                last_interaction TIMESTAMPTZ DEFAULT NOW(),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (user1_id, user2_id)
            )
        """)
        # Add DOB column to users table for horoscope feature
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS date_of_birth DATE")
        # Create user badges table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_badges (
                user_id BIGINT,
                badge_id TEXT,
                earned_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (user_id, badge_id)
            )
        """)
        # Add shadow ban column for troll filtering
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS shadow_banned BOOLEAN DEFAULT FALSE")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS shadow_banned_at TIMESTAMPTZ")
        con.commit()

def update_crush_leaderboard(target_user_id: int):
    """Update crush leaderboard when someone receives a secret crush."""
    from datetime import datetime, date, timedelta

    with _conn() as con, con.cursor() as cur:
        # Check if we need weekly reset
        today = date.today()
        monday = today - timedelta(days=today.weekday())  # Get Monday of current week

        # Get or create leaderboard entry
        cur.execute("""
            SELECT crush_count, week_start FROM crush_leaderboard
            WHERE user_id = %s
        """, (target_user_id,))
        row = cur.fetchone()

        if row:
            current_count, week_start = row
            # Check if it's a new week (reset needed)
            if week_start != monday:
                current_count = 0
                week_start = monday
        else:
            current_count = 0
            week_start = monday

        # Update or insert
        cur.execute("""
            INSERT INTO crush_leaderboard (user_id, crush_count, week_start, last_updated)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                crush_count = %s,
                week_start = %s,
                last_updated = NOW()
        """, (target_user_id, current_count + 1, week_start, current_count + 1, week_start))
        con.commit()

def get_crush_leaderboard(limit: int = 3) -> list[tuple[int, int]]:
    """Get top users from crush leaderboard (user_id, count)."""
    from datetime import date, timedelta

    today = date.today()
    monday = today - timedelta(days=today.weekday())  # Get Monday of current week

    with _conn() as con, con.cursor() as cur:
        # Reset any outdated entries first
        cur.execute("""
            UPDATE crush_leaderboard
            SET crush_count = 0, week_start = %s
            WHERE week_start != %s
        """, (monday, monday))
        con.commit()

        # Get top users
        cur.execute("""
            SELECT user_id, crush_count
            FROM crush_leaderboard
            WHERE crush_count > 0 AND week_start = %s
            ORDER BY crush_count DESC, last_updated ASC
            LIMIT %s
        """, (monday, limit))
        return [(int(row[0]), int(row[1])) for row in cur.fetchall()]

def reset_weekly_crush_leaderboard():
    """Reset all crush leaderboard entries for new week."""
    from datetime import date, timedelta

    today = date.today()
    monday = today - timedelta(days=today.weekday())

    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            UPDATE crush_leaderboard
            SET crush_count = 0, week_start = %s, last_updated = NOW()
        """, (monday,))
        con.commit()

def update_friendship_level(user1_id: int, user2_id: int):
    """Update friendship level between two users based on interaction."""
    # Ensure consistent ordering for the friendship pair
    if user1_id > user2_id:
        user1_id, user2_id = user2_id, user1_id

    with _conn() as con, con.cursor() as cur:
        # Get current interaction count
        cur.execute("""
            SELECT interaction_count FROM friendship_levels
            WHERE user1_id = %s AND user2_id = %s
        """, (user1_id, user2_id))
        row = cur.fetchone()

        if row:
            new_count = row[0] + 1
        else:
            new_count = 1

        # Calculate new level based on interaction count
        new_level = calculate_friendship_level(new_count)

        # Update or insert
        cur.execute("""
            INSERT INTO friendship_levels (user1_id, user2_id, interaction_count, level, last_interaction)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (user1_id, user2_id) DO UPDATE SET
                interaction_count = %s,
                level = %s,
                last_interaction = NOW()
        """, (user1_id, user2_id, new_count, new_level, new_count, new_level))
        con.commit()

def get_friendship_level(user1_id: int, user2_id: int) -> tuple[int, int, str]:
    """Get friendship level between two users. Returns (level, count, emoji)."""
    # Ensure consistent ordering
    if user1_id > user2_id:
        user1_id, user2_id = user2_id, user2_id

    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT level, interaction_count FROM friendship_levels
            WHERE user1_id = %s AND user2_id = %s
        """, (user1_id, user2_id))
        row = cur.fetchone()

        if row:
            level, count = row
            emoji = get_level_emoji(level)
            return (level, count, emoji)
        else:
            return (1, 0, "🌱")

def calculate_friendship_level(interaction_count: int) -> int:
    """Calculate friendship level based on interaction count."""
    if interaction_count >= 100:  # Very close friends
        return 3  # 🌳 Tree
    elif interaction_count >= 25:  # Good friends
        return 2  # 🌿 Herb
    else:  # New friends
        return 1  # 🌱 Seedling

def get_level_emoji(level: int) -> str:
    """Get emoji representation for friendship level."""
    level_emojis = {
        1: "🌱",  # Seedling - new friendship
        2: "🌿",  # Herb - growing friendship
        3: "🌳"   # Tree - strong friendship
    }
    return level_emojis.get(level, "🌱")

def get_level_name(level: int) -> str:
    """Get name for friendship level."""
    level_names = {
        1: "New Friends",
        2: "Good Friends",
        3: "Best Friends"
    }
    return level_names.get(level, "New Friends")

def set_date_of_birth(tg_user_id: int, dob: str) -> bool:
    """Set user's date of birth (format: YYYY-MM-DD)."""
    try:
        from datetime import datetime
        # Validate date format
        datetime.strptime(dob, '%Y-%m-%d')

        with _conn() as con, con.cursor() as cur:
            cur.execute("UPDATE users SET date_of_birth = %s WHERE tg_user_id = %s", (dob, tg_user_id))
            con.commit()
            return True
    except Exception:
        return False

def get_date_of_birth(tg_user_id: int) -> str | None:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT date_of_birth FROM users WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        return str(row[0]) if row and row[0] else None

def get_zodiac_sign(month: int, day: int) -> str:
    """Get zodiac sign from month and day."""
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "♈ Aries"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "♉ Taurus"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "♊ Gemini"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "♋ Cancer"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "♌ Leo"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "♍ Virgo"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "♎ Libra"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "♏ Scorpio"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "♐ Sagittarius"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "♑ Capricorn"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "♒ Aquarius"
    else:  # Pisces
        return "♓ Pisces"

def get_daily_horoscope(zodiac_sign: str) -> str:
    """Get daily horoscope for zodiac sign."""
    import random
    from datetime import date

    # Seed random with today's date for consistent daily horoscopes
    today = date.today()
    random.seed(int(today.strftime('%Y%m%d')) + hash(zodiac_sign))

    horoscopes = {
        "♈ Aries": [
            "Today brings opportunities for leadership. Trust your instincts and take charge!",
            "Your energy is high today. Channel it into creative projects for best results.",
            "A new adventure awaits. Don't be afraid to step out of your comfort zone.",
            "Your natural confidence will attract positive attention today.",
            "Focus on your goals - your determination will pay off soon."
        ],
        "♉ Taurus": [
            "Stability and patience will be your strengths today. Slow and steady wins.",
            "Material comforts are highlighted. A small luxury might brighten your day.",
            "Your practical nature helps solve a challenging problem today.",
            "Focus on building lasting relationships rather than quick connections.",
            "Financial opportunities may present themselves. Stay grounded in decisions."
        ],
        "♊ Gemini": [
            "Communication is key today. Your words have more power than usual.",
            "A learning opportunity presents itself. Stay curious and open-minded.",
            "Your adaptability helps you navigate changing circumstances smoothly.",
            "Social connections bring unexpected benefits today.",
            "Variety is the spice of life - embrace different experiences today."
        ],
        "♋ Cancer": [
            "Trust your intuition today - it's especially strong right now.",
            "Family and close relationships take center stage today.",
            "Your nurturing nature brings comfort to someone who needs it.",
            "Home-related activities bring satisfaction and peace today.",
            "Emotional connections deepen. Share your feelings openly."
        ],
        "♌ Leo": [
            "Your natural charisma shines brightly today. Take the spotlight!",
            "Creative projects flourish under today's energy. Express yourself freely.",
            "Generosity and warmth attract good fortune your way.",
            "A leadership opportunity may arise. You're ready for it!",
            "Confidence in your abilities opens new doors today."
        ],
        "♍ Virgo": [
            "Attention to detail pays off in a big way today.",
            "Organization and planning set the foundation for future success.",
            "Your helpful nature earns appreciation from others.",
            "Health and wellness deserve extra attention today.",
            "Practical solutions emerge for long-standing problems."
        ],
        "♎ Libra": [
            "Balance and harmony are achievable in all areas today.",
            "Relationships benefit from your diplomatic touch.",
            "Beauty and aesthetics play an important role today.",
            "Cooperation leads to better outcomes than going solo.",
            "Justice and fairness guide your decisions wisely."
        ],
        "♏ Scorpio": [
            "Deep insights and understanding emerge today.",
            "Your intensity and passion inspire others around you.",
            "Transformation opportunities present themselves. Embrace change.",
            "Secrets or hidden information may come to light.",
            "Trust your instincts about people and situations today."
        ],
        "♐ Sagittarius": [
            "Adventure and exploration call to you today.",
            "Your optimism and enthusiasm are contagious.",
            "Learning and teaching opportunities abound.",
            "International or long-distance connections prove beneficial.",
            "Freedom and independence are important themes today."
        ],
        "♑ Capricorn": [
            "Hard work and discipline bring tangible rewards.",
            "Your responsible nature earns respect and recognition.",
            "Long-term goals come into clearer focus today.",
            "Authority figures may offer valuable guidance.",
            "Structure and organization lead to productivity."
        ],
        "♒ Aquarius": [
            "Innovation and original thinking set you apart today.",
            "Friends and group activities bring unexpected joy.",
            "Humanitarian causes or helping others feels especially rewarding.",
            "Technology or modern solutions solve old problems.",
            "Your unique perspective is valued by others."
        ],
        "♓ Pisces": [
            "Your intuition and empathy guide you perfectly today.",
            "Creative and artistic pursuits flow naturally.",
            "Spiritual or meditative activities bring inner peace.",
            "Compassion for others opens your heart to new connections.",
            "Dreams and imagination hold important messages."
        ]
    }

    return random.choice(horoscopes.get(zodiac_sign, horoscopes["♈ Aries"]))

def get_daily_fun_fact() -> str:
    """Get a random daily fun fact."""
    import random
    from datetime import date

    # Seed with today's date for consistent daily facts
    today = date.today()
    random.seed(int(today.strftime('%Y%m%d')))

    fun_facts = [
        "🧠 Humans share 60% of their DNA with bananas!",
        "🌊 There are more possible games of chess than atoms in the observable universe.",
        "🐙 Octopuses have three hearts and blue blood.",
        "🧡 A group of flamingos is called a 'flamboyance'.",
        "🌙 The Moon is gradually moving away from Earth at about 3.8 cm per year.",
        "🦄 Scotland's national animal is the unicorn.",
        "🍯 Honey never spoils. Archaeologists have found edible honey in ancient Egyptian tombs.",
        "🦋 Butterflies taste with their feet.",
        "🌨️ No two snowflakes are exactly alike.",
        "🧻 The Great Wall of China isn't visible from space with the naked eye.",
        "🐘 Elephants are afraid of bees.",
        "🎨 The human brain uses about 20% of the body's total energy.",
        "🌈 A rainbow can only be seen when the sun is behind you.",
        "🦖 T-Rex lived closer in time to humans than to Stegosaurus.",
        "🌊 Dolphins have names for each other.",
        "🎵 Music can make food taste better.",
        "🔥 Bananas are berries, but strawberries aren't.",
        "🌟 There are more stars in the universe than grains of sand on all Earth's beaches.",
        "🧸 The teddy bear was named after President Theodore Roosevelt.",
        "🌍 Earth is the only planet not named after a god or goddess.",
        "🦈 Sharks have been around longer than trees.",
        "☕ Coffee beans are actually seeds, not beans.",
        "🧠 Your brain generates about 12-25 watts of electricity.",
        "🌸 Cherry blossoms (sakura) were originally white, not pink.",
        "🐧 Penguins can't taste sweet, sour, or umami - only salty and bitter."
    ]

    return random.choice(fun_facts)

# Badge system functions
def get_available_badges() -> dict[str, dict]:
    """Define all available badges and their criteria."""
    return {
        "early_user": {
            "name": "Early User",
            "emoji": "🌟",
            "description": "Joined during the first 1000 users",
            "criteria": "Auto-awarded to early users"
        },
        "top_poster": {
            "name": "Top Poster",
            "emoji": "📝",
            "description": "Made 50+ posts in the community",
            "criteria": "Make 50 posts"
        },
        "helpful": {
            "name": "Helpful",
            "emoji": "🤝",
            "description": "Received 25+ positive ratings",
            "criteria": "Get 25 thumbs up"
        },
        "social_butterfly": {
            "name": "Social Butterfly",
            "emoji": "🦋",
            "description": "Has 20+ friends",
            "criteria": "Make 20 friends"
        },
        "chat_master": {
            "name": "Chat Master",
            "emoji": "💬",
            "description": "Sent 1000+ messages",
            "criteria": "Send 1000 messages"
        },
        "premium_supporter": {
            "name": "Premium Supporter",
            "emoji": "💎",
            "description": "Active premium member",
            "criteria": "Have active premium"
        },
        "verified": {
            "name": "Verified",
            "emoji": "✅",
            "description": "Verified account",
            "criteria": "Complete verification process"
        },
        "crush_magnet": {
            "name": "Crush Magnet",
            "emoji": "💘",
            "description": "Received 10+ secret crushes",
            "criteria": "Get 10 secret crushes"
        }
    }

def award_badge(tg_user_id: int, badge_id: str) -> bool:
    """Award a badge to a user."""
    badges = get_available_badges()
    if badge_id not in badges:
        return False

    with _conn() as con, con.cursor() as cur:
        try:
            cur.execute("""
                INSERT INTO user_badges (user_id, badge_id)
                VALUES (%s, %s) ON CONFLICT DO NOTHING
            """, (tg_user_id, badge_id))
            con.commit()
            return True
        except Exception:
            return False

def get_user_badges(tg_user_id: int) -> list[dict]:
    """Get all badges for a user."""
    badges_data = get_available_badges()

    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT badge_id, earned_at FROM user_badges
            WHERE user_id = %s ORDER BY earned_at ASC
        """, (tg_user_id,))
        rows = cur.fetchall()

        user_badges = []
        for badge_id, earned_at in rows:
            if badge_id in badges_data:
                badge_info = badges_data[badge_id].copy()
                badge_info['badge_id'] = badge_id
                badge_info['earned_at'] = earned_at
                user_badges.append(badge_info)

        return user_badges

def check_and_award_badges(tg_user_id: int):
    """Check user stats and award applicable badges."""
    # Use get_profile instead of _fetch_user
    user_profile = get_profile(tg_user_id)
    if not user_profile or not user_profile.get("id"):
        return

    # Get current user stats from database
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT messages_sent, rating_up, is_verified, id
            FROM users WHERE tg_user_id = %s
        """, (tg_user_id,))
        row = cur.fetchone()
        if not row:
            return

        messages_sent, rating_up, is_verified, user_db_id = row

    friends_count = _friends_count(tg_user_id)

    # Check and award badges based on criteria
    badges_to_award = []

    # Chat Master (1000+ messages)
    if messages_sent and messages_sent >= 1000:
        badges_to_award.append('chat_master')

    # Helpful (25+ positive ratings)
    if rating_up and rating_up >= 25:
        badges_to_award.append('helpful')

    # Social Butterfly (20+ friends)
    if friends_count >= 20:
        badges_to_award.append('social_butterfly')

    # Premium Supporter (active premium)
    if user_profile.get('is_premium'):
        badges_to_award.append('premium_supporter')

    # Verified (if user is verified)
    if is_verified:
        badges_to_award.append('verified')

    # Early User (first 1000 users based on ID)
    if user_db_id and user_db_id <= 1000:
        badges_to_award.append('early_user')

    # Award all applicable badges
    for badge_id in badges_to_award:
        award_badge(tg_user_id, badge_id)

def format_badges_display(badges: list[dict]) -> str:
    """Format badges for display in profile."""
    if not badges:
        return "—"

    badge_emojis = [f"{badge['emoji']}" for badge in badges[:6]]  # Show max 6 badges
    badges_text = " ".join(badge_emojis)

    if len(badges) > 6:
        badges_text += f" (+{len(badges) - 6} more)"

    return badges_text

# Shadow ban functions for troll filtering
def set_shadow_ban(tg_user_id: int, banned: bool = True) -> bool:
    """Set or unset shadow ban status for a user."""
    with _conn() as con, con.cursor() as cur:
        try:
            if banned:
                cur.execute("""
                    UPDATE users SET shadow_banned = TRUE, shadow_banned_at = NOW()
                    WHERE tg_user_id = %s
                """, (tg_user_id,))
            else:
                cur.execute("""
                    UPDATE users SET shadow_banned = FALSE, shadow_banned_at = NULL
                    WHERE tg_user_id = %s
                """, (tg_user_id,))
            con.commit()
            return True
        except Exception:
            return False

def is_shadow_banned(tg_user_id: int) -> bool:
    """Check if a user is shadow banned."""
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT shadow_banned FROM users WHERE tg_user_id = %s", (tg_user_id,))
        row = cur.fetchone()
        return bool(row[0]) if row else False

def get_shadow_ban_info(tg_user_id: int) -> tuple[bool, str | None]:
    """Get shadow ban status and timestamp."""
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT shadow_banned, shadow_banned_at
            FROM users WHERE tg_user_id = %s
        """, (tg_user_id,))
        row = cur.fetchone()
        if row:
            is_banned = bool(row[0])
            banned_at = str(row[1]) if row[1] else None
            return is_banned, banned_at
        return False, None

def ensure_story_tables():
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stories (
              id          BIGSERIAL PRIMARY KEY,
              author_id   BIGINT NOT NULL,
              kind        TEXT NOT NULL,             -- 'text' | 'photo' | 'video'
              text        TEXT,
              media_id    TEXT,                      -- file_id (photo/video)
              created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              expires_at  TIMESTAMPTZ NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS story_views (
              story_id  BIGINT NOT NULL,
              viewer_id BIGINT NOT NULL,
              viewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              PRIMARY KEY(story_id, viewer_id)
            );
        """)
        con.commit()

def ensure_confessions_table():
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS confessions (
                id BIGSERIAL PRIMARY KEY,
                author_id BIGINT NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                delivered BOOLEAN DEFAULT FALSE,
                delivered_to BIGINT,
                delivered_at TIMESTAMPTZ,
                system_seed BOOLEAN DEFAULT FALSE
            );
        """)
        con.commit()

def ensure_leaderboard_columns():
    with _conn() as con, con.cursor() as cur:
        # spin cooldown + counters + games
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS spin_last TIMESTAMPTZ")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS spins INT DEFAULT 0")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS games_played INT DEFAULT 0")
        con.commit()

# ===== PROFILE UPGRADE: bio + photo =====
def ensure_profile_upgrade_columns():
    with _conn() as con, con.cursor() as cur:
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS photo_file_id TEXT")
        con.commit()

def ensure_public_feed_columns():
    with _conn() as con, con.cursor() as cur:
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS feed_username TEXT")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS feed_is_public BOOLEAN DEFAULT TRUE")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS feed_photo TEXT")
        con.commit()

def set_bio(tg_id: int, bio: str):
    with _conn() as con, con.cursor() as cur:
        cur.execute("UPDATE users SET bio=%s WHERE tg_user_id=%s", (bio, tg_id))
        con.commit()

def get_bio(tg_id: int) -> str | None:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT bio FROM users WHERE tg_user_id=%s", (tg_id,))
        row = cur.fetchone()
    return row[0] if row and row[0] else None

def set_photo_file(tg_id: int, file_id: str):
    with _conn() as con, con.cursor() as cur:
        cur.execute("UPDATE users SET photo_file_id=%s WHERE tg_user_id=%s", (file_id, tg_id))
        con.commit()

def get_photo_file(tg_id: int) -> str | None:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT photo_file_id FROM users WHERE tg_user_id=%s", (tg_id,))
        row = cur.fetchone()
    return row[0] if row and row[0] else None

def clear_photo_file(tg_id: int):
    with _conn() as con, con.cursor() as cur:
        cur.execute("UPDATE users SET photo_file_id=NULL WHERE tg_user_id=%s", (tg_id,))
        con.commit()

def add_question(game: str, text: str, uid: int):
    """Add a custom question to the database."""
    with _conn() as con, con.cursor() as cur:
        cur.execute(
            "INSERT INTO game_questions (game, question, added_by) VALUES (%s,%s,%s)",
            (game, text, uid),
        )
        con.commit()

def get_all_questions(game: str) -> list[str]:
    """Get all questions for a specific game from database."""
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT question FROM game_questions WHERE game=%s", (game,))
        rows = cur.fetchall()
    return [r[0] for r in rows] if rows else []

# ============ SOCIAL / COINS / REFERRALS / FRIENDS HELPERS ============

def ensure_social_tables():
    with _conn() as con, con.cursor() as cur:
        # coins + daily
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS coins INT DEFAULT 0")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_daily TIMESTAMPTZ")
        # moderation strikes
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS strikes INT DEFAULT 0")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_strike TIMESTAMPTZ")
        # friends (bidirectional edges)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS friends (
                user_id BIGINT NOT NULL,
                friend_id BIGINT NOT NULL,
                added_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (user_id, friend_id)
            )
        """)
        # referrals
        cur.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                inviter_id BIGINT,
                invitee_id BIGINT,
                rewarded BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (inviter_id, invitee_id)
            )
        """)
        # reports (for /reports_summary if not there)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_reports (
                id BIGSERIAL PRIMARY KEY,
                reporter_tg_id BIGINT NOT NULL,
                reported_tg_id BIGINT NOT NULL,
                in_secret BOOLEAN NOT NULL DEFAULT FALSE,
                text TEXT,
                media_file_id TEXT,
                media_type TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        # blocked users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS blocked_users (
                user_id BIGINT,
                blocked_uid BIGINT,
                added_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY(user_id, blocked_uid)
            )
        """)
        # secret crush table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS secret_crush (
                user_id BIGINT,
                target_id BIGINT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY(user_id, target_id)
            )
        """)
        # Friend messaging tables
        cur.execute("""
        CREATE TABLE IF NOT EXISTS friend_chats (
            id BIGSERIAL PRIMARY KEY,
            a BIGINT,
            b BIGINT,
            opened_at TIMESTAMPTZ DEFAULT NOW(),
            closed_at TIMESTAMPTZ
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS friend_msg_requests (
            id BIGSERIAL PRIMARY KEY,
            sender BIGINT,
            receiver BIGINT,
            text TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            status TEXT DEFAULT 'pending'
        );
        """)
        con.commit()

# ------- Coins / Daily -------
def get_coins(uid: int) -> int:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT coins FROM users WHERE tg_user_id=%s", (uid,))
        row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else 0

def add_coins(uid: int, amount: int) -> int:
    with _conn() as con, con.cursor() as cur:
        cur.execute("UPDATE users SET coins=COALESCE(coins,0)+%s WHERE tg_user_id=%s RETURNING coins",
                    (amount, uid))
        row = cur.fetchone()
        con.commit()
    return int(row[0]) if row else 0

def give_daily(uid: int, reward: int = 10) -> tuple[bool, int, int]:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT coins, last_daily FROM users WHERE tg_user_id=%s", (uid,))
        row = cur.fetchone()
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        coins, last = (0, None) if not row else row
        if last is not None:
            delta = now - last
            if delta < timedelta(hours=24):
                left = int(timedelta(hours=24).total_seconds() - delta.total_seconds())
                return (False, int(coins or 0), left)
        newc = int(coins or 0) + int(reward)
        cur.execute("UPDATE users SET coins=%s, last_daily=%s WHERE tg_user_id=%s",
                    (newc, now, uid))
        con.commit()
    return (True, newc, 0)

# ------- Friends -------
def add_friend(a: int, b: int):
    with _conn() as con, con.cursor() as cur:
        cur.execute("INSERT INTO friends (user_id, friend_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (a,b))
        cur.execute("INSERT INTO friends (user_id, friend_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (b,a))
        con.commit()

def is_friends(a: int, b: int) -> bool:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT 1 FROM friends WHERE user_id=%s AND friend_id=%s", (a,b))
        return cur.fetchone() is not None

def list_friends(uid: int, limit: int = 50) -> list[int]:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT friend_id FROM friends WHERE user_id=%s ORDER BY added_at DESC LIMIT %s",
                    (uid, limit))
        rows = cur.fetchall()
    return [int(r[0]) for r in rows] if rows else []

def get_mutual_friends_count(user1: int, user2: int) -> int:
    """Calculate the number of mutual friends between two users."""
    if user1 == user2:
        return 0

    with _conn() as con, con.cursor() as cur:
        # Find mutual friends using SQL intersection
        cur.execute("""
            SELECT COUNT(*)
            FROM friends f1
            INNER JOIN friends f2 ON f1.friend_id = f2.friend_id
            WHERE f1.user_id = %s AND f2.user_id = %s
        """, (user1, user2))
        result = cur.fetchone()
        return int(result[0]) if result else 0

def get_mutual_friends_list(user1: int, user2: int, limit: int = 50) -> list[int]:
    """Get list of mutual friend IDs between two users."""
    if user1 == user2:
        return []

    with _conn() as con, con.cursor() as cur:
        # Find mutual friends using SQL intersection
        cur.execute("""
            SELECT f1.friend_id
            FROM friends f1
            INNER JOIN friends f2 ON f1.friend_id = f2.friend_id
            WHERE f1.user_id = %s AND f2.user_id = %s
            LIMIT %s
        """, (user1, user2, limit))
        rows = cur.fetchall()
        return [int(r[0]) for r in rows] if rows else []

def _friends_count(uid: int) -> int:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM friends WHERE user_id=%s", (uid,))
        return int(cur.fetchone()[0] or 0)

def create_friend_request(requester: int, target: int) -> bool:
    if requester == target:
        return False
    with _conn() as con, con.cursor() as cur:
        try:
            cur.execute("INSERT INTO friend_requests (requester_id, target_id) VALUES (%s,%s)",
                        (requester, target))
            con.commit()
            return True
        except Exception:
            con.rollback()
            return False

def delete_friend_request(requester: int, target: int):
    with _conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM friend_requests WHERE requester_id=%s AND target_id=%s",
                    (requester, target))
        con.commit()

def has_sent_request(requester: int, target: int) -> bool:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT 1 FROM friend_requests WHERE requester_id=%s AND target_id=%s",
                    (requester, target))
        return cur.fetchone() is not None

def has_incoming_request(target: int, requester: int) -> bool:
    # reverse check – requester ने पहले से target को भेज रखा है?
    return has_sent_request(requester, target)

def remove_friend(a: int, b: int):
    with _conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM friends WHERE user_id=%s AND friend_id=%s", (a,b))
        cur.execute("DELETE FROM friends WHERE user_id=%s AND friend_id=%s", (b,a))
        con.commit()

# ------- Referrals -------
def add_referral(inviter: int, invitee: int):
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO referrals (inviter_id, invitee_id, rewarded)
            VALUES (%s,%s,FALSE) ON CONFLICT DO NOTHING
        """, (inviter, invitee))
        con.commit()

def get_unrewarded_ref(invitee: int):
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT inviter_id FROM referrals WHERE invitee_id=%s AND rewarded=FALSE", (invitee,))
        row = cur.fetchone()
    return int(row[0]) if row else None

def mark_referral_rewarded(inviter: int, invitee: int):
    with _conn() as con, con.cursor() as cur:
        cur.execute("UPDATE referrals SET rewarded=TRUE WHERE inviter_id=%s AND invitee_id=%s", (inviter, invitee))
        con.commit()

# ---- Verified-only flag ----
def set_match_verified_only(tg_id: int, value: bool):
    with _conn() as con, con.cursor() as cur:
        cur.execute("UPDATE users SET match_verified_only=%s WHERE tg_user_id=%s", (value, tg_id))
        con.commit()

def get_match_verified_only(tg_id: int) -> bool:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT COALESCE(match_verified_only, FALSE) FROM users WHERE tg_user_id=%s", (tg_id,))
        row = cur.fetchone()
    return bool(row[0]) if row else False

# ---- Incognito flag ----
def set_incognito(tg_id: int, value: bool):
    with _conn() as con, con.cursor() as cur:
        cur.execute("UPDATE users SET incognito=%s WHERE tg_user_id=%s", (value, tg_id))
        con.commit()

def get_incognito(tg_id: int) -> bool:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT COALESCE(incognito, FALSE) FROM users WHERE tg_user_id=%s", (tg_id,))
        row = cur.fetchone()
    return bool(row[0]) if row else False

def is_blocked(viewer_id: int, author_id: int) -> bool:
    """Check if viewer has blocked the author"""
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT 1 FROM blocked_users WHERE user_id=%s AND blocked_uid=%s", (viewer_id, author_id))
        return cur.fetchone() is not None

def block_user(user_id: int, blocked_uid: int):
    """Block a user"""
    with _conn() as con, con.cursor() as cur:
        cur.execute("INSERT INTO blocked_users(user_id, blocked_uid) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user_id, blocked_uid))
        con.commit()

def unblock_user(user_id: int, blocked_uid: int):
    """Unblock a user"""
    with _conn() as con, con.cursor() as cur:
        cur.execute("DELETE FROM blocked_users WHERE user_id=%s AND blocked_uid=%s", (user_id, blocked_uid))
        con.commit()

def get_feed_notify(tg_id: int) -> bool:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT COALESCE(feed_notify, TRUE) FROM users WHERE tg_user_id=%s", (tg_id,))
        row = cur.fetchone()
    return bool(row[0]) if row else True

def set_feed_notify(tg_id: int, value: bool):
    with _conn() as con, con.cursor() as cur:
        cur.execute("UPDATE users SET feed_notify=%s WHERE tg_user_id=%s", (value, tg_id))
        con.commit()

def set_ban(tg_id: int, until_ts, reason: str, by_admin: int):
    """Ban a user until a specific timestamp."""
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            INSERT INTO users (tg_user_id, banned_until, banned_reason, banned_by)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (tg_user_id)
            DO UPDATE SET banned_until=EXCLUDED.banned_until,
                          banned_reason=EXCLUDED.banned_reason,
                          banned_by=EXCLUDED.banned_by
        """, (tg_id, until_ts, reason, by_admin))
        con.commit()

def clear_ban(tg_id: int):
    with _conn() as con, con.cursor() as cur:
        cur.execute("UPDATE users SET banned_until=NULL, banned_reason=NULL, banned_by=NULL WHERE tg_user_id=%s", (tg_id,))
        con.commit()

def add_strike(uid: int) -> int:
    """Return current strikes after adding; auto-resets if >24h old."""
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT COALESCE(strikes,0), last_strike FROM users WHERE tg_user_id=%s", (uid,))
        row = cur.fetchone()
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        strikes, last = (0, None) if not row else row
        if last is None or (now - last) > timedelta(hours=24):
            strikes = 0  # reset window
        strikes += 1
        cur.execute("UPDATE users SET strikes=%s, last_strike=%s WHERE tg_user_id=%s",
                    (strikes, now, uid))
        con.commit()
    return int(strikes)

def reset_strikes(uid: int):
    with _conn() as con, con.cursor() as cur:
        cur.execute("UPDATE users SET strikes=0, last_strike=NULL WHERE tg_user_id=%s", (uid,))
        con.commit()

SPIN_COOLDOWN = timedelta(hours=12)

def can_spin(uid: int) -> tuple[bool, int]:
    """
    return (available, seconds_left_if_locked)
    """
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT spin_last FROM users WHERE tg_user_id=%s", (uid,))
        row = cur.fetchone()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    last = row[0] if row else None
    if not last:
        return (True, 0)
    delta = now - last
    if delta >= SPIN_COOLDOWN:
        return (True, 0)
    left = int((SPIN_COOLDOWN - delta).total_seconds())
    return (False, left)

def apply_spin(uid: int) -> tuple[int, int]:
    """
    perform a spin and return (reward_coins, new_balance)
    rewards weighted: 0,5,10,20,50,100
    """
    # weights sum arbitrary tuned
    rewards = [0, 5, 10, 20, 50, 100]
    weights = [25, 30, 25, 12, 7, 1]
    import random
    reward = random.choices(rewards, weights=weights, k=1)[0]

    with _conn() as con, con.cursor() as cur:
        # update coins, spin_last, spins++, games_played++
        cur.execute("""
            UPDATE users
            SET coins = COALESCE(coins,0) + %s,
                spin_last = %s,
                spins = COALESCE(spins,0) + 1,
                games_played = COALESCE(games_played,0) + 1
            WHERE tg_user_id=%s
            RETURNING coins
        """, (reward, datetime.utcnow().replace(tzinfo=timezone.utc), uid))
        row = cur.fetchone()
        con.commit()
    bal = int(row[0]) if row and row[0] is not None else 0
    return (reward, bal)

def get_top_coins(limit: int = 10):
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT tg_user_id, COALESCE(coins,0) AS c
            FROM users
            ORDER BY COALESCE(coins,0) DESC, tg_user_id ASC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
    return [(int(r[0]), int(r[1])) for r in rows] if rows else []

def get_top_games(limit: int = 10):
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT tg_user_id, COALESCE(games_played,0) AS g
            FROM users
            ORDER BY COALESCE(games_played,0) DESC, tg_user_id ASC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
    return [(int(r[0]), int(r[1])) for r in rows] if rows else []

def get_top_referrals(limit: int = 10):
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
            SELECT inviter_id, COUNT(*) AS cnt
            FROM referrals
            WHERE rewarded=TRUE
            GROUP BY inviter_id
            ORDER BY cnt DESC, inviter_id ASC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
    return [(int(r[0]), int(r[1])) for r in rows] if rows else []

def transfer_coins(sender: int, receiver: int, amount: int) -> tuple[bool, int, int]:
    """
    Try to transfer amount from sender to receiver.
    Return (ok, new_sender_balance, new_receiver_balance_or_old).
    """
    if amount <= 0 or sender == receiver:
        return (False, get_coins(sender), get_coins(receiver))
    with _conn() as con, con.cursor() as cur:
        # check balance
        cur.execute("SELECT COALESCE(coins,0) FROM users WHERE tg_user_id=%s FOR UPDATE", (sender,))
        row = cur.fetchone()
        bal_s = int(row[0]) if row else 0
        if bal_s < amount:
            return (False, bal_s, get_coins(receiver))
        # deduct & add
        cur.execute("UPDATE users SET coins=COALESCE(coins,0)-%s WHERE tg_user_id=%s", (amount, sender))
        cur.execute("UPDATE users SET coins=COALESCE(coins,0)+%s WHERE tg_user_id=%s RETURNING coins", (amount, receiver))
        rowr = cur.fetchone()
        con.commit()
    return (True, bal_s - amount, int(rowr[0]) if rowr else get_coins(receiver))

def redeem_premium_with_coins(uid: int, need: int = 500, days: int = 3):
    """
    Try to redeem premium for <days> using <need> coins.
    Returns (ok: bool, new_balance: int, new_premium_until: datetime|None).
    All updates are atomic.
    """
    with _conn() as con, con.cursor() as cur:
        # lock row to avoid race
        cur.execute(
            "SELECT COALESCE(coins,0), premium_until FROM users WHERE tg_user_id=%s FOR UPDATE",
            (uid,)
        )
        row = cur.fetchone()
        if not row:
            return (False, 0, None)
        coins, prem_until = int(row[0]), row[1]

        if coins < need:
            return (False, coins, prem_until)

        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        base = prem_until if prem_until and prem_until > now else now
        new_until = base + timedelta(days=days)
        new_balance = coins - need

        cur.execute(
            "UPDATE users SET coins=%s, premium_until=%s, is_premium=TRUE WHERE tg_user_id=%s",
            (new_balance, new_until, uid)
        )
        con.commit()
    return (True, new_balance, new_until)

def get_ban_info(tg_id: int):
    """Get ban information for a user: (until, reason, by_admin)"""
    sql = "SELECT banned_until, banned_reason, banned_by FROM users WHERE tg_user_id=%s"
    # First try
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute(sql, (tg_id,))
            row = cur.fetchone()
        return row if row else (None, None, None)
    except psycopg2.OperationalError:
        # Retry once on connection error
        try:
            with _conn() as con, con.cursor() as cur:
                cur.execute(sql, (tg_id,))
                row = cur.fetchone()
            return row if row else (None, None, None)
        except Exception:
            return (None, None, None)
    except Exception:
        return (None, None, None)

def is_banned(tg_id: int) -> bool:
    """Check if user is currently banned."""
    try:
        until, _, _ = get_ban_info(tg_id)
        if not until:
            return False
        # lifetime or future - handle timezone aware comparison
        try:
            now = datetime.utcnow().replace(tzinfo=timezone.utc)
            return until > now
        except Exception:
            # Fallback for naive datetime comparison
            return until > datetime.utcnow()
    except Exception:
        # On any error, assume not banned to prevent blocking legitimate users
        return False

# read profile + interests
def is_registered(tg_user_id: int) -> bool:
    """Check if user has completed registration (has gender, age, and interests)."""
    try:
        profile = get_profile(tg_user_id)
        return bool(profile.get("gender") and profile.get("age") and profile.get("interests"))
    except Exception:
        return False

def get_profile(tg_user_id: int) -> dict:
    def _query():
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, gender, age, country, city, is_premium, "
                "       COALESCE(is_verified, FALSE), COALESCE(verify_status, 'none'), "
                "       COALESCE(feed_username, '') "
                "  FROM users WHERE tg_user_id=%s;",
                (tg_user_id,)
            )
            row = cur.fetchone()
            if not row:
                return {"id": None, "gender": None, "age": None, "country": None, "city": None,
                        "is_premium": False, "is_verified": False, "verify_status": "none", "interests": set()}
            user_id, gender, age, country, city, is_premium, is_verified, verify_status, feed_username = row
            cur.execute("SELECT interest_key FROM user_interests WHERE user_id=%s;", (user_id,))
            interests = {r[0] for r in cur.fetchall()}
            return {"id": user_id, "gender": gender, "age": age, "country": country, "city": city,
                    "is_premium": bool(is_premium), "is_verified": bool(is_verified),
                    "verify_status": str(verify_status or "none"), "interests": interests,
                    "username": (feed_username or None)}

    try:
        return _query()
    except psycopg2.OperationalError:
        # stale socket → reconnect once
        return _query()

# single-commit save
def persist_registration(tg_user_id: int, reg_data: dict, selected: Set[str]):
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO users (tg_user_id, gender, age, country, city)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (tg_user_id)
            DO UPDATE SET gender=EXCLUDED.gender, age=EXCLUDED.age,
                          country=EXCLUDED.country, city=EXCLUDED.city
            RETURNING id;
        """, (
            tg_user_id,
            reg_data.get("gender"),
            reg_data.get("age"),
            reg_data.get("country"),
            reg_data.get("city"),
        ))
        user_id = cur.fetchone()[0]
        cur.execute("DELETE FROM user_interests WHERE user_id=%s;", (user_id,))
        for key in selected:
            cur.execute("INSERT INTO user_interests (user_id, interest_key) VALUES (%s, %s);", (user_id, key))
        conn.commit()

# ---------- Registration flow ----------
#   reg_state: "GENDER"|"AGE"|"COUNTRY"|"CITY"|"INTERESTS"
#   reg: {"gender","age","country","city"}
#   sel_interests: set([...])
#   premium: bool

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    p = get_profile(uid)  # prefill
    context.user_data["premium"] = bool(p["is_premium"])
    context.user_data["sel_interests"] = set(p["interests"]) or set()
    context.user_data["reg_state"] = "GENDER"
    context.user_data["reg"] = {"gender": None, "age": None, "country": None, "city": None}

    # 1) hide the persistent Menu keyboard so registration isn't interrupted
    await update.message.reply_text("…", reply_markup=ReplyKeyboardRemove())

    log.info(f"{uid} REG:start")
    # 2) ask gender with inline buttons and permanent warning
    await update.message.reply_text(
        "👋 Let's set up your profile.\n\n"
        "🔒 **IMPORTANT NOTICE:**\n"
        "Gender selection is **PERMANENT** and cannot be changed later.\n"
        "This policy ensures security and matching accuracy.\n"
        "Please choose carefully.\n\n"
        "What's your **gender**?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("I'm Male",   callback_data="gender_male"),
             InlineKeyboardButton("I'm Female", callback_data="gender_female")]
        ]),
    )

async def open_interests_editor_from_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    p = get_profile(uid)
    context.user_data["premium"] = bool(p.get("is_premium", False))
    context.user_data["sel_interests"] = set(p.get("interests", set()))
    context.user_data["reg_state"] = "INTERESTS"
    context.user_data["edit_mode"] = "settings"
    context.user_data["_interests_from_settings"] = True
    await _show_interest_selector(update, context)

def _selected_text(keys: Set[str]) -> str:
    if not keys: return "Selected: (none)"
    labels = []
    for k, name, emoji, _ in INTERESTS:
        if k in keys:
            labels.append(f"{emoji} {name}")
    return "Selected: " + ", ".join(labels)

def _interest_kb(selected: Set[str], premium_user: bool, include_back: bool = True) -> InlineKeyboardMarkup:
    rows, row = [], []
    for k, name, emoji, is_premium in INTERESTS:
        checked = "✅ " if k in selected else ""
        label = f"{checked}{emoji} {name}"
        if is_premium and not premium_user:
            label += " ⭐"
        row.append(InlineKeyboardButton(label, callback_data=f"int:{k}"))
        if len(row) == 3:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([
        InlineKeyboardButton("✅ Select All", callback_data="act:all"),
        InlineKeyboardButton("❌ Remove All", callback_data="act:none"),
    ])
    rows.append([InlineKeyboardButton("💾 Save Changes", callback_data="save")])
    # Don't show back button when editing from settings
    return InlineKeyboardMarkup(rows)

async def _show_interest_selector(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    uid = update_or_query.effective_user.id
    selected = set(context.user_data.get("sel_interests", set()))
    premium_user = bool(context.user_data.get("premium", False))
    # Never show back button when called from settings
    include_back = False if context.user_data.get("_interests_from_settings", False) else True
    text = "⭐ *Select your interests* (toggle & Save):\n\n" + _selected_text(selected)

    if hasattr(update_or_query, "message") and update_or_query.message:
        await update_or_query.message.reply_text(text, reply_markup=_interest_kb(selected, premium_user, include_back))
    else:
        q = update_or_query.callback_query
        await q.edit_message_text(text, reply_markup=_interest_kb(selected, premium_user, include_back))

# ---------- callbacks ----------
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.callback_query:
        return False
    q = update.callback_query
    data = q.data or ""
    state = context.user_data.get("reg_state")
    uid = q.from_user.id

    # GENDER -> AGE
    if data.startswith("gender_") and state == "GENDER":
        g = "male" if data == "gender_male" else "female"
        context.user_data["reg"]["gender"] = g
        context.user_data["reg_state"] = "AGE"
        await q.answer()
        await q.edit_message_text(
            "✅ Gender saved.\n\n"
            "🔒 **IMPORTANT NOTICE:**\n"
            "Age is **PERMANENT** and cannot be modified after registration.\n"
            "For accurate matching and security, please enter your correct age.\n"
            "This cannot be changed later.\n\n"
            "How old are you? (Enter a number)"
        )
        log.info(f"{uid} REG:gender={g}")
        return True

    # INTERESTS screen (toggle / actions / save / back)
    if state == "INTERESTS" and data.startswith(("int:", "act:", "save", "back")):
        selected: Set[str] = set(context.user_data.get("sel_interests", set()))
        premium_user = bool(context.user_data.get("premium", False))
        include_back = not context.user_data.get("_interests_from_settings", False)

        if data.startswith("int:"):
            from utils.cb import cb_match
            try:
                m = cb_match(data, r"^int:(?P<key>[a-z_]+)$")
                key = m["key"]
            except:
                return True
            if key in PREMIUM_KEYS and not premium_user:
                await q.answer("⚡⭐ To use this feature you must have a premium subscription.", show_alert=True)
                log.info(f"{uid} REG:intent-premium-block key={key}")
                return True
            await q.answer()
            if key in selected: selected.remove(key)
            else: selected.add(key)
            context.user_data["sel_interests"] = selected
            txt = "⭐ Select your interests (toggle & Save):\n\n" + _selected_text(selected)
            await q.edit_message_text(txt, reply_markup=_interest_kb(selected, premium_user, include_back))
            log.info(f"{uid} REG:interest {key}")
            return True

        if data == "act:all":
            await q.answer()
            context.user_data["sel_interests"] = (
                {k for k,*_ in INTERESTS} if premium_user else set(NON_PREMIUM_KEYS)
            )
            sel = context.user_data["sel_interests"]
            txt = "⭐ Select your interests (toggle & Save):\n\n" + _selected_text(sel)
            await q.edit_message_text(txt, reply_markup=_interest_kb(selected, premium_user, include_back))
            return True

        if data == "act:none":
            await q.answer()
            context.user_data["sel_interests"] = set()
            sel = context.user_data["sel_interests"]
            txt = "⭐ Select your interests (toggle & Save):\n\n" + _selected_text(sel)
            await q.edit_message_text(txt, reply_markup=_interest_kb(sel, premium_user, include_back))
            return True

        if data == "save":
            await q.answer()
            keys = set(context.user_data.get("sel_interests", set()))
            if not premium_user:
                keys = {k for k in keys if k in NON_PREMIUM_KEYS}

            if context.user_data.get("edit_mode") == "settings":
                with _conn() as conn, conn.cursor() as cur:
                    cur.execute("SELECT id FROM users WHERE tg_user_id=%s", (uid,))
                    row = cur.fetchone()
                    if row:
                        user_id = row[0]
                        cur.execute("DELETE FROM user_interests WHERE user_id=%s;", (user_id,))
                        for key in keys:
                            cur.execute("INSERT INTO user_interests (user_id, interest_key) VALUES (%s, %s);", (user_id, key))
                        conn.commit()

                for k in ("reg_state","sel_interests","edit_mode","_interests_from_settings"):
                    context.user_data.pop(k, None)
                await q.edit_message_text("✅ Interests updated.")
                from handlers.settings_handlers import show_settings
                return await show_settings(update, context)

            # normal registration completion
            reg_data = context.user_data.get("reg", {})
            persist_registration(uid, reg_data, keys)
            context.user_data["registered"] = True
            await q.edit_message_text("Registration completed 🎉\nWelcome To LuvHive 💞")
            # show Menu only now
            await q.message.reply_text("What would you like to do next?", reply_markup=main_menu_kb())
            log.info(
                f"{uid} REG:completed gender={reg_data.get('gender')} age={reg_data.get('age')} "
                f"country={reg_data.get('country')} city={reg_data.get('city')} "
                f"interests={sorted(keys)} premium={premium_user}"
            )
            for k in ("reg_state","sel_interests","reg","_interests_from_settings"):
                context.user_data.pop(k, None)
            return True

        if data == "back":
            await q.answer()
            if context.user_data.get("edit_mode") == "settings":
                for k in ("reg_state","sel_interests","edit_mode","_interests_from_settings"):
                    context.user_data.pop(k, None)
                from handlers.settings_handlers import show_settings
                return await show_settings(update, context)
            else:
                await q.edit_message_text("You can adjust interests anytime from your profile.")
                await q.message.reply_text("What would you like to do next?", reply_markup=main_menu_kb())
                for k in ("reg_state","sel_interests","reg","_interests_from_settings"):
                    context.user_data.pop(k, None)
                return True

    return False

# ---------- text answers ----------
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages during registration or show main menu."""
    from handlers.text_framework import FEATURE_KEY
    af = context.user_data.get(FEATURE_KEY)
    if af and af not in ("registration",):
        return  # kisi aur feature ne text claim kiya hua hai

    # No need for _ban_gate here as it is handled in main.py's dispatcher
    # if await _ban_gate(update, context):
    #     return

    # Skip if this is a command - let CommandHandlers handle it
    if update.message and update.message.text and update.message.text.startswith('/'):
        return

    uid = update.effective_user.id

    # If user is in chat, let chat handlers deal with it
    if chat.in_chat(uid):
        return

    # Check if user is in poll creation flow - let poll handlers handle it
    poll_state = context.user_data.get("poll_state", "")
    if poll_state and str(poll_state).startswith("poll:"):
        return

    # If not registered, handle registration flow
    if not is_registered(uid):
        await handle_registration_text(update, context)
        return

    # Already registered - do NOT auto-send menu here
    # Just ignore text so real handlers (Friends/Settings/Profile etc.) can run.
    return

async def handle_registration_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Registration flow (no extra 'saved' messages):
    GENDER -> AGE -> COUNTRY -> CITY -> INTERESTS
    """
    txt = (update.message.text or "").strip()
    state = context.user_data.get("reg_state")

    if not state:
        return await start_registration(update, context)

    data = context.user_data.setdefault(
        "reg",
        {"gender": None, "age": None, "country": None, "city": None},
    )

    # ---- GENDER ----
    if state == "GENDER":
        low = txt.lower()
        if low in ("m", "male", "boy", "man", "i am male", "i'm male"):
            data["gender"] = "male"
        elif low in ("f", "female", "girl", "woman", "i am female", "i'm female"):
            data["gender"] = "female"
        else:
            return await update.message.reply_text(
                "Please select gender using buttons or type Male/Female."
            )
        context.user_data["reg_state"] = "AGE"
        return await update.message.reply_text(
            "✅ Gender saved.\n\nHow old are you? (Enter a number)"
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
        # ❌ No 'Age saved' line here
        return await update.message.reply_text("Great! What's your **country**?")

    # ---- COUNTRY ----
    if state == "COUNTRY":
        if len(txt) < 2:
            return await update.message.reply_text("Please enter a valid country.")
        data["country"] = txt.title()

        context.user_data["reg_state"] = "CITY"
        # ❌ No 'Country saved' line here
        return await update.message.reply_text("And your **city**?")

    # ---- CITY ----
    if state == "CITY":
        if len(txt) < 2:
            return await update.message.reply_text("Please enter a valid city.")
        data["city"] = txt.title()

        # ❌ No 'City saved' line here — directly open Interests
        context.user_data["reg_state"] = "INTERESTS"
        # Agar tumhare project me interests ke waqt extra user_data fields chahiye to yahan set kar lo:
        context.user_data["sel_interests"] = set()
        return await _show_interest_selector(update, context)  # <-- same helper you already had

    # ---- INTERESTS ----
    # Text is ignored while selecting interests (buttons handle it)
    if state == "INTERESTS":
        return

    # Fallback
    return await start_registration(update, context)

# Dummy function for _ban_gate as it's not provided in the context
async def _ban_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This function would normally check if the user is banned
    # For now, we'll assume no one is banned
    return False