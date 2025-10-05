
#!/usr/bin/env python3
"""
Enhanced script to create a comprehensive zip file of the entire project
Focuses on ensuring ALL webapp and public_feed_files are included
"""
import zipfile
import os
from pathlib import Path

def create_comprehensive_zip():
    """Create a zip file with all important project files"""
    
    # Get current directory
    project_root = Path('.')
    zip_filename = 'luvhive_complete_project.zip'
    
    print(f"📦 Creating comprehensive zip file: {zip_filename}")
    print(f"📁 Source directory: {project_root.absolute()}")
    
    # CRITICAL: Define all webapp and public_feed_files paths that MUST be included
    critical_webapp_paths = [
        'webapp/src/api/client.js',
        'webapp/src/components/CommentsModal.jsx',
        'webapp/src/components/Navigation.jsx', 
        'webapp/src/components/PostCard.jsx',
        'webapp/src/hooks/useTelegram.jsx',
        'webapp/src/pages/CommentsPage.jsx',
        'webapp/src/pages/CreatePost.jsx',
        'webapp/src/pages/EditProfile.jsx',
        'webapp/src/pages/Feed.jsx',
        'webapp/src/pages/Notifications.jsx',
        'webapp/src/pages/Onboard.jsx',
        'webapp/src/pages/PostDetail.jsx',
        'webapp/src/pages/Profile.jsx',
        'webapp/src/pages/Profiles.jsx',
        'webapp/src/App.jsx',
        'webapp/src/index.css',
        'webapp/src/main.jsx',
        'webapp/README.md',
        'webapp/index.html',
        'webapp/package.json',
        'webapp/package-lock.json',
        'webapp/postcss.config.js',
        'webapp/tailwind.config.js',
        'webapp/vite.config.js'
    ]
    
    critical_public_feed_paths = [
        'public_feed_files/backend/api/simple_server.py',
        'public_feed_files/backend/handlers/posts_handlers.py',
        'public_feed_files/backend/miniapp_handlers.py',
        'public_feed_files/frontend/api/client.js',
        'public_feed_files/frontend/components/PostCard.jsx',
        'public_feed_files/frontend/pages/Feed.jsx',
        'public_feed_files/styles/index.css',
        'public_feed_files/README.md'
    ]
    
    # Files/directories to exclude
    exclude_patterns = {
        '__pycache__',
        '.git',
        'venv',
        'env',
        '.venv',
        'node_modules',
        '.pytest_cache',
        'site-packages',
        'dist',
        'build',
        '*.egg-info',
        '.mypy_cache',
        '.coverage',
        'htmlcov',
        '.tox',
        '.DS_Store',
        'Thumbs.db',
        '.pythonlibs',
        'attached_assets',
        '.vite/deps',
        'zi5nFc5X',
        'ziaJBCAI', 
        'zig5q0lQ',
        'ziGGqrk5',
        'ziYFI5yV',
        'zi2lbuWg',
        'zi5KP9DG',
        'zi6lHcAI',
        'ziXiEi0y',
        'zidabPB3',
        'zigFiFwV',
        'ziwJAD8D',
        '.config',
        '.upm',
        'poetry.lock',
        '.vscode',
        '.idea',
        'bot_state.pkl',
        'database_complete_export.zip',
        'database_exports'
    }
    
    # File extensions to exclude
    exclude_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dylib', '.dll'}
    
    print("\n🔍 VERIFYING CRITICAL FILES EXIST:")
    
    # Verify webapp files
    print("\n📱 WEBAPP FILES:")
    webapp_missing = []
    for path in critical_webapp_paths:
        full_path = project_root / path
        if full_path.exists():
            print(f"  ✅ {path}")
        else:
            print(f"  ❌ MISSING: {path}")
            webapp_missing.append(path)
    
    # Verify public_feed_files
    print("\n📡 PUBLIC_FEED_FILES:")
    public_feed_missing = []
    for path in critical_public_feed_paths:
        full_path = project_root / path
        if full_path.exists():
            print(f"  ✅ {path}")
        else:
            print(f"  ❌ MISSING: {path}")
            public_feed_missing.append(path)
    
    # Check requirements.txt
    requirements_path = project_root / 'requirements.txt'
    if requirements_path.exists():
        print(f"  ✅ requirements.txt")
    else:
        print(f"  ❌ MISSING: requirements.txt")
    
    # Alert if any critical files are missing
    if webapp_missing or public_feed_missing:
        print(f"\n⚠️ WARNING: {len(webapp_missing + public_feed_missing)} critical files are missing!")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return
    
    # Create the zip file
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        file_count = 0
        webapp_files_added = 0
        public_feed_files_added = 0
        
        for root, dirs, files in os.walk(project_root):
            # Remove excluded directories from dirs list
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(project_root)
                
                # Skip if file matches exclude patterns
                should_skip = False
                for pattern in exclude_patterns:
                    if pattern in str(relative_path):
                        should_skip = True
                        break
                
                if should_skip:
                    continue
                
                # Skip if file extension should be excluded
                if file_path.suffix.lower() in exclude_extensions:
                    continue
                
                # Skip large log files
                if file_path.name.endswith('.log') and file_path.stat().st_size > 1024*100:
                    continue
                
                # Track webapp and public_feed_files
                is_webapp = 'webapp' in str(relative_path)
                is_public_feed = 'public_feed_files' in str(relative_path)
                
                # Add file to zip
                try:
                    zipf.write(file_path, relative_path)
                    file_count += 1
                    
                    if is_webapp:
                        webapp_files_added += 1
                        print(f"  📱 Added webapp: {relative_path}")
                    elif is_public_feed:
                        public_feed_files_added += 1
                        print(f"  📡 Added public_feed: {relative_path}")
                    elif str(relative_path) == 'requirements.txt':
                        print(f"  📋 Added: {relative_path}")
                    elif file_count % 20 == 0:
                        print(f"  ✅ Added {file_count} files...")
                        
                except Exception as e:
                    print(f"  ❌ Failed to add {relative_path}: {e}")
    
    # Get zip file size
    zip_size = os.path.getsize(zip_filename)
    zip_size_kb = zip_size / 1024
    
    print(f"\n🎉 Zip file created successfully!")
    print(f"📊 Total files included: {file_count}")
    print(f"📱 Webapp files included: {webapp_files_added}")
    print(f"📡 Public feed files included: {public_feed_files_added}")
    print(f"📏 Zip size: {zip_size_kb:.2f} KB ({zip_size / 1024 / 1024:.2f} MB)")
    print(f"📍 Location: {os.path.abspath(zip_filename)}")
    
    # FINAL VERIFICATION - Double check zip contents
    print("\n🔍 FINAL VERIFICATION - Contents in zip:")
    with zipfile.ZipFile(zip_filename, 'r') as zipf:
        zip_contents = zipf.namelist()
        
        # Verify requirements.txt
        if 'requirements.txt' in zip_contents:
            print("  ✅ requirements.txt - Included")
        else:
            print("  ❌ requirements.txt - MISSING!")
        
        # Double check ALL critical webapp files
        print("\n  📱 WEBAPP VERIFICATION:")
        for critical_path in critical_webapp_paths:
            if critical_path in zip_contents:
                print(f"    ✅ {critical_path}")
            else:
                print(f"    ❌ MISSING: {critical_path}")
        
        # Double check ALL critical public_feed_files
        print("\n  📡 PUBLIC_FEED_FILES VERIFICATION:")
        for critical_path in critical_public_feed_paths:
            if critical_path in zip_contents:
                print(f"    ✅ {critical_path}")
            else:
                print(f"    ❌ MISSING: {critical_path}")
        
        # Count totals in zip
        webapp_in_zip = [f for f in zip_contents if 'webapp/' in f]
        public_feed_in_zip = [f for f in zip_contents if 'public_feed_files/' in f]
        
        print(f"\n📱 TOTAL WEBAPP FILES IN ZIP: {len(webapp_in_zip)}")
        print(f"📡 TOTAL PUBLIC_FEED_FILES IN ZIP: {len(public_feed_in_zip)}")
    
    # Size validation
    if 500 <= zip_size_kb <= 1500:
        print(f"\n✅ Size target met: {zip_size_kb:.2f} KB is within 500-1500 KB range")
    else:
        print(f"\n⚠️ Size warning: {zip_size_kb:.2f} KB is outside 500-1500 KB range")
        if zip_size_kb > 1500:
            print("   Consider excluding more files to reduce size")
        else:
            print("   Size is smaller than expected - verify all files are included")
    
    return zip_filename

if __name__ == "__main__":
    create_comprehensive_zip()
