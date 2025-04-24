"""
Admin routes package
"""
from flask import Blueprint

# Create the main admin blueprint
admin = Blueprint('admin', __name__, url_prefix='/admin')

# Import and register admin route modules
from .api_key_routes import admin_api_keys

# Register sub-blueprints
admin.register_blueprint(admin_api_keys)