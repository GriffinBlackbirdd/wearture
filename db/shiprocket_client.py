"""
Shiprocket API integration for WEARXTURE
Complete implementation with automatic shipping capabilities using official API endpoints
"""
import requests
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Shiprocket configuration
SHIPROCKET_EMAIL = os.getenv("SHIPROCKET_EMAIL")
SHIPROCKET_PASSWORD = os.getenv("SHIPROCKET_PASSWORD")
SHIPROCKET_BASE_URL = "https://apiv2.shiprocket.in/v1/external"

class ShiprocketClient:
    def __init__(self):
        self.token = None
        self.headers = {
            'Content-Type': 'application/json'
        }
    
    def get_auth_token(self):
        """Get authentication token from Shiprocket"""
        try:
            if not SHIPROCKET_EMAIL or not SHIPROCKET_PASSWORD:
                print("Shiprocket credentials not configured")
                return None
            
            auth_url = f"{SHIPROCKET_BASE_URL}/auth/login"
            auth_data = {
                "email": SHIPROCKET_EMAIL,
                "password": SHIPROCKET_PASSWORD
            }
            
            response = requests.post(auth_url, json=auth_data)
            
            if response.status_code == 200:
                result = response.json()
                self.token = result.get('token')
                self.headers['Authorization'] = f'Bearer {self.token}'
                print("Shiprocket authentication successful")
                return self.token
            else:
                print(f"Shiprocket auth failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting Shiprocket token: {e}")
            return None
    
    def create_order(self, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a shipment order in Shiprocket
        
        Args:
            order_data: Order information from your database
            
        Returns:
            Shiprocket order response or None
        """
        try:
            # Get token if not available
            if not self.token:
                if not self.get_auth_token():
                    return None
            
            # Parse delivery address
            address = order_data.get('delivery_address', {})
            if isinstance(address, str):
                address = json.loads(address)
            
            # Parse order items
            items = order_data.get('items', [])
            if isinstance(items, str):
                items = json.loads(items)
            
            # Prepare order items for Shiprocket
            order_items = []
            for item in items:
                order_items.append({
                    "name": item.get('name', 'Product'),
                    "sku": item.get('sku', 'SKU001'),
                    "units": item.get('quantity', 1),
                    "selling_price": item.get('price', 0),
                    "discount": 0,
                    "tax": 0,
                    "hsn": 621210  # HSN code for textiles/clothing
                })
            
            # Prepare Shiprocket order payload
            shiprocket_order = {
                "order_id": order_data.get('order_id'),
                "order_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "pickup_location": "Primary",  # You'll set this up in Shiprocket dashboard
                "channel_id": "",
                "comment": "WEARXTURE Order",
                "billing_customer_name": f"{address.get('first_name', '')} {address.get('last_name', '')}".strip() or "Customer",
                "billing_last_name": "",
                "billing_address": address.get('address', ''),
                "billing_address_2": "",
                "billing_city": address.get('city', ''),
                "billing_pincode": address.get('pincode', ''),
                "billing_state": address.get('state', ''),
                "billing_country": address.get('country', 'India'),
                "billing_email": order_data.get('user_email', ''),
                "billing_phone": order_data.get('phone', ''),
                "shipping_is_billing": True,
                "shipping_customer_name": "",
                "shipping_last_name": "",
                "shipping_address": "",
                "shipping_address_2": "",
                "shipping_city": "",
                "shipping_pincode": "",
                "shipping_country": "",
                "shipping_state": "",
                "shipping_email": "",
                "shipping_phone": "",
                "order_items": order_items,
                "payment_method": "Prepaid" if order_data.get('payment_status') == 'completed' else "COD",
                "shipping_charges": order_data.get('delivery_charge', 0),
                "giftwrap_charges": 0,
                "transaction_charges": 0,
                "total_discount": 0,
                "sub_total": order_data.get('subtotal', 0),
                "length": 15,  # Default dimensions in cm
                "breadth": 12,
                "height": 8,
                "weight": 0.5  # Default weight in kg
            }
            
            # Create order in Shiprocket
            create_url = f"{SHIPROCKET_BASE_URL}/orders/create/adhoc"
            response = requests.post(create_url, json=shiprocket_order, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                print(f"Shiprocket order created successfully: {result}")
                return result
            else:
                print(f"Shiprocket order creation failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error creating Shiprocket order: {e}")
            return None
    
    def track_shipment(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Track a shipment by order ID"""
        try:
            if not self.token:
                if not self.get_auth_token():
                    return None
            
            track_url = f"{SHIPROCKET_BASE_URL}/courier/track/shipment/{order_id}"
            response = requests.get(track_url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Tracking failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error tracking shipment: {e}")
            return None
    
    def get_courier_rates(self, pickup_pincode: str, delivery_pincode: str, weight: float = 0.5) -> Optional[Dict[str, Any]]:
        """Get available courier rates"""
        try:
            if not self.token:
                if not self.get_auth_token():
                    return None
            
            rates_url = f"{SHIPROCKET_BASE_URL}/courier/serviceability/"
            params = {
                "pickup_postcode": pickup_pincode,
                "delivery_postcode": delivery_pincode,
                "weight": weight,
                "cod": 1
            }
            
            response = requests.get(rates_url, params=params, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Rate check failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting courier rates: {e}")
            return None
    
    def get_courier_serviceability(self, pickup_pincode: str, delivery_pincode: str, weight: float = 0.5, cod: bool = False) -> Optional[Dict[str, Any]]:
        """Get available couriers for a route using official API"""
        try:
            if not self.token:
                if not self.get_auth_token():
                    return None
            
            # Use official API endpoint from documentation
            serviceability_url = f"{SHIPROCKET_BASE_URL}/courier/serviceability/"
            params = {
                "pickup_postcode": pickup_pincode,
                "delivery_postcode": delivery_pincode,
                "weight": weight,
                "cod": 1 if cod else 0
            }
            
            response = requests.get(serviceability_url, params=params, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Serviceability check failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error checking serviceability: {e}")
            return None

    def get_courier_list(self) -> Optional[Dict[str, Any]]:
        """Get list of available couriers using official API"""
        try:
            if not self.token:
                if not self.get_auth_token():
                    return None
            
            # Use correct endpoint from documentation
            courier_url = f"{SHIPROCKET_BASE_URL}/courier/courierListWithCounts"
            response = requests.get(courier_url, headers=self.headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get courier list: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting courier list: {e}")
            return None

    def select_best_courier(self, couriers_data: Dict[str, Any], is_cod: bool = False) -> Optional[Dict[str, Any]]:
        """Select the best courier from available options"""
        try:
            available_couriers = couriers_data.get('data', {}).get('available_courier_companies', [])
            
            if not available_couriers:
                print("No available couriers found")
                return None
            
            print(f"Found {len(available_couriers)} available couriers")
            
            # Filter couriers based on COD requirement
            if is_cod:
                # Filter only COD-enabled couriers
                cod_couriers = [c for c in available_couriers if c.get('cod') == 1]
                if not cod_couriers:
                    print("No COD-enabled couriers found")
                    return None
                available_couriers = cod_couriers
                print(f"Filtered to {len(available_couriers)} COD-enabled couriers")
            
            # Selection logic
            if is_cod:
                # For COD: Pick cheapest reliable courier
                best_courier = min(available_couriers, key=lambda x: float(x.get('rate', 999999)))
                selection_criteria = f"cheapest (₹{best_courier.get('rate')})"
            else:
                # For Prepaid: Pick fastest courier (lowest delivery days)
                # Use estimated_delivery_days instead of etd
                def get_delivery_days(courier):
                    try:
                        return int(courier.get('estimated_delivery_days', 99))
                    except (ValueError, TypeError):
                        return 99
                
                best_courier = min(available_couriers, key=get_delivery_days)
                selection_criteria = f"fastest ({best_courier.get('estimated_delivery_days')} days)"
            
            print(f"Selected courier: {best_courier.get('courier_name')} - Rate: ₹{best_courier.get('rate')} - ETA: {best_courier.get('estimated_delivery_days')} days ({selection_criteria})")
            
            return best_courier
            
        except Exception as e:
            print(f"Error selecting courier: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_order_details(self, shiprocket_order_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed order information from Shiprocket"""
        try:
            if not self.token:
                if not self.get_auth_token():
                    return None
            
            order_url = f"{SHIPROCKET_BASE_URL}/orders/show/{shiprocket_order_id}"
            response = requests.get(order_url, headers=self.headers)
            
            print(f"📋 Order details response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                order_data = result.get('data', {})
                print(f"📋 Order status: {order_data.get('status')}")
                print(f"📋 Order payment method: {order_data.get('payment_method')}")
                print(f"📋 Order total: {order_data.get('total')}")
                return result
            else:
                print(f"Failed to get order details: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting order details: {e}")
            return None

    def get_shipment_id_from_order(self, shiprocket_order_id: str) -> Optional[str]:
        """Get shipment ID from order ID - with shipment creation if needed"""
        try:
            if not self.token:
                if not self.get_auth_token():
                    return None
            
            # First, try to get existing shipment ID
            order_details = self.get_order_details(shiprocket_order_id)
            
            if order_details and order_details.get('data'):
                order_data = order_details['data']
                
                # Check if shipments exist in the order
                shipments = order_data.get('shipments', [])
                if shipments and len(shipments) > 0:
                    try:
                        shipment_id = str(shipments[0].get('id'))
                        print(f"📦 Found existing shipment ID: {shipment_id}")
                        return shipment_id
                    except (KeyError, IndexError, TypeError):
                        print("⚠️ Shipments array exists but couldn't extract ID")
                
                # Alternative: sometimes shipment_id is directly in order data
                shipment_id = order_data.get('shipment_id')
                if shipment_id:
                    print(f"📦 Found direct shipment ID: {str(shipment_id)}")
                    return str(shipment_id)
            
            # If no shipment found, try to create one
            print("🔄 No existing shipment found, attempting to create shipment...")
            return self.create_shipment_from_order(shiprocket_order_id)
            
        except Exception as e:
            print(f"Error getting shipment ID: {e}")
            import traceback
            traceback.print_exc()
            return None

    def assign_courier_to_order_direct(self, shiprocket_order_id: str, courier_id: int) -> Optional[Dict[str, Any]]:
        """Try to assign courier directly to order (alternative method)"""
        try:
            if not self.token:
                if not self.get_auth_token():
                    return None
            
            # Try direct courier assignment to order
            assignment_data = {
                "order_id": int(shiprocket_order_id),
                "courier_company_id": courier_id
            }
            
            print(f"🔍 Direct order assignment data: {assignment_data}")
            
            # Try the alternative assignment endpoint
            assign_url = f"{SHIPROCKET_BASE_URL}/courier/assign"
            response = requests.post(assign_url, json=assignment_data, headers=self.headers)
            
            print(f"📤 Direct assignment response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Direct courier assignment successful")
                return result
            else:
                print(f"❌ Direct assignment failed: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error in direct courier assignment: {e}")
            return None
    def assign_awb_to_shipment(self, shipment_id: str, courier_id: int) -> Optional[Dict[str, Any]]:
        """Generate AWB for shipment using correct API endpoint from documentation"""
        try:
            if not self.token:
                if not self.get_auth_token():
                    return None
            
            # Use the correct payload format from documentation
            assignment_data = {
                "shipment_id": shipment_id,
                "courier_id": str(courier_id)  # Convert to string as per docs
            }
            
            print(f"🔍 AWB assignment data: {assignment_data}")
            
            # Use the correct endpoint from documentation
            assign_url = f"{SHIPROCKET_BASE_URL}/courier/assign/awb"
            response = requests.post(assign_url, json=assignment_data, headers=self.headers)
            
            print(f"📤 AWB Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                awb_code = result.get('awb_code')
                if awb_code:
                    print(f"✅ AWB generated: {awb_code}")
                    return result
                else:
                    print(f"⚠️ Response received but no AWB code: {result}")
                    return result
            else:
                try:
                    error_response = response.json()
                    print(f"❌ AWB assignment error: {error_response}")
                    return {"error": error_response}
                except:
                    print(f"❌ AWB assignment error (raw): {response.text}")
                    return {"error": response.text}
                
        except Exception as e:
            print(f"Error assigning AWB to shipment: {e}")
            import traceback
            traceback.print_exc()
            return None

    def schedule_pickup_correct(self, shipment_id: str) -> bool:
        """Schedule pickup using correct API format from documentation"""
        try:
            if not self.token:
                if not self.get_auth_token():
                    return False
            
            # Use correct payload format from documentation
            pickup_data = {
                "shipment_id": [int(shipment_id)]  # Array of integers as per docs
            }
            
            print(f"🚚 Pickup request data: {pickup_data}")
            
            pickup_url = f"{SHIPROCKET_BASE_URL}/courier/generate/pickup"
            response = requests.post(pickup_url, json=pickup_data, headers=self.headers)
            
            print(f"📤 Pickup response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                print(f"✅ Pickup scheduled for shipment {shipment_id}")
                return True
            else:
                print(f"❌ Pickup scheduling failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error scheduling pickup: {e}")
            import traceback
            traceback.print_exc()
            return False

    # Keep the old schedule_pickup method for backward compatibility
    def schedule_pickup(self, shipment_id: str) -> bool:
        """Schedule pickup - calls the correct method"""
        return self.schedule_pickup_correct(shipment_id)

    def create_shipment_from_order(self, shiprocket_order_id: str) -> Optional[str]:
        """Create shipment from order and return shipment ID"""
        try:
            if not self.token:
                if not self.get_auth_token():
                    return None
            
            # Method 1: Try to create shipment using order ready-to-ship
            ready_to_ship_data = {
                "ids": [int(shiprocket_order_id)]
            }
            
            ready_url = f"{SHIPROCKET_BASE_URL}/orders/processing/ready-to-ship"
            response = requests.post(ready_url, json=ready_to_ship_data, headers=self.headers)
            
            print(f"📤 Ready to ship response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                print("✅ Order moved to READY TO SHIP status")
                
                # Wait a moment and then get the shipment ID
                import time
                time.sleep(2)
                
                # Get updated order details
                order_details = self.get_order_details(shiprocket_order_id)
                if order_details and order_details.get('data'):
                    order_data = order_details['data']
                    shipments = order_data.get('shipments', [])
                    if shipments and len(shipments) > 0:
                        shipment_id = str(shipments[0].get('id'))
                        print(f"📦 Shipment created with ID: {shipment_id}")
                        return shipment_id
            
            # Method 2: Alternative approach - direct shipment creation
            print("🔄 Trying alternative shipment creation method...")
            
            shipment_data = {
                "order_id": shiprocket_order_id
            }
            
            shipment_url = f"{SHIPROCKET_BASE_URL}/orders/{shiprocket_order_id}/shipments"
            response2 = requests.post(shipment_url, json=shipment_data, headers=self.headers)
            
            print(f"📤 Direct shipment creation: {response2.status_code} - {response2.text}")
            
            if response2.status_code == 200:
                result = response2.json()
                if result.get('data') and result['data'].get('shipment_id'):
                    shipment_id = str(result['data']['shipment_id'])
                    print(f"📦 Direct shipment created: {shipment_id}")
                    return shipment_id
            
            print("❌ Both shipment creation methods failed")
            return None
            
        except Exception as e:
            print(f"Error creating shipment: {e}")
            import traceback
            traceback.print_exc()
            return None



# Initialize the client
shiprocket_client = ShiprocketClient()

# Helper functions for easy integration
def create_shiprocket_order(order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Simple function to create a Shiprocket order
    Use this in your main.py after order creation
    """
    return shiprocket_client.create_order(order_data)

def track_order(order_id: str) -> Optional[Dict[str, Any]]:
    """
    Simple function to track an order
    """
    return shiprocket_client.track_shipment(order_id)

def get_shipping_rates(pickup_pin: str, delivery_pin: str, weight: float = 0.5) -> Optional[Dict[str, Any]]:
    """
    Get shipping rates between two pincodes
    """
    return shiprocket_client.get_courier_rates(pickup_pin, delivery_pin, weight)

def create_automatic_shipping(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Complete automatic shipping workflow with multiple fallback methods
    """
    try:
        print(f"🚀 Starting automatic shipping for order {order_data.get('order_id')}...")
        
        client = shiprocket_client
        shiprocket_order_id = order_data.get('shiprocket_order_id')
        
        if not shiprocket_order_id:
            return {"success": False, "error": "No Shiprocket order ID found"}
        
        # Get serviceability and select courier first
        address = order_data.get('delivery_address', {})
        if isinstance(address, str):
            import json
            address = json.loads(address)
        
        delivery_pincode = address.get('pincode')
        is_cod = order_data.get('payment_method') == 'cod'
        pickup_pincode = "244921"  # Update with your warehouse pincode
        
        print(f"📍 Checking serviceability: {pickup_pincode} → {delivery_pincode}")
        
        serviceability = client.get_courier_serviceability(
            pickup_pincode=pickup_pincode,
            delivery_pincode=delivery_pincode,
            weight=0.5,
            cod=is_cod
        )
        
        if not serviceability:
            return {"success": False, "error": "No courier serviceability"}
        
        best_courier = client.select_best_courier(serviceability, is_cod)
        if not best_courier:
            return {"success": False, "error": "No suitable courier found"}
        
        courier_id = best_courier.get('courier_company_id')
        
        # Try multiple methods for AWB generation
        print(f"📦 Trying multiple methods to assign courier {best_courier.get('courier_name')}...")
        
        # Method 1: Get/Create shipment ID and assign AWB
        print("🔄 Method 1: Shipment-based AWB assignment...")
        shipment_id = client.get_shipment_id_from_order(shiprocket_order_id)
        
        if shipment_id:
            awb_result = client.assign_awb_to_shipment(shipment_id, courier_id)
            
            if awb_result and (awb_result.get('awb_code') or awb_result.get('response', {}).get('data', {}).get('awb_code')):
                print("✅ Method 1 successful!")
                awb_code = awb_result.get('awb_code') or awb_result.get('response', {}).get('data', {}).get('awb_code')
                
                # Schedule pickup
                pickup_scheduled = client.schedule_pickup_correct(shipment_id)
                
                return {
                    "success": True,
                    "shipment_id": shipment_id,
                    "awb_code": awb_code,
                    "courier_name": best_courier.get('courier_name'),
                    "tracking_url": f"https://shiprocket.co/tracking/{awb_code}" if awb_code else None,
                    "pickup_scheduled": pickup_scheduled,
                    "shiprocket_order_id": shiprocket_order_id
                }
        
        # Method 2: Direct courier assignment to order
        print("🔄 Method 2: Direct order courier assignment...")
        direct_result = client.assign_courier_to_order_direct(shiprocket_order_id, courier_id)
        
        if direct_result:
            # Check if AWB was generated
            awb_code = None
            shipment_id_new = None
            
            # Extract AWB and shipment info from response
            if direct_result.get('awb_code'):
                awb_code = direct_result.get('awb_code')
            
            if direct_result.get('shipment_id'):
                shipment_id_new = str(direct_result.get('shipment_id'))
            
            if awb_code or shipment_id_new:
                print("✅ Method 2 successful!")
                
                # Try to schedule pickup if we have shipment ID
                pickup_scheduled = False
                if shipment_id_new:
                    pickup_scheduled = client.schedule_pickup_correct(shipment_id_new)
                
                return {
                    "success": True,
                    "shipment_id": shipment_id_new,
                    "awb_code": awb_code,
                    "courier_name": best_courier.get('courier_name'),
                    "tracking_url": f"https://shiprocket.co/tracking/{awb_code}" if awb_code else None,
                    "pickup_scheduled": pickup_scheduled,
                    "shiprocket_order_id": shiprocket_order_id
                }
        
        return {"success": False, "error": "All shipping methods failed", "details": "Tried shipment creation and direct assignment"}
            
    except Exception as e:
        print(f"❌ Auto shipping error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}