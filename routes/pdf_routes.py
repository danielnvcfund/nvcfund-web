"""
PDF Routes
This module provides routes for generating and serving PDF documents.
"""

import os
from datetime import datetime
import logging
from flask import Blueprint, render_template, send_file, Response, current_app
from flask_login import login_required, current_user
from weasyprint import HTML
from models import FinancialInstitution
from auth import admin_required

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
pdf_bp = Blueprint('pdf', __name__, url_prefix='/pdf')

@pdf_bp.route('/swift-telex-capabilities')
@login_required
def swift_telex_capabilities():
    """Generate and serve a PDF document describing SWIFT and Telex capabilities"""
    
    # Get institution data
    institution = FinancialInstitution.query.filter_by(name='NVC BANK').first()
    if not institution:
        # Try alternate name
        institution = FinancialInstitution.query.filter(FinancialInstitution.swift_code == 'NVCGLOBAL').first()
    
    # Use default values if institution not found
    if institution:
        bank_name = institution.name
        swift_code = institution.swift_code
    else:
        bank_name = "NVC Fund Bank"
        swift_code = "NVCGLOBAL"
    
    # Prepare template context
    context = {
        'bank_name': bank_name,
        'swift_code': swift_code,
        'current_date': datetime.now().strftime('%B %d, %Y'),
        'current_year': datetime.now().year
    }
    
    # Render template
    html_content = render_template('pdf/swift_telex_capabilities.html', **context)
    
    try:
        # Generate PDF
        pdf_content = HTML(string=html_content).write_pdf()
        
        # Return PDF
        response = Response(pdf_content, mimetype='application/pdf')
        response.headers['Content-Disposition'] = 'inline; filename=swift_telex_capabilities.pdf'
        return response
    
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return f"Error generating PDF: {str(e)}", 500

# Register the blueprint
def register_pdf_routes(app):
    """Register PDF routes with the app"""
    app.register_blueprint(pdf_bp)
    logger.info("PDF routes registered successfully")