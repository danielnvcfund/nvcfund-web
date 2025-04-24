"""
API Key Management routes for administrators
"""
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from app import db
from auth import admin_required
from models import PartnerApiKey, PartnerApiKeyType, PartnerApiKeyAccessLevel, UserRole
from forms import PartnerApiKeyForm

logger = logging.getLogger(__name__)

# Create blueprint
admin_api_keys = Blueprint('admin_api_keys', __name__, url_prefix='/admin/api-keys')

@admin_api_keys.route('/')
@login_required
@admin_required
def api_keys_list():
    """List all partner API keys"""
    # Get all API keys
    api_keys = PartnerApiKey.query.order_by(PartnerApiKey.created_at.desc()).all()
    
    # Create form for CSRF protection
    form = PartnerApiKeyForm()
    
    return render_template(
        'admin/api_key_management.html',
        api_keys=api_keys,
        form=form,
        show_new_key=False
    )

@admin_api_keys.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_partner_api_key():
    """Create a new partner API key"""
    form = PartnerApiKeyForm()
    
    if form.validate_on_submit():
        try:
            # Generate a new API key
            api_key = PartnerApiKey.generate_api_key()
            
            # Create new partner API key
            partner_key = PartnerApiKey(
                partner_name=form.partner_name.data,
                partner_email=form.partner_email.data,
                partner_type=PartnerApiKeyType(form.partner_type.data),
                api_key=api_key,
                access_level=PartnerApiKeyAccessLevel(form.access_level.data),
                description=form.description.data,
                is_active=form.is_active.data
            )
            
            db.session.add(partner_key)
            db.session.commit()
            
            logger.info(f"Created new partner API key for {partner_key.partner_name}")
            
            # Return to the list page with the new key highlighted
            return render_template(
                'admin/api_key_management.html',
                api_keys=PartnerApiKey.query.order_by(PartnerApiKey.created_at.desc()).all(),
                form=PartnerApiKeyForm(),
                show_new_key=True,
                new_key=partner_key
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating partner API key: {str(e)}")
            flash(f"Error creating API key: {str(e)}", "danger")
    
    # If GET request or form validation failed
    return render_template(
        'admin/api_key_management.html',
        api_keys=PartnerApiKey.query.order_by(PartnerApiKey.created_at.desc()).all(),
        form=form,
        show_new_key=False
    )

@admin_api_keys.route('/toggle/<int:key_id>', methods=['POST'])
@login_required
@admin_required
def toggle_partner_api_key(key_id):
    """Toggle a partner API key active status"""
    partner_key = PartnerApiKey.query.get_or_404(key_id)
    
    # Toggle active status
    partner_key.is_active = not partner_key.is_active
    
    db.session.commit()
    
    status = "activated" if partner_key.is_active else "deactivated"
    flash(f"API key for {partner_key.partner_name} {status}", "success")
    
    return redirect(url_for('admin.admin_api_keys.api_keys_list'))

@admin_api_keys.route('/edit/<int:key_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_partner_api_key(key_id):
    """Edit a partner API key"""
    partner_key = PartnerApiKey.query.get_or_404(key_id)
    
    form = PartnerApiKeyForm(obj=partner_key)
    
    if form.validate_on_submit():
        try:
            # Update partner API key
            partner_key.partner_name = form.partner_name.data
            partner_key.partner_email = form.partner_email.data
            partner_key.partner_type = PartnerApiKeyType(form.partner_type.data)
            partner_key.access_level = PartnerApiKeyAccessLevel(form.access_level.data)
            partner_key.description = form.description.data
            partner_key.is_active = form.is_active.data
            
            db.session.commit()
            
            logger.info(f"Updated partner API key for {partner_key.partner_name}")
            flash(f"API key for {partner_key.partner_name} updated", "success")
            
            return redirect(url_for('admin.admin_api_keys.api_keys_list'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating partner API key: {str(e)}")
            flash(f"Error updating API key: {str(e)}", "danger")
    
    return render_template(
        'admin/edit_api_key.html',
        form=form,
        partner_key=partner_key
    )

@admin_api_keys.route('/saint-crowm-bank/create', methods=['GET'])
@login_required
@admin_required
def create_saint_crowm_bank_key():
    """Create a new API key specifically for Saint Crowm Bank"""
    try:
        # Create API key for Saint Crowm Bank
        partner_key = PartnerApiKey.create_for_saint_crowm_bank()
        
        logger.info(f"Created/retrieved API key for Saint Crowm Bank: {partner_key.api_key}")
        
        # Return to the list page with the new key highlighted
        return render_template(
            'admin/api_key_management.html',
            api_keys=PartnerApiKey.query.order_by(PartnerApiKey.created_at.desc()).all(),
            form=PartnerApiKeyForm(),
            show_new_key=True,
            new_key=partner_key
        )
        
    except Exception as e:
        logger.error(f"Error creating Saint Crowm Bank API key: {str(e)}")
        flash(f"Error creating API key: {str(e)}", "danger")
        
        return redirect(url_for('admin.admin_api_keys.api_keys_list'))