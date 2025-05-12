"""
Stripe Payment Integration Routes
This module provides routes for Stripe payment processing
"""

import os
import logging
import stripe
import json
from flask import Blueprint, render_template, redirect, request, url_for, jsonify, flash
from flask_login import login_required, current_user
from datetime import datetime
import uuid
from app import db
# Try to import transaction models - if not available, log a warning
try:
    from models import Transaction, TransactionStatus, PaymentMethod
    TRANSACTION_MODELS_AVAILABLE = True
except ImportError:
    TRANSACTION_MODELS_AVAILABLE = False
    logging.warning("Transaction models not available - payment recording disabled")

# Set up logger first
logger = logging.getLogger(__name__)

# Create blueprint
stripe_bp = Blueprint('stripe', __name__, url_prefix='/stripe')

# Set up Stripe API key from environment - use live key if available, otherwise fall back to test key
stripe.api_key = os.environ.get('STRIPE_LIVE_SECRET_KEY') or os.environ.get('STRIPE_SECRET_KEY')

# Set to True for live mode, False for test mode
STRIPE_LIVE_MODE = bool(os.environ.get('STRIPE_LIVE_SECRET_KEY'))
if STRIPE_LIVE_MODE:
    logger.info("Stripe configured in LIVE MODE - real payments will be processed")
else:
    logger.warning("Stripe configured in TEST MODE - no real payments will be processed")

# Add custom template filter
@stripe_bp.app_template_filter('strftime')
def _jinja2_filter_datetime(date, fmt=None):
    """Format a date according to the given format"""
    if not date:
        return ''
    if fmt:
        return date.strftime(fmt)
    return date.strftime('%Y-%m-%d %H:%M:%S')

# Set up domain for success and cancel URLs
def get_domain():
    """Get the domain for the application"""
    if os.environ.get('REPLIT_DEPLOYMENT'):
        return os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')
    elif os.environ.get('REPLIT_DOMAINS'):
        domains = os.environ.get('REPLIT_DOMAINS', '')
        return domains.split(',')[0] if domains else 'localhost:5000'
    else:
        # Default to localhost for development
        return 'localhost:5000'

@stripe_bp.route('/')
def index():
    """Display Stripe payment options"""
    return render_template('stripe/index.html', stripe_live_mode=STRIPE_LIVE_MODE)

