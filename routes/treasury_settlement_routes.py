"""
Treasury Settlement Routes

This module handles routes for treasury settlement operations between 
payment processors and treasury accounts.
"""

import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from sqlalchemy import func, desc

from app import db
from models import User, TransactionType, TreasuryAccount, TreasuryTransaction
from payment_models import StripePayment, PayPalPayment, POSPayment
from auth import admin_required

logger = logging.getLogger(__name__)

# Create blueprint
treasury_settlement_bp = Blueprint('treasury_settlement', __name__, url_prefix='/treasury/settlement')

@treasury_settlement_bp.route('/dashboard')
@admin_required
def settlement_dashboard():
    """Settlement dashboard showing status of payment bridges"""
    
    # Get treasury accounts for each payment processor
    stripe_account = TreasuryAccount.query.filter_by(account_type='OPERATING', 
                                                   description='Stripe Settlement Account').first()
    
    paypal_account = TreasuryAccount.query.filter_by(account_type='OPERATING', 
                                                   description='PayPal Settlement Account').first()
    
    pos_account = TreasuryAccount.query.filter_by(account_type='OPERATING', 
                                                description='POS Settlement Account').first()
    
    # Get settlement transactions for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    settlement_transactions = TreasuryTransaction.query.filter(
        TreasuryTransaction.transaction_type == TransactionType.PAYMENT_SETTLEMENT,
        TreasuryTransaction.created_at >= thirty_days_ago
    ).order_by(desc(TreasuryTransaction.created_at)).limit(10).all()
    
    return render_template('treasury/settlement_dashboard.html', 
                          stripe_account=stripe_account,
                          paypal_account=paypal_account,
                          pos_account=pos_account,
                          recent_settlements=settlement_transactions)


@treasury_settlement_bp.route('/stats')
@admin_required
def settlement_stats():
    """Get settlement statistics for the dashboard"""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Get Stripe settlement stats
    stripe_settlements = TreasuryTransaction.query.filter(
        TreasuryTransaction.transaction_type == TransactionType.PAYMENT_SETTLEMENT,
        TreasuryTransaction.description.like('%Stripe%'),
        TreasuryTransaction.created_at >= thirty_days_ago
    ).all()
    
    stripe_count = len(stripe_settlements)
    stripe_total = sum(t.amount for t in stripe_settlements)
    
    # Get PayPal settlement stats
    paypal_settlements = TreasuryTransaction.query.filter(
        TreasuryTransaction.transaction_type == TransactionType.PAYMENT_SETTLEMENT,
        TreasuryTransaction.description.like('%PayPal%'),
        TreasuryTransaction.created_at >= thirty_days_ago
    ).all()
    
    paypal_count = len(paypal_settlements)
    paypal_total = sum(t.amount for t in paypal_settlements)
    
    # Get POS settlement stats
    pos_settlements = TreasuryTransaction.query.filter(
        TreasuryTransaction.transaction_type == TransactionType.PAYMENT_SETTLEMENT,
        TreasuryTransaction.description.like('%POS%'),
        TreasuryTransaction.created_at >= thirty_days_ago
    ).all()
    
    pos_count = len(pos_settlements)
    pos_total = sum(t.amount for t in pos_settlements)
    
    # Get total settlement amount
    total_settled = stripe_total + paypal_total + pos_total
    
    return jsonify({
        'stripe': {
            'count': stripe_count,
            'total': stripe_total
        },
        'paypal': {
            'count': paypal_count,
            'total': paypal_total
        },
        'pos': {
            'count': pos_count,
            'total': pos_total
        },
        'total_settled': total_settled
    })


@treasury_settlement_bp.route('/settle/<processor>')
@admin_required
def manual_settlement(processor):
    """Manually trigger settlement for a payment processor"""
    from treasury_payment_bridge import SettlementBridge
    
    # Initialize the settlement bridge
    bridge = SettlementBridge()
    
    if processor == 'stripe':
        settlement_id, amount = bridge.settle_stripe_payments()
        flash(f'Stripe settlement complete. Settled {amount} USD.', 'success')
    
    elif processor == 'paypal':
        settlement_id, amount = bridge.settle_paypal_payments()
        flash(f'PayPal settlement complete. Settled {amount} USD.', 'success')
    
    elif processor == 'pos':
        settlement_id, amount = bridge.settle_pos_payments()
        flash(f'POS settlement complete. Settled {amount} USD.', 'success')
    
    else:
        flash(f'Unknown payment processor: {processor}', 'danger')
    
    return redirect(url_for('treasury_settlement.settlement_dashboard'))


@treasury_settlement_bp.route('/unsettled-payments')
@admin_required
def unsettled_payments():
    """View unsettled payments for all processors"""
    
    # Get unsettled payments for each processor
    stripe_payments = StripePayment.query.filter_by(is_settled=False, status='succeeded').all()
    paypal_payments = PayPalPayment.query.filter_by(is_settled=False, status='COMPLETED').all()
    pos_payments = POSPayment.query.filter_by(is_settled=False, status='completed').all()
    
    return render_template('treasury/unsettled_payments.html',
                          stripe_payments=stripe_payments,
                          paypal_payments=paypal_payments,
                          pos_payments=pos_payments)