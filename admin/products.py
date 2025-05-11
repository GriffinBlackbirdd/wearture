from fastapi import APIRouter, Depends, Request, HTTPException, status, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pydantic import BaseModel, Field
import json
import os
from datetime import datetime

# Import authentication dependencies
from .dependencies import verify_admin

# Templates
templates = Jinja2Templates(directory="templates")

# Schemas
class ProductBase(BaseModel):
    name: str
    description: str
    price: float
    category: str
    in_stock: bool = True
    sku: Optional[str] = None
    tags: Optional[List[str]] = []
    
class ProductCreate(ProductBase):
    sale_price: Optional[float] = None
    materials: Optional[str] = None
    sizes: Optional[List[str]] = []
    
class ProductUpdate(ProductBase):
    id: int
    sale_price: Optional[float] = None
    materials: Optional[str] = None
    sizes: Optional[List[str]] = []
    
class ProductResponse(ProductBase):
    id: int
    image_url: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

# Router
router = APIRouter(
    prefix="/admin",
    tags=["admin_products"]
)

# Route to display products page
@router.get("/products", response_class=HTMLResponse)
async def admin_products_page(request: Request, admin_user=Depends(verify_admin)):
    # For now, use the sample products from main.py - later we'll import from database
    from main import products_db
    
    return templates.TemplateResponse(
        "admin/products.html", 
        {"request": request, "products": products_db}
    )

# API Routes for AJAX operations

# Get all products
@router.get("/api/products", response_model=List[ProductResponse])
async def get_admin_products(admin_user=Depends(verify_admin)):
    # For now, use the sample products from main.py
    from main import products_db
    
    # Convert to ProductResponse model
    products = []
    for product in products_db:
        # Convert to dictionary and add missing fields
        product_dict = product.dict()
        product_dict['created_at'] = datetime.now()
        product_dict['updated_at'] = datetime.now()
        products.append(ProductResponse(**product_dict))
        
    return products

# Get a single product
@router.get("/api/products/{product_id}", response_model=ProductResponse)
async def get_admin_product(product_id: int, admin_user=Depends(verify_admin)):
    from main import products_db
    
    for product in products_db:
        if product.id == product_id:
            # Convert to dictionary and add missing fields
            product_dict = product.dict()
            product_dict['created_at'] = datetime.now()
            product_dict['updated_at'] = datetime.now()
            return ProductResponse(**product_dict)
            
    raise HTTPException(status_code=404, detail="Product not found")

# Create a new product
@router.post("/api/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_product(product: ProductCreate, admin_user=Depends(verify_admin)):
    from main import products_db
    
    # Generate a new product ID
    new_id = max([p.id for p in products_db], default=0) + 1
    
    # Temporary image URL for testing - in production this would come from file upload
    image_url = "/static/images/products/placeholder.jpg"
    
    # Create a new product 
    # This is a temporary implementation - in production we'd save to database
    from main import Product
    new_product = Product(
        id=new_id,
        name=product.name,
        description=product.description,
        price=product.price,
        category=product.category,
        image_url=image_url,
        in_stock=product.in_stock
    )
    
    # Add to the products list
    products_db.append(new_product)
    
    # Return the created product with additional fields
    product_dict = new_product.dict()
    product_dict['created_at'] = datetime.now()
    product_dict['updated_at'] = datetime.now()
    product_dict['tags'] = []  # Default empty tags list
    
    return ProductResponse(**product_dict)

# Update a product
@router.put("/api/products/{product_id}", response_model=ProductResponse)
async def update_admin_product(product_id: int, product: ProductUpdate, admin_user=Depends(verify_admin)):
    from main import products_db
    
    for i, p in enumerate(products_db):
        if p.id == product_id:
            # Update product - in production we'd update in database
            products_db[i].name = product.name
            products_db[i].description = product.description
            products_db[i].price = product.price
            products_db[i].category = product.category
            products_db[i].in_stock = product.in_stock
            
            # Convert to response model
            product_dict = products_db[i].dict()
            product_dict['created_at'] = datetime.now()
            product_dict['updated_at'] = datetime.now()
            product_dict['tags'] = product.tags
            
            return ProductResponse(**product_dict)
            
    raise HTTPException(status_code=404, detail="Product not found")

# Delete a product
@router.delete("/api/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_product(product_id: int, admin_user=Depends(verify_admin)):
    from main import products_db
    
    for i, product in enumerate(products_db):
        if product.id == product_id:
            products_db.pop(i)
            return
            
    raise HTTPException(status_code=404, detail="Product not found")

# Image Upload Endpoint
@router.post("/api/upload/product-image")
async def upload_product_image(
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
    upload_dir = "static/images/products"
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
    file_url = f"/static/images/products/{filename}"
    return {"url": file_url}

# Multiple Image Upload Endpoint
@router.post("/api/upload/product-images")
async def upload_product_images(
    files: List[UploadFile] = File(...),
    admin_user=Depends(verify_admin)
):
    urls = []
    
    upload_dir = "static/images/products"
    os.makedirs(upload_dir, exist_ok=True)
    
    for file in files:
        # Skip non-image files
        if not file.content_type.startswith("image/"):
            continue
        
        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)
        
        try:
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)
                
            file_url = f"/static/images/products/{filename}"
            urls.append(file_url)
        except Exception as e:
            # Log the error but continue processing other files
            print(f"Error uploading {file.filename}: {str(e)}")
        finally:
            await file.close()
    
    return {"urls": urls}