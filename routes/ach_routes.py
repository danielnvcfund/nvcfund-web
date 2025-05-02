"""
ACH (Automated Clearing House) Routes
This module provides the routes for ACH transfers within the US banking system.
"""
import json
import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file, Response
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from forms import ACHTransferForm
from models import Transaction, TransactionStatus, TransactionType, db
from ach_service import ach_service
from pdf_service import pdf_service
from utils import format_currency, format_transaction_type
import io
import os

# Create blueprint
ach = Blueprint('ach', __name__, url_prefix='/ach')

# Set up logger
logger = logging.getLogger(__name__)

@ach.route('/new', methods=['GET', 'POST'])
@login_required
def new_ach_transfer():
    """Create a new ACH transfer"""
    form = ACHTransferForm()
    
    if form.validate_on_submit():
        try:
            # Create the ACH transfer
            transaction = ach_service.create_ach_transfer(
                user_id=current_user.id,
                amount=form.amount.data,
                currency='USD',  # ACH transfers are in USD
                recipient_name=form.recipient_name.data,
                recipient_account_number=form.recipient_account_number.data,
                recipient_routing_number=form.recipient_routing_number.data,
                recipient_account_type=form.recipient_account_type.data,
                entry_class_code=form.entry_class_code.data,
                effective_date=form.effective_date.data,
                description=form.description.data,
                recurring=form.recurring.data,
                recurring_frequency=form.recurring_frequency.data if form.recurring.data else None,
                company_entry_description=form.company_entry_description.data,
                sender_account_type=form.sender_account_type.data
            )
            
            flash(f'ACH transfer initiated successfully. Reference: {transaction.transaction_id}', 'success')
            return redirect(url_for('web.ach.ach_transfer_status', transaction_id=transaction.transaction_id))
        except ValueError as e:
            flash(f'Error: {str(e)}', 'danger')
        except Exception as e:
            logger.error(f"Error creating ACH transfer: {str(e)}")
            flash('An error occurred while processing your request. Please try again later.', 'danger')
    
    return render_template('ach_transfer_form.html', form=form)

@ach.route('/status/<transaction_id>')
@login_required
def ach_transfer_status(transaction_id):
    """View the status of an ACH transfer"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        flash('Transaction not found.', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    if transaction.transaction_type != TransactionType.EDI_ACH_TRANSFER:
        flash('This transaction is not an ACH transfer.', 'warning')
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
    
    # Get status from ACH service
    status_data = ach_service.get_ach_transfer_status(transaction.transaction_id)
    
    # Parse metadata
    try:
        metadata = json.loads(transaction.tx_metadata_json) if transaction.tx_metadata_json else {}
    except json.JSONDecodeError:
        metadata = {}
    
    # Add recurring information to the template
    is_recurring = metadata.get('recurring', False)
    recurring_frequency = metadata.get('recurring_frequency')
    
    # Add formatted account information
    account_number = metadata.get('recipient_account_number', '')
    if account_number and len(account_number) > 4:
        # Mask all but the last 4 digits
        masked_account = '*' * (len(account_number) - 4) + account_number[-4:]
    else:
        masked_account = '******'
    
    return render_template('ach_transfer_status.html', 
                          transaction=transaction, 
                          metadata=metadata,
                          status_data=status_data,
                          is_recurring=is_recurring,
                          recurring_frequency=recurring_frequency,
                          masked_account=masked_account)

@ach.route('/cancel/<transaction_id>', methods=['POST'])
@login_required
def cancel_ach_transfer(transaction_id):
    """Cancel a pending ACH transfer"""
    try:
        # Verify transaction exists and belongs to current user
        transaction = Transaction.query.filter_by(
            transaction_id=transaction_id, 
            user_id=current_user.id
        ).first()
        
        if not transaction:
            flash('Transaction not found.', 'danger')
            return redirect(url_for('web.main.dashboard'))
        
        if transaction.transaction_type != TransactionType.EDI_ACH_TRANSFER:
            flash('This transaction is not an ACH transfer.', 'warning')
            return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
        
        if transaction.status != TransactionStatus.PENDING:
            flash('Only pending transfers can be cancelled.', 'warning')
            return redirect(url_for('web.ach.ach_transfer_status', transaction_id=transaction.transaction_id))
        
        # Cancel the transfer
        success = ach_service.cancel_ach_transfer(transaction_id, current_user.id)
        
        if success:
            flash('ACH transfer cancelled successfully.', 'success')
        else:
            flash('Failed to cancel ACH transfer. Please try again later.', 'danger')
    
    except Exception as e:
        logger.error(f"Error cancelling ACH transfer: {str(e)}")
        flash('An error occurred while processing your request. Please try again later.', 'danger')
    
    return redirect(url_for('web.ach.ach_transfer_status', transaction_id=transaction_id))

@ach.route('/validate/routing', methods=['POST'])
@login_required
def validate_routing_number():
    """Validate an ABA routing number"""
    routing_number = request.form.get('routing_number', '')
    
    if not routing_number:
        return jsonify({'valid': False, 'message': 'Routing number is required'})
    
    # Validate using the ACH service
    valid = ach_service.validate_routing_number(routing_number)
    
    if valid:
        return jsonify({'valid': True, 'message': 'Routing number is valid'})
    else:
        return jsonify({'valid': False, 'message': 'Invalid routing number'})

@ach.route('/transfers')
@login_required
def ach_transfers():
    """View all ACH transfers for the current user"""
    transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        transaction_type=TransactionType.EDI_ACH_TRANSFER
    ).order_by(Transaction.created_at.desc()).all()
    
    return render_template('ach_transfers.html', transactions=transactions)

@ach.route('/receipt/<transaction_id>/pdf')
@login_required
def download_ach_receipt(transaction_id):
    """Download a PDF receipt for an ACH transfer"""
    # Verify transaction exists and belongs to current user
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id,
        user_id=current_user.id
    ).first()
    
    if not transaction:
        flash('Transaction not found.', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    if transaction.transaction_type != TransactionType.EDI_ACH_TRANSFER:
        flash('This transaction is not an ACH transfer.', 'warning')
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
    
    try:
        # Get user info to add to the PDF
        sender_name = f"{current_user.first_name} {current_user.last_name}" if current_user.first_name and current_user.last_name else current_user.username
        
        # Parse metadata
        try:
            metadata = json.loads(transaction.tx_metadata_json) if transaction.tx_metadata_json else {}
            metadata['sender_name'] = sender_name
        except json.JSONDecodeError:
            metadata = {'sender_name': sender_name}
        
        # Generate PDF
        pdf_data = pdf_service.generate_ach_transaction_pdf(transaction, metadata)
        
        # Create a response with PDF
        filename = f"ACH_Transfer_{transaction_id}.pdf"
        
        response = Response(
            pdf_data,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/pdf'
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating PDF receipt: {str(e)}")
        flash('An error occurred while generating the receipt. Please try again later.', 'danger')
        return redirect(url_for('web.ach.ach_transfer_status', transaction_id=transaction_id))