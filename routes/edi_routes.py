"""
EDI Integration Routes for NVC Banking Platform
Provides web interface for managing EDI partners and transactions
"""
import os
import logging
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import User, Transaction, TransactionStatus, TransactionType, db
from auth import admin_required
from utils import generate_uuid
from edi_integration import (
    edi_service, EdiPartner, EdiFormat, EdiTransactionType,
    create_edi_transaction_from_nvc_transaction, process_edi_transaction
)

# Configure logger
logger = logging.getLogger(__name__)

# Create Blueprint
edi = Blueprint('edi', __name__, url_prefix='/edi')

@edi.route('/')
@login_required
@admin_required
def edi_dashboard():
    """EDI Dashboard - Overview of EDI activity"""
    # Get all EDI partners
    partners = edi_service.list_partners()
    
    # Get recent transactions that have EDI processing
    recent_transactions = Transaction.query.filter(
        Transaction.notes.like("%EDI transaction%")
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    
    return render_template(
        'edi/dashboard.html',
        partners=partners,
        recent_transactions=recent_transactions,
        partner_count=len(partners)
    )

@edi.route('/partners')
@login_required
@admin_required
def partner_list():
    """List all EDI partners"""
    partners = edi_service.list_partners()
    return render_template(
        'edi/partner_list.html',
        partners=partners
    )

@edi.route('/partners/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_partner():
    """Create a new EDI partner"""
    if request.method == 'POST':
        # Get form data
        partner_id = request.form.get('partner_id')
        name = request.form.get('name')
        routing_number = request.form.get('routing_number')
        account_number = request.form.get('account_number')
        edi_format = request.form.get('edi_format')
        connection_type = request.form.get('connection_type')
        is_active = request.form.get('is_active') == 'on'
        
        # Get credentials
        credentials = {}
        if connection_type == 'SFTP':
            credentials['sftp_host'] = request.form.get('sftp_host')
            credentials['sftp_port'] = request.form.get('sftp_port')
            credentials['sftp_username'] = request.form.get('sftp_username')
            credentials['sftp_password'] = request.form.get('sftp_password')
            credentials['sftp_remote_dir'] = request.form.get('sftp_remote_dir')
        
        # Validate required fields
        if not partner_id or not name or not edi_format or not connection_type:
            flash('Missing required fields', 'danger')
            return render_template(
                'edi/partner_form.html',
                partner=None,
                edi_formats=[format.value for format in EdiFormat],
                connection_types=['SFTP']
            )
        
        # Create new partner
        partner = EdiPartner(
            partner_id=partner_id,
            name=name,
            routing_number=routing_number,
            account_number=account_number,
            edi_format=EdiFormat(edi_format),
            connection_type=connection_type,
            credentials=credentials,
            is_active=is_active
        )
        
        # Add partner
        edi_service.add_partner(partner)
        
        flash(f'EDI partner {name} created successfully', 'success')
        return redirect(url_for('edi.partner_list'))
    
    # GET request - show form
    return render_template(
        'edi/partner_form.html',
        partner=None,
        edi_formats=[format.value for format in EdiFormat],
        connection_types=['SFTP']
    )

@edi.route('/partners/<partner_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_partner(partner_id):
    """Edit an EDI partner"""
    partner = edi_service.get_partner(partner_id)
    if not partner:
        flash('EDI partner not found', 'danger')
        return redirect(url_for('edi.partner_list'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        routing_number = request.form.get('routing_number')
        account_number = request.form.get('account_number')
        edi_format = request.form.get('edi_format')
        connection_type = request.form.get('connection_type')
        is_active = request.form.get('is_active') == 'on'
        
        # Get credentials
        credentials = {}
        if connection_type == 'SFTP':
            credentials['sftp_host'] = request.form.get('sftp_host')
            credentials['sftp_port'] = request.form.get('sftp_port')
            credentials['sftp_username'] = request.form.get('sftp_username')
            
            # Only update password if provided
            password = request.form.get('sftp_password')
            if password:
                credentials['sftp_password'] = password
            elif 'sftp_password' in partner.credentials:
                credentials['sftp_password'] = partner.credentials['sftp_password']
            
            credentials['sftp_remote_dir'] = request.form.get('sftp_remote_dir')
        
        # Validate required fields
        if not name or not edi_format or not connection_type:
            flash('Missing required fields', 'danger')
            return render_template(
                'edi/partner_form.html',
                partner=partner,
                edi_formats=[format.value for format in EdiFormat],
                connection_types=['SFTP']
            )
        
        # Update partner
        partner.name = name
        partner.routing_number = routing_number
        partner.account_number = account_number
        partner.edi_format = EdiFormat(edi_format)
        partner.connection_type = connection_type
        partner.credentials = credentials
        partner.is_active = is_active
        
        # Save partner
        edi_service.add_partner(partner)
        
        flash(f'EDI partner {name} updated successfully', 'success')
        return redirect(url_for('edi.partner_list'))
    
    # GET request - show form
    return render_template(
        'edi/partner_form.html',
        partner=partner,
        edi_formats=[format.value for format in EdiFormat],
        connection_types=['SFTP']
    )

@edi.route('/partners/<partner_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_partner(partner_id):
    """Delete an EDI partner"""
    success = edi_service.delete_partner(partner_id)
    if success:
        flash('EDI partner deleted successfully', 'success')
    else:
        flash('Failed to delete EDI partner', 'danger')
    
    return redirect(url_for('edi.partner_list'))

@edi.route('/transactions')
@login_required
@admin_required
def transaction_list():
    """List EDI transactions"""
    # In a real system, you would store EDI transactions in the database
    # For now, we'll just show regular transactions with EDI notes
    transactions = Transaction.query.filter(
        Transaction.notes.like("%EDI transaction%")
    ).order_by(Transaction.created_at.desc()).all()
    
    return render_template(
        'edi/transaction_list.html',
        transactions=transactions
    )

@edi.route('/test/<partner_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def test_edi_connection(partner_id):
    """Test EDI connection with a partner"""
    partner = edi_service.get_partner(partner_id)
    if not partner:
        flash('EDI partner not found', 'danger')
        return redirect(url_for('edi.partner_list'))
    
    if request.method == 'POST':
        # Create a test transaction
        transaction_type = EdiTransactionType.X12_820 if partner.edi_format == EdiFormat.X12 else \
                          EdiTransactionType.EDIFACT_PAYORD if partner.edi_format == EdiFormat.EDIFACT else \
                          EdiTransactionType.CUST_PAYMENT
        
        # Test amount and currency
        amount = 1.00
        currency = "USD"
        
        # Originator info (NVC Global)
        originator_info = {
            "name": "NVC Global Banking Platform",
            "id": "NVC001",
            "bank_id": "NVCBANK001",
            "routing_number": "021000021",  # Example routing number
            "account_number": "1234567890"  # Example account number
        }
        
        # Beneficiary info (partner)
        beneficiary_info = {
            "name": partner.name,
            "bank_id": partner.partner_id,
            "routing_number": partner.routing_number,
            "account_number": partner.account_number or "0000000000"
        }
        
        # Create test EDI transaction
        test_transaction = edi_service.create_edi_transaction(
            partner_id=partner_id,
            transaction_type=transaction_type,
            amount=amount,
            currency=currency,
            originator_info=originator_info,
            beneficiary_info=beneficiary_info,
            reference_number=f"TEST-{generate_uuid()[:8]}",
            description="Test EDI Connection",
            metadata={"test": True, "created_by": current_user.username}
        )
        
        if not test_transaction:
            flash('Failed to create test EDI transaction', 'danger')
            return redirect(url_for('edi.partner_detail', partner_id=partner_id))
        
        # Generate EDI message but don't actually send it
        # Just display the message for testing
        
        return render_template(
            'edi/test_connection_result.html',
            partner=partner,
            transaction=test_transaction,
            success=True,
            edi_message=test_transaction.edi_message
        )
    
    # GET request - show form
    return render_template(
        'edi/test_connection.html',
        partner=partner
    )

@edi.route('/process-transaction/<transaction_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def process_transaction(transaction_id):
    """Process a transaction via EDI"""
    # Get the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    if not transaction:
        flash('Transaction not found', 'danger')
        return redirect(url_for('web.main.transactions'))
    
    # Get all active partners
    partners = [p for p in edi_service.list_partners() if p.is_active]
    
    if request.method == 'POST':
        # Get selected partner
        partner_id = request.form.get('partner_id')
        if not partner_id:
            flash('Please select an EDI partner', 'danger')
            return render_template(
                'edi/process_transaction.html',
                transaction=transaction,
                partners=partners
            )
        
        # Process the transaction
        success = process_edi_transaction(transaction, partner_id)
        
        if success:
            flash('Transaction processed via EDI successfully', 'success')
            return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
        else:
            flash('Failed to process transaction via EDI', 'danger')
            return render_template(
                'edi/process_transaction.html',
                transaction=transaction,
                partners=partners
            )
    
    # GET request - show form
    return render_template(
        'edi/process_transaction.html',
        transaction=transaction,
        partners=partners
    )

@edi.route('/upload-acknowledgment/<partner_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_acknowledgment(partner_id):
    """Upload and process an EDI acknowledgment"""
    partner = edi_service.get_partner(partner_id)
    if not partner:
        flash('EDI partner not found', 'danger')
        return redirect(url_for('edi.partner_list'))
    
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'acknowledgment_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['acknowledgment_file']
        
        # If user does not select file, browser also submits an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file:
            # Save to temporary file
            filename = secure_filename(file.filename)
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            filepath = os.path.join(temp_dir, filename)
            file.save(filepath)
            
            # Read file
            with open(filepath, 'r') as f:
                file_content = f.read()
            
            # Process acknowledgment
            result = edi_service.process_edi_acknowledgment(partner_id, file_content)
            
            # Clean up
            os.remove(filepath)
            
            return render_template(
                'edi/acknowledgment_result.html',
                partner=partner,
                result=result,
                file_name=filename
            )
    
    # GET request - show upload form
    return render_template(
        'edi/upload_acknowledgment.html',
        partner=partner
    )