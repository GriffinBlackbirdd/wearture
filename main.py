from fastapi import FastAPI, HTTPException, Depends, status, Request, Form, Response, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uvicorn
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
from jose import jwt
from admin.user_auth import router as user_auth_router

from db.razorpay_client import (
    create_razorpay_order, 
    verify_payment_signature,
    capture_payment,
    get_payment_details,
    RAZORPAY_KEY_ID
)

# Import Supabase client
from db.supabase_client import (
    get_all_products, get_product, create_product, update_product, delete_product,
    get_all_categories, get_category, create_category, update_category, delete_category,
    upload_product_image, upload_category_image, verify_admin_credentials, supabase, 
    get_products_by_category, get_subcategories, update_product_images, get_related_products
)

from db.order_management import (
    create_order, get_order, update_order_payment_status,
    get_user_orders, get_pending_orders, update_order_status
)
# Load environment variables
load_dotenv()

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

# Initialize FastAPI app
app = FastAPI(
    title="WEARXTURE API",
    description="API for WEARXTURE ethnic wear collection",
    version="1.0.0"
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
app.include_router(user_auth_router)

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
    additional_images: List[str] = []  # Add this field

# Category Models
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
    created_at: datetime
    updated_at: datetime
    

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the user login/register page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request):
    """Serve the checkout page"""
    return templates.TemplateResponse("checkout.html", {"request": request})

# Create order endpoint (placeholder for now)
# Create order endpoint with Razorpay integration
@app.post("/api/orders")
async def create_order_endpoint(order_data: dict, request: Request):
    """Create a new order with Razorpay integration"""
    try:
        # Extract order details
        cart = order_data.get("cart", [])
        email = order_data.get("email")
        phone = order_data.get("phone")
        delivery_address = {
            "address": order_data.get("address"),
            "city": order_data.get("city"),
            "state": order_data.get("state"),
            "pincode": order_data.get("pincode"),
            "country": order_data.get("country")
        }
        
        is_cod = order_data.get("payment") == "cod"
        
        # Calculate total amount
        total_amount = 0
        if is_cod:
            total_amount = 80
        else:
            subtotal = order_data.get("subtotal", 0)
            delivery_charge = order_data.get("deliveryCharge", 0)
            tax = order_data.get("tax", 0)
            total_amount = subtotal + delivery_charge + tax
        
        # Generate order ID
        order_id = "ORD" + datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Prepare order record
        order_record = {
            "order_id": order_id,
            "user_email": email,
            "phone": phone,
            "delivery_address": delivery_address,
            "items": cart,
            "subtotal": order_data.get("subtotal", 0),
            "delivery_charge": order_data.get("deliveryCharge", 0),
            "tax": order_data.get("tax", 0),
            "total_amount": total_amount,
            "payment_method": order_data.get("payment"),
            "payment_status": "pending",
            "order_status": "pending"
        }
        
        print(f"Order data to save: {order_record}")
        
        # Create Razorpay order only for non-COD orders
        if not is_cod:
            try:
                # Check if Razorpay is configured
                if not RAZORPAY_KEY_ID or not razorpay_client:
                    print("Razorpay not configured. Using demo mode.")
                    
                    # Save order to database even in demo mode
                    saved_order = create_order(order_record)
                    
                    if not saved_order:
                        raise Exception("Failed to save order to database")
                    
                    return {
                        "success": True,
                        "order_id": order_id,
                        "demo_mode": True,
                        "message": "Demo order created successfully.",
                        "amount": int(total_amount * 100)
                    }
                
                # Create Razorpay order
                razorpay_order = create_razorpay_order(
                    amount=total_amount,
                    order_info={
                        "receipt": order_id,
                        "notes": {
                            "customer_email": email,
                            "customer_phone": phone
                        }
                    }
                )
                
                # Save Razorpay order ID
                order_record["razorpay_order_id"] = razorpay_order["id"]
                
                # Save order to database
                saved_order = create_order(order_record)
                
                if not saved_order:
                    raise Exception("Failed to save order to database")
                
                print(f"Order saved successfully: {order_id}")
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "razorpay_order_id": razorpay_order["id"],
                    "razorpay_key": RAZORPAY_KEY_ID,
                    "amount": int(total_amount * 100),
                    "currency": "INR",
                    "company_name": "WEARXTURE",
                    "company_logo": "/static/images/WEARXTURE LOGOai.png"
                }
            except Exception as e:
                print(f"Razorpay order creation failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Payment gateway error: {str(e)}"
                )
        else:
            # For COD orders, save directly
            order_record["payment_status"] = "cod_pending"
            saved_order = create_order(order_record)
            
            if not saved_order:
                raise Exception("Failed to save order to database")
            
            return {
                "success": True,
                "order_id": order_id,
                "message": "COD order placed successfully",
                "amount": total_amount
            }
            
    except Exception as e:
        print(f"Order creation error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order creation failed: {str(e)}"
        )
