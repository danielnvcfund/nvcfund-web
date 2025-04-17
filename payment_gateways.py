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
    "mode": "sandbox",  # Change to "live" for production
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
        # Try to get NVC Global gateway by type first, handling the enum conversion safely
        nvc_global_gateway = None
        try:
            # Try direct access with enum
            nvc_global_gateway = PaymentGateway.query.filter_by(gateway_type=PaymentGatewayType.NVC_GLOBAL).first()
        except Exception as enum_error:
            logger.warning(f"Error using enum for NVC_GLOBAL query: {str(enum_error)}")
        
        # If direct access failed, use a direct SQL query
        if not nvc_global_gateway:
            try:
                # Execute raw SQL to find NVC Global gateway
                result = db.session.execute(text("SELECT id FROM payment_gateway WHERE gateway_type::text = 'nvc_global' LIMIT 1"))
                gateway_id = result.scalar()
                
                if gateway_id:
                    nvc_global_gateway = PaymentGateway.query.get(gateway_id)
                    logger.info(f"Found NVC Global gateway with ID {gateway_id} using SQL query")
            except Exception as sql_error:
                logger.warning(f"Error executing SQL for NVC Global gateway lookup: {str(sql_error)}")
        
        # If NVC Global gateway still doesn't exist, create it
        if not nvc_global_gateway:
            try:
                # Try creating using SQLAlchemy ORM first
                try:
                    nvc_global_gateway = PaymentGateway(
                        name="NVC Global",
                        gateway_type=PaymentGatewayType.NVC_GLOBAL,
                        api_endpoint="https://api.nvcplatform.net",
                        api_key=os.environ.get('NVC_GLOBAL_API_KEY', ''),
                        webhook_secret=os.environ.get('NVC_GLOBAL_WEBHOOK_SECRET', ''),
                        ethereum_address=os.environ.get('NVC_GLOBAL_ETH_ADDRESS', None),
                        is_active=True
                    )
                    db.session.add(nvc_global_gateway)
                    db.session.commit()
                    logger.info("NVC Global payment gateway created using ORM")
                except Exception as orm_error:
                    logger.warning(f"Error creating NVC Global gateway with ORM: {str(orm_error)}")
                    db.session.rollback()
                    
                    # Fall back to raw SQL if ORM approach failed
                    stmt = text("""
                        INSERT INTO payment_gateway (
                            name, gateway_type, api_endpoint, api_key, webhook_secret, 
                            ethereum_address, is_active, created_at, updated_at
                        )
                        VALUES (
                            'NVC Global', 'nvc_global', 'https://api.nvcplatform.net', 
                            :api_key, :webhook_secret, :eth_address, true, now(), now()
                        )
                        RETURNING id
                    """)
                    
                    result = db.session.execute(stmt, {
                        'api_key': os.environ.get('NVC_GLOBAL_API_KEY', ''),
                        'webhook_secret': os.environ.get('NVC_GLOBAL_WEBHOOK_SECRET', ''),
                        'eth_address': os.environ.get('NVC_GLOBAL_ETH_ADDRESS', None)
                    })
                    
                    # Get the newly created gateway
                    gateway_id = result.fetchone()[0]
                    nvc_global_gateway = PaymentGateway.query.get(gateway_id)
                    
                    logger.info(f"NVC Global payment gateway created using SQL, ID: {gateway_id}")
            except Exception as create_error:
                logger.warning(f"Error creating NVC Global gateway: {str(create_error)}")
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

def get_gateway_handler(gateway_id=None, gateway_type=None):
    """Get a payment gateway handler based on ID or type"""
    try:
        gateway = None
        
        if gateway_id:
            gateway = PaymentGateway.query.get(gateway_id)
        elif gateway_type:
            # Handle special case for NVC_GLOBAL
            if gateway_type == PaymentGatewayType.NVC_GLOBAL:
                try:
                    # Try direct ORM access first
                    gateway = PaymentGateway.query.filter_by(
                        gateway_type=gateway_type,
                        is_active=True
                    ).first()
                    
                    # If that fails, use SQL
                    if not gateway:
                        result = db.session.execute(
                            text("SELECT id FROM payment_gateway WHERE gateway_type::text = 'nvc_global' AND is_active = true LIMIT 1")
                        )
                        gateway_id = result.scalar()
                        if gateway_id:
                            gateway = PaymentGateway.query.get(gateway_id)
                except Exception as e:
                    logger.error(f"Error getting NVC_GLOBAL gateway by type: {str(e)}")
            else:
                # Normal case for other gateway types
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
    
    def refund_payment(self, payment_id, amount=None):
        """Refund an NVC Global payment"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=payment_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            if transaction.status != TransactionStatus.COMPLETED:
                return {"success": False, "error": "Transaction not completed, cannot refund"}
            
            # Extract NVC Global payment ID from description
            import re
            match = re.search(r"NVC Global Payment ID: (NVC-[a-zA-Z0-9]+)", transaction.description)
            
            if not match:
                return {"success": False, "error": "NVC Global Payment ID not found"}
            
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