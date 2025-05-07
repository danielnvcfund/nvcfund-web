"""
POS (Point of Sale) Payment Routes
This module provides routes for processing credit card payments and payouts via Stripe.
"""
import os
import json
import logging
import stripe
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash
from flask_login import login_required, current_user
from werkzeug.exceptions import BadRequest
from app import db
from models import Transaction, TransactionStatus, TransactionType, PaymentGateway, PaymentGatewayType
from account_holder_models import AccountHolder, BankAccount, CurrencyType
from pos_payment_service import POSPaymentService
from forms import CreditCardPaymentForm, CreditCardPayoutForm

logger = logging.getLogger(__name__)

# Create a Blueprint for POS routes
pos_bp = Blueprint('pos', __name__, url_prefix='/pos')

# Initialize Stripe with the API key
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

@pos_bp.route('/', methods=['GET'])
@login_required
def pos_dashboard():
    """
    POS payment dashboard
    """
    # Get the current user's account holders
    account_holders = AccountHolder.query.filter_by(user_id=current_user.id).all()
    
    return render_template(
        'pos/dashboard.html',
        title='POS Payments',
        account_holders=account_holders
    )

@pos_bp.route('/accept-payment', methods=['GET', 'POST'])
@login_required
def accept_payment():
    """
    Render a form to accept a credit card payment
    """
    form = CreditCardPaymentForm()
    
    # Get the current user's account holders for the form
    account_holders = AccountHolder.query.filter_by(user_id=current_user.id).all()
    account_holder_choices = [(ah.id, ah.name) for ah in account_holders]
    form.account_holder_id.choices = account_holder_choices
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            amount = form.amount.data
            currency = form.currency.data
            description = form.description.data
            customer_email = form.customer_email.data
            account_holder_id = form.account_holder_id.data
            
            # Create a payment intent
            payment_intent = POSPaymentService.create_payment_intent(
                amount=amount,
                currency=currency,
                customer_email=customer_email,
                description=description,
                metadata={'account_holder_id': account_holder_id}
            )
            
            # Find the Stripe gateway
            gateway = PaymentGateway.query.filter_by(gateway_type=PaymentGatewayType.STRIPE).first()
            if not gateway:
                flash('Stripe payment gateway not configured', 'danger')
                return redirect(url_for('pos.accept_payment'))
            
            # Create a transaction from the payment intent
            transaction = POSPaymentService.create_transaction_from_payment_intent(
                payment_intent_id=payment_intent['id'],
                user_id=current_user.id,
                gateway_id=gateway.id,
                description=description
            )
            
            # Store the payment intent ID in session for the checkout page
            session['payment_intent_id'] = payment_intent['id']
            session['payment_intent_client_secret'] = payment_intent['client_secret']
            session['payment_amount'] = amount
            session['payment_currency'] = currency
            
            # Redirect to the checkout page
            return redirect(url_for('pos.checkout'))
            
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            flash(f'Error creating payment: {str(e)}', 'danger')
    
    return render_template(
        'pos/accept_payment.html',
        title='Accept Credit Card Payment',
        form=form,
        stripe_publishable_key=os.environ.get('STRIPE_PUBLISHABLE_KEY')
    )

@pos_bp.route('/checkout', methods=['GET'])
@login_required
def checkout():
    """
    Credit card checkout page
    """
    # Get payment intent details from session
    payment_intent_id = session.get('payment_intent_id')
    client_secret = session.get('payment_intent_client_secret')
    amount = session.get('payment_amount')
    currency = session.get('payment_currency')
    
    if not payment_intent_id or not client_secret:
        flash('Payment session expired or invalid', 'danger')
        return redirect(url_for('pos.accept_payment'))
    
    return render_template(
        'pos/checkout.html',
        title='Credit Card Checkout',
        payment_intent_id=payment_intent_id,
        client_secret=client_secret,
        amount=amount,
        currency=currency.upper(),
        stripe_publishable_key=os.environ.get('STRIPE_PUBLISHABLE_KEY')
    )

