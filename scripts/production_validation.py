#!/usr/bin/env python3
"""
Production validation script - ChatGPT's final pre-prod checklist
Tests all critical systems before going live
"""
import sys
import logging
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class ProductionValidator:
    """Validate all critical systems for production readiness"""
    
    def __init__(self):
        self.results = {}
        self.passed = 0
        self.total = 0
    
    def test_result(self, test_name: str, success: bool, details: str = ""):
        """Record test result"""
        self.results[test_name] = {"success": success, "details": details}
        self.total += 1
        if success:
            self.passed += 1
            log.info(f"✅ {test_name}: {details}")
        else:
            log.error(f"❌ {test_name}: {details}")
    
    def test_health_endpoints(self):
        """Test /healthz and /readyz endpoints"""
        try:
            from health import healthz, readyz
            
            # Test healthz
            health_result = healthz()
            self.test_result(
                "Health Check (/healthz)",
                health_result.get("status") == "healthy",
                f"Status: {health_result.get('status')}"
            )
            
            # Test readyz  
            ready_result = readyz()
            self.test_result(
                "Readiness Check (/readyz)",
                ready_result.get("status") == "ready",
                f"Status: {ready_result.get('status')}, DB: {ready_result.get('checks', {}).get('database', {}).get('status')}"
            )
            
        except Exception as e:
            self.test_result("Health Endpoints", False, f"Exception: {e}")
    
    def test_backup_system(self):
        """Test backup creation and verification"""
        try:
            from utils.backup_system import backup_system
            
            # Create backup
            backup_result = backup_system.create_backup()
            self.test_result(
                "Backup Creation", 
                backup_result.get("success", False),
                f"Size: {backup_result.get('metadata', {}).get('backup_size_bytes', 0)/1024:.1f}KB, Verified: {backup_result.get('metadata', {}).get('verified', False)}"
            )
            
            # List backups
            list_result = backup_system.list_backups()
            backup_count = len(list_result.get("backups", []))
            self.test_result(
                "Backup Listing",
                list_result.get("success", False) and backup_count > 0,
                f"Found {backup_count} backups"
            )
            
        except Exception as e:
            self.test_result("Backup System", False, f"Exception: {e}")
    
    def test_abuse_prevention(self):
        """Test abuse prevention and auto-mute system"""
        try:
            from utils.abuse_prevention import AbusePreventionSystem
            
            abuse_system = AbusePreventionSystem()
            
            # Test spam detection
            spam_result = abuse_system.check_message_spam(12345, "buy bitcoin crypto invest now!!!")
            self.test_result(
                "Spam Detection",
                spam_result.get("is_spam", False),
                f"Confidence: {spam_result.get('confidence', 0):.2f}, Reasons: {len(spam_result.get('reasons', []))}"
            )
            
            # Test reporting system (simulate reports)
            report_result1 = abuse_system.check_user_reports(99999, 11111)  # User 99999 reported by 11111
            report_result2 = abuse_system.check_user_reports(99999, 22222)  # User 99999 reported by 22222  
            report_result3 = abuse_system.check_user_reports(99999, 33333)  # User 99999 reported by 33333 (should trigger auto-mute)
            
            self.test_result(
                "Auto-Mute on Reports",
                report_result3.get("auto_muted", False),
                f"Auto-muted after {report_result3.get('report_count', 0)} reports"
            )
            
        except Exception as e:
            self.test_result("Abuse Prevention", False, f"Exception: {e}")
    
    def test_content_moderation(self):
        """Test content moderation system"""
        try:
            from utils.content_moderation import content_moderator
            
            # Test slur blocking
            slur_result = content_moderator.moderate_content("you are a chutiya", 12345)
            self.test_result(
                "Slur Blocking",
                slur_result.get("action") == "block",
                f"Action: {slur_result.get('action')}, Token: {slur_result.get('token')}"
            )
            
            # Test sexual content allowance
            sexual_result = content_moderator.moderate_content("you're so sexy baby", 12345)
            self.test_result(
                "Sexual Content Allow",
                sexual_result.get("action") == "allow",
                f"Action: {sexual_result.get('action')}, Reason: {sexual_result.get('reason')}"
            )
            
        except Exception as e:
            self.test_result("Content Moderation", False, f"Exception: {e}")
    
    def test_feature_flags(self):
        """Test feature flags system"""
        try:
            from utils.feature_flags import feature_flags
            
            # Get current status
            status = feature_flags.get_status()
            self.test_result(
                "Feature Flags System",
                True,
                f"Total: {status['total_features']}, Disabled: {status['disabled_count']}"
            )
            
            # Test maintenance mode check
            maintenance_msg = feature_flags.maintenance_message()
            is_maintenance = maintenance_msg is not None
            self.test_result(
                "Maintenance Mode",
                not is_maintenance,  # Should NOT be in maintenance mode
                "Not in maintenance mode (GOOD)" if not is_maintenance else f"In maintenance: {maintenance_msg}"
            )
            
        except Exception as e:
            self.test_result("Feature Flags", False, f"Exception: {e}")
    
    def test_user_deletion(self):
        """Test user deletion system"""
        try:
            from utils.user_deletion import user_deletion
            
            # Test deletion queue
            queue_result = user_deletion.get_deletion_queue()
            self.test_result(
                "User Deletion Queue",
                queue_result.get("success", False),
                f"Queued deletions: {len(queue_result.get('queue', []))}"
            )
            
        except Exception as e:
            self.test_result("User Deletion", False, f"Exception: {e}")
    
    def test_idempotency(self):
        """Test idempotency system"""
        try:
            from utils.idempotency import idempotency
            
            # Test operation idempotency
            key = idempotency.generate_operation_key("test_operation", 12345, action="validation")
            result1 = idempotency.check_and_set_idempotency(key, {"test": "first"})
            result2 = idempotency.check_and_set_idempotency(key, {"test": "second"})  # Should be duplicate
            
            self.test_result(
                "Idempotency System",
                not result1.get("is_duplicate") and result2.get("is_duplicate"),
                f"First: {result1.get('is_duplicate')}, Second: {result2.get('is_duplicate')} (should be duplicate)"
            )
            
        except Exception as e:
            self.test_result("Idempotency", False, f"Exception: {e}")
    
    def test_telegram_safety(self):
        """Test Telegram safety utilities"""
        try:
            from utils.telegram_safety import telegram_safety
            
            # Test message chunking
            long_text = "This is a very long message that needs to be chunked. " * 100
            chunks = telegram_safety._split_text(long_text, 1000)
            
            self.test_result(
                "Message Chunking",
                len(chunks) > 1 and all(len(chunk) <= 1000 for chunk in chunks),
                f"Split into {len(chunks)} chunks, max length: {max(len(chunk) for chunk in chunks)}"
            )
            
            # Test media validation
            fake_media = [f"media_{i}" for i in range(15)]  # Too many
            validated = telegram_safety.validate_media_group(fake_media)
            
            self.test_result(
                "Media Validation",
                len(validated) <= telegram_safety.MAX_MEDIA_PER_MESSAGE,
                f"Limited {len(fake_media)} items to {len(validated)}"
            )
            
        except Exception as e:
            self.test_result("Telegram Safety", False, f"Exception: {e}")
    
    def test_database_integrity(self):
        """Test database integrity"""
        try:
            import registration as reg
            
            with reg._conn() as con, con.cursor() as cur:
                # Test database connection
                cur.execute("SELECT 1")
                result = cur.fetchone()
                
                self.test_result(
                    "Database Connection",
                    result and result[0] == 1,
                    "Database responsive"
                )
                
                # Test users table
                cur.execute("SELECT COUNT(*) FROM users")
                user_count = cur.fetchone()[0]
                
                self.test_result(
                    "Users Table",
                    user_count >= 0,
                    f"{user_count} users in database"
                )
                
        except Exception as e:
            self.test_result("Database Integrity", False, f"Exception: {e}")
    
    def run_all_tests(self):
        """Run complete validation suite"""
        log.info("🚀 Starting Production Validation Suite...")
        log.info("=" * 60)
        
        tests = [
            ("Health Endpoints", self.test_health_endpoints),
            ("Backup System", self.test_backup_system),
            ("Abuse Prevention", self.test_abuse_prevention),
            ("Content Moderation", self.test_content_moderation),
            ("Feature Flags", self.test_feature_flags),
            ("User Deletion", self.test_user_deletion),
            ("Idempotency", self.test_idempotency),
            ("Telegram Safety", self.test_telegram_safety),
            ("Database Integrity", self.test_database_integrity),
        ]
        
        for test_name, test_func in tests:
            log.info(f"\n▶️  Testing {test_name}...")
            try:
                test_func()
            except Exception as e:
                log.error(f"Test suite error in {test_name}: {e}")
        
        # Summary
        log.info("\n" + "=" * 60)
        log.info("🎯 VALIDATION SUMMARY")
        log.info("=" * 60)
        
        success_rate = (self.passed / self.total) * 100 if self.total > 0 else 0
        
        if success_rate >= 90:
            log.info(f"🎉 PRODUCTION READY: {self.passed}/{self.total} tests passed ({success_rate:.1f}%)")
        elif success_rate >= 75:
            log.warning(f"⚠️  MOSTLY READY: {self.passed}/{self.total} tests passed ({success_rate:.1f}%)")
        else:
            log.error(f"❌ NEEDS WORK: {self.passed}/{self.total} tests passed ({success_rate:.1f}%)")
        
        # Show failed tests
        failed_tests = [name for name, result in self.results.items() if not result["success"]]
        if failed_tests:
            log.info(f"\n🔧 Failed tests to investigate:")
            for test in failed_tests:
                details = self.results[test]["details"]
                log.info(f"   • {test}: {details}")
        
        return success_rate >= 90

def main():
    """Run production validation"""
    validator = ProductionValidator()
    is_ready = validator.run_all_tests()
    
    if is_ready:
        print("\n🚀 GREEN LIGHT: Ready for production!")
        exit(0)
    else:
        print("\n⚠️  YELLOW LIGHT: Check failed tests before going live")
        exit(1)

if __name__ == "__main__":
    main()