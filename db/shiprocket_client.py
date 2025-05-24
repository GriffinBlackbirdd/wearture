"""
Shiprocket API integration for WEARXTURE
Simple implementation for automated order pickup and delivery
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