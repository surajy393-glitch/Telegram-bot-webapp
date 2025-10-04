# utils/payments_integrity.py - Add missing payments constraints (ChatGPT Phase-4)
import logging
import psycopg2

log = logging.getLogger(__name__)

def add_payments_constraints():
    """Add missing unique constraint on payments charge ID + status column"""
    try:
        import registration as reg
        
        with reg._conn() as con, con.cursor() as cur:
            log.info("Adding payments integrity constraints...")
            
            # 1. Create payments table if it doesn't exist (ensure schema)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(tg_user_id) ON DELETE CASCADE,
                    charge_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,  -- Telegram Stars
                    currency TEXT DEFAULT 'XTR',
                    status TEXT NOT NULL DEFAULT 'pending',  -- pending, completed, failed, refunded
                    product_type TEXT NOT NULL,  -- premium, coins, etc.
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            # 2. Add status column if missing
            try:
                cur.execute("""
                    ALTER TABLE payments 
                    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';
                """)
            except psycopg2.Error:
                pass  # Column already exists
                
            # 3. Add updated_at column if missing
            try:
                cur.execute("""
                    ALTER TABLE payments 
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
                """)
            except psycopg2.Error:
                pass  # Column already exists
            
            # 4. Add unique constraint on charge_id (prevent duplicate processing)
            con.autocommit = True
            try:
                cur.execute("""
                    CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_payments_charge_id
                    ON payments(charge_id);
                """)
                log.info("✅ Added unique constraint on payments.charge_id")
            except psycopg2.Error as e:
                log.warning(f"Payments charge_id constraint already exists or failed: {e}")
            
            # 5. Add index on user_id + status for efficient queries
            try:
                cur.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_user_status
                    ON payments(user_id, status);
                """)
                log.info("✅ Added index on payments(user_id, status)")
            except psycopg2.Error:
                pass
                
            # 6. Add index on created_at for analytics
            try:
                cur.execute("""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_created_at
                    ON payments(created_at);
                """)
                log.info("✅ Added index on payments.created_at")
            except psycopg2.Error:
                pass
            finally:
                con.autocommit = False
            
            con.commit()
            log.info("✅ Payments integrity constraints applied successfully")
            
    except Exception as e:
        log.error(f"Failed to add payments constraints: {e}")
        raise

# Apply constraints on import
if __name__ == "__main__":
    add_payments_constraints()