import os
import logging
import hashlib
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
ALLOW_INSECURE_TRIAL = int(os.environ.get("ALLOW_INSECURE_TRIAL", "0"))

# Upload mode: 'telegram' (default if creds present) or 'local'
UPLOAD_MODE = os.environ.get("UPLOAD_MODE") or ("telegram" if BOT_TOKEN and MEDIA_SINK_CHAT_ID else "local")
ROOT_DIR = Path(__file__).parent
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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

@app.post("/api/register")
async def register_user(user_data: dict):
    """Register a new user."""
    try:
        logging.info(f"📝 Registering new user: {user_data.get('username', 'unknown')}")
        
        # Validate required fields
        required_fields = ['name', 'username', 'age', 'gender']
        for field in required_fields:
            if not user_data.get(field):
                raise HTTPException(status_code=400, detail=f"फील्ड '{field}' आवश्यक है।")
        
        # Check if username already exists
        existing_user = await db.users.find_one({"username": user_data['username']})
        if existing_user:
            raise HTTPException(status_code=409, detail="यह यूजरनेम पहले से उपयोग में है।")
        
        # Generate default avatar if none provided
        avatar_url = user_data.get('avatarUrl') or user_data.get('profilePic')
        if not avatar_url:
            # Generate a default avatar based on name
            safe_name = user_data['name'].replace(' ', '+')
            avatar_url = f"https://ui-avatars.com/api/?name={safe_name}&background=random&color=fff&size=200"
        
        # Create user document
        user_doc = {
            "tg_user_id": user_data.get('id', f"user_{int(time.time())}"),
            "name": user_data['name'],
            "username": user_data['username'],
            "age": int(user_data['age']),
            "gender": user_data['gender'],
            "bio": user_data.get('bio', ''),
            "avatar_url": avatar_url,
            "mood": user_data.get('mood', 'joyful'),
            "aura": user_data.get('aura', 'purple'),
            "stats": user_data.get('stats', {"posts": 0, "followers": 0, "following": 0, "sparks": 0}),
            "join_date": datetime.datetime.utcnow(),
            "is_active": True
        }
        
        # Insert user into database
        result = await db.users.insert_one(user_doc)
        
        logging.info(f"✅ User registered successfully: {result.inserted_id}")
        
        return {
            "success": True,
            "message": "रजिस्ट्रेशन सफल हुई!",
            "user_id": str(result.inserted_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Registration error: {e}")
        raise HTTPException(status_code=500, detail="रजिस्ट्रेशन में समस्या हुई।")

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
        
        # Validate image file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="केवल इमेज फाइलें (JPEG, PNG, WebP) समर्थित हैं।")
        
        # Check file size (20MB max for images)
        if file_size_mb > 20:
            raise HTTPException(status_code=400, detail="इमेज बहुत बड़ी है। अधिकतम 20MB समर्थित है।")
        
        async with aiohttp.ClientSession() as session:
            # Choose upload method based on file size
            use_send_document = False
            
            if file_size_mb <= 10:
                # Use sendPhoto for smaller images (better compression)
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                form = aiohttp.FormData()
                form.add_field('chat_id', str(MEDIA_SINK_CHAT_ID))
                form.add_field('photo', content, filename=file.filename, content_type=file.content_type)
                form.add_field('caption', f'📷 {file.filename}')
                logging.info(f"📤 Using sendPhoto for {file.filename} ({file_size_mb:.2f}MB)")
            else:
                # Use sendDocument for large images (10-20MB)
                use_send_document = True
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
                form = aiohttp.FormData()
                form.add_field('chat_id', str(MEDIA_SINK_CHAT_ID))
                form.add_field('document', content, filename=file.filename, content_type=file.content_type)
                form.add_field('caption', f'📷 Large Image: {file.filename}')
                logging.info(f"📤 Using sendDocument for large image {file.filename} ({file_size_mb:.2f}MB)")
            
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
                if not use_send_document and 'photo' in result['result']:
                    # sendPhoto response
                    photos = result['result']['photo']
                    largest_photo = max(photos, key=lambda p: p.get('file_size', 0))
                    file_id = largest_photo['file_id']
                    logging.info(f"✅ sendPhoto successful, file_id: {file_id}")
                elif 'document' in result['result']:
                    # sendDocument response (for large images)
                    file_id = result['result']['document']['file_id']
                    logging.info(f"✅ sendDocument successful, file_id: {file_id}")
                else:
                    raise HTTPException(status_code=500, detail="No file in Telegram response")
                
                # Get file URL - MUST succeed
                file_info_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
                async with session.get(file_info_url) as file_resp:
                    file_data = await file_resp.json()
                    if not file_data.get('ok'):
                        logging.error(f"Failed to get file info: {file_data}")
                        raise HTTPException(status_code=500, detail="Failed to get file URL from Telegram")
                    
                    file_path = file_data['result']['file_path']
                    photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                
                logging.info(f"✅ Photo uploaded to Telegram: {file_id}, URL: {photo_url[:80]}...")
                
                return {
                    "success": True,
                    "file_id": file_id,
                    "photo_url": photo_url,
                    "media_type": "image",
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

@app.post("/api/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """Upload video to Telegram chat and return file info."""
    try:
        if not MEDIA_SINK_CHAT_ID:
            raise HTTPException(status_code=500, detail="MEDIA_SINK_CHAT_ID not configured")
        
        if not BOT_TOKEN:
            raise HTTPException(status_code=500, detail="BOT_TOKEN not configured")
        
        # Read file content
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        logging.info(f"📤 Uploading video: {file.filename}, size: {file_size_mb:.2f}MB, content_type: {file.content_type}")
        
        # Validate video file type
        if not file.content_type or not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="केवल वीडियो फाइलें (MP4, MOV, AVI, WebM) समर्थित हैं।")
        
        # Check file size (50MB max for videos)
        if file_size_mb > 50:
            raise HTTPException(status_code=400, detail="वीडियो बहुत बड़ा है। अधिकतम 50MB समर्थित है।")
        
        async with aiohttp.ClientSession() as session:
            # Use sendVideo for videos (up to 50MB)
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
            form = aiohttp.FormData()
            form.add_field('chat_id', str(MEDIA_SINK_CHAT_ID))
            form.add_field('video', content, filename=file.filename, content_type=file.content_type)
            form.add_field('caption', f'🎥 {file.filename}')
            logging.info(f"📤 Using sendVideo for {file.filename} ({file_size_mb:.2f}MB)")
            
            async with session.post(url, data=form, timeout=60) as resp:  # Longer timeout for videos
                resp_text = await resp.text()
                logging.info(f"Telegram video response (status {resp.status}): {resp_text[:500]}")
                try:
                    result = await resp.json() if resp.content_type == 'application/json' else {"ok": False, "description": resp_text}
                except:
                    result = {"ok": False, "description": resp_text}
                logging.info(f"Telegram video parsed response: {result}")
                
                if not result.get('ok'):
                    error_desc = result.get('description', 'Unknown error')
                    logging.error(f"❌ Telegram video error: {error_desc}")
                    
                    # User-friendly error messages
                    if 'too big' in error_desc.lower() or 'too large' in error_desc.lower():
                        raise HTTPException(status_code=400, detail="वीडियो बहुत बड़ा है। कृपया 50MB से कम साइज़ का वीडियो चुनें।")
                    elif 'wrong file' in error_desc.lower() or 'invalid' in error_desc.lower():
                        raise HTTPException(status_code=400, detail="केवल MP4, MOV, AVI, WebM वीडियो समर्थित हैं।")
                    elif 'duration' in error_desc.lower():
                        raise HTTPException(status_code=400, detail="वीडियो बहुत लंबा है। कृपया छोटा वीडियो चुनें।")
                    else:
                        raise HTTPException(status_code=500, detail=f"Telegram error: {error_desc}")
                
                # Get file_id from video
                if 'video' in result['result']:
                    video_info = result['result']['video']
                    file_id = video_info['file_id']
                    
                    # Get video thumbnail if available
                    thumb_file_id = None
                    if 'thumb' in video_info:
                        thumb_file_id = video_info['thumb']['file_id']
                    
                    logging.info(f"✅ sendVideo successful, file_id: {file_id}")
                else:
                    raise HTTPException(status_code=500, detail="No video in Telegram response")
                
                # Get video URL - MUST succeed
                file_info_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
                async with session.get(file_info_url) as file_resp:
                    file_data = await file_resp.json()
                    if not file_data.get('ok'):
                        logging.error(f"Failed to get video file info: {file_data}")
                        raise HTTPException(status_code=500, detail="Failed to get video URL from Telegram")
                    
                    file_path = file_data['result']['file_path']
                    video_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                
                # Get thumbnail URL if available
                thumb_url = None
                if thumb_file_id:
                    thumb_info_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={thumb_file_id}"
                    try:
                        async with session.get(thumb_info_url) as thumb_resp:
                            thumb_data = await thumb_resp.json()
                            if thumb_data.get('ok'):
                                thumb_path = thumb_data['result']['file_path']
                                thumb_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{thumb_path}"
                    except:
                        pass  # Thumbnail is optional
                
                logging.info(f"✅ Video uploaded to Telegram: {file_id}, URL: {video_url[:80]}...")
                
                return {
                    "success": True,
                    "file_id": file_id,
                    "video_url": video_url,
                    "thumb_url": thumb_url,
                    "media_type": "video",
                    "duration": video_info.get('duration', 0),
                    "width": video_info.get('width', 0),
                    "height": video_info.get('height', 0),
                    "message_id": result['result'].get('message_id')
                }
    
    except HTTPException:
        raise
    except aiohttp.ClientError as e:
        logging.error(f"❌ Network error: {e}")
        raise HTTPException(status_code=500, detail="नेटवर्क एरर। कृपया फिर से प्रयास करें।")
    except Exception as e:
        logging.error(f"❌ Video upload error: {e}")
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

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: str, user: dict = Depends(get_current_user)):
    """Delete a post (only by the owner)."""
    from bson import ObjectId
    user_id = user["id"]
    
    try:
        # Find the post first
        post = await db.posts.find_one({"_id": ObjectId(post_id)})
        
        if not post:
            raise HTTPException(status_code=404, detail="पोस्ट नहीं मिली।")
        
        # Check if user is the owner of the post
        if post["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="आप केवल अपनी पोस्ट डिलीट कर सकते हैं।")
        
        # Delete the post
        result = await db.posts.delete_one({"_id": ObjectId(post_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="पोस्ट डिलीट नहीं हो सकी।")
        
        # Delete associated comments
        await db.comments.delete_many({"post_id": ObjectId(post_id)})
        
        # Delete associated likes
        await db.likes.delete_many({"post_id": ObjectId(post_id)})
        
        # Decrement user's posts count
        await db.users.update_one(
            {"tg_user_id": user_id},
            {"$inc": {"posts_count": -1}}
        )
        
        return {"success": True, "message": "पोस्ट सफलतापूर्वक डिलीट हो गई।"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Delete post error: {e}")
        raise HTTPException(status_code=500, detail="पोस्ट डिलीट करने में त्रुटि हुई।")

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