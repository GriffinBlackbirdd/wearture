from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from .dependencies import verify_admin
from .auth import router as auth_router
from typing import Dict

# Templates
templates = Jinja2Templates(directory="templates")

# Admin router
router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

# Include the auth router
router.include_router(auth_router)

# Admin dashboard
@router.get("/dashboard")
async def admin_dashboard(request: Request, admin_user=Depends(verify_admin)):
    """
    Admin dashboard - protected by verify_admin dependency
    """
    return templates.TemplateResponse(
        "admin/dashboard.html", 
        {"request": request, "user_email": admin_user.email}
    )

# Redirect root admin URL to dashboard
@router.get("/")
async def admin_root():
    return RedirectResponse(url="/admin/dashboard")