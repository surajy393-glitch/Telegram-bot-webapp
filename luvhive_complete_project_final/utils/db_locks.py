# utils/db_locks.py - PostgreSQL advisory locks for background tasks
import contextlib
import logging
import psycopg2

log = logging.getLogger(__name__)

@contextlib.contextmanager
def advisory_lock(conn, key: int):
    """
    PostgreSQL advisory lock context manager.
    Prevents multiple instances of the same background task from running.
    
    Usage:
        with advisory_lock(conn, 12345) as acquired:
            if acquired:
                # Only one instance runs this code
                perform_cleanup()
            else:
                # Another instance is already running, skip
                pass
    """
    acquired = False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s);", (key,))
            acquired = cur.fetchone()[0]
            
        if acquired:
            log.info(f"Advisory lock {key} acquired")
        else:
            log.info(f"Advisory lock {key} already held, skipping")
            
        yield acquired
        
    finally:
        if acquired:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_unlock(%s);", (key,))
                log.info(f"Advisory lock {key} released")
            except Exception as e:
                log.error(f"Failed to release advisory lock {key}: {e}")

# Lock keys for different background tasks
STORY_CLEANUP_LOCK = 100001
LEADERBOARD_UPDATE_LOCK = 100002
METRICS_CLEANUP_LOCK = 100003