import os, hmac, hashlib, time, json
from urllib.parse import parse_qsl
from typing import Optional

import aiohttp, httpx, uvicorn, psycopg2
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Path, Query, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse, Response
from pydantic import BaseModel

import registration as reg  # provides _conn() pooled connection (present in your repo)

# ---------- ENV ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
EXTERNAL_URL = (os.environ.get("EXTERNAL_URL") or "").rstrip("/")
MEDIA_SINK_CHAT_ID = int(os.environ.get("MEDIA_SINK_CHAT_ID", "0"))
PUBLIC_TTL_HOURS = int(os.environ.get("FEED_PUBLIC_TTL_HOURS", "72"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
if not EXTERNAL_URL:
    print("WARNING: EXTERNAL_URL is empty; media_proxy_url will be relative")
if not MEDIA_SINK_CHAT_ID:
    print("WARNING: MEDIA_SINK_CHAT_ID not set (image upload will fail)")

# ---------- MODELS ----------
class OnboardRequest(BaseModel):
    display_name: str
    username: str
    age: int
    avatar_file_id: Optional[str] = None

# ---------- APP & CORS ----------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",  # trial: open; tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Preflight ok for all API paths
@app.options("/{rest_of_path:path}")
async def options_ok(rest_of_path: str):
    return PlainTextResponse("ok", status_code=200)

# ---------- initData verification ----------
def verify_init_data(raw: str) -> dict:
    """Telegram WebApp initData HMAC verify."""
    data = dict(parse_qsl(raw, keep_blank_values=True))
    recv_hash = data.pop("hash", None)
    if not recv_hash:
        raise ValueError("no hash")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if calc != recv_hash:
        raise ValueError("bad hash")
    try:
        auth_date = int(data.get("auth_date", "0"))
        if time.time() - auth_date > 86400 * 7:  # 7 days
            raise ValueError("expired")
    except Exception:
        pass
    user = json.loads(data["user"])
    if not user.get("id"):
        raise ValueError("no user id")
    return user

async def get_user(
    request: Request,
    form_sn: Optional[str] = Form(None, alias="init_data"),
    form_cm: Optional[str] = Form(None, alias="initData"),
    q_sn:    Optional[str] = Query(None, alias="init_data"),
    q_cm:    Optional[str] = Query(None, alias="initData"),
):
    # Accept from header too
    hdr = request.headers.get("X-Telegram-Init-Data") or request.headers.get("x-telegram-init-data")
    raw = form_sn or form_cm or q_sn or q_cm or hdr

    # JSON body fallback
    if not raw and "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
            raw = body.get("initData") or body.get("init_data")
        except Exception:
            pass

    if raw:
        try:
            return verify_init_data(raw)
        except Exception as e:
            # continue to dev bypass if enabled
            pass

    # Dev-only bypass (browser preview) - use real data from database
    if os.getenv("ALLOW_INSECURE_TRIAL") == "1":
        # First try X-Dev-User header from frontend for specific user testing
        dev_user_header = request.headers.get("X-Dev-User")
        if dev_user_header:
            dev_uid = int(dev_user_header)
        else:
            # If frontend has user data in Telegram context, detect from request path or use user context
            # This is a better fallback - extract user from URL or request context
            # For now, let's see the request and determine user dynamically
            # No X-Dev-User header provided - use fallback
            dev_uid = 647778438  # Keep as last resort fallback

        # Always use real database data if exists
        with reg._conn() as con, con.cursor() as cur:
            cur.execute("SELECT display_name, username FROM users WHERE tg_user_id=%s", (dev_uid,))
            existing = cur.fetchone()
            if existing:
                return {"id": dev_uid, "first_name": existing[0] or "User", "username": existing[1] or f"user{dev_uid}"}
        # Create new user if doesn't exist
        return {"id": dev_uid, "first_name": "User", "username": f"user{dev_uid}"}

    raise HTTPException(401, "Missing/invalid initData")

# ---------- DB helpers ----------
def get_profile_name(tg_user_id: int, conn) -> str:
    """Unified helper to get user's display name with proper fallback logic"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(
                NULLIF(display_name, ''),
                NULLIF(username, ''),
                NULLIF(feed_username, ''),
                'User' || %s
            ) AS profile_name
            FROM users WHERE tg_user_id = %s
        """, (tg_user_id, tg_user_id))
        row = cur.fetchone()
        return row[0] if row else f"User{tg_user_id}"

def ensure_user(conn, tg_user: dict):
    """Upsert user & profile rows so FK never fails - but don't overwrite existing data."""
    uid = int(tg_user["id"])
    name = tg_user.get("first_name") or "User"
    uname = tg_user.get("username") or f"user{uid}"
    with conn.cursor() as cur:
        # Skip table creation - rely on existing unified users table from bot database
        # Ensure is_onboarded column exists in existing tables
        cur.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS is_onboarded BOOLEAN NOT NULL DEFAULT FALSE
        """)
        # Only insert if user doesn't exist, don't update existing data
        cur.execute("""
            INSERT INTO users (tg_user_id, display_name, username)
            VALUES (%s, %s, %s)
            ON CONFLICT (tg_user_id) DO NOTHING
        """, (uid, name, uname))

def get_or_create_user_id(conn, tg_user: dict) -> int:
    """Return internal users.id (FK used by posts)."""
    ensure_user(conn, tg_user)
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE tg_user_id=%s", (int(tg_user["id"]),))
        row = cur.fetchone()
        if not row:
            # in rare race, insert again
            cur.execute("INSERT INTO users (tg_user_id, display_name, username) VALUES (%s,%s,%s) RETURNING id",
                        (int(tg_user["id"]), tg_user.get("first_name") or "User", tg_user.get("username") or f"user{tg_user['id']}"))
            row = cur.fetchone()
            conn.commit()  # IMPORTANT: Commit the new user creation
    return int(row[0])

# ---------- Profiles helpers ----------
def ensure_profiles_table(conn):
    """
    Create the profiles table and active_profile_id column on users if not present.
    Each profile belongs to a Telegram user (via users.id).  A user can have
    multiple profiles with unique usernames.  One profile per user may be marked as active.
    NOTE: active_profile_id is a plain BIGINT (no FK) to avoid undefined-column errors.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                profile_name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                bio TEXT,
                avatar_url TEXT,
                is_active BOOLEAN DEFAULT FALSE
            )
            """
        )
        cur.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS active_profile_id BIGINT"
        )
        conn.commit()

def get_active_profile(conn, user_id: int):
    """
    Return the active profile (id, profile_name, username, bio, avatar_url, is_active)
    for a given user_id or None if none is active.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, profile_name, username, bio, avatar_url, is_active "
            "FROM profiles WHERE user_id=%s AND is_active=TRUE",
            (user_id,)
        )
        return cur.fetchone()

# ---------- Notifications Helper ----------
def create_notification(con, user_id: int, from_user_id: int, notif_type: str,
                        post_id: Optional[int] = None, comment_id: Optional[int] = None) -> None:
    """
    Persist a notification record for the given recipient.  This helper ensures
    the `notifications` table exists and inserts a new row.  A notification
    describes an action (e.g. "follow", "post_like", "comment_like", "comment")
    performed by `from_user_id` on behalf of `user_id`.  Optionally include
    `post_id` and/or `comment_id` for context.  The `read` flag defaults to
    false so that clients can highlight new items.
    """
    with con.cursor() as cur:
        try:
            print(
                f"DEBUG: Creating notification - user_id={user_id}, from_user_id={from_user_id}, "
                f"type={notif_type}, post_id={post_id}, comment_id={comment_id}"
            )
            # Ensure notifications table exists
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    actor BIGINT REFERENCES users(id),
                    ntype TEXT NOT NULL,
                    post_id BIGINT REFERENCES feed_posts(id) ON DELETE CASCADE,
                    comment_id BIGINT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    "read" BOOLEAN DEFAULT FALSE
                )
                """
            )
            # Add comment_id column if missing (legacy table migration)
            cur.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS comment_id BIGINT")
            print("DEBUG: Notifications table created/verified")
            # Insert notification with comment_id included (may be NULL)
            cur.execute(
                "INSERT INTO notifications (user_id, actor, ntype, post_id, comment_id) VALUES (%s, %s, %s, %s, %s)",
                (user_id, from_user_id, notif_type, post_id, comment_id)
            )
            print(
                f"DEBUG: Notification inserted successfully - rowcount={cur.rowcount}, comment_id={comment_id}"
            )
        except Exception as e:
            print(f"DEBUG: Error in create_notification: {e}")
            raise

# ---------- Media helpers ----------
def media_proxy_url(file_id: str) -> str:
    base = EXTERNAL_URL or ""
    return f"{base}/api/telefile/{file_id}"

# Fallback helper for compatibility
def _media_proxy(file_id: str | None) -> str | None:
    """Fallback helper used when the original is undefined."""
    if not file_id:
        return None
    try:
        return media_proxy_url(file_id)
    except Exception:
        base = EXTERNAL_URL or ""
        return f"{base}/api/telefile/{file_id}"

async def tg_upload_to_sink(file_bytes: bytes, filename: str, mime: str, caption: str) -> str:
    """Send to MEDIA_SINK_CHAT_ID and return file_id."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    form = aiohttp.FormData()
    form.add_field("chat_id", str(MEDIA_SINK_CHAT_ID))
    form.add_field("caption", caption[:1024] if caption else "")
    form.add_field("document", file_bytes, filename=filename or "file", content_type=mime or "application/octet-stream")
    async with aiohttp.ClientSession() as s:
        async with s.post(url, data=form) as r:
            txt = await r.text()
            if r.status != 200:
                raise HTTPException(502, f"Telegram upload failed: {txt}")
            data = json.loads(txt)
            return data["result"]["document"]["file_id"]

@app.get("/api/telefile/{file_id}")
async def telefile(file_id: str):
    """
    Resolve a Telegram file by file_id and return its bytes.  A short timeout is
    enforced to avoid long hangs.  Demo placeholder IDs such as "demo_avatar…"
    return 404 so the client can show a local default avatar.  Network errors
    are caught and logged.
    """
    # Early exit for demo/placeholder avatars used during onboarding. These IDs
    # are not real Telegram file IDs and would cause external calls to time out.
    if file_id.startswith("demo_avatar"):
        raise HTTPException(404, "file not found")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Request file metadata from Telegram
            r = await client.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
                params={"file_id": file_id},
            )
            if r.status_code != 200:
                raise HTTPException(404, "file not found")
            data = r.json()
            if not data.get("ok"):
                raise HTTPException(404, "file not found")
            fp = data.get("result", {}).get("file_path")
            if not fp:
                raise HTTPException(404, "file not found")
            # Download the actual file
            fr = await client.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}")
            if fr.status_code != 200:
                raise HTTPException(404, "file stream error")
            return Response(
                content=fr.content,
                media_type=fr.headers.get("content-type", "application/octet-stream"),
                headers={"Cache-Control": "public, max-age=604800"},
            )
    except httpx.RequestError as exc:
        # Log the network error and return 404 so clients show a fallback
        print(f"telefile request error: {exc}")
        raise HTTPException(404, "file not found")

