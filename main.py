from fastapi import FastAPI, HTTPException, Depends, status, Request, Form, Response, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uvicorn
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
from jose import jwt
import httpx
import secrets
import urllib.parse
# from admin.user_auth import router as user_auth_router
from inspect import iscoroutinefunction
from db.email_service import send_order_confirmation_email
from db.email_service import send_order_status_update_email
from db.razorpay_client import (
    create_razorpay_order, 
    verify_payment_signature,
    capture_payment,
    get_payment_details,
    RAZORPAY_KEY_ID,
    razorpay_client
)

from fastapi import HTTPException, Request
import httpx

# Import Supabase client
from db.supabase_client import (
    get_all_products, get_product, create_product, update_product, delete_product,
    get_all_categories, get_category, create_category, update_category, delete_category,
    upload_product_image, upload_category_image, verify_admin_credentials, supabase, 
    get_products_by_category, get_subcategories, update_product_images, get_related_products,
    get_all_reels, get_active_reels, get_reel, create_reel, update_reel, delete_reel, upload_reel_video, upload_category_cover_image,
    create_support_query, get_all_support_queries, get_support_query, 
    update_support_query_status, get_support_queries_by_status, get_customer_support_queries
)
from db.order_management import (
    create_order, get_order, update_order_payment_status,
    get_user_orders, get_pending_orders, update_order_status, get_all_orders, update_shiprocket_info 
)
from urllib.parse import urlparse, parse_qs

from db.shiprocket_client import create_shiprocket_order, track_order, create_automatic_shipping

# Load environment variables
load_dotenv()

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET")
ACCESS_TOKEN_EXPIRE_MINUTES =  60 * 8  # 8 hours

# Initialize FastAPI app
app = FastAPI(
    title="WEARXTURE API",
    description="API for WEARXTURE ethnic wear collection",
    version="1.0.0"
)

app.add_middleware(
    SessionMiddleware, 
    secret_key=JWT_SECRET,
    max_age=3600  # 1 hour session
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")
# app.include_router(user_auth_router)

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# ========= Models =========

# Product Models
class ProductBase(BaseModel):
    name: str
    description: str
    price: float
    category_id: int
    in_stock: bool = True
    sku: Optional[str] = None
    filter: Optional[str] = None
    inventory_count: int = 0  # Add this field

class ProductCreate(ProductBase):
    sale_price: Optional[float] = None
    tags: Optional[List[str]] = []
    attributes: Optional[Dict[str, Any]] = {}
    
class ProductUpdate(ProductBase):
    id: int
    sale_price: Optional[float] = None
    tags: Optional[List[str]] = []
    attributes: Optional[Dict[str, Any]] = {}
    
class ProductResponse(ProductBase):
    id: int
    image_url: Optional[str] = None
    category_name: Optional[str] = None
    sale_price: Optional[float] = None
    tags: List[str] = []
    attributes: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    additional_images: List[str] = []
    filter: str = 'all'
    inventory_count: int = 0  # Add this field

# Category Models
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    filter: Optional[str] = 'all'  # Add this field

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    id: int

class CategoryResponse(CategoryBase):
    id: int
    image_url: Optional[str] = None
    cover_image_url: Optional[str] = None  # Add this field
    created_at: datetime
    updated_at: datetime
    filter: str = 'all'  # Add this field


# Reels Models
class ReelBase(BaseModel):
    title: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    product_url: Optional[str] = None
    is_active: bool = True
    display_order: int = 0

class ReelCreate(ReelBase):
    pass

class ReelUpdate(ReelBase):
    id: int

class ReelResponse(ReelBase):
    id: int
    video_url: Optional[str] = None
    category_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str = None
    role: str
    is_active: bool
    created_at: datetime

class ProfileUpdate(BaseModel):
    name: str
    phone: str = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class SupportQueryCreate(BaseModel):
    query_type: str
    customer_email: EmailStr
    customer_name: Optional[str] = None
    subject: Optional[str] = None
    message: str
    priority: Optional[str] = "medium"

class SupportQueryResponse(BaseModel):
    id: int
    query_type: str
    customer_email: str
    customer_name: Optional[str] = None
    subject: Optional[str] = None
    message: str
    status: str = "open"
    priority: str = "medium"
    assigned_to: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    admin_notes: Optional[str] = None

class SupportQueryUpdate(BaseModel):
    status: str
    admin_notes: Optional[str] = None

class WishlistItem(BaseModel):
    product_id: int
    user_id: Optional[int] = None
    session_id: Optional[str] = None

class WishlistResponse(BaseModel):
    id: int
    user_id: Optional[int]
    product_id: int
    product: Optional[ProductResponse]
    created_at: datetime

GOOGLE_CLIENT_ID = "46842260254-itj8edrkh8hf8qqj0fcbvmi3kcd17isn.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

class SimpleOAuthService:
    @staticmethod
    def generate_google_auth_url(redirect_uri: str, state: str) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': redirect_uri,
            'scope': 'openid email profile',
            'response_type': 'code',
            'state': state,
            'access_type': 'offline'
        }
        
        query_string = urllib.parse.urlencode(params)
        return f"https://accounts.google.com/o/oauth2/auth?{query_string}"
    
    @staticmethod
    async def exchange_code_for_token(code: str, redirect_uri: str) -> Optional[Dict]:
        """Exchange authorization code for access token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://oauth2.googleapis.com/token',
                    data={
                        'code': code,
                        'client_id': GOOGLE_CLIENT_ID,
                        'client_secret': GOOGLE_CLIENT_SECRET,
                        'redirect_uri': redirect_uri,
                        'grant_type': 'authorization_code'
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Token exchange failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"Error exchanging code for token: {e}")
            return None
    
    @staticmethod
    async def get_user_info(access_token: str) -> Optional[Dict]:
        """Get user information from Google"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"User info request failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None

class OAuthUserService:
    @staticmethod
    async def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Find user in Supabase by email"""
        try:
            from db.supabase_client import get_user_by_email_simple
            return get_user_by_email_simple(email)
        except Exception as e:
            print(f"Error finding user by email: {e}")
            return None
    
    @staticmethod
    async def create_oauth_user(user_data: dict) -> Dict[str, Any]:
        """Create user from OAuth data"""
        try:
            print(f"Creating OAuth user: {user_data['email']}")
            
            from db.supabase_client import supabase
            
            # Create user record with OAuth data
            user_record = {
                "email": user_data['email'],
                "password_hash": "oauth_user",  # Placeholder for OAuth users
                "name": user_data.get('name', ''),
                "provider": user_data.get('provider', 'google'),
                "provider_id": user_data.get('provider_id', ''),
                "avatar_url": user_data.get('avatar_url', ''),
                "is_active": True,
                "role": "customer"
            }
            
            response = supabase.table('users').insert(user_record).execute()
            
            if response.data:
                print(f"✅ OAuth user created successfully: {response.data[0]['id']}")
                return response.data[0]
            else:
                raise Exception("No data returned from insert")
            
        except Exception as e:
            print(f"❌ Error creating OAuth user: {e}")
            
            # Fallback: try to find existing user
            existing_user = await OAuthUserService.find_user_by_email(user_data['email'])
            if existing_user:
                print(f"Found existing user, updating with OAuth data")
                return await OAuthUserService.update_user_oauth_info(existing_user['id'], user_data)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create OAuth user: {str(e)}"
            )
    
    @staticmethod
    async def update_user_oauth_info(user_id: int, oauth_data: dict) -> Dict[str, Any]:
        """Update existing user with OAuth information"""
        try:
            from db.supabase_client import supabase
            
            update_data = {
                "provider": oauth_data.get('provider', 'google'),
                "provider_id": oauth_data.get('provider_id', ''),
                "avatar_url": oauth_data.get('avatar_url', ''),
            }
            
            response = supabase.table('users').update(update_data).eq('id', user_id).execute()
            
            if response.data:
                return response.data[0]
            else:
                # If update failed, get the current user
                from db.supabase_client import get_user_by_id_simple
                return get_user_by_id_simple(user_id)
                
        except Exception as e:
            print(f"Error updating user OAuth info: {e}")
            # Fallback: return user without OAuth update
            from db.supabase_client import get_user_by_id_simple
            return get_user_by_id_simple(user_id)

# ========= OAuth Routes =========

@app.get('/auth/google')
async def google_auth(request: Request):
    """Initiate Google OAuth flow"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return RedirectResponse(url="/login?error=OAuth not configured")
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    
    # Store redirect URL if provided
    redirect_after = request.query_params.get('redirect')
    if redirect_after:
        request.session['oauth_redirect'] = redirect_after
    
    # Generate OAuth URL
    redirect_uri = str(request.url_for('google_callback'))
    auth_url = SimpleOAuthService.generate_google_auth_url(redirect_uri, state)
    
    return RedirectResponse(url=auth_url)

