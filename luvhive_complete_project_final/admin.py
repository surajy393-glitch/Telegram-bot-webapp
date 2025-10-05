
# admin.py
from __future__ import annotations
from typing import List, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.display import safe_display_name

# --- Admin IDs ---
import os
import logging

log = logging.getLogger(__name__)

def _parse_admins(s: str) -> set[int]:
    out = set()
    # Strip quotes and clean the string first
    clean_s = (s or "").strip().strip('"').strip("'")
    for x in clean_s.replace(",", " ").split():
        if x.isdigit():
            out.add(int(x))
    return out

ADMIN_IDS = _parse_admins(os.getenv("ADMIN_IDS", ""))
if not ADMIN_IDS:
    log.warning("ADMIN_IDS missing! Admin panel will be disabled for security.")
    ADMIN_IDS = set()  # Empty set - no one has admin access

# --- Callback IDs ---
CB_ADMIN         = "ad:root"
CB_AD_STATS      = "ad:stats"
CB_AD_ACTIVE     = "ad:active"
CB_AD_WAITING    = "ad:waiting"
CB_AD_PREM_LIST  = "ad:pl"
CB_AD_GIVE_PREM  = "ad:gp"
CB_AD_REM_PREM   = "ad:rp"
CB_AD_USER_INFO  = "ad:info"
CB_AD_RESET_USER = "ad:reset"
CB_AD_BACKUP     = "ad:backup"
CB_AD_BCAST      = "ad:bcast"

# --- Admin panel UI ---
def admin_title() -> str:
    return "🛠 <b>Admin Panel</b>"

def admin_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📈 Stats", callback_data=CB_AD_STATS),
         InlineKeyboardButton("💬 Active Chats", callback_data=CB_AD_ACTIVE)],
        [InlineKeyboardButton("⏳ Waiting", callback_data=CB_AD_WAITING),
         InlineKeyboardButton("👑 Premium List", callback_data=CB_AD_PREM_LIST)],
        [InlineKeyboardButton("💎 Give Premium", callback_data=CB_AD_GIVE_PREM),
         InlineKeyboardButton("❌ Remove Premium", callback_data=CB_AD_REM_PREM)],
        [InlineKeyboardButton("🔎 User Info", callback_data=CB_AD_USER_INFO),
         InlineKeyboardButton("🧹 Reset User", callback_data=CB_AD_RESET_USER)],
        [InlineKeyboardButton("💾 Backup Data", callback_data=CB_AD_BACKUP),
         InlineKeyboardButton("📣 Broadcast", callback_data=CB_AD_BCAST)],
    ]
    return InlineKeyboardMarkup(rows)

# --- DB helpers ---
try:
    from registration import _conn as _db_conn
except Exception:
    import os, psycopg2
    def _db_conn():
        return psycopg2.connect(os.getenv("DATABASE_URL"))

def q_one(sql: str, args: tuple = ()) -> Optional[tuple]:
    with _db_conn() as con, con.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchone()

def q_all(sql: str, args: tuple = ()) -> List[tuple]:
    with _db_conn() as con, con.cursor() as cur:
        cur.execute(sql, args)
        return cur.fetchall()

def q_exec(sql: str, args: tuple = ()) -> None:
    with _db_conn() as con, con.cursor() as cur:
        cur.execute(sql, args)
        con.commit()   # ensure persistence

# --- Core admin actions ---
def db_stats() -> dict:
    row = q_one("""SELECT
        COUNT(*)::int,
        COALESCE(SUM(CASE WHEN is_premium THEN 1 ELSE 0 END),0)::int,
        COALESCE(SUM(dialogs_today),0)::int,
        COALESCE(SUM(dialogs_total),0)::int,
        COALESCE(SUM(messages_sent),0)::int,
        COALESCE(SUM(messages_recv),0)::int,
        COALESCE(SUM(rating_up),0)::int,
        COALESCE(SUM(rating_down),0)::int
      FROM users;""") or (0,0,0,0,0,0,0,0)
    keys = ["users","premium_users","dialogs_today","dialogs_total",
            "msgs_sent","msgs_recv","rating_up","rating_down"]
    return dict(zip(keys, row))

def premium_users(limit: int = 100) -> List[Tuple[int, str]]:
    sql = """
        SELECT tg_user_id, COALESCE(language,'')
          FROM users
         WHERE COALESCE(is_premium, FALSE) = TRUE
            OR COALESCE(premium_until, TIMESTAMPTZ 'epoch') > NOW()
         ORDER BY id DESC
         LIMIT %s;
    """
    return q_all(sql, (limit,))

def set_premium(tg_id: int, value: bool) -> None:
    """
    Upsert boolean premium flag.
    When turning OFF, also clear premium_until so admin list won't show the user.
    """
    if value:
        q_exec("""
            INSERT INTO users (tg_user_id, is_premium)
            VALUES (%s, TRUE)
            ON CONFLICT (tg_user_id) DO UPDATE
            SET is_premium = TRUE;
        """, (tg_id,))
    else:
        q_exec("""
            INSERT INTO users (tg_user_id, is_premium, premium_until)
            VALUES (%s, FALSE, NULL)
            ON CONFLICT (tg_user_id) DO UPDATE
            SET is_premium = FALSE,
                premium_until = NULL;
        """, (tg_id,))