# ---------- Basic ----------
@app.get("/api/health")
async def health(): return {"ok": True}

# ---------- Me & Onboarding ----------
@app.get("/api/me")
async def me(user=Depends(get_user)):
    with reg._conn() as con:
        # Don't call ensure_user to avoid overwriting existing data
        with con.cursor() as cur:
            # Ensure user_follows table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_follows (
                    follower_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    followee_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (follower_id, followee_id)
                )
            """)

            # Ensure newer optional columns exist before selecting them.  These
            # columns may be added lazily by other endpoints (e.g. profile update).
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS gender TEXT")
            # Select the logged‑in user's record.  Include bio and gender so the
            # front‑end can show updated profile information after editing.  We
            # coalesce bio to an empty string to avoid returning null in JSON.
            cur.execute(
                "SELECT id, display_name, username, age, avatar_url, is_onboarded, active_profile_id, "
                "COALESCE(bio,''), gender "
                "FROM users WHERE tg_user_id=%s",
                (int(user["id"]),)
            )
            row = cur.fetchone()
            if not row:
                # If the user doesn't exist yet, insert a new record with the minimal
                # required information.  We intentionally omit bio, gender and
                # active_profile_id here; they will default to NULL/None.  After
                # insertion we construct a full row tuple matching the select
                # above (including placeholders for bio and gender) so index
                # positions remain consistent.
                cur.execute(
                    """
                    INSERT INTO users (tg_user_id, display_name, username, is_onboarded)
                    VALUES (%s, %s, %s, FALSE)
                    RETURNING id, display_name, username, age, avatar_url, is_onboarded
                    """,
                    (int(user["id"]), user.get("first_name", "User"), user.get("username", f"user{user['id']}"))
                )
                new_user_row = cur.fetchone()
                con.commit()
                # Compose a row with the same number of columns as the main select.
                # new_user_row = (id, display_name, username, age, avatar_url, is_onboarded)
                row = (
                    new_user_row[0],   # id
                    new_user_row[1],   # display_name
                    new_user_row[2],   # username
                    new_user_row[3],   # age
                    new_user_row[4],   # avatar_url
                    new_user_row[5],   # is_onboarded
                    None,              # active_profile_id (none for new users)
                    "",               # bio (empty string)
                    None               # gender
                )

            # Get follower and following counts
            cur.execute("SELECT COUNT(*) FROM user_follows WHERE followee_id=%s", (row[0],))
            follower_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM user_follows WHERE follower_id=%s", (row[0],))
            following_count = cur.fetchone()[0]

            return {
                "ok": True,
                "user": {
                    "id": row[0],
                    "display_name": row[1],
                    "username": row[2],
                    "age": row[3],
                    "avatar_url": row[4],
                    "is_onboarded": row[5],
                    "active_profile_id": row[6],
                    # Newly exposed fields for the base user.  Bio comes from the
                    # users table (may be empty string) and gender may be null/None.
                    "bio": row[7],
                    "gender": row[8],
                    "follower_count": follower_count,
                    "following_count": following_count,
                    # me endpoint never indicates following, but include for symmetry
                    "is_following": False
                }
            }

@app.post("/api/onboard")
async def onboard(request: Request, user=Depends(get_user)):
    body_data = await request.json()

    # Validate using Pydantic model
    try:
        onboard_data = OnboardRequest(**body_data)
    except Exception as e:
        raise HTTPException(422, f"Invalid request data: {str(e)}")

    display_name = onboard_data.display_name.strip()
    username     = onboard_data.username.strip()
    age          = onboard_data.age
    avatar_file_id = onboard_data.avatar_file_id

    if not display_name or not username or not age:
        raise HTTPException(422, "Missing fields")

    avatar_url = media_proxy_url(avatar_file_id) if avatar_file_id else None

    with reg._conn() as con, con.cursor() as cur:
        ensure_user(con, user)
        # unique username check
        cur.execute("SELECT 1 FROM users WHERE username=%s AND tg_user_id<>%s", (username, int(user["id"])))
        if cur.fetchone():
            raise HTTPException(422, "Username already taken")

        cur.execute("""
            UPDATE users
               SET display_name=%s,
                   username=%s,
                   age=%s,
                   avatar_url=COALESCE(%s, avatar_url),
                   is_onboarded=TRUE
             WHERE tg_user_id=%s
            RETURNING id, display_name, username, is_onboarded
        """, (display_name, username, int(age), avatar_url, int(user["id"])))
        row = cur.fetchone()
        con.commit()

    return {"ok": True, "user": {"id": row[0], "display_name": row[1], "username": row[2], "is_onboarded": row[3]}}

@app.get("/api/users/{user_id}")
async def get_user_profile(user_id: int, _=Depends(get_user)):
    """
    Fetch a user's profile, including follower/following counts and whether the
    current user follows this profile.
    """
    current_user = _
    with reg._conn() as con, con.cursor() as cur:
        # Ensure user_follows table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_follows (
                follower_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                followee_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (follower_id, followee_id)
            )
        """)

        # Try internal ID first, then try Telegram user ID if not found
        cur.execute("SELECT id, display_name, username, avatar_url, COALESCE(age,0), COALESCE(bio,'') FROM users WHERE id=%s OR tg_user_id=%s", (user_id, user_id))
        r = cur.fetchone()
        if not r:
            # Log for debugging
            print(f"DEBUG: Profile not found for user_id={user_id}")
            return JSONResponse({"ok": False, "detail": "Profile not found"}, status_code=404)

        internal_id = r[0]

        # Get follower count and following count
        cur.execute("SELECT COUNT(*) FROM user_follows WHERE followee_id=%s", (internal_id,))
        follower_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM user_follows WHERE follower_id=%s", (internal_id,))
        following_count = cur.fetchone()[0]

        # Determine if current user follows, mutes, or blocks this profile
        current_user_internal_id = get_or_create_user_id(con, current_user)
        cur.execute("SELECT 1 FROM user_follows WHERE follower_id=%s AND followee_id=%s", (current_user_internal_id, internal_id))
        is_following = bool(cur.fetchone())

        # Check mute status
        try:
            cur.execute("SELECT 1 FROM user_mutes WHERE muter_id=%s AND muted_id=%s", (current_user_internal_id, internal_id))
            is_muted = bool(cur.fetchone())
        except Exception as e:
            if "does not exist" in str(e):
                con.rollback()
                is_muted = False  # Default to not muted if table doesn't exist
            else:
                raise

        # Check block status
        try:
            cur.execute("SELECT 1 FROM user_blocks WHERE blocker_id=%s AND blocked_id=%s", (current_user_internal_id, internal_id))
            is_blocked = bool(cur.fetchone())
        except Exception as e:
            if "does not exist" in str(e):
                con.rollback()
                is_blocked = False  # Default to not blocked if table doesn't exist
            else:
                raise

        return {
            "ok": True,
            "user": {
                "id": internal_id,
                "name": r[1] or "User",
                "username": r[2] or f"user{internal_id}",
                "avatar": r[3],
                "age": r[4],
                "bio": r[5],
                "follower_count": follower_count,
                "following_count": following_count,
                "is_following": is_following,
                "is_muted": is_muted,
                "is_blocked": is_blocked
            }
        }

@app.get("/api/users/{user_id}/posts")
async def get_user_posts(
    user_id: int,
    _=Depends(get_user),
    limit: int = Query(20, ge=1, le=50),
    cursor: Optional[str] = Query(None),
):
    """
    Return posts by a given user.  If the current authenticated user is
    requesting their own posts and they have an active profile, return the
    active profile's posts; otherwise return base (profile_id IS NULL) posts.
    """
    with reg._conn() as con:
        # Determine the requested user's internal ID (works with both internal or TG IDs)
        with con.cursor() as cur:
            cur.execute(
                "SELECT id FROM users WHERE id = %s OR tg_user_id = %s",
                (user_id, user_id),
            )
            user_row = cur.fetchone()
            if not user_row:
                return JSONResponse(
                    {"ok": False, "detail": "User not found"},
                    status_code=404,
                )
            internal_user_id = user_row[0]

        # Identify the caller (current user) from the dependency
        current_user_id = get_or_create_user_id(con, _) if _ else None

        # Ensure the feed_posts.profile_id column exists (for legacy DBs)
        with con.cursor() as cur:
            cur.execute(
                "ALTER TABLE feed_posts ADD COLUMN IF NOT EXISTS profile_id BIGINT"
            )

        # If the caller is requesting their own posts and has an active profile,
        # serve posts for that active profile rather than base posts.
        active_profile_id = None
        if current_user_id and current_user_id == internal_user_id:
            with con.cursor() as cur:
                cur.execute(
                    "SELECT active_profile_id FROM users WHERE id = %s",
                    (internal_user_id,),
                )
                row = cur.fetchone()
                active_profile_id = row[0] if row else None

        # Build cursor‑based pagination filters
        cursor_condition = ""
        params = [limit]
        if cursor:
            try:
                cursor_id = int(cursor)
                cursor_condition = " AND id < %s"
                params.insert(0, cursor_id)
            except ValueError:
                pass

        rows = []
        total_count = 0
        with con.cursor() as cur:
            if active_profile_id:
                # Return posts made by the caller's active profile
                params_to_use = [active_profile_id] + params
                cur.execute(
                    f"""
                    SELECT id, author_id, profile_id, created_at, content_type,
                           file_id, text, reaction_count, comment_count
                      FROM feed_posts
                     WHERE profile_id = %s{cursor_condition}
                     ORDER BY created_at DESC LIMIT %s
                    """,
                    params_to_use,
                )
                rows = cur.fetchall()
                cur.execute(
                    "SELECT COUNT(*) FROM feed_posts WHERE profile_id = %s",
                    (active_profile_id,),
                )
                total_count = cur.fetchone()[0] or 0
            else:
                # Return base posts (profile_id IS NULL) for the requested user
                params_to_use = [internal_user_id] + params
                cur.execute(
                    f"""
                    SELECT id, author_id, profile_id, created_at, content_type,
                           file_id, text, reaction_count, comment_count
                      FROM feed_posts
                     WHERE author_id = %s AND profile_id IS NULL{cursor_condition}
                     ORDER BY created_at DESC LIMIT %s
                    """,
                    params_to_use,
                )
                rows = cur.fetchall()
                cur.execute(
                    "SELECT COUNT(*) FROM feed_posts WHERE author_id = %s AND profile_id IS NULL",
                    (internal_user_id,),
                )
                total_count = cur.fetchone()[0] or 0

    # Format results
    items = [
        {
            "id": r[0],
            "author_id": r[1],
            "profile_id": r[2],
            "created_at": r[3].isoformat(),
            "type": r[4] or "text",
            "media_url": media_proxy_url(r[5]) if r[5] else None,
            "caption": r[6] or "",
            "counts": {"likes": r[7] or 0, "comments": r[8] or 0},
        }
        for r in rows
    ]
    next_cursor = str(rows[-1][0]) if rows and len(rows) == limit else None

    return {"ok": True, "items": items, "next_cursor": next_cursor, "total": total_count}

