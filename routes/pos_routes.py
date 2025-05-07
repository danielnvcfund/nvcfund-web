"""
POS Routes Module
This module provides routes for the POS (Point of Sale) system.
It handles payment processing via Stripe and other payment-related functionality.
"""

import os
import uuid
import json
import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound, BadRequest

import stripe

from models import Transaction, TransactionType, TransactionStatus, db
from forms import POSPaymentForm, POSSendPaymentForm
from pos_payment_service import POSPaymentService

# Configure logging
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
stripe_publishable_key = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_default')

# Blueprint Configuration
pos_bp = Blueprint(
    'pos',
    __name__,
    url_prefix='/pos',
    template_folder='templates'
)


@pos_bp.route('/dashboard', methods=['GET'])
@login_required
def pos_dashboard():
    """POS system dashboard"""
    # Get recent transactions (limit to 10)
    recent_transactions = Transaction.query.filter(
        (Transaction.transaction_type == TransactionType.PAYMENT) | 
        (Transaction.transaction_type == TransactionType.PAYOUT)
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    
    # Calculate total payments and payouts
    total_payments = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.transaction_type == TransactionType.PAYMENT,
        Transaction.status == TransactionStatus.COMPLETED
    ).scalar() or 0.0
    
    total_payouts = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.transaction_type == TransactionType.PAYOUT,
        Transaction.status == TransactionStatus.COMPLETED
    ).scalar() or 0.0
    
    return render_template(
        'pos/dashboard.html',
        recent_transactions=recent_transactions,
        total_payments=total_payments,
        total_payouts=total_payouts
    )


@pos_bp.route('/accept-payment', methods=['GET', 'POST'])
@login_required
def accept_payment():
    """Accept credit card payment form"""
    form = POSPaymentForm()
    
    if form.validate_on_submit():
        # Create a new transaction
        transaction = Transaction(
            transaction_id=f"POS_{uuid.uuid4().hex[:16]}",
            amount=form.amount.data,
            currency=form.currency.data,
            transaction_type=TransactionType.PAYMENT,
            status=TransactionStatus.PENDING,
            description=form.description.data or f"Payment from {form.customer_name.data}",
            recipient_name="NVC Banking Platform",
            recipient_institution="NVC Fund",
            metadata={
                'customer_name': form.customer_name.data,
                'customer_email': form.customer_email.data,
                'payment_method': 'credit_card',
                'processor': 'stripe'
            },
            created_by=current_user.id
        )
        
        # Save the transaction
        db.session.add(transaction)
        db.session.commit()
        
        # Redirect to checkout page
        return redirect(url_for('pos.checkout', transaction_id=transaction.transaction_id))
    
    return render_template('pos/accept_payment.html', form=form)


@pos_bp.route('/checkout/<transaction_id>', methods=['GET'])
@login_required
def checkout(transaction_id):
    """Checkout page for credit card payment"""
    # Find the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    # Verify that the transaction is pending
    if transaction.status != TransactionStatus.PENDING:
        flash('This transaction has already been processed.', 'warning')
        return redirect(url_for('pos.pos_dashboard'))
    
    try:
        # Get the domain URL
        domain_url = request.host_url.rstrip('/')
        
        # Create a checkout session
        checkout_session = POSPaymentService.create_checkout_session(transaction, domain_url)
        
        # Pass display_currency to the template
        display_currency = transaction.currency
        
        return render_template(
            'pos/checkout.html', 
            transaction=transaction,
            checkout_session=checkout_session,
            stripe_publishable_key=stripe_publishable_key,
            display_currency=display_currency
        )
        
    except stripe.error.StripeError as e:
        # Handle Stripe-specific errors
        logger.error(f"Stripe error creating checkout session: {str(e)}")
        flash(f"An error occurred with the payment processor: {str(e)}", 'danger')
        
        # Update transaction status
        transaction.status = TransactionStatus.FAILED
        transaction.metadata['error'] = str(e)
        db.session.commit()
        
        return redirect(url_for('pos.pos_dashboard'))
        
    except Exception as e:
        # Handle other errors
        logger.error(f"Unexpected error creating checkout session: {str(e)}")
        flash("An unexpected error occurred. Please try again later.", 'danger')
        
        # Update transaction status
        transaction.status = TransactionStatus.FAILED
        transaction.metadata['error'] = str(e)
        db.session.commit()
        
        return redirect(url_for('pos.pos_dashboard'))


@pos_bp.route('/payment-success/<transaction_id>', methods=['GET'])
@login_required
def payment_success(transaction_id):
    """Payment success page"""
    # Find the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    # Update transaction status if not already completed
    if transaction.status != TransactionStatus.COMPLETED:
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = datetime.utcnow()
        transaction.metadata['payment_status'] = 'paid'
        db.session.commit()
    
    return render_template('pos/payment_success.html', transaction=transaction)


@pos_bp.route('/payment-cancel/<transaction_id>', methods=['GET'])
@login_required
def payment_cancel(transaction_id):
    """Payment cancelled page"""
    # Find the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    # Update transaction status
    if transaction.status == TransactionStatus.PENDING:
        transaction.status = TransactionStatus.CANCELLED
        transaction.metadata['payment_status'] = 'cancelled'
        db.session.commit()
    
    return render_template('pos/payment_cancel.html', transaction=transaction)


