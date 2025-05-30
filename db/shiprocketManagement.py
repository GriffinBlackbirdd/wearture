"""
Updated shiprocketManagement.py with better error handling and pickup location management
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ShiprocketClient:
    def __init__(self):
        self.base_url = "https://apiv2.shiprocket.in/v1/external"
        self.email = os.getenv("SHIPROCKET_EMAIL")
        self.password = os.getenv("SHIPROCKET_PASSWORD")
        self.token = None
        self.token_expires_at = None
        self._pickup_locations = None  # Cache pickup locations
        
    def authenticate(self) -> bool:
        """
        Authenticate with Shiprocket API and get access token
        Returns True if successful, False otherwise
        """
        try:
            auth_url = f"{self.base_url}/auth/login"
            auth_data = {
                "email": self.email,
                "password": self.password
            }
            
            print(f"🔑 Authenticating with Shiprocket...")
            response = requests.post(auth_url, json=auth_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                # Token typically expires in 10 days
                self.token_expires_at = datetime.now() + timedelta(days=9)
                print("✅ Shiprocket authentication successful!")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
            return False
    
    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid authentication token
        """
        if not self.token or (self.token_expires_at and datetime.now() >= self.token_expires_at):
            return self.authenticate()
        return True
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers with authentication token
        """
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
    
    def get_pickup_locations(self) -> List[Dict[str, Any]]:
        """
        Get all pickup locations configured in Shiprocket (with caching)
        """
        # Return cached locations if available
        if self._pickup_locations is not None:
            return self._pickup_locations
            
        try:
            if not self._ensure_authenticated():
                return []
            
            url = f"{self.base_url}/settings/company/pickup"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                locations = data.get("data", {}).get("shipping_address", [])
                
                print(f"📍 Found {len(locations)} pickup locations:")
                for i, loc in enumerate(locations):
                    print(f"  {i+1}. '{loc.get('pickup_location')}' - {loc.get('city')}, {loc.get('state')}")
                
                # Cache the locations
                self._pickup_locations = locations
                return locations
            else:
                print(f"❌ Failed to get pickup locations: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting pickup locations: {str(e)}")
            return []
    
    def get_primary_pickup_location(self) -> Optional[str]:
        """
        Get the primary (first) pickup location name
        """
        locations = self.get_pickup_locations()
        if locations:
            primary_location = locations[0].get('pickup_location')
            print(f"🎯 Using primary pickup location: '{primary_location}'")
            return primary_location
        return None
    
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new order in Shiprocket with enhanced error handling
        """
        try:
            if not self._ensure_authenticated():
                return {"success": False, "error": "Authentication failed"}
            
            url = f"{self.base_url}/orders/create/adhoc"
            
            # Validate required fields
            required_fields = [
                "order_id", "order_date", "billing_customer_name", 
                "billing_address", "billing_city", "billing_pincode",
                "billing_state", "billing_country", "billing_email", 
                "billing_phone", "order_items", "pickup_location"
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in order_data or not order_data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return {
                    "success": False, 
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }
            
            # Validate pickup location
            pickup_location = order_data.get("pickup_location")
            valid_locations = [loc.get('pickup_location') for loc in self.get_pickup_locations()]
            
            if pickup_location not in valid_locations:
                return {
                    "success": False,
                    "error": f"Invalid pickup location '{pickup_location}'. Valid locations: {valid_locations}"
                }
            
            print(f"📦 Creating Shiprocket order with pickup location: '{pickup_location}'")
            
            response = requests.post(url, json=order_data, headers=self._get_headers())
            
            if response.status_code == 200:
                result = response.json()
                
                # Check if the response indicates success
                if result.get("status_code") == 1:
                    return {
                        "success": True,
                        "order_id": result.get("order_id"),
                        "shipment_id": result.get("shipment_id"),
                        "status": result.get("status"),
                        "status_code": result.get("status_code"),
                        "message": "Order created successfully",
                        "raw_response": result
                    }
                else:
                    # Shiprocket returned an error in the response
                    error_message = result.get("message", "Unknown error")
                    print(f"❌ Shiprocket API error: {error_message}")
                    
                    # If it's a pickup location error, provide helpful info
                    if "pickup location" in error_message.lower():
                        valid_locations = [loc.get('pickup_location') for loc in self.get_pickup_locations()]
                        error_message += f" Valid locations: {valid_locations}"
                    
                    return {
                        "success": False,
                        "error": error_message,
                        "details": result,
                        "valid_pickup_locations": valid_locations
                    }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": "Order creation error",
                "details": str(e)
            }
    
    def track_shipment(self, shipment_id: str) -> Dict[str, Any]:
        """
        Track a shipment by ID
        """
        try:
            if not self._ensure_authenticated():
                return {"success": False, "error": "Authentication failed"}
            
            url = f"{self.base_url}/courier/track/shipment/{shipment_id}"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"Tracking failed: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": "Tracking error",
                "details": str(e)
            }


