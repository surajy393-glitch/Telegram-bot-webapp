# profile.py — profile UI + DB helpers for LuvHive

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

import psycopg2
import psycopg2.extras
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

# ===== Callback IDs (used by handlers/profile_handlers.py) =====
CB_PREFIX = "prof"
CB_PROFILE = "prof"
# REMOVED: CB_GENDER and CB_AGE - no longer used (permanent values)
CB_LANG    = "prof_lang"
CB_RESET   = "prof_reset"
CB_COINS   = f"{CB_PREFIX}:coins"
CB_BIO     = f"{CB_PREFIX}:bio"
CB_PHOTO_SET = f"{CB_PREFIX}:photo_set"
CB_PHOTO_DEL = f"{CB_PREFIX}:photo_del"

# ===== PG connection =====
@contextmanager
def _conn():
    url = os.getenv("DATABASE_URL")
    if url and not (url.startswith("postgres://") or url.startswith("postgresql://")):
        url = None
    if url:
        con = psycopg2.connect(url, cursor_factory=psycopg2.extras.DictCursor)
    else:
        con = psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=int(os.getenv("PGPORT", "5432")),
            dbname=os.getenv("PGDATABASE", "postgres"),
            user=os.getenv("PGUSER", "postgres"),
            password=os.getenv("PGPASSWORD", ""),
            cursor_factory=psycopg2.extras.DictCursor,
        )
    try:
        yield con
    finally:
        con.close()

# ===== Internal helpers =====
def _ensure_user_row(tg_user_id: int) -> Dict[str, Any]:
    """Create a users row with sane defaults if missing; return the row."""
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE tg_user_id=%s", (tg_user_id,))
        row = cur.fetchone()
        if row:
            return dict(row)

        cur.execute(
            """
            INSERT INTO users (
                tg_user_id, gender, age, country, city, language,
                rating_up, rating_down, report_count,
                dialogs_total, dialogs_today,
                messages_sent, messages_recv,
                interests, premium, created_at, search_pref
            )
            VALUES (%s, '', NULL, '', '', NULL,
                    0, 0, 0,
                    0, 0,
                    0, 0,
                    NULL, FALSE, NOW(), 'any')
            RETURNING *;
            """,
            (tg_user_id,),
        )
        con.commit()
        return dict(cur.fetchone())

def _fetch_user(tg_user_id: int) -> Dict[str, Any]:
    with _conn() as con, con.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE tg_user_id=%s", (tg_user_id,))
        row = cur.fetchone()
        return dict(row) if row else _ensure_user_row(tg_user_id)

def _fetch_interests(user_row_id: Optional[int]) -> List[str]:
    """Return list of interest keys for users.id; no ORDER BY id (column may not exist)."""
    if user_row_id is None:
        return []
    with _conn() as con, con.cursor() as cur:
        try:
            cur.execute("SELECT interest_key FROM user_interests WHERE user_id=%s", (user_row_id,))
        except Exception:
            return []
        keys = [r[0] for r in cur.fetchall()]
    return sorted(keys, key=lambda s: s.lower())

# Known interest labels -> pretty label
INTEREST_LABELS = {
    "chatting": "💬 Chatting",
    "relationship": "💞 Relationship",
    "friends": "🌈 Friends",
    "love": "❤️ Love",
    "anime": "⚡ Anime",
    "games": "🎮 Games",
    "chat": "💬 Chatting",
}

LANG_CHOICES = [("English", "English"), ("Hindi", "हिन्दी")]

def _fmt_lang(lang: Optional[str]) -> str:
    if not lang:
        return "—"
    return lang[4:] if lang.startswith("set:") else lang

def _fmt_location(row: Dict[str, Any]) -> str:
    country = (row.get("country") or "").strip()
    city = (row.get("city") or "").strip()
    if country and city:
        return f"{country}, {city}"
    if country:
        return country
    if city:
        return city
    return "—"

def _fmt_gender(g: Optional[str]) -> str:
    if not g:
        return "—"
    g = g.lower()
    if g in ("m", "male"):
        return "Male"
    if g in ("f", "female"):
        return "Female"
    return g.capitalize()

