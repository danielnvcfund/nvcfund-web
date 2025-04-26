"""
Treasury API Routes
This module provides API endpoints for Treasury-related functionality.
Specialized endpoints for individual operations should be defined in treasury_routes.py.
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

# Create the treasury API blueprint
treasury_api_bp = Blueprint('treasury_api', __name__)

# Note: The 'add_institution' endpoint has been moved to treasury_routes.py
# to avoid duplicate route definitions