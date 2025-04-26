"""
SWIFT GPI Integration Routes
Routes for handling SWIFT GPI message uploads and processing
"""

import os
import uuid
import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import desc

from app import db
from auth import admin_required
from models import Transaction, TransactionStatus, TransactionType, User, SwiftMessage
from swift_integration import SwiftService
import utils

# Create the blueprint
swift_gpi_routes = Blueprint('swift_gpi', __name__, url_prefix='/swift-gpi')

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'mt', 'fin', 'swi', 'xml'}

def allowed_file(filename):
    """Check if the filename has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@swift_gpi_routes.route('/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_gpi_file():
    """Upload SWIFT GPI files for processing"""
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Generate a unique filename
            original_filename = secure_filename(file.filename)
            filename = f"{uuid.uuid4()}_{original_filename}"
            
            # Create uploads directory if it doesn't exist
            upload_folder = os.path.join(current_app.root_path, 'uploads', 'swift_gpi')
            os.makedirs(upload_folder, exist_ok=True)
            
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            # Process the file
            result = process_gpi_file(file_path, original_filename, current_user.id)
            
            if result['success']:
                flash(f'Successfully processed SWIFT GPI file. {result["messages_processed"]} messages imported.', 'success')
            else:
                flash(f'Error processing SWIFT GPI file: {result["error"]}', 'danger')
            
            return redirect(url_for('swift_gpi.gpi_dashboard'))
        
        flash('Invalid file type. Allowed types: txt, mt, fin, swi, xml', 'warning')
        return redirect(request.url)
    
    return render_template('swift/upload_gpi_file.html')

def process_gpi_file(file_path, original_filename, user_id):
    """
    Process a SWIFT GPI file and import messages into the database
    
    Args:
        file_path (str): Path to the uploaded file
        original_filename (str): Original name of the file
        user_id (int): ID of the user who uploaded the file
        
    Returns:
        dict: Processing result with success flag, error message, and count of processed messages
    """
    try:
        # Read the file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        # Parse SWIFT messages from the content
        # This is a simplified parsing logic - in a real-world scenario, you would use
        # a proper SWIFT message parser library or service
        messages = parse_swift_messages(content)
        
        # Process each message
        messages_processed = 0
        for msg in messages:
            # Create SwiftMessage record
            swift_message = SwiftMessage(
                message_type=msg['message_type'],
                sender_bic=msg['sender_bic'],
                receiver_bic=msg['receiver_bic'],
                message_text=msg['message_text'],
                reference=msg['reference'],
                related_reference=msg.get('related_reference'),
                amount=msg.get('amount'),
                currency=msg.get('currency'),
                value_date=msg.get('value_date'),
                status='RECEIVED',
                uploaded_by=user_id,
                file_source=original_filename
            )
            db.session.add(swift_message)
            messages_processed += 1
            
            # If this is a payment message (MT103, MT202), create a transaction record
            if msg['message_type'] in ['103', '202']:
                # Determine transaction type based on message content
                transaction_type = TransactionType.SWIFT_TRANSFER
                if 'IBAN' in msg['message_text']:
                    transaction_type = TransactionType.INTERNATIONAL_WIRE
                
                # Create the transaction
                transaction = Transaction(
                    transaction_id=utils.generate_transaction_id(),
                    user_id=user_id,
                    transaction_type=transaction_type,
                    amount=msg.get('amount', 0.0),
                    currency=msg.get('currency', 'USD'),
                    status=TransactionStatus.COMPLETED,
                    description=f"SWIFT GPI {msg['message_type']} - {msg['reference']}",
                    recipient_name=msg.get('beneficiary', 'Unknown'),
                    recipient_account=msg.get('beneficiary_account', 'Unknown'),
                    recipient_bank_name=msg.get('receiving_institution', 'Unknown'),
                    recipient_bank_swift=msg['receiver_bic'],
                    metadata={
                        'swift_message_id': swift_message.id,
                        'gpi_uetr': msg.get('uetr', ''),
                        'import_method': 'manual_upload',
                        'original_file': original_filename
                    }
                )
                db.session.add(transaction)
        
        # Commit all changes to the database
        db.session.commit()
        
        return {
            'success': True,
            'messages_processed': messages_processed,
            'error': None
        }
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing SWIFT GPI file: {str(e)}")
        return {
            'success': False,
            'messages_processed': 0,
            'error': str(e)
        }

def parse_swift_messages(content):
    """
    Parse SWIFT messages from file content
    
    This is a simplified parser for demonstration. In production,
    you would use a specialized SWIFT message parser.
    
    Args:
        content (str): File content to parse
        
    Returns:
        list: List of dictionaries containing parsed messages
    """
    messages = []
    
    # Simple heuristic: Split on '{1:' which typically starts a SWIFT message
    raw_messages = content.split('{1:')
    
    for i, raw_msg in enumerate(raw_messages):
        if i == 0 and not raw_msg.strip():
            continue  # Skip empty first split
        
        raw_msg = '{1:' + raw_msg if i > 0 else raw_msg
        
        # Extract basic message components
        try:
            # Basic parsing to extract key information
            message_type = extract_message_type(raw_msg)
            sender_bic = extract_sender_bic(raw_msg)
            receiver_bic = extract_receiver_bic(raw_msg)
            reference = extract_reference(raw_msg)
            related_reference = extract_related_reference(raw_msg)
            amount, currency = extract_amount_and_currency(raw_msg)
            value_date = extract_value_date(raw_msg)
            beneficiary = extract_beneficiary(raw_msg)
            beneficiary_account = extract_beneficiary_account(raw_msg)
            receiving_institution = extract_receiving_institution(raw_msg)
            uetr = extract_uetr(raw_msg)
            
            messages.append({
                'message_type': message_type,
                'sender_bic': sender_bic,
                'receiver_bic': receiver_bic,
                'message_text': raw_msg,
                'reference': reference,
                'related_reference': related_reference,
                'amount': amount,
                'currency': currency,
                'value_date': value_date,
                'beneficiary': beneficiary,
                'beneficiary_account': beneficiary_account,
                'receiving_institution': receiving_institution,
                'uetr': uetr
            })
        except Exception as e:
            current_app.logger.warning(f"Could not parse message: {str(e)}")
            # Add as unparsed message
            messages.append({
                'message_type': 'UNKNOWN',
                'sender_bic': 'UNKNOWN',
                'receiver_bic': 'UNKNOWN',
                'message_text': raw_msg,
                'reference': f"UNPARSED-{uuid.uuid4()}",
                'related_reference': None,
                'amount': None,
                'currency': None,
                'value_date': None
            })
    
    return messages

# Helper functions for SWIFT message parsing
def extract_message_type(message):
    """Extract the message type (e.g., 103, 202) from SWIFT message"""
    # Look for {2:O<type>} pattern
    if '{2:' in message:
        try:
            type_section = message.split('{2:')[1].split('}')[0]
            if 'MT' in type_section:
                return type_section.split('MT')[1][:3]
            else:
                return type_section[1:4]  # O103, I103, etc.
        except:
            pass
    
    # Fallback: look for specific MT indicators
    if ':20:' in message and ':32A:' in message:
        return '103'  # Common in MT103
    if ':20:' in message and ':21:' in message:
        return '202'  # Common in MT202
    
    return 'UNKNOWN'

def extract_sender_bic(message):
    """Extract the sender BIC from SWIFT message"""
    if '{1:' in message:
        try:
            header = message.split('{1:')[1].split('}')[0]
            return header[3:14].strip()  # Format F01BANKBICXXXX
        except:
            pass
    return 'UNKNOWN'

def extract_receiver_bic(message):
    """Extract the receiver BIC from SWIFT message"""
    if '{2:' in message:
        try:
            header = message.split('{2:')[1].split('}')[0]
            return header[-12:].strip()
        except:
            pass
    return 'UNKNOWN'

def extract_reference(message):
    """Extract the reference number from SWIFT message"""
    if ':20:' in message:
        try:
            ref_section = message.split(':20:')[1].split('\n')[0]
            return ref_section.strip()
        except:
            pass
    return f"REF-{uuid.uuid4()}"

def extract_related_reference(message):
    """Extract the related reference from SWIFT message"""
    if ':21:' in message:
        try:
            ref_section = message.split(':21:')[1].split('\n')[0]
            return ref_section.strip()
        except:
            pass
    return None

def extract_amount_and_currency(message):
    """Extract amount and currency from SWIFT message"""
    amount = None
    currency = None
    
    # Look for amount in field 32A (format: YYMMDDCURRENCY000000,00)
    if ':32A:' in message:
        try:
            amount_section = message.split(':32A:')[1].split('\n')[0].strip()
            currency = amount_section[6:9]
            amount_str = amount_section[9:].replace(',', '.')
            amount = float(amount_str)
        except:
            pass
    
    # Look for amount in field 33B 
    elif ':33B:' in message:
        try:
            amount_section = message.split(':33B:')[1].split('\n')[0].strip()
            currency = amount_section[:3]
            amount_str = amount_section[3:].replace(',', '.')
            amount = float(amount_str)
        except:
            pass
    
    return amount, currency

def extract_value_date(message):
    """Extract value date from SWIFT message"""
    if ':32A:' in message:
        try:
            date_section = message.split(':32A:')[1].split('\n')[0].strip()
            date_str = date_section[:6]  # YYMMDD
            year = 2000 + int(date_str[:2])  # Assuming 21st century
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            return datetime.date(year, month, day)
        except:
            pass
    return None

def extract_beneficiary(message):
    """Extract beneficiary name from SWIFT message"""
    if ':59:' in message:
        try:
            ben_section = message.split(':59:')[1].split('\n')[0].strip()
            return ben_section
        except:
            pass
    return 'Unknown'

def extract_beneficiary_account(message):
    """Extract beneficiary account from SWIFT message"""
    if ':59:/' in message:
        try:
            account_section = message.split(':59:/')[1].split('\n')[0].strip()
            return account_section
        except:
            pass
    return 'Unknown'

def extract_receiving_institution(message):
    """Extract receiving institution from SWIFT message"""
    if ':57A:' in message:
        try:
            inst_section = message.split(':57A:')[1].split('\n')[0].strip()
            return inst_section
        except:
            pass
    return 'Unknown'

def extract_uetr(message):
    """Extract UETR (Unique End-to-end Transaction Reference) from SWIFT message"""
    if '{121:' in message:
        try:
            uetr_section = message.split('{121:')[1].split('}')[0].strip()
            return uetr_section
        except:
            pass
    return str(uuid.uuid4())  # Generate a placeholder UETR

@swift_gpi_routes.route('/dashboard')
@login_required
@admin_required
def gpi_dashboard():
    """Dashboard for SWIFT GPI transactions"""
    # Get the latest SWIFT messages
    messages = SwiftMessage.query.order_by(desc(SwiftMessage.created_at)).limit(20).all()
    
    # Count statistics
    total_messages = SwiftMessage.query.count()
    mt103_count = SwiftMessage.query.filter_by(message_type='103').count()
    mt202_count = SwiftMessage.query.filter_by(message_type='202').count()
    other_count = total_messages - mt103_count - mt202_count
    
    return render_template('swift/gpi_dashboard.html', 
                          messages=messages,
                          total_messages=total_messages,
                          mt103_count=mt103_count,
                          mt202_count=mt202_count,
                          other_count=other_count)

@swift_gpi_routes.route('/view/<int:message_id>')
@login_required
@admin_required
def view_message(message_id):
    """View detailed SWIFT message"""
    message = SwiftMessage.query.get_or_404(message_id)
    
    # Check if there's an associated transaction
    transaction = Transaction.query.filter(
        Transaction.metadata.contains({'swift_message_id': message_id})
    ).first()
    
    return render_template('swift/view_gpi_message.html', 
                          message=message,
                          transaction=transaction)

@swift_gpi_routes.route('/messages')
@login_required
@admin_required
def list_messages():
    """List all SWIFT messages with filtering options"""
    # Get filter parameters
    message_type = request.args.get('message_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    reference = request.args.get('reference', '')
    
    # Base query
    query = SwiftMessage.query
    
    # Apply filters
    if message_type:
        query = query.filter_by(message_type=message_type)
    
    if date_from:
        try:
            from_date = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(SwiftMessage.created_at >= from_date)
        except ValueError:
            flash('Invalid date format for From Date', 'warning')
    
    if date_to:
        try:
            to_date = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            # Add one day to include the entire day
            to_date = to_date + datetime.timedelta(days=1)
            query = query.filter(SwiftMessage.created_at < to_date)
        except ValueError:
            flash('Invalid date format for To Date', 'warning')
    
    if reference:
        query = query.filter(SwiftMessage.reference.ilike(f'%{reference}%'))
    
    # Execute query with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.order_by(desc(SwiftMessage.created_at)).paginate(
        page=page, per_page=per_page)
    
    # Create a pagination object that matches what the template expects
    pagination_info = {
        'page': page,
        'pages': pagination.pages,
        'total': pagination.total,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }
    
    return render_template('swift/list_gpi_messages.html', 
                          messages=pagination.items,
                          pagination=pagination_info,
                          message_type=message_type,
                          date_from=date_from,
                          date_to=date_to,
                          reference=reference)

@swift_gpi_routes.route('/api/reconcile', methods=['POST'])
@login_required
@admin_required
def reconcile_messages():
    """
    Reconcile SWIFT GPI messages with internal transactions
    
    This endpoint matches unreconciled SWIFT messages with
    transactions in the system based on reference numbers,
    amounts, and other identifying data.
    """
    try:
        # Get unreconciled messages
        unreconciled = SwiftMessage.query.filter_by(status='RECEIVED').all()
        
        reconciled_count = 0
        
        for message in unreconciled:
            # Look for matching transaction based on reference number
            transaction = Transaction.query.filter(
                Transaction.description.contains(message.reference)
            ).first()
            
            if transaction:
                # Update transaction with SWIFT message details
                transaction.metadata = transaction.metadata or {}
                transaction.metadata['swift_message_id'] = message.id
                
                # Update message status
                message.status = 'RECONCILED'
                
                reconciled_count += 1
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'reconciled_count': reconciled_count,
            'message': f'Successfully reconciled {reconciled_count} messages'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reconciling SWIFT messages: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500