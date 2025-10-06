# backend/routers/profile_v2.py
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Any, Dict
from .deps import get_db, get_current_user  # adjust import paths

router = APIRouter(prefix="/api/my", tags=["my-profile"])

@router.get("/profile")
async def get_my_profile(db=Depends(get_db), user=Depends(get_current_user)) -> Dict[str, Any]:
    prof = await db.fetchrow("SELECT * FROM profiles WHERE telegram_id=$1", user.telegram_id)
    if not prof:
        # upsert; guarantees single canonical profile
        prof = await db.fetchrow("""
            INSERT INTO profiles (id, user_id, telegram_id, display_name, bio, avatar_url)
            VALUES (gen_random_uuid(), $1, $2, $3, '', NULL)
            ON CONFLICT (telegram_id) DO UPDATE
              SET user_id = EXCLUDED.user_id
            RETURNING *;
        """, user.id, user.telegram_id, user.display_name or user.username or '')
    # counts
    counts = await db.fetchrow("""
        SELECT
          (SELECT COUNT(*) FROM posts WHERE profile_id=$1) AS posts_count,
          COALESCE((SELECT COUNT(*) FROM followers WHERE followee_id=$1),0) AS followers_count,
          COALESCE((SELECT COUNT(*) FROM followers WHERE follower_id=$1),0) AS following_count
    """, prof["id"])
    return {"profile": dict(prof), "counts": dict(counts)}

@router.get("/posts")
async def get_my_posts(db=Depends(get_db), user=Depends(get_current_user)):
    profile_id = await db.fetchval("SELECT id FROM profiles WHERE telegram_id=$1", user.telegram_id)
    if not profile_id:
        return []  # no demo fallback; real empty state only
    rows = await db.fetch("""
        SELECT * FROM posts
        WHERE profile_id=$1
        ORDER BY created_at DESC
        LIMIT 100
    """, profile_id)
    return [dict(r) for r in rows]

@router.post("/post")
async def create_post(payload: Dict[str, Any], request: Request, db=Depends(get_db), user=Depends(get_current_user)):
    key = request.headers.get("X-Idempotency-Key")
    if not key:
        raise HTTPException(400, "X-Idempotency-Key required")

    # resolve canonical profile (upsert if needed)
    profile = await db.fetchrow("""
        INSERT INTO profiles (id, user_id, telegram_id)
        VALUES (gen_random_uuid(), $1, $2)
        ON CONFLICT (telegram_id) DO UPDATE SET user_id=EXCLUDED.user_id
        RETURNING id;
    """, user.id, user.telegram_id)
    profile_id = profile["id"]

    # return existing if same idempotency request seen
    existing = await db.fetchrow("""
        SELECT * FROM posts WHERE user_id=$1 AND idempotency_key=$2
    """, user.id, key)
    if existing:
        return dict(existing)

    try:
        created = await db.fetchrow("""
            INSERT INTO posts (id, user_id, profile_id, content, media_url, idempotency_key)
            VALUES (gen_random_uuid(), $1, $2, $3, $4, $5)
            RETURNING *;
        """, user.id, profile_id, payload.get("content",""), payload.get("media_url"), key)
        return dict(created)
    except Exception:
        # race-safe
        existing = await db.fetchrow("""
            SELECT * FROM posts WHERE user_id=$1 AND idempotency_key=$2
        """, user.id, key)
        if existing:
            return dict(existing)
        raise