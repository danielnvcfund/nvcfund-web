"""
Dashboard Routes
This module provides the routes for the client dashboard with account overview
"""
from flask import Blueprint, render_template, redirect, url_for
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
        return redirect(url_for('account.create_profile'))
    
    # Get all accounts for the account holder
    accounts = BankAccount.query.filter_by(account_holder_id=account_holder.id).all()
    
    # If no accounts exist, create default accounts
    if not accounts:
        try:
            accounts = create_default_accounts_for_holder(account_holder)
            if not accounts:
                logger.error(f"Failed to create default accounts for user {current_user.id}")
        except Exception as e:
            logger.error(f"Error creating default accounts: {str(e)}")
    
    return render_template(
        'dashboard/client_dashboard.html',
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
        return redirect(url_for('account.create_profile'))
    
    # Get all accounts for the account holder
    accounts = BankAccount.query.filter_by(account_holder_id=account_holder.id).all()
    
    return render_template(
        'dashboard/account_summary.html',
        account_holder=account_holder,
        accounts=accounts
    )