
#!/usr/bin/env bash
set -u

# Set environment variables  
export WEBAPP_URL="https://80b36b2d-922c-49ab-bd43-31b478351840-00-1xprbvjyuj6eq.sisko.replit.dev"
echo "🌐 WEBAPP_URL set to: $WEBAPP_URL"

# Install FastAPI dependencies
echo "📦 Installing API dependencies..."
pip install -q fastapi uvicorn python-multipart pydantic psycopg2-binary python-jose

# Function to start frontend server
start_frontend() {
  echo "🎨 Starting React frontend on port 5000..."
  cd webapp
  npm install --silent
  npm run dev -- --host 0.0.0.0 --port 5000 &
  FRONTEND_PID=$!
  echo "Frontend server PID: $FRONTEND_PID"
  cd ..
}

# Function to start API server
start_api() {
  echo "🚀 Starting Mini App API server on port 8000..."
  python3 -m uvicorn api.miniapp_handlers:app --host 0.0.0.0 --port 8000 --reload &
  API_PID=$!
  echo "API server PID: $API_PID"
}

# Function to start bot
start_bot() {
  echo "🤖 Starting Telegram bot..."
  python3 -u main.py &
  BOT_PID=$!
  echo "Bot PID: $BOT_PID"
}

# Cleanup function
cleanup() {
  echo "🛑 Stopping services..."
  if [ ! -z "${FRONTEND_PID:-}" ]; then
    kill $FRONTEND_PID 2>/dev/null || true
  fi
  if [ ! -z "${API_PID:-}" ]; then
    kill $API_PID 2>/dev/null || true
  fi
  if [ ! -z "${BOT_PID:-}" ]; then
    kill $BOT_PID 2>/dev/null || true
  fi
  exit 0
}

# Set trap for cleanup
trap cleanup SIGTERM SIGINT

while true; do
  echo "🎉 Starting LuvHive Mini App (Frontend + API + Bot)..."
  
  # Start frontend server first (port 5000)
  start_frontend
  sleep 3
  
  # Start API server (port 8000)
  start_api
  sleep 3
  
  # Start bot
  start_bot
  
  # Wait for either process to exit
  wait $BOT_PID
  bot_code=$?
  
  echo "⚠️ Bot exited with code $bot_code"
  
  # Kill all servers
  kill $FRONTEND_PID 2>/dev/null || true
  kill $API_PID 2>/dev/null || true
  
  echo "🔄 Restarting in 3s..."
  sleep 3
done
