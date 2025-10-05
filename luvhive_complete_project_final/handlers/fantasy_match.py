# handlers/fantasy_match.py
import os
import logging, re
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ParseMode
import registration as reg
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import Optional, List, Dict, Tuple, Any, Iterable, Literal
# Unified imports from fantasy_common with fallback for legacy analyzers
try:
    from handlers.fantasy_common import (
        db_exec, _exec, _exec_legacy,         # _exec aliases to db_exec
        get_message, reply_any, edit_or_send, # safe Telegram wrappers
        effective_uid, get_display_name, _get_display_name
    )
except Exception:
    # Fallback: still works even if _exec isn't exported by name
    from handlers.fantasy_common import (
        db_exec, get_message, reply_any, edit_or_send,
        effective_uid, get_display_name, _get_display_name
    )
    _exec = db_exec
    _exec_legacy = db_exec

# Compatibility shim for fantasy_chat imports
Fetch = Literal["none", "one", "all", "val"]

# Back-compat shims (so legacy code that imports _exec/_exec_legacy keeps working)
# _exec = db_exec # This line is removed as _exec is now imported from fantasy_common
# _exec_legacy = db_exec # This line is removed as _exec_legacy is now imported from fantasy_common

log = logging.getLogger("fantasy")

# Using unified db_exec from fantasy_common instead

# Import admin IDs for toggle command
try:
    from admin import ADMIN_IDS
except ImportError:
    ADMIN_IDS = []

# Silent mode toggle system
FANTASY_NOTIF_MODE_KEY = "fantasy_notif_mode"  # "silent" | "dm"
DEFAULT_FANTASY_NOTIF_MODE = "silent"          # <- Keep silent by default

def _get_notif_mode(context) -> str:
    try:
        return (context.application.bot_data.get(FANTASY_NOTIF_MODE_KEY) or DEFAULT_FANTASY_NOTIF_MODE).lower()
    except Exception:
        return DEFAULT_FANTASY_NOTIF_MODE

def set_fantasy_notif_mode(context, mode: str):
    if mode in ("silent","dm"):
        context.application.bot_data[FANTASY_NOTIF_MODE_KEY] = mode

def _fmt_mins_left(exp) -> str:
    """CRITICAL FIX: Timezone-aware datetime handling to prevent crashes"""
    try:
        from datetime import timezone
        now = datetime.now(timezone.utc)

        # Handle timezone-aware PostgreSQL TIMESTAMPTZ
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        else:
            exp = exp.astimezone(timezone.utc)

        left = int((exp - now).total_seconds()/60)
        return f"{max(0,left)} min"
    except Exception:
        return "soon"

# Using unified db_exec from fantasy_common instead

# ---------- ARRAY LITERAL FOR TEXT[] ----------
def _arr(val):
    if not val:
        return "{}"
    cleaned = [re.sub(r"[{}\"]", "", str(x)) for x in val]
    return "{" + ",".join(cleaned) + "}"

# ---------- GENDER NORMALIZATION ----------
def normalize_gender(g):
    g = str(g or "").strip().lower()
    if g in ("m","male","boy","man"): return "m"
    if g in ("f","female","girl","woman"): return "f"
    return None  # Don't default to any gender

def _is_m(g): return normalize_gender(g) == "m"
def _is_f(g): return normalize_gender(g) == "f"

# ---------- FANTASY KEY ----------
def _make_fantasy_key(vibe: str, shared_kw: list) -> str:
    vibe = (vibe or "").strip().lower()
    norm = sorted({ (k or "").strip().lower() for k in (shared_kw or []) if k })
    return f"{vibe}:{'-'.join(norm)}"

# ---------- ENSURE TABLES ----------
def ensure_fantasy_tables():
    db_exec("""
      CREATE TABLE IF NOT EXISTS fantasy_submissions (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        gender  TEXT NOT NULL,
        fantasy_text TEXT NOT NULL,
        vibe    TEXT NOT NULL,
        keywords TEXT[] NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        active  BOOLEAN DEFAULT TRUE
      )
    """)
    db_exec("""
      CREATE TABLE IF NOT EXISTS fantasy_matches (
        id BIGSERIAL PRIMARY KEY,
        boy_id  BIGINT NOT NULL,
        girl_id BIGINT NOT NULL,
        fantasy_key TEXT NOT NULL,
        vibe    TEXT NOT NULL,
        shared_keywords TEXT[] NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        expires_at TIMESTAMPTZ NOT NULL,
        status  TEXT DEFAULT 'pending'
      )
    """)
    db_exec("""
      CREATE TABLE IF NOT EXISTS fantasy_match_notifs (
        id BIGSERIAL PRIMARY KEY,
        match_id BIGINT NOT NULL,
        user_id  BIGINT NOT NULL,
        sent_at  TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(match_id, user_id)
      )
    """)
    # Add missing columns to fantasy_matches
    db_exec("""
      ALTER TABLE fantasy_matches 
      ADD COLUMN IF NOT EXISTS boy_ready BOOLEAN DEFAULT FALSE,
      ADD COLUMN IF NOT EXISTS girl_ready BOOLEAN DEFAULT FALSE,
      ADD COLUMN IF NOT EXISTS boy_is_premium BOOLEAN DEFAULT FALSE,
      ADD COLUMN IF NOT EXISTS connected_at TIMESTAMPTZ,
      ADD COLUMN IF NOT EXISTS chat_id TEXT
    """)
    log.info("[fantasy] ensured tables")

