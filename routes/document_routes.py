import os
from flask import Blueprint, send_file, render_template
import pdfkit
import tempfile

document_routes = Blueprint('documents', __name__, url_prefix='/documents')

@document_routes.route('/nvc_funds_transfer_guide.pdf')
def nvc_funds_transfer_guide_pdf():
    """Generate a PDF with funds transfer instructions"""
    
    # Render the HTML template
    html_content = render_template('documents/nvc_funds_transfer_guide.html')
    
    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        pdf_path = temp_file.name
    
    # Convert HTML to PDF
    pdfkit.from_string(html_content, pdf_path)
    
    # Send the PDF file
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name='NVC_Global_Funds_Transfer_Guide.pdf',
        mimetype='application/pdf'
    )