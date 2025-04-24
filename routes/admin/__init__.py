"""
Admin routes package
"""
from flask import Blueprint, render_template, redirect, url_for

# Create the main admin blueprint
admin = Blueprint('admin', __name__, url_prefix='/admin')

# Import and register admin route modules
from .api_key_routes import admin_api_keys

# Register sub-blueprints
admin.register_blueprint(admin_api_keys)

# Add redirect routes for backward compatibility
@admin.route('/api-keys')
def list_api_keys():
    """Redirect to the API keys list page"""
    return redirect(url_for('admin_api_keys.api_keys_list'))

@admin.route('/api-keys/saint-crowm-bank/create')
def create_saint_crowm_bank_key():
    """Redirect to the Saint Crowm Bank key creation page"""
    return redirect(url_for('admin_api_keys.create_saint_crowm_bank_key'))