"""
SWIFT Integration Routes
Routes for handling SWIFT messaging functionality including standby letters of credit,
fund transfers, and free format messages.
"""
import json
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user

from models import db, Transaction, TransactionType, TransactionStatus
from forms import LetterOfCreditForm, SwiftFundTransferForm, SwiftFreeFormatMessageForm
from swift_integration import SwiftService

swift = Blueprint('swift', __name__)

@swift.route('/letter_of_credit/new', methods=['GET', 'POST'])
@login_required
def new_letter_of_credit():
    """Create a new Standby Letter of Credit (SBLC) using SWIFT MT760"""
    form = LetterOfCreditForm()
    
    if form.validate_on_submit():
        try:
            # Create the letter of credit
            transaction = SwiftService.create_letter_of_credit(
                user_id=current_user.id,
                receiver_institution_id=form.receiver_institution_id.data,
                amount=form.amount.data,
                currency=form.currency.data,
                beneficiary=form.beneficiary.data,
                expiry_date=form.expiry_date.data,
                terms_and_conditions=form.terms_and_conditions.data
            )
            
            flash(f'Standby Letter of Credit created successfully. Reference: {transaction.transaction_id}', 'success')
            return redirect(url_for('web.swift.letter_of_credit_status', transaction_id=transaction.transaction_id))
        except Exception as e:
            flash(f'Error creating Letter of Credit: {str(e)}', 'danger')
    
    return render_template('letter_of_credit_form.html', form=form)

