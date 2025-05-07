"""
POS Payment System Routes

This module provides routes for the POS (Point of Sale) payment system
allowing both accepting payments via credit card and sending money to credit cards.
"""

import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.exceptions import BadRequest, InternalServerError
from wtforms import StringField, DecimalField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange
import stripe

from app import db
from forms import BaseForm
from models import Transaction, TransactionStatus, TransactionType, User

# Create a POS blueprint
pos_bp = Blueprint('pos', __name__, url_prefix='/pos')

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Constants
SUPPORTED_CURRENCIES = [
    ('USD', 'USD - US Dollar'),
    ('EUR', 'EUR - Euro'),
    ('GBP', 'GBP - British Pound'),
    ('NVCT', 'NVCT - NVC Token')
]

class AcceptPaymentForm(BaseForm):
    """Form for accepting payments via credit card"""
    amount = DecimalField('Amount', validators=[
        DataRequired(),
        NumberRange(min=1, message='Amount must be at least 1')
    ])
    currency = SelectField('Currency', validators=[DataRequired()])
    customer_name = StringField('Customer Name', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    customer_email = StringField('Customer Email', validators=[
        Optional(),
        Email()
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500)
    ])

    def __init__(self, *args, **kwargs):
        super(AcceptPaymentForm, self).__init__(*args, **kwargs)
        self.currency.choices = SUPPORTED_CURRENCIES


class SendPaymentForm(BaseForm):
    """Form for sending money to credit cards"""
    amount = DecimalField('Amount', validators=[
        DataRequired(),
        NumberRange(min=1, message='Amount must be at least 1')
    ])
    currency = SelectField('Currency', validators=[DataRequired()])
    recipient_name = StringField('Recipient Name', validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    recipient_email = StringField('Recipient Email', validators=[
        Optional(),
        Email()
    ])
    card_number = StringField('Card Number (Last 4 digits)', validators=[
        DataRequired(),
        Length(min=4, max=4)
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500)
    ])

    def __init__(self, *args, **kwargs):
        super(SendPaymentForm, self).__init__(*args, **kwargs)
        self.currency.choices = SUPPORTED_CURRENCIES


def create_transaction(transaction_type, amount, currency, status=TransactionStatus.PENDING,
                      recipient_name=None, description=None, reference_id=None, metadata=None):
    """Create a transaction record in the database"""
    
    # Generate a unique transaction ID if not provided
    if not reference_id:
        reference_id = f"POS-{uuid.uuid4().hex[:8].upper()}"
    
    # Default metadata if none provided
    if not metadata:
        metadata = {}
    
    # Create the transaction record
    transaction = Transaction(
        transaction_id=reference_id,
        user_id=current_user.id if current_user.is_authenticated else None,
        transaction_type=transaction_type,
        amount=float(amount),
        currency=currency,
        status=status,
        recipient_name=recipient_name,
        description=description,
        metadata=metadata
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return transaction


@pos_bp.route('/')
@login_required
def pos_dashboard():
    """POS Dashboard - main entry point for the POS system"""
    
    # Get recent transactions for this user
    recent_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type.in_([TransactionType.PAYMENT, TransactionType.PAYOUT])
    ).order_by(Transaction.created_at.desc()).limit(5).all()
    
    # Calculate total amounts
    total_payments = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == TransactionType.PAYMENT,
        Transaction.status == TransactionStatus.COMPLETED
    ).with_entities(db.func.sum(Transaction.amount)).scalar() or 0
    
    total_payouts = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == TransactionType.PAYOUT,
        Transaction.status == TransactionStatus.COMPLETED
    ).with_entities(db.func.sum(Transaction.amount)).scalar() or 0
    
    return render_template(
        'pos/dashboard.html',
        recent_transactions=recent_transactions,
        total_payments=total_payments,
        total_payouts=total_payouts
    )


@pos_bp.route('/accept-payment', methods=['GET', 'POST'])
@login_required
def accept_payment():
    """Accept a payment via credit card"""
    
    form = AcceptPaymentForm()
    
    if form.validate_on_submit():
        # Store transaction information
        transaction = create_transaction(
            transaction_type=TransactionType.PAYMENT,
            amount=form.amount.data,
            currency=form.currency.data,
            recipient_name=form.customer_name.data,
            description=form.description.data,
            metadata={
                'customer_email': form.customer_email.data,
                'payment_method': 'credit_card'
            }
        )
        
        # Redirect to checkout page
        return redirect(url_for('pos.checkout', transaction_id=transaction.transaction_id))
    
    return render_template('pos/accept_payment.html', form=form)