# Verify payment endpoint
@app.post("/api/verify-payment")
async def verify_payment(payment_data: dict):
    """Verify Razorpay payment signature"""
    try:
        order_id = payment_data.get("razorpay_order_id")
        payment_id = payment_data.get("razorpay_payment_id")
        signature = payment_data.get("razorpay_signature")
        
        # Verify signature
        is_valid = verify_payment_signature(order_id, payment_id, signature)
        
        if is_valid:
            # Get payment details
            payment_details = get_payment_details(payment_id)
            
            # Update order status in database
            # In production, update your order status
            
            return {
                "success": True,
                "payment_id": payment_id,
                "status": payment_details.get("status"),
                "message": "Payment verified successfully"
            }
        else:
            return {
                "success": False,
                "message": "Payment verification failed"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification failed: {str(e)}"
        )

# Order confirmation page
@app.get("/order-confirmation", response_class=HTMLResponse)
async def order_confirmation_page(request: Request):
    """Enhanced order confirmation page with styling"""
    return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Order Confirmed - WEARXTURE</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=Poppins:wght@300;400;500;600;700&display=swap');
                
                :root {
                    --primary-color: #e25822;
                    --success-color: #28a745;
                    --text-color: #333;
                    --light-text: #777;
                    --font-heading: 'Playfair Display', serif;
                    --font-body: 'Poppins', sans-serif;
                }
                
                body {
                    font-family: var(--font-body);
                    text-align: center;
                    padding: 50px;
                    background-color: #f9f9f9;
                    margin: 0;
                }
                
                .confirmation-container {
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                    padding: 40px;
                    animation: fadeIn 0.8s ease;
                }
                
                @keyframes fadeIn {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                .success-icon {
                    color: var(--success-color);
                    font-size: 80px;
                    margin-bottom: 20px;
                    animation: checkmark 0.8s ease 0.2s both;
                }
                
                @keyframes checkmark {
                    0% {
                        transform: scale(0);
                        opacity: 0;
                    }
                    50% {
                        transform: scale(1.2);
                    }
                    100% {
                        transform: scale(1);
                        opacity: 1;
                    }
                }
                
                h1 {
                    font-family: var(--font-heading);
                    color: var(--text-color);
                    margin-bottom: 10px;
                    font-size: 36px;
                    font-weight: 700;
                }
                
                .order-message {
                    color: var(--light-text);
                    margin-bottom: 30px;
                    font-size: 18px;
                    line-height: 1.6;
                }
                
                .order-details {
                    background: #f9f9f9;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 30px 0;
                    text-align: left;
                }
                
                .order-details h3 {
                    font-size: 20px;
                    margin-bottom: 15px;
                    color: var(--text-color);
                }
                
                .detail-row {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 10px;
                    font-size: 16px;
                }
                
                .detail-label {
                    color: var(--light-text);
                }
                
                .detail-value {
                    font-weight: 500;
                    color: var(--text-color);
                }
                
                .btn {
                    background: var(--primary-color);
                    color: white;
                    padding: 14px 35px;
                    text-decoration: none;
                    border-radius: 50px;
                    display: inline-block;
                    margin: 10px;
                    font-weight: 600;
                    transition: all 0.3s ease;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    box-shadow: 0 4px 15px rgba(226, 88, 34, 0.3);
                }
                
                .btn:hover {
                    background: #c24d1e;
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(226, 88, 34, 0.4);
                }
                
                .btn-secondary {
                    background: white;
                    color: var(--text-color);
                    border: 2px solid var(--primary-color);
                    box-shadow: none;
                }
                
                .btn-secondary:hover {
                    background: var(--primary-color);
                    color: white;
                }
                
                .delivery-info {
                    margin-top: 30px;
                    padding: 20px;
                    background: #f0f8ff;
                    border-radius: 12px;
                    border-left: 4px solid #3498db;
                }
                
                .delivery-info i {
                    color: #3498db;
                    margin-right: 10px;
                }
                
                .social-share {
                    margin-top: 30px;
                    padding-top: 30px;
                    border-top: 1px solid #eee;
                }
                
                .social-share h4 {
                    margin-bottom: 15px;
                    color: var(--light-text);
                }
                
                .social-icons {
                    display: flex;
                    justify-content: center;
                    gap: 15px;
                }
                
                .social-icon {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: #f1f1f1;
                    color: var(--text-color);
                    transition: all 0.3s ease;
                }
                
                .social-icon:hover {
                    background: var(--primary-color);
                    color: white;
                    transform: translateY(-3px);
                }
            </style>
        </head>
        <body>
            <div class="confirmation-container">
                <div class="success-icon">
                    <i class="fas fa-check-circle"></i>
                </div>
                <h1>Order Confirmed!</h1>
                <p class="order-message">
                    Thank you for your order! We're excited to get your items to you.
                    You'll receive a confirmation email shortly with your order details.
                </p>
                
                <div class="order-details">
                    <h3>Order Summary</h3>
                    <div class="detail-row">
                        <span class="detail-label">Order Number:</span>
                        <span class="detail-value">#ORD20250117093412</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Payment Status:</span>
                        <span class="detail-value">Confirmed</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Estimated Delivery:</span>
                        <span class="detail-value">3-5 Business Days</span>
                    </div>
                </div>
                
                <div class="delivery-info">
                    <i class="fas fa-truck"></i>
                    <strong>Track Your Order:</strong>
                    <p>You can track your order status in your email or by visiting our tracking page.</p>
                </div>
                
                <div style="margin-top: 30px;">
                    <a href="/" class="btn">Continue Shopping</a>
                    <a href="#" class="btn btn-secondary">View Order Details</a>
                </div>
                
                <div class="social-share">
                    <h4>Share the love</h4>
                    <div class="social-icons">
                        <a href="#" class="social-icon">
                            <i class="fab fa-facebook-f"></i>
                        </a>
                        <a href="#" class="social-icon">
                            <i class="fab fa-twitter"></i>
                        </a>
                        <a href="#" class="social-icon">
                            <i class="fab fa-instagram"></i>
                        </a>
                        <a href="#" class="social-icon">
                            <i class="fab fa-whatsapp"></i>
                        </a>
                    </div>
                </div>
            </div>
        </body>
        </html>
    """)
# Order confirmation page (placeholder)
@app.get("/order-confirmation", response_class=HTMLResponse)
async def order_confirmation_page(request: Request):
    """Order confirmation page"""
    # In a real app, this would show order details
    return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Order Confirmed - WEARXTURE</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                }
                .success-icon {
                    color: #28a745;
                    font-size: 72px;
                    margin-bottom: 20px;
                }
                h1 {
                    color: #333;
                    margin-bottom: 10px;
                }
                p {
                    color: #666;
                    margin-bottom: 30px;
                }
                .btn {
                    background: #e25822;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                }
                .btn:hover {
                    background: #c24d1e;
                }
            </style>
        </head>
        <body>
            <div class="success-icon">✓</div>
            <h1>Order Confirmed!</h1>
            <p>Thank you for your order. We'll send you a confirmation email shortly.</p>
            <a href="/" class="btn">Continue Shopping</a>
        </body>
        </html>
    """)
    

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
        additional_images=additional_images  # Add this field
    )


