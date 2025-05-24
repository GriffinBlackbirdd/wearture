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


def update_shiprocket_info(order_id: str, shiprocket_data: Dict[str, Any]) -> bool:
    """Update order with Shiprocket information"""
    try:
        update_data = {
            "shiprocket_order_id": shiprocket_data.get("order_id"),
            "shiprocket_shipment_id": shiprocket_data.get("shipment_id"),
            "tracking_url": shiprocket_data.get("tracking_url"),
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table('orders').update(update_data).eq('order_id', order_id).execute()
        return bool(response.data)
    except Exception as e:
        print(f"Error updating Shiprocket info: {e}")
        return False
        
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

# Add these imports at the top of order_management.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.barcode import code128
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import base64

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.barcode import code128
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import base64
import os
from typing import Dict, Any
import json
from datetime import datetime

def generate_invoice_pdf(order_data: Dict[str, Any]) -> bytes:
    """
    Generate an invoice PDF with barcode for an order
    """
    # Create a byte stream for the PDF
    pdf_buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        pdf_buffer, 
        pagesize=A4,
        rightMargin=inch/2,
        leftMargin=inch/2,
        topMargin=inch/2,
        bottomMargin=inch/2
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#e25822'),
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    
    # Try to add logo
    logo_added = False
    logo_path = os.path.join("static", "images", "WEARXTURE LOGOai.png")
    
    try:
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=2*inch, height=0.8*inch, kind='proportional')
            logo.hAlign = 'LEFT'
            
            # Create header with logo
            header_right_text = Paragraph(
                "Ethnic Wear Collection<br/>Email: support@wearxture.com<br/>Phone: +91-XXXXXXXXXX", 
                normal_style
            )
            
            header_data = [[logo, header_right_text]]
            header_table = Table(header_data, colWidths=[3*inch, 3.5*inch])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(header_table)
            logo_added = True
    except Exception as e:
        print(f"Error adding logo: {e}")
    
    # Fallback if logo failed
    if not logo_added:
        elements.append(Paragraph("WEARXTURE", title_style))
        elements.append(Paragraph("Ethnic Wear Collection", styles['Normal']))
        elements.append(Paragraph("Email: support@wearxture.com | Phone: +91-7505348249", styles['Normal']))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Invoice heading
    elements.append(Paragraph("INVOICE / SHIPPING LABEL", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Order info with barcode
    try:
        # Create barcode
        barcode = code128.Code128(order_data['order_id'], barHeight=0.5*inch, barWidth=1.2)
        
        # Order details on left
        order_date = datetime.fromisoformat(str(order_data['created_at'])).strftime('%B %d, %Y')
        order_info_left = [
            ['Order ID:', order_data['order_id']],
            ['Order Date:', order_date],
            ['Payment Method:', order_data['payment_method'].upper()],
            ['Order Status:', order_data['order_status'].replace('_', ' ').title()],
        ]
        
        left_table = Table(order_info_left, colWidths=[1.5*inch, 2.5*inch])
        left_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        # Combine left details and barcode
        main_info_data = [[left_table, barcode]]
        main_info_table = Table(main_info_data, colWidths=[4*inch, 2.5*inch])
        main_info_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(main_info_table)
    except Exception as e:
        print(f"Error adding barcode: {e}")
        # Fallback without barcode
        elements.append(Paragraph(f"Order ID: {order_data['order_id']}", normal_style))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Customer details
    elements.append(Paragraph("SHIP TO:", heading_style))
    
    address = order_data['delivery_address']
    if isinstance(address, str):
        try:
            address = json.loads(address)
        except:
            address = {}
    
    customer_info = f"""
    {order_data['user_email']}<br/>
    {order_data['phone']}<br/>
    {address.get('address', '')}<br/>
    {address.get('city', '')}, {address.get('state', '')} {address.get('pincode', '')}<br/>
    {address.get('country', 'India')}
    """
    elements.append(Paragraph(customer_info, normal_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Order items
    elements.append(Paragraph("ORDER ITEMS:", heading_style))
    
    items = order_data['items']
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except:
            items = []
    
    # Items table
    items_data = [['SKU', 'Product', 'Qty', 'Price', 'Total']]
    
    for item in items:
        # Get SKU
        sku = "N/A"
        try:
            product_id = item.get('product_id') or item.get('id')
            if product_id:
                from db.supabase_client import get_product
                product_details = get_product(product_id)
                if product_details:
                    sku = product_details.get('sku', 'N/A') or 'N/A'
        except:
            pass
        
        product_name = str(item.get('name', 'Product'))[:30]
        if len(str(item.get('name', ''))) > 30:
            product_name += '...'
        
        items_data.append([
            sku,
            product_name,
            str(item.get('quantity', 1)),
            f"Rs. {item.get('price', 0)}",
            f"Rs. {item.get('price', 0) * item.get('quantity', 1)}"
        ])
    
    items_table = Table(items_data, colWidths=[1*inch, 2.5*inch, 0.5*inch, 0.8*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Order summary
    is_cod = order_data.get('payment_method') == 'cod'
    summary_data = []
    
    if is_cod:
        if order_data.get('payment_status') == 'cod_fee_paid':
            total_amount = float(order_data.get('total_amount', 0))
            remaining_amount = total_amount - 80
            summary_data = [['Amount to Collect (COD):', f"Rs. {remaining_amount}"]]
            elements.append(Paragraph("Note: COD fee of Rs. 80 already paid online", normal_style))
        else:
            summary_data = [['Amount to Collect (COD):', f"Rs. {order_data.get('total_amount', 0)}"]]
    else:
        summary_data = [
            ['Subtotal:', f"Rs. {order_data.get('subtotal', 0)}"],
            ['Delivery Charge:', f"Rs. {order_data.get('delivery_charge', 0)}"],
            ['Tax:', f"Rs. {order_data.get('tax', 0)}"],
            ['Total Amount:', f"Rs. {order_data.get('total_amount', 0)}"]
        ]
    
    summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
    ]))
    elements.append(summary_table)
    
    # COD special display
    if is_cod:
        elements.append(Spacer(1, 0.3*inch))
        cod_style = ParagraphStyle(
            'COD',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#e74c3c'),
            alignment=TA_CENTER
        )
        elements.append(Paragraph("CASH ON DELIVERY", cod_style))
        
        amount_style = ParagraphStyle(
            'Amount',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_CENTER
        )
        
        if order_data.get('payment_status') == 'cod_fee_paid':
            total_amount = float(order_data.get('total_amount', 0))
            remaining_amount = total_amount - 80
            elements.append(Paragraph(f"COLLECT: Rs. {remaining_amount}", amount_style))
        else:
            elements.append(Paragraph(f"COLLECT: Rs. {order_data.get('total_amount', 0)}", amount_style))
    
    # Build PDF
    try:
        doc.build(elements)
        pdf_buffer.seek(0)
        return pdf_buffer.read()
    except Exception as e:
        print(f"Error building PDF: {e}")
        raise
    finally:
        pdf_buffer.close()