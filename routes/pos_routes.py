"""
POS Payment Routes
This module provides routes for the POS payment system.
"""

import os
import json
import uuid
import logging
from datetime import datetime, timedelta

import stripe
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, current_app
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound, BadRequest

from models import Transaction, TransactionType, TransactionStatus, db
from forms import POSPaymentForm, POSPayoutForm, POSTransactionFilterForm
from pos_payment_service import POSPaymentService

# Configure logging
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Create blueprint
pos_bp = Blueprint('pos', __name__, url_prefix='/pos')

# Add custom template filters
@pos_bp.app_template_filter('from_json')
def parse_json(value):
    """Parse JSON string into Python object"""
    try:
        if value is None:
            return {}
        return json.loads(value)
    except (ValueError, TypeError):
        return {}


@pos_bp.route('/dashboard')
@login_required
def pos_dashboard():
    """Render the POS dashboard"""
    # Get recent transactions (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    # IMPORTANT: The database doesn't have a PAYOUT transaction type,
    # we need to use PAYMENT to represent all POS transactions
    # Instead, we'll distinguish them by the metadata
    payment_types = [TransactionType.PAYMENT.value]
    
    recent_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type.in_(payment_types),
        Transaction.created_at >= thirty_days_ago
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    
    # Calculate totals
    total_payments = 0.0
    total_payouts = 0.0
    
    # Get transactions for calculating totals
    completed_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.status == TransactionStatus.COMPLETED,
        Transaction.created_at >= thirty_days_ago,
        Transaction.transaction_type.in_(payment_types)
    ).all()
    
    for tx in completed_transactions:
        if tx.transaction_type == TransactionType.PAYMENT.value:
            # Convert to USD for display consistency (simplified)
            if tx.currency == 'USD':
                total_payments += tx.amount
            elif tx.currency == 'EUR':
                total_payments += tx.amount * 1.1  # Simplified EUR to USD conversion
            elif tx.currency == 'GBP':
                total_payments += tx.amount * 1.25  # Simplified GBP to USD conversion
            elif tx.currency == 'NVCT':
                total_payments += tx.amount  # 1:1 with USD
        # For payouts, check the metadata to determine if it's a payout
        elif tx.transaction_type == TransactionType.PAYMENT.value:
            # Parse the metadata to check if it's a payout
            metadata = {}
            if tx.tx_metadata_json:
                try:
                    metadata = json.loads(tx.tx_metadata_json)
                except:
                    pass
                
            # If payment_type is 'pos_payout', consider it a payout
            if metadata.get('payment_type') == 'pos_payout':
                # Convert to USD for display consistency (simplified)
                if tx.currency == 'USD':
                    total_payouts += tx.amount
                elif tx.currency == 'EUR':
                    total_payouts += tx.amount * 1.1  # Simplified EUR to USD conversion
                elif tx.currency == 'GBP':
                    total_payouts += tx.amount * 1.25  # Simplified GBP to USD conversion
                elif tx.currency == 'NVCT':
                    total_payouts += tx.amount  # 1:1 with USD
    
    return render_template(
        'pos/dashboard.html',
        recent_transactions=recent_transactions,
        total_payments=total_payments,
        total_payouts=total_payouts
    )


