"""
Routes for Financial Institution Recapitalization Program
This module provides simple routes for the recapitalization program.
"""
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user


# Create blueprint
recapitalization = Blueprint('recapitalization', __name__, url_prefix='/recapitalization')


@recapitalization.route('/')
@login_required
def index():
    """Main page for the recapitalization program"""
    return render_template('capital_injection/placeholder.html')


@recapitalization.route('/register-institution')
@login_required
def register_institution():
    """Register a financial institution for recapitalization"""
    flash('The institution registration feature is coming soon. Please contact our team for assistance.', 'info')
    return redirect(url_for('recapitalization.index'))


@recapitalization.route('/request-info')
@login_required
def request_info():
    """Request more information about the recapitalization program"""
    flash('Thank you for your interest. Our team will contact you shortly with more information.', 'success')
    return redirect(url_for('recapitalization.index'))