@pos_bp.route('/checkout/<transaction_id>')
@login_required
def checkout(transaction_id):
    """Checkout page for credit card payment"""
    
    # Get the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    # Only allow checkout for pending payments
    if transaction.status != TransactionStatus.PENDING:
        flash('This transaction has already been processed.', 'warning')
        return redirect(url_for('pos.pos_dashboard'))
    
    # Create a Stripe checkout session
    try:
        YOUR_DOMAIN = request.host_url.rstrip('/')
        
        # Handle currency conversion (Stripe doesn't support NVCT)
        display_currency = transaction.currency
        stripe_currency = transaction.currency
        
        # If currency is NVCT, use USD for Stripe but show NVCT on the interface
        if stripe_currency == 'NVCT':
            stripe_currency = 'USD'
        
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
            success_url=YOUR_DOMAIN + url_for('pos.payment_success', transaction_id=transaction.transaction_id),
            cancel_url=YOUR_DOMAIN + url_for('pos.payment_cancel', transaction_id=transaction.transaction_id),
            client_reference_id=transaction.transaction_id,
            customer_email=transaction.metadata.get('customer_email'),
            payment_intent_data={
                'description': transaction.description or f"Payment to {current_user.username}",
                'metadata': {
                    'transaction_id': transaction.transaction_id,
                    'display_currency': display_currency
                }
            }
        )
        
        # Update transaction with Stripe session ID
        transaction.metadata['stripe_session_id'] = checkout_session.id
        db.session.commit()
        
        return render_template(
            'pos/checkout.html',
            transaction=transaction,
            checkout_session=checkout_session,
            display_currency=display_currency,
            stripe_publishable_key=os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_dummy')
        )
        
    except stripe.error.StripeError as e:
        # Handle Stripe errors
        flash(f"Payment processing error: {str(e)}", 'danger')
        transaction.status = TransactionStatus.FAILED
        transaction.metadata['error'] = str(e)
        db.session.commit()
        return redirect(url_for('pos.pos_dashboard'))
    
    except Exception as e:
        # Handle other errors
        current_app.logger.error(f"Error creating checkout session: {str(e)}")
        flash("An unexpected error occurred. Please try again later.", 'danger')
        return redirect(url_for('pos.pos_dashboard'))


@pos_bp.route('/payment-success/<transaction_id>')
@login_required
def payment_success(transaction_id):
    """Payment success page"""
    
    # Get the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    # Update transaction status if it's still pending
    if transaction.status == TransactionStatus.PENDING:
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = datetime.utcnow()
        db.session.commit()
    
    return render_template('pos/payment_success.html', transaction=transaction)


@pos_bp.route('/payment-cancel/<transaction_id>')
@login_required
def payment_cancel(transaction_id):
    """Payment cancel page"""
    
    # Get the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    # Update transaction status to cancelled if it's still pending
    if transaction.status == TransactionStatus.PENDING:
        transaction.status = TransactionStatus.CANCELLED
        db.session.commit()
    
    return render_template('pos/payment_cancel.html', transaction=transaction)


@pos_bp.route('/send-payment', methods=['GET', 'POST'])
@login_required
def send_payment():
    """Send money to a credit card"""
    
    form = SendPaymentForm()
    
    if form.validate_on_submit():
        # In a real implementation, you would integrate with your payment processor's API
        # to send money to a credit card (this is often called a "payout" or "transfer")
        
        # For demonstration purposes, we'll create a transaction record
        transaction = create_transaction(
            transaction_type=TransactionType.PAYOUT,
            amount=form.amount.data,
            currency=form.currency.data,
            recipient_name=form.recipient_name.data,
            description=form.description.data,
            metadata={
                'recipient_email': form.recipient_email.data,
                'card_last4': form.card_number.data,
                'payment_method': 'credit_card'
            },
            status=TransactionStatus.COMPLETED  # Simulate immediate completion
        )
        
        # In a real implementation, you would check the status of the payout
        # and update the transaction status accordingly
        
        flash('Payment sent successfully!', 'success')
        return redirect(url_for('pos.send_payment_success', transaction_id=transaction.transaction_id))
    
    return render_template('pos/send_payment.html', form=form)


@pos_bp.route('/send-payment-success/<transaction_id>')
@login_required
def send_payment_success(transaction_id):
    """Send payment success page"""
    
    # Get the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    return render_template('pos/send_payment_success.html', transaction=transaction)


@pos_bp.route('/transactions')
@login_required
def transactions():
    """View all POS transactions"""
    
    # Get all POS transactions for this user
    transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type.in_([TransactionType.PAYMENT, TransactionType.PAYOUT])
    ).order_by(Transaction.created_at.desc()).all()
    
    return render_template('pos/transactions.html', transactions=transactions)


@pos_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Webhook endpoint for Stripe events"""
    
    try:
        # Get the event data
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get('Stripe-Signature')
        
        # Verify the event
        # In production, you would set STRIPE_WEBHOOK_SECRET in your environment
        webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            # Invalid payload
            raise BadRequest(f"Invalid payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            raise BadRequest(f"Invalid signature: {str(e)}")
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Get the transaction ID from the client reference ID
            transaction_id = session.get('client_reference_id')
            if transaction_id:
                # Update the transaction status
                transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
                if transaction:
                    transaction.status = TransactionStatus.COMPLETED
                    transaction.completed_at = datetime.utcnow()
                    transaction.metadata['payment_intent'] = session.get('payment_intent')
                    transaction.metadata['stripe_customer'] = session.get('customer')
                    db.session.commit()
        
        return jsonify(success=True)
    
    except Exception as e:
        current_app.logger.error(f"Error processing webhook: {str(e)}")
        raise InternalServerError(f"Error processing webhook: {str(e)}")


# Register routes with the application
def register_pos_routes(app):
    """Register POS routes with the application"""
    app.register_blueprint(pos_bp)
    current_app.logger.info("POS Payment routes registered successfully")
