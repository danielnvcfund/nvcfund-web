"""
POS Payment Service for NVC Banking Platform
This module provides functionality for processing Point of Sale (POS) credit card payments
using Stripe as the payment processor.
"""
import os
import logging
import stripe
import json
import uuid
from datetime import datetime
from app import db
from models import Transaction, TransactionStatus, TransactionType, PaymentGateway, PaymentGatewayType
from account_holder_models import AccountHolder, BankAccount, CurrencyType

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

class POSPaymentService:
    """Service for handling POS payments via Stripe"""
    
    @staticmethod
    def create_payment_intent(amount, currency="usd", customer_email=None, description=None, metadata=None):
        """
        Create a payment intent for a credit card transaction
        
        Args:
            amount: Amount in dollars (will be converted to cents for Stripe)
            currency: Currency code (default: usd)
            customer_email: Customer email for receipt
            description: Description of the transaction
            metadata: Additional metadata for the transaction
            
        Returns:
            dict: Payment intent details including client_secret
        """
        try:
            # Convert dollar amount to cents for Stripe
            amount_cents = int(float(amount) * 100)
            
            # Set up the payment intent parameters
            payment_intent_params = {
                'amount': amount_cents,
                'currency': currency.lower(),
                'payment_method_types': ['card'],
                'description': description or 'NVC Fund Bank payment',
                'metadata': metadata or {},
            }
            
            # Add customer if email provided
            if customer_email:
                payment_intent_params['receipt_email'] = customer_email
                
            # Create the payment intent
            intent = stripe.PaymentIntent.create(**payment_intent_params)
            
            return {
                'id': intent.id,
                'client_secret': intent.client_secret,
                'amount': amount,
                'currency': currency.upper(),
                'status': intent.status
            }
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            raise
    
    @staticmethod
    def process_payment_webhook(event_data):
        """
        Process a Stripe webhook event for payment updates
        
        Args:
            event_data: The Stripe event data from webhook
            
        Returns:
            dict: Status of the processed webhook
        """
        try:
            event_type = event_data.get('type')
            
            # Handle payment_intent.succeeded event
            if event_type == 'payment_intent.succeeded':
                payment_intent = event_data.get('data', {}).get('object', {})
                
                # Find transaction by Stripe payment intent ID
                transaction = Transaction.query.filter_by(
                    external_id=payment_intent.get('id')
                ).first()
                
                if transaction:
                    # Update transaction status
                    transaction.status = TransactionStatus.COMPLETED
                    transaction.updated_at = datetime.utcnow()
                    db.session.commit()
                    logger.info(f"Transaction {transaction.transaction_id} marked as completed")
                
                return {'status': 'success', 'message': 'Payment processed successfully'}
            
            # Handle payment_intent.payment_failed event
            elif event_type == 'payment_intent.payment_failed':
                payment_intent = event_data.get('data', {}).get('object', {})
                
                # Find transaction by Stripe payment intent ID
                transaction = Transaction.query.filter_by(
                    external_id=payment_intent.get('id')
                ).first()
                
                if transaction:
                    # Update transaction status
                    transaction.status = TransactionStatus.FAILED
                    transaction.updated_at = datetime.utcnow()
                    
                    # Add error message to transaction description
                    error_message = payment_intent.get('last_payment_error', {}).get('message', 'Payment failed')
                    if transaction.description:
                        transaction.description += f" | Error: {error_message}"
                    else:
                        transaction.description = f"Error: {error_message}"
                    
                    db.session.commit()
                    logger.info(f"Transaction {transaction.transaction_id} marked as failed")
                
                return {'status': 'success', 'message': 'Payment failure recorded'}
                
            # Other events can be handled as needed
            return {'status': 'success', 'message': f'Event {event_type} received'}
            
        except Exception as e:
            logger.error(f"Error processing payment webhook: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    @staticmethod
    def create_transaction_from_payment_intent(payment_intent_id, user_id, gateway_id, description=None):
        """
        Create a transaction record from a Stripe payment intent
        
        Args:
            payment_intent_id: Stripe payment intent ID
            user_id: User ID making the payment
            gateway_id: Payment gateway ID
            description: Transaction description
            
        Returns:
            Transaction: Created transaction object
        """
        try:
            # Retrieve the payment intent from Stripe
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Create a unique transaction ID
            transaction_id = f"POS-{uuid.uuid4().hex[:12]}"
            
            # Create the transaction record
            transaction = Transaction(
                transaction_id=transaction_id,
                user_id=user_id,
                amount=float(intent.amount) / 100,  # Convert cents to dollars
                currency=intent.currency.upper(),
                transaction_type=TransactionType.PAYMENT,
                status=TransactionStatus.PENDING if intent.status != 'succeeded' else TransactionStatus.COMPLETED,
                description=description or f"Credit card payment - {intent.description}",
                gateway_id=gateway_id,
                external_id=payment_intent_id,  # Store Stripe payment intent ID
                tx_metadata_json=json.dumps(intent.metadata.to_dict()) if intent.metadata else None
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            logger.info(f"Created transaction {transaction_id} from payment intent {payment_intent_id}")
            
            return transaction
            
        except Exception as e:
            logger.error(f"Error creating transaction from payment intent: {str(e)}")
            raise
    
    @staticmethod
    def create_payout(destination_card, amount, currency="usd", description=None, metadata=None):
        """
        Create a payout to a credit card via Stripe
        
        Args:
            destination_card: Tokenized card or card ID to send money to
            amount: Amount in dollars (will be converted to cents for Stripe)
            currency: Currency code (default: usd)
            description: Description of the payout
            metadata: Additional metadata for the payout
            
        Returns:
            dict: Payout details
        """
        try:
            # Convert dollar amount to cents for Stripe
            amount_cents = int(float(amount) * 100)
            
            # Create a transfer to the destination card
            transfer = stripe.Transfer.create(
                amount=amount_cents,
                currency=currency.lower(),
                destination=destination_card,
                description=description or 'NVC Fund Bank payout',
                metadata=metadata or {}
            )
            
            return {
                'id': transfer.id,
                'amount': float(transfer.amount) / 100,  # Convert back to dollars
                'currency': transfer.currency.upper(),
                'status': transfer.status
            }
            
        except Exception as e:
            logger.error(f"Error creating payout: {str(e)}")
            raise
    
    @staticmethod
    def create_transaction_from_account(
        account_holder_id, 
        account_id, 
        amount, 
        currency,
        recipient_name=None,
        recipient_card_token=None,
        transaction_type=TransactionType.PAYMENT,
        description=None
    ):
        """
        Create a transaction from a bank account for POS payment
        
        Args:
            account_holder_id: Account holder ID
            account_id: Bank account ID
            amount: Amount to transfer
            currency: Currency code
            recipient_name: Name of the recipient
            recipient_card_token: Card token for the recipient
            transaction_type: Type of transaction
            description: Transaction description
            
        Returns:
            Transaction: Created transaction object
        """
        try:
            # Verify the account holder and account exist
            account_holder = AccountHolder.query.get(account_holder_id)
            if not account_holder:
                raise ValueError(f"Account holder {account_holder_id} not found")
                
            account = BankAccount.query.get(account_id)
            if not account:
                raise ValueError(f"Account {account_id} not found")
                
            # Verify the account belongs to the account holder
            if account.account_holder_id != account_holder_id:
                raise ValueError(f"Account {account_id} does not belong to account holder {account_holder_id}")
                
            # Verify sufficient funds
            if account.balance < float(amount):
                raise ValueError(f"Insufficient funds in account {account.account_number}")
                
            # Create a unique transaction ID
            transaction_id = f"POS-{uuid.uuid4().hex[:12]}"
            
            # Find the Stripe gateway
            gateway = PaymentGateway.query.filter_by(gateway_type=PaymentGatewayType.STRIPE).first()
            if not gateway:
                raise ValueError("Stripe payment gateway not configured")
                
            # Create the transaction record
            transaction = Transaction(
                transaction_id=transaction_id,
                user_id=account_holder.user_id,
                amount=float(amount),
                currency=currency,
                transaction_type=transaction_type,
                status=TransactionStatus.PENDING,
                description=description or f"Credit card payment from account {account.account_number}",
                gateway_id=gateway.id,
                recipient_name=recipient_name,
                recipient_account=recipient_card_token  # Store the card token
            )
            
            db.session.add(transaction)
            
            # Update account balance
            account.balance -= float(amount)
            account.available_balance -= float(amount)
            
            db.session.commit()
            
            logger.info(f"Created transaction {transaction_id} from account {account.account_number}")
            
            return transaction
            
        except Exception as e:
            logger.error(f"Error creating transaction from account: {str(e)}")
            raise