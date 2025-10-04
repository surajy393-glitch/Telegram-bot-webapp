"""
Advanced Bot Handlers for Instagram-Style Social Platform
Additional features: Stories, Posts, Advanced Matching, Games
"""

import os
import logging
import random
import datetime
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClient

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "instagram_platform")
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Advanced Matching System
class AdvancedMatcher:
    """Advanced matching algorithm with compatibility scoring"""
    
    @staticmethod
    async def calculate_compatibility(user1_data: Dict, user2_data: Dict) -> float:
        """Calculate compatibility score between two users"""
        score = 0.0
        
        # Age compatibility (within 5 years = higher score)
        age_diff = abs(user1_data.get('age', 25) - user2_data.get('age', 25))
        if age_diff <= 2:
            score += 0.3
        elif age_diff <= 5:
            score += 0.2
        elif age_diff <= 10:
            score += 0.1
        
        # Interest overlap
        interests1 = set(user1_data.get('interests', []))
        interests2 = set(user2_data.get('interests', []))
        
        if interests1 and interests2:
            overlap = len(interests1.intersection(interests2))
            total = len(interests1.union(interests2))
            interest_score = overlap / total if total > 0 else 0
            score += interest_score * 0.4
        
        # Activity level (recent logins)
        last_active1 = user1_data.get('last_active', datetime.datetime.min)
        last_active2 = user2_data.get('last_active', datetime.datetime.min)
        
        if isinstance(last_active1, datetime.datetime) and isinstance(last_active2, datetime.datetime):
            days_since1 = (datetime.datetime.utcnow() - last_active1).days
            days_since2 = (datetime.datetime.utcnow() - last_active2).days
            
            if days_since1 <= 1 and days_since2 <= 1:
                score += 0.2
            elif days_since1 <= 7 and days_since2 <= 7:
                score += 0.1
        
        # Premium users get slight boost
        if user1_data.get('is_premium') or user2_data.get('is_premium'):
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    @staticmethod
    async def find_compatible_matches(user_id: int, limit: int = 10) -> List[Dict]:
        """Find most compatible matches for a user"""
        user_data = await db.users.find_one({"tg_user_id": user_id})
        if not user_data:
            return []
        
        # Get potential matches
        match_filter = {
            "tg_user_id": {"$ne": user_id},
            "registration_complete": True
        }
        
        # Apply gender preferences
        if user_data.get('preferred_gender'):
            match_filter['gender'] = user_data['preferred_gender']
        
        # Apply age preferences
        if user_data.get('preferred_min_age'):
            match_filter['age'] = {"$gte": user_data['preferred_min_age']}
        if user_data.get('preferred_max_age'):
            if 'age' in match_filter:
                match_filter['age']['$lte'] = user_data['preferred_max_age']
            else:
                match_filter['age'] = {"$lte": user_data['preferred_max_age']}
        
        potential_matches = await db.users.find(match_filter).to_list(50)
        
        # Calculate compatibility scores
        matches_with_scores = []
        for match in potential_matches:
            score = await AdvancedMatcher.calculate_compatibility(user_data, match)
            matches_with_scores.append((match, score))
        
        # Sort by score and return top matches
        matches_with_scores.sort(key=lambda x: x[1], reverse=True)
        return [match[0] for match in matches_with_scores[:limit]]

# Stories System
class StoriesManager:
    """Manage user stories with advanced features"""
    
    @staticmethod
    async def create_story(user_id: int, content: str, media_type: str = "text") -> bool:
        """Create a new story"""
        try:
            story_data = {
                "user_id": user_id,
                "content": content,
                "media_type": media_type,
                "created_at": datetime.datetime.utcnow(),
                "expires_at": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
                "views": [],
                "reactions": []
            }
            
            await db.stories.insert_one(story_data)
            return True
        except Exception as e:
            logger.error(f"Error creating story: {e}")
            return False
    
    @staticmethod
    async def view_story(story_id: str, viewer_id: int) -> bool:
        """Record a story view"""
        try:
            from bson import ObjectId
            await db.stories.update_one(
                {"_id": ObjectId(story_id)},
                {"$addToSet": {"views": viewer_id}}
            )
            return True
        except Exception as e:
            logger.error(f"Error viewing story: {e}")
            return False
    
    @staticmethod
    async def get_active_stories(user_id: Optional[int] = None) -> List[Dict]:
        """Get active stories (not expired)"""
        filter_dict = {"expires_at": {"$gt": datetime.datetime.utcnow()}}
        if user_id:
            filter_dict["user_id"] = user_id
        
        stories = await db.stories.find(filter_dict).sort("created_at", -1).to_list(50)
        
        # Add user info to each story
        for story in stories:
            user = await db.users.find_one({"tg_user_id": story["user_id"]})
            story["user"] = {
                "display_name": user.get("display_name", "Unknown"),
                "username": user.get("username", "user")
            } if user else {"display_name": "Unknown", "username": "user"}
            story["id"] = str(story["_id"])
        
        return stories

