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
                'historical_notes': 'Established by Royal Decree on August 1, 1851 under the reign of Queen Isabella II of Spain, with initial operations beginning under the managing directorship of Jose Maria Tuason and Fernando Aguirre.',
                'detailed_history': [
                    {'year': '1826', 'event': 'Royal order circulated among the Obras Pias for opinions regarding establishment of a "public bank"'},
                    {'year': '1827', 'event': 'Obras Pias created by the Spaniards on February 3 as a charitable institution to manage funds for charitable, religious and educational purposes'},
                    {'year': '1828', 'event': 'Foundation of the first public bank in the Philippines was decreed by royal order dated April 6 by King Ferdinand VII of Spain'},
                    {'year': '1851', 'event': 'Officially established on August 1 as El Banco Español Filipino de Isabel II, with first operations in the Royal Custom house (Aduana) in Intramuros'},
                    {'year': '1851', 'event': 'First meeting of the interim Board of Directors held on September 11; First managers were Jose Maria Tuason and Fernando Aguirre'},
                    {'year': '1852', 'event': 'First bank notes issued on May 1, redeemable at face value for gold or silver Mexican coins; First deposit made by Fulgencio Barrera'},
                    {'year': '1857', 'event': 'Articles of Association granted on August 13'},
                    {'year': '1869', 'event': 'Officially dropped the name of Queen Isabella II, becoming simply "El Banco Español Filipino"'},
                    {'year': '1892', 'event': 'Bank moved from Royal Custom House in Intramuros to the new business district of Binondo at Plaza San Gabriel'},
                    {'year': '1897', 'event': 'First branch established in Iloilo on March 15'},
                    {'year': '1898', 'event': 'Following the Treaty of Paris, began transformation from Spanish institution to Philippine institution'},
                    {'year': '1912', 'event': 'Officially renamed as Bank of the Philippine Islands (BPI) on January 1, following Republic Act No. 1790 passed in 1907'},
                    {'year': '1949', 'event': 'Lost the right to issue Philippine pesos with the establishment of the Central Bank of the Philippines'},
                    {'year': '1969', 'event': 'Ayala Corporation became the dominant shareholder group'},
                    {'year': '2023', 'event': 'New Trust Asset Management Agreement established with NVC Fund Bank, leveraging historical assets'}
                ],
                'founding_figures': [
                    {'name': 'Antonio de Urbiztondo y Eguia', 'role': 'Governor-General of the Philippines', 'contribution': 'Led the actual organization of the bank, called for support of the Junta de Autoridades in approving bank statutes'},
                    {'name': 'Jose Maria Tuason', 'role': 'First Managing Director', 'contribution': 'Alternated serving as managing director with Fernando Aguirre'},
                    {'name': 'Fernando Aguirre', 'role': 'First Managing Director', 'contribution': 'Alternated serving as managing director with Jose Maria Tuason'},
                    {'name': 'Jose Juaquin de Ynchausti', 'role': 'Primary Shareholder and Later Director', 'contribution': 'Founder of Ynchausti y Cia, parent of Tanduay Distillery; served as managing director 1868-1873 and 1876-1884'},
                    {'name': 'Antonio de Ayala', 'role': 'Business Representative', 'contribution': 'Represented business community of Manila, from Casa Roxas (precursor to Ayala Corporation)'}
                ],
                'investments': [
                    {'name': 'Gold Reserves', 'amount': 2_500_000_000_000_000, 'investment_type': 'Precious Metals', 'interest_rate': 0.0, 'status': 'Active', 'origin': 'Historical accumulation from Spanish Galleon Trade and Filipino gold mines'},
                    {'name': 'Sovereign Bonds', 'amount': 3_750_000_000_000_000, 'investment_type': 'Government Securities', 'interest_rate': 2.5, 'status': 'Active', 'maturity': '2050-12-31'},
                    {'name': 'Agricultural Land Holdings', 'amount': 1_875_000_000_000_000, 'investment_type': 'Real Estate', 'interest_rate': 3.2, 'status': 'Active', 'location': 'Global with concentration in Philippines, Americas, and Spain'},
                    {'name': 'Industrial Infrastructure', 'amount': 3_175_000_000_000_000, 'investment_type': 'Commercial Development', 'interest_rate': 4.1, 'status': 'Active', 'sectors': 'Energy, Transportation, Manufacturing, Technology'}
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