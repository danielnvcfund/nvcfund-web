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
    """Serve printable version of the NVC API Infrastructure document"""
    try:
        # Instead of trying to generate a PDF, let's serve a printable HTML version
        # that looks like a PDF but is actually HTML (avoids PDF generation issues)
        return render_template('api_docs/nvc_api_infrastructure_printable.html', 
                              title='NVC API Infrastructure (Printable Version)')
    except Exception as e:
        logger.error(f"Error serving API Infrastructure printable version: {str(e)}")
        # If there's an error, redirect to the regular HTML version
        return redirect(url_for('api_docs.nvc_api_infrastructure'))

@api_docs_bp.route('/api-reference')
def api_reference():
    """API reference documentation"""
    return render_template('api_docs/api_reference.html', title='API Reference')

@api_docs_bp.route('/integration-guides')
def integration_guides():
    """API integration guides"""
    return render_template('api_docs/integration_guides.html', title='Integration Guides')