def category_from_db(db_category: Dict[str, Any]) -> CategoryResponse:
    """Convert a database category to a CategoryResponse model"""
    return CategoryResponse(
        id=db_category["id"],
        name=db_category["name"],
        description=db_category["description"],
        parent_id=db_category["parent_id"],
        image_url=db_category["image_url"],
        created_at=db_category["created_at"],
        updated_at=db_category["updated_at"]
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
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "products": products,
            "categories": categories,
            "new_products": new_products
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
    ADMIN_EMAIL = "hamidarreyan@gmail.com"
    ADMIN_PASSWORD = "admin123"
    
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

# ========= Admin Page Routes =========

# Admin dashboard
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    try:
        email = await verify_admin_token(request)
        
        # Get counts for dashboard
        product_count = len(get_all_products())
        category_count = len(get_all_categories())
        
        return templates.TemplateResponse(
            "admin/dashboard.html", 
            {
                "request": request, 
                "user_email": email,
                "product_count": product_count,
                "category_count": category_count
            }
        )
    except HTTPException:
        return RedirectResponse(url="/admin/login")

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

# ========= Admin API Routes =========

# Create a new product
@app.post("/admin/api/products", response_model=ProductResponse)
async def create_admin_product(
    product: ProductCreate, 
    admin_email: str = Depends(verify_admin_token)
):
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
        "attributes": product.attributes
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

# Update a category
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
    
    # Prepare category data for database
    category_data = {
        "name": category.name,
        "description": category.description,
        "parent_id": category.parent_id
    }
    
    # Update in database
    db_category = update_category(category_id, category_data)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )
    
    return category_from_db(db_category)

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
@app.get("/category/{category_id}", response_class=HTMLResponse, tags=["Pages"])
async def category_page(request: Request, category_id: int):
    """
    Render the category page with all products in that category
    """
    # Get category from database
    db_category = get_category(category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    category = category_from_db(db_category)
    
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
# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)