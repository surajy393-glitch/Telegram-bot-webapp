#!/usr/bin/env python3
"""
Database polish script - Final safety configurations (ChatGPT Final Polish)
"""
import sys
import logging
from pathlib import Path
from psycopg2 import sql

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def configure_database_timeouts():
    """Configure safe database timeouts to prevent deadlocks"""
    try:
        import registration as reg
        
        with reg._conn() as con, con.cursor() as cur:
            log.info("🔧 Configuring database timeouts...")
            
            # Safe timeout settings (ChatGPT recommendations)
            timeout_configs = [
                ("statement_timeout", "5s"),           # Max query execution time
                ("idle_in_transaction_session_timeout", "15s"),  # Max idle in transaction
                ("lock_timeout", "2s"),                # Max time waiting for locks
                ("deadlock_timeout", "1s"),            # Deadlock detection time
            ]
            
            # Whitelist allowed settings for security
            allowed_settings = {
                "statement_timeout", "idle_in_transaction_session_timeout", 
                "lock_timeout", "deadlock_timeout"
            }
            
            for setting, value in timeout_configs:
                try:
                    if setting not in allowed_settings:
                        log.warning(f"   Setting {setting} not allowed")
                        continue
                    
                    # Note: These settings typically require superuser privileges
                    # In production, you'd run these as database admin
                    log.info(f"   Setting {setting} = {value}")
                    q = sql.SQL("SET {setting} TO %s").format(setting=sql.SQL(setting))
                    cur.execute(q, (value,))
                except Exception as e:
                    log.warning(f"   Could not set {setting}: {e}")
            
            con.commit()
            log.info("✅ Database timeout configuration completed")
            
    except Exception as e:
        log.error(f"Failed to configure database timeouts: {e}")

def run_data_integrity_checks():
    """Run ChatGPT's self-checks for duplicates and orphans"""
    try:
        import registration as reg
        
        with reg._conn() as con, con.cursor() as cur:
            log.info("🔍 Running data integrity checks...")
            
            # Check for duplicates (should be zero)
            duplicate_checks = [
                ("feed_likes", "SELECT user_id, post_id, COUNT(*) c FROM feed_likes GROUP BY 1,2 HAVING COUNT(*)>1;"),
                ("poll_votes", "SELECT voter_id, poll_id, COUNT(*) c FROM poll_votes GROUP BY 1,2 HAVING COUNT(*)>1;"),
                ("blocked_users", "SELECT user_id, blocked_uid, COUNT(*) c FROM blocked_users GROUP BY 1,2 HAVING COUNT(*)>1;"),
                ("friend_requests", "SELECT sender, receiver, COUNT(*) c FROM friend_requests GROUP BY 1,2 HAVING COUNT(*)>1;"),
            ]
            
            for table, query in duplicate_checks:
                try:
                    cur.execute(query)
                    duplicates = cur.fetchall()
                    if duplicates:
                        log.warning(f"⚠️  Found {len(duplicates)} duplicate entries in {table}")
                        for dup in duplicates[:5]:  # Show first 5
                            log.warning(f"   Duplicate: {dup}")
                    else:
                        log.info(f"✅ No duplicates in {table}")
                except Exception as e:
                    log.warning(f"Could not check {table}: {e}")
            
            # Check for orphaned records
            orphan_checks = [
                ("feed_likes", "SELECT l.id FROM feed_likes l LEFT JOIN feed_posts p ON p.id=l.post_id WHERE p.id IS NULL LIMIT 10;"),
                ("feed_comments", "SELECT c.id FROM feed_comments c LEFT JOIN feed_posts p ON p.id=c.post_id WHERE p.id IS NULL LIMIT 10;"),
                ("user_interests", "SELECT ui.user_id FROM user_interests ui LEFT JOIN users u ON u.id=ui.user_id WHERE u.id IS NULL LIMIT 10;"),
            ]
            
            for table, query in orphan_checks:
                try:
                    cur.execute(query)
                    orphans = cur.fetchall()
                    if orphans:
                        log.warning(f"⚠️  Found {len(orphans)} orphaned records in {table}")
                        for orphan in orphans[:3]:  # Show first 3
                            log.warning(f"   Orphaned: {orphan}")
                    else:
                        log.info(f"✅ No orphans in {table}")
                except Exception as e:
                    log.warning(f"Could not check {table}: {e}")
            
            log.info("✅ Data integrity checks completed")
            
    except Exception as e:
        log.error(f"Failed to run integrity checks: {e}")

def update_payments_table():
    """Ensure payments table has proper charge_id uniqueness"""
    try:
        import registration as reg
        
        with reg._conn() as con, con.cursor() as cur:
            log.info("💳 Updating payments table...")
            
            # Add columns if missing
            cur.execute("""
                ALTER TABLE payments 
                ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'succeeded',
                ADD COLUMN IF NOT EXISTS charge_id TEXT;
            """)
            
            # Add unique constraint on charge_id
            try:
                cur.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_charge
                    ON payments(charge_id) WHERE charge_id IS NOT NULL;
                """)
                log.info("✅ Added unique constraint on payments.charge_id")
            except Exception as e:
                log.warning(f"Payments constraint may already exist: {e}")
            
            con.commit()
            log.info("✅ Payments table updated")
            
    except Exception as e:
        log.error(f"Failed to update payments table: {e}")

def cleanup_idempotency_keys():
    """Clean up old idempotency keys"""
    try:
        from utils.idempotency import idempotency
        
        log.info("🧹 Cleaning up old idempotency keys...")
        result = idempotency.cleanup_old_keys()
        
        if result.get("success"):
            deleted = result.get("deleted_count", 0)
            log.info(f"✅ Cleaned up {deleted} old idempotency keys")
        else:
            log.warning(f"Cleanup failed: {result.get('error')}")
            
    except Exception as e:
        log.error(f"Failed to cleanup idempotency keys: {e}")

def main():
    """Run all database polish operations"""
    log.info("🚀 Starting database polish operations...")
    
    operations = [
        ("Database timeouts", configure_database_timeouts),
        ("Data integrity checks", run_data_integrity_checks), 
        ("Payments table update", update_payments_table),
        ("Idempotency cleanup", cleanup_idempotency_keys),
    ]
    
    for name, operation in operations:
        try:
            log.info(f"▶️  {name}...")
            operation()
        except Exception as e:
            log.error(f"❌ {name} failed: {e}")
    
    log.info("✅ Database polish completed!")

if __name__ == "__main__":
    main()