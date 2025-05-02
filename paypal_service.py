"""
PayPal Integration Service for NVC Banking Platform

This module provides functionality for interacting with PayPal's REST API,
including payment processing, payout operations, and webhook handling.
"""
import os
import json
import logging
import requests
from datetime import datetime
from flask import current_app
from models import Transaction, TransactionStatus, TransactionType

# Configure logging
logger = logging.getLogger(__name__)

# PayPal API endpoints
PAYPAL_API_BASE_SANDBOX = "https://api-m.sandbox.paypal.com"
PAYPAL_API_BASE_PRODUCTION = "https://api-m.paypal.com"

class PayPalService:
    """Service for PayPal integration with NVC Banking Platform"""
    
    def __init__(self, sandbox_mode=True):
        """
        Initialize the PayPal service
        
        Args:
            sandbox_mode (bool): Whether to use the sandbox environment (default: True)
        """
        self.client_id = os.environ.get("PAYPAL_CLIENT_ID")
        self.client_secret = os.environ.get("PAYPAL_CLIENT_SECRET")
        self.sandbox_mode = sandbox_mode
        self.api_base = PAYPAL_API_BASE_SANDBOX if sandbox_mode else PAYPAL_API_BASE_PRODUCTION
        self.access_token = None
        self.token_expiry = None
        
        # Check for required credentials
        if not self.client_id:
            logger.warning("PAYPAL_CLIENT_ID environment variable not set")
        if not self.client_secret:
            logger.warning("PAYPAL_CLIENT_SECRET environment variable not set")
    
    def _get_auth_token(self):
        """
        Get an OAuth 2.0 access token from PayPal
        
        Returns:
            str: Access token if successful, None otherwise
        """
        if not self.client_id or not self.client_secret:
            logger.error("Missing PayPal API credentials")
            return None
            
        # Check if we already have a valid token
        if self.access_token and self.token_expiry and self.token_expiry > datetime.now():
            return self.access_token
            
        try:
            auth_url = f"{self.api_base}/v1/oauth2/token"
            headers = {
                "Accept": "application/json",
                "Accept-Language": "en_US"
            }
            data = {
                "grant_type": "client_credentials"
            }
            
            response = requests.post(
                auth_url,
                headers=headers,
                data=data,
                auth=(self.client_id, self.client_secret)
            )
            
            response.raise_for_status()
            token_data = response.json()
            
            self.access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 0)
            
            # Set token expiry time (with a small buffer)
            from datetime import timedelta
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
            
            return self.access_token
        except Exception as e:
            logger.error(f"Error obtaining PayPal access token: {str(e)}")
            return None
    
    def _api_request(self, method, endpoint, data=None, params=None, headers=None):
        """
        Make an API request to PayPal
        
        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE)
            endpoint (str): API endpoint to call
            data (dict, optional): Request body data
            params (dict, optional): Query parameters
            headers (dict, optional): Additional headers
            
        Returns:
            dict: Response JSON if successful
            None: If request failed
        """
        token = self._get_auth_token()
        if not token:
            logger.error("No access token available for PayPal API request")
            return None
            
        url = f"{self.api_base}{endpoint}"
        
        default_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        if headers:
            default_headers.update(headers)
            
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=default_headers,
                params=params,
                json=data if data else None
            )
            
            response.raise_for_status()
            
            if response.status_code == 204:  # No content
                return {}
                
            return response.json()
        except requests.exceptions.RequestException as e:
            error_info = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_info = f"{error_info} - Details: {json.dumps(error_data)}"
                except:
                    error_info = f"{error_info} - Status: {e.response.status_code}"
            
            logger.error(f"PayPal API request failed: {error_info}")
            return None
    
    def create_payment(self, amount, currency="USD", description="Payment via NVC Banking Platform", 
                       return_url=None, cancel_url=None, **additional_params):
        """
        Create a PayPal payment
        
        Args:
            amount (float): Payment amount
            currency (str): Currency code (default: USD)
            description (str): Payment description
            return_url (str): URL to redirect on successful payment
            cancel_url (str): URL to redirect on cancelled payment
            **additional_params: Additional parameters for the payment
            
        Returns:
            dict: Payment information including approval URL if successful
            None: If payment creation failed
        """
        if not return_url or not cancel_url:
            logger.error("Return URL and Cancel URL are required for PayPal payments")
            return None
            
        data = {
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "transactions": [
                {
                    "amount": {
                        "total": str(amount),
                        "currency": currency
                    },
                    "description": description
                }
            ],
            "redirect_urls": {
                "return_url": return_url,
                "cancel_url": cancel_url
            }
        }
        
        # Add any additional parameters
        for key, value in additional_params.items():
            if key not in data:
                data[key] = value
                
        return self._api_request("POST", "/v1/payments/payment", data=data)
    
    def execute_payment(self, payment_id, payer_id):
        """
        Execute a PayPal payment after approval
        
        Args:
            payment_id (str): PayPal payment ID
            payer_id (str): PayPal payer ID
            
        Returns:
            dict: Payment execution result if successful
            None: If payment execution failed
        """
        data = {
            "payer_id": payer_id
        }
        
        return self._api_request("POST", f"/v1/payments/payment/{payment_id}/execute", data=data)
    
    def get_payment_details(self, payment_id):
        """
        Get details of a PayPal payment
        
        Args:
            payment_id (str): PayPal payment ID
            
        Returns:
            dict: Payment details if successful
            None: If retrieval failed
        """
        return self._api_request("GET", f"/v1/payments/payment/{payment_id}")
    
    def create_payout(self, receiver_email, amount, currency="USD", note="Payout via NVC Banking Platform", 
                      sender_item_id=None, email_subject=None, email_message=None):
        """
        Create a PayPal payout to a single recipient
        
        Args:
            receiver_email (str): Recipient's PayPal email
            amount (float): Payout amount
            currency (str): Currency code (default: USD)
            note (str): Note to recipient
            sender_item_id (str): Sender's reference ID
            email_subject (str): Subject of the notification email
            email_message (str): Content of the notification email
            
        Returns:
            dict: Payout information if successful
            None: If payout creation failed
        """
        if not sender_item_id:
            # Generate a unique sender item ID if not provided
            from uuid import uuid4
            sender_item_id = f"NVC-PAYOUT-{uuid4().hex[:8].upper()}"
            
        data = {
            "sender_batch_header": {
                "sender_batch_id": f"Batch_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "email_subject": email_subject or "You have received a payout from NVC Banking Platform",
                "email_message": email_message or "You have received a payout from NVC Banking Platform. Thank you for using our service."
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value": str(amount),
                        "currency": currency
                    },
                    "note": note,
                    "sender_item_id": sender_item_id,
                    "receiver": receiver_email
                }
            ]
        }
        
        return self._api_request("POST", "/v1/payments/payouts", data=data)
    
    def get_payout_details(self, payout_batch_id):
        """
        Get details of a PayPal payout batch
        
        Args:
            payout_batch_id (str): PayPal payout batch ID
            
        Returns:
            dict: Payout details if successful
            None: If retrieval failed
        """
        return self._api_request("GET", f"/v1/payments/payouts/{payout_batch_id}")
    
    def get_payout_item_details(self, payout_item_id):
        """
        Get details of a specific payout item
        
        Args:
            payout_item_id (str): PayPal payout item ID
            
        Returns:
            dict: Payout item details if successful
            None: If retrieval failed
        """
        return self._api_request("GET", f"/v1/payments/payouts-item/{payout_item_id}")
    
    def verify_webhook_signature(self, webhook_id, event_body, headers):
        """
        Verify a PayPal webhook signature
        
        Args:
            webhook_id (str): PayPal webhook ID
            event_body (str): Raw event body
            headers (dict): Request headers
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        data = {
            "webhook_id": webhook_id,
            "transmission_id": headers.get("Paypal-Transmission-Id"),
            "transmission_time": headers.get("Paypal-Transmission-Time"),
            "cert_url": headers.get("Paypal-Cert-Url"),
            "auth_algo": headers.get("Paypal-Auth-Algo"),
            "transmission_sig": headers.get("Paypal-Transmission-Sig"),
            "webhook_event": json.loads(event_body) if isinstance(event_body, str) else event_body
        }
        
        result = self._api_request("POST", "/v1/notifications/verify-webhook-signature", data=data)
        
        if result and result.get("verification_status") == "SUCCESS":
            return True
        return False
    
    def create_transaction_record(self, user_id, amount, currency, paypal_payment_id, 
                                  recipient_email=None, transaction_type=TransactionType.PAYMENT,
                                  status=TransactionStatus.PENDING, description=None):
        """
        Create a transaction record in the NVC Banking Platform database
        
        Args:
            user_id (int): User ID initiating the transaction
            amount (float): Transaction amount
            currency (str): Currency code
            paypal_payment_id (str): PayPal payment ID
            recipient_email (str, optional): Recipient's email
            transaction_type (TransactionType): Type of transaction
            status (TransactionStatus): Transaction status
            description (str, optional): Transaction description
            
        Returns:
            Transaction: Created transaction object
        """
        try:
            from app import db
            
            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                currency=currency,
                payment_provider="paypal",
                external_transaction_id=paypal_payment_id,
                transaction_type=transaction_type,
                status=status,
                description=description or f"PayPal transaction of {amount} {currency}",
                recipient_identifier=recipient_email
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            logger.info(f"Created transaction record for PayPal payment {paypal_payment_id}")
            return transaction
        except Exception as e:
            logger.error(f"Error creating transaction record: {str(e)}")
            return None
    
    def update_transaction_status(self, transaction_id, new_status, notes=None):
        """
        Update the status of a transaction in the NVC Banking Platform database
        
        Args:
            transaction_id (int): Transaction ID
            new_status (TransactionStatus): New transaction status
            notes (str, optional): Additional notes about the status update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            from app import db
            
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                logger.error(f"Transaction {transaction_id} not found")
                return False
                
            transaction.status = new_status
            
            if notes:
                # Append notes to existing notes if any
                if transaction.notes:
                    transaction.notes = f"{transaction.notes}\n{notes}"
                else:
                    transaction.notes = notes
                    
            db.session.commit()
            
            logger.info(f"Updated transaction {transaction_id} status to {new_status.name}")
            return True
        except Exception as e:
            logger.error(f"Error updating transaction status: {str(e)}")
            return False
    
    def process_webhook_event(self, event_data):
        """
        Process a webhook event from PayPal
        
        Args:
            event_data (dict): Webhook event data
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            event_type = event_data.get("event_type")
            resource = event_data.get("resource", {})
            
            logger.info(f"Processing PayPal webhook event type: {event_type}")
            
            if event_type == "PAYMENT.SALE.COMPLETED":
                # Handle completed payment
                payment_id = resource.get("parent_payment")
                if payment_id:
                    # Find the transaction associated with this payment
                    transaction = Transaction.query.filter_by(
                        external_transaction_id=payment_id,
                        payment_provider="paypal"
                    ).first()
                    
                    if transaction:
                        return self.update_transaction_status(
                            transaction.id,
                            TransactionStatus.COMPLETED,
                            f"Payment completed via PayPal webhook. Sale ID: {resource.get('id')}"
                        )
            
            elif event_type == "PAYMENT.SALE.DENIED":
                # Handle denied payment
                payment_id = resource.get("parent_payment")
                if payment_id:
                    transaction = Transaction.query.filter_by(
                        external_transaction_id=payment_id,
                        payment_provider="paypal"
                    ).first()
                    
                    if transaction:
                        return self.update_transaction_status(
                            transaction.id,
                            TransactionStatus.FAILED,
                            f"Payment denied via PayPal webhook. Sale ID: {resource.get('id')}"
                        )
            
            elif event_type == "PAYMENT.SALE.REFUNDED":
                # Handle refunded payment
                payment_id = resource.get("parent_payment")
                if payment_id:
                    transaction = Transaction.query.filter_by(
                        external_transaction_id=payment_id,
                        payment_provider="paypal"
                    ).first()
                    
                    if transaction:
                        return self.update_transaction_status(
                            transaction.id,
                            TransactionStatus.REFUNDED,
                            f"Payment refunded via PayPal webhook. Sale ID: {resource.get('id')}"
                        )
            
            elif event_type == "PAYOUTS.ITEM.COMPLETED":
                # Handle completed payout
                payout_item_id = resource.get("payout_item_id")
                if payout_item_id:
                    transaction = Transaction.query.filter_by(
                        external_transaction_id=payout_item_id,
                        payment_provider="paypal"
                    ).first()
                    
                    if transaction:
                        return self.update_transaction_status(
                            transaction.id,
                            TransactionStatus.COMPLETED,
                            f"Payout completed via PayPal webhook. Payout Item ID: {payout_item_id}"
                        )
            
            elif event_type == "PAYOUTS.ITEM.FAILED":
                # Handle failed payout
                payout_item_id = resource.get("payout_item_id")
                if payout_item_id:
                    transaction = Transaction.query.filter_by(
                        external_transaction_id=payout_item_id,
                        payment_provider="paypal"
                    ).first()
                    
                    if transaction:
                        return self.update_transaction_status(
                            transaction.id,
                            TransactionStatus.FAILED,
                            f"Payout failed via PayPal webhook. Payout Item ID: {payout_item_id}"
                        )
            
            # For other event types, just log them
            logger.info(f"Unhandled PayPal webhook event type: {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing PayPal webhook event: {str(e)}")
            return False
            
# Create a singleton instance
paypal_service = PayPalService(sandbox_mode=True)