# ---------- Posts ----------
@app.post("/api/posts")
async def create_post(
    user=Depends(get_user),
    caption: str = Form(""),
    media: UploadFile | None = File(None),
    media_type: str = Form("auto")
):
    with reg._conn() as con:
        ensure_profiles_table(con)
        internal_uid = get_or_create_user_id(con, user)

        # Get active profile ID if any - this determines which profile created the post
        with con.cursor() as cur:
            cur.execute("SELECT active_profile_id FROM users WHERE id=%s", (internal_uid,))
            row = cur.fetchone()
            active_profile_id = row[0] if row else None

        # Always use base user ID for author_id to satisfy FK constraint
        author_id = internal_uid

        ctype, file_id = "text", None
        if media:
            data = await media.read()
            if len(data) > 10*1024*1024:
                raise HTTPException(413, "File too large (>10MB)")
            file_id = await tg_upload_to_sink(data, media.filename or "media", media.content_type or "application/octet-stream", caption)
            mt = (media.content_type or "").lower()
            if media_type == "auto":
                if mt.startswith("image/"): ctype = "photo"
                elif mt.startswith("video/"): ctype = "video"
                else: ctype = "document"
            else:
                ctype = media_type

        with con.cursor() as cur:
            # ensure posts table with profile_id column
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feed_posts (
                  id BIGSERIAL PRIMARY KEY,
                  author_id BIGINT NOT NULL,
                  profile_id BIGINT,
                  created_at TIMESTAMPTZ DEFAULT NOW(),
                  content_type TEXT,
                  file_id TEXT,
                  text TEXT,
                  reaction_count INT DEFAULT 0,
                  comment_count INT DEFAULT 0
                )
            """)
            # Add profile_id column if it doesn't exist
            cur.execute("ALTER TABLE feed_posts ADD COLUMN IF NOT EXISTS profile_id BIGINT")

            # Insert post with the profile that created it
            cur.execute("""
                INSERT INTO feed_posts (author_id, profile_id, content_type, file_id, text)
                VALUES (%s,%s,%s,%s,%s)
                RETURNING id, created_at
            """, (author_id, active_profile_id, ctype, file_id, caption))
            row = cur.fetchone()
            con.commit()

    post = {
        "id": row[0],
        "author_id": author_id,
        "profile_id": active_profile_id,
        "created_at": row[1].isoformat(),
        "type": ctype,
        "media_url": media_proxy_url(file_id) if file_id else None,
        "caption": caption,
        "counts": {"likes": 0, "comments": 0},
        "liked": False, "saved": False
    }
    return {"ok": True, "post": post}

@app.get("/api/posts/{post_id}")
async def get_post(post_id: int, _=Depends(get_user)):
    """
    Fetch a single post and resolve the author name correctly.

    Posts may be created either by the base user (profile_id is NULL)
    or by a sub‑profile (profile_id refers to profiles.id).  We always
    fetch author_id and profile_id together and use profile_id (when present)
    to resolve the author name.  When profile_id is NULL, we fall back to the
    base user's display name.
    """
    with reg._conn() as con, con.cursor() as cur:
        cur.execute(
            "SELECT id, author_id, profile_id, created_at, content_type, file_id, text, reaction_count, comment_count "
            "FROM feed_posts WHERE id=%s",
            (post_id,),
        )
        r = cur.fetchone()
        if not r:
            raise HTTPException(404, "Post not found")

        _, author_id, profile_id, created_at, ctype, file_id, text, rx_count, cm_count = r

        author_name = "Anonymous"
        tg_uid = None

        # First resolve via profile_id, if present
        if profile_id:
            cur.execute(
                """
                SELECT p.id, u.tg_user_id,
                       COALESCE(
                           NULLIF(p.profile_name, ''),
                           NULLIF(p.username, ''),
                           'Profile' || p.id
                       ) AS name
                  FROM profiles p
                  JOIN users u ON p.user_id = u.id
                 WHERE p.id = %s
                """,
                (profile_id,),
            )
            prow = cur.fetchone()
            if prow:
                tg_uid = prow[1]
                author_name = prow[2]

        # Otherwise, resolve via base user
        if not profile_id or not tg_uid:
            cur.execute(
                """
                SELECT tg_user_id,
                       COALESCE(
                           NULLIF(display_name, ''),
                           NULLIF(username, ''),
                           NULLIF(feed_username, ''),
                           'User' || tg_user_id
                       ) AS name
                  FROM users WHERE id = %s
                """,
                (author_id,),
            )
            urow = cur.fetchone()
            if urow:
                tg_uid = urow[0]
                author_name = urow[1]

    # Helper for media URL fallback
    def _media_proxy(fid: str | None) -> str | None:
        if not fid:
            return None
        try:
            return media_proxy_url(fid)
        except Exception:
            base = EXTERNAL_URL or ""
            return f"{base}/api/telefile/{fid}"

    return {
        "ok": True,
        "post": {
            "id": r[0],
            "author_id": author_id,
            "profile_id": profile_id,
            "created_at": created_at.isoformat(),
            "type": ctype,
            "media_url": _media_proxy(file_id),
            "caption": text,
            "counts": {"likes": rx_count or 0, "comments": cm_count or 0},
            "author_name": author_name,
            "author": {
                "name": author_name,
                "tg_user_id": tg_uid
            },
        },
    }

# ---------------------------------------------------------------------------
# Post moderation and editing endpoints
#
# The mobile client displays a 3‑dot menu on each post allowing the author to
# edit the caption, hide like counts, disable commenting, pin/unpin to the
# profile grid and delete the post.  The simple API below only implements
# deletion and caption editing.  Other features can be added similarly by
# updating the `feed_posts` table and writing update queries.

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, request: Request):
    """
    Delete a post.  Only the creator (base user or sub‑profile) may delete
    their own post.  Deleting also removes comments via cascading deletes.
    """
    user = await get_user(request)
    with reg._conn() as con:
        uid = get_or_create_user_id(con, user)
        ensure_profiles_table(con)
        with con.cursor() as cur:
            # Fetch the post's author_id and profile_id to determine ownership
            cur.execute("SELECT author_id, profile_id FROM feed_posts WHERE id=%s", (post_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Post not found")
            post_author_id, post_profile_id = row

            # Owned by base user or by one of the user's sub‑profiles
            owns_post = False
            if post_author_id == uid:
                owns_post = True
            elif post_profile_id is not None:
                cur.execute("SELECT 1 FROM profiles WHERE id=%s AND user_id=%s", (post_profile_id, uid))
                if cur.fetchone():
                    owns_post = True

            if not owns_post:
                raise HTTPException(status_code=403, detail="Forbidden")

            # Delete the post; cascade deletes comments via foreign key
            cur.execute("DELETE FROM feed_posts WHERE id=%s", (post_id,))
            con.commit()

    return {"ok": True}

@app.post("/api/posts/{post_id}/caption")
async def update_post_caption(post_id: int, request: Request, caption: str = Form(...)):
    """
    Update the text (caption) of a post.  Only the creator may modify the caption.
    """
    user = await get_user(request)
    with reg._conn() as con:
        uid = get_or_create_user_id(con, user)
        ensure_profiles_table(con)
        with con.cursor() as cur:
            # Fetch the post's author_id and profile_id to determine ownership
            cur.execute("SELECT author_id, profile_id FROM feed_posts WHERE id=%s", (post_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Post not found")
            post_author_id, post_profile_id = row

            # Owned by base user or by one of the user's sub‑profiles
            owns_post = False
            if post_author_id == uid:
                owns_post = True
            elif post_profile_id is not None:
                cur.execute("SELECT 1 FROM profiles WHERE id=%s AND user_id=%s", (post_profile_id, uid))
                if cur.fetchone():
                    owns_post = True

            if not owns_post:
                raise HTTPException(status_code=403, detail="Forbidden")

            # Update caption
            cur.execute("UPDATE feed_posts SET text=%s WHERE id=%s", (caption, post_id))
            con.commit()

    return {"ok": True}

@app.post("/api/posts/{post_id}/like")
async def like_post(post_id: int, request: Request, action: str = Form("add")):
    user = await get_user(request)
    with reg._conn() as con:
        uid = get_or_create_user_id(con, user)
        with con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS post_likes (
                  post_id BIGINT REFERENCES feed_posts(id) ON DELETE CASCADE,
                  user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                  created_at TIMESTAMPTZ DEFAULT NOW(),
                  PRIMARY KEY (post_id, user_id)
                )
            """)
            if action == "remove":
                cur.execute("DELETE FROM post_likes WHERE post_id=%s AND user_id=%s", (post_id, uid))
                liked_action = False
            else:
                cur.execute("INSERT INTO post_likes (post_id, user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (post_id, uid))
                liked_action = cur.rowcount > 0
                print(f"DEBUG: INSERT like - post_id={post_id}, uid={uid}, rowcount={cur.rowcount}, liked_action={liked_action}")
            cur.execute("UPDATE feed_posts SET reaction_count=(SELECT COUNT(*) FROM post_likes WHERE post_id=%s) WHERE id=%s", (post_id, post_id))
            # Determine post owner
            post_owner_id = None
            cur.execute("SELECT author_id FROM feed_posts WHERE id=%s", (post_id,))
            post_row = cur.fetchone()
            if post_row:
                post_owner_id = post_row[0]
            print(f"DEBUG: Post owner check - post_id={post_id}, post_owner_id={post_owner_id}, uid={uid}")
            con.commit()
            # Notify the post owner if a new like (and liker isn't the owner)
            print(f"DEBUG: Notification condition check - liked_action={liked_action}, post_owner_id={post_owner_id}, same_user={post_owner_id == uid}")
            if liked_action and post_owner_id and post_owner_id != uid:
                try:
                    create_notification(con, post_owner_id, uid, "post_like", post_id=post_id, comment_id=None)
                    con.commit()
                except Exception:
                    con.rollback()
    return {"ok": True}

# ---------- Report Post ----------
@app.post("/api/posts/{post_id}/report")
async def report_post(post_id: int, reason: str = Form(...), user=Depends(get_user)):
    """
    Records an anonymous report for a given post and reason. Each report is tied
    to the reporting user's internal ID but is otherwise not surfaced publicly.
    """
    with reg._conn() as con, con.cursor() as cur:
        # Ensure the reports table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS post_reports (
                id         BIGSERIAL PRIMARY KEY,
                post_id    BIGINT NOT NULL REFERENCES feed_posts(id) ON DELETE CASCADE,
                user_id    BIGINT NOT NULL REFERENCES users(id)     ON DELETE CASCADE,
                reason     TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        # Persist the report
        reporter_id = get_or_create_user_id(con, user)
        cur.execute(
            "INSERT INTO post_reports (post_id, user_id, reason) VALUES (%s, %s, %s)",
            (post_id, reporter_id, reason)
        )
        con.commit()
    return {"ok": True}

# ---------- Comments ----------
@app.get("/api/posts/{post_id}/comments")
async def get_comments(post_id: int, _=Depends(get_user), limit: int = Query(20, ge=1, le=50), cursor: Optional[str] = Query(None)):
    """Get comments for a post with pagination"""
    with reg._conn() as con, con.cursor() as cur:
        # Ensure comments table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES feed_posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                is_pinned BOOLEAN DEFAULT FALSE,
                like_count INT DEFAULT 0,
                profile_id BIGINT
            )
        """)
        # Ensure created_at column is timezone-aware for existing tables
        cur.execute("ALTER TABLE comments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()")
        # Ensure the is_pinned column exists for legacy schemas that used `pinned`
        cur.execute("ALTER TABLE comments ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT FALSE")
        # Ensure the like_count column exists; some legacy schemas may miss it
        cur.execute("ALTER TABLE comments ADD COLUMN IF NOT EXISTS like_count INT DEFAULT 0")
        # Add profile_id column if it doesn't exist (migration)
        cur.execute("ALTER TABLE comments ADD COLUMN IF NOT EXISTS profile_id BIGINT")

        # Build cursor condition
        cursor_condition = ""
        params = [post_id, limit]
        if cursor:
            try:
                cursor_id = int(cursor)
                cursor_condition = " AND c.id < %s"
                params.insert(-1, cursor_id)
            except ValueError:
                pass  # Invalid cursor, ignore

        # Query comments with author info.  Always use c.is_pinned; alias as `pinned` in the result.
        cur.execute(
            f"""
            SELECT
                c.id,
                c.user_id,
                c.profile_id,
                c.text,
                c.created_at,
                c.is_pinned AS pinned,
                c.like_count,
                u.display_name, u.username, u.avatar_url, u.tg_user_id,
                p.profile_name, p.username AS profile_username
            FROM comments c
            LEFT JOIN users u ON c.user_id = u.id
            LEFT JOIN profiles p ON c.profile_id = p.id
            WHERE c.post_id = %s{cursor_condition}
            ORDER BY c.is_pinned DESC, c.created_at DESC
            LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()

    comments = []
    for r in rows:
        # Determine the correct author name. Priority:
        # 1. profile_name (r[11]) if not null
        # 2. profile_username (r[12]) if not null
        # 3. base user display_name (r[7]) or username (r[8])
        # 4. fallback "User<tg_user_id>"
        profile_name = r[11] if len(r) > 11 else None
        profile_username = r[12] if len(r) > 12 else None
        user_display_name = r[7]
        user_username = r[8]
        tg_uid = r[10]

        if profile_name:
            author_name = profile_name
        elif profile_username:
            author_name = profile_username
        else:
            author_name = user_display_name or user_username or f"User{tg_uid}"

        comments.append({
            "id": r[0],
            "user_id": r[1],
            "profile_id": r[2],
            "text": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
            "pinned": r[5],
            "like_count": r[6] or 0,
            "author": {
                "name": author_name,
                "avatar_url": r[9],
                "tg_user_id": tg_uid
            }
        })

    # Calculate next cursor
    next_cursor = str(rows[-1][0]) if rows and len(rows) == limit else None

    return {"ok": True, "items": comments, "next_cursor": next_cursor}

