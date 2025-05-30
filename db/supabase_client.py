"""
Updated Supabase client integration for WEARXTURE with multiple image support
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any, Union
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Get Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)



import hashlib
from typing import Dict, Optional, Any

# Add these functions to your db/supabase_client.py file

def get_user_by_email_simple(email: str):
    """Get user by email from custom users table"""
    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None

def get_user_by_id_simple(user_id: int):
    """Get user by ID from custom users table"""
    try:
        response = supabase.table('users').select('*').eq('id', user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return None

def create_user_simple(email: str, password: str, name: str, phone: str = None):
    """Create user in custom users table (email/password signup)"""
    try:
        import bcrypt
        
        # Hash the password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user_data = {
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "phone": phone,
            "provider": "email",
            "is_active": True,
            "role": "customer"
        }
        
        response = supabase.table('users').insert(user_data).execute()
        return response.data[0] if response.data else None
        
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

def authenticate_user_simple(email: str, password: str):
    """Authenticate user with email/password"""
    try:
        import bcrypt
        
        # Get user from database
        user = get_user_by_email_simple(email)
        if not user:
            return None
        
        # Check if this is an OAuth user
        if user.get('provider') != 'email' or user.get('password_hash') == 'oauth_user':
            return None  # OAuth users can't login with password
        
        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return user
        
        return None
        
    except Exception as e:
        print(f"Error authenticating user: {e}")
        return None

def update_user(user_id: int, update_data: dict):
    """Update user information"""
    try:
        # Handle password update
        if 'password' in update_data:
            import bcrypt
            password_hash = bcrypt.hashpw(
                update_data['password'].encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            update_data['password_hash'] = password_hash
            del update_data['password']
        
        response = supabase.table('users').update(update_data).eq('id', user_id).execute()
        return response.data[0] if response.data else None
        
    except Exception as e:
        print(f"Error updating user: {e}")
        return None
        
def update_user(user_id: int, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update user data in the custom users table
    """
    try:
        # If password is being updated, hash it
        if 'password' in user_data:
            user_data['password_hash'] = hash_password(user_data['password'])
            del user_data['password']
        
        # Add updated timestamp
        user_data['updated_at'] = datetime.now().isoformat()
        
        print(f"🔧 Updating user {user_id} with data: {list(user_data.keys())}")
        
        response = supabase.table('users').update(user_data).eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            user = response.data[0]
            print(f"✅ User updated successfully: {user.get('id')}")
            # Remove password hash from response
            user.pop('password_hash', None)
            return user
        
        print(f"❌ No data returned from update")
        return None
        
    except Exception as e:
        print(f"❌ Error updating user {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return None
        
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        print(f"Bcrypt error, falling back to SHA256: {e}")
        # Fallback to SHA256 if bcrypt fails
        return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Try bcrypt first
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        # Fallback to SHA256 comparison
        return hashlib.sha256(password.encode()).hexdigest() == hashed

def create_user_simple(email: str, password: str, name: str, phone: str = None) -> Optional[Dict[str, Any]]:
    """
    Create a new user - ONLY using our custom users table, NO Supabase Auth
    """
    try:
        print(f"🔧 Creating user: {email}")
        
        # Hash the password
        password_hash = hash_password(password)
        print(f"✅ Password hashed")
        
        # Create user data - only fields that exist in our table
        user_data = {
            'email': email.lower().strip(),
            'password_hash': password_hash,
            'name': name.strip(),
            'is_active': True,
            'role': 'customer'
        }
        
        # Add phone only if provided
        if phone and phone.strip():
            user_data['phone'] = phone.strip()
        
        print(f"🔧 User data: {list(user_data.keys())}")
        
        # Insert ONLY into our custom users table - NO auth table involved
        response = supabase.table('users').insert(user_data).execute()
        
        print(f"🔧 Supabase response received")
        print(f"🔧 Response data: {response.data}")
        
        if response.data and len(response.data) > 0:
            user = response.data[0]
            print(f"✅ User created with ID: {user.get('id')}")
            
            # Remove password hash from response
            user.pop('password_hash', None)
            return user
        else:
            print(f"❌ No data in response")
            return None
            
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None

def authenticate_user_simple(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user - ONLY using our custom users table
    """
    try:
        print(f"🔧 Authenticating user: {email}")
        
        # Get user from OUR custom users table only
        response = supabase.table('users').select('*').eq('email', email.lower().strip()).execute()
        
        if not response.data or len(response.data) == 0:
            print(f"❌ User not found in custom users table")
            return None
        
        user = response.data[0]
        print(f"✅ User found: {user.get('id')}")
        
        # Verify password
        if verify_password(password, user['password_hash']):
            print(f"✅ Password verified")
            # Remove password hash from response
            user.pop('password_hash', None)
            return user
        else:
            print(f"❌ Password verification failed")
            return None
        
    except Exception as e:
        print(f"❌ Error authenticating user: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_user_by_email_simple(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email - ONLY from our custom users table
    """
    try:
        response = supabase.table('users').select('*').eq('email', email.lower().strip()).execute()
        
        if response.data and len(response.data) > 0:
            user = response.data[0]
            # Remove password hash from response
            user.pop('password_hash', None)
            return user
        
        return None
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None

def get_user_by_id_simple(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    try:
        response = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if response.data and len(response.data) > 0:
            user = response.data[0]
            user.pop('password_hash', None)
            return user
        
        return None
        
    except Exception as e:
        return None


# Products functions
def get_all_products() -> List[Dict[str, Any]]:
    """
    Get all products from the database
    """
    try:
        response = supabase.table('products').select('*, categories(name)').execute()
        return response.data
    except Exception as e:
        print(f"Error getting products: {e}")
        return []

def get_product(product_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a specific product by ID
    """
    try:
        response = supabase.table('products').select('*, categories(name)').eq('id', product_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting product {product_id}: {e}")
        return None

def get_products_by_category(category_id: int) -> List[Dict[str, Any]]:
    """
    Get all products that belong to a specific category
    """
    try:
        response = supabase.table('products').select('*, categories(name)').eq('category_id', category_id).execute()
        return response.data
    except Exception as e:
        print(f"Error getting products by category {category_id}: {e}")
        return []

def get_subcategories(parent_id: int) -> List[Dict[str, Any]]:
    """
    Get all subcategories that belong to a parent category
    """
    try:
        response = supabase.table('categories').select('*').eq('parent_id', parent_id).execute()
        return response.data
    except Exception as e:
        print(f"Error getting subcategories for parent {parent_id}: {e}")
        return []

def create_product(product_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a new product
    """
    try:
        # Set created_at and updated_at
        now = datetime.now().isoformat()
        product_data['created_at'] = now
        product_data['updated_at'] = now
        
        # Ensure filter is set
        if 'filter' not in product_data:
            product_data['filter'] = 'all'
        
        # Ensure inventory_count is set
        if 'inventory_count' not in product_data:
            product_data['inventory_count'] = 0
        
        # Handle any JSON fields
        if 'attributes' in product_data and isinstance(product_data['attributes'], dict):
            product_data['attributes'] = json.dumps(product_data['attributes'])
        
        # Insert into database
        response = supabase.table('products').insert(product_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error creating product: {e}")
        return None


def update_product(product_id: int, product_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update an existing product
    """
    try:
        # Set updated_at
        product_data['updated_at'] = datetime.now().isoformat()
        
        # Get existing product to preserve additional_images if not updating
        existing_product = get_product(product_id)
        
        # Handle any JSON fields
        if 'attributes' in product_data and isinstance(product_data['attributes'], dict):
            # Preserve existing additional_images in attributes if they exist
            if existing_product and 'attributes' in existing_product:
                try:
                    existing_attrs = json.loads(existing_product['attributes']) if isinstance(existing_product['attributes'], str) else existing_product['attributes']
                    if 'additional_images' in existing_attrs and 'additional_images' not in product_data['attributes']:
                        product_data['attributes']['additional_images'] = existing_attrs['additional_images']
                except:
                    pass
            product_data['attributes'] = json.dumps(product_data['attributes'])
        
        # Update in database
        response = supabase.table('products').update(product_data).eq('id', product_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error updating product {product_id}: {e}")
        return None

def update_product_images(product_id: int, image_urls: List[str]) -> Optional[Dict[str, Any]]:
    """
    Update product with multiple images - FIXED VERSION
    First image becomes the main image, rest are stored as additional images
    """
    try:
        print(f"🔄 Updating product {product_id} with {len(image_urls)} images")
        print(f"   URLs: {image_urls}")
        
        # Get existing product
        product = get_product(product_id)
        if not product:
            print(f"❌ Product {product_id} not found")
            return None
        
        # Parse existing attributes
        attributes = {}
        if 'attributes' in product and product['attributes']:
            try:
                if isinstance(product['attributes'], str):
                    attributes = json.loads(product['attributes'])
                else:
                    attributes = product['attributes']
            except:
                print(f"⚠️ Could not parse existing attributes, starting fresh")
                attributes = {}
        
        # Prepare update data
        update_data = {}
        
        if image_urls:
            # First image is the main image
            update_data['image_url'] = image_urls[0]
            print(f"   📸 Main image: {image_urls[0]}")
            
            # Rest are additional images
            if len(image_urls) > 1:
                attributes['additional_images'] = image_urls[1:]
                print(f"   📸 Additional images: {len(image_urls[1:])} items")
            else:
                attributes['additional_images'] = []
                print(f"   📸 No additional images")
            
            # Store attributes as JSON string
            update_data['attributes'] = json.dumps(attributes)
            update_data['updated_at'] = datetime.now().isoformat()
        
        print(f"   💾 Update data prepared: {list(update_data.keys())}")
        
        # Update product in database
        response = supabase.table('products').update(update_data).eq('id', product_id).execute()
        
        if response.data and len(response.data) > 0:
            print(f"   ✅ Product updated successfully")
            return response.data[0]
        else:
            print(f"   ❌ No data returned from update")
            return None
            
    except Exception as e:
        print(f"❌ Error updating product images for {product_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

def delete_product(product_id: int) -> bool:
    """
    Delete a product
    """
    try:
        response = supabase.table('products').delete().eq('id', product_id).execute()
        return True if response.data else False
    except Exception as e:
        print(f"Error deleting product {product_id}: {e}")
        return False

# Categories functions
def get_all_categories() -> List[Dict[str, Any]]:
    """
    Get all categories from the database
    """
    try:
        response = supabase.table('categories').select('*').execute()
        return response.data
    except Exception as e:
        print(f"Error getting categories: {e}")
        return []

def get_category(category_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a specific category by ID
    """
    try:
        response = supabase.table('categories').select('*').eq('id', category_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting category {category_id}: {e}")
        return None

def create_category(category_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a new category
    """
    try:
        # Set created_at and updated_at
        now = datetime.now().isoformat()
        category_data['created_at'] = now
        category_data['updated_at'] = now
        
        # Ensure filter is set
        if 'filter' not in category_data:
            category_data['filter'] = 'all'
        
        # Insert into database
        response = supabase.table('categories').insert(category_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error creating category: {e}")
        return None

def update_category(category_id: int, category_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update an existing category
    """
    try:
        # Set updated_at
        category_data['updated_at'] = datetime.now().isoformat()
        
        # Update in database
        response = supabase.table('categories').update(category_data).eq('id', category_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error updating category {category_id}: {e}")
        return None

def delete_category(category_id: int) -> bool:
    """
    Delete a category
    """
    try:
        response = supabase.table('categories').delete().eq('id', category_id).execute()
        return True if response.data else False
    except Exception as e:
        print(f"Error deleting category {category_id}: {e}")
        return False

# Image upload functions
def upload_product_image(file_content: bytes, file_name: str) -> Optional[str]:
    """
    Upload a product image to Supabase Storage
    Returns the public URL of the uploaded image
    """
    try:
        # Create a unique file name
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_filename = f"{timestamp}_{file_name}"
        
        # Upload to Supabase Storage
        response = supabase.storage.from_("product-images").upload(
            path=unique_filename,
            file=file_content,
            file_options={"content-type": "image/jpeg"}  # Adjust based on file type
        )
        
        # Get the public URL
        if response:
            print("Image uploaded successfully, getting public URL")
            public_url = supabase.storage.from_("product-images").get_public_url(unique_filename)
            print(f"Public URL: {public_url}")
            return public_url
        
        print("Image upload failed, response:", response)
        return None
    except Exception as e:
        print(f"Error uploading product image: {e}")
        return None

def upload_category_image(file_content: bytes, file_name: str) -> Optional[str]:
    """
    Upload a category image to Supabase Storage
    Returns the public URL of the uploaded image
    """
    try:
        # Create a unique file name
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_filename = f"{timestamp}_{file_name}"
        
        # Upload to Supabase Storage
        response = supabase.storage.from_("category-images").upload(
            path=unique_filename,
            file=file_content,
            file_options={"content-type": "image/jpeg"}  # Adjust based on file type
        )
        
        # Get the public URL
        if response:
            print("Category image uploaded successfully, getting public URL")
            public_url = supabase.storage.from_("category-images").get_public_url(unique_filename)
            print(f"Public URL: {public_url}")
            return public_url
        
        print("Category image upload failed, response:", response)
        return None
    except Exception as e:
        print(f"Error uploading category image: {e}")
        return None

# Authentication functions
def verify_admin_credentials(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Verify admin credentials using Supabase auth
    """
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            return {
                "id": response.user.id,
                "email": response.user.email,
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token
            }
        return None
    except Exception as e:
        print(f"Error verifying credentials: {e}")
        return None

# Related products function
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

# Reels functions
def get_all_reels() -> List[Dict[str, Any]]:
    """
    Get all reels from the database
    """
    try:
        response = supabase.table('reels').select('*, categories(name)').order('display_order').execute()
        return response.data
    except Exception as e:
        print(f"Error getting reels: {e}")
        return []

def get_active_reels() -> List[Dict[str, Any]]:
    """
    Get only active reels for display
    """
    try:
        response = supabase.table('reels').select('*, categories(name)').eq('is_active', True).order('display_order').execute()
        return response.data
    except Exception as e:
        print(f"Error getting active reels: {e}")
        return []

def get_reel(reel_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a specific reel by ID
    """
    try:
        response = supabase.table('reels').select('*, categories(name)').eq('id', reel_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting reel {reel_id}: {e}")
        return None

def create_reel(reel_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a new reel
    """
    try:
        # Set created_at and updated_at
        now = datetime.now().isoformat()
        reel_data['created_at'] = now
        reel_data['updated_at'] = now
        
        # Insert into database
        response = supabase.table('reels').insert(reel_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error creating reel: {e}")
        return None

def update_reel(reel_id: int, reel_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update an existing reel
    """
    try:
        # Set updated_at
        reel_data['updated_at'] = datetime.now().isoformat()
        
        # Update in database
        response = supabase.table('reels').update(reel_data).eq('id', reel_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error updating reel {reel_id}: {e}")
        print(f"Update data: {reel_data}")
        import traceback
        traceback.print_exc()
        return None

def update_reel_video_url(reel_id: int, video_url: str) -> bool:
    """
    Update reel video URL using direct SQL to bypass any RLS issues
    """
    try:
        # Try using the regular update method first
        response = supabase.table('reels').update({
            'video_url': video_url,
            'updated_at': datetime.now().isoformat()
        }).eq('id', reel_id).execute()
        
        print(f"Update response: {response}")
        return bool(response.data)
    except Exception as e:
        print(f"Error updating reel video URL: {e}")
        import traceback
        traceback.print_exc()
        return False
        
def delete_reel(reel_id: int) -> bool:
    """
    Delete a reel
    """
    try:
        response = supabase.table('reels').delete().eq('id', reel_id).execute()
        return True if response.data else False
    except Exception as e:
        print(f"Error deleting reel {reel_id}: {e}")
        return False

def upload_reel_video(file_content: bytes, file_name: str) -> Optional[str]:
    """
    Upload a reel video to Supabase Storage
    Returns the public URL of the uploaded video
    """
    try:
        # Create a unique file name
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_filename = f"{timestamp}_{file_name}"
        
        print(f"Attempting to upload file: {unique_filename}")
        
        # Upload to Supabase Storage
        response = supabase.storage.from_("reels").upload(
            path=unique_filename,
            file=file_content,
            file_options={"content-type": "video/mp4"}  # Adjust based on file type
        )
        
        print(f"Storage upload response: {response}")
        
        # Get the public URL
        if response:
            print("File uploaded successfully to storage, getting public URL")
            public_url = supabase.storage.from_("reels").get_public_url(unique_filename)
            print(f"Public URL: {public_url}")
            return public_url
        else:
            print("Storage upload failed")
            return None
    except Exception as e:
        print(f"Error in upload_reel_video: {e}")
        import traceback
        traceback.print_exc()
        return None

def deduct_inventory(product_id: int, quantity: int) -> bool:
    """
    Deduct inventory for a product after an order is placed
    Returns True if successful, False otherwise
    """
    try:
        # Get current product
        product = get_product(product_id)
        if not product:
            print(f"Product {product_id} not found")
            return False
        
        current_inventory = product.get('inventory_count', 0)
        
        # Check if sufficient inventory
        if current_inventory < quantity:
            print(f"Insufficient inventory for product {product_id}. Required: {quantity}, Available: {current_inventory}")
            return False
        
        # Deduct inventory
        new_inventory = current_inventory - quantity
        
        # Update product
        response = supabase.table('products').update({
            'inventory_count': new_inventory,
            'in_stock': new_inventory > 0,  # Update stock status based on inventory
            'updated_at': datetime.now().isoformat()
        }).eq('id', product_id).execute()
        
        if response.data:
            print(f"Inventory deducted for product {product_id}: {current_inventory} -> {new_inventory}")
            return True
        
        return False
    except Exception as e:
        print(f"Error deducting inventory for product {product_id}: {e}")
        return False

def restore_inventory(product_id: int, quantity: int) -> bool:
    """
    Restore inventory for a product (used when order is cancelled)
    Returns True if successful, False otherwise
    """
    try:
        # Get current product
        product = get_product(product_id)
        if not product:
            print(f"Product {product_id} not found")
            return False
        
        current_inventory = product.get('inventory_count', 0)
        
        # Add back inventory
        new_inventory = current_inventory + quantity
        
        # Update product
        response = supabase.table('products').update({
            'inventory_count': new_inventory,
            'in_stock': True,  # If we're restoring, it should be in stock
            'updated_at': datetime.now().isoformat()
        }).eq('id', product_id).execute()
        
        if response.data:
            print(f"Inventory restored for product {product_id}: {current_inventory} -> {new_inventory}")
            return True
        
        return False
    except Exception as e:
        print(f"Error restoring inventory for product {product_id}: {e}")
        return False

def upload_category_cover_image(file_content: bytes, file_name: str) -> Optional[str]:
    """
    Upload a category cover image to Supabase Storage
    Returns the public URL of the uploaded image
    """
    try:
        # Create a unique file name
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_filename = f"cover_{timestamp}_{file_name}"
        
        # Upload to Supabase Storage (using the same bucket as category images)
        response = supabase.storage.from_("category-images").upload(
            path=unique_filename,
            file=file_content,
            file_options={"content-type": "image/jpeg"}  # Adjust based on file type
        )
        
        # Get the public URL
        if response:
            print("Category cover image uploaded successfully, getting public URL")
            public_url = supabase.storage.from_("category-images").get_public_url(unique_filename)
            print(f"Public URL: {public_url}")
            return public_url
        
        print("Category cover image upload failed, response:", response)
        return None
    except Exception as e:
        print(f"Error uploading category cover image: {e}")
        return None



# SUPPORT QUERIES
# Add these functions to your supabase_client.py file

# Support Queries functions
def create_support_query(query_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a new support query
    """
    try:
        # Set created_at and updated_at
        now = datetime.now().isoformat()
        query_data['created_at'] = now
        query_data['updated_at'] = now
        
        # Set default status if not provided
        if 'status' not in query_data:
            query_data['status'] = 'open'
            
        # Set default priority if not provided
        if 'priority' not in query_data:
            query_data['priority'] = 'medium'
        
        # Insert into database
        response = supabase.table('support_queries').insert(query_data).execute()
        
        if response.data and len(response.data) > 0:
            print(f"✅ Support query created with ID: {response.data[0].get('id')}")
            return response.data[0]
        
        print("❌ Failed to create support query")
        return None
        
    except Exception as e:
        print(f"❌ Error creating support query: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_all_support_queries() -> List[Dict[str, Any]]:
    """
    Get all support queries for admin view
    """
    try:
        response = supabase.table('support_queries').select('*').order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Error getting support queries: {e}")
        return []

def get_support_query(query_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a specific support query by ID
    """
    try:
        response = supabase.table('support_queries').select('*').eq('id', query_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting support query {query_id}: {e}")
        return None

def update_support_query_status(query_id: int, status: str, admin_notes: str = None) -> Optional[Dict[str, Any]]:
    """
    Update support query status and admin notes
    """
    try:
        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }
        
        if admin_notes:
            update_data['admin_notes'] = admin_notes
            
        if status == 'resolved':
            update_data['resolved_at'] = datetime.now().isoformat()
        
        response = supabase.table('support_queries').update(update_data).eq('id', query_id).execute()
        
        if response.data:
            return response.data[0]
        return None
        
    except Exception as e:
        print(f"Error updating support query {query_id}: {e}")
        return None

def get_support_queries_by_status(status: str) -> List[Dict[str, Any]]:
    """
    Get support queries filtered by status
    """
    try:
        response = supabase.table('support_queries').select('*').eq('status', status).order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Error getting support queries by status {status}: {e}")
        return []

def get_customer_support_queries(customer_email: str) -> List[Dict[str, Any]]:
    """
    Get support queries for a specific customer
    """
    try:
        response = supabase.table('support_queries').select('*').eq('customer_email', customer_email).order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Error getting support queries for customer {customer_email}: {e}")
        return []


# Add these functions to your db/supabase_client.py file

def get_user_wishlist(user_id: int) -> List[Dict[str, Any]]:
    """
    Get all wishlist items for a user
    """
    try:
        response = supabase.table('user_wishlist').select('*').eq('user_id', user_id).execute()
        return response.data
    except Exception as e:
        print(f"Error getting user wishlist: {e}")
        return []

def get_user_wishlist_with_products(user_id: int) -> List[Dict[str, Any]]:
    """
    Get wishlist items with full product details for a user
    """
    try:
        response = supabase.table('user_wishlist') \
            .select('*, products(*, categories(name))') \
            .eq('user_id', user_id) \
            .execute()
        
        # Extract products from the wishlist items
        products = []
        for item in response.data:
            if item.get('products'):
                products.append(item['products'])
        
        return products
    except Exception as e:
        print(f"Error getting user wishlist with products: {e}")
        return []

def add_to_user_wishlist(user_id: int, product_id: int) -> bool:
    """
    Add a product to user's wishlist
    """
    try:
        # Check if item already exists
        existing = supabase.table('user_wishlist') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('product_id', product_id) \
            .execute()
        
        if existing.data:
            print(f"Product {product_id} already in wishlist for user {user_id}")
            return True
        
        # Add new item
        response = supabase.table('user_wishlist').insert({
            'user_id': user_id,
            'product_id': product_id,
            'created_at': datetime.now().isoformat()
        }).execute()
        
        return bool(response.data)
    except Exception as e:
        print(f"Error adding to user wishlist: {e}")
        return False

def remove_from_user_wishlist(user_id: int, product_id: int) -> bool:
    """
    Remove a product from user's wishlist
    """
    try:
        response = supabase.table('user_wishlist') \
            .delete() \
            .eq('user_id', user_id) \
            .eq('product_id', product_id) \
            .execute()
        
        return True  # Supabase delete always returns success if no error
    except Exception as e:
        print(f"Error removing from user wishlist: {e}")
        return False

def clear_user_wishlist(user_id: int) -> bool:
    """
    Clear all items from user's wishlist
    """
    try:
        response = supabase.table('user_wishlist') \
            .delete() \
            .eq('user_id', user_id) \
            .execute()
        
        return True
    except Exception as e:
        print(f"Error clearing user wishlist: {e}")
        return False

def is_in_user_wishlist(user_id: int, product_id: int) -> bool:
    """
    Check if a product is in user's wishlist
    """
    try:
        response = supabase.table('user_wishlist') \
            .select('id') \
            .eq('user_id', user_id) \
            .eq('product_id', product_id) \
            .execute()
        
        return len(response.data) > 0
    except Exception as e:
        print(f"Error checking wishlist: {e}")
        return False

def get_wishlist_count(user_id: int) -> int:
    """
    Get count of items in user's wishlist
    """
    try:
        response = supabase.table('user_wishlist') \
            .select('id', count='exact') \
            .eq('user_id', user_id) \
            .execute()
        
        return response.count or 0
    except Exception as e:
        print(f"Error getting wishlist count: {e}")
        return 0

def sync_guest_wishlist_to_user(user_id: int, guest_wishlist_ids: List[int]) -> bool:
    """
    Sync guest wishlist items to authenticated user's wishlist
    """
    try:
        # Get existing wishlist items
        existing_response = supabase.table('user_wishlist') \
            .select('product_id') \
            .eq('user_id', user_id) \
            .execute()
        
        existing_product_ids = [item['product_id'] for item in existing_response.data]
        
        # Find new items to add
        new_items = []
        for product_id in guest_wishlist_ids:
            if product_id not in existing_product_ids:
                new_items.append({
                    'user_id': user_id,
                    'product_id': product_id,
                    'created_at': datetime.now().isoformat()
                })
        
        # Insert new items if any
        if new_items:
            response = supabase.table('user_wishlist').insert(new_items).execute()
            return bool(response.data)
        
        return True
    except Exception as e:
        print(f"Error syncing guest wishlist: {e}")
        return False

        