@pos_bp.route('/send-payment', methods=['GET', 'POST'])
@login_required
def send_payment():
    """Send money to a credit card"""
    form = POSSendPaymentForm()
    
    if form.validate_on_submit():
        # Create a new transaction
        transaction = Transaction(
            transaction_id=f"POS_SEND_{uuid.uuid4().hex[:16]}",
            amount=form.amount.data,
            currency=form.currency.data,
            transaction_type=TransactionType.PAYOUT,
            status=TransactionStatus.PENDING,
            description=form.description.data or f"Payment to {form.recipient_name.data}",
            recipient_name=form.recipient_name.data,
            recipient_institution="Credit Card Payment",
            metadata={
                'recipient_email': form.recipient_email.data,
                'card_last4': form.card_number.data,
                'payment_method': 'credit_card',
                'processor': 'stripe'
            },
            created_by=current_user.id
        )
        
        # Save the transaction
        db.session.add(transaction)
        db.session.commit()
        
        try:
            # Process the payout
            payout_result = POSPaymentService.create_payout(transaction)
            
            # Redirect to success page
            return redirect(url_for('pos.send_payment_success', transaction_id=transaction.transaction_id))
            
        except stripe.error.StripeError as e:
            # Handle Stripe-specific errors
            logger.error(f"Stripe error creating payout: {str(e)}")
            flash(f"An error occurred with the payment processor: {str(e)}", 'danger')
            
            # Update transaction status
            transaction.status = TransactionStatus.FAILED
            transaction.metadata['error'] = str(e)
            db.session.commit()
            
            return redirect(url_for('pos.send_payment'))
            
        except Exception as e:
            # Handle other errors
            logger.error(f"Unexpected error creating payout: {str(e)}")
            flash("An unexpected error occurred. Please try again later.", 'danger')
            
            # Update transaction status
            transaction.status = TransactionStatus.FAILED
            transaction.metadata['error'] = str(e)
            db.session.commit()
            
            return redirect(url_for('pos.send_payment'))
    
    return render_template('pos/send_payment.html', form=form)


@pos_bp.route('/send-payment-success/<transaction_id>', methods=['GET'])
@login_required
def send_payment_success(transaction_id):
    """Send payment success page"""
    # Find the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    return render_template('pos/send_payment_success.html', transaction=transaction)


@pos_bp.route('/transactions', methods=['GET'])
@login_required
def transactions():
    """List all POS transactions with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Base query
    query = Transaction.query.filter(
        (Transaction.transaction_type == TransactionType.PAYMENT) | 
        (Transaction.transaction_type == TransactionType.PAYOUT)
    )
    
    # Apply filters
    # Transaction type filter
    transaction_type = request.args.get('transaction_type')
    if transaction_type:
        try:
            query = query.filter(Transaction.transaction_type == TransactionType[transaction_type])
        except KeyError:
            flash(f"Invalid transaction type: {transaction_type}", "warning")
    
    # Status filter
    status = request.args.get('status')
    if status:
        try:
            query = query.filter(Transaction.status == TransactionStatus[status])
        except KeyError:
            flash(f"Invalid status: {status}", "warning")
    
    # Date range filter
    date_range = request.args.get('date_range', 'all')
    now = datetime.utcnow()
    if date_range == 'today':
        query = query.filter(Transaction.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0))
    elif date_range == 'week':
        query = query.filter(Transaction.created_at >= (now - timedelta(days=7)))
    elif date_range == 'month':
        query = query.filter(Transaction.created_at >= (now - timedelta(days=30)))
    elif date_range == 'year':
        query = query.filter(Transaction.created_at >= (now - timedelta(days=365)))
    
    # Search filter
    search = request.args.get('search', '')
    if search:
        query = query.filter(
            (Transaction.transaction_id.like(f"%{search}%")) |
            (Transaction.recipient_name.like(f"%{search}%")) |
            (Transaction.description.like(f"%{search}%"))
        )
    
    # Sort by created_at (newest first)
    query = query.order_by(Transaction.created_at.desc())
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    transactions = pagination.items
    
    return render_template(
        'pos/transactions.html',
        transactions=transactions,
        pagination=pagination
    )


@pos_bp.route('/view-receipt/<transaction_id>', methods=['GET'])
@login_required
def view_receipt(transaction_id):
    """View a transaction receipt"""
    # Find the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    if transaction.transaction_type == TransactionType.PAYMENT:
        return render_template('pos/payment_success.html', transaction=transaction)
    elif transaction.transaction_type == TransactionType.PAYOUT:
        return render_template('pos/send_payment_success.html', transaction=transaction)
    else:
        flash("Unsupported transaction type for receipt view.", "warning")
        return redirect(url_for('pos.transactions'))


@pos_bp.route('/cancel-transaction/<transaction_id>', methods=['GET'])
@login_required
def cancel_transaction(transaction_id):
    """Cancel a pending transaction"""
    # Find the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    # Verify that the transaction is pending
    if transaction.status != TransactionStatus.PENDING:
        flash('Only pending transactions can be cancelled.', 'warning')
        return redirect(url_for('pos.transactions'))
    
    # Update transaction status
    transaction.status = TransactionStatus.CANCELLED
    transaction.metadata['cancelled_by'] = current_user.id
    transaction.metadata['cancelled_at'] = datetime.utcnow().isoformat()
    db.session.commit()
    
    flash('Transaction has been cancelled successfully.', 'success')
    return redirect(url_for('pos.transactions'))


@pos_bp.route('/webhook', methods=['POST'])
def webhook():
    """Stripe webhook handler"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = None
        
        if endpoint_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        else:
            event = json.loads(payload)
        
        # Process the event
        if POSPaymentService.process_webhook_event(event):
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Error processing webhook event'}), 400
        
    except ValueError as e:
        # Invalid payload
        logger.error(f"Invalid payload: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400
        
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Invalid signature: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400
        
    except Exception as e:
        # Other error
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400


def register_routes(app):
    """Register the POS routes blueprint"""
    # No need to register blueprint here, it's registered in app.py
    logger.info("POS Payment routes registered successfully")