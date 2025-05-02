"""
PayPal Payment Routes for NVC Banking Platform

This module handles routes for PayPal payments, payouts, and webhook handling.
"""
import os
import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, session

from forms import PayPalPaymentForm, PayPalPayoutForm
from models import Transaction, TransactionStatus, TransactionType, PaymentGateway
from paypal_service import paypal_service
from flask_login import login_required, current_user
from auth import admin_required

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
paypal_bp = Blueprint('paypal', __name__, url_prefix='/paypal')

@paypal_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """PayPal Dashboard showing transaction history"""
    transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        payment_provider='paypal'
    ).order_by(Transaction.created_at.desc()).all()
    
    return render_template(
        'paypal/dashboard.html',
        transactions=transactions
    )

@paypal_bp.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    """Create a new PayPal payment"""
    form = PayPalPaymentForm()
    
    if form.validate_on_submit():
        # Get form data
        amount = form.amount.data
        currency = form.currency.data
        recipient_email = form.recipient_email.data
        description = form.description.data
        
        # Generate return and cancel URLs
        return_url = url_for('paypal.payment_success', _external=True)
        cancel_url = url_for('paypal.payment_cancel', _external=True)
        
        # Create PayPal payment
        payment_result = paypal_service.create_payment(
            amount=amount,
            currency=currency,
            description=description,
            return_url=return_url,
            cancel_url=cancel_url
        )
        
        if not payment_result:
            flash('Failed to create PayPal payment. Please try again.', 'danger')
            return render_template('paypal/payment_form.html', form=form)
        
        # Extract payment ID and approval URL
        payment_id = payment_result.get('id')
        
        # Create transaction record in database
        transaction = paypal_service.create_transaction_record(
            user_id=current_user.id,
            amount=amount,
            currency=currency,
            paypal_payment_id=payment_id,
            recipient_email=recipient_email,
            transaction_type=TransactionType.PAYMENT,
            status=TransactionStatus.PENDING,
            description=description
        )
        
        if not transaction:
            flash('Failed to create transaction record. Payment may still be processed.', 'warning')
        
        # Find approval URL
        for link in payment_result.get('links', []):
            if link.get('rel') == 'approval_url':
                approval_url = link.get('href')
                # Redirect user to PayPal approval URL
                return redirect(approval_url)
        
        flash('Invalid PayPal response. Please try again.', 'danger')
        return render_template('paypal/payment_form.html', form=form)
    
    return render_template('paypal/payment_form.html', form=form)

@paypal_bp.route('/payment/success', methods=['GET'])
@login_required
def payment_success():
    """Handle successful PayPal payment approval"""
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    
    if not payment_id or not payer_id:
        flash('Invalid payment response from PayPal', 'danger')
        return redirect(url_for('paypal.dashboard'))
    
    # Execute the payment
    execution_result = paypal_service.execute_payment(payment_id, payer_id)
    
    if not execution_result:
        flash('Failed to execute PayPal payment', 'danger')
        return redirect(url_for('paypal.dashboard'))
    
    # Update transaction status in database
    transaction = Transaction.query.filter_by(
        external_transaction_id=payment_id,
        payment_provider='paypal'
    ).first()
    
    if transaction:
        paypal_service.update_transaction_status(
            transaction.id,
            TransactionStatus.COMPLETED,
            f"Payment completed successfully. Payer ID: {payer_id}"
        )
    
    flash('Payment completed successfully', 'success')
    return redirect(url_for('paypal.payment_details', payment_id=payment_id))

@paypal_bp.route('/payment/cancel', methods=['GET'])
@login_required
def payment_cancel():
    """Handle cancelled PayPal payment"""
    payment_id = request.args.get('paymentId')
    
    if payment_id:
        # Update transaction status in database
        transaction = Transaction.query.filter_by(
            external_transaction_id=payment_id,
            payment_provider='paypal'
        ).first()
        
        if transaction:
            paypal_service.update_transaction_status(
                transaction.id,
                TransactionStatus.CANCELLED,
                "Payment cancelled by user"
            )
    
    flash('Payment was cancelled', 'warning')
    return redirect(url_for('paypal.dashboard'))

@paypal_bp.route('/payment/<payment_id>', methods=['GET'])
@login_required
def payment_details(payment_id):
    """View details of a PayPal payment"""
    # Get transaction from database
    transaction = Transaction.query.filter_by(
        external_transaction_id=payment_id,
        payment_provider='paypal'
    ).first_or_404()
    
    # Check if user has permission to view this transaction
    if transaction.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to view this transaction', 'danger')
        return redirect(url_for('paypal.dashboard'))
    
    # Get payment details from PayPal
    payment_details = paypal_service.get_payment_details(payment_id)
    
    return render_template(
        'paypal/payment_details.html',
        transaction=transaction,
        payment_details=payment_details
    )

