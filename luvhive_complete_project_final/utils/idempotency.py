# utils/idempotency.py - Idempotent callbacks and operations (ChatGPT Final Polish)
import logging
import hashlib
import json
import time
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

class IdempotencyManager:
    """Manage idempotent operations for button callbacks and critical actions"""
    
    def __init__(self):
        self.ttl_days = 90  # Keep idempotency keys for 90 days
    
    def generate_callback_key(self, update_id: int, user_id: int, action: str, target_id: Optional[str] = None) -> str:
        """Generate unique key for callback idempotency"""
        key_data = f"{update_id}:{user_id}:{action}:{target_id or ''}"
        return f"callback:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def generate_operation_key(self, operation: str, user_id: int, **params) -> str:
        """Generate unique key for general operations"""
        param_str = json.dumps(params, sort_keys=True)
        key_data = f"{operation}:{user_id}:{param_str}"
        return f"op:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def check_and_set_idempotency(self, key: str, result_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Check if operation already performed, if not mark as in progress
        Returns: {"is_duplicate": bool, "previous_result": Any}
        """
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                # Try to insert idempotency key
                cur.execute("""
                    INSERT INTO idempotency_keys (key, operation, result, created_at)
                    VALUES (%s, 'in_progress', %s, NOW())
                    ON CONFLICT (key) DO NOTHING
                    RETURNING key;
                """, (key, json.dumps(result_data) if result_data else None))
                
                if cur.rowcount > 0:
                    # Successfully inserted - not a duplicate
                    con.commit()
                    return {"is_duplicate": False, "previous_result": None}
                else:
                    # Key already exists - check what happened
                    cur.execute("""
                        SELECT operation, result, created_at
                        FROM idempotency_keys 
                        WHERE key = %s;
                    """, (key,))
                    
                    row = cur.fetchone()
                    if row:
                        operation, result, created_at = row
                        
                        # If still in progress after 5 minutes, allow retry
                        if operation == 'in_progress' and created_at:
                            if datetime.now() - created_at > timedelta(minutes=5):
                                cur.execute("""
                                    DELETE FROM idempotency_keys WHERE key = %s;
                                """, (key,))
                                con.commit()
                                return {"is_duplicate": False, "previous_result": None}
                        
                        previous_result = json.loads(result) if result else None
                        return {"is_duplicate": True, "previous_result": previous_result}
                    
                    return {"is_duplicate": False, "previous_result": None}
                    
        except Exception as e:
            log.error(f"Idempotency check failed for key {key}: {e}")
            return {"is_duplicate": False, "previous_result": None}
    
    def complete_operation(self, key: str, result_data: Dict[str, Any]) -> bool:
        """Mark operation as completed with result"""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    UPDATE idempotency_keys 
                    SET operation = 'completed', 
                        result = %s
                    WHERE key = %s;
                """, (json.dumps(result_data), key))
                
                con.commit()
                return True
                
        except Exception as e:
            log.error(f"Failed to complete operation for key {key}: {e}")
            return False
    
    def cleanup_old_keys(self, days_old: int = None) -> Dict[str, Any]:
        """Clean up old idempotency keys (run nightly)"""
        try:
            import registration as reg
            
            cleanup_days = days_old or self.ttl_days
            
            with reg._conn() as con, con.cursor() as cur:
                # Delete old keys
                cur.execute("""
                    DELETE FROM idempotency_keys 
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    RETURNING key;
                """, (cleanup_days,))
                
                deleted_count = cur.rowcount
                con.commit()
                
                log.info(f"🧹 Cleaned up {deleted_count} idempotency keys older than {cleanup_days} days")
                
                return {
                    "success": True,
                    "deleted_count": deleted_count,
                    "cleanup_days": cleanup_days
                }
                
        except Exception as e:
            log.error(f"Failed to cleanup idempotency keys: {e}")
            return {"success": False, "error": str(e)}

# Global idempotency manager
idempotency = IdempotencyManager()

def idempotent_callback(action: str, target_id: Optional[str] = None):
    """Decorator for idempotent callback handlers"""
    def decorator(func):
        async def wrapper(update, context, *args, **kwargs):
            if not update.callback_query or not update.effective_user:
                return await func(update, context, *args, **kwargs)
            
            # Generate idempotency key
            key = idempotency.generate_callback_key(
                update.callback_query.id,
                update.effective_user.id,
                action,
                target_id
            )
            
            # Check if already processed
            check_result = idempotency.check_and_set_idempotency(key)
            if check_result["is_duplicate"]:
                log.info(f"🔄 Duplicate callback {action} from user {update.effective_user.id}")
                if update.callback_query:
                    await update.callback_query.answer("Already processed!")
                return check_result["previous_result"]
            
            # Execute the function
            try:
                result = await func(update, context, *args, **kwargs)
                
                # Mark as completed
                idempotency.complete_operation(key, {"status": "success", "result": str(result)})
                
                return result
                
            except Exception as e:
                # Mark as failed but don't prevent retry
                idempotency.complete_operation(key, {"status": "error", "error": str(e)})
                raise
                
        return wrapper
    return decorator

# Convenience functions
def check_operation_idempotency(operation: str, user_id: int, **params) -> Dict[str, Any]:
    """Check if operation is duplicate"""
    key = idempotency.generate_operation_key(operation, user_id, **params)
    return idempotency.check_and_set_idempotency(key)

def complete_operation(operation: str, user_id: int, result: Dict[str, Any], **params) -> bool:
    """Complete operation with result"""
    key = idempotency.generate_operation_key(operation, user_id, **params)
    return idempotency.complete_operation(key, result)

if __name__ == "__main__":
    # Test cleanup
    result = idempotency.cleanup_old_keys()
    print(f"Cleanup result: {result}")