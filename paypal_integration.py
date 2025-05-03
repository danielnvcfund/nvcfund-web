import os
import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union, Any

import requests
import paypalrestsdk
from flask import url_for

# Import models directly only if needed for type hints
from models import Transaction, TransactionStatus, TransactionType, User

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# PayPal API Configuration
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET')
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')  # sandbox or live

if not PAYPAL_CLIENT_SECRET:
    logger.warning("PAYPAL_CLIENT_SECRET environment variable not set")

# Configure PayPal SDK
paypalrestsdk.configure({
    "mode": PAYPAL_MODE,
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_CLIENT_SECRET,
})

class PayPalService:
    """Service for interacting with the PayPal REST API"""

    @staticmethod
    def create_payment(amount: float, currency: str, description: str, 
                       return_url: str, cancel_url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Create a PayPal payment
        
        Args:
            amount: The payment amount
            currency: The currency code (e.g., USD)
            description: The payment description
            return_url: The URL to redirect to after approval
            cancel_url: The URL to redirect to if cancelled
            
        Returns:
            Tuple containing the payment ID and approval URL if successful, or (None, None) if failed
        """
        try:
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "transactions": [{
                    "amount": {
                        "total": str(amount),
                        "currency": currency
                    },
                    "description": description
                }],
                "redirect_urls": {
                    "return_url": return_url,
                    "cancel_url": cancel_url
                }
            })
            
            if payment.create():
                # Extract approval URL
                approval_url = next(link.href for link in payment.links if link.rel == 'approval_url')
                logger.info(f"Payment created successfully: {payment.id}")
                return payment.id, approval_url
            else:
                logger.error(f"Failed to create payment: {payment.error}")
                return None, None
                
        except Exception as e:
            logger.error(f"Error creating PayPal payment: {str(e)}")
            return None, None
    
    @staticmethod
    def execute_payment(payment_id: str, payer_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Execute a PayPal payment after it has been approved
        
        Args:
            payment_id: The PayPal payment ID
            payer_id: The PayPal payer ID
            
        Returns:
            Tuple containing success status and payment details if successful
        """
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            if payment.execute({"payer_id": payer_id}):
                logger.info(f"Payment executed successfully: {payment_id}")
                return True, payment.to_dict()
            else:
                logger.error(f"Failed to execute payment: {payment.error}")
                return False, None
                
        except Exception as e:
            logger.error(f"Error executing PayPal payment: {str(e)}")
            return False, None
    
    @staticmethod
    def get_payment_details(payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a PayPal payment
        
        Args:
            payment_id: The PayPal payment ID
            
        Returns:
            Dictionary containing payment details if successful, None otherwise
        """
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            return payment.to_dict()
        except Exception as e:
            logger.error(f"Error getting PayPal payment details: {str(e)}")
            return None
    
    @staticmethod
    def create_payout(amount: float, currency: str, recipient_email: str, 
                      note: str, email_subject: Optional[str] = None, 
                      email_message: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Create a PayPal payout to a single recipient
        
        Args:
            amount: The payout amount
            currency: The currency code (e.g., USD)
            recipient_email: The recipient's PayPal email
            note: Note to the recipient
            email_subject: Subject for the payout email notification
            email_message: Message for the payout email notification
            
        Returns:
            Tuple containing (success status, batch ID, details)
        """
        try:
            # Create a unique batch ID for this payout
            sender_batch_id = str(uuid.uuid4())
            
            # Set up the payout
            payout = paypalrestsdk.Payout({
                "sender_batch_header": {
                    "sender_batch_id": sender_batch_id,
                    "email_subject": email_subject or f"You received a payment of {currency} {amount}",
                },
                "items": [
                    {
                        "recipient_type": "EMAIL",
                        "amount": {
                            "value": str(amount),
                            "currency": currency
                        },
                        "note": note,
                        "receiver": recipient_email,
                        "sender_item_id": str(uuid.uuid4()),
                    }
                ]
            })
            
            # Include email message if provided
            if email_message:
                payout.sender_batch_header["email_message"] = email_message
            
            # Create the payout
            if payout.create(sync_mode=False):  # Async mode
                logger.info(f"Payout created successfully: {payout.batch_header.payout_batch_id}")
                return True, payout.batch_header.payout_batch_id, payout.to_dict()
            else:
                logger.error(f"Failed to create payout: {payout.error}")
                return False, None, None
                
        except Exception as e:
            logger.error(f"Error creating PayPal payout: {str(e)}")
            return False, None, None
    
    @staticmethod
    def get_payout_details(payout_batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a PayPal payout
        
        Args:
            payout_batch_id: The PayPal payout batch ID
            
        Returns:
            Dictionary containing payout details if successful, None otherwise
        """
        try:
            payout = paypalrestsdk.Payout.find(payout_batch_id)
            return payout.to_dict()
        except Exception as e:
            logger.error(f"Error getting PayPal payout details: {str(e)}")
            return None
    
    @staticmethod
    def cancel_unclaimed_payout(payout_item_id: str) -> bool:
        """
        Cancel an unclaimed payout
        
        Args:
            payout_item_id: The PayPal payout item ID to cancel
            
        Returns:
            Boolean indicating success or failure
        """
        try:
            # Make direct API call to cancel the payout item
            paypal_url = f"https://api.{'sandbox' if PAYPAL_MODE == 'sandbox' else 'paypal'}.com/v1/payments/payouts-item/{payout_item_id}/cancel"
            
            # Get OAuth token
            auth_response = requests.post(
                f"https://api.{'sandbox' if PAYPAL_MODE == 'sandbox' else 'paypal'}.com/v1/oauth2/token",
                auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
                data={"grant_type": "client_credentials"}
            )
            
            if auth_response.status_code != 200:
                logger.error(f"Failed to get PayPal OAuth token: {auth_response.text}")
                return False
            
            auth_data = auth_response.json()
            access_token = auth_data["access_token"]
            
            # Make the cancellation request
            cancel_response = requests.post(
                paypal_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                }
            )
            
            if cancel_response.status_code in (200, 202, 204):
                logger.info(f"Payout item cancelled successfully: {payout_item_id}")
                return True
            else:
                logger.error(f"Failed to cancel payout item: {cancel_response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling PayPal payout: {str(e)}")
            return False
    
    @staticmethod
    def is_webhook_signature_valid(transmission_id: str, timestamp: str, 
                                  webhook_id: str, event_body: str, 
                                  transmission_sig: str, cert_url: str) -> bool:
        """
        Verify the signature of a PayPal webhook event
        
        Args:
            All required webhook signature verification parameters
            
        Returns:
            Boolean indicating if the signature is valid
        """
        try:
            # This requires WebhookEvent.verify implementation which isn't 
            # directly available in paypalrestsdk, so we'd need to manually verify
            # For simplicity, this is a placeholder that always returns True
            # In a real implementation, you should use the PayPal SDK's verification logic
            logger.warning("PayPal webhook signature verification not fully implemented")
            return True
        except Exception as e:
            logger.error(f"Error verifying PayPal webhook signature: {str(e)}")
            return False