# ---------- IDEMPOTENT SENDER ----------
async def _send_once(context: ContextTypes.DEFAULT_TYPE, match_id: int, user_id: int,
                     text: str, kb: Optional[InlineKeyboardMarkup] = None):
    """Send notification only once per match per user - BULLETPROOF"""
    try:
        # Check if already sent (bulletproof with proper connection handling)
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 1 FROM fantasy_match_notifs 
                WHERE match_id = %s AND user_id = %s 
                LIMIT 1
            """, (match_id, user_id))

            if cur.fetchone():
                log.debug(f"[fantasy] ✅ Already sent notification for match {match_id} to user {user_id}")
                return

            # Send message
            await context.bot.send_message(user_id, text, reply_markup=kb, parse_mode="Markdown")

            # Record that we sent it (bulletproof)
            cur.execute("""
                INSERT INTO fantasy_match_notifs(match_id, user_id, sent_at) 
                VALUES (%s, %s, NOW())
                ON CONFLICT (match_id, user_id) DO NOTHING
            """, (match_id, user_id))
            conn.commit()

            log.info(f"[fantasy] 🔥 Sent notification for match {match_id} to user {user_id}")

    except Exception as e:
        log.error(f"[fantasy] send_once error: {e}")

# ---------- DM BOTH SIDES ----------
async def _dm_pair_boy_and_girl(context: ContextTypes.DEFAULT_TYPE, match_id: int,
                                boy_id: int, girl_id: int,
                                vibe: str, shared_kw: list, expires_at: datetime):
    kw_str = ", ".join(shared_kw) if shared_kw else ""
    # CRITICAL FIX: Timezone-aware datetime handling
    from datetime import timezone
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = expires_at.astimezone(timezone.utc)
    mins   = max(0, int((expires_at - now).total_seconds() / 60))
    ttl    = f"{mins} minutes" if mins > 0 else "soon"

    # Check if both users are premium for instant chat
    boy_is_premium = safe_has_premium(boy_id)
    girl_is_premium = safe_has_premium(girl_id)

    # Update match with premium status
    _exec("""
        UPDATE fantasy_matches 
        SET boy_is_premium = %s 
        WHERE id = %s
    """, (boy_is_premium, match_id))

    if boy_is_premium and girl_is_premium:
        # Both premium - instant chat messaging
        txt_g = (
          "🔥💎 *PREMIUM FANTASY MATCH!*\n"
          "Both of you are premium with a similar fantasy!\n\n"
          f"*Match:* {vibe.title()} — _{kw_str}_\n"
          f"Window: {ttl}\n\n"
          "✨ *Ready for instant chat* when both sides confirm!"
        )
        kb_g = InlineKeyboardMarkup([
          [InlineKeyboardButton("💬 I'm Ready", callback_data=f"fant:girl_ready:{match_id}")],
          [InlineKeyboardButton("⏳ Maybe Later", callback_data=f"fant:girl_later:{match_id}")]
        ])
        await _send_once(context, match_id, girl_id, txt_g, kb_g)

        txt_b = (
          "🔥💎 *PREMIUM FANTASY MATCH!*\n"
          "Both of you are premium with a similar fantasy!\n\n"
          f"*Match:* {vibe.title()} — _{kw_str}_\n"
          f"Window: {ttl}\n\n"
          "✨ *Start chatting instantly* - both premium users!"
        )
        kb_b = InlineKeyboardMarkup([
          [InlineKeyboardButton("💬 Start Chat Now", callback_data=f"fant:connect:{match_id}")],
          [InlineKeyboardButton("⏳ Maybe Later", callback_data=f"fant:boy_later:{match_id}")]
        ])
        await _send_once(context, match_id, boy_id, txt_b, kb_b)

    else:
        # Standard flow - girl neutral, boy premium gate
        txt_g = (
          "🔥 *Your Fantasy Match is Ready!*\n"
          "Someone submitted a *similar fantasy* as yours.\n\n"
          f"*Match:* {vibe.title()} — _{kw_str}_\n"
          f"Window: {ttl}\n\n"
          "We'll connect you both once the other side is ready to chat."
        )
        kb_g = InlineKeyboardMarkup([
          [InlineKeyboardButton("💬 I'm Ready", callback_data=f"fant:girl_ready:{match_id}")],
          [InlineKeyboardButton("⏳ Maybe Later", callback_data=f"fant:girl_later:{match_id}")]
        ])
        await _send_once(context, match_id, girl_id, txt_g, kb_g)

        # Boy (premium gate)
        if boy_is_premium:
            txt_b = (
              "🔥 *Your Fantasy Match is Ready!*\n"
              "Both of you submitted a *similar fantasy*.\n\n"
              f"*Match:* {vibe.title()} — _{kw_str}_\n"
              f"Window: {ttl}\n\n"
              "Do you want to connect anonymously *now*?"
            )
            kb_b = InlineKeyboardMarkup([
              [InlineKeyboardButton("💬 Start Chat", callback_data=f"fant:connect:{match_id}")],
              [InlineKeyboardButton("⏳ Maybe Later", callback_data=f"fant:boy_later:{match_id}")]
            ])
            await _send_once(context, match_id, boy_id, txt_b, kb_b)
        else:
            txt_b = (
              "🔥 *YOUR FANTASY MATCH IS HERE!*\n"
              "🎯 A girl submitted the *EXACT same fantasy* as you!\n\n"
              f"*Fantasy:* {vibe.title()} — _{kw_str}_\n"
              f"⏰ Time left: {ttl}\n\n"
              "💭 *She's waiting for someone bold enough to make it real...*\n"
              "🔓 *She can't see you until you unlock chat*\n"
              "⚡ *Anonymous. Private. Your fantasy brought to life.*\n\n"
              "💎 **PREMIUM UNLOCKS:**\n"
              "✅ Instant chat access (no waiting)\n"
              "✅ Photo & video sharing during chat\n"
              "✅ Voice messages for intimate connections\n"
              "✅ Document sharing (any file type)\n"
              "✅ Extended fantasy sessions (4 hours vs 2)\n"
              "✅ Priority matching with hottest fantasies\n\n"
              "🚨 *Don't let her slip away!*"
            )
            kb_b = InlineKeyboardMarkup([
              [InlineKeyboardButton("💎 Upgrade Now", callback_data="premium:open")],
              [InlineKeyboardButton("⏳ Maybe Later", callback_data=f"fant:boy_later:{match_id}")]
            ])
            await _send_once(context, match_id, boy_id, txt_b, kb_b)

            jq = getattr(context, "job_queue", None)
            if jq:
                jq.run_once(_remind_boy_90m, when=90*60,
                            data={"match_id": match_id, "boy_id": boy_id})
                jq.run_once(_expire_pair_120m, when=120*60,
                            data={"match_id": match_id, "boy_id": boy_id, "girl_id": girl_id})

# ---------- REMINDER / EXPIRY ----------
async def _remind_boy_90m(context: ContextTypes.DEFAULT_TYPE):
    try:
        job = getattr(context, "job", None)
        if not job or not getattr(job, "data", None):
            log.debug("[fantasy] _remind_boy_90m: missing job or job data, skipping")
            return
        data = getattr(job, "data", {})
        if not isinstance(data, dict):
            log.debug("[fantasy] _remind_boy_90m: invalid job data type, skipping")
            return
        match_id, boy_id = data.get("match_id"), data.get("boy_id")
        if not match_id or not boy_id:
            return
        rows = _exec("SELECT status, expires_at FROM fantasy_matches WHERE id=%s", (match_id,))
        if not rows or rows is True: return
        status, exp = rows[0]
        if status != 'pending' or reg.has_active_premium(boy_id): return
        # CRITICAL FIX: Timezone-aware datetime handling
        from datetime import timezone
        now = datetime.now(timezone.utc)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        else:
            exp = exp.astimezone(timezone.utc)
        left = max(0, int((exp - now).total_seconds()/60))
        txt = f"🚨 **FINAL WARNING - {left} MINUTES LEFT!**\n\n💔 *Your fantasy match is about to expire!*\n\n🔥 She's still waiting for you to unlock the chat...\n💭 This exact fantasy match may never happen again!\n\n⚡ **Don't let your dreams slip away!**\n💎 Upgrade NOW and start chatting instantly!"
        kb  = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 UPGRADE NOW", callback_data="premium:open")],
            [InlineKeyboardButton("💔 Let It Expire", callback_data=f"fant:boy_later:{match_id}")]
        ])
        await _send_once(context, match_id, boy_id, txt, kb)
    except Exception as e:
        log.error(f"[fantasy] remind_90m error: {e}")

async def _expire_pair_120m(context: ContextTypes.DEFAULT_TYPE):
    try:
        job = getattr(context, "job", None)
        if not job or not getattr(job, "data", None):
            log.debug("[fantasy] _expire_pair_120m: missing job or job data, skipping")
            return
        data = getattr(job, "data", {})
        if not isinstance(data, dict):
            log.debug("[fantasy] _expire_pair_120m: invalid job data type, skipping")
            return
        match_id, boy_id, girl_id = data.get("match_id"), data.get("boy_id"), data.get("girl_id")
        if not match_id or not boy_id or not girl_id:
            return
        rows = _exec("SELECT status FROM fantasy_matches WHERE id=%s", (match_id,))
        if not rows or rows is True: return
        status = rows[0][0]
        if status != 'pending': return
        _exec("UPDATE fantasy_matches SET status='expired' WHERE id=%s", (match_id,))

        await _send_once(context, match_id, girl_id,
            "❌ He didn't join the chat.\nDon't worry, we'll find another match for you.")
        await _send_once(context, match_id, boy_id,
            "💔 **YOUR FANTASY MATCH EXPIRED**\n\n😔 She waited for you, but you didn't upgrade in time...\n\n💭 *Your exact fantasy match might not come again for weeks*\n\n🔥 **Don't let this happen again!**\n💎 Get Premium for instant access to future matches",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Get Premium Now", callback_data="premium:open")],
                [InlineKeyboardButton("😢 I'll Wait", callback_data="fant:dismiss")]
            ]))
    except Exception as e:
        log.error(f"[fantasy] expire_120m error: {e}")

# ---------- MATCHER ----------
def _overlap(a, b): return list(set(a or []) & set(b or []))

async def _send_30min_warnings(context: ContextTypes.DEFAULT_TYPE):
    """Send 30-minute warnings to non-premium boys"""
    try:
        # Find matches expiring in 30 minutes for non-premium boys
        warning_matches = _exec("""
            SELECT fm.id, fm.boy_id, fm.girl_id, fm.vibe, fm.shared_keywords
            FROM fantasy_matches fm
            WHERE fm.status = 'pending'
              AND fm.expires_at <= NOW() + INTERVAL '30 minutes'
              AND fm.expires_at > NOW() + INTERVAL '25 minutes'
              AND NOT EXISTS (
                  SELECT 1 FROM fantasy_match_notifs fmn 
                  WHERE fmn.match_id = fm.id AND fmn.user_id = fm.boy_id 
                  AND fmn.sent_at > NOW() - INTERVAL '35 minutes'
              )
              AND NOT EXISTS (
                  SELECT 1 FROM users u 
                  WHERE u.tg_user_id = fm.boy_id AND u.premium_until > NOW()
              )
        """) or []

        if warning_matches and warning_matches is not True:
            for match in warning_matches:
                match_id, boy_id, girl_id, vibe, shared_kw = match
                kw_str = ", ".join(shared_kw) if shared_kw else ""

                warning_text = (
                    f"⏰ **LAST 30 MINUTES!**\n\n"
                    f"Your fantasy match _{vibe}_ expires soon!\n"
                    f"Keywords: _{kw_str}_\n\n"
                    f"💎 **Upgrade now to start chatting** or you'll miss this golden opportunity!\n\n"
                    f"Don't let her wait anymore..."
                )

                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Upgrade Now", callback_data="premium:open")],
                    [InlineKeyboardButton("💬 Connect", callback_data=f"fant:connect:{match_id}")]
                ])

                await _send_once(context, match_id, boy_id, warning_text, kb)
                log.info(f"[fantasy] Sent 30-min warning for match {match_id} to boy {boy_id}")

    except Exception as e:
        log.error(f"[fantasy] 30-min warning error: {e}")

async def _send_expiry_notifications(context: ContextTypes.DEFAULT_TYPE, match_id: int, boy_id: int, girl_id: int):
    """Send expiry notifications to both users"""
    try:
        girl_text = "❌ **Match Expired**\n\nYour fantasy match time ran out.\nDon't worry! We'll find you another match soon. 💕"
        boy_text = "❌ **Match Expired**\n\nTime's up! Your fantasy match expired.\nNext time, don't hesitate to upgrade for instant chat access. 💎"

        kb = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade Now", callback_data="premium:open")]])

        await _send_once(context, match_id, girl_id, girl_text)
        await _send_once(context, match_id, boy_id, boy_text, kb)

    except Exception as e:
        log.error(f"[fantasy] Expiry notification error: {e}")

async def _start_fantasy_chat(context: ContextTypes.DEFAULT_TYPE, match_id: int, boy_id: int, girl_id: int):
    """Start the fantasy chat between two users"""
    try:
        # Import fantasy_relay to start the chat
        from . import fantasy_relay

        # Start the chat session
        await fantasy_relay.start_fantasy_chat(context, match_id, boy_id, girl_id)

        log.info(f"[fantasy] Started chat session for match {match_id} between {boy_id} and {girl_id}")

    except Exception as e:
        log.error(f"[fantasy] Start chat error: {e}")

        # Fallback: Send manual messages to both users
        try:
            await context.bot.send_message(
                boy_id, 
                "🔥 **CHAT ACTIVE!**\n\nYour fantasy match is live! Start sending messages to chat with your match.",
                parse_mode=ParseMode.MARKDOWN
            )
            await context.bot.send_message(
                girl_id, 
                "🔥 **CHAT ACTIVE!**\n\nYour fantasy match is live! Start sending messages to chat with your match.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as fallback_error:
            log.error(f"[fantasy] Fallback message error: {fallback_error}")

async def job_fantasy_match_pairs(context: ContextTypes.DEFAULT_TYPE):
    """Main matching job - runs every 3 minutes but sends notifications ONCE per match"""
    try:
        # Send 30-minute warnings for non-premium boys
        await _send_30min_warnings(context)

        # Clean up expired matches (2-hour expiry)
        expired = _exec("""
            UPDATE fantasy_matches 
            SET status = 'expired' 
            WHERE status = 'pending' AND expires_at <= NOW()
            RETURNING id, boy_id, girl_id
        """) or []

        if expired and expired is not True:
            log.info(f"[fantasy] cleaned up {len(expired)} expired matches")

            # Send expiry notifications
            for exp_match in expired:
                await _send_expiry_notifications(context, exp_match[0], exp_match[1], exp_match[2])

        # Only get users NOT currently in active matches (prevents spam)
        subs = _exec("""
          SELECT user_id, gender, vibe, keywords
          FROM fantasy_submissions
          WHERE active = TRUE 
            AND created_at > NOW() - INTERVAL '7 days'
            AND user_id NOT IN (
              SELECT DISTINCT boy_id FROM fantasy_matches WHERE status = 'pending'
              UNION
              SELECT DISTINCT girl_id FROM fantasy_matches WHERE status = 'pending'
            )
        """) or []

        if subs and subs is not True:
            boys  = [(u,g,v,k) for (u,g,v,k) in subs if _is_m(g)]
            girls = [(u,g,v,k) for (u,g,v,k) in subs if _is_f(g)]
        else:
            boys, girls = [], []

        created = 0
        for (g_uid,_,vibe_g,kw_g) in girls:
            # find best boy same vibe with max overlap
            cands = [(b_uid,kw_b) for (b_uid,_,vibe_b,kw_b) in boys if (vibe_b==vibe_g and b_uid!=g_uid)]
            best, best_ov = None, []
            for (b_uid,kw_b) in cands:
                ov = _overlap(kw_b, kw_g)
                if len(ov) > len(best_ov):
                    # skip if currently paired (pending/active only)
                    rec = _exec("""SELECT 1 FROM fantasy_matches
                                   WHERE ((boy_id=%s AND girl_id=%s) OR (boy_id=%s AND girl_id=%s))
                                     AND status IN ('pending', 'connected') AND expires_at > NOW() LIMIT 1""",
                                 (b_uid, g_uid, g_uid, b_uid))
                    if rec: continue
                    best, best_ov = (b_uid, kw_b), ov
            if not best or len(best_ov)==0:
                continue

            b_uid,_ = best
            # CRITICAL FIX: Use timezone-aware datetime for consistency
            from datetime import timezone
            exp  = datetime.now(timezone.utc) + timedelta(hours=2)
            fkey = _make_fantasy_key(vibe_g, best_ov)

            row = _exec("""
              INSERT INTO fantasy_matches
                (boy_id, girl_id, fantasy_key, vibe, shared_keywords, expires_at, status)
              VALUES
                (%s,     %s,      %s,          %s,   %s::TEXT[],   %s,       'pending')
              RETURNING id
            """, (b_uid, g_uid, fkey, vibe_g, _arr(best_ov), exp))
            if not row or row is True:
                log.error(f"[fantasy] Failed to insert match for boy={b_uid}, girl={g_uid}")
                continue

            match_id = row[0][0]
            created += 1
            log.info(f"[fantasy] Created match {match_id}: boy={b_uid}, girl={g_uid}, vibe={vibe_g}")

            # 🔇 SILENT MODE: do NOT DM here; just store the match
            if _get_notif_mode(context) == "dm":
                # optional: allow switching back to DM mode later
                await _dm_pair_boy_and_girl(context, match_id, b_uid, g_uid, vibe_g, best_ov, exp)
            # else: silent — UI will surface pending matches when user opens /fantasy

        log.info(f"[fantasy] pairs created: {created}")
    except Exception as e:
        log.error(f"[fantasy] matcher error: {e}")

def clear_state(context):
    """Clear fantasy-related state"""
    if context.user_data:
        context.user_data.pop('awaiting_keywords', None)
        context.user_data.pop('selected_vibe', None)
        context.user_data.pop('fantasy_vibe', None)

# Safe wrapper for registration functions
def safe_get_gender(user_id: int) -> Optional[str]:
    """Safely get user gender from registration module"""
    try:
        if hasattr(reg, 'get_gender') and callable(getattr(reg, 'get_gender', None)):
            gender = getattr(reg, 'get_gender')(user_id)
            if gender:
                return normalize_gender(gender)

        # Fallback to direct database query
        pool = reg._get_pool()
        conn = pool.getconn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT gender FROM users WHERE tg_user_id = %s", (user_id,))
            result = cur.fetchone()
            if result and result[0]:
                return normalize_gender(result[0])
        finally:
            pool.putconn(conn)

        log.error(f"[fantasy] No gender found for user {user_id}")
        return None
    except Exception as e:
        log.error(f"[fantasy] Error getting gender for user {user_id}: {e}")
        return None

def safe_has_premium(user_id: int) -> bool:
    """Safely check if user has premium"""
    try:
        if hasattr(reg, 'has_active_premium') and callable(getattr(reg, 'has_active_premium', None)):
            return getattr(reg, 'has_active_premium')(user_id)
        else:
            # Fallback to direct database query
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT premium_until FROM users WHERE tg_user_id = %s", (user_id,))
                result = cur.fetchone()
                if result and result[0]:
                    from datetime import datetime
                    # CRITICAL FIX: Timezone-aware datetime handling
                    from datetime import timezone
                    now = datetime.now(timezone.utc)
                    premium_until = result[0]
                    if premium_until.tzinfo is None:
                        premium_until = premium_until.replace(tzinfo=timezone.utc)
                    else:
                        premium_until = premium_until.astimezone(timezone.utc)
                    return premium_until > now
                return False
    except Exception as e:
        log.error(f"[fantasy] Error checking premium for user {user_id}: {e}")
        return False

# Database connection
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost/postgres')

@contextmanager
def get_db():
    """Safe database connection context manager"""
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        yield conn
    except Exception as e:
        log.error(f"[fantasy] DB error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# ===== VIBE CATEGORIES SYSTEM =====

VIBE_CATEGORIES = {
    "romantic": {
        "emoji": "💕",
        "title": "Romantic",
        "desc": "Sweet, passionate, loving connections"
    },
    "roleplay": {
        "emoji": "🎭",
        "title": "Roleplay",
        "desc": "Act out scenarios, characters, situations"
    },
    "wild": {
        "emoji": "🔥",
        "title": "Wild",
        "desc": "Intense, passionate, no limits"
    },
    "adventure": {
        "emoji": "🌟",
        "title": "Adventure",
        "desc": "Exciting, daring, new experiences"
    },
    "travel": {
        "emoji": "✈️",
        "title": "Travel",
        "desc": "Exotic locations, vacation fantasies"
    },
    "intimate": {
        "emoji": "🌙",
        "title": "Intimate",
        "desc": "Deep, personal, emotional connections"
    }
}

def _normalize_keywords(s: str) -> list[str]:
    s = (s or "").lower()
    # if user typed a sentence, we still try to derive 2–3 keywords
    raw = re.split(r"[,\n ]+", s)
    words = []
    for w in raw:
        w = re.sub(r"[^a-z0-9]", "", w)
        if 2 <= len(w) <= 15:
            # skip generic stop words
            if w in {"the","and","a","an","in","on","at","to","for","with","of","is","are","was","were"}:
                continue
            words.append(w)
        if len(words) >= 6:  # collect a few, we'll trim to 3 below
            break
    # unique & cap at 3
    seen, res = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            res.append(w)
        if len(res) == 3:
            break
    return res

def calculate_keyword_overlap(kw1: List[str], kw2: List[str]) -> Tuple[List[str], float]:
    """Calculate overlap between two keyword lists"""
    if not kw1 or not kw2:
        return [], 0.0

    shared = list(set(kw1) & set(kw2))
    overlap_score = len(shared) / min(len(kw1), len(kw2))

    return shared, overlap_score

# ===== DATABASE OPERATIONS =====

def save_fantasy_submission(user_id: int, gender: str, vibe: str, keywords: List[str]) -> Tuple[bool, str]:
    """Save user's fantasy submission"""
    try:
        with get_db() as conn:
            cur = conn.cursor()

            # Check active count (max 3)
            cur.execute("""
                SELECT COUNT(*) FROM fantasy_submissions 
                WHERE user_id = %s AND active = TRUE
            """, (user_id,))

            result = cur.fetchone()
            count = result[0] if result else 0
            if count >= 3:
                return False, "You already have 3 active fantasies. Delete one first."

            # Insert new fantasy
            cur.execute("""
                INSERT INTO fantasy_submissions (user_id, gender, vibe, keywords, active)
                VALUES (%s, %s, %s, %s, TRUE)
                RETURNING id
            """, (user_id, gender, vibe, keywords))

            result = cur.fetchone()
            fantasy_id = result[0] if result else None
            conn.commit()

            log.info(f"[fantasy] Saved fantasy {fantasy_id} for user {user_id}")
            return True, f"Fantasy saved! ID: {fantasy_id}"

    except Exception as e:
        log.error(f"[fantasy] Save error: {e}")
        return False, "Failed to save fantasy. Try again."

