import os
import logging
import asyncio
import datetime
import pytz
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Path, Query, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path as PathLib
import uuid
import json
import hmac
import hashlib
import time
from urllib.parse import parse_qsl
import aiohttp

# Load environment variables
ROOT_DIR = PathLib(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
EXTERNAL_URL = (os.environ.get("EXTERNAL_URL") or "").rstrip("/")
MEDIA_SINK_CHAT_ID = int(os.environ.get("MEDIA_SINK_CHAT_ID", "0"))
PUBLIC_TTL_HOURS = int(os.environ.get("FEED_PUBLIC_TTL_HOURS", "72"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

# FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Preflight options for all API paths
@app.options("/{rest_of_path:path}")
async def options_ok(rest_of_path: str):
    return PlainTextResponse("ok", status_code=200)

# Pydantic models
class OnboardRequest(BaseModel):
    display_name: str
    username: str
    age: int
    avatar_file_id: Optional[str] = None

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class PostCreate(BaseModel):
    content: str
    media_urls: List[str] = []

class CommentCreate(BaseModel):
    content: str
    post_id: str

class StoryCreate(BaseModel):
    media_url: str
    duration: int = 24  # hours

# Telegram WebApp initData verification
def verify_init_data(raw: str) -> dict:
    """Telegram WebApp initData HMAC verify."""
    try:
        # Parse query string
        parsed = dict(parse_qsl(raw))
        
        # Extract hash
        received_hash = parsed.pop('hash', None)
        if not received_hash:
            raise ValueError("No hash provided")
        
        # Create data-check-string
        data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(parsed.items())])
        
        # Create secret key
        secret_key = hmac.new("WebAppData".encode(), BOT_TOKEN.encode(), hashlib.sha256).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash != received_hash:
            raise ValueError("Invalid hash")
        
        # Parse user data
        if 'user' in parsed:
            user_data = json.loads(parsed['user'])
            return user_data
        
        raise ValueError("No user data found")
    except Exception as e:
        raise ValueError(f"Init data verification failed: {e}")

# Dependency to get current user
async def get_current_user(request: Request) -> dict:
    """Extract user from Telegram initData or dev mode."""
    
    # Try different sources for initData
    init_data = None
    
    # Check form data, query params, and headers
    if request.method == "POST":
        try:
            form_data = await request.form()
            init_data = form_data.get("initData")
        except:
            pass
    
    if not init_data:
        init_data = request.query_params.get("initData")
    
    if not init_data:
        init_data = request.headers.get("X-Init-Data")
    
    # Try JSON body
    if not init_data and "application/json" in request.headers.get("content-type", ""):
        try:
            body = await request.json()
            init_data = body.get("initData") or body.get("init_data")
        except:
            pass
    
    if init_data:
        try:
            return verify_init_data(init_data)
        except Exception as e:
            pass
    
    # Dev mode fallback
    if os.getenv("ALLOW_INSECURE_TRIAL") == "1":
        dev_user_header = request.headers.get("X-Dev-User")
        if dev_user_header:
            dev_uid = int(dev_user_header)
        else:
            dev_uid = 647778438  # Fallback user ID
        
        # Check if user exists in MongoDB
        user = await db.users.find_one({"tg_user_id": dev_uid})
        if user:
            return {
                "id": dev_uid, 
                "first_name": user.get("display_name", "User"), 
                "username": user.get("username", f"user{dev_uid}")
            }
        
        return {"id": dev_uid, "first_name": "User", "username": f"user{dev_uid}"}
    
    raise HTTPException(401, "Missing/invalid initData")

# API Routes
@app.get("/api")
async def root():
    return {"message": "Social Platform API"}

@app.get("/api/test-telegram")
async def test_telegram():
    """Test Telegram connection and permissions."""
    try:
        async with aiohttp.ClientSession() as session:
            # Test bot info
            async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe") as resp:
                bot_info = await resp.json()
            
            # Test send message
            async with session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": MEDIA_SINK_CHAT_ID, "text": "🧪 API Test"}
            ) as resp:
                msg_result = await resp.json()
            
            return {
                "bot_working": bot_info.get('ok'),
                "bot_username": bot_info.get('result', {}).get('username'),
                "can_send_messages": msg_result.get('ok'),
                "chat_id": MEDIA_SINK_CHAT_ID,
                "message": "✅ Telegram connection working!" if msg_result.get('ok') else "❌ Cannot send to chat"
            }
    except Exception as e:
        return {"error": str(e), "message": "❌ Telegram connection failed"}

@app.get("/uploads/{filename}")
async def serve_upload(filename: str):
    """Serve uploaded images."""
    file_path = PathLib(f"/app/backend/uploads/{filename}")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=file_path.read_bytes(), media_type="image/jpeg")

