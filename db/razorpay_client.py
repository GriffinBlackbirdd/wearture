"""
Razorpay client integration for WEARXTURE
"""
import razorpay
import os
from dotenv import load_dotenv
import hmac
import hashlib
from typing import Dict, Any, Optional

# Load environment variables
load_dotenv()

# Razorpay configuration
RAZORPAY_KEY_ID="rzp_live_TWSHolf7gZYlpR"
RAZORPAY_SECRET_KEY="sNPEE3PDRLnICSNSgeiPqzOW"
# RAZORPAY_KEY_ID="rzp_test_kuFBWGnWltF0jo"
# RAZORPAY_SECRET_KEY="8WrBj49808XbknAwLGqYFi6N"
RAZORPAY_TEST_MODE = os.getenv("RAZORPAY_TEST_MODE", "false").lower() == "false"

# Initialize Razorpay client only if credentials are available
razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_SECRET_KEY:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET_KEY))

def create_razorpay_order(amount: float, currency: str = "INR", order_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Create a Razorpay order
    
    Args:
        amount: Amount in the smallest currency unit (paise for INR)
        currency: Currency code (default: INR)
        order_info: Additional order information
    
    Returns:
        Razorpay order response
    """
    try:
        # Check if Razorpay client is initialized
        if not razorpay_client:
            raise Exception("Razorpay is not configured. Please check your API keys.")
        
        # For test mode, create a test order
        if RAZORPAY_TEST_MODE:
            print(f"Creating test order for amount: {amount} INR")
        
        order_data = {
            "amount": int(amount * 100),  # Convert to paise
            "currency": currency,
            "receipt": order_info.get("receipt", ""),
            "notes": order_info.get("notes", {})
        }
        
        order = razorpay_client.order.create(data=order_data)
        return order
    except Exception as e:
        raise Exception(f"Failed to create Razorpay order: {str(e)}")

def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Verify Razorpay payment signature
    
    Args:
        order_id: Razorpay order ID
        payment_id: Razorpay payment ID
        signature: Payment signature from Razorpay
    
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Create the message to be hashed
        message = f"{order_id}|{payment_id}"
        
        # Generate the signature
        generated_signature = hmac.new(
            RAZORPAY_SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return generated_signature == signature
    except Exception as e:
        print(f"Error verifying signature: {e}")
        return False

def capture_payment(payment_id: str, amount: int) -> Dict[str, Any]:
    """
    Capture a payment
    
    Args:
        payment_id: Razorpay payment ID
        amount: Amount to capture in paise
    
    Returns:
        Capture response
    """
    try:
        if not razorpay_client:
            raise Exception("Razorpay is not configured")
            
        response = razorpay_client.payment.capture(payment_id, amount)
        return response
    except Exception as e:
        raise Exception(f"Failed to capture payment: {str(e)}")

def get_payment_details(payment_id: str) -> Dict[str, Any]:
    """
    Get payment details
    
    Args:
        payment_id: Razorpay payment ID
    
    Returns:
        Payment details
    """
    try:
        if not razorpay_client:
            raise Exception("Razorpay is not configured")
            
        payment = razorpay_client.payment.fetch(payment_id)
        return payment
    except Exception as e:
        raise Exception(f"Failed to fetch payment details: {str(e)}")

def refund_payment(payment_id: str, amount: Optional[int] = None) -> Dict[str, Any]:
    """
    Refund a payment
    
    Args:
        payment_id: Razorpay payment ID
        amount: Amount to refund in paise (optional, refunds full amount if not specified)
    
    Returns:
        Refund response
    """
    try:
        if not razorpay_client:
            raise Exception("Razorpay is not configured")
            
        refund_data = {"payment_id": payment_id}
        if amount:
            refund_data["amount"] = amount
            
        refund = razorpay_client.refund.create(data=refund_data)
        return refund
    except Exception as e:
        raise Exception(f"Failed to process refund: {str(e)}")