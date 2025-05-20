"""
Dashboard Routes
This module provides the routes for the client dashboard with account overview
"""
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db, logger
from account_holder_models import AccountHolder, BankAccount
from account_generator import create_default_accounts_for_holder

# Create blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def index():
    """Client dashboard with account overview"""
    # Check if the user has an account holder profile
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    
    # If no account holder exists, redirect to create one
    if not account_holder:
        flash('Please complete your profile to generate your accounts', 'info')
        return redirect(url_for('dashboard.welcome'))
    
    # Get all accounts for the account holder
    accounts = BankAccount.query.filter_by(account_holder_id=account_holder.id).all()
    
    # If no accounts exist, create default accounts
    if not accounts:
        try:
            accounts = create_default_accounts_for_holder(account_holder)
            if accounts:
                flash('We have created default accounts for you!', 'success')
            else:
                logger.error(f"Failed to create default accounts for user {current_user.id}")
                flash('There was an issue creating your default accounts. Please contact support.', 'warning')
        except Exception as e:
            logger.error(f"Error creating default accounts: {str(e)}")
            flash(f'Error creating accounts: {str(e)}', 'danger')
    
    return render_template(
        'dashboard/client_dashboard.html',
        account_holder=account_holder,
        accounts=accounts
    )


@dashboard_bp.route('/welcome')
@login_required
def welcome():
    """Welcome page for new users without profiles"""
    return render_template(
        'dashboard/welcome.html'
    )


@dashboard_bp.route('/accounts')
@login_required
def accounts():
    """Direct access to accounts page"""
    # Get account holder for current user
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    
    # If no account holder exists, create one with minimal info
    if not account_holder:
        try:
            # Create minimal account holder
            account_holder = AccountHolder()
            account_holder.name = current_user.username
            account_holder.username = current_user.username
            account_holder.email = current_user.email
            account_holder.external_id = f"USR-{current_user.id}"
            account_holder.user_id = current_user.id
            db.session.add(account_holder)
            db.session.commit()
            flash('Your profile has been created', 'success')
        except Exception as e:
            logger.error(f"Error creating account holder: {str(e)}")
            flash(f'Error creating your profile: {str(e)}', 'danger')
            return redirect(url_for('dashboard.welcome'))
    
    # Get all accounts for the account holder
    accounts = BankAccount.query.filter_by(account_holder_id=account_holder.id).all()
    
    # If no accounts exist, create default accounts
    if not accounts:
        try:
            accounts = create_default_accounts_for_holder(account_holder)
            if accounts:
                flash('Your bank accounts have been created successfully!', 'success')
            else:
                logger.error(f"Failed to create default accounts for user {current_user.id}")
                flash('There was an issue creating your default accounts. Please contact support.', 'warning')
        except Exception as e:
            logger.error(f"Error creating default accounts: {str(e)}")
            flash(f'Error creating accounts: {str(e)}', 'danger')
    
    return render_template(
        'dashboard/account_summary.html',
        account_holder=account_holder,
        accounts=accounts
    )


@dashboard_bp.route('/account-summary')
@login_required
def account_summary():
    """Summary of all accounts"""
    # Get account holder for current user
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    
    # If no account holder exists, redirect to create one
    if not account_holder:
        return redirect(url_for('dashboard.welcome'))
    
    # Get all accounts for the account holder
    accounts = BankAccount.query.filter_by(account_holder_id=account_holder.id).all()
    
    return render_template(
        'dashboard/account_summary.html',
        account_holder=account_holder,
        accounts=accounts
    )