@app.get('/auth/google/callback')
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    try:
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            return RedirectResponse(url="/login?error=OAuth not configured")
        
        # Verify state parameter for CSRF protection
        returned_state = request.query_params.get('state')
        stored_state = request.session.get('oauth_state')
        
        if not returned_state or returned_state != stored_state:
            print("OAuth state mismatch - CSRF protection triggered")
            # Continue anyway for compatibility
        
        # Get authorization code
        code = request.query_params.get('code')
        if not code:
            return RedirectResponse(url="/login?error=No authorization code provided")
        
        # Exchange code for access token
        redirect_uri = str(request.url_for('google_callback'))
        token_data = await SimpleOAuthService.exchange_code_for_token(code, redirect_uri)
        
        if not token_data or 'access_token' not in token_data:
            return RedirectResponse(url="/login?error=Failed to get access token")
        
        # Get user info from Google
        user_info = await SimpleOAuthService.get_user_info(token_data['access_token'])
        
        if not user_info or not user_info.get('email'):
            return RedirectResponse(url="/login?error=No email provided by Google")
        
        # Prepare OAuth user data
        oauth_user_data = {
            'email': user_info['email'],
            'name': user_info.get('name', ''),
            'provider': 'google',
            'provider_id': user_info.get('id', ''),
            'avatar_url': user_info.get('picture', '')
        }
        
        # Find or create user
        existing_user = await OAuthUserService.find_user_by_email(oauth_user_data['email'])
        
        if existing_user:
            # Update existing user with OAuth info
            user = await OAuthUserService.update_user_oauth_info(existing_user['id'], oauth_user_data)
        else:
            # Create new user
            user = await OAuthUserService.create_oauth_user(oauth_user_data)
        
        # Generate JWT token
        access_token = create_access_token(
            user_id=user['id'],
            email=user['email']
        )
        
        # Get redirect URL
        redirect_url = request.session.pop('oauth_redirect', None)
        
        if redirect_url == 'profile':
            final_redirect = "/profile"
        elif redirect_url == 'checkout':
            final_redirect = "/checkout"
        else:
            final_redirect = "/"
        
        # Clean up session
        request.session.pop('oauth_state', None)
        
        # Create response and set cookie
        response = RedirectResponse(url=final_redirect, status_code=303)
        response.set_cookie(
            key="user_access_token",
            value=access_token,
            max_age=28800,  # 8 hours
            httponly=True,
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        print(f"❌ OAuth callback error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/login?error=Authentication failed")

# Wishlist page route
@app.get("/wishlist", response_class=HTMLResponse)
async def wishlist_page(request: Request):
    """Display user wishlist page"""
    return templates.TemplateResponse("wishlist.html", {"request": request})

# Get user's wishlist
@app.get("/api/user/wishlist")
async def get_user_wishlist(request: Request):
    """Get wishlist items for authenticated or guest user"""
    try:
        # Check if user is authenticated
        token = request.cookies.get("user_access_token")
        user = None
        
        if token:
            user = get_current_user_simple(token)
        
        if user:
            # Get wishlist for authenticated user
            from db.supabase_client import get_user_wishlist
            wishlist_items = get_user_wishlist(user['id'])
        else:
            # For guest users, return empty array (they use localStorage)
            wishlist_items = []
        
        return {
            "success": True,
            "wishlist": wishlist_items
        }
        
    except Exception as e:
        print(f"Error getting wishlist: {e}")
        return {
            "success": False,
            "error": str(e),
            "wishlist": []
        }

# Add item to wishlist
@app.post("/api/user/wishlist")
async def add_to_wishlist(wishlist_item: WishlistItem, request: Request):
    """Add item to user's wishlist"""
    try:
        # Check if user is authenticated
        token = request.cookies.get("user_access_token")
        user = None
        
        if token:
            user = get_current_user_simple(token)
        
        if user:
            # Add to database for authenticated user
            from db.supabase_client import add_to_user_wishlist
            success = add_to_user_wishlist(user['id'], wishlist_item.product_id)
            
            if success:
                return {
                    "success": True,
                    "message": "Item added to wishlist"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to add item to wishlist"
                )
        else:
            # For guest users, they handle this with localStorage
            return {
                "success": True,
                "message": "Item added to wishlist (guest mode)"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error adding to wishlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add to wishlist: {str(e)}"
        )

# Remove item from wishlist
@app.delete("/api/user/wishlist/{product_id}")
async def remove_from_wishlist(product_id: int, request: Request):
    """Remove item from user's wishlist"""
    try:
        # Check if user is authenticated
        token = request.cookies.get("user_access_token")
        user = None
        
        if token:
            user = get_current_user_simple(token)
        
        if user:
            # Remove from database for authenticated user
            from db.supabase_client import remove_from_user_wishlist
            success = remove_from_user_wishlist(user['id'], product_id)
            
            if success:
                return {
                    "success": True,
                    "message": "Item removed from wishlist"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to remove item from wishlist"
                )
        else:
            # For guest users, they handle this with localStorage
            return {
                "success": True,
                "message": "Item removed from wishlist (guest mode)"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error removing from wishlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove from wishlist: {str(e)}"
        )

# Clear entire wishlist
@app.delete("/api/user/wishlist")
async def clear_wishlist(request: Request):
    """Clear user's entire wishlist"""
    try:
        # Check if user is authenticated
        token = request.cookies.get("user_access_token")
        user = None
        
        if token:
            user = get_current_user_simple(token)
        
        if user:
            # Clear database wishlist for authenticated user
            from db.supabase_client import clear_user_wishlist
            success = clear_user_wishlist(user['id'])
            
            if success:
                return {
                    "success": True,
                    "message": "Wishlist cleared"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to clear wishlist"
                )
        else:
            # For guest users, they handle this with localStorage
            return {
                "success": True,
                "message": "Wishlist cleared (guest mode)"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error clearing wishlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear wishlist: {str(e)}"
        )

# Check if item is in wishlist
@app.get("/api/user/wishlist/check/{product_id}")
async def check_wishlist_item(product_id: int, request: Request):
    """Check if a product is in user's wishlist"""
    try:
        # Check if user is authenticated
        token = request.cookies.get("user_access_token")
        user = None
        
        if token:
            user = get_current_user_simple(token)
        
        if user:
            # Check database for authenticated user
            from db.supabase_client import is_in_user_wishlist
            is_in_wishlist = is_in_user_wishlist(user['id'], product_id)
            
            return {
                "success": True,
                "in_wishlist": is_in_wishlist
            }
        else:
            # For guest users, they handle this with localStorage
            return {
                "success": True,
                "in_wishlist": False,
                "guest_mode": True
            }
        
    except Exception as e:
        print(f"Error checking wishlist: {e}")
        return {
            "success": False,
            "in_wishlist": False,
            "error": str(e)
        }

# Get wishlist with product details
@app.get("/api/user/wishlist/products")
async def get_wishlist_with_products(request: Request):
    """Get wishlist items with full product details"""
    try:
        # Check if user is authenticated
        token = request.cookies.get("user_access_token")
        user = None
        
        if token:
            user = get_current_user_simple(token)
        
        if user:
            # Get wishlist with product details for authenticated user
            from db.supabase_client import get_user_wishlist_with_products
            wishlist_products = get_user_wishlist_with_products(user['id'])
            
            return {
                "success": True,
                "wishlist": [product_from_db(product) for product in wishlist_products]
            }
        else:
            # For guest users, return empty (they use localStorage + API calls)
            return {
                "success": True,
                "wishlist": [],
                "guest_mode": True
            }
        
    except Exception as e:
        print(f"Error getting wishlist products: {e}")
        return {
            "success": False,
            "wishlist": [],
            "error": str(e)
        }

async def get_authenticated_user(request: Request) -> Dict[str, Any]:
    """Dependency to get authenticated user"""
    token = request.cookies.get("user_access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user = get_current_user_simple(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return user
            
@app.post("/api/products/by-ids")
async def get_products_by_ids(product_ids: List[int]):
    """Get products by their IDs (useful for wishlist)"""
    try:
        db_products = get_all_products()
        
        # Filter products by the provided IDs
        filtered_products = [
            product_from_db(product) for product in db_products 
            if product['id'] in product_ids
        ]
        
        return {
            "success": True,
            "products": filtered_products
        }
    except Exception as e:
        print(f"Error getting products by IDs: {e}")
        return {
            "success": False,
            "products": [],
            "error": str(e)
        }
# JWT Helper Functions
def create_access_token(user_id: int, email: str, expires_delta: timedelta = None):
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=8)
    
    to_encode = {
        "email": email,
        "user_id": user_id,
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    return encoded_jwt

def get_current_user_simple(token: str) -> Optional[Dict[str, Any]]:
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        email: str = payload.get("email")
        user_id: int = payload.get("user_id")
        
        if email is None or user_id is None:
            return None
            
        from db.supabase_client import get_user_by_id_simple
        user = get_user_by_id_simple(user_id)
        return user
        
    except:
        return None
# Profile page route
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Display user profile page"""
    try:
        token = request.cookies.get("user_access_token")
        
        if not token:
            return RedirectResponse(url="/login?redirect=profile")
        
        user = get_current_user_simple(token)
        
        if not user:
            return RedirectResponse(url="/login?redirect=profile")
        
        return templates.TemplateResponse("profile.html", {"request": request, "user": user})
        
    except Exception as e:
        return RedirectResponse(url="/login?redirect=profile")

# API route to update user profile
@app.put("/api/auth/update-profile")
async def update_user_profile(
    profile_data: ProfileUpdate,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Update user profile information"""
    try:
        from db.supabase_client import update_user
        
        # Prepare update data
        update_data = {
            'name': profile_data.name.strip(),
            'phone': profile_data.phone.strip() if profile_data.phone else None
        }
        
        # Update user in database
        updated_user = update_user(user['id'], update_data)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile"
            )
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "user": updated_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

# API route to change password
@app.put("/api/auth/change-password")
async def change_user_password(
    password_data: PasswordChange,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Change user password"""
    try:
        from db.supabase_client import authenticate_user_simple, update_user
        
        # Verify current password
        auth_user = authenticate_user_simple(user['email'], password_data.current_password)
        if not auth_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        update_data = {'password': password_data.new_password}
        updated_user = update_user(user['id'], update_data)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        return {
            "success": True,
            "message": "Password updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )
@app.get("/api/auth/status")
async def check_auth_status(request: Request):
    """Check if user is authenticated"""
    try:
        token = request.cookies.get("user_access_token")
        
        if not token:
            return {"authenticated": False}
        
        user = get_current_user_simple(token)
        
        if user:
            return {
                "authenticated": True,
                "user": user
            }
        else:
            return {"authenticated": False}
            
    except Exception as e:
        print(f"Auth status check error: {e}")
        return {"authenticated": False}
# Logout route
@app.get("/logout")
async def logout_user():
    """Logout user and redirect to home"""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="user_access_token")
    return response

# Update the get_authenticated_user dependency

            
# Authentication Routes
@app.post("/api/auth/register")
async def register_user_simple(user_data: UserRegister):
    """Register a new user - NO Supabase Auth, only custom users table"""
    try:
        print(f"🔧 Registration attempt for: {user_data.email}")
        
        # Import our simple functions
        from db.supabase_client import create_user_simple, get_user_by_email_simple
        
        # Check if user already exists in OUR custom users table
        existing_user = get_user_by_email_simple(user_data.email)
        if existing_user:
            print(f"❌ User already exists: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        print(f"✅ Email available: {user_data.email}")
        
        # Create new user in OUR custom users table ONLY
        new_user = create_user_simple(
            email=user_data.email,
            password=user_data.password,
            name=user_data.name,
            phone=user_data.phone
        )
        
        if not new_user:
            print(f"❌ Failed to create user")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account"
            )
        
        print(f"✅ User created successfully: {new_user.get('id')}")
        
        return {
            "success": True,
            "message": "User registered successfully",
            "user": new_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Registration error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@app.post("/api/auth/login")
async def login_user_simple(user_data: UserLogin):
    """Login user with cookie setting"""
    try:
        from db.supabase_client import authenticate_user_simple
        
        user = authenticate_user_simple(user_data.email, user_data.password)
        
        if not user or not user.get('is_active', False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        access_token = create_access_token(
            user_id=user['id'],
            email=user['email']
        )
        
        # Create response and set cookie
        response_data = {
            "success": True,
            "access_token": access_token,
            "user": user,
            "token_type": "bearer"
        }
        
        response = JSONResponse(content=response_data)
        response.set_cookie(
            key="user_access_token",
            value=access_token,
            max_age=28800,  # 8 hours
            httponly=True,
            samesite="lax"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@app.get("/api/auth/me")
async def get_current_user_info(request: Request):
    """Get current user information"""
    try:
        token = request.cookies.get("user_access_token")
        
        if not token:
            return JSONResponse(
                status_code=401,
                content={"success": False, "detail": "Not authenticated"}
            )
        
        user = get_current_user_simple(token)
        
        if not user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "detail": "Invalid token"}
            )
        
        return {"success": True, "user": user}
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "detail": "Server error"}
        )

@app.post("/api/auth/logout")
async def logout_user():
    """Logout user"""
    response = JSONResponse(content={"success": True, "message": "Logged out successfully"})
    response.delete_cookie(key="user_access_token")
    return response

# User Authentication Dependency
async def get_authenticated_user(request: Request) -> Dict[str, Any]:
    """Dependency to get authenticated user"""
    token = request.cookies.get("user_access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user = get_current_user(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return user



@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the user login/register page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/return", response_class=HTMLResponse)
async def return_page(request: Request):
    return templates.TemplateResponse("return.html", {"request": request})

@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """Serve the checkout page"""
    return templates.TemplateResponse("checkout.html", {"request": request})



@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    return templates.TemplateResponse("legal/terms.html", {"request": request})

@app.get("/return-policy", response_class=HTMLResponse)
async def returnPolicy_page(request: Request):
    return templates.TemplateResponse("legal/returnPolicy.html", {"request": request})

@app.get("/shipping-policy", response_class=HTMLResponse)
async def shippingPolicy_page(request: Request):
    return templates.TemplateResponse("legal/shippingPolicy.html", {"request": request})

@app.get("/privacy-policy", response_class=HTMLResponse)
async def privacyPolicy_page(request: Request):
    return templates.TemplateResponse("legal/privacyPolicy.html", {"request": request})

@app.get("/contact", response_class=HTMLResponse)
async def contact_page(request: Request):
    return templates.TemplateResponse("legal/contact.html", {"request": request})

# Create order endpoint (placeholder for now)
# Create order endpoint
@app.post("/api/orders")
async def create_order_endpoint(order_data: dict, request: Request):
    """Create a new order with Razorpay integration, inventory management, and Shiprocket integration"""
    try:
        print(f"📋 Starting order creation process...")
        
        # Extract order details
        cart = order_data.get("cart", [])
        email = order_data.get("email")
        phone = order_data.get("phone")
        delivery_address = {
            "address": order_data.get("address"),
            "city": order_data.get("city"),
            "state": order_data.get("state"),
            "pincode": order_data.get("pincode"),
            "country": order_data.get("country"),
            "first_name": order_data.get("firstName", ""),
            "last_name": order_data.get("lastName", ""),
            "name": f"{order_data.get('firstName', '')} {order_data.get('lastName', '')}".strip()
        }
        
        is_cod = order_data.get("isCOD", False)
        
        print(f"📦 Order details:")
        print(f"   Customer: {email}")
        print(f"   Items: {len(cart)}")
        print(f"   Payment: {'COD' if is_cod else 'Online'}")
        print(f"   Location: {delivery_address.get('city')}, {delivery_address.get('state')}")
        
        # First, validate inventory for all items
        print(f"📊 Validating inventory for {len(cart)} items...")
        from db.supabase_client import get_product
        
        inventory_issues = []
        for item in cart:
            product_id = item.get("id") or item.get("product_id")
            quantity = item.get("quantity", 1)
            
            if product_id:
                # Get product from database
                product = get_product(product_id)
                
                if not product:
                    inventory_issues.append(f"Product {product_id} not found")
                    continue
                
                inventory_count = product.get("inventory_count", 0)
                
                if inventory_count < quantity:
                    inventory_issues.append(
                        f"Insufficient inventory for {item.get('name', 'product')}. "
                        f"Available: {inventory_count}, Requested: {quantity}"
                    )
        
        # If there are inventory issues, return error immediately
        if inventory_issues:
            print(f"❌ Inventory validation failed:")
            for issue in inventory_issues:
                print(f"   - {issue}")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="; ".join(inventory_issues)
            )
        
        print(f"✅ Inventory validation passed")
        
        # Get the actual order total and the amount to charge on Razorpay
        actual_order_total = order_data.get("actualOrderTotal", 0)
        razorpay_amount = order_data.get("razorpayAmount", 0)  # This is 80 for COD, full amount otherwise
        remaining_amount = order_data.get("remainingAmount", 0)  # For COD only
        
        # Generate order ID
        order_id = "ORD" + datetime.now().strftime("%Y%m%d%H%M%S")
        
        print(f"🆔 Generated Order ID: {order_id}")
        
        # Prepare cart items with product IDs for inventory management
        cart_with_ids = []
        for item in cart:
            # Ensure both id and product_id are set for database operations
            product_id = item.get("id") or item.get("product_id")
            cart_item = {
                **item,
                "product_id": product_id,
                "id": product_id
            }
            cart_with_ids.append(cart_item)
        
        # Prepare order record with actual totals
        order_record = {
            "order_id": order_id,
            "user_email": email,
            "phone": phone,
            "delivery_address": delivery_address,
            "items": cart_with_ids,  # Use cart with proper IDs
            "subtotal": order_data.get("subtotal", 0),
            "delivery_charge": order_data.get("deliveryCharge", 0),
            "tax": order_data.get("tax", 0),
            "total_amount": actual_order_total,  # The actual order total
            "payment_method": order_data.get("payment"),
            "payment_status": "pending",
            "order_status": "pending"
        }
        
        # Add COD-specific fields
        if is_cod:
            order_record.update({
                "cod_fee": 80,
                "cod_remaining": remaining_amount,
                "cod_status": "fee_pending"
            })
        
        print(f"💾 Preparing to save order to database...")
        
        # Create Razorpay order for all payment types (including COD fee)
        razorpay_order = None
        demo_mode = False
        
        try:
            # Check if Razorpay is configured
            if not RAZORPAY_KEY_ID or not razorpay_client:
                print("⚠️ Razorpay not configured. Using demo mode.")
                demo_mode = True
            else:
                print(f"💳 Creating Razorpay order for ₹{razorpay_amount}...")
                
                # Create Razorpay order
                razorpay_order = create_razorpay_order(
                    amount=razorpay_amount,  # COD: 80, Otherwise: full amount
                    order_info={
                        "receipt": order_id,
                        "notes": {
                            "customer_email": email,
                            "customer_phone": phone,
                            "is_cod": "true" if is_cod else "false",
                            "actual_order_total": str(actual_order_total)
                        }
                    }
                )
                
                print(f"✅ Razorpay order created: {razorpay_order['id']}")
                
                # Save Razorpay order ID
                order_record["razorpay_order_id"] = razorpay_order["id"]
                
        except Exception as razorpay_error:
            print(f"⚠️ Razorpay order creation failed: {str(razorpay_error)}")
            print("Falling back to demo mode...")
            demo_mode = True
        
        # Save order to database
        print(f"💾 Saving order to database...")
        saved_order = create_order(order_record)
        
        if not saved_order or (isinstance(saved_order, dict) and saved_order.get("error")):
            error_msg = saved_order.get("error") if isinstance(saved_order, dict) else "Failed to save order to database"
            print(f"❌ Order creation failed: {error_msg}")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        print(f"✅ Order saved successfully with ID: {order_id}")
        
        # Send order confirmation email
        try:
            print(f"📧 Sending order confirmation email...")
            from db.email_service import send_order_confirmation_email
            email_sent = send_order_confirmation_email(saved_order)
            
            if email_sent:
                print(f"✅ Order confirmation email sent to {email}")
            else:
                print(f"⚠️ Failed to send order confirmation email")
                
        except Exception as email_error:
            # Don't let email errors affect order creation
            print(f"⚠️ Error sending confirmation email: {email_error}")

        # Enhanced Shiprocket integration with proper pickup location handling
        try:
            print("🚚 Starting Shiprocket integration...")
            from db.shiprocketManagement import ShiprocketClient, format_wearxture_order_for_shiprocket
            
            # Initialize Shiprocket client
            shiprocket_client = ShiprocketClient()
            
            # Get the correct pickup location from Shiprocket
            pickup_location = shiprocket_client.get_primary_pickup_location()
            
            if pickup_location:
                print(f"📍 Using pickup location: '{pickup_location}'")
                
                # Format the order data for Shiprocket
                shiprocket_order_data = format_wearxture_order_for_shiprocket(
                    saved_order, 
                    pickup_location=pickup_location
                )
                
                if shiprocket_order_data:
                    print(f"📋 Formatted order data for Shiprocket")
                    
                    # Create the order in Shiprocket
                    shiprocket_result = shiprocket_client.create_order(shiprocket_order_data)
                    
                    if shiprocket_result.get('success'):
                        print(f"✅ Shiprocket order created successfully!")
                        print(f"   Shiprocket Order ID: {shiprocket_result.get('order_id')}")
                        print(f"   Shipment ID: {shiprocket_result.get('shipment_id')}")
                        
                        # Update your order record with Shiprocket details
                        try:
                            from db.order_management import update_shiprocket_info
                            shiprocket_info = {
                                'order_id': shiprocket_result.get('order_id'),
                                'shipment_id': shiprocket_result.get('shipment_id'),
                                'tracking_url': f"https://shiprocket.co/tracking/{shiprocket_result.get('shipment_id')}" if shiprocket_result.get('shipment_id') else None
                            }
                            
                            success = update_shiprocket_info(saved_order['order_id'], shiprocket_info)
                            if success:
                                print("✅ Order updated with Shiprocket tracking info")
                            else:
                                print("⚠️ Failed to update order with Shiprocket info")
                                
                        except Exception as update_error:
                            print(f"⚠️ Error updating order with Shiprocket info: {update_error}")
                        
                    else:
                        error_msg = shiprocket_result.get('error', 'Unknown error')
                        print(f"❌ Shiprocket order creation failed: {error_msg}")
                        
                        # Log additional details for debugging
                        if 'details' in shiprocket_result:
                            print(f"   Details: {shiprocket_result['details']}")
                        
                        if 'valid_pickup_locations' in shiprocket_result:
                            print(f"   Valid pickup locations: {shiprocket_result['valid_pickup_locations']}")
                            
                        # Log the order data that failed
                        print(f"   Failed order data keys: {list(shiprocket_order_data.keys())}")
                else:
                    print("❌ Failed to format order data for Shiprocket")
            else:
                print("❌ No pickup locations available in Shiprocket account")
                print("   Please configure at least one pickup location in your Shiprocket dashboard")
            
        except Exception as shiprocket_error:
            print(f"⚠️ Shiprocket integration error (non-critical): {shiprocket_error}")
            import traceback
            traceback.print_exc()
            # Continue with order processing even if Shiprocket fails
        
        # Prepare response based on demo mode or real payment
        if demo_mode:
            print(f"🎭 Returning demo mode response")
            return {
                "success": True,
                "order_id": order_id,
                "demo_mode": True,
                "message": "Demo order created successfully. In production, you would be redirected to Razorpay.",
                "amount": int(razorpay_amount * 100),
                "is_cod": is_cod,
                "actual_order_total": actual_order_total,
                "remaining_amount": remaining_amount if is_cod else 0
            }
        else:
            print(f"💳 Returning Razorpay payment response")
            return {
                "success": True,
                "order_id": order_id,
                "razorpay_order_id": razorpay_order["id"],
                "razorpay_key": RAZORPAY_KEY_ID,
                "amount": int(razorpay_amount * 100),
                "currency": "INR",
                "company_name": "WEARXTURE",
                "company_logo": "/static/images/WEARXTURE LOGOai.png",
                "is_cod": is_cod,
                "actual_order_total": actual_order_total,
                "remaining_amount": remaining_amount if is_cod else 0
            }
            
    except HTTPException as http_error:
        # Re-raise HTTP exceptions as is
        print(f"❌ HTTP Exception: {http_error.detail}")
        raise http_error
        
    except Exception as e:
        print(f"❌ Unexpected error in order creation: {str(e)}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order creation failed: {str(e)}"
        )


@app.get("/api/orders/{order_id}/tracking")
async def get_order_tracking(order_id: str, request: Request):
    """Get tracking information for an order"""
    try:
        # Verify user owns this order (same logic as other order endpoints)
        token = request.cookies.get("user_access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_email = payload.get("sub")
        
        # Get order from database
        order = get_order(order_id)
        if not order or order.get("user_email") != user_email:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Get tracking info from Shiprocket
        tracking_info = track_order(order_id)
        
        if tracking_info:
            return {"success": True, "tracking": tracking_info}
        else:
            return {"success": False, "message": "Tracking not available yet"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}
@app.post("/api/check-inventory")
async def check_inventory(cart_items: List[dict]):
    """Check inventory availability for cart items"""
    try:
        results = []
        all_available = True
        
        for item in cart_items:
            product_id = item.get("id")
            quantity = item.get("quantity", 1)
            
            if product_id:
                product = get_product(product_id)
                
                if product:
                    inventory_count = product.get("inventory_count", 0)
                    available = inventory_count >= quantity
                    
                    if not available:
                        all_available = False
                    
                    results.append({
                        "id": product_id,
                        "name": product.get("name"),
                        "requested": quantity,
                        "available": inventory_count,
                        "sufficient": available
                    })
                else:
                    results.append({
                        "id": product_id,
                        "error": "Product not found"
                    })
                    all_available = False
        
        return {
            "success": all_available,
            "items": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check inventory: {str(e)}"
        )

# Admin customers page
@app.get("/admin/customers", response_class=HTMLResponse)
async def admin_customers_page(request: Request):
    try:
        admin_email = await verify_admin_token(request)
        return templates.TemplateResponse(
            "admin/customers.html", 
            {"request": request, "user_email": admin_email}
        )
    except HTTPException:
        return RedirectResponse(url="/admin/login")
# Verify payment endpoint@app.post("/api/verify-payment")
# Verify payment endpoint
@app.post("/api/verify-payment")
async def verify_payment(payment_data: dict):
    """Verify Razorpay payment signature - simplified version"""
    try:
        order_id = payment_data.get("razorpay_order_id")
        payment_id = payment_data.get("razorpay_payment_id")
        signature = payment_data.get("razorpay_signature")
        wearxture_order_id = payment_data.get("order_id")
        is_cod = payment_data.get("is_cod", False)
        
        print(f"🔍 Verifying payment for order {wearxture_order_id}, COD: {is_cod}")
        
        # Demo mode handling
        if payment_data.get("demo_mode"):
            print("🎭 Processing demo mode payment...")
            
            order = get_order(wearxture_order_id)
            
            if order:
                update_data = {
                    "payment_status": "cod_fee_paid" if is_cod else "completed",
                    "razorpay_payment_id": "DEMO_PAYMENT_ID"
                }
                
                if is_cod:
                    update_data["cod_status"] = "fee_paid"
                    update_data["order_status"] = "confirmed"
                else:
                    update_data["order_status"] = "confirmed"
                
                updated_order = update_order_payment_status(wearxture_order_id, update_data)
                
                if updated_order:
                    # Send payment confirmation email
                    try:
                        print("📧 Sending payment confirmation email...")
                        from db.email_service import send_order_confirmation_email
                        email_sent = send_order_confirmation_email(updated_order)
                        if email_sent:
                            print(f"✅ Payment confirmation email sent for order {wearxture_order_id}")
                    except Exception as e:
                        print(f"⚠️ Error sending payment confirmation email: {e}")
                    
                    # NOTE: Removed auto-shipping code - Direct Ship will handle it automatically
                    print(f"✅ Order confirmed. Direct Ship will handle shipping automatically.")
                
                return {
                    "success": True,
                    "demo": True,
                    "message": "Demo payment verified. Shipping will be handled automatically by Direct Ship.",
                    "is_cod": is_cod
                }
            
            return {"success": False, "message": "Order not found"}
        
        # Real payment verification
        print("💳 Processing real payment verification...")
        is_valid = verify_payment_signature(order_id, payment_id, signature)
        
        if is_valid:
            print("✅ Payment signature verified successfully")
            
            # Get payment details from Razorpay
            payment_details = get_payment_details(payment_id)
            
            # Get order from database
            order = get_order(wearxture_order_id)
            
            if order:
                update_data = {
                    "payment_status": "cod_fee_paid" if is_cod else "completed",
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": signature
                }
                
                if is_cod:
                    update_data["cod_status"] = "fee_paid"
                    update_data["order_status"] = "confirmed"
                else:
                    update_data["order_status"] = "confirmed"
                
                updated_order = update_order_payment_status(wearxture_order_id, update_data)
                
                if updated_order:
                    # Send payment confirmation email
                    try:
                        print("📧 Sending payment confirmation email...")
                        from db.email_service import send_order_confirmation_email
                        email_sent = send_order_confirmation_email(updated_order)
                        if email_sent:
                            print(f"✅ Payment confirmation email sent for order {wearxture_order_id}")
                    except Exception as e:
                        print(f"⚠️ Error sending payment confirmation email: {e}")
                    
                    # NOTE: Removed auto-shipping code - Direct Ship will handle it automatically
                    print(f"✅ Payment confirmed. Direct Ship will automatically process shipping within a few minutes.")
                    
                    return {
                        "success": True,
                        "payment_id": payment_id,
                        "status": payment_details.get("status") if payment_details else "captured",
                        "message": "COD fee paid successfully. Shipping will be processed automatically." if is_cod else "Payment verified successfully. Shipping will be processed automatically.",
                        "is_cod": is_cod
                    }
                else:
                    return {"success": False, "message": "Failed to update order status"}
            else:
                return {"success": False, "message": "Order not found"}
        else:
            print("❌ Payment signature verification failed")
            return {"success": False, "message": "Payment verification failed"}
            
    except Exception as e:
        print(f"❌ Payment verification error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification failed: {str(e)}"
        )

app.post("/api/orders/{order_id}/email-invoice")
async def email_order_invoice(
    order_id: str,
    request: Request
):
    """Email invoice PDF for an order to the customer"""
    try:
        # Get order from database
        order = get_order(order_id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Verify that the requesting user owns this order
        token = request.cookies.get("user_access_token")
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        # Decode the JWT token to get user info
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_email = payload.get("sub")
        
        # Verify ownership
        if order.get("user_email") != user_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Generate PDF
        from db.order_management import generate_invoice_pdf
        pdf_data = generate_invoice_pdf(order)
        
        # Send email with invoice
        from db.email_service import send_invoice_email
        email_sent = send_invoice_email(order, pdf_data)
        
        if email_sent:
            return {"success": True, "message": "Invoice sent to your email"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send invoice email"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send invoice: {str(e)}"
        )
# Order confirmation page
@app.get("/order-confirmation", response_class=HTMLResponse)
async def order_confirmation_page(request: Request):
    """Minimal order confirmation page"""
    return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Order Confirmed - WEARXTURE</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600&display=swap');
                
                :root {
                    --primary-color: #e25822;
                    --success-color: #28a745;
                    --text-color: #333;
                    --light-text: #666;
                    --font-body: 'Poppins', sans-serif;
                }
                
                body {
                    font-family: var(--font-body);
                    background-color: #f8f9fa;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                }
                
                .confirmation-container {
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
                    padding: 32px 24px;
                    max-width: 400px;
                    width: 100%;
                    text-align: center;
                    animation: fadeIn 0.5s ease;
                }
                
                @keyframes fadeIn {
                    from {
                        opacity: 0;
                        transform: translateY(10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                .success-icon {
                    width: 56px;
                    height: 56px;
                    background: rgba(40, 167, 69, 0.1);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 20px;
                    animation: checkmark 0.5s ease 0.1s both;
                }
                
                .success-icon i {
                    color: var(--success-color);
                    font-size: 28px;
                }
                
                @keyframes checkmark {
                    0% {
                        transform: scale(0.8);
                        opacity: 0;
                    }
                    100% {
                        transform: scale(1);
                        opacity: 1;
                    }
                }
                
                h1 {
                    font-size: 24px;
                    font-weight: 600;
                    color: var(--text-color);
                    margin: 0 0 8px 0;
                }
                
                .order-message {
                    color: var(--light-text);
                    font-size: 14px;
                    line-height: 1.5;
                    margin-bottom: 28px;
                }
                
                .order-number {
                    font-size: 14px;
                    color: var(--text-color);
                    margin-bottom: 32px;
                    font-weight: 500;
                }
                
                .order-number span {
                    color: var(--primary-color);
                }
                
                .actions {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }
                
                .btn {
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 500;
                    text-decoration: none;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    border: none;
                    display: inline-block;
                }
                
                .btn-primary {
                    background: var(--primary-color);
                    color: white;
                }
                
                .btn-primary:hover {
                    background: #c24d1e;
                    transform: translateY(-1px);
                }
                
                .btn-secondary {
                    background: white;
                    color: var(--text-color);
                    border: 1px solid #e0e0e0;
                }
                
                .btn-secondary:hover {
                    background: #f8f9fa;
                }
                
                .email-note {
                    margin-top: 24px;
                    padding-top: 24px;
                    border-top: 1px solid #eee;
                    font-size: 13px;
                    color: var(--light-text);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                }
                
                .email-note i {
                    color: #3498db;
                    font-size: 16px;
                }
                
                @media (max-width: 480px) {
                    body {
                        padding: 16px;
                    }
                    
                    .confirmation-container {
                        padding: 24px 20px;
                    }
                    
                    h1 {
                        font-size: 22px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="confirmation-container">
                <div class="success-icon">
                    <i class="fas fa-check"></i>
                </div>
                
                <h1>Order Confirmed</h1>
                
                <p class="order-message">
                    Thank you for your purchase. We'll send you a confirmation email shortly.
                </p>
                
                <div class="order-number">
                    Order: <span>#ORD20250117093412</span>
                </div>
                
                <div class="actions">
                    <a href="/" class="btn btn-primary">Continue Shopping</a>
                    <a href="/orders" class="btn btn-secondary">View Orders</a>
                </div>
                
                <div class="email-note">
                    <i class="fas fa-envelope"></i>
                    Check your email for details
                </div>
            </div>
        </body>
        </html>
    """)
# # Order confirmation page (placeholder)
# @app.get("/order-confirmation", response_class=HTMLResponse)
# async def order_confirmation_page(request: Request):
#     """Order confirmation page"""
#     # In a real app, this would show order details
#     return HTMLResponse("""
#         <!DOCTYPE html>
#         <html>
#         <head>
#             <title>Order Confirmed - WEARXTURE</title>
#             <style>
#                 body {
#                     font-family: Arial, sans-serif;
#                     text-align: center;
#                     padding: 50px;
#                 }
#                 .success-icon {
#                     color: #28a745;
#                     font-size: 72px;
#                     margin-bottom: 20px;
#                 }
#                 h1 {
#                     color: #333;
#                     margin-bottom: 10px;
#                 }
#                 p {
#                     color: #666;
#                     margin-bottom: 30px;
#                 }
#                 .btn {
#                     background: #e25822;
#                     color: white;
#                     padding: 12px 30px;
#                     text-decoration: none;
#                     border-radius: 5px;
#                     display: inline-block;
#                 }
#                 .btn:hover {
#                     background: #c24d1e;
#                 }
#             </style>
#         </head>
#         <body>
#             <div class="success-icon">✓</div>
#             <h1>Order Confirmed!</h1>
#             <p>Thank you for your order. We'll send you a confirmation email shortly.</p>
#             <a href="/" class="btn">Continue Shopping</a>
#         </body>
#         </html>
#     """)
    

# User orders page
@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    """Display user orders page"""
    return templates.TemplateResponse("orders.html", {"request": request})

# Helper for converting Supabase data to Pydantic models
def product_from_db(db_product: Dict[str, Any]) -> ProductResponse:
    """Convert a database product to a ProductResponse model with proper parsing"""
    # Extract category name if available
    category_name = None
    if "categories" in db_product and db_product["categories"]:
        category_name = db_product["categories"]["name"]
    
    # Parse attributes from JSON string if needed
    attributes = db_product.get("attributes", {})
    if isinstance(attributes, str):
        try:
            import json
            attributes = json.loads(attributes)
        except json.JSONDecodeError:
            print(f"Error decoding JSON attributes: {attributes}")
            attributes = {}
    
    # Extract additional images from attributes
    additional_images = []
    if isinstance(attributes, dict) and 'additional_images' in attributes:
        additional_images = attributes.get('additional_images', [])
    
    # Parse tags from JSON string or handle as array
    tags = db_product.get("tags", [])
    if isinstance(tags, str):
        try:
            import json
            tags = json.loads(tags)
        except json.JSONDecodeError:
            # If not valid JSON, try comma-separated
            tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    return ProductResponse(
        id=db_product["id"],
        name=db_product["name"],
        description=db_product["description"],
        price=db_product["base_price"],
        sale_price=db_product["sale_price"],
        category_id=db_product["category_id"],
        category_name=category_name,
        image_url=db_product["image_url"],
        in_stock=db_product["in_stock"],
        sku=db_product["sku"],
        tags=tags,
        attributes=attributes,
        created_at=db_product["created_at"],
        updated_at=db_product["updated_at"],
        additional_images=additional_images,
        filter=db_product.get("filter", "all"),
        inventory_count=db_product.get("inventory_count", 0)  # Add this line
    )


def category_from_db(db_category: Dict[str, Any]) -> CategoryResponse:
    """Convert a database category to a CategoryResponse model"""
    return CategoryResponse(
        id=db_category["id"],
        name=db_category["name"],
        description=db_category["description"],
        parent_id=db_category["parent_id"],
        image_url=db_category["image_url"],
        cover_image_url=db_category.get("cover_image_url"),  # Use get() to handle missing field
        created_at=db_category["created_at"],
        updated_at=db_category["updated_at"],
        filter=db_category.get("filter", "all")  # Add this line
    )


def reel_from_db(db_reel: Dict[str, Any]) -> ReelResponse:
    """Convert a database reel to a ReelResponse model"""
    # Extract category name if available
    category_name = None
    if "categories" in db_reel and db_reel["categories"]:
        category_name = db_reel["categories"]["name"]
    
    return ReelResponse(
        id=db_reel["id"],
        title=db_reel["title"],
        description=db_reel["description"],
        category_id=db_reel["category_id"],
        category_name=category_name,
        product_url=db_reel["product_url"],
        video_url=db_reel["video_url"],
        is_active=db_reel["is_active"],
        display_order=db_reel["display_order"],
        created_at=db_reel["created_at"],
        updated_at=db_reel["updated_at"]
    )

# ========= Authentication Functions =========

# Verify the admin token from cookie
async def verify_admin_token(request: Request):
    token = request.cookies.get("admin_access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        return email
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

# ========= Public API Routes =========

# Root endpoint - render HTML template
# Root endpoint - render HTML template
@app.get("/", response_class=HTMLResponse, tags=["Pages"])
async def home_page(request: Request):
    # Get products and categories from database
    db_products = get_all_products()
    products = [product_from_db(p) for p in db_products]
    
    db_categories = get_all_categories()
    categories = [category_from_db(c) for c in db_categories]
    
    # Get featured or new products (limit to 4 for slider)
    # Sort by created_at to get newest first
    new_products = sorted(products, key=lambda x: x.created_at, reverse=True)[:4]
    
    # Get active reels
    db_reels = get_active_reels()
    reels = [reel_from_db(r) for r in db_reels]
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "products": products,
            "categories": categories,
            "new_products": new_products,
            "reels": reels
        }
    )

