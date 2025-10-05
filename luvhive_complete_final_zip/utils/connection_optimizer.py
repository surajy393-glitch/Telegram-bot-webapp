# utils/connection_optimizer.py - SMART CONNECTION MANAGEMENT
"""
Intelligent connection management to reduce CPU overhead
Smart pooling and caching like a tactical mastermind!
"""

import logging
import time
import functools
from typing import Dict, Any, Optional
import psycopg2
from psycopg2 import pool
import registration as reg

log = logging.getLogger("luvbot.connections")

class SmartConnectionManager:
    """Intelligent database connection management"""
    
    def __init__(self):
        self.connection_cache = {}
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
        self.max_idle_time = 600     # 10 minutes
        self.retry_delays = [1, 2, 5, 10]  # Progressive retry delays
        
        log.info("🔧 Smart Connection Manager initialized")
    
    def cleanup_idle_connections(self):
        """Clean up idle connections to free resources"""
        current_time = time.time()
        
        # Only cleanup every 5 minutes
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        try:
            # Force cleanup of reg connection pool if available
            if hasattr(reg, '_pool') and reg._pool:
                # Check pool stats
                unused = getattr(reg._pool, '_unused', [])
                if len(unused) > 5:  # Too many idle connections
                    # Close some idle connections
                    for _ in range(3):
                        if unused:
                            conn = unused.pop()
                            try:
                                conn.close()
                            except:
                                pass
                    log.info(f"🧹 Cleaned up {3} idle database connections")
            
            self.last_cleanup = current_time
            
        except Exception as e:
            log.warning(f"⚠️ Connection cleanup warning: {e}")
    
    def get_optimized_connection(self):
        """Get an optimized database connection with retry logic"""
        self.cleanup_idle_connections()
        
        for attempt, delay in enumerate(self.retry_delays, 1):
            try:
                # Use existing connection function with optimizations
                conn = reg._conn()
                
                # Set connection-level optimizations
                if conn:
                    with conn.cursor() as cur:
                        # Optimize connection settings for performance
                        cur.execute("SET statement_timeout = '30s'")
                        cur.execute("SET lock_timeout = '10s'")
                        cur.execute("SET idle_in_transaction_session_timeout = '60s'")
                    conn.commit()
                
                return conn
                
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt < len(self.retry_delays):
                    log.warning(f"🔄 DB connection retry {attempt}/{len(self.retry_delays)} after {delay}s: {e}")
                    time.sleep(delay)
                else:
                    log.error(f"💥 DB connection failed after {len(self.retry_delays)} attempts: {e}")
                    raise
            except Exception as e:
                log.error(f"❌ Unexpected DB connection error: {e}")
                raise

# Global connection manager
connection_manager = SmartConnectionManager()

def optimized_db_operation(func):
    """Decorator for optimized database operations"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Apply connection optimizations before DB operations
        connection_manager.cleanup_idle_connections()
        return func(*args, **kwargs)
    return wrapper

def get_smart_connection():
    """Get a smart, optimized database connection"""
    return connection_manager.get_optimized_connection()

def force_connection_cleanup():
    """Force immediate connection cleanup"""
    connection_manager.cleanup_idle_connections()
    log.info("🧹 Forced connection cleanup completed")