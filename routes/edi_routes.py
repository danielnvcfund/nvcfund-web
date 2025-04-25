"""
Routes for handling Electronic Data Interchange (EDI) operations
"""

import os
import json
import logging
from datetime import datetime, timedelta

import flask
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from auth import admin_required
from edi_integration import edi_service, EdiFormat, EdiTransaction, EdiTransactionType, process_edi_transaction
from models import Transaction, TransactionType, TransactionStatus, User
from forms import EdiPartnerForm, EDITransactionForm
from utils import generate_transaction_id, generate_uuid

logger = logging.getLogger(__name__)

# Create the blueprint
edi = Blueprint('edi', __name__, url_prefix='/edi')

@edi.route('/dashboard')
@login_required
def dashboard():
    """EDI Dashboard"""
    # Get active partners
    partners = edi_service.list_partners()
    
    # Get recent EDI transactions
    recent_transactions = []
    
    try:
        # Query the most recent EDI transactions
        recent_transactions = Transaction.query.filter(
            Transaction.transaction_type.in_([
                TransactionType.EDI_PAYMENT,
                TransactionType.EDI_ACH_TRANSFER,
                TransactionType.EDI_WIRE_TRANSFER
            ])
        ).order_by(Transaction.created_at.desc()).limit(5).all()
    except Exception as e:
        logger.error(f"Error fetching EDI transactions: {str(e)}")
        flash("Could not load recent EDI transactions.", "error")
    
    return render_template('edi/dashboard.html', 
                          partners=partners,
                          partner_count=len(partners),
                          recent_transactions=recent_transactions)

@edi.route('/partners')
@login_required
def partner_list():
    """List all EDI partners"""
    partners = edi_service.list_partners()
    return render_template('edi/partner_list.html', partners=partners)

