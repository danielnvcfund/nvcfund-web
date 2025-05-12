"""
PayPal integration routes for the NVC Banking Platform.
These routes handle PayPal payments, payouts, and callbacks.
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app
from flask_login import login_required, current_user
import stripe

from app import db
import sys
import os
# Add the parent directory to sys.path to allow importing from the root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from paypal_integration import PayPalService
from forms import PayPalPaymentForm, PayPalPayoutForm
from models import Transaction, TransactionStatus, TransactionType, PaymentGateway, PaymentGatewayType

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create PayPal blueprint
paypal_bp = Blueprint('paypal', __name__, url_prefix='/paypal')

def get_paypal_gateway() -> Optional[PaymentGateway]:
    """Get the PayPal payment gateway from the database"""
    return PaymentGateway.query.filter_by(
        gateway_type=PaymentGatewayType.PAYPAL, 
        is_active=True
    ).first()

def register_paypal_blueprint(app):
    """Register the PayPal blueprint with the Flask app"""
    app.register_blueprint(paypal_bp)
    
    # Log the current mode (live or sandbox)
    paypal_mode = os.environ.get('PAYPAL_MODE', 'live')  # Default to live mode
    logger.info(f"PayPal configured in {paypal_mode.upper()} MODE - {'real payments will be processed' if paypal_mode == 'live' else 'test mode active'}")
    logger.info("PayPal routes registered successfully")

@paypal_bp.route('/dashboard')
@login_required
def dashboard():
    """PayPal dashboard page showing recent transactions"""
    # Get user's PayPal transactions
    transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        gateway_id=get_paypal_gateway().id if get_paypal_gateway() else None
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    
    return render_template('paypal/dashboard.html', transactions=transactions)

@paypal_bp.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    """PayPal payment form and handler"""
    form = PayPalPaymentForm()
    
    if form.validate_on_submit():
        # Check PayPal gateway first
        gateway = get_paypal_gateway()
        if not gateway:
            flash("PayPal gateway not configured in the system", "danger")
            return redirect(url_for('paypal.dashboard'))
        
        # Check if PayPal credentials are available
        if not os.environ.get('PAYPAL_CLIENT_ID') or not os.environ.get('PAYPAL_CLIENT_SECRET'):
            flash("PayPal API credentials not correctly configured. Please try using Stripe instead.", "warning")
            logger.error("PayPal API credentials missing when trying to create payment")
            return redirect(url_for('stripe.index'))
        
        # Create a unique transaction ID
        transaction_id = f"PAYPAL-{uuid.uuid4().hex[:10]}"
        
        # Generate the return and cancel URLs
        return_url = url_for('paypal.payment_return', _external=True)
        cancel_url = url_for('paypal.payment_cancel', _external=True)
        
        # Create the PayPal payment
        payment_id, approval_url = PayPalService.create_payment(
            amount=form.amount.data,
            currency=form.currency.data,
            description=form.description.data or "NVC Banking Platform Payment",
            return_url=return_url,
            cancel_url=cancel_url
        )
        
        if payment_id and approval_url:
            # Check if this is a cryptocurrency transaction
            crypto_currencies = ['NVCT', 'ETH', 'BTC', 'USDT', 'USDC', 'AFD1']
            is_crypto = form.currency.data in crypto_currencies
            
            # Determine transaction type based on currency
            if is_crypto:
                if form.currency.data == 'NVCT':
                    tx_type = TransactionType.NVCT_PAYMENT
                elif form.currency.data == 'AFD1':
                    tx_type = TransactionType.AFD1_PAYMENT
                else:
                    tx_type = TransactionType.CRYPTO_PAYMENT
            else:
                tx_type = TransactionType.PAYMENT
            
            # Build metadata including cryptocurrency details if applicable
            tx_metadata = {}
            if form.notes.data:
                tx_metadata["notes"] = form.notes.data
            
            if is_crypto:
                tx_metadata["is_cryptocurrency"] = True
                tx_metadata["crypto_currency"] = form.currency.data
                tx_metadata["original_amount"] = form.amount.data
                tx_metadata["payment_method"] = "cryptocurrency"
            
            transaction = Transaction(
                transaction_id=transaction_id,
                user_id=current_user.id,
                amount=form.amount.data,
                currency=form.currency.data,
                transaction_type=tx_type,
                status=TransactionStatus.PENDING,
                description=form.description.data + (" (Cryptocurrency Payment)" if is_crypto else ""),
                recipient_name=form.recipient_email.data,
                gateway_id=gateway.id,
                external_id=payment_id,  # Store PayPal payment ID
                tx_metadata_json=tx_metadata
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            # Store the transaction ID in the session for later reference
            session['paypal_transaction_id'] = transaction_id
            
            # Redirect to PayPal's approval page
            return redirect(approval_url)
        else:
            # More specific error message for API authentication failures
            flash("Could not create PayPal payment due to API authentication issues. You can try using Stripe instead.", "warning")
            logger.error("Failed to create PayPal payment - API returned no payment ID or approval URL")
            # Suggest Stripe as an alternative - redirect to index page of Stripe routes
            return redirect(url_for('stripe.index'))
    
    return render_template('paypal/payment_form.html', form=form)

@paypal_bp.route('/payment/return')
@login_required
def payment_return():
    """Handler for successful PayPal payment returns"""
    # Get the parameters from the PayPal redirect
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    transaction_id = session.get('paypal_transaction_id')
    
    if not payment_id or not payer_id:
        flash("Missing payment information from PayPal", "danger")
        return redirect(url_for('paypal.dashboard'))
    
    # Find the transaction
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id,
        external_id=payment_id
    ).first()
    
    if not transaction:
        flash("Transaction not found", "danger")
        return redirect(url_for('paypal.dashboard'))
    
    # Execute the PayPal payment
    success, payment_details = PayPalService.execute_payment(payment_id, payer_id)
    
    if success:
        # Update the transaction
        transaction.status = TransactionStatus.COMPLETED
        transaction.external_transaction_id = payment_details.get('id', payment_id)
        db.session.commit()
        
        flash("Payment completed successfully!", "success")
        return redirect(url_for('paypal.payment_details', payment_id=payment_id))
    else:
        # Payment failed
        transaction.status = TransactionStatus.FAILED
        db.session.commit()
        
        flash("Payment execution failed. Please try again or contact support.", "danger")
        return redirect(url_for('paypal.dashboard'))

@paypal_bp.route('/payment/cancel')
@login_required
def payment_cancel():
    """Handler for cancelled PayPal payments"""
    transaction_id = session.get('paypal_transaction_id')
    
    if transaction_id:
        # Find the transaction
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        
        if transaction:
            # Update the transaction status
            transaction.status = TransactionStatus.CANCELLED
            db.session.commit()
    
    flash("Payment was cancelled.", "warning")
    return redirect(url_for('paypal.dashboard'))

@paypal_bp.route('/payment/<payment_id>')
@login_required
def payment_details(payment_id):
    """View details of a PayPal payment"""
    # Find the transaction
    transaction = Transaction.query.filter_by(
        user_id=current_user.id,
        external_id=payment_id
    ).first()
    
    if not transaction:
        flash("Transaction not found", "danger")
        return redirect(url_for('paypal.dashboard'))
    
    # Get detailed payment information from PayPal
    payment_details = PayPalService.get_payment_details(payment_id)
    
    return render_template(
        'paypal/payment_details.html',
        transaction=transaction,
        payment_details=payment_details
    )

@paypal_bp.route('/payout', methods=['GET', 'POST'])
@login_required
def payout():
    """PayPal payout form and handler"""
    form = PayPalPayoutForm()
    
    if form.validate_on_submit():
        # Create a unique transaction ID
        transaction_id = f"PAYPAL-PAYOUT-{uuid.uuid4().hex[:10]}"
        
        # Create the PayPal payout
        success, batch_id, payout_details = PayPalService.create_payout(
            amount=form.amount.data,
            currency=form.currency.data,
            recipient_email=form.recipient_email.data,
            note=form.note.data or "NVC Banking Platform Payout",
            email_subject=form.email_subject.data,
            email_message=form.email_message.data
        )
        
        if success and batch_id:
            # Save the transaction details to the database
            gateway = get_paypal_gateway()
            if not gateway:
                flash("PayPal gateway not configured", "danger")
                return redirect(url_for('paypal.dashboard'))
            
            # Check if this is a cryptocurrency transaction
            crypto_currencies = ['NVCT', 'ETH', 'BTC', 'USDT', 'USDC', 'AFD1']
            is_crypto = form.currency.data in crypto_currencies
            
            # Determine transaction type based on currency
            if is_crypto:
                if form.currency.data == 'NVCT':
                    tx_type = TransactionType.NVCT_PAYMENT
                elif form.currency.data == 'AFD1':
                    tx_type = TransactionType.AFD1_PAYMENT
                else:
                    tx_type = TransactionType.CRYPTO_PAYMENT
            else:
                tx_type = TransactionType.PAYOUT
            
            # Build metadata including cryptocurrency details if applicable
            tx_metadata = {}
            if form.email_subject.data:
                tx_metadata["email_subject"] = form.email_subject.data
            if form.email_message.data:
                tx_metadata["email_message"] = form.email_message.data
            
            if is_crypto:
                tx_metadata["is_cryptocurrency"] = True
                tx_metadata["crypto_currency"] = form.currency.data
                tx_metadata["original_amount"] = form.amount.data
                tx_metadata["payment_method"] = "cryptocurrency"
            
            transaction = Transaction(
                transaction_id=transaction_id,
                user_id=current_user.id,
                amount=form.amount.data,
                currency=form.currency.data,
                transaction_type=tx_type,
                status=TransactionStatus.PROCESSING,  # Payouts are asynchronous
                description=form.note.data + (" (Cryptocurrency Payout)" if is_crypto else ""),
                recipient_name=form.recipient_email.data,
                gateway_id=gateway.id,
                external_id=batch_id,  # Store PayPal batch ID
                tx_metadata_json=tx_metadata
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            flash("Payout initiated successfully!", "success")
            return redirect(url_for('paypal.payout_status', batch_id=batch_id))
        else:
            flash("Failed to create PayPal payout. Please try again.", "danger")
    
    return render_template('paypal/payout_form.html', form=form)

@paypal_bp.route('/payout/<batch_id>')
@login_required
def payout_status(batch_id):
    """View status of a PayPal payout"""
    # Find the transaction
    transaction = Transaction.query.filter_by(
        user_id=current_user.id,
        external_id=batch_id
    ).first()
    
    if not transaction:
        flash("Payout not found", "danger")
        return redirect(url_for('paypal.dashboard'))
    
    # Get detailed payout information from PayPal
    payout_details = PayPalService.get_payout_details(batch_id)
    
    # Update transaction status based on payout status
    if payout_details:
        batch_status = payout_details.get('batch_header', {}).get('batch_status')
        if batch_status == 'SUCCESS':
            transaction.status = TransactionStatus.COMPLETED
            db.session.commit()
        elif batch_status == 'DENIED' or batch_status == 'FAILED':
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
    
    return render_template(
        'paypal/payout_status.html',
        transaction=transaction,
        payout_details=payout_details
    )

@paypal_bp.route('/webhook', methods=['POST'])
def webhook():
    """PayPal webhook endpoint for receiving event notifications"""
    # Verify the webhook signature
    event_body = request.data.decode('utf-8')
    transmission_id = request.headers.get('PAYPAL-TRANSMISSION-ID')
    timestamp = request.headers.get('PAYPAL-TRANSMISSION-TIME')
    webhook_id = os.environ.get('PAYPAL_WEBHOOK_ID')
    transmission_sig = request.headers.get('PAYPAL-TRANSMISSION-SIG')
    cert_url = request.headers.get('PAYPAL-CERT-URL')
    
    if not all([transmission_id, timestamp, webhook_id, transmission_sig, cert_url]):
        logger.warning("Missing required webhook headers")
        return jsonify({"success": False, "error": "Missing required headers"}), 400
    
    # Verify the webhook signature
    if not PayPalService.is_webhook_signature_valid(
        transmission_id, timestamp, webhook_id, event_body, transmission_sig, cert_url
    ):
        logger.warning("Invalid webhook signature")
        return jsonify({"success": False, "error": "Invalid signature"}), 400
    
    # Process the webhook event
    payload = request.json
    event_type = payload.get('event_type')
    
    logger.info(f"Received PayPal webhook event: {event_type}")
    
    # Handle various event types
    if event_type == 'PAYMENT.SALE.COMPLETED':
        # Payment sale completed
        resource = payload.get('resource', {})
        transaction_id = resource.get('parent_payment')
        
        # Update the transaction status
        if transaction_id:
            transaction = Transaction.query.filter_by(external_id=transaction_id).first()
            if transaction:
                transaction.status = TransactionStatus.COMPLETED
                db.session.commit()
                logger.info(f"Updated transaction {transaction.transaction_id} to COMPLETED")
    
    # Handle other event types as needed
    
    return jsonify({"success": True}), 200