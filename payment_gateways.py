import os
import json
import uuid
import logging
import requests
import stripe
from datetime import datetime
from app import db
from models import PaymentGateway, Transaction, TransactionStatus, TransactionType, PaymentGatewayType

logger = logging.getLogger(__name__)

def check_gateway_status(gateway):
    """
    Check the status of a payment gateway
    
    Args:
        gateway: PaymentGateway instance to check
        
    Returns:
        tuple: (status, message) where status is 'ok', 'warning', or 'error'
    """
    if not gateway.is_active:
        return ('warning', 'Gateway is disabled')
    
    # Stripe gateway check
    if gateway.gateway_type == PaymentGatewayType.STRIPE:
        if not stripe.api_key:
            return ('error', 'Stripe API key not configured')
        
        try:
            # Simple API call to check Stripe connectivity
            stripe.Balance.retrieve()
            return ('ok', 'Connected to Stripe API')
        except stripe.error.AuthenticationError:
            return ('error', 'Invalid Stripe API key')
        except Exception as e:
            return ('error', f'Stripe API error: {str(e)}')
    
    # XRP Ledger gateway check
    elif gateway.gateway_type == PaymentGatewayType.XRP_LEDGER:
        try:
            # Import here to avoid circular imports
            from xrp_ledger import test_connection
            status = test_connection()
            if status:
                return ('ok', 'Connected to XRP Ledger')
            else:
                return ('error', 'Failed to connect to XRP Ledger')
        except Exception as e:
            return ('error', f'XRP Ledger error: {str(e)}')
    
    # Blockchain gateway check
    elif gateway.gateway_type == PaymentGatewayType.COINBASE:
        try:
            response = requests.get('https://api.coinbase.com/v2/time')
            if response.status_code == 200:
                return ('ok', 'Connected to Coinbase API')
            else:
                return ('warning', f'Coinbase API responded with status {response.status_code}')
        except Exception as e:
            return ('error', f'Coinbase API error: {str(e)}')
    
    # PayPal gateway check
    elif gateway.gateway_type == PaymentGatewayType.PAYPAL:
        # For now just return a simple status based on configuration
        if gateway.api_key and gateway.api_endpoint:
            return ('ok', 'PayPal configuration present')
        else:
            return ('warning', 'PayPal configuration incomplete')
    
    # Default for other gateway types
    elif gateway.api_endpoint:
        try:
            # Simple connectivity check to the API endpoint
            response = requests.get(gateway.api_endpoint, timeout=5)
            if response.status_code < 400:
                return ('ok', f'API endpoint responding with status {response.status_code}')
            else:
                return ('warning', f'API endpoint responded with status {response.status_code}')
        except Exception as e:
            return ('error', f'API endpoint error: {str(e)}')
    
    return ('warning', 'Gateway status unknown')

# Set up Stripe with API key from environment
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def init_payment_gateways():
    """Initialize payment gateways in the database if they don't exist"""
    try:
        # Simply check if Stripe gateway exists using the ORM
        stripe_gateway = PaymentGateway.query.filter_by(gateway_type=PaymentGatewayType.STRIPE).first()
        
        if not stripe_gateway:
            # Create Stripe gateway with minimal required fields
            stripe_gateway = PaymentGateway(
                name="Stripe",
                gateway_type=PaymentGatewayType.STRIPE,
                api_endpoint="https://api.stripe.com",
                api_key=os.environ.get('STRIPE_SECRET_KEY'),
                webhook_secret=os.environ.get('STRIPE_WEBHOOK_SECRET', ''),
                ethereum_address=None,
                is_active=True
            )
            db.session.add(stripe_gateway)
            db.session.commit()
            logger.info("Stripe payment gateway initialized")
        
        # Initialize other gateways as needed...
        
        return True
    
    except Exception as e:
        logger.error(f"Error initializing payment gateways: {str(e)}")
        return False

