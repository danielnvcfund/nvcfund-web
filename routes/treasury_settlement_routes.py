"""
Treasury Settlement Routes - Manage settlement between payment processors and treasury accounts
"""
import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from models import db, TreasuryAccount, TreasuryTransaction, PaymentGateway
from models import TransactionType, TransactionStatus, TreasuryAccountType
from forms import TreasurySettlementForm
from treasury_payment_bridge import treasury_payment_bridge

from auth import admin_required

logger = logging.getLogger(__name__)

# Create blueprint
treasury_settlement_bp = Blueprint('treasury_settlement', __name__)

@treasury_settlement_bp.route('/treasury/settlements', methods=['GET'])
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
    
    # Get settlement statistics
    stats = {}
    
    # Stripe stats
    if stripe_account:
        stripe_total = db.session.query(
            db.func.sum(TreasuryTransaction.amount)
        ).filter(
            TreasuryTransaction.transaction_type == TransactionType.PAYMENT_SETTLEMENT,
            TreasuryTransaction.to_account_id == stripe_account.id,
            TreasuryTransaction.created_at >= (datetime.utcnow() - timedelta(days=30))
        ).scalar() or 0.0
        
        stats['stripe'] = {
            'account': stripe_account,
            'total_30d': stripe_total,
            'currency': stripe_account.currency
        }
    
    # PayPal stats
    if paypal_account:
        paypal_total = db.session.query(
            db.func.sum(TreasuryTransaction.amount)
        ).filter(
            TreasuryTransaction.transaction_type == TransactionType.PAYMENT_SETTLEMENT,
            TreasuryTransaction.to_account_id == paypal_account.id,
            TreasuryTransaction.created_at >= (datetime.utcnow() - timedelta(days=30))
        ).scalar() or 0.0
        
        stats['paypal'] = {
            'account': paypal_account,
            'total_30d': paypal_total,
            'currency': paypal_account.currency
        }
    
    # POS stats
    if pos_account:
        pos_total = db.session.query(
            db.func.sum(TreasuryTransaction.amount)
        ).filter(
            TreasuryTransaction.transaction_type == TransactionType.PAYMENT_SETTLEMENT,
            TreasuryTransaction.to_account_id == pos_account.id,
            TreasuryTransaction.created_at >= (datetime.utcnow() - timedelta(days=30))
        ).scalar() or 0.0
        
        stats['pos'] = {
            'account': pos_account,
            'total_30d': pos_total,
            'currency': pos_account.currency
        }
    
    # Prepare the form for manual settlement
    form = TreasurySettlementForm()
    
    # Populate account choices for the form
    operating_accounts = TreasuryAccount.query.filter(
        TreasuryAccount.account_type == TreasuryAccountType.OPERATING,
        TreasuryAccount.is_active == True
    ).all()
    
    account_choices = [(a.id, f"{a.name} ({a.currency})") for a in operating_accounts]
    form.account_id.choices = account_choices
    
    return render_template(
        'treasury/settlement_dashboard.html',
        stripe_account=stripe_account,
        paypal_account=paypal_account,
        pos_account=pos_account,
        settlements=settlements,
        stats=stats,
        form=form
    )

@treasury_settlement_bp.route('/treasury/settlements/create-accounts', methods=['POST'])
@login_required
@admin_required
def create_settlement_accounts():
    """Create dedicated settlement accounts for payment processors"""
    processor_type = request.form.get('processor_type')
    currency = request.form.get('currency', 'USD')
    
    if not processor_type:
        flash('Processor type is required', 'error')
        return redirect(url_for('treasury_settlement.settlement_dashboard'))
    
    # Create the account
    try:
        account = treasury_payment_bridge.create_processor_linked_account(
            processor_type=processor_type,
            currency=currency
        )
        flash(f'{processor_type.title()} settlement account created successfully', 'success')
    except Exception as e:
        logger.error(f"Error creating settlement account: {str(e)}")
        flash(f'Error creating settlement account: {str(e)}', 'error')
    
    return redirect(url_for('treasury_settlement.settlement_dashboard'))

@treasury_settlement_bp.route('/treasury/settlements/process', methods=['POST'])
@login_required
@admin_required
def process_settlements():
    """Process settlements from payment processors to treasury accounts"""
    days_back = int(request.form.get('days_back', 1))
    processor = request.form.get('processor', 'all')
    
    try:
        if processor == 'all':
            result = treasury_payment_bridge.process_all_settlements(days_back)
            flash('Processed settlements for all payment processors', 'success')
        elif processor == 'stripe':
            result = treasury_payment_bridge.process_stripe_settlement(days_back)
            flash('Processed Stripe settlements', 'success')
        elif processor == 'paypal':
            result = treasury_payment_bridge.process_paypal_settlement(days_back)
            flash('Processed PayPal settlements', 'success')
        elif processor == 'pos':
            result = treasury_payment_bridge.process_pos_settlement(days_back)
            flash('Processed POS settlements', 'success')
        else:
            flash('Invalid processor type', 'error')
            return redirect(url_for('treasury_settlement.settlement_dashboard'))
        
        logger.info(f"Settlement processing result: {result}")
    except Exception as e:
        logger.error(f"Error processing settlements: {str(e)}")
        flash(f'Error processing settlements: {str(e)}', 'error')
    
    return redirect(url_for('treasury_settlement.settlement_dashboard'))

@treasury_settlement_bp.route('/treasury/settlements/manual', methods=['POST'])
@login_required
@admin_required
def manual_settlement():
    """Record a manual settlement transaction"""
    form = TreasurySettlementForm()
    
    if form.validate_on_submit():
        try:
            # Record the settlement transaction
            treasury_payment_bridge.record_settlement_transaction(
                account_id=form.account_id.data,
                amount=form.amount.data,
                processor_type=form.processor_type.data,
                external_reference=form.reference.data,
                description=form.description.data
            )
            
            flash('Manual settlement recorded successfully', 'success')
        except Exception as e:
            logger.error(f"Error recording manual settlement: {str(e)}")
            flash(f'Error recording manual settlement: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", 'error')
    
    return redirect(url_for('treasury_settlement.settlement_dashboard'))

@treasury_settlement_bp.route('/treasury/settlements/api/status', methods=['GET'])
@login_required
def settlement_status_api():
    """API endpoint to get settlement status"""
    try:
        # Get linked accounts for each processor
        stripe_account = treasury_payment_bridge.get_processor_linked_account('stripe')
        paypal_account = treasury_payment_bridge.get_processor_linked_account('paypal')
        pos_account = treasury_payment_bridge.get_processor_linked_account('pos')
        
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'processors': {}
        }
        
        # Stripe status
        if stripe_account:
            status['processors']['stripe'] = {
                'linked': True,
                'account_id': stripe_account.id,
                'account_name': stripe_account.name,
                'balance': stripe_account.current_balance,
                'currency': stripe_account.currency
            }
        else:
            status['processors']['stripe'] = {'linked': False}
        
        # PayPal status
        if paypal_account:
            status['processors']['paypal'] = {
                'linked': True,
                'account_id': paypal_account.id,
                'account_name': paypal_account.name,
                'balance': paypal_account.current_balance,
                'currency': paypal_account.currency
            }
        else:
            status['processors']['paypal'] = {'linked': False}
        
        # POS status
        if pos_account:
            status['processors']['pos'] = {
                'linked': True,
                'account_id': pos_account.id,
                'account_name': pos_account.name,
                'balance': pos_account.current_balance,
                'currency': pos_account.currency
            }
        else:
            status['processors']['pos'] = {'linked': False}
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting settlement status: {str(e)}")
        return jsonify({'error': str(e)}), 500