def user_info(tg_id: int) -> Optional[dict]:
    row = q_one("""SELECT tg_user_id, gender, age, country, city, language,
                          dialogs_total, dialogs_today, messages_sent, messages_recv,
                          rating_up, rating_down, report_count, is_premium
                   FROM users WHERE tg_user_id=%s;""", (tg_id,))
    if not row:
        return None
    keys = ["tg_id","gender","age","country","city","language",
            "dialogs_total","dialogs_today","messages_sent","messages_recv",
            "rating_up","rating_down","report_count","is_premium"]
    return dict(zip(keys, row))

def reset_user_metrics(tg_id: int) -> None:
    """
    Make the user 'fresh' again for registration while preserving premium.
    Clears profile fields, interests and all counters; keeps is_premium intact.
    """
    # preserve premium
    row = q_one("SELECT is_premium FROM users WHERE tg_user_id=%s;", (tg_id,))
    premium_flag = row[0] if row else False

    # clear profile + counters, keep premium
    q_exec("""
        UPDATE users
        SET gender=NULL, age=NULL, country=NULL, city=NULL,
            dialogs_today=0, dialogs_total=0,
            messages_sent=0, messages_recv=0,
            rating_up=0, rating_down=0, report_count=0,
            search_pref='any',
            is_premium=%s
        WHERE tg_user_id=%s;
    """, (premium_flag, tg_id))

    # wipe interests
    q_exec("""
        DELETE FROM user_interests
        WHERE user_id = (SELECT id FROM users WHERE tg_user_id=%s);
    """, (tg_id,))

    # wipe ratings and reports logs
    q_exec("DELETE FROM chat_ratings WHERE rated_user_id=%s OR rater_user_id=%s;", (tg_id, tg_id))
    q_exec("DELETE FROM reports WHERE reported_user_id=%s OR reporter_user_id=%s;", (tg_id, tg_id))

def runtime_counts() -> Tuple[int, int]:
    active = waiting = 0
    try:
        from chat import peers, queue
        active = len(peers)//2
        waiting = len(queue)
    except Exception:
        pass
    return active, waiting

def get_pending_vault_content(limit: int = 20) -> List[dict]:
    """Get pending vault content for admin review"""
    sql = """
        SELECT vc.id, vc.submitter_id, vc.content_text, 
               vc.media_type, vc.file_url, vc.file_id, vc.category_id, vc.created_at,
               COALESCE('User ' || u.tg_user_id::text, 'Unknown User') as submitter_name
        FROM vault_content vc
        LEFT JOIN users u ON vc.submitter_id = u.tg_user_id
        WHERE vc.approval_status = 'pending'
        ORDER BY vc.created_at DESC
        LIMIT %s
    """
    rows = q_all(sql, (limit,))
    
    content_list = []
    for row in rows:
        content_list.append({
            'id': row[0],
            'submitter_id': row[1], 
            'text': row[2],
            'media_type': row[3],
            'file_url': row[4],
            'file_id': row[5],
            'category': row[6],
            'created_at': row[7],
            'submitter_name': row[8] or 'Unknown User'
        })
    
    return content_list

def approve_vault_content(content_id: int) -> bool:
    """Approve vault content submission and notify submitter"""
    try:
        # Get submitter info before approval
        result = q_one("SELECT submitter_id FROM vault_content WHERE id = %s", (content_id,))
        if not result:
            return False
            
        submitter_id = result[0]
        
        # Approve the content
        q_exec("UPDATE vault_content SET approval_status = 'approved' WHERE id = %s", (content_id,))
        
        # Award coin for approved submission
        from handlers.blur_vault import award_submission_coin
        total_coins = award_submission_coin(submitter_id)
        
        # Send approval notification to submitter
        try:
            import asyncio
            from main import app
            
            async def send_approval_notification():
                await app.bot.send_message(
                    submitter_id,
                    f"🎉 **YOUR SUBMISSION WAS APPROVED!** 🎉\n\n"
                    f"✅ Content ID #{content_id} is now live in the vault!\n"
                    f"🎁 **BONUS COIN EARNED:** +1 coin (Total: {total_coins})\n\n"
                    f"💰 **Double Reward:**\n"
                    f"• +1 coin for submission\n"
                    f"• +1 coin for approval\n\n"
                    f"🔥 Your content is now available for others to discover!\n"
                    f"💎 Type /balance to check your coin balance",
                    parse_mode="Markdown"
                )
            
            # Schedule the notification
            if app._running:
                asyncio.create_task(send_approval_notification())
        except Exception as e:
            log.warning(f"Failed to send approval notification to {submitter_id}: {e}")
        
        return True
    except Exception as e:
        log.error(f"Error approving content {content_id}: {e}")
        return False

def delete_vault_content(content_id: int) -> bool:
    """Delete/reject vault content submission"""
    try:
        q_exec("DELETE FROM vault_content WHERE id = %s", (content_id,))
        return True
    except Exception as e:
        log.error(f"Error deleting content {content_id}: {e}")
        return False



# --- DB Health Check ---
async def cmd_dbhealth(update, context):
    """Admin command to check database connectivity"""
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return
    
    try:
        from registration import _conn
        with _conn() as con, con.cursor() as cur:
            cur.execute("SELECT 1;")
            row = cur.fetchone()
        await update.message.reply_text(f"✅ DB OK: {row}")
    except Exception as e:
        await update.message.reply_text(f"❌ DB ERROR: {e.__class__.__name__}: {e}")
