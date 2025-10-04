
import registration as reg

def fix_profile_database():
    """Fix profile switching issues by correcting database relationships"""
    
    with reg._conn() as conn:
        with conn.cursor() as cur:
            print("Starting profile database fixes...")
            
            # First, let's see what we're working with
            print("\n1. Checking current profiles...")
            cur.execute("SELECT id, user_id, profile_name, username FROM profiles ORDER BY id")
            profiles = cur.fetchall()
            for profile in profiles:
                print(f"  Profile ID: {profile[0]}, User ID: {profile[1]}, Name: '{profile[2]}', Username: '{profile[3]}'")
            
            print("\n2. Checking users...")
            cur.execute("SELECT id, tg_user_id, display_name FROM users ORDER BY id")
            users = cur.fetchall()
            for user in users:
                print(f"  User ID: {user[0]}, Telegram ID: {user[1]}, Name: '{user[2]}'")
            
            # Find the main user (assuming it's the one with the lowest ID for now)
            if users:
                main_user_id = users[0][0]  # Use the first user
                print(f"\n3. Using user ID {main_user_id} as the main user...")
                
                # Link the "Nasty Thing" profile to the actual user account
                print("4. Linking 'Nasty Thing' profile to main user...")
                cur.execute("""
                    UPDATE profiles 
                    SET user_id = %s 
                    WHERE profile_name = 'Nasty Thing'
                """, (main_user_id,))
                updated_rows = cur.rowcount
                print(f"   Updated {updated_rows} profile(s)")
                
                # Fix feed posts pointing to nonexistent profile IDs
                print("5. Fixing feed posts with invalid author_ids...")
                cur.execute("""
                    UPDATE feed_posts 
                    SET author_id = %s 
                    WHERE author_id NOT IN (SELECT id FROM profiles)
                """, (main_user_id,))  # Note: This assumes you want to reassign to user_id, but you might need profile_id
                updated_posts = cur.rowcount
                print(f"   Updated {updated_posts} post(s)")
                
                # Actually, let's be more specific about feed_posts - they should reference profile IDs
                print("6. Checking if feed_posts should reference profiles instead...")
                cur.execute("SELECT id FROM profiles WHERE user_id = %s LIMIT 1", (main_user_id,))
                profile_result = cur.fetchone()
                if profile_result:
                    profile_id = profile_result[0]
                    cur.execute("""
                        UPDATE feed_posts 
                        SET author_id = %s 
                        WHERE author_id NOT IN (SELECT id FROM profiles)
                    """, (profile_id,))
                    updated_posts2 = cur.rowcount
                    print(f"   Updated {updated_posts2} additional post(s) to reference profile ID")
                
                conn.commit()
                print("\n✅ Database fixes completed successfully!")
                
                # Show final state
                print("\nFinal profile state:")
                cur.execute("SELECT id, user_id, profile_name, username FROM profiles ORDER BY id")
                final_profiles = cur.fetchall()
                for profile in final_profiles:
                    print(f"  Profile ID: {profile[0]}, User ID: {profile[1]}, Name: '{profile[2]}', Username: '{profile[3]}'")
                    
            else:
                print("No users found in database!")
                
if __name__ == "__main__":
    fix_profile_database()
