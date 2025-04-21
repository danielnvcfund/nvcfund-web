import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, session, abort, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user, login_required

import auth
import high_availability
from forms import (
    LoginForm, RegistrationForm, RequestResetForm, ResetPasswordForm, ForgotUsernameForm,
    PaymentForm, TransferForm, BlockchainTransactionForm, FinancialInstitutionForm, PaymentGatewayForm,
    InvitationForm, AcceptInvitationForm
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

# Web Routes for User Interface
@app.route('/')
def index():
    """Homepage route"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
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
        
        # Generate JWT token for API access
        token = generate_jwt_token(user.id)
        
        flash(f'Welcome back, {user.username}!', 'success')
        
        # Get the destination URL
        next_page = request.args.get('next')
        redirect_url = next_page if next_page else url_for('dashboard')
        
        # Return the token storage page which will store the token and redirect
        return render_template('store_token.html', jwt_token=token, redirect_url=redirect_url)
    
    # If there were form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # For GET request or form validation failed, show login form
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    """User logout route"""
    session.clear()
    flash('You have been logged out', 'info')
    
    # Use the clear_token template to remove JWT tokens from browser storage
    return render_template('clear_token.html', redirect_url=url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Register user
        user, error = register_user(form.username.data, form.email.data, form.password.data)
        
        if error:
            flash(error, 'danger')
            return render_template('login.html', register=True, form=form)
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    # If there were form validation errors or this is a GET request
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # For compatibility with the current login.html template, we still use register=True
    # but in the future, we can pass the form object directly
    return render_template('login.html', register=True, form=form)

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_request():
    """Route for requesting a password reset"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    form = RequestResetForm()
    
    if form.validate_on_submit():
        # Find user by email
        user = User.query.filter_by(email=form.email.data).first()
        
        # Generate reset token
        token = generate_reset_token(user)
        
        # Here you would typically send an email with the reset token
        # For now, we'll just display it in a flash message for testing
        reset_url = url_for('reset_password', token=token, _external=True)
        
        flash(f'A password reset link has been sent to your email. For testing, use this link: {reset_url}', 'info')
        return redirect(url_for('login'))
    
    return render_template('reset_request.html', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Route for resetting password using a token"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    # Verify token and get user
    user = verify_reset_token(token)
    
    if not user:
        flash('Invalid or expired reset token', 'danger')
        return redirect(url_for('reset_request'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        # Update user's password
        user.set_password(form.password.data)
        db.session.commit()
        
        flash('Your password has been updated! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', form=form)

@app.route('/forgot_username', methods=['GET', 'POST'])
def forgot_username():
    """Route for recovering username"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    form = ForgotUsernameForm()
    
    if form.validate_on_submit():
        # Find user by email
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            # Here you would typically send an email with the username
            # For now, we'll just display it in a flash message for testing
            flash(f'Your username is: {user.username}', 'info')
        else:
            flash('No user found with that email address', 'danger')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_username.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard route"""
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in to access the dashboard', 'danger')
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    if not user:
        # If user doesn't exist in database, clear session and redirect to login
        session.clear()
        flash('User not found, please log in again', 'danger')
        return redirect(url_for('login'))
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=user_id)\
        .order_by(Transaction.created_at.desc())\
        .limit(5).all()
    
    # Get transaction analytics
    analytics = get_transaction_analytics(user_id, days=30)
    
    # Generate JWT token for API access if the user doesn't have one already
    jwt_token = generate_jwt_token(user_id)
    
    # Pre-serialize analytics data
    import json
    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            import decimal
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            return super(DecimalEncoder, self).default(obj)
    
    analytics_json = json.dumps(analytics, cls=DecimalEncoder) if analytics else '{}'
    
    # Create or get Ethereum address if missing
    if not user.ethereum_address:
        # Check if user has a blockchain account
        blockchain_account = BlockchainAccount.query.filter_by(user_id=user.id).first()
        
        if not blockchain_account:
            # Create a new account
            eth_address, private_key = generate_ethereum_account()
            if eth_address:
                blockchain_account = BlockchainAccount(
                    user_id=user.id,
                    eth_address=eth_address,
                    eth_private_key=private_key
                )
                db.session.add(blockchain_account)
                db.session.commit()
                
                # Update user object for template
                user.ethereum_address = eth_address
        else:
            # User has account but ethereum_address property is missing
            user.ethereum_address = blockchain_account.eth_address
    
    return render_template(
        'dashboard.html',
        user=user,
        recent_transactions=recent_transactions,
        analytics=analytics,
        analytics_json=analytics_json,
        jwt_token=jwt_token
    )

@app.route('/transactions')
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

@app.route('/transaction/<transaction_id>')
@login_required
def transaction_details(transaction_id):
    """Transaction details route"""
    user_id = session.get('user_id')
    
    # Get transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        flash('Transaction not found', 'danger')
        return redirect(url_for('transactions'))
    
    # Check if the transaction belongs to the user or user is admin
    if transaction.user_id != user_id and session.get('role') != UserRole.ADMIN.value:
        flash('You do not have permission to view this transaction', 'danger')
        return redirect(url_for('transactions'))
    
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

@app.route('/payment/new', methods=['GET', 'POST'])
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
                return redirect(url_for('transaction_details', transaction_id=result['transaction_id']))
        else:
            flash(f"Payment failed: {result.get('error', 'Unknown error')}", 'danger')
            return render_template('payment_form.html', form=form, user=user)
    
    # If there were form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # GET request or form validation failed, show payment form
    return render_template('payment_form.html', form=form, user=user)

@app.route('/financial_institutions')
@admin_required
def financial_institutions():
    """Financial institutions management route"""
    institutions = FinancialInstitution.query.all()
    return render_template(
        'financial_institutions.html',
        institutions=institutions,
        institution_types=FinancialInstitutionType
    )

@app.route('/financial_institution/new', methods=['GET', 'POST'])
@admin_required
def new_financial_institution():
    """Add new financial institution route"""
    form = FinancialInstitutionForm()
    
    if form.validate_on_submit():
        # Generate Ethereum address for the institution
        eth_address, _ = generate_ethereum_account()
        
        if not eth_address:
            flash('Failed to generate Ethereum address', 'danger')
            return redirect(url_for('financial_institutions'))
        
        # Create institution
        institution = FinancialInstitution(
            name=form.name.data,
            institution_type=FinancialInstitutionType[form.institution_type.data],
            api_endpoint=form.api_endpoint.data,
            api_key=form.api_key.data,
            ethereum_address=eth_address,
            is_active=form.is_active.data
        )
        
        db.session.add(institution)
        db.session.commit()
        
        flash('Financial institution added successfully', 'success')
        return redirect(url_for('financial_institutions'))
    
    # If there were form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # GET request or validation failed, show form
    return render_template('financial_institution_form.html', form=form, is_new=True)

@app.route('/financial_institution/<int:institution_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_financial_institution(institution_id):
    """Edit financial institution route"""
    institution = FinancialInstitution.query.get_or_404(institution_id)
    
    # Create form and populate with institution data
    form = FinancialInstitutionForm(obj=institution)
    
    # For the institution_type field, we need to provide the Enum name instead of value
    form.institution_type.data = institution.institution_type.name
    
    if form.validate_on_submit():
        # Update institution from form data
        form.populate_obj(institution)
        
        # Handle the institution_type specifically since it's an Enum
        institution.institution_type = FinancialInstitutionType[form.institution_type.data]
        institution.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Financial institution updated successfully', 'success')
        return redirect(url_for('financial_institutions'))
    
    # If there were form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # GET request or validation failed, show form
    return render_template('financial_institution_form.html', form=form, is_new=False)

@app.route('/payment_gateways')
@admin_required
def payment_gateways():
    """Payment gateways management route"""
    gateways = PaymentGateway.query.all()
    return render_template(
        'payment_gateways.html',
        gateways=gateways,
        gateway_types=PaymentGatewayType
    )

@app.route('/payment_gateway/new', methods=['GET', 'POST'])
@admin_required
def new_payment_gateway():
    """Add new payment gateway route"""
    form = PaymentGatewayForm()
    
    if form.validate_on_submit():
        # Generate Ethereum address for the gateway
        eth_address, _ = generate_ethereum_account()
        
        if not eth_address:
            flash('Failed to generate Ethereum address', 'danger')
            return redirect(url_for('payment_gateways'))
        
        # Create gateway
        gateway = PaymentGateway(
            name=form.name.data,
            gateway_type=PaymentGatewayType[form.gateway_type.data],
            api_endpoint=form.api_endpoint.data,
            api_key=form.api_key.data,
            webhook_secret=form.webhook_secret.data,
            ethereum_address=eth_address,
            is_active=form.is_active.data
        )
        
        db.session.add(gateway)
        db.session.commit()
        
        flash('Payment gateway added successfully', 'success')
        return redirect(url_for('payment_gateways'))
    
    # If there were form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # GET request or validation failed, show form
    return render_template('payment_gateway_form.html', form=form, is_new=True)

@app.route('/payment_gateway/<int:gateway_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_payment_gateway(gateway_id):
    """Edit payment gateway route"""
    gateway = PaymentGateway.query.get_or_404(gateway_id)
    
    # Create form and populate with gateway data
    form = PaymentGatewayForm(obj=gateway)
    
    # For the gateway_type field, we need to provide the Enum name instead of value
    form.gateway_type.data = gateway.gateway_type.name
    
    if form.validate_on_submit():
        # Update gateway from form data
        form.populate_obj(gateway)
        
        # Handle the gateway_type specifically since it's an Enum
        gateway.gateway_type = PaymentGatewayType[form.gateway_type.data]
        gateway.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Payment gateway updated successfully', 'success')
        return redirect(url_for('payment_gateways'))
    
    # If there were form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # GET request or validation failed, show form
    return render_template('payment_gateway_form.html', form=form, is_new=False)

# First blockchain_status route now removed, using the more complete version below

@app.route('/user_management')
@admin_required
def user_management():
    """User management route"""
    users = User.query.all()
    return render_template(
        'user_management.html',
        users=users,
        roles=UserRole
    )

@app.route('/partner_integration')
@admin_required
def partner_integration():
    """Partner integration management route"""
    api_users = User.query.filter_by(role=UserRole.API).all()
    financial_institutions = FinancialInstitution.query.all()
    
    return render_template(
        'partner_integration.html',
        api_users=api_users,
        financial_institutions=financial_institutions
    )

@app.route('/user/<int:user_id>/update_role', methods=['POST'])
@admin_required
def update_user_role(user_id):
    """Update user role route"""
    user = User.query.get_or_404(user_id)
    role_name = request.form.get('role')
    
    if role_name:
        try:
            user.role = UserRole[role_name]
            db.session.commit()
            flash(f'Role for {user.username} updated successfully to {user.role.value}', 'success')
        except (KeyError, ValueError) as e:
            flash(f'Error updating role: {str(e)}', 'danger')
    else:
        flash('No role selected', 'danger')
    
    return redirect(url_for('user_management'))

@app.route('/user/<int:user_id>/toggle_status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status route"""
    user = User.query.get_or_404(user_id)
    
    # Toggle status
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}', 'success')
    
    return redirect(url_for('user_management'))

@app.route('/api_docs')
def api_docs():
    """API documentation route"""
    return render_template('api_docs.html')

@app.route('/terms')
def terms_of_service():
    """Terms of Service route"""
    return render_template('terms_of_service.html')

@app.route('/invitations', methods=['GET'])
@admin_required
def invitations():
    """Invitation management route"""
    # Get filter parameters
    status_filter = request.args.get('status')
    type_filter = request.args.get('type')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Create invitation form for the modal
    form = InvitationForm()
    
    # Get current time for template
    now = datetime.utcnow()
    
    # Initialize pagination dictionaries
    pending_pagination = {
        'current_page': page,
        'has_next': False,
        'has_prev': False,
        'pages': 1,
        'next_page': None,
        'prev_page': None
    }
    
    accepted_pagination = pending_pagination.copy()
    expired_pagination = pending_pagination.copy()
    
    # Get pending invitations
    pending_query = Invitation.query.filter_by(status=InvitationStatus.PENDING)
    if type_filter:
        pending_query = pending_query.filter_by(invitation_type=InvitationType[type_filter])
    pending_invitations = pending_query.order_by(Invitation.created_at.desc()).paginate(page=page, per_page=per_page)
    
    # Update pending pagination info
    pending_pagination['current_page'] = pending_invitations.page
    pending_pagination['has_next'] = pending_invitations.has_next
    pending_pagination['has_prev'] = pending_invitations.has_prev
    pending_pagination['pages'] = pending_invitations.pages
    pending_pagination['next_page'] = pending_invitations.next_num if pending_invitations.has_next else None
    pending_pagination['prev_page'] = pending_invitations.prev_num if pending_invitations.has_prev else None
    
    # Get accepted invitations
    accepted_query = Invitation.query.filter_by(status=InvitationStatus.ACCEPTED)
    if type_filter:
        accepted_query = accepted_query.filter_by(invitation_type=InvitationType[type_filter])
    accepted_invitations = accepted_query.order_by(Invitation.accepted_at.desc()).paginate(page=page, per_page=per_page)
    
    # Update accepted pagination info
    accepted_pagination['current_page'] = accepted_invitations.page
    accepted_pagination['has_next'] = accepted_invitations.has_next
    accepted_pagination['has_prev'] = accepted_invitations.has_prev
    accepted_pagination['pages'] = accepted_invitations.pages
    accepted_pagination['next_page'] = accepted_invitations.next_num if accepted_invitations.has_next else None
    accepted_pagination['prev_page'] = accepted_invitations.prev_num if accepted_invitations.has_prev else None
    
    # Get expired/revoked invitations
    expired_query = Invitation.query.filter(Invitation.status.in_([InvitationStatus.EXPIRED, InvitationStatus.REVOKED]))
    if type_filter:
        expired_query = expired_query.filter_by(invitation_type=InvitationType[type_filter])
    expired_invitations = expired_query.order_by(Invitation.updated_at.desc()).paginate(page=page, per_page=per_page)
    
    # Update expired pagination info
    expired_pagination['current_page'] = expired_invitations.page
    expired_pagination['has_next'] = expired_invitations.has_next
    expired_pagination['has_prev'] = expired_invitations.has_prev
    expired_pagination['pages'] = expired_invitations.pages
    expired_pagination['next_page'] = expired_invitations.next_num if expired_invitations.has_next else None
    expired_pagination['prev_page'] = expired_invitations.prev_num if expired_invitations.has_prev else None
    
    # Count pending invitations for badge
    pending_count = Invitation.query.filter_by(status=InvitationStatus.PENDING).count()
    
    # Helper function for templates
    def get_invitation_url(invitation):
        return url_for('register_with_invitation', invite_code=invitation.invite_code, _external=True)
    
    return render_template(
        'invitations.html',
        form=form,
        pending_invitations=pending_invitations.items,
        accepted_invitations=accepted_invitations.items,
        expired_invitations=expired_invitations.items,
        pending_pagination=pending_pagination,
        accepted_pagination=accepted_pagination,
        expired_pagination=expired_pagination,
        pending_count=pending_count,
        invitation_types=list(InvitationType),
        invitation_statuses=list(InvitationStatus),
        now=now,
        get_invitation_url=get_invitation_url
    )

@app.route('/invitations/create', methods=['POST'])
@admin_required
def create_invitation():
    """Create a new invitation"""
    form = InvitationForm()
    
    if form.validate_on_submit():
        # Create the invitation
        invitation, error = create_invitation(
            email=form.email.data,
            invitation_type=InvitationType[form.invitation_type.data],
            invited_by=current_user.id,
            organization_name=form.organization_name.data,
            message=form.message.data,
            expiration_days=form.expiration_days.data
        )
        
        if error:
            flash(f'Error creating invitation: {error}', 'danger')
            return redirect(url_for('invitations'))
        
        # Send invitation email
        email_sent = send_invitation_email(invitation)
        
        if email_sent:
            flash(f'Invitation sent to {invitation.email}', 'success')
        else:
            flash(f'Invitation created but email could not be sent to {invitation.email}. Copy the invitation link to share manually.', 'warning')
        
        return redirect(url_for('invitations'))
    
    # If validation fails, show errors
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('invitations'))

@app.route('/invitations/<int:invite_id>/revoke', methods=['POST'])
@admin_required
def revoke_invitation(invite_id):
    """Revoke an invitation"""
    success, error = revoke_invite(invite_id, current_user.id)
    
    if success:
        flash(f'Invitation successfully revoked', 'success')
    else:
        flash(f'Error revoking invitation: {error}', 'danger')
    
    return redirect(url_for('invitations'))

@app.route('/invitations/<int:invite_id>/resend', methods=['POST'])
@admin_required
def resend_invitation(invite_id):
    """Resend an invitation"""
    success, error, new_invitation = resend_invite(invite_id, current_user.id)
    
    if request.is_json:
        if success:
            # Send invitation email
            email_sent = send_invitation_email(new_invitation)
            
            if email_sent:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Invitation created but email could not be sent'})
        else:
            return jsonify({'success': False, 'error': error})
    
    if success:
        # Send invitation email
        email_sent = send_invitation_email(new_invitation)
        
        if email_sent:
            flash(f'Invitation resent to {new_invitation.email}', 'success')
        else:
            flash(f'New invitation created but email could not be sent to {new_invitation.email}. Copy the invitation link to share manually.', 'warning')
    else:
        flash(f'Error resending invitation: {error}', 'danger')
    
    return redirect(url_for('invitations'))

@app.route('/register/<invite_code>', methods=['GET', 'POST'])
def register_with_invitation(invite_code):
    """Register using an invitation link"""
    # Check if user is already logged in
    if current_user.is_authenticated:
        flash('You are already logged in. Please log out to accept a new invitation.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Get the invitation
    invitation = get_invitation_by_code(invite_code)
    
    if not invitation:
        flash('Invalid invitation code', 'danger')
        return redirect(url_for('index'))
    
    # Get the inviter
    inviter = User.query.get(invitation.invited_by)
    
    # Initialize the form
    form = AcceptInvitationForm()
    
    # If valid form submitted
    if form.validate_on_submit() and invitation.is_valid():
        # Register the user
        user, error = register_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            role=UserRole.USER  # Default role, can be updated based on invitation type
        )
        
        if error:
            flash(f'Error registering user: {error}', 'danger')
            return render_template('accept_invitation.html', invitation=invitation, inviter=inviter, form=form)
        
        # Process the invitation acceptance
        success, error = accept_invitation(invite_code, user)
        
        if error:
            flash(f'Error accepting invitation: {error}', 'danger')
            return render_template('accept_invitation.html', invitation=invitation, inviter=inviter, form=form)
        
        # Log in the user
        login_user(user)
        flash('Registration successful! Welcome to the NVC Banking Platform.', 'success')
        
        # Redirect to dashboard
        return redirect(url_for('dashboard'))
    
    # For GET requests or invalid form submission
    return render_template('accept_invitation.html', invitation=invitation, inviter=inviter, form=form)

@app.route('/error')
def error():
    """Error page route"""
    error_code = request.args.get('code', 500)
    error_message = request.args.get('message', 'An unexpected error occurred')
    
    return render_template('error.html', error_code=error_code, error_message=error_message)

# API Routes for Integration with nvcplatform.net
@app.route('/api/token', methods=['POST'], endpoint='api_get_token')
def get_token():
    """Get JWT token for API access"""
    if not request.is_json:
        return jsonify({'error': 'Missing JSON in request'}), 400
    
    username = request.json.get('username')
    password = request.json.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400
    
    user = authenticate_user(username, password)
    
    if not user:
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Create access token
    access_token = generate_jwt_token(user.id)
    
    return jsonify({
        'access_token': access_token,
        'user_id': user.id,
        'username': user.username
    }), 200

@app.route('/api/users', methods=['POST'], endpoint='api_create_user')
def create_user():
    """Create a new user via API"""
    if not request.is_json:
        return jsonify({'error': 'Missing JSON in request'}), 400
    
    username = request.json.get('username')
    email = request.json.get('email')
    password = request.json.get('password')
    
    if not username or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Register user with API role
    user, error = register_user(username, email, password, role=UserRole.API)
    
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'api_key': user.api_key,
        'ethereum_address': user.ethereum_address
    }), 201

@app.route('/api/transactions', methods=['GET'], endpoint='api_get_transactions')
@jwt_required
def get_transactions(user):
    """Get user transactions via API"""
    # Get filters from query parameters
    transaction_type = request.args.get('type')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = request.args.get('limit', 50)
    offset = request.args.get('offset', 0)
    
    try:
        limit = int(limit)
        offset = int(offset)
    except ValueError:
        return jsonify({'error': 'Invalid limit or offset'}), 400
    
    # Base query
    query = Transaction.query.filter_by(user_id=user.id)
    
    # Apply filters
    if transaction_type:
        try:
            query = query.filter_by(transaction_type=TransactionType(transaction_type))
        except ValueError:
            return jsonify({'error': f'Invalid transaction type: {transaction_type}'}), 400
    
    if status:
        try:
            query = query.filter_by(status=TransactionStatus(status))
        except ValueError:
            return jsonify({'error': f'Invalid status: {status}'}), 400
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Transaction.created_at >= start_date_obj)
        except ValueError:
            return jsonify({'error': f'Invalid start date format: {start_date}'}), 400
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            end_date_obj = end_date_obj + timedelta(days=1)  # Include the end date
            query = query.filter(Transaction.created_at <= end_date_obj)
        except ValueError:
            return jsonify({'error': f'Invalid end date format: {end_date}'}), 400
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination
    transactions = query.order_by(Transaction.created_at.desc())\
        .limit(limit).offset(offset).all()
    
    # Format response
    result = []
    for tx in transactions:
        result.append({
            'id': tx.id,
            'transaction_id': tx.transaction_id,
            'amount': tx.amount,
            'currency': tx.currency,
            'type': tx.transaction_type.value,
            'status': tx.status.value,
            'description': tx.description,
            'eth_transaction_hash': tx.eth_transaction_hash,
            'created_at': tx.created_at.isoformat(),
            'updated_at': tx.updated_at.isoformat()
        })
    
    return jsonify({
        'transactions': result,
        'total': total_count,
        'limit': limit,
        'offset': offset
    }), 200

@app.route('/api/transactions/<transaction_id>', methods=['GET'], endpoint='api_get_transaction')
@jwt_required
def get_transaction(user, transaction_id):
    """Get transaction details via API"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    # Check if the transaction belongs to the user
    if transaction.user_id != user.id:
        return jsonify({'error': 'You do not have permission to view this transaction'}), 403
    
    # Get blockchain transaction if available
    blockchain_tx_data = None
    if transaction.eth_transaction_hash:
        blockchain_tx = BlockchainTransaction.query.filter_by(eth_tx_hash=transaction.eth_transaction_hash).first()
        
        if blockchain_tx:
            blockchain_tx_data = {
                'eth_tx_hash': blockchain_tx.eth_tx_hash,
                'from_address': blockchain_tx.from_address,
                'to_address': blockchain_tx.to_address,
                'amount': blockchain_tx.amount,
                'gas_used': blockchain_tx.gas_used,
                'gas_price': blockchain_tx.gas_price,
                'block_number': blockchain_tx.block_number,
                'status': blockchain_tx.status,
                'created_at': blockchain_tx.created_at.isoformat()
            }
        else:
            # Try to get from blockchain
            blockchain_tx_data = get_transaction_status(transaction.eth_transaction_hash)
    
    result = {
        'id': transaction.id,
        'transaction_id': transaction.transaction_id,
        'user_id': transaction.user_id,
        'amount': transaction.amount,
        'currency': transaction.currency,
        'type': transaction.transaction_type.value,
        'status': transaction.status.value,
        'description': transaction.description,
        'eth_transaction_hash': transaction.eth_transaction_hash,
        'institution_id': transaction.institution_id,
        'gateway_id': transaction.gateway_id,
        'created_at': transaction.created_at.isoformat(),
        'updated_at': transaction.updated_at.isoformat(),
        'blockchain_transaction': blockchain_tx_data
    }
    
    return jsonify(result), 200

@app.route('/api/payments', methods=['POST'], endpoint='api_create_payment')
@jwt_required
def create_payment(user):
    """Create a new payment via API"""
    if not request.is_json:
        return jsonify({'error': 'Missing JSON in request'}), 400
    
    # Validate required fields
    required_fields = ['gateway_id', 'amount', 'currency', 'description']
    optional_fields = {'metadata': None}
    
    valid, data = validate_api_request(request.json, required_fields, optional_fields)
    
    if not valid:
        return jsonify({'error': data}), 400
    
    try:
        gateway_id = int(data['gateway_id'])
        amount = float(data['amount'])
    except ValueError:
        return jsonify({'error': 'Invalid gateway_id or amount'}), 400
    
    # Get gateway handler
    try:
        gateway_handler = get_gateway_handler(gateway_id)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    # Process payment
    result = gateway_handler.process_payment(
        amount,
        data['currency'],
        data['description'],
        user.id,
        data['metadata']
    )
    
    if result.get('success'):
        # Return appropriate response based on gateway
        response = {
            'success': True,
            'transaction_id': result['transaction_id']
        }
        
        # Add gateway-specific fields
        if 'hosted_url' in result:  # Coinbase
            response['hosted_url'] = result['hosted_url']
            response['charge_id'] = result['charge_id']
        elif 'approval_url' in result:  # PayPal
            response['approval_url'] = result['approval_url']
            response['paypal_order_id'] = result['paypal_order_id']
        elif 'client_secret' in result:  # Stripe
            response['client_secret'] = result['client_secret']
            response['payment_intent_id'] = result['payment_intent_id']
        
        return jsonify(response), 201
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Unknown error')
        }), 400

@app.route('/api/payments/<transaction_id>/status', methods=['GET'], endpoint='api_get_payment_status')
@jwt_required
def get_payment_status(user, transaction_id):
    """Get payment status via API"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    # Check if the transaction belongs to the user
    if transaction.user_id != user.id:
        return jsonify({'error': 'You do not have permission to view this transaction'}), 403
    
    # Check if it's a payment transaction
    if transaction.transaction_type != TransactionType.PAYMENT:
        return jsonify({'error': 'Not a payment transaction'}), 400
    
    # Get gateway handler
    if not transaction.gateway_id:
        return jsonify({'error': 'No payment gateway associated with this transaction'}), 400
    
    try:
        gateway_handler = get_gateway_handler(transaction.gateway_id)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    # Check payment status
    result = gateway_handler.check_payment_status(transaction_id)
    
    if result.get('success'):
        return jsonify(result), 200
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Unknown error')
        }), 400

