# utils/content_moderation.py - Refined content moderation for dating/anonymous chat platform
import re
import unicodedata
import logging
from typing import Dict, Set, Optional, List, Any
from datetime import datetime

log = logging.getLogger(__name__)

class ContentModerationSystem:
    """
    Dating platform appropriate content moderation.
    ChatGPT's recommendations: Allow sexual language, block slurs/harassment.
    """
    
    def __init__(self):
        # Actual slurs/harassment that should be blocked
        self.SLURS = {
            # Hindi/Hinglish slurs
            "mc", "bc", "madarchod", "behenchod", "chutiya", "gandu", "randi", 
            "bhosdi", "harami", "kutta", "suar", "chudai", "madarchod", "bhenchod",
            "chutiye", "ganduu", "randii", "bhosdike", "haraamii",
            
            # English slurs/severe harassment (be selective - this is dating app)
            "retard", "nigger", "faggot", "kys", "kill yourself",
            
            # Targeted harassment patterns
            "you are a slut", "you are a whore", "you are a bitch",
            "fuck off", "fuck you", "go die"
        }
        
        # Sexual language that is ALLOWED (normal for dating apps)
        self.SEXUAL_ALLOWED = {
            "fuck", "sex", "sext", "horny", "nude", "naked", "boobs", "ass", 
            "dick", "pussy", "cum", "cock", "tits", "vagina", "penis",
            "sexy", "hot", "kiss", "touch", "feel", "want you", "make love",
            "orgasm", "pleasure", "desire", "attraction", "intimate"
        }
        
        # Soft warning content (allowed but may suggest moderation)
        self.SOFT_WARN = {
            "xxx", "porn", "bdsm", "kinky", "onlyfans", "camgirl", "escort",
            "prostitute", "hooker", "money for sex", "pay for sex"
        }
        
        # Known false positives to always allow
        self.ALLOWLIST_EXACT = {
            "scunthorpe", "penistone", "middlesex", "sussex", "dickens",
            "hancock", "cockburn", "titchfield"
        }
        
        # Fuzzy patterns for evaded slurs (only worst ones)
        self.FUZZY_SLURS = [
            r"m+a+d+a*r+ch+o+d+",      # madarchod variants
            r"b+e*h+e+n+ch+o+d+",      # behenchod variants  
            r"ch+u+t+i+y+a*",          # chutiya variants
            r"g+a+n+d+u+",             # gandu variants
        ]

    def normalize_text(self, text: str) -> str:
        """Normalize text for consistent matching."""
        if not text:
            return ""
        
        # Lower case and strip accents to catch variants (e.g., mādarchōd)
        text = unicodedata.normalize("NFKC", text).lower()
        
        # Remove control characters and zero-width characters
        normalized = "".join(
            c for c in text
            if unicodedata.category(c)[0] != "C"
        )
        
        # Replace common evasion characters
        replacements = {
            "@": "a", "3": "e", "1": "i", "0": "o", "5": "s", 
            "4": "a", "7": "t", "$": "s", "!": "i", "+": "t"
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
            
        return normalized

    def contains_any_words(self, text: str, word_set: Set[str]) -> Optional[str]:
        """Check if text contains any words from set using word boundaries."""
        if not text or not word_set:
            return None
            
        normalized = self.normalize_text(text)
        
        for word in word_set:
            # Use word boundaries to avoid false positives like "scunthorpe" 
            pattern = rf"\b{re.escape(word.lower())}\b"
            if re.search(pattern, normalized):
                return word
                
        return None

    def contains_fuzzy_slurs(self, text: str) -> Optional[str]:
        """Check for fuzzy slur patterns (evaded spellings)."""
        if not text:
            return None
            
        normalized = self.normalize_text(text)
        
        for pattern in self.FUZZY_SLURS:
            if re.search(pattern, normalized):
                return pattern
                
        return None

    def check_allowlist(self, text: str) -> bool:
        """Check if text contains known false positives that should be allowed."""
        if not text:
            return False
            
        normalized = self.normalize_text(text)
        
        return any(
            allowed in normalized 
            for allowed in self.ALLOWLIST_EXACT
        )

    def moderate_content(self, text: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Main moderation function for dating platform.
        Returns moderation decision with context.
        """
        if not text:
            return {"action": "allow", "reason": "empty_text"}
            
        # First check allowlist for known false positives
        if self.check_allowlist(text):
            return {
                "action": "allow", 
                "reason": "allowlist_match",
                "details": "Known safe content"
            }
        
        # Check for actual slurs/harassment
        slur_hit = self.contains_any_words(text, self.SLURS)
        if slur_hit:
            self._log_moderation_event(user_id, "slur", slur_hit, text[:50])
            return {
                "action": "block",
                "reason": "slur_detected", 
                "token": slur_hit,
                "message": "Harassment and slurs are not allowed."
            }
        
        # Check for fuzzy slur evasion
        fuzzy_hit = self.contains_fuzzy_slurs(text)
        if fuzzy_hit:
            self._log_moderation_event(user_id, "fuzzy_slur", fuzzy_hit, text[:50])
            return {
                "action": "block",
                "reason": "evasion_detected",
                "token": fuzzy_hit, 
                "message": "Attempted evasion of content filters detected."
            }
        
        # Check sexual content (allowed but logged)
        sexual_hit = self.contains_any_words(text, self.SEXUAL_ALLOWED)
        if sexual_hit:
            return {
                "action": "allow",
                "reason": "sexual_content",
                "token": sexual_hit,
                "note": "Sexual content allowed for dating platform"
            }
        
        # Check soft warning content
        soft_hit = self.contains_any_words(text, self.SOFT_WARN)
        if soft_hit:
            self._log_moderation_event(user_id, "soft_warn", soft_hit, text[:50])
            return {
                "action": "soft_warn",
                "reason": "adult_content",
                "token": soft_hit,
                "message": "Please keep conversations respectful and consensual."
            }
        
        # Default: allow
        return {"action": "allow", "reason": "clean_content"}

    def _log_moderation_event(
        self, 
        user_id: Optional[int], 
        kind: str, 
        token: str, 
        sample: str
    ) -> None:
        """Log moderation events for audit and tuning."""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                # Create moderation events table if not exists
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS moderation_events (
                        id BIGSERIAL PRIMARY KEY,
                        tg_user_id BIGINT,
                        kind TEXT NOT NULL,
                        token TEXT NOT NULL,
                        sample TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                
                # Insert moderation event
                cur.execute("""
                    INSERT INTO moderation_events (tg_user_id, kind, token, sample)
                    VALUES (%s, %s, %s, %s);
                """, (user_id, kind, token, sample))
                
                con.commit()
                
        except Exception as e:
            log.warning(f"Failed to log moderation event: {e}")

    def get_moderation_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get moderation statistics for analysis."""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT 
                        kind,
                        COUNT(*) as count,
                        COUNT(DISTINCT tg_user_id) as unique_users
                    FROM moderation_events 
                    WHERE created_at > NOW() - INTERVAL '%s days'
                    GROUP BY kind
                    ORDER BY count DESC;
                """, (days,))
                
                stats = []
                for row in cur.fetchall():
                    stats.append({
                        "type": row[0],
                        "count": row[1], 
                        "unique_users": row[2]
                    })
                
                return {
                    "success": True,
                    "period_days": days,
                    "stats": stats
                }
                
        except Exception as e:
            log.error(f"Failed to get moderation stats: {e}")
            return {"success": False, "error": str(e)}

    def test_moderation_samples(self) -> Dict[str, Any]:
        """Test moderation with sample messages for validation."""
        test_cases = [
            # Should be BLOCKED
            ("you are a chutiya", "block"),
            ("MC BC", "block"), 
            ("madarchod sale", "block"),
            ("fucking retard", "block"),
            ("kys loser", "block"),
            
            # Should be ALLOWED
            ("I wanna fuck", "allow"),
            ("you're so sexy", "allow"),
            ("fuck me baby", "allow"),
            ("want to have sex", "allow"),
            ("Scunthorpe United", "allow"),
            ("Dickens novels", "allow"),
            
            # Should be SOFT WARNED  
            ("check my onlyfans", "soft_warn"),
            ("porn porn porn", "soft_warn"),
            ("escort services", "soft_warn"),
        ]
        
        results = []
        for text, expected in test_cases:
            result = self.moderate_content(text)
            actual = result["action"]
            
            results.append({
                "text": text,
                "expected": expected,
                "actual": actual,
                "pass": actual == expected,
                "details": result
            })
        
        passed = sum(1 for r in results if r["pass"])
        total = len(results)
        
        return {
            "passed": passed,
            "total": total,
            "success_rate": (passed / total) * 100,
            "results": results
        }

# Global moderation instance
content_moderator = ContentModerationSystem()

def moderate_message(text: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Main function to moderate a message. Dating-platform appropriate."""
    return content_moderator.moderate_content(text, user_id)

def is_content_blocked(text: str, user_id: Optional[int] = None) -> bool:
    """Simple check if content should be blocked."""
    result = moderate_message(text, user_id)
    return result["action"] == "block"

def get_moderation_message(text: str, user_id: Optional[int] = None) -> Optional[str]:
    """Get user-facing moderation message if content is problematic."""
    result = moderate_message(text, user_id)
    return result.get("message")