# utils/hybrid_db.py - Hybrid Database Layer with Automatic Fallback
import os
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

log = logging.getLogger("luvbot.hybrid_db")

# Configuration
USE_SUPABASE = os.environ.get("USE_SUPABASE", "false").lower() == "true"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# Import handlers
if USE_SUPABASE and SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        from utils.supabase_db import *
        log.info("✅ Using Supabase database (HTTP-based, no SSL issues)")
        DB_MODE = "supabase"
    except Exception as e:
        log.warning(f"⚠️ Supabase failed, falling back to PostgreSQL: {e}")
        from registration import _conn, DB_URL
        DB_MODE = "postgresql"
else:
    log.info("📦 Using PostgreSQL database")  
    from registration import _conn, DB_URL
    DB_MODE = "postgresql"

# ============ UNIFIED INTERFACE ============

def get_nudge_users_hybrid() -> List[int]:
    """Get users for notifications - ALWAYS includes TESTERS"""
    TESTERS = [8482725798, 647778438, 1437934486]
    
    if DB_MODE == "supabase":
        users = set(get_nudge_users())
    else:
        # PostgreSQL fallback
        try:
            with _conn() as con, con.cursor() as cur:
                cur.execute("SELECT tg_user_id FROM users WHERE COALESCE(feed_notify, TRUE)=TRUE")
                users = set(int(r[0]) for r in (cur.fetchall() or []))
        except Exception as e:
            log.error(f"🚨 PostgreSQL nudge users failed: {e}")
            users = set()
    
    # ALWAYS include TESTERS for guaranteed delivery
    users.update(TESTERS)
    return list(users)

def get_active_user_ids_hybrid() -> List[int]:
    """Get active users - ALWAYS includes TESTERS"""
    TESTERS = [8482725798, 647778438, 1437934486]
    
    if DB_MODE == "supabase":
        users = set(get_active_user_ids())
    else:
        # PostgreSQL fallback
        try:
            with _conn() as con, con.cursor() as cur:
                cur.execute("SELECT tg_user_id FROM users WHERE COALESCE(feed_notify, TRUE)=TRUE")
                users = set(int(r[0]) for r in (cur.fetchall() or []))
        except Exception as e:
            log.error(f"🚨 PostgreSQL active users failed: {e}")
            users = set()
    
    # ALWAYS include TESTERS for guaranteed delivery
    users.update(TESTERS)
    return list(users)

def get_premium_user_ids_hybrid() -> List[int]:
    """Get premium users - works with both DB types"""
    if DB_MODE == "supabase":
        return get_premium_user_ids()
    else:
        # PostgreSQL fallback
        try:
            with _conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT tg_user_id
                    FROM users
                    WHERE COALESCE(is_premium,FALSE)=TRUE
                       OR COALESCE(premium_until, TIMESTAMPTZ 'epoch') > NOW()
                """)
                return [int(r[0]) for r in (cur.fetchall() or [])]
        except Exception as e:
            log.error(f"🚨 PostgreSQL premium users failed: {e}")
            return []

def add_confession_hybrid(author_id: int, text: str) -> bool:
    """Add confession - works with both DB types"""
    if DB_MODE == "supabase":
        return add_confession(author_id, text)
    else:
        # PostgreSQL fallback
        try:
            with _conn() as con, con.cursor() as cur:
                cur.execute("""
                    INSERT INTO confessions (author_id, text, delivered, system_seed, created_at)
                    VALUES (%s, %s, FALSE, FALSE, NOW())
                """, (author_id, text))
                con.commit()
                log.info(f"✅ Confession added for user {author_id} (PostgreSQL)")
                return True
        except Exception as e:
            log.error(f"🚨 PostgreSQL add confession failed: {e}")
            return False

def get_available_confessions_for_user_hybrid(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """ROTATING POOL: Get confessions available for specific user (no repeats)"""
    if DB_MODE == "supabase":
        return get_available_confessions_for_user(user_id, limit)
    else:
        # PostgreSQL with rotating pool logic
        try:
            with _conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT c.id, c.author_id, c.text
                    FROM confessions c
                    WHERE c.author_id != %s
                      AND c.id NOT IN (
                          SELECT cd.confession_id 
                          FROM confession_deliveries cd 
                          WHERE cd.user_id = %s
                      )
                      AND c.created_at >= NOW() - INTERVAL '7 days'
                    ORDER BY c.system_seed DESC, RANDOM()
                    LIMIT %s
                """, (user_id, user_id, limit))
                rows = cur.fetchall() or []
                return [
                    {'id': r[0], 'author_id': r[1], 'text': r[2]}
                    for r in rows
                ]
        except Exception as e:
            log.error(f"🚨 PostgreSQL get available confessions failed: {e}")
            return []

def get_pending_confessions_hybrid(limit: int = 50) -> List[Dict[str, Any]]:
    """DEPRECATED: Use get_available_confessions_for_user_hybrid instead"""
    # Fallback for compatibility - return seed confessions
    try:
        with _conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT id, author_id, text
                FROM confessions
                WHERE system_seed = TRUE
                ORDER BY RANDOM()
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall() or []
            return [
                {'id': r[0], 'author_id': r[1], 'text': r[2]}
                for r in rows
            ]
    except Exception as e:
        log.error(f"🚨 PostgreSQL fallback confessions failed: {e}")
        return []

def track_confession_delivery_hybrid(confession_id: int, user_id: int) -> bool:
    """ROTATING POOL: Track confession delivery without marking as permanently delivered"""
    if DB_MODE == "supabase":
        return track_confession_delivery(confession_id, user_id)
    else:
        # PostgreSQL with delivery tracking
        try:
            with _conn() as con, con.cursor() as cur:
                # Insert into tracking table (prevents repeats to same user)
                cur.execute("""
                    INSERT INTO confession_deliveries (confession_id, user_id, delivered_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (confession_id, user_id) DO NOTHING
                """, (confession_id, user_id))
                con.commit()
                log.info(f"📋 Tracked delivery: confession #{confession_id} → user {user_id}")
                return True
        except Exception as e:
            log.error(f"🚨 PostgreSQL track delivery failed: {e}")
            return False

def mark_confession_delivered_hybrid(confession_id: int, delivered_to: int) -> bool:
    """LEGACY: Use track_confession_delivery_hybrid for rotating pool"""
    # For backward compatibility, just track the delivery
    return track_confession_delivery_hybrid(confession_id, delivered_to)

def is_registered_hybrid(tg_user_id: int) -> bool:
    """Check if user registered - works with both DB types"""
    if DB_MODE == "supabase":
        return is_registered(tg_user_id)
    else:
        # PostgreSQL fallback
        try:
            with _conn() as con, con.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE tg_user_id = %s", (tg_user_id,))
                return cur.fetchone() is not None
        except Exception:
            return False

# ============ STATUS INFO ============
def get_db_status() -> Dict[str, Any]:
    """Get current database status"""
    return {
        "mode": DB_MODE,
        "use_supabase": USE_SUPABASE,
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_ANON_KEY),
        "fallback_available": bool(DB_URL if 'DB_URL' in globals() else False)
    }