@app.route('/api/transfers', methods=['POST'], endpoint='api_create_transfer')
@jwt_required
def create_transfer(user):
    """Create a new transfer via API"""
    if not request.is_json:
        return jsonify({'error': 'Missing JSON in request'}), 400
    
    # Validate required fields
    required_fields = ['institution_id', 'amount', 'currency', 'description']
    optional_fields = {'recipient_info': None}
    
    valid, data = validate_api_request(request.json, required_fields, optional_fields)
    
    if not valid:
        return jsonify({'error': data}), 400
    
    try:
        institution_id = int(data['institution_id'])
        amount = float(data['amount'])
    except ValueError:
        return jsonify({'error': 'Invalid institution_id or amount'}), 400
    
    # Get institution handler
    try:
        institution_handler = get_institution_handler(institution_id)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    # Initiate transfer
    result = institution_handler.initiate_transfer(
        amount,
        data['currency'],
        data['description'],
        user.id,
        data['recipient_info']
    )
    
    if result.get('success'):
        return jsonify({
            'success': True,
            'transaction_id': result['transaction_id'],
            'transfer_id': result.get('transfer_id'),
            'status': result.get('status'),
            'amount': result['amount'],
            'currency': result['currency']
        }), 201
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Unknown error')
        }), 400

@app.route('/api/transfers/<transaction_id>/status', methods=['GET'], endpoint='api_get_transfer_status')
@jwt_required
def get_transfer_status(user, transaction_id):
    """Get transfer status via API"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    # Check if the transaction belongs to the user
    if transaction.user_id != user.id:
        return jsonify({'error': 'You do not have permission to view this transaction'}), 403
    
    # Check if it's a transfer transaction
    if transaction.transaction_type != TransactionType.TRANSFER:
        return jsonify({'error': 'Not a transfer transaction'}), 400
    
    # Get institution handler
    if not transaction.institution_id:
        return jsonify({'error': 'No financial institution associated with this transaction'}), 400
    
    try:
        institution_handler = get_institution_handler(transaction.institution_id)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    # Check transfer status
    result = institution_handler.check_transfer_status(transaction_id)
    
    if result.get('success'):
        return jsonify(result), 200
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Unknown error')
        }), 400

@app.route('/api/blockchain/transactions', methods=['POST'], endpoint='api_create_blockchain_transaction')
@jwt_required
def create_blockchain_transaction(user):
    """Create a new blockchain transaction via API"""
    if not request.is_json:
        return jsonify({'error': 'Missing JSON in request'}), 400
    
    # Validate required fields
    required_fields = ['to_address', 'amount', 'description']
    optional_fields = {'use_contract': False}
    
    valid, data = validate_api_request(request.json, required_fields, optional_fields)
    
    if not valid:
        return jsonify({'error': data}), 400
    
    try:
        amount = float(data['amount'])
    except ValueError:
        return jsonify({'error': 'Invalid amount'}), 400
    
    # Validate Ethereum address
    if not validate_ethereum_address(data['to_address']):
        return jsonify({'error': 'Invalid Ethereum address'}), 400
    
    # Create transaction record
    transaction_id = generate_transaction_id()
    
    transaction = Transaction(
        transaction_id=transaction_id,
        user_id=user.id,
        amount=amount,
        currency='ETH',
        transaction_type=TransactionType.SETTLEMENT,
        status=TransactionStatus.PENDING,
        description=data['description'],
        created_at=datetime.utcnow()
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    # Send Ethereum transaction
    if data['use_contract']:
        tx_hash = settle_payment_via_contract(
            user.ethereum_address,
            data['to_address'],
            amount,
            user.ethereum_private_key,
            transaction.id
        )
    else:
        tx_hash = send_ethereum_transaction(
            user.ethereum_address,
            data['to_address'],
            amount,
            user.ethereum_private_key,
            transaction.id
        )
    
    if tx_hash:
        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'eth_transaction_hash': tx_hash,
            'amount': amount,
            'to_address': data['to_address']
        }), 201
    else:
        # Transaction was already created, but blockchain transaction failed
        transaction.status = TransactionStatus.FAILED
        db.session.commit()
        
        return jsonify({
            'success': False,
            'error': 'Failed to send Ethereum transaction',
            'transaction_id': transaction_id
        }), 400

@app.route('/api/blockchain/balances', methods=['GET'], endpoint='api_get_blockchain_balance')
@jwt_required
def get_blockchain_balance(user):
    """Get Ethereum balance via API"""
    from web3 import Web3, HTTPProvider
    
    # Get address from query parameters or use user's address
    address = request.args.get('address')
    if not address or address.strip() == "":
        # Use the authenticated user's address if none specified
        address = user.ethereum_address
    
    if not address or address == "None" or address == "null" or address == "undefined" or address.strip() == "":
        return jsonify({
            'success': False,
            'error': 'No Ethereum address available'
        }), 400
    
    # Initialize Web3
    eth_node_url = os.environ.get("ETHEREUM_NODE_URL", f"https://sepolia.infura.io/v3/{os.environ.get('INFURA_PROJECT_ID')}")
    web3 = Web3(HTTPProvider(eth_node_url))
    
    # Ensure address is checksummed
    try:
        if not web3.is_address(address):
            return jsonify({
                'success': False,
                'error': f'Invalid Ethereum address format: {address}'
            }), 400
            
        checksummed_address = web3.to_checksum_address(address)
        
        # Get Ethereum balance
        balance_wei = web3.eth.get_balance(checksummed_address)
        balance_eth = web3.from_wei(balance_wei, 'ether')
        
        return jsonify({
            'success': True,
            'address': checksummed_address,
            'balance_eth': float(balance_eth),
            'balance_wei': int(balance_wei)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

# Webhook routes for payment gateways
@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    """Webhook handler for Stripe"""
    payload = request.get_data()
    signature = request.headers.get('Stripe-Signature')
    
    if not payload or not signature:
        return jsonify({'error': 'Missing payload or signature'}), 400
    
    # Get gateway with Stripe type
    gateway = PaymentGateway.query.filter_by(gateway_type=PaymentGatewayType.STRIPE).first()
    
    if not gateway:
        return jsonify({'error': 'Stripe gateway not configured'}), 400
    
    # Verify webhook signature
    import stripe
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, gateway.webhook_secret
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        transaction_id = payment_intent['metadata'].get('transaction_id')
        
        if transaction_id:
            transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
            
            if transaction:
                transaction.status = TransactionStatus.COMPLETED
                db.session.commit()
                
                # Log successful payment
                logger.info(f"Payment succeeded for transaction {transaction_id}")
    
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        transaction_id = payment_intent['metadata'].get('transaction_id')
        
        if transaction_id:
            transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
            
            if transaction:
                transaction.status = TransactionStatus.FAILED
                db.session.commit()
                
                # Log failed payment
                logger.info(f"Payment failed for transaction {transaction_id}")
    
    return jsonify({'success': True}), 200

@app.route('/webhooks/paypal', methods=['POST'])
def paypal_webhook():
    """Webhook handler for PayPal"""
    if not request.is_json:
        return jsonify({'error': 'Missing JSON in request'}), 400
    
    event_type = request.json.get('event_type')
    resource = request.json.get('resource', {})
    
    if not event_type:
        return jsonify({'error': 'Missing event type'}), 400
    
    # Get gateway with PayPal type
    gateway = PaymentGateway.query.filter_by(gateway_type=PaymentGatewayType.PAYPAL).first()
    
    if not gateway:
        return jsonify({'error': 'PayPal gateway not configured'}), 400
    
    # Verify webhook signature
    webhook_id = request.headers.get('Paypal-Transmission-Id')
    if not webhook_id:
        return jsonify({'error': 'Missing webhook ID'}), 400
    
    # Handle the event
    if event_type == 'PAYMENT.CAPTURE.COMPLETED':
        # Get custom ID (our transaction ID)
        custom_id = resource.get('custom_id')
        
        if custom_id:
            transaction = Transaction.query.filter_by(transaction_id=custom_id).first()
            
            if transaction:
                transaction.status = TransactionStatus.COMPLETED
                db.session.commit()
                
                # Log successful payment
                logger.info(f"PayPal payment completed for transaction {custom_id}")
    
    elif event_type == 'PAYMENT.CAPTURE.DENIED':
        # Get custom ID (our transaction ID)
        custom_id = resource.get('custom_id')
        
        if custom_id:
            transaction = Transaction.query.filter_by(transaction_id=custom_id).first()
            
            if transaction:
                transaction.status = TransactionStatus.FAILED
                db.session.commit()
                
                # Log failed payment
                logger.info(f"PayPal payment denied for transaction {custom_id}")
    
    return jsonify({'success': True}), 200

@app.route('/webhooks/coinbase', methods=['POST'])
def coinbase_webhook():
    """Webhook handler for Coinbase"""
    payload = request.get_data()
    signature = request.headers.get('X-CC-Webhook-Signature')
    
    if not payload or not signature:
        return jsonify({'error': 'Missing payload or signature'}), 400
    
    # Get gateway with Coinbase type
    gateway = PaymentGateway.query.filter_by(gateway_type=PaymentGatewayType.COINBASE).first()
    
    if not gateway:
        return jsonify({'error': 'Coinbase gateway not configured'}), 400
    
    # Verify webhook signature
    import hmac
    import hashlib
    
    expected_signature = hmac.new(
        gateway.webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature):
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Parse the payload
    if not request.is_json:
        return jsonify({'error': 'Invalid payload format'}), 400
    
    event = request.json
    
    # Handle the event
    if event['type'] == 'charge:confirmed':
        # Get metadata (our transaction ID)
        metadata = event['data']['metadata']
        transaction_id = metadata.get('transaction_id')
        
        if transaction_id:
            transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
            
            if transaction:
                transaction.status = TransactionStatus.COMPLETED
                
                # Try to extract blockchain transaction hash
                payments = event['data'].get('payments', [])
                for payment in payments:
                    if payment['network'] == 'ethereum':
                        transaction.eth_transaction_hash = payment['transaction_id']
                        break
                
                db.session.commit()
                
                # Log successful payment
                logger.info(f"Coinbase payment confirmed for transaction {transaction_id}")
    
    elif event['type'] == 'charge:failed':
        # Get metadata (our transaction ID)
        metadata = event['data']['metadata']
        transaction_id = metadata.get('transaction_id')
        
        if transaction_id:
            transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
            
            if transaction:
                transaction.status = TransactionStatus.FAILED
                db.session.commit()
                
                # Log failed payment
                logger.info(f"Coinbase payment failed for transaction {transaction_id}")
    
    return jsonify({'success': True}), 200

@app.route('/blockchain')
@login_required
def blockchain_status():
    """Blockchain status and management page"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Initialize connection status
    try:
        web3 = init_web3()
        connected = web3 is not None and web3.is_connected()
    except Exception as e:
        logger.error(f"Error initializing web3: {str(e)}")
        web3 = None
        connected = False
    
    if connected:
        try:
            # Get current block
            current_block = web3.eth.block_number
            
            # Get network name
            chain_id = web3.eth.chain_id
            network_map = {
                1: "Ethereum Mainnet",
                3: "Ropsten Testnet",
                4: "Rinkeby Testnet",
                5: "Goerli Testnet",
                42: "Kovan Testnet",
                11155111: "Sepolia Testnet"
            }
            network_name = network_map.get(chain_id, f"Unknown Network (Chain ID: {chain_id})")
            
            # Get etherscan URL based on network
            etherscan_url_map = {
                1: "https://etherscan.io",
                3: "https://ropsten.etherscan.io",
                4: "https://rinkeby.etherscan.io",
                5: "https://goerli.etherscan.io",
                42: "https://kovan.etherscan.io",
                11155111: "https://sepolia.etherscan.io"
            }
            etherscan_url = etherscan_url_map.get(chain_id, "https://etherscan.io")
            
            connection_status = "Connected"
            connection_status_color = "success"
            connection_status_icon = "fa-check-circle"
        except Exception as e:
            # Web3 said it's connected but something went wrong
            connected = False
            current_block = "Unknown"
            network_name = "Unknown"
            etherscan_url = "https://etherscan.io"
            connection_status = f"Error: {str(e)}"
            connection_status_color = "danger"
            connection_status_icon = "fa-exclamation-circle"
    else:
        # Not connected - use fallback mode
        current_block = "Unknown"
        network_name = "Fallback Mode"
        etherscan_url = "https://etherscan.io"
        connection_status = "Disconnected - Using Offline Mode"
        connection_status_color = "warning"
        connection_status_icon = "fa-exclamation-triangle"
        
        # Create a fallback notice for the UI
        fallback_notice = {
            'type': 'warning',
            'title': 'Blockchain Connection Issue',
            'message': 'The application could not connect to the Ethereum network. You are currently in offline mode. ' + 
                       'Some blockchain features are limited but you can still view existing data. ' +
                       'Please contact your administrator to provide a valid Infura Project ID.'
        }
    
    # Get contracts
    settlement_contract = get_settlement_contract()
    multisig_contract = get_multisig_wallet()
    token_contract = get_nvc_token()
    
    # Get blockchain transactions for the user
    blockchain_transactions = BlockchainTransaction.query.filter_by(user_id=user_id).order_by(BlockchainTransaction.created_at.desc()).limit(10).all()
    
    # Get user's Ethereum address and balance
    blockchain_account = BlockchainAccount.query.filter_by(user_id=user_id).first()
    user_eth_address = None
    user_token_balance = 0
    
    if blockchain_account:
        user_eth_address = blockchain_account.eth_address
        if connected and token_contract and user_eth_address:
            try:
                user_token_balance = get_nvc_token_balance(user_eth_address)
            except Exception as e:
                logger.error(f"Error getting token balance: {str(e)}")
                user_token_balance = 0
    
    # Check if user is a multisig owner
    is_owner = False
    if multisig_contract and user_eth_address and connected:
        # In a real implementation, we would check if the user's address is in the owners list
        is_owner = False  # Placeholder
    
    # For admin users, get more data
    is_admin = session.get('role') == UserRole.ADMIN.value
    
    # Use notice for fallback/offline mode if not already defined
    if not connected and 'fallback_notice' not in locals():
        fallback_notice = {
            "title": "Blockchain Offline Mode",
            "message": "The system is currently unable to connect to the Ethereum network. Basic platform functionality is still available, but blockchain operations are limited. Transactions will be queued and processed when connectivity is restored. Please contact your administrator to provide a valid Infura Project ID.",
            "type": "warning"
        }
    
    # Render the blockchain status page
    return render_template(
        'blockchain_status.html',
        user=user,
        connected=connected,
        connection_status=connection_status,
        connection_status_color=connection_status_color,
        connection_status_icon=connection_status_icon,
        network_name=network_name,
        current_block=current_block,
        etherscan_url=etherscan_url,
        settlement_contract=settlement_contract,
        multisig_contract=multisig_contract,
        token_contract=token_contract,
        blockchain_transactions=blockchain_transactions,
        user_eth_address=user_eth_address,
        user_token_balance=user_token_balance,
        is_admin=is_admin,
        is_owner=is_owner,
        fallback_notice=fallback_notice,
        # These would come from the blockchain in a real implementation
        token_name="NVC Banking Token",
        token_symbol="NVC",
        token_total_supply=1000000,
        settlement_fee_percentage=1.0,
        settlement_contract_balance=0.0,
        multisig_required_confirmations=2,
        multisig_contract_balance=0.0,
        multisig_owners=[],
        settlements=[],
        multisig_transactions=[],
        token_transfers=[]
    )