# API welcome
@app.get("/api", tags=["API"])
async def read_root():
    return {"message": "Welcome to WEARXTURE API"}

# Get all products
@app.get("/api/products", response_model=List[ProductResponse], tags=["API"])
async def get_products():
    db_products = get_all_products()
    return [product_from_db(p) for p in db_products]

# Get a specific product by ID
@app.get("/api/products/{product_id}", response_model=ProductResponse, tags=["API"])
async def get_product_by_id(product_id: int):
    db_product = get_product(product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_from_db(db_product)

# Get all categories
@app.get("/api/categories", response_model=List[CategoryResponse], tags=["API"])
async def get_categories():
    db_categories = get_all_categories()
    return [category_from_db(c) for c in db_categories]

# Get a specific category by ID
@app.get("/api/categories/{category_id}", response_model=CategoryResponse, tags=["API"])
async def get_category_by_id(category_id: int):
    db_category = get_category(category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category_from_db(db_category)

# ========= Admin Authentication Routes =========

# Admin login page
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})

# Admin login handler
# Admin login handler - replace the existing @app.post("/admin/login") function with this
@app.post("/admin/login")
async def login(username: str = Form(...), password: str = Form(...)):
    # Hardcoded admin credentials for development
    ADMIN_EMAIL = "sohil19158912@gmail.com"
    ADMIN_PASSWORD = "Faraz@1915"
    
    # Simple hardcoded credential check
    if username != ADMIN_EMAIL or password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token with expiry
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expires = datetime.utcnow() + access_token_expires
    
    # Create the JWT token payload
    to_encode = {
        "sub": username,
        "exp": expires
    }
    
    # Encode the JWT
    access_token = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    
    # Set JWT as a cookie and redirect
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    
    return response

