# utils/maintenance.py - Data retention and database maintenance
import logging
import time
import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

log = logging.getLogger(__name__)

class MaintenanceSystem:
    """Automated database maintenance and data retention management."""
    
    def __init__(self):
        self.retention_policies = {
            "story_views": 7,           # Delete after 7 days
            "feed_views": 30,           # Delete after 30 days  
            "chat_sessions": 90,        # Delete after 90 days
            "error_logs": 14,           # Delete after 14 days
            "idempotency_keys": 7,      # Delete after 7 days
            "stories": 1,               # Delete expired stories (24h)
            "old_payments": 365,        # Archive old payments after 1 year
        }
        
        self.vacuum_schedule = {
            "daily": ["story_views", "feed_views", "stories"],
            "weekly": ["feed_posts", "feed_comments", "feed_likes", "users"],
            "monthly": ["payments", "chat_ratings", "reports"]
        }
    
    def run_data_retention_cleanup(self) -> Dict[str, Any]:
        """
        Run data retention cleanup based on policies.
        ChatGPT recommendation: prevent database bloat with automated cleanup.
        """
        import registration as reg
        
        cleanup_results = {}
        total_deleted = 0
        
        try:
            with reg._conn() as con, con.cursor() as cur:
                
                # 1. Clean expired stories (24 hour expiry)
                cur.execute("""
                    DELETE FROM stories 
                    WHERE expires_at < NOW()
                    RETURNING id;
                """)
                expired_stories = cur.fetchall()
                cleanup_results["expired_stories"] = len(expired_stories)
                total_deleted += len(expired_stories)
                
                # 2. Clean old story views
                days = self.retention_policies["story_views"]
                cur.execute("""
                    DELETE FROM story_views 
                    WHERE viewed_at < NOW() - (INTERVAL '1 day' * %s)
                    RETURNING story_id;
                """, (days,))
                old_story_views = cur.fetchall()
                cleanup_results["old_story_views"] = len(old_story_views)
                total_deleted += len(old_story_views)
                
                # 3. Clean old feed views
                days = self.retention_policies["feed_views"]
                cur.execute("""
                    DELETE FROM feed_views 
                    WHERE viewed_at < NOW() - (INTERVAL '1 day' * %s)
                    RETURNING post_id;
                """, (days,))
                old_feed_views = cur.fetchall()
                cleanup_results["old_feed_views"] = len(old_feed_views)
                total_deleted += len(old_feed_views)
                
                # 4. Clean old idempotency keys
                days = self.retention_policies["idempotency_keys"]
                cur.execute("""
                    DELETE FROM idempotency_keys 
                    WHERE created_at < NOW() - (INTERVAL '1 day' * %s)
                    RETURNING key;
                """, (days,))
                old_idempotency = cur.fetchall()
                cleanup_results["old_idempotency_keys"] = len(old_idempotency)
                total_deleted += len(old_idempotency)
                
                # 5. Archive old completed payments (move to archive table)
                days = self.retention_policies["old_payments"]
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS payments_archive (
                        LIKE payments INCLUDING ALL
                    );
                """)
                
                cur.execute("""
                    WITH archived AS (
                        DELETE FROM payments 
                        WHERE status IN ('succeeded', 'failed', 'refunded') 
                          AND updated_at < NOW() - (INTERVAL '1 day' * %s)
                        RETURNING *
                    )
                    INSERT INTO payments_archive SELECT * FROM archived
                    RETURNING id;
                """, (days,))
                archived_payments = cur.fetchall()
                cleanup_results["archived_payments"] = len(archived_payments)
                
                # 6. Clean very old error logs (if exists)
                try:
                    cur.execute("""
                        DELETE FROM error_logs 
                        WHERE created_at < NOW() - INTERVAL '14 days'
                        RETURNING id;
                    """)
                    old_errors = cur.fetchall()
                    cleanup_results["old_error_logs"] = len(old_errors)
                    total_deleted += len(old_errors)
                except:
                    # Table might not exist
                    cleanup_results["old_error_logs"] = 0
                
                con.commit()
                
                log.info(f"🧹 Data retention cleanup completed: {total_deleted} records cleaned")
                
                return {
                    "success": True,
                    "total_deleted": total_deleted,
                    "cleanup_details": cleanup_results,
                    "executed_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            log.error(f"Data retention cleanup failed: {e}")
            return {"success": False, "error": str(e)}
    
    def run_database_vacuum(self, table_list: List[str] = None) -> Dict[str, Any]:
        """
        Run VACUUM and ANALYZE on specified tables for performance.
        ChatGPT recommendation: weekly vacuum/analyze for biggest tables.
        """
        import registration as reg
        
        if not table_list:
            table_list = ["users", "feed_posts", "feed_comments", "feed_likes", "story_views"]
        
        vacuum_results = {}
        
        try:
            with reg._conn() as con, con.cursor() as cur:
                
                for table in table_list:
                    try:
                        start_time = time.time()
                        
                        # Whitelist safe tables for vacuum
                        safe_tables = {
                            "users", "feed_posts", "feed_comments", "feed_likes", "story_views",
                            "stories", "payments", "chat_ratings", "reports"
                        }
                        if table not in safe_tables:
                            raise ValueError(f"Table {table} not allowed for vacuum")
                        
                        # Get table stats before vacuum
                        cur.execute("""
                            SELECT 
                                schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del,
                                n_dead_tup, last_vacuum, last_analyze
                            FROM pg_stat_user_tables 
                            WHERE tablename = %s;
                        """, (table,))
                        
                        stats_before = cur.fetchone()
                        
                        # Run VACUUM ANALYZE - SAFE: using predefined queries
                        vacuum_queries = {
                            "users": "VACUUM ANALYZE users;",
                            "feed_posts": "VACUUM ANALYZE feed_posts;",
                            "feed_comments": "VACUUM ANALYZE feed_comments;", 
                            "feed_likes": "VACUUM ANALYZE feed_likes;",
                            "story_views": "VACUUM ANALYZE story_views;",
                            "stories": "VACUUM ANALYZE stories;",
                            "payments": "VACUUM ANALYZE payments;",
                            "chat_ratings": "VACUUM ANALYZE chat_ratings;",
                            "reports": "VACUUM ANALYZE reports;"
                        }
                        
                        vacuum_query = vacuum_queries.get(table)
                        if not vacuum_query:
                            raise ValueError(f"No predefined vacuum query for table: {table}")
                        
                        cur.execute(vacuum_query)
                        
                        # Get table size after
                        cur.execute("""
                            SELECT pg_size_pretty(pg_total_relation_size(%s));
                        """, (table,))
                        
                        row = cur.fetchone()
                        table_size = row[0] if row else "Unknown"
                        
                        duration = time.time() - start_time
                        
                        vacuum_results[table] = {
                            "duration_seconds": round(duration, 2),
                            "table_size": table_size,
                            "dead_tuples_before": stats_before[5] if stats_before else 0,
                            "last_vacuum_before": stats_before[6].isoformat() if stats_before and stats_before[6] else None,
                            "vacuumed_at": datetime.now().isoformat()
                        }
                        
                        log.info(f"🧹 VACUUM {table} completed in {duration:.2f}s")
                        
                    except Exception as e:
                        log.warning(f"VACUUM failed for table {table}: {e}")
                        vacuum_results[table] = {"error": str(e)}
                
                return {
                    "success": True,
                    "vacuum_results": vacuum_results,
                    "tables_processed": len(table_list)
                }
                
        except Exception as e:
            log.error(f"Database vacuum failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_database_health_stats(self) -> Dict[str, Any]:
        """Get comprehensive database health statistics."""
        import registration as reg
        
        try:
            with reg._conn() as con, con.cursor() as cur:
                health_stats = {}
                
                # Database size and connection info
                cur.execute("""
                    SELECT 
                        pg_size_pretty(pg_database_size(current_database())) as db_size,
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                        (SELECT count(*) FROM pg_stat_activity) as total_connections;
                """)
                
                db_info = cur.fetchone()
                health_stats["database"] = {
                    "size": db_info[0],
                    "active_connections": db_info[1],
                    "total_connections": db_info[2]
                }
                
                # Table sizes and stats
                cur.execute("""
                    SELECT 
                        tablename,
                        pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size,
                        n_tup_ins + n_tup_upd + n_tup_del as total_operations,
                        n_dead_tup as dead_tuples,
                        last_vacuum,
                        last_analyze
                    FROM pg_stat_user_tables 
                    ORDER BY pg_total_relation_size(tablename::regclass) DESC
                    LIMIT 10;
                """)
                
                table_stats = []
                for row in cur.fetchall():
                    table_stats.append({
                        "table": row[0],
                        "size": row[1],
                        "total_operations": row[2],
                        "dead_tuples": row[3],
                        "last_vacuum": row[4].isoformat() if row[4] else None,
                        "last_analyze": row[5].isoformat() if row[5] else None
                    })
                
                health_stats["tables"] = table_stats
                
                # Query performance stats
                cur.execute("""
                    SELECT 
                        query,
                        calls,
                        total_time,
                        mean_time,
                        rows
                    FROM pg_stat_statements 
                    WHERE query NOT LIKE '%pg_stat_statements%'
                    ORDER BY mean_time DESC 
                    LIMIT 5;
                """)
                
                slow_queries = []
                for row in cur.fetchall():
                    slow_queries.append({
                        "query": row[0][:100] + "..." if len(row[0]) > 100 else row[0],
                        "calls": row[1],
                        "total_time_ms": round(row[2], 2),
                        "mean_time_ms": round(row[3], 2),
                        "avg_rows": row[4]
                    })
                
                health_stats["slow_queries"] = slow_queries
                
                return {
                    "success": True,
                    "health_stats": health_stats,
                    "collected_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            log.warning(f"Could not collect all health stats: {e}")
            # Return basic stats even if advanced features fail
            try:
                with reg._conn() as con, con.cursor() as cur:
                    cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                    db_size = cur.fetchone()[0]
                    
                    return {
                        "success": True,
                        "health_stats": {
                            "database": {"size": db_size},
                            "note": "Limited stats due to missing extensions"
                        },
                        "collected_at": datetime.now().isoformat()
                    }
            except Exception as e2:
                return {"success": False, "error": str(e2)}
    
    def setup_automated_maintenance(self) -> Dict[str, Any]:
        """Set up automated maintenance schedules."""
        try:
            # Create maintenance log table
            import registration as reg
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS maintenance_log (
                        id BIGSERIAL PRIMARY KEY,
                        operation TEXT NOT NULL,
                        status TEXT NOT NULL,
                        details JSONB,
                        duration_seconds REAL,
                        executed_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                con.commit()
            
            log.info("✅ Maintenance system initialized")
            
            return {
                "success": True,
                "message": "Automated maintenance system configured",
                "retention_policies": self.retention_policies,
                "vacuum_schedule": self.vacuum_schedule
            }
            
        except Exception as e:
            log.error(f"Failed to setup maintenance: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_maintenance_cycle(self, cycle_type: str = "daily") -> Dict[str, Any]:
        """Execute a complete maintenance cycle."""
        start_time = time.time()
        results = {
            "cycle_type": cycle_type,
            "started_at": datetime.now().isoformat(),
            "operations": {}
        }
        
        try:
            # 1. Data retention cleanup
            if cycle_type in ["daily", "weekly"]:
                cleanup_result = self.run_data_retention_cleanup()
                results["operations"]["data_retention"] = cleanup_result
            
            # 2. Database vacuum based on schedule
            vacuum_tables = self.vacuum_schedule.get(cycle_type, [])
            if vacuum_tables:
                vacuum_result = self.run_database_vacuum(vacuum_tables)
                results["operations"]["vacuum"] = vacuum_result
            
            # 3. Health stats collection
            health_result = self.get_database_health_stats()
            results["operations"]["health_check"] = health_result
            
            duration = time.time() - start_time
            results["duration_seconds"] = round(duration, 2)
            results["completed_at"] = datetime.now().isoformat()
            results["success"] = True
            
            log.info(f"🧹 {cycle_type.title()} maintenance completed in {duration:.2f}s")
            
            return results
            
        except Exception as e:
            duration = time.time() - start_time
            results["duration_seconds"] = round(duration, 2)
            results["error"] = str(e)
            results["success"] = False
            
            log.error(f"Maintenance cycle failed: {e}")
            return results

# Global maintenance system instance
maintenance_system = MaintenanceSystem()

def run_daily_maintenance():
    """Function to be called by cron/scheduler for daily maintenance."""
    return maintenance_system.execute_maintenance_cycle("daily")

def run_weekly_maintenance():
    """Function to be called by cron/scheduler for weekly maintenance."""
    return maintenance_system.execute_maintenance_cycle("weekly")

def run_monthly_maintenance():
    """Function to be called by cron/scheduler for monthly maintenance.""" 
    return maintenance_system.execute_maintenance_cycle("monthly")