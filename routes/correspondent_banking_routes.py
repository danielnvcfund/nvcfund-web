"""
Correspondent Banking Routes
Routes for viewing and downloading correspondent banking agreements.
"""

import os
import logging
from flask import Blueprint, render_template, send_from_directory, redirect, url_for, send_file, request, flash
from flask_login import login_required, current_user

correspondent_bp = Blueprint('correspondent', __name__, url_prefix='/correspondent-banking')
logger = logging.getLogger(__name__)

@correspondent_bp.route('/')
@login_required
def index():
    """Correspondent Banking index page"""
    return render_template('correspondent/index.html', title='Correspondent Banking')

@correspondent_bp.route('/agreement')
@login_required
def agreement():
    """View correspondent banking agreement information"""
    return render_template('correspondent/agreement.html', title='Correspondent Banking Agreement')

@correspondent_bp.route('/agreement.pdf')
@login_required
def download_agreement():
    """Download the correspondent banking agreement PDF"""
    try:
        # Path to the static PDF file
        static_file_path = os.path.join(os.getcwd(), 'static', 'documents', 'NVC_Fund_Bank_Correspondent_Banking_Agreement.pdf')
        
        # If the file doesn't exist, generate it
        if not os.path.exists(static_file_path):
            from generate_correspondent_banking_agreement import generate_correspondent_banking_agreement
            generate_correspondent_banking_agreement()
        
        # Serve the PDF file
        return send_file(
            static_file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_Fund_Bank_Correspondent_Banking_Agreement.pdf'
        )
        
    except Exception as e:
        logger.error(f"Error serving correspondent banking agreement PDF: {str(e)}")
        flash("There was an error generating the agreement PDF. Please try again later.", "error")
        return redirect(url_for('correspondent.agreement'))

@correspondent_bp.route('/onboarding')
@login_required
def onboarding():
    """Correspondent bank onboarding process"""
    return render_template('correspondent/onboarding.html', title='Correspondent Bank Onboarding')

@correspondent_bp.route('/partners')
@login_required
def partners():
    """View current correspondent banking partners"""
    # This would typically pull from a database of partners
    # For now, we'll just pass sample data to the template
    partners = [
        {
            'name': 'Example International Bank',
            'country': 'United States',
            'swift': 'EXAMUS33',
            'relationship_since': '2023-06-15',
            'status': 'Active'
        },
        {
            'name': 'Global Financial Services',
            'country': 'United Kingdom',
            'swift': 'GLOBGB2L',
            'relationship_since': '2023-09-22',
            'status': 'Active'
        }
    ]
    return render_template('correspondent/partners.html', title='Correspondent Bank Partners', partners=partners)