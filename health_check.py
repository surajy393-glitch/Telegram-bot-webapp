#!/usr/bin/env python3
"""
Production Health Check Script
Monitor bot performance and database health for 100K+ users
"""
import os
import psutil
import psycopg2
from datetime import datetime

def check_database_health():
    """Check PostgreSQL health and connection stats"""
    try:
        dsn = os.getenv("DATABASE_URL", "postgresql://luvbot:luvbot123@localhost:5432/luvhive_bot")
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        
        print("\n" + "="*60)
        print("📊 DATABASE HEALTH CHECK")
        print("="*60)
        
        # Active connections
        cur.execute("SELECT count(*) FROM pg_stat_activity WHERE datname='luvhive_bot';")
        active_conns = cur.fetchone()[0]
        print(f"🔌 Active Connections: {active_conns}")
        
        # Total users
        cur.execute("SELECT count(*) FROM users;")
        total_users = cur.fetchone()[0]
        print(f"👥 Total Users: {total_users:,}")
        
        # Database size
        cur.execute("SELECT pg_size_pretty(pg_database_size('luvhive_bot'));")
        db_size = cur.fetchone()[0]
        print(f"💾 Database Size: {db_size}")
        
        # Slow queries (if any)
        cur.execute("""
            SELECT count(*) FROM pg_stat_activity 
            WHERE state = 'active' 
            AND now() - query_start > interval '5 seconds'
            AND query NOT LIKE '%pg_stat_activity%';
        """)
        slow_queries = cur.fetchone()[0]
        print(f"🐌 Slow Queries (>5s): {slow_queries}")
        
        # Table sizes
        cur.execute("""
            SELECT schemaname, tablename, 
                   pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 5;
        """)
        print(f"\n📋 Top 5 Tables by Size:")
        for row in cur.fetchall():
            print(f"   - {row[1]}: {row[2]}")
        
        cur.close()
        conn.close()
        
        # Health status
        if active_conns > 400:
            print("\n⚠️  WARNING: High connection count! Consider connection pooling.")
        if slow_queries > 10:
            print("\n⚠️  WARNING: Many slow queries! Check indexes and optimize.")
        
        print("✅ Database health check complete\n")
        
    except Exception as e:
        print(f"\n❌ Database health check failed: {e}\n")

def check_system_resources():
    """Check system resource usage"""
    print("="*60)
    print("💻 SYSTEM RESOURCES")
    print("="*60)
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"🖥️  CPU Usage: {cpu_percent}%")
    
    # Memory
    mem = psutil.virtual_memory()
    print(f"🧠 RAM Usage: {mem.percent}% ({mem.used / 1024**3:.1f}GB / {mem.total / 1024**3:.1f}GB)")
    
    # Disk
    disk = psutil.disk_usage('/')
    print(f"💿 Disk Usage: {disk.percent}% ({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)")
    
    # Network
    net = psutil.net_io_counters()
    print(f"📡 Network: ↑{net.bytes_sent / 1024**2:.1f}MB ↓{net.bytes_recv / 1024**2:.1f}MB")
    
    # Bot process
    try:
        for proc in psutil.process_iter(['name', 'pid', 'memory_percent', 'cpu_percent']):
            if 'python' in proc.info['name'].lower() and 'main.py' in ' '.join(proc.cmdline()):
                print(f"\n🤖 Bot Process (PID {proc.info['pid']}):")
                print(f"   Memory: {proc.info['memory_percent']:.1f}%")
                print(f"   CPU: {proc.info['cpu_percent']:.1f}%")
                break
    except:
        pass
    
    # Warnings
    if cpu_percent > 80:
        print("\n⚠️  WARNING: High CPU usage!")
    if mem.percent > 85:
        print("\n⚠️  WARNING: High memory usage!")
    if disk.percent > 90:
        print("\n⚠️  WARNING: Low disk space!")
    
    print("✅ System check complete\n")

def main():
    print(f"\n🏥 LuvHive Bot Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    check_system_resources()
    check_database_health()
    print("="*60)
    print("✅ ALL CHECKS COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
