-- 1. List duplicates (reference only)
-- SELECT telegram_id, COUNT(*), ARRAY_AGG(id) FROM profiles GROUP BY telegram_id HAVING COUNT(*)>1;

-- 2. Choose canonical per telegram_id and re-link posts
WITH dups AS (
  SELECT telegram_id,
         MIN(id) AS canonical_id,
         ARRAY_REMOVE(ARRAY_AGG(id), MIN(id)) AS dup_ids
  FROM profiles
  GROUP BY telegram_id
  HAVING COUNT(*) > 1
)
UPDATE posts p
SET profile_id = d.canonical_id
FROM dups d
WHERE p.profile_id = ANY(d.dup_ids);

-- 3. Remove duplicate profiles
DELETE FROM profiles p
USING dups d
WHERE p.id = ANY(d.dup_ids);

-- 4. Hard-stop future duplicates
ALTER TABLE profiles
  ADD CONSTRAINT IF NOT EXISTS profiles_telegram_id_unique
  UNIQUE (telegram_id);

-- 5. Idempotency for posts (blocks double create)
ALTER TABLE posts
  ADD COLUMN IF NOT EXISTS idempotency_key text;
CREATE UNIQUE INDEX IF NOT EXISTS posts_user_id_idempotency_key_uniq
  ON posts (user_id, idempotency_key);

-- 6. Ensure posts always point to a profile
ALTER TABLE posts
  ALTER COLUMN profile_id SET NOT NULL;

-- 7. Kill demo/seed content if present (optional, tweak filters as needed)
DELETE FROM posts WHERE content ILIKE '%demo%' OR content ILIKE '%sample%';