@pos_bp.route('/payment-success', methods=['GET'])
@login_required
def payment_success():
    """
    Payment success page
    """
    payment_intent_id = request.args.get('payment_intent')
    
    if not payment_intent_id:
        payment_intent_id = session.get('payment_intent_id')
        
    # Clear payment session data
    if 'payment_intent_id' in session:
        del session['payment_intent_id']
    if 'payment_intent_client_secret' in session:
        del session['payment_intent_client_secret']
    if 'payment_amount' in session:
        del session['payment_amount']
    if 'payment_currency' in session:
        del session['payment_currency']
    
    try:
        # Retrieve payment intent details if ID is provided
        payment_details = None
        if payment_intent_id:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            payment_details = {
                'id': intent.id,
                'amount': float(intent.amount) / 100,
                'currency': intent.currency.upper(),
                'status': intent.status
            }
            
            # Update transaction if needed
            transaction = Transaction.query.filter_by(external_id=payment_intent_id).first()
            if transaction and transaction.status != TransactionStatus.COMPLETED:
                transaction.status = TransactionStatus.COMPLETED
                db.session.commit()
        
        return render_template(
            'pos/payment_success.html',
            title='Payment Successful',
            payment_details=payment_details
        )
        
    except Exception as e:
        logger.error(f"Error retrieving payment details: {str(e)}")
        flash(f'Error retrieving payment details: {str(e)}', 'warning')
        return render_template(
            'pos/payment_success.html',
            title='Payment Successful',
            payment_details=None
        )

@pos_bp.route('/payment-cancel', methods=['GET'])
@login_required
def payment_cancel():
    """
    Payment cancellation page
    """
    payment_intent_id = session.get('payment_intent_id')
    
    # Clear payment session data
    if 'payment_intent_id' in session:
        del session['payment_intent_id']
    if 'payment_intent_client_secret' in session:
        del session['payment_intent_client_secret']
    if 'payment_amount' in session:
        del session['payment_amount']
    if 'payment_currency' in session:
        del session['payment_currency']
    
    # Cancel the payment intent if it exists
    if payment_intent_id:
        try:
            stripe.PaymentIntent.cancel(payment_intent_id)
            
            # Update transaction if needed
            transaction = Transaction.query.filter_by(external_id=payment_intent_id).first()
            if transaction:
                transaction.status = TransactionStatus.CANCELLED
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Error cancelling payment intent: {str(e)}")
    
    return render_template(
        'pos/payment_cancel.html',
        title='Payment Cancelled'
    )

@pos_bp.route('/send-payment', methods=['GET', 'POST'])
@login_required
def send_payment():
    """
    Render a form to send a payment to a credit card
    """
    form = CreditCardPayoutForm()
    
    # Get the current user's account holders for the form
    account_holders = AccountHolder.query.filter_by(user_id=current_user.id).all()
    
    # Populate account holder choices
    account_holder_choices = [(ah.id, ah.name) for ah in account_holders]
    form.account_holder_id.choices = account_holder_choices
    
    # Dynamically update accounts based on selected account holder
    if form.account_holder_id.data:
        account_holder = AccountHolder.query.get(form.account_holder_id.data)
        if account_holder:
            accounts = BankAccount.query.filter_by(account_holder_id=account_holder.id).all()
            form.account_id.choices = [(acc.id, f"{acc.account_number} ({acc.currency.value})") for acc in accounts]
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            account_holder_id = form.account_holder_id.data
            account_id = form.account_id.data
            amount = form.amount.data
            currency = form.currency.data
            recipient_name = form.recipient_name.data
            card_token = form.card_token.data  # This would come from Stripe.js
            description = form.description.data
            
            # Verify the account has sufficient funds
            account = BankAccount.query.get(account_id)
            if not account:
                flash('Invalid account selected', 'danger')
                return redirect(url_for('pos.send_payment'))
                
            if account.balance < float(amount):
                flash('Insufficient funds in the selected account', 'danger')
                return redirect(url_for('pos.send_payment'))
            
            # Create a transaction for the payout
            transaction = POSPaymentService.create_transaction_from_account(
                account_holder_id=account_holder_id,
                account_id=account_id,
                amount=amount,
                currency=currency,
                recipient_name=recipient_name,
                recipient_card_token=card_token,
                transaction_type=TransactionType.PAYOUT,
                description=description
            )
            
            # Create the payout to the credit card
            payout = POSPaymentService.create_payout(
                destination_card=card_token,
                amount=amount,
                currency=currency,
                description=description,
                metadata={'transaction_id': transaction.transaction_id}
            )
            
            # Update the transaction with the payout details
            transaction.external_id = payout['id']
            if payout['status'] == 'paid':
                transaction.status = TransactionStatus.COMPLETED
            db.session.commit()
            
            flash('Payment sent successfully', 'success')
            return redirect(url_for('pos.send_payment_success', transaction_id=transaction.transaction_id))
            
        except Exception as e:
            logger.error(f"Error sending payment: {str(e)}")
            flash(f'Error sending payment: {str(e)}', 'danger')
    
    return render_template(
        'pos/send_payment.html',
        title='Send Payment to Credit Card',
        form=form,
        stripe_publishable_key=os.environ.get('STRIPE_PUBLISHABLE_KEY')
    )

