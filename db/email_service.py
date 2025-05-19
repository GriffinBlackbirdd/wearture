"""
Email service for WEARXTURE using Resend API
"""
import os
from typing import Dict, Any, Optional, List
import resend
from datetime import datetime
from dotenv import load_dotenv
import base64
# Load environment variables
load_dotenv()

# Initialize Resend with API key
RESEND_API_KEY = "re_gLrjYmbX_ApmFGqTxHBCjANnTqmY9hhkc"
resend.api_key = RESEND_API_KEY

# Sender email address (use your verified domain)
FROM_EMAIL = os.getenv("FROM_EMAIL", "support@wearxture.com")

def send_order_confirmation_email(order_data: Dict[str, Any]) -> bool:
    """
    Send order confirmation email to customer
    
    Args:
        order_data: Order information including:
            - order_id: Order ID
            - user_email: Customer's email
            - items: List of ordered items
            - delivery_address: Shipping address
            - total_amount: Order total
            - payment_method: Payment method (cod, upi, etc.)
            - created_at: Order creation timestamp
    
    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        # Extract order details
        order_id = order_data.get("order_id", "")
        customer_email = order_data.get("user_email", "")
        items = order_data.get("items", [])
        
        # Format items for display
        if isinstance(items, str):
            import json
            try:
                items = json.loads(items)
            except:
                items = []
        
        # Prepare shipping address
        address = order_data.get("delivery_address", {})
        if isinstance(address, str):
            import json
            try:
                address = json.loads(address)
            except:
                address = {}
        
        # Format payment method
        payment_method = order_data.get("payment_method", "")
        is_cod = payment_method.lower() == "cod"
        
        # Format order date
        created_at = order_data.get("created_at", "")
        if created_at:
            try:
                order_date = datetime.fromisoformat(str(created_at)).strftime("%B %d, %Y at %I:%M %p")
            except:
                order_date = str(created_at)
        else:
            order_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        # Generate HTML content
        html_content = generate_order_email_html(
            order_id=order_id,
            order_date=order_date,
            items=items,
            address=address,
            total_amount=order_data.get("total_amount", 0),
            is_cod=is_cod,
            cod_remaining=order_data.get("cod_remaining", 0) if is_cod else 0,
            payment_status=order_data.get("payment_status", ""),
            order_status=order_data.get("order_status", "")
        )
        
        # Send email via Resend
        response = resend.Emails.send({
            "from": f"WEARXTURE <{FROM_EMAIL}>",
            "to": customer_email,
            "subject": f"Order Confirmation - #{order_id}",
            "html": html_content
        })
        
        # Log email sending
        print(f"Order confirmation email sent to {customer_email} for order {order_id}")
        return True
        
    except Exception as e:
        print(f"Error sending order confirmation email: {str(e)}")
        return False

def generate_order_email_html(
    order_id: str,
    order_date: str,
    items: List[Dict[str, Any]],
    address: Dict[str, Any],
    total_amount: float,
    is_cod: bool = False,
    cod_remaining: float = 0,
    payment_status: str = "",
    order_status: str = ""
) -> str:
    """
    Generate HTML content for order confirmation email
    """
    # Format items HTML
    items_html = ""
    for item in items:
        item_name = item.get("name", "Product")
        item_price = item.get("price", 0)
        item_quantity = item.get("quantity", 1)
        item_total = item_price * item_quantity
        item_image = item.get("image", "")
        
        items_html += f"""
        <tr>
            <td style="padding: 15px 0; border-bottom: 1px solid #eeeeee;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td width="80" style="padding-right: 15px;">
                            <img src="{item_image}" alt="{item_name}" width="80" height="100" style="border-radius: 6px; object-fit: cover;">
                        </td>
                        <td>
                            <p style="font-weight: 600; margin: 0 0 5px 0;">{item_name}</p>
                            <p style="color: #777777; font-size: 14px; margin: 0 0 5px 0;">Qty: {item_quantity}</p>
                            <p style="color: #e25822; font-weight: 500; margin: 0;">₹{item_total:.0f}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """
    
    # Format address
    address_html = f"""
    {address.get('address', '')}<br>
    {address.get('city', '')}, {address.get('state', '')} {address.get('pincode', '')}<br>
    {address.get('country', 'India')}
    """
    
    # Special message for COD orders
    cod_message = ""
    if is_cod and cod_remaining > 0:
        cod_message = f"""
        <tr>
            <td style="padding: 15px; background-color: #fff8f3; border-radius: 8px; margin-top: 15px;">
                <p style="font-weight: 600; margin: 0 0 5px 0;">Cash on Delivery</p>
                <p style="margin: 0 0 5px 0;">COD Fee Paid: <span style="color: #28a745; font-weight: 500;">₹80</span></p>
                <p style="margin: 0; font-weight: 600;">Amount Due on Delivery: <span style="color: #e25822;">₹{cod_remaining:.0f}</span></p>
            </td>
        </tr>
        """
    
    # Complete HTML template
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Order Confirmation</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
            body {{ font-family: 'Poppins', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .header {{ background-color: #e25822; padding: 20px; text-align: center; }}
            .logo {{ max-width: 180px; }}
            .content {{ background-color: #ffffff; padding: 30px; }}
            .footer {{ background-color: #f9f9f9; padding: 20px; text-align: center; font-size: 14px; color: #777; }}
            .button {{ display: inline-block; background-color: #e25822; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; font-weight: 500; margin-top: 15px; }}
            h1 {{ color: #333; margin-top: 0; }}
            .order-info {{ background-color: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .divider {{ height: 1px; background-color: #eeeeee; margin: 15px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="https://wearxture.com/static/images/WEARXTURE%20LOGOai.png" alt="WEARXTURE" class="logo">
            </div>
            
            <div class="content">
                <h1>Order Confirmed</h1>
                <p>Thank you for your order! We're currently processing it and will notify you when it ships.</p>
                
                <div class="order-info">
                    <p><strong>Order #:</strong> {order_id}</p>
                    <p><strong>Order Date:</strong> {order_date}</p>
                    <p><strong>Payment Method:</strong> {payment_status.replace('_', ' ').title()}</p>
                    <p><strong>Order Status:</strong> {order_status.replace('_', ' ').title()}</p>
                </div>
                
                <h2>Order Items</h2>
                <table width="100%" cellpadding="0" cellspacing="0">
                    {items_html}
                </table>
                
                <div class="divider"></div>
                
                <h2>Shipping Address</h2>
                <p>{address_html}</p>
                
                <div class="divider"></div>
                
                <h2>Order Summary</h2>
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="padding: 5px 0;"><strong>Total Amount:</strong></td>
                        <td style="text-align: right; font-weight: 600; color: #e25822;">₹{total_amount:.0f}</td>
                    </tr>
                    {cod_message}
                </table>
                
                <a href="https://wearxture.com/orders" class="button">View Your Order</a>
            </div>
            
            <div class="footer">
                <p>This email confirms your order with WEARXTURE. For any questions or concerns, <br>please contact our customer support at support@wearxture.com</p>
                <p>&copy; 2025 WEARXTURE. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def send_order_status_update_email(order_data: Dict[str, Any], old_status: str, new_status: str) -> bool:
    """
    Send an email notification when order status changes
    
    Args:
        order_data: Order information
        old_status: Previous order status
        new_status: New order status
    
    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        # Extract order details
        order_id = order_data.get("order_id", "")
        customer_email = order_data.get("user_email", "")
        
        # Status specific messages
        status_messages = {
            "confirmed": "Your order has been confirmed and is now being processed.",
            "processing": "We're preparing your items for shipment.",
            "dispatched": "Your order has been dispatched and is on its way!",
            "delivered": "Your order has been delivered. Enjoy your new items!",
            "cancelled": "Your order has been cancelled as requested."
        }
        
        # Default message if status not found
        status_message = status_messages.get(new_status, f"Your order status has been updated to {new_status}.")
        
        # Generate simple HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Order Status Update</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
                body {{ font-family: 'Poppins', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .header {{ background-color: #e25822; padding: 20px; text-align: center; }}
                .logo {{ max-width: 180px; }}
                .content {{ background-color: #ffffff; padding: 30px; }}
                .footer {{ background-color: #f9f9f9; padding: 20px; text-align: center; font-size: 14px; color: #777; }}
                .button {{ display: inline-block; background-color: #e25822; color: white; padding: 12px 25px; text-decoration: none; border-radius: 8px; font-weight: 500; margin-top: 15px; }}
                h1 {{ color: #333; margin-top: 0; }}
                .status-update {{ background-color: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="https://wearxture.com/static/images/WEARXTURE%20LOGOai.png" alt="WEARXTURE" class="logo">
                </div>
                
                <div class="content">
                    <h1>Order Status Update</h1>
                    <p>Your order #{order_id} has been updated.</p>
                    
                    <div class="status-update">
                        <p><strong>New Status:</strong> {new_status.replace('_', ' ').title()}</p>
                        <p>{status_message}</p>
                    </div>
                    
                    <a href="https://wearxture.com/order/{order_id}" class="button">View Order Details</a>
                </div>
                
                <div class="footer">
                    <p>This email is about your order with WEARXTURE. For any questions or concerns, <br>please contact our customer support at support@wearxture.com</p>
                    <p>&copy; 2025 WEARXTURE. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email via Resend
        response = resend.Emails.send({
            "from": f"WEARXTURE <{FROM_EMAIL}>",
            "to": customer_email,
            "subject": f"Order #{order_id} Status Update: {new_status.replace('_', ' ').title()}",
            "html": html_content
        })
        
        # Log email sending
        print(f"Order status update email sent to {customer_email} for order {order_id}")
        return True
        
    except Exception as e:
        print(f"Error sending order status update email: {str(e)}")
        return False

def send_invoice_email(order_data: Dict[str, Any], invoice_pdf: bytes) -> bool:
    """
    Send invoice as attachment to customer
    
    Args:
        order_data: Order information
        invoice_pdf: PDF invoice content as bytes
    
    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        # Extract order details
        order_id = order_data.get("order_id", "")
        customer_email = order_data.get("user_email", "")
        
        # Generate simple HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Your Invoice from WEARXTURE</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
                body {{ font-family: 'Poppins', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .header {{ background-color: #e25822; padding: 20px; text-align: center; }}
                .logo {{ max-width: 180px; }}
                .content {{ background-color: #ffffff; padding: 30px; }}
                .footer {{ background-color: #f9f9f9; padding: 20px; text-align: center; font-size: 14px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="https://wearxture.com/static/images/WEARXTURE%20LOGOai.png" alt="WEARXTURE" class="logo">
                </div>
                
                <div class="content">
                    <h1>Your Invoice</h1>
                    <p>Thank you for shopping with WEARXTURE. Please find attached the invoice for your order #{order_id}.</p>
                    <p>If you have any questions regarding your purchase, please contact our customer support.</p>
                </div>
                
                <div class="footer">
                    <p>This email is about your order with WEARXTURE. For any questions or concerns, <br>please contact our customer support at support@wearxture.com</p>
                    <p>&copy; 2025 WEARXTURE. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email with attachment via Resend
        response = resend.Emails.send({
            "from": f"WEARXTURE <{FROM_EMAIL}>",
            "to": customer_email,
            "subject": f"Invoice for Order #{order_id}",
            "html": html_content,
            "attachments": [
                {
                    "content": base64.b64encode(invoice_pdf).decode('utf-8'),
                    "filename": f"WEARXTURE_Invoice_{order_id}.pdf"
                }
            ]
        })
        
        # Log email sending
        print(f"Invoice email sent to {customer_email} for order {order_id}")
        return True
        
    except Exception as e:
        print(f"Error sending invoice email: {str(e)}")
        return False