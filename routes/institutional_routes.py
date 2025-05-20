"""
Routes for institutional and correspondent banking account management
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app import db
from account_holder_models import AccountHolder, CurrencyType, BankAccount, AccountType
from account_generator import create_institutional_account, create_correspondent_account

institutional_bp = Blueprint('institutional', __name__, url_prefix='/institutional')


@institutional_bp.route('/')
@login_required
def institutional_dashboard():
    """Institutional banking dashboard"""
    # Get account holder for current user
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    
    # If no account holder exists, redirect to create one
    if not account_holder:
        flash("Please complete your profile before accessing institutional banking.", "warning")
        return redirect(url_for('dashboard.welcome'))
    
    # Get all institutional and correspondent accounts
    institutional_accounts = BankAccount.query.filter_by(
        account_holder_id=account_holder.id,
        account_type=AccountType.INSTITUTIONAL
    ).all()
    
    nostro_accounts = BankAccount.query.filter_by(
        account_holder_id=account_holder.id,
        account_type=AccountType.NOSTRO
    ).all()
    
    vostro_accounts = BankAccount.query.filter_by(
        account_holder_id=account_holder.id,
        account_type=AccountType.VOSTRO
    ).all()
    
    # We don't use CORRESPONDENT type directly, accounts are either NOSTRO or VOSTRO
    correspondent_accounts = nostro_accounts + vostro_accounts
    
    return render_template(
        'institutional/dashboard.html',
        account_holder=account_holder,
        institutional_accounts=institutional_accounts,
        nostro_accounts=nostro_accounts,
        vostro_accounts=vostro_accounts,
        correspondent_accounts=correspondent_accounts
    )


@institutional_bp.route('/create-institutional-account', methods=['GET', 'POST'])
@login_required
def create_institutional_account_route():
    """Create a new institutional account"""
    # Get account holder
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    
    # If no account holder exists, redirect to create one
    if not account_holder:
        flash("Please complete your profile before creating institutional accounts.", "warning")
        return redirect(url_for('dashboard.welcome'))
    
    if request.method == 'POST':
        # Get form data
        currency = request.form.get('currency')
        
        # Check if currency is provided
        if not currency:
            flash("Please select a currency for the account", "danger")
            return render_template(
                'institutional/create_account.html',
                currencies=[c.name for c in CurrencyType]
            )
            
        # Create the institutional account - currency can now be string
        institutional_account = create_institutional_account(
            account_holder=account_holder,
            currency=currency
        )
        
        if institutional_account:
            flash(f"New institutional account created: {institutional_account.account_number}", "success")
            return redirect(url_for('institutional.institutional_dashboard'))
        else:
            flash("Error creating institutional account. Please try again.", "danger")
    
    # Render form for GET requests
    return render_template(
        'institutional/create_account.html',
        currencies=[c.name for c in CurrencyType]
    )


@institutional_bp.route('/create-correspondent-account', methods=['GET', 'POST'])
@login_required
def create_correspondent_account_route():
    """Create a new correspondent bank account (Nostro or Vostro)"""
    # Get account holder
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    
    # If no account holder exists, redirect to create one
    if not account_holder:
        flash("Please complete your profile before creating correspondent accounts.", "warning")
        return redirect(url_for('dashboard.welcome'))
    
    if request.method == 'POST':
        # Get form data
        currency = request.form.get('currency')
        account_type = request.form.get('account_type')
        
        # Check if currency and account type are provided
        if not currency or not account_type:
            flash("Please select both a currency and account type", "danger")
            return render_template(
                'institutional/create_correspondent.html',
                currencies=[c.name for c in CurrencyType]
            )
        
        # Determine if Nostro or Vostro based on form selection
        is_nostro = (account_type == 'nostro')
        
        # Create the correspondent account
        correspondent_account = create_correspondent_account(
            account_holder=account_holder,
            currency=currency,
            nostro=is_nostro
        )
        
        if correspondent_account:
            account_type_name = "Nostro" if is_nostro else "Vostro"
            flash(f"New {account_type_name} correspondent account created: {correspondent_account.account_number}", "success")
            return redirect(url_for('institutional.institutional_dashboard'))
        else:
            flash("Error creating correspondent account. Please try again.", "danger")
    
    # Render form for GET requests
    return render_template(
        'institutional/create_correspondent.html',
        currencies=[c.name for c in CurrencyType]
    )