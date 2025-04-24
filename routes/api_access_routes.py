"""
API Access Request routes
This module provides routes for users to request API access
and for admins to review those requests.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db, csrf
from models import User, UserRole, ApiAccessRequest, ApiAccessRequestStatus, PartnerApiKey, PartnerApiKeyType, PartnerApiKeyAccessLevel
from forms import ApiAccessRequestForm, ApiAccessReviewForm
from auth import admin_required
import logging
import secrets
from datetime import datetime

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

# Developer API Key Management Routes
@api_access_bp.route('/keys', methods=['GET'])
@login_required
def developer_keys():
    """Show and manage developer API keys"""
    # Only users with DEVELOPER role can access this
    if current_user.role != UserRole.DEVELOPER:
        flash("You need developer privileges to access API key management", "warning")
        return redirect(url_for('api_access.request_access'))
    
    # Get API keys for the current developer
    api_keys = PartnerApiKey.query.filter_by(
        user_id=current_user.id
    ).order_by(PartnerApiKey.created_at.desc()).all()
    
    return render_template(
        'api_access/developer_keys.html',
        api_keys=api_keys,
        form={"csrf_token": csrf.generate_csrf()},
        title="My API Keys"
    )

@api_access_bp.route('/keys/create', methods=['POST'])
@login_required
def create_api_key():
    """Create a new API key for the developer"""
    # Only users with DEVELOPER role can create API keys
    if current_user.role != UserRole.DEVELOPER:
        flash("You need developer privileges to create API keys", "warning")
        return redirect(url_for('api_access.request_access'))
    
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash("API key name is required", "danger")
            return redirect(url_for('api_access.developer_keys'))
        
        # Generate a new API key
        api_key = f"nvc_dev_{secrets.token_hex(16)}"
        
        # Create the API key record
        new_key = PartnerApiKey(
            partner_name=name,
            partner_email=current_user.email,
            description=description,
            partner_type=PartnerApiKeyType.DEVELOPER,
            api_key=api_key,
            access_level=PartnerApiKeyAccessLevel.READ,  # Default to read-only for safety
            is_active=True,
            user_id=current_user.id
        )
        
        db.session.add(new_key)
        db.session.commit()
        
        flash(f"API key '{name}' created successfully. Please copy your key now as it won't be displayed again in full.", "success")
        return redirect(url_for('api_access.developer_keys'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating API key: {str(e)}")
        flash(f"Error creating API key: {str(e)}", "danger")
        return redirect(url_for('api_access.developer_keys'))

@api_access_bp.route('/keys/update', methods=['POST'])
@login_required
def update_api_key():
    """Update an existing API key"""
    # Only users with DEVELOPER role can update API keys
    if current_user.role != UserRole.DEVELOPER:
        flash("You need developer privileges to update API keys", "warning")
        return redirect(url_for('api_access.request_access'))
    
    try:
        key_id = request.form.get('key_id')
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        active = request.form.get('active') == 'on'
        
        if not key_id or not name:
            flash("API key ID and name are required", "danger")
            return redirect(url_for('api_access.developer_keys'))
        
        # Find the API key and verify ownership
        api_key = PartnerApiKey.query.filter_by(id=key_id).first()
        
        if not api_key:
            flash("API key not found", "danger")
            return redirect(url_for('api_access.developer_keys'))
        
        if api_key.user_id != current_user.id:
            flash("You do not have permission to edit this API key", "danger")
            return redirect(url_for('api_access.developer_keys'))
        
        # Update the API key details
        api_key.partner_name = name
        api_key.description = description
        api_key.is_active = active
        api_key.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f"API key '{name}' updated successfully", "success")
        return redirect(url_for('api_access.developer_keys'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating API key: {str(e)}")
        flash(f"Error updating API key: {str(e)}", "danger")
        return redirect(url_for('api_access.developer_keys'))

@api_access_bp.route('/keys/delete', methods=['POST'])
@login_required
def delete_api_key():
    """Delete an API key"""
    # Only users with DEVELOPER role can delete API keys
    if current_user.role != UserRole.DEVELOPER:
        flash("You need developer privileges to delete API keys", "warning")
        return redirect(url_for('api_access.request_access'))
    
    try:
        key_id = request.form.get('key_id')
        confirm_delete = request.form.get('confirm_delete') == 'on'
        
        if not key_id or not confirm_delete:
            flash("API key ID and confirmation are required", "danger")
            return redirect(url_for('api_access.developer_keys'))
        
        # Find the API key and verify ownership
        api_key = PartnerApiKey.query.filter_by(id=key_id).first()
        
        if not api_key:
            flash("API key not found", "danger")
            return redirect(url_for('api_access.developer_keys'))
        
        if api_key.user_id != current_user.id:
            flash("You do not have permission to delete this API key", "danger")
            return redirect(url_for('api_access.developer_keys'))
        
        # Delete the API key
        key_name = api_key.partner_name
        db.session.delete(api_key)
        db.session.commit()
        
        flash(f"API key '{key_name}' deleted successfully", "success")
        return redirect(url_for('api_access.developer_keys'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting API key: {str(e)}")
        flash(f"Error deleting API key: {str(e)}", "danger")
        return redirect(url_for('api_access.developer_keys'))