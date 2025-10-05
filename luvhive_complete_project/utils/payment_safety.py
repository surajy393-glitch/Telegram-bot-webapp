# utils/payment_safety.py - Enhanced payment safety and fraud prevention
import logging
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

log = logging.getLogger(__name__)

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"

class PaymentSafetySystem:
    """Enhanced payment safety with idempotency and fraud prevention."""
    
    def __init__(self):
        self.payment_cache = {}  # In-memory cache for recent payments
        self.fraud_patterns = self._load_fraud_patterns()
        
    def _load_fraud_patterns(self) -> Dict[str, Any]:
        """Load fraud detection patterns."""
        return {
            "max_payments_per_hour": 5,
            "max_payment_amount": 1000,  # Telegram Stars
            "suspicious_velocity_threshold": 3,  # payments in 5 minutes
            "max_failed_attempts": 3
        }
    
    def create_payment_record(
        self, 
        user_id: int, 
        amount: int,
        currency: str,
        telegram_charge_id: str,
        payment_type: str = "premium"
    ) -> Dict[str, Any]:
        """
        Create secure payment record with idempotency protection.
        ChatGPT recommendation: store telegram_charge_id with unique constraint.
        """
        import registration as reg
        
        try:
            # Fraud check before processing
            fraud_check = self._check_payment_fraud(user_id, amount)
            if not fraud_check["allowed"]:
                return {"success": False, "error": fraud_check["reason"]}
            
            with reg._conn() as con, con.cursor() as cur:
                # Create payments table if not exists
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        amount INTEGER NOT NULL,
                        currency TEXT NOT NULL DEFAULT 'XTR',
                        telegram_charge_id TEXT UNIQUE NOT NULL,
                        payment_type TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        processed_at TIMESTAMPTZ,
                        metadata JSONB,
                        
                        CONSTRAINT chk_payment_amount CHECK (amount > 0),
                        CONSTRAINT chk_payment_status CHECK (status IN ('pending', 'processing', 'succeeded', 'failed', 'refunded', 'disputed'))
                    );
                """)
                
                # Create index for fast lookups (outside transaction)
                con.autocommit = True
                try:
                    cur.execute("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_user_status 
                        ON payments(user_id, status);
                    """)
                    
                    cur.execute("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_telegram_charge 
                        ON payments(telegram_charge_id);
                    """)
                finally:
                    con.autocommit = False
                
                # Insert payment record (idempotent via unique constraint)
                try:
                    cur.execute("""
                        INSERT INTO payments (
                            user_id, amount, currency, telegram_charge_id, 
                            payment_type, status, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, created_at;
                    """, (
                        user_id, amount, currency, telegram_charge_id,
                        payment_type, PaymentStatus.PENDING.value,
                        json.dumps({"created_by": "payment_system", "fraud_check": fraud_check})
                    ))
                    
                    result = cur.fetchone()
                    payment_id = result[0]
                    created_at = result[1]
                    
                    con.commit()
                    
                    log.info(f"💰 Payment record created: ID={payment_id}, User={user_id}, Amount={amount}")
                    
                    return {
                        "success": True,
                        "payment_id": payment_id,
                        "telegram_charge_id": telegram_charge_id,
                        "status": PaymentStatus.PENDING.value,
                        "created_at": created_at.isoformat()
                    }
                    
                except Exception as e:
                    if "unique constraint" in str(e).lower():
                        # Payment already exists - return existing record
                        cur.execute("""
                            SELECT id, status, created_at 
                            FROM payments 
                            WHERE telegram_charge_id = %s
                        """, (telegram_charge_id,))
                        
                        existing = cur.fetchone()
                        if existing:
                            return {
                                "success": True,
                                "payment_id": existing[0],
                                "telegram_charge_id": telegram_charge_id,
                                "status": existing[1],
                                "created_at": existing[2].isoformat(),
                                "note": "Payment already exists (idempotent)"
                            }
                    
                    raise e
                    
        except Exception as e:
            log.error(f"Failed to create payment record: {e}")
            return {"success": False, "error": str(e)}
    
    def update_payment_status(
        self, 
        telegram_charge_id: str, 
        new_status: PaymentStatus,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Update payment status with atomic transaction.
        ChatGPT recommendation: persist first, grant second (same transaction).
        """
        import registration as reg
        
        try:
            with reg._conn() as con, con.cursor() as cur:
                # Get current payment info
                cur.execute("""
                    SELECT id, user_id, amount, status, payment_type
                    FROM payments 
                    WHERE telegram_charge_id = %s
                """, (telegram_charge_id,))
                
                payment = cur.fetchone()
                if not payment:
                    return {"success": False, "error": "Payment not found"}
                
                payment_id, user_id, amount, current_status, payment_type = payment
                
                # Validate status transition
                valid_transitions = {
                    PaymentStatus.PENDING.value: [PaymentStatus.PROCESSING.value, PaymentStatus.FAILED.value],
                    PaymentStatus.PROCESSING.value: [PaymentStatus.SUCCEEDED.value, PaymentStatus.FAILED.value],
                    PaymentStatus.SUCCEEDED.value: [PaymentStatus.REFUNDED.value, PaymentStatus.DISPUTED.value],
                    PaymentStatus.FAILED.value: [],
                    PaymentStatus.REFUNDED.value: [],
                    PaymentStatus.DISPUTED.value: [PaymentStatus.SUCCEEDED.value, PaymentStatus.REFUNDED.value]
                }
                
                if new_status.value not in valid_transitions.get(current_status, []):
                    return {
                        "success": False, 
                        "error": f"Invalid status transition: {current_status} -> {new_status.value}"
                    }
                
                # Update payment status
                update_metadata = json.dumps({
                    **(metadata or {}),
                    "status_updated_at": datetime.now().isoformat(),
                    "previous_status": current_status
                })
                
                cur.execute("""
                    UPDATE payments SET 
                        status = %s,
                        updated_at = NOW(),
                        processed_at = CASE WHEN %s = 'succeeded' THEN NOW() ELSE processed_at END,
                        metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                    WHERE telegram_charge_id = %s
                    RETURNING updated_at;
                """, (new_status.value, new_status.value, update_metadata, telegram_charge_id))
                
                updated_at = cur.fetchone()[0]
                
                # If payment succeeded, grant premium benefits in same transaction
                if new_status == PaymentStatus.SUCCEEDED and payment_type == "premium":
                    grant_result = self._grant_premium_benefits(cur, user_id, amount)
                    if not grant_result["success"]:
                        # Rollback if benefit granting fails
                        con.rollback()
                        return {"success": False, "error": f"Failed to grant benefits: {grant_result['error']}"}
                
                con.commit()
                
                log.info(f"💰 Payment {payment_id} updated: {current_status} -> {new_status.value}")
                
                return {
                    "success": True,
                    "payment_id": payment_id,
                    "user_id": user_id,
                    "old_status": current_status,
                    "new_status": new_status.value,
                    "updated_at": updated_at.isoformat()
                }
                
        except Exception as e:
            log.error(f"Failed to update payment status: {e}")
            return {"success": False, "error": str(e)}
    
    def _grant_premium_benefits(self, cursor, user_id: int, amount: int) -> Dict[str, Any]:
        """Grant premium benefits based on payment amount."""
        try:
            # Calculate premium duration based on amount
            # Assuming: 100 Stars = 1 month, 250 Stars = 3 months, 500 Stars = 6 months
            duration_mapping = {
                100: 30,    # 1 month
                250: 90,    # 3 months  
                500: 180,   # 6 months
                1000: 365   # 1 year
            }
            
            days = duration_mapping.get(amount, 30)  # Default to 1 month
            
            # Update user's premium status
            cursor.execute("""
                UPDATE users SET 
                    is_premium = TRUE,
                    premium_until = GREATEST(
                        COALESCE(premium_until, NOW()),
                        NOW()
                    ) + INTERVAL '%s days'
                WHERE tg_user_id = %s
                RETURNING premium_until;
            """, (days, user_id))
            
            result = cursor.fetchone()
            if result:
                premium_until = result[0]
                log.info(f"✨ Premium granted to user {user_id} until {premium_until}")
                return {
                    "success": True,
                    "premium_until": premium_until.isoformat(),
                    "days_added": days
                }
            else:
                return {"success": False, "error": "User not found"}
                
        except Exception as e:
            log.error(f"Failed to grant premium benefits: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_payment_fraud(self, user_id: int, amount: int) -> Dict[str, Any]:
        """Check payment for fraud patterns."""
        import registration as reg
        
        try:
            with reg._conn() as con, con.cursor() as cur:
                now = time.time()
                one_hour_ago = datetime.now() - timedelta(hours=1)
                five_min_ago = datetime.now() - timedelta(minutes=5)
                
                # Check payment velocity (last hour)
                cur.execute("""
                    SELECT COUNT(*) FROM payments 
                    WHERE user_id = %s AND created_at > %s
                """, (user_id, one_hour_ago))
                
                payments_last_hour = cur.fetchone()[0]
                
                if payments_last_hour >= self.fraud_patterns["max_payments_per_hour"]:
                    return {
                        "allowed": False,
                        "reason": f"Too many payments in last hour: {payments_last_hour}"
                    }
                
                # Check suspicious velocity (last 5 minutes)
                cur.execute("""
                    SELECT COUNT(*) FROM payments 
                    WHERE user_id = %s AND created_at > %s
                """, (user_id, five_min_ago))
                
                payments_last_5min = cur.fetchone()[0]
                
                if payments_last_5min >= self.fraud_patterns["suspicious_velocity_threshold"]:
                    return {
                        "allowed": False,
                        "reason": f"Suspicious payment velocity: {payments_last_5min} in 5 minutes"
                    }
                
                # Check amount limits
                if amount > self.fraud_patterns["max_payment_amount"]:
                    return {
                        "allowed": False,
                        "reason": f"Amount exceeds limit: {amount} > {self.fraud_patterns['max_payment_amount']}"
                    }
                
                # Check failed payment attempts
                cur.execute("""
                    SELECT COUNT(*) FROM payments 
                    WHERE user_id = %s AND status = 'failed' AND created_at > %s
                """, (user_id, one_hour_ago))
                
                failed_attempts = cur.fetchone()[0]
                
                if failed_attempts >= self.fraud_patterns["max_failed_attempts"]:
                    return {
                        "allowed": False,
                        "reason": f"Too many failed attempts: {failed_attempts}"
                    }
                
                return {
                    "allowed": True,
                    "fraud_score": (payments_last_hour * 0.2) + (payments_last_5min * 0.5) + (failed_attempts * 0.3),
                    "checks_passed": [
                        "payment_velocity", "amount_limit", "failed_attempts"
                    ]
                }
                
        except Exception as e:
            log.error(f"Fraud check failed: {e}")
            return {"allowed": True, "error": str(e)}  # Allow payment if check fails
    
    def get_payment_status(self, telegram_charge_id: str) -> Dict[str, Any]:
        """Get current payment status and details."""
        import registration as reg
        
        try:
            with reg._conn() as con, con.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, amount, currency, status, payment_type,
                           created_at, updated_at, processed_at, metadata
                    FROM payments 
                    WHERE telegram_charge_id = %s
                """, (telegram_charge_id,))
                
                payment = cur.fetchone()
                if not payment:
                    return {"success": False, "error": "Payment not found"}
                
                return {
                    "success": True,
                    "payment": {
                        "id": payment[0],
                        "user_id": payment[1], 
                        "amount": payment[2],
                        "currency": payment[3],
                        "status": payment[4],
                        "payment_type": payment[5],
                        "created_at": payment[6].isoformat(),
                        "updated_at": payment[7].isoformat(),
                        "processed_at": payment[8].isoformat() if payment[8] else None,
                        "metadata": payment[9] if payment[9] else {}
                    }
                }
                
        except Exception as e:
            log.error(f"Failed to get payment status: {e}")
            return {"success": False, "error": str(e)}

# Global payment safety instance
payment_safety = PaymentSafetySystem()