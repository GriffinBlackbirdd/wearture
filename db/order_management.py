"""
Order management functions for WEARXTURE
"""
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
from db.supabase_client import supabase, deduct_inventory, restore_inventory, get_product

def create_order(order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a new order in the database and deduct inventory
    """
    try:
        # Prepare order data for database
        now = datetime.now().isoformat()
        
        # Create base order record
        order_record = {
            "order_id": order_data["order_id"],
            "user_email": order_data["user_email"],
            "phone": order_data["phone"],
            "delivery_address": json.dumps(order_data["delivery_address"]),
            "items": json.dumps(order_data["items"]),
            "subtotal": float(order_data.get("subtotal", 0)),
            "delivery_charge": float(order_data.get("delivery_charge", 0)),
            "tax": float(order_data.get("tax", 0)),
            "total_amount": float(order_data["total_amount"]),
            "payment_method": order_data["payment_method"],
            "payment_status": order_data.get("payment_status", "pending"),
            "order_status": order_data.get("order_status", "pending"),
            "razorpay_order_id": order_data.get("razorpay_order_id"),
            "razorpay_payment_id": order_data.get("razorpay_payment_id"),
            "created_at": now,
            "updated_at": now
        }
        
        # Add COD-specific fields if they exist
        if order_data.get("payment_method") == "cod":
            cod_info = {
                "cod_fee": order_data.get("cod_fee", 80),
                "cod_remaining": order_data.get("cod_remaining", 0),
                "cod_status": order_data.get("cod_status", "fee_pending")
            }
            order_record["payment_status"] = "cod_fee_pending"
        
        print(f"Creating order: {order_record['order_id']}")
        
        # First, check inventory for all items
        items = order_data.get("items", [])
        inventory_check_failed = False
        insufficient_products = []
        
        for item in items:
            product_id = item.get("product_id") or item.get("id")
            quantity = item.get("quantity", 1)
            
            if product_id:
                product = get_product(product_id)
                if product:
                    current_inventory = product.get('inventory_count', 0)
                    if current_inventory < quantity:
                        inventory_check_failed = True
                        insufficient_products.append({
                            "name": item.get("name"),
                            "required": quantity,
                            "available": current_inventory
                        })
        
        if inventory_check_failed:
            error_msg = "Insufficient inventory: " + ", ".join([
                f"{p['name']} (need {p['required']}, have {p['available']})" 
                for p in insufficient_products
            ])
            print(f"Order creation failed: {error_msg}")
            return {"error": error_msg, "success": False}
        
        # Insert into database
        response = supabase.table('orders').insert(order_record).execute()
        
        if response.data:
            created_order = response.data[0]
            print(f"Order created successfully: {created_order['order_id']}")
            
            # Deduct inventory for each item
            inventory_deduction_failed = False
            deducted_items = []
            
            for item in items:
                product_id = item.get("product_id") or item.get("id")
                quantity = item.get("quantity", 1)
                
                if product_id:
                    success = deduct_inventory(product_id, quantity)
                    if success:
                        deducted_items.append((product_id, quantity))
                    else:
                        inventory_deduction_failed = True
                        # Restore inventory for previously deducted items
                        for deducted_id, deducted_qty in deducted_items:
                            restore_inventory(deducted_id, deducted_qty)
                        break
            
            if inventory_deduction_failed:
                # Delete the order if inventory deduction failed
                supabase.table('orders').delete().eq('order_id', created_order['order_id']).execute()
                return {"error": "Failed to deduct inventory", "success": False}
            
            return created_order
        else:
            print(f"Error creating order: No data returned")
            return None
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    """
    Get an order by ID
    
    Args:
        order_id: Order ID
    
    Returns:
        Order data or None if not found
    """
    try:
        response = supabase.table('orders').select("*").eq('order_id', order_id).execute()
        
        if response.data:
            order = response.data[0]
            # Parse JSON fields
            if order.get('delivery_address'):
                order['delivery_address'] = json.loads(order['delivery_address'])
            if order.get('items'):
                order['items'] = json.loads(order['items'])
            return order
        return None
    except Exception as e:
        print(f"Error getting order {order_id}: {e}")
        return None

def update_order_payment_status(order_id: str, payment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update order payment status
    
    Args:
        order_id: Order ID
        payment_data: Payment information including:
            - payment_status: New payment status
            - razorpay_payment_id: Razorpay payment ID
            - razorpay_signature: Payment signature
    
    Returns:
        Updated order or None if failed
    """
    try:
        update_data = {
            "payment_status": payment_data["payment_status"],
            "razorpay_payment_id": payment_data.get("razorpay_payment_id"),
            "razorpay_signature": payment_data.get("razorpay_signature"),
            "updated_at": datetime.now().isoformat()
        }
        
        # If payment is successful, update order status
        if payment_data["payment_status"] == "completed":
            update_data["order_status"] = "confirmed"
        
        response = supabase.table('orders').update(update_data).eq('order_id', order_id).execute()
        
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error updating order payment status: {e}")
        return None

def get_user_orders(user_email: str) -> List[Dict[str, Any]]:
    """
    Get all orders for a user
    
    Args:
        user_email: User's email address
    
    Returns:
        List of orders
    """
    try:
        response = supabase.table('orders').select("*").eq('user_email', user_email).order('created_at', desc=True).execute()
        
        orders = response.data or []
        
        # Parse JSON fields
        for order in orders:
            if order.get('delivery_address'):
                order['delivery_address'] = json.loads(order['delivery_address'])
            if order.get('items'):
                order['items'] = json.loads(order['items'])
        
        return orders
    except Exception as e:
        print(f"Error getting user orders: {e}")
        return []

def get_pending_orders() -> List[Dict[str, Any]]:
    """
    Get all pending orders (admin function)
    
    Returns:
        List of pending orders
    """
    try:
        response = supabase.table('orders').select("*").eq('order_status', 'pending').order('created_at', desc=True).execute()
        
        orders = response.data or []
        
        # Parse JSON fields
        for order in orders:
            if order.get('delivery_address'):
                order['delivery_address'] = json.loads(order['delivery_address'])
            if order.get('items'):
                order['items'] = json.loads(order['items'])
        
        return orders
    except Exception as e:
        print(f"Error getting pending orders: {e}")
        return []


def update_order_status(order_id: str, status: str, notes: str = "") -> Optional[Dict[str, Any]]:
    """
    Update order status and handle inventory management
    """
    try:
        # Get current order
        current_order = get_order(order_id)
        if not current_order:
            return None
        
        current_status = current_order.get('order_status')
        
        # Update order
        update_data = {
            "order_status": status,
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table('orders').update(update_data).eq('order_id', order_id).execute()
        
        if response.data:
            # If order is cancelled, restore inventory
            if status == 'cancelled' and current_status != 'cancelled':
                items = current_order.get('items', [])
                if isinstance(items, str):
                    try:
                        items = json.loads(items)
                    except:
                        items = []
                
                for item in items:
                    product_id = item.get("product_id") or item.get("id")
                    quantity = item.get("quantity", 1)
                    
                    if product_id:
                        restore_inventory(product_id, quantity)
                        print(f"Restored {quantity} units of product {product_id} for cancelled order {order_id}")
            
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error updating order status: {e}")
        return None

def get_all_orders() -> List[Dict[str, Any]]:
    """
    Get all orders (admin function)
    
    Returns:
        List of all orders
    """
    try:
        response = supabase.table('orders').select("*").order('created_at', desc=True).execute()
        
        orders = response.data or []
        
        # Parse JSON fields
        for order in orders:
            if order.get('delivery_address'):
                order['delivery_address'] = json.loads(order['delivery_address'])
            if order.get('items'):
                order['items'] = json.loads(order['items'])
        
        return orders
    except Exception as e:
        print(f"Error getting all orders: {e}")
        return []