def get_user_fantasies(user_id: int) -> List[Dict]:
    """Get user's active fantasies"""
    try:
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""
                SELECT id, vibe, keywords, created_at 
                FROM fantasy_submissions 
                WHERE user_id = %s AND active = TRUE
                ORDER BY created_at DESC
            """, (user_id,))
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        log.error(f"[fantasy] Get fantasies error: {e}")
        return []

def delete_fantasy(fantasy_id: int, user_id: int) -> bool:
    """Delete user's fantasy"""
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE fantasy_submissions 
                SET active = FALSE 
                WHERE id = %s AND user_id = %s
            """, (fantasy_id, user_id))
            conn.commit()
            return cur.rowcount > 0
    except Exception as e:
        log.error(f"[fantasy] Delete error: {e}")
        return False

# ===== HELPER FUNCTIONS =====

def _jobq(context):
    """Safe job queue accessor"""
    try:
        return context.application.job_queue
    except:
        return None

def get_fantasy_stats(user_id: int) -> dict:
    """Get comprehensive fantasy stats for a user"""
    try:
        stats = {
            'total_fantasies': 0,
            'active_fantasies': 0,
            'total_matches': 0,
            'successful_matches': 0,   # connected OR ended
            'pending_matches': 0,
            'total_chats': 0           # count ended matches as completed chat sessions
        }

        # Use reliable database connection for all stats queries
        with get_db() as conn:
            cur = conn.cursor()
            
            # Submissions
            cur.execute("""
                SELECT 
                  COUNT(*) AS total,
                  COUNT(CASE WHEN active = true THEN 1 END) AS active
                FROM fantasy_submissions
                WHERE user_id = %s
            """, (user_id,))
            result = cur.fetchone()
            if result:
                stats['total_fantasies'] = result[0] or 0
                stats['active_fantasies'] = result[1] or 0

            # TOTAL MATCHES = algorithm matches + board requests
            cur.execute("""
                SELECT
                  (SELECT COUNT(*) FROM fantasy_matches
                    WHERE boy_id = %s OR girl_id = %s)
                + (SELECT COUNT(*) FROM fantasy_match_requests
                    WHERE requester_id = %s OR fantasy_owner_id = %s)
            """, (user_id, user_id, user_id, user_id))
            result = cur.fetchone()
            if result:
                stats['total_matches'] = result[0] or 0

            # SUCCESSFUL MATCHES = chats that ever connected (include ENDED)
            cur.execute("""
                SELECT
                  (SELECT COUNT(*) FROM fantasy_matches
                    WHERE (boy_id = %s OR girl_id = %s)
                      AND status IN ('connected','ended'))
                + (SELECT COUNT(*) FROM fantasy_match_requests
                    WHERE (requester_id = %s OR fantasy_owner_id = %s)
                      AND status IN ('accepted','connected','ended'))
            """, (user_id, user_id, user_id, user_id))
            result = cur.fetchone()
            if result:
                stats['successful_matches'] = result[0] or 0

            # PENDING MATCHES = still pending (requests also checked for expiry)
            cur.execute("""
                SELECT
                  (SELECT COUNT(*) FROM fantasy_matches
                    WHERE (boy_id = %s OR girl_id = %s)
                      AND status = 'pending')
                + (SELECT COUNT(*) FROM fantasy_match_requests
                    WHERE (requester_id = %s OR fantasy_owner_id = %s)
                      AND status = 'pending' AND expires_at > NOW())
            """, (user_id, user_id, user_id, user_id))
            result = cur.fetchone()
            if result:
                stats['pending_matches'] = result[0] or 0

            # CHAT SESSIONS = matches where a connection actually started
            cur.execute("""
                SELECT COUNT(*) FROM fantasy_matches
                WHERE (boy_id = %s OR girl_id = %s)
                  AND connected_at IS NOT NULL
            """, (user_id, user_id))
            result = cur.fetchone()
            if result:
                stats['total_chats'] = result[0] or 0

        return stats

    except Exception as e:
        log.error(f"[fantasy] Error getting stats for user {user_id}: {e}")
        return {
            'total_fantasies': 0, 'active_fantasies': 0, 'total_matches': 0,
            'successful_matches': 0, 'pending_matches': 0, 'total_chats': 0
        }


# ===== MATCHING ENGINE =====



# ===== COMMAND HANDLERS =====

def _short(s, n=40):  # title line me thoda compact
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[:n-1] + "…"

async def cmd_fantasy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main fantasy command - NEW EXTRAORDINARY INTERFACE matching screenshot 4"""
    user_id = effective_uid(update)
    if user_id is None:
        return await reply_any(update, context, "Could not identify user.")

    # Handle both message and callback query contexts    
    message = get_message(update)
    if not message:
        return await reply_any(update, context, "Invalid context for fantasy command.")

    # Check if user is registered - CRITICAL FIX: Proper immediate send and return
    gender = safe_get_gender(user_id)
    if not gender:
        text = "Please complete registration first using /start"
        keyboard = [[InlineKeyboardButton("🚀 Start Registration", callback_data="start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # CRITICAL: Immediately send and return - don't continue to main UI
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await message.reply_text(text, reply_markup=reply_markup)
        return  # CRITICAL: Must return here to prevent unregistered users from accessing main UI

    # --- fetch user's active fantasies (using same working pattern as manage fantasies)
    rows = get_user_fantasies(user_id)[:3]  # Limit to 3 for main interface
    cnt_rows = _exec(
        "SELECT COUNT(*) FROM fantasy_submissions WHERE user_id=%s AND active=TRUE",
        (user_id,)
    )
    # Handle different _exec return types
    if isinstance(cnt_rows, (list, tuple)) and len(cnt_rows) > 0:
        total_cnt = cnt_rows[0][0] if isinstance(cnt_rows[0], (list, tuple)) else cnt_rows[0]
    elif isinstance(cnt_rows, int):
        total_cnt = cnt_rows
    else:
        total_cnt = 0

    # --- build header text
    header = "🔥 **FANTASY MATCH**\n\n" + "Submit your fantasies and get matched with someone who shares the same desires...\n\n"
    if total_cnt > 0:
        lines = [f"**Your Active Fantasies ({min(total_cnt,3)}/3):**"]
        EMO = {"romantic":"💕","roleplay":"🎭","wild":"🔥","adventure":"⭐","travel":"✈️","intimate":"🌙"}
        for i, fantasy in enumerate(rows, start=1):
            vb = fantasy.get('vibe', 'romantic')
            keywords = fantasy.get('keywords', [])
            emoji = EMO.get((vb or "").lower(), "✨")
            vb_name = (vb or "romantic").capitalize()
            # Use keywords as display text since fantasy_text might not be available
            display_text = ", ".join(keywords[:3]) if keywords else "Your fantasy"
            lines.append(f"{i}. {emoji} **{vb_name}** — {display_text}")
        text = header + "\n".join(lines) + "\n\n💫 **Available 24/7 • Free for everyone**"
    else:
        text = header + "You have no fantasies yet — tap below to create one.\n\n💫 **Available 24/7 • Free for everyone**"

    # --- keyboard
    keyboard = [[InlineKeyboardButton("✍️ Submit New Fantasy", callback_data="fant:submit")]]
    keyboard.append([InlineKeyboardButton("🔮 Fantasy Board", callback_data="board:open")])
    if total_cnt > 0:
        keyboard.insert(1, [InlineKeyboardButton("🗑️ Manage Fantasies", callback_data="fant:manage")])
    keyboard.extend([
        [InlineKeyboardButton("⏳ Pending Matches", callback_data="request:pending:0")],
        [InlineKeyboardButton("📊 My Stats", callback_data="fant:stats")],
        [InlineKeyboardButton("💎 Premium Benefits", callback_data="fant:premium")]
    ])

    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await message.reply_text(
                text, parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception:
        try:
            # Fallback without markdown if formatting fails
            clean_text = text.replace('*', '')
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    clean_text, reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await message.reply_text(
                    clean_text, reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            log.error(f"Fantasy display error: {e}")

# ===== CALLBACK HANDLERS =====

async def handle_fantasy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all fantasy callbacks"""
    query = update.callback_query
    if not query or not query.from_user or not query.data:
        return

    await query.answer()

    user_id = query.from_user.id
    data = query.data.split(":")

    if len(data) < 2:
        return

    action = data[1]

    # Route callbacks
    if action == "submit":
        uid = query.from_user.id
        cnt_rows = _exec("SELECT COUNT(*) FROM fantasy_submissions WHERE user_id=%s AND active=TRUE", (uid,))
        # Handle different _exec return types
        if isinstance(cnt_rows, (list, tuple)) and len(cnt_rows) > 0:
            cnt = cnt_rows[0][0] if isinstance(cnt_rows[0], (list, tuple)) else cnt_rows[0]
        elif isinstance(cnt_rows, int):
            cnt = cnt_rows
        else:
            cnt = 0
        if cnt >= 3:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Manage Fantasies", callback_data="fant:manage")],
                [InlineKeyboardButton("⬅️ Back", callback_data="fant:back")]
            ])
            return await query.edit_message_text(
                "⚠️ You already have 3 active fantasies.\nDelete one to add a new fantasy.",
                reply_markup=kb
            )
        await show_vibe_selection(update, context)
    elif action == "back":
        # Handle back button - return to main fantasy interface
        await cmd_fantasy(update, context)
    elif action == "vibe" and len(data) > 2:
        vibe = data[2]
        # Use new text framework for fantasy input
        from . import fantasy_chat
        await fantasy_chat.handle_fantasy_vibe_selection(update, context, vibe)
    elif action == "manage":
        await show_fantasy_management(update, context)
    elif action == "delete" and len(data) > 2:
        await handle_fantasy_delete(update, context, int(data[2]))
    elif action == "stats":
        await show_fantasy_stats(update, context)
    elif action == "premium":
        await show_premium_info(update, context)
    elif action == "girl_ready" and len(data) > 2:
        await handle_girl_ready(update, context, int(data[2]))
    elif action == "connect" and len(data) > 2:
        await handle_boy_connect(update, context, int(data[2]))
    elif action in ["girl_later", "boy_later"] and len(data) > 2:
        await handle_maybe_later(update, context, int(data[2]))
    elif action == "cancel" and len(data) > 2:
        await handle_cancel_match(update, context, int(data[2]))
    elif action == "pending":
        await handle_pending_matches(update, context)

async def show_vibe_selection(update, context):
    """Show vibe category selection"""
    text = "🎯 **CHOOSE YOUR FANTASY VIBE**\n\n"
    text += "Select the category that best matches your fantasy:\n\n"

    keyboard = []
    for vibe_key, vibe_info in VIBE_CATEGORIES.items():
        text += f"{vibe_info['emoji']} **{vibe_info['title']}** - {vibe_info['desc']}\n"
        keyboard.append([InlineKeyboardButton(
            f"{vibe_info['emoji']} {vibe_info['title']}", 
            callback_data=f"fant:vibe:{vibe_key}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="fant:back")])

    try:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await update.callback_query.edit_message_text(
            text.replace('*', ''),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_keyword_input(update, context):
    """Show keyword input prompt"""
    vibe = context.user_data.get('selected_vibe', 'romantic') if context.user_data else 'romantic'
    vibe_info = VIBE_CATEGORIES.get(vibe, VIBE_CATEGORIES['romantic'])

    text = f"✍️ **DESCRIBE YOUR {vibe_info['title'].upper()} FANTASY**\n\n"
    text += f"{vibe_info['emoji']} *{vibe_info['desc']}*\n\n"
    text += "Type your fantasy description (10-300 characters):\n\n"
    text += "📝 Be specific about what you want\n"
    text += "🔍 Keywords help us find your perfect match\n"
    text += "🔒 This stays completely anonymous"

    context.user_data['fantasy_vibe'] = vibe

    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="fant:back")]]

    try:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await update.callback_query.edit_message_text(
            text.replace('*', ''),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def on_keywords_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text_in = (update.message.text or "").strip()
    # if user typed a sentence, _normalize_keywords will still derive keywords
    kws  = _normalize_keywords(text_in)

    # must have vibe selected
    vibe = context.user_data.get('fantasy_vibe')
    if not vibe:
        return await update.message.reply_text("⚠️ Pick a vibe first, then send your description/keywords.")

    if len(text_in) < 10 or len(text_in) > 300:
        return await update.message.reply_text("⚠️ Please write 10–300 characters.")

    # check active count
    uid = update.effective_user.id
    rows = _exec("SELECT COUNT(*) FROM fantasy_submissions WHERE user_id=%s AND active=TRUE", (uid,))
    active = rows[0][0] if rows and rows is not True else 0
    if active >= 3:
        return await update.message.reply_text("⚠️ You already have 3 active fantasies. Disable one before adding new.")

    gender = safe_get_gender(uid)

    # INSERT with safe TEXT[] cast
    ok = _exec("""
        INSERT INTO fantasy_submissions (user_id, gender, vibe, keywords)
        VALUES (%s,%s,%s,%s::TEXT[])
    """, (uid, gender, vibe, _arr(kws)))

    if ok is None:
        # DB error (table missing or type mismatch)
        return await update.message.reply_text("❌ Failed to save fantasy. Try again.")

    # clear state and confirm
    clear_state(context)
    await update.message.reply_text("✅ Fantasy saved! We'll try to find a similar match soon.")

async def show_fantasy_management(update, context):
    """Show fantasy management interface"""
    user_id = update.callback_query.from_user.id
    fantasies = get_user_fantasies(user_id)

    if not fantasies:
        await update.callback_query.edit_message_text(
            "You don't have any active fantasies.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Submit Fantasy", callback_data="fant:submit")],
                [InlineKeyboardButton("🔙 Back", callback_data="fant:back")]
            ])
        )
        return

    text = "🗑️ **MANAGE YOUR FANTASIES**\n\n"
    text += "Select a fantasy to delete:\n\n"

    keyboard = []
    for i, fantasy in enumerate(fantasies, 1):
        vibe_info = VIBE_CATEGORIES.get(fantasy['vibe'], {})
        emoji = vibe_info.get('emoji', '🔥')
        keywords = ", ".join(fantasy['keywords'][:2]) if fantasy['keywords'] else "No keywords"

        text += f"{i}. {emoji} {fantasy['vibe'].title()} — {keywords}\n"
        keyboard.append([InlineKeyboardButton(
            f"❌ Delete #{i}", 
            callback_data=f"fant:delete:{fantasy['id']}"
        )])

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="fant:back")])

    try:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await update.callback_query.edit_message_text(
            text.replace('*', ''),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_fantasy_delete(update, context, fantasy_id: int):
    """Delete a fantasy"""
    user_id = update.callback_query.from_user.id

    if delete_fantasy(fantasy_id, user_id):
        await update.callback_query.answer("✅ Fantasy deleted!")
        await show_fantasy_management(update, context)
    else:
        await update.callback_query.answer("❌ Could not delete fantasy", show_alert=True)

async def show_fantasy_stats(update, context):
    """Show user's fantasy stats"""
    user_id = update.callback_query.from_user.id

    # Get real stats from database
    stats = get_fantasy_stats(user_id)

    text = "📊 **YOUR FANTASY STATS**\n\n"
    text += f"🔥 Total fantasies: {stats['total_fantasies']}\n"
    text += f"📝 Active fantasies: {stats['active_fantasies']}\n"
    text += f"💕 Total matches: {stats['total_matches']}\n"
    text += f"✅ Successful matches: {stats['successful_matches']}\n"
    text += f"⏳ Pending matches: {stats['pending_matches']}\n"
    text += f"💬 Chat sessions: {stats['total_chats']}\n\n"

    if stats['total_matches'] > 0:
        success_rate = round((stats['successful_matches'] / stats['total_matches']) * 100)
        text += f"📈 Success rate: {success_rate}%\n"

    if stats['total_matches'] == 0:
        text += "*Submit more fantasies to get matched!*"
    elif stats['successful_matches'] == 0:
        text += "*Your matches are waiting for connections!*"
    else:
        text += "*Keep creating amazing connections!*"

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="fant:back")]]

    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text, parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception:
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text.replace('*', ''),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(
                    text.replace('*', ''),
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            log.error(f"Fantasy stats display error: {e}")

async def show_premium_info(update, context):
    """Show premium benefits for fantasy match"""
    text = "💎 **PREMIUM FANTASY BENEFITS**\n\n"
    text += "🔥 **Instant Chat Access** - No waiting for approval\n"
    text += "⚡ **Priority Matching** - Get matched first\n"
    text += "🎯 **Extended Time Windows** - 4 hours instead of 2\n"
    text += "📸 **Photo Sharing** - Send & receive photos during chat\n"
    text += "🎙️ **Voice Messages** - Share intimate voice notes\n"
    text += "🎥 **Video Sharing** - Send videos & video notes\n"
    text += "📄 **File Sharing** - Share any document type\n"
    text += "🔄 **Unlimited Re-matches** - Multiple partners per fantasy\n"
    text += "👻 **Advanced Anonymity** - Enhanced privacy features"

    keyboard = [
        [InlineKeyboardButton("💎 Upgrade Now", callback_data="premium:open")],
        [InlineKeyboardButton("🔙 Back", callback_data="fant:back")]
    ]

    try:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        await update.callback_query.edit_message_text(
            text.replace('*', ''),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_girl_ready(update, context, match_id: int):
    """Handle girl ready callback"""
    user_id = update.callback_query.from_user.id

    try:
        with get_db() as conn:
            cur = conn.cursor()
            # Allow girl to mark ready even if match is 'connected' (boy went first)
            cur.execute("""
                UPDATE fantasy_matches 
                SET girl_ready = TRUE 
                WHERE id = %s AND girl_id = %s AND status IN ('pending', 'connected')
            """, (match_id, user_id))
            conn.commit()

            if cur.rowcount == 0:
                await update.callback_query.edit_message_text(
                    "❌ Match not found or expired.",
                    reply_markup=None
                )
                return

            # Check if both are ready now
            cur.execute("""
                SELECT boy_ready, girl_ready, boy_id, girl_id 
                FROM fantasy_matches 
                WHERE id = %s
            """, (match_id,))
            result = cur.fetchone()

            if result and result[0] and result[1]:  # Both ready
                # Start the chat for both users
                await _start_fantasy_chat(context, match_id, result[2], result[3])
                await update.callback_query.edit_message_text(
                    "🔥 **CHAT STARTED!**\n\nYour fantasy match is now live!\n\n💕 Enjoy your conversation...",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=None
                )
            else:
                await update.callback_query.edit_message_text(
                    "✅ You're ready! We'll connect you once the other side is available.",
                    reply_markup=None
                )

    except Exception as e:
        log.error(f"[fantasy] Girl ready error: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error occurred. Please try again.",
            reply_markup=None
        )

async def handle_boy_connect(update, context, match_id: int):
    """Handle premium boy connect callback"""
    user_id = update.callback_query.from_user.id

    if not safe_has_premium(user_id):
        await update.callback_query.edit_message_text(
            "❌ Premium required to connect! Upgrade now to chat with your match.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Upgrade Now", callback_data="premium:open")]
            ])
        )
        return

    try:
        with get_db() as conn:
            cur = conn.cursor()
            # Mark boy as ready and update status to connected
            cur.execute("""
                UPDATE fantasy_matches 
                SET boy_ready = TRUE, status = 'connected', connected_at = NOW()
                WHERE id = %s AND boy_id = %s AND status IN ('pending', 'connected')
            """, (match_id, user_id))
            conn.commit()

            if cur.rowcount == 0:
                await update.callback_query.edit_message_text(
                    "❌ Match not found or expired.",
                    reply_markup=None
                )
                return

            # Check if both are ready now
            cur.execute("""
                SELECT boy_ready, girl_ready, boy_id, girl_id 
                FROM fantasy_matches 
                WHERE id = %s
            """, (match_id,))
            result = cur.fetchone()

            if result and result[0] and result[1]:  # Both ready
                # Start the chat for both users
                await _start_fantasy_chat(context, match_id, result[2], result[3])
                await update.callback_query.edit_message_text(
                    "🔥 **CHAT STARTED!**\n\nYour fantasy match is now live!\n\n💕 Start chatting with your match...",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=None
                )
            else:
                # Boy is ready, waiting for girl
                await update.callback_query.edit_message_text(
                    "💕 **READY TO CHAT!**\n\nYour fantasy match is prepared.\n\n⏰ *Waiting for her to get ready...*",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=None
                )

    except Exception as e:
        log.error(f"[fantasy] Connect error: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error occurred. Please try again.",
            reply_markup=None
        )

