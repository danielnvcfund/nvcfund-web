"""
Direct static file serving routes
"""

import os
import logging
from flask import Flask, send_from_directory
from generate_custody_agreement import generate_custody_agreement

logger = logging.getLogger(__name__)

def register_static_routes(app):
    """Register direct static file routes with the Flask app"""
    
    @app.route('/custody-agreement')
    def serve_custody_agreement():
        """Serve the custody agreement PDF directly without auth"""
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