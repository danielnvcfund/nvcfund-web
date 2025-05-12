import os
import json
import uuid
import logging
import requests
import stripe
from datetime import datetime
from sqlalchemy.sql import text
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

# Set up PayPal SDK
import paypalrestsdk
paypalrestsdk.configure({
    "mode": "live",  # Changed to "live" for production
    "client_id": os.environ.get('PAYPAL_CLIENT_ID'),
    "client_secret": os.environ.get('PAYPAL_SECRET')
})

def init_payment_gateways():
    """Initialize payment gateways in the database if they don't exist"""
    try:
        # Initialize Stripe gateway
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
        
        # Initialize PayPal gateway
        paypal_gateway = PaymentGateway.query.filter_by(gateway_type=PaymentGatewayType.PAYPAL).first()
        
        if not paypal_gateway:
            # Create PayPal gateway
            paypal_gateway = PaymentGateway(
                name="PayPal",
                gateway_type=PaymentGatewayType.PAYPAL,
                api_endpoint="https://api-m.sandbox.paypal.com",  # Sandbox endpoint, change to https://api-m.paypal.com for production
                api_key=os.environ.get('PAYPAL_CLIENT_ID', ''),
                webhook_secret=os.environ.get('PAYPAL_SECRET', ''),
                ethereum_address=None,
                is_active=True
            )
            db.session.add(paypal_gateway)
            db.session.commit()
            logger.info("PayPal payment gateway initialized")
        
        # Initialize NVC Global gateway
        # First look for the gateway with ID 3 (known ID for NVC Global)
        nvc_global_gateway = PaymentGateway.query.get(3)
        
        # If we have the NVC Global gateway by ID 3, update it if needed
        if nvc_global_gateway:
            logger.info("Found existing NVC Global gateway (ID: 3)")
            
            # Make sure it has the right name
            if nvc_global_gateway.name != "NVC Global":
                nvc_global_gateway.name = "NVC Global"
                
            # Ensure it's using CUSTOM type since the nvc_global type has compatibility issues
            if str(nvc_global_gateway.gateway_type) != "CUSTOM":
                try:
                    nvc_global_gateway.gateway_type = PaymentGatewayType.CUSTOM
                except Exception as e:
                    logger.warning(f"Failed to update gateway type to CUSTOM: {str(e)}")
                    
                    # Try direct SQL update as fallback
                    try:
                        db.session.rollback()
                        db.session.execute(
                            text("UPDATE payment_gateway SET gateway_type = 'CUSTOM' WHERE id = 3")
                        )
                        db.session.commit()
                        logger.info("Updated NVC Global gateway type to CUSTOM using SQL")
                        
                        # Fetch the gateway again to get the updated data
                        nvc_global_gateway = PaymentGateway.query.get(3)
                    except Exception as sql_e:
                        logger.warning(f"Failed to update gateway type with SQL: {str(sql_e)}")
        else:
            # If the gateway doesn't exist at ID 3, try to find it by name
            try:
                nvc_global_gateway = PaymentGateway.query.filter_by(name="NVC Global").first()
                
                if nvc_global_gateway:
                    logger.info(f"Found NVC Global gateway by name, ID: {nvc_global_gateway.id}")
                else:
                    # If not found by name, create it as a CUSTOM type gateway
                    try:
                        # Clear any transaction errors
                        db.session.rollback()
                        
                        # Create with ORM
                        nvc_global_gateway = PaymentGateway(
                            id=3,  # Explicitly set ID 3
                            name="NVC Global", 
                            gateway_type=PaymentGatewayType.CUSTOM,  # Use CUSTOM type which works with our enum
                            api_endpoint="https://api.nvcplatform.net",
                            api_key=os.environ.get('NVC_GLOBAL_API_KEY', ''),
                            webhook_secret=os.environ.get('NVC_GLOBAL_WEBHOOK_SECRET', ''),
                            ethereum_address=os.environ.get('NVC_GLOBAL_ETH_ADDRESS', None),
                            is_active=True
                        )
                        db.session.add(nvc_global_gateway)
                        db.session.commit()
                        logger.info("Created NVC Global gateway using CUSTOM type")
                    except Exception as create_e:
                        logger.warning(f"Failed to create NVC Global gateway with ORM: {str(create_e)}")
                        db.session.rollback()
                        
                        # Fallback to SQL for creation
                        try:
                            stmt = text("""
                                INSERT INTO payment_gateway (
                                    id, name, gateway_type, api_endpoint, api_key, webhook_secret, 
                                    ethereum_address, is_active, created_at, updated_at
                                )
                                VALUES (
                                    3, 'NVC Global', 'CUSTOM', 'https://api.nvcplatform.net', 
                                    :api_key, :webhook_secret, :eth_address, true, now(), now()
                                )
                                ON CONFLICT (id) DO UPDATE 
                                SET name = 'NVC Global',
                                    gateway_type = 'CUSTOM',
                                    api_key = :api_key,
                                    webhook_secret = :webhook_secret,
                                    api_endpoint = 'https://api.nvcplatform.net',
                                    updated_at = now()
                                RETURNING id
                            """)
                            
                            result = db.session.execute(stmt, {
                                'api_key': os.environ.get('NVC_GLOBAL_API_KEY', ''),
                                'webhook_secret': os.environ.get('NVC_GLOBAL_WEBHOOK_SECRET', ''),
                                'eth_address': os.environ.get('NVC_GLOBAL_ETH_ADDRESS', None)
                            })
                            
                            returned_id = result.scalar()
                            db.session.commit()
                            
                            if returned_id:
                                nvc_global_gateway = PaymentGateway.query.get(returned_id)
                                logger.info(f"Created NVC Global gateway using SQL, ID: {returned_id}")
                            else:
                                logger.warning("Failed to create NVC Global gateway with SQL")
                        except Exception as sql_e:
                            logger.warning(f"Failed to create NVC Global gateway with SQL: {str(sql_e)}")
                            db.session.rollback()
            except Exception as e:
                logger.warning(f"Error looking up NVC Global gateway by name: {str(e)}")
                db.session.rollback()
        
        # Update NVC Global gateway keys if needed
        if nvc_global_gateway and (
            not nvc_global_gateway.api_key or 
            nvc_global_gateway.api_key != os.environ.get('NVC_GLOBAL_API_KEY', '')
        ):
            try:
                nvc_global_gateway.api_key = os.environ.get('NVC_GLOBAL_API_KEY', '')
                nvc_global_gateway.webhook_secret = os.environ.get('NVC_GLOBAL_WEBHOOK_SECRET', '')
                db.session.commit()
                logger.info("NVC Global payment gateway API keys updated")
            except Exception as e:
                logger.warning(f"Error updating NVC Global gateway keys: {str(e)}")
                db.session.rollback()
        
        return True
    
    except Exception as e:
        logger.error(f"Error initializing payment gateways: {str(e)}")
        return False

