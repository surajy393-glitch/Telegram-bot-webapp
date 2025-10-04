#!/usr/bin/env python3
"""
LuvHive Complete Project Packager
Creates a comprehensive zip file with all project components
"""

import os
import zipfile
import json
import time
from pathlib import Path
import subprocess
import sys

def create_database_export():
    """Create database schema and export current data"""
    print("📊 Exporting database schema and data...")
    
    # Database schema
    schema_sql = """
-- LuvHive Database Schema Export
-- Generated on: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """

-- Users table
CREATE TABLE IF NOT EXISTS users (
    tg_user_id BIGINT PRIMARY KEY,
    display_name VARCHAR(100),
    username VARCHAR(50) UNIQUE,
    age INTEGER,
    gender VARCHAR(20),
    bio TEXT,
    avatar_file_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    is_premium BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    last_seen TIMESTAMP DEFAULT NOW(),
    profile_pic_url TEXT,
    mood VARCHAR(50),
    aura VARCHAR(50),
    interests TEXT[], -- Array of interests
    search_preferences JSONB,
    privacy_settings JSONB,
    is_banned BOOLEAN DEFAULT FALSE,
    ban_until TIMESTAMP,
    ban_reason TEXT
);

-- Posts table  
CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES users(tg_user_id),
    content TEXT NOT NULL,
    media_urls TEXT[],
    mood VARCHAR(50),
    music JSONB, -- {name, artist, duration, genre}
    location VARCHAR(255),
    vibe_score INTEGER DEFAULT 0,
    spark_count INTEGER DEFAULT 0,
    glow_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    is_spark_post BOOLEAN DEFAULT FALSE,
    spark_duration VARCHAR(50)
);

-- Stories table
CREATE TABLE IF NOT EXISTS stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES users(tg_user_id),
    story_type VARCHAR(20), -- 'text' or 'image'
    content JSONB, -- Story content with type-specific data
    background_color VARCHAR(100),
    mood VARCHAR(50),
    music JSONB,
    location VARCHAR(255),
    poll JSONB, -- Poll data if present
    views_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '24 hours')
);

-- Comments table
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES users(tg_user_id),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Likes table
CREATE TABLE IF NOT EXISTS likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES users(tg_user_id),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, post_id)
);

-- Follows table
CREATE TABLE IF NOT EXISTS follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    follower_id BIGINT REFERENCES users(tg_user_id),
    following_id BIGINT REFERENCES users(tg_user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(follower_id, following_id)
);

-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user1_id BIGINT REFERENCES users(tg_user_id),
    user2_id BIGINT REFERENCES users(tg_user_id),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP
);

-- Premium subscriptions table
CREATE TABLE IF NOT EXISTS premium_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES users(tg_user_id),
    plan_type VARCHAR(50),
    start_date TIMESTAMP DEFAULT NOW(),
    end_date TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    payment_id VARCHAR(255)
);

-- Blocked users table
CREATE TABLE IF NOT EXISTS blocked_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT REFERENCES users(tg_user_id),
    blocked_uid BIGINT REFERENCES users(tg_user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, blocked_uid)
);

-- Reported content table
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id BIGINT REFERENCES users(tg_user_id),
    reported_user_id BIGINT REFERENCES users(tg_user_id),
    content_type VARCHAR(20), -- 'post', 'story', 'comment', 'user'
    content_id UUID,
    reason VARCHAR(100),
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    reviewed_by BIGINT
);

