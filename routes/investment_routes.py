"""
Investment routes for NVC Banking Platform
"""

from flask import Blueprint, render_template

investment_bp = Blueprint('investment', __name__, url_prefix='/investment')

@investment_bp.route('/offering')
def offering():
    """Display the $50M investment offering overview"""
    return render_template('investment/offering_overview.html', title="Investment Opportunity")

@investment_bp.route('/prospectus')
def prospectus():
    """Display the detailed investment prospectus"""
    return render_template('investment/offering_prospectus.html', title="Investment Prospectus")