def format_wearxture_order_for_shiprocket(wearxture_order: Dict[str, Any], 
                                        pickup_location: str = None) -> Dict[str, Any]:
    """
    Convert WEARXTURE order format to Shiprocket order format with automatic pickup location
    """
    try:
        # Get pickup location if not provided
        if not pickup_location:
            client = ShiprocketClient()
            pickup_location = client.get_primary_pickup_location()
            
        if not pickup_location:
            raise ValueError("No pickup location available")
        
        # Parse delivery address
        delivery_address = wearxture_order.get("delivery_address", {})
        if isinstance(delivery_address, str):
            import json
            delivery_address = json.loads(delivery_address)
        
        # Parse items
        items = wearxture_order.get("items", [])
        if isinstance(items, str):
            import json
            items = json.loads(items)
        
        # Check if this is a COD order
        is_cod_order = wearxture_order.get("payment_method") == "cod"
        
        # Format order items for Shiprocket
        shiprocket_items = []
        for item in items:
            # Get SKU from product if available
            sku = f"SKU-{item.get('id', 'unknown')}"
            
            # Try to get actual SKU from database if product_id is available
            try:
                product_id = item.get('product_id') or item.get('id')
                if product_id:
                    from db.supabase_client import get_product
                    product_details = get_product(product_id)
                    if product_details and product_details.get('sku'):
                        sku = product_details.get('sku')
            except:
                pass  # Use default SKU if database lookup fails
            
            # Format product name with size information
            product_name = item.get("name", "Product")
            size = item.get("size")
            
            # Include size in product name if available
            if size and size.strip() and size.lower() not in ['standard', 'one size', 'default']:
                product_name = f"{product_name} (Size: {size})"
            
            # Calculate selling price - for COD, reduce each item's price proportionally
            original_price = item.get("price", 0)
            item_quantity = item.get("quantity", 1)
            
            if is_cod_order:
                # Calculate the proportional reduction for this item
                total_cart_value = sum(it.get("price", 0) * it.get("quantity", 1) for it in items)
                if total_cart_value > 0:
                    # Proportionally reduce each item's price to account for ₹80 COD fee
                    cod_reduction_per_item = (80 / total_cart_value) * original_price
                    adjusted_price = max(0, original_price - cod_reduction_per_item)
                else:
                    adjusted_price = original_price
            else:
                adjusted_price = original_price
            
            shiprocket_items.append({
                "name": product_name,  # Now includes size information
                "sku": sku,
                "units": item_quantity,
                "selling_price": str(int(adjusted_price)),
                "discount": "",
                "tax": "",
                "hsn": 441122  # Default HSN code for textiles
            })
        
        # Calculate dimensions and weight
        total_items = sum(item.get("quantity", 1) for item in items)
        estimated_weight = max(0.5, total_items * 0.3)  # Minimum 0.5kg, 0.3kg per item
        
        # Get customer name from delivery address or email
        customer_name = delivery_address.get("name") or delivery_address.get("first_name")
        if not customer_name:
            # Extract name from email as fallback
            email = wearxture_order.get("user_email", "")
            customer_name = email.split("@")[0] if email else "Customer"
        
        # Calculate subtotal for Shiprocket (adjusted for COD if needed)
        shiprocket_subtotal = sum(int(item["selling_price"]) * item["units"] for item in shiprocket_items)
        
        # Format the order
        shiprocket_order = {
            "order_id": wearxture_order.get("order_id"),
            "order_date": datetime.now().strftime("%Y-%m-%d %H:%M"),  # Use current time
            "pickup_location": pickup_location,  # Use the provided pickup location
            "billing_customer_name": customer_name,
            "billing_last_name": "",
            "billing_address": delivery_address.get("address", ""),
            "billing_city": delivery_address.get("city", ""),
            "billing_pincode": delivery_address.get("pincode", ""),
            "billing_state": delivery_address.get("state", ""),
            "billing_country": delivery_address.get("country", "India"),
            "billing_email": wearxture_order.get("user_email", ""),
            "billing_phone": wearxture_order.get("phone", ""),
            "shipping_is_billing": True,
            "order_items": shiprocket_items,
            "payment_method": "Prepaid" if wearxture_order.get("payment_method") != "cod" else "COD",
            "shipping_charges": int(wearxture_order.get("delivery_charge", 0)),
            "giftwrap_charges": 0,
            "transaction_charges": 0,
            "total_discount": 0,
            "sub_total": shiprocket_subtotal,  # Use adjusted subtotal
            "length": 25,  # Default dimensions in cm
            "breadth": 20,
            "height": 10,
            "weight": estimated_weight
        }
        
        print(f"📋 Formatted Shiprocket order:")
        print(f"   Order ID: {shiprocket_order['order_id']}")
        print(f"   Pickup Location: '{shiprocket_order['pickup_location']}'")
        print(f"   Customer: {shiprocket_order['billing_customer_name']}")
        print(f"   Payment Method: {shiprocket_order['payment_method']}")
        print(f"   Items: {len(shiprocket_items)}")
        for item in shiprocket_items:
            print(f"     - {item['name']} (Qty: {item['units']}, Price: ₹{item['selling_price']})")  # This will now show adjusted prices
        print(f"   Subtotal: ₹{shiprocket_order['sub_total']}")
        if is_cod_order:
            original_total = int(wearxture_order.get("subtotal", 0))
            print(f"   Note: COD order - Original total: ₹{original_total}, Adjusted total: ₹{shiprocket_subtotal} (₹80 COD fee deducted)")
        
        return shiprocket_order
        
    except Exception as e:
        print(f"❌ Error formatting order for Shiprocket: {str(e)}")
        return {}


def test_shiprocket_integration():
    """
    Enhanced test function to verify Shiprocket integration
    """
    print("🚀 Testing Shiprocket Integration...")
    
    client = ShiprocketClient()
    
    # Test authentication
    if not client.authenticate():
        print("❌ Authentication failed")
        return False
    
    # Test getting pickup locations
    pickup_locations = client.get_pickup_locations()
    if not pickup_locations:
        print("❌ No pickup locations found")
        return False
    
    print(f"✅ Found {len(pickup_locations)} pickup locations")
    
    # Get primary pickup location
    primary_location = client.get_primary_pickup_location()
    if primary_location:
        print(f"✅ Primary pickup location: '{primary_location}'")
    
    # Test courier rates (optional)
    try:
        if pickup_locations:
            pickup_pincode = pickup_locations[0].get("pin_code", "244921")
            rates = client.get_courier_rates(pickup_pincode, "400001", 0.5)
            print(f"🚚 Found {len(rates)} available couriers for test route")
    except Exception as e:
        print(f"⚠️ Courier rates test failed: {e}")
    
    print("✅ Shiprocket integration test completed successfully!")
    return True