@app.post("/api/posts/{post_id}/comments")
async def add_comment(post_id: int, request: Request, text: str = Form(...)):
    """Add a comment to a post"""
    user = await get_user(request)

    if not text.strip():
        raise HTTPException(400, "Comment text cannot be empty")

    with reg._conn() as con:
        uid = get_or_create_user_id(con, user)

        # Use active sub-profile if available
        ensure_profiles_table(con)
        active_profile = get_active_profile(con, uid)
        comment_author_id = uid  # always base user
        comment_profile_id = active_profile[0] if active_profile else None

        with con.cursor() as cur:
            # Ensure comments table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id BIGSERIAL PRIMARY KEY,
                    post_id BIGINT NOT NULL REFERENCES feed_posts(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    text TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    is_pinned BOOLEAN DEFAULT FALSE,
                    like_count INT DEFAULT 0,
                    profile_id BIGINT
                )
            """)
            # Add profile_id column if it doesn't exist (migration)
            cur.execute("ALTER TABLE comments ADD COLUMN IF NOT EXISTS profile_id BIGINT")

            # Insert comment
            cur.execute(
                """
                INSERT INTO comments (post_id, user_id, profile_id, text, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING id, created_at
                """,
                (post_id, comment_author_id, comment_profile_id, text.strip())
            )
            comment_id, created_at = cur.fetchone()

            # Update comment count on post
            cur.execute("UPDATE feed_posts SET comment_count=(SELECT COUNT(*) FROM comments WHERE post_id=%s) WHERE id=%s", (post_id, post_id))

            # Get post owner for notification
            cur.execute("SELECT author_id FROM feed_posts WHERE id=%s", (post_id,))
            post_row = cur.fetchone()
            post_owner_id = post_row[0] if post_row else None

            con.commit()

            # Create notification if commenting on someone else's post
            if post_owner_id and post_owner_id != comment_author_id:
                try:
                    create_notification(con, post_owner_id, comment_author_id, "comment", post_id=post_id)
                    con.commit()
                except Exception:
                    con.rollback()

    return {
        "ok": True,
        "comment": {
            "id": comment_id,
            "text": text.strip(),
            "created_at": created_at.isoformat(),
            "author": {"name": user.get("first_name", "User")}
        }
    }

# ---------- Comment Likes ----------
@app.post("/api/comments/{comment_id}/like")
async def like_comment(comment_id: int, request: Request, action: str = Form("add")):
    """
    Toggle like on a comment.  If the current user likes someone else's comment,
    a `comment_like` notification is generated for the comment owner.  The
    response includes the updated like count and whether the comment is liked
    by the caller after the operation.
    """
    user = await get_user(request)
    with reg._conn() as con:
        uid = get_or_create_user_id(con, user)
        with con.cursor() as cur:
            # Ensure comment_likes table exists
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS comment_likes (
                    comment_id BIGINT REFERENCES comments(id) ON DELETE CASCADE,
                    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (comment_id, user_id)
                )
                """
            )
            # Toggle like/unlike
            if action == "remove":
                cur.execute("DELETE FROM comment_likes WHERE comment_id=%s AND user_id=%s", (comment_id, uid))
                liked = False
            else:
                cur.execute(
                    "INSERT INTO comment_likes (comment_id, user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    (comment_id, uid)
                )
                liked = cur.rowcount > 0
            # Update like_count on the comment
            cur.execute(
                "UPDATE comments SET like_count=(SELECT COUNT(*) FROM comment_likes WHERE comment_id=%s) WHERE id=%s",
                (comment_id, comment_id)
            )
            # Fetch comment owner to notify (if liker is different)
            cur.execute("SELECT user_id FROM comments WHERE id=%s", (comment_id,))
            row = cur.fetchone()
            comment_owner_id = row[0] if row else None
            con.commit()
            # Notify comment owner on like
            if liked and comment_owner_id and comment_owner_id != uid:
                try:
                    create_notification(con, comment_owner_id, uid, "comment_like", post_id=None, comment_id=comment_id)
                    con.commit()
                except Exception:
                    con.rollback()
        # Retrieve updated like count
        with con.cursor() as cur:
            cur.execute("SELECT like_count FROM comments WHERE id=%s", (comment_id,))
            row = cur.fetchone()
            like_count = row[0] or 0
    return {"ok": True, "like_count": like_count, "liked": liked}

