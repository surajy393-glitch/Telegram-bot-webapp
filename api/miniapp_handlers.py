"""
LuvHive Mini App API Handlers
Instagram-style social media endpoints for Telegram Mini App
"""

import os
import json
import hashlib
import hmac
import base64
import time
from datetime import datetime, timedelta
from urllib.parse import unquote
from typing import Optional, Dict, Any, List
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header, Request
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import registration as reg


# Initialize FastAPI app
app = FastAPI(title="LuvHive Mini App API", version="1.0.0")

# Add CORS middleware with restricted origins for security
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
ALLOWED_ORIGINS = []

# Add development origins
if os.environ.get("DEVELOPMENT"):
    ALLOWED_ORIGINS.extend([
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "https://localhost:5000"
    ])

# Add production origin
if WEBAPP_URL:
    ALLOWED_ORIGINS.append(WEBAPP_URL)
    # Also allow without trailing slash
    if WEBAPP_URL.endswith('/'):
        ALLOWED_ORIGINS.append(WEBAPP_URL.rstrip('/'))
    else:
        ALLOWED_ORIGINS.append(WEBAPP_URL + '/')

# Fallback for development if no WEBAPP_URL set
if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["https://your-repl-name.repl.co"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # SECURITY: Restricted to Mini App origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiting storage (use Redis in production)
rate_limit_storage = defaultdict(lambda: deque())

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting: 60 requests per minute per IP"""
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    # Clean old requests (older than 1 minute)
    user_requests = rate_limit_storage[client_ip]
    while user_requests and user_requests[0] < current_time - 60:
        user_requests.popleft()
    
    # Check rate limit for write operations
    if request.method in ["POST", "PUT", "DELETE"]:
        if len(user_requests) >= 30:  # 30 writes per minute
            raise HTTPException(status_code=429, detail="Rate limit exceeded - too many requests")
        user_requests.append(current_time)
    elif len(user_requests) >= 60:  # 60 total requests per minute
        raise HTTPException(status_code=429, detail="Rate limit exceeded - too many requests")
        
    if request.method == "GET":
        user_requests.append(current_time)
    
    response = await call_next(request)
    return response

# Security
security = HTTPBearer()
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Pydantic models
class User(BaseModel):
    id: int
    username: Optional[str]
    name: str
    avatar: Optional[str]

class PostCounts(BaseModel):
    likes: int = 0
    comments: int = 0
    views: int = 0

class Post(BaseModel):
    id: int
    author: User
    created_at: str
    type: str  # photo, video, text
    media_url: Optional[str] = None
    caption: Optional[str] = None
    liked: bool = False
    saved: bool = False
    counts: PostCounts
    badges: Dict[str, Any] = {}
    ttl_hours_left: Optional[int] = None

class Comment(BaseModel):
    id: int
    author: User
    text: str
    created_at: str
    parent_id: Optional[int] = None

class Profile(BaseModel):
    id: int
    username: Optional[str]
    name: str
    avatar: Optional[str]
    bio: Optional[str]
    post_count: int = 0
    follower_count: int = 0
    following_count: int = 0
    is_following: bool = False
    is_private: bool = False
    active_profile_id: Optional[int] = None

class FeedResponse(BaseModel):
    items: List[Post]
    next_cursor: Optional[str] = None

class CommentsResponse(BaseModel):
    items: List[Comment]
    next_cursor: Optional[str] = None


def verify_telegram_auth(init_data: str) -> Optional[Dict]:
    """Verify Telegram WebApp initData authenticity using proper Telegram algorithm"""
    if not init_data or not BOT_TOKEN:
        return None
    
    try:
        # Parse the init data
        parsed_data = {}
        received_hash = ""
        
        for item in init_data.split('&'):
            if '=' in item:
                key, value = item.split('=', 1)
                key = unquote(key)
                value = unquote(value)
                
                if key == 'hash':
                    received_hash = value
                else:
                    parsed_data[key] = value
        
        if not received_hash:
            return None
        
        # Create data_check_string with ALPHABETICAL SORTING (Telegram requirement)
        sorted_items = []
        for key in sorted(parsed_data.keys()):  # CRITICAL: Must be alphabetically sorted!
            sorted_items.append(f"{key}={parsed_data[key]}")
        
        data_check_string = '\n'.join(sorted_items)
        
        # Create the secret key using proper Telegram algorithm
        secret_key = hmac.new(
            "WebAppData".encode(), 
            BOT_TOKEN.encode(), 
            hashlib.sha256
        ).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Verify hash - use constant time comparison for security
        if hmac.compare_digest(calculated_hash, received_hash):
            # Parse user data if present
            if 'user' in parsed_data:
                try:
                    user_data = json.loads(parsed_data['user'])
                    return user_data
                except json.JSONDecodeError:
                    return None
            return parsed_data
        
        print(f"Auth verification failed: hash mismatch")
        return None
        
    except Exception as e:
        print(f"Auth verification error: {e}")
        return None


def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None)
) -> Dict:
    """Dependency to get current authenticated user"""
    
    # Verify Telegram auth - PRODUCTION READY
    if x_telegram_init_data:
        user_data = verify_telegram_auth(x_telegram_init_data)
        if user_data:
            return user_data
    
    # SECURITY: Only allow dev fallback in explicit development mode
    if os.environ.get("DEVELOPMENT") == "true":
        print("⚠️ WARNING: Using development auth fallback - NOT FOR PRODUCTION!")
        return {"id": 123456789, "first_name": "DevTest", "username": "devuser"}
    
    # Production: Reject unauthenticated requests
    raise HTTPException(
        status_code=401, 
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"}
    )


def ensure_miniapp_tables():
    """Create mini app specific database tables with production-ready constraints and indexes"""
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Mini app posts table with proper constraints
            cur.execute("""
                CREATE TABLE IF NOT EXISTS miniapp_posts (
                    id BIGSERIAL PRIMARY KEY,
                    author_id BIGINT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'text' CHECK (type IN ('text', 'photo', 'video')),
                    caption TEXT CHECK (LENGTH(caption) <= 2000),
                    media_url TEXT,
                    media_type TEXT,
                    visibility TEXT NOT NULL DEFAULT 'public' CHECK (visibility IN ('public', 'followers', 'private')),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT valid_media CHECK (
                        (type = 'text' AND media_url IS NULL) OR 
                        (type IN ('photo', 'video') AND media_url IS NOT NULL)
                    )
                );
            """)
            
            # Likes table with conflict prevention
            cur.execute("""
                CREATE TABLE IF NOT EXISTS miniapp_likes (
                    post_id BIGINT NOT NULL REFERENCES miniapp_posts(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (post_id, user_id)
                );
            """)
            
            # Comments table with text length limits
            cur.execute("""
                CREATE TABLE IF NOT EXISTS miniapp_comments (
                    id BIGSERIAL PRIMARY KEY,
                    post_id BIGINT NOT NULL REFERENCES miniapp_posts(id) ON DELETE CASCADE,
                    author_id BIGINT NOT NULL,
                    text TEXT NOT NULL CHECK (LENGTH(text) >= 1 AND LENGTH(text) <= 500),
                    parent_id BIGINT REFERENCES miniapp_comments(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            
            # Saves table with TTL enforcement
            cur.execute("""
                CREATE TABLE IF NOT EXISTS miniapp_saves (
                    post_id BIGINT NOT NULL REFERENCES miniapp_posts(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '72 hours',
                    PRIMARY KEY (post_id, user_id),
                    CHECK (expires_at > created_at)
                );
            """)
            
            # Follows table with self-follow prevention
            cur.execute("""
                CREATE TABLE IF NOT EXISTS miniapp_follows (
                    follower_id BIGINT NOT NULL,
                    followee_id BIGINT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    status TEXT NOT NULL DEFAULT 'approved' CHECK (status IN ('approved', 'pending')),
                    PRIMARY KEY (follower_id, followee_id),
                    CHECK (follower_id != followee_id)
                );
            """)
            
            # Post views for hide-seen functionality with unique constraint
            cur.execute("""
                CREATE TABLE IF NOT EXISTS miniapp_post_views (
                    post_id BIGINT NOT NULL REFERENCES miniapp_posts(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL,
                    viewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (post_id, user_id)
                );
            """)
            
            # User profiles with username constraints
            cur.execute("""
                CREATE TABLE IF NOT EXISTS miniapp_profiles (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT UNIQUE CHECK (username IS NULL OR (LENGTH(username) >= 3 AND LENGTH(username) <= 30)),
                    display_name TEXT CHECK (display_name IS NULL OR LENGTH(display_name) <= 100),
                    bio TEXT CHECK (bio IS NULL OR LENGTH(bio) <= 500),
                    avatar_url TEXT,
                    is_private BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            
            # CRITICAL: Production-ready composite indexes for cursor pagination and performance
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_posts_created_id ON miniapp_posts(created_at DESC, id DESC);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_posts_author_created_id ON miniapp_posts(author_id, created_at DESC, id DESC);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_posts_visibility_created ON miniapp_posts(visibility, created_at DESC) WHERE visibility = 'public';")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_posts_ttl ON miniapp_posts(created_at);")
            
            # Likes optimization
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_likes_post_created ON miniapp_likes(post_id, created_at DESC);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_likes_user ON miniapp_likes(user_id, created_at DESC);")
            
            # Comments optimization
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_comments_post_created ON miniapp_comments(post_id, created_at DESC);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_comments_author ON miniapp_comments(author_id, created_at DESC);")
            
            # Follows optimization for feed queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_follows_follower_status ON miniapp_follows(follower_id, status) WHERE status = 'approved';")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_follows_followee_status ON miniapp_follows(followee_id, status) WHERE status = 'approved';")
            
            # Saves optimization with TTL cleanup
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_saves_user_expires ON miniapp_saves(user_id, expires_at DESC);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_saves_expires ON miniapp_saves(expires_at);")
            
            # Post views optimization for hide-seen queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_post_views_user_viewed ON miniapp_post_views(user_id, viewed_at DESC);")
            
            # Profile optimization
            cur.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_profiles_username ON miniapp_profiles(username) WHERE username IS NOT NULL;")
            
            # TTL cleanup function for expired saves
            cur.execute("""
                CREATE OR REPLACE FUNCTION cleanup_expired_saves() RETURNS void AS $$
                BEGIN
                    DELETE FROM miniapp_saves WHERE expires_at <= NOW();
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            con.commit()
            print("✅ Mini app database tables created with production-ready constraints and indexes")
            
    except Exception as e:
        print(f"❌ Failed to create mini app tables: {e}")


def get_user_profile(user_id: int) -> Dict:
    """Get user profile data"""
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Try to get from miniapp_profiles first
            cur.execute("""
                SELECT username, display_name, bio, avatar_url, is_private
                FROM miniapp_profiles 
                WHERE user_id = %s
            """, (user_id,))
            profile = cur.fetchone()
            
            if not profile:
                # Fallback to main users table
                cur.execute("""
                    SELECT COALESCE(feed_username, ''), COALESCE(feed_username, ''), '', '', FALSE
                    FROM users 
                    WHERE tg_user_id = %s
                """, (user_id,))
                profile = cur.fetchone()
            
            # Get active_profile_id from users table
            cur.execute("""
                SELECT active_profile_id
                FROM users 
                WHERE tg_user_id = %s
            """, (user_id,))
            active_profile_result = cur.fetchone()
            active_profile_id = active_profile_result[0] if active_profile_result else None
            
            if profile:
                username, display_name, bio, avatar_url, is_private = profile
                return {
                    "id": user_id,
                    "username": username or None,
                    "name": display_name or f"User{user_id}",
                    "avatar": avatar_url,
                    "bio": bio,
                    "is_private": bool(is_private),
                    "active_profile_id": active_profile_id
                }
            
            # Create default profile
            return {
                "id": user_id,
                "username": None,
                "name": f"User{user_id}",
                "avatar": None,
                "bio": None,
                "is_private": False,
                "active_profile_id": active_profile_id
            }
            
    except Exception as e:
        print(f"Error getting profile: {e}")
        return {
            "id": user_id,
            "username": None,
            "name": f"User{user_id}",
            "avatar": None,
            "bio": None,
            "is_private": False,
            "active_profile_id": None
        }


def get_post_counts(post_id: int) -> Dict[str, int]:
    """Get like, comment, view counts for a post"""
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Get counts in one query
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM miniapp_likes WHERE post_id = %s) as likes,
                    (SELECT COUNT(*) FROM miniapp_comments WHERE post_id = %s) as comments,
                    (SELECT COUNT(*) FROM miniapp_post_views WHERE post_id = %s) as views
            """, (post_id, post_id, post_id))
            
            result = cur.fetchone()
            if result:
                likes, comments, views = result
                return {"likes": likes or 0, "comments": comments or 0, "views": views or 0}
            
            return {"likes": 0, "comments": 0, "views": 0}
            
    except Exception as e:
        print(f"Error getting post counts: {e}")
        return {"likes": 0, "comments": 0, "views": 0}


def check_user_post_interactions(user_id: int, post_id: int) -> Dict[str, bool]:
    """Check if user liked/saved a post"""
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM miniapp_likes WHERE post_id = %s AND user_id = %s) > 0 as liked,
                    (SELECT COUNT(*) FROM miniapp_saves WHERE post_id = %s AND user_id = %s AND expires_at > NOW()) > 0 as saved
            """, (post_id, user_id, post_id, user_id))
            
            result = cur.fetchone()
            if result:
                liked, saved = result
                return {"liked": bool(liked), "saved": bool(saved)}
            
            return {"liked": False, "saved": False}
            
    except Exception as e:
        print(f"Error checking interactions: {e}")
        return {"liked": False, "saved": False}


def calculate_ttl_hours(created_at: datetime) -> Optional[int]:
    """Calculate hours left for 72-hour TTL"""
    try:
        now = datetime.now(created_at.tzinfo) if created_at.tzinfo else datetime.now()
        ttl_deadline = created_at + timedelta(hours=72)
        
        if now >= ttl_deadline:
            return 0
        
        hours_left = int((ttl_deadline - now).total_seconds() / 3600)
        return max(0, hours_left)
        
    except Exception:
        return None


# Initialize tables on startup
ensure_miniapp_tables()

# =============================================================================
# API ROUTES
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "app": "LuvHive Mini App API"}


@app.get("/api/me", response_model=Profile)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's profile"""
    user_id = current_user["id"]
    profile_data = get_user_profile(user_id)
    
    # Get post/follower counts
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM miniapp_posts WHERE author_id = %s) as post_count,
                    (SELECT COUNT(*) FROM miniapp_follows WHERE followee_id = %s) as follower_count,
                    (SELECT COUNT(*) FROM miniapp_follows WHERE follower_id = %s) as following_count
            """, (user_id, user_id, user_id))
            
            result = cur.fetchone()
            if result:
                post_count, follower_count, following_count = result
                profile_data.update({
                    "post_count": post_count or 0,
                    "follower_count": follower_count or 0,
                    "following_count": following_count or 0
                })
    except Exception as e:
        print(f"Error getting profile counts: {e}")
    
    return Profile(**profile_data)


@app.get("/api/users/{user_id}", response_model=Profile)
async def get_user_profile_api(user_id: int, current_user: dict = Depends(get_current_user)):
    """Get another user's profile"""
    profile_data = get_user_profile(user_id)
    current_user_id = current_user["id"]
    
    # Check if current user follows this user
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM miniapp_posts WHERE author_id = %s) as post_count,
                    (SELECT COUNT(*) FROM miniapp_follows WHERE followee_id = %s) as follower_count,
                    (SELECT COUNT(*) FROM miniapp_follows WHERE follower_id = %s) as following_count,
                    (SELECT COUNT(*) FROM miniapp_follows WHERE follower_id = %s AND followee_id = %s) > 0 as is_following
            """, (user_id, user_id, user_id, current_user_id, user_id))
            
            result = cur.fetchone()
            if result:
                post_count, follower_count, following_count, is_following = result
                profile_data.update({
                    "post_count": post_count or 0,
                    "follower_count": follower_count or 0,
                    "following_count": following_count or 0,
                    "is_following": bool(is_following)
                })
    except Exception as e:
        print(f"Error getting profile data: {e}")
    
    return Profile(**profile_data)


@app.get("/api/feed", response_model=FeedResponse)
async def get_feed(
    tab: str = "following",
    cursor: Optional[str] = None,
    limit: int = 20,
    hide_seen: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get feed posts (following or explore)"""
    user_id = current_user["id"]
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Base query components
            where_conditions = ["mp.created_at > NOW() - INTERVAL '72 hours'"]  # 72-hour TTL
            params = []
            
            if tab == "following":
                # Get posts from users we follow
                where_conditions.append("""
                    mp.author_id IN (
                        SELECT followee_id FROM miniapp_follows 
                        WHERE follower_id = %s AND status = 'approved'
                    )
                """)
                params.append(user_id)
                order_by = "mp.created_at DESC"
            else:  # explore
                # Get public posts, ranked by engagement
                where_conditions.append("mp.visibility = 'public'")
                # Exclude own posts in explore
                where_conditions.append("mp.author_id != %s")
                params.append(user_id)
                order_by = "mp.created_at DESC"  # Simple for now, can add ranking later
            
            if hide_seen:
                # Exclude posts the user has already seen
                where_conditions.append("""
                    mp.id NOT IN (
                        SELECT post_id FROM miniapp_post_views 
                        WHERE user_id = %s
                    )
                """)
                params.append(user_id)
            
            # Cursor pagination
            if cursor:
                try:
                    decoded_cursor = base64.b64decode(cursor).decode()
                    cursor_time, cursor_id = decoded_cursor.split(',')
                    where_conditions.append("(mp.created_at, mp.id) < (%s, %s)")
                    params.extend([cursor_time, int(cursor_id)])
                except:
                    pass  # Invalid cursor, ignore
            
            # Build final query
            where_clause = " AND ".join(where_conditions)
            query = f"""
                SELECT mp.id, mp.author_id, mp.type, mp.caption, mp.media_url, mp.created_at
                FROM miniapp_posts mp
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT %s
            """
            params.append(limit + 1)  # +1 to check if there are more
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            # Process results
            posts = []
            has_more = len(rows) > limit
            if has_more:
                rows = rows[:-1]  # Remove the extra row
            
            for row in rows:
                post_id, author_id, post_type, caption, media_url, created_at = row
                
                # Get author profile
                author_profile = get_user_profile(author_id)
                
                # Get post counts
                counts = get_post_counts(post_id)
                
                # Check user interactions
                interactions = check_user_post_interactions(user_id, post_id)
                
                # Calculate TTL
                ttl_hours = calculate_ttl_hours(created_at)
                
                # Track view
                try:
                    cur.execute("""
                        INSERT INTO miniapp_post_views (post_id, user_id) 
                        VALUES (%s, %s) 
                        ON CONFLICT DO NOTHING
                    """, (post_id, user_id))
                except:
                    pass  # Ignore view tracking errors
                
                post = Post(
                    id=post_id,
                    author=User(**author_profile),
                    created_at=created_at.isoformat(),
                    type=post_type,
                    media_url=media_url,
                    caption=caption,
                    liked=interactions["liked"],
                    saved=interactions["saved"],
                    counts=PostCounts(**counts),
                    ttl_hours_left=ttl_hours
                )
                posts.append(post)
            
            # Generate next cursor
            next_cursor = None
            if has_more and posts:
                last_post = posts[-1]
                cursor_data = f"{last_post.created_at},{last_post.id}"
                next_cursor = base64.b64encode(cursor_data.encode()).decode()
            
            con.commit()  # Commit view tracking
            
            return FeedResponse(items=posts, next_cursor=next_cursor)
            
    except Exception as e:
        print(f"Error getting feed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load feed")


