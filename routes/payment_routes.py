"""
Payment Routes Module
This module handles the routes for payment options
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

# Blueprint Definition
payment_bp = Blueprint('payment', __name__, url_prefix='/payments')

@payment_bp.route('/options', methods=['GET'])
@login_required
def options():
    """Display payment options for funding NVCT accounts"""
    return render_template(
        'payments/options.html',
        title="Payment Options for NVCT Funding"
    )