# Admin logout
@app.get("/admin/logout")
async def logout():
    response = RedirectResponse(url="/admin/login")
    response.delete_cookie(key="admin_access_token")
    return response


# Add this import at the top of main.py
from fastapi.responses import FileResponse

# Add this endpoint in main.py after the other order endpoints
@app.get("/admin/api/orders/{order_id}/invoice")
async def download_order_invoice(
    order_id: str,
    admin_email: str = Depends(verify_admin_token)
):
    """Download invoice PDF for an order"""
    try:
        # Get order from database
        order = get_order(order_id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Import the generate_invoice_pdf function
        from db.order_management import generate_invoice_pdf
        
        # Generate PDF
        pdf_data = generate_invoice_pdf(order)
        
        # Create response with PDF
        response = Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=WEARXTURE_Invoice_{order_id}.pdf"
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate invoice: {str(e)}"
        )
# ========= Admin Page Routes =========

    # Admin dashboard
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
        try:
            email = await verify_admin_token(request)
            
            # Get counts for dashboard
            product_count = len(get_all_products())
            category_count = len(get_all_categories())
        # Get unique customers from orders
            from db.order_management import get_all_orders
            orders = get_all_orders()
            unique_customers = len(set(order.get('user_email') for order in orders))
            
                
            return templates.TemplateResponse(
                "admin/dashboard.html", 
                {
                    "request": request, 
                    "user_email": email,
                    "product_count": product_count,
                    "category_count": category_count,
                    "customer_count": unique_customers

                }
            )
        except HTTPException:
            return RedirectResponse(url="/admin/login")


