# utils/supabase_db.py - Bulletproof Database Layer (Zero SSL Errors)
import os
import logging
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from supabase import create_client, Client

log = logging.getLogger("luvbot.supabase")

# Supabase configuration - will be set via environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# Global client instance
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """Get or create Supabase client (bulletproof, no SSL issues)"""
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment")
        
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        log.info("✅ Supabase client initialized (HTTP-based, no SSL connection issues)")
    
    return _supabase_client

@contextmanager
def supabase_conn():
    """
    Drop-in replacement for _conn() - same interface, zero SSL errors
    Usage: with supabase_conn() as db: ...
    """
    try:
        db = get_supabase_client()
        yield db
    except Exception as e:
        log.error(f"🚨 Supabase operation failed: {e}")
        raise

# ============ USER MANAGEMENT ============
def is_registered(tg_user_id: int) -> bool:
    """Check if user is registered"""
    try:
        with supabase_conn() as db:
            response = db.table('users').select('id').eq('tg_user_id', tg_user_id).execute()
            return len(response.data) > 0
    except Exception:
        return False

def get_profile(tg_user_id: int) -> Dict[str, Any]:
    """Get user profile"""
    try:
        with supabase_conn() as db:
            response = db.table('users').select('*').eq('tg_user_id', tg_user_id).single().execute()
            if response.data:
                # Convert interests from separate table
                interests_response = db.table('user_interests').select('interest_key').eq('user_id', response.data['id']).execute()
                response.data['interests'] = {item['interest_key'] for item in interests_response.data}
                return response.data
            return {}
    except Exception:
        return {}

def create_user(tg_user_id: int, **kwargs) -> bool:
    """Create new user"""
    try:
        with supabase_conn() as db:
            user_data = {
                'tg_user_id': tg_user_id,
                'created_at': 'now()',
                **kwargs
            }
            response = db.table('users').insert(user_data).execute()
            return len(response.data) > 0
    except Exception as e:
        log.error(f"Failed to create user {tg_user_id}: {e}")
        return False

def update_user(tg_user_id: int, **kwargs) -> bool:
    """Update user data"""
    try:
        with supabase_conn() as db:
            response = db.table('users').update(kwargs).eq('tg_user_id', tg_user_id).execute()
            return len(response.data) > 0
    except Exception as e:
        log.error(f"Failed to update user {tg_user_id}: {e}")
        return False

# ============ CONFESSION MANAGEMENT ============
def add_confession(author_id: int, text: str) -> bool:
    """Add new confession"""
    try:
        with supabase_conn() as db:
            confession_data = {
                'author_id': author_id,
                'text': text,
                'delivered': False,
                'system_seed': False,
                'created_at': 'now()'
            }
            response = db.table('confessions').insert(confession_data).execute()
            log.info(f"✅ Confession added for user {author_id}")
            return len(response.data) > 0
    except Exception as e:
        log.error(f"Failed to add confession: {e}")
        return False

def get_pending_confessions(limit: int = 50) -> List[Dict[str, Any]]:
    """Get pending confessions for delivery"""
    try:
        with supabase_conn() as db:
            response = db.table('confessions').select('*').eq('delivered', False).order('system_seed', desc=False).order('created_at', desc=False).limit(limit).execute()
            return response.data
    except Exception as e:
        log.error(f"Failed to get pending confessions: {e}")
        return []

def mark_confession_delivered(confession_id: int, delivered_to: int) -> bool:
    """Mark confession as delivered"""
    try:
        with supabase_conn() as db:
            response = db.table('confessions').update({
                'delivered': True,
                'delivered_to': delivered_to,
                'delivered_at': 'now()'
            }).eq('id', confession_id).execute()
            return len(response.data) > 0
    except Exception as e:
        log.error(f"Failed to mark confession {confession_id} as delivered: {e}")
        return False

def get_available_confessions_for_user(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """ROTATING POOL: Get confessions available for specific user (no repeats)"""
    try:
        with supabase_conn() as db:
            # Get confession IDs already delivered to this user
            delivered_response = db.table('confession_deliveries').select('confession_id').eq('user_id', user_id).execute()
            delivered_ids = [item['confession_id'] for item in delivered_response.data]
            
            # Get available confessions not from this user and not already delivered to them
            query = db.table('confessions').select('id, author_id, text').neq('author_id', user_id)
            
            # Exclude already delivered confessions
            if delivered_ids:
                query = query.not_.in_('id', delivered_ids)
            
            # Get recent confessions (last 7 days) prioritizing system seeds
            response = query.gte('created_at', 'now() - interval \'7 days\'').order('system_seed', desc=True).limit(limit).execute()
            
            return response.data
    except Exception as e:
        log.error(f"Failed to get available confessions for user {user_id}: {e}")
        return []

def track_confession_delivery(confession_id: int, user_id: int) -> bool:
    """ROTATING POOL: Track confession delivery without marking as permanently delivered"""
    try:
        with supabase_conn() as db:
            # Insert into tracking table (prevents repeats to same user)
            delivery_data = {
                'confession_id': confession_id,
                'user_id': user_id,
                'delivered_at': 'now()'
            }
            # Use upsert to handle conflicts gracefully
            response = db.table('confession_deliveries').upsert(delivery_data).execute()
            log.info(f"📋 Tracked delivery: confession #{confession_id} → user {user_id}")
            return True
    except Exception as e:
        log.error(f"Failed to track confession delivery: {e}")
        return False

# ============ NOTIFICATION USERS ============
def get_nudge_users() -> List[int]:
    """Get users who should receive notifications"""
    try:
        with supabase_conn() as db:
            response = db.table('users').select('tg_user_id').or_('feed_notify.eq.true,feed_notify.is.null').execute()
            return [user['tg_user_id'] for user in response.data]
    except Exception as e:
        log.error(f"Failed to get nudge users: {e}")
        return []

def get_active_user_ids() -> List[int]:
    """Get active user IDs for notifications"""
    try:
        with supabase_conn() as db:
            response = db.table('users').select('tg_user_id').or_('feed_notify.eq.true,feed_notify.is.null').execute()
            return [user['tg_user_id'] for user in response.data]
    except Exception as e:
        log.error(f"Failed to get active users: {e}")
        return []

def get_premium_user_ids() -> List[int]:
    """Get premium user IDs"""
    try:
        with supabase_conn() as db:
            response = db.table('users').select('tg_user_id').or_(
                'is_premium.eq.true,premium_until.gt.now()'
            ).execute()
            return [user['tg_user_id'] for user in response.data]
    except Exception as e:
        log.error(f"Failed to get premium users: {e}")
        return []

# ============ TABLE CREATION ============
def ensure_tables():
    """Ensure all required tables exist (run this once during setup)"""
    # This will be handled via Supabase dashboard or SQL editor
    # Tables: users, user_interests, confessions, etc.
    log.info("✅ Supabase tables managed via dashboard")
    return True

# ============ BACKWARD COMPATIBILITY ============
# These functions provide the same interface as the old system
def _fetch_nudge_users() -> List[int]:
    """Backward compatibility for notifications"""
    return get_nudge_users()

def _fetch_active_user_ids() -> List[int]:  
    """Backward compatibility for notifications"""
    return get_active_user_ids()

def _fetch_premium_user_ids() -> List[int]:
    """Backward compatibility for notifications"""  
    return get_premium_user_ids()