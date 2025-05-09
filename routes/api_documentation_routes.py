"""
API Documentation Routes
This module contains routes for API documentation and guides.
"""
import os
import logging
from flask import Blueprint, render_template, send_from_directory, redirect, url_for
from flask_login import login_required, current_user
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from io import BytesIO
import tempfile

api_docs_bp = Blueprint('api_docs', __name__, url_prefix='/api-docs')
logger = logging.getLogger(__name__)

@api_docs_bp.route('/')
def index():
    """API documentation index page"""
    return render_template('api_docs/index.html', title='API Documentation')

@api_docs_bp.route('/nvc-api-infrastructure')
def nvc_api_infrastructure():
    """NVC API Infrastructure document page"""
    return render_template('api_docs/nvc_api_infrastructure.html', title='NVC API Infrastructure')

@api_docs_bp.route('/nvc-api-infrastructure.pdf')
def nvc_api_infrastructure_pdf():
    """Serve static PDF version of the NVC API Infrastructure document"""
    try:
        # Return a static PDF file instead of generating it dynamically
        static_file_path = os.path.join(os.getcwd(), 'static', 'documents', 'NVC_API_Infrastructure.pdf')
        
        if not os.path.exists(static_file_path):
            # If the static PDF doesn't exist, create it
            logger.info(f"Creating static PDF file at {static_file_path}")
            with open(static_file_path, 'w') as f:
                f.write("""NVC Banking Platform API Infrastructure

Strategic Integration with the Financial Ecosystem

What is an API?

API (Application Programming Interface) serves as a structured communication bridge that allows different software systems to interact with each other. In the context of the NVC Banking Platform, APIs enable secure, standardized methods for exchanging financial data, processing transactions, integrating with external services, and automating financial operations.

Strategic Importance of APIs in the NVC Banking Platform

The NVC Banking Platform's API infrastructure is central to its functioning as a global financial hub.

Please see the HTML version for the complete document.
""")
        
        # Serve the static PDF file
        response = make_response(send_file(static_file_path, mimetype='application/pdf'))
        response.headers['Content-Disposition'] = 'attachment; filename=NVC_API_Infrastructure.pdf'
        return response
    
    except Exception as e:
        logger.error(f"Error serving API Infrastructure PDF: {str(e)}")
        # If we can't serve the PDF for some reason, redirect to the HTML version
        return redirect(url_for('api_docs.nvc_api_infrastructure'))

@api_docs_bp.route('/api-reference')
def api_reference():
    """API reference documentation"""
    return render_template('api_docs/api_reference.html', title='API Reference')

@api_docs_bp.route('/integration-guides')
def integration_guides():
    """API integration guides"""
    return render_template('api_docs/integration_guides.html', title='Integration Guides')