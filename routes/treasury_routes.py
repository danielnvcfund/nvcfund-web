"""
Treasury Management System Routes
This module provides routes for managing treasury functions such as accounts,
transactions, investments, cash flow forecasting, and loans.
"""

import datetime
from decimal import Decimal
from uuid import uuid4

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, func

from app import db
from models import (
    User, FinancialInstitution, Transaction, TransactionStatus, TransactionType,
    TreasuryAccount, TreasuryAccountType, TreasuryTransaction, TreasuryTransactionType,
    TreasuryInvestment, InvestmentType, InvestmentStatus,
    TreasuryLoan, LoanType, LoanStatus, InterestType,
    CashFlowForecast, CashFlowDirection, RecurrenceType
)
from forms import (
    TreasuryAccountForm, TreasuryTransactionForm, TreasuryInvestmentForm,
    TreasuryLoanForm, CashFlowForecastForm, LoanPaymentForm
)
from auth import admin_required
from utils import generate_unique_id, format_currency

# Create Treasury Management blueprint
treasury_bp = Blueprint('treasury', __name__, url_prefix='/treasury')


@treasury_bp.route('/')
@login_required
def dashboard():
    """Treasury Management System Dashboard."""
    
    # Get counts of different entities
    account_count = TreasuryAccount.query.filter_by(is_active=True).count()
    transaction_count = TreasuryTransaction.query.count()
    investment_count = TreasuryInvestment.query.count()
    loan_count = TreasuryLoan.query.count()
    
    # Get total balances by currency
    balances_query = db.session.query(
        TreasuryAccount.currency,
        func.sum(TreasuryAccount.current_balance).label('total_balance')
    ).group_by(TreasuryAccount.currency).all()
    
    # Convert query result to a dictionary for the template
    balances_by_currency = {currency: float(balance) for currency, balance in balances_query}
    
    # Get accounts with low balance warnings
    low_balance_accounts = TreasuryAccount.query.filter(
        TreasuryAccount.minimum_balance.isnot(None),
        TreasuryAccount.current_balance < TreasuryAccount.minimum_balance,
        TreasuryAccount.is_active == True
    ).all()
    
    # Get upcoming cash flows
    upcoming_cash_flows = CashFlowForecast.query.filter(
        CashFlowForecast.transaction_date >= datetime.date.today(),
        CashFlowForecast.transaction_date <= datetime.date.today() + datetime.timedelta(days=30)
    ).order_by(CashFlowForecast.transaction_date).all()
    
    # Get upcoming loan payments
    upcoming_loan_payments = TreasuryLoan.query.filter(
        TreasuryLoan.next_payment_date.isnot(None),
        TreasuryLoan.next_payment_date <= datetime.date.today() + datetime.timedelta(days=30),
        TreasuryLoan.status == 'active'
    ).order_by(TreasuryLoan.next_payment_date).all()
    
    # Get recent transactions
    recent_transactions = TreasuryTransaction.query.order_by(
        desc(TreasuryTransaction.created_at)
    ).limit(5).all()
    
    # Summarize investments by type
    investments_by_type = db.session.query(
        TreasuryInvestment.investment_type,
        func.sum(TreasuryInvestment.amount).label('total_amount')
    ).group_by(TreasuryInvestment.investment_type).all()
    
    # Get accounts by type
    accounts_by_type = {}
    for account_type in TreasuryAccountType:
        accounts_by_type[account_type.name] = TreasuryAccount.query.filter_by(
            account_type=account_type, is_active=True
        ).all()
    
    return render_template(
        'treasury/dashboard.html',
        account_count=account_count,
        transaction_count=transaction_count,
        investment_count=investment_count,
        loan_count=loan_count,
        balances_by_currency=balances_by_currency,
        low_balance_accounts=low_balance_accounts,
        upcoming_cash_flows=upcoming_cash_flows,
        upcoming_loan_payments=upcoming_loan_payments,
        recent_transactions=recent_transactions,
        investments_by_type=investments_by_type,
        accounts_by_type=accounts_by_type
    )


