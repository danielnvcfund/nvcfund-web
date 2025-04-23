"""
Main routes for the NVC Banking Platform
Contains all the primary web interface routes
"""
import os
import json
import uuid
import logging
import subprocess
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, abort, current_app, send_file, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user, login_required

import auth
import high_availability
from forms import (
    LoginForm, RegistrationForm, RequestResetForm, ResetPasswordForm, ForgotUsernameForm,
    PaymentForm, TransferForm, BlockchainTransactionForm, FinancialInstitutionForm, PaymentGatewayForm,
    InvitationForm, AcceptInvitationForm, TestPaymentForm, BankTransferForm, LetterOfCreditForm,
    ClientRegistrationForm
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from app import db
from models import (
    User, UserRole, Transaction, TransactionStatus, TransactionType,
    FinancialInstitution, FinancialInstitutionType,
    PaymentGateway, PaymentGatewayType, SmartContract, BlockchainTransaction,
    BlockchainAccount, Invitation, InvitationType, InvitationStatus, 
    AssetManager, BusinessPartner, PartnerType, Webhook, FormData
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

@main.route('/nvctoken')
def nvc_token_economics():
    """NVC Token economics preview page"""
    return render_template('nvctoken_preview.html')
    
@main.route('/php-bridge-docs')
@login_required
def php_bridge_docs():
    """PHP API Bridge Documentation"""
    # Only admin users can access this page
    if session.get('role') != UserRole.ADMIN.value:
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    return render_template('api_bridge_docs.html')

@main.route('/nvctoken/pdf')
def nvc_token_economics_pdf():
    """NVC Token economics documentation in PDF format - generates a fresh PDF on demand"""
    from flask import current_app, send_file, flash
    import sys
    import os
    import subprocess
    import logging
    
    try:
        # Get paths for static directory and files
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        static_dir = os.path.join(base_dir, 'static', 'docs')
        html_path = os.path.join(static_dir, 'NVCTokenomics.html')
        pdf_path = os.path.join(static_dir, 'NVCTokenomics.pdf')
        pdf_script = os.path.join(static_dir, 'NVCTokenomics.pdf.py')
        
        # Ensure the PDF is freshly generated
        current_app.logger.info(f"Generating fresh PDF from {html_path}")
        
        # Run the external script to generate the PDF
        result = subprocess.run(
            [sys.executable, pdf_script], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode != 0:
            current_app.logger.error(f"PDF generation script failed: {result.stderr}")
            # Try direct command line approach with wkhtmltopdf
            try:
                subprocess.run(["wkhtmltopdf", html_path, pdf_path], check=True)
                current_app.logger.info("Generated PDF using wkhtmltopdf")
            except Exception as e:
                current_app.logger.error(f"wkhtmltopdf failed: {str(e)}")
        else:
            current_app.logger.info(f"PDF generation script output: {result.stdout}")
        
        # Check if the PDF was created
        if os.path.exists(pdf_path):
            # Return the PDF file
            return send_file(
                pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='NVCTokenomics.pdf'
            )
        else:
            current_app.logger.error("PDF file does not exist after generation attempt")
            raise FileNotFoundError("PDF file not found after generation attempt")
            
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        flash('Error generating PDF document. Please try again later.', 'danger')
        
    # If all else fails, redirect back to the HTML page
    return redirect('/static/docs/NVCTokenomics.html')
@main.route('/')
def index():
    """Homepage route"""
    return render_template('index.html')

@main.route('/quick-access')
def quick_access():
    """Quick access page for registration and documentation"""
    return render_template('quick_access.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    # Use Flask-Login's current_user to check if user is already logged in
    if current_user.is_authenticated:
        # Redirect based on role
        if current_user.role == UserRole.ADMIN:
            return redirect(url_for('web.main.admin_dashboard'))
        else:
            return redirect(url_for('web.main.dashboard'))
        
    form = LoginForm()
    
    if form.validate_on_submit():
        user = authenticate_user(form.username.data, form.password.data)
        
        if not user:
            flash('Invalid username or password', 'danger')
            return render_template('login.html', form=form)
        
        # Use Flask-Login's login_user function
        from flask_login import login_user
        login_user(user, remember=True)
        
        # Make sure session is permanent
        session.permanent = True
        
        # Also maintain session for backward compatibility
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role.value
        
        # Generate JWT token for API access
        from auth import generate_jwt_token
        jwt_token = generate_jwt_token(user.id)
        session['jwt_token'] = jwt_token  # Also store in session
        
        flash(f'Welcome back, {user.username}!', 'success')
        
        # We need to pass the JWT token to the template/client for API calls
        # We'll set it in a special template that will store it in localStorage and redirect
        next_url = request.args.get('next')
        dashboard_url = url_for('web.main.admin_dashboard') if user.role == UserRole.ADMIN else url_for('web.main.dashboard')
        response = make_response(render_template('store_token.html', 
                                                 jwt_token=jwt_token, 
                                                 redirect_url=next_url or dashboard_url))
        return response
    
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
    # Use Flask-Login's logout_user function
    from flask_login import logout_user
    logout_user()
    
    # Also clear session for backward compatibility
    session.clear()
    
    # Ensure cookies are cleared
    response = make_response(render_template('clear_token.html', redirect_url=url_for('web.main.index')))
    
    # Expire the session cookie
    response.delete_cookie('session')
    
    # Expire the remember_token cookie
    response.delete_cookie('remember_token')
    
    flash('You have been logged out', 'info')
    
    # Render a template that clears the JWT token from storage before redirecting
    return response

@main.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route with comprehensive signup process"""
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('web.main.dashboard'))
        
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            # Create user with basic info
            user, error = register_user(form.username.data, form.email.data, form.password.data)
            
            if error:
                flash(error, 'danger')
                return render_template('register.html', form=form)
            
            # Update additional profile information
            if user:
                user.first_name = form.first_name.data
                user.last_name = form.last_name.data
                user.organization = form.organization.data
                user.country = form.country.data
                user.phone = form.phone.data
                user.newsletter = form.newsletter.data
                
                # User has agreed to terms
                if form.terms_agree.data:
                    db.session.commit()
                    
                    # Here you would normally send a verification email
                    # For now, just show a success message
                    flash('Registration successful! You can now log in to your account.', 'success')
                    return redirect(url_for('web.main.login'))
                else:
                    # This shouldn't happen due to form validation, but just in case
                    db.session.rollback()
                    flash('You must agree to the Terms of Service and Privacy Policy to register.', 'danger')
            else:
                flash('An error occurred during registration. Please try again.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again later.', 'danger')
    
    # If there were form validation errors or this is a GET request
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # Render the dedicated registration page
    return render_template('register.html', form=form)

@main.route('/client-registration', methods=['GET', 'POST'])
def client_registration():
    """Client registration route with detailed business and banking information"""
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('web.main.dashboard'))
        
    form = ClientRegistrationForm()
    
    # Check for invite code in URL parameters
    invite_code = request.args.get('invite_code')
    if invite_code:
        form.invite_code.data = invite_code
        
        # Get the invitation if it exists
        invitation = get_invitation_by_code(invite_code)
        if invitation and invitation.invitation_type == InvitationType.CLIENT and invitation.is_valid():
            # Pre-fill email field if we have it
            form.email.data = invitation.email
    
    if form.validate_on_submit():
        try:
            # Create user with basic info
            user, error = register_user(form.username.data, form.email.data, form.password.data, role=UserRole.USER)
            
            if error:
                flash(error, 'danger')
                return render_template('client_registration.html', form=form)
            
            # Update additional profile information
            if user:
                # Client personal details
                user.first_name = form.first_name.data
                user.last_name = form.last_name.data
                user.organization = form.organization.data
                user.country = form.country.data
                user.phone = form.phone.data
                user.newsletter = form.newsletter.data
                
                # Create Ethereum wallet for the user
                if not user.ethereum_address:
                    try:
                        address, private_key = generate_ethereum_account()
                        user.ethereum_address = address
                        user.ethereum_private_key = private_key
                    except Exception as e:
                        logger.error(f"Error creating Ethereum wallet: {str(e)}")
                
                # User has agreed to terms
                if form.terms_agree.data:
                    # Process invitation if an invite code was provided
                    if form.invite_code.data:
                        success, invite_error = accept_invitation(form.invite_code.data, user)
                        if invite_error:
                            logger.warning(f"Invitation acceptance issue: {invite_error}")
                    
                    db.session.commit()
                    
                    # Send welcome email to client
                    try:
                        from email_service import send_client_welcome_email
                        send_client_welcome_email(user)
                    except Exception as email_error:
                        logger.error(f"Error sending welcome email: {str(email_error)}")
                    
                    flash('Client registration successful! You can now log in to your account.', 'success')
                    return redirect(url_for('web.main.login'))
                else:
                    # This shouldn't happen due to form validation, but just in case
                    db.session.rollback()
                    flash('You must agree to the Terms of Service and Privacy Policy to register.', 'danger')
            else:
                flash('An error occurred during registration. Please try again.', 'danger')
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Client registration error: {str(e)}")
            flash('An error occurred during registration. Please try again later.', 'danger')
    
    # If there were form validation errors or this is a GET request
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # Render the dedicated client registration page
    return render_template('client_registration.html', form=form)

@main.route('/reset_password_request', methods=['GET', 'POST'])
def reset_request():
    """Route for requesting a password reset"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('web.main.dashboard'))
    
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
            
        return redirect(url_for('web.main.login'))
    
    return render_template('reset_request.html', form=form)

@main.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Route for resetting password using a token"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('web.main.dashboard'))
    
    # Verify token and get user
    user = verify_reset_token(token)
    
    if not user:
        flash('Invalid or expired reset token', 'danger')
        return redirect(url_for('web.main.reset_request'))
    
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        # Update user's password
        user.set_password(form.password.data)
        db.session.commit()
        
        flash('Your password has been updated! You can now log in.', 'success')
        return redirect(url_for('web.main.login'))
    
    return render_template('reset_password.html', form=form)

@main.route('/forgot_username', methods=['GET', 'POST'])
def forgot_username():
    """Route for recovering username"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('web.main.dashboard'))
    
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
        
        return redirect(url_for('web.main.login'))
    
    return render_template('forgot_username.html', form=form)

@main.route('/dashboard')
@login_required
def dashboard():
    """User dashboard route"""
    # Since we're using @login_required, current_user is guaranteed to be authenticated
    # and we don't need to check session.get('user_id')
    
    # Get the user from current_user (already provided by Flask-Login)
    user = current_user
    
    # If the user is an admin, make sure they still see the regular user dashboard
    # instead of being redirected to the admin dashboard
    # Temporarily store original role to display correct UI elements
    original_role = user.role
        
    # Make sure user has an Ethereum address
    if not user.ethereum_address:
        # Generate and assign a default Ethereum address
        from blockchain_utils import generate_ethereum_account
        eth_address, _ = generate_ethereum_account()
        user.ethereum_address = eth_address
        try:
            db.session.commit()
            logger.info(f"Assigned new Ethereum address {eth_address} to user {user.id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to assign Ethereum address to user: {str(e)}")
            # Use a fallback address if needed - this is just for UI purposes
            user.ethereum_address = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=user.id)\
        .order_by(Transaction.created_at.desc())\
        .limit(5).all()
    
    # Get transaction analytics
    analytics = get_transaction_analytics(user.id, days=30)
    
    # The get_transaction_analytics function now always returns a valid data structure
    # even when errors occur, so we don't need to check for None anymore
    
    # Log the analytics structure for debugging purposes
    logger.debug(f"Analytics data for user {user.id}: {type(analytics)}, has {len(analytics.get('raw_data', []))} data points")
    
    # Ensure JSON serialization works with decimal values
    import json
    from decimal import Decimal
    
    # Custom JSON encoder to handle Decimal values
    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, set):
                return list(obj)
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            return super(DecimalEncoder, self).default(obj)
    
    # Pre-serialize the analytics data to ensure it's valid JSON
    try:
        analytics_json = json.dumps(analytics, cls=DecimalEncoder)
        # Verify the JSON is valid by attempting to parse it back
        json.loads(analytics_json)
        logger.debug("Successfully serialized analytics data")
    except Exception as e:
        logger.error(f"Error serializing analytics data: {str(e)}")
        # Provide a basic valid JSON structure as fallback
        analytics_json = json.dumps({
            'days': 30,
            'start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'total_transactions': 0,
            'total_amount': 0,
            'by_type': {},
            'by_status': {},
            'by_date': {},
            'raw_data': []
        })
    
    # Generate a fresh JWT token for the user
    jwt_token = generate_jwt_token(user.id)
    
    # Make sure the ethereum_address is directly available in the template
    # Add it as a data attribute in the template to be accessed by JavaScript
    return render_template(
        'dashboard.html',
        user=user,
        recent_transactions=recent_transactions,
        analytics_json=analytics_json,
        user_eth_address=user.ethereum_address if user.ethereum_address else "",
        jwt_token=jwt_token
    )

@main.route('/transactions')
@login_required
def transactions():
    """Transaction history route"""
    # Since we're using @login_required, current_user is guaranteed to be authenticated
    # Use current_user.id instead of session.get('user_id')
    
    # Get filters from query parameters
    transaction_type = request.args.get('type')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query - allow admins to see all transactions
    is_admin = current_user.role == UserRole.ADMIN if hasattr(current_user, 'role') else False
    logger.debug(f"Transactions listing - User ID: {current_user.id}, Role: {current_user.role}, Is admin: {is_admin}")
    
    if is_admin:
        query = Transaction.query  # Admin can see all transactions
    else:
        query = Transaction.query.filter_by(user_id=current_user.id)  # Regular users see only their own
    
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
        transaction_statuses=TransactionStatus,
        is_admin=is_admin
    )

@main.route('/transaction/<transaction_id>')
@login_required
def transaction_details(transaction_id):
    """Transaction details route"""
    from utils import format_currency
    
    # Use current_user.id instead of session.get('user_id')
    
    # Get transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        flash('Transaction not found', 'danger')
        return redirect(url_for('web.main.transactions'))
    
    # Check if the transaction belongs to the user or user is admin
    is_admin = current_user.role == UserRole.ADMIN if hasattr(current_user, 'role') else False
    is_owner = transaction.user_id == current_user.id if hasattr(current_user, 'id') else False
    
    logger.debug(f"Transaction access check - User ID: {current_user.id}, Role: {current_user.role}, " +
                 f"Transaction owner ID: {transaction.user_id}, Is admin: {is_admin}, Is owner: {is_owner}")
    
    if not is_owner and not is_admin:
        flash('Transaction not found or you do not have permission to access it', 'danger')
        return render_template('error.html', 
                               error_title="Access Denied", 
                               error_message="Transaction not found or you do not have permission to access it")
    
    # Log successful access for debugging
    logger.debug(f"User {current_user.id} ({current_user.username}) accessed transaction {transaction_id}")
    
    # Get blockchain transaction if available
    blockchain_tx = None
    if transaction.eth_transaction_hash:
        blockchain_tx = BlockchainTransaction.query.filter_by(eth_tx_hash=transaction.eth_transaction_hash).first()
        
        # If not in our database, try to get from blockchain
        if not blockchain_tx:
            blockchain_tx = get_transaction_status(transaction.eth_transaction_hash)
    
    # Format the transaction amount
    try:
        # Don't apply format_currency directly to prevent double currency symbols
        formatted_amount = transaction.amount
        formatted_currency = transaction.currency
        
        # Just for debugging purposes
        logger.debug(f"Currency: {transaction.currency}, Amount: {transaction.amount}, Formatted: {formatted_amount} {formatted_currency}")
    except Exception as e:
        logger.error(f"Error formatting currency: {str(e)}")
        formatted_amount = transaction.amount
        formatted_currency = transaction.currency
    
    return render_template(
        'transaction_details.html',
        transaction=transaction,
        blockchain_tx=blockchain_tx,
        formatted_amount=formatted_amount,
        formatted_currency=formatted_currency,
        is_admin=is_admin,
        is_owner=is_owner
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
    
    # Import required models and blockchain functions outside try block
    from blockchain import (
        get_db, get_models, 
        get_settlement_contract, get_multisig_wallet, get_nvc_token
    )
    db = get_db()
    BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
    
    # Get recent blockchain transactions
    recent_transactions = BlockchainTransaction.query.order_by(BlockchainTransaction.created_at.desc()).limit(5).all()
    
    # Get smart contract info
    try:
        # Add detailed logging for debugging
        logger.info("Fetching smart contract instances for UI display")
        
        # Get contract instances and log their status
        settlement_contract = get_settlement_contract()
        logger.info(f"Settlement contract retrieved: {settlement_contract is not None}")
        if settlement_contract:
            logger.info(f"Settlement contract address: {settlement_contract.address}")
        
        multisig_wallet = get_multisig_wallet()
        logger.info(f"MultiSig contract retrieved: {multisig_wallet is not None}")
        if multisig_wallet:
            logger.info(f"MultiSig contract address: {multisig_wallet.address}")
        
        nvc_token = get_nvc_token()
        logger.info(f"NVC token contract retrieved: {nvc_token is not None}")
        if nvc_token:
            logger.info(f"NVC token contract address: {nvc_token.address}")
        
        # Create direct references to contract objects to pass to template
        # Instead of nested dict, we'll use the actual contract instances
        
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
        logger.error(f"Error getting contract info: {str(e)}")
        contract_info = {
            'error': str(e),
            'settlement': {'deployed': False, 'address': 'Error'},
            'multisig': {'deployed': False, 'address': 'Error'},
            'token': {'deployed': False, 'address': 'Error'}
        }
    
    # Network info
    network_id = node_info.get('network_id', 'Unknown')
    network_name = 'Sepolia Testnet' if network_id == '11155111' else f'Network ID {network_id}'
    
    # Connection status details
    if node_info.get('connected', False):
        connection_status = 'Connected'
        connection_status_color = 'success'
        connection_status_icon = 'fa-check-circle'
        current_block = node_info.get('latest_block', 'Unknown')
        fallback_notice = None
    else:
        connection_status = 'Disconnected'
        connection_status_color = 'danger'
        connection_status_icon = 'fa-times-circle'
        current_block = 'N/A'
        fallback_notice = {
            'title': 'Connection Issue',
            'message': 'Cannot connect to Ethereum network. Please check your connection or contact support.',
            'type': 'warning'
        }
    
    # Etherscan URL for the current network
    etherscan_url = 'https://sepolia.etherscan.io' if network_id == '11155111' else 'https://etherscan.io'
    
    # User roles and addresses
    is_admin = current_user.role == UserRole.ADMIN
    is_owner = False  # This would be set if the user is an owner of the MultiSig wallet
    
    # Get the user from Flask-Login's current_user
    # Since we're using @login_required, current_user is guaranteed to be authenticated
    
    # Make sure user has an Ethereum address
    if current_user and not current_user.ethereum_address:
        # Generate and assign a default Ethereum address
        from blockchain_utils import generate_ethereum_account
        eth_address, _ = generate_ethereum_account()
        current_user.ethereum_address = eth_address
        try:
            db.session.commit()
            logger.info(f"Assigned new Ethereum address {eth_address} to user {current_user.id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to assign Ethereum address to user: {str(e)}")
            # Use a fallback address if needed - this is just for UI purposes
            current_user.ethereum_address = "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"
    
    user_eth_address = current_user.ethereum_address if current_user else "0x0"
    user_token_balance = 0  # This would be calculated from the blockchain
    
    # Create template-compatible contract objects (non-Web3 objects)
    class ContractObject:
        def __init__(self, address, is_deployed=True):
            self.address = address
            self.is_deployed = is_deployed
    
    # Create objects in the format the template expects
    settlement_contract_obj = None
    multisig_contract_obj = None
    token_contract_obj = None
    
    if settlement_contract:
        settlement_contract_obj = ContractObject(settlement_contract.address)
        logger.info(f"Created settlement contract object with address: {settlement_contract_obj.address}")
    
    if multisig_wallet:
        multisig_contract_obj = ContractObject(multisig_wallet.address)
        logger.info(f"Created multisig contract object with address: {multisig_contract_obj.address}")
    
    if nvc_token:
        token_contract_obj = ContractObject(nvc_token.address)
        logger.info(f"Created token contract object with address: {token_contract_obj.address}")
    
    # Check database directly for contracts as a fallback
    if not settlement_contract_obj or not multisig_contract_obj or not token_contract_obj:
        logger.info("Using fallback method to find contracts in database")
        db = get_db()
        BlockchainTransaction, SmartContract, Transaction, TransactionStatus = get_models()
        
        # Get contracts directly from database if Web3 objects failed
        if not settlement_contract_obj:
            db_contract = SmartContract.query.filter_by(name="SettlementContract").first()
            if db_contract:
                settlement_contract_obj = ContractObject(db_contract.address)
                logger.info(f"Created settlement contract object from DB with address: {settlement_contract_obj.address}")
        
        if not multisig_contract_obj:
            db_contract = SmartContract.query.filter_by(name="MultiSigWallet").first()
            if db_contract:
                multisig_contract_obj = ContractObject(db_contract.address)
                logger.info(f"Created multisig contract object from DB with address: {multisig_contract_obj.address}")
        
        if not token_contract_obj:
            db_contract = SmartContract.query.filter_by(name="NVCToken").first()
            if db_contract:
                token_contract_obj = ContractObject(db_contract.address)
                logger.info(f"Created token contract object from DB with address: {token_contract_obj.address}")
    
    # Generate a JWT token for blockchain API access
    jwt_token = generate_jwt_token(current_user.id)
    
    # Prepare template variables
    return render_template(
        'blockchain_status.html',
        # Contract instances - properly formatted for template
        settlement_contract=settlement_contract_obj,
        multisig_contract=multisig_contract_obj,
        token_contract=token_contract_obj,
        # Node and network info
        connected=node_info.get('connected', False),
        connection_status=connection_status,
        connection_status_color=connection_status_color,
        connection_status_icon=connection_status_icon,
        network_name=network_name,
        current_block=current_block,
        etherscan_url=etherscan_url,
        # User info
        user_eth_address=user_eth_address,
        user_token_balance=user_token_balance,
        is_admin=is_admin,
        is_owner=is_owner,
        # Notifications
        fallback_notice=fallback_notice,
        # Transactions
        blockchain_transactions=recent_transactions,
        # Contract details
        token_name="NVC Banking Token",
        token_symbol="NVCT",
        token_total_supply=10_000_000_000_000,  # 10 trillion tokens as specified in NVCTokenomics
        settlement_fee_percentage=1.0,
        settlement_contract_balance=0.0,
        multisig_required_confirmations=2,
        multisig_contract_balance=0.0,
        multisig_owners=[],
        # JWT Token for API access
        jwt_token=jwt_token
    )

# Routes for SWIFT Standby Letter of Credit functionality
@main.route('/letter_of_credit/new', methods=['GET', 'POST'])
@login_required
def issue_letter_of_credit():
    """Create a new Standby Letter of Credit via SWIFT"""
    form = LetterOfCreditForm()
    
    if form.validate_on_submit():
        # Import SWIFT service
        from swift_integration import SwiftService
        
        # Use current_user.id instead of session.get('user_id')
        
        # Call the SWIFT service to create the letter of credit
        success, message, transaction = SwiftService.create_standby_letter_of_credit(
            user_id=current_user.id,
            receiver_institution_id=form.receiver_institution_id.data,
            amount=form.amount.data,
            currency=form.currency.data,
            beneficiary=form.beneficiary.data,
            expiry_date=form.expiry_date.data,
            terms_and_conditions=form.terms_and_conditions.data
        )
        
        if success and transaction:
            flash(f'Standby Letter of Credit issued successfully! Transaction ID: {transaction.transaction_id}', 'success')
            return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
        else:
            flash(f'Error issuing Standby Letter of Credit: {message}', 'danger')
            return render_template('letter_of_credit_form.html', form=form)
    
    # Handle form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    return render_template('letter_of_credit_form.html', form=form)

@main.route('/letter_of_credit/status/<transaction_id>')
@login_required
def letter_of_credit_status(transaction_id):
    """Check the status of a Letter of Credit transaction"""
    # Import SWIFT service
    from swift_integration import SwiftService
    
    # Use current_user.id instead of session.get('user_id')
    
    # First ensure the transaction belongs to the current user
    transaction = Transaction.query.filter_by(transaction_id=transaction_id, user_id=current_user.id).first()
    
    if not transaction:
        flash('Transaction not found or you do not have permission to access it', 'danger')
        return redirect(url_for('web.main.transactions'))
    
    # Only proceed if this is a Letter of Credit transaction
    if transaction.transaction_type != TransactionType.LETTER_OF_CREDIT:
        flash('This is not a Letter of Credit transaction', 'warning')
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
    
    # Get status from SWIFT service
    status_data = SwiftService.get_letter_of_credit_status(transaction_id)
    
    # Update status in transaction object if needed
    if status_data.get('success'):
        swift_status = status_data.get('status', 'unknown')
        if swift_status == 'delivered' and transaction.status != TransactionStatus.COMPLETED:
            transaction.status = TransactionStatus.COMPLETED
            db.session.commit()
            flash('Letter of Credit status updated to COMPLETED', 'success')
        elif swift_status == 'failed' and transaction.status != TransactionStatus.FAILED:
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
            flash('Letter of Credit status updated to FAILED', 'warning')
    
    return render_template('letter_of_credit_status.html', 
        transaction=transaction, 
        status_data=status_data,
        swift_data=json.loads(transaction.tx_metadata_json or '{}').get('swift', {})
    )
    
@main.route('/payment/new', methods=['GET', 'POST'])
@main.route('/payment/new/<transaction_id>', methods=['GET', 'POST'])
@login_required
def new_payment(transaction_id=None):
    """New payment route"""
    # Use current_user instead of getting user from session
    user = current_user
    
    # Get available payment gateways
    gateways = PaymentGateway.query.filter_by(is_active=True).all()
    
    # Create form and populate gateway choices
    form = PaymentForm()
    
    # If transaction_id provided, set it in the form
    if transaction_id:
        # Set transaction ID in the form
        form.transaction_id.data = transaction_id
        
        # Check if we have saved form data for this transaction
        saved_data = FormData.get_for_transaction(transaction_id, 'payment')
        if saved_data and request.method == 'GET':
            # Pre-fill the form with saved data
            logger.info(f"Loading saved payment form data for transaction {transaction_id}")
            
            for field_name, value in saved_data.items():
                if hasattr(form, field_name):
                    field = getattr(form, field_name)
                    if value is not None:
                        try:
                            field.data = value
                        except Exception as e:
                            logger.error(f"Error restoring field {field_name}: {str(e)}")
                            
            flash('Your previously entered information has been restored', 'info')
    gateway_choices = [(g.id, g.name) for g in gateways]
    form.gateway_id.choices = gateway_choices
    
    # Generate a transaction ID for form recovery if we don't have one yet
    transaction_id = form.transaction_id.data
    if not transaction_id:
        transaction_id = f"temp_{uuid.uuid4().hex}"
        form.transaction_id.data = transaction_id
    
    # We already handle form data loading when transaction_id is provided above
    
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
            current_user.id
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
                return redirect(url_for('web.main.transaction_details', transaction_id=result['transaction_id']))
        else:
            flash(f"Payment failed: {result.get('error', 'Unknown error')}", 'danger')
            return render_template('payment_form.html', form=form, user=user)
    
    # Always try to save the form data if there's anything entered in POST request
    if request.method == 'POST' and form.transaction_id.data:
        try:
            # Create a dictionary of form data
            form_data = {}
            for field_name in dir(form):
                if field_name.startswith('_') or field_name == 'meta':
                    continue
                    
                field = getattr(form, field_name)
                if hasattr(field, 'data'):
                    # Convert to string for all data types to ensure JSON compatibility
                    form_data[field_name] = str(field.data) if field.data is not None else None
            
            # Save form data
            user_id = current_user.id
            FormData.create_from_form(user_id, transaction_id, 'payment', form_data)
            db.session.commit()
            logger.info(f"Saved payment form data for transaction {transaction_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving form data: {str(e)}")
    
    # If there were form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # GET request or form validation failed, show payment form
    return render_template('payment_form.html', form=form, user=user, gateways=gateways)

@main.route('/api-docs')
def api_docs():
    """API documentation route"""
    return render_template('api_docs.html')

@main.route('/switch-role')
@login_required
def switch_role():
    """
    Switch role without session invalidation.
    Determines which dashboard to show based on current location.
    """
    # Get the user and referer
    user = current_user
    referer = request.referrer or ""
    
    # Determine which dashboard to redirect to based on the current page
    if 'admin-dashboard' in referer:
        # User is currently in admin dashboard, switch to user dashboard
        logger.info(f"User {user.username} switching from admin to user dashboard")
        return redirect(url_for('web.main.dashboard'))
    else:
        # User is in user dashboard or elsewhere, check if they should see admin dashboard
        if user.role == UserRole.ADMIN or user.username in ['admin', 'headadmin']:
            logger.info(f"User {user.username} switching from user to admin dashboard")
            return redirect(url_for('web.main.admin_dashboard')) 
        else:
            flash('Your account does not have admin privileges', 'danger')
            return redirect(url_for('web.main.dashboard'))
    
@main.route('/terms_of_service')
def terms_of_service():
    """Terms of service route"""
    return render_template('terms_of_service.html')

@main.route('/payments/return')
def payment_return():
    """Handle payment return from payment processors (PayPal, NVC Global, etc.)"""
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
    
    if not gateway:
        flash('Invalid payment gateway', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    # Accept returns from PayPal and NVC Global
    valid_gateways = [PaymentGatewayType.PAYPAL]
    # Handle the NVC Global special case due to enum issues
    if str(gateway.gateway_type) == 'nvc_global' or gateway.gateway_type == PaymentGatewayType.NVC_GLOBAL:
        # Allow NVC Global returns
        pass
    elif gateway.gateway_type not in valid_gateways:
        flash('Unsupported payment gateway for return URL', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    # Get gateway handler
    gateway_handler = get_gateway_handler(gateway.id)
    
    if not gateway_handler:
        flash('Error getting payment gateway handler', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
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

@main.route('/payments/nvc-callback', methods=['POST'])
def nvc_callback():
    """Handle callbacks from NVC Global payment platform"""
    # Get the request data
    data = request.json
    if not data:
        logger.error("NVC callback received with no data")
        return jsonify({"success": False, "error": "No data received"}), 400
    
    # Extract transaction ID from the request
    transaction_id = data.get('transaction_id')
    if not transaction_id:
        logger.error("NVC callback missing transaction_id")
        return jsonify({"success": False, "error": "Missing transaction_id"}), 400
    
    # Extract payment status
    payment_status = data.get('status')
    if not payment_status:
        logger.error("NVC callback missing payment status")
        return jsonify({"success": False, "error": "Missing payment status"}), 400
    
    # Get the transaction from our database
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not transaction:
        logger.error(f"NVC callback for unknown transaction: {transaction_id}")
        return jsonify({"success": False, "error": "Transaction not found"}), 404
    
    # Get the gateway
    gateway = PaymentGateway.query.get(transaction.gateway_id)
    if not gateway:
        logger.error(f"NVC callback for transaction with invalid gateway: {transaction_id}")
        return jsonify({"success": False, "error": "Invalid gateway"}), 400
    
    # Verify this is for NVC Global
    is_nvc_global = str(gateway.gateway_type) == 'nvc_global' or gateway.gateway_type == PaymentGatewayType.NVC_GLOBAL
    if not is_nvc_global:
        logger.error(f"NVC callback for non-NVC transaction: {transaction_id}, type: {gateway.gateway_type}")
        return jsonify({"success": False, "error": "Invalid gateway type"}), 400
    
    # Verify signature/auth for the webhook if available
    webhook_signature = request.headers.get('X-NVC-Signature')
    if webhook_signature and gateway.webhook_secret:
        # This would typically validate the signature against the request body
        # using the gateway's webhook secret
        pass
    
    # Update transaction status based on the received status
    try:
        status_mapping = {
            'pending': TransactionStatus.PENDING,
            'processing': TransactionStatus.PROCESSING,
            'completed': TransactionStatus.COMPLETED,
            'failed': TransactionStatus.FAILED,
            'refunded': TransactionStatus.REFUNDED
        }
        
        if payment_status in status_mapping:
            new_status = status_mapping[payment_status]
            
            # Update transaction status
            transaction.status = new_status
            transaction.description = f"{transaction.description} (NVC Status Update: {payment_status})"
            db.session.commit()
            
            # Send notification email for completed or failed transactions
            if new_status in [TransactionStatus.COMPLETED, TransactionStatus.FAILED]:
                try:
                    from email_service import send_transaction_confirmation_email
                    user = User.query.get(transaction.user_id)
                    if user:
                        send_transaction_confirmation_email(user, transaction)
                except Exception as email_error:
                    logger.warning(f"Failed to send NVC status update email: {str(email_error)}")
            
            logger.info(f"Updated transaction {transaction_id} status to {payment_status}")
            return jsonify({"success": True}), 200
        else:
            logger.warning(f"Unknown NVC payment status: {payment_status}")
            return jsonify({"success": False, "error": "Unknown payment status"}), 400
    
    except Exception as e:
        logger.error(f"Error processing NVC callback: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@main.route('/payments/cancel')
def payment_cancel():
    """Handle payment cancellation from payment processors"""
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

@main.route('/admin-dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard route - only accessible to admin users or special users"""
    # Check if user has admin access
    if not current_user.role == UserRole.ADMIN and current_user.username not in ['admin', 'headadmin']:
        flash('You do not have permission to access the admin dashboard', 'danger')
        return redirect(url_for('web.main.dashboard'))
    # Get user and all users
    user = current_user
    all_users = User.query.all()
    
    # Get recent transactions for all users
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
    
    # Get pending transactions
    pending_transactions = Transaction.query.filter(
        Transaction.status.in_([TransactionStatus.PENDING, TransactionStatus.PROCESSING])
    ).order_by(Transaction.created_at.desc()).all()
    
    # Get system-wide statistics for admin
    total_transaction_volume = db.session.query(func.sum(Transaction.amount)).scalar() or 0
    # Since we don't have last_login field, count users with transactions in the last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    active_users_count = db.session.query(func.count(func.distinct(Transaction.user_id))).filter(
        Transaction.created_at > thirty_days_ago
    ).scalar() or 0
    
    # Get gateway statistics
    payment_gateways = PaymentGateway.query.all()
    gateway_usage = {}
    for gateway in payment_gateways:
        count = Transaction.query.filter_by(gateway_id=gateway.id).count()
        gateway_usage[gateway.name] = count
    
    # Get transaction analytics for all users (admin view)
    analytics = get_transaction_analytics(None, days=30)  # None means get analytics for all users
    
    # Ensure JSON serialization works with decimal values
    import json
    from decimal import Decimal
    
    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                return float(obj)
            return super(DecimalEncoder, self).default(obj)
    
    # Serialize analytics data
    try:
        analytics_json = json.dumps(analytics, cls=DecimalEncoder)
        json.loads(analytics_json)  # Validate JSON is parseable
    except Exception as e:
        logger.error(f"Error serializing analytics data: {str(e)}")
        # Provide a basic valid JSON structure as fallback
        analytics_json = json.dumps({
            'days': 30,
            'start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'total_transactions': 0,
            'total_amount': 0,
            'by_type': {},
            'by_status': {},
            'by_date': {},
            'raw_data': []
        })
    
    # Generate a fresh JWT token for the user
    jwt_token = generate_jwt_token(user.id)
    
    return render_template(
        'admin/admin_dashboard.html',
        user=user,
        all_users=all_users,
        recent_transactions=recent_transactions,
        pending_transactions=pending_transactions,
        analytics_json=analytics_json,
        jwt_token=jwt_token,
        total_transaction_volume=total_transaction_volume,
        active_users_count=active_users_count,
        gateway_usage=gateway_usage,
        payment_gateways=payment_gateways
    )

@main.route('/admin/incomplete-transactions', methods=['GET'])
@login_required
def admin_incomplete_transactions():
    """View incomplete transactions with saved form data - admin only"""
    # Check if user has admin access
    if not current_user.role == UserRole.ADMIN and current_user.username not in ['admin', 'headadmin']:
        flash('You do not have permission to access the admin dashboard', 'danger')
        return redirect(url_for('web.main.dashboard'))
    # Get all transactions with status PENDING or PROCESSING
    pending_transactions = Transaction.query.filter(
        Transaction.status.in_([TransactionStatus.PENDING, TransactionStatus.PROCESSING])
    ).order_by(Transaction.created_at.desc()).all()
    
    # Get form data for each transaction
    transaction_data = []
    for transaction in pending_transactions:
        # Try to get bank transfer form data
        bank_transfer_data = FormData.get_for_transaction_admin(transaction.transaction_id, 'bank_transfer')
        # Try to get payment form data
        payment_data = FormData.get_for_transaction_admin(transaction.transaction_id, 'payment')
        
        # Add to results if we have form data
        if bank_transfer_data or payment_data:
            transaction_data.append({
                'transaction': transaction,
                'bank_transfer_data': bank_transfer_data,
                'payment_data': payment_data
            })
    
    return render_template(
        'admin/incomplete_transactions.html', 
        transaction_data=transaction_data,
        now=datetime.utcnow()
    )

@main.route('/payment/test', methods=['GET', 'POST'])
@login_required
def test_payment():
    """Test payment integration route - admin only"""
    # Check if user has admin access
    if not current_user.role == UserRole.ADMIN and current_user.username not in ['admin', 'headadmin']:
        flash('You do not have permission to access the test payment page', 'danger')
        return redirect(url_for('web.main.dashboard'))
    # Use current_user instead of getting user from session
    user = current_user
    
    # Get available payment gateways
    gateways = PaymentGateway.query.filter_by(is_active=True).all()
    
    # Create form and populate gateway choices
    form = TestPaymentForm()
    gateway_choices = [(g.id, g.name) for g in gateways]
    form.gateway_id.choices = gateway_choices
    
    # Get recent test transactions
    test_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.description.like('%Test payment%')
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    
    if form.validate_on_submit():
        # Import the test payment handler to process the test payment
        from test_payment_handler import process_test_payment
        return process_test_payment(form, current_user.id)
    
    # If there were form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    return render_template('payment_test.html', form=form, user=user, test_transactions=test_transactions)

@main.route('/payment/bank-transfer/<transaction_id>', methods=['GET', 'POST'])
@login_required
def bank_transfer_form(transaction_id):
    """Bank transfer form route for NVC Global payments"""
    # Flask-Login's @login_required should ensure current_user is authenticated
    # But we'll add an extra check to be safe
    if not current_user.is_authenticated:
        flash('Please log in to access this page', 'warning')
        return redirect(url_for('web.main.login', next=request.path))
    
    # Get the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        flash('Transaction not found', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    # Verify this transaction belongs to the current user
    if transaction.user_id != current_user.id:
        flash('You do not have permission to access this transaction', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    # Verify the transaction is for NVC Global and is in an appropriate state
    if not transaction.gateway or transaction.gateway.name != 'NVC Global' or transaction.status not in [TransactionStatus.PENDING, TransactionStatus.PROCESSING]:
        flash('This transaction cannot be processed as a bank transfer', 'danger')
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
    
    # Create the bank transfer form with transaction_id set
    form = BankTransferForm(transaction_id=transaction_id)
    
    # Set the transaction ID in the form
    form.transaction_id.data = transaction_id
    
    # Check if we have saved form data for this transaction
    saved_data = FormData.get_for_transaction(transaction_id, 'bank_transfer')
    if saved_data and request.method == 'GET':
        # Pre-fill the form with saved data
        logger.info(f"Loading saved bank transfer form data for transaction {transaction_id}")
        
        for field_name, value in saved_data.items():
            if hasattr(form, field_name):
                field = getattr(form, field_name)
                if value is not None:
                    try:
                        field.data = value
                    except Exception as e:
                        logger.error(f"Error restoring field {field_name}: {str(e)}")
                        
        flash('Your previously entered information has been restored', 'info')
    
    # Always try to save the form data if there's anything entered
    if request.method == 'POST' and form.transaction_id.data:
        try:
            # Create a dictionary of form data
            form_data = {}
            for field_name in dir(form):
                if field_name.startswith('_') or field_name == 'meta':
                    continue
                    
                field = getattr(form, field_name)
                if hasattr(field, 'data'):
                    # Convert to string for all data types to ensure JSON compatibility
                    form_data[field_name] = str(field.data) if field.data is not None else None
            
            # Save form data
            user_id = current_user.id
            FormData.create_from_form(user_id, transaction_id, 'bank_transfer', form_data)
            db.session.commit()
            logger.info(f"Saved bank transfer form data for transaction {transaction_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving form data: {str(e)}")
    
    if form.validate_on_submit():
        # Process the bank transfer request
        try:
            # Update transaction metadata with bank details
            bank_details = {
                'recipient': {
                    'name': form.recipient_name.data,
                    'email': form.recipient_email.data,
                    'address': form.recipient_address.data,
                    'city': form.recipient_city.data,
                    'state': form.recipient_state.data,
                    'zip': form.recipient_zip.data,
                    'country': form.recipient_country.data
                },
                'bank': {
                    'name': form.bank_name.data,
                    'account_number': form.account_number.data,
                    'account_type': form.account_type.data,
                    'transfer_type': form.transfer_type.data,
                    'address': form.bank_address.data,
                    'city': form.bank_city.data,
                    'state': form.bank_state.data,
                    'country': form.bank_country.data
                },
                'reference': form.reference.data,
                'payment_note': form.description.data
            }
            
            # Add routing or SWIFT code based on transfer type
            if form.transfer_type.data == 'domestic':
                bank_details['bank']['routing_number'] = form.routing_number.data
            else:
                bank_details['bank']['swift_bic'] = form.swift_bic.data
                bank_details['bank']['iban'] = form.iban.data
                bank_details['international'] = {
                    'currency': form.currency.data,
                    'purpose': form.purpose.data,
                    'purpose_detail': form.purpose_detail.data if form.purpose.data == 'other' else None,
                    'intermediary_bank': form.intermediary_bank.data,
                    'intermediary_swift': form.intermediary_swift.data
                }
            
            # Update transaction with bank transfer details
            if transaction.tx_metadata_json:
                metadata = json.loads(transaction.tx_metadata_json)
                metadata['bank_transfer'] = bank_details
                transaction.tx_metadata_json = json.dumps(metadata)
            else:
                transaction.tx_metadata_json = json.dumps({'bank_transfer': bank_details})
            
            # Update transaction description to include bank transfer info
            transaction.description = f"{transaction.description} (Bank Transfer to {form.bank_name.data})"
            
            # Update transaction status to processing
            transaction.status = TransactionStatus.PROCESSING
            
            # Save transaction
            db.session.commit()
            
            # Get gateway handler to process the bank transfer
            try:
                # Make sure we have a valid gateway
                if not transaction.gateway or not transaction.gateway.id:
                    raise ValueError("No valid payment gateway found for this transaction")
                
                gateway_handler = get_gateway_handler(transaction.gateway.id)
                
                # Process the bank transfer through NVC Global
                result = gateway_handler.process_bank_transfer(transaction)
                
                if result.get('success'):
                    flash('Bank transfer initiated successfully', 'success')
                    return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
                else:
                    flash(f"Error processing bank transfer: {result.get('error', 'Unknown error')}", 'danger')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error processing bank transfer: {str(e)}")
                flash(f"Error processing bank transfer: {str(e)}", 'danger')
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating transaction with bank details: {str(e)}")
            flash(f"Error updating transaction with bank details: {str(e)}", 'danger')
    
    # For GET request or form validation errors, show the bank transfer form
    return render_template(
        'bank_transfer_form.html', 
        form=form, 
        transaction_id=transaction.transaction_id,
        amount=format_currency(transaction.amount, transaction.currency),
        date=transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        description=transaction.description
    )

@main.route('/payment/process-bank-transfer', methods=['POST'])
@login_required
def process_bank_transfer():
    """Process a bank transfer form submission"""
    # Ensure user is authenticated
    if not current_user.is_authenticated:
        flash('Please log in to access this page', 'warning')
        return redirect(url_for('web.main.login', next=request.path))
    
    # Get the form data
    form = BankTransferForm()
    
    # First attempt to save form data for possible recovery
    transaction_id = request.form.get('transaction_id')
    if transaction_id:
        # Ensure the transaction_id is set in the form
        form.transaction_id.data = transaction_id
        try:
            # Create a dictionary of form data
            form_data = {}
            for field_name in dir(form):
                if field_name.startswith('_') or field_name == 'meta':
                    continue
                    
                field = getattr(form, field_name)
                if hasattr(field, 'data'):
                    # Convert to string for all data types to ensure JSON compatibility
                    form_data[field_name] = str(field.data) if field.data is not None else None
            
            # Save form data
            user_id = current_user.id
            FormData.create_from_form(user_id, transaction_id, 'bank_transfer', form_data)
            db.session.commit()
            logger.info(f"Saved bank transfer form data for transaction {transaction_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving form data: {str(e)}")
    
    # Begin form validation
    if form.validate_on_submit():
        # Get the transaction from the database
        user_id = current_user.id
        transaction = Transaction.query.filter_by(transaction_id=transaction_id, user_id=user_id).first()
        
        if not transaction:
            flash('Transaction not found or you do not have permission to access it', 'danger')
            return redirect(url_for('web.main.dashboard'))
        
        # Make sure the transaction is for NVC Global and in an appropriate state
        if not transaction.gateway or transaction.gateway.name != 'NVC Global' or transaction.status not in [TransactionStatus.PENDING, TransactionStatus.PROCESSING]:
            flash('This transaction cannot be processed as a bank transfer', 'danger')
            return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
            
        try:
            # Update transaction metadata with bank details
            bank_details = {
                'recipient': {
                    'name': form.recipient_name.data,
                    'email': form.recipient_email.data,
                    'address': form.recipient_address.data,
                    'city': form.recipient_city.data,
                    'state': form.recipient_state.data,
                    'zip': form.recipient_zip.data,
                    'country': form.recipient_country.data
                },
                'bank': {
                    'name': form.bank_name.data,
                    'account_number': form.account_number.data,
                    'account_type': form.account_type.data,
                    'transfer_type': form.transfer_type.data,
                    'address': form.bank_address.data,
                    'city': form.bank_city.data,
                    'state': form.bank_state.data,
                    'country': form.bank_country.data
                },
                'reference': form.reference.data,
                'payment_note': form.description.data
            }
            
            # Add routing or SWIFT code based on transfer type
            if form.transfer_type.data == 'domestic':
                bank_details['bank']['routing_number'] = form.routing_number.data
            else:
                bank_details['bank']['swift_bic'] = form.swift_bic.data
                bank_details['bank']['iban'] = form.iban.data
                bank_details['international'] = {
                    'currency': form.currency.data,
                    'purpose': form.purpose.data,
                    'purpose_detail': form.purpose_detail.data if form.purpose.data == 'other' else None,
                    'intermediary_bank': form.intermediary_bank.data,
                    'intermediary_swift': form.intermediary_swift.data
                }
            
            # Update transaction with bank transfer details
            if transaction.tx_metadata_json:
                try:
                    metadata = json.loads(transaction.tx_metadata_json)
                    metadata['bank_transfer'] = bank_details
                    transaction.tx_metadata_json = json.dumps(metadata)
                except json.JSONDecodeError:
                    # If existing metadata is invalid, create new
                    transaction.tx_metadata_json = json.dumps({'bank_transfer': bank_details})
            else:
                transaction.tx_metadata_json = json.dumps({'bank_transfer': bank_details})
            
            # Update transaction description
            transaction.description = f"{transaction.description} (Bank Transfer to {form.bank_name.data})"
            
            # Update transaction status
            transaction.status = TransactionStatus.PROCESSING
            
            # Save transaction
            db.session.commit()
            
            # Process the bank transfer through NVC Global
            try:
                # Make sure we have a valid gateway
                if not transaction.gateway or not transaction.gateway.id:
                    raise ValueError("No valid payment gateway found for this transaction")
                
                gateway_handler = get_gateway_handler(transaction.gateway.id)
                
                # Process the bank transfer
                result = gateway_handler.process_bank_transfer(transaction)
                
                if result.get('success'):
                    flash('Bank transfer initiated successfully', 'success')
                    return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
                else:
                    flash(f"Error processing bank transfer: {result.get('error', 'Unknown error')}", 'danger')
                    return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error processing bank transfer: {str(e)}")
                flash(f"Error processing bank transfer: {str(e)}", 'danger')
                return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating transaction with bank details: {str(e)}")
            flash(f"Error updating transaction with bank details: {str(e)}", 'danger')
    
    # If there were form validation errors
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    # If the form validation failed, redirect to dashboard
    return redirect(url_for('web.main.dashboard'))