# Games System
class GamesManager:
    """Interactive games and activities"""
    
    TRUTH_QUESTIONS = [
        "What's the most embarrassing thing that's happened to you?",
        "What's your biggest fear in a relationship?", 
        "What's the weirdest dream you've ever had?",
        "What's your most unpopular opinion?",
        "What's the biggest lie you've ever told?",
        "What's your guilty pleasure?",
        "What's the most adventurous thing you've done?",
        "What's your biggest regret?",
        "What's the strangest food you've eaten?",
        "What's your secret talent?"
    ]
    
    DARE_CHALLENGES = [
        "Send a voice message singing your favorite song",
        "Share a funny childhood photo",
        "Do 10 jumping jacks and share a video",
        "Write a haiku about your day",
        "Draw a picture and share it",
        "Share your best dance moves in a video",
        "Tell a joke in a voice message",
        "Share a photo of your current view",
        "Write a short story in one message",
        "Share your favorite recipe"
    ]
    
    WYR_QUESTIONS = [
        ("Have the ability to fly", "Have the ability to become invisible"),
        ("Always be 10 minutes late", "Always be 20 minutes early"),
        ("Read minds", "Predict the future"),
        ("Live without music", "Live without movies"), 
        ("Have super strength", "Have super speed"),
        ("Never use social media again", "Never watch TV again"),
        ("Always say what you think", "Never speak again"),
        ("Be famous", "Be rich"),
        ("Time travel to the past", "Time travel to the future"),
        ("Have unlimited money", "Have unlimited time")
    ]
    
    @staticmethod
    async def get_truth_or_dare(difficulty: str = "normal") -> Dict[str, str]:
        """Get a random truth or dare question"""
        truth = random.choice(GamesManager.TRUTH_QUESTIONS)
        dare = random.choice(GamesManager.DARE_CHALLENGES)
        
        return {
            "truth": truth,
            "dare": dare,
            "difficulty": difficulty
        }
    
    @staticmethod
    async def get_would_you_rather() -> Dict[str, str]:
        """Get a random Would You Rather question"""
        option_a, option_b = random.choice(GamesManager.WYR_QUESTIONS)
        
        return {
            "option_a": option_a,
            "option_b": option_b,
            "question": f"Would you rather {option_a.lower()} or {option_b.lower()}?"
        }
    
    @staticmethod
    async def record_game_response(user_id: int, game_type: str, question: str, answer: str) -> bool:
        """Record a user's game response"""
        try:
            response_data = {
                "user_id": user_id,
                "game_type": game_type,
                "question": question,
                "answer": answer,
                "created_at": datetime.datetime.utcnow()
            }
            
            await db.game_responses.insert_one(response_data)
            return True
        except Exception as e:
            logger.error(f"Error recording game response: {e}")
            return False