# ---------- Feed ----------
@app.get("/api/feed")
async def get_feed(
    user=Depends(get_user),
    tab: str = Query("fresh", description="Tab: fresh, waves, following"),
    limit: int = Query(20, ge=1, le=50),
    cursor: Optional[str] = Query(None),
    hide_seen: bool = Query(False)
):
    """
    Main feed endpoint supporting different tabs:
    - fresh: Latest posts from others (default)
    - waves: Posts with recent engagement/activity
    - following: Posts from users the current user follows
    """
    hours = PUBLIC_TTL_HOURS

    with reg._conn() as con, con.cursor() as cur:
        if tab == "waves":
            # WAVES: Posts with recent engagement (comments/likes in last 24h)
            # Focus on posts that have community interaction
            cur.execute(f"""
              SELECT p.id, p.author_id, p.profile_id, p.created_at, p.content_type, p.file_id, p.text,
                     p.reaction_count, p.comment_count,
                     GREATEST(
                       p.created_at,
                       COALESCE(MAX(c.created_at), p.created_at),
                       COALESCE(MAX(pl.created_at), p.created_at)
                     ) AS last_engaged_at
                FROM feed_posts p
                LEFT JOIN comments c ON c.post_id = p.id AND c.created_at > NOW() - INTERVAL '24 hours'
                LEFT JOIN post_likes pl ON pl.post_id = p.id AND pl.created_at > NOW() - INTERVAL '24 hours'
               WHERE p.created_at > NOW() - INTERVAL '{hours} hours'
                 AND (
                       c.id IS NOT NULL
                    OR pl.post_id IS NOT NULL
                    OR p.reaction_count > 0
                    OR p.comment_count > 0
                 )
               GROUP BY p.id, p.author_id, p.profile_id, p.created_at, p.content_type, p.file_id, p.text, p.reaction_count, p.comment_count
               ORDER BY last_engaged_at DESC
               LIMIT %s
            """, (limit,))
        elif tab == "following":
            # FOLLOWING: Posts from users the current user follows
            current_user_id = get_or_create_user_id(con, user)
            cur.execute(f"""
              SELECT p.id, p.author_id, p.profile_id, p.created_at, p.content_type, p.file_id, p.text,
                     p.reaction_count, p.comment_count
                FROM feed_posts p
                JOIN user_follows uf ON p.author_id = uf.followee_id
               WHERE uf.follower_id = %s
                 AND p.created_at > NOW() - INTERVAL '{hours} hours'
               ORDER BY p.created_at DESC
               LIMIT %s
            """, (current_user_id, limit))
        else:  # fresh (default)
            # FRESH: Latest posts from OTHERS (exclude your own posts)
            current_user_id = get_or_create_user_id(con, user)
            cur.execute(f"""
              SELECT id, author_id, profile_id, created_at, content_type, file_id, text, reaction_count, comment_count
                FROM feed_posts
               WHERE created_at > NOW() - INTERVAL '{hours} hours'
                 AND author_id != %s
               ORDER BY created_at DESC LIMIT %s
            """, (current_user_id, limit))
        rows = cur.fetchall()

        # Determine the current user's internal ID.
        current_user_id = get_or_create_user_id(con, user)

        # Compute which of these posts the current user has liked.
        post_ids = [r[0] for r in rows]
        liked_set = set()
        if post_ids:
            cur.execute(
                "SELECT post_id FROM post_likes "
                "WHERE user_id = %s AND post_id = ANY(%s)",
                (current_user_id, post_ids)
            )
            liked_set = {pid for (pid,) in cur.fetchall()}

        # Ensure profile_id column exists for all queries
        cur.execute("ALTER TABLE feed_posts ADD COLUMN IF NOT EXISTS profile_id BIGINT")

        # Re-fetch rows with profile_id included if tab is 'waves'
        if tab == "waves":
            cur.execute(f"""
              SELECT p.id, p.author_id, p.profile_id, p.created_at, p.content_type, p.file_id, p.text,
                     p.reaction_count, p.comment_count,
                     GREATEST(
                       p.created_at,
                       COALESCE(MAX(c.created_at), p.created_at),
                       COALESCE(MAX(pl.created_at), p.created_at)
                     ) AS last_engaged_at
                FROM feed_posts p
                LEFT JOIN comments c ON c.post_id = p.id AND c.created_at > NOW() - INTERVAL '24 hours'
                LEFT JOIN post_likes pl ON pl.post_id = p.id AND pl.created_at > NOW() - INTERVAL '24 hours'
               WHERE p.created_at > NOW() - INTERVAL '{hours} hours'
                 AND (
                       c.id IS NOT NULL
                    OR pl.post_id IS NOT NULL
                    OR p.reaction_count > 0
                    OR p.comment_count > 0
                 )
               GROUP BY p.id, p.author_id, p.profile_id, p.created_at, p.content_type, p.file_id, p.text, p.reaction_count, p.comment_count
               ORDER BY last_engaged_at DESC
               LIMIT %s
            """, (limit,))
        else:  # fresh or following
            cur.execute(f"""
              SELECT id, author_id, profile_id, created_at, content_type, file_id, text, reaction_count, comment_count
                FROM feed_posts
               WHERE created_at > NOW() - INTERVAL '{hours} hours'
                 AND author_id != %s
               ORDER BY created_at DESC LIMIT %s
            """, (current_user_id, limit))
        rows = cur.fetchall()

        # Fetch author details for both users and profiles
        author_ids = list({r[1] for r in rows})  # author_id
        profile_ids = list({r[2] for r in rows if r[2] is not None})  # profile_id
        authors: dict[int, dict] = {}

        if author_ids:
            # Fetch base user names
            cur.execute(
                """
                SELECT id, tg_user_id,
                       COALESCE(
                           NULLIF(display_name, ''),
                           NULLIF(username, ''),
                           NULLIF(feed_username, ''),
                           'User' || tg_user_id
                       ) AS name
                  FROM users
                 WHERE id = ANY(%s)
                """,
                (author_ids,),
            )
            for (rid, tgid, name) in cur.fetchall():
                authors[rid] = {"name": name, "tg_user_id": tgid}

        # Fetch profile names and map to their owners' tg_user_id
        profile_authors: dict[int, dict] = {}
        if profile_ids:
            cur.execute(
                """
                SELECT p.id, u.tg_user_id,
                       COALESCE(
                           NULLIF(p.profile_name, ''),
                           NULLIF(p.username, ''),
                           'Profile' || p.id
                       ) AS name
                  FROM profiles p
                  JOIN users u ON p.user_id = u.id
                 WHERE p.id = ANY(%s)
                """,
                (profile_ids,),
            )
            for (pid, tgid, name) in cur.fetchall():
                profile_authors[pid] = {"name": name, "tg_user_id": tgid}

        # Local helper for media URLs—falls back if media_proxy_url is undefined
        def _media_proxy(file_id: str | None) -> str | None:
            if not file_id:
                return None
            try:
                return media_proxy_url(file_id)
            except Exception:
                base = EXTERNAL_URL or ""
                return f"{base}/api/telefile/{file_id}"

        items = []
        for r in rows:
            post_id, author_id, profile_id = r[0], r[1], r[2]
            liked_flag = post_id in liked_set

            # Determine author name: use profile name if profile_id exists, otherwise base user name
            author_name = "Anonymous"
            tg_uid = None

            if profile_id and profile_id in profile_authors:
                # Post was made by a sub-profile
                profile_info = profile_authors[profile_id]
                author_name = profile_info.get("name", "Anonymous")
                # Get the tg_user_id from the base user who owns this profile
                base_user_info = authors.get(author_id)
                tg_uid = base_user_info.get("tg_user_id") if base_user_info else None
            elif author_id in authors:
                # Post was made by base user
                author_info = authors[author_id]
                author_name = author_info.get("name", "Anonymous")
                tg_uid = author_info.get("tg_user_id")

            items.append({
                "id": post_id,
                "author_id": author_id,
                "profile_id": profile_id,
                "created_at": r[3].isoformat(),
                "type": r[4] or "text",
                "media_url": _media_proxy(r[5]),
                "caption": r[6] or "",
                "counts": {"likes": r[7] or 0, "comments": r[8] or 0},
                "liked": liked_flag,
                "author_name": author_name,
                "author": {
                    "name": author_name,
                    "tg_user_id": tg_uid
                }
            })

    return {"ok": True, "items": items}

# ---------- Follow / Unfollow ----------
@app.post("/api/follow/{user_id}")
async def toggle_follow(user_id: int, request: Request):
    """
    Toggle following status for a user.  Allows the current authenticated user to
    follow or unfollow another user (identified by either internal ID or
    Telegram user ID).  Returns the new follow state.
    """
    current_user = await get_user(request)
    with reg._conn() as con:
        follower_id = get_or_create_user_id(con, current_user)
        with con.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id=%s OR tg_user_id=%s", (user_id, user_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            followee_id = row[0]
            if followee_id == follower_id:
                raise HTTPException(status_code=400, detail="Cannot follow yourself")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_follows (
                    follower_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    followee_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (follower_id, followee_id)
                )
            """)
            cur.execute("SELECT 1 FROM user_follows WHERE follower_id=%s AND followee_id=%s",
                        (follower_id, followee_id))
            is_following = bool(cur.fetchone())
            if is_following:
                cur.execute("DELETE FROM user_follows WHERE follower_id=%s AND followee_id=%s", (follower_id, followee_id))
                action = "unfollowed"
                following = False
            else:
                cur.execute("INSERT INTO user_follows (follower_id, followee_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (follower_id, followee_id))
                action = "followed"
                following = True
            con.commit()
            # Notify the followee when a new follow occurs
            if not is_following and following and followee_id != follower_id:
                try:
                    create_notification(con, followee_id, follower_id, "follow", post_id=None, comment_id=None)
                    con.commit()
                except Exception:
                    con.rollback()
    return {"ok": True, "action": action, "following": following}

# ---------- Mute / Unmute ----------
@app.post("/api/mute/{user_id}")
async def toggle_mute(user_id: int, request: Request):
    """
    Toggle mute status for a user.  When a user is muted, their posts and
    comments will not appear in the caller's feed.  Returns the new mute state.
    """
    current_user = await get_user(request)
    with reg._conn() as con:
        muter_id = get_or_create_user_id(con, current_user)
        with con.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id=%s OR tg_user_id=%s", (user_id, user_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            muted_id = row[0]
            if muted_id == muter_id:
                raise HTTPException(status_code=400, detail="Cannot mute yourself")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_mutes (
                    muter_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    muted_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (muter_id, muted_id)
                )
            """)
            cur.execute("SELECT 1 FROM user_mutes WHERE muter_id=%s AND muted_id=%s", (muter_id, muted_id))
            is_muted = bool(cur.fetchone())
            if is_muted:
                cur.execute("DELETE FROM user_mutes WHERE muter_id=%s AND muted_id=%s", (muter_id, muted_id))
                action = "unmuted"
                muted = False
            else:
                cur.execute("INSERT INTO user_mutes (muter_id, muted_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (muter_id, muted_id))
                action = "muted"
                muted = True
            con.commit()
    return {"ok": True, "action": action, "muted": muted}

# ---------- Block / Unblock ----------
@app.post("/api/block/{user_id}")
async def toggle_block(user_id: int, request: Request):
    """
    Toggle block status for a user.  When a user is blocked, any existing
    follow relationships between the users are removed and the blocked user
    will not see the caller's posts.  Returns the new blocked state.
    """
    current_user = await get_user(request)
    with reg._conn() as con:
        blocker_id = get_or_create_user_id(con, current_user)
        with con.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id=%s OR tg_user_id=%s", (user_id, user_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            blocked_id = row[0]
            if blocked_id == blocker_id:
                raise HTTPException(status_code=400, detail="Cannot block yourself")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_blocks (
                    blocker_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    blocked_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (blocker_id, blocked_id)
                )
            """)
            cur.execute("SELECT 1 FROM user_blocks WHERE blocker_id=%s AND blocked_id=%s", (blocker_id, blocked_id))
            is_blocked = bool(cur.fetchone())
            if is_blocked:
                cur.execute("DELETE FROM user_blocks WHERE blocker_id=%s AND blocked_id=%s", (blocker_id, blocked_id))
                action = "unblocked"
                blocked = False
            else:
                cur.execute("INSERT INTO user_blocks (blocker_id, blocked_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (blocker_id, blocked_id))
                # Remove follow relationships in both directions
                cur.execute("""
                    DELETE FROM user_follows
                    WHERE (follower_id=%s AND followee_id=%s)
                       OR (follower_id=%s AND followee_id=%s)
                """, (blocker_id, blocked_id, blocked_id, blocker_id))
                action = "blocked"
                blocked = True
            con.commit()
    return {"ok": True, "action": action, "blocked": blocked}

# ---------- Report User ----------
@app.post("/api/users/{user_id}/report")
async def report_user(user_id: int, request: Request, reason: str = Form(...)):
    """
    Report another user for inappropriate behaviour.  A textual reason must
    be provided.  Reports are stored anonymously.
    """
    if not reason or not reason.strip():
        raise HTTPException(status_code=400, detail="Reason is required")
    current_user = await get_user(request)
    with reg._conn() as con:
        reporter_id = get_or_create_user_id(con, current_user)
        with con.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id=%s OR tg_user_id=%s", (user_id, user_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            reported_id = row[0]
            if reported_id == reporter_id:
                raise HTTPException(status_code=400, detail="Cannot report yourself")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_reports (
                    id BIGSERIAL PRIMARY KEY,
                    reporter_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    reported_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    reason TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("INSERT INTO user_reports (reporter_id, reported_id, reason) VALUES (%s,%s,%s)",
                        (reporter_id, reported_id, reason.strip()))
            con.commit()
    return {"ok": True}

# ---------- Avatar Update ----------
@app.post("/api/profile/avatar")
async def update_avatar(
    request: Request,
    avatar: UploadFile = File(...)
):
    """
    Update the current user's profile picture.
    Accepts a file upload and stores it via Telegram.
    Returns the new avatar_url for the user.
    """
    current_user = await get_user(request)
    data = await avatar.read()
    if not data:
        raise HTTPException(status_code=400, detail="No file uploaded")
    try:
        file_id = await tg_upload_to_sink(
            data, avatar.filename or "avatar", avatar.content_type or "application/octet-stream", caption="avatar"
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to upload avatar: {e}")
    avatar_url = media_proxy_url(file_id)
    with reg._conn() as con:
        uid = get_or_create_user_id(con, current_user)
        with con.cursor() as cur:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT")
            cur.execute("UPDATE users SET avatar_url=%s WHERE id=%s", (avatar_url, uid))
            con.commit()
    return {"ok": True, "avatar_url": avatar_url}

# ---------- Follower and Following Lists ----------
@app.get("/api/users/{user_id}/followers")
async def get_user_followers(
    user_id: int,
    limit: int = Query(20, ge=1, le=50),
    cursor: Optional[int] = Query(None),
    user=Depends(get_user),
):
    with reg._conn() as con, con.cursor() as cur:
        # Resolve target's internal ID (works with Telegram ID too)
        cur.execute("SELECT id FROM users WHERE id=%s OR tg_user_id=%s", (user_id, user_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        target_id = row[0]
        # Ensure the follows table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_follows (
                follower_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                followee_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (follower_id, followee_id)
            )
        """)
        # Get the current logged in user
        current_user_internal_id = get_or_create_user_id(con, user)
        # Pagination: filter by cursor if supplied
        if cursor:
            cur.execute(
                """SELECT follower_id FROM user_follows
                   WHERE followee_id = %s AND follower_id > %s
                   ORDER BY follower_id LIMIT %s""",
                (target_id, cursor, limit))
        else:
            cur.execute(
                """SELECT follower_id FROM user_follows
                   WHERE followee_id = %s
                   ORDER BY follower_id LIMIT %s""",
                (target_id, limit))
        rows = cur.fetchall()
        items = []
        for (follower_id,) in rows:
            cur.execute(
                """SELECT id, tg_user_id,
                          COALESCE(NULLIF(display_name, ''), NULLIF(username, ''),
                                   NULLIF(feed_username, ''), 'User' || tg_user_id) AS name,
                          avatar_url
                   FROM users WHERE id = %s""",
                (follower_id,))
            u = cur.fetchone()
            if not u:
                continue
            u_id, tg_uid, name, avatar_url = u
            # Check if current user also follows this follower
            cur.execute(
                "SELECT 1 FROM user_follows WHERE follower_id=%s AND followee_id=%s",
                (current_user_internal_id, u_id))
            is_following_user = bool(cur.fetchone())
            items.append({
                "id": u_id,
                "tg_user_id": tg_uid,
                "name": name,
                "avatar": avatar_url,
                "is_following": is_following_user,
            })
        next_cursor = rows[-1][0] if rows and len(rows) == limit else None
        return {"ok": True, "items": items, "next_cursor": next_cursor}

