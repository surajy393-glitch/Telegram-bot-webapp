-- Add a column to store client-provided idempotency key
ALTER TABLE posts
ADD COLUMN IF NOT EXISTS idempotency_key text;

-- Prevent duplicates per user + key
CREATE UNIQUE INDEX IF NOT EXISTS posts_user_id_idempotency_key_uniq
ON posts (user_id, idempotency_key);