"""
Direct Account Routes
This module provides direct access to account creation and viewing
"""
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db, logger
from account_holder_models import AccountHolder, BankAccount
from account_generator import create_default_accounts_for_holder

# Create blueprint
direct_bp = Blueprint('direct', __name__, url_prefix='/generate-accounts')


@direct_bp.route('/')
@login_required
def index():
    """Show explanation page for account generation"""
    return render_template('direct_account_link.html')


@direct_bp.route('/create')
@login_required
def create_accounts():
    """Create accounts immediately"""
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
            return redirect(url_for('direct.index'))
    
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
        'account_view.html',
        account_holder=account_holder,
        accounts=accounts
    )