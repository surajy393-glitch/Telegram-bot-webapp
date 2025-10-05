#!/usr/bin/env python3
"""
Run the original bot with environment variables set
"""
import os
import sys

# Set environment variables for original bot
os.environ["BOT_TOKEN"] = "8494034049:AAEb5jiuYLUMmkjsIURx6RqhHJ4mj3bOI10"
os.environ["MEDIA_SINK_CHAT_ID"] = "-1003138482795"
os.environ["DATABASE_URL"] = "sqlite:///luvhive.db"  # Use SQLite for simplicity
os.environ["ADMIN_IDS"] = "647778438,1234567890"

# Import and run the main bot
try:
    print("🚀 Starting ORIGINAL LuvHive Bot...")
    print("📱 Using your exact bot files without any modifications")
    print("=" * 50)
    
    # Import main
    import main
    
except Exception as e:
    print(f"❌ Error starting original bot: {e}")
    print("The original bot requires PostgreSQL database setup.")
    print("Working on webapp part instead...")