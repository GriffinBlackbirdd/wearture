from fastapi import Depends, HTTPException, status, Request, Cookie
from jose import jwt, JWTError
from typing import Optional
from .auth import JWT_SECRET, TokenData

# User verification from JWT token in cookie
async def get_current_admin_user(request: Request, admin_access_token: Optional[str] = Cookie(None)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # If no token in cookie, redirect to login
    if not admin_access_token:
        raise credentials_exception
    
    try:
        # Decode the JWT token
        payload = jwt.decode(admin_access_token, JWT_SECRET, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
        return token_data
    except JWTError:
        raise credentials_exception

# Dependency to verify admin authentication
def verify_admin(user: TokenData = Depends(get_current_admin_user)):
    if not user or not user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return user