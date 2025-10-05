#!/usr/bin/env python3
"""
Complete LuvHive Project Archive Creator
Creates a comprehensive zip file with ALL project components including:
- Telegram Bot (main.py + handlers + utils)
- Backend FastAPI Server
- Frontend React Webapp  
- Database Schema & Export
- All Configuration Files
- Documentation & Scripts
"""

import zipfile
import os
import sys
from pathlib import Path
import datetime

def create_complete_zip():
    # Create zip filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"/app/LuvHive_Complete_Project_{timestamp}.zip"
    
    print(f"🚀 Creating complete LuvHive project archive: {zip_filename}")
    print("=" * 60)
    
    # Files and directories to include (everything in /app)
    base_dir = Path("/app")
    
    # Files/directories to exclude (logs, temp files, __pycache__)
    exclude_patterns = [
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '*.log',
        '.DS_Store',
        'node_modules',
        '.git',
        '.emergent',
        'bot_state.pkl',
        '*.swp',
        '*.tmp'
    ]
    
    def should_exclude(file_path):
        """Check if file should be excluded based on patterns"""
        str_path = str(file_path)
        for pattern in exclude_patterns:
            if pattern in str_path or str_path.endswith(pattern.replace('*', '')):
                return True
        return False
    
    # Count totals
    total_files = 0
    included_files = 0
    excluded_files = 0
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        
        # Add all files recursively
        for root, dirs, files in os.walk(base_dir):
            # Remove excluded directories from dirs list to avoid walking into them
            dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d)]
            
            for file in files:
                file_path = Path(root) / file
                total_files += 1
                
                if should_exclude(file_path):
                    excluded_files += 1
                    continue
                
                # Create relative path from /app
                relative_path = file_path.relative_to(base_dir)
                
                try:
                    zipf.write(file_path, relative_path)
                    included_files += 1
                    print(f"✅ Added: {relative_path}")
                    
                except Exception as e:
                    print(f"❌ Error adding {relative_path}: {e}")
                    excluded_files += 1
    
    # Get zip file size
    zip_size = os.path.getsize(zip_filename)
    zip_size_mb = zip_size / (1024 * 1024)
    
    print("=" * 60)
    print("📊 ARCHIVE SUMMARY:")
    print(f"📁 Total files scanned: {total_files}")
    print(f"✅ Files included: {included_files}")
    print(f"🚫 Files excluded: {excluded_files}")
    print(f"📦 Archive size: {zip_size_mb:.2f} MB")
    print(f"📄 Archive location: {zip_filename}")
    print("=" * 60)
    
    # Verify archive contents
    print("\n🔍 VERIFYING ARCHIVE CONTENTS:")
    with zipfile.ZipFile(zip_filename, 'r') as zipf:
        file_list = zipf.namelist()
        
        # Check for key components
        key_components = {
            "Bot Files": ["main.py", "registration.py", "handlers/", "utils/"],
            "Backend": ["backend/server.py", "backend/requirements.txt"],
            "Frontend": ["frontend/package.json", "frontend/src/App.js"],
            "Database": ["database_schema.sql"],
            "Config": [".env", "requirements.txt"],
            "Documentation": ["README.md"]
        }
        
        for component, expected_files in key_components.items():
            found = []
            for expected in expected_files:
                matching = [f for f in file_list if expected in f]
                found.extend(matching[:3])  # Show first 3 matches
            
            if found:
                print(f"✅ {component}: {', '.join(found[:3])}")
                if len(found) > 3:
                    print(f"   ... and {len(found)-3} more files")
            else:
                print(f"⚠️  {component}: Not found")
    
    print(f"\n🎉 COMPLETE! Archive created successfully: {zip_filename}")
    print(f"📥 You can download this file: LuvHive_Complete_Project_{timestamp}.zip")
    
    return zip_filename

if __name__ == "__main__":
    try:
        zip_path = create_complete_zip()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error creating archive: {e}")
        sys.exit(1)