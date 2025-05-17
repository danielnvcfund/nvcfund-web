"""
Capital Injection and Bank Recapitalization Routes
This module provides routes for financial institution recapitalization
and equity injection programs.
"""
import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from models.capital_injection import (
    FinancialInstitutionProfile, InstitutionDocument,
    CapitalInjectionApplication, ApplicationStatusUpdate,
    CapitalInjectionTerm, ApplicationStatus
)
from forms.capital_injection_forms import (
    FinancialInstitutionProfileForm, CapitalInjectionApplicationForm,
    ApplicationReviewForm, DocumentUploadForm, CapitalInjectionTermsForm
)
from decorators import admin_required, analyst_required


# Create blueprint
capital_injection = Blueprint('capital_injection', __name__, url_prefix='/capital-injection')

# Define allowed file extensions and upload folder
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads', 'capital_injection')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file, institution_id=None, application_id=None, document_type=None):
    """Save uploaded file and return the saved path"""
    if file and allowed_file(file.filename):
        # Generate unique filename
        unique_filename = str(uuid.uuid4())
        original_extension = file.filename.rsplit('.', 1)[1].lower()
        new_filename = f"{unique_filename}.{original_extension}"
        
        # Determine subfolder
        subfolder = "general"
        if institution_id:
            subfolder = f"institution_{institution_id}"
        elif application_id:
            subfolder = f"application_{application_id}"
        
        if document_type:
            subfolder = os.path.join(subfolder, document_type)
        
        save_path = os.path.join(UPLOAD_FOLDER, subfolder)
        os.makedirs(save_path, exist_ok=True)
        
        file_path = os.path.join(save_path, new_filename)
        file.save(file_path)
        
        # Return relative path from UPLOAD_FOLDER
        return os.path.join(subfolder, new_filename)
    
    return None


@capital_injection.route('/')
@login_required
def index():
    """Capital injection home page"""
    # Get financial institution profiles for the current user
    # Administrative users see all profiles
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    is_analyst = hasattr(current_user, 'is_analyst') and current_user.is_analyst
    
    if is_admin or is_analyst:
        profiles = FinancialInstitutionProfile.query.all()
        applications = CapitalInjectionApplication.query.all()
    else:
        # Regular user - get only their own profiles
        profiles = FinancialInstitutionProfile.query.filter_by(created_by=current_user.id).all()
        applications = CapitalInjectionApplication.query.filter(
            CapitalInjectionApplication.institution_id.in_([p.id for p in profiles])
        ).all()
    
    # Group applications by status
    pending_apps = [a for a in applications if a.status in 
                    [ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW, ApplicationStatus.ADDITIONAL_INFO_REQUIRED]]
    approved_apps = [a for a in applications if a.status == ApplicationStatus.APPROVED]
    funded_apps = [a for a in applications if a.status == ApplicationStatus.FUNDED]
    other_apps = [a for a in applications if a.status not in 
                  [ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW, 
                   ApplicationStatus.ADDITIONAL_INFO_REQUIRED, ApplicationStatus.APPROVED, ApplicationStatus.FUNDED]]
    
    return render_template('capital_injection/index.html',
                           profiles=profiles,
                           pending_apps=pending_apps,
                           approved_apps=approved_apps,
                           funded_apps=funded_apps,
                           other_apps=other_apps,
                           is_admin=is_admin,
                           is_analyst=is_analyst)


