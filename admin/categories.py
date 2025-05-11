from fastapi import APIRouter, Depends, Request, HTTPException, status, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pydantic import BaseModel, Field
import os
from datetime import datetime

# Import authentication dependencies
from .dependencies import verify_admin

# Templates
templates = Jinja2Templates(directory="templates")

# Schemas
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    id: int

class CategoryResponse(CategoryBase):
    id: int
    image_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

# Sample data for categories (temporary, will be replaced with database)
categories_db = [
    {
        "id": 1,
        "name": "Anarkali Suits",
        "description": "Traditional Anarkali suits for all occasions",
        "parent_id": None,
        "image_url": "/static/images/categories/anarkali.jpg",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    },
    {
        "id": 2,
        "name": "Gowns",
        "description": "Elegant and glamorous gowns",
        "parent_id": None,
        "image_url": "/static/images/categories/gowns.jpg",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    },
    {
        "id": 3,
        "name": "Sarees",
        "description": "Traditional and designer sarees",
        "parent_id": None,
        "image_url": "/static/images/categories/sarees.jpg",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    },
    {
        "id": 4,
        "name": "Lehengas",
        "description": "Bridal and party wear lehengas",
        "parent_id": None,
        "image_url": "/static/images/categories/lehengas.jpg",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
]

# Router
router = APIRouter(
    prefix="/admin",
    tags=["admin_categories"]
)

# Route to display categories page
@router.get("/categories", response_class=HTMLResponse)
async def admin_categories_page(request: Request, admin_user=Depends(verify_admin)):
    return templates.TemplateResponse(
        "admin/categories.html", 
        {"request": request, "categories": categories_db}
    )

# API Routes for AJAX operations

# Get all categories
@router.get("/api/categories", response_model=List[CategoryResponse])
async def get_admin_categories(admin_user=Depends(verify_admin)):
    return [CategoryResponse(**category) for category in categories_db]

# Get a single category
@router.get("/api/categories/{category_id}", response_model=CategoryResponse)
async def get_admin_category(category_id: int, admin_user=Depends(verify_admin)):
    for category in categories_db:
        if category["id"] == category_id:
            return CategoryResponse(**category)
            
    raise HTTPException(status_code=404, detail="Category not found")

# Create a new category
@router.post("/api/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_category(category: CategoryCreate, admin_user=Depends(verify_admin)):
    # Generate a new category ID
    new_id = max([c["id"] for c in categories_db], default=0) + 1
    
    # Default image URL
    image_url = "/static/images/categories/default.jpg"
    
    # Create a new category dict
    new_category = {
        "id": new_id,
        "name": category.name,
        "description": category.description,
        "parent_id": category.parent_id,
        "image_url": image_url,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    # Add to the categories list
    categories_db.append(new_category)
    
    return CategoryResponse(**new_category)

# Update a category
@router.put("/api/categories/{category_id}", response_model=CategoryResponse)
async def update_admin_category(category_id: int, category: CategoryUpdate, admin_user=Depends(verify_admin)):
    for i, cat in enumerate(categories_db):
        if cat["id"] == category_id:
            # Update category fields
            categories_db[i]["name"] = category.name
            categories_db[i]["description"] = category.description
            categories_db[i]["parent_id"] = category.parent_id
            categories_db[i]["updated_at"] = datetime.now()
            
            return CategoryResponse(**categories_db[i])
            
    raise HTTPException(status_code=404, detail="Category not found")

# Delete a category
@router.delete("/api/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_category(category_id: int, admin_user=Depends(verify_admin)):
    for i, category in enumerate(categories_db):
        if category["id"] == category_id:
            categories_db.pop(i)
            return
            
    raise HTTPException(status_code=404, detail="Category not found")

# Upload category image
@router.post("/api/upload/category-image")
async def upload_category_image(
    file: UploadFile = File(...),
    admin_user=Depends(verify_admin)
):
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Create a unique filename
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    
    # Ensure the upload directory exists
    upload_dir = "static/images/categories"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save the file
    file_path = os.path.join(upload_dir, filename)
    
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not upload file: {str(e)}")
    finally:
        await file.close()
    
    # Return the file URL
    file_url = f"/static/images/categories/{filename}"
    return {"url": file_url}