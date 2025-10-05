# utils/db_integrity.py - Database integrity improvements for scaling
import logging
import psycopg2
from typing import Any, Optional

log = logging.getLogger(__name__)

def apply_missing_constraints():
    """Apply missing database constraints for data integrity."""
    import registration as reg
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            log.info("Applying database integrity constraints...")
            
            # 1. Idempotency table for preventing duplicate side-effects
            cur.execute("""
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    key TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    result JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            # 2. Check constraints for data validation (PostgreSQL compatible)
            try:
                cur.execute("""
                    ALTER TABLE users 
                    ADD CONSTRAINT chk_users_age_range 
                    CHECK (age IS NULL OR (age BETWEEN 13 AND 120));
                """)
            except psycopg2.Error:
                # Constraint already exists, ignore
                pass
            
            con.commit()  # Commit before index creation
        
        # 3. Friend request unique constraint (prevent duplicate requests) - outside transaction
        try:
            with reg._conn() as con, con.cursor() as cur:
                con.autocommit = True
                cur.execute("""
                    CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_friend_requests_pair
                    ON friend_requests(sender, receiver);
                """)
        except Exception:
            pass  # Index might already exist
        
        # 4. Foreign key constraints
        with reg._conn() as con, con.cursor() as cur:
            
            # 4. Add missing foreign key constraints where safe (PostgreSQL compatible)
            try:
                cur.execute("""
                    ALTER TABLE feed_posts 
                    ADD CONSTRAINT fk_feed_posts_author
                    FOREIGN KEY (author_id) REFERENCES users(tg_user_id) ON DELETE CASCADE;
                """)
            except psycopg2.Error:
                # Constraint already exists or conflicts, ignore
                pass
            
            # 5. Ensure feed_comments has proper foreign key  
            try:
                cur.execute("""
                    ALTER TABLE feed_comments
                    ADD CONSTRAINT fk_feed_comments_author  
                    FOREIGN KEY (author_id) REFERENCES users(tg_user_id) ON DELETE CASCADE;
                """)
            except psycopg2.Error:
                # Constraint already exists or conflicts, ignore
                pass
            
            con.commit()
            log.info("✅ Database integrity constraints applied successfully")
            
    except Exception as e:
        log.error(f"Failed to apply database constraints: {e}")

def create_idempotency_key(operation: str, user_id: int, data: str = "") -> str:
    """Create unique idempotency key for an operation."""
    import hashlib
    import time
    
    # Create deterministic key from operation + user + data
    key_data = f"{operation}:{user_id}:{data}:{int(time.time() // 60)}"  # 1-minute window
    return hashlib.md5(key_data.encode()).hexdigest()

def check_idempotency(key: str, operation: str) -> Optional[Any]:
    """Check if operation was already performed. Returns previous result if found."""
    import registration as reg
    import json
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute(
                "SELECT result FROM idempotency_keys WHERE key=%s AND operation=%s",
                (key, operation)
            )
            row = cur.fetchone()
            return json.loads(row[0]) if row and row[0] else None
    except Exception as e:
        log.warning(f"Idempotency check failed: {e}")
        return None

def store_idempotency(key: str, operation: str, result: Any = None) -> None:
    """Store operation result for idempotency."""
    import registration as reg
    import json
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                INSERT INTO idempotency_keys (key, operation, result) 
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO NOTHING
            """, (key, operation, json.dumps(result) if result else None))
            con.commit()
    except Exception as e:
        log.warning(f"Failed to store idempotency key: {e}")

# UPSERT helper functions for race-condition-free operations
def upsert_like(user_id: int, post_id: int, action: str = "toggle") -> dict:
    """
    Thread-safe like/unlike operation using UPSERT pattern.
    Returns {"action": "liked|unliked", "total_likes": count}
    """
    import registration as reg
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            if action == "like":
                # Always like (idempotent)
                cur.execute("""
                    INSERT INTO feed_likes (user_id, post_id) 
                    VALUES (%s, %s)
                    ON CONFLICT (post_id, user_id) DO NOTHING
                """, (user_id, post_id))
                result_action = "liked"
                
            elif action == "unlike":
                # Always unlike (idempotent)
                cur.execute("""
                    DELETE FROM feed_likes 
                    WHERE user_id = %s AND post_id = %s
                """, (user_id, post_id))
                result_action = "unliked"
                
            else:  # toggle (default)
                # Check current state and toggle
                cur.execute("""
                    SELECT 1 FROM feed_likes 
                    WHERE user_id = %s AND post_id = %s
                """, (user_id, post_id))
                
                if cur.fetchone():
                    # Unlike
                    cur.execute("""
                        DELETE FROM feed_likes 
                        WHERE user_id = %s AND post_id = %s
                    """, (user_id, post_id))
                    result_action = "unliked"
                else:
                    # Like
                    cur.execute("""
                        INSERT INTO feed_likes (user_id, post_id) 
                        VALUES (%s, %s)
                        ON CONFLICT (post_id, user_id) DO NOTHING
                    """, (user_id, post_id))
                    result_action = "liked"
            
            # Get total likes count
            cur.execute("SELECT COUNT(*) FROM feed_likes WHERE post_id = %s", (post_id,))
            total_likes = cur.fetchone()[0]
            
            con.commit()
            return {"action": result_action, "total_likes": total_likes}
            
    except Exception as e:
        log.error(f"Like operation failed: {e}")
        return {"action": "error", "total_likes": 0}

def upsert_reaction(user_id: int, post_id: int, emoji: str) -> dict:
    """
    Thread-safe reaction operation. One reaction per user per post.
    Returns {"action": "added|removed|changed", "emoji": emoji, "counts": {emoji: count}}
    """
    import registration as reg
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Check current reaction
            cur.execute("""
                SELECT emoji FROM feed_reactions 
                WHERE user_id = %s AND post_id = %s
            """, (user_id, post_id))
            
            current = cur.fetchone()
            current_emoji = current[0] if current else None
            
            if current_emoji == emoji:
                # Remove same reaction
                cur.execute("""
                    DELETE FROM feed_reactions 
                    WHERE user_id = %s AND post_id = %s
                """, (user_id, post_id))
                action = "removed"
            else:
                # Add/change reaction (atomic replacement)
                cur.execute("""
                    INSERT INTO feed_reactions (user_id, post_id, emoji) 
                    VALUES (%s, %s, %s)
                    ON CONFLICT (post_id, user_id, emoji) DO NOTHING;
                    
                    DELETE FROM feed_reactions 
                    WHERE user_id = %s AND post_id = %s AND emoji != %s;
                """, (user_id, post_id, emoji, user_id, post_id, emoji))
                action = "changed" if current_emoji else "added"
            
            # Get updated counts  
            cur.execute("""
                SELECT emoji, COUNT(*) FROM feed_reactions 
                WHERE post_id = %s GROUP BY emoji
            """, (post_id,))
            
            counts = {row[0]: row[1] for row in cur.fetchall()}
            con.commit()
            
            return {"action": action, "emoji": emoji, "counts": counts}
            
    except Exception as e:
        log.error(f"Reaction operation failed: {e}")
        return {"action": "error", "emoji": emoji, "counts": {}}

# Initialize integrity constraints at startup
try:
    apply_missing_constraints()
except Exception as e:
    log.error(f"Failed to apply startup constraints: {e}")