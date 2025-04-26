"""
API blueprint initialization
"""
from flask import Blueprint

# Create main API blueprint
api_bp = Blueprint('general_api', __name__, url_prefix='/api')

# Import and register blueprints
from routes.api.treasury_api import treasury_api_bp

# Register blueprints
api_bp.register_blueprint(treasury_api_bp)