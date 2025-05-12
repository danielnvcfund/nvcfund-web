"""
Payment History Routes
This module provides routes for viewing transaction history and managing payments.
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, abort, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc

from models import db, Transaction, TransactionStatus, TransactionType
from routes.pdf_receipt_routes import generate_receipt_pdf
from email_service import send_receipt_email

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
payment_history_bp = Blueprint('payment_history', __name__, url_prefix='/payment-history')


@payment_history_bp.route('/')
@login_required
def index():
    """Display payment history for the current user"""
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of transactions per page
    
    # Get filter parameters
    current_status = request.args.get('status', 'all')
    current_type = request.args.get('type', 'all')
    current_days = request.args.get('days', '30')
    
    # Build query
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    # Apply status filter
    if current_status != 'all':
        try:
            status_enum = TransactionStatus[current_status.upper()]
            query = query.filter_by(status=status_enum)
        except KeyError:
            # Invalid status - ignore filter
            pass
    
    # Apply type filter
    if current_type != 'all':
        try:
            type_enum = TransactionType[current_type.upper()]
            query = query.filter_by(transaction_type=type_enum)
        except KeyError:
            # Invalid type - ignore filter
            pass
    
    # Apply date filter
    if current_days != '0':  # 0 means all time
        try:
            days = int(current_days)
            if days > 0:
                date_threshold = datetime.utcnow() - timedelta(days=days)
                query = query.filter(Transaction.created_at >= date_threshold)
        except ValueError:
            # Invalid days value - ignore filter
            pass
    
    # Order by newest first
    query = query.order_by(desc(Transaction.created_at))
    
    # Paginate results
    transactions = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get list of all possible statuses and types for filters
    status_options = [s.name.lower() for s in TransactionStatus]
    payment_type_options = [t.name.lower() for t in TransactionType]
    
    return render_template(
        'payment_history/index.html',
        transactions=transactions,
        current_status=current_status,
        current_type=current_type,
        current_days=current_days,
        status_options=status_options,
        payment_type_options=payment_type_options
    )


@payment_history_bp.route('/transaction/<transaction_id>')
@login_required
def transaction_detail(transaction_id):
    """Display details for a specific transaction"""
    # Find the transaction
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id, 
        user_id=current_user.id
    ).first_or_404()
    
    return render_template(
        'payment_history/transaction_detail.html',
        transaction=transaction
    )


@payment_history_bp.route('/download-receipt/<transaction_id>')
@login_required
def download_receipt(transaction_id):
    """Redirect to PDF receipt download route"""
    return redirect(url_for('pdf_receipt.generate_receipt', transaction_id=transaction_id))


@payment_history_bp.route('/email-receipt/<transaction_id>')
@login_required
def email_receipt(transaction_id):
    """Generate and email a receipt for a transaction"""
    # Find the transaction
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id, 
        user_id=current_user.id
    ).first_or_404()
    
    # Redirect to PDF receipt email route
    return redirect(url_for('pdf_receipt.email_receipt', transaction_id=transaction_id))


@payment_history_bp.route('/cancel/<transaction_id>')
@login_required
def cancel_transaction(transaction_id):
    """Cancel a pending transaction"""
    # Find the transaction
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id, 
        user_id=current_user.id,
        status=TransactionStatus.PENDING
    ).first_or_404()
    
    # Update transaction status
    transaction.status = TransactionStatus.CANCELLED
    db.session.commit()
    
    flash('Transaction has been cancelled successfully.', 'success')
    return redirect(url_for('payment_history.transaction_detail', transaction_id=transaction_id))