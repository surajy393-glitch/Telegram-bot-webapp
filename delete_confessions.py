
#!/usr/bin/env python3
"""
Delete confessions with IDs 9 to 47 from the database
Keep confessions with ID 48 and above (7 confessions should remain)
"""

from registration import _conn
import sys

def delete_confessions_batch():
    """Delete confessions with IDs 9 to 47"""
    try:
        with _conn() as con, con.cursor() as cur:
            # First, check what confessions exist in the range
            cur.execute("""
                SELECT id, author_id, LEFT(text, 50) as text_preview, system_seed
                FROM confessions 
                WHERE id BETWEEN 9 AND 47
                ORDER BY id
            """)
            confessions_to_delete = cur.fetchall()
            
            if not confessions_to_delete:
                print("✅ No confessions found in ID range 9-47")
                return
                
            print(f"📋 Found {len(confessions_to_delete)} confessions to delete (ID 9-47):")
            for conf in confessions_to_delete:
                conf_id, author_id, text_preview, is_seed = conf
                seed_marker = "🌱" if is_seed else "💬"
                print(f"  {seed_marker} ID {conf_id}: Author {author_id} - '{text_preview}...'")
            
            # Confirm deletion
            print(f"\n⚠️  This will DELETE {len(confessions_to_delete)} confessions!")
            confirm = input("Type 'DELETE' to confirm: ")
            if confirm != 'DELETE':
                print("❌ Deletion cancelled")
                return
            
            # Delete related data first (foreign key constraints)
            print("\n🗑️  Deleting related data...")
            
            # Delete confession reactions
            cur.execute("DELETE FROM confession_reactions WHERE confession_id BETWEEN 9 AND 47")
            reactions_deleted = cur.rowcount
            print(f"   Deleted {reactions_deleted} confession reactions")
            
            # Delete confession replies
            cur.execute("DELETE FROM confession_replies WHERE original_confession_id BETWEEN 9 AND 47")
            replies_deleted = cur.rowcount
            print(f"   Deleted {replies_deleted} confession replies")
            
            # Delete confession deliveries
            cur.execute("DELETE FROM confession_deliveries WHERE confession_id BETWEEN 9 AND 47")
            deliveries_deleted = cur.rowcount
            print(f"   Deleted {deliveries_deleted} confession deliveries")
            
            # Delete pending confession replies
            cur.execute("DELETE FROM pending_confession_replies WHERE original_confession_id BETWEEN 9 AND 47")
            pending_replies_deleted = cur.rowcount
            print(f"   Deleted {pending_replies_deleted} pending replies")
            
            # Finally delete the confessions themselves
            cur.execute("DELETE FROM confessions WHERE id BETWEEN 9 AND 47")
            confessions_deleted = cur.rowcount
            
            # Commit all changes
            con.commit()
            
            print(f"\n✅ Successfully deleted {confessions_deleted} confessions (ID 9-47)")
            print(f"   Total related records deleted: {reactions_deleted + replies_deleted + deliveries_deleted + pending_replies_deleted}")
            
            # Check remaining confessions
            cur.execute("SELECT COUNT(*) FROM confessions WHERE id >= 48")
            remaining_count = cur.fetchone()[0]
            print(f"📊 Remaining confessions (ID 48+): {remaining_count}")
            
            if remaining_count == 7:
                print("🎯 Perfect! Exactly 7 confessions remain as requested")
            else:
                print(f"ℹ️  Note: {remaining_count} confessions remain (not exactly 7)")
            
            # Show remaining confessions
            cur.execute("""
                SELECT id, author_id, LEFT(text, 50) as text_preview, system_seed
                FROM confessions 
                WHERE id >= 48
                ORDER BY id
            """)
            remaining_confs = cur.fetchall()
            
            if remaining_confs:
                print("\n📋 Remaining confessions:")
                for conf in remaining_confs:
                    conf_id, author_id, text_preview, is_seed = conf
                    seed_marker = "🌱" if is_seed else "💬"
                    print(f"  {seed_marker} ID {conf_id}: Author {author_id} - '{text_preview}...'")
            
    except Exception as e:
        print(f"❌ Error deleting confessions: {e}")
        print("🔄 Rolling back changes...")
        con.rollback()
        sys.exit(1)

if __name__ == "__main__":
    print("🗑️  CONFESSION DELETION SCRIPT")
    print("Target: Delete confessions ID 9-47, keep 7 confessions (ID 48+)")
    print("=" * 60)
    
    delete_confessions_batch()
    
    print("\n✅ Script completed successfully!")