@app.post("/api/posts")
async def create_post(
    caption: str = Form(""),
    type: str = Form("text"),
    media: UploadFile = File(None),
    current_user: dict = Depends(get_current_user)
):
    """Create a new post"""
    user_id = current_user["id"]
    
    try:
        media_url = None
        media_type = None
        
        # Handle media upload
        if media and media.filename:
            # Validate file size (10MB max)
            content = await media.read()
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="File too large (max 10MB)")
            
            # For now, we'll just store the filename
            # In production, you'd upload to S3/CDN and store the URL
            media_url = f"/uploads/{media.filename}"
            media_type = media.content_type
        
        # Create post
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                INSERT INTO miniapp_posts (author_id, type, caption, media_url, media_type)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (user_id, type, caption or None, media_url, media_type))
            
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=500, detail="Failed to create post")
            
            post_id, created_at = result
            con.commit()
            
            return {"id": post_id, "created_at": created_at.isoformat(), "status": "created"}
            
    except Exception as e:
        print(f"Error creating post: {e}")
        raise HTTPException(status_code=500, detail="Failed to create post")


@app.get("/api/posts/{post_id}", response_model=Post)
async def get_post(post_id: int, current_user: dict = Depends(get_current_user)):
    """Get a specific post"""
    user_id = current_user["id"]
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("""
                SELECT mp.id, mp.author_id, mp.type, mp.caption, mp.media_url, mp.created_at
                FROM miniapp_posts mp
                WHERE mp.id = %s
            """, (post_id,))
            
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Post not found")
            
            post_id, author_id, post_type, caption, media_url, created_at = row
            
            # Get author profile
            author_profile = get_user_profile(author_id)
            
            # Get post counts
            counts = get_post_counts(post_id)
            
            # Check user interactions
            interactions = check_user_post_interactions(user_id, post_id)
            
            # Calculate TTL
            ttl_hours = calculate_ttl_hours(created_at)
            
            # Track view
            try:
                cur.execute("""
                    INSERT INTO miniapp_post_views (post_id, user_id) 
                    VALUES (%s, %s) 
                    ON CONFLICT DO NOTHING
                """, (post_id, user_id))
                con.commit()
            except:
                pass
            
            post = Post(
                id=post_id,
                author=User(**author_profile),
                created_at=created_at.isoformat(),
                type=post_type,
                media_url=media_url,
                caption=caption,
                liked=interactions["liked"],
                saved=interactions["saved"],
                counts=PostCounts(**counts),
                ttl_hours_left=ttl_hours
            )
            
            return post
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting post: {e}")
        raise HTTPException(status_code=500, detail="Failed to get post")