@stripe_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create a Stripe checkout session"""
    try:
        # Get amount and currency from form
        amount = float(request.form.get('amount', 100))
        currency = request.form.get('currency', 'usd')
        
        # Create a unique reference for this payment
        payment_reference = f"payment_{uuid.uuid4().hex[:8]}"
        
        # Generate success and cancel URLs
        domain = get_domain()
        success_url = f"https://{domain}{url_for('stripe.success')}?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"https://{domain}{url_for('stripe.cancel')}"
        
        # Log successful payment information creation
        logger.info(f"Creating Stripe checkout session for {amount} {currency}")
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': currency,
                        'product_data': {
                            'name': 'NVC Banking Services',
                            'description': 'Payment for NVC Banking Platform services',
                        },
                        'unit_amount': int(amount * 100),  # Convert to cents
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=payment_reference,
            metadata={
                'payment_reference': payment_reference,
                'user_id': str(current_user.id) if hasattr(current_user, 'id') else 'guest',
            }
        )
        
        # Redirect to Stripe hosted checkout page
        checkout_url = checkout_session.url
        if checkout_url:
            return redirect(checkout_url, code=303)
        else:
            logger.error("Stripe checkout URL is None")
            flash("Error creating checkout session. Please try again.", "error")
            return redirect(url_for('stripe.index'))
    
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {str(e)}")
        flash(f"Error creating checkout session: {str(e)}", "error")
        return redirect(url_for('stripe.index'))

@stripe_bp.route('/success')
def success():
    """Handle successful payment"""
    session_id = request.args.get('session_id')
    transaction_id = None
    
    if session_id:
        try:
            # Retrieve the session to get payment details
            session = stripe.checkout.Session.retrieve(session_id)
            
            # Generate transaction ID from payment intent if not already stored
            if hasattr(session, 'payment_intent') and session.payment_intent:
                # Use payment intent as transaction ID or create one from it
                transaction_id = f"stripe_{session.payment_intent}"
            elif hasattr(session, 'id'):
                # If no payment intent, use session ID as fallback
                transaction_id = f"stripe_{session.id}"
            else:
                # Generate a random transaction ID as last resort
                transaction_id = f"stripe_{uuid.uuid4().hex}"
            
            # Log successful payment
            logger.info(f"Successful Stripe payment: {session_id}, Transaction ID: {transaction_id}")
            
            # Here we would save the transaction to our database
            # This would typically be done in the webhook, but we set the ID here for the UI
            
            # Return success page with transaction details
            return render_template('stripe/success.html', 
                                  session=session, 
                                  transaction_id=transaction_id)
        
        except Exception as e:
            logger.error(f"Error retrieving Stripe session: {str(e)}")
            flash(f"Error retrieving payment information: {str(e)}", "error")
    
    return render_template('stripe/success.html', transaction_id=transaction_id)

@stripe_bp.route('/cancel')
def cancel():
    """Handle cancelled payment"""
    return render_template('stripe/cancel.html')

@stripe_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    event = None
    
    try:
        if endpoint_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        else:
            request_json = request.get_json()
            if request_json:
                event = stripe.Event.construct_from(
                    request_json, stripe.api_key
                )
            else:
                logger.error("No JSON data in webhook request")
                return jsonify({'error': 'No JSON data in request'}), 400
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    
    # Handle the event
    if event and event.type == 'checkout.session.completed':
        session = event.data.object
        
        # Ensure we have a session ID
        if not hasattr(session, 'id'):
            logger.error("Session object does not have id attribute")
            return jsonify({'error': 'Invalid session object'}), 400
        
        logger.info(f"Payment completed for session: {session.id}")
        
        try:
            # Extract payment details
            amount = session.amount_total / 100.0 if hasattr(session, 'amount_total') else 0.0
            currency = session.currency.upper() if hasattr(session, 'currency') else 'USD'
            payment_intent = session.payment_intent if hasattr(session, 'payment_intent') else None
            
            # Create transaction ID
            transaction_id = f"stripe_{payment_intent}" if payment_intent else f"stripe_{session.id}"
            
            # Extract customer information if available
            customer_email = session.customer_email if hasattr(session, 'customer_email') else None
            customer_name = "Customer"  # Default name if not available
            
            # Extract additional metadata
            metadata = {}
            if hasattr(session, 'metadata') and session.metadata:
                metadata = session.metadata
            
            # Store the transaction in the database if models are available
            if TRANSACTION_MODELS_AVAILABLE:
                try:
                    # Create transaction record
                    transaction = Transaction(
                        transaction_id=transaction_id,
                        amount=amount,
                        currency=currency,
                        status=TransactionStatus.COMPLETED,
                        payment_method=PaymentMethod.CREDIT_CARD,
                        recipient_name=customer_name,
                        recipient_email=customer_email,
                        description="Stripe payment",
                        tx_metadata_json=json.dumps(metadata)
                    )
                    db.session.add(transaction)
                    db.session.commit()
                    logger.info(f"Transaction stored in database: {transaction_id}")
                except Exception as e:
                    logger.error(f"Error storing transaction in database: {str(e)}")
                    # Continue processing even if database storage fails
            else:
                logger.warning(f"Transaction models not available - couldn't record {transaction_id}")
            
            logger.info(f"Transaction recorded successfully: {transaction_id}")
            
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}")
            return jsonify({'error': f'Payment processing error: {str(e)}'}), 500
    
    # Handle payment_intent.succeeded event as backup
    elif event and event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        logger.info(f"Payment intent succeeded: {payment_intent.id}")
        
        # Similar transaction recording logic could be implemented here
    
    # Handle other event types as needed
    
    return jsonify({'status': 'success'})

def register_stripe_routes(app):
    """Register Stripe routes with the app"""
    app.register_blueprint(stripe_bp)
    logger.info("Stripe payment routes registered successfully")