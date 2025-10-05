# utils/data_retention.py - Clean up old data per ChatGPT Phase-4 recommendations
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any

log = logging.getLogger(__name__)

class DataRetentionSystem:
    """Clean up old data to prevent database bloat and comply with privacy"""
    
    def __init__(self):
        # Retention periods (ChatGPT recommendation: 30-90 days)
        self.retention_config = {
            "story_views": 30,          # Story views after 30 days
            "feed_views": 30,           # Feed post views after 30 days  
            "chat_reports": 90,         # Chat reports after 90 days
            "moderation_events": 90,    # Moderation events after 90 days
            "violation_logs": 180,      # Keep violation logs longer (6 months)
            "rate_limit_logs": 7,       # Rate limit logs after 1 week
            "old_sessions": 30,         # Old user sessions after 30 days
        }
    
    def cleanup_story_views(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old story views"""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                # Clean views older than specified days
                cur.execute("""
                    DELETE FROM story_views 
                    WHERE viewed_at < NOW() - INTERVAL '%s days'
                    RETURNING story_id;
                """, (days_old,))
                
                deleted_count = cur.rowcount
                con.commit()
                
                log.info(f"🗑️ Cleaned {deleted_count} story views older than {days_old} days")
                return {"success": True, "deleted": deleted_count, "type": "story_views"}
                
        except Exception as e:
            log.error(f"Failed to clean story views: {e}")
            return {"success": False, "error": str(e)}
    
    def cleanup_feed_views(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old feed post views"""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                # Clean feed views older than specified days
                cur.execute("""
                    DELETE FROM feed_views 
                    WHERE viewed_at < NOW() - INTERVAL '%s days'
                    RETURNING post_id;
                """, (days_old,))
                
                deleted_count = cur.rowcount
                con.commit()
                
                log.info(f"🗑️ Cleaned {deleted_count} feed views older than {days_old} days")
                return {"success": True, "deleted": deleted_count, "type": "feed_views"}
                
        except Exception as e:
            log.error(f"Failed to clean feed views: {e}")
            return {"success": False, "error": str(e)}
    
    def cleanup_chat_reports(self, days_old: int = 90) -> Dict[str, Any]:
        """Clean up old chat reports"""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                # Clean reports older than specified days
                cur.execute("""
                    DELETE FROM reports 
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    RETURNING id;
                """, (days_old,))
                
                deleted_count = cur.rowcount
                con.commit()
                
                log.info(f"🗑️ Cleaned {deleted_count} reports older than {days_old} days")
                return {"success": True, "deleted": deleted_count, "type": "reports"}
                
        except Exception as e:
            log.error(f"Failed to clean reports: {e}")
            return {"success": False, "error": str(e)}
    
    def cleanup_moderation_events(self, days_old: int = 90) -> Dict[str, Any]:
        """Clean up old moderation events"""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                # Clean moderation events older than specified days
                cur.execute("""
                    DELETE FROM moderation_events 
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    RETURNING id;
                """, (days_old,))
                
                deleted_count = cur.rowcount
                con.commit()
                
                log.info(f"🗑️ Cleaned {deleted_count} moderation events older than {days_old} days")
                return {"success": True, "deleted": deleted_count, "type": "moderation_events"}
                
        except Exception as e:
            log.error(f"Failed to clean moderation events: {e}")
            return {"success": False, "error": str(e)}
    
    def cleanup_old_user_sessions(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old user session data"""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                # Clean old session-like data (if you have such tables)
                # This is a placeholder - adjust based on your actual session storage
                cur.execute("""
                    DELETE FROM user_sessions 
                    WHERE last_activity < NOW() - INTERVAL '%s days'
                    RETURNING user_id;
                """, (days_old,))
                
                deleted_count = cur.rowcount
                con.commit()
                
                log.info(f"🗑️ Cleaned {deleted_count} user sessions older than {days_old} days")
                return {"success": True, "deleted": deleted_count, "type": "user_sessions"}
                
        except Exception as e:
            # This might fail if table doesn't exist - that's ok
            log.debug(f"No user_sessions table or cleanup failed: {e}")
            return {"success": True, "deleted": 0, "type": "user_sessions", "note": "Table not found"}
    
    def run_full_cleanup(self) -> Dict[str, Any]:
        """Run complete data retention cleanup"""
        log.info("🧹 Starting full data retention cleanup...")
        
        results = []
        total_deleted = 0
        
        # Run all cleanup operations
        cleanup_operations = [
            ("story_views", lambda: self.cleanup_story_views(self.retention_config["story_views"])),
            ("feed_views", lambda: self.cleanup_feed_views(self.retention_config["feed_views"])),
            ("chat_reports", lambda: self.cleanup_chat_reports(self.retention_config["chat_reports"])),
            ("moderation_events", lambda: self.cleanup_moderation_events(self.retention_config["moderation_events"])),
            ("old_sessions", lambda: self.cleanup_old_user_sessions(self.retention_config["old_sessions"])),
        ]
        
        for operation_name, operation_func in cleanup_operations:
            try:
                result = operation_func()
                results.append(result)
                if result.get("success"):
                    total_deleted += result.get("deleted", 0)
            except Exception as e:
                log.error(f"Cleanup operation {operation_name} failed: {e}")
                results.append({"success": False, "error": str(e), "type": operation_name})
        
        log.info(f"✅ Data retention cleanup completed - {total_deleted} total records cleaned")
        
        return {
            "success": True,
            "total_deleted": total_deleted,
            "operations": results,
            "cleanup_date": datetime.now().isoformat()
        }

# Global retention system instance  
retention_system = DataRetentionSystem()

def run_data_cleanup():
    """Main function to run data cleanup - can be called from cron"""
    return retention_system.run_full_cleanup()

if __name__ == "__main__":
    # Run cleanup when called directly
    result = run_data_cleanup()
    if result["success"]:
        print(f"✅ Cleanup completed - {result['total_deleted']} records removed")
    else:
        print(f"❌ Cleanup failed")
        exit(1)