import os
import base64
from flask import Blueprint, render_template, send_file, current_app
import weasyprint
from io import BytesIO

documentation_bp = Blueprint('documentation', __name__)

def get_nvc_logo_data_url():
    """Get the NVC logo as a data URL for embedding in PDFs"""
    logo_path = os.path.join(current_app.root_path, 'static/images/nvc_logo_white.svg')
    try:
        with open(logo_path, 'rb') as f:
            logo_data = f.read()
            return f"data:image/svg+xml;base64,{base64.b64encode(logo_data).decode('utf-8')}"
    except Exception as e:
        current_app.logger.error(f"Error loading logo: {str(e)}")
        # Return a simple text as fallback
        return "NVC GLOBAL"

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
        
        # Read the HTML content
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Embed the logo in the HTML
        logo_data_url = get_nvc_logo_data_url()
        html_content = html_content.replace('NVC Logo', f'<img src="{logo_data_url}" alt="NVC Logo" style="width: 200px; height: auto; display: block; margin: 0 auto;">')
        
        # Create PDF using WeasyPrint with modified HTML content
        pdf = weasyprint.HTML(string=html_content, base_url=os.path.dirname(html_path)).write_pdf()
        
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
        
        # Read the HTML content
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Embed the logo in the HTML
        logo_data_url = get_nvc_logo_data_url()
        if "NVC Logo" in html_content:
            html_content = html_content.replace('NVC Logo', f'<img src="{logo_data_url}" alt="NVC Logo" style="width: 200px; height: auto; display: block; margin: 0 auto;">')
        
        # Create PDF using WeasyPrint with modified HTML content
        pdf = weasyprint.HTML(string=html_content, base_url=os.path.dirname(html_path)).write_pdf()
        
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
        
        # Read the HTML content
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Embed the logo in the HTML
        logo_data_url = get_nvc_logo_data_url()
        if "NVC Logo" in html_content:
            html_content = html_content.replace('NVC Logo', f'<img src="{logo_data_url}" alt="NVC Logo" style="width: 200px; height: auto; display: block; margin: 0 auto;">')
        
        # Create PDF using WeasyPrint with modified HTML content
        pdf = weasyprint.HTML(string=html_content, base_url=os.path.dirname(html_path)).write_pdf()
        
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
        
        # Read the HTML content
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Embed the logo in the HTML
        logo_data_url = get_nvc_logo_data_url()
        if "NVC Logo" in html_content:
            html_content = html_content.replace('NVC Logo', f'<img src="{logo_data_url}" alt="NVC Logo" style="width: 200px; height: auto; display: block; margin: 0 auto;">')
        
        # Create PDF using WeasyPrint with modified HTML content
        pdf = weasyprint.HTML(string=html_content, base_url=os.path.dirname(html_path)).write_pdf()
        
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
        
        # Read the HTML content
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Embed the logo in the HTML
        logo_data_url = get_nvc_logo_data_url()
        if "NVC Logo" in html_content:
            html_content = html_content.replace('NVC Logo', f'<img src="{logo_data_url}" alt="NVC Logo" style="width: 200px; height: auto; display: block; margin: 0 auto;">')
        
        # Create PDF using WeasyPrint with modified HTML content
        pdf = weasyprint.HTML(string=html_content, base_url=os.path.dirname(html_path)).write_pdf()
        
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