# Admin orders page - this is already added to your main.py
@app.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders_page(request: Request):
    try:
        admin_email = await verify_admin_token(request)
        return templates.TemplateResponse(
            "admin/orders.html", 
            {"request": request, "user_email": admin_email}
        )
    except HTTPException:
        return RedirectResponse(url="/admin/login")
# 1. Get all orders (admin) 
@app.get("/admin/api/orders")
async def get_admin_orders(admin_email: str = Depends(verify_admin_token)):
    """Get all orders for admin view"""
    try:
        orders = get_all_orders()
        
        # Sort by created_at descending (newest first)
        orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch orders: {str(e)}"
        )

# 2. Get specific order details (admin)
@app.get("/admin/api/orders/{order_id}")
async def get_admin_order_details(order_id: str, admin_email: str = Depends(verify_admin_token)):
    """Get detailed information about a specific order"""
    try:
        order = get_order(order_id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        return order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch order details: {str(e)}"
        )

# 3. Update order status (admin)
# Update the existing update_admin_order_status function
@app.put("/admin/api/orders/{order_id}/status")
async def update_admin_order_status(
    order_id: str,
    status_update: dict,
    admin_email: str = Depends(verify_admin_token)
):
    """Update the status of an order with inventory management and email notification"""
    try:
        new_status = status_update.get("status")
        notes = status_update.get("notes", "")
        
        if not new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status is required"
            )
        
        # Validate status
        valid_statuses = ["pending", "confirmed", "processing", "dispatched", "delivered", "cancelled"]
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Get current order to access old status
        current_order = get_order(order_id)
        if not current_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
            
        old_status = current_order.get("order_status", "unknown")
        
        # Skip update if status hasn't changed
        if old_status == new_status:
            return {
                "success": True,
                "message": f"Order status already set to {new_status}",
                "order": current_order
            }
        
        # Update the order status with inventory management
        updated_order = update_order_status(order_id, new_status, notes)
        
        if not updated_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found or update failed"
            )
        
        # Send status update email to customer
        try:
            from db.email_service import send_order_status_update_email
            email_sent = send_order_status_update_email(
                updated_order, 
                old_status, 
                new_status
            )
            if email_sent:
                print(f"Status update email sent for order {order_id}: {old_status} -> {new_status}")
            else:
                print(f"Failed to send status update email for order {order_id}")
        except Exception as e:
            # Don't let email errors affect order processing
            print(f"Error sending status update email: {e}")
            import traceback
            traceback.print_exc()
        
        # Return success response
        return {
            "success": True,
            "order": updated_order,
            "message": f"Order status updated to {new_status}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating order status: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order status: {str(e)}"
        )
