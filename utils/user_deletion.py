# utils/user_deletion.py - Complete user data purge (ChatGPT Phase-4)
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from psycopg2 import sql

log = logging.getLogger(__name__)

class UserDeletionSystem:
    """Complete user data purge for privacy compliance"""
    
    def __init__(self):
        # Tables that need user data cleanup
        self.user_data_tables = [
            ("users", "tg_user_id"),               # Main user profile
            ("user_interests", "user_id"),         # User interests (references users.id)
            ("feed_posts", "author_id"),           # User's posts  
            ("feed_comments", "author_id"),        # User's comments
            ("feed_likes", "user_id"),             # User's likes
            ("feed_views", "user_id"),             # User's post views
            ("stories", "author_id"),              # User's stories
            ("story_views", "viewer_id"),          # User's story views  
            ("friend_requests", "sender"),         # Sent friend requests
            ("friend_requests", "receiver"),       # Received friend requests
            ("blocked_users", "user_id"),          # Users they blocked
            ("blocked_users", "blocked_uid"),      # Users who blocked them
            ("reports", "reporter_id"),            # Reports they made
            ("reports", "reported_user_id"),       # Reports against them
            ("payments", "user_id"),               # Payment history
            ("moderation_events", "tg_user_id"),   # Moderation actions on them
            ("admin_audit_log", "target_user_id"), # Admin actions on them
            ("chat_ratings", "rater_id"),          # Ratings they gave
            ("chat_ratings", "rated_user_id"),     # Ratings they received
        ]
    
    def schedule_user_deletion(self, user_id: int, admin_id: Optional[int] = None, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Schedule user for deletion (gives 7-day grace period)
        """
        try:
            import registration as reg
            from utils.admin_audit import admin_audit
            
            with reg._conn() as con, con.cursor() as cur:
                # Create deletion schedule table if not exists
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_deletion_queue (
                        id BIGSERIAL PRIMARY KEY,
                        tg_user_id BIGINT NOT NULL,
                        scheduled_by BIGINT,  -- Admin ID who scheduled
                        reason TEXT,
                        scheduled_at TIMESTAMPTZ DEFAULT NOW(),
                        deletion_date TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',
                        status TEXT DEFAULT 'scheduled',  -- scheduled, cancelled, completed
                        metadata JSONB
                    );
                """)
                
                # Check if user already scheduled for deletion
                cur.execute("""
                    SELECT id, status FROM user_deletion_queue 
                    WHERE tg_user_id = %s AND status = 'scheduled';
                """, (user_id,))
                
                existing = cur.fetchone()
                if existing:
                    return {
                        "success": False,
                        "error": "User already scheduled for deletion",
                        "deletion_id": existing[0]
                    }
                
                # Schedule deletion
                cur.execute("""
                    INSERT INTO user_deletion_queue (tg_user_id, scheduled_by, reason)
                    VALUES (%s, %s, %s)
                    RETURNING id, deletion_date;
                """, (user_id, admin_id, reason))
                
                deletion_record = cur.fetchone()
                deletion_id = deletion_record[0]
                deletion_date = deletion_record[1]
                
                con.commit()
                
                # Audit log
                if admin_id:
                    admin_audit.log_admin_action(
                        admin_user_id=admin_id,
                        action="schedule_deletion",
                        target_user_id=user_id,
                        target_type="user",
                        details={"deletion_id": deletion_id, "reason": reason}
                    )
                
                log.info(f"🗑️ Scheduled user {user_id} for deletion on {deletion_date}")
                
                return {
                    "success": True,
                    "deletion_id": deletion_id,
                    "user_id": user_id,
                    "deletion_date": deletion_date.isoformat(),
                    "grace_period_days": 7
                }
                
        except Exception as e:
            log.error(f"Failed to schedule user deletion: {e}")
            return {"success": False, "error": str(e)}
    
    def cancel_user_deletion(self, user_id: int, admin_id: Optional[int] = None) -> Dict[str, Any]:
        """Cancel scheduled user deletion"""
        try:
            import registration as reg
            from utils.admin_audit import admin_audit
            
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    UPDATE user_deletion_queue 
                    SET status = 'cancelled', metadata = jsonb_set(
                        COALESCE(metadata, '{}'), 
                        '{cancelled_by}', 
                        %s::jsonb
                    )
                    WHERE tg_user_id = %s AND status = 'scheduled'
                    RETURNING id;
                """, (json.dumps(admin_id) if admin_id else 'null', user_id))
                
                if cur.rowcount == 0:
                    return {"success": False, "error": "No scheduled deletion found"}
                
                deletion_id = cur.fetchone()[0]
                con.commit()
                
                # Audit log
                if admin_id:
                    admin_audit.log_admin_action(
                        admin_user_id=admin_id,
                        action="cancel_deletion",
                        target_user_id=user_id,
                        target_type="user",
                        details={"deletion_id": deletion_id}
                    )
                
                log.info(f"✅ Cancelled deletion for user {user_id}")
                return {"success": True, "deletion_id": deletion_id}
                
        except Exception as e:
            log.error(f"Failed to cancel user deletion: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_user_deletion(self, user_id: int, force: bool = False) -> Dict[str, Any]:
        """
        Execute complete user data deletion
        
        Args:
            user_id: Telegram user ID to delete
            force: Skip grace period check if True
        """
        try:
            import registration as reg
            import json
            
            with reg._conn() as con, con.cursor() as cur:
                # Check if deletion is scheduled and grace period passed
                if not force:
                    cur.execute("""
                        SELECT id, deletion_date FROM user_deletion_queue 
                        WHERE tg_user_id = %s AND status = 'scheduled'
                          AND deletion_date <= NOW();
                    """, (user_id,))
                    
                    deletion_record = cur.fetchone()
                    if not deletion_record:
                        return {
                            "success": False,
                            "error": "User not scheduled for deletion or grace period not expired"
                        }
                    deletion_id = deletion_record[0]
                else:
                    deletion_id = None
                
                # Start deletion process
                deleted_data = {}
                total_deleted = 0
                
                log.info(f"🗑️ Starting complete deletion of user {user_id}")
                
                # Safe tables for deletion
                SAFE_TABLES = {
                    "users", "user_interests", "feed_posts", "feed_comments", "feed_likes", "feed_views",
                    "stories", "story_views", "friend_requests", "blocked_users", "reports", 
                    "payments", "moderation_events", "admin_audit_log", "chat_ratings"
                }
                SAFE_COLUMNS = {
                    "tg_user_id", "user_id", "author_id", "viewer_id", "sender", "receiver",
                    "blocked_uid", "reporter_id", "reported_user_id", "target_user_id",
                    "rater_id", "rated_user_id"
                }
                
                # Delete from all user data tables
                for table, column in self.user_data_tables:
                    try:
                        if table not in SAFE_TABLES or column not in SAFE_COLUMNS:
                            log.warning(f"Skipping unsafe table/column: {table}.{column}")
                            continue
                            
                        # Handle users table special case (references by id not tg_user_id)
                        if table == "user_interests":
                            q = sql.SQL("""
                                DELETE FROM {table} 
                                WHERE {column} IN (
                                    SELECT id FROM users WHERE tg_user_id = %s
                                )
                            """).format(
                                table=sql.Identifier(table),
                                column=sql.Identifier(column)
                            )
                            cur.execute(q, (user_id,))
                        else:
                            q = sql.SQL("DELETE FROM {table} WHERE {column} = %s").format(
                                table=sql.Identifier(table),
                                column=sql.Identifier(column)
                            )
                            cur.execute(q, (user_id,))
                        
                        row_count = cur.rowcount
                        deleted_data[table] = row_count
                        total_deleted += row_count
                        
                        if row_count > 0:
                            log.info(f"   Deleted {row_count} records from {table}")
                            
                    except Exception as table_error:
                        log.warning(f"   Failed to delete from {table}: {table_error}")
                        deleted_data[table] = f"ERROR: {table_error}"
                
                # Mark deletion as completed
                if deletion_id:
                    cur.execute("""
                        UPDATE user_deletion_queue 
                        SET status = 'completed', 
                            metadata = jsonb_set(
                                COALESCE(metadata, '{}'), 
                                '{completed_at}', 
                                %s::jsonb
                            )
                        WHERE id = %s;
                    """, (json.dumps(datetime.now().isoformat()), deletion_id))
                
                con.commit()
                
                log.info(f"✅ Complete deletion of user {user_id} finished - {total_deleted} total records removed")
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "total_deleted": total_deleted,
                    "deleted_data": deleted_data,
                    "deletion_date": datetime.now().isoformat()
                }
                
        except Exception as e:
            log.error(f"Failed to execute user deletion: {e}")
            return {"success": False, "error": str(e)}
    
    def get_deletion_queue(self) -> Dict[str, Any]:
        """Get current deletion queue"""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT tg_user_id, scheduled_by, reason, scheduled_at, deletion_date, status
                    FROM user_deletion_queue 
                    WHERE status = 'scheduled'
                    ORDER BY deletion_date ASC;
                """)
                
                queue = []
                for row in cur.fetchall():
                    queue.append({
                        "user_id": row[0],
                        "scheduled_by": row[1],
                        "reason": row[2],
                        "scheduled_at": row[3].isoformat() if row[3] else None,
                        "deletion_date": row[4].isoformat() if row[4] else None,
                        "status": row[5]
                    })
                
                return {"success": True, "queue": queue}
                
        except Exception as e:
            log.error(f"Failed to get deletion queue: {e}")
            return {"success": False, "error": str(e)}

# Global deletion system instance
user_deletion = UserDeletionSystem()

# Convenience functions
def delete_user_data(user_id: int, force: bool = False):
    """Delete all user data (use with caution)"""
    return user_deletion.execute_user_deletion(user_id, force=force)

def schedule_user_for_deletion(user_id: int, admin_id: Optional[int] = None, reason: Optional[str] = None):
    """Schedule user for deletion with grace period"""
    return user_deletion.schedule_user_deletion(user_id, admin_id, reason)

if __name__ == "__main__":
    # Test deletion queue
    result = user_deletion.get_deletion_queue()
    print(f"Deletion queue: {result}")