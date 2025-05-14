"""
Routes for correspondent banking functionality
"""

import logging
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import UserRole, CorrespondentBankApplication
from forms import CorrespondentBankApplicationForm
from correspondent_bank_service import process_application_submission, get_application_by_reference, update_application_status, get_application_statistics
from decorators import roles_required

# Setup blueprint
correspondent = Blueprint('correspondent', __name__, url_prefix='/correspondent')

# Setup logging
logger = logging.getLogger(__name__)


@correspondent.route('/portal', methods=['GET'])
def portal():
    """Display the correspondent bank portal homepage"""
    form = CorrespondentBankApplicationForm()
    return render_template('correspondent/portal.html', form=form)


@correspondent.route('/submit-application', methods=['POST'])
def submit_application():
    """Process correspondent bank application submission"""
    form = CorrespondentBankApplicationForm()
    
    if form.validate_on_submit():
        try:
            # Prepare form data for processing
            form_data = {
                'institution_name': form.institution_name.data,
                'country': form.country.data,
                'swift_code': form.swift_code.data,
                'institution_type': form.institution_type.data,
                'regulatory_authority': form.regulatory_authority.data,
                'contact_name': form.contact_name.data,
                'contact_title': form.contact_title.data,
                'contact_email': form.contact_email.data,
                'contact_phone': form.contact_phone.data,
                'services': form.services.data,
                'expected_volume': form.expected_volume.data,
                'african_regions': form.african_regions.data,
                'additional_info': form.additional_info.data
            }
            
            # Process the application
            success, result = process_application_submission(form_data)
            
            if success:
                # Redirect to confirmation page
                return redirect(url_for('correspondent.application_confirmation', reference=result))
            else:
                # Display error
                flash(f'Error processing application: {result}', 'danger')
                return render_template('correspondent/portal.html', form=form)
                
        except Exception as e:
            logger.error(f"Error in application submission: {str(e)}")
            flash('An unexpected error occurred. Please try again later.', 'danger')
            return render_template('correspondent/portal.html', form=form)
    else:
        # Form validation failed
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
        return render_template('correspondent/portal.html', form=form)


@correspondent.route('/application-confirmation/<reference>', methods=['GET'])
def application_confirmation(reference):
    """Display application confirmation page"""
    application = get_application_by_reference(reference)
    
    if not application:
        flash('Application reference not found.', 'danger')
        return redirect(url_for('correspondent.portal'))
        
    return render_template(
        'correspondent/application_confirmation.html',
        reference=reference,
        institution=application.institution_name,
        contact=application.contact_name
    )


@correspondent.route('/applications', methods=['GET'])
@login_required
@roles_required([UserRole.ADMIN.name])
def list_applications():
    """List all applications (admin only)"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    applications = CorrespondentBankApplication.query.order_by(
        CorrespondentBankApplication.submission_date.desc()
    ).paginate(page=page, per_page=per_page)
    
    stats = get_application_statistics()
    
    return render_template(
        'correspondent/applications_list.html',
        applications=applications,
        stats=stats
    )


@correspondent.route('/application/<reference>', methods=['GET'])
@login_required
@roles_required([UserRole.ADMIN.name])
def view_application(reference):
    """View application details (admin only)"""
    application = get_application_by_reference(reference)
    
    if not application:
        flash('Application not found.', 'danger')
        return redirect(url_for('correspondent.list_applications'))
        
    # Convert JSON strings to lists
    try:
        services = json.loads(application.services)
        african_regions = json.loads(application.african_regions)
    except:
        services = []
        african_regions = []
        
    return render_template(
        'correspondent/application_details.html',
        application=application,
        services=services,
        regions=african_regions
    )


@correspondent.route('/application/<reference>/status', methods=['POST'])
@login_required
@roles_required([UserRole.ADMIN.name])
def update_status(reference):
    """Update application status (admin only)"""
    application = get_application_by_reference(reference)
    
    if not application:
        flash('Application not found.', 'danger')
        return redirect(url_for('correspondent.list_applications'))
        
    new_status = request.form.get('status')
    notes = request.form.get('notes')
    
    if not new_status or new_status not in ['PENDING', 'REVIEWING', 'APPROVED', 'REJECTED']:
        flash('Invalid status value.', 'danger')
        return redirect(url_for('correspondent.view_application', reference=reference))
        
    success = update_application_status(reference, new_status, current_user.id, notes)
    
    if success:
        flash(f'Application status updated to {new_status}.', 'success')
    else:
        flash('Error updating application status.', 'danger')
        
    return redirect(url_for('correspondent.view_application', reference=reference))