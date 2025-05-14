"""
Wire Transfer Routes Module
This module handles the routes for the wire transfer functionality.
"""

import json
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, session, send_file
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from io import BytesIO
from utils import save_form_data_to_session, restore_form_data_from_session, clear_form_data_from_session
from generate_wire_transfer_pdf import generate_wire_transfer_pdf

from models import db, User, WireTransfer, CorrespondentBank, Transaction, TreasuryAccount, TreasuryTransaction, TreasuryTransactionType, TransactionStatus
from utils import generate_transaction_id, generate_unique_id, format_currency
from forms import WireTransferForm
from wire_transfer_service import (
    create_wire_transfer, process_wire_transfer, confirm_wire_transfer, 
    cancel_wire_transfer, reject_wire_transfer, get_wire_transfer,
    get_user_wire_transfers, get_active_correspondent_banks
)
import decorators  # Import the decorators module
from decorators import roles_required
from utils import format_currency

# Blueprint Definition
wire_transfer_bp = Blueprint('wire_transfer', __name__, url_prefix='/wire-transfers')


@wire_transfer_bp.route('/download/<int:wire_transfer_id>', methods=['GET'])
@login_required
def download_wire_transfer_pdf(wire_transfer_id):
    """Download a PDF receipt for a wire transfer"""
    try:
        # Check access permission
        wire_transfer = WireTransfer.query.get_or_404(wire_transfer_id)
        
        # Check if current user has access to this wire transfer
        if current_user.role.name != 'ADMIN' and (not wire_transfer.user or wire_transfer.user.id != current_user.id):
            flash("You don't have permission to access this wire transfer", "danger")
            return redirect(url_for('wire_transfer.list_wire_transfers'))
        
        # Generate the PDF
        pdf_bytes, filename = generate_wire_transfer_pdf(wire_transfer_id)
        
        if not pdf_bytes:
            flash(f"Could not generate PDF: {filename}", "danger")
            return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer_id))
        
        # Create BytesIO object
        pdf_buffer = BytesIO(pdf_bytes)
        pdf_buffer.seek(0)
        
        # Send the PDF as a response
        return send_file(
            pdf_buffer,
            download_name=filename,
            as_attachment=True,
            mimetype='application/pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error downloading wire transfer PDF: {str(e)}")
        flash(f"Error generating PDF: {str(e)}", "danger")
        return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer_id))


@wire_transfer_bp.route('/', methods=['GET'])
@login_required
def list_wire_transfers():
    """List all wire transfers for the current user or all transfers for admin users"""
    if current_user.role.name == 'ADMIN':
        # Admin can see all wire transfers
        wire_transfers = WireTransfer.query.order_by(WireTransfer.created_at.desc()).all()
    else:
        # Regular users only see their own transfers
        wire_transfers = get_user_wire_transfers(current_user.id)
    
    return render_template(
        'wire_transfers/list.html',
        wire_transfers=wire_transfers,
        title="Wire Transfers"
    )


