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
    Update product with multiple images
    First image becomes the main image, rest are stored as additional images
    """
    try:
        # Get existing product
        product = get_product(product_id)
        if not product:
            return None
        
        # Parse existing attributes
        attributes = {}
        if 'attributes' in product and product['attributes']:
            try:
                attributes = json.loads(product['attributes']) if isinstance(product['attributes'], str) else product['attributes']
            except:
                attributes = {}
        
        # Update images
        update_data = {}
        if image_urls:
            # First image is the main image
            update_data['image_url'] = image_urls[0]
            
            # Rest are additional images
            if len(image_urls) > 1:
                attributes['additional_images'] = image_urls[1:]
            else:
                attributes['additional_images'] = []
            
            update_data['attributes'] = json.dumps(attributes)
        
        # Update product
        return update_product(product_id, update_data)
    except Exception as e:
        print(f"Error updating product images for {product_id}: {e}")
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