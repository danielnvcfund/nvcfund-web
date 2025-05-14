"""
Service module for handling correspondent bank applications and related operations.
"""

import json
import random
import string
from datetime import datetime
import logging

from flask import render_template
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import CorrespondentBankApplication, User, UserRole
from email_service import send_email

# Setup logging
logger = logging.getLogger(__name__)

def process_application_submission(form_data):
    """
    Process a new correspondent bank application submission
    
    Args:
        form_data: The form data from the application
        
    Returns:
        tuple: (success, application_reference or error_message)
    """
    try:
        # Generate reference number
        reference_number = generate_reference_number()
        
        # Process services and regions (convert list to JSON string)
        services_json = json.dumps(form_data.get('services', []))
        african_regions_json = json.dumps(form_data.get('african_regions', []))
        
        # Create application record
        application = CorrespondentBankApplication(
            reference_number=reference_number,
            institution_name=form_data.get('institution_name'),
            country=form_data.get('country'),
            swift_code=form_data.get('swift_code'),
            institution_type=form_data.get('institution_type'),
            regulatory_authority=form_data.get('regulatory_authority'),
            contact_name=form_data.get('contact_name'),
            contact_title=form_data.get('contact_title'),
            contact_email=form_data.get('contact_email'),
            contact_phone=form_data.get('contact_phone'),
            services=services_json,
            expected_volume=form_data.get('expected_volume'),
            african_regions=african_regions_json,
            additional_info=form_data.get('additional_info')
        )
        
        db.session.add(application)
        db.session.commit()
        
        # Send confirmation email to applicant
        send_applicant_confirmation(application)
        
        # Notify admin team
        send_admin_notification(application)
        
        return True, reference_number
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error: {str(e)}")
        return False, f"Database error: {str(e)}"
    
    except Exception as e:
        logger.error(f"Error processing application: {str(e)}")
        return False, f"Error processing application: {str(e)}"


def generate_reference_number():
    """
    Generate a unique reference number for a correspondent bank application
    
    Format: CBP-YYYYMMDD-XXXXX (where X is random alphanumeric)
    """
    prefix = "CBP"
    date_part = datetime.utcnow().strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    reference = f"{prefix}-{date_part}-{random_part}"
    
    # Check if this reference exists (unlikely but possible)
    while CorrespondentBankApplication.query.filter_by(reference_number=reference).first():
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        reference = f"{prefix}-{date_part}-{random_part}"
    
    return reference


def send_applicant_confirmation(application):
    """
    Send confirmation email to the applicant
    
    Args:
        application: The CorrespondentBankApplication object
    """
    try:
        # Get application details for email template
        institution_name = application.institution_name
        contact_name = application.contact_name
        contact_email = application.contact_email
        reference_number = application.reference_number
        
        # Render email template
        email_subject = f"Application Received - Reference: {reference_number}"
        email_body = render_template(
            'emails/correspondent_bank_application_confirmation.html',
            institution=institution_name,
            contact_name=contact_name,
            reference=reference_number
        )
        
        # Send the email
        send_email(
            to_email=contact_email,
            subject=email_subject,
            html_content=email_body
        )
        
        logger.info(f"Confirmation email sent to {contact_email} for application {reference_number}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending confirmation email: {str(e)}")
        return False


def send_admin_notification(application):
    """
    Notify administrators about a new application
    
    Args:
        application: The CorrespondentBankApplication object
    """
    try:
        # Fetch admin users to notify
        admins = User.query.filter_by(role=UserRole.ADMIN.name).all()
        admin_emails = [user.email for user in admins if user.email]
        
        if not admin_emails:
            logger.warning("No admin emails found for notification")
            return False
            
        # Render admin notification template
        email_subject = f"New Correspondent Bank Application: {application.institution_name}"
        
        # Convert JSON strings to lists for template
        services = json.loads(application.services)
        regions = json.loads(application.african_regions)
        
        email_body = render_template(
            'emails/new_correspondent_bank_application.html',
            application=application,
            services=services,
            regions=regions,
            submission_date=application.submission_date.strftime('%B %d, %Y %H:%M UTC')
        )
        
        # Send to each admin
        for email in admin_emails:
            send_email(
                to_email=email,
                subject=email_subject,
                html_content=email_body
            )
            
        logger.info(f"Admin notification sent for application {application.reference_number}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending admin notification: {str(e)}")
        return False


def get_application_by_reference(reference):
    """
    Retrieve an application by its reference number
    
    Args:
        reference: Application reference number
        
    Returns:
        CorrespondentBankApplication or None
    """
    return CorrespondentBankApplication.query.filter_by(reference_number=reference).first()


def update_application_status(reference, new_status, user_id=None, notes=None):
    """
    Update the status of an application
    
    Args:
        reference: Application reference number
        new_status: New status value
        user_id: ID of the user making the change
        notes: Optional notes about the status change
        
    Returns:
        boolean: Success or failure
    """
    try:
        application = get_application_by_reference(reference)
        if not application:
            return False
            
        # Update status
        application.status = new_status
        
        # Update reviewer fields
        if new_status == 'REVIEWING':
            application.assigned_to = user_id
            application.review_date = datetime.utcnow()
        elif new_status == 'APPROVED':
            application.approval_date = datetime.utcnow()
        elif new_status == 'REJECTED':
            application.rejection_reason = notes
            
        # Add notes if provided
        if notes:
            application.notes = (application.notes or '') + f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] {notes}"
            
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating application status: {str(e)}")
        return False


def get_application_statistics():
    """
    Get statistics about correspondent bank applications
    
    Returns:
        dict: Statistics about applications
    """
    try:
        total = CorrespondentBankApplication.query.count()
        pending = CorrespondentBankApplication.query.filter_by(status='PENDING').count()
        reviewing = CorrespondentBankApplication.query.filter_by(status='REVIEWING').count()
        approved = CorrespondentBankApplication.query.filter_by(status='APPROVED').count()
        rejected = CorrespondentBankApplication.query.filter_by(status='REJECTED').count()
        
        # Get applications by region (using JSON functions)
        region_stats = {}
        for region in ['West Africa', 'East Africa', 'Southern Africa', 'North Africa']:
            # This query counts applications where the african_regions JSON array contains the region
            count = CorrespondentBankApplication.query.filter(
                CorrespondentBankApplication.african_regions.like(f'%{region}%')
            ).count()
            region_stats[region] = count
            
        return {
            'total': total,
            'pending': pending,
            'reviewing': reviewing,
            'approved': approved,
            'rejected': rejected,
            'regions': region_stats
        }
        
    except Exception as e:
        logger.error(f"Error generating application statistics: {str(e)}")
        return {
            'total': 0,
            'pending': 0,
            'reviewing': 0,
            'approved': 0,
            'rejected': 0,
            'regions': {}
        }