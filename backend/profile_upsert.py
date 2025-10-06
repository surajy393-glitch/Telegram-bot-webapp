# registration.py (illustrative)
row = await db.fetchrow("""
  INSERT INTO profiles (id, user_id, telegram_id, display_name)
  VALUES (gen_random_uuid(), $1, $2, $3)
  ON CONFLICT (telegram_id) DO UPDATE
    SET user_id = EXCLUDED.user_id,
        display_name = COALESCE(EXCLUDED.display_name, profiles.display_name)
  RETURNING *;
""", user.id, user.telegram_id, user.display_name)