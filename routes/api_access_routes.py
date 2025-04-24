"""
API Access Request routes
This module provides routes for users to request API access
and for admins to review those requests.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from models import ApiAccessRequest, ApiAccessRequestStatus, User, UserRole
from forms import ApiAccessRequestForm, ApiAccessReviewForm
from auth import admin_required
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
api_access_bp = Blueprint('api_access', __name__, url_prefix='/api-access')

@api_access_bp.route('/request', methods=['GET', 'POST'])
@login_required
def request_access():
    """Handle API access request form for regular users"""
    # Check if user already has DEVELOPER role
    if current_user.role == UserRole.DEVELOPER:
        flash("You already have API access with developer privileges", "info")
        return redirect(url_for('web.main.dashboard'))
        
    # Check if user already has a pending request
    existing_request = ApiAccessRequest.query.filter_by(
        user_id=current_user.id,
        status=ApiAccessRequestStatus.PENDING
    ).first()
    
    if existing_request:
        flash("You already have a pending API access request. Please wait for administrator review.", "info")
        return redirect(url_for('web.main.dashboard'))
    
    form = ApiAccessRequestForm()
    if form.validate_on_submit():
        try:
            # Create new request
            access_request = ApiAccessRequest(
                user_id=current_user.id,
                request_reason=form.request_reason.data,
                integration_purpose=form.integration_purpose.data,
                company_name=form.company_name.data,
                website=form.website.data
            )
            
            db.session.add(access_request)
            db.session.commit()
            
            flash("Your API access request has been submitted and is pending review", "success")
            return redirect(url_for('web.main.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating API access request: {str(e)}")
            flash(f"Error submitting request: {str(e)}", "danger")
    
    return render_template(
        'api_access/request_form.html',
        form=form,
        title="Request API Access"
    )

@api_access_bp.route('/status', methods=['GET'])
@login_required
def access_status():
    """Show the status of user's API access requests"""
    requests = ApiAccessRequest.query.filter_by(user_id=current_user.id).order_by(
        ApiAccessRequest.created_at.desc()
    ).all()
    
    return render_template(
        'api_access/status.html',
        requests=requests,
        title="API Access Request Status"
    )

# Admin routes for managing API access requests
@api_access_bp.route('/admin/review', methods=['GET'])
@login_required
@admin_required
def admin_review_list():
    """List all API access requests for admin review"""
    # Get all pending requests first, then others
    pending_requests = ApiAccessRequest.query.filter_by(
        status=ApiAccessRequestStatus.PENDING
    ).order_by(ApiAccessRequest.created_at.asc()).all()
    
    other_requests = ApiAccessRequest.query.filter(
        ApiAccessRequest.status != ApiAccessRequestStatus.PENDING
    ).order_by(ApiAccessRequest.updated_at.desc()).limit(20).all()
    
    return render_template(
        'api_access/admin_review_list.html',
        pending_requests=pending_requests,
        other_requests=other_requests,
        title="Review API Access Requests"
    )

@api_access_bp.route('/admin/review/<int:request_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_review_request(request_id):
    """Review a specific API access request"""
    access_request = ApiAccessRequest.query.get_or_404(request_id)
    requester = User.query.get(access_request.user_id)
    
    form = ApiAccessReviewForm()
    if form.validate_on_submit():
        try:
            # Update request status
            old_status = access_request.status
            access_request.status = ApiAccessRequestStatus(form.status.data)
            access_request.reviewed_by = current_user.id
            access_request.reviewer_notes = form.reviewer_notes.data
            
            # If approved, update user role to DEVELOPER
            if access_request.status == ApiAccessRequestStatus.APPROVED and old_status != ApiAccessRequestStatus.APPROVED:
                requester.role = UserRole.DEVELOPER
                logger.info(f"User {requester.username} (ID: {requester.id}) upgraded to DEVELOPER role")
            
            db.session.commit()
            
            flash(f"API access request for {requester.username} has been {access_request.status.value}", "success")
            return redirect(url_for('api_access.admin_review_list'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating API access request: {str(e)}")
            flash(f"Error updating request: {str(e)}", "danger")
    else:
        # Pre-populate the form
        form.status.data = access_request.status.value
        form.reviewer_notes.data = access_request.reviewer_notes
    
    return render_template(
        'api_access/admin_review.html',
        form=form,
        access_request=access_request,
        requester=requester,
        title=f"Review Request: {requester.username}"
    )