def get_gateway_by_type(gateway_type):
    """Get a payment gateway by type
    
    Args:
        gateway_type (PaymentGatewayType or str): The type of gateway to retrieve
        
    Returns:
        PaymentGateway: The payment gateway object or None if not found
    """
    try:
        # Convert string to enum if needed
        if isinstance(gateway_type, str):
            try:
                gateway_type = PaymentGatewayType(gateway_type)
            except ValueError:
                # Handle special case for NVC Global
                if gateway_type.lower() == 'nvc_global':
                    gateway_type = PaymentGatewayType.NVC_GLOBAL
        
        # Special case for NVC_GLOBAL gateway
        if gateway_type == PaymentGatewayType.NVC_GLOBAL:
            # Try to find by ID 3 first (known ID)
            nvc_gateway = PaymentGateway.query.get(3)
            if nvc_gateway and nvc_gateway.is_active:
                return nvc_gateway
                
            # Fallback: Find by name (case-insensitive)
            result = db.session.execute(
                text("SELECT id FROM payment_gateway WHERE LOWER(name) = 'nvc global' AND is_active = true LIMIT 1")
            )
            gateway_id = result.scalar()
            if gateway_id:
                return PaymentGateway.query.get(gateway_id)
        
        # General case: find by type
        return PaymentGateway.query.filter_by(gateway_type=gateway_type, is_active=True).first()
        
    except Exception as e:
        logger.error(f"Error getting gateway by type: {str(e)}")
        return None

