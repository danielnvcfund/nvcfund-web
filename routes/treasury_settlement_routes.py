"""
Treasury Settlement Routes
-------------------------

Routes for handling treasury settlement operations between payment processors
and treasury accounts.
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, func

from app import db
from models import (
    TreasuryAccount, 
    TreasuryTransaction,
    TransactionType,
    TransactionStatus
)
from forms import TreasurySettlementForm
import treasury_payment_bridge
from auth import admin_required

logger = logging.getLogger(__name__)

# Create Blueprint
treasury_settlement_bp = Blueprint('treasury_settlement', __name__, url_prefix='/treasury/settlement')

@treasury_settlement_bp.route('/')
@login_required
def settlement_dashboard():
    """Show treasury settlement dashboard"""
    
    # Get linked accounts for each processor
    stripe_account = treasury_payment_bridge.get_processor_linked_account('stripe')
    paypal_account = treasury_payment_bridge.get_processor_linked_account('paypal')
    pos_account = treasury_payment_bridge.get_processor_linked_account('pos')
    
    # Get recent settlement transactions
    settlements = TreasuryTransaction.query.filter(
        TreasuryTransaction.transaction_type == TransactionType.PAYMENT_SETTLEMENT
    ).order_by(
        TreasuryTransaction.created_at.desc()
    ).limit(20).all()
    
    # Create form for manual settlements
    form = TreasurySettlementForm()
    form.account_id.choices = [(a.id, f"{a.name} ({a.currency})") for a in 
                               TreasuryAccount.query.filter_by(is_active=True).all()]
    
    return render_template(
        'treasury/settlement_dashboard.html',
        stripe_account=stripe_account,
        paypal_account=paypal_account,
        pos_account=pos_account,
        settlements=settlements,
        form=form
    )

@treasury_settlement_bp.route('/process', methods=['POST'])
@login_required
@admin_required
def process_settlements():
    """Process settlements for payment processors"""
    processor = request.form.get('processor', 'all')
    days_back = int(request.form.get('days_back', 1))
    
    results = {}
    
    if processor == 'all':
        # Process all payment processors
        results = treasury_payment_bridge.process_all_settlements(days_back)
        
        # Calculate totals
        total_count = sum(count for count, _ in results.values())
        total_amount = sum(amount for _, amount in results.values())
        
        flash(f"Processed {total_count} settlements across all payment processors, totaling approximately {total_amount:.2f} USD", "success")
    else:
        # Process a specific payment processor
        if processor == 'stripe':
            count, amount = treasury_payment_bridge.process_stripe_settlements(days_back)
            results[processor] = (count, amount)
            flash(f"Processed {count} Stripe settlements totaling {amount:.2f} USD", "success")
        
        elif processor == 'paypal':
            count, amount = treasury_payment_bridge.process_paypal_settlements(days_back)
            results[processor] = (count, amount)
            flash(f"Processed {count} PayPal settlements totaling {amount:.2f} USD", "success")
        
        elif processor == 'pos':
            count, amount = treasury_payment_bridge.process_pos_settlements(days_back)
            results[processor] = (count, amount)
            flash(f"Processed {count} POS settlements totaling {amount:.2f} USD", "success")
        
        else:
            flash(f"Invalid processor type: {processor}", "error")
    
    return redirect(url_for('treasury_settlement.settlement_dashboard'))

@treasury_settlement_bp.route('/create_accounts', methods=['POST'])
@login_required
@admin_required
def create_settlement_accounts():
    """Create settlement accounts for payment processors"""
    processor_type = request.form.get('processor_type')
    
    if not processor_type:
        flash("No processor type specified", "error")
        return redirect(url_for('treasury_settlement.settlement_dashboard'))
    
    # Create the settlement account
    account = treasury_payment_bridge.create_settlement_account(processor_type)
    
    if account:
        flash(f"Created {processor_type} settlement account: {account.name}", "success")
    else:
        flash(f"Failed to create {processor_type} settlement account", "error")
    
    return redirect(url_for('treasury_settlement.settlement_dashboard'))

@treasury_settlement_bp.route('/manual', methods=['POST'])
@login_required
@admin_required
def manual_settlement():
    """Record a manual settlement from a payment processor to a treasury account"""
    form = TreasurySettlementForm()
    form.account_id.choices = [(a.id, f"{a.name} ({a.currency})") for a in 
                               TreasuryAccount.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        transaction = treasury_payment_bridge.manual_settlement(
            account_id=form.account_id.data,
            processor_type=form.processor_type.data,
            amount=form.amount.data,
            currency=form.currency.data,
            reference=form.reference.data,
            description=form.description.data
        )
        
        if transaction:
            flash(f"Recorded manual settlement of {form.amount.data} {form.currency.data} to account {transaction.to_account.name}", "success")
        else:
            flash("Failed to record manual settlement", "error")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", "error")
    
    return redirect(url_for('treasury_settlement.settlement_dashboard'))

@treasury_settlement_bp.route('/stats')
@login_required
def settlement_stats():
    """Get settlement statistics in JSON format"""
    stats = treasury_payment_bridge.get_settlement_statistics()
    
    # Convert to JSON-serializable format
    result = {
        'total_settled_30d': stats.get('total_settled_30d', 0),
        'processors': {}
    }
    
    for processor, details in stats.get('processor_totals', {}).items():
        result['processors'][processor] = {
            'total_30d': details.get('total_30d', 0),
            'count_30d': details.get('count_30d', 0),
            'currency': details.get('currency', 'USD'),
            'has_account': details.get('account') is not None
        }
        
        if details.get('account'):
            result['processors'][processor]['account_name'] = details['account'].name
            result['processors'][processor]['account_balance'] = details['account'].current_balance
    
    # Most recent settlements
    result['most_recent'] = {}
    for processor, tx in stats.get('most_recent', {}).items():
        if tx:
            result['most_recent'][processor] = {
                'date': tx.created_at.isoformat(),
                'amount': tx.amount,
                'currency': tx.currency
            }
        else:
            result['most_recent'][processor] = None
    
    return jsonify(result)