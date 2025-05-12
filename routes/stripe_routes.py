"""
Stripe Payment Integration Routes
This module provides routes for Stripe payment processing
"""

import os
import logging
import stripe
from flask import Blueprint, render_template, redirect, request, url_for, jsonify, flash
from flask_login import login_required, current_user
from datetime import datetime
import uuid

# Set up Stripe API key from environment
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Create blueprint
stripe_bp = Blueprint('stripe', __name__, url_prefix='/stripe')
logger = logging.getLogger(__name__)

# Set up domain for success and cancel URLs
def get_domain():
    """Get the domain for the application"""
    if os.environ.get('REPLIT_DEPLOYMENT'):
        return os.environ.get('REPLIT_DEV_DOMAIN')
    elif os.environ.get('REPLIT_DOMAINS'):
        return os.environ.get('REPLIT_DOMAINS').split(',')[0]
    else:
        # Default to localhost for development
        return 'localhost:5000'

@stripe_bp.route('/')
def index():
    """Display Stripe payment options"""
    return render_template('stripe/index.html')

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
        return redirect(checkout_session.url, code=303)
    
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {str(e)}")
        flash(f"Error creating checkout session: {str(e)}", "error")
        return redirect(url_for('stripe.index'))

@stripe_bp.route('/success')
def success():
    """Handle successful payment"""
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            # Retrieve the session to get payment details
            session = stripe.checkout.Session.retrieve(session_id)
            
            # Log successful payment
            logger.info(f"Successful Stripe payment: {session_id}")
            
            # Return success page
            return render_template('stripe/success.html', session=session)
        
        except Exception as e:
            logger.error(f"Error retrieving Stripe session: {str(e)}")
            flash(f"Error retrieving payment information: {str(e)}", "error")
    
    return render_template('stripe/success.html')

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
            event = stripe.Event.construct_from(
                request.json, stripe.api_key
            )
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    
    # Handle the event
    if event.type == 'checkout.session.completed':
        session = event.data.object
        logger.info(f"Payment completed for session: {session.id}")
        
        # Here you would process the payment in your database
        # For example, update the user's account, record the transaction, etc.
    
    # Handle other event types as needed
    
    return jsonify({'status': 'success'})

def register_stripe_routes(app):
    """Register Stripe routes with the app"""
    app.register_blueprint(stripe_bp)
    logger.info("Stripe payment routes registered successfully")