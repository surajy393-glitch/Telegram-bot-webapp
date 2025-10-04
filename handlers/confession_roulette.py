from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, JobQueue
from telegram.error import RetryAfter, TimedOut, NetworkError, Forbidden, TelegramError
import asyncio
import datetime
import pytz
import re
from html import escape
import os

# Import canonical SSL-enforced connection
from registration import _conn
import psycopg2

# Import async database utility
from utils.db_async import run_db

# Import state management
from handlers.text_framework import set_state, make_cancel_kb, clear_state, requires_state, claim_or_reject

# Import send_and_delete utility for auto-deletion
from handlers.posts_handlers import send_and_delete_notification as send_and_delete

# Testers fallback for small pools
TESTERS = {8482725798, 647778438, 1437934486}

# IST timezone for round key
IST = pytz.timezone("Asia/Kolkata")

def _current_round_key(dt: datetime.datetime = None) -> str:
    now = (dt or datetime.datetime.now(IST)).astimezone(IST)
    # lock per-day-per-19:30 slot
    return now.strftime("%Y-%m-%d 19:30")

def _ensure_conf_round_lock():
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS confession_round_lock(
                    user_id BIGINT NOT NULL,
                    round_key TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY(user_id, round_key)
                )
            """)
            con.commit()
    except Exception as e:
        print(f"[conf] lock schema err: {e}")

def _try_mark_round_delivery(user_id: int) -> bool:
    _ensure_conf_round_lock()
    rk = _current_round_key()
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute(
                """INSERT INTO confession_round_lock(user_id, round_key)
                   VALUES (%s, %s)
                   ON CONFLICT DO NOTHING
                   RETURNING user_id""",
                (user_id, rk),
            )
            got = cur.fetchone()
            con.commit()
            return bool(got)
    except Exception as e:
        print(f"[conf] round lock err: {e}")
        return False

async def _safe_send(bot, chat_id: int, text: str, parse_mode=None, reply_markup=None, retries: int = 3) -> bool:
    """Send with enhanced retries for TLS/connection hiccups."""
    for i in range(retries):
        try:
            await bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
            return True
        except RetryAfter as e:
            retry_after = getattr(e, "retry_after", 1.0)
            print(f"[confession] ⏳ Rate limited, waiting {retry_after}s")
            await asyncio.sleep(retry_after + 0.2)
        except (TimedOut, NetworkError, Forbidden) as e:
            print(f"[confession] 📡❌ Network/Forbidden error (attempt {i+1}): {e}")
            await asyncio.sleep(0.4 + 0.3 * i)
        except Exception as e:
            print(f"[confession] 🤖❌ Telegram error (attempt {i+1}): {e}")
            await asyncio.sleep(0.4 + 0.3 * i)
    return False

def ensure_confessions_table():
    with _conn() as con, con.cursor() as cur:
        # Original confessions table
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
        # Add system_seed column if it doesn't exist (for existing installations)
        cur.execute("""
            ALTER TABLE confessions 
            ADD COLUMN IF NOT EXISTS system_seed BOOLEAN DEFAULT FALSE;
        """)

        # Add deleted_at column for soft deletes
        cur.execute("""
            ALTER TABLE confessions
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
        """)

        # 📊 Enhanced tables for gamification and stats

        # User confession stats and streaks
        cur.execute("""
            CREATE TABLE IF NOT EXISTS confession_stats (
                user_id BIGINT PRIMARY KEY,
                total_confessions INTEGER DEFAULT 0,
                weekly_confessions INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                total_reactions_received INTEGER DEFAULT 0,
                total_replies_received INTEGER DEFAULT 0,
                best_confessor_score INTEGER DEFAULT 0,
                last_confession_date DATE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # Confession reactions (likes, love, fire, etc.)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS confession_reactions (
                id BIGSERIAL PRIMARY KEY,
                confession_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                reaction_type VARCHAR(10) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                approved BOOLEAN DEFAULT FALSE,
                approved_at TIMESTAMPTZ,
                UNIQUE(confession_id, user_id, reaction_type)
            );
        """)

        # Anonymous replies to confessions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS confession_replies (
                id BIGSERIAL PRIMARY KEY,
                original_confession_id BIGINT NOT NULL,
                replier_user_id BIGINT NOT NULL,
                reply_text TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                reply_reactions INTEGER DEFAULT 0,
                is_anonymous BOOLEAN DEFAULT TRUE,
                approved BOOLEAN DEFAULT FALSE,
                approved_at TIMESTAMPTZ,
                UNIQUE(original_confession_id, replier_user_id)
            );
        """)

        # Leaderboards for different categories
        cur.execute("""
            CREATE TABLE IF NOT EXISTS confession_leaderboard (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                period VARCHAR(20) NOT NULL,
                confession_count INTEGER DEFAULT 0,
                total_reactions_received INTEGER DEFAULT 0,
                replies_received INTEGER DEFAULT 0,
                rank_type VARCHAR(30) NOT NULL,
                rank_position INTEGER DEFAULT 0,
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(user_id, period, rank_type)
            );
        """)

        # Confession delivery tracking (enhanced)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS confession_deliveries (
                id BIGSERIAL PRIMARY KEY,
                confession_id BIGINT NOT NULL,
                recipient_id BIGINT NOT NULL,
                delivered_at TIMESTAMPTZ DEFAULT NOW(),
                has_replied BOOLEAN DEFAULT FALSE,
                reaction_count INTEGER DEFAULT 0,
                UNIQUE(confession_id, recipient_id)
            );
        """)

        # Mutes for notifications
        cur.execute("""
            CREATE TABLE IF NOT EXISTS confession_mutes(
                user_id BIGINT NOT NULL,
                confession_id BIGINT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY(user_id, confession_id)
            )
        """)

        # Pending confessions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pending_confessions (
                id BIGSERIAL PRIMARY KEY,
                author_id BIGINT NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Pending replies table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pending_confession_replies (
                id BIGSERIAL PRIMARY KEY,
                original_confession_id BIGINT NOT NULL,
                replier_user_id BIGINT NOT NULL,
                reply_text TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        con.commit()

# === ENHANCED CONFESSION FEATURES ===

def update_user_confession_stats(user_id: int):
    """Update user confession stats when they submit a confession"""
    try:
        with _conn() as con, con.cursor() as cur:
            current_date = datetime.date.today()

            # Get current stats or create if doesn't exist
            cur.execute("SELECT * FROM confession_stats WHERE user_id = %s", (user_id,))
            stats = cur.fetchone()

            if stats:
                # Update existing stats
                total_confessions = stats[1] + 1
                weekly_confessions = stats[2] + 1

                # Check streak logic
                last_date = stats[8] if stats[8] else current_date
                if isinstance(last_date, str):
                    last_date = datetime.datetime.strptime(last_date, '%Y-%m-%d').date()

                if last_date == current_date:
                    # Same day, don't increment streak
                    current_streak = stats[3]
                elif last_date == current_date - datetime.timedelta(days=1):
                    # Consecutive day, increment streak
                    current_streak = stats[3] + 1
                else:
                    # Streak broken, reset to 1
                    current_streak = 1

                longest_streak = max(stats[4], current_streak)

                cur.execute("""
                    UPDATE confession_stats 
                    SET total_confessions = %s, weekly_confessions = %s, 
                        current_streak = %s, longest_streak = %s, 
                        last_confession_date = %s, updated_at = NOW()
                    WHERE user_id = %s
                """, (total_confessions, weekly_confessions, current_streak, 
                      longest_streak, current_date, user_id))
            else:
                # Create new stats record
                cur.execute("""
                    INSERT INTO confession_stats 
                    (user_id, total_confessions, weekly_confessions, current_streak, 
                     longest_streak, total_reactions_received, total_replies_received, 
                     best_confessor_score, last_confession_date, created_at, updated_at)
                    VALUES (%s, 1, 1, 1, 1, 0, 0, 0, %s, NOW(), NOW())
                """, (user_id, current_date))

            con.commit()
    except Exception as e:
        print(f"❌ Error updating confession stats for user {user_id}: {e}")

def get_confession_stats(user_id: int) -> dict:
    """Get comprehensive confession stats for a user"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Get or create user stats
            cur.execute("""
                INSERT INTO confession_stats (user_id) 
                VALUES (%s) 
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))

            cur.execute("""
                SELECT total_confessions, weekly_confessions, current_streak, 
                       longest_streak, total_reactions_received, total_replies_received,
                       best_confessor_score, last_confession_date
                FROM confession_stats 
                WHERE user_id = %s
            """, (user_id,))

            result = cur.fetchone()
            if result:
                return {
                    'total_confessions': result[0] or 0,
                    'weekly_confessions': result[1] or 0,
                    'current_streak': result[2] or 0,
                    'longest_streak': result[3] or 0,
                    'total_reactions': result[4] or 0,
                    'total_replies': result[5] or 0,
                    'confessor_score': result[6] or 0,
                    'last_confession': result[7]
                }
    except Exception as e:
        print(f"❌ Error getting user stats: {e}")

    return {
        'total_confessions': 0, 'weekly_confessions': 0, 'current_streak': 0,
        'longest_streak': 0, 'total_reactions': 0, 'total_replies': 0,
        'confessor_score': 0, 'last_confession': None
    }

def get_weekly_leaderboard(limit: int = 10) -> dict:
    """Get weekly leaderboards for different categories"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Best confessors (most confessions + engagement)
            cur.execute("""
                SELECT user_id, weekly_confessions, total_reactions_received
                FROM confession_stats 
                WHERE weekly_confessions > 0
                ORDER BY (weekly_confessions * 2 + total_reactions_received) DESC
                LIMIT %s
            """, (limit,))
            best_confessors = cur.fetchall()

            # Most liked confessions this week
            cur.execute("""
                SELECT c.author_id, c.text, COUNT(cr.id) as reaction_count
                FROM confessions c
                LEFT JOIN confession_reactions cr ON c.id = cr.confession_id
                WHERE c.created_at >= DATE_TRUNC('week', NOW())
                GROUP BY c.id, c.author_id, c.text
                HAVING COUNT(cr.id) > 0
                ORDER BY reaction_count DESC
                LIMIT %s
            """, (limit,))
            most_liked = cur.fetchall()

            # Reply masters (most helpful replies)
            cur.execute("""
                SELECT replier_user_id, COUNT(*) as reply_count, SUM(reply_reactions) as total_reactions
                FROM confession_replies 
                WHERE created_at >= DATE_TRUNC('week', NOW())
                GROUP BY replier_user_id
                ORDER BY reply_count DESC
                LIMIT %s
            """, (limit,))
            reply_masters = cur.fetchall()

            return {
                'best_confessors': best_confessors,
                'most_liked': most_liked, 
                'reply_masters': reply_masters
            }
    except Exception as e:
        print(f"❌ Error getting leaderboards: {e}")
        return {'best_confessors': [], 'most_liked': [], 'reply_masters': []}

def get_live_activity_stats() -> dict:
    """Get real-time confession activity stats"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Today's activity
            cur.execute("""
                SELECT 
                    COUNT(CASE WHEN created_at::date = CURRENT_DATE THEN 1 END) as confessions_today,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 hour' THEN 1 END) as confessions_hour
                FROM confessions
                WHERE created_at >= CURRENT_DATE
            """)
            conf_stats = cur.fetchone()

            # Active players (replied or confessed recently)
            cur.execute("""
                SELECT COUNT(DISTINCT user_id) as active_players
                FROM (
                    SELECT author_id as user_id FROM confessions WHERE created_at >= NOW() - INTERVAL '2 hours'
                    UNION
                    SELECT replier_user_id as user_id FROM confession_replies WHERE created_at >= NOW() - INTERVAL '2 hours'
                ) active
            """)
            active_count = cur.fetchone()[0] or 0

            # Recent reactions
            cur.execute("""
                SELECT COUNT(*) as reactions_today
                FROM confession_reactions 
                WHERE created_at::date = CURRENT_DATE
            """)
            reactions_today = cur.fetchone()[0] or 0

            # Recent replies
            cur.execute("""
                SELECT COUNT(*) as replies_today
                FROM confession_replies 
                WHERE created_at::date = CURRENT_DATE
            """)
            replies_today = cur.fetchone()[0] or 0

            return {
                'confessions_today': conf_stats[0] or 0,
                'confessions_hour': conf_stats[1] or 0,
                'active_players': active_count,
                'reactions_today': reactions_today,
                'replies_today': replies_today
            }
    except Exception as e:
        print(f"❌ Error getting activity stats: {e}")
        return {
            'confessions_today': 0, 'confessions_hour': 0, 'active_players': 0,
            'reactions_today': 0, 'replies_today': 0
        }

def update_user_confession_stats(user_id: int):
    """Update user stats after sending a confession"""
    try:
        with _conn() as con, con.cursor() as cur:
            today = datetime.date.today()

            # Get current stats
            cur.execute("""
                SELECT current_streak, last_confession_date 
                FROM confession_stats 
                WHERE user_id = %s
            """, (user_id,))
            result = cur.fetchone()

            if result:
                current_streak, last_confession = result
                # Check if streak continues
                if last_confession == today - datetime.timedelta(days=1):
                    new_streak = current_streak + 1
                elif last_confession == today:
                    new_streak = current_streak  # Same day, no change
                else:
                    new_streak = 1  # Streak broken or new start
            else:
                new_streak = 1

            # Update stats
            cur.execute("""
                INSERT INTO confession_stats (
                    user_id, total_confessions, weekly_confessions, current_streak, 
                    longest_streak, last_confession_date
                ) VALUES (%s, 1, 1, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    total_confessions = confession_stats.total_confessions + 1,
                    weekly_confessions = confession_stats.weekly_confessions + 1,
                    current_streak = %s,
                    longest_streak = GREATEST(confession_stats.longest_streak, %s),
                    last_confession_date = %s,
                    updated_at = NOW()
            """, (user_id, new_streak, new_streak, today, new_streak, new_streak, today))

            con.commit()
    except Exception as e:
        print(f"❌ Error updating user stats: {e}")

def add_confession_reaction(confession_id: int, user_id: int, reaction_type: str) -> tuple[bool, int]:
    """Add a reaction to a confession - returns (success, author_id)"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Get author ID first
            cur.execute("SELECT author_id FROM confessions WHERE id = %s AND deleted_at IS NULL", (confession_id,))
            result = cur.fetchone()
            if not result:
                return False, None
            author_id = result[0]

            # Insert reaction (ignore if duplicate) with approved status
            cur.execute("""
                INSERT INTO confession_reactions (confession_id, user_id, reaction_type, approved, approved_at)
                VALUES (%s, %s, %s, TRUE, NOW())
                ON CONFLICT (confession_id, user_id, reaction_type) DO NOTHING
                RETURNING id
            """, (confession_id, user_id, reaction_type))

            if cur.fetchone():
                # Update author's reaction count
                cur.execute("""
                    UPDATE confession_stats 
                    SET total_reactions_received = total_reactions_received + 1
                    WHERE user_id = %s
                """, (author_id,))
                con.commit()
                return True, author_id
    except Exception as e:
        print(f"❌ Error adding reaction: {e}")
    return False, None

async def notify_confessor_about_activity(context, author_id: int, activity_type: str, details: dict | None = None):
    """DM to original confessor on reaction/reply (with retries + CTA buttons)."""
    if not author_id:
        return

    details = details or {}
    cid = details.get('confession_id')

    try:
        if activity_type == "reaction":
            # Clean reaction notification without buttons
            emoji = details.get('reaction_type', '❤️')
            msg = f"""✅ Someone reacted {emoji} to your confession #{cid}.

💭 Your confession touched someone's heart...
🔄 Share another secret: /confess"""
            # No buttons for reactions - clean notification
            await _safe_send(context.bot, author_id, msg)
            
        else:  # "reply"
            # Reply notification without buttons - clean notification only
            preview = (details.get('reply_text') or '')
            preview = (preview[:50] + "…") if len(preview) > 50 else preview
            msg = f"""💌 Anonymous reply on your confession #{cid}:

"{preview}" """
            
            await _safe_send(context.bot, author_id, msg)

    except Exception as e:
        print(f"❌ Error sending confessor notification: {e}")

def send_anonymous_reply(original_confession_id: int, replier_id: int, reply_text: str) -> tuple[bool, int]:
    """Move reply to approved table; treat duplicates as success so approval never fails."""
    try:
        with _conn() as con, con.cursor() as cur:
            # Find original author
            cur.execute(
                "SELECT author_id FROM confessions WHERE id=%s AND deleted_at IS NULL",
                (original_confession_id,)
            )
            row = cur.fetchone()
            if not row:
                return False, None
            author_id = int(row[0])

            # Insert (idempotent): ON CONFLICT DO NOTHING with approved status
            cur.execute("""
                INSERT INTO confession_replies (original_confession_id, replier_user_id, reply_text, approved, approved_at)
                VALUES (%s, %s, %s, TRUE, NOW())
                ON CONFLICT (original_confession_id, replier_user_id) DO NOTHING
                RETURNING id
            """, (original_confession_id, replier_id, reply_text))
            inserted = cur.fetchone()

            # Stats tab sirf nayi row pe update karein
            if inserted:
                cur.execute("""
                    UPDATE confession_stats
                       SET total_replies_received = total_replies_received + 1
                     WHERE user_id = %s
                """, (author_id,))

            con.commit()
            # ⚠️ IMPORTANT: Duplicate par bhi True return karo — approval flow ab kabhi fail nahi hoga
            return True, author_id

    except Exception as e:
        print(f"❌ Error sending reply: {e}")
        return False, None

def submit_reply_for_approval(original_confession_id: int, replier_id: int, reply_text: str) -> tuple[bool, int]:
    """Submit reply for admin approval - returns (success, pending_reply_id)"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Check if user already has a pending or approved reply for this confession
            cur.execute("""
                SELECT 1 FROM pending_confession_replies 
                WHERE original_confession_id = %s AND replier_user_id = %s
                UNION
                SELECT 1 FROM confession_replies 
                WHERE original_confession_id = %s AND replier_user_id = %s
            """, (original_confession_id, replier_id, original_confession_id, replier_id))

            if cur.fetchone():
                return False, None  # Already replied or has pending reply

            # Insert into pending replies
            cur.execute("""
                INSERT INTO pending_confession_replies (original_confession_id, replier_user_id, reply_text)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (original_confession_id, replier_id, reply_text))

            pending_reply_id = cur.fetchone()[0]
            con.commit()
            return True, pending_reply_id

    except Exception as e:
        print(f"❌ Error submitting reply for approval: {e}")
    return False, None

# === ADMIN APPROVAL SYSTEM ===
async def notify_admin_new_confession(context, pending_id: int, text: str, author_id: int):
    """Notify admin about new confession pending approval"""
    # Get admin IDs from environment or fallback
    admin_ids = [1437934486, 647778438]  # Your admin IDs

    # NOTE: Voice functionality removed - confessions are text-only

    for admin_id in admin_ids:
        try:
            keyboard = [
                [
                    {"text": "✅ Approve", "callback_data": f"approve_conf:{pending_id}"},
                    {"text": "❌ Reject", "callback_data": f"reject_conf:{pending_id}"}
                ]
            ]

            # Only text confessions - no voice functionality
            # Regular text confession
            message = (
                f"🔔 NEW CONFESSION PENDING APPROVAL\n\n"
                f"📝 Text: \"{text}\"\n\n"
                f"👤 Author ID: {author_id}\n"
                f"🆔 Pending ID: #{pending_id}\n\n"
                f"Please review and approve/reject:"
            )

            await context.bot.send_message(
                admin_id, 
                message,
                reply_markup={"inline_keyboard": keyboard}
            )
        except Exception as e:
            print(f"❌ Failed to notify admin {admin_id}: {e}")

async def notify_admin_new_reply(context, pending_reply_id: int, confession_id: int, reply_text: str, replier_id: int):
    """Notify admin about new reply pending approval"""
    # Get admin IDs from environment or fallback
    admin_ids = [1437934486, 647778438]  # Your admin IDs

    for admin_id in admin_ids:
        try:
            keyboard = [
                [
                    {"text": "✅ Approve Reply", "callback_data": f"approve_reply:{pending_reply_id}"},
                    {"text": "❌ Reject Reply", "callback_data": f"reject_reply:{pending_reply_id}"}
                ]
            ]

            message = (
                f"💬 NEW REPLY PENDING APPROVAL\n\n"
                f"📝 Reply Text: \"{reply_text}\"\n\n"
                f"🎯 To Confession: #{confession_id}\n"
                f"👤 Replier ID: {replier_id}\n"
                f"🆔 Pending Reply ID: #{pending_reply_id}\n\n"
                f"Please review and approve/reject this reply:"
            )

            await context.bot.send_message(
                admin_id, 
                message,
                reply_markup={"inline_keyboard": keyboard}
            )
        except Exception as e:
            print(f"❌ Failed to notify admin {admin_id}: {e}")

async def approve_confession(update, context, pending_id: int):
    """Admin approves a confession - moves it to main confessions table"""
    try:
        def approve_db_transaction(pending_id):
            with _conn() as con, con.cursor() as cur:
                # Get pending confession
                cur.execute("SELECT author_id, text FROM pending_confessions WHERE id = %s", (pending_id,))
                result = cur.fetchone()
                if not result:
                    return None

                author_id, text = result

                # Move to main confessions table
                cur.execute(
                    "INSERT INTO confessions (author_id, text, system_seed) VALUES (%s, %s, FALSE)",
                    (author_id, text)
                )

                # Remove from pending
                cur.execute("DELETE FROM pending_confessions WHERE id = %s", (pending_id,))
                con.commit()
                return (author_id, text)
        
        result = await run_db(approve_db_transaction, pending_id)
        if not result:
            return await update.callback_query.answer("❌ Confession not found!")
        
        author_id, text = result
        await update.callback_query.answer("✅ Confession approved!")
        await update.callback_query.edit_message_text(
            f"✅ APPROVED CONFESSION\n\n"
            f"📝 Text: \"{text}\"\n"
            f"👤 Author: {author_id}\n\n"
            f"This confession is now in the delivery pool!"
        )

        # Don't notify user about approval - keep it silent

    except Exception as e:
        print(f"❌ Error approving confession: {e}")
        await update.callback_query.answer("❌ Error approving confession!")

async def reject_confession(update, context, pending_id: int):
    """Admin rejects a confession - removes it permanently"""
    try:
        def reject_db_transaction(pending_id):
            with _conn() as con, con.cursor() as cur:
                # Get pending confession for notification
                cur.execute("SELECT author_id, text FROM pending_confessions WHERE id = %s", (pending_id,))
                result = cur.fetchone()
                if not result:
                    return None

                author_id, text = result

                # Remove from pending (rejected)
                cur.execute("DELETE FROM pending_confessions WHERE id = %s", (pending_id,))
                con.commit()
                return (author_id, text)
        
        result = await run_db(reject_db_transaction, pending_id)
        if not result:
            return await update.callback_query.answer("❌ Confession not found!")
        
        author_id, text = result
        await update.callback_query.answer("❌ Confession rejected!")
        await update.callback_query.edit_message_text(
            f"❌ REJECTED CONFESSION\n\n"
            f"📝 Text: \"{text}\"\n"
            f"👤 Author: {author_id}\n\n"
            f"This confession was not approved for delivery."
        )

        # Don't notify user about rejection - keep it silent

    except Exception as e:
        print(f"❌ Error rejecting confession: {e}")
        await update.callback_query.answer("❌ Error rejecting confession!")

async def approve_reply(update, context, pending_reply_id: int):
    """Admin approves a reply - moves it to main confession_replies table and notifies both users"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Get pending reply details
            cur.execute("""
                SELECT original_confession_id, replier_user_id, reply_text 
                FROM pending_confession_replies WHERE id = %s
            """, (pending_reply_id,))
            result = cur.fetchone()
            if not result:
                return await update.callback_query.answer("❌ Reply not found!")

            confession_id, replier_id, reply_text = result

            # Move to approved replies using the existing function
            success, author_id = send_anonymous_reply(confession_id, replier_id, reply_text)

            if success:
                # Remove from pending
                cur.execute("DELETE FROM pending_confession_replies WHERE id = %s", (pending_reply_id,))
                con.commit()

                await update.callback_query.answer("✅ Reply approved!")
                await update.callback_query.edit_message_text(
                    f"✅ APPROVED REPLY\n\n"
                    f"📝 Reply: \"{reply_text}\"\n"
                    f"🎯 To Confession: #{confession_id}\n"
                    f"👤 Replier: {replier_id}\n\n"
                    f"Reply has been delivered to the confessor!"
                )

                # STEALTH MODERATION: Users never know about approvals - they already think it was delivered instantly

                # Notify original confessor ONLY AFTER APPROVAL
                await notify_confessor_about_activity(
                    context, 
                    author_id, 
                    "reply", 
                    {
                        "confession_id": confession_id,
                        "reply_text": reply_text
                    }
                )
                print(f"✅ Reply approved and confessor notified for confession #{confession_id}")
            else:
                await update.callback_query.answer("❌ Error moving reply to approved!")

    except Exception as e:
        print(f"❌ Error approving reply: {e}")
        await update.callback_query.answer("❌ Error approving reply!")

async def reject_reply(update, context, pending_reply_id: int):
    """Admin rejects a reply - removes it permanently and notifies replier"""
    try:
        with _conn() as con, con.cursor() as cur:
            # Get pending reply details for notification
            cur.execute("""
                SELECT original_confession_id, replier_user_id, reply_text 
                FROM pending_confession_replies WHERE id = %s
            """, (pending_reply_id,))
            result = cur.fetchone()
            if not result:
                return await update.callback_query.answer("❌ Reply not found!")

            confession_id, replier_id, reply_text = result

            # Remove from pending (rejected)
            cur.execute("DELETE FROM pending_confession_replies WHERE id = %s", (pending_reply_id,))
            con.commit()

            await update.callback_query.answer("❌ Reply rejected!")
            await update.callback_query.edit_message_text(
                f"❌ REJECTED REPLY\n\n"
                f"📝 Reply: \"{reply_text}\"\n"
                f"🎯 To Confession: #{confession_id}\n"
                f"👤 Replier: {replier_id}\n\n"
                f"This reply was not approved for delivery."
            )

            # STEALTH MODERATION: Users never know about rejections - they think all replies are delivered instantly
            print(f"❌ Reply rejected for confession #{confession_id} - confessor will not be notified")

    except Exception as e:
        print(f"❌ Error rejecting reply: {e}")
        await update.callback_query.answer("❌ Error rejecting reply!")

# === ADMIN COMMANDS ===
async def cmd_pending_confessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view all pending confessions with action buttons"""
    if update.effective_user.id not in [1437934486, 647778438]:  # Admin check
        return await update.message.reply_text("❌ Admin only command!")

    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT id, author_id, text, created_at
                FROM pending_confessions 
                ORDER BY created_at ASC
                LIMIT 20
            """)
            pending = cur.fetchall()

            if not pending:
                return await update.message.reply_text("✅ No pending confessions!")

            header = f"📋 PENDING CONFESSIONS ({len(pending)})\n\n"
            await update.message.reply_text(header)

            # Send each confession with action buttons
            for conf_id, author_id, text, created_at in pending:
                keyboard = [
                    [
                        {"text": "✅ Approve", "callback_data": f"approve_conf:{conf_id}"},
                        {"text": "❌ Reject", "callback_data": f"reject_conf:{conf_id}"}
                    ]
                ]

                # Only text confessions - no voice functionality
                # Send text confession with action buttons
                display_text = text[:200] + "..." if len(text) > 200 else text
                message = (
                    f"🔔 CONFESSION #{conf_id}\n\n"
                    f"📝 Text: \"{display_text}\"\n\n"
                    f"👤 Author: {author_id}\n"
                    f"⏰ {created_at}\n\n"
                    f"Choose action:"
                )

                await update.message.reply_text(
                    message,
                    reply_markup={"inline_keyboard": keyboard}
                )

    except Exception as e:
        print(f"❌ Error fetching pending confessions: {e}")
        await update.message.reply_text("❌ Error fetching pending confessions!")

async def cmd_pending_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view all pending replies"""
    if update.effective_user.id not in [1437934486, 647778438]:  # Admin check
        return await update.message.reply_text("❌ Admin only command!")

    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT pr.id, pr.original_confession_id, pr.replier_user_id, pr.reply_text, pr.created_at,
                       SUBSTRING(c.text, 1, 50) as confession_preview
                FROM pending_confession_replies pr
                JOIN confessions c ON pr.original_confession_id = c.id
                ORDER BY pr.created_at ASC
                LIMIT 20
            """)
            pending = cur.fetchall()

            if not pending:
                return await update.message.reply_text("✅ No pending replies!")

            message = f"💬 PENDING REPLIES ({len(pending)})\n\n"

            for reply_id, conf_id, replier_id, reply_text, created_at, conf_preview in pending:
                # Truncate long texts
                display_reply = reply_text[:80] + "..." if len(reply_text) > 80 else reply_text
                display_conf = conf_preview + "..." if len(conf_preview) >= 50 else conf_preview

                message += f"🆔 Reply #{reply_id} | 👤 {replier_id}\n"
                message += f"🎯 To Confession #{conf_id}: \"{display_conf}\"\n"
                message += f"💬 Reply: \"{display_reply}\"\n"
                message += f"⏰ {created_at}\n\n"

                # If message gets too long, send it and start a new one
                if len(message) > 3000:
                    await update.message.reply_text(message)
                    message = ""

            if message:
                await update.message.reply_text(message)

    except Exception as e:
        print(f"❌ Error fetching pending replies: {e}")
        await update.message.reply_text("❌ Error fetching pending replies!")

# === CALLBACK HANDLERS ===
async def handle_confession_callbacks(update, context):
    """Handle approve/reject confession and reply callbacks"""
    query = update.callback_query
    data = query.data

    if data.startswith("approve_conf:"):
        pending_id = int(data.split(":")[1])
        await approve_confession(update, context, pending_id)
    elif data.startswith("reject_conf:"):
        pending_id = int(data.split(":")[1])
        await reject_confession(update, context, pending_id)
    elif data.startswith("approve_reply:"):
        pending_reply_id = int(data.split(":")[1])
        await approve_reply(update, context, pending_reply_id)
    elif data.startswith("reject_reply:"):
        pending_reply_id = int(data.split(":")[1])
        await reject_reply(update, context, pending_reply_id)
    else:
        await query.answer("❌ Unknown action!")

# === REGISTRATION FUNCTION ===
def register_admin_confession_handlers(app):
    """Register all admin confession handlers"""
    from telegram.ext import CallbackQueryHandler, CommandHandler

    # Admin commands
    app.add_handler(CommandHandler("pending", cmd_pending_confessions), group=0)
    app.add_handler(CommandHandler("pending_confessions", cmd_pending_confessions), group=0)
    app.add_handler(CommandHandler("pending_replies", cmd_pending_replies), group=0)

    # Callback handlers for approve/reject buttons (both confessions and replies)
    app.add_handler(CallbackQueryHandler(handle_confession_callbacks, pattern=r"^(approve_conf:|reject_conf:|approve_reply:|reject_reply:)"), group=0)

    # Callback handlers for confession reactions
    app.add_handler(CallbackQueryHandler(handle_confession_reaction_callbacks, pattern=r"^conf_react:"), group=0)

    # New confession menu handlers
    app.add_handler(CallbackQueryHandler(handle_confession_menu_callbacks, pattern=r"^confession_menu:"), group=0)
    app.add_handler(CallbackQueryHandler(handle_confession_type_callbacks, pattern=r"^confess_type:|confession_menu:main"), group=0)

    # Reply button handler
    app.add_handler(CallbackQueryHandler(handle_confession_reply_callbacks, pattern=r"^conf_reply:"), group=0)
    app.add_handler(CallbackQueryHandler(handle_reply_cancel, pattern=r"^reply_cancel"), group=0)

# === /confess flow ===
async def cmd_confess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show confession category selection menu"""
    user_id = update.effective_user.id
    
    # Show category selection menu directly (like 2nd screenshot)
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [
            InlineKeyboardButton("🔥 Spicy Secrets", callback_data="confess_type:spicy"),
            InlineKeyboardButton("💭 Daily Diary", callback_data="confess_type:diary")
        ],
        [
            InlineKeyboardButton("💔 Heartbreak Stories", callback_data="confess_type:heartbreak"),
            InlineKeyboardButton("😈 Guilty Pleasures", callback_data="confess_type:guilty")
        ],
        [
            InlineKeyboardButton("🎯 Life Goals", callback_data="confess_type:goals"),
            InlineKeyboardButton("💫 Random Thoughts", callback_data="confess_type:random")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="confession_menu:main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = """📝 **CHOOSE YOUR CONFESSION MOOD** 📝

🔥 **Spicy Secrets** - Wild confessions & forbidden thoughts
💭 **Daily Diary** - How was your day? Share everything!
💔 **Heartbreak Stories** - Love, loss, and emotional moments
😈 **Guilty Pleasures** - Fun secrets & embarrassing moments
🎯 **Life Goals** - Dreams, ambitions, and future plans
💫 **Random Thoughts** - Anything floating in your mind

💡 **Choose a category that matches your mood!**"""

    await update.message.reply_text(message, reply_markup=reply_markup)

# === CONFESSION MENU HANDLERS ===
async def handle_confession_menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 3-button confession menu callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "confession_menu:confess":
        await show_confess_categories(update, context, user_id)
    elif data == "confession_menu:stats":
        await show_my_stats(update, context, user_id)
    elif data == "confession_menu:leaderboard":
        await show_leaderboard(update, context, user_id)
    elif data == "confession_menu:main":
        # Back to main menu
        await show_main_confession_menu(update, context, user_id)

async def show_confess_categories(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show mood-based confession categories"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = [
        [
            InlineKeyboardButton("🔥 Spicy Secrets", callback_data="confess_type:spicy"),
            InlineKeyboardButton("💭 Daily Diary", callback_data="confess_type:diary")
        ],
        [
            InlineKeyboardButton("💔 Heartbreak Stories", callback_data="confess_type:heartbreak"),
            InlineKeyboardButton("😈 Guilty Pleasures", callback_data="confess_type:guilty")
        ],
        [
            InlineKeyboardButton("🎯 Life Goals", callback_data="confess_type:goals"),
            InlineKeyboardButton("💫 Random Thoughts", callback_data="confess_type:random")
        ],
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="confession_menu:main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = """📝 **CHOOSE YOUR CONFESSION MOOD** 📝

🔥 **Spicy Secrets** - Wild confessions & forbidden thoughts
💭 **Daily Diary** - How was your day? Share everything!
💔 **Heartbreak Stories** - Love, loss, and emotional moments
😈 **Guilty Pleasures** - Fun secrets & embarrassing moments
🎯 **Life Goals** - Dreams, ambitions, and future plans
💫 **Random Thoughts** - Anything floating in your mind

💡 **Choose a category that matches your mood!**"""

    await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

async def show_my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show personal stats dashboard"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    user_stats = get_cached_user_stats(user_id)  # Performance optimized
    leaderboard = get_weekly_leaderboard(limit=10)

    # Find user's position in leaderboard
    user_rank = "Not ranked yet"
    for i, (uid, conf_count, reactions) in enumerate(leaderboard['best_confessors']):
        if uid == user_id:
            user_rank = f"#{i+1}"
            break

    keyboard = [
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="confession_menu:main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = f"""📊 **YOUR CONFESSION STATS** 📊

🏠 **Your Anonymous Journey:**
• 🔥 Current streak: {user_stats['current_streak']} days
• 📝 This week: {user_stats['weekly_confessions']} confessions sent
• ❤️ Total reactions: {user_stats['total_reactions']} 
• 💬 Replies received: {user_stats['total_replies']}
• 🏆 Best Confessor Rank: {user_rank}

📈 **All Time Stats:**
• 🎯 Total confessions: {user_stats['total_confessions']} {get_confession_badge(user_stats['total_confessions'])}
• 🏅 Longest streak: {user_stats['longest_streak']} days {get_streak_badge(user_stats['longest_streak'])}
• ⭐ Confessor score: {user_stats['confessor_score']} {get_score_badge(user_stats['confessor_score'])}

{get_user_title_badge(user_stats)}

💡 **Tips to improve:**
• Confess daily to build your streak
• Write engaging stories to get more reactions
• Reply to others to build community

🎁 **Rewards:** Most liked confession each week gets 50 coins!"""

    await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show weekly leaderboard with rankings"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    leaderboard = get_weekly_leaderboard(limit=5)
    activity = get_live_activity_stats()

    keyboard = [
        [
            InlineKeyboardButton("🔙 Back to Menu", callback_data="confession_menu:main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = """🏆 **WEEKLY LEADERBOARD** 🏆

👑 **BEST CONFESSORS (This Week):**"""

    # Add top confessors
    if leaderboard['best_confessors']:
        for i, (uid, conf_count, reactions) in enumerate(leaderboard['best_confessors'][:3]):
            medals = ["🥇", "🥈", "🥉"]
            message += f"\n{medals[i]} Anonymous_{str(uid)[-3:]}: {conf_count} confessions, {reactions} ❤️"
    else:
        message += "\n📝 No confessions this week yet - be the first!"

    message += "\n\n💖 **MOST LIKED CONFESSIONS:**"

    # Add most liked confessions
    if leaderboard['most_liked']:
        for i, (author_id, text, reaction_count) in enumerate(leaderboard['most_liked'][:3]):
            medals = ["🥇", "🥈", "🥉"]
            short_text = text[:45] + "..." if len(text) > 45 else text
            message += f'\n{medals[i]} "{short_text}" ({reaction_count} ❤️)'
    else:
        message += "\n💫 No confessions with reactions yet - yours could be first!"

    message += f"""

⚡ **LIVE ACTIVITY:**
• {activity['active_players']} people sharing their hearts
• {activity['confessions_today']} confessions sent today
• {activity['replies_today']} supportive replies given  
• {activity['reactions_today']} reactions shared
• Last confession: just now

🎁 **Weekly Prize:** Most liked confession gets 50 coins!
🔥 Fight for the top spot and become the confession champion!"""

    await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

async def handle_confession_type_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confession type selection and back to main menu"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "confession_menu:main":
        # Back to main menu
        await show_main_confession_menu(update, context, user_id)
    elif data.startswith("confess_type:"):
        confession_type = data.split(":")[1]
        await start_confession_flow(update, context, user_id, confession_type)

async def show_main_confession_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show the main 3-button confession menu"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = [
        [
            InlineKeyboardButton("📝 Confess", callback_data="confession_menu:confess"),
            InlineKeyboardButton("📊 My Stats", callback_data="confession_menu:stats")
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="confession_menu:leaderboard")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Get quick stats for the header
    user_stats = get_cached_user_stats(user_id)  # Performance optimized
    activity = get_live_activity_stats()

    message = f"""🏠 **YOUR ANONYMOUS HOME** 🏠
📖 Welcome to your safe space for secrets & daily diary!

🔥 **LIVE NOW:**
• {activity['active_players']} people sharing their hearts
• {activity['confessions_today']} stories shared today
• Your current streak: {user_stats['current_streak']} days

💫 **What would you like to do?**
Choose below to confess, check your stats, or see the leaderboard!"""

    await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

async def handle_confession_reply_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reply button clicks - start anonymous reply flow"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    try:
        confession_id = int(query.data.split(":")[1])
    except (IndexError, ValueError):
        return # Malformed callback data

    # Fix: Set proper state and flags for reply text capture
    set_state(context, "confession_reply", "text", ttl_minutes=5)
    context.user_data["awaiting_confession_reply_text"] = True
    context.user_data["conf_reply_target_id"] = confession_id

    await query.message.reply_text(
        "💬 **ANONYMOUS REPLY** 💬\n\n"
        "✨ *How it works:*\n"
        "• Your identity stays secret\n"
        "• Confessor will see your message\n"
        "• You both can continue anonymously\n\n"
        "📝 **Type your supportive message below:**",
        parse_mode="Markdown",
        reply_markup=make_cancel_kb(),
    )

async def save_confession_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, confession_id: int, reply_text: str):
    """Save anonymous reply to confession with admin approval"""
    user_id = update.effective_user.id

    try:
        def save_reply_db_transaction(confession_id, user_id, reply_text):
            with _conn() as con, con.cursor() as cur:
                cur.execute("""
                    INSERT INTO pending_confession_replies (original_confession_id, replier_user_id, reply_text) 
                    VALUES (%s, %s, %s) RETURNING id
                """, (confession_id, user_id, reply_text))

                pending_reply_id = cur.fetchone()[0]
                con.commit()
                return pending_reply_id
        
        pending_reply_id = await run_db(save_reply_db_transaction, confession_id, user_id, reply_text)
        
        # Notify admin for approval
        await notify_admin_new_reply(context, pending_reply_id, confession_id, reply_text, user_id)

        success_message = """✅ **ANONYMOUS REPLY SENT!**

💫 Your supportive message has been delivered anonymously.

🎭 You've helped someone today!

🏆 This reply counts toward your 'Reply Master' ranking!
🌟 Keep spreading kindness in the community!"""

        await update.message.reply_text(success_message)

    except Exception as e:
        print(f"❌ Failed to save confession reply: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again.")

# Handle cancel reply button
async def handle_reply_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel reply button"""
    query = update.callback_query
    await query.answer()

    # Clear reply state
    context.user_data.pop("awaiting_confession_reply_text", None)
    context.user_data.pop("conf_reply_target_id", None)
    clear_state(context) # Ensure state is cleared properly

    await query.message.reply_text("❌ Reply cancelled. You can always reply later!")

async def start_confession_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, confession_type: str):
    """Start the confession writing flow based on selected type"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # Use text framework to claim confession input (prevents collision with verification)
    if not await claim_or_reject(update, context, "confession", "text", ttl_minutes=3):
        return

    context.user_data["conf.type"] = confession_type
    context.user_data["conf.state"] = "awaiting"

    # Confession type prompts
    type_prompts = {
        "spicy": {
            "title": "🔥 SPICY SECRETS",
            "prompt": "Share your wildest thoughts, forbidden desires, or steamy confessions. No judgment here - let it all out!",
            "examples": ["A secret attraction", "Something you've always wanted to try", "A wild fantasy"]
        },
        "diary": {
            "title": "💭 DAILY DIARY",
            "prompt": "How was your day? Share everything - good moments, bad moments, feelings, thoughts, interactions with people!",
            "examples": ["How you really felt today", "Something special that happened", "A conversation that mattered"]
        },
        "heartbreak": {
            "title": "💔 HEARTBREAK STORIES",
            "prompt": "Share your stories of love, loss, heartbreak, or emotional moments. Your feelings are valid and understood here.",
            "examples": ["A lost love", "Unrequited feelings", "Family relationship struggles"]
        },
        "guilty": {
            "title": "😈 GUILTY PLEASURES",
            "prompt": "Share your embarrassing moments, guilty pleasures, or fun secrets that make you smile (or cringe)!",
            "examples": ["Something embarrassing you did", "A secret hobby", "A guilty pleasure show/music"]
        },
        "goals": {
            "title": "🎯 LIFE GOALS",
            "prompt": "Share your dreams, ambitions, fears about the future, or goals you're working towards. What drives you?",
            "examples": ["A dream you're chasing", "Something you're afraid to try", "Where you see yourself in 5 years"]
        },
        "random": {
            "title": "💫 RANDOM THOUGHTS",
            "prompt": "Share anything floating in your mind - random observations, shower thoughts, weird ideas, or just stream of consciousness!",
            "examples": ["A random realization", "Something that's bothering you", "A weird thought you had"]
        }
    }

    selected = type_prompts.get(confession_type, type_prompts["random"])

    keyboard = [
        [
            InlineKeyboardButton("🔙 Back to Categories", callback_data="confession_menu:confess")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = f"""📝 **{selected['title']}** 📝

{selected['prompt']}

💡 **Some ideas to get you started:**
• {selected['examples'][0]}
• {selected['examples'][1]}  
• {selected['examples'][2]}

✨ **Just start typing your confession below!**
📝 **Text:** Type your confession message

Your message will be completely anonymous and sent to a random person who will react with understanding and support."""

    await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

@requires_state("confession", "text")
async def on_confession_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if not txt:
        return await update.message.reply_text("❌ Empty confession. Try again.")

    user_id = update.effective_user.id

    try:
        # 📝 ADMIN APPROVAL SYSTEM: Save to pending table first
        with _conn() as con, con.cursor() as cur:
            cur.execute(
                "INSERT INTO pending_confessions (author_id, text) VALUES (%s,%s) RETURNING id",
                (user_id, txt)
            )
            pending_id = cur.fetchone()[0]
            con.commit()

            # 🔔 Notify admin for approval
            await notify_admin_new_confession(context, pending_id, txt, user_id)

    except Exception as e:
        print(f"❌ Failed to save pending confession: {e}")
        return await update.message.reply_text("❌ Something went wrong. Please try again.")

        # Queue stats update (batch processing for performance)
    queue_stats_update(user_id, 'confession_submitted')

    # Get cached stats for feedback (performance optimized)
    updated_stats = get_cached_user_stats(user_id)

    # Build engaging success message with progress
    success_message = f"""🎯 CONFESSION SENT SUCCESSFULLY!

📈 YOUR INSTANT PROGRESS:
✅ Weekly count: {updated_stats['weekly_confessions']} confessions (+1)
🔥 Streak continues: {updated_stats['current_streak']} days"""

    # Add achievement notifications with visual badges
    if updated_stats['current_streak'] == 7:
        success_message += "\n🔥⚡🔥 Achievement unlocked: 'Week Warrior' 👑 badge!"
    elif updated_stats['current_streak'] == 3:
        success_message += "\n🎉✨ Achievement unlocked: 'Streak Starter' 🏅 badge!"
    elif updated_stats['total_confessions'] == 1:
        success_message += "\n🌟💫 Welcome to Confession Roulette! First confession sent! 🎖️"
    elif updated_stats['total_confessions'] == 10:
        success_message += "\n🏆👑🏆 Achievement unlocked: 'Confession Master' 💎 badge!"
    elif updated_stats['total_confessions'] == 50:
        success_message += "\n🔥💎🔥 Achievement unlocked: 'Confession Legend' ⚡ badge!"
    elif updated_stats['current_streak'] == 14:
        success_message += "\n🔥🔥🔥 Achievement unlocked: 'Fortnight Fire' 🌟 badge!"
    elif updated_stats['current_streak'] == 30:
        success_message += "\n💎⚡💎 LEGENDARY! 'Monthly Master' 👑💎 badge!"

    success_message += f"""

💫 WHAT HAPPENS NEXT:
• Your confession reaches someone random in 30 minutes
• They can send you ONE anonymous reply
• You'll get notified of any reactions & replies instantly
• Keep your streak alive for exclusive rewards!

🎁 UPCOMING STREAK REWARDS:"""

    # Show next rewards based on current streak
    if updated_stats['current_streak'] < 7:
        success_message += f"\n• {7 - updated_stats['current_streak']} days: 'Week Master' badge + profile glow"
    if updated_stats['current_streak'] < 10:
        success_message += f"\n• {10 - updated_stats['current_streak']} days: Premium spotlight feature (10x reach)"
    if updated_stats['current_streak'] < 30:
        success_message += f"\n• {30 - updated_stats['current_streak']} days: 'Confession Legend' title + special powers"

    success_message += f"""

💭 "Your vulnerability is your strength. Someone needs to hear this tonight."
🔔 Stay tuned for reactions and anonymous replies!"""

    # Send success message and schedule auto-deletion after 45 seconds
    sent_message = await update.message.reply_text(success_message)
    
    # Schedule automatic deletion after 45 seconds
    import asyncio
    async def delete_message():
        try:
            await asyncio.sleep(45)
            await context.bot.delete_message(
                chat_id=sent_message.chat_id,
                message_id=sent_message.message_id
            )
        except Exception as e:
            # Ignore errors (message might already be deleted by user)
            pass
    
    # Create background task for deletion
    asyncio.create_task(delete_message())
    
    clear_state(context)

async def on_confession_reply_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reply text input when user is in reply state"""
    # Only capture when reply state is claimed
    if not context.user_data.get("awaiting_confession_reply_text"):
        return

    txt = (update.message.text or "").strip()
    if not txt:
        return await update.message.reply_text("❌ Empty reply. Try again.")

    uid = update.effective_user.id if update.effective_user else 0
    conf_id = context.user_data.get("conf_reply_target_id")
    if not conf_id:
        # safety: clear & exit
        clear_state(context)
        context.user_data.pop("awaiting_confession_reply_text", None)
        return await update.message.reply_text("⚠️ No confession in context. Tap Reply again.")

    # Save reply to pending table for admin approval
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                INSERT INTO pending_confession_replies (original_confession_id, replier_user_id, reply_text)
                VALUES (%s, %s, %s) RETURNING id
            """, (conf_id, uid, txt))

            pending_reply_id = cur.fetchone()[0]
            con.commit()

            # Notify admin for approval
            await notify_admin_new_reply(context, pending_reply_id, conf_id, txt, uid)
    except Exception as e:
        print(f"[confession] save reply err: {e}")
        return await update.message.reply_text("❌ Could not save reply, try again.")

    # NOTE: Confessor will only be notified after admin approval - no immediate notification
    # Removed immediate notification to fix dual notification issue

    # Send reply confirmation with auto-delete after 5 seconds
    reply_msg = await update.message.reply_text("✅ Reply sent anonymously!")
    
    # Schedule message deletion after 5 seconds
    async def delete_reply_after_delay():
        await asyncio.sleep(5)
        try:
            await context.bot.delete_message(reply_msg.chat.id, reply_msg.message_id)
        except Exception:
            pass
    asyncio.create_task(delete_reply_after_delay())

    # clear state/flags
    clear_state(context)
    context.user_data.pop("awaiting_confession_reply_text", None)
    context.user_data.pop("conf_reply_target_id", None)

# NOTE: Voice functionality completely removed from confession system to prevent verification issues

def get_confession_badge(total_confessions: int) -> str:
    """Get visual badge based on total confessions"""
    if total_confessions >= 100:
        return "💎⚡💎"  # Diamond legend
    elif total_confessions >= 50:
        return "🔥💎🔥"  # Fire diamond
    elif total_confessions >= 25:
        return "👑🏆"    # Crown trophy
    elif total_confessions >= 10:
        return "🏆💎"    # Trophy diamond
    elif total_confessions >= 5:
        return "🏅✨"    # Medal sparkle
    elif total_confessions >= 1:
        return "🎖️"     # First badge
    else:
        return ""

def get_streak_badge(streak_days: int) -> str:
    """Get visual badge based on streak length"""
    if streak_days >= 30:
        return "🔥💎⚡"  # Ultimate fire
    elif streak_days >= 14:
        return "🔥🔥🔥"  # Triple fire
    elif streak_days >= 7:
        return "🔥⚡"    # Fire bolt
    elif streak_days >= 3:
        return "🔥"      # Single fire
    elif streak_days >= 1:
        return "✨"      # Sparkle
    else:
        return ""

def get_score_badge(score: int) -> str:
    """Get visual badge based on confessor score"""
    if score >= 1000:
        return "👑💎⚡"  # Royal diamond
    elif score >= 500:
        return "👑🏆"    # Royal trophy
    elif score >= 100:
        return "🏆✨"    # Trophy sparkle
    elif score >= 50:
        return "🏅"      # Medal
    else:
        return ""

def get_user_title_badge(stats: dict) -> str:
    """Get user title based on achievements"""
    total = stats.get('total_confessions', 0)
    streak = stats.get('current_streak', 0) or stats.get('longest_streak', 0)
    score = stats.get('confessor_score', 0)

    if total >= 100 and streak >= 30:
        return "🌟 **YOUR TITLE:** 💎 Confession Legend 💎 🌟"
    elif total >= 50 and streak >= 14:
        return "🔥 **YOUR TITLE:** ⚡ Streak Master ⚡ 🔥"
    elif total >= 25:
        return "👑 **YOUR TITLE:** 🏆 Confession Champion 🏆 👑"
    elif total >= 10:
        return "🏅 **YOUR TITLE:** ✨ Confession Warrior ✨ 🏅"
    elif total >= 5:
        return "🎖️ **YOUR TITLE:** 💫 Rising Confessor 💫 🎖️"
    elif total >= 1:
        return "✨ **YOUR TITLE:** 💫 New Confessor 💫 ✨"
    else:
        return "🌱 **YOUR TITLE:** 🎯 Confession Rookie 🎯 🌱"

# === PERFORMANCE OPTIMIZATION: BATCH STATS PROCESSING ===

# In-memory stats update queue for batch processing
stats_update_queue = []
stats_cache = {}
last_cache_refresh = {}

def queue_stats_update(user_id: int, action_type: str):
    """Queue stats update for batch processing (performance optimization)"""
    import time
    stats_update_queue.append({
        'user_id': user_id,
        'action_type': action_type,
        'timestamp': time.time()
    })

    # Process queue if it gets too large (prevent memory bloat)
    if len(stats_update_queue) > 100:
        process_stats_queue_batch()

def get_cached_user_stats(user_id: int) -> dict:
    """Get user stats from cache or fresh calculation (performance optimized)"""
    import time
    current_time = time.time()

    # Check if cache is fresh (refresh every 5 minutes)
    cache_age = current_time - last_cache_refresh.get(user_id, 0)
    if cache_age > 300:  # 5 minutes
        # Refresh cache with current stats
        fresh_stats = get_confession_stats(user_id)
        stats_cache[user_id] = fresh_stats
        last_cache_refresh[user_id] = current_time
        return fresh_stats

    # Return cached stats if available
    if user_id in stats_cache:
        return stats_cache[user_id]

    # Fallback to fresh calculation
    fresh_stats = get_confession_stats(user_id)
    stats_cache[user_id] = fresh_stats
    last_cache_refresh[user_id] = current_time
    return fresh_stats

def process_stats_queue_batch():
    """Process queued stats updates in batch (called periodically)"""
    if not stats_update_queue:
        return

    try:
        # Group updates by user_id for efficiency
        user_updates = {}
        for update in stats_update_queue:
            user_id = update['user_id']
            if user_id not in user_updates:
                user_updates[user_id] = []
            user_updates[user_id].append(update)

        # Process each user's updates
        for user_id, updates in user_updates.items():
            # Count different action types
            confession_count = sum(1 for u in updates if 'confession' in u['action_type'])

            if confession_count > 0:
                # Update database stats
                update_user_confession_stats(user_id)

                # Invalidate cache to force refresh
                if user_id in stats_cache:
                    del stats_cache[user_id]
                if user_id in last_cache_refresh:
                    del last_cache_refresh[user_id]

        # Clear processed queue
        stats_update_queue.clear()

        print(f"📊 Processed stats updates for {len(user_updates)} users")

    except Exception as e:
        print(f"❌ Error processing stats queue: {e}")
        # Clear queue to prevent infinite errors
        stats_update_queue.clear()

async def schedule_batch_stats_processing(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled job to process stats updates every 2 minutes"""
    process_stats_queue_batch()

def get_next_achievement_preview(stats: dict) -> str:
    """Show what achievement is coming next"""
    total = stats.get('total_confessions', 0)
    streak = stats.get('current_streak', 0)

    if total < 5:
        needed = 5 - total
        return f"💫 **NEXT MILESTONE:** {needed} more confessions for 'Rising Confessor' 🎖️ title!"
    elif total < 10:
        needed = 10 - total
        return f"⚡ **NEXT MILESTONE:** {needed} more confessions for 'Confession Warrior' 🏅 title!"
    elif total < 25:
        needed = 25 - total
        return f"🔥 **NEXT MILESTONE:** {needed} more confessions for 'Confession Champion' 👑 title!"
    elif total < 50:
        needed = 50 - total
        return f"💎 **NEXT MILESTONE:** {needed} more confessions for 'Streak Master' ⚡ title!"
    elif total < 100:
        needed = 100 - total
        return f"🌟 **NEXT MILESTONE:** {needed} more confessions for 'Confession Legend' 💎 title!"
    else:
        return "👑 **STATUS:** You've achieved maximum rank! You're a true Confession Legend! 💎"

# NOTE: save_confession_voice_reply function removed - voice functionality disabled

# === Multi-recipient guarantee delivery ===
# Tunables
BATCH_LIMIT        = 2000
CHUNK_SIZE         = 30
CHUNK_PAUSE_SEC    = 0.25
FIRST_PASS_MAX     = 1     # guarantee pass
SECOND_PASS_MAX    = 2     # second pass cap per recipient

def _fetch_sets_single_conn(con):
    """Use ONE connection for all pool queries; ORDER BY drives real-first later."""
    with con.cursor() as cur:
        # today confessors
        cur.execute("""
            SELECT DISTINCT author_id
            FROM confessions
            WHERE created_at::date = CURRENT_DATE AND deleted_at IS NULL
        """)
        today_conf = {int(r[0]) for r in (cur.fetchall() or [])}

        # today touchers (if you have last_seen; else notify=true)
        try:
            cur.execute("""
                SELECT tg_user_id
                FROM users
                WHERE (last_seen::date = CURRENT_DATE OR last_seen IS NULL)
                  AND COALESCE(feed_notify, TRUE)=TRUE
            """)
        except Exception: # Fallback if users table or last_seen column doesn't exist
            cur.execute("""
                SELECT tg_user_id
                FROM users
                WHERE COALESCE(feed_notify, TRUE)=TRUE
            """)
        today_touch = {int(r[0]) for r in (cur.fetchall() or [])}

        # fallback 48h confessors
        cur.execute("""
            SELECT DISTINCT author_id
            FROM confessions
            WHERE created_at >= NOW() - INTERVAL '48 hours' AND deleted_at IS NULL
        """)
        fallback_48 = {int(r[0]) for r in (cur.fetchall() or [])}

    return today_conf, today_touch, fallback_48

async def deliver_confessions_batch(context: ContextTypes.DEFAULT_TYPE):
    """
    Fair, scale delivery on ONE DB connection with retry:
      - pending confs (real-first): ORDER BY system_seed ASC, created_at ASC
      - pools from same conn
      - first pass (guarantee): confessors get >=1
      - second pass: touchers, then 48h pool
      - chunked sends + DB mark delivered
    """
    # --- DB open with retry (handles TLS close) ---
    for try_db in range(2):  # one reconnect attempt
        try:
            with _conn() as con:
                # PENDING (real first)
                with con.cursor() as cur:
                    cur.execute("""
                        SELECT id, author_id, text
                        FROM confessions
                        WHERE delivered = FALSE AND deleted_at IS NULL
                          AND created_at >= NOW() - INTERVAL '48 hours'
                        ORDER BY system_seed ASC, created_at ASC
                        LIMIT %s
                    """, (BATCH_LIMIT,))
                    confs = cur.fetchall() or []
                if not confs:
                    print("[confession] nothing to deliver");  return

                today_conf, today_touch, fallback_48 = _fetch_sets_single_conn(con)

                # widen pool in tiny test to include testers
                base_union = (today_conf | today_touch | fallback_48)
                if len(base_union) < 3:
                    base_union |= TESTERS
                    print(f"[confession] 🧪 Added testers, pool size: {len(base_union)}")

                per_recipient = {}
                recent_pairs  = set()
                assignments   = []

                def _pick(author: int, pool: set[int], cap: int):
                    cand = set(pool)
                    cand.discard(int(author))
                    if not cand: return None
                    ordered = sorted(cand, key=lambda r: per_recipient.get(r, 0))
                    for r in ordered:
                        if per_recipient.get(r, 0) < cap and (author, r) not in recent_pairs:
                            return r
                    return None

                # FIRST PASS: guarantee for confessors
                for cid, author, text in confs:
                    if int(author) not in today_conf:
                        continue
                    r = _pick(author, base_union, FIRST_PASS_MAX)
                    if r is None:  continue
                    assignments.append((int(cid), int(author), str(text), int(r)))
                    per_recipient[r] = per_recipient.get(r, 0) + 1
                    recent_pairs.add((int(author), int(r)))

                # SECOND PASS: fill remaining
                assigned_ids = {a[0] for a in assignments}
                remaining = [(int(cid), int(author), str(text)) for (cid, author, text) in confs
                             if int(cid) not in assigned_ids]
                for cid, author, text in remaining:
                    r = _pick(author, base_union, SECOND_PASS_MAX)
                    if r is None:  continue
                    assignments.append((cid, int(author), text, int(r)))
                    per_recipient[r] = per_recipient.get(r, 0) + 1
                    recent_pairs.add((int(author), int(r)))

                if not assignments:
                    print("[confession] no eligible recipients this tick");  return

                print(f"[confession] 📤 Ready to send {len(assignments)} confessions to {len(per_recipient)} recipients")

                # SEND in chunks + mark delivered (same conn reused)
                sent = 0
                for i in range(0, len(assignments), CHUNK_SIZE):
                    chunk = assignments[i:i+CHUNK_SIZE]
                    for cid, author, text, recipient in chunk:
                        # Check round lock to prevent double delivery
                        if not _try_mark_round_delivery(recipient):
                            print(f"[confession] 🔒 User {recipient} already got confession this round, skipping")
                            continue
                        # Enhanced confession message with reply option
                        msg = f"""🔔 SOMEONE NEEDS YOUR SUPPORT!

💭 Anonymous confession:
"{text}"

💬 Send them an anonymous supportive reply?
Type /reply_{cid} followed by your message

❤️ React: ❤️ 😂 😮 😈 🔥 💔 🤗

⚠️ You can only reply once per confession
🌟 Your kindness could change someone's day"""
                        ok = await _safe_send(context.bot, recipient, msg, retries=3)
                        if not ok:
                            print(f"[confession] 📧❌ send fail (after retries) cid={cid} -> {recipient}")
                            continue
                        try:
                            with con.cursor() as cur:
                                cur.execute("""
                                  UPDATE confessions
                                     SET delivered = TRUE,
                                         delivered_to = %s,
                                         delivered_at = NOW()
                                   WHERE id = %s
                                """, (recipient, cid))
                            con.commit()
                            sent += 1
                            print(f"[confession] ✅ cid={cid} -> user_{recipient}")
                        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                            print(f"[confession] 🗄️❌ DB mark failed, will retry next tick: {e}")
                    await asyncio.sleep(CHUNK_PAUSE_SEC)

                print(f"[confession] 🎯 delivered={sent} rows; recipients_served={len(per_recipient)}")
                return

        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            print(f"[confession] 🔌❌ DB connection error (try {try_db+1}): {e}")
            await asyncio.sleep(0.7)
            continue  # reconnect once and retry

        except Exception as e:
            print(f"[confession] 🚨 exception: {e}")
            return

    print(f"[confession] 💥 Failed after all DB retry attempts")

async def handle_confession_reaction_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confession reaction button callbacks"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    try:
        # Parse callback data: conf_react:confession_id:reaction_type
        if callback_data.startswith("conf_react:"):
            parts = callback_data.split(":")
            if len(parts) == 3:
                confession_id = int(parts[1])
                reaction_type = parts[2]

                # Add reaction using existing function
                success, author_id = add_confession_reaction(confession_id, user_id, reaction_type)

                if success and author_id:
                    # Map reaction types to emojis
                    emoji_map = {"love": "❤️", "laugh": "😂", "wow": "😮", "sad": "😢", "angry": "😠", "fire": "🔥", "clap": "👏"}
                    reaction_emoji = emoji_map.get(reaction_type, "❤️")

                    # Notify user of successful reaction with auto-delete after 15 seconds
                    reaction_msg = f"✅ Reacted with {reaction_emoji} to confession #{confession_id}!\n\n" \
                                   f"💭 Your reaction is anonymous but meaningful...\n" \
                                   f"🔄 Share your own secret: /confess"
                    asyncio.create_task(send_and_delete(
                        context.bot, user_id, reaction_msg, delay=15
                    ))

                    # Notify original confessor
                    await notify_confessor_about_activity(
                        context,
                        author_id,
                        "reaction",
                        {'reaction_type': reaction_emoji, 'confession_id': confession_id}
                    )

                    print(f"✅ User {user_id} reacted {reaction_type} to confession #{confession_id}")

                else:
                    await _safe_send(
                        context.bot, user_id,
                        "❌ Failed to add reaction. You may have already reacted to this confession."
                    )

    except Exception as e:
        print(f"❌ Error handling confession reaction: {e}")
        await _safe_send(
            context.bot, user_id,
            "❌ Something went wrong with your reaction. Please try again."
        )

def insert_seed_confessions():
    """Insert 30 seed confessions for the confession roulette feature"""
    seed_confessions = [
        (8482725798, 'Kabhi kabhi sochti hoon koi mujhe bas ek baar pyaar se gale lagaye aur bole "main hoon na"… shayad mujhe bas itna hi chahiye life me ❤️'),
        (647778438, 'Rain me bheegna mujhe hamesha pasand tha, but jab ek baar kisi ne deliberately umbrella close karke bola "let\'s get wet together", tab laga filmy romance real hai 🌧️🔥'),
        (1437934486, 'Main tough dikhne ki koshish karta hoon, par ek soft touch aur ek warm hug mujhe turant tod deta hai… bas koi ho jo mujhe bina judge kiye samajh le 🤗'),
        (8482725798, 'Ek baar truth or dare me dare mila kiss karne ka, aur wo life ka best moment tha… kyunki secretly maine hamesha usi ka wait kiya tha 😈💋'),
        (647778438, 'Log mujhe innocent kehte hain, par sach ye hai ki meri mind me bohot naughty thoughts hote hain… bas ek partner chahiye jo unhe explore kar sake 😉🔥'),
        (1437934486, 'Kya tumhe kabhi kisi ki aankhon me dekh ke lagta hai ki time ruk gaya? Mujhe wo feel ek baar hua tha aur abhi tak us nazar ko bhool nahi paya 👀💞'),
        (8482725798, 'Mera dil ek hi cheez pe weak ho jata hai — public me secretly hand hold karna… wo single touch pura din yaad rehta hai 🫦'),
        (647778438, 'Mujhe secretly pasand hai jab koi possessive style me bole "you\'re mine"… wo line mujhe safe aur desired feel karati hai 😳❤️'),
        (1437934486, 'Raat ke 2 baje ka ek "you up?" message hi sabse bada trap hai… us time pe sabse asli secrets nikalte hain 🌌😏'),
        (8482725798, 'Koi accept kare ya na kare, mujhe neck kisses aur ear whispers pe control hi nahi rehta… bas guard down ho jata hai 🫠🔥'),
        (647778438, 'Kabhi kabhi sochta hoon ki agar koi bas mere forehead pe ek gentle kiss kare, to shayad main uske saath forever ho jaun 💫'),
        (1437934486, 'Public me affection dekhna logon ko ajeeb lagta hai, but mujhe usme hi thrill hai… ek baar kisi ne crowd me haath pakda tha aur wo feel unforgettable hai 👀'),
        (8482725798, 'Maine ek baar kisi ko bas aankhon se "I like you" bola tha… aur usne samajh bhi liya. Us din realize hua ki feelings words ke bina bhi express ho sakti hain 👀💌'),
        (647778438, 'Maine ek baar kisi ko bas aankhon se "I like you" bola tha… aur usne samajh bhi liya. Us din realize hua ki feelings words ke bina bhi express ho sakti hain 👀💌'),
        (1437934486, 'Maine ek baar kisi ko bas aankhon se "I like you" bola tha… aur usne samajh bhi liya. Us din realize hua ki feelings words ke bina bhi express ho sakti hain 👀💌'),
        (8482725798, 'Mera sapna hai kisi ke sath rooftop pe baith kar city lights dekhna aur bas chup rehna… silence bhi kabhi kabhi sabse loud hota hai 🌃'),
        (647778438, 'Ek baar kisi ne mujhe tease kiya aur main blush se control hi nahi kar paayi… us din samjha blush bhi addiction ban sakta hai 😳'),
        (1437934486, 'Mujhe genuinely pasand hai jab koi mujhe care karta hai little things me… jaise "khana khaya?" ya "pani piya?" 🥺'),
        (8482725798, 'Maine ek baar kisi ko apna crush bolne hi wala tha, aur tabhi usne bola "tum mere best dost ho"… tab se confess karne me darr lagta hai 💔'),
        (647778438, 'Kabhi kabhi ek random stranger ki smile dil chura leti hai… aur main pura din usi ke bare me sochta/ti rehta hoon 🙂'),
        (1437934486, 'Sometimes I just want to disappear with someone for a weekend… no phones, no social media, sirf hum aur vibes 🌌🔥'),
        (8482725798, 'Mujhe confess karna hai ki kabhi kabhi main apne crush ki insta story 20 baar dekh leti hoon, bas ek glimpse ke liye 😅'),
        (647778438, 'Ek baar kisi ne mujhe tease kiya aur main blush se control hi nahi kar paayi… us din samjha blush bhi addiction ban sakta hai 😳'),
        (1437934486, 'Sometimes I just want someone to sit with me in silence and hold my hand… aur bas wohi enough hai ❤️'),
        (8482725798, 'Mujhe confess karna hai ki kabhi kabhi main apne crush ki insta story 20 baar dekh leti hoon, bas ek glimpse ke liye 😅'),
        (647778438, 'Ek baar kisi ne mujhe tease kiya aur main blush se control hi nahi kar paayi… us din samjha blush bhi addiction ban sakta hai 😳'),
        (1437934486, 'Sometimes I just want someone to sit with me in silence and hold my hand… aur bas wohi enough hai ❤️'),
        (8482725798, 'Mujhe confess karna hai ki kabhi kabhi main apne crush ki insta story 20 baar dekh leti hoon, bas ek glimpse ke liye 😅'),
        (647778438, 'Ek baar kisi ne mujhe tease kiya aur main blush se control hi nahi kar paayi… us din samjha blush bhi addiction ban sakta hai 😳'),
        (1437934486, 'Sometimes I just want someone to sit with me in silence and hold my hand… aur bas wohi enough hai ❤️'),
    ]

    try:
        with _conn() as con, con.cursor() as cur:
            # Check if seed confessions already exist
            cur.execute("SELECT COUNT(*) FROM confessions WHERE system_seed = TRUE")
            existing_count = cur.fetchone()[0]

            if existing_count > 0:
                print(f"[confession] {existing_count} seed confessions already exist, skipping insert")
                return

            # Insert seed confessions
            for author_id, text in seed_confessions:
                cur.execute("""
                    INSERT INTO confessions (author_id, text, created_at, delivered, system_seed)
                    VALUES (%s, %s, NOW(), FALSE, TRUE)
                """, (author_id, text))

            con.commit()
            print(f"[confession] Inserted {len(seed_confessions)} seed confessions")

    except Exception as e:
        print(f"[confession] Failed to insert seed confessions: {e}")

# === ANONYMOUS REPLY SYSTEM ===
async def cmd_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reply_<confession_id> command for anonymous replies"""
    command_text = update.message.text
    user_id = update.effective_user.id

    try:
        # Extract confession ID from command
        if not command_text.startswith('/reply_'):
            return await update.message.reply_text("❌ Invalid reply command format. Use: /reply_<id> <your message>")

        parts = command_text.split(' ', 1)
        reply_cmd_part = parts[0]

        if not reply_cmd_part.startswith('/reply_'):
             return await update.message.reply_text("❌ Invalid reply command format. Use: /reply_<id> <your message>")

        confession_id_str = reply_cmd_part.replace('/reply_', '')

        if len(parts) == 1: # User just typed /reply_<id> without a message
            return await update.message.reply_text(
                f"💬 SEND ANONYMOUS REPLY\n\n"
                f"Reply to confession #{confession_id_str}:\n"
                f"Type: /reply_{confession_id_str} <your supportive message>\n\n"
                f"💡 Tips for great replies:\n"
                f"• Be supportive and understanding\n"
                f"• Share similar experiences if helpful\n"
                f"• Avoid judgment or criticism\n"
                f"• Keep it anonymous but heartfelt"
            )

        reply_text = parts[1].strip()

        if not confession_id_str.isdigit():
            return await update.message.reply_text("❌ Invalid confession ID.")

        if len(reply_text) < 10:
            return await update.message.reply_text("❌ Reply too short. Please write a meaningful, supportive message (at least 10 characters).")

        confession_id = int(confession_id_str)

        # Check if confession exists and get author
        with _conn() as con, con.cursor() as cur:
            cur.execute("SELECT author_id, text FROM confessions WHERE id = %s AND deleted_at IS NULL", (confession_id,))
            result = cur.fetchone()

            if not result:
                return await update.message.reply_text("❌ Confession not found.")

            author_id, confession_text = result

            if author_id == user_id:
                return await update.message.reply_text("❌ You cannot reply to your own confession.")

        # Submit reply for admin approval
        submit_success, pending_reply_id = submit_reply_for_approval(confession_id, user_id, reply_text)
        if submit_success:
            # Success - make it appear the reply was sent instantly (hide moderation)
            await update.message.reply_text(
                f"✅ ANONYMOUS REPLY SENT!\n\n"
                f"Your supportive message will be delivered after quick review.\n"
                f"💫 You've helped someone today!\n\n"
                f"🏆 This reply counts toward your 'Reply Master' ranking!\n"
                f"🌟 Keep spreading kindness in the community!"
            )
            # NOTE: Confessor will only be notified after admin approval - no immediate notification

            # Notify admin about new pending reply
            await notify_admin_new_reply(context, pending_reply_id, confession_id, reply_text, user_id)

        else:
            await update.message.reply_text(
                "❌ Could not submit reply. You may have already replied to this confession, or there was an error."
            )

    except Exception as e:
        print(f"❌ Reply command error: {e}")
        await update.message.reply_text("❌ Error processing reply. Please try again.")

# Helper function to get confession author
def _get_confession_author(conf_id: int) -> int | None:
    """Get the author ID of a confession"""
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("SELECT author_id FROM confessions WHERE id=%s AND deleted_at IS NULL", (conf_id,))
            row = cur.fetchone()
            return (row[0] if row else None)
    except Exception as e:
        print(f"[confession] author lookup err: {e}")
        return None

def register(app):
    # Ensure table structure is up to date
    ensure_confessions_table()

    # Insert seed confessions on startup
    insert_seed_confessions()

    # Schedule batch stats processing every 2 minutes for performance
    job_queue: JobQueue = app.job_queue
    if job_queue:
        job_queue.run_repeating(schedule_batch_stats_processing, interval=300, first=120)  # Every 5 minutes (reduced from 2 min)
        print("📊 Scheduled batch stats processing for performance optimization")

    app.add_handler(CommandHandler("confess", cmd_confess), group=-1)

    # HIGH priority reply text handler to beat firewall
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, on_confession_reply_text),
        group=-5
    )

    # Confession text handler - TODO: Integrate with text_framework for consistency
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_confession_text), group=-1)
    # NOTE: Voice functionality completely removed to prevent verification issues

    # Anonymous reply system - handle /reply_<id> pattern
    app.add_handler(MessageHandler(filters.Regex(r'^/reply_\d+'), cmd_reply), group=-1)

    # Register all the handlers related to confessions
    register_admin_confession_handlers(app)

    # Handler for the "Reply Back" button from notifications
    app.add_handler(CallbackQueryHandler(start_reply_from_notification, pattern=r"^conf_reply:start:\d+$"), group=-10)

    # Handler for the "Mute This Confession" button
    app.add_handler(CallbackQueryHandler(conf_mute, pattern=r"^conf_mute:\d+$"), group=-10)

    # Register the main confession reaction handler
    app.add_handler(CallbackQueryHandler(handle_confession_reaction_callbacks, pattern=r"^conf_react:"), group=0)

# --- NEW HANDLERS FOR NOTIFICATIONS ---

async def start_reply_from_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Reply Back' button press from a notification to initiate anonymous reply."""
    q = update.callback_query
    await q.answer()
    try:
        conf_id = int((q.data or "").split(":")[2])
    except Exception:
        return # Malformed callback data

    # Claim state for reply capture
    set_state(context, "confession_reply", "text", ttl_minutes=5)
    context.user_data["awaiting_confession_reply_text"] = True
    context.user_data["conf_reply_target_id"] = conf_id

    await q.message.reply_text(
        "💬 <b>Reply anonymously</b>\n\nType your supportive message below:",
        parse_mode="HTML",
        reply_markup=make_cancel_kb()
    )

async def conf_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mutes future notifications for a specific confession."""
    q = update.callback_query
    await q.answer()
    try:
        conf_id = int((q.data or "").split(":")[1])
        uid = q.from_user.id
        with _conn() as con, con.cursor() as cur:
            # Ensure table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS confession_mutes(
                    user_id BIGINT NOT NULL,
                    confession_id BIGINT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY(user_id, confession_id)
                )
            """)
            # Insert mute, do nothing if already exists
            cur.execute(
                "INSERT INTO confession_mutes(user_id, confession_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (uid, conf_id)
            )
            con.commit()
        await q.answer("Muted this confession.", show_alert=True)
    except Exception as e:
        print(f"[confession] mute err: {e}")