# ===== Public API used by handlers =====
def profile_text(tg_user_id: int, username: Optional[str]) -> str:
    """Build the profile panel text (HTML)."""
    u = _fetch_user(tg_user_id)
    interests_keys = _fetch_interests(u.get("id"))
    if not interests_keys and u.get("interests"):
        interests_keys = [s.strip() for s in (u["interests"] or "").split(",") if s.strip()]
    interests_txt = "— —" if not interests_keys else ", ".join(
        INTEREST_LABELS.get(k.lower(), k) for k in interests_keys
    )

    lines = []
    lines.append("💎 <b>My Profile</b>")
    lines.append(f"🆔 <b>ID</b> — {tg_user_id}")
    lines.append(f"🧑 <b>Gender</b> — {_fmt_gender(u.get('gender'))}")
    lines.append(f"🎂 <b>Age</b> — {u.get('age') if u.get('age') is not None else '—'}")
    lines.append(f"📍 <b>Location</b> — {_fmt_location(u)}")
    lines.append(f"🌐 <b>Language</b> — {_fmt_lang(u.get('language'))}")
    if username:
        lines.append(f"🌐 <b>Telegram</b> — @{username}")
    lines.append(f"🎯 <b>Interests</b> — {interests_txt}")


    lines.append("")
    lines.append("⭐ <b>Dialogs</b>")
    lines.append(f"└ Total: {int(u.get('dialogs_total') or 0)}")
    lines.append(f"└ Today: {int(u.get('dialogs_today') or 0)}")
    lines.append(f"└ Reports: {int(u.get('report_count') or 0)}")
    
    # Add friends count
    import registration as reg
    try:
        friends_count = reg._friends_count(tg_user_id)
        lines.append("")
        lines.append("👥 <b>Friends</b>")
        lines.append(f"└ Total: {friends_count}")
    except Exception:
        pass
    lines.append("")
    lines.append("💬 <b>Messages</b>")
    lines.append(f"└ Sent: {int(u.get('messages_sent') or 0)}")
    lines.append(f"└ Received: {int(u.get('messages_recv') or 0)}")
    lines.append("")
    up = int(u.get('rating_up') or 0)
    down = int(u.get('rating_down') or 0)
    lines.append(f"⭐ {up + down} 👍 {up} 👎 {down}")
    is_v = bool(u.get("is_verified"))
    lines.append(f"✔️ <b>Verified:</b> {'Yes' if is_v else 'No'}")
    is_p = u.get("is_premium", u.get("premium"))

    # Show premium expiry if present
    prem_until = None
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("SELECT premium_until FROM users WHERE tg_user_id=%s", (tg_user_id,))
            row = cur.fetchone()
            prem_until = row[0] if row else None
    except Exception:
        pass

    if is_p and prem_until:
        lines.append(f"✨ <b>Premium:</b> Yes (until {prem_until:%Y-%m-%d})")
    else:
        lines.append(f"✨ <b>Premium:</b> {'Yes' if is_p else 'No'}")
    
    # Add badges display
    import registration as reg
    try:
        # Check and award badges before displaying
        reg.check_and_award_badges(tg_user_id)
        user_badges = reg.get_user_badges(tg_user_id)
        badges_display = reg.format_badges_display(user_badges)
        lines.append("")
        lines.append(f"🏆 <b>Badges:</b> {badges_display}")
        if user_badges:
            lines.append("   " + ", ".join([f"{b['emoji']} {b['name']}" for b in user_badges[:3]]))
            if len(user_badges) > 3:
                lines.append(f"   +{len(user_badges) - 3} more badges")
    except Exception:
        pass
    
    return "\n".join(lines)

def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Change Language", callback_data=CB_LANG)],
        [InlineKeyboardButton("🧹 Reset Ratings for 10⭐", callback_data=CB_RESET)],
        [InlineKeyboardButton("🖼 Set Photo", callback_data=CB_PHOTO_SET)],
        [InlineKeyboardButton("🗑 Remove Photo", callback_data=CB_PHOTO_DEL)],
        [InlineKeyboardButton("💰 Coins", callback_data=CB_COINS)],
    ])

# REMOVED: gender_keyboard() function - gender changes no longer allowed for security

def language_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(label, callback_data=f"{CB_LANG}:{value}")]
            for value, label in LANG_CHOICES]
    return InlineKeyboardMarkup(rows)

# ===== Mutators used by handlers =====
# REMOVED: set_gender() function - gender changes no longer allowed for security
# Gender is set only during registration and cannot be changed later

# REMOVED: set_age() function - age changes no longer allowed for security
# Age is set only during registration and cannot be changed later

def set_language(tg_user_id: int, lang_value: str) -> None:
    if lang_value.startswith("set:"):
        lang_value = lang_value[4:]
    with _conn() as con, con.cursor() as cur:
        cur.execute("UPDATE users SET language=%s WHERE tg_user_id=%s",
                    (lang_value, tg_user_id))
        con.commit()

def reset_ratings_for(tg_user_id: int) -> None:
    """
    Clear received ratings for this Telegram user:
    - Delete rows from chat_ratings where they were the ratee
    - Zero out rating_up / rating_down counters in users
    """
    with _conn() as con, con.cursor() as cur:
        # delete rating rows
        try:
            cur.execute("DELETE FROM chat_ratings WHERE ratee_id=%s", (tg_user_id,))
        except Exception:
            pass
        # zero counters
        cur.execute(
            "UPDATE users SET rating_up=0, rating_down=0 WHERE tg_user_id=%s",
            (tg_user_id,),
        )
        con.commit()

async def view_profile(update, context):
    """View user profile - delegate to posts_handlers"""
    try:
        from handlers.posts_handlers import view_profile as posts_view_profile
        return await posts_view_profile(update, context)
    except Exception:
        # Fallback to simple profile view
        from handlers.profile_handlers import show_profile
        return await show_profile(update, context)

# ===== Static DB initialization =====
# Optional: safe to call on startup; leaves existing tables intact
def init_profile_db() -> None:
    with _conn() as con, con.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            tg_user_id BIGINT UNIQUE NOT NULL,
            gender TEXT,
            age INTEGER,
            country TEXT,
            city TEXT,
            language TEXT,
            rating_up INTEGER DEFAULT 0,
            rating_down INTEGER DEFAULT 0,
            report_count INTEGER DEFAULT 0,
            dialogs_total INTEGER DEFAULT 0,
            dialogs_today INTEGER DEFAULT 0,
            messages_sent INTEGER DEFAULT 0,
            messages_recv INTEGER DEFAULT 0,
            interests TEXT,
            premium BOOLEAN DEFAULT FALSE,
            is_premium BOOLEAN DEFAULT FALSE,
            premium_until TIMESTAMPTZ,
            created_at TIMESTAMP DEFAULT NOW(),
            search_pref TEXT DEFAULT 'any'
        );
        """)
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_gender_change_at TIMESTAMPTZ")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_age_change_at    TIMESTAMPTZ")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_interests (
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            interest_key TEXT NOT NULL
        );
        """)
        con.commit()