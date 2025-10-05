#!/usr/bin/env python3
"""
Development to Production Database Sync Script
Bypasses Replit's faulty database copy feature
"""
import os
import psycopg2
import subprocess
import json
from datetime import datetime
import tempfile

class DatabaseSync:
    def __init__(self):
        self.dev_db_url = os.environ.get('DATABASE_URL')
        if not self.dev_db_url:
            raise Exception("DATABASE_URL not found")
            
        # Parse database URL
        import urllib.parse as urlparse
        parsed = urlparse.urlparse(self.dev_db_url)
        self.db_config = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],  # Remove leading slash
            'user': parsed.username,
            'password': parsed.password,
        }
        
    def create_production_dump(self, output_file="production_sync.sql"):
        """Create a complete database dump for production"""
        print(f"🔄 Creating production database dump...")
        
        # Set environment variables for pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_config['password']
        
        # Create comprehensive dump with data
        dump_cmd = [
            'pg_dump',
            '-h', str(self.db_config['host']),
            '-p', str(self.db_config['port']),
            '-U', self.db_config['user'],
            '-d', self.db_config['database'],
            '--clean',  # Add DROP statements
            '--create', # Add CREATE DATABASE
            '--no-owner',  # Don't set ownership
            '--no-privileges',  # Don't set privileges
            '--inserts',  # Use INSERT instead of COPY for better compatibility
            '-f', output_file
        ]
        
        try:
            result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Database dump created: {output_file}")
                return True
            else:
                print(f"❌ Dump failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error creating dump: {e}")
            return False
    
    def create_data_only_dump(self, output_file="production_data.sql"):
        """Create data-only dump for existing production database"""
        print(f"🔄 Creating data-only dump...")
        
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_config['password']
        
        dump_cmd = [
            'pg_dump',
            '-h', str(self.db_config['host']),
            '-p', str(self.db_config['port']),
            '-U', self.db_config['user'],
            '-d', self.db_config['database'],
            '--data-only',  # Only data, no schema
            '--inserts',    # Use INSERTs
            '--disable-triggers',  # Disable triggers during insert
            '-f', output_file
        ]
        
        try:
            result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Data dump created: {output_file}")
                return True
            else:
                print(f"❌ Data dump failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error creating data dump: {e}")
            return False
    
    def get_database_stats(self):
        """Get current database statistics"""
        try:
            conn = psycopg2.connect(**self.db_config)
            with conn.cursor() as cur:
                # Get table counts
                cur.execute("""
                    SELECT 
                        schemaname,
                        relname as tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes,
                        n_live_tup as live_rows
                    FROM pg_stat_user_tables 
                    WHERE schemaname = 'public'
                    ORDER BY n_live_tup DESC;
                """)
                
                stats = cur.fetchall()
                print(f"\n📊 Database Statistics:")
                print(f"{'Table':<25} {'Live Rows':<10} {'Inserts':<10} {'Updates':<10}")
                print("-" * 60)
                
                total_rows = 0
                for schema, table, inserts, updates, deletes, live_rows in stats:
                    print(f"{table:<25} {live_rows:<10} {inserts:<10} {updates:<10}")
                    total_rows += live_rows or 0
                
                print(f"\n📈 Total Live Rows: {total_rows}")
                return total_rows
                
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return 0
    
    def create_deployment_script(self):
        """Create deployment script for Replit"""
        script_content = f'''#!/bin/bash
# Production Deployment Script
# Auto-generated on {datetime.now()}

echo "🚀 Starting production deployment..."

# Check if production_sync.sql exists
if [ -f "production_sync.sql" ]; then
    echo "📁 Found production database dump"
    
    # Apply to production database
    if [ -n "$PRODUCTION_DATABASE_URL" ]; then
        echo "🔄 Applying database changes to production..."
        psql "$PRODUCTION_DATABASE_URL" -f production_sync.sql
        echo "✅ Production database updated"
    else
        echo "❌ PRODUCTION_DATABASE_URL not found"
        exit 1
    fi
else
    echo "❌ production_sync.sql not found"
    exit 1
fi

echo "🎉 Deployment complete!"
'''
        
        with open('deploy_production.sh', 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod('deploy_production.sh', 0o755)
        print("✅ Deployment script created: deploy_production.sh")

if __name__ == "__main__":
    print("🔄 Database Sync Tool - Development to Production")
    print("=" * 50)
    
    sync = DatabaseSync()
    
    # Get current stats
    row_count = sync.get_database_stats()
    
    if row_count > 0:
        print(f"\n🎯 Found {row_count} rows to sync")
        
        # Create full dump
        if sync.create_production_dump():
            print("✅ Full database dump ready for production")
        
        # Create data-only dump as backup option
        if sync.create_data_only_dump():
            print("✅ Data-only dump ready as fallback")
        
        # Create deployment script
        sync.create_deployment_script()
        
        print(f"\n🚀 Ready for production deployment!")
        print(f"📁 Files created:")
        print(f"   - production_sync.sql (complete database)")
        print(f"   - production_data.sql (data only)")
        print(f"   - deploy_production.sh (deployment script)")
        
    else:
        print("⚠️  No data found in development database")