"""
Extension to web routes for registration and dashboard redirection
"""
from flask import redirect, url_for, flash
from flask_login import current_user

from routes.dashboard_routes import dashboard_bp

@dashboard_bp.route('/welcome')
def welcome():
    """
    Welcome page after registration, 
    sends users to account creation if they don't have accounts yet
    """
    if current_user.is_authenticated:
        flash('Welcome to NVC Banking! Complete your profile to generate your accounts.', 'info')
        return redirect(url_for('account.create_profile'))
    else:
        return redirect(url_for('web.main.register'))