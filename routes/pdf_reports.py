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

@pdf_reports.route('/')
def reports_index():
    """Display the reports index page"""
    current_date = datetime.now().strftime("%B %d, %Y")
    return render_template('reports/index.html', current_date=current_date)

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
        
        # Get the base URL for resolving relative URLs
        base_url = current_app.config.get('SERVER_NAME') or 'localhost:5000'
        base_url = f"http://{base_url}"
        
        # Create a PDF from the HTML content
        pdf_file = BytesIO()
        weasyprint.HTML(string=html_content, base_url=base_url).write_pdf(pdf_file)
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

@pdf_reports.route('/capabilities-html')
def nvc_fund_bank_capabilities_html():
    """Display HTML version of the NVC Fund Bank capabilities report"""
    try:
        # Render the HTML template with context data
        current_date = datetime.now().strftime("%B %d, %Y")
        
        logger.info("NVC Fund Bank HTML capabilities report displayed")
        return render_template(
            'reports/nvc_fund_bank_capabilities_web.html',
            current_date=current_date
        )
    
    except Exception as e:
        logger.error(f"Error displaying HTML capabilities report: {str(e)}")
        return f"Error displaying report: {str(e)}", 500

# Register the routes
def register_pdf_reports_routes(app):
    app.register_blueprint(pdf_reports, url_prefix='/reports')
    logger.info("PDF Reports routes registered successfully")