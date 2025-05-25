"""
OAuth Handler for Google and Facebook Login
Simple implementation for WEARXTURE
"""
import os
import httpx
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from typing import Dict, Optional

# Load environment variables
config = Config('.env')

# OAuth configuration
oauth = OAuth(config)

# Register Google OAuth
oauth.register(
    name='google',
    client_id=config('GOOGLE_CLIENT_ID'),
    client_secret=config('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Register Facebook OAuth
oauth.register(
    name='facebook',
    client_id=config('FACEBOOK_CLIENT_ID'),
    client_secret=config('FACEBOOK_CLIENT_SECRET'),
    access_token_url='https://graph.facebook.com/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    api_base_url='https://graph.facebook.com/',
    client_kwargs={'scope': 'email public_profile'}
)

class OAuthHandler:
    """Simple OAuth handler for Google and Facebook"""
    
    @staticmethod
    async def get_google_auth_url(request) -> str:
        """Generate Google OAuth authorization URL"""
        redirect_uri = f"{config('OAUTH_REDIRECT_URL')}/auth/google/callback"
        return await oauth.google.authorize_redirect(request, redirect_uri)
    
    @staticmethod
    async def get_facebook_auth_url(request) -> str:
        """Generate Facebook OAuth authorization URL"""
        redirect_uri = f"{config('OAUTH_REDIRECT_URL')}/auth/facebook/callback"
        return await oauth.facebook.authorize_redirect(request, redirect_uri)
    
    @staticmethod
    async def handle_google_callback(request) -> Optional[Dict]:
        """Handle Google OAuth callback and extract user info"""
        try:
            # Get the token from Google
            token = await oauth.google.authorize_access_token(request)
            
            # Get user info from Google
            user_info = token.get('userinfo')
            if user_info:
                return {
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture'),
                    'provider': 'google',
                    'provider_id': user_info.get('sub')
                }
        except Exception as e:
            print(f"Google OAuth error: {e}")
            return None
    
    @staticmethod
    async def handle_facebook_callback(request) -> Optional[Dict]:
        """Handle Facebook OAuth callback and extract user info"""
        try:
            # Get the token from Facebook
            token = await oauth.facebook.authorize_access_token(request)
            
            # Get user info from Facebook
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://graph.facebook.com/me',
                    params={
                        'fields': 'id,name,email,picture',
                        'access_token': token['access_token']
                    }
                )
                user_data = response.json()
                
                if user_data:
                    return {
                        'email': user_data.get('email'),
                        'name': user_data.get('name'),
                        'picture': user_data.get('picture', {}).get('data', {}).get('url'),
                        'provider': 'facebook',
                        'provider_id': user_data.get('id')
                    }
        except Exception as e:
            print(f"Facebook OAuth error: {e}")
            return None
    
    @staticmethod
    def create_or_get_user(user_data: Dict) -> Dict:
        """Create or get user from Supabase based on OAuth data"""
        try:
            from db.supabase_client import supabase
            
            email = user_data.get('email')
            name = user_data.get('name')
            provider = user_data.get('provider')
            provider_id = user_data.get('provider_id')
            
            if not email:
                raise Exception("No email provided by OAuth provider")
            
            # Check if user exists by email
            existing_user = supabase.table('users').select('*').eq('email', email).execute()
            
            if existing_user.data:
                # Update existing user with OAuth info if needed
                user = existing_user.data[0]
                update_data = {}
                
                if not user.get(f'{provider}_id'):
                    update_data[f'{provider}_id'] = provider_id
                
                if update_data:
                    supabase.table('users').update(update_data).eq('id', user['id']).execute()
                
                return user
            else:
                # Create new user
                new_user_data = {
                    'email': email,
                    'name': name,
                    'auth_provider': provider,
                    f'{provider}_id': provider_id,
                    'is_verified': True,  # OAuth users are pre-verified
                    'profile_picture': user_data.get('picture')
                }
                
                result = supabase.table('users').insert(new_user_data).execute()
                
                if result.data:
                    return result.data[0]
                else:
                    raise Exception("Failed to create user")
                    
        except Exception as e:
            print(f"Error creating/getting user: {e}")
            return None