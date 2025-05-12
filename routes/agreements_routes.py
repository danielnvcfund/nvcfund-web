"""
Institutional Agreements Routes
Routes for various types of agreements with NVC Fund Bank, including
Asset Management, Custody, Memorandum of Understanding (MOU), and more.
"""

import os
import logging
from flask import Blueprint, render_template, send_from_directory, redirect, url_for, send_file, request, flash
from flask_login import login_required, current_user
from generate_custody_agreement import generate_custody_agreement

agreements_bp = Blueprint('agreements', __name__, url_prefix='/agreements')
logger = logging.getLogger(__name__)

@agreements_bp.route('/')
@login_required
def index():
    """Main agreements selection page"""
    return render_template('agreements/index.html', title='NVC Fund Bank Agreements')

# =================== Asset Management Agreement Routes ===================

@agreements_bp.route('/asset-management/agreement')
@login_required
def asset_management_agreement():
    """View asset management agreement information"""
    return render_template('agreements/asset_management_agreement.html', title='Asset Management Agreement')

@agreements_bp.route('/asset-management/agreement.pdf')
@login_required
def download_asset_management_agreement():
    """Download the asset management agreement PDF"""
    try:
        # Path to the static PDF file
        static_file_path = os.path.join(os.getcwd(), 'static', 'documents', 'NVC_Fund_Bank_Asset_Management_Agreement.pdf')
        
        # If the file doesn't exist, generate it (future implementation)
        if not os.path.exists(static_file_path):
            # This would be implemented similar to the correspondent agreement generator
            flash("Asset Management Agreement template is being developed. Please check back soon.", "info")
            return redirect(url_for('agreements.asset_management_agreement'))
        
        # Serve the PDF file
        return send_file(
            static_file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_Fund_Bank_Asset_Management_Agreement.pdf'
        )
        
    except Exception as e:
        logger.error(f"Error serving asset management agreement PDF: {str(e)}")
        flash("There was an error generating the agreement PDF. Please try again later.", "error")
        return redirect(url_for('agreements.asset_management_agreement'))

@agreements_bp.route('/asset-management/onboarding')
@login_required
def asset_management_onboarding():
    """Asset management onboarding process"""
    return render_template('agreements/asset_management_onboarding.html', title='Asset Management Onboarding')

# =================== Custody Agreement Routes ===================

@agreements_bp.route('/custody/agreement')
@login_required
def custody_agreement():
    """View custody agreement information"""
    return render_template('agreements/custody_agreement.html', title='Custody Agreement')

@agreements_bp.route('/custody/agreement.pdf')
@login_required
def download_custody_agreement():
    """Download the custody agreement PDF"""
    try:
        # Path to the static PDF file
        static_file_path = os.path.join(os.getcwd(), 'static', 'documents', 'NVC_Fund_Bank_Custody_Agreement.pdf')
        
        # If the file doesn't exist, generate it
        if not os.path.exists(static_file_path):
            # Generate the custody agreement PDF
            logger.info("Generating custody agreement PDF...")
            static_file_path = generate_custody_agreement()
            logger.info(f"Custody agreement PDF generated at: {static_file_path}")
        
        # Serve the PDF file
        return send_file(
            static_file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_Fund_Bank_Custody_Agreement.pdf'
        )
        
    except Exception as e:
        logger.error(f"Error serving custody agreement PDF: {str(e)}")
        flash("There was an error generating the agreement PDF. Please try again later.", "error")
        return redirect(url_for('agreements.custody_agreement'))

@agreements_bp.route('/custody/onboarding')
@login_required
def custody_onboarding():
    """Custody services onboarding process"""
    return render_template('agreements/custody_onboarding.html', title='Custody Services Onboarding')

# =================== MOU Routes ===================

@agreements_bp.route('/mou/agreement')
@login_required
def mou_agreement():
    """View MOU agreement information"""
    return render_template('agreements/mou_agreement.html', title='Memorandum of Understanding')

@agreements_bp.route('/mou/agreement.pdf')
@login_required
def download_mou_agreement():
    """Download the MOU agreement PDF"""
    try:
        # Path to the static PDF file
        static_file_path = os.path.join(os.getcwd(), 'static', 'documents', 'NVC_Fund_Bank_Memorandum_of_Understanding.pdf')
        
        # If the file doesn't exist, generate it (future implementation)
        if not os.path.exists(static_file_path):
            # This would be implemented similar to the correspondent agreement generator
            flash("Memorandum of Understanding template is being developed. Please check back soon.", "info")
            return redirect(url_for('agreements.mou_agreement'))
        
        # Serve the PDF file
        return send_file(
            static_file_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_Fund_Bank_Memorandum_of_Understanding.pdf'
        )
        
    except Exception as e:
        logger.error(f"Error serving MOU PDF: {str(e)}")
        flash("There was an error generating the MOU PDF. Please try again later.", "error")
        return redirect(url_for('agreements.mou_agreement'))

@agreements_bp.route('/mou/onboarding')
@login_required
def mou_onboarding():
    """MOU onboarding process"""
    return render_template('agreements/mou_onboarding.html', title='MOU Onboarding')