async def handle_maybe_later(update, context, match_id: int):
    """Handle maybe later callback"""
    await update.callback_query.edit_message_text(
        "No worries! We'll keep your fantasy active for new matches.",
        reply_markup=None
    )

async def handle_cancel_match(update, context, match_id: int):
    """Handle cancel match callback - allows user to cancel pending match"""
    user_id = update.callback_query.from_user.id

    try:
        with get_db() as conn:
            cur = conn.cursor()
            # Cancel the match by setting status to 'cancelled'
            cur.execute("""
                UPDATE fantasy_matches 
                SET status = 'cancelled' 
                WHERE id = %s AND (boy_id = %s OR girl_id = %s) AND status = 'pending'
            """, (match_id, user_id, user_id))
            conn.commit()

            if cur.rowcount == 0:
                await update.callback_query.edit_message_text(
                    "❌ Match not found or already processed.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Fantasy", callback_data="fant:back")]
                    ])
                )
                return

            # Success - show clean interface (3rd screenshot style)
            await update.callback_query.edit_message_text(
                "✅ **Match Cancelled**\n\n🔄 Your fantasy is still active and will be matched with new partners.\n\n💫 *Check back soon for new matches!*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Fantasy", callback_data="fant:back")]
                ])
            )

    except Exception as e:
        log.error(f"[fantasy] Cancel match error: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error cancelling match. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Fantasy", callback_data="fant:back")]
            ])
        )

