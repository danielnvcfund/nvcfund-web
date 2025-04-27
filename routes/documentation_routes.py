import os
from flask import Blueprint, render_template, send_file, current_app
import weasyprint
from io import BytesIO

documentation_bp = Blueprint('documentation', __name__)

@documentation_bp.route('/', methods=['GET'])
def documentation_index():
    """Documentation index landing page"""
    return render_template('documentation/index.html')

@documentation_bp.route('/transaction_system_explained', methods=['GET'])
def transaction_system_pdf():
    """Generate a PDF explaining the transaction system"""
    try:
        # Get the HTML content
        html_path = os.path.join(current_app.root_path, 'static/docs/transaction_settlement_explainer.html')
        
        # Create PDF using WeasyPrint
        pdf = weasyprint.HTML(filename=html_path).write_pdf()
        
        # Create a BytesIO object
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        # Send the PDF as a response
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_Transaction_System_Explained.pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        return "An error occurred while generating the PDF. Please try again later.", 500
        
@documentation_bp.route('/server_to_server_guide', methods=['GET'])
def server_to_server_pdf():
    """Generate a PDF of the Server-to-Server Integration Guide"""
    try:
        # Get the HTML content
        html_path = os.path.join(current_app.root_path, 'static/docs/server_to_server_integration_guide.html')
        
        # Create PDF using WeasyPrint
        pdf = weasyprint.HTML(filename=html_path).write_pdf()
        
        # Create a BytesIO object
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        # Send the PDF as a response
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_Server_to_Server_Integration_Guide.pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        return "An error occurred while generating the PDF. Please try again later.", 500
        
@documentation_bp.route('/nvct_tokenomics', methods=['GET'])
def nvct_pdf():
    """Generate a PDF of the NVC Tokenomics document"""
    try:
        # Get the HTML content
        html_path = os.path.join(current_app.root_path, 'static/docs/NVCTokenomics.html')
        
        # Create PDF using WeasyPrint
        pdf = weasyprint.HTML(filename=html_path).write_pdf()
        
        # Create a BytesIO object
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        # Send the PDF as a response
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_Tokenomics.pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        return "An error occurred while generating the PDF. Please try again later.", 500
        
@documentation_bp.route('/funds_transfer_guide', methods=['GET'])
def funds_transfer_pdf():
    """Generate a PDF of the Funds Transfer Guide"""
    try:
        # Get the HTML content
        html_path = os.path.join(current_app.root_path, 'static/docs/nvc_funds_transfer_guide.html')
        
        # Create PDF using WeasyPrint
        pdf = weasyprint.HTML(filename=html_path).write_pdf()
        
        # Create a BytesIO object
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        # Send the PDF as a response
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_Funds_Transfer_Guide.pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        return "An error occurred while generating the PDF. Please try again later.", 500
        
@documentation_bp.route('/mainnet_readiness', methods=['GET'])
def mainnet_pdf():
    """Generate a PDF of the Mainnet Readiness Assessment"""
    try:
        # Get the HTML content
        html_path = os.path.join(current_app.root_path, 'static/docs/nvc_mainnet_readiness_assessment.html')
        
        # Create PDF using WeasyPrint
        pdf = weasyprint.HTML(filename=html_path).write_pdf()
        
        # Create a BytesIO object
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        # Send the PDF as a response
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_Mainnet_Readiness_Assessment.pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        return "An error occurred while generating the PDF. Please try again later.", 500