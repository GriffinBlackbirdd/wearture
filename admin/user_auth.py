from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from supabase import Client
from typing import Optional
from datetime import datetime, timedelta
from jose import jwt

from db.supabase_client import supabase
from .auth import JWT_SECRET, ACCESS_TOKEN_EXPIRE_MINUTES

# Models
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str

# Router
router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"]
)

# Helper functions
def create_user_token(user_id: str, email: str, remember: bool = False):
    """Create JWT token for user"""
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES * 24 * 7) if remember else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": email,
        "user_id": user_id,
        "exp": datetime.utcnow() + expires_delta
    }
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    return encoded_jwt

# Register endpoint
@router.post("/register")
async def register(user_data: UserRegister):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = supabase.table('users').select("*").eq('email', user_data.email).execute()
        
        if existing_user.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Create user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "name": user_data.name
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        # Create user profile in database
        user_profile = {
            "id": auth_response.user.id,
            "email": user_data.email,
            "name": user_data.name,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        supabase.table('users').insert(user_profile).execute()
        
        return {"success": True, "message": "Registration successful. Please login."}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

# Login endpoint
@router.post("/login")
async def login(response: Response, credentials: UserLogin):
    """Login user and return token"""
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create JWT token
        access_token = create_user_token(
            user_id=auth_response.user.id,
            email=auth_response.user.email,
            remember=credentials.remember
        )
        
        # Set cookie with appropriate expiry
        max_age = 60 * 60 * 24 * 7 if credentials.remember else ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        response.set_cookie(
            key="user_access_token",
            value=access_token,
            httponly=True,
            max_age=max_age,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        return {
            "success": True,
            "user": {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "name": auth_response.user.user_metadata.get("name")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

# Logout endpoint
@router.post("/logout")
async def logout(response: Response):
    """Logout user and clear token"""
    response.delete_cookie(key="user_access_token")
    return {"success": True, "message": "Logged out successfully"}

# Check auth status
@router.get("/status")
async def auth_status(request: Request):
    """Check if user is authenticated"""
    token = request.cookies.get("user_access_token")
    
    if not token:
        return {"authenticated": False}
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        
        # Get user profile
        user = supabase.table('users').select("*").eq('id', user_id).execute()
        
        if not user.data:
            return {"authenticated": False}
        
        return {
            "authenticated": True,
            "user": {
                "id": user.data[0]["id"],
                "email": user.data[0]["email"],
                "name": user.data[0]["name"]
            }
        }
        
    except:
        return {"authenticated": False}

# Password reset request
@router.post("/forgot-password")
async def forgot_password(email: EmailStr):
    """Send password reset email"""
    try:
        # Request password reset
        supabase.auth.reset_password_email(email)
        
        return {
            "success": True,
            "message": "Password reset email sent if account exists"
        }
        
    except Exception as e:
        # Don't reveal if email exists or not
        return {
            "success": True,
            "message": "Password reset email sent if account exists"
        }