"""
Public download routes for NVC Banking Platform
"""

import os
import logging
from flask import Blueprint, send_from_directory, render_template
from generate_custody_agreement import generate_custody_agreement

public_downloads_bp = Blueprint('public_downloads', __name__, url_prefix='/public')
logger = logging.getLogger(__name__)

@public_downloads_bp.route('/download/custody-agreement')
def download_custody_agreement():
    """Download the custody agreement PDF without requiring authentication"""
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
        return send_from_directory(
            'static/documents',
            'NVC_Fund_Bank_Custody_Agreement.pdf',
            mimetype='application/pdf',
            as_attachment=True
        )
        
    except Exception as e:
        logger.error(f"Error serving custody agreement PDF: {str(e)}")
        return "Error generating PDF. Please try again later."