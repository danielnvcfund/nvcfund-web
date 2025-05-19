"""
Routes for Loan Management System

This module provides routes for handling loans, including:
- Comprehensive loan application and creation
- Underwriting scoring and evaluation
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
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, session
from flask_login import login_required, current_user
from sqlalchemy import desc
from werkzeug.utils import secure_filename

from app import db
from self_liquidating_loan import (
    SelfLiquidatingLoan, LoanCollateral, LoanPayment, LoanRenewal,
    LoanCorrespondentAvailability, LoanStatus, CollateralType, 
    InterestPaymentFrequency, RenewalStatus
)
from forms_loan import (
    ComprehensiveLoanApplicationForm, LoanCollateralForm, LoanStatusUpdateForm,
    LoanPaymentForm, LoanRenewalForm, LoanCorrespondentAvailabilityForm
)
from loan_underwriting import (
    evaluate_loan_application, CreditRating, IndustryRiskCategory, 
    CollateralQuality, LoanGrade
)

from models import User, FinancialInstitution, CorrespondentBank

# Create Blueprint
loan_bp = Blueprint('loan', __name__, url_prefix='/loans')


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


@loan_bp.route('/')
@login_required
def index():
    """Display list of loans"""
    # Get all loans, or filter by user's role/permissions
    try:
        loans = SelfLiquidatingLoan.query.order_by(desc(SelfLiquidatingLoan.created_at)).all()
    except Exception as e:
        current_app.logger.error(f"Error retrieving loans: {str(e)}")
        flash(f"Could not retrieve loan data: {str(e)}", "error")
        loans = []
        
    return render_template(
        'loans/index.html',
        loans=loans,
        LoanStatus=LoanStatus
    )


@loan_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_loan():
    """Create a new basic loan application"""
    # Redirect to comprehensive application form
    return redirect(url_for('loan.comprehensive_application'))


@loan_bp.route('/comprehensive-application', methods=['GET', 'POST'])
@login_required
def comprehensive_application():
    """Create a new comprehensive loan application"""
    form = ComprehensiveLoanApplicationForm()
    
    # Get correspondent banks for the form if needed
    correspondent_banks = CorrespondentBank.query.filter_by(is_active=True).all()
    financial_institutions = FinancialInstitution.query.filter_by(is_active=True).all()
    
    if form.validate_on_submit():
        # Generate a unique loan number
        loan_number = generate_loan_number()
        
        # Process the application data for underwriting scoring
        application_data = {
            "application_id": loan_number,
            "borrower_name": form.borrower_name.data,
            "loan_amount": form.loan_amount.data,
            "industry": form.borrower_industry.data,
            "financial": {
                "annual_revenue": form.annual_revenue.data,
                "annual_net_income": form.annual_net_income.data,
                "years_profitable": form.years_profitable.data,
                # Extract financial data from financial history if provided
                "annual_debt": sum([f.annual_debt.data or 0 for f in form.financial_history]) / max(len(form.financial_history.data), 1) if form.financial_history.data else 0,
                "annual_debt_payments": sum([f.annual_debt_payments.data or 0 for f in form.financial_history]) / max(len(form.financial_history.data), 1) if form.financial_history.data else 0,
                # Calculate financial ratios if possible
                "debt_to_equity": calculate_debt_to_equity(form)
            },
            "credit": {
                "credit_rating": form.credit_rating.data,
                "years_of_credit_history": 5,  # Default value
                "delinquencies_last_3_years": 1 if form.has_previous_defaults.data else 0,
                "bankruptcies_last_10_years": 1 if form.has_previous_bankruptcy.data else 0
            },
            "collateral": {
                "quality": get_collateral_quality(form),
                "value": form.collateral_value.data or 0,
                "has_personal_guarantee": form.has_personal_guarantee.data,
                "diversity_count": 1  # Default to 1 type of collateral
            },
            "management": {
                "years_in_industry": form.management_experience_years.data or form.years_in_business.data,
                "previous_successful_ventures": count_successful_ventures(form),
                "team_size": len(form.management_team.data) if form.management_team.data else 1,
                "has_relevant_education": has_relevant_education(form)
            },
            "business_plan": {
                "has_clear_strategy": form.has_business_plan.data and bool(form.business_plan_summary.data),
                "has_market_analysis": form.has_business_plan.data and bool(form.market_analysis.data),
                "has_financial_projections": form.has_business_plan.data,
                "has_risk_assessment": form.has_business_plan.data,
                "has_competitive_analysis": form.has_business_plan.data and bool(form.market_analysis.data)
            },
            "market": {
                "industry_growth_rate": 0.03,  # Default value
                "market_volatility": "moderate",  # Default value
                "regulatory_environment": "neutral",  # Default value
                "technology_disruption_risk": "moderate"  # Default value
            },
            "relationship": {
                "years_as_customer": 0,  # Default for new customers
                "products_used": 0,  # Default for new customers
                "deposit_relationship": False,  # Default for new customers
                "previous_loans_repaid": 0  # Default for new customers
            }
        }
        
        # Evaluate the loan application
        evaluation_results = evaluate_loan_application(application_data)
        
        # Store evaluation results in session for access during status updates
        session['loan_evaluation_results'] = evaluation_results
        
        # Determine the interest rate if not specified by the applicant
        interest_rate = form.interest_rate.data
        if not interest_rate:
            interest_rate = evaluation_results['interest_rate']['recommended_rate']
        
        # Create a new loan record
        loan = SelfLiquidatingLoan(
            loan_number=loan_number,
            loan_amount=form.loan_amount.data,
            currency=form.currency.data,
            interest_rate=interest_rate,
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
        
        # Add additional custom fields from comprehensive form
        add_additional_loan_data(loan, form, evaluation_results)
        
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
        
        # Save additional documents
        save_additional_documents(loan, form, loan_number)
        
        # Save the loan to the database
        db.session.add(loan)
        db.session.commit()
        
        flash('Comprehensive loan application submitted successfully! The application will now go through our underwriting process.', 'success')
        return redirect(url_for('loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/comprehensive_application.html',
        form=form,
        correspondent_banks=correspondent_banks,
        financial_institutions=financial_institutions
    )


def calculate_debt_to_equity(form):
    """Calculate debt to equity ratio from financial data if available"""
    if not form.financial_history.data:
        return None
    
    # Calculate average debt and equity from financial history
    total_debt = 0
    total_equity = 0
    count = 0
    
    for f in form.financial_history:
        if f.total_liabilities.data and f.total_assets.data:
            total_debt += f.total_liabilities.data
            total_equity += (f.total_assets.data - f.total_liabilities.data)
            count += 1
    
    if count == 0 or total_equity == 0:
        return None
    
    return total_debt / total_equity


def get_collateral_quality(form):
    """Determine collateral quality based on form data"""
    if not form.collateral_available.data:
        return CollateralQuality.POOR.name
    
    # Simple heuristic for collateral quality
    loan_amount = form.loan_amount.data
    collateral_value = form.collateral_value.data or 0
    
    if collateral_value <= 0:
        return CollateralQuality.POOR.name
    
    # Calculate loan-to-value ratio
    ltv = loan_amount / collateral_value
    
    if ltv <= 0.5:
        return CollateralQuality.EXCELLENT.name
    elif ltv <= 0.65:
        return CollateralQuality.STRONG.name
    elif ltv <= 0.75:
        return CollateralQuality.GOOD.name
    elif ltv <= 0.8:
        return CollateralQuality.SATISFACTORY.name
    elif ltv <= 0.9:
        return CollateralQuality.FAIR.name
    elif ltv <= 1.0:
        return CollateralQuality.WEAK.name
    else:
        return CollateralQuality.POOR.name


def count_successful_ventures(form):
    """Count previous successful ventures from management team data"""
    count = 0
    if form.management_team.data:
        for member in form.management_team.data:
            if member.previous_companies.data and len(member.previous_companies.data.split(',')) > 1:
                count += 1
    return min(count, 3)  # Cap at 3 for scoring purposes


def has_relevant_education(form):
    """Check if any management team members have relevant education"""
    if form.management_team.data:
        for member in form.management_team.data:
            if member.education.data and any(term in member.education.data.lower() for term in ['mba', 'finance', 'business', 'economics', 'accounting']):
                return True
    return False


def add_additional_loan_data(loan, form, evaluation_results):
    """Add additional data from comprehensive form to loan object"""
    # Store evaluation results and score as JSON
    loan.underwriting_score = evaluation_results['scores']['final_score']
    loan.underwriting_grade = evaluation_results['grade']['name']
    loan.underwriting_data_json = json.dumps(evaluation_results)
    
    # Store customized terms preferences
    loan.requested_amount = form.customized_terms.requested_amount.data
    loan.preferred_term_years = form.customized_terms.preferred_term_years.data
    loan.preferred_interest_rate = form.customized_terms.preferred_interest_rate.data
    loan.preferred_payment_frequency = form.customized_terms.preferred_payment_frequency.data
    
    # Store business information
    loan.industry = form.borrower_industry.data
    loan.years_in_business = form.years_in_business.data
    loan.number_of_employees = form.number_of_employees.data
    loan.annual_revenue = form.annual_revenue.data
    loan.annual_net_income = form.annual_net_income.data
    loan.loan_purpose = form.loan_purpose.data
    
    # Store additional contacts as JSON
    if form.additional_contacts.data:
        contacts_data = []
        for contact in form.additional_contacts.data:
            contacts_data.append({
                'name': contact['name'],
                'title': contact['title'],
                'email': contact['email'],
                'phone': contact['phone'],
                'is_primary': contact['is_primary']
            })
        loan.additional_contacts_json = json.dumps(contacts_data)
    
    # Store management team data as JSON
    if form.management_team.data:
        team_data = []
        for member in form.management_team.data:
            team_data.append({
                'name': member['name'],
                'title': member['title'],
                'years_experience': member['years_experience'],
                'education': member['education'],
                'previous_companies': member['previous_companies']
            })
        loan.management_team_json = json.dumps(team_data)
    
    # Store financial history as JSON
    if form.financial_history.data:
        financial_data = []
        for year_data in form.financial_history.data:
            financial_data.append({
                'fiscal_year': year_data['fiscal_year'],
                'annual_revenue': year_data['annual_revenue'],
                'annual_net_income': year_data['annual_net_income'],
                'annual_debt': year_data['annual_debt'],
                'annual_debt_payments': year_data['annual_debt_payments'],
                'total_assets': year_data['total_assets'],
                'total_liabilities': year_data['total_liabilities'],
                'current_assets': year_data['current_assets'],
                'current_liabilities': year_data['current_liabilities'],
                'cash_and_equivalents': year_data['cash_and_equivalents']
            })
        loan.financial_history_json = json.dumps(financial_data)
    
    # Store collateral information
    loan.collateral_value = form.collateral_value.data
    loan.collateral_description = form.collateral_description.data
    loan.has_personal_guarantee = form.has_personal_guarantee.data
    
    # Store business plan information
    loan.has_business_plan = form.has_business_plan.data
    loan.business_plan_summary = form.business_plan_summary.data
    loan.market_analysis = form.market_analysis.data


def save_additional_documents(loan, form, loan_number):
    """Save additional documents from comprehensive form"""
    documents = {}
    
    if form.business_registration_document.data:
        path = save_uploaded_file(form.business_registration_document.data, loan_number, 'business_registration')
        if path:
            documents['business_registration'] = path
    
    if form.financial_statements_document.data:
        path = save_uploaded_file(form.financial_statements_document.data, loan_number, 'financial_statements')
        if path:
            documents['financial_statements'] = path
    
    if form.tax_returns_document.data:
        path = save_uploaded_file(form.tax_returns_document.data, loan_number, 'tax_returns')
        if path:
            documents['tax_returns'] = path
    
    if form.business_plan_document.data:
        path = save_uploaded_file(form.business_plan_document.data, loan_number, 'business_plan')
        if path:
            documents['business_plan'] = path
    
    if form.collateral_document.data:
        path = save_uploaded_file(form.collateral_document.data, loan_number, 'collateral')
        if path:
            documents['collateral'] = path
    
    # Store document paths in loan record
    if documents:
        loan.additional_documents_json = json.dumps(documents)


@loan_bp.route('/<int:loan_id>')
@login_required
def view_loan(loan_id):
    """View details of a specific loan"""
    loan = SelfLiquidatingLoan.query.get_or_404(loan_id)
    
    # Get related data
    collaterals = LoanCollateral.query.filter_by(loan_id=loan_id).all()
    payments = LoanPayment.query.filter_by(loan_id=loan_id).order_by(desc(LoanPayment.payment_date)).all()
    renewals = LoanRenewal.query.filter_by(loan_id=loan_id).order_by(desc(LoanRenewal.request_date)).all()
    correspondent_availabilities = LoanCorrespondentAvailability.query.filter_by(loan_id=loan_id).all()
    
    # Parse underwriting data if available
    underwriting_data = None
    if loan.underwriting_data_json:
        try:
            underwriting_data = json.loads(loan.underwriting_data_json)
        except:
            underwriting_data = None
    
    # Parse additional contacts if available
    additional_contacts = None
    if loan.additional_contacts_json:
        try:
            additional_contacts = json.loads(loan.additional_contacts_json)
        except:
            additional_contacts = None
    
    # Parse management team if available
    management_team = None
    if loan.management_team_json:
        try:
            management_team = json.loads(loan.management_team_json)
        except:
            management_team = None
    
    # Parse financial history if available
    financial_history = None
    if loan.financial_history_json:
        try:
            financial_history = json.loads(loan.financial_history_json)
        except:
            financial_history = None
    
    # Parse additional documents if available
    additional_documents = None
    if loan.additional_documents_json:
        try:
            additional_documents = json.loads(loan.additional_documents_json)
        except:
            additional_documents = None
    
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
        RenewalStatus=RenewalStatus,
        underwriting_data=underwriting_data,
        additional_contacts=additional_contacts,
        management_team=management_team,
        financial_history=financial_history,
        additional_documents=additional_documents
    )


@loan_bp.route('/<int:loan_id>/status', methods=['GET', 'POST'])
@login_required
def update_status(loan_id):
    """Update the status of a loan"""
    loan = SelfLiquidatingLoan.query.get_or_404(loan_id)
    form = LoanStatusUpdateForm(obj=loan)
    
    # Get evaluation results from session if available
    evaluation_results = session.get('loan_evaluation_results')
    
    # Or get from loan record if available
    if not evaluation_results and loan.underwriting_data_json:
        try:
            evaluation_results = json.loads(loan.underwriting_data_json)
        except:
            evaluation_results = None
    
    if form.validate_on_submit():
        # Store old status for comparison
        old_status = loan.status
        
        # Update loan status
        loan.status = form.status.data
        loan.updated_by = current_user.id
        
        # Update underwriting score and rate adjustment if provided
        if form.underwriting_score.data:
            loan.underwriting_score = form.underwriting_score.data
        
        if form.rate_adjustment.data:
            # Apply rate adjustment to standard rate (5.75%)
            base_rate = 5.75
            loan.interest_rate = base_rate + form.rate_adjustment.data
            
        if form.final_interest_rate.data:
            loan.interest_rate = form.final_interest_rate.data
        
        # Handle specific status changes
        if loan.status == LoanStatus.UNDERWRITING:
            # Start underwriting process
            if not loan.underwriting_start_date:
                loan.underwriting_start_date = datetime.utcnow()
        
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
                status_docs = json.loads(loan.collateral_documents_json or '{}')
                status_docs[f"status_{loan.status.name.lower()}"] = status_doc_path
                loan.collateral_documents_json = json.dumps(status_docs)
        
        db.session.commit()
        
        flash(f'Loan status updated from {old_status.name} to {loan.status.name}', 'success')
        return redirect(url_for('loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/update_status.html',
        form=form,
        loan=loan,
        LoanStatus=LoanStatus,
        evaluation_results=evaluation_results
    )


@loan_bp.route('/<int:loan_id>/collateral/add', methods=['GET', 'POST'])
@login_required
def add_collateral(loan_id):
    """Add collateral to a loan"""
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
        
        # Update total collateral value on the loan
        total_collateral = collateral.value
        existing_collaterals = LoanCollateral.query.filter_by(loan_id=loan_id).all()
        for existing in existing_collaterals:
            total_collateral += existing.value
        
        loan.collateral_value = total_collateral
        db.session.commit()
        
        flash('Collateral added successfully!', 'success')
        return redirect(url_for('loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/add_collateral.html',
        form=form,
        loan=loan,
        CollateralType=CollateralType
    )


@loan_bp.route('/<int:loan_id>/payment/add', methods=['GET', 'POST'])
@login_required
def add_payment(loan_id):
    """Record a payment for a loan"""
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
            if payment_doc_path:
                payment.payment_document_id = payment_doc_path
        
        db.session.add(payment)
        db.session.commit()
        
        flash('Payment recorded successfully!', 'success')
        return redirect(url_for('loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/add_payment.html',
        form=form,
        loan=loan
    )


@loan_bp.route('/<int:loan_id>/renewal/add', methods=['GET', 'POST'])
@login_required
def add_renewal(loan_id):
    """Request a renewal for a loan"""
    loan = SelfLiquidatingLoan.query.get_or_404(loan_id)
    
    # Check if loan is eligible for renewal
    if not loan.is_eligible_for_renewal():
        flash('This loan is not eligible for renewal at this time.', 'warning')
        return redirect(url_for('loan.view_loan', loan_id=loan.id))
    
    form = LoanRenewalForm()
    form.loan_id.data = loan_id
    
    # Count existing renewals to determine renewal number
    existing_renewals = LoanRenewal.query.filter_by(loan_id=loan_id).count()
    renewal_number = existing_renewals + 1
    
    if form.validate_on_submit():
        # Create new renewal record
        renewal = LoanRenewal(
            loan_id=loan_id,
            renewal_number=renewal_number,
            request_date=form.request_date.data,
            previous_interest_rate=loan.interest_rate,
            new_interest_rate=form.new_interest_rate.data if form.new_interest_rate.data else loan.interest_rate,
            additional_terms_json=json.dumps({'additional_terms': form.additional_terms.data}) if form.additional_terms.data else None,
            status=form.status.data,
            status_reason=form.status_reason.data,
            created_by=current_user.id
        )
        
        # Calculate new maturity date (add term years to current maturity date)
        if loan.maturity_date:
            renewal.new_maturity_date = loan.maturity_date + timedelta(days=loan.term_years * 365)
        
        # Save uploaded renewal agreement document
        if form.renewal_agreement_document.data:
            renewal_doc_path = save_uploaded_file(
                form.renewal_agreement_document.data,
                loan.loan_number,
                f"renewal_{renewal_number}"
            )
            if renewal_doc_path:
                renewal.renewal_agreement_document_id = renewal_doc_path
        
        # Update loan status
        loan.status = LoanStatus.RENEWAL_PENDING
        loan.renewal_status = RenewalStatus.REQUESTED
        
        db.session.add(renewal)
        db.session.commit()
        
        flash('Loan renewal request submitted successfully!', 'success')
        return redirect(url_for('loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/add_renewal.html',
        form=form,
        loan=loan,
        renewal_number=renewal_number,
        RenewalStatus=RenewalStatus
    )


@loan_bp.route('/<int:loan_id>/renewal/<int:renewal_id>/update', methods=['GET', 'POST'])
@login_required
def update_renewal(loan_id, renewal_id):
    """Update a loan renewal request"""
    loan = SelfLiquidatingLoan.query.get_or_404(loan_id)
    renewal = LoanRenewal.query.get_or_404(renewal_id)
    
    form = LoanRenewalForm(obj=renewal)
    form.loan_id.data = loan_id
    
    if form.validate_on_submit():
        # Update renewal status
        old_status = renewal.status
        renewal.status = form.status.data
        renewal.status_reason = form.status_reason.data
        
        # Handle approval
        if renewal.status == RenewalStatus.APPROVED and old_status != RenewalStatus.APPROVED:
            renewal.approval_date = datetime.utcnow()
            renewal.approved_by = current_user.id
        
        # Handle execution
        if renewal.status == RenewalStatus.EXECUTED and old_status != RenewalStatus.EXECUTED:
            renewal.effective_date = datetime.utcnow()
            
            # Update loan with new terms
            loan.interest_rate = renewal.new_interest_rate
            loan.maturity_date = renewal.new_maturity_date
            loan.renewals_used += 1
            loan.status = LoanStatus.RENEWED
            loan.renewal_status = RenewalStatus.ELIGIBLE if loan.renewals_used < loan.renewal_options else RenewalStatus.NOT_ELIGIBLE
        
        # Save new document if provided
        if form.renewal_agreement_document.data:
            renewal_doc_path = save_uploaded_file(
                form.renewal_agreement_document.data,
                loan.loan_number,
                f"renewal_{renewal.renewal_number}_update"
            )
            if renewal_doc_path:
                renewal.renewal_agreement_document_id = renewal_doc_path
        
        db.session.commit()
        
        flash(f'Loan renewal status updated to {renewal.status.name}!', 'success')
        return redirect(url_for('loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/update_renewal.html',
        form=form,
        loan=loan,
        renewal=renewal,
        RenewalStatus=RenewalStatus
    )


@loan_bp.route('/<int:loan_id>/correspondent-availability/add', methods=['GET', 'POST'])
@login_required
def add_correspondent_availability(loan_id):
    """Offer a loan to a correspondent bank"""
    loan = SelfLiquidatingLoan.query.get_or_404(loan_id)
    
    # Check if loan is available to correspondents
    if not loan.is_available_to_correspondents:
        flash('This loan is not available to correspondent banks.', 'warning')
        return redirect(url_for('loan.view_loan', loan_id=loan.id))
    
    form = LoanCorrespondentAvailabilityForm()
    form.loan_id.data = loan_id
    
    # Get correspondent banks for the form
    correspondent_banks = CorrespondentBank.query.filter_by(is_active=True).all()
    form.correspondent_bank_id.choices = [(bank.id, bank.name) for bank in correspondent_banks]
    
    if form.validate_on_submit():
        # Check if this correspondent already has an active offer for this loan
        existing = LoanCorrespondentAvailability.query.filter_by(
            loan_id=loan_id,
            correspondent_bank_id=form.correspondent_bank_id.data,
            is_active=True
        ).first()
        
        if existing:
            flash('This correspondent bank already has an active offer for this loan.', 'warning')
            return redirect(url_for('loan.view_loan', loan_id=loan.id))
        
        # Calculate participation amount based on percentage
        participation_amount = (form.participation_percentage.data / 100) * loan.loan_amount
        
        # Create new correspondent availability record
        availability = LoanCorrespondentAvailability(
            loan_id=loan_id,
            correspondent_bank_id=form.correspondent_bank_id.data,
            offered_date=form.offered_date.data,
            expiration_date=form.expiration_date.data,
            participation_percentage=form.participation_percentage.data,
            participation_amount=participation_amount,
            special_terms=form.special_terms.data,
            is_active=True
        )
        
        db.session.add(availability)
        db.session.commit()
        
        flash('Loan has been offered to the correspondent bank successfully!', 'success')
        return redirect(url_for('loan.view_loan', loan_id=loan.id))
    
    return render_template(
        'loans/add_correspondent_availability.html',
        form=form,
        loan=loan,
        correspondent_banks=correspondent_banks
    )


@loan_bp.route('/api/underwriting-score', methods=['POST'])
@login_required
def api_underwriting_score():
    """API endpoint to calculate underwriting score for a loan application"""
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.json
    
    # Basic validation
    required_fields = ['borrower_name', 'loan_amount', 'financial']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
    
    try:
        # Process the application data
        evaluation_results = evaluate_loan_application(data)
        return jsonify(evaluation_results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500