# Account Management Routes
@treasury_bp.route('/accounts')
@login_required
def account_list():
    """List all treasury accounts."""
    accounts = TreasuryAccount.query.order_by(TreasuryAccount.name).all()
    
    # Group accounts by type
    accounts_by_type = {}
    for account_type in TreasuryAccountType:
        accounts_by_type[account_type.name] = [
            account for account in accounts if account.account_type == account_type
        ]
    
    return render_template(
        'treasury/account_list.html',
        accounts=accounts,
        accounts_by_type=accounts_by_type,
        account_types=TreasuryAccountType
    )


@treasury_bp.route('/accounts/new', methods=['GET', 'POST'])
@login_required
def new_account():
    """Create a new treasury account."""
    form = TreasuryAccountForm()
    
    # Populate institution choices
    institutions = FinancialInstitution.query.order_by(FinancialInstitution.name).all()
    form.institution_id.choices = [(0, 'None')] + [(i.id, i.name) for i in institutions]
    
    if form.validate_on_submit():
        account = TreasuryAccount(
            name=form.name.data,
            account_type=form.account_type.data,
            description=form.description.data,
            account_number=form.account_number.data,
            currency=form.currency.data,
            initial_balance=form.initial_balance.data,
            current_balance=form.initial_balance.data,
            available_balance=form.initial_balance.data,
            target_balance=form.target_balance.data,
            minimum_balance=form.minimum_balance.data,
            maximum_balance=form.maximum_balance.data,
            is_active=True,
            created_by_id=current_user.id
        )
        
        if form.institution_id.data > 0:
            account.institution_id = form.institution_id.data
        
        db.session.add(account)
        db.session.commit()
        
        flash(f'Account "{account.name}" has been created successfully.', 'success')
        return redirect(url_for('treasury.view_account', account_id=account.id))
    
    return render_template(
        'treasury/account_form.html',
        form=form,
        is_new=True
    )


@treasury_bp.route('/accounts/<int:account_id>')
@login_required
def view_account(account_id):
    """View a treasury account details."""
    account = TreasuryAccount.query.get_or_404(account_id)
    
    # Get related data
    transactions = TreasuryTransaction.query.filter(
        (TreasuryTransaction.from_account_id == account_id) | 
        (TreasuryTransaction.to_account_id == account_id)
    ).order_by(desc(TreasuryTransaction.created_at)).limit(10).all()
    
    investments = TreasuryInvestment.query.filter_by(account_id=account_id).all()
    
    loans = TreasuryLoan.query.filter_by(account_id=account_id).all()
    
    cash_flows = CashFlowForecast.query.filter_by(account_id=account_id).order_by(
        CashFlowForecast.transaction_date
    ).all()
    
    return render_template(
        'treasury/account_detail.html',
        account=account,
        transactions=transactions,
        investments=investments,
        loans=loans,
        cash_flows=cash_flows
    )


@treasury_bp.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_account(account_id):
    """Edit a treasury account."""
    account = TreasuryAccount.query.get_or_404(account_id)
    form = TreasuryAccountForm(obj=account)
    
    # Populate institution choices
    institutions = FinancialInstitution.query.order_by(FinancialInstitution.name).all()
    form.institution_id.choices = [(0, 'None')] + [(i.id, i.name) for i in institutions]
    
    if form.validate_on_submit():
        # Don't update current or available balance directly through this form
        # as these should be managed by transactions
        account.name = form.name.data
        account.account_type = form.account_type.data
        account.description = form.description.data
        account.account_number = form.account_number.data
        account.currency = form.currency.data
        account.target_balance = form.target_balance.data
        account.minimum_balance = form.minimum_balance.data
        account.maximum_balance = form.maximum_balance.data
        
        if form.institution_id.data > 0:
            account.institution_id = form.institution_id.data
        else:
            account.institution_id = None
        
        db.session.commit()
        
        flash(f'Account "{account.name}" has been updated successfully.', 'success')
        return redirect(url_for('treasury.view_account', account_id=account.id))
    
    return render_template(
        'treasury/account_form.html',
        form=form,
        is_new=False,
        account=account
    )


# Transaction Management Routes
@treasury_bp.route('/transactions')
@login_required
def transaction_list():
    """List all treasury transactions."""
    transactions = TreasuryTransaction.query.order_by(
        desc(TreasuryTransaction.created_at)
    ).all()
    
    return render_template(
        'treasury/transaction_list.html',
        transactions=transactions
    )


@treasury_bp.route('/transactions/new', methods=['GET', 'POST'])
@login_required
def new_transaction():
    """Create a new treasury transaction."""
    form = TreasuryTransactionForm()
    
    # Populate account choices
    accounts = TreasuryAccount.query.filter_by(is_active=True).order_by(TreasuryAccount.name).all()
    # Add an "External Account" option for external transfers
    form.from_account_id.choices = [(0, 'External Account')] + [(a.id, a.name) for a in accounts]
    form.to_account_id.choices = [(0, 'External Account')] + [(a.id, a.name) for a in accounts]
    
    # Pre-select the from_account_id from query string if provided
    from_account_id = request.args.get('from_account_id', type=int)
    if from_account_id and from_account_id in [a.id for a in accounts]:
        form.from_account_id.data = from_account_id
    
    # Pre-select the to_account_id from query string if provided
    to_account_id = request.args.get('to_account_id', type=int)
    if to_account_id and to_account_id in [a.id for a in accounts]:
        form.to_account_id.data = to_account_id
    
    if form.validate_on_submit():
        # Generate a unique transaction reference if not provided
        reference_number = form.reference_number.data
        if not reference_number:
            reference_number = f"TXN-{generate_unique_id()}"
        
        transaction = TreasuryTransaction(
            transaction_id=reference_number,
            transaction_type=form.transaction_type.data,
            amount=form.amount.data,
            currency=form.currency.data,
            exchange_rate=form.exchange_rate.data,
            description=form.description.data,
            memo=form.memo.data,
            reference_number=reference_number,
            status=TransactionStatus.PENDING,
            created_by_id=current_user.id
        )
        
        if form.from_account_id.data > 0:
            transaction.from_account_id = form.from_account_id.data
        
        if form.to_account_id.data > 0:
            transaction.to_account_id = form.to_account_id.data
        
        # Validate that not both from and to accounts are external
        if transaction.from_account_id is None and transaction.to_account_id is None:
            form.from_account_id.errors.append('Both source and destination cannot be external accounts.')
            return render_template(
                'treasury/transaction_form.html',
                form=form,
                is_new=True
            )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'Transaction {transaction.transaction_id} has been created and is pending approval.', 'success')
        return redirect(url_for('treasury.view_transaction', transaction_id=transaction.id))
    
    return render_template(
        'treasury/transaction_form.html',
        form=form,
        is_new=True
    )


@treasury_bp.route('/transactions/<int:transaction_id>')
@login_required
def view_transaction(transaction_id):
    """View a treasury transaction details."""
    transaction = TreasuryTransaction.query.get_or_404(transaction_id)
    
    return render_template(
        'treasury/transaction_detail.html',
        transaction=transaction
    )


@treasury_bp.route('/transactions/<int:transaction_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_transaction(transaction_id):
    """Approve a pending treasury transaction."""
    transaction = TreasuryTransaction.query.get_or_404(transaction_id)
    
    if transaction.status != TransactionStatus.PENDING:
        flash('This transaction cannot be approved because it is not in a pending state.', 'warning')
        return redirect(url_for('treasury.view_transaction', transaction_id=transaction.id))
    
    # Process the transaction and update account balances
    try:
        # Check if from_account has sufficient funds
        if transaction.from_account_id:
            from_account = TreasuryAccount.query.get(transaction.from_account_id)
            if from_account.available_balance < transaction.amount:
                flash('Insufficient funds in the source account.', 'danger')
                return redirect(url_for('treasury.view_transaction', transaction_id=transaction.id))
            
            # Deduct from source account
            from_account.current_balance -= transaction.amount
            from_account.available_balance -= transaction.amount
        
        # Add to destination account
        if transaction.to_account_id:
            to_account = TreasuryAccount.query.get(transaction.to_account_id)
            # If currencies are different, calculate the amount with exchange rate
            if transaction.from_account_id and from_account.currency != to_account.currency:
                converted_amount = transaction.amount * transaction.exchange_rate
            else:
                converted_amount = transaction.amount
            
            to_account.current_balance += converted_amount
            to_account.available_balance += converted_amount
        
        # Update transaction status
        transaction.status = TransactionStatus.COMPLETED
        transaction.approved_at = datetime.datetime.utcnow()
        transaction.approved_by_id = current_user.id
        
        db.session.commit()
        flash('Transaction has been approved and account balances have been updated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving transaction: {str(e)}', 'danger')
    
    return redirect(url_for('treasury.view_transaction', transaction_id=transaction.id))


@treasury_bp.route('/transactions/<int:transaction_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_transaction(transaction_id):
    """Reject a pending treasury transaction."""
    transaction = TreasuryTransaction.query.get_or_404(transaction_id)
    
    if transaction.status != TransactionStatus.PENDING:
        flash('This transaction cannot be rejected because it is not in a pending state.', 'warning')
    else:
        transaction.status = TransactionStatus.REJECTED
        transaction.approved_at = datetime.datetime.utcnow()
        transaction.approved_by_id = current_user.id
        db.session.commit()
        flash('Transaction has been rejected.', 'success')
    
    return redirect(url_for('treasury.view_transaction', transaction_id=transaction.id))


# Investment Management Routes
@treasury_bp.route('/investments')
@login_required
def investment_list():
    """List all treasury investments."""
    investments = TreasuryInvestment.query.order_by(
        desc(TreasuryInvestment.created_at)
    ).all()
    
    return render_template(
        'treasury/investment_list.html',
        investments=investments
    )


@treasury_bp.route('/investments/new', methods=['GET', 'POST'])
@login_required
def new_investment():
    """Create a new treasury investment."""
    form = TreasuryInvestmentForm()
    
    # Populate account choices
    accounts = TreasuryAccount.query.filter_by(is_active=True).order_by(TreasuryAccount.name).all()
    form.account_id.choices = [(a.id, f"{a.name} ({format_currency(a.available_balance, a.currency)})") for a in accounts]
    
    # Pre-select the account_id from query string if provided
    account_id = request.args.get('account_id', type=int)
    if account_id and account_id in [a.id for a in accounts]:
        form.account_id.data = account_id
        # Pre-fill the currency based on the selected account
        account = TreasuryAccount.query.get(account_id)
        if account:
            form.currency.data = account.currency
    
    if form.validate_on_submit():
        account = TreasuryAccount.query.get_or_404(form.account_id.data)
        
        # Check if account has sufficient funds
        if account.available_balance < form.amount.data:
            flash('Insufficient funds in the selected account.', 'danger')
            return render_template(
                'treasury/investment_form.html',
                form=form,
                is_new=True
            )
        
        # Generate a unique investment ID if not provided
        reference_id = f"INV-{generate_unique_id()}"
        
        investment = TreasuryInvestment(
            investment_id=reference_id,
            account_id=form.account_id.data,
            investment_type=form.investment_type.data,
            counterparty=form.counterparty.data,
            amount=form.amount.data,
            currency=form.currency.data,
            interest_rate=form.interest_rate.data,
            start_date=form.start_date.data,
            maturity_date=form.maturity_date.data,
            description=form.description.data,
            status=InvestmentStatus.PENDING,
            created_by_id=current_user.id
        )
        
        # Create associated transaction
        transaction = TreasuryTransaction(
            transaction_id=f"TXN-{reference_id}",
            transaction_type=TreasuryTransactionType.INVESTMENT_PURCHASE,
            from_account_id=account.id,
            amount=form.amount.data,
            currency=form.currency.data,
            description=f"Investment purchase: {form.investment_type.data.value}",
            reference_number=reference_id,
            status=TransactionStatus.PENDING,
            created_by_id=current_user.id
        )
        
        db.session.add(investment)
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'Investment {investment.investment_id} has been created and is pending approval.', 'success')
        return redirect(url_for('treasury.view_investment', investment_id=investment.id))
    
    return render_template(
        'treasury/investment_form.html',
        form=form,
        is_new=True
    )


@treasury_bp.route('/investments/<int:investment_id>')
@login_required
def view_investment(investment_id):
    """View a treasury investment details."""
    investment = TreasuryInvestment.query.get_or_404(investment_id)
    
    # Get related transactions
    transactions = TreasuryTransaction.query.filter_by(
        reference_number=investment.investment_id
    ).order_by(desc(TreasuryTransaction.created_at)).all()
    
    return render_template(
        'treasury/investment_detail.html',
        investment=investment,
        transactions=transactions
    )


@treasury_bp.route('/investments/<int:investment_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_investment(investment_id):
    """Approve a pending investment."""
    investment = TreasuryInvestment.query.get_or_404(investment_id)
    
    if investment.status != InvestmentStatus.PENDING:
        flash('This investment cannot be approved because it is not in a pending state.', 'warning')
        return redirect(url_for('treasury.view_investment', investment_id=investment.id))
    
    try:
        # Get the associated transaction
        transaction = TreasuryTransaction.query.filter_by(
            reference_number=investment.investment_id,
            transaction_type=TreasuryTransactionType.INVESTMENT_PURCHASE
        ).first()
        
        if transaction and transaction.status == TransactionStatus.PENDING:
            # Update account balance
            account = TreasuryAccount.query.get(investment.account_id)
            if account.available_balance < investment.amount:
                flash('Insufficient funds in the account.', 'danger')
                return redirect(url_for('treasury.view_investment', investment_id=investment.id))
            
            account.current_balance -= investment.amount
            account.available_balance -= investment.amount
            
            # Update transaction and investment status
            transaction.status = TransactionStatus.COMPLETED
            transaction.approved_at = datetime.datetime.utcnow()
            transaction.approved_by_id = current_user.id
            
            investment.status = InvestmentStatus.ACTIVE
            investment.approved_at = datetime.datetime.utcnow()
            investment.approved_by_id = current_user.id
            
            db.session.commit()
            flash('Investment has been approved and account balance has been updated.', 'success')
        else:
            flash('No pending transaction found for this investment.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving investment: {str(e)}', 'danger')
    
    return redirect(url_for('treasury.view_investment', investment_id=investment.id))


@treasury_bp.route('/investments/<int:investment_id>/mature', methods=['POST'])
@login_required
@admin_required
def mature_investment(investment_id):
    """Mark an investment as matured and process the return of funds."""
    investment = TreasuryInvestment.query.get_or_404(investment_id)
    
    if investment.status != InvestmentStatus.ACTIVE:
        flash('This investment cannot be matured because it is not in an active state.', 'warning')
        return redirect(url_for('treasury.view_investment', investment_id=investment.id))
    
    try:
        # Calculate maturity value
        maturity_value = investment.calculate_maturity_value()
        interest_earned = maturity_value - investment.amount
        
        # Create maturity transaction
        transaction = TreasuryTransaction(
            transaction_id=f"MTR-{investment.investment_id}",
            transaction_type=TreasuryTransactionType.INVESTMENT_MATURITY,
            to_account_id=investment.account_id,
            amount=maturity_value,
            currency=investment.currency,
            description=f"Investment maturity: {investment.investment_type.value} - Principal: {format_currency(investment.amount, investment.currency)}, Interest: {format_currency(interest_earned, investment.currency)}",
            reference_number=investment.investment_id,
            status=TransactionStatus.COMPLETED,
            created_by_id=current_user.id,
            approved_at=datetime.datetime.utcnow(),
            approved_by_id=current_user.id
        )
        
        # Update account balance
        account = TreasuryAccount.query.get(investment.account_id)
        account.current_balance += maturity_value
        account.available_balance += maturity_value
        
        # Update investment status
        investment.status = InvestmentStatus.COMPLETED
        investment.actual_maturity_date = datetime.date.today()
        investment.return_amount = maturity_value
        
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'Investment has been matured successfully. {format_currency(maturity_value, investment.currency)} has been returned to the account.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing investment maturity: {str(e)}', 'danger')
    
    return redirect(url_for('treasury.view_investment', investment_id=investment.id))


# Loan Management Routes
@treasury_bp.route('/loans')
@login_required
def loan_list():
    """List all treasury loans."""
    loans = TreasuryLoan.query.order_by(
        desc(TreasuryLoan.created_at)
    ).all()
    
    return render_template(
        'treasury/loan_list.html',
        loans=loans
    )


@treasury_bp.route('/loans/new', methods=['GET', 'POST'])
@login_required
def new_loan():
    """Create a new treasury loan."""
    form = TreasuryLoanForm()
    
    # Populate account choices
    accounts = TreasuryAccount.query.filter_by(is_active=True).order_by(TreasuryAccount.name).all()
    form.account_id.choices = [(a.id, a.name) for a in accounts]
    
    # Populate financial institution choices
    institutions = FinancialInstitution.query.order_by(FinancialInstitution.name).all()
    form.lender_institution_id.choices = [(i.id, i.name) for i in institutions]
    
    # Pre-select the account_id from query string if provided
    account_id = request.args.get('account_id', type=int)
    if account_id and account_id in [a.id for a in accounts]:
        form.account_id.data = account_id
        # Pre-fill the currency based on the selected account
        account = TreasuryAccount.query.get(account_id)
        if account:
            form.currency.data = account.currency
    
    if form.validate_on_submit():
        # Use provided loan ID or generate a unique one
        loan_id = form.loan_id.data if form.loan_id.data else f"LOAN-{generate_unique_id()}"
        
        # Get the financial institution data
        lender_institution = FinancialInstitution.query.get(form.lender_institution_id.data)
        
        loan = TreasuryLoan(
            loan_id=loan_id,
            name=form.name.data,
            account_id=form.account_id.data,
            loan_type=form.loan_type.data,
            principal_amount=form.principal_amount.data,
            outstanding_amount=form.principal_amount.data,
            currency=form.currency.data,
            interest_type=form.interest_type.data,
            interest_rate=form.interest_rate.data,
            reference_rate=form.reference_rate.data,
            margin=form.margin.data,
            payment_frequency=form.payment_frequency.data,
            start_date=form.start_date.data,
            maturity_date=form.maturity_date.data,
            next_payment_date=form.first_payment_date.data,
            next_payment_amount=form.payment_amount.data,
            lender_institution_id=form.lender_institution_id.data,
            description=form.description.data,
            collateral_description=form.collateral_description.data,
            status=LoanStatus(form.status.data)
        )
        
        # Create loan disbursement transaction
        lender_name = lender_institution.name if lender_institution else "Unknown Lender"
        transaction = TreasuryTransaction(
            transaction_id=f"TXN-{loan_id}",
            transaction_type=TreasuryTransactionType.LOAN_DISBURSEMENT,
            to_account_id=form.account_id.data,
            amount=form.principal_amount.data,
            currency=form.currency.data,
            description=f"Loan disbursement: {form.loan_type.data.value} from {lender_name}",
            reference_number=loan_id,
            status=TransactionStatus.PENDING,
            created_by_id=current_user.id
        )
        
        db.session.add(loan)
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'Loan {loan.loan_id} has been created successfully.', 'success')
        return redirect(url_for('treasury.view_loan', loan_id=loan.id))
    
    return render_template(
        'treasury/loan_form.html',
        form=form,
        is_new=True
    )


@treasury_bp.route('/loans/<int:loan_id>')
@login_required
def view_loan(loan_id):
    """View a treasury loan details."""
    loan = TreasuryLoan.query.get_or_404(loan_id)
    
    # Get related transactions
    transactions = TreasuryTransaction.query.filter_by(
        reference_number=loan.loan_id
    ).order_by(desc(TreasuryTransaction.created_at)).all()
    
    return render_template(
        'treasury/loan_detail.html',
        loan=loan,
        transactions=transactions
    )


@treasury_bp.route('/loans/<int:loan_id>/disburse', methods=['POST'])
@login_required
@admin_required
def disburse_loan(loan_id):
    """Approve and disburse a loan to the designated account."""
    loan = TreasuryLoan.query.get_or_404(loan_id)
    
    # Find the pending disbursement transaction
    transaction = TreasuryTransaction.query.filter_by(
        reference_number=loan.loan_id,
        transaction_type=TreasuryTransactionType.LOAN_DISBURSEMENT,
        status=TransactionStatus.PENDING
    ).first()
    
    if not transaction:
        flash('No pending disbursement transaction found for this loan.', 'warning')
        return redirect(url_for('treasury.view_loan', loan_id=loan.id))
    
    try:
        # Update account balance
        account = TreasuryAccount.query.get(loan.account_id)
        account.current_balance += loan.principal_amount
        account.available_balance += loan.principal_amount
        
        # Update transaction status
        transaction.status = TransactionStatus.COMPLETED
        transaction.approved_at = datetime.datetime.utcnow()
        transaction.approved_by_id = current_user.id
        
        db.session.commit()
        flash(f'Loan has been disbursed successfully. {format_currency(loan.principal_amount, loan.currency)} has been added to the account.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error disbursing loan: {str(e)}', 'danger')
    
    return redirect(url_for('treasury.view_loan', loan_id=loan.id))


