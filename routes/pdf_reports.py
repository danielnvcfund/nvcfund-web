"""
PDF Reports Routes
This module provides routes for generating PDF reports for the NVC Fund system
"""
import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, send_file, make_response, current_app
import weasyprint
from io import BytesIO

# Create a blueprint for PDF reports
pdf_reports = Blueprint('pdf_reports', __name__)
logger = logging.getLogger(__name__)

@pdf_reports.route('/capabilities-report')
def nvc_fund_bank_capabilities_report():
    """Generate a PDF report on NVC Fund Bank capabilities"""
    try:
        # Render the HTML template with context data
        current_date = datetime.now().strftime("%B %d, %Y")
        html_content = render_template(
            'reports/nvc_fund_bank_capabilities.html',
            current_date=current_date
        )
        
        # Create a PDF from the HTML content
        pdf_file = BytesIO()
        weasyprint.HTML(string=html_content).write_pdf(pdf_file)
        pdf_file.seek(0)
        
        # Create a response with the PDF content
        response = make_response(pdf_file.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=NVC_Fund_Bank_Capabilities.pdf'
        
        logger.info("NVC Fund Bank capabilities report successfully generated")
        return response
    
    except Exception as e:
        logger.error(f"Error generating capabilities report: {str(e)}")
        return f"Error generating PDF: {str(e)}", 500

# Register the routes
def register_pdf_reports_routes(app):
    app.register_blueprint(pdf_reports, url_prefix='/reports')
    logger.info("PDF Reports routes registered successfully")