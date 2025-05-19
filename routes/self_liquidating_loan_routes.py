"""
Routes for Loan Management System

This module provides routes for handling loans, including:
- Loan application and creation
- Loan status management
- Collateral management
- Payment processing
- Loan renewal
- Correspondent bank availability
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc
from werkzeug.utils import secure_filename

from app import db
from self_liquidating_loan import (
    SelfLiquidatingLoan, LoanCollateral, LoanPayment, LoanRenewal,
    LoanCorrespondentAvailability, LoanStatus, CollateralType, 
    InterestPaymentFrequency, RenewalStatus
)
from forms_self_liquidating_loan import (
    SelfLiquidatingLoanApplicationForm, LoanCollateralForm, LoanStatusUpdateForm,
    LoanPaymentForm, LoanRenewalForm, LoanCorrespondentAvailabilityForm
)

from models import User, FinancialInstitution, CorrespondentBank

# Create Blueprint
self_liquidating_loan_bp = Blueprint('self_liquidating_loan', __name__, url_prefix='/loans')


def generate_loan_number():
    """Generate a unique loan number with SLF prefix (Self-Liquidating Facility)"""
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M')
    random_suffix = str(uuid.uuid4())[:8]
    return f"SLF-{timestamp}-{random_suffix}"


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file, loan_id, document_type):
    """Save an uploaded file and return the file path"""
    if not file or file.filename == '':
        return None
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        base_filename, extension = os.path.splitext(filename)
        new_filename = f"{loan_id}_{document_type}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{extension}"
        
        upload_folder = os.path.join(current_app.static_folder, 'uploads', 'loan_documents')
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, new_filename)
        file.save(file_path)
        
        return os.path.join('uploads', 'loan_documents', new_filename)
        
    return None


@self_liquidating_loan_bp.route('/')
@login_required
def index():
    """Display list of loans"""
    # Get all loans, or filter by user's role/permissions
    loans = SelfLiquidatingLoan.query.order_by(desc(SelfLiquidatingLoan.created_at)).all()
    
    return render_template(
        'loans/index.html',
        loans=loans,
        LoanStatus=LoanStatus
    )


@self_liquidating_loan_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_loan():
    """Create a new loan application"""
    form = SelfLiquidatingLoanApplicationForm()
    
    # Get correspondent banks for the form if needed
    correspondent_banks = CorrespondentBank.query.filter_by(is_active=True).all()
    financial_institutions = FinancialInstitution.query.filter_by(is_active=True).all()
    
    if form.validate_on_submit():
        # Generate a unique loan number
        loan_number = generate_loan_number()
        
        # Create a new loan record
        loan = SelfLiquidatingLoan(
            loan_number=loan_number,
            loan_amount=form.loan_amount.data,
            currency=form.currency.data,
            interest_rate=form.interest_rate.data,
            term_years=form.term_years.data,
            renewal_options=2,  # Based on requirements (10 years with 2 renewal options)
            borrower_name=form.borrower_name.data,
            borrower_entity_type=form.borrower_entity_type.data,
            borrower_tax_id=form.borrower_tax_id.data,
            borrower_address=form.borrower_address.data,
            borrower_contact_name=form.borrower_contact_name.data,
            borrower_contact_email=form.borrower_contact_email.data,
            borrower_contact_phone=form.borrower_contact_phone.data,
            status=LoanStatus.APPLICATION,
            interest_payment_frequency=form.interest_payment_frequency.data,
            liquidation_mechanism_description=form.liquidation_mechanism_description.data,
            is_available_to_correspondents=form.is_available_to_correspondents.data,
            current_principal_balance=form.loan_amount.data,  # Initial principal equals loan amount
            created_by=current_user.id,
            updated_by=current_user.id,
            application_date=datetime.utcnow()
        )
        
        # Save uploaded documents if provided
        if form.loan_agreement_document.data:
            loan.loan_agreement_document_id = save_uploaded_file(
                form.loan_agreement_document.data, 
                loan_number, 
                'agreement'
            )
            
        if form.promissory_note_document.data:
            loan.promissory_note_document_id = save_uploaded_file(
                form.promissory_note_document.data, 
                loan_number, 
                'promissory_note'
            )
        
        # Save the loan to the database
        db.session.add(loan)
        db.session.commit()
        
        flash('Loan application created successfully!', 'success')
        return redirect(url_for('self_liquidating_loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/new.html',
        form=form,
        correspondent_banks=correspondent_banks,
        financial_institutions=financial_institutions
    )


@self_liquidating_loan_bp.route('/<int:loan_id>')
@login_required
def view_loan(loan_id):
    """View details of a specific self-liquidating loan"""
    loan = SelfLiquidatingLoan.query.get_or_404(loan_id)
    
    # Get related data
    collaterals = LoanCollateral.query.filter_by(loan_id=loan_id).all()
    payments = LoanPayment.query.filter_by(loan_id=loan_id).order_by(desc(LoanPayment.payment_date)).all()
    renewals = LoanRenewal.query.filter_by(loan_id=loan_id).order_by(desc(LoanRenewal.request_date)).all()
    correspondent_availabilities = LoanCorrespondentAvailability.query.filter_by(loan_id=loan_id).all()
    
    return render_template(
        'loans/view.html',
        loan=loan,
        collaterals=collaterals,
        payments=payments,
        renewals=renewals,
        correspondent_availabilities=correspondent_availabilities,
        LoanStatus=LoanStatus,
        CollateralType=CollateralType,
        InterestPaymentFrequency=InterestPaymentFrequency,
        RenewalStatus=RenewalStatus
    )


@self_liquidating_loan_bp.route('/<int:loan_id>/status', methods=['GET', 'POST'])
@login_required
def update_status(loan_id):
    """Update the status of a self-liquidating loan"""
    loan = SelfLiquidatingLoan.query.get_or_404(loan_id)
    form = LoanStatusUpdateForm(obj=loan)
    
    if form.validate_on_submit():
        # Store old status for comparison
        old_status = loan.status
        
        # Update loan status
        loan.status = form.status.data
        loan.updated_by = current_user.id
        
        # Handle specific status changes
        if loan.status == LoanStatus.APPROVED and form.approval_date.data:
            loan.approval_date = form.approval_date.data
            
        if loan.status == LoanStatus.FUNDED and form.funding_date.data:
            loan.funding_date = form.funding_date.data
            # Calculate maturity date based on funding date
            loan.maturity_date = loan.funding_date + timedelta(days=loan.term_years * 365)
            
            # Calculate first interest payment date
            if loan.interest_payment_frequency == InterestPaymentFrequency.MONTHLY:
                loan.next_interest_payment_date = loan.funding_date + timedelta(days=30)
            elif loan.interest_payment_frequency == InterestPaymentFrequency.QUARTERLY:
                loan.next_interest_payment_date = loan.funding_date + timedelta(days=90)
            elif loan.interest_payment_frequency == InterestPaymentFrequency.SEMI_ANNUALLY:
                loan.next_interest_payment_date = loan.funding_date + timedelta(days=182)
            elif loan.interest_payment_frequency == InterestPaymentFrequency.ANNUALLY:
                loan.next_interest_payment_date = loan.funding_date + timedelta(days=365)
            
            # If funding amount is provided and different from loan amount, update
            if form.funding_amount.data and form.funding_amount.data != loan.loan_amount:
                loan.loan_amount = form.funding_amount.data
                loan.current_principal_balance = form.funding_amount.data
        
        # Save status document if provided
        if form.status_document.data:
            status_doc_path = save_uploaded_file(
                form.status_document.data,
                loan.loan_number,
                f"status_{loan.status.name.lower()}"
            )
            # Update or create status change document record
            if status_doc_path:
                # Here you might want to save the document reference
                # This could be stored in a separate table or in JSON format
                status_docs = json.loads(loan.collateral_documents_json or '{}')
                status_docs[f"status_{loan.status.name.lower()}"] = status_doc_path
                loan.collateral_documents_json = json.dumps(status_docs)
        
        db.session.commit()
        
        flash(f'Loan status updated from {old_status.name} to {loan.status.name}', 'success')
        return redirect(url_for('self_liquidating_loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/update_status.html',
        form=form,
        loan=loan,
        LoanStatus=LoanStatus
    )


@self_liquidating_loan_bp.route('/<int:loan_id>/collateral/add', methods=['GET', 'POST'])
@login_required
def add_collateral(loan_id):
    """Add collateral to a self-liquidating loan"""
    loan = SelfLiquidatingLoan.query.get_or_404(loan_id)
    form = LoanCollateralForm()
    form.loan_id.data = loan_id
    
    if form.validate_on_submit():
        # Create new collateral record
        collateral = LoanCollateral(
            loan_id=loan_id,
            collateral_type=form.collateral_type.data,
            description=form.description.data,
            value=form.value.data,
            valuation_date=form.valuation_date.data,
            valuation_source=form.valuation_source.data,
            location=form.location.data
        )
        
        # Set type-specific fields
        if form.collateral_type.data == CollateralType.PROMISSORY_NOTE:
            collateral.note_issuer = form.note_issuer.data
            collateral.note_maturity_date = form.note_maturity_date.data
            collateral.note_interest_rate = form.note_interest_rate.data
        elif form.collateral_type.data in [CollateralType.BUSINESS_ASSETS, CollateralType.RECEIVABLES]:
            collateral.asset_type = form.asset_type.data
            collateral.receivables_aging = form.receivables_aging.data
        
        # Save uploaded documents
        if form.collateral_document.data:
            collateral.collateral_document_id = save_uploaded_file(
                form.collateral_document.data,
                loan.loan_number,
                f"collateral_{collateral.collateral_type.name.lower()}"
            )
            
        if form.appraisal_document.data:
            collateral.appraisal_document_id = save_uploaded_file(
                form.appraisal_document.data,
                loan.loan_number,
                f"appraisal_{collateral.collateral_type.name.lower()}"
            )
            
        if form.perfection_document.data:
            collateral.perfection_document_id = save_uploaded_file(
                form.perfection_document.data,
                loan.loan_number,
                f"perfection_{collateral.collateral_type.name.lower()}"
            )
        
        db.session.add(collateral)
        db.session.commit()
        
        flash('Collateral added successfully!', 'success')
        return redirect(url_for('self_liquidating_loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/add_collateral.html',
        form=form,
        loan=loan,
        CollateralType=CollateralType
    )


@self_liquidating_loan_bp.route('/<int:loan_id>/payment/add', methods=['GET', 'POST'])
@login_required
def add_payment(loan_id):
    """Record a payment for a self-liquidating loan"""
    loan = SelfLiquidatingLoan.query.get_or_404(loan_id)
    form = LoanPaymentForm()
    form.loan_id.data = loan_id
    
    if form.validate_on_submit():
        # Create new payment record
        payment = LoanPayment(
            loan_id=loan_id,
            payment_date=form.payment_date.data,
            payment_amount=form.payment_amount.data,
            payment_method=form.payment_method.data,
            payment_reference=form.payment_reference.data,
            is_self_liquidating_payment=form.is_self_liquidating_payment.data,
            liquidation_source=form.liquidation_source.data,
            created_by=current_user.id
        )
        
        # Calculate principal, interest, and fees amounts
        total_specified = 0
        if form.principal_amount.data is not None:
            payment.principal_amount = form.principal_amount.data
            total_specified += payment.principal_amount
            
        if form.interest_amount.data is not None:
            payment.interest_amount = form.interest_amount.data
            total_specified += payment.interest_amount
            
        if form.fees_amount.data is not None:
            payment.fees_amount = form.fees_amount.data
            total_specified += payment.fees_amount
        
        # Auto-allocate any remaining amount if total_specified doesn't match payment_amount
        if total_specified < payment.payment_amount:
            remaining = payment.payment_amount - total_specified
            
            # If no interest specified, allocate to interest first up to the current interest due
            if form.interest_amount.data is None:
                # Calculate current interest due
                interest_due = loan.calculate_interest_payment_amount()
                payment.interest_amount = min(remaining, interest_due)
                remaining -= payment.interest_amount
            
            # Allocate any remaining to principal
            if remaining > 0 and form.principal_amount.data is None:
                payment.principal_amount = remaining
                remaining = 0
            
            # If there's still remaining and no fees specified, allocate to fees
            if remaining > 0 and form.fees_amount.data is None:
                payment.fees_amount = remaining
        
        # Update loan balances
        loan.current_principal_balance -= payment.principal_amount
        loan.total_interest_paid += payment.interest_amount
        loan.total_principal_paid += payment.principal_amount
        loan.last_payment_date = payment.payment_date
        
        # Calculate next interest payment date
        if payment.interest_amount > 0:
            loan.next_interest_payment_date = loan.calculate_next_interest_payment()
        
        # Check if loan is paid off
        if loan.current_principal_balance <= 0:
            loan.status = LoanStatus.PAID
            loan.current_principal_balance = 0
        
        # Save uploaded payment document
        if form.payment_document.data:
            payment_doc_path = save_uploaded_file(
                form.payment_document.data,
                loan.loan_number,
                f"payment_{payment.payment_date.strftime('%Y%m%d')}"
            )
            # You might want to store this somewhere
        
        # Save to database
        db.session.add(payment)
        db.session.commit()
        
        flash('Payment recorded successfully!', 'success')
        return redirect(url_for('self_liquidating_loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/add_payment.html',
        form=form,
        loan=loan
    )


@self_liquidating_loan_bp.route('/<int:loan_id>/renewal', methods=['GET', 'POST'])
@login_required
def process_renewal(loan_id):
    """Process a renewal for a self-liquidating loan"""
    loan = SelfLiquidatingLoan.query.get_or_404(loan_id)
    form = LoanRenewalForm()
    form.loan_id.data = loan_id
    
    # Check if loan is eligible for renewal
    if not loan.is_eligible_for_renewal() and request.method == 'GET':
        flash('This loan is not currently eligible for renewal.', 'warning')
        return redirect(url_for('self_liquidating_loan.view_loan', loan_id=loan.id))
    
    if form.validate_on_submit():
        # Create new renewal record
        renewal = LoanRenewal(
            loan_id=loan_id,
            renewal_number=loan.renewals_used + 1,
            request_date=form.request_date.data,
            previous_interest_rate=loan.interest_rate,
            new_interest_rate=form.new_interest_rate.data if form.new_interest_rate.data else loan.interest_rate,
            status=form.status.data,
            status_reason=form.status_reason.data,
            additional_terms_json=json.dumps({'additional_terms': form.additional_terms.data}) if form.additional_terms.data else None,
            created_by=current_user.id
        )
        
        # If status is APPROVED or EXECUTED, set approval fields
        if form.status.data in [RenewalStatus.APPROVED, RenewalStatus.EXECUTED]:
            renewal.approval_date = datetime.utcnow()
            renewal.approved_by = current_user.id
            
            # If EXECUTED, update the loan with new terms
            if form.status.data == RenewalStatus.EXECUTED:
                renewal.effective_date = datetime.utcnow()
                
                # Calculate new maturity date (extend by term_years)
                current_maturity = loan.maturity_date
                renewal.new_maturity_date = current_maturity + timedelta(days=loan.term_years * 365)
                
                # Update loan
                loan.maturity_date = renewal.new_maturity_date
                if form.new_interest_rate.data:
                    loan.interest_rate = form.new_interest_rate.data
                loan.renewals_used += 1
                loan.status = LoanStatus.RENEWED
                loan.renewal_status = RenewalStatus.EXECUTED
        
        # Save renewal agreement document if provided
        if form.renewal_agreement_document.data:
            renewal.renewal_agreement_document_id = save_uploaded_file(
                form.renewal_agreement_document.data,
                loan.loan_number,
                f"renewal_{renewal.renewal_number}"
            )
        
        # Save to database
        db.session.add(renewal)
        db.session.commit()
        
        flash('Loan renewal processed successfully!', 'success')
        return redirect(url_for('self_liquidating_loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/process_renewal.html',
        form=form,
        loan=loan,
        RenewalStatus=RenewalStatus
    )


@self_liquidating_loan_bp.route('/<int:loan_id>/correspondent-availability', methods=['GET', 'POST'])
@login_required
def manage_correspondent_availability(loan_id):
    """Manage correspondent bank availability for a self-liquidating loan"""
    loan = SelfLiquidatingLoan.query.get_or_404(loan_id)
    form = LoanCorrespondentAvailabilityForm()
    form.loan_id.data = loan_id
    
    # Populate correspondent bank choices
    correspondent_banks = CorrespondentBank.query.filter_by(is_active=True).all()
    form.correspondent_bank_id.choices = [(bank.id, bank.name) for bank in correspondent_banks]
    
    if form.validate_on_submit():
        # Create new correspondent availability record
        availability = LoanCorrespondentAvailability(
            loan_id=loan_id,
            correspondent_bank_id=form.correspondent_bank_id.data,
            offered_date=form.offered_date.data,
            expiration_date=form.expiration_date.data,
            participation_percentage=form.participation_percentage.data,
            participation_amount=(loan.loan_amount * form.participation_percentage.data / 100),
            special_terms=form.special_terms.data,
            is_active=True
        )
        
        # Save to database
        db.session.add(availability)
        db.session.commit()
        
        # Update loan's off-taker availability
        if not loan.is_available_to_correspondents:
            loan.is_available_to_correspondents = True
            loan.off_taker_availability_date = form.offered_date.data
            db.session.commit()
        
        flash('Loan availability to correspondent bank added successfully!', 'success')
        return redirect(url_for('self_liquidating_loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/manage_correspondent_availability.html',
        form=form,
        loan=loan,
        correspondent_banks=correspondent_banks
    )


@self_liquidating_loan_bp.route('/api/loans', methods=['GET'])
@login_required
def api_get_loans():
    """API endpoint to get self-liquidating loans"""
    loans = SelfLiquidatingLoan.query.order_by(desc(SelfLiquidatingLoan.created_at)).all()
    
    loan_list = []
    for loan in loans:
        loan_data = {
            'id': loan.id,
            'loan_number': loan.loan_number,
            'borrower_name': loan.borrower_name,
            'loan_amount': loan.loan_amount,
            'currency': loan.currency.name,
            'interest_rate': loan.interest_rate,
            'term_years': loan.term_years,
            'status': loan.status.name,
            'application_date': loan.application_date.isoformat() if loan.application_date else None,
            'funding_date': loan.funding_date.isoformat() if loan.funding_date else None,
            'maturity_date': loan.maturity_date.isoformat() if loan.maturity_date else None,
            'is_available_to_correspondents': loan.is_available_to_correspondents
        }
        loan_list.append(loan_data)
    
    return jsonify(loan_list)


@self_liquidating_loan_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard for self-liquidating loans with statistics and charts"""
    # Get statistics
    total_loans = SelfLiquidatingLoan.query.count()
    active_loans = SelfLiquidatingLoan.query.filter_by(status=LoanStatus.ACTIVE).count()
    total_loan_value = db.session.query(db.func.sum(SelfLiquidatingLoan.loan_amount)).scalar() or 0
    total_principal_outstanding = db.session.query(db.func.sum(SelfLiquidatingLoan.current_principal_balance)).scalar() or 0
    total_interest_paid = db.session.query(db.func.sum(SelfLiquidatingLoan.total_interest_paid)).scalar() or 0
    
    # Get loans by status for chart
    loans_by_status = {}
    for status in LoanStatus:
        count = SelfLiquidatingLoan.query.filter_by(status=status).count()
        loans_by_status[status.name] = count
    
    # Recent loans
    recent_loans = SelfLiquidatingLoan.query.order_by(desc(SelfLiquidatingLoan.created_at)).limit(5).all()
    
    # Recent payments
    recent_payments = LoanPayment.query.order_by(desc(LoanPayment.payment_date)).limit(5).all()
    
    return render_template(
        'loans/dashboard.html',
        total_loans=total_loans,
        active_loans=active_loans,
        total_loan_value=total_loan_value,
        total_principal_outstanding=total_principal_outstanding,
        total_interest_paid=total_interest_paid,
        loans_by_status=loans_by_status,
        recent_loans=recent_loans,
        recent_payments=recent_payments,
        LoanStatus=LoanStatus
    )