@app.get("/api/users/{user_id}/following")
async def get_user_following(
    user_id: int,
    limit: int = Query(20, ge=1, le=50),
    cursor: Optional[int] = Query(None),
    user=Depends(get_user),
):
    with reg._conn() as con, con.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE id=%s OR tg_user_id=%s", (user_id, user_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        target_id = row[0]
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_follows (
                follower_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                followee_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (follower_id, followee_id)
            )
        """)
        current_user_internal_id = get_or_create_user_id(con, user)
        if cursor:
            cur.execute(
                """SELECT followee_id FROM user_follows
                   WHERE follower_id = %s AND followee_id > %s
                   ORDER BY followee_id LIMIT %s""",
                (target_id, cursor, limit))
        else:
            cur.execute(
                """SELECT followee_id FROM user_follows
                   WHERE follower_id = %s
                   ORDER BY followee_id LIMIT %s""",
                (target_id, limit))
        rows = cur.fetchall()
        items = []
        for (followee_id,) in rows:
            cur.execute(
                """SELECT id, tg_user_id,
                          COALESCE(NULLIF(display_name, ''), NULLIF(username, ''),
                                   NULLIF(feed_username, ''), 'User' || tg_user_id) AS name,
                          avatar_url
                   FROM users WHERE id = %s""",
                (followee_id,))
            u = cur.fetchone()
            if not u:
                continue
            u_id, tg_uid, name, avatar_url = u
            cur.execute(
                "SELECT 1 FROM user_follows WHERE follower_id=%s AND followee_id=%s",
                (current_user_internal_id, u_id))
            is_following_user = bool(cur.fetchone())
            items.append({
                "id": u_id,
                "tg_user_id": tg_uid,
                "name": name,
                "avatar": avatar_url,
                "is_following": is_following_user,
            })
        next_cursor = rows[-1][0] if rows and len(rows) == limit else None
        return {"ok": True, "items": items, "next_cursor": next_cursor}

# ---------- Profile Editing ----------
@app.post("/api/profile/update")
async def update_profile(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    bio: str = Form(None),
    gender: str = Form(None)
):
    """
    Update the main Telegram user's profile.  This endpoint updates the
    `users` table for the authenticated user.  To modify a sub‑profile,
    use `/api/profiles/{id}/update` instead.  It accepts name, username,
    optional bio and gender fields.
    """
    # Normalize input
    name = (name or "").strip()
    username = (username or "").strip()
    bio = (bio or "").strip() or None
    gender = (gender or "").strip().lower() or None
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    if not username:
        raise HTTPException(status_code=422, detail="Username cannot be empty")
    if gender and gender not in {"male", "female", "other"}:
        raise HTTPException(status_code=422, detail="Invalid gender")

    current_user = await get_user(request)
    with reg._conn() as con:
        uid = get_or_create_user_id(con, current_user)
        with con.cursor() as cur:
            # Ensure optional columns exist
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS gender TEXT")

            # Prevent collisions with other users
            cur.execute("SELECT id FROM users WHERE username=%s AND id<>%s", (username, uid))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Username already taken")
            # Prevent collisions with profiles
            cur.execute("SELECT 1 FROM profiles WHERE username=%s", (username,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Username already taken")

            # Perform update
            cur.execute(
                "UPDATE users SET display_name=%s, username=%s, bio=%s, gender=%s WHERE id=%s",
                (name, username, bio, gender, uid)
            )
            con.commit()
    return {"ok": True, "detail": "Profile updated"}

@app.post("/api/profiles/{profile_id}/update")
async def update_subprofile(
    profile_id: int,
    request: Request,
    profile_name: str = Form(..., alias="name"),
    username: str = Form(...),
    bio: str = Form(None)
):
    """
    Update the given sub‑profile's display name, username and bio.  The
    authenticated user must own the profile.  Gender updates are not
    supported for sub‑profiles because the `profiles` table does not
    include a gender column.  Pass form fields `name` (mapped to
    `profile_name`), `username` and optional `bio`.
    """
    # Normalize input values
    profile_name = (profile_name or "").strip()
    username = (username or "").strip()
    bio = (bio or "").strip() or None
    if not profile_name:
        raise HTTPException(422, "Profile name cannot be empty")
    if not username:
        raise HTTPException(422, "Username cannot be empty")

    current_user = await get_user(request)
    with reg._conn() as con:
        ensure_profiles_table(con)
        uid = get_or_create_user_id(con, current_user)
        with con.cursor() as cur:
            # Verify profile exists and belongs to this user
            cur.execute("SELECT user_id FROM profiles WHERE id=%s", (profile_id,))
            owner = cur.fetchone()
            if not owner:
                raise HTTPException(404, "Profile not found")
            if int(owner[0]) != uid:
                raise HTTPException(403, "Forbidden")

            # Check for username conflicts with other users and profiles
            cur.execute("SELECT 1 FROM users WHERE username=%s", (username,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Username already taken")
            cur.execute(
                "SELECT 1 FROM profiles WHERE username=%s AND id<>%s",
                (username, profile_id)
            )
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="Username already taken")

            # Perform the update
            cur.execute(
                "UPDATE profiles SET profile_name=%s, username=%s, bio=%s WHERE id=%s",
                (profile_name, username, bio, profile_id)
            )
            con.commit()

    return {"ok": True, "profile_id": profile_id}

# ---------- Profiles API ----------
@app.get("/api/profiles")
async def list_profiles(user=Depends(get_user)):
    """
    Return all sub‑profiles AND the base user.  The base user appears with id=0.
    """
    with reg._conn() as con:
        ensure_profiles_table(con)
        uid = get_or_create_user_id(con, user)
        with con.cursor() as cur:
            # Ensure optional columns exist on the users table.  Without
            # pre‑creating the bio column, selecting it below would result in an
            # undefined‑column error on fresh databases.  These migrations are
            # idempotent so calling them repeatedly is safe.
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS gender TEXT")
            # fetch sub-profiles
            cur.execute(
                "SELECT id, profile_name, username, bio, avatar_url, is_active "
                "FROM profiles WHERE user_id=%s ORDER BY id",
                (uid,)
            )
            rows = cur.fetchall()
            profiles = [
                {
                    "id": r[0],
                    "profile_name": r[1],
                    "username": r[2],
                    "bio": r[3],
                    "avatar_url": r[4],
                    "is_active": bool(r[5]),
                }
                for r in rows
            ]
            # fetch base user details
            cur.execute(
                "SELECT display_name, username, bio, avatar_url, active_profile_id "
                "FROM users WHERE id=%s",
                (uid,)
            )
            urow = cur.fetchone()
            base_profile = {
                "id": 0,
                "profile_name": urow[0] or urow[1] or f"User{uid}",
                "username": urow[1] or f"user{uid}",
                "bio": urow[2],
                "avatar_url": urow[3],
                "is_active": urow[4] is None,
            }
            profiles.insert(0, base_profile)
            return {"ok": True, "profiles": profiles}

@app.post("/api/profiles")
async def create_profile(request: Request, user=Depends(get_user)):
    """
    Create a new sub-profile for the current Telegram user.
    Expects JSON with profile_name, username, optional bio, and optional avatar_file_id.
    Automatically activates the profile if none are active yet.
    """
    data = await request.json()
    profile_name = (data.get("profile_name") or "").strip()
    username = (data.get("username") or "").strip()
    bio = (data.get("bio") or "").strip() or None
    avatar_file_id = data.get("avatar_file_id")
    if not profile_name or not username:
        raise HTTPException(400, "profile_name and username are required")
    avatar_url = media_proxy_url(avatar_file_id) if avatar_file_id else None
    with reg._conn() as con:
        ensure_profiles_table(con)
        uid = get_or_create_user_id(con, user)
        with con.cursor() as cur:
            # Enforce unique usernames across profiles
            cur.execute("SELECT 1 FROM profiles WHERE username=%s", (username,))
            if cur.fetchone():
                raise HTTPException(409, "Username already taken")
            cur.execute(
                """
                INSERT INTO profiles (user_id, profile_name, username, bio, avatar_url, is_active)
                VALUES (%s,%s,%s,%s,%s,FALSE)
                RETURNING id
                """,
                (uid, profile_name, username, bio, avatar_url)
            )
            new_profile_id = cur.fetchone()[0]
            # If this user has no active profile yet, make the new one active
            cur.execute(
                "SELECT 1 FROM profiles WHERE user_id=%s AND is_active=TRUE",
                (uid,)
            )
            if not cur.fetchone():
                cur.execute(
                    "UPDATE profiles SET is_active=TRUE WHERE id=%s",
                    (new_profile_id,)
                )
                cur.execute(
                    "UPDATE users SET active_profile_id=%s WHERE id=%s",
                    (new_profile_id, uid)
                )
            con.commit()
            return {"ok": True, "profile_id": new_profile_id}

@app.post("/api/profile/switch")
async def switch_profile(request: Request, user=Depends(get_user)):
    """
    Switch the active sub‑profile.  If profile_id=0, reset to the base profile.
    """
    data = await request.json()
    try:
        profile_id = int(data.get("profile_id", 0))
    except Exception:
        raise HTTPException(400, "Invalid profile_id")
    with reg._conn() as con:
        ensure_profiles_table(con)
        uid = get_or_create_user_id(con, user)
        with con.cursor() as cur:
            if profile_id == 0:
                # Reset to base user - CRITICAL: Set active_profile_id to NULL
                cur.execute("UPDATE profiles SET is_active=FALSE WHERE user_id=%s", (uid,))
                cur.execute("UPDATE users SET active_profile_id=NULL WHERE id=%s", (uid,))
                con.commit()
                print(f"DEBUG: Reset active_profile_id to NULL for user {uid}")
                return {"ok": True, "active_profile_id": None}
            # verify profile belongs to this user
            cur.execute("SELECT id FROM profiles WHERE id=%s AND user_id=%s", (profile_id, uid))
            if not cur.fetchone():
                raise HTTPException(404, "Profile not found")
            # deactivate and activate
            cur.execute("UPDATE profiles SET is_active=FALSE WHERE user_id=%s", (uid,))
            cur.execute("UPDATE profiles SET is_active=TRUE WHERE id=%s", (profile_id,))
            cur.execute("UPDATE users SET active_profile_id=%s WHERE id=%s", (profile_id, uid))
            con.commit()
            print(f"DEBUG: Set active_profile_id to {profile_id} for user {uid}")
            return {"ok": True, "active_profile_id": profile_id}

@app.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: int, user=Depends(get_user)):
    """
    Return a single sub‑profile's details with follow status.
    """
    with reg._conn() as con:
        ensure_profiles_table(con)
        follower_id = get_or_create_user_id(con, user)
        with con.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, profile_name, username, bio, avatar_url, is_active "
                "FROM profiles WHERE id=%s",
                (profile_id,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Profile not found")

            pid, uid, pname, uname, bio, avatar_url, is_active = row

            # Check if current user follows, mutes, or blocks the base user of this profile
            is_following = False
            is_muted = False
            is_blocked = False
            if follower_id and uid:
                cur.execute(
                    "SELECT 1 FROM user_follows WHERE follower_id=%s AND followee_id=%s",
                    (follower_id, uid),
                )
                is_following = bool(cur.fetchone())

                try:
                    cur.execute("SELECT 1 FROM user_mutes WHERE muter_id=%s AND muted_id=%s", (follower_id, uid))
                    is_muted = bool(cur.fetchone())
                except Exception as e:
                    if "does not exist" in str(e):
                        con.rollback()
                        is_muted = False
                    else:
                        raise

                try:
                    cur.execute("SELECT 1 FROM user_blocks WHERE blocker_id=%s AND blocked_id=%s", (follower_id, uid))
                    is_blocked = bool(cur.fetchone())
                except Exception as e:
                    if "does not exist" in str(e):
                        con.rollback()
                        is_blocked = False
                    else:
                        raise

            # Count the base user's followers and followings
            follower_count = 0
            following_count = 0
            if uid:
                cur.execute("SELECT COUNT(*) FROM user_follows WHERE followee_id=%s", (uid,))
                follower_count = cur.fetchone()[0] or 0
                cur.execute("SELECT COUNT(*) FROM user_follows WHERE follower_id=%s", (uid,))
                following_count = cur.fetchone()[0] or 0

            return {
                "profile": {
                    "id": pid,
                    "user_id": uid,
                    "profile_name": pname,
                    "username": uname,
                    "bio": bio,
                    "avatar_url": avatar_url,
                    "is_active": is_active,
                    "is_following": is_following,
                    "is_muted": is_muted,
                    "is_blocked": is_blocked,
                    "follower_count": follower_count,
                    "following_count": following_count,
                }
            }

@app.get("/api/profiles/{profile_id}/posts")
async def get_profile_posts(
    profile_id: int,
    user=Depends(get_user),
    limit: int = Query(20, ge=1, le=50),
    cursor: Optional[str] = Query(None)
):
    """
    Return posts created by a specific sub-profile.
    """
    with reg._conn() as con:
        ensure_profiles_table(con)
        with con.cursor() as cur:
            # Verify profile exists
            cur.execute("SELECT user_id FROM profiles WHERE id=%s", (profile_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Profile not found")

            # Ensure profile_id column exists
            cur.execute("ALTER TABLE feed_posts ADD COLUMN IF NOT EXISTS profile_id BIGINT")

            # Build cursor-based pagination query
            cursor_condition = ""
            params = [profile_id, limit]
            if cursor:
                try:
                    cursor_id = int(cursor)
                    cursor_condition = " AND id < %s"
                    params.insert(-1, cursor_id)
                except ValueError:
                    pass  # Invalid cursor, ignore

        with con.cursor() as cur:
            cur.execute(f"""
                SELECT id, author_id, profile_id, created_at, content_type, file_id, text, reaction_count, comment_count
                FROM feed_posts
                WHERE profile_id = %s{cursor_condition}
                ORDER BY created_at DESC
                LIMIT %s
            """, params)
            rows = cur.fetchall()

        # Count total posts for this profile
        with con.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM feed_posts WHERE profile_id = %s", (profile_id,))
            total_count = cur.fetchone()[0] or 0

    items = [{
        "id": r[0],
        "author_id": r[1],
        "profile_id": r[2],
        "created_at": r[3].isoformat(),
        "type": r[4] or "text",
        "media_url": media_proxy_url(r[5]) if r[5] else None,
        "caption": r[6] or "",
        "counts": {"likes": r[7] or 0, "comments": r[8] or 0}
    } for r in rows]

    # Calculate next cursor
    next_cursor = str(rows[-1][0]) if rows and len(rows) == limit else None

    return {
        "ok": True,
        "items": items,
        "next_cursor": next_cursor,
        "total": total_count
    }

# ---------- Notifications API ----------
@app.get("/api/notifications")
async def get_notifications(
    user=Depends(get_user),
    cursor: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Retrieve recent notifications for the current user with proper user name resolution.
    Includes post and comment text to avoid additional API calls.
    """
    with reg._conn() as con:
        # Look up the internal user ID for the current Telegram user
        uid = get_or_create_user_id(con, user)
        with con.cursor() as cur:
            # Build one query with post and comment text to avoid 404s
            base_sql = """
                SELECT n.id,
                       n.ntype AS type,
                       n.created_at,
                       n.actor,
                       n.post_id,
                       n.comment_id,
                       n.read,
                       u.tg_user_id,
                       COALESCE(
                           NULLIF(p.profile_name, ''),
                           NULLIF(u.display_name, ''),
                           NULLIF(u.username, ''),
                           NULLIF(u.feed_username, ''),
                           'User' || u.tg_user_id
                       ) AS from_name,
                       fp.text AS post_text,
                       c.text AS comment_text
                  FROM notifications n
                  LEFT JOIN users u    ON n.actor = u.id
                  LEFT JOIN profiles p ON p.user_id = u.id AND p.is_active = TRUE
                  LEFT JOIN feed_posts fp ON n.post_id = fp.id
                  LEFT JOIN comments   c ON n.comment_id = c.id
                 WHERE n.user_id = %s
            """
            if cursor:
                sql = base_sql + " AND n.id < %s ORDER BY n.id DESC LIMIT %s"
                cur.execute(sql, (uid, cursor, limit))
            else:
                sql = base_sql + " ORDER BY n.id DESC LIMIT %s"
                cur.execute(sql, (uid, limit))
            rows = cur.fetchall()

    # Each row now includes post_text and comment_text
    items = []
    for row in rows:
        (
            notif_id, ntype, created_at, actor_id, post_id, comment_id,
            read_flag, tg_uid, from_name, post_text, comment_text
        ) = row
        items.append({
            "id": notif_id,
            "type": ntype,
            "created_at": created_at.isoformat() if created_at else None,
            "post_id": post_id,
            "comment_id": comment_id,
            "post_text": post_text,
            "comment_text": comment_text,
            "read": read_flag,
            "from_user": {
                "tg_user_id": tg_uid,
                "id": actor_id,
                "name": from_name or f"User{tg_uid or actor_id}",
            },
        })

    # Calculate next cursor: use the smallest ID from this batch as the next cursor
    next_cursor = rows[-1][0] if rows and len(rows) == limit else None

    return {"ok": True, "items": items, "next_cursor": next_cursor}