def get_gateway_handler(gateway_id=None, gateway_type=None):
    """Get a payment gateway handler based on ID or type"""
    try:
        gateway = None
        
        if gateway_id:
            gateway = PaymentGateway.query.get(gateway_id)
        elif gateway_type:
            gateway = PaymentGateway.query.filter_by(
                gateway_type=gateway_type,
                is_active=True
            ).first()
        
        if not gateway:
            logger.error(f"Payment gateway not found: id={gateway_id}, type={gateway_type}")
            return None
        
        # Map gateway types to handler classes
        handlers = {
            PaymentGatewayType.STRIPE: StripeGateway,
            PaymentGatewayType.PAYPAL: PayPalGateway,
            # Add more handlers as needed
        }
        
        handler_class = handlers.get(gateway.gateway_type)
        
        if not handler_class:
            logger.error(f"No handler available for gateway type: {gateway.gateway_type}")
            return None
        
        return handler_class(gateway.id)
    
    except Exception as e:
        logger.error(f"Error getting gateway handler: {str(e)}")
        return None

class PaymentGatewayInterface:
    """Base interface for payment gateway interactions"""
    
    def __init__(self, gateway_id):
        self.gateway = PaymentGateway.query.get(gateway_id)
        if not self.gateway:
            raise ValueError(f"Payment gateway with ID {gateway_id} not found")
            
        if not self.gateway.is_active:
            raise ValueError(f"Payment gateway {self.gateway.name} is not active")
    
    def process_payment(self, amount, currency, description, user_id, metadata=None):
        """Process a payment through the gateway"""
        raise NotImplementedError("Subclasses must implement process_payment")
    
    def check_payment_status(self, payment_id):
        """Check the status of a payment"""
        raise NotImplementedError("Subclasses must implement check_payment_status")
    
    def refund_payment(self, payment_id, amount=None):
        """Refund a payment"""
        raise NotImplementedError("Subclasses must implement refund_payment")
    
    def _create_transaction_record(self, amount, currency, user_id, description, status=TransactionStatus.PENDING):
        """Create a transaction record in the database"""
        try:
            # Using the transaction service to create a transaction
            from transaction_service import create_transaction
            
            extended_description = f"{description} (via {self.gateway.name})"
            
            transaction, error = create_transaction(
                user_id=user_id,
                amount=amount,
                currency=currency,
                transaction_type=TransactionType.PAYMENT,  # This is an enum value
                description=extended_description,
                send_email=True  # Send email notification
            )
            
            if error:
                logger.error(f"Error creating transaction: {error}")
                # Fallback to direct creation if transaction service fails
                transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}-{int(datetime.utcnow().timestamp())}"
                
                transaction = Transaction(
                    transaction_id=transaction_id,
                    user_id=user_id,
                    amount=amount,
                    currency=currency,
                    transaction_type=TransactionType.PAYMENT,
                    status=status,
                    description=extended_description,
                    gateway_id=self.gateway.id,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(transaction)
                db.session.commit()
            
            # Update the gateway ID explicitly since transaction_service doesn't set it
            transaction.gateway_id = self.gateway.id
            transaction.status = status  # Use the specified status
            db.session.commit()
            
            return transaction
            
        except Exception as e:
            logger.error(f"Error in _create_transaction_record: {str(e)}")
            # Fallback to direct creation
            transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}-{int(datetime.utcnow().timestamp())}"
            
            transaction = Transaction(
                transaction_id=transaction_id,
                user_id=user_id,
                amount=amount,
                currency=currency,
                transaction_type=TransactionType.PAYMENT,
                status=status,
                description=description,
                gateway_id=self.gateway.id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            return transaction


class StripeGateway(PaymentGatewayInterface):
    """Stripe payment gateway implementation using the Stripe Python library"""
    
    def process_payment(self, amount, currency, description, user_id, metadata=None):
        """
        Process a payment through Stripe
        
        Creates a PaymentIntent that can be used with Stripe's checkout page or Elements
        """
        try:
            # Create transaction record
            transaction = self._create_transaction_record(
                amount, currency, user_id, description
            )
            
            # Prepare metadata
            stripe_metadata = {
                "transaction_id": transaction.transaction_id,
                "user_id": str(user_id)
            }
            
            if metadata:
                stripe_metadata.update(metadata)
            
            # Check if this is a test payment with specific scenarios
            is_test = metadata and metadata.get('test', False)
            test_scenario = metadata and metadata.get('scenario')
            
            # Base payment intent parameters
            payment_intent_params = {
                "amount": int(amount * 100),  # Convert to cents
                "currency": currency.lower(),
                "description": description,
                "metadata": stripe_metadata,
                "payment_method_types": ["card"],
            }
            
            # For test scenarios, modify parameters as needed
            if is_test and test_scenario:
                logger.info(f"Processing test payment with scenario: {test_scenario}")
                
                if test_scenario == 'failure':
                    # For simulating failures in the test UI
                    payment_intent_params["metadata"]["test_failure"] = "true"
                elif test_scenario == '3ds':
                    # For simulating 3D Secure in the test UI
                    payment_intent_params["metadata"]["test_3ds"] = "true"
                elif test_scenario == 'webhook':
                    # For simulating webhook processing
                    payment_intent_params["metadata"]["test_webhook"] = "true"
            
            # Create a PaymentIntent using the Stripe Python library
            payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
            
            # Update transaction with Stripe payment intent ID
            transaction.status = TransactionStatus.PROCESSING
            transaction.description = f"{description} (Stripe Payment Intent: {payment_intent.id})"
            db.session.commit()
            
            # Send email notification about the pending payment
            try:
                from email_service import send_payment_initiated_email
                from models import User
                
                user = User.query.get(user_id)
                if user:
                    send_payment_initiated_email(user, transaction)
            except Exception as email_error:
                logger.warning(f"Failed to send payment initiated email: {str(email_error)}")
            
            return {
                "success": True,
                "transaction_id": transaction.transaction_id,
                "payment_intent_id": payment_intent.id,
                "client_secret": payment_intent.client_secret,
                "amount": amount,
                "currency": currency
            }
        
        except stripe.error.StripeError as se:
            # Handle Stripe-specific errors
            error_message = str(se)
            logger.error(f"Stripe error: {error_message}")
            
            # Update transaction status
            try:
                transaction.status = TransactionStatus.FAILED
                transaction.description = f"{description} (Error: {error_message})"
                db.session.commit()
            except Exception:
                pass  # Ignore secondary errors in error handling
            
            return {
                "success": False,
                "transaction_id": transaction.transaction_id if transaction else None,
                "error": error_message
            }
        except Exception as e:
            logger.error(f"Error processing Stripe payment: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_payment_status(self, payment_id):
        """Check the status of a Stripe payment using the Stripe Python library"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=payment_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Extract Stripe payment intent ID from description
            import re
            match = re.search(r"Stripe Payment Intent: (pi_[a-zA-Z0-9]+)", transaction.description)
            
            if not match:
                return {"success": False, "error": "Stripe Payment Intent ID not found"}
            
            stripe_payment_id = match.group(1)
            
            # Retrieve payment intent using Stripe library
            payment_intent = stripe.PaymentIntent.retrieve(stripe_payment_id)
            
            # Map Stripe status to our status
            status_mapping = {
                "succeeded": TransactionStatus.COMPLETED,
                "processing": TransactionStatus.PROCESSING,
                "requires_payment_method": TransactionStatus.PENDING,
                "requires_confirmation": TransactionStatus.PENDING,
                "requires_action": TransactionStatus.PENDING,
                "canceled": TransactionStatus.FAILED
            }
            
            stripe_status = payment_intent.status
            internal_status = status_mapping.get(stripe_status, transaction.status)
            
            # Update transaction status if changed
            if transaction.status != internal_status:
                transaction.status = internal_status
                db.session.commit()
                
                # Send email if status changed to completed or failed
                if internal_status in [TransactionStatus.COMPLETED, TransactionStatus.FAILED]:
                    try:
                        from email_service import send_transaction_confirmation_email
                        from models import User
                        
                        user = User.query.get(transaction.user_id)
                        if user:
                            send_transaction_confirmation_email(user, transaction)
                    except Exception as email_error:
                        logger.warning(f"Failed to send status update email: {str(email_error)}")
            
            return {
                "success": True,
                "transaction_id": transaction.transaction_id,
                "payment_intent_id": stripe_payment_id,
                "status": stripe_status,
                "internal_status": internal_status.value,
                "amount": transaction.amount,
                "currency": transaction.currency
            }
        
        except stripe.error.StripeError as se:
            # Handle Stripe-specific errors
            error_message = str(se)
            logger.error(f"Stripe error: {error_message}")
            return {
                "success": False,
                "transaction_id": transaction.transaction_id if transaction else None,
                "error": error_message
            }
        except Exception as e:
            logger.error(f"Error checking Stripe payment status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def refund_payment(self, payment_id, amount=None):
        """Refund a Stripe payment"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=payment_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            if transaction.status != TransactionStatus.COMPLETED:
                return {"success": False, "error": "Transaction not completed, cannot refund"}
            
            # Extract Stripe payment intent ID from description
            import re
            match = re.search(r"Stripe Payment Intent: (pi_[a-zA-Z0-9]+)", transaction.description)
            
            if not match:
                return {"success": False, "error": "Stripe Payment Intent ID not found"}
            
            stripe_payment_id = match.group(1)
            
            # Create refund using Stripe library
            refund_params = {
                "payment_intent": stripe_payment_id,
            }
            
            if amount:
                refund_params["amount"] = int(amount * 100)  # Convert to cents
            
            refund = stripe.Refund.create(**refund_params)
            
            # Update transaction status
            transaction.status = TransactionStatus.REFUNDED
            transaction.description = f"{transaction.description} (Refunded: {refund.id})"
            db.session.commit()
            
            # Send refund notification email
            try:
                from email_service import send_refund_notification_email
                from models import User
                
                user = User.query.get(transaction.user_id)
                if user:
                    send_refund_notification_email(user, transaction, amount or transaction.amount)
            except Exception as email_error:
                logger.warning(f"Failed to send refund notification email: {str(email_error)}")
            
            return {
                "success": True,
                "transaction_id": transaction.transaction_id,
                "refund_id": refund.id,
                "status": refund.status,
                "amount": amount or transaction.amount,
                "currency": transaction.currency
            }
        
        except stripe.error.StripeError as se:
            # Handle Stripe-specific errors
            error_message = str(se)
            logger.error(f"Stripe error: {error_message}")
            return {
                "success": False,
                "transaction_id": transaction.transaction_id,
                "error": error_message
            }
        except Exception as e:
            logger.error(f"Error refunding Stripe payment: {str(e)}")
            return {"success": False, "error": str(e)}


class PayPalGateway(PaymentGatewayInterface):
    """PayPal payment gateway implementation"""
    
    def process_payment(self, amount, currency, description, user_id, metadata=None):
        """Process a payment through PayPal"""
        try:
            # Create transaction record
            transaction = self._create_transaction_record(
                amount, currency, user_id, description
            )
            
            # Get access token
            auth_response = requests.post(
                f"{self.gateway.api_endpoint}/v1/oauth2/token",
                auth=(self.gateway.api_key, self.gateway.webhook_secret),  # Using webhook_secret as PayPal secret
                data={"grant_type": "client_credentials"}
            )
            
            auth_data = auth_response.json()
            
            if auth_response.status_code != 200:
                transaction.status = TransactionStatus.FAILED
                transaction.description = f"{description} (Error: Failed to authenticate with PayPal)"
                db.session.commit()
                
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": "Failed to authenticate with PayPal"
                }
            
            access_token = auth_data["access_token"]
            
            # Prepare API request to PayPal
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {
                            "currency_code": currency.upper(),
                            "value": str(amount)
                        },
                        "description": description,
                        "custom_id": transaction.transaction_id
                    }
                ],
                "application_context": {
                    "return_url": f"https://nvcplatform.net/payments/return?transaction_id={transaction.transaction_id}",
                    "cancel_url": f"https://nvcplatform.net/payments/cancel?transaction_id={transaction.transaction_id}"
                }
            }
            
            # Make API request to PayPal
            response = requests.post(
                f"{self.gateway.api_endpoint}/v2/checkout/orders",
                headers=headers,
                json=payload
            )
            
            data = response.json()
            
            if response.status_code == 201:
                # Update transaction with PayPal order ID
                transaction.status = TransactionStatus.PROCESSING
                transaction.description = f"{description} (PayPal Order ID: {data['id']})"
                db.session.commit()
                
                # Find approval URL
                approval_url = next(
                    link["href"] for link in data["links"] if link["rel"] == "approve"
                )
                
                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "paypal_order_id": data["id"],
                    "approval_url": approval_url,
                    "amount": amount,
                    "currency": currency
                }
            else:
                # Handle error
                transaction.status = TransactionStatus.FAILED
                transaction.description = f"{description} (Error: {data.get('message', 'Unknown error')})"
                db.session.commit()
                
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": data.get("message", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Error processing PayPal payment: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_payment_status(self, payment_id):
        """Check the status of a PayPal payment"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=payment_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Extract PayPal order ID from description
            import re
            match = re.search(r"PayPal Order ID: ([A-Z0-9]+)", transaction.description)
            
            if not match:
                return {"success": False, "error": "PayPal Order ID not found"}
            
            paypal_order_id = match.group(1)
            
            # Get access token
            auth_response = requests.post(
                f"{self.gateway.api_endpoint}/v1/oauth2/token",
                auth=(self.gateway.api_key, self.gateway.webhook_secret),
                data={"grant_type": "client_credentials"}
            )
            
            auth_data = auth_response.json()
            
            if auth_response.status_code != 200:
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": "Failed to authenticate with PayPal"
                }
            
            access_token = auth_data["access_token"]
            
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Make API request to PayPal
            response = requests.get(
                f"{self.gateway.api_endpoint}/v2/checkout/orders/{paypal_order_id}",
                headers=headers
            )
            
            data = response.json()
            
            if response.status_code == 200:
                # Map PayPal status to our status
                status_mapping = {
                    "CREATED": TransactionStatus.PENDING,
                    "SAVED": TransactionStatus.PENDING,
                    "APPROVED": TransactionStatus.PROCESSING,
                    "VOIDED": TransactionStatus.FAILED,
                    "COMPLETED": TransactionStatus.COMPLETED,
                    "PAYER_ACTION_REQUIRED": TransactionStatus.PENDING
                }
                
                paypal_status = data["status"]
                internal_status = status_mapping.get(paypal_status, transaction.status)
                
                # Update transaction status if changed
                if transaction.status != internal_status:
                    transaction.status = internal_status
                    db.session.commit()
                
                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "paypal_order_id": paypal_order_id,
                    "status": paypal_status,
                    "internal_status": internal_status.value,
                    "amount": transaction.amount,
                    "currency": transaction.currency
                }
            else:
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": data.get("message", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Error checking PayPal payment status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def refund_payment(self, payment_id, amount=None):
        """Refund a PayPal payment"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=payment_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            if transaction.status != TransactionStatus.COMPLETED:
                return {"success": False, "error": "Transaction not completed, cannot refund"}
            
            # Extract PayPal order ID from description
            import re
            match = re.search(r"PayPal Order ID: ([A-Z0-9]+)", transaction.description)
            
            if not match:
                return {"success": False, "error": "PayPal Order ID not found"}
            
            paypal_order_id = match.group(1)
            
            # Get access token
            auth_response = requests.post(
                f"{self.gateway.api_endpoint}/v1/oauth2/token",
                auth=(self.gateway.api_key, self.gateway.webhook_secret),
                data={"grant_type": "client_credentials"}
            )
            
            auth_data = auth_response.json()
            
            if auth_response.status_code != 200:
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": "Failed to authenticate with PayPal"
                }
            
            access_token = auth_data["access_token"]
            
            # Get capture ID from order
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            order_response = requests.get(
                f"{self.gateway.api_endpoint}/v2/checkout/orders/{paypal_order_id}",
                headers=headers
            )
            
            order_data = order_response.json()
            
            if order_response.status_code != 200:
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": order_data.get("message", "Failed to get order details")
                }
            
            # Get capture ID
            capture_id = order_data["purchase_units"][0]["payments"]["captures"][0]["id"]
            
            # Prepare refund payload
            refund_payload = {}
            
            if amount:
                refund_payload["amount"] = {
                    "value": str(amount),
                    "currency_code": transaction.currency.upper()
                }
            
            # Make refund request
            refund_response = requests.post(
                f"{self.gateway.api_endpoint}/v2/payments/captures/{capture_id}/refund",
                headers=headers,
                json=refund_payload
            )
            
            refund_data = refund_response.json()
            
            if refund_response.status_code == 201:
                # Update transaction status
                transaction.status = TransactionStatus.REFUNDED
                transaction.description = f"{transaction.description} (Refunded: {refund_data['id']})"
                db.session.commit()
                
                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "refund_id": refund_data["id"],
                    "status": refund_data["status"],
                    "amount": amount or transaction.amount,
                    "currency": transaction.currency
                }
            else:
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": refund_data.get("message", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Error refunding PayPal payment: {str(e)}")
            return {"success": False, "error": str(e)}


