# utils/db_migration.py
import logging
import registration as reg
from psycopg2 import sql

log = logging.getLogger("luvbot.migration")

def apply_scaling_constraints():
    """
    Apply critical unique constraints for scaling to 10k+ users.
    Uses CONCURRENTLY to avoid blocking live operations.
    """
    constraints = [
        {
            "name": "uq_feed_likes_user_post",
            "table": "feed_likes",
            "columns": "(user_id, post_id)",
            "description": "Prevent duplicate likes"
        },
        {
            "name": "uq_poll_votes_user_poll", 
            "table": "poll_votes",
            "columns": "(voter_id, poll_id)",
            "description": "Prevent duplicate votes"
        },
        {
            "name": "uq_blocked_users_pair",
            "table": "blocked_users", 
            "columns": "(user_id, blocked_uid)",
            "description": "Prevent duplicate blocks"
        },
        {
            "name": "uq_friend_requests_pair",
            "table": "friend_requests",
            "columns": "(sender, receiver)", 
            "description": "Prevent duplicate friend requests"
        }
    ]
    
    results = []
    
    for constraint in constraints:
        try:
            # Use separate connection with autocommit for CONCURRENTLY
            with reg._conn() as con:
                con.autocommit = True
                with con.cursor() as cur:
                    # Validate constraint components for security
                    table_name = constraint['table']
                    index_name = constraint['name']
                    columns = constraint['columns']
                    
                    # Whitelist safe tables
                    safe_tables = {"feed_likes", "poll_votes", "blocked_users", "friend_requests"}
                    if table_name not in safe_tables:
                        raise ValueError(f"Table {table_name} not allowed for migration")
                    
                    # Use predefined migrations instead of dynamic SQL
                    migration_sql = {
                        "uq_feed_likes_user_post": "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_feed_likes_user_post ON feed_likes (user_id, post_id);",
                        "uq_poll_votes_user_poll": "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_poll_votes_user_poll ON poll_votes (voter_id, poll_id);",
                        "uq_blocked_users_pair": "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_blocked_users_pair ON blocked_users (user_id, blocked_uid);",
                        "uq_friend_requests_pair": "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_friend_requests_pair ON friend_requests (sender, receiver);"
                    }
                    
                    migration_query = migration_sql.get(index_name)
                    if not migration_query:
                        raise ValueError(f"Unknown migration: {index_name}")
                    
                    log.info(f"Creating constraint: {constraint['description']}")
                    cur.execute(migration_query)
                    results.append(f"✅ {constraint['description']}")
                    
        except Exception as e:
            error_msg = f"❌ Failed {constraint['description']}: {str(e)}"
            log.warning(error_msg)
            results.append(error_msg)
        finally:
            try:
                con.autocommit = False
            except:
                pass
    
    return results

def ensure_payment_constraints():
    """Ensure payment table has proper constraints for transaction safety."""
    try:
        with reg._conn() as con:
            con.autocommit = True
            with con.cursor() as cur:
                # Unique constraint on charge_id to prevent double processing
                cur.execute("""
                    CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_payments_charge_id
                    ON payments(charge_id) WHERE charge_id IS NOT NULL;
                """)
                
                # Index for efficient user payment queries
                cur.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_user_status
                    ON payments(user_id, status);
                """)
                
                log.info("✅ Payment constraints applied")
                return ["✅ Payment transaction safety enabled"]
                
    except Exception as e:
        error_msg = f"❌ Payment constraints failed: {str(e)}"
        log.warning(error_msg)
        return [error_msg]
    finally:
        try:
            con.autocommit = False
        except:
            pass

def run_all_migrations():
    """Run all scaling migrations safely."""
    log.info("🔧 Starting scaling migrations...")
    
    results = []
    results.extend(apply_scaling_constraints())
    results.extend(ensure_payment_constraints())
    
    log.info("✅ Migration completed")
    return results