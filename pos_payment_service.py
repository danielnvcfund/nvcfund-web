"""
POS Payment Service

This module provides functionality for processing credit card payments 
through the Stripe payment gateway. It supports both accepting payments
via credit card and sending money to credit cards.
"""

import os
import uuid
import logging
from datetime import datetime

import stripe
from flask import current_app

from models import Transaction, TransactionStatus, TransactionType
from app import db

# Configure logging
logger = logging.getLogger(__name__)

# Set Stripe API key
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')


class POSPaymentService:
    """Service for handling POS (Point of Sale) credit card payments"""
    
    @staticmethod
    def create_checkout_session(transaction, domain_url):
        """
        Create a Stripe checkout session for a transaction
        
        Args:
            transaction (Transaction): The transaction object
            domain_url (str): The domain URL for success and cancel redirects
            
        Returns:
            stripe.checkout.Session: The Stripe checkout session
        """
        # Handle currency conversion (Stripe doesn't support NVCT)
        display_currency = transaction.currency
        stripe_currency = transaction.currency
        
        # If currency is NVCT, use USD for Stripe but show NVCT on the interface
        if stripe_currency == 'NVCT':
            stripe_currency = 'USD'
        
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': stripe_currency.lower(),
                        'product_data': {
                            'name': transaction.description or 'Payment to NVC Banking Platform',
                        },
                        'unit_amount': int(transaction.amount * 100),  # Amount in cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{domain_url}/pos/payment-success/{transaction.transaction_id}",
                cancel_url=f"{domain_url}/pos/payment-cancel/{transaction.transaction_id}",
                client_reference_id=transaction.transaction_id,
                customer_email=transaction.metadata.get('customer_email'),
                payment_intent_data={
                    'description': transaction.description or f"Payment to {transaction.recipient_name or 'NVC Banking Platform'}",
                    'metadata': {
                        'transaction_id': transaction.transaction_id,
                        'display_currency': display_currency
                    }
                }
            )
            
            # Update transaction with Stripe session ID
            transaction.metadata['stripe_session_id'] = checkout_session.id
            db.session.commit()
            
            return checkout_session
            
        except stripe.error.StripeError as e:
            # Handle Stripe errors
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            transaction.status = TransactionStatus.FAILED
            transaction.metadata['error'] = str(e)
            db.session.commit()
            raise
            
        except Exception as e:
            # Handle other errors
            logger.error(f"Unexpected error creating checkout session: {str(e)}")
            raise
    
    @staticmethod
    def process_webhook_event(event):
        """
        Process a Stripe webhook event
        
        Args:
            event (dict): The Stripe event object
            
        Returns:
            bool: True if the event was processed successfully, False otherwise
        """
        try:
            # Handle the event type
            if event['type'] == 'checkout.session.completed':
                return POSPaymentService._handle_checkout_completed(event['data']['object'])
            elif event['type'] == 'payment_intent.succeeded':
                return POSPaymentService._handle_payment_succeeded(event['data']['object'])
            elif event['type'] == 'payment_intent.payment_failed':
                return POSPaymentService._handle_payment_failed(event['data']['object'])
            else:
                # Unhandled event type
                logger.info(f"Unhandled event type: {event['type']}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing webhook event: {str(e)}")
            return False
    
    @staticmethod
    def _handle_checkout_completed(session):
        """
        Handle a checkout.session.completed event
        
        Args:
            session (dict): The Stripe session object
            
        Returns:
            bool: True if the event was handled successfully, False otherwise
        """
        try:
            # Get the transaction ID from the client reference ID
            transaction_id = session.get('client_reference_id')
            if not transaction_id:
                logger.warning("No client_reference_id found in checkout session")
                return False
            
            # Find the transaction
            transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
            if not transaction:
                logger.warning(f"Transaction not found for ID: {transaction_id}")
                return False
            
            # Update the transaction status
            if transaction.status != TransactionStatus.COMPLETED:
                transaction.status = TransactionStatus.COMPLETED
                transaction.completed_at = datetime.utcnow()
                transaction.metadata['payment_intent'] = session.get('payment_intent')
                transaction.metadata['stripe_customer'] = session.get('customer')
                transaction.metadata['payment_status'] = 'paid'
                db.session.commit()
                
                logger.info(f"Transaction {transaction_id} marked as completed")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling checkout.session.completed: {str(e)}")
            return False
    
    @staticmethod
    def _handle_payment_succeeded(payment_intent):
        """
        Handle a payment_intent.succeeded event
        
        Args:
            payment_intent (dict): The Stripe payment intent object
            
        Returns:
            bool: True if the event was handled successfully, False otherwise
        """
        try:
            # Get the transaction ID from metadata
            transaction_id = payment_intent.get('metadata', {}).get('transaction_id')
            if not transaction_id:
                logger.warning("No transaction_id found in payment intent metadata")
                return False
            
            # Find the transaction
            transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
            if not transaction:
                logger.warning(f"Transaction not found for ID: {transaction_id}")
                return False
            
            # Update the transaction
            transaction.metadata['stripe_payment_intent_id'] = payment_intent.get('id')
            transaction.metadata['payment_method'] = payment_intent.get('payment_method')
            transaction.metadata['payment_status'] = 'succeeded'
            
            if transaction.status != TransactionStatus.COMPLETED:
                transaction.status = TransactionStatus.COMPLETED
                transaction.completed_at = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Payment intent succeeded for transaction {transaction_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling payment_intent.succeeded: {str(e)}")
            return False
    
    @staticmethod
    def _handle_payment_failed(payment_intent):
        """
        Handle a payment_intent.payment_failed event
        
        Args:
            payment_intent (dict): The Stripe payment intent object
            
        Returns:
            bool: True if the event was handled successfully, False otherwise
        """
        try:
            # Get the transaction ID from metadata
            transaction_id = payment_intent.get('metadata', {}).get('transaction_id')
            if not transaction_id:
                logger.warning("No transaction_id found in payment intent metadata")
                return False
            
            # Find the transaction
            transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
            if not transaction:
                logger.warning(f"Transaction not found for ID: {transaction_id}")
                return False
            
            # Update the transaction
            transaction.status = TransactionStatus.FAILED
            transaction.metadata['stripe_payment_intent_id'] = payment_intent.get('id')
            transaction.metadata['payment_status'] = 'failed'
            transaction.metadata['last_payment_error'] = payment_intent.get('last_payment_error', {}).get('message')
            
            db.session.commit()
            logger.info(f"Payment intent failed for transaction {transaction_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling payment_intent.payment_failed: {str(e)}")
            return False
    
    @staticmethod
    def create_payout(transaction):
        """
        Create a payout to a bank account or debit card
        
        Note: In production, this would integrate with Stripe Connect 
        or a similar service to send money to recipients
        
        Args:
            transaction (Transaction): The transaction object
            
        Returns:
            dict: The payout result
        """
        try:
            # In a real implementation, you would use Stripe Connect or a similar service
            # to create a payout to the recipient's bank account or debit card
            
            # For demonstration purposes, we'll just simulate a successful payout
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            transaction.metadata['payout_status'] = 'completed'
            transaction.metadata['payout_id'] = f"payout_{uuid.uuid4().hex[:8]}"
            
            db.session.commit()
            
            return {
                'success': True,
                'payout_id': transaction.metadata['payout_id'],
                'status': 'completed'
            }
            
        except Exception as e:
            # Handle errors
            logger.error(f"Error creating payout: {str(e)}")
            
            transaction.status = TransactionStatus.FAILED
            transaction.metadata['payout_status'] = 'failed'
            transaction.metadata['error'] = str(e)
            
            db.session.commit()
            
            raise