@app.get("/api/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

@app.post("/api/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@app.get("/api/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user profile."""
    user_id = user["id"]
    
    # Find user in database
    db_user = await db.users.find_one({"tg_user_id": user_id})
    
    if not db_user:
        return {
            "id": user_id,
            "display_name": user.get("first_name", "User"),
            "username": user.get("username", f"user{user_id}"),
            "is_onboarded": False
        }
    
    return {
        "id": user_id,
        "display_name": db_user.get("display_name"),
        "username": db_user.get("username"),
        "age": db_user.get("age"),
        "avatar_file_id": db_user.get("avatar_file_id"),
        "is_onboarded": True,
        "followers_count": db_user.get("followers_count", 0),
        "following_count": db_user.get("following_count", 0),
        "posts_count": db_user.get("posts_count", 0)
    }

@app.post("/api/onboard")
async def onboard_user(data: OnboardRequest, user: dict = Depends(get_current_user)):
    """Onboard a new user."""
    user_id = user["id"]
    
    # Create user document
    user_doc = {
        "tg_user_id": user_id,
        "display_name": data.display_name,
        "username": data.username,
        "age": data.age,
        "avatar_file_id": data.avatar_file_id,
        "created_at": datetime.datetime.utcnow(),
        "followers_count": 0,
        "following_count": 0,
        "posts_count": 0,
        "is_premium": False
    }
    
    # Upsert user
    await db.users.update_one(
        {"tg_user_id": user_id},
        {"$set": user_doc},
        upsert=True
    )
    
    return {"success": True, "message": "User onboarded successfully"}

@app.get("/api/posts")
async def get_posts(user: dict = Depends(get_current_user)):
    """Get posts for feed."""
    posts = await db.posts.find().sort("created_at", -1).limit(50).to_list(50)
    
    # Add user info to posts
    for post in posts:
        post_user = await db.users.find_one({"tg_user_id": post["user_id"]})
        if post_user:
            post["user"] = {
                "id": post_user["tg_user_id"],
                "display_name": post_user.get("display_name", "User"),
                "username": post_user.get("username", f"user{post_user['tg_user_id']}"),
                "avatar_file_id": post_user.get("avatar_file_id")
            }
        post["id"] = str(post["_id"])
        del post["_id"]  # Remove the ObjectId field
    
    return posts

@app.post("/api/posts")
async def create_post(data: PostCreate, user: dict = Depends(get_current_user)):
    """Create a new post."""
    user_id = user["id"]
    
    post_doc = {
        "user_id": user_id,
        "content": data.content,
        "media_urls": data.media_urls,
        "created_at": datetime.datetime.utcnow(),
        "likes_count": 0,
        "comments_count": 0
    }
    
    result = await db.posts.insert_one(post_doc)
    
    # Increment user's posts count
    await db.users.update_one(
        {"tg_user_id": user_id},
        {"$inc": {"posts_count": 1}}
    )
    
    return {"success": True, "post_id": str(result.inserted_id)}

@app.post("/api/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    """Upload photo to Telegram chat and return file info."""
    try:
        if not MEDIA_SINK_CHAT_ID:
            raise HTTPException(status_code=500, detail="MEDIA_SINK_CHAT_ID not configured")
        
        if not BOT_TOKEN:
            raise HTTPException(status_code=500, detail="BOT_TOKEN not configured")
        
        # Read file content
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        logging.info(f"📤 Uploading photo: {file.filename}, size: {file_size_mb:.2f}MB, content_type: {file.content_type}")
        
        # Check file size (Telegram limit is 10MB for photos, 20MB for documents)
        if file_size_mb > 10:
            raise HTTPException(status_code=400, detail="फाइल बहुत बड़ी है। अधिकतम 10MB समर्थित है।")
        
        # Check if it's an image
        is_image = file.content_type and file.content_type.startswith('image/')
        
        async with aiohttp.ClientSession() as session:
            # Use sendPhoto for images (auto-compresses), sendDocument for others
            if is_image:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                form = aiohttp.FormData()
                form.add_field('chat_id', str(MEDIA_SINK_CHAT_ID))
                form.add_field('photo', content, filename=file.filename, content_type=file.content_type)
                form.add_field('caption', f'📷 {file.filename}')
            else:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
                form = aiohttp.FormData()
                form.add_field('chat_id', str(MEDIA_SINK_CHAT_ID))
                form.add_field('document', content, filename=file.filename, content_type=file.content_type or 'application/octet-stream')
                form.add_field('caption', f'📎 {file.filename}')
            
            async with session.post(url, data=form, timeout=30) as resp:
                resp_text = await resp.text()
                logging.info(f"Telegram raw response (status {resp.status}): {resp_text[:500]}")
                try:
                    result = await resp.json() if resp.content_type == 'application/json' else {"ok": False, "description": resp_text}
                except:
                    result = {"ok": False, "description": resp_text}
                logging.info(f"Telegram parsed response: {result}")
                
                if not result.get('ok'):
                    error_desc = result.get('description', 'Unknown error')
                    logging.error(f"❌ Telegram error: {error_desc}")
                    
                    # User-friendly error messages
                    if 'too big' in error_desc.lower() or 'too large' in error_desc.lower():
                        raise HTTPException(status_code=400, detail="फाइल बहुत बड़ी है। कृपया छोटी इमेज चुनें।")
                    elif 'wrong file' in error_desc.lower() or 'invalid' in error_desc.lower():
                        raise HTTPException(status_code=400, detail="केवल JPEG/PNG इमेज समर्थित हैं।")
                    else:
                        raise HTTPException(status_code=500, detail=f"Telegram error: {error_desc}")
                
                # Get file_id from photo or document
                if is_image and 'photo' in result['result']:
                    photos = result['result']['photo']
                    largest_photo = max(photos, key=lambda p: p.get('file_size', 0))
                    file_id = largest_photo['file_id']
                elif 'document' in result['result']:
                    file_id = result['result']['document']['file_id']
                else:
                    raise HTTPException(status_code=500, detail="No file in Telegram response")
                
                # Get file URL
                file_info_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
                async with session.get(file_info_url) as file_resp:
                    file_data = await file_resp.json()
                    if file_data.get('ok'):
                        file_path = file_data['result']['file_path']
                        photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                    else:
                        photo_url = None
                
                logging.info(f"✅ Photo uploaded to Telegram: {file_id}")
                
                return {
                    "success": True,
                    "file_id": file_id,
                    "photo_url": photo_url,
                    "message_id": result['result'].get('message_id')
                }
    
    except HTTPException:
        raise
    except aiohttp.ClientError as e:
        logging.error(f"❌ Network error: {e}")
        raise HTTPException(status_code=500, detail="नेटवर्क एरर। कृपया फिर से प्रयास करें।")
    except Exception as e:
        logging.error(f"❌ Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stories")
async def get_stories(user: dict = Depends(get_current_user)):
    """Get active stories."""
    # Stories expire after 24 hours
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    
    stories = await db.stories.find({
        "created_at": {"$gt": cutoff}
    }).sort("created_at", -1).to_list(100)
    
    # Add user info to stories
    for story in stories:
        story_user = await db.users.find_one({"tg_user_id": story["user_id"]})
        if story_user:
            story["user"] = {
                "id": story_user["tg_user_id"],
                "display_name": story_user.get("display_name", "User"),
                "username": story_user.get("username", f"user{story_user['tg_user_id']}"),
                "avatar_file_id": story_user.get("avatar_file_id")
            }
        story["id"] = str(story["_id"])
        del story["_id"]  # Remove the ObjectId field
    
    return stories

@app.post("/api/stories")
async def create_story(data: StoryCreate, user: dict = Depends(get_current_user)):
    """Create a new story."""
    user_id = user["id"]
    
    story_doc = {
        "user_id": user_id,
        "media_url": data.media_url,
        "duration": data.duration,
        "created_at": datetime.datetime.utcnow(),
        "views_count": 0
    }
    
    result = await db.stories.insert_one(story_doc)
    return {"success": True, "story_id": str(result.inserted_id)}

@app.post("/api/posts/{post_id}/like")
async def like_post(post_id: str, user: dict = Depends(get_current_user)):
    """Like or unlike a post."""
    from bson import ObjectId
    user_id = user["id"]
    
    # Check if already liked
    existing_like = await db.likes.find_one({
        "user_id": user_id,
        "post_id": ObjectId(post_id)
    })
    
    if existing_like:
        # Unlike
        await db.likes.delete_one({"_id": existing_like["_id"]})
        await db.posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$inc": {"likes_count": -1}}
        )
        return {"liked": False}
    else:
        # Like
        await db.likes.insert_one({
            "user_id": user_id,
            "post_id": ObjectId(post_id),
            "created_at": datetime.datetime.utcnow()
        })
        await db.posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$inc": {"likes_count": 1}}
        )
        return {"liked": True}

@app.get("/api/posts/{post_id}/comments")
async def get_comments(post_id: str):
    """Get comments for a post."""
    from bson import ObjectId
    
    comments = await db.comments.find({
        "post_id": ObjectId(post_id)
    }).sort("created_at", 1).to_list(100)
    
    # Add user info to comments
    for comment in comments:
        comment_user = await db.users.find_one({"tg_user_id": comment["user_id"]})
        if comment_user:
            comment["user"] = {
                "id": comment_user["tg_user_id"],
                "display_name": comment_user.get("display_name", "User"),
                "username": comment_user.get("username", f"user{comment_user['tg_user_id']}"),
                "avatar_file_id": comment_user.get("avatar_file_id")
            }
        comment["id"] = str(comment["_id"])
        comment["post_id"] = str(comment["post_id"])  # Convert ObjectId to string
        del comment["_id"]  # Remove the ObjectId field
    
    return comments

@app.post("/api/posts/{post_id}/comments")
async def create_comment(post_id: str, data: CommentCreate, user: dict = Depends(get_current_user)):
    """Create a comment on a post."""
    from bson import ObjectId
    user_id = user["id"]
    
    comment_doc = {
        "user_id": user_id,
        "post_id": ObjectId(post_id),
        "content": data.content,
        "created_at": datetime.datetime.utcnow()
    }
    
    result = await db.comments.insert_one(comment_doc)
    
    # Increment post's comments count
    await db.posts.update_one(
        {"_id": ObjectId(post_id)},
        {"$inc": {"comments_count": 1}}
    )
    
    return {"success": True, "comment_id": str(result.inserted_id)}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)