# Premium Features Manager
class PremiumManager:
    """Manage premium features and subscriptions"""
    
    PREMIUM_BENEFITS = {
        "unlimited_likes": "Unlimited likes per day",
        "advanced_filters": "Advanced search filters",
        "priority_matching": "Priority in matching queue",
        "premium_games": "Exclusive premium games",
        "ad_free": "Ad-free experience",
        "premium_badge": "Premium badge on profile",
        "premium_content": "Access to premium content",
        "priority_support": "Priority customer support"
    }
    
    @staticmethod
    async def check_premium_status(user_id: int) -> Dict[str, Any]:
        """Check user's premium status"""
        user = await db.users.find_one({"tg_user_id": user_id})
        if not user:
            return {"is_premium": False}
        
        is_premium = user.get('is_premium', False)
        premium_expires = user.get('premium_expires')
        
        # Check if premium has expired
        if is_premium and premium_expires:
            if isinstance(premium_expires, datetime.datetime):
                if premium_expires < datetime.datetime.utcnow():
                    # Premium expired, update user
                    await db.users.update_one(
                        {"tg_user_id": user_id},
                        {"$set": {"is_premium": False}}
                    )
                    is_premium = False
        
        return {
            "is_premium": is_premium,
            "premium_expires": premium_expires,
            "benefits": list(PremiumManager.PREMIUM_BENEFITS.keys()) if is_premium else []
        }
    
    @staticmethod
    async def grant_premium(user_id: int, duration_days: int = 30) -> bool:
        """Grant premium access to a user"""
        try:
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)
            
            await db.users.update_one(
                {"tg_user_id": user_id},
                {
                    "$set": {
                        "is_premium": True,
                        "premium_expires": expires_at,
                        "premium_granted_at": datetime.datetime.utcnow()
                    }
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error granting premium: {e}")
            return False

# Notification System
class NotificationManager:
    """Manage user notifications and alerts"""
    
    @staticmethod
    async def send_match_notification(user_id: int, match_id: int) -> bool:
        """Send notification for new match"""
        try:
            notification_data = {
                "user_id": user_id,
                "type": "match",
                "title": "🎉 New Match!",
                "message": "You have a new match! Start chatting now.",
                "data": {"match_id": match_id},
                "created_at": datetime.datetime.utcnow(),
                "read": False
            }
            
            await db.notifications.insert_one(notification_data)
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    @staticmethod
    async def get_user_notifications(user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's notifications"""
        notifications = await db.notifications.find({
            "user_id": user_id
        }).sort("created_at", -1).limit(limit).to_list(limit)
        
        return notifications
    
    @staticmethod
    async def mark_notification_read(notification_id: str) -> bool:
        """Mark notification as read"""
        try:
            from bson import ObjectId
            await db.notifications.update_one(
                {"_id": ObjectId(notification_id)},
                {"$set": {"read": True}}
            )
            return True
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False

# Analytics and Stats
class AnalyticsManager:
    """Track user analytics and platform statistics"""
    
    @staticmethod
    async def track_user_action(user_id: int, action: str, data: Dict = None) -> bool:
        """Track user action for analytics"""
        try:
            action_data = {
                "user_id": user_id,
                "action": action,
                "data": data or {},
                "timestamp": datetime.datetime.utcnow()
            }
            
            await db.user_actions.insert_one(action_data)
            return True
        except Exception as e:
            logger.error(f"Error tracking user action: {e}")
            return False
    
    @staticmethod
    async def get_platform_stats() -> Dict[str, Any]:
        """Get overall platform statistics"""
        try:
            total_users = await db.users.count_documents({"registration_complete": True})
            total_posts = await db.posts.count_documents({})
            total_stories = await db.stories.count_documents({})
            total_matches = await db.matches.count_documents({"status": "active"})
            
            # Active users (last 7 days)
            week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
            active_users = await db.users.count_documents({
                "last_active": {"$gte": week_ago}
            })
            
            # Active stories (last 24 hours)
            day_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
            active_stories = await db.stories.count_documents({
                "created_at": {"$gte": day_ago}
            })
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "total_posts": total_posts,
                "total_stories": total_stories,
                "active_stories": active_stories,
                "total_matches": total_matches,
                "platform_health": "excellent" if active_users > total_users * 0.3 else "good"
            }
        except Exception as e:
            logger.error(f"Error getting platform stats: {e}")
            return {}

# Admin Tools
class AdminManager:
    """Administrative tools and functions"""
    
    ADMIN_USER_IDS = [1437934486, 647778438]  # Add your admin user IDs here
    
    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in AdminManager.ADMIN_USER_IDS
    
    @staticmethod
    async def get_user_report(user_id: int) -> Dict[str, Any]:
        """Get detailed user report for admin"""
        if not AdminManager.is_admin(user_id):
            return {"error": "Unauthorized"}
        
        try:
            stats = await AnalyticsManager.get_platform_stats()
            
            # Recent user registrations
            recent_users = await db.users.find({
                "created_at": {"$gte": datetime.datetime.utcnow() - datetime.timedelta(days=7)}
            }).sort("created_at", -1).limit(10).to_list(10)
            
            # Recent activity
            recent_actions = await db.user_actions.find({}).sort("timestamp", -1).limit(20).to_list(20)
            
            return {
                "platform_stats": stats,
                "recent_users": len(recent_users),
                "recent_activity": len(recent_actions),
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"Error generating user report: {e}")
            return {"error": str(e)}

# Export all managers for use in main bot
__all__ = [
    'AdvancedMatcher',
    'StoriesManager', 
    'GamesManager',
    'PremiumManager',
    'NotificationManager',
    'AnalyticsManager',
    'AdminManager'
]