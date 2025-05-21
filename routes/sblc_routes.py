"""
Standby Letter of Credit (SBLC) Routes
This module handles all routes related to SBLC issuance and management.
"""
import logging
import json
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, redirect, request, url_for, flash, current_app, Response
from flask_login import login_required, current_user
from werkzeug.exceptions import NotFound, Forbidden, BadRequest
from weasyprint import HTML
from io import BytesIO

from app import db
from sblc_models import StandbyLetterOfCredit, SBLCAmendment, SBLCDraw, SBLCStatus, SBLCDrawStatus
from models import User, FinancialInstitution
from account_holder_models import AccountHolder
from swift_integration import SwiftService

logger = logging.getLogger(__name__)

# Create blueprint
sblc_bp = Blueprint('sblc', __name__, url_prefix='/sblc')

# Helper functions
def admin_or_bank_officer_required(f):
    """Decorator to ensure user is admin or bank officer"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated and has proper role
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('web.main.login'))
        
        # Check if user has admin or bank officer role
        # Adjust the role check based on your user model implementation
        if not hasattr(current_user, 'role') or current_user.role not in ['ADMIN', 'BANK_OFFICER']:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('web.main.dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

def get_sblc_stats():
    """Get statistics about SBLCs for dashboard"""
    try:
        total = StandbyLetterOfCredit.query.count()
        active = StandbyLetterOfCredit.query.filter_by(status=SBLCStatus.ISSUED).count()
        draft = StandbyLetterOfCredit.query.filter_by(status=SBLCStatus.DRAFT).count()
        
        # Calculate total value (converted to USD)
        # This is a simplified implementation - in production you might want to use 
        # actual conversion rates from your currency exchange service
        value_by_currency = {}
        total_value_usd = 0
        
        for sblc in StandbyLetterOfCredit.query.all():
            if sblc.currency not in value_by_currency:
                value_by_currency[sblc.currency] = 0
            
            value_by_currency[sblc.currency] += sblc.amount
            
            # Simple conversion to USD for total value calculation
            # In production, use your actual currency exchange rates
            if sblc.currency == 'USD':
                total_value_usd += sblc.amount
            elif sblc.currency == 'EUR':
                total_value_usd += sblc.amount * 1.1  # Approximate EUR to USD
            elif sblc.currency == 'GBP':
                total_value_usd += sblc.amount * 1.3  # Approximate GBP to USD
            else:
                total_value_usd += sblc.amount  # Default 1:1 for other currencies
        
        return {
            'total': total,
            'active': active,
            'draft': draft,
            'total_value': total_value_usd,
            'value_by_currency': value_by_currency
        }
    except Exception as e:
        logger.error(f"Error getting SBLC stats: {str(e)}")
        return {
            'total': 0,
            'active': 0,
            'draft': 0,
            'total_value': 0,
            'value_by_currency': {}
        }

# Routes
@sblc_bp.route('/')
@login_required
def index():
    """SBLC main index page"""
    return redirect(url_for('sblc.sblc_list'))

@sblc_bp.route('/list')
@login_required
def sblc_list():
    """List all SBLCs"""
    try:
        # Get filter status from query parameters
        status_filter = request.args.get('status', 'all')
        
        # Query SBLCs based on filter
        if status_filter == 'all':
            sblcs = StandbyLetterOfCredit.query.order_by(StandbyLetterOfCredit.created_at.desc()).all()
        else:
            try:
                status_enum = SBLCStatus(status_filter)
                sblcs = StandbyLetterOfCredit.query.filter_by(status=status_enum).order_by(StandbyLetterOfCredit.created_at.desc()).all()
            except ValueError:
                # Invalid status parameter
                sblcs = StandbyLetterOfCredit.query.order_by(StandbyLetterOfCredit.created_at.desc()).all()
                status_filter = 'all'
        
        # Get statistics
        stats = get_sblc_stats()
        
        # Create status option list for dropdown
        status_options = [(status.value, status.name.replace('_', ' ').title()) for status in SBLCStatus]
        
        return render_template(
            'swift/sblc_list.html',
            sblcs=sblcs,
            stats=stats,
            status_options=status_options,
            current_filter=status_filter
        )
    except Exception as e:
        logger.error(f"Error in SBLC list: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'danger')
        return redirect(url_for('web.main.dashboard'))

@sblc_bp.route('/new', methods=['GET', 'POST'])
@sblc_bp.route('/create', methods=['GET', 'POST'])  # Keep old route for backward compatibility
@login_required
@admin_or_bank_officer_required
def create_sblc():
    """Create a new SBLC"""
    if request.method == 'POST':
        try:
            # Get form data
            applicant_id = request.form.get('applicant_id')
            applicant_account = request.form.get('applicant_account')
            amount = float(request.form.get('amount'))
            currency = request.form.get('currency')
            
            # Validate required fields
            if not all([applicant_id, applicant_account, amount, currency]):
                flash("All required fields must be filled out.", 'danger')
                return redirect(url_for('sblc.create_sblc'))
            
            # Create expiry date (1 year from now by default)
            expiry_date_str = request.form.get('expiry_date')
            if expiry_date_str:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
            else:
                expiry_date = datetime.utcnow() + timedelta(days=365)
            
            # Get applicant
            applicant = AccountHolder.query.get(applicant_id)
            if not applicant:
                flash("Selected applicant not found.", 'danger')
                return redirect(url_for('sblc.create_sblc'))
            
            # Get contract date
            contract_date_str = request.form.get('contract_date')
            if contract_date_str:
                contract_date = datetime.strptime(contract_date_str, '%Y-%m-%d')
            else:
                contract_date = datetime.utcnow()
            
            # Create new SBLC
            sblc = StandbyLetterOfCredit(
                applicant_id=applicant_id,
                applicant_account_number=applicant_account,
                amount=amount,
                currency=currency,
                expiry_date=expiry_date,
                expiry_place=request.form.get('expiry_place', 'New York, NY, USA'),
                beneficiary_name=request.form.get('beneficiary_name'),
                beneficiary_address=request.form.get('beneficiary_address'),
                beneficiary_account_number=request.form.get('beneficiary_account'),
                beneficiary_bank_name=request.form.get('beneficiary_bank'),
                beneficiary_bank_swift=request.form.get('beneficiary_swift'),
                beneficiary_bank_address=request.form.get('beneficiary_bank_address'),
                contract_name=request.form.get('contract_name'),
                contract_date=contract_date,
                partial_drawings=request.form.get('partial_drawings') == 'on',
                multiple_drawings=request.form.get('multiple_drawings') == 'on',
                applicable_law=request.form.get('applicable_law', 'International Standby Practices ISP98'),
                special_conditions=request.form.get('special_conditions'),
                status=SBLCStatus.DRAFT,
                created_by_id=current_user.id,
                last_updated_by_id=current_user.id
            )
            
            # Check if issuing bank is specified (if not NVC Banking Platform)
            issuing_bank_id = request.form.get('issuing_bank_id')
            if issuing_bank_id:
                sblc.issuing_bank_id = issuing_bank_id
            
            # Save to database
            db.session.add(sblc)
            db.session.commit()
            
            flash(f"SBLC created with reference number {sblc.reference_number}", 'success')
            return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating SBLC: {str(e)}")
            flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(url_for('sblc.create_sblc'))
    
    # GET request - show form
    account_holders = AccountHolder.query.all()
    banks = FinancialInstitution.query.all()
    
    return render_template(
        'swift/sblc_form.html',
        account_holders=account_holders,
        banks=banks,
        sblc=None,
        is_new=True
    )

@sblc_bp.route('/<int:sblc_id>')
@login_required
def view_sblc(sblc_id):
    """View a specific SBLC"""
    sblc = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Generate MT760 message for reference
    swift_message = SwiftService.create_mt760_message(sblc)
    
    return render_template(
        'swift/sblc_template.html',
        sblc=sblc,
        swift_message=swift_message
    )

@sblc_bp.route('/<int:sblc_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_or_bank_officer_required
def edit_sblc(sblc_id):
    """Edit an existing SBLC"""
    sblc = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Only draft SBLCs can be edited
    if sblc.status != SBLCStatus.DRAFT:
        flash("Only draft SBLCs can be edited.", 'warning')
        return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))
    
    if request.method == 'POST':
        try:
            # Update SBLC fields
            sblc.amount = float(request.form.get('amount'))
            sblc.currency = request.form.get('currency')
            
            # Update expiry date if provided
            expiry_date_str = request.form.get('expiry_date')
            if expiry_date_str:
                sblc.expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
                
            # Update contract date if provided
            contract_date_str = request.form.get('contract_date')
            if contract_date_str:
                sblc.contract_date = datetime.strptime(contract_date_str, '%Y-%m-%d')
            
            # Update other fields
            sblc.expiry_place = request.form.get('expiry_place')
            sblc.beneficiary_name = request.form.get('beneficiary_name')
            sblc.beneficiary_address = request.form.get('beneficiary_address')
            sblc.beneficiary_account_number = request.form.get('beneficiary_account')
            sblc.beneficiary_bank_name = request.form.get('beneficiary_bank')
            sblc.beneficiary_bank_swift = request.form.get('beneficiary_swift')
            sblc.beneficiary_bank_address = request.form.get('beneficiary_bank_address')
            sblc.contract_name = request.form.get('contract_name')
            sblc.partial_drawings = request.form.get('partial_drawings') == 'on'
            sblc.multiple_drawings = request.form.get('multiple_drawings') == 'on'
            sblc.applicable_law = request.form.get('applicable_law')
            sblc.special_conditions = request.form.get('special_conditions')
            sblc.last_updated_by_id = current_user.id
            
            # Update issuing bank if specified
            issuing_bank_id = request.form.get('issuing_bank_id')
            if issuing_bank_id:
                sblc.issuing_bank_id = issuing_bank_id
            else:
                sblc.issuing_bank_id = None
            
            # Save changes
            db.session.commit()
            
            flash("SBLC updated successfully", 'success')
            return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating SBLC: {str(e)}")
            flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(url_for('sblc.edit_sblc', sblc_id=sblc.id))
    
    # GET request - show form
    account_holders = AccountHolder.query.all()
    banks = FinancialInstitution.query.all()
    
    return render_template(
        'swift/sblc_form.html',
        account_holders=account_holders,
        banks=banks,
        sblc=sblc,
        is_new=False
    )

@sblc_bp.route('/<int:sblc_id>/issue', methods=['POST'])
@login_required
@admin_or_bank_officer_required
def issue_sblc(sblc_id):
    """Issue an SBLC (change status from DRAFT to ISSUED)"""
    sblc = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Only draft SBLCs can be issued
    if sblc.status != SBLCStatus.DRAFT:
        flash("Only draft SBLCs can be issued.", 'warning')
        return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))
    
    try:
        # Update status
        sblc.status = SBLCStatus.ISSUED
        sblc.last_updated_by_id = current_user.id
        db.session.commit()
        
        flash(f"SBLC {sblc.reference_number} has been issued successfully", 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error issuing SBLC: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'danger')
    
    return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))

@sblc_bp.route('/<int:sblc_id>/cancel', methods=['POST'])
@login_required
@admin_or_bank_officer_required
def cancel_sblc(sblc_id):
    """Cancel an SBLC"""
    sblc = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Only draft or issued SBLCs can be cancelled
    if sblc.status not in [SBLCStatus.DRAFT, SBLCStatus.ISSUED]:
        flash("This SBLC cannot be cancelled in its current state.", 'warning')
        return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))
    
    try:
        # Update status
        sblc.status = SBLCStatus.CANCELLED
        sblc.last_updated_by_id = current_user.id
        db.session.commit()
        
        flash(f"SBLC {sblc.reference_number} has been cancelled", 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cancelling SBLC: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'danger')
    
    return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))

@sblc_bp.route('/<int:sblc_id>/pdf')
@login_required
def download_sblc_pdf(sblc_id):
    """Generate and download a PDF version of the SBLC"""
    sblc = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Create PDF using WeasyPrint
    try:
        # Render the template to HTML
        html_content = render_template('swift/sblc_pdf_template.html', sblc=sblc)
        
        # Convert HTML to PDF
        pdf_file = BytesIO()
        HTML(string=html_content, base_url=request.url_root).write_pdf(pdf_file)
        
        # Reset file pointer
        pdf_file.seek(0)
        
        # Create response
        response = Response(
            pdf_file,
            content_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=SBLC-{sblc.reference_number}.pdf'
            }
        )
        
        return response
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        flash(f"An error occurred generating the PDF: {str(e)}", 'danger')
        return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))

@sblc_bp.route('/<int:sblc_id>/swift')
@login_required
def download_swift(sblc_id):
    """Generate and download the SWIFT MT760 message for the SBLC"""
    sblc = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Generate MT760 message
    try:
        swift_message = SwiftService.create_mt760_message(sblc)
        
        # Create response
        response = Response(
            swift_message,
            content_type='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename=MT760-{sblc.reference_number}.txt'
            }
        )
        
        return response
    except Exception as e:
        logger.error(f"Error generating SWIFT message: {str(e)}")
        flash(f"An error occurred generating the SWIFT message: {str(e)}", 'danger')
        return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))

@sblc_bp.route('/<int:sblc_id>/amend', methods=['GET', 'POST'])
@login_required
@admin_or_bank_officer_required
def create_amendment(sblc_id):
    """Create an amendment for an SBLC"""
    sblc = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Only issued SBLCs can be amended
    if sblc.status != SBLCStatus.ISSUED:
        flash("Only issued SBLCs can be amended.", 'warning')
        return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))
    
    if request.method == 'POST':
        try:
            # Get amendment details
            changes_description = request.form.get('changes_description')
            effective_date_str = request.form.get('effective_date')
            
            if not changes_description or not effective_date_str:
                flash("Changes description and effective date are required.", 'danger')
                return redirect(url_for('sblc.create_amendment', sblc_id=sblc.id))
            
            effective_date = datetime.strptime(effective_date_str, '%Y-%m-%d')
            
            # Track changed fields
            changed_fields = {}
            beneficiary_changed = False
            terms_changed = False
            drawing_options_changed = False
            
            # Check for amount change
            new_amount = request.form.get('new_amount')
            if new_amount and float(new_amount) != sblc.amount:
                changed_fields['amount'] = {
                    'old': sblc.amount,
                    'new': float(new_amount)
                }
            
            # Check for expiry date change
            new_expiry_date_str = request.form.get('new_expiry_date')
            new_expiry_date = None
            if new_expiry_date_str:
                new_expiry_date = datetime.strptime(new_expiry_date_str, '%Y-%m-%d')
                if new_expiry_date != sblc.expiry_date:
                    changed_fields['expiry_date'] = {
                        'old': sblc.expiry_date.strftime('%Y-%m-%d'),
                        'new': new_expiry_date.strftime('%Y-%m-%d')
                    }
            
            # Create amendment record
            amendment = SBLCAmendment(
                sblc=sblc,
                changes_description=changes_description,
                effective_date=effective_date,
                new_amount=float(new_amount) if new_amount else None,
                new_expiry_date=new_expiry_date,
                beneficiary_changed=beneficiary_changed,
                terms_changed=terms_changed,
                drawing_options_changed=drawing_options_changed,
                changes_json=json.dumps(changed_fields),
                created_by_id=current_user.id
            )
            
            # Add amendment to database
            db.session.add(amendment)
            
            # Update SBLC fields based on amendment
            if new_amount:
                sblc.amount = float(new_amount)
            
            if new_expiry_date:
                sblc.expiry_date = new_expiry_date
            
            # Update SBLC status
            sblc.status = SBLCStatus.AMENDED
            sblc.last_updated_by_id = current_user.id
            
            # Save changes
            db.session.commit()
            
            flash("Amendment created successfully", 'success')
            return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating amendment: {str(e)}")
            flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(url_for('sblc.create_amendment', sblc_id=sblc.id))
    
    # GET request - show amendment form
    return render_template(
        'swift/sblc_amendment_form.html',
        sblc=sblc
    )

@sblc_bp.route('/<int:sblc_id>/draw', methods=['GET', 'POST'])
@login_required
@admin_or_bank_officer_required
def create_draw(sblc_id):
    """Create a draw request against an SBLC"""
    sblc = StandbyLetterOfCredit.query.get_or_404(sblc_id)
    
    # Check if SBLC can be drawn
    if not sblc.can_be_drawn():
        flash("This SBLC cannot be drawn at this time.", 'warning')
        return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))
    
    if request.method == 'POST':
        try:
            # Get draw details
            amount = float(request.form.get('amount'))
            beneficiary_account = request.form.get('beneficiary_account')
            beneficiary_bank = request.form.get('beneficiary_bank')
            beneficiary_swift = request.form.get('beneficiary_swift')
            reason = request.form.get('reason')
            
            # Validate fields
            if not all([amount, beneficiary_account, beneficiary_bank, beneficiary_swift, reason]):
                flash("All required fields must be filled out.", 'danger')
                return redirect(url_for('sblc.create_draw', sblc_id=sblc.id))
            
            # Check if amount is valid
            remaining_amount = sblc.remaining_amount()
            if amount > remaining_amount:
                flash(f"Draw amount exceeds available balance of {sblc.currency} {remaining_amount}.", 'danger')
                return redirect(url_for('sblc.create_draw', sblc_id=sblc.id))
            
            # Create draw record
            draw = SBLCDraw(
                sblc=sblc,
                amount=amount,
                beneficiary_account=beneficiary_account,
                beneficiary_bank=beneficiary_bank,
                beneficiary_swift=beneficiary_swift,
                reason=reason,
                status=SBLCDrawStatus.PENDING
            )
            
            # Add draw to database
            db.session.add(draw)
            db.session.commit()
            
            flash("Draw request created successfully and is pending approval", 'success')
            return redirect(url_for('sblc.view_sblc', sblc_id=sblc.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating draw: {str(e)}")
            flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(url_for('sblc.create_draw', sblc_id=sblc.id))
    
    # GET request - show draw form
    return render_template(
        'swift/sblc_draw_form.html',
        sblc=sblc,
        remaining_amount=sblc.remaining_amount()
    )

@sblc_bp.route('/draw/<int:draw_id>/approve', methods=['POST'])
@login_required
@admin_or_bank_officer_required
def approve_draw(draw_id):
    """Approve a pending draw request"""
    draw = SBLCDraw.query.get_or_404(draw_id)
    
    # Check if draw can be approved
    if draw.status != SBLCDrawStatus.PENDING:
        flash("This draw request cannot be approved in its current state.", 'warning')
        return redirect(url_for('sblc.view_sblc', sblc_id=draw.sblc_id))
    
    try:
        # Update draw status
        draw.status = SBLCDrawStatus.APPROVED
        draw.reviewer_id = current_user.id
        draw.review_date = datetime.utcnow()
        draw.review_notes = request.form.get('review_notes')
        
        # If this is a full draw, update SBLC status
        sblc = draw.sblc
        if draw.amount >= sblc.remaining_amount():
            sblc.status = SBLCStatus.DRAWN
        
        db.session.commit()
        
        flash("Draw request approved successfully", 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving draw: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'danger')
    
    return redirect(url_for('sblc.view_sblc', sblc_id=draw.sblc_id))

@sblc_bp.route('/draw/<int:draw_id>/reject', methods=['POST'])
@login_required
@admin_or_bank_officer_required
def reject_draw(draw_id):
    """Reject a pending draw request"""
    draw = SBLCDraw.query.get_or_404(draw_id)
    
    # Check if draw can be rejected
    if draw.status != SBLCDrawStatus.PENDING:
        flash("This draw request cannot be rejected in its current state.", 'warning')
        return redirect(url_for('sblc.view_sblc', sblc_id=draw.sblc_id))
    
    try:
        # Update draw status
        draw.status = SBLCDrawStatus.REJECTED
        draw.reviewer_id = current_user.id
        draw.review_date = datetime.utcnow()
        draw.review_notes = request.form.get('review_notes')
        
        db.session.commit()
        
        flash("Draw request rejected", 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error rejecting draw: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'danger')
    
    return redirect(url_for('sblc.view_sblc', sblc_id=draw.sblc_id))

@sblc_bp.route('/draw/<int:draw_id>/complete', methods=['POST'])
@login_required
@admin_or_bank_officer_required
def complete_draw(draw_id):
    """Mark a draw as complete after funds have been transferred"""
    draw = SBLCDraw.query.get_or_404(draw_id)
    
    # Check if draw can be completed
    if draw.status != SBLCDrawStatus.APPROVED:
        flash("This draw request cannot be completed in its current state.", 'warning')
        return redirect(url_for('sblc.view_sblc', sblc_id=draw.sblc_id))
    
    try:
        # Update draw status
        draw.status = SBLCDrawStatus.COMPLETED
        
        db.session.commit()
        
        flash("Draw marked as complete", 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error completing draw: {str(e)}")
        flash(f"An error occurred: {str(e)}", 'danger')
    
    return redirect(url_for('sblc.view_sblc', sblc_id=draw.sblc_id))