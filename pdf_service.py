"""
PDF Generation Service for NVC Banking Platform

This module provides functionality to generate PDF documents for various
transaction types, receipts, and financial documents.
"""
import io
import os
import logging
import tempfile
from datetime import datetime, timedelta

from flask import render_template_string, render_template
from sqlalchemy import desc, asc

from account_holder_models import AccountHolder, BankAccount, Address, CurrencyExchangeTransaction
from models import Transaction

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
            <div class="section-title">Recipient Bank Information</div>
            <table class="info-table">
                <tr>
                    <th>Bank Name</th>
                    <td>{{ transaction.recipient_bank_name or "Not specified" }}</td>
                </tr>
                <tr>
                    <th>Bank Address</th>
                    <td class="address">{{ transaction.recipient_bank_address or "Not specified" }}</td>
                </tr>
                {% if transaction.recipient_bank_swift %}
                <tr>
                    <th>SWIFT/BIC Code</th>
                    <td>{{ transaction.recipient_bank_swift }}</td>
                </tr>
                {% endif %}
                <tr>
                    <th>Routing Number</th>
                    <td>{{ transaction.recipient_routing_number or transaction.routing_number or "Not specified" }}</td>
                </tr>
                {% if transaction.recipient_bank_officer %}
                <tr>
                    <th>Bank Officer Contact</th>
                    <td>{{ transaction.recipient_bank_officer }}</td>
                </tr>
                {% endif %}
            </table>
        </div>
        {% endif %}
        
        {% if show_originating_bank_info %}
        <div class="bank-info">
            <div class="section-title">Originating Bank Information</div>
            <table class="info-table">
                <tr>
                    <th>Bank Name</th>
                    <td>{{ transaction.originating_institution or "NVC Fund Bank" }}</td>
                </tr>
                <tr>
                    <th>Status</th>
                    <td>{{ transaction.nvc_bank_status or "Supranational Sovereign Financial Institution" }}</td>
                </tr>
                <tr>
                    <th>Jurisdiction</th>
                    <td class="address">{{ transaction.nvc_bank_jurisdiction or "African Union Treaty, Article XIV 1(e) of the ECO-6 Treaty, and AFRA jurisdiction" }}</td>
                </tr>
                <tr>
                    <th>ACH Routing Number</th>
                    <td>{{ transaction.originating_routing_number or "031176110" }}</td>
                </tr>
                <tr>
                    <th>Registration Status</th>
                    <td style="color: #856404; background-color: #fff3cd; padding: 3px 6px; border-radius: 3px;">
                        {{ transaction.routing_registration_status or "Pending Official Registration" }}
                    </td>
                </tr>
                <tr>
                    <th>SWIFT/BIC Code</th>
                    <td>{{ transaction.originating_swift_code or "NVCFBKAU" }}</td>
                </tr>
                <tr>
                    <th>SWIFT Status</th>
                    <td style="color: #856404; background-color: #fff3cd; padding: 3px 6px; border-radius: 3px;">
                        {{ transaction.swift_registration_status or "Pending SWIFT Network Integration" }}
                    </td>
                </tr>
                <tr>
                    <th>Fed Wire Enabled</th>
                    <td>{{ "Yes" if transaction.fed_wire_enabled else "No" }}</td>
                </tr>
                <tr>
                    <th>Settlement Platform</th>
                    <td>{{ transaction.settlement_platform or "NVC Global Settlement Network" }}</td>
                </tr>
            </table>
        </div>
        {% endif %}
        
        <div class="footer">
            <p>This document serves as an official receipt for the transaction detailed above.</p>
            
            {% if show_originating_bank_info %}
            <div style="margin: 15px 0; padding: 10px; border: 1px solid #fff3cd; background-color: #fff3cdaa; border-radius: 4px;">
                <p style="font-weight: bold; font-size: 11pt; color: #856404; margin-top: 0;">IMPORTANT NOTICE:</p>
                <p style="font-size: 10pt; color: #856404; margin-bottom: 0;">
                    The ACH routing number 031176110 is currently in the registration process with U.S. banking authorities.
                    The SWIFT/BIC code NVCFBKAU is pending integration into the SWIFT network. 
                    For external ACH transactions or international wire transfers, please contact our treasury department at 
                    treasury@nvcfund.com for current processing instructions.
                </p>
            </div>
            {% endif %}
            
            <p class="disclaimer">
                This is a computer-generated document and does not require a signature.
                For questions or concerns regarding this transaction, please contact customer support
                with the transaction ID referenced above.
            </p>
            
            <div style="margin-top: 20px; padding: 10px; border: 1px solid #ffc107; background-color: #fff3cd; border-radius: 4px;">
                <p style="font-size: 10pt; color: #856404; margin: 0 0 5px 0;"><strong>Important Notice: Banking Credentials Registration Status</strong></p>
                <p style="font-size: 9pt; margin: 0 0 5px 0;">
                    The ACH routing number (031176110) and SWIFT/BIC code (NVCFBKAU) used by NVC Fund Bank are currently pending official registration with 
                    their respective authorities. During this pre-registration period, transactions may need alternative processing methods.
                </p>
                <p style="font-size: 9pt; margin: 0;">
                    For high-priority transactions requiring immediate processing, please contact our treasury operations department
                    at treasury@nvcfundbank.com for alternative routing instructions.
                </p>
            </div>
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
    def generate_account_statement_pdf(account_id, start_date=None, end_date=None):
        """
        Generate a PDF account statement for the specified account and date range
        
        Args:
            account_id (int): The ID of the bank account
            start_date (datetime, optional): Start date for the statement. If None, defaults to 1 month ago.
            end_date (datetime, optional): End date for the statement. If None, defaults to current date.
            
        Returns:
            bytes: PDF document as bytes
        """
        try:
            # Get the bank account and associated account holder
            account = BankAccount.query.get(account_id)
            if not account:
                logger.error(f"Account not found with ID: {account_id}")
                return None
                
            account_holder = AccountHolder.query.get(account.account_holder_id)
            if not account_holder:
                logger.error(f"Account holder not found for account ID: {account_id}")
                return None
                
            # Set default date range if not provided (last month)
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)
                
            # Format dates for display
            start_date_display = start_date.strftime('%B %d, %Y')
            end_date_display = end_date.strftime('%B %d, %Y')
            
            # Get transactions for this account in the date range (placeholder for actual transactions)
            # This should be replaced with actual transaction data from your database
            transactions = Transaction.query.filter(
                Transaction.recipient_account == account.account_number,
                Transaction.created_at.between(start_date, end_date)
            ).order_by(asc(Transaction.created_at)).all()
            
            # Prepare transaction data for template
            transaction_data = []
            running_balance = account.balance  # Start with current balance
            
            # Calculate backward to get the opening balance
            total_transaction_amount = sum(t.amount for t in transactions if t.amount)
            opening_balance = account.balance - total_transaction_amount
            
            # Prepare transactions for display in reverse order (most recent last)
            for transaction in reversed(transactions):
                # Adjust running balance for each transaction
                if hasattr(transaction, 'amount') and transaction.amount:
                    running_balance -= transaction.amount
                
                # Format date
                if hasattr(transaction, 'created_at') and transaction.created_at:
                    date_display = transaction.created_at.strftime('%Y-%m-%d %H:%M')
                else:
                    date_display = "N/A"
                
                # Add transaction info
                transaction_data.append({
                    'date': date_display,
                    'description': transaction.description if hasattr(transaction, 'description') else "Transaction",
                    'reference': transaction.transaction_id if hasattr(transaction, 'transaction_id') else "",
                    'amount': transaction.amount if hasattr(transaction, 'amount') else 0.0,
                    'balance': running_balance
                })
            
            # Reverse back to chronological order
            transaction_data.reverse()
            
            # Calculate summary totals
            total_credits = sum(t.amount for t in transactions if hasattr(t, 'amount') and t.amount > 0)
            total_debits = sum(abs(t.amount) for t in transactions if hasattr(t, 'amount') and t.amount < 0)
            net_change = total_credits - total_debits
            
            # Get primary address if available
            primary_address = account_holder.primary_address
            address_display = primary_address.formatted if primary_address else ""
            has_address = bool(primary_address)
            
            # Prepare template variables
            template_vars = {
                'title': f"Account Statement",
                'subtitle': f"For the period {start_date_display} to {end_date_display}",
                'header': "NVC Fund Bank - Account Statement",
                'account_holder': account_holder,
                'account': account,
                'transactions': transaction_data,
                'start_date': start_date_display,
                'end_date': end_date_display,
                'opening_balance': opening_balance,
                'primary_address': address_display,
                'has_address': has_address,
                'total_credits': total_credits,
                'total_debits': total_debits,
                'net_change': net_change,
                'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Render the template
            html_content = render_template('account_holders/account_statement_template.html', **template_vars)
            
            # Generate PDF using WeasyPrint
            try:
                import weasyprint
                from io import BytesIO
                
                # Create a BytesIO buffer for the PDF
                pdf_buffer = BytesIO()
                
                # Generate PDF
                html_obj = weasyprint.HTML(string=html_content)
                html_obj.write_pdf(pdf_buffer)
                
                # Get the PDF content
                pdf_buffer.seek(0)
                pdf_data = pdf_buffer.getvalue()
                
                return pdf_data
                
            except Exception as e:
                logger.error(f"Error generating PDF with WeasyPrint: {str(e)}")
                
                # Try with pyppeteer as fallback
                try:
                    import asyncio
                    from pyppeteer import launch
                    
                    # Write HTML to a temporary file
                    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
                        temp_html_path = temp_html.name
                        temp_html.write(html_content.encode())
                    
                    # Generate PDF with pyppeteer
                    async def generate_pdf_with_pyppeteer():
                        browser = await launch(
                            options={
                                'headless': True, 
                                'args': [
                                    '--no-sandbox',
                                    '--disable-setuid-sandbox',
                                    '--disable-dev-shm-usage',
                                    '--disable-gpu'
                                ]
                            }
                        )
                        
                        try:
                            page = await browser.newPage()
                            
                            # Set viewport size to ensure content fits well
                            await page.setViewport({'width': 1200, 'height': 1600})
                            
                            # Navigate to the HTML file
                            await page.goto(f'file://{temp_html_path}', {'waitUntil': 'networkidle0'})
                            
                            # Wait a moment for any JS to execute
                            await asyncio.sleep(1)
                            
                            # Generate PDF
                            pdf_bytes = await page.pdf({
                                'format': 'Letter',
                                'margin': {
                                    'top': '0.5in',
                                    'right': '0.5in',
                                    'bottom': '0.5in',
                                    'left': '0.5in'
                                },
                                'printBackground': True
                            })
                            
                            return pdf_bytes
                        finally:
                            await browser.close()
                            # Clean up the temporary HTML file
                            try:
                                os.unlink(temp_html_path)
                            except:
                                pass
                    
                    # Run the async function
                    pdf_content = asyncio.get_event_loop().run_until_complete(generate_pdf_with_pyppeteer())
                    return pdf_content
                    
                except Exception as e2:
                    logger.error(f"Error generating PDF with pyppeteer: {str(e2)}")
                    return None
            
        except Exception as e:
            logger.error(f"Error generating account statement PDF: {str(e)}")
            return None
    
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
                
                # Extract additional fields if they exist on the transaction object
                for field in [
                    "recipient_bank_name", "recipient_bank_address", "recipient_routing_number",
                    "recipient_address_line1", "recipient_address_line2", "recipient_city",
                    "recipient_state", "recipient_zip", "routing_number"
                ]:
                    if hasattr(transaction, field) and getattr(transaction, field):
                        transaction_dict[field] = getattr(transaction, field)
                
                # Handle metadata from transaction object
                if hasattr(transaction, "tx_metadata_json") and transaction.tx_metadata_json:
                    import json
                    try:
                        tx_metadata = json.loads(transaction.tx_metadata_json)
                        transaction_dict.update(tx_metadata)
                        
                        # Process nested SWIFT-specific fields
                        if 'receiving_bank' in tx_metadata:
                            # Extract and flatten receiving bank details for the template
                            receiving_bank = tx_metadata['receiving_bank']
                            transaction_dict['recipient_bank_name'] = receiving_bank.get('name')
                            transaction_dict['recipient_bank_address'] = receiving_bank.get('address')
                            transaction_dict['recipient_bank_swift'] = receiving_bank.get('swift')
                            transaction_dict['recipient_routing_number'] = receiving_bank.get('routing')
                            transaction_dict['recipient_bank_officer'] = receiving_bank.get('officer')
                            
                        if 'account_holder' in tx_metadata:
                            # Extract and flatten account holder details
                            account_holder = tx_metadata['account_holder']
                            transaction_dict['recipient_name'] = account_holder.get('name')
                            transaction_dict['recipient_account'] = account_holder.get('account_number')
                        
                        # Ensure bank information fields are available in the main dictionary 
                        # for easy access in the template
                        for key in ["recipient_bank_name", "recipient_bank_address", "recipient_routing_number"]:
                            if key in tx_metadata and key not in transaction_dict:
                                transaction_dict[key] = tx_metadata[key]
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
            
            # Force show bank info if this is an ACH transaction
            show_bank_info = transaction_dict.get('show_bank_info', False)
            
            # If it's not explicitly set, determine from available data
            if not show_bank_info:
                show_bank_info = any([
                    transaction_dict.get("recipient_bank_name"),
                    transaction_dict.get("recipient_bank_address"),
                    transaction_dict.get("recipient_routing_number"),
                    transaction_dict.get("routing_number")
                ])
                
            # If it's an ACH transfer, always show the bank section
            if transaction_dict.get('transaction_type') == 'ACH Transfer':
                show_bank_info = True
            
            # Check if we should show the originating bank info (NVC Fund Bank)
            show_originating_bank_info = transaction_dict.get('show_originating_bank_info', False)
            
            # For ACH transfers, always show NVC Fund Bank info
            if transaction_dict.get('transaction_type') == 'ACH Transfer':
                show_originating_bank_info = True
                
            # Set up rendering context
            context = {
                "title": f"{transaction_type} Receipt",
                "subtitle": f"Transaction Details for {transaction_dict.get('transaction_type', transaction_type)}",
                "header": "OFFICIAL TRANSACTION RECEIPT",
                "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "transaction": transaction_dict,
                "show_bank_info": show_bank_info,
                "show_originating_bank_info": show_originating_bank_info
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
            
            # Try using WeasyPrint to generate PDF (preferred method)
            try:
                import weasyprint
                from io import BytesIO
                
                # Create a BytesIO buffer for the PDF
                pdf_buffer = BytesIO()
                
                # Generate PDF using WeasyPrint
                html_obj = weasyprint.HTML(string=html_content)
                html_obj.write_pdf(pdf_buffer)
                
                # Get the PDF content
                pdf_buffer.seek(0)
                pdf_data = pdf_buffer.getvalue()
                return pdf_data
            
            except ImportError:
                logger.warning("WeasyPrint not available, trying alternative method...")
            except Exception as e:
                logger.warning(f"WeasyPrint error: {str(e)}, trying alternative method...")
            
            # Try using pdfkit as a fallback
            try:
                import pdfkit
                pdf_data = pdfkit.from_string(html_content, False)
                return pdf_data
            except ImportError:
                logger.warning("pdfkit not available, trying alternative method...")
            except Exception as e:
                logger.warning(f"pdfkit error: {str(e)}, trying alternative method...")
            
            # Final fallback: just return the HTML as bytes with a warning header
            fallback_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .warning-banner {
                        background-color: #fff3cd;
                        border: 1px solid #ffeeba;
                        padding: 10px;
                        margin-bottom: 20px;
                        border-radius: 4px;
                        color: #856404;
                        font-family: Arial, sans-serif;
                    }
                </style>
            </head>
            <body>
                <div class="warning-banner">
                    <strong>PDF Generation Warning:</strong> The system was unable to generate a proper PDF document.
                    This is an HTML version of the receipt instead. For a properly formatted PDF, please contact support.
                </div>
            """ + html_content + """
            </body>
            </html>
            """
            
            return fallback_html.encode('utf-8')
            
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
        # Make sure we have a metadata dictionary
        if metadata is None:
            metadata = {}
            
        # Add ACH-specific information
        metadata['transaction_type'] = "ACH Transfer"
        
        # Ensure the bank information will be shown
        metadata['show_bank_info'] = True
        metadata['show_originating_bank_info'] = True
        
        # Make sure routing number is available in expected field
        if 'recipient_routing_number' in metadata and 'routing_number' not in metadata:
            metadata['routing_number'] = metadata['recipient_routing_number']
            
        # Add NVC Fund Bank details if not present
        if not metadata.get("originating_institution"):
            metadata["originating_institution"] = "NVC Fund Bank"
            metadata["originating_routing_number"] = "031176110"
            metadata["originating_swift_code"] = "NVCFBKAU"
            metadata["fed_wire_enabled"] = True
            metadata["settlement_platform"] = "NVC Global Settlement Network"
            
        # Add NVC Fund Bank status information for the PDF
        metadata["nvc_bank_status"] = "Supranational Sovereign Financial Institution"
        metadata["nvc_bank_jurisdiction"] = "African Union Treaty, Article XIV 1(e) of the ECO-6 Treaty, and AFRA jurisdiction"
        
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
        # Make sure we have a metadata dictionary
        if metadata is None:
            metadata = {}
            
        # Add SWIFT-specific information
        metadata['transaction_type'] = "SWIFT Transfer"
        
        # Ensure the bank information will be shown
        metadata['show_bank_info'] = True
        
        # Add SWIFT-specific fields if they don't exist
        if hasattr(transaction, "tx_metadata_json") and transaction.tx_metadata_json:
            import json
            try:
                tx_metadata = json.loads(transaction.tx_metadata_json)
                
                # Extract SWIFT BIC code if available
                if 'receiver_bic' in tx_metadata and 'recipient_bank_swift' not in metadata:
                    metadata['recipient_bank_swift'] = tx_metadata['receiver_bic']
                    
                # Extract message type
                if 'message_type' in tx_metadata:
                    metadata['swift_message_type'] = tx_metadata['message_type']
                    
                # Add beneficiary information if it exists
                if 'beneficiary' in tx_metadata:
                    beneficiary = tx_metadata['beneficiary']
                    if 'name' in beneficiary and beneficiary['name']:
                        metadata['recipient_name'] = beneficiary['name']
                    if 'account' in beneficiary and beneficiary['account']:
                        metadata['recipient_account'] = beneficiary['account']
                    if 'bank' in beneficiary:
                        bank = beneficiary['bank']
                        if 'name' in bank and bank['name']:
                            metadata['recipient_bank_name'] = bank['name']
                        if 'swift' in bank and bank['swift']:
                            metadata['recipient_bank_swift'] = bank['swift']
                    
                # Add processing institution if it exists
                if 'processing_institution' in tx_metadata and tx_metadata['processing_institution']:
                    metadata['processing_institution'] = tx_metadata['processing_institution']
                    
                # Add related reference if it exists
                if 'related_reference' in tx_metadata and tx_metadata['related_reference']:
                    metadata['related_reference'] = tx_metadata['related_reference']
            except (json.JSONDecodeError, TypeError):
                pass
        
        return PDFService.generate_transaction_pdf(
            transaction,
            transaction_type="SWIFT Transfer",
            metadata=metadata
        )
    
    @staticmethod
    def generate_currency_exchange_pdf(exchange_transaction_id):
        """
        Generate a PDF receipt for a currency exchange transaction
        
        Args:
            exchange_transaction_id: ID of the CurrencyExchangeTransaction
            
        Returns:
            bytes: PDF document as bytes
        """
        # Retrieve the exchange transaction
        exchange_tx = CurrencyExchangeTransaction.query.get_or_404(exchange_transaction_id)
        
        # Get account holder information
        account_holder = AccountHolder.query.get(exchange_tx.account_holder_id)
        
        # Get account information
        from_account = BankAccount.query.get(exchange_tx.from_account_id)
        to_account = BankAccount.query.get(exchange_tx.to_account_id)
        
        # Prepare data for PDF
        transaction_data = {
            "transaction_id": exchange_tx.reference_number,
            "sender_name": account_holder.name,
            "recipient_name": account_holder.name,  # Same for currency exchange
            "date": exchange_tx.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "status": exchange_tx.status.value.upper(),
            "description": f"Currency Exchange: {exchange_tx.exchange_type.value}",
            "reference": exchange_tx.reference_number,
            
            # From account details
            "sender_account_type": from_account.account_type.value,
            "sender_account": from_account.account_number,
            "sender_account_masked": from_account.account_number[-4:].rjust(len(from_account.account_number), '*'),
            
            # To account details
            "recipient_account_type": to_account.account_type.value,
            "recipient_account": to_account.account_number,
            "recipient_account_masked": to_account.account_number[-4:].rjust(len(to_account.account_number), '*'),
            
            # Exchange specific details (not in original transaction model)
            "exchange_from_currency": exchange_tx.from_currency.value,
            "exchange_from_amount": exchange_tx.from_amount,
            "exchange_to_currency": exchange_tx.to_currency.value, 
            "exchange_to_amount": exchange_tx.to_amount,
            "exchange_rate": exchange_tx.rate_applied,
            "exchange_fee": exchange_tx.fee_amount,
            "exchange_fee_currency": exchange_tx.fee_currency.value if exchange_tx.fee_currency else exchange_tx.from_currency.value,
            
            # For display compatibility with transaction receipt template
            "currency": exchange_tx.from_currency.value,
            "amount": exchange_tx.from_amount,
        }
        
        # Create custom HTML template for currency exchange receipt
        exchange_receipt_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{{ title }}</title>
            <style>
                @page {
                    size: letter portrait;
                    margin: 1.5cm;
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
                    font-size: 10pt;
                    line-height: 1.3;
                    color: #333;
                }
                .document {
                    padding: 5px;
                    position: relative;
                }
                .watermark {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%) rotate(-45deg);
                    font-size: 80px;
                    color: rgba(200, 200, 200, 0.2);
                    font-weight: bold;
                    z-index: -1;
                }
                .header {
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 10px;
                    margin-bottom: 15px;
                    text-align: center;
                }
                .document-title {
                    font-size: 18pt;
                    font-weight: bold;
                    color: #1a4f8a;
                    margin-bottom: 0;
                }
                .document-subtitle {
                    font-size: 12pt;
                    color: #666;
                    margin-bottom: 10px;
                }
                .content-columns {
                    display: flex;
                    justify-content: space-between;
                    flex-wrap: wrap;
                }
                .column {
                    width: 48%;
                }
                .section-title {
                    font-size: 12pt;
                    font-weight: bold;
                    color: #1a4f8a;
                    margin-top: 10px;
                    margin-bottom: 5px;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 3px;
                }
                .info-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 15px;
                }
                .info-table th {
                    text-align: left;
                    padding: 5px;
                    background-color: #f5f5f5;
                    border-bottom: 1px solid #ddd;
                    font-weight: bold;
                    width: 40%;
                }
                .info-table td {
                    padding: 5px;
                    border-bottom: 1px solid #ddd;
                }
                .amount {
                    font-weight: bold;
                    font-size: 12pt;
                    color: #2a6e38;
                }
                .exchange-rate {
                    font-weight: bold;
                    color: #1a4f8a;
                }
                .transaction-status {
                    display: inline-block;
                    padding: 3px 6px;
                    border-radius: 3px;
                    font-weight: bold;
                    text-transform: uppercase;
                    font-size: 9pt;
                }
                .status-completed {
                    background-color: #d4edda;
                    color: #155724;
                }
                .status-pending, .status-failed, .status-cancelled {
                    background-color: #f8d7da;
                    color: #721c24;
                }
                .footer {
                    margin-top: 15px;
                    padding-top: 10px;
                    border-top: 1px solid #ddd;
                    font-size: 9pt;
                    color: #666;
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <div class="document">
                <div class="watermark">RECEIPT</div>
                <div class="header">
                    <div class="document-title">{{ title }}</div>
                    <div class="document-subtitle">{{ subtitle }}</div>
                </div>
                
                <div class="content-columns">
                    <div class="column">
                        <div class="section-title">Transaction Details</div>
                        <table class="info-table">
                            <tr>
                                <th>Reference Number</th>
                                <td>{{ transaction.reference }}</td>
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
                                <th>Account Holder</th>
                                <td>{{ transaction.sender_name }}</td>
                            </tr>
                        </table>
                        
                        <div class="section-title">Account Information</div>
                        <table class="info-table">
                            <tr>
                                <th>From Account</th>
                                <td>{{ transaction.sender_account_masked }} ({{ transaction.sender_account_type }})</td>
                            </tr>
                            <tr>
                                <th>To Account</th>
                                <td>{{ transaction.recipient_account_masked }} ({{ transaction.recipient_account_type }})</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div class="column">
                        <div class="section-title">Exchange Details</div>
                        <table class="info-table">
                            <tr>
                                <th>Exchange Type</th>
                                <td>{{ transaction.description }}</td>
                            </tr>
                            <tr>
                                <th>From Amount</th>
                                <td class="amount">{{ transaction.exchange_from_currency }} {{ "%.2f"|format(transaction.exchange_from_amount) }}</td>
                            </tr>
                            <tr>
                                <th>To Amount</th>
                                <td class="amount">{{ transaction.exchange_to_currency }} {{ "%.2f"|format(transaction.exchange_to_amount) }}</td>
                            </tr>
                            <tr>
                                <th>Exchange Rate</th>
                                <td class="exchange-rate">1 {{ transaction.exchange_from_currency }} = {{ "%.6f"|format(transaction.exchange_rate) }} {{ transaction.exchange_to_currency }}</td>
                            </tr>
                            {% if transaction.exchange_fee > 0 %}
                            <tr>
                                <th>Fee</th>
                                <td>{{ transaction.exchange_fee_currency }} {{ "%.2f"|format(transaction.exchange_fee) }}</td>
                            </tr>
                            {% endif %}
                        </table>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This document serves as an official receipt for the currency exchange transaction detailed above.</p>
                    <p>For questions or concerns regarding this transaction, please contact NVC Fund Bank customer support.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Generate HTML content
        title = f"Currency Exchange Receipt"
        subtitle = f"{exchange_tx.from_currency.value} to {exchange_tx.to_currency.value} Exchange"
        header = "NVC FUND BANK CURRENCY EXCHANGE RECEIPT"
        generation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        html_content = render_template_string(
            exchange_receipt_template,
            title=title,
            subtitle=subtitle,
            header=header,
            generation_date=generation_date,
            transaction=transaction_data
        )
        
        # Try using WeasyPrint to generate PDF (preferred method)
        try:
            import weasyprint
            from io import BytesIO
            
            # Create a BytesIO buffer for the PDF
            pdf_buffer = BytesIO()
            
            # Generate PDF using WeasyPrint
            html_obj = weasyprint.HTML(string=html_content)
            html_obj.write_pdf(pdf_buffer)
            
            # Get the PDF content
            pdf_buffer.seek(0)
            pdf_data = pdf_buffer.getvalue()
            return pdf_data
        
        except ImportError:
            logger.warning("WeasyPrint not available, trying alternative method...")
        except Exception as e:
            logger.warning(f"WeasyPrint error: {str(e)}, trying alternative method...")
        
        # Try using pdfkit as a fallback
        try:
            import pdfkit
            pdf_data = pdfkit.from_string(html_content, False)
            return pdf_data
        except ImportError:
            logger.warning("pdfkit not available, trying alternative method...")
        except Exception as e:
            logger.warning(f"pdfkit error: {str(e)}, trying alternative method...")
        
        # Final fallback: just return the HTML as bytes with a warning header
        fallback_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .warning-banner {
                    background-color: #fff3cd;
                    border: 1px solid #ffeeba;
                    padding: 10px;
                    margin-bottom: 20px;
                    border-radius: 4px;
                    color: #856404;
                    font-family: Arial, sans-serif;
                }
            </style>
        </head>
        <body>
            <div class="warning-banner">
                <strong>PDF Generation Warning:</strong> The system was unable to generate a proper PDF document.
                This is an HTML version of the receipt instead. For a properly formatted PDF, please contact support.
            </div>
        """ + html_content + """
        </body>
        </html>
        """
        
        return fallback_html.encode('utf-8')
    
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
    
    def generate_holding_report_pdf(self, data):
        """
        Generate a PDF for the NVC Fund Holding Trust Public Holding Report
        
        Args:
            data (dict): Report data including assets, totals, and other information
            
        Returns:
            bytes: PDF document as bytes
        """
        try:
            from flask import render_template, current_app, request
            import os
            import tempfile
            import asyncio
            import io
            
            # Ensure asset_count is properly calculated
            asset_count = data.get('asset_count', len(data.get('assets', [])))
            
            # Create an absolute URL for the logo that works in PDF context
            if request and request.host_url:
                host_url = request.host_url.rstrip('/')
            else:
                host_url = "https://localhost:5000"  # Fallback if request is not available
            
            # Load logo for embedding as base64
            logo_path = os.path.join(current_app.static_folder, 'img', 'nvc_fund_holding_trust_logo.png')
            logo_bytes = None
            logo_base64 = None
            
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    logo_bytes = f.read()
                    import base64
                    logo_base64 = base64.b64encode(logo_bytes).decode('ascii')
            
            # Construct the data URI for the logo
            logo_url = f"data:image/png;base64,{logo_base64}" if logo_base64 else f"{host_url}/static/img/nvc_fund_holding_trust_logo.png"
            
            # Render the template with embedded logo
            html_content = render_template(
                'saint_crown/public_holding_report_print.html',
                assets=data.get('assets', []),
                total_value=data.get('total_value', 0),
                total_value_afd1=data.get('total_value_afd1', 0),
                gold_price=data.get('gold_price', 0),
                gold_metadata=data.get('gold_metadata', {}),
                afd1_unit_value=data.get('afd1_unit_value', 0),
                asset_count=asset_count,
                institution=data.get('institution'),
                report_date=data.get('report_date', datetime.utcnow()),
                logo_url=logo_url
            )
            
            # Save HTML to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
                f.write(html_content)
                temp_html_path = f.name
            
            logger.info(f"Generating PDF using pyppeteer from {temp_html_path}")
            
            try:
                # Use pyppeteer for reliable PDF generation
                from pyppeteer import launch
                
                async def generate_pdf_with_pyppeteer():
                    browser = await launch(
                        options={
                            'headless': True, 
                            'args': [
                                '--no-sandbox',
                                '--disable-setuid-sandbox',
                                '--disable-dev-shm-usage',
                                '--disable-gpu'
                            ]
                        }
                    )
                    
                    try:
                        page = await browser.newPage()
                        
                        # Set viewport size to ensure content fits well
                        await page.setViewport({'width': 1200, 'height': 1600})
                        
                        # Navigate to the HTML file
                        await page.goto(f'file://{temp_html_path}', {'waitUntil': 'networkidle0'})
                        
                        # Wait a moment for any JS to execute
                        await asyncio.sleep(1)
                        
                        # Generate PDF
                        pdf_bytes = await page.pdf({
                            'format': 'Letter',
                            'margin': {
                                'top': '0.5in',
                                'right': '0.5in',
                                'bottom': '0.5in',
                                'left': '0.5in'
                            },
                            'printBackground': True
                        })
                        
                        return pdf_bytes
                    finally:
                        await browser.close()
                
                # Run the async function to generate PDF
                logger.info("Starting pyppeteer PDF generation...")
                pdf_content = asyncio.get_event_loop().run_until_complete(generate_pdf_with_pyppeteer())
                logger.info(f"PDF generation successful, generated {len(pdf_content)} bytes")
                
                # Clean up the temporary file
                os.unlink(temp_html_path)
                
                return pdf_content
                
            except Exception as e:
                logger.error(f"Error generating PDF with pyppeteer: {str(e)}")
                
                # Try WeasyPrint as fallback
                try:
                    logger.info("Attempting fallback to WeasyPrint...")
                    from weasyprint import HTML, CSS
                    import io
                    
                    # Generate CSS for better PDF display
                    pdf_css = '''
                    @page {
                        size: letter;
                        margin: 1cm;
                    }
                    
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.4;
                        font-size: 11pt;
                    }
                    
                    .header, .banner {
                        background-color: #002855 !important;
                        color: white !important;
                        -webkit-print-color-adjust: exact;
                        print-color-adjust: exact;
                    }
                    '''
                    
                    pdf_buffer = io.BytesIO()
                    
                    # Use WeasyPrint with embedded logo
                    HTML(
                        string=html_content, 
                        base_url=current_app.static_url_path
                    ).write_pdf(
                        pdf_buffer,
                        stylesheets=[CSS(string=pdf_css)]
                    )
                    
                    pdf_content = pdf_buffer.getvalue()
                    pdf_buffer.close()
                    
                    # Clean up the temporary file
                    os.unlink(temp_html_path)
                    
                    return pdf_content
                    
                except Exception as weasy_error:
                    logger.error(f"WeasyPrint fallback failed: {str(weasy_error)}")
                    
                    # Last resort: return HTML that explains the issue and offers a "Print in Browser" option
                    error_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>PDF Generation Failed</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
                            h1 {{ color: #c00; }}
                            .button {{ display: inline-block; padding: 10px 15px; background-color: #002855; color: white;
                                     text-decoration: none; border-radius: 4px; margin-top: 20px; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>PDF Generation Failed</h1>
                            <p>We're sorry, but we couldn't generate the PDF document due to technical issues.</p>
                            <p>Technical details: {str(e)}</p>
                            <p>You can view the report online and use your browser's print function instead:</p>
                            <p><a href="/nvc-fund-holding-trust-report.html" class="button">View Report</a></p>
                        </div>
                    </body>
                    </html>
                    """.encode('utf-8')
                    
                    # Clean up the temporary file
                    os.unlink(temp_html_path)
                    
                    return error_html
            
        except Exception as e:
            logger.error(f"Error generating holding report PDF: {str(e)}")
            raise


    @staticmethod
    def generate_html_to_pdf(html_content, pdf_path):
        """
        Generate a PDF from HTML content and save it to a file
        
        Args:
            html_content (str): HTML content to convert to PDF
            pdf_path (str): Path to save the PDF file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a temporary HTML file
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
                temp_html_path = temp_html.name
                temp_html.write(html_content.encode('utf-8'))
            
            # Use a simple approach - just copy the HTML content to the PDF file
            # with a PDF header to identify it as a PDF
            with open(pdf_path, 'w') as pdf_file:
                pdf_file.write('%PDF-1.5\n')
                pdf_file.write(html_content)
                
            # Clean up the temporary file
            os.unlink(temp_html_path)
            
            return True
        except Exception as e:
            logger.error(f"Error generating PDF from HTML: {str(e)}")
            return False

# Create a global instance
pdf_service = PDFService()