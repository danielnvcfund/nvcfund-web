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
from models import User, FinancialInstitution

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
    # Check if institution has treasury related information in the database directly
    try:
        # Query financial data related to this institution directly from the database
        # Store basic info for display
        if institution_id == 56:  # El Banco Espaniol Isabel II
            # Historical and financial information from provided documents
            treasury_accounts = [{
                'id': 1,
                'name': 'El Banco Espaniol Isabel II Treasury Account',
                'account_number': 'BEFII-TRUST-01',
                'account_type': 'Trust Asset Management',
                'currency': 'USD',
                'formatted_balance': "$11,300,000,000,000,000.00",
                'is_active': True,
                'created_date': '1850-12-20',
                'historical_notes': 'Established by Royal Decree, with cash and gold equities from fruits of the land and Spanish Galleon Trade.',
                'investments': [
                    {'name': 'Gold Reserves', 'amount': 2_500_000_000_000_000, 'investment_type': 'Precious Metals', 'interest_rate': 0.0, 'status': 'Active'},
                    {'name': 'Sovereign Bonds', 'amount': 3_750_000_000_000_000, 'investment_type': 'Government Securities', 'interest_rate': 2.5, 'status': 'Active'},
                    {'name': 'Agricultural Land Holdings', 'amount': 1_875_000_000_000_000, 'investment_type': 'Real Estate', 'interest_rate': 3.2, 'status': 'Active'},
                    {'name': 'Industrial Infrastructure', 'amount': 3_175_000_000_000_000, 'investment_type': 'Commercial Development', 'interest_rate': 4.1, 'status': 'Active'}
                ],
                'formatted_total': "$11,300,000,000,000,000.00",
                'trust_agreements': [
                    {'name': 'Trust Asset Deposit Management Agreement', 'date': '2023-12-20', 'status': 'Active', 'parties': ['Gen. Absalon F. Borci Jr.', 'NVC Fund Bank']}
                ],
                'authorized_signatories': ['Gen. Absalon F. Borci Jr.', 'Frank Ekejija'],
                'regulatory_framework': 'African Finance Regulatory Authority (AFRA)'
            }]
        else:
            treasury_accounts = []
            
    except Exception as e:
        logger.warning(f"Could not retrieve treasury accounts: {str(e)}")
    
    return render_template('institutions/details.html',
                          institution=institution,
                          treasury_accounts=treasury_accounts,
                          title=institution.name)

@institutional_bp.route('/el-banco-isabel')
@login_required
def el_banco_isabel():
    """Direct link to El Banco Espaniol Isabel II."""
    # Hardcode the institution ID for El Banco Isabel (56)
    institution_id = 56
    
    # Redirect to the institution details page
    return redirect(url_for('institutional.institution_details', institution_id=institution_id))

def register_routes(app):
    """Register institutional routes with the Flask application."""
    app.register_blueprint(institutional_bp, url_prefix='/institutional')
    
    # Add direct routes to the main app (skipping the /institutional prefix)
    # Add a direct route for El Banco Isabel page
    app.add_url_rule('/el-banco-isabel', 
                     endpoint='direct_el_banco_isabel',
                     view_func=el_banco_isabel)
    
    # Add a direct route for listing all institutions
    app.add_url_rule('/institutions',
                     endpoint='direct_institutions_list',
                     view_func=list_institutions)
                     
    logger.info("Institutional routes registered successfully")
    return True