@swift.route('/letter_of_credit/status/<transaction_id>')
@login_required
def letter_of_credit_status(transaction_id):
    """View the status of a Letter of Credit"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not transaction:
        flash('Transaction not found.', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    if transaction.transaction_type != TransactionType.SWIFT_LETTER_OF_CREDIT:
        flash('This transaction is not a Letter of Credit.', 'warning')
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
    
    # Get status from SWIFT service
    status_data = SwiftService.get_letter_of_credit_status(transaction.id)
    
    # Parse SWIFT message data
    try:
        swift_data = json.loads(transaction.tx_metadata_json) if transaction.tx_metadata_json else {}
    except json.JSONDecodeError:
        swift_data = {}
    
    return render_template('letter_of_credit_status.html', 
                          transaction=transaction, 
                          swift_data=swift_data,
                          status_data=status_data)

@swift.route('/fund_transfer/new', methods=['GET', 'POST'])
@login_required
def new_fund_transfer():
    """Create a new SWIFT MT103/MT202 fund transfer"""
    form = SwiftFundTransferForm()
    
    if form.validate_on_submit():
        try:
            # Create the fund transfer
            transaction = SwiftService.create_swift_fund_transfer(
                user_id=current_user.id,
                receiver_institution_id=form.receiver_institution_id.data,
                amount=form.amount.data,
                currency=form.currency.data,
                ordering_customer=form.ordering_customer.data,
                beneficiary_customer=form.beneficiary_customer.data,
                details_of_payment=form.details_of_payment.data,
                is_financial_institution=bool(form.is_financial_institution.data)
            )
            
            message_type = "MT202" if form.is_financial_institution.data else "MT103"
            flash(f'SWIFT {message_type} fund transfer initiated successfully. Reference: {transaction.transaction_id}', 'success')
            return redirect(url_for('web.swift.fund_transfer_status', transaction_id=transaction.transaction_id))
        except Exception as e:
            flash(f'Error creating fund transfer: {str(e)}', 'danger')
    
    return render_template('swift_fund_transfer_form.html', form=form)

@swift.route('/free_format/new', methods=['GET', 'POST'])
@login_required
def new_free_format_message():
    """Create a new SWIFT MT799 free format message"""
    form = SwiftFreeFormatMessageForm()
    
    if form.validate_on_submit():
        try:
            # Create the free format message
            transaction = SwiftService.create_free_format_message(
                user_id=current_user.id,
                receiver_institution_id=form.receiver_institution_id.data,
                subject=form.subject.data,
                message_body=form.message_body.data
            )
            
            flash(f'SWIFT MT799 message sent successfully. Reference: {transaction.transaction_id}', 'success')
            return redirect(url_for('web.swift.message_status', transaction_id=transaction.transaction_id))
        except Exception as e:
            flash(f'Error sending message: {str(e)}', 'danger')
    
    return render_template('swift_free_format_message_form.html', form=form)

@swift.route('/message/status/<transaction_id>')
@login_required
def message_status(transaction_id):
    """View the status of any SWIFT message"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not transaction:
        flash('Transaction not found.', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    # Determine which status check to use based on transaction type
    if transaction.transaction_type == TransactionType.SWIFT_LETTER_OF_CREDIT:
        status_data = SwiftService.get_letter_of_credit_status(transaction.id)
        template = 'letter_of_credit_status.html'
    elif transaction.transaction_type in [TransactionType.SWIFT_FUND_TRANSFER, TransactionType.SWIFT_INSTITUTION_TRANSFER]:
        status_data = SwiftService.get_fund_transfer_status(transaction.id)
        template = 'swift_fund_transfer_status.html'
    elif transaction.transaction_type == TransactionType.SWIFT_FREE_FORMAT:
        status_data = SwiftService.get_free_format_message_status(transaction.id)
        template = 'swift_message_status.html'
    else:
        flash('This transaction is not a SWIFT message.', 'warning')
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
    
    # Parse SWIFT message data
    try:
        swift_data = json.loads(transaction.tx_metadata_json) if transaction.tx_metadata_json else {}
    except json.JSONDecodeError:
        swift_data = {}
    
    return render_template(template, 
                          transaction=transaction, 
                          swift_data=swift_data,
                          status_data=status_data)

@swift.route('/fund_transfer/status/<transaction_id>')
@login_required
def fund_transfer_status(transaction_id):
    """View the status of a fund transfer"""
    # This is just a specialized redirect to message_status for fund transfers
    return redirect(url_for('web.swift.message_status', transaction_id=transaction_id))

@swift.route('/cancel_message/<transaction_id>', methods=['POST'])
@login_required
def cancel_message(transaction_id):
    """Cancel a pending SWIFT message"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not transaction:
        flash('Transaction not found.', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    if transaction.transaction_type != TransactionType.SWIFT_FREE_FORMAT:
        flash('This transaction is not a SWIFT message.', 'warning')
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
    
    if transaction.status != TransactionStatus.PENDING:
        flash('Only pending messages can be cancelled.', 'warning')
        return redirect(url_for('web.swift.message_status', transaction_id=transaction.transaction_id))
    
    try:
        # Update transaction status
        transaction.status = TransactionStatus.CANCELLED
        db.session.commit()
        flash('Message has been cancelled successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling message: {str(e)}', 'danger')
    
    return redirect(url_for('web.swift.message_status', transaction_id=transaction.transaction_id))

@swift.route('/cancel_transfer/<transaction_id>', methods=['POST'])
@login_required
def cancel_transfer(transaction_id):
    """Cancel a pending SWIFT fund transfer"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not transaction:
        flash('Transaction not found.', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
    if transaction.transaction_type not in [TransactionType.SWIFT_FUND_TRANSFER, TransactionType.SWIFT_INSTITUTION_TRANSFER]:
        flash('This transaction is not a SWIFT fund transfer.', 'warning')
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
    
    if transaction.status != TransactionStatus.PENDING:
        flash('Only pending transfers can be cancelled.', 'warning')
        return redirect(url_for('web.swift.fund_transfer_status', transaction_id=transaction.transaction_id))
    
    try:
        # Update transaction status
        transaction.status = TransactionStatus.CANCELLED
        db.session.commit()
        flash('Fund transfer has been cancelled successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling fund transfer: {str(e)}', 'danger')
    
    return redirect(url_for('web.swift.fund_transfer_status', transaction_id=transaction.transaction_id))

@swift.route('/api/swift/status/<transaction_id>')
@login_required
def api_swift_status(transaction_id):
    """API endpoint to get SWIFT message status"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not transaction:
        return jsonify({'success': False, 'error': 'Transaction not found'})
    
    # Determine which status check to use based on transaction type
    if transaction.transaction_type == TransactionType.SWIFT_LETTER_OF_CREDIT:
        status_data = SwiftService.get_letter_of_credit_status(transaction.id)
    elif transaction.transaction_type in [TransactionType.SWIFT_FUND_TRANSFER, TransactionType.SWIFT_INSTITUTION_TRANSFER]:
        status_data = SwiftService.get_fund_transfer_status(transaction.id)
    elif transaction.transaction_type == TransactionType.SWIFT_FREE_FORMAT:
        status_data = SwiftService.get_free_format_message_status(transaction.id)
    else:
        return jsonify({'success': False, 'error': 'Not a SWIFT message transaction'})
        
    return jsonify(status_data)