async def handle_pending_matches(update, context):
    """Handle pending fantasy matches view - detailed view of all pending matches"""
    user_id = update.callback_query.from_user.id

    try:
        # Get pending matches with ready status
        rows = _exec("""
           SELECT id, boy_id, girl_id, vibe, shared_keywords, expires_at, status, boy_ready, girl_ready
           FROM fantasy_matches
           WHERE (boy_id=%s OR girl_id=%s) AND status='pending'
           ORDER BY created_at DESC
           LIMIT 5
        """, (user_id, user_id)) or []

        # Handle database return properly
        if not rows or rows is True:
            await update.callback_query.edit_message_text(
                "🤷‍♂️ **No Pending Matches**\n\nYou don't have any pending fantasy matches right now.\n\n✍️ *Submit more fantasies to get matched!*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✍️ Submit New Fantasy", callback_data="fant:submit")],
                    [InlineKeyboardButton("🔙 Back to Fantasy", callback_data="fant:back")]
                ])
            )
            return

        # Build detailed pending matches view
        txt = "🧩 **PENDING FANTASY MATCHES**\n\n"
        txt += "Your active matches waiting for connection:\n\n"
        kb = []

        for i, (mid, b, g, vibe, skw, exp, st, boy_ready, girl_ready) in enumerate(rows, 1):
            kw_str = ", ".join(skw or [])
            ttl = _fmt_mins_left(exp)
            mine_is_girl = (user_id == g)
            mine_is_boy = (user_id == b)

            # Match details
            txt += f"**{i}. {vibe.title()}** — _{kw_str}_\n"
            txt += f"   ⏳ Time left: {ttl}\n"

            # Status indicator
            if (mine_is_girl and girl_ready) or (mine_is_boy and boy_ready):
                txt += "   ✅ *You're ready! Waiting for your match...*\n"
            else:
                txt += "   ⏳ *Confirm when you're ready to chat*\n"

            # Individual match buttons
            match_btns = []
            if mine_is_girl and not girl_ready:
                match_btns = [
                    InlineKeyboardButton(f"💬 Ready #{i}", callback_data=f"fant:girl_ready:{mid}"),
                    InlineKeyboardButton(f"❌ Cancel #{i}", callback_data=f"fant:cancel:{mid}")
                ]
            elif mine_is_boy and safe_has_premium(user_id) and not boy_ready:
                match_btns = [
                    InlineKeyboardButton(f"💬 Start #{i}", callback_data=f"fant:connect:{mid}"),
                    InlineKeyboardButton(f"❌ Cancel #{i}", callback_data=f"fant:cancel:{mid}")
                ]
            elif mine_is_boy and not safe_has_premium(user_id):
                match_btns = [
                    InlineKeyboardButton(f"💎 Upgrade #{i}", callback_data="premium:open"),
                    InlineKeyboardButton(f"❌ Cancel #{i}", callback_data=f"fant:cancel:{mid}")
                ]
            else:
                # Already ready, just show cancel option
                match_btns = [InlineKeyboardButton(f"❌ Cancel #{i}", callback_data=f"fant:cancel:{mid}")]

            if match_btns:
                kb.append(match_btns)

            txt += "\n"

        txt += "💡 *If you can't wait longer, tap cancel match to find new match*\n\n"
        txt += "🔄 *New matches appear automatically as they're found*"

        # Navigation buttons
        kb.append([InlineKeyboardButton("🔙 Back to Fantasy", callback_data="fant:back")])

        await update.callback_query.edit_message_text(
            txt, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )

    except Exception as e:
        log.error(f"[fantasy] Pending matches error: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading pending matches. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Fantasy", callback_data="fant:back")]
            ])
        )

