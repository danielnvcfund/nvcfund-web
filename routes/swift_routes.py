"""
SWIFT Integration Routes
Routes for handling SWIFT messaging functionality including standby letters of credit,
fund transfers, and free format messages.
"""
import json
import logging
from datetime import datetime
import re

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user

from models import db, Transaction, TransactionType, TransactionStatus, FinancialInstitution
from forms import LetterOfCreditForm, SwiftFundTransferForm, SwiftFreeFormatMessageForm
from swift_integration import SwiftService

# Configure logger
logger = logging.getLogger(__name__)

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
            # Create the fund transfer with proper handling of None values
            transaction = SwiftService.create_swift_fund_transfer(
                user_id=user_id,  # Use the user_id from session instead of current_user
                receiver_institution_id=form.receiver_institution_id.data,
                receiver_institution_name=form.receiver_institution_name.data or '',
                amount=form.amount.data or 0,
                currency=form.currency.data or 'USD',
                ordering_customer=form.ordering_customer.data or '',
                beneficiary_customer=form.beneficiary_customer.data or '',
                details_of_payment=form.details_of_payment.data or '',
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
    
    # Get the transaction type safely
    tx_type = None
    try:
        if hasattr(transaction.transaction_type, 'value'):
            tx_type = transaction.transaction_type.value
        elif hasattr(transaction.transaction_type, 'name'):
            tx_type = transaction.transaction_type.name
        else:
            tx_type = str(transaction.transaction_type)
    except Exception as e:
        logger.error(f"Error determining transaction type: {str(e)}")
    
    # Try to determine message type from metadata first
    message_type = None
    try:
        if transaction.tx_metadata_json:
            metadata = json.loads(transaction.tx_metadata_json)
            if 'message_type' in metadata:
                message_type = metadata['message_type']
    except Exception as e:
        logger.error(f"Error parsing transaction metadata: {str(e)}")
    
    # Determine which status check to use based on transaction type or metadata
    if message_type == 'MT760' or (tx_type and 'letter_of_credit' in str(tx_type).lower()):
        status_data = SwiftService.get_letter_of_credit_status(transaction.id)
        template = 'letter_of_credit_status.html'
    elif message_type in ['MT103', 'MT202'] or (tx_type and ('fund_transfer' in str(tx_type).lower() or 'institution_transfer' in str(tx_type).lower())):
        status_data = SwiftService.get_fund_transfer_status(transaction.id)
        template = 'swift_fund_transfer_status.html'
    elif message_type == 'MT799' or (tx_type and 'free_format' in str(tx_type).lower()):
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
    
    # Check if this is a SWIFT free format message
    tx_type = None
    try:
        if hasattr(transaction.transaction_type, 'value'):
            tx_type = transaction.transaction_type.value
        elif hasattr(transaction.transaction_type, 'name'):
            tx_type = transaction.transaction_type.name
        else:
            tx_type = str(transaction.transaction_type)
        
        # Check if message type is in metadata
        message_type = None
        if transaction.tx_metadata_json:
            metadata = json.loads(transaction.tx_metadata_json)
            if 'message_type' in metadata:
                message_type = metadata['message_type']
                
        if not (message_type == 'MT799' or (tx_type and 'free_format' in str(tx_type).lower())):
            flash('This transaction is not a SWIFT free format message.', 'warning')
            return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
    except Exception as e:
        logger.error(f"Error determining transaction type: {str(e)}")
        flash('Error determining transaction type.', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
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
    
    # Check if this is a SWIFT fund transfer
    tx_type = None
    try:
        if hasattr(transaction.transaction_type, 'value'):
            tx_type = transaction.transaction_type.value
        elif hasattr(transaction.transaction_type, 'name'):
            tx_type = transaction.transaction_type.name
        else:
            tx_type = str(transaction.transaction_type)
        
        # Check if message type is in metadata
        message_type = None
        if transaction.tx_metadata_json:
            metadata = json.loads(transaction.tx_metadata_json)
            if 'message_type' in metadata:
                message_type = metadata['message_type']
                
        if not (message_type in ['MT103', 'MT202'] or (tx_type and ('fund_transfer' in str(tx_type).lower() or 'institution_transfer' in str(tx_type).lower()))):
            flash('This transaction is not a SWIFT fund transfer.', 'warning')
            return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
    except Exception as e:
        logger.error(f"Error determining transaction type: {str(e)}")
        flash('Error determining transaction type.', 'danger')
        return redirect(url_for('web.main.dashboard'))
    
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
    # Check for both enum and string values to handle different transaction creation methods
    
    # First, let's look for transactions with SWIFT-related metadata
    swift_transactions = []
    
    # Get all transactions for the current user
    all_user_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.created_at.desc()).all()
    
    # Get all transactions with SWIFT in their type string
    swift_type_transactions = []
    payment_type_transactions = []

    # First separate transactions by type to avoid enum comparison issues
    for tx in all_user_transactions:
        try:
            # Get the transaction type value safely
            tx_type = None
            if hasattr(tx.transaction_type, 'value'):
                tx_type = tx.transaction_type.value
            elif hasattr(tx.transaction_type, 'name'):
                tx_type = tx.transaction_type.name
            else:
                tx_type = str(tx.transaction_type)
                
            # Add to appropriate list
            if isinstance(tx_type, str) and 'swift' in tx_type.lower():
                swift_type_transactions.append(tx)
            elif tx_type == 'PAYMENT' or tx_type == 'payment':
                payment_type_transactions.append(tx)
        except Exception as e:
            logger.error(f"Error determining transaction type: {str(e)}")

    # Add all transactions with SWIFT in their type
    swift_transactions.extend(swift_type_transactions)
    
    # For PAYMENT transactions, check if they could be SWIFT
    for tx in payment_type_transactions:
        try:
            # Check for description hints first
            if tx.description and ('SWIFT' in tx.description or 'Letter of Credit' in tx.description or 
                                'Fund Transfer' in tx.description or 'Financial Institution Transfer' in tx.description):
                swift_transactions.append(tx)
                continue
                
            # Check if this is a SWIFT transaction based on metadata
            if tx.tx_metadata_json:
                try:
                    metadata = json.loads(tx.tx_metadata_json)
                    if ('message_type' in metadata and metadata['message_type'] in ['MT103', 'MT202', 'MT760', 'MT799']):
                        swift_transactions.append(tx)
                        continue
                    # Check for references that follow SWIFT formats
                    if 'reference' in metadata and any(metadata['reference'].startswith(prefix) 
                            for prefix in ['FT', 'IT', 'LC', 'FM']):
                        swift_transactions.append(tx)
                        continue
                    # Check for receiver institution which indicates SWIFT message
                    if 'receiver_institution' in metadata or 'receiving_institution' in metadata:
                        swift_transactions.append(tx)
                        continue
                except json.JSONDecodeError:
                    # Malformed JSON, just skip this check
                    pass
                
            # Special handling for PHP integration transactions that use PAYMENT type
            # but might be SWIFT transfers - check based on institution_id being set
            if tx.institution_id is not None:
                institution = FinancialInstitution.query.get(tx.institution_id)
                if institution and 'bank' in institution.name.lower():
                    swift_transactions.append(tx)
                    continue
        except Exception as e:
            logger.error(f"Error processing potential SWIFT transaction: {str(e)}")
            # Continue to next transaction
    
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
    try:
        is_swift_message = False
        
        # Get the transaction type value safely
        tx_type = None
        if hasattr(transaction.transaction_type, 'value'):
            tx_type = transaction.transaction_type.value
        elif hasattr(transaction.transaction_type, 'name'):
            tx_type = transaction.transaction_type.name
        else:
            tx_type = str(transaction.transaction_type)
            
        # Check if this is a SWIFT transaction type
        if isinstance(tx_type, str) and 'swift' in tx_type.lower():
            is_swift_message = True
        
        # If not a SWIFT type, check description for SWIFT hints
        if not is_swift_message and transaction.description and ('SWIFT' in transaction.description or 
                              'Letter of Credit' in transaction.description or 
                              'Fund Transfer' in transaction.description or 
                              'Financial Institution Transfer' in transaction.description):
            is_swift_message = True
            
        # Then check metadata for SWIFT-specific data
        if not is_swift_message and transaction.tx_metadata_json:
            try:
                metadata = json.loads(transaction.tx_metadata_json)
                if 'message_type' in metadata and metadata['message_type'] in ['MT103', 'MT202', 'MT760', 'MT799']:
                    is_swift_message = True
                # Check for references that follow SWIFT formats
                elif 'reference' in metadata and any(metadata['reference'].startswith(prefix) 
                        for prefix in ['FT', 'IT', 'LC', 'FM']):
                    is_swift_message = True
                # Check for receiver institution which indicates SWIFT message
                elif 'receiver_institution' in metadata or 'receiving_institution' in metadata:
                    is_swift_message = True
            except (json.JSONDecodeError, AttributeError):
                pass
                
        # Special case for PAYMENT type with institution ID (possible PHP integration)
        if not is_swift_message and (tx_type == 'PAYMENT' or tx_type == 'payment') and transaction.institution_id is not None:
            institution = FinancialInstitution.query.get(transaction.institution_id)
            if institution and 'bank' in institution.name.lower():
                is_swift_message = True
        
        if not is_swift_message:
            flash('This transaction is not a SWIFT message.', 'warning')
            return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
    except Exception as e:
        logger.error(f"Error checking if transaction is SWIFT message: {str(e)}")
        flash('Error processing transaction data.', 'danger')
        return redirect(url_for('web.swift.swift_messages'))
    
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
    
    # Try to determine message type from metadata first
    message_type = None
    if 'message_type' in metadata:
        message_type = metadata['message_type']  # MT103, MT202, etc.
    
    # Get message details based on transaction type
    if transaction.transaction_type == TransactionType.SWIFT_FUND_TRANSFER or message_type == 'MT103':
        message_type = "MT103"
        ordering_customer = metadata.get('ordering_customer', '')
        beneficiary_customer = metadata.get('beneficiary_customer', '')
        details_of_payment = metadata.get('details_of_payment', '')
    elif transaction.transaction_type == TransactionType.SWIFT_INSTITUTION_TRANSFER or message_type == 'MT202':
        message_type = "MT202"
        ordering_customer = metadata.get('ordering_customer', '')
        beneficiary_customer = metadata.get('beneficiary_customer', '')
        details_of_payment = metadata.get('details_of_payment', '')
    elif transaction.transaction_type == TransactionType.SWIFT_LETTER_OF_CREDIT or message_type == 'MT760':
        message_type = "MT760"
        ordering_customer = metadata.get('beneficiary', '')
        beneficiary_customer = institution_name
        details_of_payment = metadata.get('terms_and_conditions', '')
    elif transaction.transaction_type == TransactionType.SWIFT_FREE_FORMAT or message_type == 'MT799':
        message_type = "MT799"
        ordering_customer = ''
        beneficiary_customer = institution_name
        details_of_payment = metadata.get('message_body', '')
    else:
        # Fallback for PAYMENT or other types: Determine from description or defaults
        if 'Fund Transfer' in transaction.description:
            message_type = "MT103"
            ordering_customer = metadata.get('ordering_customer', current_user.first_name + ' ' + current_user.last_name if current_user.first_name else current_user.username)
            beneficiary_customer = metadata.get('beneficiary_customer', 'Beneficiary')
            details_of_payment = metadata.get('details_of_payment', transaction.description)
        elif 'Institution Transfer' in transaction.description:
            message_type = "MT202"
            ordering_customer = metadata.get('ordering_customer', 'NVC Global Banking')
            beneficiary_customer = institution_name or 'Receiving Institution'
            details_of_payment = metadata.get('details_of_payment', transaction.description)
        elif 'Letter of Credit' in transaction.description:
            message_type = "MT760"
            ordering_customer = metadata.get('beneficiary', current_user.first_name + ' ' + current_user.last_name if current_user.first_name else current_user.username)
            beneficiary_customer = institution_name or 'Beneficiary Institution'
            details_of_payment = metadata.get('terms_and_conditions', transaction.description)
        else:
            # Default to MT103 if can't determine
            message_type = "MT103"
            ordering_customer = current_user.first_name + ' ' + current_user.last_name if current_user.first_name else current_user.username
            beneficiary_customer = institution_name or 'Beneficiary'
            details_of_payment = transaction.description
    
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
    
    # Try to determine message type from metadata first
    message_type = None
    try:
        if transaction.tx_metadata_json:
            metadata = json.loads(transaction.tx_metadata_json)
            if 'message_type' in metadata:
                message_type = metadata['message_type']
    except Exception as e:
        logger.error(f"Error parsing transaction metadata: {str(e)}")
    
    # Get the transaction type value safely
    tx_type = None
    try:
        if hasattr(transaction.transaction_type, 'value'):
            tx_type = transaction.transaction_type.value
        elif hasattr(transaction.transaction_type, 'name'):
            tx_type = transaction.transaction_type.name
        else:
            tx_type = str(transaction.transaction_type)
    except Exception as e:
        logger.error(f"Error determining transaction type: {str(e)}")
    
    # Determine which status check to use based on transaction type or metadata
    if message_type == 'MT760' or (tx_type and 'letter_of_credit' in str(tx_type).lower()):
        status_data = SwiftService.get_letter_of_credit_status(transaction.id)
    elif message_type in ['MT103', 'MT202'] or (tx_type and ('fund_transfer' in str(tx_type).lower() or 'institution_transfer' in str(tx_type).lower())):
        status_data = SwiftService.get_fund_transfer_status(transaction.id)
    elif message_type == 'MT799' or (tx_type and 'free_format' in str(tx_type).lower()):
        status_data = SwiftService.get_free_format_message_status(transaction.id)
    else:
        # If we can't determine the type, use a generic status check
        try:
            # Provide a generic status based on transaction status
            status_value = None
            if hasattr(transaction.status, 'value'):
                status_value = transaction.status.value
            elif hasattr(transaction.status, 'name'):
                status_value = transaction.status.name
            else:
                status_value = str(transaction.status)
                
            status_data = {
                'success': True,
                'status': status_value,
                'timestamp': datetime.utcnow().isoformat(),
                'details': 'Transaction status retrieved successfully'
            }
        except Exception as e:
            logger.error(f"Error generating generic status: {str(e)}")
            status_data = {'success': False, 'error': 'Could not determine transaction type or status'}
        
    return jsonify(status_data)