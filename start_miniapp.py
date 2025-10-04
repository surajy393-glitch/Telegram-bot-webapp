#!/usr/bin/env python3
"""
LuvHive Mini App Startup Script
Runs both the Telegram bot and the FastAPI server for the Instagram-style mini app
"""

import os
import sys
import asyncio
import subprocess
import signal
from concurrent.futures import ThreadPoolExecutor

def start_fastapi_server():
    """Start the FastAPI server for the mini app"""
    try:
        # Install FastAPI dependencies if needed
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements-api.txt"
        ], check=False)
        
        # Start FastAPI server
        import uvicorn
        from api.miniapp_handlers import app
        
        print("🚀 Starting LuvHive Mini App API server on port 8000...")
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            reload=False,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")

def start_telegram_bot():
    """Start the main Telegram bot"""
    try:
        print("🤖 Starting LuvHive Telegram Bot...")
        subprocess.run([sys.executable, "main.py"], check=True)
    except KeyboardInterrupt:
        print("🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")

def main():
    """Main function to start both services"""
    print("🎉 LuvHive Mini App - Instagram-style Social Feed")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ["BOT_TOKEN", "DATABASE_URL"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Set webapp URL if not specified
    if not os.environ.get("WEBAPP_URL"):
        os.environ["WEBAPP_URL"] = "https://your-repl-name.repl.co"
        print("ℹ️ WEBAPP_URL not set, using default. Update this in your environment.")
    
    try:
        # Use ThreadPoolExecutor to run both services
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Start API server in background thread
            api_future = executor.submit(start_fastapi_server)
            
            # Small delay to let API start first
            import time
            time.sleep(2)
            
            # Start bot in main thread
            start_telegram_bot()
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down LuvHive Mini App...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("👋 LuvHive Mini App stopped.")

if __name__ == "__main__":
    main()