@edi.route('/partners/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_partner():
    """Add a new EDI partner"""
    form = EdiPartnerForm()
    
    if form.validate_on_submit():
        try:
            # Create new partner
            credentials = {
                "sftp_host": form.sftp_host.data,
                "sftp_port": form.sftp_port.data,
                "sftp_username": form.sftp_username.data,
                "sftp_remote_dir": form.sftp_remote_dir.data
            }
            
            # Only set password if provided
            if form.sftp_password.data:
                credentials["sftp_password"] = form.sftp_password.data
            
            # Convert EDI format string to enum
            edi_format = EdiFormat[form.edi_format.data]
            
            # Create partner
            partner = edi_service.add_partner({
                "partner_id": form.partner_id.data,
                "name": form.name.data,
                "routing_number": form.routing_number.data,
                "account_number": form.account_number.data,
                "edi_format": edi_format,
                "connection_type": form.connection_type.data,
                "credentials": credentials,
                "is_active": form.is_active.data
            })
            
            flash(f"EDI partner {partner.name} added successfully.", "success")
            return redirect(url_for('edi.partner_list'))
        except Exception as e:
            logger.error(f"Error adding EDI partner: {str(e)}")
            flash(f"Failed to add EDI partner: {str(e)}", "error")
    
    return render_template('edi/new_partner.html', form=form)

@edi.route('/partners/edit/<partner_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_partner(partner_id):
    """Edit an existing EDI partner"""
    partner = edi_service.get_partner(partner_id)
    
    if not partner:
        flash(f"EDI partner with ID {partner_id} not found.", "error")
        return redirect(url_for('edi.partner_list'))
    
    form = EdiPartnerForm(obj=partner)
    
    # Pre-fill credentials
    if partner.credentials:
        form.sftp_host.data = partner.credentials.get("sftp_host", "")
        form.sftp_port.data = partner.credentials.get("sftp_port", "22")
        form.sftp_username.data = partner.credentials.get("sftp_username", "")
        form.sftp_remote_dir.data = partner.credentials.get("sftp_remote_dir", "")
    
    if form.validate_on_submit():
        try:
            # Update credentials
            credentials = {
                "sftp_host": form.sftp_host.data,
                "sftp_port": form.sftp_port.data,
                "sftp_username": form.sftp_username.data,
                "sftp_remote_dir": form.sftp_remote_dir.data
            }
            
            # Only update password if provided
            if form.sftp_password.data:
                credentials["sftp_password"] = form.sftp_password.data
            elif partner.credentials and "sftp_password" in partner.credentials:
                credentials["sftp_password"] = partner.credentials["sftp_password"]
            
            # Convert EDI format string to enum
            edi_format = EdiFormat[form.edi_format.data]
            
            # Update partner
            updated_partner = edi_service.add_partner({
                "partner_id": partner_id,  # Keep the original ID
                "name": form.name.data,
                "routing_number": form.routing_number.data,
                "account_number": form.account_number.data,
                "edi_format": edi_format,
                "connection_type": form.connection_type.data,
                "credentials": credentials,
                "is_active": form.is_active.data
            })
            
            flash(f"EDI partner {updated_partner.name} updated successfully.", "success")
            return redirect(url_for('edi.partner_list'))
        except Exception as e:
            logger.error(f"Error updating EDI partner: {str(e)}")
            flash(f"Failed to update EDI partner: {str(e)}", "error")
    
    return render_template('edi/edit_partner.html', form=form, partner=partner)

@edi.route('/partners/delete/<partner_id>')
@login_required
@admin_required
def delete_partner(partner_id):
    """Delete an EDI partner"""
    if edi_service.delete_partner(partner_id):
        flash(f"EDI partner with ID {partner_id} deleted successfully.", "success")
    else:
        flash(f"Failed to delete EDI partner with ID {partner_id}.", "error")
    
    return redirect(url_for('edi.partner_list'))

@edi.route('/partners/test-connection/<partner_id>')
@login_required
def test_edi_connection(partner_id):
    """Test connection to an EDI partner"""
    partner = edi_service.get_partner(partner_id)
    
    if not partner:
        flash(f"EDI partner with ID {partner_id} not found.", "error")
        return redirect(url_for('edi.partner_list'))
    
    # Create a test file with current timestamp
    test_data = f"NVC Banking Platform EDI Test - {datetime.now().isoformat()}"
    
    try:
        # Write test file to temporary location
        test_file_path = os.path.join(current_app.config.get('TEMP_FOLDER', '/tmp'), f"edi_test_{generate_uuid()}.txt")
        with open(test_file_path, 'w') as f:
            f.write(test_data)
        
        # Try to upload the file
        result = edi_service._send_via_sftp(test_file_path, f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt", partner)
        
        # Remove the temporary file
        try:
            os.remove(test_file_path)
        except:
            pass
        
        if result:
            flash(f"Successfully connected to EDI partner {partner.name}.", "success")
        else:
            flash(f"Failed to connect to EDI partner {partner.name}. Please check credentials.", "error")
    except Exception as e:
        logger.error(f"Error testing EDI connection: {str(e)}")
        flash(f"Error testing connection: {str(e)}", "error")
    
    return redirect(url_for('edi.partner_list'))

@edi.route('/transactions')
@login_required
def transaction_list():
    """List EDI transactions"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get filter parameters
    partner_id = request.args.get('partner_id')
    transaction_type = request.args.get('transaction_type')
    status = request.args.get('status')
    
    # Build query
    query = Transaction.query.filter(
        Transaction.transaction_type.in_([
            TransactionType.EDI_PAYMENT,
            TransactionType.EDI_ACH_TRANSFER,
            TransactionType.EDI_WIRE_TRANSFER
        ])
    )
    
    # Apply filters
    if transaction_type:
        query = query.filter(Transaction.transaction_type == TransactionType[transaction_type])
    
    if status:
        query = query.filter(Transaction.status == TransactionStatus[status.upper()])
    
    # We need to check the metadata for partner_id filter
    if partner_id:
        # This is a more complex filter since partner_id is in metadata
        filtered_transaction_ids = []
        all_edi_transactions = query.all()
        
        for t in all_edi_transactions:
            if t.tx_metadata_json:
                try:
                    metadata = json.loads(t.tx_metadata_json)
                    if metadata.get('edi_partner_id') == partner_id:
                        filtered_transaction_ids.append(t.id)
                except:
                    pass
        
        if filtered_transaction_ids:
            query = query.filter(Transaction.id.in_(filtered_transaction_ids))
        else:
            # No transactions match the partner filter
            query = Transaction.query.filter(Transaction.id == -1)  # Empty result
    
    # Execute query with pagination
    pagination = query.order_by(Transaction.created_at.desc()).paginate(page=page, per_page=per_page)
    transactions = pagination.items
    
    # Process transactions to add metadata
    for transaction in transactions:
        if transaction.tx_metadata_json:
            try:
                transaction.metadata = json.loads(transaction.tx_metadata_json)
            except:
                transaction.metadata = {}
        else:
            transaction.metadata = {}
    
    # Get partners for filter dropdown
    partners = edi_service.list_partners()
    
    return render_template(
        'edi/transaction_list.html',
        transactions=transactions,
        pagination=pagination,
        partners=partners,
        request=request
    )

@edi.route('/transactions/<transaction_id>/retry')
@login_required
@admin_required
def retry_transaction(transaction_id):
    """Retry a failed EDI transaction"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        flash(f"Transaction with ID {transaction_id} not found.", "error")
        return redirect(url_for('edi.transaction_list'))
    
    if transaction.status != TransactionStatus.FAILED and transaction.status != TransactionStatus.PENDING:
        flash(f"Cannot retry transaction with status {transaction.status.value}.", "error")
        return redirect(url_for('edi.transaction_list'))
    
    # Get partner ID from metadata
    partner_id = None
    if transaction.tx_metadata_json:
        try:
            metadata = json.loads(transaction.tx_metadata_json)
            partner_id = metadata.get('edi_partner_id')
        except:
            pass
    
    if not partner_id:
        flash("Could not determine EDI partner for this transaction.", "error")
        return redirect(url_for('edi.transaction_list'))
    
    # Process the transaction
    if process_edi_transaction(transaction, partner_id):
        flash(f"Transaction {transaction_id} has been reprocessed.", "success")
    else:
        flash(f"Failed to reprocess transaction {transaction_id}.", "error")
    
    return redirect(url_for('edi.transaction_list'))

@edi.route('/transactions/<transaction_id>/message')
@login_required
def view_edi_message(transaction_id):
    """View EDI message for a transaction"""
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        flash(f"Transaction with ID {transaction_id} not found.", "error")
        return redirect(url_for('edi.transaction_list'))
    
    # Get EDI message from metadata
    edi_message = None
    partner_name = None
    if transaction.tx_metadata_json:
        try:
            metadata = json.loads(transaction.tx_metadata_json)
            edi_message = metadata.get('edi_message')
            partner_name = metadata.get('edi_partner_name')
        except:
            pass
    
    if not edi_message:
        flash("No EDI message found for this transaction.", "error")
        return redirect(url_for('edi.transaction_list'))
    
    return render_template(
        'edi/view_message.html',
        transaction=transaction,
        edi_message=edi_message,
        partner_name=partner_name
    )