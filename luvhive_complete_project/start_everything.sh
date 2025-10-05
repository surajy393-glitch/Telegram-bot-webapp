#!/bin/bash

echo "🚀 LuvHive Complete Project Startup"
echo "==================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Install Node dependencies
if command_exists yarn; then
    echo "📦 Installing Node dependencies with Yarn..."
    cd frontend && yarn install && cd ..
elif command_exists npm; then
    echo "📦 Installing Node dependencies with NPM..."
    cd frontend && npm install && cd ..
else
    echo "❌ Neither yarn nor npm found. Please install Node.js first."
    exit 1
fi

echo ""
echo "🎯 Choose what to run:"
echo "1) Telegram Bot Only"
echo "2) WebApp Only (Frontend + Backend)"
echo "3) Everything Together (Bot + WebApp)"
echo "4) Just install dependencies (no run)"

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "🤖 Starting Telegram Bot..."
        python main.py
        ;;
    2)
        echo "🌐 Starting WebApp..."
        echo "Starting backend..."
        cd backend && python server.py &
        BACKEND_PID=$!
        echo "Backend started with PID: $BACKEND_PID"
        
        echo "Starting frontend..."
        cd ../frontend && yarn start &
        FRONTEND_PID=$!
        echo "Frontend started with PID: $FRONTEND_PID"
        
        echo ""
        echo "✅ WebApp is running!"
        echo "📱 Frontend: http://localhost:3000"
        echo "🔌 Backend: http://localhost:8001"
        echo "📚 API Docs: http://localhost:8001/docs"
        echo ""
        echo "Press Ctrl+C to stop all services"
        wait $BACKEND_PID $FRONTEND_PID
        ;;
    3)
        echo "🚀 Starting Everything..."
        
        echo "Starting Telegram Bot..."
        python main.py &
        BOT_PID=$!
        echo "Bot started with PID: $BOT_PID"
        
        echo "Starting WebApp Backend..."
        cd backend && python server.py &
        BACKEND_PID=$!
        echo "Backend started with PID: $BACKEND_PID"
        
        echo "Starting WebApp Frontend..."
        cd ../frontend && yarn start &
        FRONTEND_PID=$!
        echo "Frontend started with PID: $FRONTEND_PID"
        
        echo ""
        echo "✅ Everything is running!"
        echo "🤖 Telegram Bot: Check your bot on Telegram"
        echo "📱 WebApp Frontend: http://localhost:3000"
        echo "🔌 WebApp Backend: http://localhost:8001"
        echo "📚 API Docs: http://localhost:8001/docs"
        echo ""
        echo "Press Ctrl+C to stop all services"
        wait $BOT_PID $BACKEND_PID $FRONTEND_PID
        ;;
    4)
        echo "✅ Dependencies installed successfully!"
        echo "You can now run individual components manually."
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac