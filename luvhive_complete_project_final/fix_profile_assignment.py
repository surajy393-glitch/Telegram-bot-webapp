
import registration as reg

def fix_profile_assignment():
    """Fix the 'Nasty Thing' profile assignment from Siddharth to Ganesh"""
    
    with reg._conn() as conn:
        with conn.cursor() as cur:
            print("Starting profile assignment fix...")
            
            # First, let's see the current state
            print("\n1. Current profiles state:")
            cur.execute("SELECT p.id, p.user_id, p.profile_name, p.username, u.tg_user_id, u.display_name FROM profiles p JOIN users u ON p.user_id = u.id ORDER BY p.id")
            profiles = cur.fetchall()
            for profile in profiles:
                print(f"  Profile ID: {profile[0]}, User ID: {profile[1]}, Name: '{profile[2]}', Username: '{profile[3]}', Telegram ID: {profile[4]}, User Name: '{profile[5]}'")
            
            print("\n2. Current users state:")
            cur.execute("SELECT id, tg_user_id, display_name FROM users ORDER BY id")
            users = cur.fetchall()
            for user in users:
                print(f"  User ID: {user[0]}, Telegram ID: {user[1]}, Name: '{user[2]}'")
            
            # Find Ganesh's user ID (tg_user_id = 647778438)
            cur.execute("SELECT id FROM users WHERE tg_user_id = %s", (647778438,))
            ganesh_row = cur.fetchone()
            if not ganesh_row:
                print("❌ Ganesh's user record not found!")
                return False
                
            ganesh_user_id = ganesh_row[0]
            print(f"\n3. Found Ganesh's internal user ID: {ganesh_user_id}")
            
            # Move the "Nasty Thing" profile to Ganesh's user ID
            print("4. Moving 'Nasty Thing' profile to Ganesh...")
            cur.execute("""
                UPDATE profiles
                SET user_id = %s
                WHERE profile_name = 'Nasty Thing'
                  AND user_id != %s
            """, (ganesh_user_id, ganesh_user_id))
            updated_profiles = cur.rowcount
            print(f"   Updated {updated_profiles} profile(s)")
            
            if updated_profiles > 0:
                # Get the profile ID of the "Nasty Thing" profile
                cur.execute("SELECT id FROM profiles WHERE profile_name = 'Nasty Thing' AND user_id = %s", (ganesh_user_id,))
                nasty_thing_profile_id = cur.fetchone()[0]
                print(f"   'Nasty Thing' profile ID: {nasty_thing_profile_id}")
                
                # Optional: Reassign posts from Ganesh's base user ID to the "Nasty Thing" profile
                print("5. Reassigning Ganesh's posts to 'Nasty Thing' profile...")
                cur.execute("""
                    UPDATE feed_posts
                    SET author_id = %s
                    WHERE author_id = %s
                """, (nasty_thing_profile_id, ganesh_user_id))
                updated_posts = cur.rowcount
                print(f"   Updated {updated_posts} post(s)")
            
            conn.commit()
            print("\n✅ Profile assignment fix completed successfully!")
            
            # Show final state
            print("\nFinal profile state:")
            cur.execute("SELECT p.id, p.user_id, p.profile_name, p.username, u.tg_user_id, u.display_name FROM profiles p JOIN users u ON p.user_id = u.id ORDER BY p.id")
            final_profiles = cur.fetchall()
            for profile in final_profiles:
                print(f"  Profile ID: {profile[0]}, User ID: {profile[1]}, Name: '{profile[2]}', Username: '{profile[3]}', Telegram ID: {profile[4]}, User Name: '{profile[5]}'")
            
            return True
                
if __name__ == "__main__":
    success = fix_profile_assignment()
    if success:
        print("\n🔄 Please restart your backend server for changes to take effect!")
    else:
        print("\n❌ Fix failed - please check the logs above")