@pos_bp.route('/send-payment-success', methods=['GET'])
@login_required
def send_payment_success():
    """
    Payment sent success page
    """
    transaction_id = request.args.get('transaction_id')
    
    transaction = None
    if transaction_id:
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    return render_template(
        'pos/send_payment_success.html',
        title='Payment Sent Successfully',
        transaction=transaction
    )

@pos_bp.route('/transactions', methods=['GET'])
@login_required
def transactions():
    """
    View POS payment transactions
    """
    # Get all POS transactions for the current user
    transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type.in_([TransactionType.PAYMENT, TransactionType.PAYOUT])
    ).order_by(Transaction.created_at.desc()).all()
    
    return render_template(
        'pos/transactions.html',
        title='POS Transactions',
        transactions=transactions
    )

# Webhook endpoint for Stripe events
@pos_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Handle Stripe webhook events
    """
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    if not webhook_secret:
        logger.warning("Stripe webhook secret not configured")
    
    try:
        # Get the event payload and signature
        payload = request.data
        sig_header = request.headers.get('Stripe-Signature')
        
        try:
            # Verify the event using the webhook secret
            if webhook_secret:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
                event_data = event
            else:
                # If no webhook secret, use the JSON directly (less secure)
                event_data = json.loads(payload)
        except ValueError as e:
            # Invalid payload
            logger.error(f"Invalid Stripe webhook payload: {str(e)}")
            return jsonify(success=False, error="Invalid payload"), 400
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            logger.error(f"Invalid Stripe webhook signature: {str(e)}")
            return jsonify(success=False, error="Invalid signature"), 400
        
        # Process the webhook event
        result = POSPaymentService.process_payment_webhook(event_data)
        
        return jsonify(success=True, result=result)
        
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}")
        return jsonify(success=False, error=str(e)), 500

# API endpoints for JavaScript clients

@pos_bp.route('/api/create-payment-intent', methods=['POST'])
@login_required
def api_create_payment_intent():
    """
    API endpoint to create a payment intent
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['amount', 'currency']
        for field in required_fields:
            if field not in data:
                return jsonify(success=False, error=f"Missing required field: {field}"), 400
        
        # Create the payment intent
        payment_intent = POSPaymentService.create_payment_intent(
            amount=data['amount'],
            currency=data['currency'],
            customer_email=data.get('customer_email'),
            description=data.get('description'),
            metadata=data.get('metadata', {})
        )
        
        # Find the Stripe gateway
        gateway = PaymentGateway.query.filter_by(gateway_type=PaymentGatewayType.STRIPE).first()
        if not gateway:
            return jsonify(success=False, error="Stripe payment gateway not configured"), 500
        
        # Create a transaction from the payment intent
        transaction = POSPaymentService.create_transaction_from_payment_intent(
            payment_intent_id=payment_intent['id'],
            user_id=current_user.id,
            gateway_id=gateway.id,
            description=data.get('description')
        )
        
        return jsonify(
            success=True,
            client_secret=payment_intent['client_secret'],
            payment_intent_id=payment_intent['id'],
            transaction_id=transaction.transaction_id
        )
        
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        return jsonify(success=False, error=str(e)), 500

@pos_bp.route('/api/get-account-holders', methods=['GET'])
@login_required
def api_get_account_holders():
    """
    API endpoint to get account holders for the current user
    """
    try:
        account_holders = AccountHolder.query.filter_by(user_id=current_user.id).all()
        
        result = []
        for ah in account_holders:
            accounts = []
            for account in ah.accounts:
                accounts.append({
                    'id': account.id,
                    'account_number': account.account_number,
                    'currency': account.currency.value,
                    'balance': account.balance,
                    'account_type': account.account_type.value
                })
                
            result.append({
                'id': ah.id,
                'name': ah.name,
                'email': ah.email,
                'accounts': accounts
            })
        
        return jsonify(success=True, account_holders=result)
        
    except Exception as e:
        logger.error(f"Error getting account holders: {str(e)}")
        return jsonify(success=False, error=str(e)), 500

def register_pos_routes(app):
    """Register POS routes with the Flask app"""
    app.register_blueprint(pos_bp)
    logger.info("POS Payment routes registered successfully")