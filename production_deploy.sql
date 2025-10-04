-- Production Database Sync - Auto-generated
-- Run this on your production database after normal deployment

-- Key Data Tables Export
-- Export users table
INSERT INTO users (tg_user_id, gender, age, registration_date, last_seen, times_reported, times_rated, avg_rating, premium_until, premium_type, daily_messages, status, preferred_gender, min_age, max_age, ban_reason, ban_until) 
SELECT tg_user_id, gender, age, registration_date, last_seen, times_reported, times_rated, avg_rating, premium_until, premium_type, daily_messages, status, preferred_gender, min_age, max_age, ban_reason, ban_until 
FROM users ON CONFLICT (tg_user_id) DO UPDATE SET
    gender = EXCLUDED.gender,
    age = EXCLUDED.age,
    registration_date = EXCLUDED.registration_date,
    last_seen = EXCLUDED.last_seen,
    times_reported = EXCLUDED.times_reported,
    times_rated = EXCLUDED.times_rated,
    avg_rating = EXCLUDED.avg_rating,
    premium_until = EXCLUDED.premium_until,
    premium_type = EXCLUDED.premium_type,
    daily_messages = EXCLUDED.daily_messages,
    status = EXCLUDED.status,
    preferred_gender = EXCLUDED.preferred_gender,
    min_age = EXCLUDED.min_age,
    max_age = EXCLUDED.max_age,
    ban_reason = EXCLUDED.ban_reason,
    ban_until = EXCLUDED.ban_until;

-- This is a template - you need to manually copy data from development