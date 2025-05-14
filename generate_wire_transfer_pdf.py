import os
import tempfile
from datetime import datetime
from flask import current_app, render_template
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from models import WireTransfer, WireTransferStatus

def generate_wire_transfer_pdf(wire_transfer_id):
    """
    Generate a PDF receipt for a wire transfer
    
    Args:
        wire_transfer_id (int): The ID of the wire transfer
        
    Returns:
        tuple: (pdf_bytes, filename) or (None, error_message)
    """
    try:
        # Get the wire transfer
        wire_transfer = WireTransfer.query.get(wire_transfer_id)
        if not wire_transfer:
            return None, "Wire transfer not found"
        
        # Format date
        formatted_date = wire_transfer.created_at.strftime('%Y-%m-%d %H:%M:%S')
        
        # Get status badge class
        status_class = "badge-warning"
        if wire_transfer.status == WireTransferStatus.COMPLETED:
            status_class = "badge-success"
        elif wire_transfer.status == WireTransferStatus.PROCESSING:
            status_class = "badge-primary"
        elif wire_transfer.status == WireTransferStatus.CANCELLED:
            status_class = "badge-secondary"
        elif wire_transfer.status == WireTransferStatus.FAILED:
            status_class = "badge-danger"
        
        # Render template with wire_transfer data
        html_content = render_template(
            'pdf/wire_transfer_receipt.html',
            wire_transfer=wire_transfer,
            formatted_date=formatted_date,
            status_class=status_class,
            generation_date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
            temp_html.write(html_content.encode('utf-8'))
            temp_html_path = temp_html.name
        
        try:
            # Configure fonts
            font_config = FontConfiguration()
            
            # Generate PDF
            css = CSS(string='''
                @page {
                    size: letter portrait;
                    margin: 1cm;
                    @bottom-right {
                        content: "Page " counter(page) " of " counter(pages);
                    }
                }
                body {
                    font-family: Arial, sans-serif;
                }
                .header {
                    text-align: center;
                    margin-bottom: 20px;
                }
                .logo {
                    max-width: 200px;
                    margin-bottom: 10px;
                }
                .title {
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                .subtitle {
                    font-size: 16px;
                    color: #555;
                    margin-bottom: 20px;
                }
                .section {
                    margin-bottom: 20px;
                    padding: 15px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }
                .section-title {
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 10px;
                    padding-bottom: 5px;
                    border-bottom: 1px solid #eee;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th, td {
                    padding: 8px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }
                th {
                    font-weight: bold;
                    width: 40%;
                }
                .footer {
                    margin-top: 30px;
                    text-align: center;
                    font-size: 12px;
                    color: #777;
                }
                .badge {
                    display: inline-block;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                    color: white;
                }
                .badge-success {
                    background-color: #28a745;
                }
                .badge-warning {
                    background-color: #ffc107;
                    color: #212529;
                }
                .badge-danger {
                    background-color: #dc3545;
                }
                .badge-primary {
                    background-color: #007bff;
                }
                .badge-secondary {
                    background-color: #6c757d;
                }
                .watermark {
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%) rotate(-45deg);
                    font-size: 100px;
                    color: rgba(200, 200, 200, 0.2);
                    z-index: -1;
                }
            ''', font_config=font_config)
            
            html = HTML(filename=temp_html_path)
            pdf_bytes = html.write_pdf(stylesheets=[css], font_config=font_config)
            
            # Generate filename
            filename = f"Wire_Transfer_{wire_transfer.reference_number}.pdf"
            
            return pdf_bytes, filename
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_html_path):
                os.unlink(temp_html_path)
                
    except Exception as e:
        current_app.logger.error(f"Error generating wire transfer PDF: {str(e)}")
        return None, f"Error generating PDF: {str(e)}"