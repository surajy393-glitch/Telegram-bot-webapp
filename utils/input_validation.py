# utils/input_validation.py - Input validation and content safety for scaling
import re
import logging
from typing import Optional, Tuple

log = logging.getLogger(__name__)

# Content length limits (prevent abuse and database bloat)
MAX_BIO_LENGTH = 500
MAX_POST_TEXT_LENGTH = 2000  
MAX_COMMENT_LENGTH = 500
MAX_USERNAME_LENGTH = 30
MAX_MEDIA_PER_POST = 5

# Basic bad words list for content moderation
BAD_WORDS = {
    # English profanity (basic set)
    "fuck", "shit", "bitch", "asshole", "damn", "hell", "crap",
    # Add more languages as needed
    "mc", "bc", "bhosdi", "chutiya", "madarchod", "behenchod", "randi", "gandu",
    # Spam/scam indicators  
    "telegram.me", "t.me", "whatsapp", "instagram", "onlyfans", "bitcoin", "crypto"
}

# Username validation regex
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")

def validate_text_length(text: str, max_length: int, field_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate text length and return (is_valid, error_message).
    """
    if not text:
        return True, None
        
    if len(text.strip()) > max_length:
        return False, f"{field_name} is too long (max {max_length} characters)"
        
    return True, None

def validate_bio(bio: str) -> Tuple[bool, Optional[str]]:
    """Validate user bio content and length."""
    return validate_text_length(bio, MAX_BIO_LENGTH, "Bio")

def validate_post_text(text: str) -> Tuple[bool, Optional[str]]:
    """Validate post text content and length."""
    return validate_text_length(text, MAX_POST_TEXT_LENGTH, "Post")

def validate_comment(text: str) -> Tuple[bool, Optional[str]]:
    """Validate comment content and length."""
    return validate_text_length(text, MAX_COMMENT_LENGTH, "Comment")

def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """
    Validate username format and length.
    Must be 3-30 chars, alphanumeric + underscore only.
    """
    if not username:
        return False, "Username is required"
        
    username = username.strip()
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
        
    if len(username) > MAX_USERNAME_LENGTH:
        return False, f"Username must be {MAX_USERNAME_LENGTH} characters or less"
        
    if not USERNAME_REGEX.match(username):
        return False, "Username can only contain letters, numbers, and underscores"
        
    return True, None

def check_content_safety(text: str) -> Tuple[bool, Optional[str]]:
    """
    Check content for basic safety issues.
    Returns (is_safe, warning_message).
    """
    if not text:
        return True, None
        
    text_lower = text.lower()
    
    # Check for bad words
    for bad_word in BAD_WORDS:
        if bad_word in text_lower:
            log.warning(f"Content flagged for bad word: {bad_word}")
            return False, "Content contains inappropriate language"
    
    # Check for excessive capitalization (spam indicator)
    if len(text) > 10 and sum(1 for c in text if c.isupper()) / len(text) > 0.7:
        return False, "Please don't use excessive CAPITAL LETTERS"
    
    # Check for repeated characters (spam indicator)
    if re.search(r'(.)\1{4,}', text):  # 5+ repeated chars
        return False, "Please avoid excessive repeated characters"
        
    # Check for too many emojis (spam indicator)
    emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', text))
    if emoji_count > 10:
        return False, "Please use fewer emojis"
        
    return True, None

def sanitize_markdown(text: str) -> str:
    """
    Basic markdown sanitization to prevent formatting attacks.
    Escapes special characters that could break Telegram's markdown.
    """
    if not text:
        return text
        
    # Escape markdown special characters
    chars_to_escape = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
        
    return text

def validate_and_sanitize_input(text: str, input_type: str) -> Tuple[bool, Optional[str], str]:
    """
    Complete input validation and sanitization pipeline.
    
    Args:
        text: Input text to validate
        input_type: One of 'bio', 'post', 'comment', 'username'
        
    Returns:
        (is_valid, error_message, sanitized_text)
    """
    if not text:
        return True, None, text
        
    text = text.strip()
    
    # Length validation
    if input_type == 'bio':
        valid, error = validate_bio(text)
    elif input_type == 'post':
        valid, error = validate_post_text(text)
    elif input_type == 'comment':
        valid, error = validate_comment(text)
    elif input_type == 'username':
        valid, error = validate_username(text)
    else:
        valid, error = True, None
        
    if not valid:
        return False, error, text
    
    # Content safety check
    safe, safety_error = check_content_safety(text)
    if not safe:
        return False, safety_error, text
    
    # Sanitize for markdown (except username)
    if input_type != 'username':
        sanitized = sanitize_markdown(text)
    else:
        sanitized = text
        
    return True, None, sanitized

# Auto-moderation tracking
USER_VIOLATIONS = {}  # user_id -> {"count": int, "last_violation": timestamp}

def track_violation(user_id: int) -> bool:
    """
    Track content violations. Returns True if user should be auto-muted.
    Auto-mute after 3 violations in 24 hours.
    """
    import time
    
    now = time.time()
    user_data = USER_VIOLATIONS.get(user_id, {"count": 0, "last_violation": 0})
    
    # Reset count if last violation was more than 24 hours ago
    if now - user_data["last_violation"] > 86400:  # 24 hours
        user_data["count"] = 0
    
    user_data["count"] += 1
    user_data["last_violation"] = now
    USER_VIOLATIONS[user_id] = user_data
    
    # Auto-mute threshold
    if user_data["count"] >= 3:
        log.warning(f"User {user_id} auto-muted for content violations")
        return True
        
    return False