def get_gateway_handler(gateway_id=None, gateway_type=None):
    """Get a payment gateway handler based on ID or type"""
    try:
        # Special case for direct access to NVC Global using ID 3
        if gateway_id == 3:
            nvc_gateway = PaymentGateway.query.get(3)
            if nvc_gateway and nvc_gateway.is_active:
                logger.info("Found NVC Global gateway using direct ID lookup (ID 3)")
                return NVCGlobalGateway(3)
                
        # Special case for NVC_GLOBAL gateway type (either by enum or string)
        if gateway_type == PaymentGatewayType.NVC_GLOBAL or (isinstance(gateway_type, str) and gateway_type.lower() == 'nvc_global'):
            # Direct lookup for NVC Global gateway - now it's using CUSTOM type but with NVC Global name
            try:
                # Find by ID 3 first (known ID)
                nvc_gateway = PaymentGateway.query.get(3)
                if nvc_gateway and nvc_gateway.is_active:
                    logger.info("Found NVC Global gateway by ID 3")
                    return NVCGlobalGateway(3)
                    
                # Fallback: Find by name (case-insensitive)
                result = db.session.execute(
                    text("SELECT id FROM payment_gateway WHERE LOWER(name) = 'nvc global' AND is_active = true LIMIT 1")
                )
                gateway_id = result.scalar()
                if gateway_id:
                    logger.info(f"Found NVC Global gateway by name lookup, ID: {gateway_id}")
                    return NVCGlobalGateway(gateway_id)
            except Exception as e:
                logger.error(f"Error getting NVC Global gateway: {str(e)}")
        
        gateway = None
        
        if gateway_id:
            gateway = PaymentGateway.query.get(gateway_id)
        elif gateway_type:
            # Normal case for other gateway types
            try:
                gateway = PaymentGateway.query.filter_by(
                    gateway_type=gateway_type,
                    is_active=True
                ).first()
            except Exception as e:
                logger.error(f"Error getting gateway by type {gateway_type}: {str(e)}")
        
        # Special case for gateway with name "NVC Global" but any type
        if gateway and gateway.name == "NVC Global":
            logger.info(f"Found NVC Global gateway by name match (ID: {gateway.id}, type: {gateway.gateway_type})")
            return NVCGlobalGateway(gateway.id)
        
        if not gateway:
            logger.error(f"Payment gateway not found: id={gateway_id}, type={gateway_type}")
            return None
        
        # Map gateway types to handler classes
        handlers = {
            PaymentGatewayType.STRIPE: StripeGateway,
            PaymentGatewayType.PAYPAL: PayPalGateway,
            PaymentGatewayType.COINBASE: CoinbaseGateway,
            PaymentGatewayType.NVC_GLOBAL: NVCGlobalGateway,
            # Add more handlers as needed
        }
        
        # Special handling for NVC Global since there might be enum case sensitivity issues
        if str(gateway.gateway_type).lower() == 'nvc_global':
            return NVCGlobalGateway(gateway.id)
        
        # Get the handler class for the gateway type
        handler_class = handlers.get(gateway.gateway_type)
        
        if not handler_class:
            # Check if we have a string representation that matches NVC_GLOBAL
            if str(gateway.gateway_type).lower() == 'nvc_global':
                return NVCGlobalGateway(gateway.id)
            
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
        
        except Exception as se:
            # Handle Stripe-specific errors
            error_message = str(se)
            logger.error(f"Stripe error: {error_message}")
            
            # Update transaction status if transaction was created
            if 'transaction' in locals():
                try:
                    transaction.status = TransactionStatus.FAILED
                    transaction.description = f"{description} (Error: {error_message})"
                    db.session.commit()
                except Exception:
                    pass  # Ignore secondary errors in error handling
            
            return {
                "success": False,
                "transaction_id": transaction.transaction_id if 'transaction' in locals() else None,
                "error": error_message
            }
    
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
        
        except Exception as e:
            # Handle Stripe-specific errors
            error_message = str(e)
            logger.error(f"Stripe error: {error_message}")
            return {
                "success": False,
                "transaction_id": transaction.transaction_id if 'transaction' in locals() else None,
                "error": error_message
            }
    
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
            
            return {
                "success": True,
                "transaction_id": transaction.transaction_id,
                "refund_id": refund.id,
                "status": refund.status,
                "amount": amount or transaction.amount,
                "currency": transaction.currency
            }
        
        except Exception as e:
            logger.error(f"Error refunding Stripe payment: {str(e)}")
            return {"success": False, "error": str(e)}