# --- Story Tables ------------------------------------------------------------------

def ensure_stories_tables(con):
    """
    Ensure the tables needed for stories exist and match your current DB schema.
    Uses 'kind' and 'author_id' (not 'type' or 'profile_id') to avoid UndefinedColumn errors.
    """
    with con.cursor() as cur:
        # stories table based on your dump
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stories (
                id BIGSERIAL PRIMARY KEY,
                author_id BIGINT,
                kind TEXT NOT NULL,
                text TEXT,
                media_id TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
            )
        """)
        # story_segments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS story_segments (
                id BIGSERIAL PRIMARY KEY,
                story_id BIGINT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
                segment_type TEXT,
                content_type TEXT,
                file_id TEXT,
                text TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                user_id BIGINT,
                profile_id BIGINT
            )
        """)
        # story_views table (must contain user_id)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS story_views (
                id BIGSERIAL PRIMARY KEY,
                story_id BIGINT NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                viewed_at TIMESTAMPTZ DEFAULT NOW(),
                CONSTRAINT unique_story_view UNIQUE (story_id, user_id)
            )
        """)
    con.commit()

def get_or_create_user_story(con, user_id):
    """
    Return the active 'user' story id for this user, or create one if none exists.
    """
    with con.cursor() as cur:
        cur.execute("""
            SELECT id FROM stories
            WHERE kind='user'
              AND author_id=%s
              AND expires_at > NOW()
            ORDER BY id DESC LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        # otherwise, create a new one that expires in 24 hours
        cur.execute("""
            INSERT INTO stories (author_id, kind, expires_at)
            VALUES (%s, 'user', NOW() + INTERVAL '24 hours')
            RETURNING id
        """, (user_id,))
        story_id = cur.fetchone()[0]
    con.commit()
    return story_id

def get_or_create_official_story(con) -> int:
    """
    Returns the official story ID, creating it if missing.
    Uses the 'kind' column to identify official vs. user stories.
    """
    ensure_stories_tables(con)
    with con.cursor() as cur:
        cur.execute("SELECT id FROM stories WHERE kind = 'official' LIMIT 1")
        row = cur.fetchone()
        if row:
            return row[0]
        # Insert a new official story with an expires_at far in the future
        # Use author_id = NULL for official stories (system stories)
        cur.execute("""
            INSERT INTO stories (author_id, kind, text, media_id, expires_at)
            VALUES (NULL, 'official', NULL, NULL, NOW() + INTERVAL '365 days')
            RETURNING id
        """)
        official_id = cur.fetchone()[0]
    con.commit()
    return official_id

# --- Official Story Endpoints -------------------------------------------------------

