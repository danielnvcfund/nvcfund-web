"""
Transaction PDF Generator
This module handles the generation of PDF receipts for treasury transactions.
"""

import os
import tempfile
from datetime import datetime
from flask import current_app, render_template
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from models import Transaction, TransactionStatus, TreasuryTransaction

def generate_transaction_pdf(transaction_id):
    """
    Generate a PDF receipt for a treasury transaction
    
    Args:
        transaction_id (int): The ID of the transaction
        
    Returns:
        tuple: (pdf_bytes, filename) or (None, error_message)
    """
    try:
        # Get the transaction
        transaction = TreasuryTransaction.query.get(transaction_id)
        if not transaction:
            return None, "Transaction not found"
        
        # Format date
        formatted_date = transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')
        completed_date = transaction.completed_at.strftime('%Y-%m-%d %H:%M:%S') if transaction.completed_at else None
        
        # Get status badge class
        status_class = "badge-warning"
        if transaction.status == TransactionStatus.COMPLETED:
            status_class = "badge-success"
        elif transaction.status == TransactionStatus.REJECTED:
            status_class = "badge-danger"
        elif transaction.status == TransactionStatus.CANCELLED:
            status_class = "badge-secondary"
        elif transaction.status == TransactionStatus.PENDING:
            status_class = "badge-warning"
        
        # Render template with transaction data
        html_content = render_template(
            'pdf/transaction_receipt.html',
            transaction=transaction,
            formatted_date=formatted_date,
            completed_date=completed_date,
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
            filename = f"Transaction_{transaction.transaction_id}.pdf"
            
            return pdf_bytes, filename
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_html_path):
                os.unlink(temp_html_path)
                
    except Exception as e:
        current_app.logger.error(f"Error generating transaction PDF: {str(e)}")
        return None, f"Error generating PDF: {str(e)}"