@capital_injection.route('/institution/new', methods=['GET', 'POST'])
@login_required
def new_institution():
    """Create new financial institution profile"""
    form = FinancialInstitutionProfileForm()
    
    if form.validate_on_submit():
        # Create new institution profile
        profile = FinancialInstitutionProfile(
            institution_name=form.institution_name.data,
            institution_type=form.institution_type.data,
            registration_number=form.registration_number.data,
            tax_id=form.tax_id.data,
            year_established=form.year_established.data,
            headquarters_country=form.headquarters_country.data,
            headquarters_city=form.headquarters_city.data,
            primary_contact_name=form.primary_contact_name.data,
            primary_contact_title=form.primary_contact_title.data,
            primary_contact_email=form.primary_contact_email.data,
            primary_contact_phone=form.primary_contact_phone.data,
            total_assets=form.total_assets.data,
            total_liabilities=form.total_liabilities.data,
            total_equity=form.total_equity.data,
            tier1_capital=form.tier1_capital.data,
            tier2_capital=form.tier2_capital.data,
            risk_weighted_assets=form.risk_weighted_assets.data,
            primary_regulator=form.primary_regulator.data,
            regulatory_framework=form.regulatory_framework.data,
            current_capital_ratio=form.current_capital_ratio.data,
            current_tier1_ratio=form.current_tier1_ratio.data,
            current_leverage_ratio=form.current_leverage_ratio.data,
            required_capital_ratio=form.required_capital_ratio.data,
            created_by=current_user.id
        )
        
        db.session.add(profile)
        db.session.commit()
        
        # Handle document uploads
        for field_name in ['financial_statements', 'regulatory_reports', 'organizational_chart', 'banking_license']:
            files = request.files.getlist(field_name)
            for file in files:
                if file and file.filename:
                    document_path = save_uploaded_file(file, institution_id=profile.id, document_type=field_name)
                    if document_path:
                        document = InstitutionDocument(
                            institution_id=profile.id,
                            document_type=field_name,
                            document_name=secure_filename(file.filename),
                            document_path=document_path
                        )
                        db.session.add(document)
        
        db.session.commit()
        flash('Financial institution profile created successfully', 'success')
        return redirect(url_for('capital_injection.view_institution', institution_id=profile.id))
    
    return render_template('capital_injection/new_institution.html', form=form)


@capital_injection.route('/institution/<int:institution_id>')
@login_required
def view_institution(institution_id):
    """View financial institution profile"""
    profile = FinancialInstitutionProfile.query.get_or_404(institution_id)
    documents = InstitutionDocument.query.filter_by(institution_id=institution_id).all()
    applications = CapitalInjectionApplication.query.filter_by(institution_id=institution_id).all()
    
    # Check permission
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    is_analyst = hasattr(current_user, 'is_analyst') and current_user.is_analyst
    is_owner = profile.created_by == current_user.id
    
    if not (is_admin or is_analyst or is_owner):
        flash('You do not have permission to view this profile', 'danger')
        return redirect(url_for('capital_injection.index'))
    
    return render_template('capital_injection/view_institution.html',
                           profile=profile,
                           documents=documents,
                           applications=applications,
                           is_admin=is_admin,
                           is_analyst=is_analyst,
                           is_owner=is_owner)


