# utils/admin_audit.py - Admin action audit logging (ChatGPT Phase-4)
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

log = logging.getLogger(__name__)

class AdminAuditLogger:
    """Log all admin actions for security and compliance"""
    
    def __init__(self):
        self.audit_file = "/tmp/luvhive_admin_audit.log"
        
        # Initialize audit table
        self._init_audit_table()
    
    def _init_audit_table(self):
        """Create admin audit log table if not exists"""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS admin_audit_log (
                        id BIGSERIAL PRIMARY KEY,
                        admin_user_id BIGINT NOT NULL,
                        action TEXT NOT NULL,
                        target_user_id BIGINT,
                        target_type TEXT,  -- user, post, report, etc.
                        details JSONB,
                        ip_address TEXT,
                        user_agent TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                
                # Add index for efficient querying
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_admin_audit_admin_user 
                    ON admin_audit_log(admin_user_id, created_at);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_admin_audit_target_user 
                    ON admin_audit_log(target_user_id, created_at);
                """)
                
                con.commit()
                
        except Exception as e:
            log.error(f"Failed to initialize admin audit table: {e}")
    
    def log_admin_action(
        self, 
        admin_user_id: int,
        action: str,
        target_user_id: Optional[int] = None,
        target_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Log an admin action to database and file
        
        Args:
            admin_user_id: Telegram user ID of the admin
            action: Action performed (ban, unban, delete_post, etc.)
            target_user_id: User being acted upon (if applicable)
            target_type: Type of target (user, post, report, etc.)
            details: Additional action details
            ip_address: Admin's IP address if available
        """
        try:
            # Prepare audit record
            audit_record = {
                "timestamp": datetime.now().isoformat(),
                "admin_user_id": admin_user_id,
                "action": action,
                "target_user_id": target_user_id,
                "target_type": target_type,
                "details": details or {},
                "ip_address": ip_address
            }
            
            # Write to database
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    INSERT INTO admin_audit_log 
                    (admin_user_id, action, target_user_id, target_type, details, ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (
                    admin_user_id,
                    action, 
                    target_user_id,
                    target_type,
                    json.dumps(details) if details else None,
                    ip_address
                ))
                
                con.commit()
            
            # Write to audit log file as backup
            with open(self.audit_file, "a") as f:
                f.write(json.dumps(audit_record) + "\n")
            
            log.info(f"📋 Admin audit: {admin_user_id} performed {action} on {target_type}:{target_user_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to log admin action: {e}")
            return False
    
    def get_admin_history(self, admin_user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get admin action history for specific admin"""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT action, target_user_id, target_type, details, created_at
                    FROM admin_audit_log 
                    WHERE admin_user_id = %s 
                      AND created_at > NOW() - INTERVAL '%s days'
                    ORDER BY created_at DESC
                    LIMIT 100;
                """, (admin_user_id, days))
                
                history = []
                for row in cur.fetchall():
                    history.append({
                        "action": row[0],
                        "target_user_id": row[1],
                        "target_type": row[2], 
                        "details": row[3],
                        "created_at": row[4].isoformat() if row[4] else None
                    })
                
                return {
                    "success": True,
                    "admin_user_id": admin_user_id,
                    "period_days": days,
                    "actions": history
                }
                
        except Exception as e:
            log.error(f"Failed to get admin history: {e}")
            return {"success": False, "error": str(e)}
    
    def get_target_history(self, target_user_id: int, days: int = 90) -> Dict[str, Any]:
        """Get all admin actions performed on a specific user"""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT admin_user_id, action, details, created_at
                    FROM admin_audit_log 
                    WHERE target_user_id = %s 
                      AND created_at > NOW() - INTERVAL '%s days'
                    ORDER BY created_at DESC
                    LIMIT 50;
                """, (target_user_id, days))
                
                history = []
                for row in cur.fetchall():
                    history.append({
                        "admin_user_id": row[0],
                        "action": row[1],
                        "details": row[2],
                        "created_at": row[3].isoformat() if row[3] else None
                    })
                
                return {
                    "success": True,
                    "target_user_id": target_user_id,
                    "period_days": days,
                    "actions": history
                }
                
        except Exception as e:
            log.error(f"Failed to get target history: {e}")
            return {"success": False, "error": str(e)}

# Global audit logger instance
admin_audit = AdminAuditLogger()

# Convenience functions for common admin actions
def log_user_ban(admin_id: int, target_user_id: int, reason: Optional[str] = None):
    """Log user ban action"""
    return admin_audit.log_admin_action(
        admin_user_id=admin_id,
        action="ban_user",
        target_user_id=target_user_id,
        target_type="user",
        details={"reason": reason} if reason else None
    )

def log_user_unban(admin_id: int, target_user_id: int, reason: Optional[str] = None):
    """Log user unban action"""  
    return admin_audit.log_admin_action(
        admin_user_id=admin_id,
        action="unban_user", 
        target_user_id=target_user_id,
        target_type="user",
        details={"reason": reason} if reason else None
    )

def log_post_deletion(admin_id: int, post_id: int, author_id: int, reason: Optional[str] = None):
    """Log post deletion action"""
    return admin_audit.log_admin_action(
        admin_user_id=admin_id,
        action="delete_post",
        target_user_id=author_id,
        target_type="post", 
        details={"post_id": post_id, "reason": reason}
    )

def log_user_lookup(admin_id: int, target_user_id: int):
    """Log admin user information lookup"""
    return admin_audit.log_admin_action(
        admin_user_id=admin_id,
        action="lookup_user",
        target_user_id=target_user_id,
        target_type="user"
    )