# utils/rate_limiter.py - Token bucket rate limiting for Telegram bot scaling
import time
import logging
from collections import defaultdict
from typing import Dict, Any

log = logging.getLogger(__name__)

# Global and per-user token buckets for rate limiting
GLOBAL_BUCKET = {"ts": time.time(), "tokens": 40.0}
USER_BUCKETS: Dict[int, Dict[str, float]] = defaultdict(lambda: {"ts": time.time(), "tokens": 5.0})

def _refill_tokens(bucket: Dict[str, float], rate: float, burst: float) -> None:
    """Refill tokens in bucket based on elapsed time."""
    now = time.time()
    elapsed = now - bucket["ts"]
    bucket["tokens"] = min(burst, bucket["tokens"] + rate * elapsed)
    bucket["ts"] = now

def _take_token(bucket: Dict[str, float]) -> bool:
    """Try to take one token from bucket."""
    if bucket["tokens"] < 1.0:
        return False
    bucket["tokens"] -= 1.0
    return True

def allow_send(user_id: int) -> bool:
    """
    Check if user is allowed to send a message.
    Uses token bucket algorithm with global + per-user limits.
    
    Global: ~15 msg/s burst 60 (prevents bot-wide flood)
    Per-user: ~1.5 msg/s burst 5 (prevents individual spam)
    """
    # Refill global bucket (15 msg/s, burst 60)
    _refill_tokens(GLOBAL_BUCKET, rate=15.0, burst=60.0)
    if not _take_token(GLOBAL_BUCKET):
        log.warning(f"Global rate limit hit for user {user_id}")
        return False
    
    # Refill user bucket (1.5 msg/s, burst 5)  
    user_bucket = USER_BUCKETS[user_id]
    _refill_tokens(user_bucket, rate=1.5, burst=5.0)
    if not _take_token(user_bucket):
        log.warning(f"User rate limit hit for user {user_id}")
        return False
        
    return True

def reset_user_bucket(user_id: int) -> None:
    """Reset user's rate limit bucket (e.g., for premium users)."""
    if user_id in USER_BUCKETS:
        USER_BUCKETS[user_id] = {"ts": time.time(), "tokens": 5.0}

def get_stats() -> Dict[str, Any]:
    """Get rate limiting statistics for monitoring."""
    return {
        "global_tokens": GLOBAL_BUCKET["tokens"],
        "active_users": len(USER_BUCKETS),
        "global_bucket_age": time.time() - GLOBAL_BUCKET["ts"]
    }