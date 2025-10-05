# utils/feature_flags.py - Feature flags for incident management (ChatGPT Final Polish)
import os
import logging
from typing import Dict, Any, Optional

log = logging.getLogger(__name__)

class FeatureFlagManager:
    """Manage feature flags for graceful degradation during incidents"""
    
    def __init__(self):
        self.flags = self._load_flags()
        
    def _load_flags(self) -> Dict[str, bool]:
        """Load feature flags from environment variables"""
        return {
            # Core features
            "ENABLE_FEED": self._get_bool_flag("ENABLE_FEED", True),
            "ENABLE_STORIES": self._get_bool_flag("ENABLE_STORIES", True),
            "ENABLE_CHAT": self._get_bool_flag("ENABLE_CHAT", True),
            "ENABLE_PREMIUM": self._get_bool_flag("ENABLE_PREMIUM", True),
            
            # Social features  
            "ENABLE_LIKES": self._get_bool_flag("ENABLE_LIKES", True),
            "ENABLE_COMMENTS": self._get_bool_flag("ENABLE_COMMENTS", True),
            "ENABLE_FRIEND_REQUESTS": self._get_bool_flag("ENABLE_FRIEND_REQUESTS", True),
            "ENABLE_RATINGS": self._get_bool_flag("ENABLE_RATINGS", True),
            
            # Administrative
            "ENABLE_REGISTRATION": self._get_bool_flag("ENABLE_REGISTRATION", True),
            "ENABLE_REPORTS": self._get_bool_flag("ENABLE_REPORTS", True),
            "ENABLE_BROADCASTS": self._get_bool_flag("ENABLE_BROADCASTS", True),
            "ENABLE_VERIFICATION": self._get_bool_flag("ENABLE_VERIFICATION", True),
            
            # Performance intensive
            "ENABLE_MEDIA_UPLOAD": self._get_bool_flag("ENABLE_MEDIA_UPLOAD", True),
            "ENABLE_SEARCH": self._get_bool_flag("ENABLE_SEARCH", True),
            "ENABLE_ANALYTICS": self._get_bool_flag("ENABLE_ANALYTICS", True),
            
            # Maintenance mode
            "MAINTENANCE_MODE": self._get_bool_flag("MAINTENANCE_MODE", False),
            "READ_ONLY_MODE": self._get_bool_flag("READ_ONLY_MODE", False),
        }
    
    def _get_bool_flag(self, flag_name: str, default: bool) -> bool:
        """Get boolean flag from environment"""
        value = os.getenv(flag_name, "1" if default else "0")
        return value.lower() in ("1", "true", "yes", "on")
    
    def is_enabled(self, feature: str) -> bool:
        """Check if feature is enabled"""
        return self.flags.get(feature, False)
    
    def require_feature(self, feature: str) -> Optional[str]:
        """
        Check feature requirement, return error message if disabled
        Returns None if enabled, error message if disabled
        """
        if self.is_enabled(feature):
            return None
            
        # Feature-specific messages
        messages = {
            "ENABLE_FEED": "📱 Feed is temporarily disabled for maintenance.",
            "ENABLE_STORIES": "📸 Stories are temporarily disabled.",
            "ENABLE_CHAT": "💬 Chat is temporarily unavailable.",
            "ENABLE_PREMIUM": "👑 Premium features are temporarily disabled.",
            "ENABLE_LIKES": "❤️ Likes are temporarily disabled.",
            "ENABLE_COMMENTS": "💬 Comments are temporarily disabled.",
            "ENABLE_FRIEND_REQUESTS": "👥 Friend requests are temporarily disabled.",
            "ENABLE_RATINGS": "⭐ Rating system is temporarily disabled.",
            "ENABLE_REGISTRATION": "📝 New registrations are temporarily paused.",
            "ENABLE_REPORTS": "🚨 Reporting is temporarily unavailable.",
            "ENABLE_MEDIA_UPLOAD": "📷 Media uploads are temporarily disabled.",
            "ENABLE_SEARCH": "🔍 Search is temporarily unavailable.",
        }
        
        return messages.get(feature, f"🚫 {feature} is temporarily disabled.")
    
    def maintenance_message(self) -> Optional[str]:
        """Get maintenance mode message if active"""
        if self.is_enabled("MAINTENANCE_MODE"):
            return "🔧 LuvHive is currently under maintenance. Please try again in a few minutes."
        return None
    
    def read_only_message(self) -> Optional[str]:
        """Get read-only mode message if active"""
        if self.is_enabled("READ_ONLY_MODE"):
            return "📖 LuvHive is in read-only mode. You can browse but cannot make changes right now."
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current feature flag status"""
        disabled_features = [
            feature for feature, enabled in self.flags.items() 
            if not enabled
        ]
        
        return {
            "maintenance_mode": self.is_enabled("MAINTENANCE_MODE"),
            "read_only_mode": self.is_enabled("READ_ONLY_MODE"), 
            "total_features": len(self.flags),
            "disabled_count": len(disabled_features),
            "disabled_features": disabled_features,
            "all_flags": self.flags
        }
    
    def reload_flags(self):
        """Reload flags from environment (for runtime updates)"""
        old_flags = self.flags.copy()
        self.flags = self._load_flags()
        
        # Log changes
        for flag, value in self.flags.items():
            if flag in old_flags and old_flags[flag] != value:
                status = "enabled" if value else "disabled"
                log.info(f"🔄 Feature flag {flag} {status}")

# Global feature flags instance
feature_flags = FeatureFlagManager()

# Convenience functions
def is_feature_enabled(feature: str) -> bool:
    """Check if feature is enabled"""
    return feature_flags.is_enabled(feature)

def check_feature_access(feature: str) -> Optional[str]:
    """Check feature access, return error message if disabled"""
    return feature_flags.require_feature(feature)

def is_maintenance_mode() -> bool:
    """Check if in maintenance mode"""
    return feature_flags.is_enabled("MAINTENANCE_MODE")

def is_read_only_mode() -> bool:
    """Check if in read-only mode"""
    return feature_flags.is_enabled("READ_ONLY_MODE")

# Decorator for feature-gated functions
def requires_feature(feature_name: str):
    """Decorator to check feature flag before executing function"""
    def decorator(func):
        async def async_wrapper(update, context, *args, **kwargs):
            error_msg = check_feature_access(feature_name)
            if error_msg:
                if update.effective_message:
                    await update.effective_message.reply_text(error_msg)
                return None
            return await func(update, context, *args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            error_msg = check_feature_access(feature_name)
            if error_msg:
                raise RuntimeError(error_msg)
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator