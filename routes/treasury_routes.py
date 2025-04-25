"""
Treasury Management System Routes
This module provides routes for the Treasury Management System functionality.
"""

import logging
import secrets
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc

from app import db
from models import (
    TreasuryAccount, TreasuryAccountType, TreasuryInvestment, InvestmentType,
    TreasuryTransaction, TreasuryTransactionType, CashFlowForecast, 
    CashFlowDirection, RecurrenceType, TreasuryLoan, LoanType, InterestType,
    PaymentFrequency, TreasuryLoanPayment, TransactionStatus, FinancialInstitution
)
from auth import admin_required
from forms import (
    TreasuryAccountForm, TreasuryInvestmentForm, TreasuryTransactionForm,
    CashFlowForecastForm, TreasuryLoanForm, TreasuryLoanPaymentForm
)

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
treasury_bp = Blueprint('treasury', __name__, url_prefix='/treasury')

# Treasury Dashboard
@treasury_bp.route('/')
@login_required
def treasury_dashboard():
    """Treasury management dashboard view"""
    # Get account summaries
    accounts = TreasuryAccount.query.all()
    
    # Calculate total balances by currency
    balances_by_currency = {}
    for account in accounts:
        if account.currency in balances_by_currency:
            balances_by_currency[account.currency] += account.current_balance
        else:
            balances_by_currency[account.currency] = account.current_balance
            
    # Get recent transactions
    recent_transactions = TreasuryTransaction.query.order_by(
        desc(TreasuryTransaction.created_at)
    ).limit(5).all()
    
    # Get upcoming loan payments
    upcoming_loans = TreasuryLoan.query.filter(
        TreasuryLoan.next_payment_date <= datetime.utcnow() + timedelta(days=30)
    ).order_by(TreasuryLoan.next_payment_date).limit(5).all()
    
    # Get pending cash flows
    upcoming_cash_flows = CashFlowForecast.query.filter(
        CashFlowForecast.transaction_date <= datetime.utcnow() + timedelta(days=30)
    ).order_by(CashFlowForecast.transaction_date).limit(5).all()
    
    # Get maturing investments
    maturing_investments = TreasuryInvestment.query.filter(
        TreasuryInvestment.maturity_date <= datetime.utcnow() + timedelta(days=30)
    ).order_by(TreasuryInvestment.maturity_date).limit(5).all()
    
    return render_template(
        'treasury/dashboard.html',
        accounts=accounts,
        balances_by_currency=balances_by_currency,
        recent_transactions=recent_transactions,
        upcoming_loans=upcoming_loans,
        upcoming_cash_flows=upcoming_cash_flows,
        maturing_investments=maturing_investments
    )

# Treasury Accounts
@treasury_bp.route('/accounts')
@login_required
def account_list():
    """List all treasury accounts"""
    accounts = TreasuryAccount.query.all()
    return render_template('treasury/account_list.html', accounts=accounts)

@treasury_bp.route('/accounts/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_account():
    """Create a new treasury account"""
    form = TreasuryAccountForm()
    
    # Load financial institutions for dropdown
    institutions = FinancialInstitution.query.all()
    form.institution_id.choices = [(i.id, i.name) for i in institutions]
    
    if form.validate_on_submit():
        account = TreasuryAccount(
            name=form.name.data,
            description=form.description.data,
            account_type=form.account_type.data,
            institution_id=form.institution_id.data,
            account_number=form.account_number.data,
            currency=form.currency.data,
            current_balance=form.initial_balance.data,
            available_balance=form.initial_balance.data,
            target_balance=form.target_balance.data,
            minimum_balance=form.minimum_balance.data,
            maximum_balance=form.maximum_balance.data
        )
        
        db.session.add(account)
        db.session.commit()
        
        flash(f"Treasury account '{account.name}' created successfully", "success")
        return redirect(url_for('treasury.account_list'))
        
    return render_template('treasury/account_form.html', form=form, is_new=True)

@treasury_bp.route('/accounts/<int:account_id>')
@login_required
def view_account(account_id):
    """View a treasury account details"""
    account = TreasuryAccount.query.get_or_404(account_id)
    
    # Get related data
    transactions = TreasuryTransaction.query.filter(
        (TreasuryTransaction.from_account_id == account_id) | 
        (TreasuryTransaction.to_account_id == account_id)
    ).order_by(desc(TreasuryTransaction.created_at)).limit(10).all()
    
    investments = TreasuryInvestment.query.filter_by(
        account_id=account_id
    ).order_by(desc(TreasuryInvestment.created_at)).all()
    
    loans = TreasuryLoan.query.filter_by(
        account_id=account_id
    ).order_by(desc(TreasuryLoan.created_at)).all()
    
    cash_flows = CashFlowForecast.query.filter_by(
        account_id=account_id
    ).order_by(CashFlowForecast.transaction_date).all()
    
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
@admin_required
def edit_account(account_id):
    """Edit a treasury account"""
    account = TreasuryAccount.query.get_or_404(account_id)
    form = TreasuryAccountForm(obj=account)
    
    # Load financial institutions for dropdown
    institutions = FinancialInstitution.query.all()
    form.institution_id.choices = [(i.id, i.name) for i in institutions]
    
    if form.validate_on_submit():
        form.populate_obj(account)
        db.session.commit()
        
        flash(f"Treasury account '{account.name}' updated successfully", "success")
        return redirect(url_for('treasury.view_account', account_id=account.id))
        
    return render_template('treasury/account_form.html', form=form, is_new=False, account=account)

# Treasury Investments
@treasury_bp.route('/investments')
@login_required
def investment_list():
    """List all treasury investments"""
    investments = TreasuryInvestment.query.all()
    return render_template('treasury/investment_list.html', investments=investments)

@treasury_bp.route('/investments/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_investment():
    """Create a new treasury investment"""
    form = TreasuryInvestmentForm()
    
    # Load accounts for dropdown
    accounts = TreasuryAccount.query.all()
    form.account_id.choices = [(a.id, a.name) for a in accounts]
    
    # Load institutions for dropdown
    institutions = FinancialInstitution.query.all()
    form.institution_id.choices = [(i.id, i.name) for i in institutions]
    
    if form.validate_on_submit():
        # Generate a unique investment ID
        investment_id = f"INV-{secrets.token_hex(5).upper()}"
        
        investment = TreasuryInvestment(
            investment_id=investment_id,
            account_id=form.account_id.data,
            investment_type=form.investment_type.data,
            amount=form.amount.data,
            currency=form.currency.data,
            interest_rate=form.interest_rate.data,
            start_date=form.start_date.data,
            maturity_date=form.maturity_date.data,
            institution_id=form.institution_id.data,
            description=form.description.data,
            status=TransactionStatus.COMPLETED if form.is_active.data else TransactionStatus.PENDING
        )
        
        db.session.add(investment)
        
        # If investment is active, deduct from account balance
        if form.is_active.data:
            account = TreasuryAccount.query.get(form.account_id.data)
            if account:
                account.current_balance -= form.amount.data
                account.available_balance -= form.amount.data
        
        db.session.commit()
        
        flash(f"Investment '{investment_id}' created successfully", "success")
        return redirect(url_for('treasury.investment_list'))
        
    return render_template('treasury/investment_form.html', form=form, is_new=True)

@treasury_bp.route('/investments/<int:investment_id>')
@login_required
def view_investment(investment_id):
    """View a treasury investment details"""
    investment = TreasuryInvestment.query.get_or_404(investment_id)
    
    # Calculate current value
    current_value = investment.calculate_maturity_value()
    days_to_maturity = (investment.maturity_date - datetime.utcnow()).days
    
    return render_template(
        'treasury/investment_detail.html',
        investment=investment,
        current_value=current_value,
        days_to_maturity=max(0, days_to_maturity)
    )

# Treasury Transactions
@treasury_bp.route('/transactions')
@login_required
def transaction_list():
    """List all treasury transactions"""
    transactions = TreasuryTransaction.query.order_by(
        desc(TreasuryTransaction.created_at)
    ).all()
    return render_template('treasury/transaction_list.html', transactions=transactions)

@treasury_bp.route('/transactions/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_transaction():
    """Create a new treasury transaction"""
    form = TreasuryTransactionForm()
    
    # Load accounts for dropdown
    accounts = TreasuryAccount.query.all()
    form.from_account_id.choices = [(0, 'External Account')] + [(a.id, a.name) for a in accounts]
    form.to_account_id.choices = [(0, 'External Account')] + [(a.id, a.name) for a in accounts]
    
    if form.validate_on_submit():
        # Generate a unique transaction ID
        transaction_id = f"TRX-{secrets.token_hex(5).upper()}"
        
        transaction = TreasuryTransaction(
            transaction_id=transaction_id,
            from_account_id=form.from_account_id.data if form.from_account_id.data > 0 else None,
            to_account_id=form.to_account_id.data if form.to_account_id.data > 0 else None,
            transaction_type=form.transaction_type.data,
            amount=form.amount.data,
            currency=form.currency.data,
            exchange_rate=form.exchange_rate.data,
            status=TransactionStatus.PENDING,
            description=form.description.data,
            reference_number=form.reference_number.data,
            memo=form.memo.data,
            created_by=current_user.id
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash(f"Transaction '{transaction_id}' created successfully", "success")
        return redirect(url_for('treasury.transaction_list'))
        
    return render_template('treasury/transaction_form.html', form=form, is_new=True)

@treasury_bp.route('/transactions/<int:transaction_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_transaction(transaction_id):
    """Approve a treasury transaction"""
    transaction = TreasuryTransaction.query.get_or_404(transaction_id)
    
    if transaction.status != TransactionStatus.PENDING:
        flash("This transaction has already been processed", "warning")
        return redirect(url_for('treasury.view_transaction', transaction_id=transaction.id))
    
    # Process the transaction
    success = transaction.process_transaction()
    
    if success:
        transaction.approval_user_id = current_user.id
        transaction.approval_date = datetime.utcnow()
        db.session.commit()
        
        flash("Transaction approved and processed successfully", "success")
    else:
        flash("Failed to process the transaction", "danger")
    
    return redirect(url_for('treasury.view_transaction', transaction_id=transaction.id))

@treasury_bp.route('/transactions/<int:transaction_id>')
@login_required
def view_transaction(transaction_id):
    """View a treasury transaction details"""
    transaction = TreasuryTransaction.query.get_or_404(transaction_id)
    return render_template('treasury/transaction_detail.html', transaction=transaction)

# Cash Flow Forecasting
@treasury_bp.route('/cash-flows')
@login_required
def cash_flow_list():
    """List all cash flow forecasts"""
    cash_flows = CashFlowForecast.query.order_by(
        CashFlowForecast.transaction_date
    ).all()
    return render_template('treasury/cash_flow_list.html', cash_flows=cash_flows)

@treasury_bp.route('/cash-flows/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_cash_flow():
    """Create a new cash flow forecast"""
    form = CashFlowForecastForm()
    
    # Load accounts for dropdown
    accounts = TreasuryAccount.query.all()
    form.account_id.choices = [(a.id, a.name) for a in accounts]
    
    if form.validate_on_submit():
        cash_flow = CashFlowForecast(
            account_id=form.account_id.data,
            direction=form.direction.data,
            amount=form.amount.data,
            currency=form.currency.data,
            transaction_date=form.transaction_date.data,
            recurrence_type=form.recurrence_type.data,
            recurrence_end_date=form.recurrence_end_date.data,
            source_description=form.source_description.data,
            category=form.category.data,
            probability=form.probability.data,
            notes=form.notes.data
        )
        
        db.session.add(cash_flow)
        db.session.commit()
        
        flash("Cash flow forecast created successfully", "success")
        return redirect(url_for('treasury.cash_flow_list'))
        
    return render_template('treasury/cash_flow_form.html', form=form, is_new=True)

# Treasury Loans
@treasury_bp.route('/loans')
@login_required
def loan_list():
    """List all treasury loans"""
    loans = TreasuryLoan.query.all()
    return render_template('treasury/loan_list.html', loans=loans)

@treasury_bp.route('/loans/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_loan():
    """Create a new treasury loan"""
    form = TreasuryLoanForm()
    
    # Load accounts for dropdown
    accounts = TreasuryAccount.query.all()
    form.account_id.choices = [(a.id, a.name) for a in accounts]
    
    # Load institutions for dropdown
    institutions = FinancialInstitution.query.all()
    form.lender_institution_id.choices = [(i.id, i.name) for i in institutions]
    
    if form.validate_on_submit():
        # Generate a unique loan ID
        loan_id = f"LOAN-{secrets.token_hex(5).upper()}"
        
        loan = TreasuryLoan(
            loan_id=loan_id,
            account_id=form.account_id.data,
            loan_type=form.loan_type.data,
            principal_amount=form.principal_amount.data,
            outstanding_amount=form.principal_amount.data,
            currency=form.currency.data,
            interest_type=form.interest_type.data,
            interest_rate=form.interest_rate.data,
            reference_rate=form.reference_rate.data,
            margin=form.margin.data,
            start_date=form.start_date.data,
            maturity_date=form.maturity_date.data,
            payment_frequency=form.payment_frequency.data,
            next_payment_date=form.first_payment_date.data,
            next_payment_amount=form.payment_amount.data,
            lender_institution_id=form.lender_institution_id.data,
            status=form.status.data,
            description=form.description.data,
            collateral_description=form.collateral_description.data
        )
        
        db.session.add(loan)
        
        # If loan is active, add to account balance
        if form.status.data == 'active':
            account = TreasuryAccount.query.get(form.account_id.data)
            if account:
                account.current_balance += form.principal_amount.data
                account.available_balance += form.principal_amount.data
        
        db.session.commit()
        
        flash(f"Loan '{loan_id}' created successfully", "success")
        return redirect(url_for('treasury.loan_list'))
        
    return render_template('treasury/loan_form.html', form=form, is_new=True)

@treasury_bp.route('/loans/<int:loan_id>')
@login_required
def view_loan(loan_id):
    """View a treasury loan details"""
    loan = TreasuryLoan.query.get_or_404(loan_id)
    
    # Get loan payments
    payments = TreasuryLoanPayment.query.filter_by(loan_id=loan_id).order_by(
        TreasuryLoanPayment.payment_date
    ).all()
    
    # Calculate current interest due
    current_interest = loan.calculate_interest_due()
    days_to_next_payment = (loan.next_payment_date - datetime.utcnow()).days if loan.next_payment_date else None
    
    return render_template(
        'treasury/loan_detail.html',
        loan=loan,
        payments=payments,
        current_interest=current_interest,
        days_to_next_payment=days_to_next_payment
    )

@treasury_bp.route('/loans/<int:loan_id>/payment', methods=['GET', 'POST'])
@login_required
@admin_required
def make_loan_payment(loan_id):
    """Make a payment on a treasury loan"""
    loan = TreasuryLoan.query.get_or_404(loan_id)
    form = TreasuryLoanPaymentForm()
    
    if form.validate_on_submit():
        # Make the payment
        payment = loan.make_payment(form.payment_amount.data, form.payment_date.data)
        payment.notes = form.notes.data
        
        # Create a transaction record for the payment
        transaction_id = f"LOAN-PMT-{secrets.token_hex(5).upper()}"
        transaction = TreasuryTransaction(
            transaction_id=transaction_id,
            from_account_id=loan.account_id,
            transaction_type=TreasuryTransactionType.LOAN_PAYMENT,
            amount=form.payment_amount.data,
            currency=loan.currency,
            status=TransactionStatus.COMPLETED,
            execution_date=form.payment_date.data,
            description=f"Loan payment for {loan.loan_id}",
            memo=form.notes.data,
            created_by=current_user.id,
            approval_user_id=current_user.id,
            approval_date=datetime.utcnow()
        )
        
        # Link the payment to the transaction
        payment.transaction_id = transaction.id
        
        # Update the account balance
        account = TreasuryAccount.query.get(loan.account_id)
        if account:
            account.current_balance -= form.payment_amount.data
            account.available_balance -= form.payment_amount.data
        
        db.session.add(payment)
        db.session.add(transaction)
        db.session.commit()
        
        flash("Loan payment recorded successfully", "success")
        return redirect(url_for('treasury.view_loan', loan_id=loan.id))
        
    # Pre-fill the form with default values
    form.payment_date.data = datetime.utcnow()
    form.payment_amount.data = loan.next_payment_amount
    
    return render_template(
        'treasury/loan_payment_form.html',
        form=form,
        loan=loan
    )

# API Endpoints for Charts and Reports
@treasury_bp.route('/api/account-balances')
@login_required
def api_account_balances():
    """API endpoint for account balances data"""
    accounts = TreasuryAccount.query.all()
    data = [
        {
            'name': account.name,
            'balance': account.current_balance,
            'currency': account.currency,
            'account_type': account.account_type.value
        }
        for account in accounts
    ]
    
    return jsonify(data)

@treasury_bp.route('/api/cash-flow-forecast')
@login_required
def api_cash_flow_forecast():
    """API endpoint for cash flow forecast data"""
    # Get date range from request or default to next 90 days
    days = request.args.get('days', 90, type=int)
    end_date = datetime.utcnow() + timedelta(days=days)
    
    cash_flows = CashFlowForecast.query.filter(
        CashFlowForecast.transaction_date <= end_date
    ).order_by(CashFlowForecast.transaction_date).all()
    
    # Group by date and direction
    data = {}
    for cf in cash_flows:
        date_str = cf.transaction_date.strftime('%Y-%m-%d')
        if date_str not in data:
            data[date_str] = {'date': date_str, 'inflow': 0, 'outflow': 0}
        
        if cf.direction == CashFlowDirection.INFLOW:
            data[date_str]['inflow'] += cf.amount * (cf.probability / 100)
        else:
            data[date_str]['outflow'] += cf.amount * (cf.probability / 100)
    
    # Convert to list and sort by date
    result = list(data.values())
    result.sort(key=lambda x: x['date'])
    
    return jsonify(result)

@treasury_bp.route('/api/loan-schedule/<int:loan_id>')
@login_required
def api_loan_schedule(loan_id):
    """API endpoint for loan repayment schedule"""
    loan = TreasuryLoan.query.get_or_404(loan_id)
    
    # Generate the payment schedule
    schedule = []
    
    # Simple amortization schedule calculation
    if loan.payment_frequency == PaymentFrequency.MONTHLY:
        payment_interval = 30  # days
    elif loan.payment_frequency == PaymentFrequency.QUARTERLY:
        payment_interval = 90  # days
    elif loan.payment_frequency == PaymentFrequency.SEMI_ANNUAL:
        payment_interval = 182  # days
    else:  # ANNUAL
        payment_interval = 365  # days
    
    # Number of payments
    term_days = (loan.maturity_date - loan.start_date).days
    num_payments = term_days // payment_interval
    
    # If fixed payments
    if loan.next_payment_amount:
        payment_amount = loan.next_payment_amount
    else:
        # Calculate approximate payment
        rate_per_period = loan.interest_rate / 100 / (365 / payment_interval)
        payment_amount = (loan.principal_amount * rate_per_period) / (1 - (1 + rate_per_period) ** -num_payments)
    
    # Generate schedule
    balance = loan.principal_amount
    payment_date = loan.start_date
    
    for i in range(num_payments):
        payment_date = payment_date + timedelta(days=payment_interval)
        
        # Calculate interest portion
        days_since_last = payment_interval
        interest = balance * (loan.interest_rate / 100) * (days_since_last / 365)
        
        # Calculate principal portion
        principal = payment_amount - interest
        
        # Update balance
        balance = balance - principal
        
        schedule.append({
            'payment_number': i + 1,
            'date': payment_date.strftime('%Y-%m-%d'),
            'payment': payment_amount,
            'principal': principal,
            'interest': interest,
            'balance': max(0, balance)
        })
    
    return jsonify(schedule)