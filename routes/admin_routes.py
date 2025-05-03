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
    
    # Prepare metadata for safe display in template
    metadata_display = None
    metadata_is_mapping = False
    admin_notes = []
    
    try:
        if transaction.metadata:
            import json
            # Try to convert to JSON to check if serializable
            try:
                json.dumps(transaction.metadata)
                metadata_display = transaction.metadata
                metadata_is_mapping = isinstance(transaction.metadata, dict)
                
                # Extract admin notes if available
                if metadata_is_mapping and 'admin_notes' in transaction.metadata:
                    admin_notes = transaction.metadata['admin_notes']
            except (TypeError, ValueError):
                # Not JSON serializable, convert to string
                metadata_display = str(transaction.metadata)
    except Exception as e:
        metadata_display = f"Error accessing metadata: {str(e)}"
    
    return render_template(
        'admin/transaction_detail.html', 
        transaction=transaction,
        metadata_display=metadata_display,
        metadata_is_mapping=metadata_is_mapping,
        admin_notes=admin_notes
    )

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