@wire_transfer_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_wire_transfer():
    """Create a new wire transfer"""
    # Get active correspondent banks that support wire transfers
    correspondent_banks = get_active_correspondent_banks()
    if not correspondent_banks:
        flash("No active correspondent banks available for wire transfers.", "warning")
        return redirect(url_for('wire_transfer.list_wire_transfers'))
    
    # Get treasury accounts for the user
    try:
        treasury_accounts = TreasuryAccount.query.filter_by(is_active=True).all()
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error getting treasury accounts: {str(e)}")
        flash("An error occurred while retrieving treasury accounts", "danger")
        return redirect(url_for('wire_transfer.list_wire_transfers'))
    
    form = WireTransferForm()
    
    # Populate form choices
    form.correspondent_bank_id.choices = [
        (bank.id, f"{bank.name} - SWIFT: {bank.swift_code}") for bank in correspondent_banks
    ]
    
    form.treasury_account_id.choices = [
        (account.id, f"{account.name} - {account.currency} {account.available_balance}") 
        for account in treasury_accounts
    ]
    
    # Form data will be automatically restored when rendering the form
    
    if form.validate_on_submit():
        try:
            # Save form data to session in case we encounter an error
            save_form_data_to_session(form)
            
            # Get the treasury account
            treasury_account = TreasuryAccount.query.get(form.treasury_account_id.data)
            if not treasury_account:
                flash("Treasury account not found", "danger")
                return redirect(url_for('wire_transfer.new_wire_transfer'))
            
            # Check if there's enough balance
            if treasury_account.available_balance < form.amount.data:
                flash("Insufficient funds in the selected treasury account", "danger")
                return redirect(url_for('wire_transfer.new_wire_transfer'))
            
            # Generate unique transaction ID and reference number for the wire transfer
            transaction_id = generate_transaction_id()
            reference_number = f"WIRE-{generate_unique_id()}"
            
            # Create treasury transaction for the wire transfer
            treasury_tx = TreasuryTransaction()
            treasury_tx.transaction_id = transaction_id
            treasury_tx.from_account_id = treasury_account.id
            treasury_tx.transaction_type = TreasuryTransactionType.EXTERNAL_TRANSFER
            treasury_tx.amount = form.amount.data
            treasury_tx.currency = treasury_account.currency
            treasury_tx.description = f"Wire transfer to {form.beneficiary_name.data} via {form.beneficiary_bank_name.data}"
            treasury_tx.status = TransactionStatus.PENDING
            treasury_tx.reference_number = reference_number
            treasury_tx.created_by = current_user.id
            db.session.add(treasury_tx)
            db.session.commit()
            
            # Create the wire transfer
            wire_transfer, transaction, error = create_wire_transfer(
                user_id=current_user.id,
                correspondent_bank_id=form.correspondent_bank_id.data,
                amount=form.amount.data,
                currency=treasury_account.currency,
                originator_name=form.originator_name.data,
                originator_account=form.originator_account.data,
                originator_address=form.originator_address.data,
                beneficiary_name=form.beneficiary_name.data,
                beneficiary_account=form.beneficiary_account.data,
                beneficiary_address=form.beneficiary_address.data,
                beneficiary_bank_name=form.beneficiary_bank_name.data,
                beneficiary_bank_address=form.beneficiary_bank_address.data,
                beneficiary_bank_swift=form.beneficiary_bank_swift.data,
                beneficiary_bank_routing=form.beneficiary_bank_routing.data,
                intermediary_bank_name=form.intermediary_bank_name.data,
                intermediary_bank_swift=form.intermediary_bank_swift.data,
                purpose=form.purpose.data,
                message_to_beneficiary=form.message_to_beneficiary.data,
                treasury_transaction_id=treasury_tx.id
            )
            
            if error:
                db.session.rollback()
                # We don't clear the form data here so it will be restored when the form loads again
                flash(f"Error creating wire transfer: {error}", "danger")
                return redirect(url_for('wire_transfer.new_wire_transfer'))
            
            # Link the wire transfer to the treasury transaction
            wire_transfer.treasury_transaction_id = treasury_tx.id
            db.session.commit()
            
            # Clear form data from session on successful submission
            clear_form_data_from_session(WireTransferForm)
            
            flash("Wire transfer created successfully", "success")
            return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer.id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error creating wire transfer: {str(e)}")
            # We retain form data in session for this error case too
            flash("An error occurred while creating the wire transfer", "danger")
    
    # Prepopulate form fields with user information only if there's no saved form data
    if request.method == 'GET' and not restore_form_data_from_session(form):
        form.originator_name.data = current_user.full_name
        
    return render_template(
        'wire_transfers/new.html',
        form=form,
        title="New Wire Transfer"
    )


@wire_transfer_bp.route('/<int:wire_transfer_id>', methods=['GET'])
@login_required
def view_wire_transfer(wire_transfer_id):
    """View wire transfer details"""
    wire_transfer = WireTransfer.query.get_or_404(wire_transfer_id)
    
    # Check if the user is authorized to view this wire transfer
    if current_user.role.name != 'ADMIN' and wire_transfer.user_id != current_user.id:
        flash("You are not authorized to view this wire transfer", "danger")
        return redirect(url_for('wire_transfer.list_wire_transfers'))
    
    return render_template(
        'wire_transfers/view.html',
        wire_transfer=wire_transfer,
        title=f"Wire Transfer {wire_transfer.reference_number}"
    )