# Admin products page
@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products_page(request: Request):
    try:
        await verify_admin_token(request)
        
        # Get products from database
        db_products = get_all_products()
        products = [product_from_db(p) for p in db_products]
        
        # Get categories for the dropdown
        db_categories = get_all_categories()
        categories = [category_from_db(c) for c in db_categories]
        
        return templates.TemplateResponse(
            "admin/products.html", 
            {"request": request, "products": products, "categories": categories}
        )
    except HTTPException:
        return RedirectResponse(url="/admin/login")

# Admin categories page
@app.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories_page(request: Request):
    try:
        await verify_admin_token(request)
        
        # Get categories from database
        db_categories = get_all_categories()
        categories = [category_from_db(c) for c in db_categories]
        
        return templates.TemplateResponse(
            "admin/categories.html", 
            {"request": request, "categories": categories}
        )
    except HTTPException:
        return RedirectResponse(url="/admin/login")

# Admin reels page
@app.get("/admin/reels", response_class=HTMLResponse)
async def admin_reels_page(request: Request):
    try:
        await verify_admin_token(request)
        
        # Get reels from database
        db_reels = get_all_reels()
        reels = [reel_from_db(r) for r in db_reels]
        
        # Get categories for the dropdown
        db_categories = get_all_categories()
        categories = [category_from_db(c) for c in db_categories]
        
        return templates.TemplateResponse(
            "admin/reels.html", 
            {"request": request, "reels": reels, "categories": categories}
        )
    except HTTPException:
        return RedirectResponse(url="/admin/login")



# Get all reels
@app.get("/admin/api/reels", response_model=List[ReelResponse])
async def get_admin_reels(admin_email: str = Depends(verify_admin_token)):
    db_reels = get_all_reels()
    return [reel_from_db(r) for r in db_reels]

# Get a specific reel by ID
@app.get("/admin/api/reels/{reel_id}", response_model=ReelResponse)
async def get_admin_reel(reel_id: int, admin_email: str = Depends(verify_admin_token)):
    db_reel = get_reel(reel_id)
    if not db_reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    return reel_from_db(db_reel)

# Create a new reel
@app.post("/admin/api/reels", response_model=ReelResponse)
async def create_admin_reel(
    reel: ReelCreate,
    admin_email: str = Depends(verify_admin_token)
):
    # Prepare reel data for database
    reel_data = {
        "title": reel.title,
        "description": reel.description,
        "category_id": reel.category_id,
        "product_url": reel.product_url,
        "is_active": reel.is_active,
        "display_order": reel.display_order
    }
    
    # Create in database
    db_reel = create_reel(reel_data)
    if not db_reel:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create reel"
        )
    
    # Important: Fetch the reel again to get the full data including category name
    created_reel = get_reel(db_reel["id"])
    if not created_reel:
        raise HTTPException(status_code=404, detail="Created reel not found")
    
    return reel_from_db(created_reel)

# Update a reel
@app.put("/admin/api/reels/{reel_id}", response_model=ReelResponse)
async def update_admin_reel(
    reel_id: int,
    reel: ReelUpdate,
    admin_email: str = Depends(verify_admin_token)
):
    # Check if reel exists
    existing_reel = get_reel(reel_id)
    if not existing_reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    # Prepare reel data for database
    reel_data = {
        "title": reel.title,
        "description": reel.description,
        "category_id": reel.category_id,
        "product_url": reel.product_url,
        "is_active": reel.is_active,
        "display_order": reel.display_order
    }
    
    # Update in database
    db_reel = update_reel(reel_id, reel_data)
    if not db_reel:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update reel"
        )
    
    # Important: Fetch the reel again to get the full data including category name
    updated_reel = get_reel(reel_id)
    if not updated_reel:
        raise HTTPException(status_code=404, detail="Updated reel not found")
    
    return reel_from_db(updated_reel)

# Delete a reel
@app.delete("/admin/api/reels/{reel_id}")
async def delete_admin_reel(
    reel_id: int,
    admin_email: str = Depends(verify_admin_token)
):
    # Check if reel exists
    existing_reel = get_reel(reel_id)
    if not existing_reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    # Delete from database
    success = delete_reel(reel_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete reel"
        )
    
    return {"success": True}

# Upload reel video
# Upload reel video
@app.post("/admin/api/upload/reel-video")
async def upload_admin_reel_video(
    reel_id: int = Form(...),
    file: UploadFile = File(...),
    admin_email: str = Depends(verify_admin_token)
):
    # Check if reel exists
    existing_reel = get_reel(reel_id)
    if not existing_reel:
        raise HTTPException(status_code=404, detail="Reel not found")
    
    try:
        print(f"Starting upload for reel {reel_id}: {file.filename}")
        
        # Read file content
        file_content = await file.read()
        print(f"File read successfully, size: {len(file_content)} bytes")
        
        # Upload to Supabase Storage
        video_url = upload_reel_video(file_content, file.filename)
        print(f"Upload function returned: {video_url}")
        
        if not video_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload video to storage"
            )
        
        print(f"Attempting to update reel {reel_id} with video URL: {video_url}")
        
        # Update reel with new video URL
        result = update_reel(reel_id, {"video_url": video_url})
        print(f"Update result: {result}")
        
        if result:
            return {"success": True, "video_url": video_url}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update reel with video URL"
            )
    except Exception as e:
        print(f"Exception during upload: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading video: {str(e)}"
        )
    finally:
        await file.close()

# Get a specific category by ID
@app.get("/api/categories/{category_id}", response_model=CategoryResponse, tags=["API"])
async def get_category_by_id(category_id: int):
    db_category = get_category(category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category_from_db(db_category)

# Get active reels for frontend display
@app.get("/api/reels", response_model=List[ReelResponse], tags=["API"])
async def get_reels():
    db_reels = get_active_reels()
    return [reel_from_db(r) for r in db_reels]


# ========= Admin API Routes =========

# Create a new product
@app.post("/admin/api/products", response_model=ProductResponse)
async def create_admin_product(
    product: ProductCreate, 
    admin_email: str = Depends(verify_admin_token)
):
    # Get the category to inherit its filter
    category = get_category(product.category_id)
    filter_value = category.get("filter", "all") if category else "all"
    
    # Prepare product data for database
    product_data = {
        "name": product.name,
        "description": product.description,
        "base_price": product.price,
        "sale_price": product.sale_price,
        "category_id": product.category_id,
        "in_stock": product.in_stock,
        "sku": product.sku,
        "tags": product.tags,
        "attributes": product.attributes,
        "filter": filter_value,
        "inventory_count": product.inventory_count,  # Add this line
        "image_url": "/static/images/products/placeholder.jpg"  # Default image
    }
    
    # Create in database
    db_product = create_product(product_data)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product"
        )
    
    return product_from_db(db_product)

# Update a product
@app.put("/admin/api/products/{product_id}", response_model=ProductResponse)
async def update_admin_product(
    product_id: int,
    product: ProductUpdate,
    admin_email: str = Depends(verify_admin_token)
):
    # Check if product exists
    existing_product = get_product(product_id)
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # If category changed, get new filter
    filter_value = existing_product.get("filter", "all")
    if product.category_id != existing_product["category_id"]:
        category = get_category(product.category_id)
        filter_value = category.get("filter", "all") if category else "all"
    
    # Prepare product data for database
# Prepare product data for database
    product_data = {
        "name": product.name,
        "description": product.description,
        "base_price": product.price,
        "sale_price": product.sale_price,
        "category_id": product.category_id,
        "in_stock": product.in_stock,
        "sku": product.sku,
        "tags": product.tags,
        "attributes": product.attributes,
        "filter": filter_value,
        "inventory_count": product.inventory_count  # Add this line
    }
    
    # Update in database
    db_product = update_product(product_id, product_data)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product"
        )
    
    # Important: Fetch the product again to get the full data including category name
    updated_product = get_product(product_id)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Updated product not found")
    
    # Return the complete updated product
    return product_from_db(updated_product)