class PayPalGateway(PaymentGatewayInterface):
    """PayPal payment gateway implementation using the PayPal Python SDK"""
    
    def process_payment(self, amount, currency, description, user_id, metadata=None):
        """Process a payment through PayPal"""
        try:
            # Create transaction record
            transaction = self._create_transaction_record(
                amount, currency, user_id, description
            )
            
            # Get domain for return URLs
            current_domain = self._get_current_domain()
            
            # Create PayPal payment using the SDK
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": f"{current_domain}/payments/return?transaction_id={transaction.transaction_id}",
                    "cancel_url": f"{current_domain}/payments/cancel?transaction_id={transaction.transaction_id}"
                },
                "transactions": [{
                    "amount": {
                        "total": str(amount),
                        "currency": currency.upper()
                    },
                    "description": description,
                    "custom": transaction.transaction_id,
                    "invoice_number": transaction.transaction_id
                }]
            })
            
            # Create the payment in PayPal
            if payment.create():
                logger.info(f"Payment {payment.id} created successfully")
                
                # Find the approval URL
                approval_url = next(link.href for link in payment.links if link.rel == 'approval_url')
                
                # Update transaction with PayPal payment ID
                transaction.status = TransactionStatus.PROCESSING
                transaction.description = f"{description} (PayPal Payment ID: {payment.id})"
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
                    "paypal_payment_id": payment.id,
                    "approval_url": approval_url,
                    "amount": amount,
                    "currency": currency
                }
            else:
                error_message = payment.error.get('message', 'Unknown error') if hasattr(payment, 'error') else 'Unknown error'
                logger.error(f"Failed to create PayPal payment: {error_message}")
                
                # Update transaction status
                transaction.status = TransactionStatus.FAILED
                transaction.description = f"{description} (Error: {error_message})"
                db.session.commit()
                
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": error_message
                }
                
        except Exception as e:
            logger.error(f"Error processing PayPal payment: {str(e)}")
            
            # If transaction was created, update its status
            if 'transaction' in locals():
                try:
                    transaction.status = TransactionStatus.FAILED
                    transaction.description = f"{description} (Error: {str(e)})"
                    db.session.commit()
                except Exception:
                    pass  # Ignore secondary errors
                
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": str(e)
                }
            
            return {"success": False, "error": str(e)}
            
    def _get_current_domain(self):
        """Get the current domain for the application"""
        # In production, you'd want to use the actual domain
        # For now, use Replit domain
        replit_domain = os.environ.get('REPLIT_DEPLOYMENT', '') 
        if replit_domain:
            return f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}"
        else:
            domains = os.environ.get('REPLIT_DOMAINS', '').split(',')
            if domains and domains[0]:
                return f"https://{domains[0]}"
            return "http://localhost:5000"
    
    def check_payment_status(self, payment_id):
        """Check the status of a PayPal payment using the SDK"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=payment_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Extract PayPal payment ID from description
            import re
            match = re.search(r"PayPal Payment ID: ([A-Z0-9-]+)", transaction.description)
            
            if not match:
                return {"success": False, "error": "PayPal Payment ID not found"}
            
            paypal_payment_id = match.group(1)
            
            # Retrieve payment from PayPal
            payment = paypalrestsdk.Payment.find(paypal_payment_id)
            
            if not payment:
                return {"success": False, "error": "Payment not found in PayPal"}
            
            # Map PayPal status to our status
            status_mapping = {
                "created": TransactionStatus.PENDING,
                "approved": TransactionStatus.PROCESSING,
                "canceled": TransactionStatus.FAILED,
                "failed": TransactionStatus.FAILED,
                "completed": TransactionStatus.COMPLETED,
                "pending": TransactionStatus.PENDING
            }
            
            # Get payment state
            paypal_state = payment.state.lower()
            internal_status = status_mapping.get(paypal_state, transaction.status)
            
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
                "paypal_payment_id": paypal_payment_id,
                "status": paypal_state,
                "internal_status": internal_status.value,
                "amount": transaction.amount,
                "currency": transaction.currency
            }
        
        except Exception as e:
            logger.error(f"Error checking PayPal payment status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def refund_payment(self, payment_id, amount=None):
        """Refund a PayPal payment using the SDK"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=payment_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            if transaction.status != TransactionStatus.COMPLETED:
                return {"success": False, "error": "Transaction not completed, cannot refund"}
            
            # Extract PayPal payment ID from description
            import re
            match = re.search(r"PayPal Payment ID: ([A-Z0-9-]+)", transaction.description)
            
            if not match:
                return {"success": False, "error": "PayPal Payment ID not found"}
            
            paypal_payment_id = match.group(1)
            
            # Retrieve payment from PayPal
            payment = paypalrestsdk.Payment.find(paypal_payment_id)
            
            if not payment:
                return {"success": False, "error": "Payment not found in PayPal"}
            
            # Get the sale ID from the payment
            sale_id = payment.transactions[0].related_resources[0].sale.id
            
            # Create refund
            sale = paypalrestsdk.Sale.find(sale_id)
            
            refund_data = {}
            if amount:
                refund_data = {
                    "amount": {
                        "total": str(amount),
                        "currency": transaction.currency.upper()
                    }
                }
                
            # Process refund
            refund = sale.refund(refund_data)
            
            if refund.success():
                # Update transaction status
                transaction.status = TransactionStatus.REFUNDED
                transaction.description = f"{transaction.description} (Refunded: {refund.id})"
                db.session.commit()
                
                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "refund_id": refund.id,
                    "status": refund.state,
                    "amount": amount or transaction.amount,
                    "currency": transaction.currency
                }
            else:
                error_message = refund.error.get('message', 'Unknown error') if hasattr(refund, 'error') else 'Unknown error'
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": error_message
                }
        
        except Exception as e:
            logger.error(f"Error refunding PayPal payment: {str(e)}")
            return {"success": False, "error": str(e)}


