"""
Main routes for the NVC Banking Platform
Contains all the primary web interface routes
"""
import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, abort, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user, login_required

import auth
import high_availability
from forms import (
    LoginForm, RegistrationForm, RequestResetForm, ResetPasswordForm, ForgotUsernameForm,
    PaymentForm, TransferForm, BlockchainTransactionForm, FinancialInstitutionForm, PaymentGatewayForm,
    InvitationForm, AcceptInvitationForm, TestPaymentForm
)
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import (
    User, UserRole, Transaction, TransactionStatus, TransactionType,
    FinancialInstitution, FinancialInstitutionType,
    PaymentGateway, PaymentGatewayType, SmartContract, BlockchainTransaction,
    BlockchainAccount, Invitation, InvitationType, InvitationStatus, 
    AssetManager, BusinessPartner, PartnerType, Webhook
)
from auth import (
    login_required, admin_required, api_key_required, authenticate_user,
    register_user, generate_jwt_token, verify_reset_token, generate_reset_token
)
from blockchain import (
    send_ethereum_transaction, settle_payment_via_contract,
    get_transaction_status, init_web3, get_settlement_contract, 
    get_multisig_wallet, get_nvc_token
)
from blockchain_utils import generate_ethereum_account
from payment_gateways import get_gateway_handler
from financial_institutions import get_institution_handler
from invitations import (
    create_invitation, get_invitation_by_code, accept_invitation,
    revoke_invitation as revoke_invite, resend_invitation as resend_invite,
    get_invitation_url, send_invitation_email
)
from utils import (
    generate_transaction_id, generate_api_key, format_currency,
    calculate_transaction_fee, get_transaction_analytics,
    check_pending_transactions, validate_ethereum_address,
    validate_api_request
)

logger = logging.getLogger(__name__)

# Create main blueprint
main = Blueprint('main', __name__)

