import os
import base64
from flask import Blueprint, render_template, send_file, current_app
import weasyprint
from io import BytesIO

documentation_bp = Blueprint('documentation', __name__)

def generate_pdf_with_logo(html_content, base_url=None):
    """
    Generate a PDF from HTML content with page numbers
    
    Args:
        html_content (str): The HTML content to convert to PDF
        base_url (str): The base URL for resolving relative links
        
    Returns:
        bytes: The PDF content
    """
    # Add page number CSS
    page_number_css = """
    @page {
        @bottom-right {
            content: "Page " counter(page) " of " counter(pages);
            font-family: Arial, sans-serif;
            font-size: 10pt;
            color: #666;
        }
    }
    """
    
    # Create an HTML string with the page number CSS
    html_with_page_numbers = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            {page_number_css}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Generate PDF
    pdf = weasyprint.HTML(string=html_with_page_numbers, base_url=base_url).write_pdf()
    return pdf

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
        
        # Generate PDF with page numbers
        pdf = generate_pdf_with_logo(html_content, base_url=os.path.dirname(html_path))
        
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
        
        # Generate PDF with page numbers
        pdf = generate_pdf_with_logo(html_content, base_url=os.path.dirname(html_path))
        
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
        
        # Generate PDF with page numbers
        pdf = generate_pdf_with_logo(html_content, base_url=os.path.dirname(html_path))
        
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
        
        # Generate PDF with page numbers
        pdf = generate_pdf_with_logo(html_content, base_url=os.path.dirname(html_path))
        
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
        
        # Generate PDF with page numbers
        pdf = generate_pdf_with_logo(html_content, base_url=os.path.dirname(html_path))
        
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

@documentation_bp.route('/transfer_capabilities', methods=['GET'])
def transfer_capabilities_pdf():
    """Generate a PDF of the NVC Transfer Capabilities document"""
    try:
        # Get the HTML content
        html_path = os.path.join(current_app.root_path, 'static/docs/nvc_transfer_capabilities.html')
        
        # Read the HTML content
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Generate PDF with page numbers
        pdf = generate_pdf_with_logo(html_content, base_url=os.path.dirname(html_path))
        
        # Create a BytesIO object
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        # Send the PDF as a response
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_Transfer_Capabilities_Assessment.pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        return "An error occurred while generating the PDF. Please try again later.", 500

@documentation_bp.route('/paypal_capabilities', methods=['GET'])
def paypal_capabilities_pdf():
    """Generate a PDF of the PayPal Payment Capabilities document"""
    try:
        # Get the HTML content
        html_path = os.path.join(current_app.root_path, 'static/docs/paypal_payment_capabilities.html')
        
        # Read the HTML content
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Generate PDF with page numbers
        pdf = generate_pdf_with_logo(html_content, base_url=os.path.dirname(html_path))
        
        # Create a BytesIO object
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        # Send the PDF as a response
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_PayPal_Payment_Capabilities.pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        return "An error occurred while generating the PDF. Please try again later.", 500
        
@documentation_bp.route('/ach_capabilities', methods=['GET'])
def ach_capabilities_pdf():
    """Generate a PDF of the ACH Transfer Capabilities document"""
    try:
        # Get the HTML content
        html_path = os.path.join(current_app.root_path, 'static/docs/ach_capabilities.html')
        
        # Read the HTML content
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Generate PDF with page numbers
        pdf = generate_pdf_with_logo(html_content, base_url=os.path.dirname(html_path))
        
        # Create a BytesIO object
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        # Send the PDF as a response
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_ACH_Transfer_Capabilities.pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        return "An error occurred while generating the PDF. Please try again later.", 500
        
@documentation_bp.route('/swift_telex_capabilities', methods=['GET'])
def swift_telex_capabilities_pdf():
    """Generate a PDF of the SWIFT & Telex Messaging Capabilities document"""
    try:
        # Get the HTML content from the templates directory
        html_path = os.path.join(current_app.root_path, 'templates/pdf/swift_telex_capabilities.html')
        
        # Read the HTML content
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Generate PDF with page numbers
        pdf = generate_pdf_with_logo(html_content, base_url=os.path.dirname(html_path))
        
        # Create a BytesIO object
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        # Send the PDF as a response
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_SWIFT_Telex_Capabilities.pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        return "An error occurred while generating the PDF. Please try again later.", 500
        
@documentation_bp.route('/swift_bic_registration', methods=['GET'])
def swift_bic_registration_pdf():
    """Generate a PDF of the SWIFT BIC Registration Guide"""
    try:
        # Get the HTML content
        html_path = os.path.join(current_app.root_path, 'static/docs/swift_bic_registration_guide.html')
        
        # Read the HTML content
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Generate PDF with page numbers
        pdf = generate_pdf_with_logo(html_content, base_url=os.path.dirname(html_path))
        
        # Create a BytesIO object
        pdf_io = BytesIO(pdf)
        pdf_io.seek(0)
        
        # Send the PDF as a response
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='NVC_SWIFT_BIC_Registration_Guide.pdf'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        return "An error occurred while generating the PDF. Please try again later.", 500