@paypal_bp.route('/payout', methods=['GET', 'POST'])
@login_required
def payout():
    """Create a new PayPal payout"""
    form = PayPalPayoutForm()
    
    if form.validate_on_submit():
        # Get form data
        amount = form.amount.data
        currency = form.currency.data
        recipient_email = form.recipient_email.data
        note = form.note.data
        email_subject = form.email_subject.data
        email_message = form.email_message.data
        
        # Create PayPal payout
        payout_result = paypal_service.create_payout(
            receiver_email=recipient_email,
            amount=amount,
            currency=currency,
            note=note,
            email_subject=email_subject,
            email_message=email_message
        )
        
        if not payout_result:
            flash('Failed to create PayPal payout. Please try again.', 'danger')
            return render_template('paypal/payout_form.html', form=form)
        
        # Extract payout batch ID and item ID
        batch_id = payout_result.get('batch_header', {}).get('payout_batch_id')
        payout_item = payout_result.get('items', [{}])[0] if payout_result.get('items') else {}
        payout_item_id = payout_item.get('payout_item_id')
        
        # Create transaction record in database
        transaction = paypal_service.create_transaction_record(
            user_id=current_user.id,
            amount=amount,
            currency=currency,
            paypal_payment_id=payout_item_id or batch_id,
            recipient_email=recipient_email,
            transaction_type=TransactionType.PAYOUT,
            status=TransactionStatus.PENDING,
            description=note
        )
        
        if not transaction:
            flash('Failed to create transaction record. Payout may still be processed.', 'warning')
        
        flash('Payout initiated successfully', 'success')
        return redirect(url_for('paypal.payout_status', batch_id=batch_id))
    
    return render_template('paypal/payout_form.html', form=form)

@paypal_bp.route('/payout/<batch_id>', methods=['GET'])
@login_required
def payout_status(batch_id):
    """Check status of a PayPal payout batch"""
    # Get payout details from PayPal
    payout_details = paypal_service.get_payout_details(batch_id)
    
    if not payout_details:
        flash('Failed to retrieve payout details', 'danger')
        return redirect(url_for('paypal.dashboard'))
    
    return render_template(
        'paypal/payout_status.html',
        payout_details=payout_details
    )

@paypal_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle PayPal webhooks"""
    # Verify webhook signature if webhook ID is configured
    webhook_id = current_app.config.get('PAYPAL_WEBHOOK_ID')
    
    event_body = request.data
    data = json.loads(event_body)
    
    # Log webhook event
    logger.info(f"Received PayPal webhook: {data.get('event_type')}")
    
    if webhook_id:
        # Verify signature
        signature_verified = paypal_service.verify_webhook_signature(
            webhook_id,
            event_body,
            request.headers
        )
        
        if not signature_verified:
            logger.warning("Invalid PayPal webhook signature")
            return jsonify({"status": "Invalid signature"}), 401
    else:
        logger.warning("PayPal webhook ID not configured, skipping signature verification")
    
    # Process webhook event
    success = paypal_service.process_webhook_event(data)
    
    if success:
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "error"}), 500

@paypal_bp.route('/admin/transactions', methods=['GET'])
@login_required
@admin_required
def admin_transactions():
    """Admin view of all PayPal transactions"""
    transactions = Transaction.query.filter_by(
        payment_provider='paypal'
    ).order_by(Transaction.created_at.desc()).all()
    
    return render_template(
        'paypal/admin_transactions.html',
        transactions=transactions
    )

@paypal_bp.route('/admin/transaction/<int:transaction_id>/update', methods=['POST'])
@login_required
@admin_required
def admin_update_transaction(transaction_id):
    """Admin endpoint to update transaction status"""
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Only allow updating PayPal transactions
    if transaction.payment_provider != 'paypal':
        flash('This is not a PayPal transaction', 'danger')
        return redirect(url_for('paypal.admin_transactions'))
    
    new_status = request.form.get('status')
    notes = request.form.get('notes')
    
    if not new_status:
        flash('Status is required', 'danger')
        return redirect(url_for('paypal.admin_transactions'))
    
    try:
        # Convert string status to enum
        new_status_enum = TransactionStatus[new_status]
        
        # Update transaction status
        success = paypal_service.update_transaction_status(
            transaction_id,
            new_status_enum,
            notes
        )
        
        if success:
            flash('Transaction status updated successfully', 'success')
        else:
            flash('Failed to update transaction status', 'danger')
    except KeyError:
        flash('Invalid status', 'danger')
    
    return redirect(url_for('paypal.admin_transactions'))

def register_paypal_blueprint(app):
    """Register the PayPal blueprint with the app"""
    app.register_blueprint(paypal_bp)
    logger.info("PayPal routes registered successfully")