@capital_injection.route('/institution/<int:institution_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_institution(institution_id):
    """Edit financial institution profile"""
    profile = FinancialInstitutionProfile.query.get_or_404(institution_id)
    
    # Check permission
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    is_owner = profile.created_by == current_user.id
    
    if not (is_admin or is_owner):
        flash('You do not have permission to edit this profile', 'danger')
        return redirect(url_for('capital_injection.view_institution', institution_id=institution_id))
    
    form = FinancialInstitutionProfileForm(obj=profile)
    
    if form.validate_on_submit():
        # Update profile
        form.populate_obj(profile)
        profile.updated_at = datetime.utcnow()
        
        # Handle document uploads
        for field_name in ['financial_statements', 'regulatory_reports', 'organizational_chart', 'banking_license']:
            files = request.files.getlist(field_name)
            for file in files:
                if file and file.filename:
                    document_path = save_uploaded_file(file, institution_id=profile.id, document_type=field_name)
                    if document_path:
                        document = InstitutionDocument(
                            institution_id=profile.id,
                            document_type=field_name,
                            document_name=secure_filename(file.filename),
                            document_path=document_path
                        )
                        db.session.add(document)
        
        db.session.commit()
        flash('Financial institution profile updated successfully', 'success')
        return redirect(url_for('capital_injection.view_institution', institution_id=profile.id))
    
    return render_template('capital_injection/edit_institution.html', form=form, profile=profile)


@capital_injection.route('/application/new/<int:institution_id>', methods=['GET', 'POST'])
@login_required
def new_application(institution_id):
    """Create new capital injection application"""
    profile = FinancialInstitutionProfile.query.get_or_404(institution_id)
    
    # Check permission
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    is_owner = profile.created_by == current_user.id
    
    if not (is_admin or is_owner):
        flash('You do not have permission to create an application for this institution', 'danger')
        return redirect(url_for('capital_injection.view_institution', institution_id=institution_id))
    
    form = CapitalInjectionApplicationForm()
    
    if form.validate_on_submit():
        # Create new application
        application = CapitalInjectionApplication(
            institution_id=institution_id,
            capital_type=form.capital_type.data,
            investment_structure=form.investment_structure.data,
            requested_amount=float(form.requested_amount.data),
            minimum_acceptable_amount=float(form.minimum_acceptable_amount.data) if form.minimum_acceptable_amount.data else None,
            term_years=form.term_years.data,
            proposed_interest_rate=form.proposed_interest_rate.data,
            proposed_dividend_rate=form.proposed_dividend_rate.data,
            regulatory_concern=form.regulatory_concern.data if form.regulatory_concern.data else None,
            target_capital_ratio=form.target_capital_ratio.data,
            regulator_approval_required=form.regulator_approval_required.data,
            regulator_approval_received=form.regulator_approval_received.data,
            regulator_approval_date=form.regulator_approval_date.data,
            use_of_funds=form.use_of_funds.data,
            business_plan_summary=form.business_plan_summary.data,
            expected_impact=form.expected_impact.data,
            risk_assessment=form.risk_assessment.data,
            mitigating_factors=form.mitigating_factors.data,
            status=ApplicationStatus.DRAFT
        )
        
        db.session.add(application)
        db.session.flush()  # Get ID without committing
        
        # Handle document uploads
        for field_name in ['capital_plan', 'business_plan', 'financial_projections', 'regulator_correspondence']:
            files = request.files.getlist(field_name)
            for file in files:
                if file and file.filename:
                    document_path = save_uploaded_file(file, application_id=application.id, document_type=field_name)
                    if document_path:
                        document = InstitutionDocument(
                            institution_id=institution_id,
                            document_type=field_name,
                            document_name=secure_filename(file.filename),
                            document_path=document_path
                        )
                        db.session.add(document)
        
        # Submit or save as draft
        if 'submit_application' in request.form:
            application.status = ApplicationStatus.SUBMITTED
            status_update = ApplicationStatusUpdate(
                application_id=application.id,
                previous_status=ApplicationStatus.DRAFT,
                new_status=ApplicationStatus.SUBMITTED,
                updated_by=current_user.username,
                notes="Application submitted"
            )
            db.session.add(status_update)
            flash('Application submitted successfully', 'success')
        else:
            flash('Application saved as draft', 'success')
        
        db.session.commit()
        return redirect(url_for('capital_injection.view_application', application_id=application.id))
    
    return render_template('capital_injection/new_application.html', 
                          form=form, 
                          profile=profile,
                          institution_id=institution_id)


@capital_injection.route('/application/<int:application_id>')
@login_required
def view_application(application_id):
    """View capital injection application"""
    application = CapitalInjectionApplication.query.get_or_404(application_id)
    profile = FinancialInstitutionProfile.query.get_or_404(application.institution_id)
    documents = InstitutionDocument.query.filter_by(institution_id=profile.id).all()
    status_updates = ApplicationStatusUpdate.query.filter_by(application_id=application_id).order_by(ApplicationStatusUpdate.update_date.desc()).all()
    
    # Check permission
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    is_analyst = hasattr(current_user, 'is_analyst') and current_user.is_analyst
    is_owner = profile.created_by == current_user.id
    
    if not (is_admin or is_analyst or is_owner):
        flash('You do not have permission to view this application', 'danger')
        return redirect(url_for('capital_injection.index'))
    
    return render_template('capital_injection/view_application.html',
                           application=application,
                           profile=profile,
                           documents=documents,
                           status_updates=status_updates,
                           is_admin=is_admin,
                           is_analyst=is_analyst,
                           is_owner=is_owner)


@capital_injection.route('/application/<int:application_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_application(application_id):
    """Edit capital injection application"""
    application = CapitalInjectionApplication.query.get_or_404(application_id)
    profile = FinancialInstitutionProfile.query.get_or_404(application.institution_id)
    
    # Check permission
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    is_owner = profile.created_by == current_user.id
    
    if not (is_admin or is_owner):
        flash('You do not have permission to edit this application', 'danger')
        return redirect(url_for('capital_injection.view_application', application_id=application_id))
    
    # Can only edit draft applications
    if application.status != ApplicationStatus.DRAFT:
        flash('You can only edit applications in draft status', 'warning')
        return redirect(url_for('capital_injection.view_application', application_id=application_id))
    
    form = CapitalInjectionApplicationForm(obj=application)
    
    if form.validate_on_submit():
        # Update application
        previous_status = application.status
        
        form.populate_obj(application)
        application.updated_at = datetime.utcnow()
        
        # Handle document uploads
        for field_name in ['capital_plan', 'business_plan', 'financial_projections', 'regulator_correspondence']:
            files = request.files.getlist(field_name)
            for file in files:
                if file and file.filename:
                    document_path = save_uploaded_file(file, application_id=application.id, document_type=field_name)
                    if document_path:
                        document = InstitutionDocument(
                            institution_id=profile.id,
                            document_type=field_name,
                            document_name=secure_filename(file.filename),
                            document_path=document_path
                        )
                        db.session.add(document)
        
        # Submit or save as draft
        if 'submit_application' in request.form:
            application.status = ApplicationStatus.SUBMITTED
            status_update = ApplicationStatusUpdate(
                application_id=application.id,
                previous_status=previous_status,
                new_status=ApplicationStatus.SUBMITTED,
                updated_by=current_user.username,
                notes="Application submitted"
            )
            db.session.add(status_update)
            flash('Application submitted successfully', 'success')
        else:
            flash('Application updated', 'success')
        
        db.session.commit()
        return redirect(url_for('capital_injection.view_application', application_id=application.id))
    
    return render_template('capital_injection/edit_application.html', 
                          form=form, 
                          application=application,
                          profile=profile)


@capital_injection.route('/application/<int:application_id>/review', methods=['GET', 'POST'])
@login_required
@analyst_required
def review_application(application_id):
    """Review capital injection application"""
    application = CapitalInjectionApplication.query.get_or_404(application_id)
    profile = FinancialInstitutionProfile.query.get_or_404(application.institution_id)
    
    form = ApplicationReviewForm()
    # Set up status choices dynamically based on current status
    status_choices = []
    if application.status == ApplicationStatus.SUBMITTED:
        status_choices = [
            (ApplicationStatus.UNDER_REVIEW.value, 'Under Review'),
            (ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value, 'Request More Information')
        ]
    elif application.status == ApplicationStatus.UNDER_REVIEW:
        status_choices = [
            (ApplicationStatus.APPROVED.value, 'Approve'),
            (ApplicationStatus.CONDITIONALLY_APPROVED.value, 'Conditionally Approve'),
            (ApplicationStatus.REJECTED.value, 'Reject'),
            (ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value, 'Request More Information')
        ]
    elif application.status == ApplicationStatus.ADDITIONAL_INFO_REQUIRED:
        status_choices = [
            (ApplicationStatus.UNDER_REVIEW.value, 'Under Review'),
            (ApplicationStatus.APPROVED.value, 'Approve'),
            (ApplicationStatus.CONDITIONALLY_APPROVED.value, 'Conditionally Approve'),
            (ApplicationStatus.REJECTED.value, 'Reject')
        ]
    elif application.status == ApplicationStatus.APPROVED:
        status_choices = [
            (ApplicationStatus.FUNDING_IN_PROGRESS.value, 'Funding In Progress'),
            (ApplicationStatus.REJECTED.value, 'Reject (Reverse Approval)')
        ]
    elif application.status == ApplicationStatus.FUNDING_IN_PROGRESS:
        status_choices = [
            (ApplicationStatus.FUNDED.value, 'Funded (Complete)'),
            (ApplicationStatus.APPROVED.value, 'Return to Approved')
        ]
    
    form.status.choices = status_choices
    
    if form.validate_on_submit():
        previous_status = application.status
        new_status = form.status.data
        
        # Update application
        application.status = new_status
        application.analyst_notes = form.analyst_notes.data
        application.committee_notes = form.committee_notes.data
        
        if form.approved_amount.data:
            application.approved_amount = form.approved_amount.data
        
        # Update approval terms if provided
        terms_dict = {}
        if form.interest_rate.data is not None:
            terms_dict['interest_rate'] = form.interest_rate.data
        if form.dividend_rate.data is not None:
            terms_dict['dividend_rate'] = form.dividend_rate.data
        if form.approved_term_years.data is not None:
            terms_dict['term_years'] = form.approved_term_years.data
        if form.special_conditions.data:
            terms_dict['special_conditions'] = form.special_conditions.data
        
        if terms_dict:
            application.approved_terms_dict = terms_dict
        
        # If approved, set approval date
        if new_status == ApplicationStatus.APPROVED.value and previous_status != ApplicationStatus.APPROVED:
            application.approval_date = datetime.utcnow()
        
        # If funded, set funding date
        if new_status == ApplicationStatus.FUNDED.value:
            application.funding_date = datetime.utcnow()
            # Generate a funding transaction ID
            application.funding_transaction_id = f"FUND-{uuid.uuid4().hex[:12].upper()}"
            application.funding_amount = application.approved_amount
        
        # Create status update record
        status_update = ApplicationStatusUpdate(
            application_id=application.id,
            previous_status=previous_status,
            new_status=new_status,
            updated_by=current_user.username,
            notes=f"Status updated to {new_status} by {current_user.username}"
        )
        db.session.add(status_update)
        
        db.session.commit()
        flash(f'Application status updated to {new_status.replace("_", " ").title()}', 'success')
        return redirect(url_for('capital_injection.view_application', application_id=application.id))
    
    # Pre-populate form if viewing
    if request.method == 'GET':
        form.analyst_notes.data = application.analyst_notes
        form.committee_notes.data = application.committee_notes
        form.approved_amount.data = application.approved_amount
        
        # Extract terms from JSON
        if application.approved_terms:
            terms = application.approved_terms_dict
            if 'interest_rate' in terms:
                form.interest_rate.data = terms['interest_rate']
            if 'dividend_rate' in terms:
                form.dividend_rate.data = terms['dividend_rate']
            if 'term_years' in terms:
                form.approved_term_years.data = terms['term_years']
            if 'special_conditions' in terms:
                form.special_conditions.data = terms['special_conditions']
    
    return render_template('capital_injection/review_application.html',
                          form=form,
                          application=application,
                          profile=profile)


@capital_injection.route('/document/upload/<int:institution_id>', methods=['GET', 'POST'])
@login_required
def upload_document(institution_id):
    """Upload document for an institution"""
    profile = FinancialInstitutionProfile.query.get_or_404(institution_id)
    
    # Check permission
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    is_analyst = hasattr(current_user, 'is_analyst') and current_user.is_analyst
    is_owner = profile.created_by == current_user.id
    
    if not (is_admin or is_analyst or is_owner):
        flash('You do not have permission to upload documents for this institution', 'danger')
        return redirect(url_for('capital_injection.view_institution', institution_id=institution_id))
    
    form = DocumentUploadForm()
    
    if form.validate_on_submit():
        files = request.files.getlist('document_file')
        for file in files:
            if file and file.filename:
                document_path = save_uploaded_file(file, institution_id=institution_id, document_type=form.document_type.data)
                if document_path:
                    document = InstitutionDocument(
                        institution_id=institution_id,
                        document_type=form.document_type.data,
                        document_name=form.document_name.data,
                        document_path=document_path
                    )
                    db.session.add(document)
        
        db.session.commit()
        flash('Document uploaded successfully', 'success')
        return redirect(url_for('capital_injection.view_institution', institution_id=institution_id))
    
    return render_template('capital_injection/upload_document.html',
                          form=form,
                          profile=profile)


@capital_injection.route('/document/<int:document_id>')
@login_required
def get_document(document_id):
    """Retrieve a document"""
    document = InstitutionDocument.query.get_or_404(document_id)
    profile = FinancialInstitutionProfile.query.get_or_404(document.institution_id)
    
    # Check permission
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    is_analyst = hasattr(current_user, 'is_analyst') and current_user.is_analyst
    is_owner = profile.created_by == current_user.id
    
    if not (is_admin or is_analyst or is_owner):
        flash('You do not have permission to view this document', 'danger')
        return redirect(url_for('capital_injection.index'))
    
    # Extract filename and directory
    document_dir = os.path.dirname(document.document_path)
    document_filename = os.path.basename(document.document_path)
    
    return send_from_directory(os.path.join(UPLOAD_FOLDER, document_dir), document_filename, as_attachment=True)


@capital_injection.route('/term/manage', methods=['GET'])
@login_required
@admin_required
def manage_terms():
    """Manage capital injection terms"""
    terms = CapitalInjectionTerm.query.all()
    return render_template('capital_injection/manage_terms.html', terms=terms)


@capital_injection.route('/term/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_term():
    """Create new capital injection terms"""
    form = CapitalInjectionTermsForm()
    
    if form.validate_on_submit():
        # Create new term
        term = CapitalInjectionTerm(
            capital_type=form.capital_type.data,
            investment_structure=form.investment_structure.data,
            min_amount=form.min_amount.data,
            max_amount=form.max_amount.data,
            min_term_years=form.min_term_years.data,
            max_term_years=form.max_term_years.data,
            interest_rate_range_min=form.interest_rate_range_min.data,
            interest_rate_range_max=form.interest_rate_range_max.data,
            dividend_rate_range_min=form.dividend_rate_range_min.data,
            dividend_rate_range_max=form.dividend_rate_range_max.data,
            is_active=form.is_active.data,
            details=form.details.data
        )
        
        db.session.add(term)
        db.session.flush()  # Get ID without committing
        
        # Handle document upload
        files = request.files.getlist('terms_document')
        for file in files:
            if file and file.filename:
                document_path = save_uploaded_file(file, document_type='terms_document')
                if document_path:
                    term.terms_document = document_path
        
        db.session.commit()
        flash('Capital injection terms created successfully', 'success')
        return redirect(url_for('capital_injection.manage_terms'))
    
    return render_template('capital_injection/new_term.html', form=form)


@capital_injection.route('/term/<int:term_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_term(term_id):
    """Edit capital injection terms"""
    term = CapitalInjectionTerm.query.get_or_404(term_id)
    form = CapitalInjectionTermsForm(obj=term)
    
    if form.validate_on_submit():
        # Update term
        form.populate_obj(term)
        term.updated_at = datetime.utcnow()
        
        # Handle document upload
        files = request.files.getlist('terms_document')
        for file in files:
            if file and file.filename:
                document_path = save_uploaded_file(file, document_type='terms_document')
                if document_path:
                    term.terms_document = document_path
        
        db.session.commit()
        flash('Capital injection terms updated successfully', 'success')
        return redirect(url_for('capital_injection.manage_terms'))
    
    return render_template('capital_injection/edit_term.html', form=form, term=term)


@capital_injection.route('/term/<int:term_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_term(term_id):
    """Toggle active status of a term"""
    term = CapitalInjectionTerm.query.get_or_404(term_id)
    term.is_active = not term.is_active
    db.session.commit()
    
    status = "activated" if term.is_active else "deactivated"
    flash(f'Term {status} successfully', 'success')
    return redirect(url_for('capital_injection.manage_terms'))


@capital_injection.route('/dashboard')
@login_required
@analyst_required
def dashboard():
    """Dashboard for capital injection program"""
    # Get summary statistics
    total_applications = CapitalInjectionApplication.query.count()
    pending_applications = CapitalInjectionApplication.query.filter(
        CapitalInjectionApplication.status.in_([
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.UNDER_REVIEW,
            ApplicationStatus.ADDITIONAL_INFO_REQUIRED
        ])
    ).count()
    approved_applications = CapitalInjectionApplication.query.filter_by(
        status=ApplicationStatus.APPROVED
    ).count()
    funded_applications = CapitalInjectionApplication.query.filter_by(
        status=ApplicationStatus.FUNDED
    ).count()
    
    # Get total amounts
    total_requested = db.session.query(db.func.sum(CapitalInjectionApplication.requested_amount)).scalar() or 0
    total_approved = db.session.query(db.func.sum(CapitalInjectionApplication.approved_amount)).filter(
        CapitalInjectionApplication.status.in_([
            ApplicationStatus.APPROVED,
            ApplicationStatus.FUNDING_IN_PROGRESS,
            ApplicationStatus.FUNDED
        ])
    ).scalar() or 0
    total_funded = db.session.query(db.func.sum(CapitalInjectionApplication.funding_amount)).filter_by(
        status=ApplicationStatus.FUNDED
    ).scalar() or 0
    
    # Get recent applications
    recent_applications = CapitalInjectionApplication.query.order_by(
        CapitalInjectionApplication.application_date.desc()
    ).limit(10).all()
    
    # Get applications by status
    applications_by_status = {}
    for status in ApplicationStatus:
        count = CapitalInjectionApplication.query.filter_by(status=status).count()
        applications_by_status[status.value] = count
    
    return render_template('capital_injection/dashboard.html',
                          total_applications=total_applications,
                          pending_applications=pending_applications,
                          approved_applications=approved_applications,
                          funded_applications=funded_applications,
                          total_requested=total_requested,
                          total_approved=total_approved,
                          total_funded=total_funded,
                          recent_applications=recent_applications,
                          applications_by_status=applications_by_status)