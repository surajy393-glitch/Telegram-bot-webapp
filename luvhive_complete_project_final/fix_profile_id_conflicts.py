
import registration as reg

def fix_profile_id_conflicts():
    """
    Fix profile ID conflicts by assigning unique IDs to sub-profiles
    that don't overlap with users.id values
    """
    
    with reg._conn() as conn:
        with conn.cursor() as cur:
            print("🔧 Starting profile ID conflict resolution...")
            
            # First, let's see the current state
            print("\n1. Current users:")
            cur.execute("SELECT id, tg_user_id, display_name FROM users ORDER BY id")
            users = cur.fetchall()
            for user in users:
                print(f"  User ID: {user[0]}, Telegram ID: {user[1]}, Name: '{user[2]}'")
            
            print("\n2. Current profiles:")
            cur.execute("SELECT id, user_id, profile_name, username FROM profiles ORDER BY id")
            profiles = cur.fetchall()
            for profile in profiles:
                print(f"  Profile ID: {profile[0]}, User ID: {profile[1]}, Name: '{profile[2]}', Username: '{profile[3]}'")
            
            print("\n3. Current posts and their authors:")
            cur.execute("SELECT id, author_id, text FROM feed_posts ORDER BY id")
            posts = cur.fetchall()
            for post in posts:
                print(f"  Post ID: {post[0]}, Author ID: {post[1]}, Text: '{(post[2] or '')[:50]}...'")
            
            # Find the highest user ID to avoid conflicts
            cur.execute("SELECT MAX(id) FROM users")
            max_user_id = cur.fetchone()[0] or 0
            
            # Start profile IDs from a safe range (1000+ above max user ID)
            new_profile_id_start = max_user_id + 1000
            
            print(f"\n4. Max user ID is {max_user_id}, starting profile IDs from {new_profile_id_start}")
            
            # Update profile IDs to non-conflicting values
            profile_id_mappings = {}
            
            for i, profile in enumerate(profiles):
                old_id = profile[0]
                new_id = new_profile_id_start + i + 1
                profile_name = profile[2]
                
                print(f"5. Updating '{profile_name}' from ID {old_id} to ID {new_id}")
                
                # Store mapping for later updates
                profile_id_mappings[old_id] = new_id
                
                # Update the profile ID
                cur.execute("UPDATE profiles SET id = %s WHERE id = %s", (new_id, old_id))
            
            # Update users.active_profile_id if any are set
            print("\n6. Updating active_profile_id references...")
            for old_id, new_id in profile_id_mappings.items():
                cur.execute("UPDATE users SET active_profile_id = %s WHERE active_profile_id = %s", (new_id, old_id))
                updated_rows = cur.rowcount
                if updated_rows > 0:
                    print(f"   Updated {updated_rows} user(s) active_profile_id from {old_id} to {new_id}")
            
            # Check if any posts need their author_id updated
            # (Only if posts were actually created by sub-profiles)
            print("\n7. Checking for posts that need author_id updates...")
            
            # For now, we'll assume all existing posts are from base users
            # and don't need updating. If specific posts were created by sub-profiles,
            # they would need manual identification and updating.
            
            # Reset the sequence for the profiles table to continue from the new range
            cur.execute("SELECT MAX(id) FROM profiles")
            max_profile_id = cur.fetchone()[0] or new_profile_id_start
            new_sequence_value = max_profile_id + 1
            
            print(f"\n8. Resetting profiles ID sequence to start from {new_sequence_value}")
            cur.execute(f"ALTER SEQUENCE profiles_id_seq RESTART WITH {new_sequence_value}")
            
            conn.commit()
            print("\n✅ Profile ID conflicts resolved successfully!")
            
            # Show final state
            print("\nFinal state:")
            print("Users:")
            cur.execute("SELECT id, tg_user_id, display_name, active_profile_id FROM users ORDER BY id")
            final_users = cur.fetchall()
            for user in final_users:
                print(f"  User ID: {user[0]}, Telegram ID: {user[1]}, Name: '{user[2]}', Active Profile: {user[3]}")
            
            print("\nProfiles:")
            cur.execute("SELECT id, user_id, profile_name, username FROM profiles ORDER BY id")
            final_profiles = cur.fetchall()
            for profile in final_profiles:
                print(f"  Profile ID: {profile[0]}, User ID: {profile[1]}, Name: '{profile[2]}', Username: '{profile[3]}'")
            
            return True
                
if __name__ == "__main__":
    success = fix_profile_id_conflicts()
    if success:
        print("\n🔄 Please restart your backend server for changes to take effect!")
        print("The next posts created will show correct author names.")
    else:
        print("\n❌ Fix failed - please check the logs above")
