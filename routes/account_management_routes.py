"""
Account Management Routes
This module provides routes for creating and managing bank accounts
"""
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from app import db, logger
from models import User
from account_holder_models import AccountHolder, Address, PhoneNumber, BankAccount, AccountType, CurrencyType, AccountStatus
from account_generator import create_default_accounts_for_holder, create_additional_account, AccountNumberGenerator
from forms.account_forms import AddressForm, AccountForm, PhoneForm, AccountHolderForm

# Create blueprint
account_bp = Blueprint('account', __name__, url_prefix='/accounts')


@account_bp.route('/')
@login_required
def index():
    """Account management dashboard"""
    # Get account holder for current user
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    
    # If no account holder exists, redirect to create one
    if not account_holder:
        flash('Please complete your account profile first', 'warning')
        return redirect(url_for('account.create_profile'))
    
    # Get all accounts for the account holder
    accounts = BankAccount.query.filter_by(account_holder_id=account_holder.id).all()
    
    return render_template(
        'accounts/index.html',
        account_holder=account_holder,
        accounts=accounts
    )


@account_bp.route('/create-profile', methods=['GET', 'POST'])
@login_required
def create_profile():
    """Create account holder profile"""
    # Check if user already has an account holder profile
    existing_profile = AccountHolder.query.filter_by(user_id=current_user.id).first()
    if existing_profile:
        flash('You already have an account profile', 'info')
        return redirect(url_for('account.index'))
    
    address_form = AddressForm()
    
    if request.method == 'POST' and address_form.validate_on_submit():
        try:
            # Create new account holder
            account_holder = AccountHolder()
            account_holder.external_id = uuid.uuid4().hex
            account_holder.name = request.form.get('name', current_user.username)
            account_holder.username = current_user.username
            account_holder.email = current_user.email
            account_holder.is_business = request.form.get('is_business') == 'on'
            account_holder.business_name = request.form.get('business_name')
            account_holder.business_type = request.form.get('business_type')
            account_holder.tax_id = request.form.get('tax_id')
            account_holder.user_id = current_user.id
            db.session.add(account_holder)
            db.session.flush()  # Get ID without full commit
            
            # Create address
            address = Address()
            address.name = 'Primary Address'
            address.line1 = address_form.line1.data
            address.line2 = address_form.line2.data
            address.city = address_form.city.data
            address.region = address_form.region.data
            address.zip = address_form.zip.data
            address.country = address_form.country.data
            address.account_holder_id = account_holder.id
            db.session.add(address)
            
            # Create phone number
            phone = PhoneNumber()
            phone.name = 'Primary Phone'
            phone.number = request.form.get('phone')
            phone.is_primary = True
            phone.is_mobile = True
            phone.account_holder_id = account_holder.id
            db.session.add(phone)
            
            # Commit to save account holder, address and phone
            db.session.commit()
            
            # Create default bank accounts
            created_accounts = create_default_accounts_for_holder(account_holder)
            
            if created_accounts:
                flash('Your profile has been created and bank accounts have been assigned!', 'success')
                return redirect(url_for('account.index'))
            else:
                flash('Your profile was created but there was an issue creating your bank accounts. Please contact support.', 'warning')
                return redirect(url_for('account.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating account holder profile: {str(e)}")
            flash(f'Error creating profile: {str(e)}', 'danger')
    
    return render_template(
        'accounts/create_profile.html',
        address_form=address_form
    )


@account_bp.route('/new-account', methods=['GET', 'POST'])
@login_required
def new_account():
    """Create a new bank account"""
    # Get account holder for current user
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    
    # If no account holder exists, redirect to create one
    if not account_holder:
        flash('Please complete your account profile first', 'warning')
        return redirect(url_for('account.create_profile'))
    
    form = AccountForm()
    
    # Populate currency choices based on CurrencyType enum
    form.currency.choices = [(currency.name, currency.name) for currency in CurrencyType]
    
    # Populate account type choices based on AccountType enum
    form.account_type.choices = [(account_type.name, account_type.name.capitalize()) 
                                for account_type in AccountType]
                                
    if form.currency.choices is None:
        form.currency.choices = [('USD', 'USD'), ('EUR', 'EUR'), ('NVCT', 'NVCT')]
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Get selected currency and account type
            currency = CurrencyType[form.currency.data]
            account_type = AccountType[form.account_type.data]
            
            # Create the new account
            new_account = create_additional_account(
                account_holder=account_holder,
                currency=currency,
                account_type=account_type
            )
            
            if new_account:
                flash(f'New {currency.name} {account_type.name.lower()} account created successfully!', 'success')
                return redirect(url_for('account.index'))
            else:
                flash('There was an error creating your account. Please try again.', 'danger')
        
        except Exception as e:
            logger.error(f"Error creating new account: {str(e)}")
            flash(f'Error creating account: {str(e)}', 'danger')
    
    return render_template(
        'accounts/new_account.html',
        form=form,
        account_holder=account_holder
    )


@account_bp.route('/details/<int:account_id>')
@login_required
def account_details(account_id):
    """View account details"""
    # Get account holder for current user
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    
    # If no account holder exists, redirect to create one
    if not account_holder:
        flash('Please complete your account profile first', 'warning')
        return redirect(url_for('account.create_profile'))
    
    # Get account, ensuring it belongs to the current user
    account = BankAccount.query.filter_by(
        id=account_id, 
        account_holder_id=account_holder.id
    ).first_or_404()
    
    return render_template(
        'accounts/details.html',
        account=account,
        account_holder=account_holder
    )


@account_bp.route('/api/generate-account-number', methods=['POST'])
@login_required
def generate_account_number_api():
    """API endpoint to generate a new account number without creating an account"""
    try:
        if request.json:
            account_type_name = request.json.get('accountType', 'CHECKING')
        else:
            account_type_name = 'CHECKING'
            
        account_type = AccountType[account_type_name]
        
        account_number = AccountNumberGenerator.generate_account_number(account_type)
        
        return jsonify({
            'success': True,
            'accountNumber': account_number
        })
    
    except Exception as e:
        logger.error(f"Error generating account number: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400