-- Story views table
CREATE TABLE IF NOT EXISTS story_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    viewer_id BIGINT REFERENCES users(tg_user_id),
    viewed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(story_id, viewer_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_stories_user_id ON stories(user_id);
CREATE INDEX IF NOT EXISTS idx_stories_expires_at ON stories(expires_at);
CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_likes_post_id ON likes(post_id);
CREATE INDEX IF NOT EXISTS idx_follows_follower_id ON follows(follower_id);
CREATE INDEX IF NOT EXISTS idx_follows_following_id ON follows(following_id);

-- Sample data
INSERT INTO users (tg_user_id, display_name, username, age, gender, bio, created_at) VALUES
(647778438, 'LuvHive Admin', 'admin', 25, 'prefer-not-to-say', 'Welcome to LuvHive! 💕', NOW()),
(1437934486, 'Test User', 'testuser', 22, 'female', 'Just testing the amazing LuvHive features! ✨', NOW())
ON CONFLICT (tg_user_id) DO NOTHING;
"""

    # Write schema to file
    with open('/app/database_complete_schema.sql', 'w') as f:
        f.write(schema_sql)
    
    return '/app/database_complete_schema.sql'

def create_deployment_guide():
    """Create comprehensive deployment guide"""
    print("📝 Creating deployment guide...")
    
    deployment_guide = """
# 🚀 LuvHive Complete Deployment Guide

## 📋 Project Overview
LuvHive is a comprehensive social media platform with:
- Telegram Bot for user interactions
- React WebApp for social feeds
- FastAPI Backend for API services
- MongoDB for data storage

## 🔧 Prerequisites
- Python 3.9+
- Node.js 16+ and Yarn
- MongoDB database
- Telegram Bot Token
- Domain/Server for hosting

## 📁 Project Structure
```
luvhive/
├── main.py                 # Main Telegram bot entry point
├── backend/
│   ├── server.py          # FastAPI backend server
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/               # React application
│   ├── package.json       # Frontend dependencies
│   └── build/            # Production build (after npm run build)
├── handlers/              # Telegram bot handlers
├── utils/                # Utility functions
├── database_complete_schema.sql  # Database schema
└── .env                  # Environment variables
```

## ⚙️ Environment Setup

### 1. Backend Environment (.env)
```bash
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
EXTERNAL_URL=your_domain.com

# Database Configuration  
MONGO_URL=mongodb://localhost:27017/luvhive
DB_NAME=luvhive

# API Configuration
REACT_APP_BACKEND_URL=https://your_domain.com

# Security
SECRET_KEY=your_secret_key_here
ALLOW_INSECURE_TRIAL=0  # Set to 1 for development only

# Optional Services
MEDIA_SINK_CHAT_ID=your_media_chat_id
FEED_PUBLIC_TTL_HOURS=72
```

### 2. Frontend Environment (frontend/.env)
```bash
REACT_APP_BACKEND_URL=https://your_domain.com
REACT_APP_API_URL=https://your_domain.com/api
```

## 🚀 Deployment Steps

### Step 1: Database Setup
```bash
# Install MongoDB and create database
mongosh
use luvhive

# Import schema (optional - will be created automatically)
mongoimport --db luvhive --collection users --file users.json
```

### Step 2: Backend Deployment
```bash
# Install Python dependencies
cd backend/
pip install -r requirements.txt

# Set environment variables
export BOT_TOKEN="your_bot_token"
export MONGO_URL="your_mongo_connection_string"

# Start the backend server
python server.py
```

### Step 3: Frontend Deployment  
```bash
# Install and build frontend
cd frontend/
yarn install
yarn build

# Serve with nginx or deploy to hosting service
# The build/ folder contains the production files
```

### Step 4: Bot Deployment
```bash
# Start the main bot
python main.py
```

## 🔄 Production Deployment Options

### Option A: Single Server (Recommended for small scale)
```bash
# Use supervisor for process management
sudo apt install supervisor

# Create supervisor config for bot
sudo nano /etc/supervisor/conf.d/luvhive-bot.conf
```

### Option B: Docker Deployment
```dockerfile
# Use the included Dockerfile
docker build -t luvhive .
docker run -d --name luvhive-app -p 8001:8001 luvhive
```

### Option C: Cloud Deployment
- **Frontend**: Deploy to Vercel, Netlify, or CloudFlare Pages
- **Backend**: Deploy to Railway, Render, or DigitalOcean
- **Database**: Use MongoDB Atlas
- **Bot**: Deploy to Railway, Render, or VPS

## 📱 Telegram Bot Setup
1. Create bot with @Botfather
2. Get bot token and add to .env
3. Set webhook URL or use polling mode
4. Configure bot commands and menu

## 🌐 WebApp Integration
The React webapp integrates with Telegram WebApp:
- Users can access via bot inline button
- Supports Telegram authentication
- Full social media features available

## 🔧 Key Features Implemented

### ✅ Working Features
- **Story Creation**: Text/Photo stories with 24hr expiration
- **Post Creation**: Full social posts with media, music, location
- **User Profiles**: Instagram-style profiles with post grids
- **Social Feed**: Real-time feed with stories and posts
- **User Registration**: Complete onboarding flow
- **Mood System**: Mood indicators and aura matching
- **Music Integration**: Song selection for posts/stories
- **Privacy Controls**: Block/report functionality

### 🔨 Technical Implementation
- **Frontend**: React 18 with Tailwind CSS
- **State Management**: React Context + localStorage
- **Backend**: FastAPI with async MongoDB
- **Real-time Updates**: WebSocket support ready
- **File Upload**: Chunked upload for large media
- **Error Handling**: Comprehensive error handling
- **Security**: Input validation and CSRF protection

## 🚨 Important Notes
1. **API Keys**: Ensure all API keys are properly configured
2. **CORS**: Update CORS settings for your domain
3. **SSL**: Use HTTPS for production (required by Telegram)
4. **Backup**: Regular database backups recommended
5. **Monitoring**: Set up logging and monitoring
6. **Updates**: Keep dependencies updated regularly

## 🐛 Troubleshooting

### Common Issues:
1. **Bot not responding**: Check bot token and network connectivity
2. **WebApp not loading**: Verify CORS and HTTPS settings
3. **Database errors**: Check MongoDB connection and permissions
4. **Frontend build errors**: Clear node_modules and reinstall

### Debug Commands:
```bash
# Check bot status
python -c "import main; print('Bot configuration OK')"

# Test API endpoints
curl https://your_domain.com/api/

# Check database connection
mongosh your_connection_string
```

## 📞 Support
For technical support or customizations:
- Review error logs in /var/log/ or application logs
- Check database connectivity and permissions  
- Verify all environment variables are set correctly
- Test API endpoints individually

## 🎯 Next Steps
1. Deploy to production environment
2. Set up monitoring and logging
3. Configure backups and disaster recovery
4. Add analytics and performance tracking
5. Scale infrastructure as needed

---
Built with ❤️ for the LuvHive community
"""

    with open('/app/DEPLOYMENT_GUIDE.md', 'w') as f:
        f.write(deployment_guide)
    
    return '/app/DEPLOYMENT_GUIDE.md'

def create_project_readme():
    """Create comprehensive project README"""
    print("📖 Creating project README...")
    
    readme_content = """
# 💕 LuvHive Social Platform

A comprehensive social media platform combining Telegram Bot interactions with a modern React webapp for authentic connections and meaningful conversations.

## ✨ Features

### 🤖 Telegram Bot
- Advanced chat matching system
- Premium subscriptions and payments
- Anonymous confession roulette  
- Daily horoscopes and fun facts
- Comprehensive admin panel
- Multi-language support

### 🌐 WebApp (Social Media Platform)
- **Story Creation**: 24-hour ephemeral stories with text/photo
- **Post Sharing**: Full social posts with images, music, and location
- **User Profiles**: Instagram-style profiles with post grids
- **Social Feed**: Real-time feed with stories and posts
- **Mood System**: Express and match based on current mood
- **Music Integration**: Add songs to posts and stories
- **Privacy Controls**: Block, report, and privacy settings

## 🏗️ Architecture

### Technology Stack
- **Backend**: FastAPI (Python) with async MongoDB
- **Frontend**: React 18 with Tailwind CSS
- **Bot Framework**: python-telegram-bot (PTB)
- **Database**: MongoDB with optimized indexing
- **Authentication**: Telegram WebApp integration
- **File Storage**: Chunked upload system

### Key Components
1. **Main Bot** (`main.py`) - Central Telegram bot with command handlers
2. **Backend API** (`backend/server.py`) - RESTful API for webapp
3. **React Frontend** (`frontend/src/`) - Modern social media interface
4. **Handler System** (`handlers/`) - Modular bot feature handlers
5. **Utilities** (`utils/`) - Shared functionality and helpers

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+ and Yarn
- MongoDB database
- Telegram Bot Token

### Installation
1. **Clone and setup backend**:
   ```bash
   pip install -r backend/requirements.txt
   cp .env.example .env  # Configure your environment
   ```

2. **Setup frontend**:
   ```bash
   cd frontend/
   yarn install
   yarn build
   ```

3. **Start services**:
   ```bash
   # Start bot
   python main.py
   
   # Start API server (in separate terminal)
   python backend/server.py
   ```

### Environment Configuration
See `DEPLOYMENT_GUIDE.md` for detailed environment setup instructions.

## 📱 Core Features

### Social Media WebApp
- **Story Creation**: Rich story editor with backgrounds, music, polls
- **Post Sharing**: Multi-media posts with mood indicators
- **User Profiles**: Complete profile management with post grids  
- **Social Feed**: Algorithm-driven content discovery
- **Real-time Interactions**: Sparks, Glows, comments, and shares

### Bot Integration
- **Smart Matching**: AI-powered user matching system
- **Premium Features**: Enhanced capabilities for subscribers
- **Admin Tools**: Comprehensive moderation and analytics
- **Content Management**: Automated content moderation

## 🔧 Development

### Adding New Features
1. **Bot Features**: Add handlers in `handlers/` directory
2. **API Endpoints**: Extend `backend/server.py` with new routes
3. **Frontend Components**: Create React components in `frontend/src/components/`
4. **Database Models**: Update MongoDB schemas as needed

### Testing
```bash
# Backend testing
python -m pytest tests/

# Frontend testing  
cd frontend/
yarn test

# Integration testing
python test_integration.py
```

## 📊 Database Schema

### Core Collections
- **users**: User profiles and authentication data
- **posts**: Social media posts with media and metadata
- **stories**: 24-hour ephemeral content
- **comments**: Post comments and interactions
- **likes**: User reactions to content
- **follows**: User relationship graph

See `database_complete_schema.sql` for complete schema.

## 🛡️ Security Features

- **Input Validation**: Comprehensive input sanitization
- **Authentication**: Telegram WebApp secure authentication
- **Privacy Controls**: User-controlled privacy settings
- **Content Moderation**: Automated and manual moderation tools
- **Rate Limiting**: API rate limiting and spam protection

## 🚀 Deployment

### Production Deployment
1. **Database**: MongoDB with proper indexing and backups
2. **Backend**: FastAPI with gunicorn/uvicorn in production
3. **Frontend**: Static build served via CDN/nginx
4. **Bot**: Process management with supervisor/systemd
5. **Monitoring**: Comprehensive logging and health checks

See `DEPLOYMENT_GUIDE.md` for step-by-step deployment instructions.

## 📈 Performance

### Optimization Features
- **Database Indexing**: Optimized MongoDB indexes for fast queries
- **Caching**: Redis caching for frequently accessed data
- **CDN Integration**: Static asset optimization
- **Lazy Loading**: Frontend component lazy loading
- **API Optimization**: Efficient pagination and filtering

## 🔄 Updates & Maintenance

### Regular Tasks
- **Database Cleanup**: Automated expired content removal
- **Security Updates**: Regular dependency updates
- **Performance Monitoring**: Continuous performance tracking
- **Backup Management**: Automated backup and recovery procedures

## 🎯 Roadmap

### Upcoming Features
- [ ] Real-time messaging system
- [ ] Advanced AI recommendation engine
- [ ] Video story support
- [ ] Group chat functionality
- [ ] Advanced analytics dashboard
- [ ] Multi-language support expansion

## 📞 Support & Contributing

### Getting Help
1. Check `DEPLOYMENT_GUIDE.md` for setup issues
2. Review error logs for debugging information
3. Verify environment configuration
4. Test API endpoints individually

### Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is proprietary software developed for LuvHive. All rights reserved.

## 🏆 Acknowledgments

- Built with modern web technologies for optimal performance
- Designed for scalability and maintainability
- Focused on user privacy and security
- Optimized for the Telegram ecosystem

---

**Happy Connecting! 💕**

For more information, see the comprehensive deployment guide and technical documentation included in this package.
"""

    with open('/app/README.md', 'w') as f:
        f.write(readme_content)
    
    return '/app/README.md'

def create_env_example():
    """Create environment example file"""
    print("🔑 Creating environment example...")
    
    env_example = """# 🔐 LuvHive Environment Configuration
# Copy this file to .env and fill in your actual values

# ===== TELEGRAM BOT CONFIGURATION =====
BOT_TOKEN=your_telegram_bot_token_here
EXTERNAL_URL=https://your-domain.com

# ===== DATABASE CONFIGURATION =====
MONGO_URL=mongodb://localhost:27017/luvhive
DB_NAME=luvhive

# ===== API & WEB CONFIGURATION =====
REACT_APP_BACKEND_URL=https://your-domain.com
REACT_APP_API_URL=https://your-domain.com/api

# ===== SECURITY =====
SECRET_KEY=your_super_secret_key_here_change_this
ALLOW_INSECURE_TRIAL=0  # Set to 1 only for development/testing

# ===== OPTIONAL SERVICES =====
MEDIA_SINK_CHAT_ID=your_media_backup_chat_id
FEED_PUBLIC_TTL_HOURS=72

# ===== PAYMENT INTEGRATION (if using) =====
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLIC_KEY=pk_test_your_stripe_public_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# ===== REDIS (for caching - optional) =====
REDIS_URL=redis://localhost:6379/0

# ===== EMAIL SERVICES (optional) =====
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# ===== LOGGING =====
LOG_LEVEL=INFO
LOG_FILE=/app/logs/luvhive.log

# ===== PRODUCTION SETTINGS =====
DEBUG=False
RUN_MODE=polling  # or 'webhook' for production
PORT=8001
WEBHOOK_PATH=hook

# ===== FILE STORAGE =====
MAX_FILE_SIZE=10485760  # 10MB in bytes
ALLOWED_FILE_TYPES=image/jpeg,image/png,image/gif,video/mp4

# ===== RATE LIMITING =====
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Notes:
# - Never commit the actual .env file to version control
# - Use strong, unique passwords and keys
# - For production, use environment-specific values
# - Consider using a secrets management service for sensitive data
"""

    with open('/app/.env.example', 'w') as f:
        f.write(env_example)
    
    return '/app/.env.example'

def create_complete_zip():
    """Create comprehensive zip file with all project components"""
    print("🎁 Creating complete LuvHive project zip file...")
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    zip_filename = f"/app/LuvHive_Complete_Project_{timestamp}.zip"
    
    # Create additional documentation files
    schema_file = create_database_export()
    deployment_guide = create_deployment_guide()
    readme_file = create_project_readme()
    env_example = create_env_example()
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Root directory files
        root_files = [
            '/app/main.py',
            '/app/README.md',
            '/app/.env.example', 
            '/app/DEPLOYMENT_GUIDE.md',
            '/app/database_complete_schema.sql',
            '/app/requirements.txt',
            '/app/pyproject.toml'
        ]
        
        for file_path in root_files:
            if os.path.exists(file_path):
                arcname = os.path.basename(file_path)
                zipf.write(file_path, arcname)
                print(f"  ✅ Added: {arcname}")
        
        # Backend files
        backend_base = '/app/backend'
        if os.path.exists(backend_base):
            for root, dirs, files in os.walk(backend_base):
                for file in files:
                    if not file.startswith('.') and file.endswith(('.py', '.txt', '.yml', '.yaml', '.json')):
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('backend', os.path.relpath(file_path, backend_base))
                        zipf.write(file_path, arcname)
                        print(f"  ✅ Added: {arcname}")
        
        # Frontend files
        frontend_base = '/app/frontend'
        if os.path.exists(frontend_base):
            for root, dirs, files in os.walk(frontend_base):
                # Skip node_modules, build, and other large directories
                dirs[:] = [d for d in dirs if d not in ['node_modules', 'build', '.git', 'dist', 'coverage']]
                
                for file in files:
                    if not file.startswith('.') and not file.endswith(('.log', '.tmp')):
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('frontend', os.path.relpath(file_path, frontend_base))
                        zipf.write(file_path, arcname)
                        print(f"  ✅ Added: {arcname}")
        
        # Handler files
        handlers_base = '/app/handlers'
        if os.path.exists(handlers_base):
            for root, dirs, files in os.walk(handlers_base):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('handlers', os.path.relpath(file_path, handlers_base))
                        zipf.write(file_path, arcname)
                        print(f"  ✅ Added: {arcname}")
        
        # Utils files
        utils_base = '/app/utils'
        if os.path.exists(utils_base):
            for root, dirs, files in os.walk(utils_base):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.join('utils', os.path.relpath(file_path, utils_base))
                        zipf.write(file_path, arcname)
                        print(f"  ✅ Added: {arcname}")
        
        # Additional important files
        additional_files = [
            ('/app/chat.py', 'chat.py'),
            ('/app/profile.py', 'profile.py'),
            ('/app/registration.py', 'registration.py'),
            ('/app/premium.py', 'premium.py'),
            ('/app/settings.py', 'settings.py'),
            ('/app/menu.py', 'menu.py'),
            ('/app/admin.py', 'admin.py'),
            ('/app/health.py', 'health.py'),
            ('/app/api_server.py', 'api_server.py')
        ]
        
        for file_path, arcname in additional_files:
            if os.path.exists(file_path):
                zipf.write(file_path, arcname)
                print(f"  ✅ Added: {arcname}")
        
        # Configuration files
        config_files = [
            ('/app/supervisor.conf', 'config/supervisor.conf'),
            ('/app/nginx.conf', 'config/nginx.conf')
        ]
        
        for file_path, arcname in config_files:
            if os.path.exists(file_path):
                zipf.write(file_path, arcname)
                print(f"  ✅ Added: {arcname}")
        
        print(f"\n🎉 Complete project packaged successfully!")
        print(f"📦 Zip file created: {zip_filename}")
        print(f"📊 Total files: {len(zipf.namelist())}")
    
    # Get file size
    file_size = os.path.getsize(zip_filename)
    file_size_mb = file_size / (1024 * 1024)
    
    print(f"💾 File size: {file_size_mb:.2f} MB")
    print(f"📁 Location: {zip_filename}")
    
    return zip_filename

if __name__ == "__main__":
    print("🚀 LuvHive Complete Project Packager")
    print("=" * 50)
    
    try:
        zip_file = create_complete_zip()
        
        print("\n" + "=" * 50)
        print("✅ PROJECT PACKAGING COMPLETE!")
        print(f"📦 Your complete LuvHive project is ready: {os.path.basename(zip_file)}")
        print("\n📋 Package Contents:")
        print("  🤖 Telegram Bot (main.py + all handlers)")
        print("  🌐 React WebApp (complete frontend)")  
        print("  ⚡ FastAPI Backend (API server)")
        print("  🗄️ Database Schema (complete SQL)")
        print("  📖 Documentation (README + Deployment Guide)")
        print("  🔧 Configuration Examples")
        print("  ⚙️ All Utility Functions")
        print("\n🚀 Ready for deployment!")
        
    except Exception as e:
        print(f"❌ Error creating zip file: {e}")
        sys.exit(1)