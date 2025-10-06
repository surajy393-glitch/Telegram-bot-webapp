#!/usr/bin/env python3
"""
LuvHive Backend API Testing Suite
Tests core functionality: Story Creation, Post Creation, Profile Integration, User Management
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime

# Backend URL from frontend .env
BACKEND_URL = "https://bot-web-interface.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.session = None
        self.test_user_id = 647778438  # Dev mode fallback user ID
        self.headers = {
            "X-Dev-User": str(self.test_user_id),
            "Content-Type": "application/json"
        }
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }

    async def setup(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()

    async def cleanup(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()

    def log_result(self, test_name, success, message=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
        
        if success:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {message}")

    async def test_api_root(self):
        """Test basic API connectivity"""
        try:
            async with self.session.get(f"{BACKEND_URL}") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("message") == "Social Platform API":
                        self.log_result("API Root Endpoint", True, "Backend is accessible")
                        return True
                    else:
                        self.log_result("API Root Endpoint", False, f"Unexpected response: {data}")
                        return False
                else:
                    self.log_result("API Root Endpoint", False, f"HTTP {response.status}")
                    return False
        except Exception as e:
            self.log_result("API Root Endpoint", False, f"Connection error: {str(e)}")
            return False

    async def test_user_profile(self):
        """Test user profile endpoint (/api/me)"""
        try:
            async with self.session.get(f"{BACKEND_URL}/me", headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    required_fields = ["id", "display_name", "username", "is_onboarded"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        self.log_result("User Profile API", True, f"Profile data: {data.get('display_name', 'Unknown')} (@{data.get('username', 'unknown')})")
                        return data
                    else:
                        self.log_result("User Profile API", False, f"Missing fields: {missing_fields}")
                        return None
                else:
                    self.log_result("User Profile API", False, f"HTTP {response.status}")
                    return None
        except Exception as e:
            self.log_result("User Profile API", False, f"Error: {str(e)}")
            return None

    async def test_user_onboarding(self):
        """Test user onboarding if needed"""
        try:
            # First check if user is already onboarded
            user_data = await self.test_user_profile()
            if user_data and user_data.get("is_onboarded"):
                self.log_result("User Onboarding", True, "User already onboarded")
                return True

            # Onboard user
            onboard_data = {
                "display_name": "Test User",
                "username": f"testuser{self.test_user_id}",
                "age": 25,
                "avatar_file_id": None
            }
            
            async with self.session.post(f"{BACKEND_URL}/onboard", 
                                       headers=self.headers, 
                                       json=onboard_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        self.log_result("User Onboarding", True, "User onboarded successfully")
                        return True
                    else:
                        self.log_result("User Onboarding", False, f"Onboarding failed: {data}")
                        return False
                else:
                    self.log_result("User Onboarding", False, f"HTTP {response.status}")
                    return False
        except Exception as e:
            self.log_result("User Onboarding", False, f"Error: {str(e)}")
            return False

    async def test_post_creation(self):
        """Test post creation functionality"""
        try:
            post_data = {
                "content": "Testing LuvHive post creation! 🎉 This is a test post with music and vibes.",
                "media_urls": ["https://example.com/test-image.jpg"]
            }
            
            async with self.session.post(f"{BACKEND_URL}/posts", 
                                       headers=self.headers, 
                                       json=post_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("post_id"):
                        self.log_result("Post Creation API", True, f"Post created with ID: {data['post_id']}")
                        return data["post_id"]
                    else:
                        self.log_result("Post Creation API", False, f"Creation failed: {data}")
                        return None
                else:
                    self.log_result("Post Creation API", False, f"HTTP {response.status}")
                    return None
        except Exception as e:
            self.log_result("Post Creation API", False, f"Error: {str(e)}")
            return None

    async def test_posts_feed(self):
        """Test posts feed retrieval with timestamp validation"""
        try:
            async with self.session.get(f"{BACKEND_URL}/posts", headers=self.headers) as response:
                if response.status == 200:
                    posts = await response.json()
                    if isinstance(posts, list):
                        self.log_result("Posts Feed API", True, f"Retrieved {len(posts)} posts from feed")
                        
                        # Check if posts have required structure
                        if posts:
                            post = posts[0]
                            required_fields = ["id", "content", "user_id", "created_at"]
                            missing_fields = [field for field in required_fields if field not in post]
                            if missing_fields:
                                self.log_result("Posts Feed Structure", False, f"Missing fields in posts: {missing_fields}")
                            else:
                                self.log_result("Posts Feed Structure", True, "Posts have correct structure")
                                
                                # Test timestamp format validation
                                await self.test_timestamp_format(post.get("created_at"), "Post")
                        
                        return posts
                    else:
                        self.log_result("Posts Feed API", False, f"Expected list, got: {type(posts)}")
                        return None
                else:
                    self.log_result("Posts Feed API", False, f"HTTP {response.status}")
                    return None
        except Exception as e:
            self.log_result("Posts Feed API", False, f"Error: {str(e)}")
            return None

    async def test_story_creation(self):
        """Test story creation functionality"""
        try:
            story_data = {
                "media_url": "https://example.com/test-story.jpg",
                "duration": 24
            }
            
            async with self.session.post(f"{BACKEND_URL}/stories", 
                                       headers=self.headers, 
                                       json=story_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("story_id"):
                        self.log_result("Story Creation API", True, f"Story created with ID: {data['story_id']}")
                        return data["story_id"]
                    else:
                        self.log_result("Story Creation API", False, f"Creation failed: {data}")
                        return None
                else:
                    self.log_result("Story Creation API", False, f"HTTP {response.status}")
                    return None
        except Exception as e:
            self.log_result("Story Creation API", False, f"Error: {str(e)}")
            return None

    async def test_stories_feed(self):
        """Test stories feed retrieval with timestamp validation"""
        try:
            async with self.session.get(f"{BACKEND_URL}/stories", headers=self.headers) as response:
                if response.status == 200:
                    stories = await response.json()
                    if isinstance(stories, list):
                        self.log_result("Stories Feed API", True, f"Retrieved {len(stories)} active stories")
                        
                        # Check if stories have required structure
                        if stories:
                            story = stories[0]
                            required_fields = ["id", "media_url", "user_id", "created_at"]
                            missing_fields = [field for field in required_fields if field not in story]
                            if missing_fields:
                                self.log_result("Stories Feed Structure", False, f"Missing fields in stories: {missing_fields}")
                            else:
                                self.log_result("Stories Feed Structure", True, "Stories have correct structure")
                                
                                # Test timestamp format validation
                                await self.test_timestamp_format(story.get("created_at"), "Story")
                        
                        return stories
                    else:
                        self.log_result("Stories Feed API", False, f"Expected list, got: {type(stories)}")
                        return None
                else:
                    self.log_result("Stories Feed API", False, f"HTTP {response.status}")
                    return None
        except Exception as e:
            self.log_result("Stories Feed API", False, f"Error: {str(e)}")
            return None

    async def test_post_interactions(self, post_id):
        """Test post like and comment functionality"""
        if not post_id:
            self.log_result("Post Interactions", False, "No post ID provided")
            return

        try:
            # Test liking a post
            async with self.session.post(f"{BACKEND_URL}/posts/{post_id}/like", 
                                       headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if "liked" in data:
                        self.log_result("Post Like API", True, f"Post like status: {data['liked']}")
                    else:
                        self.log_result("Post Like API", False, f"Unexpected response: {data}")
                else:
                    self.log_result("Post Like API", False, f"HTTP {response.status}")

            # Test commenting on a post
            comment_data = {
                "content": "Great post! Testing comment functionality 💬",
                "post_id": post_id
            }
            
            async with self.session.post(f"{BACKEND_URL}/posts/{post_id}/comments", 
                                       headers=self.headers, 
                                       json=comment_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("comment_id"):
                        self.log_result("Post Comment API", True, f"Comment created with ID: {data['comment_id']}")
                    else:
                        self.log_result("Post Comment API", False, f"Comment creation failed: {data}")
                else:
                    self.log_result("Post Comment API", False, f"HTTP {response.status}")

            # Test retrieving comments
            async with self.session.get(f"{BACKEND_URL}/posts/{post_id}/comments", 
                                      headers=self.headers) as response:
                if response.status == 200:
                    comments = await response.json()
                    if isinstance(comments, list):
                        self.log_result("Post Comments Retrieval", True, f"Retrieved {len(comments)} comments")
                    else:
                        self.log_result("Post Comments Retrieval", False, f"Expected list, got: {type(comments)}")
                else:
                    self.log_result("Post Comments Retrieval", False, f"HTTP {response.status}")

        except Exception as e:
            self.log_result("Post Interactions", False, f"Error: {str(e)}")

    async def test_telegram_connection(self):
        """Test Telegram bot connection and permissions"""
        try:
            async with self.session.get(f"{BACKEND_URL}/test-telegram", headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("bot_working") and data.get("can_send_messages"):
                        self.log_result("Telegram Connection", True, f"Bot: @{data.get('bot_username', 'unknown')}, Chat ID: {data.get('chat_id')}")
                        return True
                    else:
                        self.log_result("Telegram Connection", False, f"Bot issues: {data.get('message', 'Unknown error')}")
                        return False
                else:
                    self.log_result("Telegram Connection", False, f"HTTP {response.status}")
                    return False
        except Exception as e:
            self.log_result("Telegram Connection", False, f"Error: {str(e)}")
            return False

    async def test_media_upload_image(self):
        """Test image upload to Telegram via /api/upload-photo"""
        try:
            # Create a small test image (1x1 pixel PNG)
            import base64
            # 1x1 transparent PNG
            png_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yQAAAABJRU5ErkJggg==')
            
            # Create form data for file upload
            form_data = aiohttp.FormData()
            form_data.add_field('file', png_data, filename='test_image.png', content_type='image/png')
            
            # Upload headers without Content-Type (let aiohttp set it for multipart)
            upload_headers = {
                "X-Dev-User": str(self.test_user_id)
            }
            
            async with self.session.post(f"{BACKEND_URL}/upload-photo", 
                                       headers=upload_headers, 
                                       data=form_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("photo_url"):
                        self.log_result("Image Upload API", True, f"Image uploaded: {data.get('file_id', 'unknown')}")
                        return data["photo_url"]
                    else:
                        self.log_result("Image Upload API", False, f"Upload failed: {data}")
                        return None
                else:
                    response_text = await response.text()
                    self.log_result("Image Upload API", False, f"HTTP {response.status}: {response_text[:200]}")
                    return None
        except Exception as e:
            self.log_result("Image Upload API", False, f"Error: {str(e)}")
            return None

    async def test_media_upload_video(self):
        """Test video upload to Telegram via /api/upload-video"""
        try:
            # Create a minimal MP4 video (just headers, won't actually play but should be accepted)
            # This is a minimal MP4 file structure
            mp4_data = b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom\x00\x00\x00\x08free'
            
            # Create form data for file upload
            form_data = aiohttp.FormData()
            form_data.add_field('file', mp4_data, filename='test_video.mp4', content_type='video/mp4')
            
            # Upload headers without Content-Type (let aiohttp set it for multipart)
            upload_headers = {
                "X-Dev-User": str(self.test_user_id)
            }
            
            async with self.session.post(f"{BACKEND_URL}/upload-video", 
                                       headers=upload_headers, 
                                       data=form_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("video_url"):
                        self.log_result("Video Upload API", True, f"Video uploaded: {data.get('file_id', 'unknown')}")
                        return data["video_url"]
                    else:
                        self.log_result("Video Upload API", False, f"Upload failed: {data}")
                        return None
                else:
                    response_text = await response.text()
                    self.log_result("Video Upload API", False, f"HTTP {response.status}: {response_text[:200]}")
                    return None
        except Exception as e:
            self.log_result("Video Upload API", False, f"Error: {str(e)}")
            return None

    async def test_media_upload_size_limits(self):
        """Test media upload size limit validation"""
        try:
            # Test oversized image (simulate 25MB file)
            large_data = b'0' * (25 * 1024 * 1024)  # 25MB of zeros
            
            form_data = aiohttp.FormData()
            form_data.add_field('file', large_data, filename='large_image.jpg', content_type='image/jpeg')
            
            upload_headers = {
                "X-Dev-User": str(self.test_user_id)
            }
            
            async with self.session.post(f"{BACKEND_URL}/upload-photo", 
                                       headers=upload_headers, 
                                       data=form_data) as response:
                if response.status == 400:
                    response_text = await response.text()
                    if "बहुत बड़ी" in response_text or "too big" in response_text.lower():
                        self.log_result("Size Limit Validation", True, "Large file correctly rejected")
                    else:
                        self.log_result("Size Limit Validation", False, f"Unexpected error message: {response_text}")
                else:
                    self.log_result("Size Limit Validation", False, f"Expected 400, got {response.status}")
        except Exception as e:
            self.log_result("Size Limit Validation", False, f"Error: {str(e)}")

    async def test_timestamp_format(self, timestamp_str, entity_type):
        """Test if timestamp is in proper ISO format for frontend consumption"""
        try:
            if not timestamp_str:
                self.log_result(f"{entity_type} Timestamp Format", False, "Timestamp is missing")
                return False
            
            # Try to parse the timestamp
            from datetime import datetime
            try:
                # Check if it's a valid ISO format timestamp
                parsed_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
                # Check if timestamp is recent (within last year) to ensure it's not a default value
                now = datetime.utcnow()
                time_diff = abs((now - parsed_time.replace(tzinfo=None)).total_seconds())
                
                if time_diff < 365 * 24 * 3600:  # Within last year
                    self.log_result(f"{entity_type} Timestamp Format", True, f"Valid ISO timestamp: {timestamp_str}")
                    return True
                else:
                    self.log_result(f"{entity_type} Timestamp Format", False, f"Timestamp too old or invalid: {timestamp_str}")
                    return False
                    
            except ValueError as e:
                self.log_result(f"{entity_type} Timestamp Format", False, f"Invalid timestamp format: {timestamp_str} - {str(e)}")
                return False
                
        except Exception as e:
            self.log_result(f"{entity_type} Timestamp Format", False, f"Error validating timestamp: {str(e)}")
            return False

    async def test_user_profile_posts(self):
        """Test user profile endpoint and verify it includes user posts data structure"""
        try:
            # Get user profile
            async with self.session.get(f"{BACKEND_URL}/me", headers=self.headers) as response:
                if response.status == 200:
                    profile_data = await response.json()
                    
                    # Check if profile has required fields for posts display
                    required_fields = ["id", "display_name", "username"]
                    missing_fields = [field for field in required_fields if field not in profile_data]
                    
                    if missing_fields:
                        self.log_result("User Profile Posts Structure", False, f"Missing profile fields: {missing_fields}")
                        return False
                    
                    # Test if we can get posts for this user by checking posts feed
                    async with self.session.get(f"{BACKEND_URL}/posts", headers=self.headers) as posts_response:
                        if posts_response.status == 200:
                            posts = await posts_response.json()
                            user_posts = [post for post in posts if post.get("user_id") == profile_data["id"]]
                            
                            self.log_result("User Profile Posts Integration", True, 
                                          f"Profile data compatible with posts feed. Found {len(user_posts)} user posts")
                            
                            # Verify posts have user data structure needed for profile display
                            if user_posts:
                                post = user_posts[0]
                                if "user" in post and "display_name" in post["user"]:
                                    self.log_result("User Profile Posts Data Structure", True, 
                                                  "Posts include user data for profile display")
                                else:
                                    self.log_result("User Profile Posts Data Structure", False, 
                                                  "Posts missing user data structure")
                            
                            return True
                        else:
                            self.log_result("User Profile Posts Integration", False, 
                                          f"Cannot retrieve posts for profile: HTTP {posts_response.status}")
                            return False
                else:
                    self.log_result("User Profile Posts Structure", False, f"HTTP {response.status}")
                    return False
                    
        except Exception as e:
            self.log_result("User Profile Posts", False, f"Error: {str(e)}")
            return False

    async def test_profile_editing_endpoints(self):
        """Test profile update/editing functionality"""
        try:
            # First get current profile
            async with self.session.get(f"{BACKEND_URL}/me", headers=self.headers) as response:
                if response.status != 200:
                    self.log_result("Profile Editing - Get Profile", False, f"Cannot get current profile: HTTP {response.status}")
                    return False
                
                current_profile = await response.json()
                
            # Test profile update (using onboard endpoint as it's the available update mechanism)
            updated_data = {
                "display_name": "Updated Test User",
                "username": current_profile.get("username", f"testuser{self.test_user_id}"),
                "age": 26,
                "avatar_file_id": current_profile.get("avatar_file_id")
            }
            
            async with self.session.post(f"{BACKEND_URL}/onboard", 
                                       headers=self.headers, 
                                       json=updated_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        self.log_result("Profile Update API", True, "Profile update successful")
                        
                        # Verify the update by getting profile again
                        async with self.session.get(f"{BACKEND_URL}/me", headers=self.headers) as verify_response:
                            if verify_response.status == 200:
                                updated_profile = await verify_response.json()
                                if updated_profile.get("display_name") == "Updated Test User":
                                    self.log_result("Profile Update Verification", True, "Profile changes persisted correctly")
                                    return True
                                else:
                                    self.log_result("Profile Update Verification", False, 
                                                  f"Profile not updated. Expected 'Updated Test User', got '{updated_profile.get('display_name')}'")
                                    return False
                            else:
                                self.log_result("Profile Update Verification", False, f"Cannot verify update: HTTP {verify_response.status}")
                                return False
                    else:
                        self.log_result("Profile Update API", False, f"Update failed: {data}")
                        return False
                else:
                    self.log_result("Profile Update API", False, f"HTTP {response.status}")
                    return False
                    
        except Exception as e:
            self.log_result("Profile Editing", False, f"Error: {str(e)}")
            return False

    async def test_comments_timestamp_format(self, post_id):
        """Test comment timestamps for proper ISO format"""
        if not post_id:
            return
            
        try:
            async with self.session.get(f"{BACKEND_URL}/posts/{post_id}/comments", 
                                      headers=self.headers) as response:
                if response.status == 200:
                    comments = await response.json()
                    if comments and len(comments) > 0:
                        comment = comments[0]
                        if "created_at" in comment:
                            await self.test_timestamp_format(comment["created_at"], "Comment")
                        else:
                            self.log_result("Comment Timestamp Format", False, "Comment missing created_at field")
                    else:
                        self.log_result("Comment Timestamp Format", True, "No comments to test (expected)")
                else:
                    self.log_result("Comment Timestamp Format", False, f"Cannot get comments: HTTP {response.status}")
        except Exception as e:
            self.log_result("Comment Timestamp Format", False, f"Error: {str(e)}")

    async def test_status_endpoints(self):
        """Test status check endpoints"""
        try:
            # Test creating a status check
            status_data = {
                "client_name": "backend_test_suite"
            }
            
            async with self.session.post(f"{BACKEND_URL}/status", 
                                       headers=self.headers, 
                                       json=status_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("id") and data.get("client_name"):
                        self.log_result("Status Creation API", True, f"Status check created: {data['id']}")
                    else:
                        self.log_result("Status Creation API", False, f"Unexpected response: {data}")
                else:
                    self.log_result("Status Creation API", False, f"HTTP {response.status}")

            # Test retrieving status checks
            async with self.session.get(f"{BACKEND_URL}/status", headers=self.headers) as response:
                if response.status == 200:
                    statuses = await response.json()
                    if isinstance(statuses, list):
                        self.log_result("Status Retrieval API", True, f"Retrieved {len(statuses)} status checks")
                    else:
                        self.log_result("Status Retrieval API", False, f"Expected list, got: {type(statuses)}")
                else:
                    self.log_result("Status Retrieval API", False, f"HTTP {response.status}")

        except Exception as e:
            self.log_result("Status Endpoints", False, f"Error: {str(e)}")

    async def run_all_tests(self):
        """Run comprehensive backend API tests"""
        print("🚀 Starting LuvHive Backend API Tests")
        print("=" * 50)
        
        await self.setup()
        
        try:
            # Test basic connectivity
            if not await self.test_api_root():
                print("❌ Backend is not accessible. Stopping tests.")
                return
            
            # Test user management
            await self.test_user_onboarding()
            user_profile = await self.test_user_profile()
            
            # Test Telegram integration (critical for media uploads)
            telegram_working = await self.test_telegram_connection()
            
            # Test media upload functionality (core feature)
            if telegram_working:
                await self.test_media_upload_image()
                await self.test_media_upload_video()
                await self.test_media_upload_size_limits()
            else:
                self.log_result("Media Upload Tests", False, "Skipped due to Telegram connection issues")
            
            # Test core functionality
            post_id = await self.test_post_creation()
            await self.test_posts_feed()
            
            story_id = await self.test_story_creation()
            await self.test_stories_feed()
            
            # Test interactions
            if post_id:
                await self.test_post_interactions(post_id)
                # Test comment timestamps after creating comments
                await self.test_comments_timestamp_format(post_id)
            
            # Test critical fixes from review request
            print("\n🔍 Testing Critical Fixes:")
            await self.test_user_profile_posts()
            await self.test_profile_editing_endpoints()
            
            # Test utility endpoints
            await self.test_status_endpoints()
            
        finally:
            await self.cleanup()
        
        # Print summary
        print("\n" + "=" * 50)
        print("🏁 Test Summary")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100 if (self.results['passed'] + self.results['failed']) > 0 else 0
        print(f"\n📊 Success Rate: {success_rate:.1f}%")
        
        return self.results['failed'] == 0

async def main():
    """Main test runner"""
    tester = BackendTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 All backend tests passed! LuvHive API is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some backend tests failed. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())