@treasury_bp.route('/loans/<int:loan_id>/payment', methods=['GET', 'POST'])
@login_required
def make_loan_payment(loan_id):
    """Make a payment towards a loan."""
    loan = TreasuryLoan.query.get_or_404(loan_id)
    
    # Check if loan is active
    if loan.status != 'active':
        flash('Payments can only be made on active loans.', 'warning')
        return redirect(url_for('treasury.view_loan', loan_id=loan.id))
    
    form = LoanPaymentForm()
    
    # Populate account choices
    accounts = TreasuryAccount.query.filter_by(is_active=True).order_by(TreasuryAccount.name).all()
    form.from_account_id.choices = [(a.id, f"{a.name} ({format_currency(a.available_balance, a.currency)})") for a in accounts]
    
    # Pre-fill with suggested values
    if request.method == 'GET':
        form.payment_amount.data = loan.next_payment_amount or 0
        form.principal_amount.data = loan.calculate_principal_payment(form.payment_amount.data)
        form.interest_amount.data = loan.calculate_interest_payment(form.payment_amount.data)
    
    if form.validate_on_submit():
        account = TreasuryAccount.query.get_or_404(form.from_account_id.data)
        
        # Check if account has sufficient funds
        if account.available_balance < form.payment_amount.data:
            flash('Insufficient funds in the selected account.', 'danger')
            return render_template(
                'treasury/loan_payment_form.html',
                form=form,
                loan=loan
            )
        
        # Create payment transaction
        transaction = TreasuryTransaction(
            transaction_id=f"LPMT-{generate_unique_id()}",
            transaction_type=TreasuryTransactionType.LOAN_PAYMENT,
            from_account_id=form.from_account_id.data,
            amount=form.payment_amount.data,
            currency=loan.currency,
            description=f"Loan payment for {loan.loan_id}: Principal: {format_currency(form.principal_amount.data, loan.currency)}, Interest: {format_currency(form.interest_amount.data, loan.currency)}",
            reference_number=loan.loan_id,
            status=TransactionStatus.PENDING,
            created_by_id=current_user.id
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash('Loan payment has been created and is pending approval.', 'success')
        return redirect(url_for('treasury.view_loan', loan_id=loan.id))
    
    return render_template(
        'treasury/loan_payment_form.html',
        form=form,
        loan=loan
    )


@treasury_bp.route('/loans/<int:loan_id>/payment/<int:transaction_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_loan_payment(loan_id, transaction_id):
    """Approve a pending loan payment."""
    loan = TreasuryLoan.query.get_or_404(loan_id)
    transaction = TreasuryTransaction.query.get_or_404(transaction_id)
    
    if transaction.status != TransactionStatus.PENDING or transaction.transaction_type != TreasuryTransactionType.LOAN_PAYMENT:
        flash('Invalid transaction for loan payment approval.', 'warning')
        return redirect(url_for('treasury.view_loan', loan_id=loan.id))
    
    try:
        # Update account balance
        account = TreasuryAccount.query.get(transaction.from_account_id)
        account.current_balance -= transaction.amount
        account.available_balance -= transaction.amount
        
        # Extract principal and interest from description
        # This is a simplification - in a real system, these would be stored as separate fields
        principal_amount = Decimal(str(transaction.amount)) * Decimal('0.8')  # Assume 80% principal for demo
        interest_amount = transaction.amount - principal_amount
        
        # Update loan details
        loan.outstanding_amount -= principal_amount
        loan.total_payments = (loan.total_payments or 0) + transaction.amount
        loan.total_interest_paid = (loan.total_interest_paid or 0) + interest_amount
        
        # Update loan status if fully paid
        if loan.outstanding_amount <= 0:
            loan.status = 'paid'
            loan.next_payment_date = None
            loan.next_payment_amount = None
            flash('Loan has been fully paid off!', 'success')
        else:
            # Calculate next payment date and amount
            if loan.payment_frequency == 'monthly':
                loan.next_payment_date = (loan.next_payment_date or datetime.date.today()) + datetime.timedelta(days=30)
            elif loan.payment_frequency == 'quarterly':
                loan.next_payment_date = (loan.next_payment_date or datetime.date.today()) + datetime.timedelta(days=90)
            elif loan.payment_frequency == 'semi_annual':
                loan.next_payment_date = (loan.next_payment_date or datetime.date.today()) + datetime.timedelta(days=182)
            elif loan.payment_frequency == 'annual':
                loan.next_payment_date = (loan.next_payment_date or datetime.date.today()) + datetime.timedelta(days=365)
        
        # Update transaction status
        transaction.status = TransactionStatus.COMPLETED
        transaction.approved_at = datetime.datetime.utcnow()
        transaction.approved_by_id = current_user.id
        
        db.session.commit()
        flash('Loan payment has been approved and processed successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing loan payment: {str(e)}', 'danger')
    
    return redirect(url_for('treasury.view_loan', loan_id=loan.id))


# Cash Flow Management Routes
@treasury_bp.route('/cash-flows')
@login_required
def cash_flow_list():
    """List all cash flow forecasts."""
    cash_flows = CashFlowForecast.query.order_by(
        CashFlowForecast.transaction_date
    ).all()
    
    return render_template(
        'treasury/cash_flow_list.html',
        cash_flows=cash_flows
    )


@treasury_bp.route('/cash-flows/new', methods=['GET', 'POST'])
@login_required
def new_cash_flow():
    """Create a new cash flow forecast."""
    form = CashFlowForecastForm()
    
    # Populate account choices
    accounts = TreasuryAccount.query.filter_by(is_active=True).order_by(TreasuryAccount.name).all()
    form.account_id.choices = [(a.id, a.name) for a in accounts]
    
    # Pre-select the account_id from query string if provided
    account_id = request.args.get('account_id', type=int)
    if account_id and account_id in [a.id for a in accounts]:
        form.account_id.data = account_id
        # Pre-fill the currency based on the selected account
        account = TreasuryAccount.query.get(account_id)
        if account:
            form.currency.data = account.currency
    
    if form.validate_on_submit():
        cash_flow = CashFlowForecast(
            account_id=form.account_id.data,
            transaction_date=form.transaction_date.data,
            direction=form.direction.data,
            amount=form.amount.data,
            currency=form.currency.data,
            probability=form.probability.data,
            category=form.category.data,
            source_description=form.source_description.data,
            recurrence_type=form.recurrence_type.data,
            recurrence_end_date=form.recurrence_end_date.data,
            notes=form.notes.data,
            created_by_id=current_user.id
        )
        
        db.session.add(cash_flow)
        
        # If this is a recurring forecast, create additional entries
        if form.recurrence_type.data != RecurrenceType.NONE and form.recurrence_end_date.data:
            start_date = form.transaction_date.data
            end_date = form.recurrence_end_date.data
            current_date = start_date
            
            if form.recurrence_type.data == RecurrenceType.DAILY:
                delta = datetime.timedelta(days=1)
            elif form.recurrence_type.data == RecurrenceType.WEEKLY:
                delta = datetime.timedelta(weeks=1)
            elif form.recurrence_type.data == RecurrenceType.MONTHLY:
                # Use the same day of next month
                delta = datetime.timedelta(days=30)  # Approximate for simplicity
            elif form.recurrence_type.data == RecurrenceType.QUARTERLY:
                delta = datetime.timedelta(days=90)  # Approximate for simplicity
            elif form.recurrence_type.data == RecurrenceType.ANNUAL:
                delta = datetime.timedelta(days=365)  # Approximate for simplicity
            
            current_date += delta
            while current_date <= end_date:
                recurring_cash_flow = CashFlowForecast(
                    account_id=form.account_id.data,
                    transaction_date=current_date,
                    direction=form.direction.data,
                    amount=form.amount.data,
                    currency=form.currency.data,
                    probability=form.probability.data,
                    category=form.category.data,
                    source_description=form.source_description.data,
                    recurrence_type=form.recurrence_type.data,
                    recurrence_end_date=form.recurrence_end_date.data,
                    notes=form.notes.data,
                    created_by_id=current_user.id
                )
                db.session.add(recurring_cash_flow)
                current_date += delta
        
        db.session.commit()
        
        flash('Cash flow forecast has been created successfully.', 'success')
        return redirect(url_for('treasury.cash_flow_list'))
    
    return render_template(
        'treasury/cash_flow_form.html',
        form=form,
        is_new=True
    )