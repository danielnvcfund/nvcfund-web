"""
Payment Routes for the NVC Banking Platform

This module defines routes for transfer and deposit operations.
"""
from decimal import Decimal, InvalidOperation
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db, logger
from account_holder_models import AccountHolder, BankAccount, AccountType, CurrencyType, AccountStatus

# Import the existing transaction models from the main models file
from models import Transaction, TransactionType, TransactionStatus

# Create forms locally to avoid import issues
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class TransferForm(FlaskForm):
    """Form for transferring funds between accounts"""
    from_account = SelectField('From Account', validators=[DataRequired()])
    to_account_number = StringField('To Account Number', validators=[DataRequired(), Length(min=10, max=50)])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    description = TextAreaField('Description', validators=[Length(max=255)])
    submit = SubmitField('Transfer Funds')
    
    def __init__(self, *args, **kwargs):
        """Initialize the form with user accounts"""
        user_accounts = kwargs.pop('user_accounts', [])
        super(TransferForm, self).__init__(*args, **kwargs)
        
        # Populate the from_account select field with user accounts
        if user_accounts:
            self.from_account.choices = [
                (
                    account.account_number, 
                    f"{account.account_name} ({account.account_number}) - {account.currency.name} {account.balance:,.2f}"
                ) 
                for account in user_accounts
            ]