@app.post("/api/stories/official")
async def create_official_story_content(
    text: str = Form(""),
    media: UploadFile | None = File(None),
    media_type: str = Form("auto"),
    user=Depends(get_user)
):
    """
    Admin-only: Update the LuvHive Official story content.
    """
    with reg._conn() as con:
        ensure_stories_tables(con)
        story_id = get_or_create_official_story(con)

        file_id = None
        if media:
            data = await media.read()
            if len(data) > 10 * 1024 * 1024:
                raise HTTPException(413, "File too large (>10MB)")
            file_id = await tg_upload_to_sink(
                data, media.filename or "media", media.content_type or "application/octet-stream", text
            )

        # Update the official story content
        with con.cursor() as cur:
            cur.execute("""
                UPDATE stories 
                SET text = %s, media_id = %s, created_at = NOW()
                WHERE id = %s
                RETURNING created_at
            """, (text or None, file_id, story_id))
            created = cur.fetchone()[0]

        con.commit()
        return {
            "ok": True,
            "story_id": story_id,
            "story": {
                "id": story_id,
                "kind": "official",
                "text": text or "",
                "media_url": media_proxy_url(file_id) if file_id else None,
                "created_at": created.isoformat()
            }
        }

# --- User Story Endpoints -----------------------------------------------------------

@app.post("/api/stories")
async def create_user_story(
    text: str = Form(""),
    media: UploadFile | None = File(None),
    media_type: str = Form("auto"),
    user=Depends(get_user)
):
    """
    Create a story segment for the current user.
    Reuses existing story within 24h or creates a new one.
    """
    with reg._conn() as con:
        ensure_stories_tables(con)
        uid = get_or_create_user_id(con, user)

        # Upload file if present
        file_id = None
        content_type = "text"
        if media:
            raw = await media.read()
            if len(raw) > 10 * 1024 * 1024:
                raise HTTPException(413, "File too large (>10MB)")
            file_id = await tg_upload_to_sink(
                raw, media.filename or "media",
                media.content_type or "application/octet-stream", text
            )
            mtype = media.content_type.lower() if media.content_type else ""
            if media_type == "auto":
                content_type = "photo" if mtype.startswith("image/") else \
                               "video" if mtype.startswith("video/") else "document"
            else:
                content_type = media_type

        # Reuse or create the user's story row
        story_id = get_or_create_user_story(con, uid)

        with con.cursor() as cur:
            # Insert a segment into the existing story
            cur.execute("""
                INSERT INTO story_segments
                    (story_id, segment_type, content_type, file_id, text, user_id)
                VALUES (%s, 'user', %s, %s, %s, %s)
                RETURNING id, created_at
            """, (story_id, content_type, file_id, text or None, uid))
            segment_id, created = cur.fetchone()

        con.commit()
        return {
            "ok": True,
            "story_id": story_id,
            "segment": {
                "id": segment_id,
                "content_type": content_type,
                "media_url": media_proxy_url(file_id) if file_id else None,
                "text": text or "",
                "created_at": created.isoformat()
            }
        }

@app.get("/api/stories")
async def list_stories(current=Depends(get_user)):
    """
    Return all story circles visible to the current user:
    - The official LuvHive story (if any recent content)
    - Stories from users you follow or own (last 24h)
    """
    with reg._conn() as con:
        ensure_stories_tables(con)
        uid = get_or_create_user_id(con, current)
        results = []

        with con.cursor() as cur:
            # Ensure user_follows table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_follows (
                    follower_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    followee_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (follower_id, followee_id)
                )
            """)

            # Get official story
            official_id = get_or_create_official_story(con)

            # Check if user has seen official story
            seen_official = False
            try:
                cur.execute("SELECT 1 FROM story_views WHERE story_id=%s AND user_id=%s", (official_id, uid))
                seen_official = bool(cur.fetchone())
            except Exception:
                con.rollback()
                seen_official = False

            # Get official story content (if any)
            cur.execute("""
                SELECT text, media_id, created_at FROM stories WHERE id=%s
            """, (official_id,))
            official_data = cur.fetchone()

            if official_data and (official_data[0] or official_data[1]):  # Has content
                results.append({
                    "id": official_id, 
                    "kind": "official", 
                    "author_id": None,  # Official stories have NULL author_id
                    "name": "LuvHive✨", 
                    "avatar_url": "official_default",
                    "text": official_data[0] or "",
                    "media_url": media_proxy_url(official_data[1]) if official_data[1] else None,
                    "created_at": official_data[2].isoformat() if official_data[2] else None,
                    "seen": seen_official
                })

            # Get user stories from followed users and self
            try:
                cur.execute("SELECT followee_id FROM user_follows WHERE follower_id=%s", (uid,))
                followed_user_ids = [r[0] for r in cur.fetchall()]
                followed_user_ids.append(uid)  # Include own stories
            except Exception:
                con.rollback()
                followed_user_ids = [uid]  # fallback to just current user

            if followed_user_ids:
                # Get recent user stories
                cur.execute("""
                    SELECT id, author_id, kind, text, media_id, created_at
                    FROM stories
                    WHERE kind='user' AND author_id = ANY(%s) AND expires_at > NOW()
                    ORDER BY created_at DESC
                """, (followed_user_ids,))

                user_stories = cur.fetchall()

                for story_id, author_id, kind, text, media_id, created_at in user_stories:
                    # Check if current user has viewed this story
                    viewed = False
                    try:
                        cur.execute("SELECT 1 FROM story_views WHERE story_id=%s AND user_id=%s", (story_id, uid))
                        viewed = bool(cur.fetchone())
                    except Exception:
                        con.rollback()
                        viewed = False

                    # Get segments for this story
                    cur.execute("""
                        SELECT id, segment_type, content_type, file_id, text, created_at
                        FROM story_segments
                        WHERE story_id = %s
                        ORDER BY created_at ASC
                    """, (story_id,))
                    segment_rows = cur.fetchall()

                    segments = []
                    for seg_row in segment_rows:
                        seg_id, seg_type, content_type, file_id, seg_text, seg_created = seg_row
                        segments.append({
                            "id": seg_id,
                            "segment_type": seg_type,
                            "content_type": content_type,
                            "media_url": media_proxy_url(file_id) if file_id else None,
                            "text": seg_text or "",
                            "created_at": seg_created.isoformat() if seg_created else None
                        })

                    # Get author name
                    author_name = get_profile_name(author_id, con) if author_id else "Anonymous"

                    results.append({
                        "id": story_id,
                        "kind": kind,
                        "author_id": author_id,
                        "name": author_name,
                        "avatar_url": None,
                        "text": text or "",
                        "media_url": media_proxy_url(media_id) if media_id else None,
                        "created_at": created_at.isoformat() if created_at else None,
                        "seen": viewed,
                        "segments": segments
                    })

        return {"ok": True, "stories": results}

@app.get("/api/stories/{story_id}")
async def get_story_details(story_id: int, user=Depends(get_user)):
    """
    Fetch a story's details with segments and mark it as viewed by the current user.
    """
    with reg._conn() as con:
        ensure_stories_tables(con)
        uid = get_or_create_user_id(con, user)

        with con.cursor() as cur:
            cur.execute("SELECT author_id, kind, text, media_id, created_at, expires_at FROM stories WHERE id=%s", (story_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Story not found")

            author_id, kind, text, media_id, created_at, expires_at = row

            # Get story segments
            cur.execute("""
                SELECT id, segment_type, content_type, file_id, text, created_at
                FROM story_segments
                WHERE story_id = %s
                ORDER BY created_at ASC
            """, (story_id,))
            segment_rows = cur.fetchall()

            segments = []
            for seg_row in segment_rows:
                seg_id, seg_type, content_type, file_id, seg_text, seg_created = seg_row
                segments.append({
                    "id": seg_id,
                    "segment_type": seg_type,
                    "content_type": content_type,
                    "media_url": media_proxy_url(file_id) if file_id else None,
                    "text": seg_text or "",
                    "created_at": seg_created.isoformat() if seg_created else None
                })

            # Record view
            try:
                cur.execute("""
                    INSERT INTO story_views (story_id, user_id)
                    VALUES (%s, %s)
                    ON CONFLICT (story_id, user_id) DO NOTHING
                """, (story_id, uid))
            except Exception:
                con.rollback()

        con.commit()
        return {
            "ok": True, 
            "story": {
                "id": story_id, 
                "author_id": author_id,
                "kind": kind, 
                "text": text or "",
                "media_url": media_proxy_url(media_id) if media_id else None,
                "created_at": created_at.isoformat() if created_at else None,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "segments": segments
            }
        }

@app.post("/api/stories/{story_id}/view")
async def mark_story_viewed(story_id: int, user=Depends(get_user)):
    """
    Record that the user has viewed the given story. Safe to call multiple times.
    """
    with reg._conn() as con:
        ensure_stories_tables(con)
        uid = get_or_create_user_id(con, user)
        with con.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO story_views (story_id, user_id)
                    VALUES (%s, %s)
                    ON CONFLICT (story_id, user_id) DO NOTHING
                """, (story_id, uid))
            except Exception:
                # Fallback if constraint doesn't exist
                con.rollback()
                cur.execute("""
                    INSERT INTO story_views (story_id, user_id)
                    VALUES (%s, %s)
                """, (story_id, uid))
        con.commit()
        return {"ok": True}



@app.post("/api/stories/official/{segment_type}")
async def create_official_story_segment(
    segment_type: str,
    text: str = Form(""),
    media: UploadFile | None = File(None),
    media_type: str = Form("auto"),
    user=Depends(get_user)
):
    """
    Create a new segment in the LuvHive official story.
    Only admin calls should hit this endpoint.
    """
    seg_type = segment_type.lower()
    if seg_type not in {"confession", "dare", "poll", "spotlight"}:
        raise HTTPException(400, "Invalid official segment type")
    with reg._conn() as con:
        ensure_stories_tables(con)
        story_id = get_or_create_official_story(con)
        ctype = "text"
        file_id = None
        if media:
            data = await media.read()
            if len(data) > 10 * 1024 * 1024:
                raise HTTPException(413, "File too large")
            file_id = await tg_upload_to_sink(
                data, media.filename or "media", media.content_type or "application/octet-stream", text
            )
            # Determine content_type
            mtype = (media.content_type or "").lower()
            if media_type == "auto":
                ctype = "photo" if mtype.startswith("image/") else "video" if mtype.startswith("video/") else "document"
            else:
                ctype = media_type
        with con.cursor() as cur:
            cur.execute("""
                INSERT INTO story_segments
                    (story_id, segment_type, content_type, file_id, text, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (story_id, seg_type, ctype, file_id, text or None, get_or_create_user_id(con, user)))
            seg_id, created = cur.fetchone()
        con.commit()
        return {
            "ok": True,
            "story_id": story_id,
            "segment": {
                "id": seg_id,
                "segment_type": seg_type,
                "content_type": ctype,
                "media_url": media_proxy_url(file_id) if file_id else None,
                "text": text or "",
                "created_at": created.isoformat()
            }
        }

def run_api():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)