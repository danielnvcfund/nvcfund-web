from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Transaction, TransactionStatus
from auth import admin_required
from app import db

admin_bp = Blueprint('transaction_admin', __name__, url_prefix='/transaction-admin')

@admin_bp.route('/transactions', methods=['GET'])
@login_required
@admin_required
def admin_transactions():
    """Admin transaction management page"""
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    return render_template('admin/transactions.html', transactions=transactions)

@admin_bp.route('/transaction/<transaction_id>', methods=['GET'])
@login_required
@admin_required
def admin_transaction_detail(transaction_id):
    """Admin transaction detail page"""
    transaction = Transaction.query.filter_by(id=transaction_id).first_or_404()
    
    # Ensure metadata is in a serializable format
    from sqlalchemy.ext.declarative import DeclarativeMeta
    from sqlalchemy.sql.schema import MetaData
    import json
    
    # Handle SQLAlchemy MetaData objects (not JSON serializable)
    if hasattr(transaction, 'metadata') and transaction.metadata is not None:
        if isinstance(transaction.metadata, MetaData):
            # Convert to a simple string representation
            transaction._safe_metadata = str(transaction.metadata)
        elif isinstance(transaction.metadata, dict):
            # Keep as is, it's already serializable
            transaction._safe_metadata = transaction.metadata
        else:
            # Fallback for any other type
            transaction._safe_metadata = str(transaction.metadata)
    else:
        transaction._safe_metadata = None
    
    return render_template('admin/transaction_detail.html', transaction=transaction)

@admin_bp.route('/transaction/update-status/<transaction_id>', methods=['POST'])
@login_required
@admin_required
def update_transaction_status(transaction_id):
    """Update a transaction's status"""
    transaction = Transaction.query.filter_by(id=transaction_id).first_or_404()
    
    new_status = request.form.get('status')
    if not new_status or not hasattr(TransactionStatus, new_status):
        flash('Invalid status', 'error')
        return redirect(url_for('transaction_admin.admin_transaction_detail', transaction_id=transaction_id))
    
    old_status = transaction.status.name
    transaction.status = getattr(TransactionStatus, new_status)
    
    # Add a note about the status change
    notes = transaction.metadata.get('admin_notes', [])
    notes.append({
        'timestamp': transaction.updated_at.isoformat(),
        'user': current_user.username,
        'action': f'Status changed from {old_status} to {new_status}'
    })
    transaction.metadata['admin_notes'] = notes
    
    db.session.commit()
    flash(f'Transaction status updated to {new_status}', 'success')
    return redirect(url_for('transaction_admin.admin_transaction_detail', transaction_id=transaction_id))

@admin_bp.route('/transaction/add-note/<transaction_id>', methods=['POST'])
@login_required
@admin_required
def add_transaction_note(transaction_id):
    """Add an admin note to a transaction"""
    transaction = Transaction.query.filter_by(id=transaction_id).first_or_404()
    
    note = request.form.get('note')
    if not note:
        flash('Note cannot be empty', 'error')
        return redirect(url_for('transaction_admin.admin_transaction_detail', transaction_id=transaction_id))
    
    notes = transaction.metadata.get('admin_notes', [])
    notes.append({
        'timestamp': transaction.updated_at.isoformat(),
        'user': current_user.username,
        'note': note
    })
    transaction.metadata['admin_notes'] = notes
    
    db.session.commit()
    flash('Note added', 'success')
    return redirect(url_for('transaction_admin.admin_transaction_detail', transaction_id=transaction_id))