# Delete a product
@app.delete("/admin/api/products/{product_id}")
async def delete_admin_product(
    product_id: int,
    admin_email: str = Depends(verify_admin_token)
):
    # Check if product exists
    existing_product = get_product(product_id)
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Delete from database
    success = delete_product(product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product"
        )
    
    return {"success": True}

# Create a new category
@app.post("/admin/api/categories", response_model=CategoryResponse)
async def create_admin_category(
    category: CategoryCreate,
    admin_email: str = Depends(verify_admin_token)
):
    # Prepare category data for database
    category_data = {
        "name": category.name,
        "description": category.description,
        "parent_id": category.parent_id,
        "filter": category.filter,  # Add this line
        "image_url": "/static/images/categories/placeholder.jpg"  # Default image
    }
    
    # Create in database
    db_category = create_category(category_data)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category"
        )
    
    return category_from_db(db_category)

# Replace both instances of the update_admin_category function with this single version:
# Get a specific category by ID for admin
@app.get("/admin/api/categories/{category_id}", response_model=CategoryResponse)
async def get_admin_category_by_id(
    category_id: int,
    admin_email: str = Depends(verify_admin_token)
):
    db_category = get_category(category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category_from_db(db_category)

    
@app.put("/admin/api/categories/{category_id}", response_model=CategoryResponse)
async def update_admin_category(
    category_id: int,
    category: CategoryUpdate,
    admin_email: str = Depends(verify_admin_token)
):
    # Check if category exists
    existing_category = get_category(category_id)
    if not existing_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # If category changed, get new filter
    filter_value = category.filter if hasattr(category, "filter") and category.filter else "all"
    
    # Prepare category data for database
    category_data = {
        "name": category.name,
        "description": category.description,
        "parent_id": category.parent_id,
        "filter": filter_value
    }
    
    # Update in database
    db_category = update_category(category_id, category_data)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )
    
    return category_from_db(db_category)


# Add this route to main.py

# Dynamic version - fetches categories from database

# Add this to your main.py file

@app.get("/collections", response_class=HTMLResponse, tags=["Pages"])
async def collections_page(request: Request):
    """
    Render the collections page with categories from database
    Same approach as the index page
    """
    # Get categories from database
    db_categories = get_all_categories()
    categories = [category_from_db(c) for c in db_categories]
    
    return templates.TemplateResponse(
        "collections.html", 
        {
            "request": request, 
            "categories": categories
        }
    )

# Delete a category
@app.delete("/admin/api/categories/{category_id}")
async def delete_admin_category(
    category_id: int,
    admin_email: str = Depends(verify_admin_token)
):
    # Check if category exists
    existing_category = get_category(category_id)
    if not existing_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Delete from database
    success = delete_category(category_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category"
        )
    
    return {"success": True}


@app.get("/api/user/orders")
async def get_user_orders_endpoint(request: Request):
    """Get orders for the authenticated user"""
    try:
        # Get user from token
        token = request.cookies.get("user_access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user = get_current_user_simple(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get orders for this user
        from db.order_management import get_user_orders
        orders = get_user_orders(user['email'])
        
        return orders if orders else []
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching user orders: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch orders")

# @app.get("/order/{order_id}", response_class=HTMLResponse)
# async def order_detail_page(request: Request, order_id: str):
#     """Display individual order details"""
#     return templates.TemplateResponse("order_detail.html", {"request": request, "order_id": order_id})

@app.get("/order/{order_id}", response_class=HTMLResponse)
async def order_detail_page(request: Request, order_id: str):
    """Display individual order details page"""
    try:
        # Check if user is authenticated
        token = request.cookies.get("user_access_token")
        if not token:
            return RedirectResponse(url="/login")
        
        user = get_current_user_simple(token)
        if not user:
            return RedirectResponse(url="/login")
        
        return templates.TemplateResponse("order_detail.html", {
            "request": request, 
            "order_id": order_id,
            "user": user
        })
        
    except Exception as e:
        print(f"Order detail page error: {e}")
        return RedirectResponse(url="/profile")
# API endpoint to get single order details
@app.get("/api/orders/{order_id}")
async def get_order_details(order_id: str, request: Request):
    """Get details for a specific order"""
    try:
        # Check if user is authenticated
        token = request.cookies.get("user_access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user = get_current_user_simple(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get order from database
        from db.order_management import get_order
        order = get_order(order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Verify the order belongs to this user
        if order.get("user_email") != user['email']:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get order details error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to fetch order")
# ========= File Upload Routes =========
# Upload product image
@app.post("/admin/api/upload/product-image")
async def upload_admin_product_image(
    product_id: int = Form(...),
    file: UploadFile = File(...),
    admin_email: str = Depends(verify_admin_token)
):
    # Check if product exists
    existing_product = get_product(product_id)
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        print(f"Uploading image for product {product_id}: {file.filename}")
        # Read file content
        file_content = await file.read()
        
        # Upload to Supabase Storage
        image_url = upload_product_image(file_content, file.filename)
        print(f"Upload result: {image_url}")
        
        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image"
            )
        
        # Update product with new image URL
        result = update_product(product_id, {"image_url": image_url})
        print(f"Product update result: {result}")
        
        return {"success": True, "image_url": image_url}
    except Exception as e:
        print(f"Exception during upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        )
    finally:
        await file.close()

# Upload category image
@app.post("/admin/api/upload/category-image")
async def upload_admin_category_image(
    category_id: int = Form(...),
    file: UploadFile = File(...),
    admin_email: str = Depends(verify_admin_token)
):
    # Check if category exists
    existing_category = get_category(category_id)
    if not existing_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload to Supabase Storage
        image_url = upload_category_image(file_content, file.filename)
        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image"
            )
        
        # Update category with new image URL
        update_category(category_id, {"image_url": image_url})
        
        return {"success": True, "image_url": image_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        )
    finally:
        await file.close()

# Multiple product images upload
@app.post("/admin/api/upload/product-images")
async def upload_multiple_product_images(
    product_id: int = Form(...),
    files: List[UploadFile] = File(...),
    admin_email: str = Depends(verify_admin_token)
):
    # Check if product exists
    existing_product = get_product(product_id)
    if not existing_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    uploaded_urls = []
    
    try:
        for file in files:
            # Read file content
            file_content = await file.read()
            
            # Upload to Supabase Storage
            image_url = upload_product_image(file_content, file.filename)
            if image_url:
                uploaded_urls.append(image_url)
            
            await file.close()
        
        if uploaded_urls:
            # Update product with all images using the new function
            result = update_product_images(product_id, uploaded_urls)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update product images"
                )
            
            # Get the updated product to return
            updated_product = get_product(product_id)
            
        return {
            "success": True, 
            "image_urls": uploaded_urls,
            "main_image": uploaded_urls[0] if uploaded_urls else None,
            "additional_images": uploaded_urls[1:] if len(uploaded_urls) > 1 else []
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading images: {str(e)}"
        )

# ========= Debug Routes =========

# Debug endpoint to check routes
@app.get("/debug/routes")
async def debug_routes():
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "name": route.name,
            "methods": route.methods
        })
    return routes


@app.get("/admin/test-storage")
async def test_storage():
    """Test endpoint to verify Supabase storage is working"""
    try:
        # Create a simple test file
        test_content = b"This is a test file"
        test_filename = f"test-file-{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        
        # Try uploading to product-images bucket
        response = supabase.storage.from_("product-images").upload(
            path=test_filename,
            file=test_content,
            file_options={"content-type": "text/plain"}
        )
        
        # Get the URL
        if response:
            public_url = supabase.storage.from_("product-images").get_public_url(test_filename)
            return {
                "success": True, 
                "message": "Storage test successful", 
                "url": public_url,
                "response": response
            }
        else:
            return {
                "success": False,
                "message": "Upload succeeded but no response returned",
                "response": response
            }
    except Exception as e:
        return {
            "success": False, 
            "message": f"Storage test failed: {str(e)}",
            "error": repr(e)
        }

