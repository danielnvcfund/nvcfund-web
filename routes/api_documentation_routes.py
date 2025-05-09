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
    """Provide PDF version of the NVC API Infrastructure document"""
    # For now, we'll redirect to the HTML version since we're having PDF generation issues
    return redirect(url_for('api_docs.nvc_api_infrastructure'))

@api_docs_bp.route('/api-reference')
def api_reference():
    """API reference documentation"""
    return render_template('api_docs/api_reference.html', title='API Reference')

@api_docs_bp.route('/integration-guides')
def integration_guides():
    """API integration guides"""
    return render_template('api_docs/integration_guides.html', title='Integration Guides')