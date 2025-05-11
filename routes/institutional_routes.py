"""
Institutional Routes

This module provides routes for accessing institutional partner details and investments.
"""

import os
import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from app import app, db
from models import User, Institution, FinancialInstitution

# Create a blueprint for institutional routes
institutional_bp = Blueprint('institutional', __name__)
logger = logging.getLogger(__name__)

@institutional_bp.route('/institutions')
@login_required
def list_institutions():
    """List all financial institutions."""
    institutions = FinancialInstitution.query.filter_by(is_active=True).all()
    return render_template('institutions/list.html', 
                          institutions=institutions, 
                          title="Financial Institutions")

@institutional_bp.route('/institutions/<int:institution_id>')
@login_required
def institution_details(institution_id):
    """Show details for a specific financial institution."""
    institution = FinancialInstitution.query.get_or_404(institution_id)
    
    # Get treasury accounts for this institution
    treasury_accounts = []
    try:
        from treasury_loan import TreasuryAccount, TreasuryInvestment
        treasury_accounts = TreasuryAccount.query.filter_by(
            institution_id=institution_id,
            is_active=True
        ).all()
        
        # For each treasury account, get its investments
        for account in treasury_accounts:
            account.investments = TreasuryInvestment.query.filter_by(
                account_id=account.id
            ).all()
            
            # Calculate total investment amount
            account.total_investment = sum(inv.amount for inv in account.investments)
            
            # Format large numbers with commas
            account.formatted_balance = f"{account.current_balance:,.2f}"
            account.formatted_total = f"{account.total_investment:,.2f}"
    except ImportError:
        logger.warning("Treasury module not available")
    
    return render_template('institutions/details.html',
                          institution=institution,
                          treasury_accounts=treasury_accounts,
                          title=institution.name)

@institutional_bp.route('/el-banco-isabel')
@login_required
def el_banco_isabel():
    """Direct link to El Banco Espaniol Isabel II."""
    # Look up the institution by name
    institution = FinancialInstitution.query.filter_by(
        name="El Banco Espaniol Isabel II"
    ).first_or_404()
    
    # Redirect to the institution details page
    return redirect(url_for('institutional.institution_details', institution_id=institution.id))

def register_routes(app):
    """Register institutional routes with the Flask application."""
    app.register_blueprint(institutional_bp, url_prefix='/institutional')
    
    # Add routes to app directly for easier access
    app.add_url_rule('/el-banco-isabel', 
                    view_func=institutional_bp.view_functions['el_banco_isabel'])
    
    logger.info("Institutional routes registered successfully")
    return True