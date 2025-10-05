#!/bin/bash

echo "🚀 Starting LuvHive WebApp..."

# Install dependencies
echo "📦 Installing backend dependencies..."
cd backend
pip install -r requirements.txt

echo "📦 Installing frontend dependencies..."
cd ../frontend
yarn install

echo "🔧 Starting backend server..."
cd ../backend
python server.py &
BACKEND_PID=$!

echo "🔧 Starting frontend server..."
cd ../frontend
yarn start &
FRONTEND_PID=$!

echo "✅ LuvHive WebApp is starting!"
echo "📱 Frontend: http://localhost:3000"
echo "🔌 Backend: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID