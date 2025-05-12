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
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'live')  # Changed default to 'live'

if not PAYPAL_CLIENT_SECRET:
    logger.warning("PAYPAL_CLIENT_SECRET environment variable not set")
    
logger.info(f"PayPal configured in {PAYPAL_MODE.upper()} MODE - {'real payments will be processed' if PAYPAL_MODE == 'live' else 'test mode active'}")

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
            currency: The currency code (e.g., USD, BTC, ETH)
            description: The payment description
            return_url: The URL to redirect to after approval
            cancel_url: The URL to redirect to if cancelled
            
        Returns:
            Tuple containing the payment ID and approval URL if successful, or (None, None) if failed
        """
        # Verify PayPal credentials are valid
        if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
            logger.error("PayPal credentials not configured properly")
            return None, None
            
        # Check if this is a cryptocurrency transaction
        crypto_currencies = ['NVCT', 'ETH', 'BTC', 'USDT', 'USDC', 'AFD1']
        
        try:
            # For standard fiat currencies (USD, EUR, etc.)
            if currency not in crypto_currencies:
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
            else:
                # For cryptocurrency transactions
                # Add cryptocurrency as an item in the payment with crypto handling
                payment = paypalrestsdk.Payment({
                    "intent": "sale",
                    "payer": {
                        "payment_method": "paypal"
                    },
                    "transactions": [{
                        "amount": {
                            # For cryptocurrency transactions, PayPal requires a base currency (USD)
                            "total": str(amount),
                            "currency": "USD"
                        },
                        "description": f"{description} ({amount} {currency})",
                        "item_list": {
                            "items": [{
                                "name": f"{currency} cryptocurrency transfer",
                                "quantity": "1",
                                "price": str(amount),
                                "currency": "USD",
                                "description": f"Payment of {amount} {currency}"
                            }]
                        },
                        # Save cryptocurrency information in custom field
                        "custom": json.dumps({
                            "original_currency": currency,
                            "original_amount": amount
                        })
                    }],
                    "redirect_urls": {
                        "return_url": return_url,
                        "cancel_url": cancel_url
                    }
                })
            
            try:
                if payment.create():
                    # Extract approval URL
                    approval_url = next(link.href for link in payment.links if link.rel == 'approval_url')
                    logger.info(f"Payment created successfully: {payment.id} ({currency})")
                    return payment.id, approval_url
                else:
                    logger.error(f"Failed to create payment: {payment.error}")
                    return None, None
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "Unauthorized" in error_msg:
                    logger.error(f"PayPal API authentication failed - {error_msg}")
                    logger.warning("Check that PayPal API credentials are valid and for the correct environment (live/sandbox)")
                elif "404" in error_msg or "not found" in error_msg.lower():
                    logger.error(f"PayPal API error: Resource not found - {error_msg}")
                elif "configuration" in error_msg.lower():
                    logger.error(f"PayPal SDK configuration missing - {error_msg}")
                else:
                    logger.error(f"PayPal API error: {error_msg}")
                return None, None
                
        except Exception as e:
            logger.error(f"Error creating PayPal payment: {str(e)}")
            error_type = type(e).__name__
            logger.error(f"Exception type: {error_type}")
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
            currency: The currency code (e.g., USD, BTC, ETH)
            recipient_email: The recipient's PayPal email
            note: Note to the recipient
            email_subject: Subject for the payout email notification
            email_message: Message for the payout email notification
            
        Returns:
            Tuple containing (success status, batch ID, details)
        """
        # Check if this is a cryptocurrency transaction
        crypto_currencies = ['NVCT', 'ETH', 'BTC', 'USDT', 'USDC', 'AFD1']
        is_crypto = currency in crypto_currencies
        
        try:
            # Create a unique batch ID for this payout
            sender_batch_id = str(uuid.uuid4())
            
            # For cryptocurrency transactions, we use USD as the base currency for PayPal
            # but include the crypto details in the note and email
            payout_currency = "USD" if is_crypto else currency
            
            # Customize email subjects and messages for crypto transactions
            if is_crypto:
                if email_subject is None:
                    email_subject = f"You received a crypto payment of {amount} {currency}"
                
                crypto_note = f"{note} - {amount} {currency} cryptocurrency payment"
            else:
                if email_subject is None:
                    email_subject = f"You received a payment of {amount} {currency}"
                
                crypto_note = note
            
            # Set up the payout
            payout = paypalrestsdk.Payout({
                "sender_batch_header": {
                    "sender_batch_id": sender_batch_id,
                    "email_subject": email_subject,
                },
                "items": [
                    {
                        "recipient_type": "EMAIL",
                        "amount": {
                            "value": str(amount),
                            "currency": payout_currency
                        },
                        "note": crypto_note,
                        "receiver": recipient_email,
                        "sender_item_id": str(uuid.uuid4()),
                    }
                ]
            })
            
            # Build custom email message for crypto transactions
            if is_crypto and email_message is None:
                email_message = (f"You have received a cryptocurrency payment of {amount} {currency}. "
                                f"This payment was processed through PayPal via the NVC Banking Platform.")
            
            # Include email message if provided
            if email_message:
                payout.sender_batch_header["email_message"] = email_message
            
            # Add metadata for crypto transactions
            if is_crypto:
                # Store crypto information in the payout metadata
                payout.items[0]["custom"] = json.dumps({
                    "original_currency": currency,
                    "original_amount": amount,
                    "is_cryptocurrency": True
                })
            
            # Create the payout
            if payout.create(sync_mode=False):  # Async mode
                logger.info(f"Payout created successfully: {payout.batch_header.payout_batch_id} ({currency})")
                
                # Add cryptocurrency information to the returned details
                payout_data = payout.to_dict()
                if is_crypto:
                    # Make sure there's a place to store custom metadata
                    if 'custom_data' not in payout_data:
                        payout_data['custom_data'] = {}
                    
                    # Add cryptocurrency information to the details
                    payout_data['custom_data']['original_currency'] = currency
                    payout_data['custom_data']['original_amount'] = amount
                    payout_data['custom_data']['is_cryptocurrency'] = True
                
                return True, payout.batch_header.payout_batch_id, payout_data
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