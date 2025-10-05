# utils/privacy_compliance.py - Privacy and data deletion compliance
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from psycopg2 import sql

log = logging.getLogger(__name__)

class PrivacyManager:
    """Handles user data deletion and privacy compliance."""
    
    def __init__(self):
        self.deletion_queue = {}  # user_id -> deletion_timestamp
        self.deletion_grace_period = 24 * 3600  # 24 hours in seconds
    
    def request_data_deletion(self, user_id: int) -> Dict[str, Any]:
        """
        Request complete user data deletion with 24-hour grace period.
        User can cancel within 24 hours.
        """
        import registration as reg
        
        try:
            # Check if user exists
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("SELECT tg_user_id FROM users WHERE tg_user_id = %s", (user_id,))
                if not cur.fetchone():
                    return {"success": False, "error": "User not found"}
            
            # Schedule deletion (24 hour grace period)
            deletion_time = time.time() + self.deletion_grace_period
            self.deletion_queue[user_id] = deletion_time
            
            log.info(f"🗑️ Data deletion scheduled for user {user_id} in 24 hours")
            
            return {
                "success": True,
                "message": "Data deletion scheduled in 24 hours. Use /cancel_deletion to cancel.",
                "deletion_time": datetime.fromtimestamp(deletion_time).isoformat(),
                "grace_period_hours": 24
            }
            
        except Exception as e:
            log.error(f"Failed to schedule data deletion for user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def cancel_data_deletion(self, user_id: int) -> Dict[str, Any]:
        """Cancel pending data deletion request."""
        try:
            if user_id in self.deletion_queue:
                del self.deletion_queue[user_id]
                log.info(f"✅ Data deletion cancelled for user {user_id}")
                return {
                    "success": True, 
                    "message": "Data deletion request cancelled successfully."
                }
            else:
                return {
                    "success": False, 
                    "error": "No pending deletion request found."
                }
                
        except Exception as e:
            log.error(f"Failed to cancel deletion for user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_pending_deletions(self) -> Dict[str, Any]:
        """Execute all pending deletions that have passed grace period."""
        current_time = time.time()
        executed_deletions = []
        failed_deletions = []
        
        # Find users ready for deletion
        ready_for_deletion = [
            user_id for user_id, deletion_time in self.deletion_queue.items()
            if current_time >= deletion_time
        ]
        
        for user_id in ready_for_deletion:
            try:
                result = self._execute_user_deletion(user_id)
                if result["success"]:
                    executed_deletions.append(user_id)
                    del self.deletion_queue[user_id]
                else:
                    failed_deletions.append({"user_id": user_id, "error": result["error"]})
                    
            except Exception as e:
                log.error(f"Failed to delete data for user {user_id}: {e}")
                failed_deletions.append({"user_id": user_id, "error": str(e)})
        
        log.info(f"🗑️ Executed {len(executed_deletions)} deletions, {len(failed_deletions)} failed")
        
        return {
            "success": True,
            "executed_deletions": executed_deletions,
            "failed_deletions": failed_deletions,
            "pending_deletions": len(self.deletion_queue)
        }
    
    def _execute_user_deletion(self, user_id: int) -> Dict[str, Any]:
        """Execute complete user data deletion across all tables."""
        import registration as reg
        
        deleted_records = {}
        
        try:
            with reg._conn() as con, con.cursor() as cur:
                # Tables to delete from (in dependency order)
                deletion_order = [
                    # User-generated content
                    ("feed_comments", "author_id"),
                    ("feed_likes", "user_id"), 
                    ("feed_reactions", "user_id"),
                    ("feed_views", "viewer_id"),
                    ("feed_posts", "author_id"),
                    
                    # Stories and views
                    ("story_views", "viewer_id"),
                    ("stories", "author_id"),
                    
                    # Social connections
                    ("blocked_users", "user_id"),
                    ("blocked_users", "blocked_uid"),
                    ("secret_crush", "user_id"),
                    ("secret_crush", "target_id"), 
                    ("friend_requests", "sender"),
                    ("friend_requests", "receiver"),
                    ("friend_msg_requests", "sender"),
                    ("friend_msg_requests", "receiver"),
                    
                    # Ratings and reports
                    ("chat_ratings", "rater_id"),
                    ("chat_ratings", "rated_id"),
                    ("reports", "reporter_id"),
                    ("reports", "reported_id"),
                    
                    # User interests and core profile
                    ("user_interests", "user_id"),
                    ("users", "tg_user_id"),
                ]
                
                total_deleted = 0
                
                # Safe tables for user deletion
                SAFE_TABLES = {
                    "feed_comments", "feed_likes", "feed_reactions", "feed_views", "feed_posts",
                    "story_views", "stories", "blocked_users", "secret_crush", 
                    "friend_requests", "friend_msg_requests", "chat_ratings", "reports",
                    "user_interests", "users"
                }
                SAFE_COLUMNS = {
                    "author_id", "user_id", "viewer_id", "blocked_uid", "target_id",
                    "sender", "receiver", "rater_id", "rated_id", "reporter_id", "reported_id", "tg_user_id"
                }
                
                for table, column in deletion_order:
                    try:
                        if table not in SAFE_TABLES or column not in SAFE_COLUMNS:
                            log.warning(f"Skipping unsafe table/column: {table}.{column}")
                            continue
                            
                        # Count records first
                        q = sql.SQL("SELECT COUNT(*) FROM {table} WHERE {column} = %s").format(
                            table=sql.Identifier(table),
                            column=sql.Identifier(column)
                        )
                        cur.execute(q, (user_id,))
                        count_before = cur.fetchone()[0]
                        
                        if count_before > 0:
                            # Delete records
                            q = sql.SQL("DELETE FROM {table} WHERE {column} = %s").format(
                                table=sql.Identifier(table),
                                column=sql.Identifier(column)
                            )
                            cur.execute(q, (user_id,))
                            deleted_count = cur.rowcount
                            deleted_records[f"{table}.{column}"] = deleted_count
                            total_deleted += deleted_count
                            
                    except Exception as e:
                        # Some tables might not exist or have different schemas
                        log.warning(f"Could not delete from {table}.{column}: {e}")
                
                con.commit()
                
                log.info(f"🗑️ Deleted {total_deleted} records for user {user_id}: {deleted_records}")
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "total_records_deleted": total_deleted,
                    "deleted_records": deleted_records,
                    "deleted_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            log.error(f"Failed to execute deletion for user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user_data_summary(self, user_id: int) -> Dict[str, Any]:
        """Get summary of user's data for transparency."""
        import registration as reg
        
        try:
            with reg._conn() as con, con.cursor() as cur:
                data_summary = {}
                
                # Count user's data across tables
                tables_to_check = [
                    ("users", "tg_user_id", "profile"),
                    ("feed_posts", "author_id", "posts"),
                    ("feed_comments", "author_id", "comments"),
                    ("feed_likes", "user_id", "likes_given"),
                    ("feed_reactions", "user_id", "reactions_given"),
                    ("stories", "author_id", "stories"),
                    ("story_views", "viewer_id", "story_views"),
                    ("blocked_users", "user_id", "users_blocked"),
                    ("friend_requests", "sender", "friend_requests_sent"),
                ]
                
                total_records = 0
                
                # Safe tables for data summary
                SAFE_TABLES = {
                    "users", "feed_posts", "feed_comments", "feed_likes", "feed_reactions",
                    "stories", "story_views", "blocked_users", "friend_requests"
                }
                SAFE_COLUMNS = {"tg_user_id", "author_id", "user_id", "viewer_id", "sender"}
                
                for table, column, description in tables_to_check:
                    try:
                        if table not in SAFE_TABLES or column not in SAFE_COLUMNS:
                            log.warning(f"Skipping unsafe table/column: {table}.{column}")
                            continue
                            
                        q = sql.SQL("SELECT COUNT(*) FROM {table} WHERE {column} = %s").format(
                            table=sql.Identifier(table),
                            column=sql.Identifier(column)
                        )
                        cur.execute(q, (user_id,))
                        count = cur.fetchone()[0]
                        if count > 0:
                            data_summary[description] = count
                            total_records += count
                    except Exception as e:
                        log.warning(f"Could not check {table}: {e}")
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "total_records": total_records,
                    "data_breakdown": data_summary,
                    "has_pending_deletion": user_id in self.deletion_queue,
                    "checked_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            log.error(f"Failed to get data summary for user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def anonymize_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Alternative to deletion: anonymize user data while preserving statistics.
        Replaces personal info with anonymous placeholders.
        """
        import registration as reg
        
        try:
            with reg._conn() as con, con.cursor() as cur:
                # Generate anonymous ID
                anon_id = f"anon_{int(time.time())}"
                
                # Anonymize profile data
                cur.execute("""
                    UPDATE users SET 
                        feed_username = %s,
                        country = 'Anonymous',
                        city = 'Anonymous',
                        feed_photo = NULL
                    WHERE tg_user_id = %s
                """, (anon_id, user_id))
                
                # Anonymize post content (keep structure for stats)
                cur.execute("""
                    UPDATE feed_posts SET 
                        text = '[Content removed by user]'
                    WHERE author_id = %s AND text IS NOT NULL
                """, (user_id,))
                
                # Anonymize comments
                cur.execute("""
                    UPDATE feed_comments SET 
                        text = '[Comment removed by user]',
                        author_name = %s
                    WHERE author_id = %s
                """, (anon_id, user_id))
                
                con.commit()
                
                log.info(f"🔒 Anonymized data for user {user_id}")
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "anonymized_id": anon_id,
                    "anonymized_at": datetime.now().isoformat(),
                    "note": "Data anonymized while preserving platform statistics"
                }
                
        except Exception as e:
            log.error(f"Failed to anonymize data for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

# Global privacy manager instance
privacy_manager = PrivacyManager()

def get_privacy_policy_text() -> str:
    """Return privacy policy text for /privacy command."""
    return """
🔒 **LuvHive Privacy Policy**

**Data We Collect:**
• Profile information you provide (age, interests, etc.)
• Messages and content you post in feeds
• Usage statistics and interactions

**How We Use Your Data:**
• Provide chat matching services
• Improve platform features
• Ensure safety and prevent abuse

**Your Rights:**
• View your data with /my_data
• Delete all data with /delete_me (24hr grace period)
• Cancel deletion with /cancel_deletion

**Data Retention:**
• Active profiles: retained while account is active
• Deleted accounts: permanently removed after 24 hours
• Anonymized statistics: may be retained for service improvement

**Contact:** Use /support for privacy questions

Last updated: September 2025
"""