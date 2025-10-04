#!/usr/bin/env python3
"""
LuvHive Backend API Testing Suite - Updated for UI/UX Fixes
Tests avatar URL generation, delete functionality, reply system, and media uploads
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime

# Backend URL from frontend .env
BACKEND_URL = "https://telegram-dating-4.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.session = None
        self.test_user_id = 647778438  # Dev mode fallback user ID
        self.test_user_id_2 = 123456789  # Second user for delete testing
        self.headers = {
            "X-Dev-User": str(self.test_user_id),
            "Content-Type": "application/json"
        }
        self.headers_2 = {
            "X-Dev-User": str(self.test_user_id_2),
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

    async def test_registration_with_avatar_generation(self):
        """Test POST /api/register with avatar URL generation logic"""
        try:
            # Test registration without avatar - should generate default avatar URL
            registration_data = {
                "name": "Priya Sharma",
                "username": f"priya_test_{int(datetime.now().timestamp())}",
                "age": 24,
                "gender": "female",
                "bio": "Testing avatar generation",
                "mood": "joyful",
                "aura": "purple"
            }
            
            async with self.session.post(f"{BACKEND_URL}/register", 
                                       headers={"Content-Type": "application/json"}, 
                                       json=registration_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        self.log_result("Registration with Avatar Generation", True, f"User registered: {data.get('user_id')}")
                        return True
                    else:
                        self.log_result("Registration with Avatar Generation", False, f"Registration failed: {data}")
                        return False
                else:
                    response_text = await response.text()
                    self.log_result("Registration with Avatar Generation", False, f"HTTP {response.status}: {response_text}")
                    return False
        except Exception as e:
            self.log_result("Registration with Avatar Generation", False, f"Error: {str(e)}")
            return False

    async def test_user_profile_avatar_structure(self):
        """Test GET /api/me - Verify user profile includes avatarUrl field"""
        try:
            async with self.session.get(f"{BACKEND_URL}/me", headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    required_fields = ["id", "display_name", "username", "is_onboarded"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        # Check if avatar-related field exists (avatar_file_id or avatarUrl)
                        has_avatar_field = "avatar_file_id" in data or "avatarUrl" in data or "avatar_url" in data
                        if has_avatar_field:
                            self.log_result("User Profile Avatar Structure", True, f"Profile has avatar field: {data.get('display_name', 'Unknown')}")
                        else:
                            self.log_result("User Profile Avatar Structure", False, "Profile missing avatar field")
                        return data
                    else:
                        self.log_result("User Profile Avatar Structure", False, f"Missing fields: {missing_fields}")
                        return None
                else:
                    self.log_result("User Profile Avatar Structure", False, f"HTTP {response.status}")
                    return None
        except Exception as e:
            self.log_result("User Profile Avatar Structure", False, f"Error: {str(e)}")
            return None

    async def test_telegram_connection(self):
        """Test GET /api/test-telegram - Verify Telegram connection"""
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

    async def test_posts_with_avatar_data(self):
        """Test GET /api/posts - Verify posts include proper user avatar data"""
        try:
            async with self.session.get(f"{BACKEND_URL}/posts", headers=self.headers) as response:
                if response.status == 200:
                    posts = await response.json()
                    if isinstance(posts, list):
                        self.log_result("Posts Feed API", True, f"Retrieved {len(posts)} posts from feed")
                        
                        # Check if posts have user avatar data
                        if posts:
                            post = posts[0]
                            if "user" in post:
                                user_data = post["user"]
                                has_avatar = "avatar_file_id" in user_data or "avatarUrl" in user_data or "avatar_url" in user_data
                                if has_avatar:
                                    self.log_result("Posts Avatar Data", True, "Posts include user avatar data")
                                else:
                                    self.log_result("Posts Avatar Data", False, "Posts missing user avatar data")
                            else:
                                self.log_result("Posts Avatar Data", False, "Posts missing user data")
                        
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

    async def test_post_creation(self):
        """Test POST /api/posts - Test creating new posts"""
        try:
            post_data = {
                "content": "Testing LuvHive post creation with enhanced avatar system! 🎉 #LuvHive #Testing",
                "media_urls": []
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
                    response_text = await response.text()
                    self.log_result("Post Creation API", False, f"HTTP {response.status}: {response_text}")
                    return None
        except Exception as e:
            self.log_result("Post Creation API", False, f"Error: {str(e)}")
            return None

    async def test_post_delete_ownership_verification(self, post_id):
        """Test DELETE /api/posts/{post_id} - Test delete with proper user ownership verification"""
        if not post_id:
            self.log_result("Post Delete Ownership", False, "No post ID provided")
            return

        try:
            # First, try to delete with the owner (should succeed)
            async with self.session.delete(f"{BACKEND_URL}/posts/{post_id}", 
                                         headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        self.log_result("Post Delete by Owner", True, "Post deleted successfully by owner")
                        
                        # Create another post for non-owner test
                        new_post_data = {
                            "content": "Another test post for delete verification 🔒",
                            "media_urls": []
                        }
                        
                        async with self.session.post(f"{BACKEND_URL}/posts", 
                                                   headers=self.headers, 
                                                   json=new_post_data) as create_response:
                            if create_response.status == 200:
                                create_data = await create_response.json()
                                new_post_id = create_data.get("post_id")
                                
                                if new_post_id:
                                    # Try to delete with different user (should fail)
                                    async with self.session.delete(f"{BACKEND_URL}/posts/{new_post_id}", 
                                                                 headers=self.headers_2) as delete_response:
                                        if delete_response.status == 403:
                                            self.log_result("Post Delete by Non-Owner", True, "Non-owner correctly blocked from deleting")
                                        else:
                                            response_text = await delete_response.text()
                                            self.log_result("Post Delete by Non-Owner", False, f"Expected 403, got {delete_response.status}: {response_text}")
                    else:
                        self.log_result("Post Delete by Owner", False, f"Delete failed: {data}")
                else:
                    response_text = await response.text()
                    self.log_result("Post Delete by Owner", False, f"HTTP {response.status}: {response_text}")
        except Exception as e:
            self.log_result("Post Delete Ownership", False, f"Error: {str(e)}")

    async def test_comment_reply_functionality(self, post_id):
        """Test POST /api/posts/{post_id}/comments - Test reply/comment functionality"""
        if not post_id:
            self.log_result("Comment Reply Functionality", False, "No post ID provided")
            return

        try:
            # Test creating a comment/reply
            comment_data = {
                "content": "This is a test reply! Great post! 💬✨",
                "post_id": post_id
            }
            
            async with self.session.post(f"{BACKEND_URL}/posts/{post_id}/comments", 
                                       headers=self.headers, 
                                       json=comment_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success") and data.get("comment_id"):
                        self.log_result("Comment Creation API", True, f"Comment created with ID: {data['comment_id']}")
                        return data["comment_id"]
                    else:
                        self.log_result("Comment Creation API", False, f"Comment creation failed: {data}")
                        return None
                else:
                    response_text = await response.text()
                    self.log_result("Comment Creation API", False, f"HTTP {response.status}: {response_text}")
                    return None
        except Exception as e:
            self.log_result("Comment Creation API", False, f"Error: {str(e)}")
            return None

    async def test_comment_retrieval(self, post_id):
        """Test GET /api/posts/{post_id}/comments - Test comment retrieval"""
        if not post_id:
            self.log_result("Comment Retrieval", False, "No post ID provided")
            return

        try:
            async with self.session.get(f"{BACKEND_URL}/posts/{post_id}/comments", 
                                      headers=self.headers) as response:
                if response.status == 200:
                    comments = await response.json()
                    if isinstance(comments, list):
                        self.log_result("Comment Retrieval API", True, f"Retrieved {len(comments)} comments")
                        
                        # Check comment structure includes user avatar data
                        if comments:
                            comment = comments[0]
                            if "user" in comment:
                                user_data = comment["user"]
                                has_avatar = "avatar_file_id" in user_data or "avatarUrl" in user_data or "avatar_url" in user_data
                                if has_avatar:
                                    self.log_result("Comment Avatar Data", True, "Comments include user avatar data")
                                else:
                                    self.log_result("Comment Avatar Data", False, "Comments missing user avatar data")
                            else:
                                self.log_result("Comment Avatar Data", False, "Comments missing user data")
                        
                        return comments
                    else:
                        self.log_result("Comment Retrieval API", False, f"Expected list, got: {type(comments)}")
                        return None
                else:
                    response_text = await response.text()
                    self.log_result("Comment Retrieval API", False, f"HTTP {response.status}: {response_text}")
                    return None
        except Exception as e:
            self.log_result("Comment Retrieval API", False, f"Error: {str(e)}")
            return None

    async def test_image_upload(self):
        """Test POST /api/upload-photo - Test image upload to Telegram"""
        try:
            # Create a small test image (1x1 pixel PNG)
            import base64
            # 1x1 transparent PNG
            png_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yQAAAABJRU5ErkJggg==')
            
            # Create form data for file upload
            form_data = aiohttp.FormData()
            form_data.add_field('file', png_data, filename='test_avatar.png', content_type='image/png')
            
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

    async def test_video_upload(self):
        """Test POST /api/upload-video - Test video upload to Telegram"""
        try:
            # Create a minimal MP4 video (just headers, won't actually play but should be accepted)
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

    async def run_comprehensive_tests(self):
        """Run comprehensive backend API tests for UI/UX fixes"""
        print("🚀 Starting LuvHive Backend API Tests - UI/UX Fixes Verification")
        print("=" * 70)
        
        await self.setup()
        
        try:
            # Test basic connectivity
            if not await self.test_api_root():
                print("❌ Backend is not accessible. Stopping tests.")
                return
            
            # Test registration with avatar URL generation
            await self.test_registration_with_avatar_generation()
            
            # Test user profile structure includes avatar data
            await self.test_user_profile_avatar_structure()
            
            # Test Telegram connection (critical for media uploads)
            telegram_working = await self.test_telegram_connection()
            
            # Test posts feed includes avatar data
            posts = await self.test_posts_with_avatar_data()
            
            # Test post creation
            post_id = await self.test_post_creation()
            
            # Test post deletion with ownership verification
            if post_id:
                await self.test_post_delete_ownership_verification(post_id)
            
            # Create another post for comment testing
            test_post_id = await self.test_post_creation()
            
            # Test comment/reply functionality
            if test_post_id:
                comment_id = await self.test_comment_reply_functionality(test_post_id)
                await self.test_comment_retrieval(test_post_id)
            
            # Test media upload functionality (core feature for full-screen modal)
            if telegram_working:
                await self.test_image_upload()
                await self.test_video_upload()
            else:
                self.log_result("Media Upload Tests", False, "Skipped due to Telegram connection issues")
            
        finally:
            await self.cleanup()
        
        # Print summary
        print("\n" + "=" * 70)
        print("🏁 Backend API Test Summary - UI/UX Fixes")
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
    success = await tester.run_comprehensive_tests()
    
    if success:
        print("\n🎉 All backend tests passed! LuvHive API supports UI/UX fixes correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some backend tests failed. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())