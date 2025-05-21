"""
Treasury to Stablecoin Transfer Routes Module
This module handles transfers between Treasury Accounts and NVCT stablecoin accounts.
"""

import json
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, session
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from models import db, User, TreasuryAccount, Transaction, TransactionStatus, TransactionType, CurrencyType
from account_holder_models import AccountHolder, BankAccount, AccountType
from account_generator import create_additional_account
from decorators import roles_required
from utils import generate_transaction_id, format_currency

# Blueprint Definition
treasury_bp = Blueprint('treasury_stablecoin', __name__, url_prefix='/treasury-stablecoin')

@treasury_bp.route('/transfer-to-stablecoin', methods=['GET', 'POST'])
@login_required
def transfer_to_stablecoin():
    """Handle transfers from Treasury Accounts to NVCT Stablecoin Accounts"""
    try:
        # Get treasury accounts that can be used to fund stablecoin accounts
        treasury_accounts = TreasuryAccount.query.filter_by(is_active=True).all()
        
        # Get user's NVCT accounts
        account_holder = None
        if hasattr(current_user, 'account_holder') and current_user.account_holder:
            account_holder = current_user.account_holder
            nvct_accounts = BankAccount.query.filter_by(
                account_holder_id=account_holder.id,
                currency=CurrencyType.NVCT
            ).all()
        else:
            nvct_accounts = []
        
        if request.method == 'POST':
            # Get form data
            treasury_account_id = request.form.get('treasury_account_id', type=int)
            nvct_account_id = request.form.get('nvct_account_id', type=int)
            amount = request.form.get('amount', type=float)
            description = request.form.get('description', '')
            
            # Basic validation
            if not treasury_account_id or not nvct_account_id or not amount:
                flash("Please fill in all required fields", "danger")
                return render_template(
                    'treasury/transfer_to_stablecoin.html',
                    treasury_accounts=treasury_accounts,
                    nvct_accounts=nvct_accounts,
                    title="Fund NVCT Account from Treasury"
                )
            
            # Get accounts
            treasury_account = TreasuryAccount.query.get(treasury_account_id)
            nvct_account = BankAccount.query.get(nvct_account_id)
            
            if not treasury_account:
                flash("Selected treasury account not found", "danger")
                return redirect(url_for('treasury.transfer_to_stablecoin'))
                
            if not nvct_account:
                flash("Selected NVCT account not found", "danger")
                return redirect(url_for('treasury.transfer_to_stablecoin'))
            
            # Check sufficient funds
            if treasury_account.available_balance < amount:
                flash("Insufficient funds in treasury account", "danger")
                return redirect(url_for('treasury.transfer_to_stablecoin'))
            
            # Check NVCT account ownership
            if nvct_account.account_holder_id != account_holder.id:
                flash("You do not have permission to fund this NVCT account", "danger")
                return redirect(url_for('treasury.transfer_to_stablecoin'))
            
            try:
                # Generate transaction ID
                transaction_id = generate_transaction_id()
                
                # Create transaction record - using only fields that exist in the Transaction model
                transaction = Transaction()
                transaction.transaction_id = transaction_id
                transaction.user_id = current_user.id
                transaction.amount = amount
                transaction.currency = "USD"  # Treasury is in USD, NVCT is pegged 1:1 with USD
                transaction.transaction_type = TransactionType.TREASURY_TRANSFER
                transaction.status = TransactionStatus.COMPLETED
                transaction.description = description or f"Treasury to NVCT transfer {treasury_account.name} to {nvct_account.account_number}"
                transaction.recipient_account = nvct_account.account_number
                
                # Store additional metadata as JSON
                metadata = {
                    "reference": f"TREASURY2NVCT-{transaction_id[:8]}",
                    "from_account_type": "treasury",
                    "from_account_id": treasury_account.id,
                    "to_account_type": "stablecoin",
                    "to_account_id": nvct_account.id,
                    "from_account_name": treasury_account.name,
                    "to_account_number": nvct_account.account_number
                }
                transaction.tx_metadata_json = json.dumps(metadata)
                
                # Update account balances
                treasury_account.balance -= amount
                treasury_account.available_balance -= amount
                nvct_account.balance += amount
                nvct_account.available_balance += amount
                
                # Save everything
                db.session.add(transaction)
                db.session.commit()
                
                flash(f"Successfully transferred {format_currency(amount, 'USD')} from Treasury to NVCT account", "success")
                return redirect(url_for('stablecoin.account_details', account_id=nvct_account.id))
                
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f"Database error processing treasury to NVCT transfer: {str(e)}")
                flash("An error occurred while processing the transfer", "danger")
        
        # Check if account holder has no NVCT accounts and create one automatically
        if account_holder and not nvct_accounts:
            try:
                # Create default NVCT account
                new_account = create_additional_account(
                    account_holder=account_holder,
                    currency=CurrencyType.NVCT,
                    account_type=AccountType.CHECKING
                )
                
                if new_account:
                    flash(f"Created a new NVCT account ({new_account.account_number}) for you", "success")
                    nvct_accounts = [new_account]
            except Exception as e:
                current_app.logger.error(f"Error creating NVCT account: {str(e)}")
                flash("Could not create NVCT account automatically, please contact support", "warning")
        
        return render_template(
            'treasury/transfer_to_stablecoin.html',
            treasury_accounts=treasury_accounts,
            nvct_accounts=nvct_accounts,
            title="Fund NVCT Account from Treasury"
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in treasury_to_stablecoin: {str(e)}")
        flash("An unexpected error occurred", "danger")
        return redirect(url_for('stablecoin.index'))