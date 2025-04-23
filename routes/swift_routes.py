"""
SWIFT Integration Routes
Routes for handling SWIFT messaging functionality including standby letters of credit,
fund transfers, and free format messages.
"""
import json
from datetime import datetime
import re

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user

from models import db, Transaction, TransactionType, TransactionStatus, FinancialInstitution
from forms import LetterOfCreditForm, SwiftFundTransferForm, SwiftFreeFormatMessageForm
from swift_integration import SwiftService

swift = Blueprint('swift', __name__)

@swift.route('/letter_of_credit/new', methods=['GET', 'POST'])
@login_required
def new_letter_of_credit():
    """Create a new Standby Letter of Credit (SBLC) using SWIFT MT760"""
    # Flask-Login's login_required decorator ensures the user is authenticated
    # We can safely use current_user
    user_id = current_user.id
    form = LetterOfCreditForm()
    
    if form.validate_on_submit():
        try:
            # Create the letter of credit
            transaction = SwiftService.create_letter_of_credit(
                user_id=user_id,  # Use the user_id from session instead of current_user
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
    # Flask-Login's login_required decorator ensures the user is authenticated
    # We can safely use current_user
    user_id = current_user.id
    form = SwiftFundTransferForm()
    
    if form.validate_on_submit():
        try:
            # Create the fund transfer
            transaction = SwiftService.create_swift_fund_transfer(
                user_id=user_id,  # Use the user_id from session instead of current_user
                receiver_institution_id=form.receiver_institution_id.data,
                receiver_institution_name=form.receiver_institution_name.data,
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
    # Flask-Login's login_required decorator ensures the user is authenticated
    # We can safely use current_user
    user_id = current_user.id
    form = SwiftFreeFormatMessageForm()
    
    if form.validate_on_submit():
        try:
            # Create the free format message
            transaction = SwiftService.create_free_format_message(
                user_id=user_id,  # Use the user_id from session instead of current_user
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
    # Flask-Login's login_required decorator ensures the user is authenticated
    # We can safely use current_user
    
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
    # Flask-Login's login_required decorator ensures the user is authenticated
    # We can safely use current_user
    
    # This is just a specialized redirect to message_status for fund transfers
    return redirect(url_for('web.swift.message_status', transaction_id=transaction_id))

@swift.route('/cancel_message/<transaction_id>', methods=['POST'])
@login_required
def cancel_message(transaction_id):
    """Cancel a pending SWIFT message"""
    # Flask-Login's login_required decorator ensures the user is authenticated
    # We can safely use current_user
    
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
    # Flask-Login's login_required decorator ensures the user is authenticated
    # We can safely use current_user
    
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

@swift.route('/messages')
@login_required
def swift_messages():
    """View all SWIFT messages"""
    # Get all SWIFT-related transactions for the current user
    # Use string values directly as a workaround for the database enum issue
    swift_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type.in_([
            'swift_fund_transfer',
            'swift_institution_transfer',
            'swift_letter_of_credit',
            'swift_free_format'
        ])
    ).order_by(Transaction.created_at.desc()).all()
    
    # Create a list of message objects with additional data
    messages = []
    for tx in swift_transactions:
        # Parse metadata
        try:
            metadata = json.loads(tx.tx_metadata_json) if tx.tx_metadata_json else {}
        except json.JSONDecodeError:
            metadata = {}
        
        # Get institution name
        institution_name = ""
        if 'receiver_institution_id' in metadata:
            institution = FinancialInstitution.query.get(metadata.get('receiver_institution_id'))
            if institution:
                institution_name = institution.name
        elif 'receiver_institution_name' in metadata:
            institution_name = metadata.get('receiver_institution_name')
        
        # Determine if it's a financial institution transfer
        is_financial_institution = False
        if tx.transaction_type == TransactionType.SWIFT_INSTITUTION_TRANSFER:
            is_financial_institution = True
        elif 'is_financial_institution' in metadata:
            is_financial_institution = bool(metadata.get('is_financial_institution'))
        
        messages.append({
            'transaction': tx,
            'institution_name': institution_name,
            'is_financial_institution': is_financial_institution,
            'metadata': metadata
        })
    
    return render_template('swift_messages.html', messages=messages)

@swift.route('/message/view/<transaction_id>')
@login_required
def view_swift_message(transaction_id):
    """View a SWIFT message in formatted form"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not transaction or transaction.user_id != current_user.id:
        flash('Transaction not found or access denied.', 'danger')
        return redirect(url_for('web.swift.swift_messages'))
    
    # Check if it's a SWIFT message
    if transaction.transaction_type.value not in [
        'swift_fund_transfer',
        'swift_institution_transfer',
        'swift_letter_of_credit',
        'swift_free_format'
    ]:
        flash('This transaction is not a SWIFT message.', 'warning')
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
    
    # Parse metadata
    try:
        metadata = json.loads(transaction.tx_metadata_json) if transaction.tx_metadata_json else {}
    except json.JSONDecodeError:
        metadata = {}
    
    # Get institution name
    institution_name = ""
    if 'receiver_institution_id' in metadata:
        institution = FinancialInstitution.query.get(metadata.get('receiver_institution_id'))
        if institution:
            institution_name = institution.name
    elif 'receiver_institution_name' in metadata:
        institution_name = metadata.get('receiver_institution_name')
    
    # Get message details based on transaction type
    if transaction.transaction_type == TransactionType.SWIFT_FUND_TRANSFER:
        message_type = "MT103"
        ordering_customer = metadata.get('ordering_customer', '')
        beneficiary_customer = metadata.get('beneficiary_customer', '')
        details_of_payment = metadata.get('details_of_payment', '')
    elif transaction.transaction_type == TransactionType.SWIFT_INSTITUTION_TRANSFER:
        message_type = "MT202"
        ordering_customer = metadata.get('ordering_customer', '')
        beneficiary_customer = metadata.get('beneficiary_customer', '')
        details_of_payment = metadata.get('details_of_payment', '')
    elif transaction.transaction_type == TransactionType.SWIFT_LETTER_OF_CREDIT:
        message_type = "MT760"
        ordering_customer = metadata.get('beneficiary', '')
        beneficiary_customer = institution_name
        details_of_payment = metadata.get('terms_and_conditions', '')
    else:  # SWIFT_FREE_FORMAT
        message_type = "MT799"
        ordering_customer = ''
        beneficiary_customer = institution_name
        details_of_payment = metadata.get('message_body', '')
    
    # Generate a receiver BIC from institution name
    if institution_name:
        # Sanitize name and generate BIC-like code
        receiver_bic = re.sub(r'[^A-Z0-9]', '', institution_name.upper()[:8])
        receiver_bic = receiver_bic.ljust(8, 'X')
    else:
        receiver_bic = "BANKXXXX"
    
    return render_template(
        'swift_message_view.html',
        transaction=transaction,
        message_type=message_type,
        institution_name=institution_name,
        ordering_customer=ordering_customer,
        beneficiary_customer=beneficiary_customer,
        details_of_payment=details_of_payment,
        receiver_bic=receiver_bic
    )

@swift.route('/api/swift/status/<transaction_id>')
@login_required
def api_swift_status(transaction_id):
    """API endpoint to get SWIFT message status"""
    # Flask-Login's login_required decorator ensures the user is authenticated
    # We can safely use current_user
    
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