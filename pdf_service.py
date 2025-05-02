"""
PDF Generation Service for NVC Banking Platform

This module provides functionality to generate PDF documents for various
transaction types, receipts, and financial documents.
"""
import io
import os
import logging
import tempfile
from datetime import datetime

from flask import render_template_string

logger = logging.getLogger(__name__)

# HTML template for transaction receipts
TRANSACTION_RECEIPT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        @page {
            size: letter portrait;
            margin: 2cm;
            @top-center {
                content: "{{ header }}";
                font-size: 10pt;
                color: #666;
            }
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10pt;
                color: #666;
            }
            @bottom-left {
                content: "Generated: {{ generation_date }}";
                font-size: 8pt;
                color: #999;
            }
            @bottom-right {
                content: "NVC Global Banking Platform";
                font-size: 8pt;
                color: #999;
            }
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 12pt;
            line-height: 1.5;
            color: #333;
        }
        .document {
            padding: 10px;
        }
        .header {
            border-bottom: 1px solid #ddd;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .document-title {
            font-size: 24pt;
            font-weight: bold;
            color: #1a4f8a;
            margin-bottom: 5px;
        }
        .document-subtitle {
            font-size: 14pt;
            color: #666;
            margin-bottom: 20px;
        }
        .logo {
            float: right;
            height: 70px;
            width: auto;
        }
        .transaction-info {
            margin-bottom: 30px;
        }
        .section-title {
            font-size: 14pt;
            font-weight: bold;
            color: #1a4f8a;
            margin-top: 20px;
            margin-bottom: 10px;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }
        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        .info-table th {
            text-align: left;
            padding: 8px;
            background-color: #f5f5f5;
            border-bottom: 1px solid #ddd;
            font-weight: bold;
            width: 30%;
        }
        .info-table td {
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }
        .amount {
            font-weight: bold;
            font-size: 14pt;
            color: #2a6e38;
        }
        .transaction-status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 10pt;
        }
        .status-pending {
            background-color: #fff3cd;
            color: #856404;
        }
        .status-completed {
            background-color: #d4edda;
            color: #155724;
        }
        .status-failed {
            background-color: #f8d7da;
            color: #721c24;
        }
        .status-cancelled {
            background-color: #e2e3e5;
            color: #383d41;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 10pt;
            color: #666;
        }
        .disclaimer {
            font-size: 9pt;
            color: #999;
            margin-top: 10px;
        }
        .barcode {
            margin-top: 30px;
            text-align: center;
        }
        .address {
            white-space: pre-line;
        }
    </style>
</head>
<body>
    <div class="document">
        <div class="header">
            <!-- <img src="logo.png" alt="NVC Global Banking" class="logo"> -->
            <div class="document-title">{{ title }}</div>
            <div class="document-subtitle">{{ subtitle }}</div>
        </div>
        
        <div class="transaction-info">
            <div class="section-title">Transaction Details</div>
            <table class="info-table">
                <tr>
                    <th>Transaction ID</th>
                    <td>{{ transaction.transaction_id }}</td>
                </tr>
                <tr>
                    <th>Amount</th>
                    <td class="amount">{{ transaction.currency }} {{ "%.2f"|format(transaction.amount) }}</td>
                </tr>
                <tr>
                    <th>Status</th>
                    <td>
                        <span class="transaction-status status-{{ transaction.status.lower() }}">
                            {{ transaction.status }}
                        </span>
                    </td>
                </tr>
                <tr>
                    <th>Date</th>
                    <td>{{ transaction.date }}</td>
                </tr>
                <tr>
                    <th>Description</th>
                    <td>{{ transaction.description }}</td>
                </tr>
                {% if transaction.reference %}
                <tr>
                    <th>Reference</th>
                    <td>{{ transaction.reference }}</td>
                </tr>
                {% endif %}
                {% if transaction.entry_class_code %}
                <tr>
                    <th>Entry Class</th>
                    <td>{{ transaction.entry_class_code }}</td>
                </tr>
                {% endif %}
                {% if transaction.effective_date %}
                <tr>
                    <th>Effective Date</th>
                    <td>{{ transaction.effective_date }}</td>
                </tr>
                {% endif %}
            </table>
        </div>
        
        <div class="sender-info">
            <div class="section-title">Sender Information</div>
            <table class="info-table">
                <tr>
                    <th>Sender</th>
                    <td>{{ transaction.sender_name }}</td>
                </tr>
                {% if transaction.sender_account_type %}
                <tr>
                    <th>Account Type</th>
                    <td>{{ transaction.sender_account_type }}</td>
                </tr>
                {% endif %}
            </table>
        </div>
        
        <div class="recipient-info">
            <div class="section-title">Recipient Information</div>
            <table class="info-table">
                <tr>
                    <th>Recipient</th>
                    <td>{{ transaction.recipient_name }}</td>
                </tr>
                {% if transaction.recipient_address %}
                <tr>
                    <th>Address</th>
                    <td class="address">{{ transaction.recipient_address }}</td>
                </tr>
                {% endif %}
                {% if transaction.recipient_account_type %}
                <tr>
                    <th>Account Type</th>
                    <td>{{ transaction.recipient_account_type }}</td>
                </tr>
                {% endif %}
                {% if transaction.recipient_account %}
                <tr>
                    <th>Account Number</th>
                    <td>{{ transaction.recipient_account_masked }}</td>
                </tr>
                {% endif %}
            </table>
        </div>
        
        {% if show_bank_info %}
        <div class="bank-info">
            <div class="section-title">Bank Information</div>
            <table class="info-table">
                {% if transaction.recipient_bank_name %}
                <tr>
                    <th>Bank Name</th>
                    <td>{{ transaction.recipient_bank_name }}</td>
                </tr>
                {% endif %}
                {% if transaction.recipient_bank_address %}
                <tr>
                    <th>Bank Address</th>
                    <td class="address">{{ transaction.recipient_bank_address }}</td>
                </tr>
                {% endif %}
                {% if transaction.recipient_routing_number %}
                <tr>
                    <th>Routing Number</th>
                    <td>{{ transaction.recipient_routing_number }}</td>
                </tr>
                {% endif %}
            </table>
        </div>
        {% endif %}
        
        <div class="footer">
            <p>This document serves as an official receipt for the transaction detailed above.</p>
            <p class="disclaimer">
                This is a computer-generated document and does not require a signature.
                For questions or concerns regarding this transaction, please contact customer support
                with the transaction ID referenced above.
            </p>
        </div>
        
        <!-- Optional Barcode -->
        <!--
        <div class="barcode">
            <img src="barcode.png" alt="Transaction Barcode">
        </div>
        -->
    </div>
