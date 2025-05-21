"""
Standby Letter of Credit (SBLC) Routes
Routes for handling all SBLC-related functionality including creation, issuance,
amendment, and verification processes.
"""
import os
import json
import uuid
import logging
from datetime import datetime, date
from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask import jsonify, session, send_file, make_response
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from app import db
from forms_sblc import StandbyLetterOfCreditForm
from sblc_models import StandbyLetterOfCredit, SBLCDrawing, SBLCAmendment, SBLCStatus, SBLCType
from swift_integration import SwiftService
from models import FinancialInstitution, AccountHolder

# Configure logger
logger = logging.getLogger(__name__)

sblc = Blueprint('sblc', __name__)

@sblc.route('/list')
@login_required
def sblc_list():
    """Display list of SBLCs with filtering options"""
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    
    # Base query
    query = StandbyLetterOfCredit.query
    
    # Apply filters
    if status_filter != 'all':
        try:
            status = SBLCStatus(status_filter)
            query = query.filter(StandbyLetterOfCredit.status == status)
        except ValueError:
            # Invalid status, ignore filter
            pass
    
    # Get SBLCs - show most recent first
    sblcs = query.order_by(StandbyLetterOfCredit.created_at.desc()).all()
    
    # Calculate statistics for dashboard
    stats = {
        'total': len(sblcs),
        'active': sum(1 for s in sblcs if s.is_active()),
        'draft': sum(1 for s in sblcs if s.status == SBLCStatus.DRAFT),
        'issued': sum(1 for s in sblcs if s.status == SBLCStatus.ISSUED),
        'expired': sum(1 for s in sblcs if s.status == SBLCStatus.EXPIRED),
        'drawn': sum(1 for s in sblcs if s.status == SBLCStatus.DRAWN),
        'total_value': sum(s.amount for s in sblcs if s.currency == 'USD'),
        'value_by_currency': {}
    }
    
    # Calculate value by currency
    for sblc_obj in sblcs:
        currency = sblc_obj.currency
        if currency not in stats['value_by_currency']:
            stats['value_by_currency'][currency] = 0
        stats['value_by_currency'][currency] += float(sblc_obj.amount)
    
    return render_template(
        'swift/sblc_list.html',
        sblcs=sblcs,
        stats=stats,
        status_options=[(s.value, s.name) for s in SBLCStatus],
        current_filter=status_filter
    )

