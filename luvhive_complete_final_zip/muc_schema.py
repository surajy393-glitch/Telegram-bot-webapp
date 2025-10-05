# muc_schema.py - Midnight University Chronicles Database Schema
# Complete database schema for the MUC story system

import logging
import psycopg2
from registration import _conn

log = logging.getLogger(__name__)

def ensure_muc_tables():
    """
    Create all Midnight University Chronicles tables with proper constraints and indexes.
    Called during startup to ensure the complete MUC story system schema exists.
    """
    try:
        with _conn() as con, con.cursor() as cur:
            log.info("Creating Midnight University Chronicles database schema...")
            
            # 1. MUC Series Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muc_series (
                    id SERIAL PRIMARY KEY,
                    slug TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            # 2. MUC Episodes Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muc_episodes (
                    id SERIAL PRIMARY KEY,
                    series_id INTEGER NOT NULL REFERENCES muc_series(id) ON DELETE CASCADE,
                    idx INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    teaser_md TEXT,
                    body_md TEXT,
                    cliff_md TEXT,
                    publish_at TIMESTAMPTZ,
                    close_at TIMESTAMPTZ,
                    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'voting', 'closed')),
                    UNIQUE(series_id, idx)
                );
            """)
            
            # 3. MUC Polls Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muc_polls (
                    id SERIAL PRIMARY KEY,
                    episode_id INTEGER NOT NULL REFERENCES muc_episodes(id) ON DELETE CASCADE,
                    prompt TEXT NOT NULL,
                    layer TEXT NOT NULL DEFAULT 'surface' CHECK (layer IN ('surface', 'deeper', 'deepest')),
                    allow_multi BOOLEAN DEFAULT FALSE
                );
            """)
            
            # 4. MUC Poll Options Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muc_poll_options (
                    id SERIAL PRIMARY KEY,
                    poll_id INTEGER NOT NULL REFERENCES muc_polls(id) ON DELETE CASCADE,
                    opt_key TEXT NOT NULL,
                    text TEXT NOT NULL,
                    next_hint TEXT
                );
            """)
            
            # 5. MUC Votes Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muc_votes (
                    id SERIAL PRIMARY KEY,
                    poll_id INTEGER NOT NULL REFERENCES muc_polls(id) ON DELETE CASCADE,
                    option_id INTEGER NOT NULL REFERENCES muc_poll_options(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(user_id, poll_id)
                );
            """)
            
            # 6. MUC Characters Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muc_characters (
                    id SERIAL PRIMARY KEY,
                    series_id INTEGER NOT NULL REFERENCES muc_series(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    bio_md TEXT,
                    attributes JSONB DEFAULT '{}',
                    secrets JSONB DEFAULT '{}'
                );
            """)
            
            # 7. MUC Character Questions Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muc_char_questions (
                    id SERIAL PRIMARY KEY,
                    series_id INTEGER NOT NULL REFERENCES muc_series(id) ON DELETE CASCADE,
                    prompt TEXT NOT NULL,
                    question_key TEXT NOT NULL,
                    active_from_episode_id INTEGER REFERENCES muc_episodes(id) ON DELETE SET NULL
                );
            """)
            
            # 8. MUC Character Options Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muc_char_options (
                    id SERIAL PRIMARY KEY,
                    question_id INTEGER NOT NULL REFERENCES muc_char_questions(id) ON DELETE CASCADE,
                    opt_key TEXT NOT NULL,
                    text TEXT NOT NULL
                );
            """)
            
            # 9. MUC Character Votes Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muc_char_votes (
                    id SERIAL PRIMARY KEY,
                    question_id INTEGER NOT NULL REFERENCES muc_char_questions(id) ON DELETE CASCADE,
                    option_id INTEGER NOT NULL REFERENCES muc_char_options(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(user_id, question_id)
                );
            """)
            
            # 10. MUC Theories Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muc_theories (
                    id SERIAL PRIMARY KEY,
                    episode_id INTEGER NOT NULL REFERENCES muc_episodes(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    text TEXT NOT NULL,
                    likes INTEGER DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            # 11. MUC User Engagement Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muc_user_engagement (
                    user_id BIGINT PRIMARY KEY,
                    streak_days INTEGER DEFAULT 0,
                    detective_score INTEGER DEFAULT 0,
                    last_seen_episode_id INTEGER REFERENCES muc_episodes(id) ON DELETE SET NULL
                );
            """)
            
            # Create performance indexes
            log.info("Creating MUC performance indexes...")
            
            # Indexes for fast episode and status queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_episodes_series_status ON muc_episodes(series_id, status);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_episodes_status_publish ON muc_episodes(status, publish_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_episodes_publish_at ON muc_episodes(publish_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_episodes_close_at ON muc_episodes(close_at);")
            
            # Indexes for voting queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_votes_user_id ON muc_votes(user_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_votes_poll_id ON muc_votes(poll_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_char_votes_user_id ON muc_char_votes(user_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_char_votes_question_id ON muc_char_votes(question_id);")
            
            # Indexes for time-based queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_votes_created_at ON muc_votes(created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_char_votes_created_at ON muc_char_votes(created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_theories_created_at ON muc_theories(created_at);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_theories_episode_likes ON muc_theories(episode_id, likes DESC);")
            
            # Indexes for character and poll relationships
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_polls_episode_id ON muc_polls(episode_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_poll_options_poll_id ON muc_poll_options(poll_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_characters_series_id ON muc_characters(series_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_char_questions_series_id ON muc_char_questions(series_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_char_options_question_id ON muc_char_options(question_id);")
            
            # Indexes for engagement tracking
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_user_engagement_detective_score ON muc_user_engagement(detective_score DESC);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_muc_user_engagement_streak ON muc_user_engagement(streak_days DESC);")
            
            con.commit()
            log.info("✅ Midnight University Chronicles database schema created successfully")
            
    except psycopg2.Error as e:
        log.error(f"❌ Failed to create MUC database schema: {e}")
        raise
    except Exception as e:
        log.error(f"❌ Unexpected error creating MUC schema: {e}")
        raise