#!/usr/bin/env python3
# setup_supabase_env.py - One-time setup script for Supabase

"""
SUPABASE SETUP INSTRUCTIONS:

1. Go to https://supabase.com and create account
2. Create new project
3. Copy Project URL and anon key
4. Run this script to set environment variables
5. Create tables using the SQL below

REQUIRED ENVIRONMENT VARIABLES:
- SUPABASE_URL=https://your-project.supabase.co  
- SUPABASE_ANON_KEY=your-anon-key

SQL TO RUN IN SUPABASE SQL EDITOR:
"""

SQL_SCHEMA = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    tg_user_id BIGINT UNIQUE NOT NULL,
    gender TEXT,
    age INTEGER,
    country TEXT,
    city TEXT,
    is_premium BOOLEAN DEFAULT FALSE,
    premium_until TIMESTAMPTZ,
    search_pref TEXT DEFAULT 'any',
    feed_notify BOOLEAN DEFAULT TRUE,
    language TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User interests junction table  
CREATE TABLE IF NOT EXISTS user_interests (
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    interest_key TEXT NOT NULL,
    PRIMARY KEY (user_id, interest_key)
);

-- Confessions table
CREATE TABLE IF NOT EXISTS confessions (
    id BIGSERIAL PRIMARY KEY,
    author_id BIGINT NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    delivered BOOLEAN DEFAULT FALSE,
    delivered_to BIGINT,
    delivered_at TIMESTAMPTZ,
    system_seed BOOLEAN DEFAULT FALSE
);

-- Blocked users table
CREATE TABLE IF NOT EXISTS blocked_users (
    user_id BIGINT NOT NULL,
    blocked_uid BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, blocked_uid)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_tg_user_id ON users(tg_user_id);
CREATE INDEX IF NOT EXISTS idx_confessions_delivered ON confessions(delivered) WHERE delivered = FALSE;
CREATE INDEX IF NOT EXISTS idx_confessions_author ON confessions(author_id);
CREATE INDEX IF NOT EXISTS idx_user_interests_user_id ON user_interests(user_id);

-- Enable Row Level Security (optional)
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE confessions ENABLE ROW LEVEL SECURITY;
"""

def setup_env_file():
    """Create .env file template"""
    env_content = """# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# Keep existing settings
BOT_TOKEN=your-bot-token
DATABASE_URL=your-existing-db-url
"""
    
    with open('.env.supabase', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env.supabase template")
    print("📝 Edit the file with your Supabase credentials")

def print_instructions():
    print("🚀 SUPABASE MIGRATION SETUP")
    print("=" * 50)
    print("1. Create Supabase account: https://supabase.com")
    print("2. Create new project")
    print("3. Copy Project URL and anon key") 
    print("4. Edit .env.supabase with your credentials")
    print("5. Run the SQL schema in Supabase SQL editor")
    print("6. Test the migration")
    print()
    print("SQL SCHEMA TO COPY:")
    print("-" * 30)
    print(SQL_SCHEMA)
    print("-" * 30)
    
if __name__ == "__main__":
    setup_env_file()
    print_instructions()