@app.post("/api/posts/{post_id}/like")
async def toggle_like(post_id: int, current_user: dict = Depends(get_current_user)):
    """Toggle like on a post"""
    user_id = current_user["id"]
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Check if already liked
            cur.execute("""
                SELECT COUNT(*) FROM miniapp_likes 
                WHERE post_id = %s AND user_id = %s
            """, (post_id, user_id))
            
            is_liked = cur.fetchone()[0] > 0
            
            if is_liked:
                # Unlike
                cur.execute("""
                    DELETE FROM miniapp_likes 
                    WHERE post_id = %s AND user_id = %s
                """, (post_id, user_id))
                action = "unliked"
            else:
                # Like
                cur.execute("""
                    INSERT INTO miniapp_likes (post_id, user_id) 
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (post_id, user_id))
                action = "liked"
            
            # Get new count
            cur.execute("""
                SELECT COUNT(*) FROM miniapp_likes WHERE post_id = %s
            """, (post_id,))
            new_count = cur.fetchone()[0]
            
            con.commit()
            
            return {"action": action, "liked": not is_liked, "count": new_count}
            
    except Exception as e:
        print(f"Error toggling like: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle like")


@app.post("/api/posts/{post_id}/save")
async def toggle_save(post_id: int, current_user: dict = Depends(get_current_user)):
    """Toggle save on a post"""
    user_id = current_user["id"]
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Check if already saved (and not expired)
            cur.execute("""
                SELECT COUNT(*) FROM miniapp_saves 
                WHERE post_id = %s AND user_id = %s AND expires_at > NOW()
            """, (post_id, user_id))
            
            is_saved = cur.fetchone()[0] > 0
            
            if is_saved:
                # Unsave
                cur.execute("""
                    DELETE FROM miniapp_saves 
                    WHERE post_id = %s AND user_id = %s
                """, (post_id, user_id))
                action = "unsaved"
            else:
                # Save (72-hour expiry)
                cur.execute("""
                    INSERT INTO miniapp_saves (post_id, user_id, expires_at) 
                    VALUES (%s, %s, NOW() + INTERVAL '72 hours')
                    ON CONFLICT (post_id, user_id) DO UPDATE SET
                    expires_at = NOW() + INTERVAL '72 hours'
                """, (post_id, user_id))
                action = "saved"
            
            con.commit()
            
            return {"action": action, "saved": not is_saved}
            
    except Exception as e:
        print(f"Error toggling save: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle save")


@app.get("/api/posts/{post_id}/comments", response_model=CommentsResponse)
async def get_comments(
    post_id: int, 
    cursor: Optional[str] = None, 
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get comments for a post"""
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Build query with cursor pagination
            where_conditions = ["post_id = %s", "parent_id IS NULL"]  # Only top-level comments for now
            params = [post_id]
            
            if cursor:
                try:
                    decoded_cursor = base64.b64decode(cursor).decode()
                    cursor_time, cursor_id = decoded_cursor.split(',')
                    where_conditions.append("(created_at, id) < (%s, %s)")
                    params.extend([cursor_time, int(cursor_id)])
                except:
                    pass
            
            where_clause = " AND ".join(where_conditions)
            query = f"""
                SELECT id, author_id, text, created_at, parent_id
                FROM miniapp_comments
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            """
            params.append(limit + 1)
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            # Process results
            comments = []
            has_more = len(rows) > limit
            if has_more:
                rows = rows[:-1]
            
            for row in rows:
                comment_id, author_id, text, created_at, parent_id = row
                
                # Get author profile
                author_profile = get_user_profile(author_id)
                
                comment = Comment(
                    id=comment_id,
                    author=User(**author_profile),
                    text=text,
                    created_at=created_at.isoformat(),
                    parent_id=parent_id
                )
                comments.append(comment)
            
            # Generate next cursor
            next_cursor = None
            if has_more and comments:
                last_comment = comments[-1]
                cursor_data = f"{last_comment.created_at},{last_comment.id}"
                next_cursor = base64.b64encode(cursor_data.encode()).decode()
            
            return CommentsResponse(items=comments, next_cursor=next_cursor)
            
    except Exception as e:
        print(f"Error getting comments: {e}")
        raise HTTPException(status_code=500, detail="Failed to get comments")


@app.post("/api/posts/{post_id}/comments", response_model=Comment)
async def create_comment(
    post_id: int,
    comment_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create a comment on a post"""
    user_id = current_user["id"]
    text = comment_data.get("text", "").strip()
    
    if not text:
        raise HTTPException(status_code=400, detail="Comment text is required")
    
    if len(text) > 500:
        raise HTTPException(status_code=400, detail="Comment too long (max 500 characters)")
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Create comment
            cur.execute("""
                INSERT INTO miniapp_comments (post_id, author_id, text)
                VALUES (%s, %s, %s)
                RETURNING id, created_at
            """, (post_id, user_id, text))
            
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=500, detail="Failed to create comment")
            
            comment_id, created_at = result
            con.commit()
            
            # Get author profile
            author_profile = get_user_profile(user_id)
            
            comment = Comment(
                id=comment_id,
                author=User(**author_profile),
                text=text,
                created_at=created_at.isoformat(),
                parent_id=None
            )
            
            return comment
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating comment: {e}")
        raise HTTPException(status_code=500, detail="Failed to create comment")


@app.post("/api/follow/{user_id}")
async def toggle_follow(user_id: int, current_user: dict = Depends(get_current_user)):
    """Toggle follow/unfollow a user"""
    follower_id = current_user["id"]
    
    if follower_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Check if already following
            cur.execute("""
                SELECT COUNT(*) FROM miniapp_follows 
                WHERE follower_id = %s AND followee_id = %s
            """, (follower_id, user_id))
            
            is_following = cur.fetchone()[0] > 0
            
            if is_following:
                # Unfollow
                cur.execute("""
                    DELETE FROM miniapp_follows 
                    WHERE follower_id = %s AND followee_id = %s
                """, (follower_id, user_id))
                action = "unfollowed"
            else:
                # Follow
                cur.execute("""
                    INSERT INTO miniapp_follows (follower_id, followee_id, status)
                    VALUES (%s, %s, 'approved')
                    ON CONFLICT DO NOTHING
                """, (follower_id, user_id))
                action = "followed"
            
            con.commit()
            
            return {"action": action, "following": not is_following}
            
    except Exception as e:
        print(f"Error toggling follow: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle follow")


@app.get("/api/saved", response_model=FeedResponse)
async def get_saved_posts(
    cursor: Optional[str] = None,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get user's saved posts"""
    user_id = current_user["id"]
    
    try:
        with reg._conn() as con, con.cursor() as cur:
            # Get saved posts that haven't expired
            where_conditions = ["ms.user_id = %s", "ms.expires_at > NOW()"]
            params = [user_id]
            
            if cursor:
                try:
                    decoded_cursor = base64.b64decode(cursor).decode()
                    cursor_time, cursor_id = decoded_cursor.split(',')
                    where_conditions.append("(ms.created_at, ms.post_id) < (%s, %s)")
                    params.extend([cursor_time, int(cursor_id)])
                except:
                    pass
            
            where_clause = " AND ".join(where_conditions)
            query = f"""
                SELECT mp.id, mp.author_id, mp.type, mp.caption, mp.media_url, mp.created_at
                FROM miniapp_saves ms
                JOIN miniapp_posts mp ON ms.post_id = mp.id
                WHERE {where_clause}
                ORDER BY ms.created_at DESC
                LIMIT %s
            """
            params.append(limit + 1)
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            # Process results (similar to feed)
            posts = []
            has_more = len(rows) > limit
            if has_more:
                rows = rows[:-1]
            
            for row in rows:
                post_id, author_id, post_type, caption, media_url, created_at = row
                
                author_profile = get_user_profile(author_id)
                counts = get_post_counts(post_id)
                interactions = check_user_post_interactions(user_id, post_id)
                ttl_hours = calculate_ttl_hours(created_at)
                
                post = Post(
                    id=post_id,
                    author=User(**author_profile),
                    created_at=created_at.isoformat(),
                    type=post_type,
                    media_url=media_url,
                    caption=caption,
                    liked=interactions["liked"],
                    saved=interactions["saved"],
                    counts=PostCounts(**counts),
                    ttl_hours_left=ttl_hours
                )
                posts.append(post)
            
            # Generate next cursor
            next_cursor = None
            if has_more and posts:
                last_post = posts[-1]
                cursor_data = f"{last_post.created_at},{last_post.id}"
                next_cursor = base64.b64encode(cursor_data.encode()).decode()
            
            return FeedResponse(items=posts, next_cursor=next_cursor)
            
    except Exception as e:
        print(f"Error getting saved posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get saved posts")


# Add CORS and error handling
from fastapi.responses import JSONResponse

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"error": "Endpoint not found"})

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)