@wire_transfer_bp.route('/<int:wire_transfer_id>/process', methods=['POST'])
@login_required
@roles_required(['ADMIN', 'TREASURY_MANAGER'])
def process_transfer(wire_transfer_id):
    """Process a wire transfer (send to correspondent bank)"""
    wire_transfer = WireTransfer.query.get_or_404(wire_transfer_id)
    
    # Verify the wire transfer can be processed
    if wire_transfer.status.value != 'pending':
        flash(f"Wire transfer cannot be processed (status: {wire_transfer.status.value})", "danger")
        return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer.id))
    
    # Process the transfer
    success, error = process_wire_transfer(wire_transfer_id)
    if success:
        flash("Wire transfer processed successfully", "success")
    else:
        flash(f"Error processing wire transfer: {error}", "danger")
    
    return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer.id))


@wire_transfer_bp.route('/<int:wire_transfer_id>/confirm', methods=['POST'])
@login_required
@roles_required(['ADMIN', 'TREASURY_MANAGER'])
def confirm_transfer(wire_transfer_id):
    """Confirm a wire transfer as completed"""
    wire_transfer = WireTransfer.query.get_or_404(wire_transfer_id)
    
    # Get confirmation details
    confirmation_number = request.form.get('confirmation_number')
    reference_number = request.form.get('reference_number')
    
    # Verify the wire transfer can be confirmed
    if wire_transfer.status.value != 'processing':
        flash(f"Wire transfer cannot be confirmed (status: {wire_transfer.status.value})", "danger")
        return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer.id))
    
    # Confirm the transfer
    success, error = confirm_wire_transfer(
        wire_transfer_id=wire_transfer_id,
        confirmation_number=confirmation_number,
        reference_number=reference_number
    )
    
    if success:
        flash("Wire transfer confirmed successfully", "success")
    else:
        flash(f"Error confirming wire transfer: {error}", "danger")
    
    return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer.id))


@wire_transfer_bp.route('/<int:wire_transfer_id>/cancel', methods=['POST'])
@login_required
def cancel_transfer(wire_transfer_id):
    """Cancel a wire transfer"""
    wire_transfer = WireTransfer.query.get_or_404(wire_transfer_id)
    
    # Check if the user is authorized to cancel this wire transfer
    if current_user.role.name != 'ADMIN' and wire_transfer.user_id != current_user.id:
        flash("You are not authorized to cancel this wire transfer", "danger")
        return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer.id))
    
    # Get cancellation reason
    reason = request.form.get('reason')
    
    # Verify the wire transfer can be cancelled
    if wire_transfer.status.value not in ['pending', 'processing']:
        flash(f"Wire transfer cannot be cancelled (status: {wire_transfer.status.value})", "danger")
        return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer.id))
    
    # Cancel the transfer
    success, error = cancel_wire_transfer(wire_transfer_id, reason)
    if success:
        flash("Wire transfer cancelled successfully", "success")
    else:
        flash(f"Error cancelling wire transfer: {error}", "danger")
    
    return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer.id))


@wire_transfer_bp.route('/<int:wire_transfer_id>/reject', methods=['POST'])
@login_required
@roles_required(['ADMIN', 'TREASURY_MANAGER'])
def reject_transfer(wire_transfer_id):
    """Reject a wire transfer"""
    wire_transfer = WireTransfer.query.get_or_404(wire_transfer_id)
    
    # Get rejection reason
    reason = request.form.get('reason')
    if not reason:
        flash("Rejection reason is required", "danger")
        return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer.id))
    
    # Verify the wire transfer can be rejected
    if wire_transfer.status.value not in ['pending', 'processing']:
        flash(f"Wire transfer cannot be rejected (status: {wire_transfer.status.value})", "danger")
        return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer.id))
    
    # Reject the transfer
    success, error = reject_wire_transfer(wire_transfer_id, reason)
    if success:
        flash("Wire transfer rejected successfully", "success")
    else:
        flash(f"Error rejecting wire transfer: {error}", "danger")
    
    return redirect(url_for('wire_transfer.view_wire_transfer', wire_transfer_id=wire_transfer.id))


@wire_transfer_bp.route('/banks', methods=['GET'])
@login_required
def get_correspondent_banks():
    """Get the list of active correspondent banks that support wire transfers (for AJAX requests)"""
    banks = get_active_correspondent_banks()
    bank_list = [
        {
            'id': bank.id,
            'name': bank.name,
            'swift_code': bank.swift_code,
            'routing_number': bank.routing_number
        }
        for bank in banks
    ]
    return jsonify(bank_list)