class DepositForm(FlaskForm):
    """Form for depositing funds into an account"""
    to_account = SelectField('To Account', validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    description = TextAreaField('Description', validators=[Length(max=255)])
    submit = SubmitField('Deposit Funds')
    
    def __init__(self, *args, **kwargs):
        """Initialize the form with user accounts"""
        user_accounts = kwargs.pop('user_accounts', [])
        super(DepositForm, self).__init__(*args, **kwargs)
        
        # Populate the to_account select field with user accounts
        if user_accounts:
            self.to_account.choices = [
                (
                    account.account_number, 
                    f"{account.account_name} ({account.account_number}) - {account.currency.name} {account.balance:,.2f}"
                ) 
                for account in user_accounts
            ]

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')


@payment_bp.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer_form():
    """Render and process the fund transfer form"""
    # Get account holder for current user
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    
    # If no account holder exists, redirect to create one
    if not account_holder:
        flash("Please complete your profile before making transfers.", "warning")
        return redirect(url_for('dashboard.welcome'))
    
    # Get all active accounts for the account holder
    accounts = BankAccount.query.filter_by(
        account_holder_id=account_holder.id,
        status=AccountStatus.ACTIVE
    ).all()
    
    if not accounts:
        flash("You don't have any active accounts to transfer from.", "warning")
        return redirect(url_for('dashboard.account_summary'))
    
    # Create form with user accounts
    form = TransferForm(user_accounts=accounts)
    
    if form.validate_on_submit():
        try:
            # Get form data
            from_account_number = form.from_account.data
            to_account_number = form.to_account_number.data
            
            # Safely convert amount to Decimal
            if form.amount.data is None:
                flash("Please enter a valid amount", "danger")
                return redirect(url_for('payment.transfer_form'))
            try:
                amount = Decimal(str(form.amount.data))
            except (ValueError, InvalidOperation):
                flash("Invalid amount format", "danger")
                return redirect(url_for('payment.transfer_form'))
            
            # Find the source account
            from_account = BankAccount.query.filter_by(
                account_number=from_account_number,
                account_holder_id=account_holder.id,
                status=AccountStatus.ACTIVE
            ).first()
            
            if not from_account:
                flash("Source account not found or not active.", "danger")
                return redirect(url_for('payment.transfer_form'))
            
            # Check if enough funds
            if from_account.available_balance < amount:
                flash(f"Insufficient funds in {from_account.account_name}. Available balance: {from_account.available_balance:,.2f}", "danger")
                return redirect(url_for('payment.transfer_form'))
            
            # Find the destination account
            to_account = BankAccount.query.filter_by(
                account_number=to_account_number,
                status=AccountStatus.ACTIVE
            ).first()
            
            if not to_account:
                flash("Destination account not found or not active.", "danger")
                return redirect(url_for('payment.transfer_form'))
                
            # Check if same account
            if from_account.account_number == to_account.account_number:
                flash("Cannot transfer funds to the same account.", "danger")
                return redirect(url_for('payment.transfer_form'))
                
            # Check if currencies match
            if from_account.currency != to_account.currency:
                flash(f'Currency mismatch. Source account is in {from_account.currency}, destination is in {to_account.currency}.', 'danger')
                return redirect(url_for('payment.transfer_form'))
                
            # Create transaction record using the existing Transaction model
            transaction_id = str(uuid.uuid4())
            transaction = Transaction()
            transaction.transaction_id = transaction_id
            transaction.user_id = current_user.id
            transaction.amount = float(amount)
            transaction.currency = from_account.currency.value
            transaction.transaction_type = TransactionType.TRANSFER
            transaction.status = TransactionStatus.COMPLETED
            transaction.description = form.description.data or f"Transfer to {to_account_number}"
            transaction.recipient_account = to_account_number
            transaction.recipient_name = to_account.account_name or "Account Holder"
            
            # Update account balances
            from_account.balance -= amount
            from_account.available_balance -= amount
            
            to_account.balance += amount
            to_account.available_balance += amount
            
            # Update last transaction timestamp
            from_account.update_last_transaction()
            to_account.update_last_transaction()
            
            # Save changes
            db.session.add(transaction)
            db.session.commit()
            
            flash(f"Successfully transferred {amount:,.2f} {from_account.currency.name} to {to_account.account_name}.", "success")
            return redirect(url_for('dashboard.account_summary'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Transfer error: {str(e)}")
            flash(f"An error occurred during the transfer: {str(e)}", "danger")
    
    return render_template(
        'payment/transfer.html',
        form=form,
        account_holder=account_holder
    )


@payment_bp.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit_form():
    """Render and process the deposit form"""
    # Get account holder for current user
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    
    # If no account holder exists, redirect to create one
    if not account_holder:
        flash("Please complete your profile before making deposits.", "warning")
        return redirect(url_for('dashboard.welcome'))
    
    # Get all active accounts for the account holder
    accounts = BankAccount.query.filter_by(
        account_holder_id=account_holder.id,
        status=AccountStatus.ACTIVE
    ).all()
    
    if not accounts:
        flash("You don't have any active accounts for deposits.", "warning")
        return redirect(url_for('dashboard.account_summary'))
    
    # Create form with user accounts
    form = DepositForm(user_accounts=accounts)
    
    if form.validate_on_submit():
        try:
            # Get form data
            to_account_number = form.to_account.data
            payment_method_str = form.payment_method.data
            
            # Safely convert amount to Decimal
            if form.amount.data is None:
                flash("Please enter a valid amount", "danger")
                return redirect(url_for('payment.deposit_form'))
            try:
                amount = Decimal(str(form.amount.data))
            except (ValueError, InvalidOperation):
                flash("Invalid amount format", "danger")
                return redirect(url_for('payment.deposit_form'))
            
            # Find the destination account
            to_account = BankAccount.query.filter_by(
                account_number=to_account_number,
                account_holder_id=account_holder.id,
                status=AccountStatus.ACTIVE
            ).first()
            
            if not to_account:
                flash("Destination account not found or not active.", "danger")
                return redirect(url_for('payment.deposit_form'))
                
            # Create transaction record using the existing Transaction model
            transaction_id = str(uuid.uuid4())
            transaction = Transaction()
            transaction.transaction_id = transaction_id
            transaction.user_id = current_user.id
            transaction.amount = float(amount)
            transaction.currency = to_account.currency.value
            transaction.transaction_type = TransactionType.DEPOSIT
            transaction.status = TransactionStatus.COMPLETED
            transaction.description = form.description.data or f"Deposit via {payment_method_str}"
            transaction.recipient_account = to_account.account_number
            transaction.recipient_name = to_account.account_name or "Account Holder"
            
            # Update account balance
            to_account.balance += amount
            to_account.available_balance += amount
            
            # Update last transaction timestamp
            to_account.update_last_transaction()
            
            # Save changes
            db.session.add(transaction)
            db.session.commit()
            
            flash(f"Successfully deposited {amount:,.2f} {to_account.currency.name} to {to_account.account_name}.", "success")
            return redirect(url_for('dashboard.account_summary'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Deposit error: {str(e)}")
            flash(f"An error occurred during the deposit: {str(e)}", "danger")
    
    return render_template(
        'payment/deposit.html',
        form=form,
        account_holder=account_holder
    )