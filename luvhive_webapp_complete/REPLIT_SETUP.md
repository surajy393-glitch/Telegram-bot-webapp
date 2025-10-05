# LuvHive WebApp - Replit Setup Guide

## Quick Start Instructions

### 1. Upload & Extract
- Upload this zip file to Replit
- Extract all files to your project root

### 2. Install Dependencies

**Backend Setup:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend Setup:**
```bash
cd frontend
yarn install
```

### 3. Environment Variables
Both `.env` files are already included:
- `backend/.env` - Backend configuration
- `frontend/.env` - Frontend configuration

### 4. Run the Application

**Start Backend (Terminal 1):**
```bash
cd backend
python server.py
```

**Start Frontend (Terminal 2):**
```bash
cd frontend
yarn start
```

### 5. Access the WebApp
- Frontend will be available at: `http://localhost:3000`
- Backend API at: `http://localhost:8001`

## Features Working ✅
- ✅ Timestamps display correctly (14h ago, 2d ago)
- ✅ User profile posts display properly
- ✅ Edit profile save button works immediately
- ✅ Social feed with posts and stories
- ✅ Create post functionality
- ✅ Avatar display system
- ✅ Like/reaction system
- ✅ Comments and reply system

## Tech Stack
- **Frontend**: React + TailwindCSS
- **Backend**: FastAPI + Python
- **Database**: MongoDB (configured)

## Important Notes
- All environment variables are pre-configured
- MongoDB URL is set for local development
- Backend runs on port 8001, Frontend on port 3000
- All three critical fixes have been implemented and tested

## Troubleshooting
If you face any issues:
1. Make sure both terminals are running
2. Check that ports 3000 and 8001 are available
3. Verify all dependencies are installed

## Structure
```
luvhive_webapp_complete/
├── frontend/          # React frontend
├── backend/           # FastAPI backend
├── .replit           # Replit configuration
└── REPLIT_SETUP.md   # This file
```

Ready to run! 🚀