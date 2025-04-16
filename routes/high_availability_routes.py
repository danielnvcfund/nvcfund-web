"""
High-Availability Web Routes for NVC Banking Platform
Provides web-based dashboard for high-availability clustering management.
"""

import logging
from flask import Blueprint, render_template, session
from flask_login import login_required, current_user
from models import User
import high_availability
from auth import admin_required

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
ha_web = Blueprint('ha_web', __name__, url_prefix='/ha')

@ha_web.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """High-availability status and management dashboard"""
    user = current_user
    
    # Initialize the HA infrastructure if not already done
    if not high_availability._ha_initialized:
        high_availability.init_high_availability()
    
    # Get HA status
    ha_status = high_availability.get_ha_status()
    
    return render_template(
        'ha_dashboard.html',
        user=user,
        ha_status=ha_status
    )