@app.get("/admin/api/products/{product_id}", response_model=ProductResponse)
async def get_admin_product_by_id(
    product_id: int,
    admin_email: str = Depends(verify_admin_token)
):
    db_product = get_product(product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_from_db(db_product)

# Category page
# Category page route
@app.get("/category/{category_id}", response_class=HTMLResponse, tags=["Pages"])
async def category_page(request: Request, category_id: int):
    """
    Render the category page with all products in that category
    """
    # Get category from database
    db_category = get_category(category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Convert to response model - this includes cover_image_url if available
    category = category_from_db(db_category)
    
    # Print debug info to verify cover_image_url is included
    print(f"Category data: {category}")
    
    # Get products from database for this specific category
    db_products = get_products_by_category(category_id)
    category_products = [product_from_db(p) for p in db_products]
    
    # Sort by newest first (created_at descending)
    category_products.sort(key=lambda x: x.created_at, reverse=True)
    
    # Get subcategories if any
    db_subcategories = get_subcategories(category_id)
    subcategories = [category_from_db(c) for c in db_subcategories]
    
    # Get parent category if this is a subcategory
    parent_category = None
    if category.parent_id:
        db_parent = get_category(category.parent_id)
        if db_parent:
            parent_category = category_from_db(db_parent)
    
    return templates.TemplateResponse(
        "category.html", 
        {
            "request": request, 
            "category": category,
            "category_products": category_products,
            "subcategories": subcategories,
            "parent_category": parent_category
        }
    )

# API endpoint to get products by category
@app.get("/api/categories/{category_id}/products", response_model=List[ProductResponse], tags=["API"])
async def get_products_by_category_id(category_id: int):
    """
    Get all products that belong to a specific category via API
    """
    # Check if category exists
    db_category = get_category(category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get products from database for this specific category
    db_products = get_products_by_category(category_id)
    
    # Convert to response model
    products = [product_from_db(p) for p in db_products]
    
    return products

@app.get("/products", response_class=HTMLResponse, tags=["Pages"])
async def all_products_page(request: Request):
    """
    Render the all products page with category filters
    """
    # Get all products
    db_products = get_all_products()
    products = [product_from_db(p) for p in db_products]
    
    # Sort by newest first (created_at descending)
    products.sort(key=lambda x: x.created_at, reverse=True)
    
    # Get all categories for the filter
    db_categories = get_all_categories()
    categories = [category_from_db(c) for c in db_categories]
    
    # Organize categories into parent and child categories
    parent_categories = [c for c in categories if c.parent_id is None]
    child_categories = [c for c in categories if c.parent_id is not None]
    
    return templates.TemplateResponse(
        "products.html",  # You'll need to create this template
        {
            "request": request,
            "products": products,
            "categories": categories,
            "parent_categories": parent_categories,
            "child_categories": child_categories
        }
    )

# Add this function to db/supabase_client.py to fetch related products

def get_related_products(product_id: int, category_id: int, limit: int = 4) -> List[Dict[str, Any]]:
    """
    Get related products based on category, excluding the current product
    """
    try:
        # First try to get products from the same category, excluding the current product
        response = supabase.table('products') \
            .select('*, categories(name)') \
            .eq('category_id', category_id) \
            .neq('id', product_id) \
            .limit(limit) \
            .execute()
        
        result = response.data
        
        # If we don't have enough related products, get some popular/recent products
        if len(result) < limit:
            needed = limit - len(result)
            existing_ids = [product_id] + [p['id'] for p in result]
            
            # Filter out already included products
            additional_response = supabase.table('products') \
                .select('*, categories(name)') \
                .not_in('id', existing_ids) \
                .limit(needed) \
                .execute()
            
            result.extend(additional_response.data)
        
        return result
    except Exception as e:
        print(f"Error getting related products for product {product_id}: {e}")
        return []

# Add this route to main.py

# This goes in your main.py file, inside the product detail route

@app.get("/product/{product_id}", response_class=HTMLResponse, tags=["Pages"])
async def product_detail_page(request: Request, product_id: int):
    """
    Render a simplified product detail page with only essential information
    """
    # Get the product from database
    db_product = get_product(product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = product_from_db(db_product)
    
    # Get the category
    category = None
    if product.category_id:
        db_category = get_category(product.category_id)
        if db_category:
            category = category_from_db(db_category)
    
    # Get related products
    db_related = get_related_products(product_id, product.category_id)
    related_products = [product_from_db(p) for p in db_related]
    
    # Extract additional images from attributes if they exist
    additional_images = []
    if hasattr(product, 'additional_images') and product.additional_images:
        additional_images = product.additional_images
    elif hasattr(product, 'attributes') and product.attributes and 'additional_images' in product.attributes:
        try:
            additional_images = product.attributes['additional_images']
        except (TypeError, KeyError):
            additional_images = []
    
    # Set up default colors if none are provided
    colors = []
    if hasattr(product, 'attributes') and product.attributes and 'colors' in product.attributes:
        colors = product.attributes.get('colors', [])
    
    # If colors are not in the right format or are empty, add some defaults
    if not colors:
        # Default colors based on different categories
        if category and category.name:
            if "saree" in category.name.lower() or "sarees" in category.name.lower():
                colors = [
                    {"name": "Red", "code": "#e74c3c"},
                    {"name": "Purple", "code": "#8e44ad"},
                    {"name": "Navy Blue", "code": "#2c3e50"}
                ]
            elif "lehenga" in category.name.lower():
                colors = [
                    {"name": "Maroon", "code": "#800000"},
                    {"name": "Gold", "code": "#ffd700"},
                    {"name": "Pink", "code": "#ff69b4"}
                ]
            elif "anarkali" in category.name.lower():
                colors = [
                    {"name": "Teal", "code": "#1abc9c"},
                    {"name": "Royal Blue", "code": "#3498db"},
                    {"name": "Coral", "code": "#ff7f50"}
                ]
            else:
                # Generic default colors
                colors = [
                    {"name": "Black", "code": "#000000"},
                    {"name": "Navy Blue", "code": "#2c3e50"},
                    {"name": "Olive Green", "code": "#556b2f"}
                ]
    
    # Create context with all template variables
    context = {
        "request": request,
        "product": product,
        "category": category,
        "related_products": related_products,
        "additional_images": additional_images,
        "colors": colors
    }
    
    return templates.TemplateResponse("product_detail.html", context)

# Upload category cover image
# Upload category cover image - FIXED VERSION
# Upload category cover image - ASYNC AWAIT VERSION
# Final version of Upload category cover image endpoint
@app.post("/admin/api/upload/category-cover-image")
async def upload_category_cover_image_endpoint(  # Changed function name to avoid confusion
    category_id: int = Form(...),
    file: UploadFile = File(...),
    admin_email: str = Depends(verify_admin_token)
):
    # Check if category exists
    existing_category = get_category(category_id)
    if not existing_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload to Supabase Storage
        # Make sure this is NOT an async function - it should return the URL directly, not a coroutine
        cover_image_url = upload_category_cover_image(file_content, file.filename)
        
        if not cover_image_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload cover image"
            )
        
        # DIRECT SUPABASE UPDATE - completely bypass any potential issues
        from db.supabase_client import supabase
        
        # Execute the update and capture the response
        update_response = supabase.table('categories').update({
            'cover_image_url': cover_image_url,
            'updated_at': datetime.now().isoformat()
        }).eq('id', category_id).execute()
        
        # Check that the update was successful
        if not update_response.data:
            print(f"Supabase update failed: {update_response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update category with cover image"
            )
            
        # Return a simple dictionary response
        return {
            "success": True, 
            "cover_image_url": cover_image_url
        }
        
    except Exception as e:
        print(f"Cover image upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Pass through HTTPException
        if isinstance(e, HTTPException):
            raise
            
        # Convert other exceptions to HTTPException
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing cover image: {str(e)}"
        )
    finally:
        await file.close()

@app.post("/admin/api/test-auto-shipping/{order_id}")
async def test_auto_shipping(
    order_id: str,
    admin_email: str = Depends(verify_admin_token)
):
    """Test automatic shipping for an existing order"""
    try:
        # Get order from database
        order = get_order(order_id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Test automatic shipping
        from db.shiprocket_client import create_automatic_shipping
        shipping_result = create_automatic_shipping(order)
        
        if shipping_result.get("success"):
            # Update order with shipping details
            shiprocket_info = {
                'shipment_id': shipping_result.get('shipment_id'),
                'awb_code': shipping_result.get('awb_code'),
                'courier_name': shipping_result.get('courier_name'),
                'tracking_url': shipping_result.get('tracking_url')
            }
            
            update_success = update_shiprocket_info(order_id, shiprocket_info)
            
            if update_success:
                # Update order status
                update_order_status(order_id, "dispatched", "Test shipping via admin panel")
                
            return {
                "success": True,
                "message": "Test shipping successful",
                "shipping_details": shipping_result
            }
        else:
            return {
                "success": False,
                "error": shipping_result.get("error"),
                "details": shipping_result
            }
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test shipping failed: {str(e)}"
        )



@app.post("/api/support/queries")
async def create_support_query_endpoint(query_data: SupportQueryCreate):
    """Create a new support query from customer"""
    try:
        # Convert Pydantic model to dict
        query_dict = {
            "query_type": query_data.query_type,
            "customer_email": query_data.customer_email,
            "customer_name": query_data.customer_name,
            "subject": query_data.subject,
            "message": query_data.message,
            "priority": query_data.priority
        }
        
        # Create query in database
        created_query = create_support_query(query_dict)
        
        if not created_query:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create support query"
            )
        
        # Send notification email to admin (optional - implement later)
        try:
            # You can add email notification logic here
            print(f"📧 New support query created: {created_query.get('id')}")
        except Exception as e:
            print(f"⚠️ Failed to send notification email: {e}")
        
        return {
            "success": True,
            "message": "Support query submitted successfully. We'll get back to you soon!",
            "query_id": created_query.get('id')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating support query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit support query"
        )

@app.get("/api/support/queries/my-queries")
async def get_my_support_queries(request: Request):
    """Get support queries for the authenticated user"""
    try:
        # Get user from token
        token = request.cookies.get("user_access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user = get_current_user_simple(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get queries for this user
        queries = get_customer_support_queries(user['email'])
        
        return {
            "success": True,
            "queries": queries
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching user support queries: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch queries")

# ========= Admin Support Query Routes =========

@app.get("/admin/support", response_class=HTMLResponse)
async def admin_support_page(request: Request):
    """Admin support queries management page"""
    try:
        admin_email = await verify_admin_token(request)
        return templates.TemplateResponse(
            "admin/support.html", 
            {"request": request, "user_email": admin_email}
        )
    except HTTPException:
        return RedirectResponse(url="/admin/login")

@app.get("/admin/api/support/queries")
async def get_admin_support_queries(
    status_filter: Optional[str] = None,
    admin_email: str = Depends(verify_admin_token)
):
    """Get all support queries for admin view"""
    try:
        if status_filter:
            queries = get_support_queries_by_status(status_filter)
        else:
            queries = get_all_support_queries()
        
        return {
            "success": True,
            "queries": queries
        }
        
    except Exception as e:
        print(f"Error fetching admin support queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch support queries"
        )

# Update the valid statuses in your main.py API endpoint
@app.get("/admin/api/support/queries/{query_id}")
async def get_admin_support_query_details(
    query_id: int,
    admin_email: str = Depends(verify_admin_token)
):
    """Get detailed information about a specific support query"""
    try:
        print(f"🔍 Getting query details for ID: {query_id}")
        
        query = get_support_query(query_id)
        
        if not query:
            print(f"❌ Query {query_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Support query not found"
            )
        
        print(f"✅ Query {query_id} found successfully")
        return {
            "success": True,
            "query": query
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching support query details: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch query details: {str(e)}"
        )


@app.put("/admin/api/support/queries/{query_id}")
async def update_admin_support_query(
    query_id: int,
    update_data: SupportQueryUpdate,
    admin_email: str = Depends(verify_admin_token)
):
    """Update support query status and admin notes"""
    try:
        # Updated valid statuses to include "replied_on_email"
        valid_statuses = ["open", "in_progress", "replied_on_email", "resolved", "closed"]
        if update_data.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Update query
        updated_query = update_support_query_status(
            query_id, 
            update_data.status, 
            update_data.admin_notes
        )
        
        if not updated_query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Support query not found or update failed"
            )
        
        return {
            "success": True,
            "message": f"Support query updated to {update_data.status}",
            "query": updated_query
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating support query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update support query"
        )

@app.put("/admin/api/support/queries/{query_id}")
async def update_admin_support_query(
    query_id: int,
    update_data: SupportQueryUpdate,
    admin_email: str = Depends(verify_admin_token)
):
    """Update support query status and admin notes"""
    try:
        # Validate status
        valid_statuses = ["open", "in_progress", "resolved", "closed"]
        if update_data.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Update query
        updated_query = update_support_query_status(
            query_id, 
            update_data.status, 
            update_data.admin_notes
        )
        
        if not updated_query:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Support query not found or update failed"
            )
        
        return {
            "success": True,
            "message": f"Support query updated to {update_data.status}",
            "query": updated_query
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating support query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update support query"
        )
# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)