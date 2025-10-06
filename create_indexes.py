"""
Production Database Indexes for High-Scale Performance
Add indexes on frequently queried columns
"""
import os
import psycopg2

def _dsn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL missing")
    # Disable SSL for localhost
    if "localhost" in dsn or "127.0.0.1" in dsn:
        if "sslmode=" not in dsn:
            dsn += "?sslmode=disable" if "?" not in dsn else "&sslmode=disable"
    return dsn

def create_production_indexes():
    """
    Create indexes for high-performance queries
    Safe to run multiple times (IF NOT EXISTS)
    """
    print("🔧 Creating production indexes for scalability...")
    
    indexes = [
        # Users table - most frequently queried
        "CREATE INDEX IF NOT EXISTS idx_users_tg_user_id ON users(tg_user_id);",
        "CREATE INDEX IF NOT EXISTS idx_users_gender ON users(gender);",
        "CREATE INDEX IF NOT EXISTS idx_users_age ON users(age);",
        "CREATE INDEX IF NOT EXISTS idx_users_country ON users(country);",
        "CREATE INDEX IF NOT EXISTS idx_users_premium ON users(is_premium);",
        "CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);",
        
        # Chat ratings - for matching
        "CREATE INDEX IF NOT EXISTS idx_chat_ratings_user_id ON chat_ratings(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_chat_ratings_partner_id ON chat_ratings(partner_id);",
        "CREATE INDEX IF NOT EXISTS idx_chat_ratings_created_at ON chat_ratings(created_at);",
        
        # Reports table
        "CREATE INDEX IF NOT EXISTS idx_reports_reported_id ON reports(reported_id);",
        "CREATE INDEX IF NOT EXISTS idx_reports_reporter_id ON reports(reporter_id);",
        
        # Friend requests
        "CREATE INDEX IF NOT EXISTS idx_friend_requests_from_user ON friend_requests(from_user_id);",
        "CREATE INDEX IF NOT EXISTS idx_friend_requests_to_user ON friend_requests(to_user_id);",
        "CREATE INDEX IF NOT EXISTS idx_friend_requests_status ON friend_requests(status);",
        
        # Blocked users
        "CREATE INDEX IF NOT EXISTS idx_blocked_users_blocker ON blocked_users(blocker_id);",
        "CREATE INDEX IF NOT EXISTS idx_blocked_users_blocked ON blocked_users(blocked_id);",
        
        # Composite indexes for common queries
        "CREATE INDEX IF NOT EXISTS idx_users_gender_age ON users(gender, age);",
        "CREATE INDEX IF NOT EXISTS idx_users_country_gender ON users(country, gender);",
    ]
    
    try:
        with psycopg2.connect(_dsn()) as conn:
            with conn.cursor() as cur:
                for idx_sql in indexes:
                    try:
                        cur.execute(idx_sql)
                        print(f"✅ {idx_sql.split('idx_')[1].split(' ')[0]}")
                    except Exception as e:
                        print(f"⚠️ Index creation warning: {e}")
            conn.commit()
        print("✅ All production indexes created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        return False

if __name__ == "__main__":
    create_production_indexes()
