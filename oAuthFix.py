# oauth_fix_final.py - Works with auto-UUID generation

import os
import sys
sys.path.append('.')

from db.supabase_client import supabase
from datetime import datetime

def add_oauth_user():
    """
    Add OAuth user - Now that UUID auto-generation is set up in database
    """
    email = "hamidarreyan@gmail.com"
    name = "Arreyan Hamid"
    
    try:
        print(f"=== Adding OAuth User (with auto-UUID) ===")
        print(f"Email: {email}")
        print(f"Name: {name}")
        
        # Check if user already exists
        existing = supabase.table('users').select('*').eq('email', email).execute()
        
        if existing.data:
            print(f"✅ User already exists!")
            user = existing.data[0]
        else:
            # Create user data WITHOUT id field (let database auto-generate)
            user_data = {
                'email': email,
                'name': name,
                'provider': 'google',
                'is_verified': True,
                'is_active': True,
                'role': 'customer',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            print(f"\n🔄 Inserting into users table...")
            response = supabase.table('users').insert(user_data).execute()
            
            if response.data:
                user = response.data[0]
                print(f"\n✅ User added to 'users' table:")
                print(f"   Generated ID: {user.get('id')}")
            else:
                print(f"❌ Insert into users failed - no data returned")
                return None
        
        # Insert into the OAuth-specific table now (FK ref to users.id)
        oauth_data = {
            'user_id': user.get('id'),  # Foreign key to users.id
            'oauth_provider': 'google',
            'oauth_subject': 'google-oauth-subject-id',  # Example value
            'created_at': datetime.now().isoformat()
        }

        print(f"\n🔄 Inserting into 'oauth_users' table (or your FK table)...")
        oauth_response = supabase.table('oauth_users').insert(oauth_data).execute()

        if oauth_response.data:
            print(f"✅ OAuth metadata inserted successfully!")
        else:
            print(f"❌ Failed to insert into 'oauth_users'")
            return None

        return user

    except Exception as e:
        print(f"❌ Error adding OAuth user: {e}")
        if hasattr(e, 'details'):
            print(f"Details: {e.details}")
        if hasattr(e, 'message'):
            print(f"Message: {e.message}")
        import traceback
        traceback.print_exc()
        return None


def show_all_users():
    """
    Display all users in the table
    """
    try:
        print(f"\n=== Current Users in Database ===")
        
        users = supabase.table('users').select('id, email, name, provider, is_verified, is_active').execute()
        
        print(f"Total users: {len(users.data)}")
        
        for i, user in enumerate(users.data, 1):
            print(f"\n{i}. {user.get('email')}")
            print(f"   ID: {user.get('id')}")
            print(f"   Name: {user.get('name')}")
            print(f"   Provider: {user.get('provider', 'email')}")
            print(f"   Verified: {user.get('is_verified')}")
            print(f"   Active: {user.get('is_active')}")
    
    except Exception as e:
        print(f"Error showing users: {e}")

def test_oauth_user_exists():
    """
    Test if the OAuth user exists and can be found
    """
    try:
        print(f"\n=== Testing OAuth User ===")
        
        oauth_user = supabase.table('users').select('*').eq('email', 'hamidarreyan@gmail.com').execute()
        
        if oauth_user.data:
            user = oauth_user.data[0]
            print(f"✅ OAuth user found in database:")
            print(f"   ID: {user.get('id')}")
            print(f"   Email: {user.get('email')}")
            print(f"   Provider: {user.get('provider')}")
            print(f"   Can be used for Google login: {'✅ YES' if user.get('provider') == 'google' else '❌ NO'}")
            return True
        else:
            print(f"❌ OAuth user not found in database")
            return False
    
    except Exception as e:
        print(f"Error testing OAuth user: {e}")
        return False

def main():
    """
    Main function to run the OAuth fix
    """
    print("=" * 60)
    print("🔧 OAUTH USER FIX - With Auto-UUID Generation")
    print("=" * 60)
    
    # Show current state
    show_all_users()
    
    # Add the OAuth user
    result = add_oauth_user()
    
    if result:
        print(f"\n" + "=" * 60)
        print("🎉 SUCCESS! OAuth user has been added to the database!")
        print("=" * 60)
        
        # Test that it exists
        test_oauth_user_exists()
        
        print(f"\n📋 NEXT STEPS:")
        print(f"1. Go to your website")
        print(f"2. Click 'Login with Google'")
        print(f"3. Login as: hamidarreyan@gmail.com")
        print(f"4. Check the profile dropdown - it should now show:")
        print(f"   - User email")
        print(f"   - My Orders")
        print(f"   - Logout option")
        print(f"   - etc.")
        
        print(f"\n✅ The profile dropdown issue should now be FIXED!")
        
    else:
        print(f"\n" + "=" * 60)
        print("❌ FAILED to add OAuth user")
        print("=" * 60)
        
        print(f"\nTroubleshooting steps:")
        print(f"1. Check if the UUID auto-generation is working in Supabase")
        print(f"2. Verify the users table structure")
        print(f"3. Try manual insert via Supabase dashboard")
        
    # Show final state
    show_all_users()

if __name__ == "__main__":
    main()