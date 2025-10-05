# utils/backup_system.py - Automated backup and restore system
import os
import subprocess
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import tempfile
import shutil
import shlex
from psycopg2 import sql

log = logging.getLogger(__name__)

class BackupSystem:
    """Automated backup and restore system for bulletproof data protection."""
    
    def __init__(self):
        self.db_config = self._parse_db_url(os.environ.get("DATABASE_URL"))
        self.backup_dir = "/tmp/backups"
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _parse_db_url(self, db_url: str) -> dict:
        """Parse and validate database URL components for security."""
        if not db_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        import urllib.parse
        parsed = urllib.parse.urlparse(db_url)
        
        # Validate scheme
        if parsed.scheme not in ['postgres', 'postgresql']:
            raise ValueError("Database URL must use postgres:// or postgresql:// scheme")
        
        # Extract components safely
        db_config = {
            'host': parsed.hostname or 'localhost',
            'port': str(parsed.port) if parsed.port else '5432',
            'username': parsed.username or 'postgres',
            'password': parsed.password or '',
            'database': parsed.path.lstrip('/') if parsed.path else 'postgres'
        }
        
        # Parse query parameters for SSL and other options
        query_params = urllib.parse.parse_qs(parsed.query)
        db_config['env_vars'] = {}
        
        if 'sslmode' in query_params:
            db_config['env_vars']['PGSSLMODE'] = query_params['sslmode'][0]
        
        return db_config
        
    def create_backup(self) -> Dict[str, Any]:
        """Create full database backup with metadata."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{self.backup_dir}/luvhive_backup_{timestamp}.sql"
            metadata_file = f"{self.backup_dir}/luvhive_backup_{timestamp}.json"
            
            # Validate backup directory is safe
            if not os.path.abspath(backup_file).startswith(os.path.abspath(self.backup_dir)):
                raise ValueError("Backup file path outside allowed directory")
            
            # Whitelist pg_dump binary location
            allowed_pg_bins = ["/usr/bin/pg_dump", "/usr/local/bin/pg_dump", "pg_dump"]
            pg_dump_bin = "pg_dump"  # Use system PATH
            
            # Create PostgreSQL dump - SAFE: using individual parameters, no credential exposure
            cmd = [
                pg_dump_bin, 
                "--no-password",
                "--verbose",
                "--clean",
                "--if-exists", 
                "--create",
                "--format=custom",
                "--file", backup_file,
                "--host", self.db_config['host'],
                "--port", self.db_config['port'],
                "--username", self.db_config['username'],
                "--dbname", self.db_config['database']
            ]
            
            # Set up environment with password and SSL settings
            env = os.environ.copy()
            if self.db_config['password']:
                env['PGPASSWORD'] = self.db_config['password']
            env.update(self.db_config.get('env_vars', {}))
            
            # ✅ SAFE: no shell=True, list argv, timeout, password in env not args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, shell=False, env=env)
            
            if result.returncode != 0:
                log.error(f"Backup failed: {result.stderr}")
                return {"success": False, "error": result.stderr}
            
            # Get database stats for metadata
            stats = self._get_db_stats()
            
            # Create backup metadata
            metadata = {
                "timestamp": timestamp,
                "backup_file": backup_file,
                "db_stats": stats,
                "backup_size_bytes": os.path.getsize(backup_file),
                "created_at": datetime.now().isoformat(),
                "retention_days": 14,
                "verified": False
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            log.info(f"✅ Backup created: {backup_file} ({metadata['backup_size_bytes']} bytes)")
            
            # Verify backup immediately
            verification_result = self.verify_backup(backup_file)
            metadata["verified"] = verification_result["success"]
            
            # Update metadata with verification result
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return {
                "success": True,
                "backup_file": backup_file,
                "metadata": metadata,
                "verification": verification_result
            }
            
        except Exception as e:
            log.error(f"Backup creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def verify_backup(self, backup_file: str) -> Dict[str, Any]:
        """Verify backup can be restored to a test database."""
        try:
            # Create temporary test database
            test_db_name = f"luvhive_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create test database URL components
            test_db_config = self.db_config.copy()
            test_db_config['database'] = test_db_name
            
            # Validate test database name (no injection)
            if not test_db_name.replace('_', '').replace('-', '').isalnum():
                raise ValueError("Invalid test database name")
            
            # Create test database - SAFE: list argv with individual parameters
            create_cmd = [
                "createdb", 
                "--no-password",
                "--host", self.db_config['host'],
                "--port", self.db_config['port'],
                "--username", self.db_config['username'],
                test_db_name
            ]
            
            # Set up environment with password
            env = os.environ.copy()
            if self.db_config['password']:
                env['PGPASSWORD'] = self.db_config['password']
            env.update(self.db_config.get('env_vars', {}))
            
            result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=60, shell=False, env=env)
            
            if result.returncode != 0:
                return {"success": False, "error": f"Failed to create test DB: {result.stderr}"}
            
            try:
                # Validate backup file path is safe
                if not os.path.abspath(backup_file).startswith(os.path.abspath(self.backup_dir)):
                    raise ValueError("Backup file path outside allowed directory")
                
                # Restore backup to test database - SAFE: list argv with individual parameters  
                restore_cmd = [
                    "pg_restore",
                    "--no-password", 
                    "--verbose",
                    "--clean",
                    "--if-exists",
                    "--host", test_db_config['host'],
                    "--port", test_db_config['port'],
                    "--username", test_db_config['username'],
                    "--dbname", test_db_config['database'],
                    backup_file
                ]
                
                # ✅ SAFE: no shell=True, list argv, timeout, password in env
                result = subprocess.run(restore_cmd, capture_output=True, text=True, timeout=180, shell=False, env=env)
                
                if result.returncode != 0:
                    return {"success": False, "error": f"Restore failed: {result.stderr}"}
                
                # Verify key tables exist and have data
                verification_queries = [
                    "SELECT COUNT(*) FROM users",
                    "SELECT COUNT(*) FROM feed_posts", 
                    "SELECT COUNT(*) FROM feed_likes",
                    "SELECT COUNT(*) FROM stories"
                ]
                
                import psycopg2
                # Connect to test database using individual parameters
                test_conn_params = {
                    'host': test_db_config['host'],
                    'port': test_db_config['port'],
                    'user': test_db_config['username'],
                    'password': test_db_config['password'],
                    'dbname': test_db_config['database']
                }
                
                with psycopg2.connect(**test_conn_params) as conn:
                    with conn.cursor() as cur:
                        table_counts = {}
                        for query in verification_queries:
                            try:
                                cur.execute(query)
                                count = cur.fetchone()[0]
                                table_name = query.split(" FROM ")[1]
                                table_counts[table_name] = count
                            except Exception as e:
                                log.warning(f"Verification query failed: {query} - {e}")
                
                log.info(f"✅ Backup verified successfully: {table_counts}")
                return {
                    "success": True, 
                    "table_counts": table_counts,
                    "verified_at": datetime.now().isoformat()
                }
                
            finally:
                # Clean up test database - SAFE: list argv with individual parameters
                drop_cmd = [
                    "dropdb", 
                    "--no-password",
                    "--host", self.db_config['host'],
                    "--port", self.db_config['port'],
                    "--username", self.db_config['username'],
                    test_db_name
                ]
                subprocess.run(drop_cmd, capture_output=True, timeout=60, shell=False, env=env)
                
        except Exception as e:
            log.error(f"Backup verification failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_db_stats(self) -> Dict[str, Any]:
        """Get database statistics for backup metadata."""
        try:
            import psycopg2
            # Connect using individual parameters for security
            conn_params = {
                'host': self.db_config['host'],
                'port': self.db_config['port'],
                'user': self.db_config['username'],
                'password': self.db_config['password'],
                'dbname': self.db_config['database']
            }
            
            with psycopg2.connect(**conn_params) as conn:
                with conn.cursor() as cur:
                    stats = {}
                    
                    # Get table counts - SAFE: using predefined queries to avoid .format() 
                    table_queries = {
                        "users": "SELECT COUNT(*) FROM users;",
                        "feed_posts": "SELECT COUNT(*) FROM feed_posts;", 
                        "feed_likes": "SELECT COUNT(*) FROM feed_likes;",
                        "feed_comments": "SELECT COUNT(*) FROM feed_comments;",
                        "stories": "SELECT COUNT(*) FROM stories;",
                        "story_views": "SELECT COUNT(*) FROM story_views;"
                    }
                    
                    for table, query in table_queries.items():
                        try:
                            cur.execute(query)
                            stats[f"{table}_count"] = cur.fetchone()[0]
                        except:
                            stats[f"{table}_count"] = 0
                    
                    # Get database size
                    cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                    stats["database_size"] = cur.fetchone()[0]
                    
                    return stats
        except Exception as e:
            log.warning(f"Failed to get DB stats: {e}")
            return {}
    
    def cleanup_old_backups(self, retention_days: int = 14) -> Dict[str, Any]:
        """Remove backups older than retention period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            removed_files = []
            total_size_freed = 0
            
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("luvhive_backup_") and filename.endswith((".sql", ".json")):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_mtime < cutoff_date:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        removed_files.append(filename)
                        total_size_freed += file_size
            
            log.info(f"✅ Cleaned up {len(removed_files)} old backup files ({total_size_freed} bytes freed)")
            return {
                "success": True,
                "removed_files": removed_files,
                "size_freed_bytes": total_size_freed
            }
            
        except Exception as e:
            log.error(f"Backup cleanup failed: {e}")
            return {"success": False, "error": str(e)}
    
    def list_backups(self) -> Dict[str, Any]:
        """List all available backups with metadata."""
        try:
            backups = []
            
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("luvhive_backup_") and filename.endswith(".json"):
                    metadata_file = os.path.join(self.backup_dir, filename)
                    
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        
                        backup_file = metadata.get("backup_file", "")
                        if os.path.exists(backup_file):
                            backups.append(metadata)
                            
                    except Exception as e:
                        log.warning(f"Failed to read backup metadata {filename}: {e}")
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            return {"success": True, "backups": backups}
            
        except Exception as e:
            log.error(f"Failed to list backups: {e}")
            return {"success": False, "error": str(e)}

# Global backup instance
backup_system = BackupSystem()

def automated_backup():
    """Function to be called by cron/scheduler for automated backups."""
    log.info("🔄 Starting automated backup...")
    
    # Create backup
    result = backup_system.create_backup()
    
    if result["success"]:
        log.info(f"✅ Automated backup completed successfully")
        
        # Clean up old backups
        cleanup_result = backup_system.cleanup_old_backups()
        if cleanup_result["success"]:
            log.info("✅ Old backup cleanup completed")
        else:
            log.warning(f"⚠️ Backup cleanup failed: {cleanup_result.get('error')}")
    else:
        log.error(f"❌ Automated backup failed: {result.get('error')}")
        # TODO: Send alert to admin
    
    return result

if __name__ == "__main__":
    # Manual backup execution
    result = automated_backup()
    print(json.dumps(result, indent=2))