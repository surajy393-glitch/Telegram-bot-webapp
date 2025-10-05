# utils/abuse_prevention.py - Advanced abuse prevention and spam detection
import logging
import time
import hashlib
from typing import Dict, List, Set, Optional, Any, Union
from collections import defaultdict, deque
from datetime import datetime, timedelta
import re

log = logging.getLogger(__name__)

class AbusePreventionSystem:
    """Advanced abuse prevention for large-scale operation."""
    
    def __init__(self):
        # Spam detection tracking
        def _create_user_data():
            return {
                "messages_last_hour": deque(maxlen=100),
                "reports_received": 0,
                "last_warning": 0.0,
                "violation_count": 0,
                "auto_muted_until": 0.0,
                "referral_rewards_today": 0,
                "last_referral_reset": 0.0
            }
        self.user_activity = defaultdict(_create_user_data)
        
        # Content fingerprinting for spam detection
        self.content_hashes = deque(maxlen=1000)  # Track recent content hashes
        self.spam_patterns = self._load_spam_patterns()
        
        # Report tracking
        self.recent_reports = defaultdict(list)  # reported_user_id -> [(reporter_id, timestamp)]
        
        # Rate limiting buckets (per-user and global)
        self.user_buckets = defaultdict(lambda: {"tokens": 10, "last_refill": time.time()})
        self.global_bucket = {"tokens": 1000, "last_refill": time.time()}
        
        # Referral abuse prevention
        def _create_referral_data():
            return {
                "referrals_today": 0,
                "last_reset": time.time(),
                "suspicious_patterns": []
            }
        self.referral_tracking = defaultdict(_create_referral_data)
    
    def _load_spam_patterns(self) -> List[re.Pattern]:
        """Load common spam patterns for detection."""
        patterns = [
            # Cryptocurrency/scam patterns
            re.compile(r'\b(bitcoin|btc|crypto|invest|profit|earn)\b', re.IGNORECASE),
            re.compile(r'\b(telegram\.me|t\.me)/[\w_]+', re.IGNORECASE),
            re.compile(r'\b(whatsapp|instagram|onlyfans)\b', re.IGNORECASE),
            
            # Phone number patterns
            re.compile(r'\+?\d{10,15}'),
            
            # Excessive repetition
            re.compile(r'(.)\1{5,}'),  # 6+ repeated characters
            re.compile(r'\b(\w+)\s+\1\s+\1\b'),  # Repeated words
            
            # Common spam phrases
            re.compile(r'\b(make money|easy money|free money)\b', re.IGNORECASE),
            re.compile(r'\b(click here|visit now|limited time)\b', re.IGNORECASE),
        ]
        return patterns
    
    def check_message_spam(self, user_id: int, message: str, media_count: int = 0) -> Dict[str, Any]:
        """
        Comprehensive spam detection for messages.
        Returns: {"is_spam": bool, "confidence": float, "reasons": [str], "action": str}
        """
        reasons = []
        confidence = 0.0
        
        # Check content patterns
        for pattern in self.spam_patterns:
            if pattern.search(message):
                reasons.append(f"Matches spam pattern: {pattern.pattern[:50]}")
                confidence += 0.3
        
        # Check for excessive repetition
        if len(set(message.lower().split())) < len(message.split()) / 3:
            reasons.append("Excessive word repetition")
            confidence += 0.4
        
        # Check message frequency
        user_data = self.user_activity[user_id]
        now = time.time()
        
        # Remove old messages (older than 1 hour)
        user_data["messages_last_hour"] = deque([
            msg_time for msg_time in user_data["messages_last_hour"]
            if now - msg_time < 3600
        ], maxlen=100)
        
        user_data["messages_last_hour"].append(now)
        messages_last_hour = len(user_data["messages_last_hour"])
        
        if messages_last_hour > 30:  # More than 30 messages per hour
            reasons.append(f"High message frequency: {messages_last_hour}/hour")
            confidence += 0.5
        
        # Check content similarity (duplicate detection)
        content_hash = hashlib.md5(message.lower().encode()).hexdigest()
        if content_hash in self.content_hashes:
            reasons.append("Duplicate content detected")
            confidence += 0.6
        else:
            self.content_hashes.append(content_hash)
        
        # Check if user has many reports
        if user_data["reports_received"] > 3:
            reasons.append(f"User has {user_data['reports_received']} reports")
            confidence += 0.3
        
        # Determine action based on confidence
        if confidence >= 0.8:
            action = "block"
        elif confidence >= 0.5:
            action = "flag"
        elif confidence >= 0.3:
            action = "warn"
        else:
            action = "allow"
        
        is_spam = confidence >= 0.5
        
        if is_spam:
            log.warning(f"🚨 Spam detected from user {user_id}: {reasons}")
            self._handle_spam_violation(user_id, confidence, reasons)
        
        return {
            "is_spam": is_spam,
            "confidence": confidence,
            "reasons": reasons,
            "action": action,
            "user_message_count_hour": messages_last_hour
        }
    
    def _handle_spam_violation(self, user_id: int, confidence: float, reasons: List[str]):
        """Handle spam violation with escalating responses."""
        user_data = self.user_activity[user_id]
        user_data["violation_count"] += 1
        
        now = time.time()
        
        # Escalating response based on violation count
        if user_data["violation_count"] == 1:
            # First violation: Warning
            user_data["last_warning"] = now
            action = "warning"
            
        elif user_data["violation_count"] == 2:
            # Second violation: 10 minute mute
            user_data["auto_muted_until"] = now + (10 * 60)
            action = "mute_10min"
            
        elif user_data["violation_count"] >= 3:
            # Third+ violation: 1 hour mute
            user_data["auto_muted_until"] = now + (60 * 60)
            action = "mute_1hour"
        else:
            # Default fallback
            action = "warning"
        
        # Log violation for admin review
        self._log_violation(user_id, confidence, reasons, action)
    
    def check_user_reports(self, reported_user_id: int, reporter_id: int) -> Dict[str, Any]:
        """
        Check if user should be auto-muted based on reports.
        ChatGPT recommendation: auto-mute if X users report in 10 min.
        """
        now = time.time()
        
        # Clean old reports (older than 10 minutes)
        self.recent_reports[reported_user_id] = [
            (rep_id, timestamp) for rep_id, timestamp in self.recent_reports[reported_user_id]
            if now - timestamp < 600  # 10 minutes
        ]
        
        # Add new report
        self.recent_reports[reported_user_id].append((reporter_id, now))
        
        # Count unique reporters in last 10 minutes
        unique_reporters = len(set(rep_id for rep_id, _ in self.recent_reports[reported_user_id]))
        report_threshold = 3  # Auto-mute after 3 reports in 10 minutes
        
        if unique_reporters >= report_threshold:
            # Auto-mute user
            user_data = self.user_activity[reported_user_id]
            user_data["auto_muted_until"] = now + (30 * 60)  # 30 minute auto-mute
            user_data["reports_received"] += unique_reporters
            
            log.warning(f"🚨 Auto-muted user {reported_user_id} after {unique_reporters} reports")
            
            return {
                "auto_muted": True,
                "report_count": unique_reporters,
                "muted_until": user_data["auto_muted_until"],
                "reason": f"Auto-muted after {unique_reporters} reports in 10 minutes"
            }
        
        return {
            "auto_muted": False,
            "report_count": unique_reporters,
            "threshold": report_threshold
        }
    
    def check_referral_abuse(self, referrer_id: int, referee_id: int) -> Dict[str, Any]:
        """
        Prevent referral abuse with daily limits and pattern detection.
        ChatGPT recommendation: cap rewards per day + require profile completion.
        """
        now = time.time()
        referral_data = self.referral_tracking[referrer_id]
        
        # Reset daily counter if needed
        if now - referral_data["last_reset"] > 86400:  # 24 hours
            referral_data["referrals_today"] = 0
            referral_data["last_reset"] = now
        
        # Check daily limit
        daily_limit = 5  # Max 5 referrals per day
        if referral_data["referrals_today"] >= daily_limit:
            return {
                "allowed": False,
                "reason": f"Daily referral limit exceeded ({daily_limit})",
                "referrals_today": referral_data["referrals_today"]
            }
        
        # Check if referee has minimal profile completion
        try:
            import registration as reg
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT gender, age, country 
                    FROM users 
                    WHERE tg_user_id = %s
                """, (referee_id,))
                
                profile = cur.fetchone()
                if not profile or not all(profile):
                    return {
                        "allowed": False,
                        "reason": "Referee must complete profile before referral credit",
                        "profile_complete": False
                    }
        
        except Exception as e:
            log.warning(f"Could not check referee profile: {e}")
        
        # Pattern detection: suspicious timing/behavior
        user_data = self.user_activity[referrer_id]
        recent_activity = len([
            msg_time for msg_time in user_data["messages_last_hour"]
            if now - msg_time < 300  # Last 5 minutes
        ])
        
        if recent_activity == 0:
            # Suspicious: Getting referral with no recent activity
            referral_data["suspicious_patterns"].append({
                "type": "inactive_referrer",
                "timestamp": now
            })
        
        # Allow referral
        referral_data["referrals_today"] += 1
        
        return {
            "allowed": True,
            "referrals_today": referral_data["referrals_today"],
            "daily_limit": daily_limit,
            "suspicious_patterns": len(referral_data["suspicious_patterns"])
        }
    
    def is_user_muted(self, user_id: int) -> Dict[str, Any]:
        """Check if user is currently auto-muted."""
        user_data = self.user_activity[user_id]
        now = time.time()
        
        if user_data["auto_muted_until"] > now:
            remaining_seconds = int(user_data["auto_muted_until"] - now)
            return {
                "is_muted": True,
                "remaining_seconds": remaining_seconds,
                "reason": "Auto-muted for spam/abuse violations"
            }
        
        return {"is_muted": False}
    
    def check_rate_limit(self, user_id: int, action: str = "message") -> Dict[str, Any]:
        """
        Advanced rate limiting with per-user and global buckets.
        Implements token bucket algorithm for smooth rate limiting.
        """
        now = time.time()
        
        # Refill user bucket (1.5 tokens per second, max 10)
        user_bucket = self.user_buckets[user_id]
        time_passed = now - user_bucket["last_refill"]
        user_bucket["tokens"] = min(10, user_bucket["tokens"] + (time_passed * 1.5))
        user_bucket["last_refill"] = now
        
        # Refill global bucket (15 tokens per second, max 1000)
        time_passed = now - self.global_bucket["last_refill"]
        self.global_bucket["tokens"] = min(1000, self.global_bucket["tokens"] + (time_passed * 15))
        self.global_bucket["last_refill"] = now
        
        # Check if request can be served
        user_cost = 1  # Most actions cost 1 token
        global_cost = 1
        
        if action == "media_upload":
            user_cost = 3  # Media uploads cost more
            global_cost = 3
        elif action == "friend_request":
            user_cost = 2
            global_cost = 2
        
        # Check user bucket
        if user_bucket["tokens"] < user_cost:
            return {
                "allowed": False,
                "reason": "User rate limit exceeded",
                "retry_after_seconds": max(1, int((user_cost - user_bucket["tokens"]) / 1.5)),
                "bucket_type": "user"
            }
        
        # Check global bucket  
        if self.global_bucket["tokens"] < global_cost:
            return {
                "allowed": False,
                "reason": "Global rate limit exceeded (high server load)",
                "retry_after_seconds": max(1, int((global_cost - self.global_bucket["tokens"]) / 15)),
                "bucket_type": "global"
            }
        
        # Consume tokens
        user_bucket["tokens"] -= user_cost
        self.global_bucket["tokens"] -= global_cost
        
        return {
            "allowed": True,
            "tokens_remaining": {
                "user": user_bucket["tokens"],
                "global": self.global_bucket["tokens"]
            }
        }
    
    def _log_violation(self, user_id: int, confidence: float, reasons: List[str], action: str):
        """Log violations for admin review and pattern analysis."""
        try:
            violation_log = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "confidence": confidence,
                "reasons": reasons,
                "action": action,
                "violation_count": self.user_activity[user_id]["violation_count"]
            }
            
            # Write to violation log file
            log_file = "/tmp/luvhive_violations.log"
            with open(log_file, "a") as f:
                import json
                f.write(json.dumps(violation_log) + "\n")
                
        except Exception as e:
            log.error(f"Failed to log violation: {e}")

# Global abuse prevention instance
abuse_prevention = AbusePreventionSystem()

def clean_and_validate_link(text: str) -> str:
    """
    Clean and validate links in text content.
    ChatGPT recommendation: strip dangerous markdown/autolinks, allow only http(s).
    """
    # Remove dangerous markdown
    dangerous_chars = ['[', ']', '(', ')', '`', '*', '_', '~']
    for char in dangerous_chars:
        text = text.replace(char, f'\\{char}')
    
    # Extract and validate URLs
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    urls = url_pattern.findall(text)
    
    # Length cap for URLs
    for url in urls:
        if len(url) > 200:  # Suspicious long URL
            text = text.replace(url, '[URL removed - too long]')
        elif not url.startswith(('http://', 'https://')):
            text = text.replace(url, '[URL removed - invalid protocol]')
    
    return text