# The HA dashboard route has been moved to routes/high_availability_routes.py

# Import our API routes
from routes.api.blockchain_routes import blockchain_api
from routes.api.blockchain_balance_routes import blockchain_balance_api

# Register API blueprints
app.register_blueprint(blockchain_api, url_prefix='/api/blockchain')
app.register_blueprint(blockchain_balance_api, url_prefix='/api/blockchain')

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """404 error handler"""
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    """500 error handler"""
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500

@app.errorhandler(403)
def forbidden(e):
    """403 error handler"""
    return render_template('error.html', error_code=403, error_message="Forbidden"), 403

@app.errorhandler(400)
def bad_request(e):
    """400 error handler"""
    return render_template('error.html', error_code=400, error_message="Bad request"), 400

# High Availability Dashboard route - redirect to the proper blueprint route
@app.route('/ha_dashboard')
def ha_dashboard_redirect():
    """Redirect to high-availability dashboard"""
    return redirect('/web/ha/dashboard')

# Direct access to HA dashboard for compatibility
@app.route('/ha/dashboard')
@login_required
@auth.admin_required
def ha_dashboard():
    """High-availability status and management dashboard"""
    try:
        user = current_user
        
        # Initialize the HA infrastructure if not already done
        if not high_availability._ha_initialized:
            high_availability.init_high_availability()
        
        # Get HA status
        ha_status = high_availability.get_ha_status()
        
        return render_template(
            'ha_dashboard.html',
            user=user,
            ha_status=ha_status
        )
    except Exception as e:
        logger.error(f"Error rendering HA dashboard: {str(e)}")
        return render_template(
            'error.html', 
            error_code=500, 
            error_message=f"Error loading HA dashboard: {str(e)}"
        ), 500