class CoinbaseGateway(PaymentGatewayInterface):
    """Coinbase payment gateway implementation for crypto payments"""
    
    def process_payment(self, amount, currency, description, user_id, metadata=None):
        """Process a payment through Coinbase Commerce"""
        try:
            # Create transaction record
            transaction = self._create_transaction_record(
                amount, currency, user_id, description
            )
            
            # Prepare API request to Coinbase
            headers = {
                "X-CC-Api-Key": self.gateway.api_key,
                "X-CC-Version": "2018-03-22",
                "Content-Type": "application/json"
            }
            
            pricing = {
                currency.upper(): str(amount)
            }
            
            # For crypto payments, we need a conversion to the requested currency
            if currency.upper() not in ["BTC", "ETH", "USDC", "DAI"]:
                # Add pricing in ETH as fallback
                pricing["ETH"] = "RESOLVE"
            
            payload = {
                "name": "nvcplatform.net Payment",
                "description": description,
                "pricing_type": "fixed_price",
                "local_price": {
                    "amount": str(amount),
                    "currency": currency.upper()
                },
                "metadata": {
                    "transaction_id": transaction.transaction_id,
                    "user_id": str(user_id)
                },
                "redirect_url": f"https://nvcplatform.net/payments/return?transaction_id={transaction.transaction_id}",
                "cancel_url": f"https://nvcplatform.net/payments/cancel?transaction_id={transaction.transaction_id}"
            }
            
            if metadata:
                payload["metadata"].update(metadata)
            
            # Make API request to Coinbase
            response = requests.post(
                f"{self.gateway.api_endpoint}/charges",
                headers=headers,
                json=payload
            )
            
            data = response.json()
            
            if response.status_code == 201:
                # Update transaction with Coinbase charge ID
                transaction.status = TransactionStatus.PROCESSING
                transaction.description = f"{description} (Coinbase Charge ID: {data['data']['id']})"
                db.session.commit()
                
                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "charge_id": data["data"]["id"],
                    "hosted_url": data["data"]["hosted_url"],
                    "amount": amount,
                    "currency": currency
                }
            else:
                # Handle error
                transaction.status = TransactionStatus.FAILED
                transaction.description = f"{description} (Error: {data.get('error', {}).get('message', 'Unknown error')})"
                db.session.commit()
                
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": data.get("error", {}).get("message", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Error processing Coinbase payment: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_payment_status(self, payment_id):
        """Check the status of a Coinbase payment"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=payment_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Extract Coinbase charge ID from description
            import re
            match = re.search(r"Coinbase Charge ID: ([a-zA-Z0-9-]+)", transaction.description)
            
            if not match:
                return {"success": False, "error": "Coinbase Charge ID not found"}
            
            coinbase_charge_id = match.group(1)
            
            # Prepare API request
            headers = {
                "X-CC-Api-Key": self.gateway.api_key,
                "X-CC-Version": "2018-03-22",
                "Content-Type": "application/json"
            }
            
            # Make API request to Coinbase
            response = requests.get(
                f"{self.gateway.api_endpoint}/charges/{coinbase_charge_id}",
                headers=headers
            )
            
            data = response.json()
            
            if response.status_code == 200:
                # Map Coinbase status to our status
                charge_data = data["data"]
                coinbase_status = charge_data["timeline"][-1]["status"]
                
                status_mapping = {
                    "NEW": TransactionStatus.PENDING,
                    "PENDING": TransactionStatus.PROCESSING,
                    "COMPLETED": TransactionStatus.COMPLETED,
                    "EXPIRED": TransactionStatus.FAILED,
                    "CANCELED": TransactionStatus.FAILED,
                    "UNRESOLVED": TransactionStatus.PROCESSING,
                    "RESOLVED": TransactionStatus.COMPLETED,
                    "RESOLVED_MANUALLY": TransactionStatus.COMPLETED
                }
                
                internal_status = status_mapping.get(coinbase_status, transaction.status)
                
                # Update transaction status if changed
                if transaction.status != internal_status:
                    transaction.status = internal_status
                    db.session.commit()
                
                # For completed transactions, check if we should store the blockchain hash
                if internal_status == TransactionStatus.COMPLETED and not transaction.eth_transaction_hash:
                    # Try to extract transaction hash from payments
                    if "payments" in charge_data and charge_data["payments"]:
                        for payment in charge_data["payments"]:
                            if payment["network"] == "ethereum":
                                transaction.eth_transaction_hash = payment["transaction_id"]
                                db.session.commit()
                                break
                
                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "charge_id": coinbase_charge_id,
                    "status": coinbase_status,
                    "internal_status": internal_status.value,
                    "amount": transaction.amount,
                    "currency": transaction.currency,
                    "blockchain_tx": transaction.eth_transaction_hash
                }
            else:
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": data.get("error", {}).get("message", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Error checking Coinbase payment status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def refund_payment(self, payment_id, amount=None):
        """
        Refund a Coinbase payment - Note: Coinbase Commerce doesn't support refunds through API
        This would typically be handled manually in the Coinbase Commerce dashboard
        """
        return {
            "success": False, 
            "error": "Automatic refunds are not supported for Coinbase payments. Please process manually."
        }


def get_gateway_handler(gateway_id):
    """
    Factory function to get the appropriate payment gateway handler
    
    Args:
        gateway_id (int): ID of the payment gateway in the database
    
    Returns:
        PaymentGatewayInterface: The appropriate payment gateway handler
    """
    try:
        gateway = PaymentGateway.query.get(gateway_id)
        
        if not gateway:
            raise ValueError(f"Payment gateway with ID {gateway_id} not found")
        
        if not gateway.is_active:
            raise ValueError(f"Payment gateway {gateway.name} is not active")
        
        # Select the appropriate handler based on gateway type
        if gateway.gateway_type.value == "stripe":
            return StripeGateway(gateway_id)
        elif gateway.gateway_type.value == "paypal":
            return PayPalGateway(gateway_id)
        elif gateway.gateway_type.value == "coinbase":
            return CoinbaseGateway(gateway_id)
        else:
            raise ValueError(f"Unsupported payment gateway type: {gateway.gateway_type.value}")
    
    except Exception as e:
        logger.error(f"Error getting gateway handler: {str(e)}")
        raise