# ===== ADMIN COMMANDS =====

async def cmd_fantasy_notif_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to toggle fantasy notification mode"""
    if update.effective_user.id not in ADMIN_IDS: 
        return

    if not update.message:
        return

    mode = (context.args[0].lower() if context.args else "silent")
    if mode not in ("silent","dm"):
        return await update.message.reply_text("Usage: /fantasy_notif_mode silent|dm")

    set_fantasy_notif_mode(context, mode)
    current_mode = _get_notif_mode(context)
    await update.message.reply_text(f"✅ Fantasy notifications set to: *{current_mode}*", parse_mode="Markdown")

# ===== FANTASY BOARD SYSTEM =====

async def cmd_fantasy_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the Fantasy Board - browse all fantasies with gender markers"""
    if not update.effective_user:
        return

    user_id = update.effective_user.id

    # Get active fantasies with gender info
    query = """
        SELECT f.id, f.user_id, f.fantasy_text, f.vibe, f.gender, f.created_at
        FROM fantasy_submissions f
        WHERE f.active = TRUE
        ORDER BY f.created_at DESC
        LIMIT 12
    """

    rows = _exec(query, ())

    text = "🔮 **FANTASY BOARD** 🔮\n\n"
    text += "Browse and choose who to chat with:\n\n"

    if not rows or rows is True:
        text += "No fantasies available right now.\n"
        text += "Be the first to create one with /fantasy!"

        keyboard = [[InlineKeyboardButton("🌟 Create Fantasy", callback_data="fb_create_fantasy")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        # Display fantasies with gender markers
        fantasy_buttons = []
        for i, row in enumerate(rows[:8], 1):  # Limit to 8 for display
            fantasy_id, owner_id, fantasy_text, vibe, gender, created_at = row

            # Skip user's own fantasies
            if owner_id == user_id:
                continue

            # Format display text
            display_text = fantasy_text[:80] + "..." if len(fantasy_text) > 80 else fantasy_text
            gender_emoji = "👨" if gender == "m" else "👩"
            vibe_emoji = {"romantic": "💕", "adventurous": "🔥", "playful": "✨", "mysterious": "🎭"}.get(vibe, "💫")

            text += f"{i}. {vibe_emoji} {gender_emoji} \"{display_text}\"\n\n"

            # Add selection button
            fantasy_buttons.append([InlineKeyboardButton(f"💬 Chat #{i}", callback_data=f"fb_select:{fantasy_id}")])

        # Build keyboard
        keyboard = fantasy_buttons[:6]  # Max 6 buttons
        keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="fb_refresh")])
        keyboard.append([InlineKeyboardButton("🌟 Create Fantasy", callback_data="fb_create_fantasy")])
        reply_markup = InlineKeyboardMarkup(keyboard)

    # Send or edit message
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        except:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def handle_fantasy_board_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Fantasy Board callbacks"""
    query = update.callback_query
    if not query or not query.data or not query.from_user:
        return

    data = query.data

    if data == "fb_refresh":
        await cmd_fantasy_board(update, context)
    elif data.startswith("fb_select:"):
        fantasy_id = int(data.split(":")[1])
        await handle_fantasy_board_selection(update, context, fantasy_id)
    elif data == "fb_create_fantasy":
        # Direct fantasy creation from Fantasy Board - open fantasy interface
        await cmd_fantasy(update, context)

async def handle_fantasy_board_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, fantasy_id: int):
    """Handle when user selects a fantasy from the board"""
    query = update.callback_query
    if not query or not query.from_user:
        return

    await query.answer()
    requester_id = query.from_user.id

    # Get fantasy details
    fantasy_row = _exec("SELECT user_id, fantasy_text, vibe, gender FROM fantasy_submissions WHERE id=%s AND active=TRUE", (fantasy_id,))
    if not fantasy_row or fantasy_row is True:
        await query.edit_message_text("❌ This fantasy is no longer available.")
        return

    fantasy_owner_id, fantasy_text, vibe, fantasy_gender = fantasy_row[0]

    if fantasy_owner_id == requester_id:
        await query.answer("You can't match with your own fantasy!", show_alert=True)
        return

    # Get requester profile
    requester_profile = reg.get_profile(requester_id) or {}
    requester_gender = normalize_gender(requester_profile.get("gender"))

    if not requester_gender:
        await query.edit_message_text("⚠️ Please complete your profile first with /profile")
        return

    # Send notification to fantasy owner
    requester_gender_emoji = "👨" if requester_gender == "m" else "👩"
    requester_gender_name = "boy" if requester_gender == "m" else "girl"

    display_text = fantasy_text[:100] + "..." if len(fantasy_text) > 100 else fantasy_text

    notification_text = f"{requester_gender_emoji} **FANTASY MATCH REQUEST** {requester_gender_emoji}\n\n"
    notification_text += f"🔥 A {requester_gender_name} wants to make your fantasy reality:\n\n"
    notification_text += f"💭 \"{display_text}\"\n\n"

    # Check premium requirements (boys need premium to chat with girls)
    if requester_gender == "m" and fantasy_gender == "f":  # Boy requesting girl
        try:
            has_premium = reg.has_active_premium(requester_id)
        except (AttributeError, Exception):
            has_premium = False

        if not has_premium:
            await query.edit_message_text("💎 **Premium Required!**\n\nUpgrade to Premium to chat with girls!\nUse /premium to unlock unlimited fantasy chats!")
            return
        notification_text += "💎 This user has Premium membership.\n\n"

    notification_text += "Would you like to start a 30-minute anonymous chat?"

    # Create approval buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Let's Chat!", callback_data=f"request:approve:{requester_id}:{fantasy_id}"),
            InlineKeyboardButton("❌ No Thanks", callback_data=f"request:decline:{requester_id}:{fantasy_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(fantasy_owner_id, notification_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        await query.edit_message_text("✅ **Request Sent!**\n\nWaiting for their response...\nYou'll be notified when they decide!")
    except Exception as e:
        log.error(f"Failed to send request notification: {e}")
        await query.edit_message_text("❌ Failed to send request. Please try again.")

# ===== REGISTRATION =====

def register(app):
    """Register all fantasy match handlers"""
    # Main command
    app.add_handler(CommandHandler("fantasy", cmd_fantasy), group=-1)

    # NEW: Fantasy Board command
    app.add_handler(CommandHandler("fantasy_board", cmd_fantasy_board), group=-1)
    app.add_handler(CommandHandler("board", cmd_fantasy_board), group=-1)

    # Callback handlers
    app.add_handler(CallbackQueryHandler(
        handle_fantasy_callback, 
        pattern="^fant:"
    ), group=-1)

    # CRITICAL: Fantasy Board callbacks - HIGHEST PRIORITY to work before text framework
    app.add_handler(CallbackQueryHandler(
        handle_fantasy_board_callback, 
        pattern="^fb_"
    ), group=-25)

    # Admin commands
    app.add_handler(CommandHandler("fantasy_notif_mode", cmd_fantasy_notif_mode), group=0)

    # OLD TEXT HANDLER - DISABLED: Now using text_framework for fantasy input
    # app.add_handler(MessageHandler(
    #     filters.TEXT & ~filters.COMMAND,
    #     on_keywords_message
    # ), group=-3)

    log.info("[fantasy] Handlers registered successfully")

# ===== SCHEDULER SETUP =====

def schedule_fantasy_jobs(app):
    """Schedule recurring fantasy jobs"""
    if hasattr(app, 'job_queue') and app.job_queue:
        # Run matching every 3 minutes
        app.job_queue.run_repeating(
            job_fantasy_match_pairs,
            interval=180,  # 3 minutes
            first=10       # Start after 10 seconds
        )
        log.info("[fantasy] Scheduled matching job every 3 minutes")
    else:
        log.warning("[fantasy] No job queue available - matching job not scheduled")