@pos_bp.route('/accept-payment', methods=['GET', 'POST'])
@login_required
def accept_payment():
    """Render the accept payment form and process form submission"""
    form = POSPaymentForm()
    
    if form.validate_on_submit():
        # Create new transaction record
        transaction = Transaction(
            transaction_id=f"POS-{uuid.uuid4().hex[:8].upper()}",
            user_id=current_user.id,
            transaction_type=TransactionType.PAYMENT,
            amount=form.amount.data,
            currency=form.currency.data,
            description=form.description.data or f"POS Payment from {form.customer_name.data}",
            status=TransactionStatus.PENDING,
            tx_metadata_json=json.dumps({
                'payment_type': 'pos',
                'customer_name': form.customer_name.data,
                'customer_email': form.customer_email.data,
                'payment_method': 'card',
                'created_via': 'pos_system'
            })
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        # Redirect to checkout page
        return redirect(url_for('pos.checkout', transaction_id=transaction.transaction_id))
    
    return render_template('pos/accept_payment.html', form=form)


@pos_bp.route('/checkout/<transaction_id>')
@login_required
def checkout(transaction_id):
    """Process checkout for a given transaction"""
    # Get transaction
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Verify transaction is still pending
    if transaction.status != TransactionStatus.PENDING:
        flash('This transaction has already been processed.', 'warning')
        return redirect(url_for('pos.pos_dashboard'))
    
    try:
        # Get domain URL
        domain_url = request.host_url.rstrip('/')
        
        # Create checkout session with Stripe
        checkout_session = POSPaymentService.create_checkout_session(transaction, domain_url)
        
        # Render checkout page
        return render_template(
            'pos/checkout.html',
            transaction=transaction,
            checkout_session=checkout_session
        )
        
    except stripe.error.StripeError as e:
        # Handle Stripe-specific errors
        logger.error(f"Stripe error during checkout: {str(e)}")
        flash(f"Payment processing error: {str(e)}", "danger")
        return redirect(url_for('pos.pos_dashboard'))
        
    except Exception as e:
        # Handle other errors
        logger.error(f"Unexpected error during checkout: {str(e)}")
        flash("An unexpected error occurred. Please try again.", "danger")
        return redirect(url_for('pos.pos_dashboard'))


@pos_bp.route('/payment-success/<transaction_id>')
@login_required
def payment_success(transaction_id):
    """Handle successful payment completion"""
    # Get transaction
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Update transaction status if not already completed
    # This is a fallback - webhooks will typically handle this
    if transaction.status == TransactionStatus.PENDING:
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = datetime.utcnow()
        db.session.commit()
    
    return render_template('pos/payment_success.html', transaction=transaction)


@pos_bp.route('/payment-cancel/<transaction_id>')
@login_required
def payment_cancel(transaction_id):
    """Handle payment cancellation"""
    # Get transaction
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Update transaction status
    if transaction.status == TransactionStatus.PENDING:
        transaction.status = TransactionStatus.CANCELLED
        db.session.commit()
    
    return render_template('pos/payment_cancel.html', transaction=transaction)


@pos_bp.route('/send-payment', methods=['GET', 'POST'])
@login_required
def send_payment():
    """Render the send payment form and process form submission"""
    form = POSPayoutForm()
    
    if form.validate_on_submit():
        # Create new transaction record
        # IMPORTANT: Using PAYMENT type instead of PAYOUT since PAYOUT doesn't exist
        # in the database's enum type. We distinguish between payments and payouts
        # using the metadata.
        transaction = Transaction(
            transaction_id=f"POS-{uuid.uuid4().hex[:8].upper()}",
            user_id=current_user.id,
            transaction_type=TransactionType.PAYMENT,  # Use PAYMENT type for all POS transactions
            amount=form.amount.data,
            currency=form.currency.data,
            description=form.description.data or f"Payout to {form.recipient_name.data}",
            status=TransactionStatus.PENDING,
            tx_metadata_json=json.dumps({
                'payment_type': 'pos_payout',  # Use metadata to indicate it's a payout
                'recipient_name': form.recipient_name.data,
                'recipient_email': form.recipient_email.data,
                'card_last4': form.card_last4.data,
                'payment_method': 'card',
                'created_via': 'pos_system'
            })
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        try:
            # Process payout (in a real system, this would interact with a payment provider)
            payout_result = POSPaymentService.create_payout(transaction)
            
            if payout_result.get('status') == 'success':
                # Redirect to success page
                return redirect(url_for('pos.send_payment_success', transaction_id=transaction.transaction_id))
            else:
                # Handle error
                flash("There was an error processing your payout. Please try again.", "danger")
                return redirect(url_for('pos.send_payment'))
                
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Error processing payout: {str(e)}")
            flash("An unexpected error occurred. Please try again.", "danger")
            return redirect(url_for('pos.send_payment'))
    
    return render_template('pos/send_payment.html', form=form)


@pos_bp.route('/send-payment-success/<transaction_id>')
@login_required
def send_payment_success(transaction_id):
    """Handle successful payout completion"""
    # Get transaction
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id,
        user_id=current_user.id
    ).first_or_404()
    
    return render_template('pos/send_payment_success.html', transaction=transaction)


@pos_bp.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    """Show transaction history with filters"""
    form = POSTransactionFilterForm(request.args)
    
    # IMPORTANT: The database doesn't have a PAYOUT transaction type,
    # we need to use PAYMENT to represent all POS transactions
    # We distinguish payment types by metadata
    payment_types = [TransactionType.PAYMENT.value]
    
    # Base query for user's POS transactions
    query = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type.in_(payment_types),
        Transaction.tx_metadata_json.cast(db.Text).contains('pos_system')
    )
    
    # Apply filters
    if form.date_from.data:
        query = query.filter(Transaction.created_at >= form.date_from.data)
    
    if form.date_to.data:
        # Add one day to include the entire end day
        end_date = form.date_to.data + timedelta(days=1)
        query = query.filter(Transaction.created_at < end_date)
    
    if form.transaction_type.data:
        query = query.filter(Transaction.transaction_type == form.transaction_type.data)
    
    if form.status.data:
        query = query.filter(Transaction.status == form.status.data)
    
    if form.min_amount.data is not None:
        query = query.filter(Transaction.amount >= form.min_amount.data)
    
    if form.max_amount.data is not None:
        query = query.filter(Transaction.amount <= form.max_amount.data)
    
    if form.currency.data:
        query = query.filter(Transaction.currency == form.currency.data)
    
    if form.search.data:
        search_term = f"%{form.search.data}%"
        query = query.filter(
            (Transaction.transaction_id.ilike(search_term)) | 
            (Transaction.description.ilike(search_term)) | 
            (Transaction.amount.ilike(search_term))
        )
    
    # Execute query with pagination
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Transaction.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    transactions = pagination.items
    
    return render_template(
        'pos/transactions.html',
        transactions=transactions,
        pagination=pagination,
        form=form
    )


@pos_bp.route('/view-receipt/<transaction_id>')
@login_required
def view_receipt(transaction_id):
    """View receipt for a transaction"""
    # Get transaction
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Only show receipts for completed transactions
    if transaction.status != TransactionStatus.COMPLETED:
        flash("Receipts are only available for completed transactions.", "warning")
        return redirect(url_for('pos.transactions'))
    
    return render_template('pos/receipt.html', transaction=transaction)


@pos_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhook events"""
    # Verify webhook signature (in production)
    # endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    if not request.data:
        return jsonify({'status': 'error', 'message': 'No data received'}), 400
    
    try:
        event = json.loads(request.data)
        
        # Process the event
        if POSPaymentService.process_webhook_event(event):
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to process webhook'}), 400
        
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'message': 'Invalid JSON'}), 400
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400


def register_routes(app):
    """Register the POS routes blueprint"""
    # No need to register blueprint here, it's registered in app.py
    logger.info("POS Payment routes registered successfully")