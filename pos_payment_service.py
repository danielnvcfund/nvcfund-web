"""
POS Payment Service Module
This module provides services for POS payment processing using Stripe.
"""

import os
import uuid
import json
import logging
from datetime import datetime
from decimal import Decimal

import stripe
from flask import url_for

from models import Transaction, TransactionType, TransactionStatus, db

# Configure logging
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')


class POSPaymentService:
    """Service for POS payment processing using Stripe"""
    
    @classmethod
    def create_checkout_session(cls, transaction, domain_url):
        """
        Create a Stripe checkout session for a given transaction
        
        Args:
            transaction: The Transaction model instance
            domain_url: The base domain URL for redirects
            
        Returns:
            Stripe checkout session object
        """
        try:
            # Calculate amount in cents (Stripe requires integer amounts)
            amount_in_cents = int(float(transaction.amount) * 100)
            
            # Create line item
            line_items = [{
                'price_data': {
                    'currency': transaction.currency.lower(),
                    'product_data': {
                        'name': f"Payment to NVC Banking Platform",
                        'description': transaction.description or "Transaction payment",
                    },
                    'unit_amount': amount_in_cents,
                },
                'quantity': 1,
            }]
            
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=f"{domain_url}{url_for('pos.payment_success', transaction_id=transaction.transaction_id)}",
                cancel_url=f"{domain_url}{url_for('pos.payment_cancel', transaction_id=transaction.transaction_id)}",
                client_reference_id=transaction.transaction_id,
                customer_email=transaction.metadata.get('customer_email', None),
                metadata={
                    'transaction_id': transaction.transaction_id,
                    'customer_name': transaction.metadata.get('customer_name', ''),
                    'description': transaction.description or '',
                }
            )
            
            # Update transaction with session ID
            transaction.metadata['stripe_session_id'] = checkout_session.id
            db.session.commit()
            
            return checkout_session
            
        except stripe.error.StripeError as e:
            # Log and re-raise Stripe-specific errors
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            raise
            
        except Exception as e:
            # Log and re-raise other errors
            logger.error(f"Unexpected error creating checkout session: {str(e)}")
            raise
    
    @classmethod
    def create_payout(cls, transaction):
        """
        Create a payout to a recipient's card (simulated)
        In a real implementation, this would use Stripe Connect or a similar service
        
        Args:
            transaction: The Transaction model instance
            
        Returns:
            Dictionary with payout results
        """
        try:
            # In a real implementation, this would make a Stripe Transfer or Payout API call
            # For now, we're just simulating a successful payout
            
            # Update transaction status
            transaction.status = TransactionStatus.COMPLETED
            transaction.completed_at = datetime.utcnow()
            transaction.metadata['payout_id'] = f"po_{uuid.uuid4().hex[:16]}"
            transaction.metadata['payout_status'] = 'paid'
            db.session.commit()
            
            return {
                'status': 'success',
                'payout_id': transaction.metadata['payout_id'],
                'transaction_id': transaction.transaction_id
            }
            
        except Exception as e:
            # Log and re-raise errors
            logger.error(f"Error creating payout: {str(e)}")
            raise
    
    @classmethod
    def process_webhook_event(cls, event):
        """
        Process Stripe webhook events
        
        Args:
            event: The Stripe event object
            
        Returns:
            Boolean indicating success/failure
        """
        try:
            # Get event type
            event_type = event['type']
            
            # Handle checkout.session.completed event
            if event_type == 'checkout.session.completed':
                # Get the session object
                session = event['data']['object']
                
                # Get the transaction ID from the client reference ID
                transaction_id = session.get('client_reference_id')
                
                if not transaction_id:
                    logger.warning(f"No transaction ID found in checkout session: {session.id}")
                    return False
                
                # Find the transaction
                transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
                
                if not transaction:
                    logger.warning(f"Transaction not found for checkout session: {session.id}")
                    return False
                
                # Update transaction status
                transaction.status = TransactionStatus.COMPLETED
                transaction.completed_at = datetime.utcnow()
                transaction.metadata['payment_status'] = session.get('payment_status', 'paid')
                transaction.metadata['payment_intent'] = session.get('payment_intent', '')
                db.session.commit()
                
                logger.info(f"Transaction {transaction_id} marked as completed via webhook")
                return True
                
            # Handle payment_intent.succeeded event
            elif event_type == 'payment_intent.succeeded':
                # Get the payment intent object
                payment_intent = event['data']['object']
                
                # Find the transaction by payment intent ID
                transaction = Transaction.query.filter(
                    Transaction.metadata.contains({'payment_intent': payment_intent.id})
                ).first()
                
                if not transaction:
                    logger.warning(f"Transaction not found for payment intent: {payment_intent.id}")
                    return False
                
                # Update transaction status if not already completed
                if transaction.status != TransactionStatus.COMPLETED:
                    transaction.status = TransactionStatus.COMPLETED
                    transaction.completed_at = datetime.utcnow()
                    transaction.metadata['payment_status'] = 'paid'
                    db.session.commit()
                    
                    logger.info(f"Transaction {transaction.transaction_id} marked as completed via payment intent webhook")
                
                return True
                
            # Handle other events as needed
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing webhook event: {str(e)}")
            return False