@sblc.route('/create', methods=['GET', 'POST'])
@login_required
def create_sblc():
    """Create a new Standby Letter of Credit"""
    form = StandbyLetterOfCreditForm()
    
    if form.validate_on_submit():
        try:
            # Create a new SBLC
            new_sblc = StandbyLetterOfCredit()
            
            # Generate unique reference number
            new_sblc.reference_number = new_sblc.generate_reference_number()
            
            # Basic details
            new_sblc.amount = form.amount.data
            new_sblc.currency = form.currency.data
            new_sblc.issue_date = form.issue_date.data
            new_sblc.expiry_date = form.expiry_date.data
            new_sblc.expiry_place = form.expiry_place.data
            new_sblc.applicable_law = form.applicable_law.data
            new_sblc.partial_drawings = form.partial_drawings.data
            new_sblc.multiple_drawings = form.multiple_drawings.data
            
            # Applicant details
            new_sblc.applicant_id = form.applicant_id.data
            new_sblc.applicant_account_number = form.applicant_account_number.data
            new_sblc.applicant_contact_info = form.applicant_contact_info.data
            
            # Beneficiary details
            new_sblc.beneficiary_name = form.beneficiary_name.data
            new_sblc.beneficiary_address = form.beneficiary_address.data
            new_sblc.beneficiary_account_number = form.beneficiary_account_number.data
            new_sblc.beneficiary_bank_name = form.beneficiary_bank_name.data
            new_sblc.beneficiary_bank_swift = form.beneficiary_bank_swift.data
            new_sblc.beneficiary_bank_address = form.beneficiary_bank_address.data
            
            # Underlying transaction
            new_sblc.contract_name = form.contract_name.data
            new_sblc.contract_date = form.contract_date.data
            new_sblc.contract_details = form.contract_details.data
            
            # Terms and conditions
            new_sblc.special_conditions = form.special_conditions.data
            
            # Default to NVC as issuing bank
            try:
                nvc_bank = FinancialInstitution.query.filter_by(name='NVC Banking Platform').first()
                if nvc_bank:
                    new_sblc.issuing_bank_id = nvc_bank.id
            except Exception as e:
                logger.error(f"Error getting NVC bank: {str(e)}")
            
            # Tracking details
            new_sblc.created_by_id = current_user.id
            
            # Set status (draft or pending issuance)
            if 'save_draft' in request.form:
                new_sblc.status = SBLCStatus.DRAFT
                success_message = "SBLC saved as draft"
            else:
                new_sblc.status = SBLCStatus.ISSUED
                new_sblc.issued_at = datetime.utcnow()
                success_message = "SBLC created and issued successfully"
            
            # Save to database
            db.session.add(new_sblc)
            db.session.commit()
            
            # Generate verification code
            verification_code = str(uuid.uuid4())
            new_sblc.verification_code = verification_code
            db.session.commit()
            
            flash(success_message, 'success')
            return redirect(url_for('sblc.view_sblc', sblc_id=new_sblc.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating SBLC: {str(e)}")
            flash(f"Error creating SBLC: {str(e)}", 'danger')
    
    return render_template('swift/sblc_form.html', form=form, edit_mode=False)

@sblc.route('/<int:sblc_id>', methods=['GET'])
@login_required
def view_sblc(sblc_id):
    """View a single SBLC with all details"""
    sblc_obj = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Get amendment history
    amendments = SBLCAmendment.query.filter_by(sblc_id=sblc_id).order_by(SBLCAmendment.amendment_number).all()
    
    # Get drawing history
    drawings = SBLCDrawing.query.filter_by(sblc_id=sblc_id).order_by(SBLCDrawing.created_at.desc()).all()
    
    return render_template(
        'swift/sblc_template.html',
        sblc=sblc_obj,
        amendments=amendments,
        drawings=drawings
    )

@sblc.route('/<int:sblc_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_sblc(sblc_id):
    """Edit an existing SBLC (only if in DRAFT status)"""
    sblc_obj = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Only draft SBLCs can be edited
    if sblc_obj.status != SBLCStatus.DRAFT:
        flash("Only draft SBLCs can be edited", 'warning')
        return redirect(url_for('sblc.view_sblc', sblc_id=sblc_id))
    
    # Create form and populate with current values
    form = StandbyLetterOfCreditForm(obj=sblc_obj)
    
    if form.validate_on_submit():
        try:
            # Update SBLC with form data
            form.populate_obj(sblc_obj)
            
            # Set status (draft or pending issuance)
            if 'save_draft' in request.form:
                sblc_obj.status = SBLCStatus.DRAFT
                success_message = "SBLC draft updated successfully"
            else:
                sblc_obj.status = SBLCStatus.ISSUED
                sblc_obj.issued_at = datetime.utcnow()
                success_message = "SBLC updated and issued successfully"
            
            # Save to database
            db.session.commit()
            
            flash(success_message, 'success')
            return redirect(url_for('sblc.view_sblc', sblc_id=sblc_obj.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating SBLC: {str(e)}")
            flash(f"Error updating SBLC: {str(e)}", 'danger')
    
    return render_template('swift/sblc_form.html', form=form, edit_mode=True)

@sblc.route('/<int:sblc_id>/issue', methods=['POST'])
@login_required
def issue_sblc(sblc_id):
    """Issue a draft SBLC via SWIFT MT760"""
    sblc_obj = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Only draft SBLCs can be issued
    if sblc_obj.status != SBLCStatus.DRAFT:
        return jsonify({'success': False, 'message': 'Only draft SBLCs can be issued'})
    
    try:
        # Create MT760 message
        mt760_message = SwiftService.create_mt760_message(sblc_obj)
        
        # Record the message in the SBLC
        sblc_obj.mt760_message = mt760_message
        
        # Update status
        sblc_obj.status = SBLCStatus.ISSUED
        sblc_obj.issued_at = datetime.utcnow()
        
        # Generate random confirmation code for demo
        confirmation = f"SWIFTACK-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        sblc_obj.swift_confirmation = confirmation
        
        # Save changes
        db.session.commit()
        
        # Return success
        return jsonify({
            'success': True, 
            'message': 'SBLC successfully issued',
            'swift_confirmation': confirmation
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error issuing SBLC: {str(e)}")
        return jsonify({'success': False, 'message': f'Error issuing SBLC: {str(e)}'})

@sblc.route('/<int:sblc_id>/verify', methods=['GET'])
def verify_sblc(sblc_id):
    """Verify the authenticity of an SBLC"""
    sblc_obj = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Check if the SBLC is issued (only issued SBLCs can be verified)
    if sblc_obj.status not in [SBLCStatus.ISSUED, SBLCStatus.AMENDED]:
        return jsonify({'verified': False, 'message': 'SBLC is not in an active state'})
    
    # Check if verification code is present
    if not sblc_obj.verification_code:
        return jsonify({'verified': False, 'message': 'SBLC does not have a verification code'})
    
    # For a real implementation, we would check with the SWIFT network
    # For demo purposes, we'll just confirm it exists in our system
    return jsonify({
        'verified': True,
        'message': 'SBLC verification successful',
        'reference': sblc_obj.reference_number,
        'issuer': 'NVC Banking Platform',
        'issue_date': sblc_obj.issue_date.strftime('%Y-%m-%d'),
        'status': sblc_obj.status.value
    })

@sblc.route('/<int:sblc_id>/download-pdf')
@login_required
def download_sblc_pdf(sblc_id):
    """Generate and download a PDF version of the SBLC"""
    from weasyprint import HTML
    import tempfile
    
    sblc_obj = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    try:
        # Render the template to HTML
        html_content = render_template(
            'swift/sblc_pdf_template.html',
            sblc=sblc_obj,
            print_mode=True
        )
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Generate PDF
            HTML(string=html_content).write_pdf(temp_file.name)
            temp_filename = temp_file.name
        
        # Send the PDF
        response = send_file(
            temp_filename,
            as_attachment=True,
            download_name=f"SBLC-{sblc_obj.reference_number}.pdf",
            mimetype='application/pdf'
        )
        
        # Delete the temporary file after sending
        @response.call_on_close
        def cleanup():
            os.remove(temp_filename)
            
        return response
        
    except Exception as e:
        logger.error(f"Error generating SBLC PDF: {str(e)}")
        flash(f"Error generating PDF: {str(e)}", 'danger')
        return redirect(url_for('sblc.view_sblc', sblc_id=sblc_id))

@sblc.route('/get-applicant-details')
@login_required
def get_applicant_details():
    """API endpoint to get details for an applicant"""
    applicant_id = request.args.get('applicant_id', 0, type=int)
    
    if not applicant_id:
        return jsonify({'success': False, 'message': 'No applicant ID provided'})
    
    try:
        # Get the applicant
        applicant = AccountHolder.query.get(applicant_id)
        
        if not applicant:
            return jsonify({'success': False, 'message': 'Applicant not found'})
        
        # Get primary account number
        account_number = ''
        if applicant.accounts:
            # Try to find USD account first
            usd_accounts = [acc for acc in applicant.accounts if acc.currency == 'USD']
            if usd_accounts:
                account_number = usd_accounts[0].account_number
            else:
                # Otherwise use the first account
                account_number = applicant.accounts[0].account_number
        
        return jsonify({
            'success': True,
            'name': applicant.name,
            'account_number': account_number,
            'address': applicant.primary_address().formatted() if applicant.primary_address() else ''
        })
        
    except Exception as e:
        logger.error(f"Error getting applicant details: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@sblc.route('/<int:sblc_id>/amend', methods=['GET', 'POST'])
@login_required
def amend_sblc(sblc_id):
    """Create an amendment to an existing SBLC"""
    # Implementation for SBLC amendments will go here
    # This is a placeholder for future implementation
    flash("SBLC amendment functionality is coming soon", "info")
    return redirect(url_for('sblc.view_sblc', sblc_id=sblc_id))

@sblc.route('/<int:sblc_id>/record-drawing', methods=['GET', 'POST'])
@login_required
def record_drawing(sblc_id):
    """Record a drawing against an SBLC"""
    # Implementation for SBLC drawing will go here
    # This is a placeholder for future implementation
    flash("SBLC drawing functionality is coming soon", "info")
    return redirect(url_for('sblc.view_sblc', sblc_id=sblc_id))