</body>
</html>
"""


class PDFService:
    """Service for generating PDF documents"""
    
    @staticmethod
    def render_transaction_html(transaction, transaction_type="Transaction", metadata=None):
        """
        Render an HTML receipt for a transaction
        
        Args:
            transaction: Transaction object or dictionary with transaction data
            transaction_type (str): Type of transaction for the PDF title
            metadata (dict): Additional metadata for the transaction
            
        Returns:
            str: HTML content
        """
        try:
            # Check if transaction is a dictionary or an object
            if not isinstance(transaction, dict):
                # Create a dictionary from transaction object attributes
                transaction_dict = {
                    "transaction_id": transaction.transaction_id,
                    "amount": transaction.amount,
                    "currency": transaction.currency,
                    "status": transaction.status.value if hasattr(transaction.status, "value") else transaction.status,
                    "date": transaction.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(transaction, "created_at") else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "description": transaction.description,
                    "recipient_name": transaction.recipient_name,
                    "recipient_account": transaction.recipient_account
                }
                
                # Handle metadata from transaction object
                if hasattr(transaction, "tx_metadata_json") and transaction.tx_metadata_json:
                    import json
                    try:
                        tx_metadata = json.loads(transaction.tx_metadata_json)
                        transaction_dict.update(tx_metadata)
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse transaction metadata for {transaction.transaction_id}")
            else:
                transaction_dict = transaction
            
            # Add additional metadata if provided
            if metadata:
                transaction_dict.update(metadata)
            
            # Process recipient account masking for security
            if transaction_dict.get("recipient_account"):
                account = str(transaction_dict["recipient_account"])
                if len(account) > 8:
                    masked = "•" * (len(account) - 4) + account[-4:]
                else:
                    masked = "•" * (len(account) - 2) + account[-2:]
                transaction_dict["recipient_account_masked"] = masked
            
            # Format recipient address if components exist
            address_parts = []
            if transaction_dict.get("recipient_address_line1"):
                address_parts.append(transaction_dict["recipient_address_line1"])
            if transaction_dict.get("recipient_address_line2"):
                address_parts.append(transaction_dict["recipient_address_line2"])
            
            city_state_zip = []
            if transaction_dict.get("recipient_city"):
                city_state_zip.append(transaction_dict["recipient_city"])
            if transaction_dict.get("recipient_state"):
                if city_state_zip:
                    city_state_zip[-1] += f", {transaction_dict['recipient_state']}"
                else:
                    city_state_zip.append(transaction_dict["recipient_state"])
            if transaction_dict.get("recipient_zip"):
                if city_state_zip:
                    city_state_zip[-1] += f" {transaction_dict['recipient_zip']}"
                else:
                    city_state_zip.append(transaction_dict["recipient_zip"])
            
            if city_state_zip:
                address_parts.append(" ".join(city_state_zip))
            
            if address_parts:
                transaction_dict["recipient_address"] = "\n".join(address_parts)
            
            # Determine sender name
            if not transaction_dict.get("sender_name"):
                transaction_dict["sender_name"] = "NVC Banking Customer"
            
            # Set up rendering context
            context = {
                "title": f"{transaction_type} Receipt",
                "subtitle": f"Transaction Details for {transaction_dict.get('transaction_type', transaction_type)}",
                "header": "OFFICIAL TRANSACTION RECEIPT",
                "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "transaction": transaction_dict,
                "show_bank_info": any([
                    transaction_dict.get("recipient_bank_name"),
                    transaction_dict.get("recipient_bank_address"),
                    transaction_dict.get("recipient_routing_number")
                ])
            }
            
            # Render template to HTML
            html_content = render_template_string(TRANSACTION_RECEIPT_TEMPLATE, **context)
            return html_content
            
        except Exception as e:
            logger.error(f"Error rendering transaction HTML: {str(e)}")
            raise
    
    @staticmethod
    def generate_transaction_pdf(transaction, transaction_type="Transaction", metadata=None):
        """
        Generate a PDF receipt for a transaction
        
        Args:
            transaction: Transaction object or dictionary with transaction data
            transaction_type (str): Type of transaction for the PDF title
            metadata (dict): Additional metadata for the transaction
            
        Returns:
            bytes: PDF document as bytes
        """
        try:
            # Render HTML template
            html_content = PDFService.render_transaction_html(transaction, transaction_type, metadata)
            
            # Try using pdfkit to generate PDF
            try:
                import pdfkit
                pdf_data = pdfkit.from_string(html_content, False)
                return pdf_data
            except ImportError:
                logger.warning("pdfkit not available, trying alternative method...")
            except Exception as e:
                logger.warning(f"pdfkit error: {str(e)}, trying alternative method...")
            
            # Save HTML to a temporary file and try wkhtmltopdf directly
            try:
                import tempfile
                import subprocess
                
                with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
                    temp_html.write(html_content.encode('utf-8'))
                    temp_html_path = temp_html.name
                
                output_pdf_path = temp_html_path.replace('.html', '.pdf')
                
                # Try to call wkhtmltopdf directly
                subprocess.run(["wkhtmltopdf", temp_html_path, output_pdf_path], check=True)
                
                with open(output_pdf_path, 'rb') as pdf_file:
                    pdf_data = pdf_file.read()
                
                # Clean up temporary files
                try:
                    os.unlink(temp_html_path)
                    os.unlink(output_pdf_path)
                except:
                    pass
                
                return pdf_data
            except Exception as e:
                logger.warning(f"wkhtmltopdf error: {str(e)}, falling back to text...")
                
                # Final fallback: just return the HTML as bytes
                return html_content.encode('utf-8')
            
        except Exception as e:
            logger.error(f"Error generating transaction PDF: {str(e)}")
            raise
    
    @staticmethod
    def generate_ach_transaction_pdf(transaction, metadata=None):
        """
        Generate a PDF receipt for an ACH transaction
        
        Args:
            transaction: ACH Transaction object
            metadata (dict): Additional metadata for the transaction
            
        Returns:
            bytes: PDF document as bytes
        """
        return PDFService.generate_transaction_pdf(
            transaction,
            transaction_type="ACH Transfer",
            metadata=metadata
        )
    
    @staticmethod
    def generate_swift_transaction_pdf(transaction, metadata=None):
        """
        Generate a PDF receipt for a SWIFT transaction
        
        Args:
            transaction: SWIFT Transaction object
            metadata (dict): Additional metadata for the transaction
            
        Returns:
            bytes: PDF document as bytes
        """
        return PDFService.generate_transaction_pdf(
            transaction,
            transaction_type="SWIFT Transfer",
            metadata=metadata
        )
    
    @staticmethod
    def save_pdf_to_file(pdf_data, filename):
        """
        Save PDF data to a file
        
        Args:
            pdf_data (bytes): PDF document as bytes
            filename (str): Path to save the PDF
            
        Returns:
            str: Path to the saved PDF file
        """
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
            
            with open(filename, 'wb') as f:
                f.write(pdf_data)
            
            return filename
        except Exception as e:
            logger.error(f"Error saving PDF to file: {str(e)}")
            raise


# Create a global instance
pdf_service = PDFService()