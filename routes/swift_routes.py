"""
SWIFT Messaging Routes for NVC Banking Platform
This module contains routes for SWIFT messaging functions including:
- Standby Letters of Credit (MT760)
- Fund Transfers (MT103/MT202)
- Free Format Messages (MT799)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json

from app import db
from models import Transaction, TransactionType, TransactionStatus
from forms import LetterOfCreditForm, SwiftFundTransferForm, SwiftFreeFormatMessageForm
from swift_integration import SwiftService

swift = Blueprint('swift', __name__)

@swift.route('/letter_of_credit/new', methods=['GET', 'POST'])
@login_required
def new_letter_of_credit():
    """Create a new Standby Letter of Credit (SBLC) via SWIFT MT760"""
    form = LetterOfCreditForm()
    
    if form.validate_on_submit():
        # Create and send SWIFT MT760 Letter of Credit
        success, message, transaction = SwiftService.create_standby_letter_of_credit(
            user_id=current_user.id,
            receiver_institution_id=form.receiver_institution_id.data,
            amount=form.amount.data,
            currency=form.currency.data,
            beneficiary=form.beneficiary.data,
            expiry_date=form.expiry_date.data,
            terms_and_conditions=form.terms_and_conditions.data
        )
        
        if success:
            flash(f"Standby Letter of Credit created successfully. {message}", "success")
            return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
        else:
            flash(f"Failed to create Letter of Credit: {message}", "danger")
    
    return render_template('letter_of_credit_form.html', form=form)

@swift.route('/letter_of_credit/status/<transaction_id>')
@login_required
def letter_of_credit_status(transaction_id):
    """Check the status of a Letter of Credit"""
    # Get the transaction record
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id,
        user_id=current_user.id
    ).first()
    
    if not transaction:
        flash("Transaction not found", "danger")
        return redirect(url_for('web.main.transactions'))
    
    # Verify this is a Letter of Credit transaction
    if transaction.transaction_type != TransactionType.LETTER_OF_CREDIT:
        flash("This is not a Letter of Credit transaction", "warning")
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
    
    # Get SWIFT status information
    status_data = SwiftService.get_swift_message_status(transaction_id)
    
    # Extract SWIFT data from transaction metadata
    swift_data = {}
    try:
        metadata = json.loads(transaction.tx_metadata_json or '{}')
        swift_data = metadata.get('swift', {})
    except:
        pass
    
    return render_template('letter_of_credit_status.html', 
                          transaction=transaction,
                          swift_data=swift_data,
                          status_data=status_data)

@swift.route('/fund_transfer', methods=['GET', 'POST'])
@login_required
def swift_fund_transfer():
    """Create a new SWIFT fund transfer (MT103 or MT202)"""
    form = SwiftFundTransferForm()
    
    if form.validate_on_submit():
        # Create and send SWIFT fund transfer
        success, message, transaction = SwiftService.create_swift_fund_transfer(
            user_id=current_user.id,
            receiver_institution_id=form.receiver_institution_id.data,
            amount=form.amount.data,
            currency=form.currency.data,
            beneficiary_customer=form.beneficiary_customer.data,
            ordering_customer=form.ordering_customer.data,
            details_of_payment=form.details_of_payment.data,
            use_mt202=form.use_mt202.data
        )
        
        if success:
            flash(f"SWIFT transfer initiated successfully. {message}", "success")
            return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
        else:
            flash(f"Failed to initiate SWIFT transfer: {message}", "danger")
    
    return render_template('swift_fund_transfer_form.html', form=form)

@swift.route('/free_format_message', methods=['GET', 'POST'])
@login_required
def swift_free_format_message():
    """Send a SWIFT MT799 free format message"""
    form = SwiftFreeFormatMessageForm()
    
    if form.validate_on_submit():
        # Create and send SWIFT free format message
        success, message, transaction = SwiftService.send_free_format_message(
            user_id=current_user.id,
            receiver_institution_id=form.receiver_institution_id.data,
            reference=form.reference.data,
            narrative_text=form.narrative_text.data
        )
        
        if success:
            flash(f"SWIFT message sent successfully. {message}", "success")
            return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
        else:
            flash(f"Failed to send SWIFT message: {message}", "danger")
    
    return render_template('swift_free_format_message_form.html', form=form)

@swift.route('/message_status/<transaction_id>')
@login_required
def swift_message_status(transaction_id):
    """Check the status of any SWIFT message"""
    # Get the transaction record
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id,
        user_id=current_user.id
    ).first()
    
    if not transaction:
        flash("Transaction not found", "danger")
        return redirect(url_for('web.main.transactions'))
    
    # Check if this is a SWIFT-related transaction
    if transaction.transaction_type not in [
        TransactionType.LETTER_OF_CREDIT, 
        TransactionType.SWIFT_TRANSFER,
        TransactionType.SWIFT_MESSAGE
    ]:
        flash("This is not a SWIFT-related transaction", "warning")
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
    
    # Get SWIFT status information
    status_data = SwiftService.get_swift_message_status(transaction_id)
    
    # Extract SWIFT data from transaction metadata
    swift_data = {}
    try:
        metadata = json.loads(transaction.tx_metadata_json or '{}')
        swift_data = metadata.get('swift', {})
    except:
        pass
    
    # Render the appropriate template based on the transaction type
    if transaction.transaction_type == TransactionType.LETTER_OF_CREDIT:
        return render_template('letter_of_credit_status.html', 
                              transaction=transaction,
                              swift_data=swift_data,
                              status_data=status_data)
    else:
        return render_template('swift_message_status.html', 
                              transaction=transaction,
                              swift_data=swift_data,
                              status_data=status_data)