# Web Routes for User Interface
@main.route('/')
def index():
    """Homepage route"""
    return render_template('index.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
        
    form = LoginForm()
    
    if form.validate_on_submit():
        user = authenticate_user(form.username.data, form.password.data)
        
        if not user:
            flash('Invalid username or password', 'danger')
            return render_template('login.html', form=form)
        
        # Set user session
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role.value
        
        flash(f'Welcome back, {user.username}!', 'success')
        
        # Redirect to next parameter or dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        return redirect(url_for('main.dashboard'))
    
    # If there were form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # For GET request or form validation failed, show login form
    return render_template('login.html', form=form)

@main.route('/logout')
def logout():
    """User logout route"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

@main.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
        
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Register user
        user, error = register_user(form.username.data, form.email.data, form.password.data)
        
        if error:
            flash(error, 'danger')
            return render_template('login.html', register=True, form=form)
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('main.login'))
    
    # If there were form validation errors or this is a GET request
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # For compatibility with the current login.html template, we still use register=True
    # but in the future, we can pass the form object directly
    return render_template('login.html', register=True, form=form)

@main.route('/reset_password_request', methods=['GET', 'POST'])
def reset_request():
    """Route for requesting a password reset"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    form = RequestResetForm()
    
    if form.validate_on_submit():
        # Find user by email
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            # Generate reset token and send email (email sent inside generate_reset_token)
            token = generate_reset_token(user)
            
            if token:
                flash('A password reset link has been sent to your email address', 'success')
            else:
                flash('There was an issue sending the reset email. Please try again later.', 'danger')
        else:
            # Don't reveal whether the email exists for security
            flash('If an account with that email exists, a password reset link will be sent', 'info')
            
        return redirect(url_for('main.login'))
    
    return render_template('reset_request.html', form=form)

@main.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Route for resetting password using a token"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    # Verify token and get user
    user = verify_reset_token(token)
    
    if not user:
        flash('Invalid or expired reset token', 'danger')
        return redirect(url_for('main.reset_request'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        # Update user's password
        user.set_password(form.password.data)
        db.session.commit()
        
        flash('Your password has been updated! You can now log in.', 'success')
        return redirect(url_for('main.login'))
    
    return render_template('reset_password.html', form=form)

@main.route('/forgot_username', methods=['GET', 'POST'])
def forgot_username():
    """Route for recovering username"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    form = ForgotUsernameForm()
    
    if form.validate_on_submit():
        # Find user by email
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            # Send email with username reminder
            from email_service import send_username_reminder_email
            success = send_username_reminder_email(user)
            
            if success:
                flash('Your username has been sent to your email address', 'success')
            else:
                flash('There was an issue sending the email. Please try again later.', 'danger')
        else:
            # Don't reveal whether the email exists for security
            flash('If an account with that email exists, a username reminder will be sent', 'info')
        
        return redirect(url_for('main.login'))
    
    return render_template('forgot_username.html', form=form)

@main.route('/dashboard')
@login_required
def dashboard():
    """User dashboard route"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access the dashboard', 'danger')
        return redirect(url_for('main.login'))
    
    user = User.query.get(user_id)
    if not user:
        # If user doesn't exist in database, clear session and redirect to login
        session.clear()
        flash('User not found, please log in again', 'danger')
        return redirect(url_for('main.login'))
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=user_id)\
        .order_by(Transaction.created_at.desc())\
        .limit(5).all()
    
    # Get transaction analytics
    analytics = get_transaction_analytics(user_id, days=30)
    
    return render_template(
        'dashboard.html',
        user=user,
        recent_transactions=recent_transactions,
        analytics=analytics
    )

@main.route('/transactions')
@login_required
def transactions():
    """Transaction history route"""
    user_id = session.get('user_id')
    
    # Get filters from query parameters
    transaction_type = request.args.get('type')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query
    query = Transaction.query.filter_by(user_id=user_id)
    
    # Apply filters
    if transaction_type:
        try:
            query = query.filter_by(transaction_type=TransactionType(transaction_type))
        except ValueError:
            pass
    
    if status:
        try:
            query = query.filter_by(status=TransactionStatus(status))
        except ValueError:
            pass
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Transaction.created_at >= start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            end_date_obj = end_date_obj + timedelta(days=1)  # Include the end date
            query = query.filter(Transaction.created_at <= end_date_obj)
        except ValueError:
            pass
    
    # Order by creation date (newest first)
    transactions = query.order_by(Transaction.created_at.desc()).all()
    
    return render_template(
        'transactions.html',
        transactions=transactions,
        transaction_types=TransactionType,
        transaction_statuses=TransactionStatus
    )

@main.route('/transaction/<transaction_id>')
@login_required
def transaction_details(transaction_id):
    """Transaction details route"""
    user_id = session.get('user_id')
    
    # Get transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        flash('Transaction not found', 'danger')
        return redirect(url_for('main.transactions'))
    
    # Check if the transaction belongs to the user or user is admin
    if transaction.user_id != user_id and session.get('role') != UserRole.ADMIN.value:
        flash('You do not have permission to view this transaction', 'danger')
        return redirect(url_for('main.transactions'))
    
    # Get blockchain transaction if available
    blockchain_tx = None
    if transaction.eth_transaction_hash:
        blockchain_tx = BlockchainTransaction.query.filter_by(eth_tx_hash=transaction.eth_transaction_hash).first()
        
        # If not in our database, try to get from blockchain
        if not blockchain_tx:
            blockchain_tx = get_transaction_status(transaction.eth_transaction_hash)
    
    return render_template(
        'transaction_details.html',
        transaction=transaction,
        blockchain_tx=blockchain_tx
    )

@main.route('/blockchain')
@login_required
def blockchain_status():
    """Blockchain status page"""
    # Get the Ethereum node connection status
    try:
        web3 = init_web3()
        node_info = {
            'connected': True,
            'network_id': web3.net.version if web3 else 'Unknown',
            'latest_block': web3.eth.block_number if web3 else 'Unknown',
            'gas_price': web3.from_wei(web3.eth.gas_price, 'gwei') if web3 else 'Unknown'
        }
    except Exception as e:
        node_info = {
            'connected': False,
            'error': str(e),
            'network_id': 'Unknown',
            'latest_block': 'Unknown',
            'gas_price': 'Unknown'
        }
    
    # Get smart contract info
    try:
        settlement_contract = get_settlement_contract()
        multisig_wallet = get_multisig_wallet()
        nvc_token = get_nvc_token()
        
        contract_info = {
            'settlement': {
                'deployed': settlement_contract is not None,
                'address': settlement_contract.address if settlement_contract else 'Not deployed'
            },
            'multisig': {
                'deployed': multisig_wallet is not None,
                'address': multisig_wallet.address if multisig_wallet else 'Not deployed'
            },
            'token': {
                'deployed': nvc_token is not None,
                'address': nvc_token.address if nvc_token else 'Not deployed'
            }
        }
    except Exception as e:
        contract_info = {
            'error': str(e),
            'settlement': {'deployed': False, 'address': 'Error'},
            'multisig': {'deployed': False, 'address': 'Error'},
            'token': {'deployed': False, 'address': 'Error'}
        }
    
    # Get recent blockchain transactions
    recent_transactions = BlockchainTransaction.query.order_by(BlockchainTransaction.created_at.desc()).limit(5).all()
    
    return render_template(
        'blockchain_status.html',
        node_info=node_info,
        contract_info=contract_info,
        recent_transactions=recent_transactions
    )

@main.route('/payment/new', methods=['GET', 'POST'])
@login_required
def new_payment():
    """New payment route"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Get available payment gateways
    gateways = PaymentGateway.query.filter_by(is_active=True).all()
    
    # Create form and populate gateway choices
    form = PaymentForm()
    form.gateway_id.choices = [(g.id, g.name) for g in gateways]
    
    if form.validate_on_submit():
        # Get gateway handler
        try:
            gateway_handler = get_gateway_handler(form.gateway_id.data)
        except ValueError as e:
            flash(str(e), 'danger')
            return render_template('payment_form.html', form=form, user=user)
        
        # Process payment
        result = gateway_handler.process_payment(
            float(form.amount.data), 
            form.currency.data, 
            form.description.data or 'Payment from nvcplatform.net', 
            user_id
        )
        
        if result.get('success'):
            flash('Payment initiated successfully', 'success')
            
            # Different gateways return different data
            if 'hosted_url' in result:  # Coinbase
                return redirect(result['hosted_url'])
            elif 'approval_url' in result:  # PayPal
                return redirect(result['approval_url'])
            elif 'client_secret' in result:  # Stripe
                return render_template(
                    'payment_confirm.html',
                    client_secret=result['client_secret'],
                    payment_intent_id=result['payment_intent_id'],
                    amount=float(form.amount.data),
                    currency=form.currency.data,
                    transaction_id=result['transaction_id']
                )
            else:
                # Generic success
                return redirect(url_for('main.transaction_details', transaction_id=result['transaction_id']))
        else:
            flash(f"Payment failed: {result.get('error', 'Unknown error')}", 'danger')
            return render_template('payment_form.html', form=form, user=user)
    
    # If there were form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # GET request or form validation failed, show payment form
    return render_template('payment_form.html', form=form, user=user, gateways=gateways)

@main.route('/api_docs')
def api_docs():
    """API documentation route"""
    return render_template('api_docs.html')
    
@main.route('/terms_of_service')
def terms_of_service():
    """Terms of service route"""
    return render_template('terms_of_service.html')

@main.route('/payments/return')
def payment_return():
    """Handle payment return from PayPal"""
    transaction_id = request.args.get('transaction_id')
    
    if not transaction_id:
        flash('Missing transaction ID', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    # Get transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        flash('Transaction not found', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    # Get gateway
    gateway = PaymentGateway.query.get(transaction.gateway_id)
    
    if not gateway or gateway.gateway_type != PaymentGatewayType.PAYPAL:
        flash('Invalid payment gateway', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    # Get gateway handler
    gateway_handler = get_gateway_handler(gateway.id)
    
    # Check payment status
    result = gateway_handler.check_payment_status(transaction_id)
    
    if result.get('success'):
        if result.get('internal_status') == TransactionStatus.COMPLETED.value:
            flash('Payment completed successfully', 'success')
        else:
            flash(f'Payment in progress: {result.get("status")}', 'info')
    else:
        flash(f'Error checking payment status: {result.get("error")}', 'warning')
    
    return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))

@main.route('/payments/cancel')
def payment_cancel():
    """Handle payment cancellation from PayPal"""
    transaction_id = request.args.get('transaction_id')
    
    if not transaction_id:
        flash('Missing transaction ID', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    # Get transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        flash('Transaction not found', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    # Update transaction status to canceled
    transaction.status = TransactionStatus.FAILED
    transaction.description = f"{transaction.description} (Canceled by user)"
    db.session.commit()
    
    flash('Payment was canceled', 'warning')
    return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
    
@main.route('/privacy_policy')
def privacy_policy():
    """Privacy policy route"""
    return render_template('privacy_policy.html')

@main.route('/payment/test', methods=['GET', 'POST'])
@login_required
@admin_required
def test_payment():
    """Test payment integration route - admin only"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Get available payment gateways
    gateways = PaymentGateway.query.filter_by(is_active=True).all()
    
    # Create form and populate gateway choices
    form = TestPaymentForm()
    form.gateway_id.choices = [(g.id, g.name) for g in gateways]
    
    # Get recent test transactions
    test_transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.description.like('%Test payment%')
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    
    if form.validate_on_submit():
        # Import the test payment handler to process the test payment
        from test_payment_handler import process_test_payment
        return process_test_payment(form, user_id)
    
    # If there were form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    return render_template('payment_test.html', form=form, user=user, test_transactions=test_transactions)