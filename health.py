# health.py - Health check endpoints for monitoring and load balancer readiness
import os
import time
import logging
import psycopg2
from typing import Dict, Any

log = logging.getLogger(__name__)

def check_database() -> Dict[str, Any]:
    """Check database connectivity and basic operations."""
    try:
        import registration as reg
        start_time = time.time()
        
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            
        response_time = time.time() - start_time
        
        return {
            "status": "healthy" if result and result[0] == 1 else "unhealthy",
            "response_time_ms": round(response_time * 1000, 2),
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

def check_telegram_api() -> Dict[str, Any]:
    """Check if bot token is valid (basic check)."""
    try:
        bot_token = os.environ.get("BOT_TOKEN", "")
        if not bot_token or len(bot_token) < 10:
            return {
                "status": "unhealthy", 
                "error": "BOT_TOKEN missing or invalid",
                "timestamp": time.time()
            }
        
        return {
            "status": "healthy",
            "token_length": len(bot_token),
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

def healthz() -> Dict[str, Any]:
    """
    Basic health check - is the service alive?
    Used by load balancers for basic liveness probes.
    """
    try:
        from utils.rate_limiter import get_stats
        rate_stats = get_stats()
        
        return {
            "status": "healthy",
            "service": "luvhive-bot",
            "version": "1.0.0",
            "uptime_seconds": int(time.time()),
            "rate_limiter": {
                "global_tokens": round(rate_stats["global_tokens"], 1),
                "active_users": rate_stats["active_users"]
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": time.time()
        }

def readyz() -> Dict[str, Any]:
    """
    Readiness check - is the service ready to handle traffic?
    Checks all critical dependencies (database, bot token).
    Used by load balancers for traffic routing decisions.
    """
    checks = {
        "database": check_database(),
        "telegram_api": check_telegram_api()
    }
    
    # Overall status is healthy only if ALL checks pass
    overall_healthy = all(check["status"] == "healthy" for check in checks.values())
    
    return {
        "status": "ready" if overall_healthy else "not_ready",
        "checks": checks,
        "timestamp": time.time()
    }

def metrics() -> Dict[str, Any]:
    """
    Basic metrics for monitoring.
    Can be extended with more detailed metrics as needed.
    """
    try:
        from utils.rate_limiter import get_stats
        rate_stats = get_stats()
        
        return {
            "rate_limiter": rate_stats,
            "environment": {
                "fast_intro": os.getenv("FAST_INTRO", "0") == "1",
                "has_admin_ids": bool(os.getenv("ADMIN_IDS"))
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": time.time()
        }