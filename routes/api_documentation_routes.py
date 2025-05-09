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
    """Generate PDF version of the NVC API Infrastructure document"""
    try:
        # Create a temp file for the PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            temp_pdf_path = temp_pdf.name
        
        # Get the HTML content
        html_file_path = os.path.join(os.getcwd(), 'static', 'documents', 'nvc_api_infrastructure.html')
        with open(html_file_path, 'r') as html_file:
            html_content = html_file.read()
        
        # Configure fonts
        font_config = FontConfiguration()
        
        # Generate PDF from HTML
        html = HTML(string=html_content, base_url=os.getcwd())
        css = CSS(string='''
            @page {
                size: letter;
                margin: 1cm;
                @top-center {
                    content: "NVC Banking Platform";
                }
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages);
                }
            }
        ''', font_config=font_config)
        
        html.write_pdf(temp_pdf_path, stylesheets=[css], font_config=font_config)
        
        directory, filename = os.path.split(temp_pdf_path)
        return send_from_directory(directory, filename, as_attachment=True, 
                                  attachment_filename='NVC_API_Infrastructure.pdf')
    
    except Exception as e:
        logger.error(f"Error generating API Infrastructure PDF: {str(e)}")
        return "Error generating PDF. Please try again later.", 500

@api_docs_bp.route('/api-reference')
def api_reference():
    """API reference documentation"""
    return render_template('api_docs/api_reference.html', title='API Reference')

@api_docs_bp.route('/integration-guides')
def integration_guides():
    """API integration guides"""
    return render_template('api_docs/integration_guides.html', title='Integration Guides')