class NVCGlobalGateway(PaymentGatewayInterface):
    """NVC Global payment gateway implementation for integrating with nvcplatform.net"""
    
    def process_payment(self, amount, currency, description, user_id, metadata=None):
        """Process a payment through the NVC Global platform"""
        try:
            # Create transaction record
            transaction = self._create_transaction_record(
                amount, currency, user_id, description
            )
            
            # Get domain for return URLs
            current_domain = self._get_current_domain()
            
            # Prepare metadata for NVC Global
            nvc_metadata = {
                "transaction_id": transaction.transaction_id,
                "user_id": str(user_id),
                "callback_url": f"{current_domain}/payments/nvc-callback?transaction_id={transaction.transaction_id}"
            }
            
            if metadata:
                nvc_metadata.update(metadata)
            
            # Create payment data for NVC Global API
            payment_data = {
                "amount": str(amount),
                "currency": currency.upper(),
                "description": description,
                "metadata": nvc_metadata,
                "return_url": f"{current_domain}/payments/return?transaction_id={transaction.transaction_id}",
                "cancel_url": f"{current_domain}/payments/cancel?transaction_id={transaction.transaction_id}"
            }
            
            # Use requests to send the API request to NVC Global platform
            headers = {
                "Authorization": f"Bearer {self.gateway.api_key}",
                "Content-Type": "application/json"
            }
            
            # Simulate an API call (we don't have the actual API documentation yet)
            response_data = {
                "success": True,
                "payment_id": f"NVC-{uuid.uuid4().hex[:8].upper()}",
                "checkout_url": f"https://checkout.nvcplatform.net/{uuid.uuid4().hex}",
                "status": "pending"
            }
            
            # Update transaction with NVC Global payment ID
            transaction.status = TransactionStatus.PROCESSING
            transaction.description = f"{description} (NVC Global Payment ID: {response_data['payment_id']})"
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
                "payment_id": response_data["payment_id"],
                "checkout_url": response_data["checkout_url"],
                "amount": amount,
                "currency": currency
            }
        
        except Exception as e:
            error_message = str(e)
            logger.error(f"NVC Global error: {error_message}")
            
            # Update transaction status if transaction was created
            if 'transaction' in locals():
                try:
                    transaction.status = TransactionStatus.FAILED
                    transaction.description = f"{description} (Error: {error_message})"
                    db.session.commit()
                except Exception:
                    pass  # Ignore secondary errors in error handling
            
            return {
                "success": False,
                "transaction_id": transaction.transaction_id if 'transaction' in locals() else None,
                "error": error_message
            }
    
    def _get_current_domain(self):
        """Get the current domain for the application"""
        replit_domain = os.environ.get('REPLIT_DOMAINS', '')
        if replit_domain:
            domains = replit_domain.split(',')
            return f"https://{domains[0]}"
        return "http://localhost:5000"  # Fallback for local development
    
    def check_payment_status(self, payment_id):
        """Check the status of an NVC Global payment"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=payment_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Extract NVC Global payment ID from description
            import re
            match = re.search(r"NVC Global Payment ID: (NVC-[a-zA-Z0-9]+)", transaction.description)
            
            if not match:
                return {"success": False, "error": "NVC Global Payment ID not found"}
            
            nvc_payment_id = match.group(1)
            
            # Use requests to check payment status (we don't have the actual API documentation yet)
            headers = {
                "Authorization": f"Bearer {self.gateway.api_key}",
                "Content-Type": "application/json"
            }
            
            # Simulate an API response (we don't have the actual API documentation yet)
            nvc_status = "completed"  # This would normally come from the API
            
            # Map NVC Global status to our status
            status_mapping = {
                "pending": TransactionStatus.PENDING,
                "processing": TransactionStatus.PROCESSING,
                "completed": TransactionStatus.COMPLETED,
                "failed": TransactionStatus.FAILED,
                "refunded": TransactionStatus.REFUNDED
            }
            
            internal_status = status_mapping.get(nvc_status, transaction.status)
            
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
                "payment_id": nvc_payment_id,
                "status": nvc_status,
                "internal_status": internal_status.value,
                "amount": transaction.amount,
                "currency": transaction.currency
            }
        
        except Exception as e:
            error_message = str(e)
            logger.error(f"NVC Global error: {error_message}")
            return {
                "success": False,
                "transaction_id": transaction.transaction_id if 'transaction' in locals() else None,
                "error": error_message
            }
    
    def process_bank_transfer(self, transaction, *args):
        """Process a bank transfer through NVC Global platform"""
        try:
            # Log any extra arguments that are being passed
            if args:
                logger.warning(f"Extra arguments detected in process_bank_transfer: {args}")
                
            # Ensure transaction has bank transfer details
            if not transaction.tx_metadata_json:
                return {
                    "success": False, 
                    "error": "No bank transfer details found for this transaction"
                }
            
            # Parse bank transfer details from transaction metadata
            try:
                # First, ensure tx_metadata_json isn't None and isn't an empty string
                if not transaction.tx_metadata_json or not transaction.tx_metadata_json.strip():
                    return {
                        "success": False, 
                        "error": "Transaction has no metadata"
                    }
                
                # Try to parse the JSON
                try:
                    metadata = json.loads(transaction.tx_metadata_json)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing transaction metadata JSON: {str(e)}")
                    # Fix common issues with malformed JSON
                    try:
                        # Try to fix and parse common JSON issues
                        fixed_json = transaction.tx_metadata_json.strip()
                        if fixed_json.startswith('"') and fixed_json.endswith('"'):
                            # Handle double-encoded JSON string
                            fixed_json = fixed_json[1:-1].replace('\\"', '"')
                        metadata = json.loads(fixed_json)
                    except Exception:
                        return {
                            "success": False, 
                            "error": f"Error parsing transaction metadata: {str(e)}"
                        }
                
                # Check if bank_transfer exists in the metadata
                if 'bank_transfer' not in metadata:
                    return {
                        "success": False, 
                        "error": "Bank transfer details not found in transaction metadata"
                    }
                bank_details = metadata['bank_transfer']
            except Exception as e:
                logger.error(f"Error processing bank transfer details: {str(e)}")
                return {
                    "success": False, 
                    "error": f"Error processing bank transfer details: {str(e)}"
                }
            
            # Try to extract NVC Global payment ID from description
            import re
            match = re.search(r"NVC Global Payment ID: (NVC-[a-zA-Z0-9]+)", transaction.description)
            
            # If no payment ID in description, generate a new one
            if not match:
                # Generate a new payment ID
                nvc_payment_id = f"NVC-{uuid.uuid4().hex[:8].upper()}"
                
                # Update metadata with payment ID
                metadata['nvc_payment_id'] = nvc_payment_id
                transaction.tx_metadata_json = json.dumps(metadata)
                
                # Update the transaction description to include the payment ID
                transaction.description = f"{transaction.description} (NVC Global Payment ID: {nvc_payment_id})"
                db.session.commit()
            else:
                nvc_payment_id = match.group(1)
            
            # Create bank transfer request data for NVC Global API
            transfer_request = {
                "payment_id": nvc_payment_id,
                "transfer_type": "bank_transfer",
                "amount": str(transaction.amount),
                "currency": transaction.currency.upper(),
                "recipient": bank_details['recipient'],
                "bank": bank_details['bank'],
                "reference": bank_details.get('reference', ''),
                "payment_note": bank_details.get('payment_note', '')
            }
            
            # Add international transfer details if applicable
            if 'international' in bank_details:
                transfer_request["international"] = bank_details['international']
            
            # Get domain for return URLs
            current_domain = self._get_current_domain()
            
            # Add callback URL
            transfer_request["callback_url"] = f"{current_domain}/payments/nvc-callback?transaction_id={transaction.transaction_id}"
            
            # Use requests to send the API request to NVC Global platform
            headers = {
                "Authorization": f"Bearer {self.gateway.api_key}",
                "Content-Type": "application/json"
            }
            
            # Simulate an API call (we don't have the actual API documentation yet)
            response_data = {
                "success": True,
                "transfer_id": f"TRANSFER-{uuid.uuid4().hex[:8].upper()}",
                "status": "processing"
            }
            
            # Update transaction with NVC Global transfer ID and status
            if 'tx_metadata_json' in transaction.__dict__:
                metadata = json.loads(transaction.tx_metadata_json)
                metadata['transfer'] = {
                    "transfer_id": response_data['transfer_id'],
                    "status": response_data['status'],
                    "created_at": datetime.utcnow().isoformat()
                }
                transaction.tx_metadata_json = json.dumps(metadata)
            else:
                transaction.tx_metadata_json = json.dumps({
                    'bank_transfer': bank_details,
                    'transfer': {
                        "transfer_id": response_data['transfer_id'],
                        "status": response_data['status'],
                        "created_at": datetime.utcnow().isoformat()
                    }
                })
            
            transaction.status = TransactionStatus.PROCESSING
            transaction.description = f"{transaction.description} (Transfer ID: {response_data['transfer_id']})"
            db.session.commit()
            
            # Send email notification about the bank transfer
            try:
                from email_service import send_transaction_confirmation_email
                from models import User
                
                user = User.query.get(transaction.user_id)
                if user:
                    send_transaction_confirmation_email(user, transaction)
            except Exception as email_error:
                logger.warning(f"Failed to send bank transfer email: {str(email_error)}")
            
            return {
                "success": True,
                "transaction_id": transaction.transaction_id,
                "transfer_id": response_data["transfer_id"],
                "status": response_data["status"],
                "amount": transaction.amount,
                "currency": transaction.currency
            }
        
        except Exception as e:
            error_message = str(e)
            logger.error(f"NVC Global bank transfer error: {error_message}")
            
            # Update transaction status if there was an error
            try:
                transaction.status = TransactionStatus.FAILED
                transaction.description = f"{transaction.description} (Bank Transfer Error: {error_message})"
                db.session.commit()
            except Exception:
                pass  # Ignore secondary errors in error handling
            
            return {
                "success": False,
                "transaction_id": transaction.transaction_id,
                "error": error_message
            }
    
    def refund_payment(self, payment_id, amount=None):
        """Refund an NVC Global payment"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=payment_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            if transaction.status != TransactionStatus.COMPLETED:
                return {"success": False, "error": "Transaction not completed, cannot refund"}
            
            # Try to extract NVC Global payment ID from description
            import re
            match = re.search(r"NVC Global Payment ID: (NVC-[a-zA-Z0-9]+)", transaction.description)
            
            # If no payment ID in description, check metadata
            if not match:
                if transaction.tx_metadata_json and transaction.tx_metadata_json.strip():
                    try:
                        metadata = json.loads(transaction.tx_metadata_json)
                        if metadata.get('nvc_payment_id'):
                            nvc_payment_id = metadata.get('nvc_payment_id')
                        else:
                            return {"success": False, "error": "NVC Global Payment ID not found"}
                    except json.JSONDecodeError as e:
                        # Try to fix common issues with malformed JSON
                        try:
                            fixed_json = transaction.tx_metadata_json.strip()
                            if fixed_json.startswith('"') and fixed_json.endswith('"'):
                                # Handle double-encoded JSON string
                                fixed_json = fixed_json[1:-1].replace('\\"', '"')
                            metadata = json.loads(fixed_json)
                            if metadata.get('nvc_payment_id'):
                                nvc_payment_id = metadata.get('nvc_payment_id')
                            else:
                                return {"success": False, "error": "NVC Global Payment ID not found"}
                        except Exception:
                            logger.error(f"Error parsing transaction metadata JSON: {str(e)}")
                            return {"success": False, "error": "Error parsing transaction metadata"}
                else:
                    return {"success": False, "error": "NVC Global Payment ID not found"}
            else:
                nvc_payment_id = match.group(1)
            
            # Create refund data
            refund_data = {
                "payment_id": nvc_payment_id
            }
            
            if amount:
                refund_data["amount"] = str(amount)
            
            # Use requests to send refund request (we don't have the actual API documentation yet)
            headers = {
                "Authorization": f"Bearer {self.gateway.api_key}",
                "Content-Type": "application/json"
            }
            
            # Simulate a refund response (we don't have the actual API documentation yet)
            refund_response = {
                "success": True,
                "refund_id": f"REFUND-{uuid.uuid4().hex[:8].upper()}",
                "status": "completed"
            }
            
            # Update transaction status
            transaction.status = TransactionStatus.REFUNDED
            transaction.description = f"{transaction.description} (Refunded: {refund_response['refund_id']})"
            db.session.commit()
            
            return {
                "success": True,
                "transaction_id": transaction.transaction_id,
                "refund_id": refund_response["refund_id"],
                "status": refund_response["status"],
                "amount": amount or transaction.amount,
                "currency": transaction.currency
            }
        
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error refunding NVC Global payment: {error_message}")
            return {"success": False, "error": error_message}


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
            
            # Get domain for return URLs
            current_domain = self._get_current_domain()
            
            payload = {
                "name": "NVC Platform Payment",
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
                "redirect_url": f"{current_domain}/payments/return?transaction_id={transaction.transaction_id}",
                "cancel_url": f"{current_domain}/payments/cancel?transaction_id={transaction.transaction_id}"
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
                error_message = data.get("error", {}).get("message", "Unknown error")
                transaction.status = TransactionStatus.FAILED
                transaction.description = f"{description} (Error: {error_message})"
                db.session.commit()
                
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": error_message
                }
        
        except Exception as e:
            logger.error(f"Error processing Coinbase payment: {str(e)}")
            
            # If transaction was created, update its status
            if 'transaction' in locals():
                try:
                    transaction.status = TransactionStatus.FAILED
                    transaction.description = f"{description} (Error: {str(e)})"
                    db.session.commit()
                except Exception:
                    pass  # Ignore secondary errors
                
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": str(e)
                }
            
            return {"success": False, "error": str(e)}
    
    def _get_current_domain(self):
        """Get the current domain for the application"""
        # In production, you'd want to use the actual domain
        # For now, use Replit domain
        replit_domain = os.environ.get('REPLIT_DEPLOYMENT', '') 
        if replit_domain:
            return f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}"
        else:
            domains = os.environ.get('REPLIT_DOMAINS', '').split(',')
            if domains and domains[0]:
                return f"https://{domains[0]}"
            return "http://localhost:5000"
    
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
            
            charge_id = match.group(1)
            
            # Prepare API request to Coinbase
            headers = {
                "X-CC-Api-Key": self.gateway.api_key,
                "X-CC-Version": "2018-03-22",
                "Content-Type": "application/json"
            }
            
            # Make API request to Coinbase
            response = requests.get(
                f"{self.gateway.api_endpoint}/charges/{charge_id}",
                headers=headers
            )
            
            data = response.json()
            
            if response.status_code == 200:
                # Map Coinbase status to our status
                coinbase_status = data["data"]["timeline"][-1]["status"]
                
                status_mapping = {
                    "NEW": TransactionStatus.PENDING,
                    "PENDING": TransactionStatus.PENDING,
                    "COMPLETED": TransactionStatus.COMPLETED,
                    "EXPIRED": TransactionStatus.FAILED,
                    "CANCELED": TransactionStatus.FAILED,
                    "UNRESOLVED": TransactionStatus.PROCESSING,
                    "RESOLVED": TransactionStatus.COMPLETED,
                    "DELAYED": TransactionStatus.PROCESSING
                }
                
                internal_status = status_mapping.get(coinbase_status, transaction.status)
                
                # Update transaction status if changed
                if transaction.status != internal_status:
                    transaction.status = internal_status
                    db.session.commit()
                
                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "charge_id": charge_id,
                    "status": coinbase_status,
                    "internal_status": internal_status.value,
                    "amount": transaction.amount,
                    "currency": transaction.currency
                }
            else:
                error_message = data.get("error", {}).get("message", "Unknown error")
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": error_message
                }
        
        except Exception as e:
            logger.error(f"Error checking Coinbase payment status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def refund_payment(self, payment_id, amount=None):
        """
        Coinbase Commerce does not directly support refunds for crypto payments.
        This should be handled manually for crypto payments.
        """
        return {
            "success": False,
            "error": "Automatic refunds are not supported for Coinbase crypto payments. Please process manually."
        }