#!/usr/bin/env python3
import zipfile
import os
from pathlib import Path
import datetime

def create_efficient_zip():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"/app/LuvHive_Complete_{timestamp}.zip"
    
    print(f"Creating LuvHive Complete Project: {zip_filename}")
    
    # Essential files and directories to include
    include_items = [
        # Bot core files
        'main.py', 'registration.py', 'premium.py', 'profile.py', 'settings.py', 'state.py',
        'admin.py', 'admin_commands.py', 'menu.py', 'chat.py',
        
        # Bot handlers and utilities
        'handlers/', 'utils/', 'scripts/',
        
        # Backend
        'backend/server.py', 'backend/requirements.txt', 'backend/.env',
        
        # Frontend webapp
        'frontend/package.json', 'frontend/yarn.lock', 'frontend/public/', 'frontend/src/',
        
        # Database and config
        'database_schema.sql', 'database_export.sql', 'production_deploy.sql',
        'requirements.txt', 'requirements-api.txt', '.env',
        
        # Documentation
        'README.md', 'README_TELEGRAM_BOT.md', 'DEPLOY_INSTRUCTIONS.md',
        'replit.md', 'pyproject.toml',
        
        # Additional webapp (if different)
        'webapp/package.json', 'webapp/public/', 'webapp/src/',
        
        # API
        'api/', 'api_server.py', 'main_api.py',
        
        # Test results and docs
        'test_result.md', 'docs/',
        
        # Setup and run scripts
        'run_forever.sh', 'start_bot.py', 'start_miniapp.py',
        'setup_supabase_env.py', 'health.py'
    ]
    
    # Files to exclude
    exclude_patterns = [
        '__pycache__', '*.pyc', '*.pyo', '*.log', '.DS_Store', 'node_modules',
        '.git', '.emergent', 'bot_state.pkl', '*.swp', '*.tmp'
    ]
    
    def should_exclude(file_path):
        str_path = str(file_path)
        for pattern in exclude_patterns:
            if pattern in str_path or str_path.endswith(pattern.replace('*', '')):
                return True
        return False
    
    base_dir = Path('/app')
    included_count = 0
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        
        for item in include_items:
            item_path = base_dir / item
            
            if item_path.exists():
                if item_path.is_file():
                    if not should_exclude(item_path):
                        rel_path = item_path.relative_to(base_dir)
                        zipf.write(item_path, rel_path)
                        included_count += 1
                        print(f"✅ {rel_path}")
                        
                elif item_path.is_dir():
                    for root, dirs, files in os.walk(item_path):
                        # Filter out excluded directories
                        dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d)]
                        
                        for file in files:
                            file_path = Path(root) / file
                            if not should_exclude(file_path):
                                rel_path = file_path.relative_to(base_dir)
                                zipf.write(file_path, rel_path)
                                included_count += 1
            else:
                print(f"⚠️  Not found: {item}")
    
    # Get file size
    zip_size = os.path.getsize(zip_filename)
    zip_size_mb = zip_size / (1024 * 1024)
    
    print(f"\n📊 SUMMARY:")
    print(f"Files included: {included_count}")
    print(f"Archive size: {zip_size_mb:.2f} MB")
    print(f"Location: {zip_filename}")
    
    return zip_filename

if __name__ == '__main__':
    create_efficient_zip()
