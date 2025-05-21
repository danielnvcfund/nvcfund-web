"""
Stripe Payment Routes for NVCT
This module handles credit card payments for NVCT accounts through Stripe
"""
import os
import json
import secrets
import logging
from datetime import datetime

import stripe
from flask import Blueprint, redirect, url_for, request, current_app, render_template, flash, session
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from models import db, Transaction, TransactionStatus, TransactionType
from account_holder_models import BankAccount, CurrencyType
from utils import generate_transaction_id

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
stripe_bp = Blueprint('stripe_nvct', __name__, url_prefix='/stripe-nvct')

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

@stripe_bp.route('/checkout', methods=['GET'])
@login_required
def checkout_for_nvct():
    """Create a Stripe checkout session for NVCT funding"""
    try:
        # Check if user has an NVCT account
        if not hasattr(current_user, 'account_holder') or not current_user.account_holder:
            flash("You need to create an account before making a payment", "warning")
            return redirect(url_for('stablecoin.create_account'))
            
        # Get user's NVCT accounts
        nvct_accounts = BankAccount.query.filter_by(
            account_holder_id=current_user.account_holder.id,
            currency=CurrencyType.NVCT
        ).all()
        
        if not nvct_accounts:
            flash("You don't have an NVCT account to fund. Please create one first.", "warning")
            return redirect(url_for('stablecoin.create_account'))
        
        # Use the first NVCT account if there are multiple
        nvct_account = nvct_accounts[0]
        
        # If there are multiple NVCT accounts, show a selection page first
        if len(nvct_accounts) > 1:
            return render_template(
                'payments/select_nvct_account.html',
                nvct_accounts=nvct_accounts,
                payment_method="credit_card",
                title="Select NVCT Account for Credit Card Payment"
            )
        
        # Create a payment reference
        payment_reference = f"NVCT-{generate_transaction_id()[:8]}"
        
        # Store the nvct_account_id in session for the webhook
        session['nvct_payment_account_id'] = nvct_account.id
        session['nvct_payment_reference'] = payment_reference
        
        # Determine URLs
        base_url = request.host_url.rstrip('/')
        if os.environ.get('REPLIT_DEPLOYMENT'):
            base_url = f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}"
        
        success_url = f"{base_url}/stripe-nvct/success"
        cancel_url = f"{base_url}/stripe-nvct/cancel"
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'NVCT Token Purchase',
                            'description': 'Purchase NVCT tokens for your stablecoin account',
                        },
                        'unit_amount_decimal': 1000,  # $10.00 default amount
                    },
                    'quantity': 1,
                    'adjustable_quantity': {
                        'enabled': True,
                        'minimum': 1,
                        'maximum': 100,
                    },
                },
            ],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=payment_reference,
            metadata={
                'payment_reference': payment_reference,
                'user_id': str(current_user.id),
                'account_id': str(nvct_account.id),
                'account_number': nvct_account.account_number,
                'payment_type': 'nvct_funding'
            }
        )
        
        # Redirect to Stripe checkout
        return redirect(checkout_session.url)
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        flash(f"Payment processor error: {str(e)}", "danger")
        return redirect(url_for('payment_options_bp.options'))
        
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {str(e)}")
        flash("There was an error processing your payment request", "danger")
        return redirect(url_for('payment_options_bp.options'))

@stripe_bp.route('/success', methods=['GET'])
@login_required
def payment_success():
    """Handle successful Stripe payment"""
    # Clear the session variables
    payment_reference = session.pop('nvct_payment_reference', None)
    nvct_account_id = session.pop('nvct_payment_account_id', None)
    
    # Display success message
    flash("Payment successful! Your NVCT account will be funded shortly.", "success")
    
    # Redirect to account details
    if nvct_account_id:
        return redirect(url_for('stablecoin.account_details', account_id=nvct_account_id))
    else:
        return redirect(url_for('stablecoin.accounts'))

@stripe_bp.route('/cancel', methods=['GET'])
@login_required
def payment_cancel():
    """Handle cancelled Stripe payment"""
    # Clear the session variables
    session.pop('nvct_payment_reference', None)
    session.pop('nvct_payment_account_id', None)
    
    # Display cancelled message
    flash("Payment was cancelled. Your NVCT account has not been charged.", "warning")
    
    # Redirect to payment options
    return redirect(url_for('payment_options_bp.options'))

@stripe_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        if endpoint_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        else:
            # Fallback if no endpoint secret is configured
            data = json.loads(payload)
            event = stripe.Event.construct_from(
                data, stripe.api_key
            )
            
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Check if this is an NVCT funding payment
            if session.get('metadata', {}).get('payment_type') == 'nvct_funding':
                handle_nvct_payment_success(session)
                
        return {'success': True}, 200
        
    except Exception as e:
        logger.error(f"Error handling Stripe webhook: {str(e)}")
        return {'error': str(e)}, 400

def handle_nvct_payment_success(session):
    """Process a successful NVCT funding payment"""
    try:
        # Extract metadata
        metadata = session.get('metadata', {})
        payment_reference = metadata.get('payment_reference')
        user_id = int(metadata.get('user_id'))
        account_id = int(metadata.get('account_id'))
        
        # Get payment details
        amount_total = session.get('amount_total', 0) / 100  # Convert from cents to dollars
        
        # Get the NVCT account
        nvct_account = BankAccount.query.get(account_id)
        if not nvct_account:
            logger.error(f"NVCT account {account_id} not found for payment {payment_reference}")
            return
            
        # Create transaction record
        transaction = Transaction()
        transaction.transaction_id = payment_reference
        transaction.user_id = user_id
        transaction.amount = amount_total
        transaction.currency = "USD"
        transaction.transaction_type = TransactionType.DEPOSIT
        transaction.status = TransactionStatus.COMPLETED
        transaction.description = f"Stripe payment for NVCT account {nvct_account.account_number}"
        transaction.recipient_account = nvct_account.account_number
        
        # Add Stripe-specific details as metadata
        metadata = {
            'stripe_session_id': session.get('id'),
            'payment_intent_id': session.get('payment_intent'),
            'payment_status': session.get('payment_status'),
            'customer_email': session.get('customer_details', {}).get('email')
        }
        transaction.tx_metadata_json = json.dumps(metadata)
        
        # Update NVCT account balance
        nvct_account.balance += amount_total
        nvct_account.available_balance += amount_total
        
        # Save everything
        db.session.add(transaction)
        db.session.commit()
        
        logger.info(f"Successfully processed NVCT payment: {payment_reference} for {amount_total} USD")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing NVCT payment: {str(e)}")