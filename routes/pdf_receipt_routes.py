"""
PDF Receipt Routes
This module provides routes for generating and downloading PDF receipts.
"""

import os
import base64
import logging
from io import BytesIO
from datetime import datetime

from flask import Blueprint, send_file, render_template, abort, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
import qrcode
from fpdf import FPDF

from models import db, Transaction, User
from email_service import send_receipt_email

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
pdf_receipt_bp = Blueprint('pdf_receipt', __name__, url_prefix='/pdf-receipt')


class ReceiptPDF(FPDF):
    """Custom PDF class for receipt generation with enhanced styling"""
    
    def header(self):
        """Create header for the receipt"""
        # Set header background color (light blue)
        self.set_fill_color(240, 248, 255)
        self.rect(0, 0, 210, 25, 'F')
        
        # Add logo placeholder - would be replaced with actual logo
        self.set_fill_color(200, 220, 255)
        self.rect(10, 5, 30, 15, 'F')
        self.set_text_color(70, 130, 180)
        self.set_font('Arial', 'B', 12)
        self.set_xy(10, 5)
        self.cell(30, 15, 'NVC LOGO', 0, 0, 'C')
        
        # Set font for header text
        self.set_text_color(0, 51, 102)
        self.set_font('Arial', 'B', 16)
        
        # Add platform name
        self.set_xy(45, 8)
        self.cell(120, 10, 'NVC Banking Platform', 0, 1, 'L')
        
        # Add document type with smaller font
        self.set_font('Arial', 'I', 10)
        self.set_text_color(70, 130, 180)
        self.set_xy(45, 15)
        self.cell(120, 5, 'OFFICIAL PAYMENT RECEIPT', 0, 1, 'L')
        
        # Reset text color
        self.set_text_color(0, 0, 0)
        
        # Line break after header
        self.ln(15)

    def footer(self):
        """Create enhanced footer for the receipt"""
        # Add horizontal line
        self.set_y(-25)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        
        # Add secure document notice
        self.set_font('Arial', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'This document contains security features. Verify at verify.nvcbank.com', 0, 1, 'C')
        
        # Add page number
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f'Page {self.page_no()}/{{nb}} • Generated on {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}', 0, 0, 'C')
        
        # Add confidentiality notice
        self.set_y(-10)
        self.cell(0, 5, 'CONFIDENTIAL - For recipient use only', 0, 0, 'C')
        
        # Reset text color
        self.set_text_color(0, 0, 0)
        
    def add_title(self, title):
        """Add a styled title to the receipt"""
        # Add background
        self.set_fill_color(240, 248, 255)
        orig_y = self.get_y()
        self.rect(10, orig_y, 190, 12, 'F')
        
        # Add title text
        self.set_text_color(0, 51, 102)
        self.set_font('Arial', 'B', 14)
        self.set_xy(12, orig_y + 2)
        self.cell(0, 8, title, 0, 1, 'L')
        
        # Reset text color and add space
        self.set_text_color(0, 0, 0)
        self.ln(5)
        
    def add_subtitle(self, subtitle):
        """Add a styled subtitle to the receipt"""
        self.set_font('Arial', 'B', 11)
        self.set_text_color(70, 130, 180)
        self.cell(0, 8, subtitle, 0, 1, 'L')
        self.set_text_color(0, 0, 0)
        self.ln(2)
        
    def add_detail_row(self, label, value, highlight=False):
        """Add a detail row with label and value"""
        if highlight:
            # Use highlight colors for important information
            self.set_font('Arial', 'B', 11)
            self.set_text_color(70, 70, 70)
            self.cell(50, 7, label, 0, 0, 'L')
            self.set_font('Arial', 'B', 12)
            self.set_text_color(0, 102, 0)  # Green for amounts
            self.cell(0, 7, str(value), 0, 1, 'L')
            self.set_text_color(0, 0, 0)
        else:
            # Standard formatting
            self.set_font('Arial', '', 10)
            self.set_text_color(70, 70, 70)
            self.cell(50, 7, label, 0, 0, 'L')
            self.set_font('Arial', 'B', 10)
            self.set_text_color(0, 0, 0)
            self.cell(0, 7, str(value), 0, 1, 'L')
        
    def add_divider(self):
        """Add a divider line"""
        self.ln(2)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        
    def add_status_badge(self, status):
        """Add a status badge with appropriate color matching web UI"""
        status_lower = str(status).lower()
        
        # Set badge colors based on status - matching the UI colors
        if 'completed' in status_lower or 'success' in status_lower:
            bg_color = (100, 149, 237)  # Cornflower blue - matching the UI blue
            text_color = (255, 255, 255)  # White text
        elif 'pending' in status_lower or 'processing' in status_lower:
            bg_color = (255, 193, 7)  # Warning yellow
            text_color = (33, 37, 41)   # Dark text
        elif 'failed' in status_lower or 'cancelled' in status_lower or 'rejected' in status_lower:
            bg_color = (220, 53, 69)    # Danger red
            text_color = (255, 255, 255)  # White text
        else:
            bg_color = (108, 117, 125)  # Secondary gray
            text_color = (255, 255, 255)  # White text
            
        # Store current position
        x, y = self.get_x(), self.get_y()
        
        # We'll use a simple rectangle instead of trying to implement rounded corners
        # as FPDF doesn't support them easily
        
        # Add styled badge with text
        self.set_fill_color(*bg_color)
        
        # Draw rectangle with slight rounding at corners
        badge_width = 50
        badge_height = 12
        self.rect(x, y, badge_width, badge_height, 'F')
        
        # Add text centered in badge
        self.set_text_color(*text_color)
        self.set_font('Arial', 'B', 9)
        
        # Center the text in the badge
        text = status.upper()
        self.set_xy(x, y + 2.5)  # Vertically center
        self.cell(badge_width, 7, text, 0, 1, 'C')
        
        # Reset position and colors
        self.set_xy(x + badge_width + 5, y)  # Move right after the badge
        self.set_text_color(0, 0, 0)
        
    def add_qr_code(self, data, x=None, y=None, w=35, h=35):
        """Add a QR code to the receipt with a box around it"""
        import qrcode
        
        # Create QR code with simple call - more compatible
        qr_img = qrcode.make(data)
        
        # Save QR code to a BytesIO object
        buffer = BytesIO()
        qr_img.save(buffer)
        buffer.seek(0)
        
        # If x and y are not specified, place QR code at current position
        if x is None:
            x = self.get_x()
        if y is None:
            y = self.get_y()
            
        # Draw box around QR code
        self.set_draw_color(200, 200, 200)
        self.rect(x-2, y-2, w+4, h+4)
            
        # Add QR code image to PDF
        self.image(buffer, x=x, y=y, w=w, h=h)
        
        # Add "Scan to verify" text
        self.set_font('Arial', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.set_xy(x, y+h+1)
        self.cell(w, 5, "Scan to verify", 0, 0, 'C')
        
        # Reset text color
        self.set_text_color(0, 0, 0)
        
        # Move position
        if y == self.get_y():
            self.ln(h + 10)
            
    def add_section(self, title):
        """Add a section with styled heading"""
        # Add section title with background
        self.set_fill_color(245, 245, 245)
        self.set_text_color(70, 130, 180)
        self.set_font('Arial', 'B', 11)
        self.cell(0, 8, title, 0, 1, 'L', True)
        
        # Reset text color
        self.set_text_color(0, 0, 0)
        self.ln(2)


def generate_receipt_pdf(transaction, user):
    """
    Generate a professionally formatted PDF receipt for the transaction
    
    Args:
        transaction: Transaction model instance
        user: User model instance
        
    Returns:
        BytesIO buffer containing the PDF
    """
    # Create PDF instance
    pdf = ReceiptPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Add receipt title
    pdf.add_title('Payment Receipt')
    
    # Add transaction ID and date in highlighted box
    pdf.set_fill_color(250, 250, 250)
    pdf.rect(10, pdf.get_y(), 190, 20, 'F')
    pdf.set_xy(15, pdf.get_y() + 3)
    
    # Add status badge on the right side with styling to match the web UI
    pdf.set_xy(150, pdf.get_y())
    status_text = transaction.status.value if hasattr(transaction.status, 'value') else str(transaction.status)
    pdf.add_status_badge(status_text)
    
    # Add transaction ID on the left side
    pdf.set_xy(15, pdf.get_y())
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(130, 5, f'Transaction Reference', 0, 1, 'L')
    pdf.set_xy(15, pdf.get_y())
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(130, 10, f'{transaction.transaction_id}', 0, 1, 'L')
    
    pdf.ln(5)
    
    # Payment Information Section
    pdf.add_section('Payment Information')
    
    # Create a two-column layout for payment details
    col_width = 90
    left_margin = 15
    
    # Key Transaction Information matching UI format
    # Type
    pdf.set_xy(left_margin, pdf.get_y() + 3)
    tx_type = transaction.transaction_type.value if hasattr(transaction.transaction_type, 'value') else str(transaction.transaction_type)
    pdf.add_detail_row('Type:', tx_type.replace('_', ' ').title())
    
    # Amount with proper AFD1 formatting if needed
    pdf.set_xy(left_margin, pdf.get_y() + 2)
    amount_str = f"{transaction.amount:.2f}"
    currency_str = transaction.currency
    pdf.add_detail_row('Amount:', f"{currency_str} {amount_str}", highlight=True)
    
    # Created date using same format as transaction details page
    pdf.set_xy(left_margin, pdf.get_y() + 2)
    created_date = transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')
    pdf.add_detail_row('Created:', created_date)
    
    # Last updated date if different from created
    if hasattr(transaction, 'updated_at') and transaction.updated_at and transaction.updated_at != transaction.created_at:
        pdf.set_xy(left_margin, pdf.get_y() + 2)
        updated_date = transaction.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        pdf.add_detail_row('Last Updated:', updated_date)
    
    # Right column - Payment Method and Type
    right_col_x = left_margin + col_width + 10
    
    # Determine payment method from transaction_type or gateway
    payment_method = "Credit Card"  # Default
    
    # Map transaction types to likely payment methods
    method_mapping = {
        "PAYMENT": "Credit Card",
        "DEPOSIT": "Bank Transfer",
        "WITHDRAWAL": "Bank Transfer",
        "TRANSFER": "Internal Transfer",
        "SWIFT_FUND_TRANSFER": "SWIFT",
        "SWIFT_INSTITUTION_TRANSFER": "SWIFT",
        "SWIFT_LETTER_OF_CREDIT": "SWIFT",
        "PAYOUT": "PayPal",
        "EDI_ACH_TRANSFER": "ACH",
        "RTGS_TRANSFER": "RTGS"
    }
    
    # Get the type value if available
    tx_type = None
    if hasattr(transaction, 'transaction_type') and transaction.transaction_type:
        try:
            tx_type = transaction.transaction_type.value
        except:
            tx_type = str(transaction.transaction_type)
    
    # Look up payment method from mapping
    if tx_type and tx_type in method_mapping:
        payment_method = method_mapping[tx_type]
    
    # Check if we have Stripe gateway ID
    if hasattr(transaction, 'gateway_id') and transaction.gateway_id:
        gateway_types = {
            1: "Stripe", 
            2: "PayPal",
            3: "NVC Global"
        }
        if transaction.gateway_id in gateway_types:
            payment_method = gateway_types[transaction.gateway_id]
    
    pdf.set_xy(right_col_x, pdf.get_y() - 9)  # Align with left column
    pdf.add_detail_row('Payment Method:', payment_method)
    
    # Payment type
    payment_type = "Payment"  # Default
    if hasattr(transaction, 'transaction_type') and transaction.transaction_type:
        try:
            payment_type = transaction.transaction_type.value.replace('_', ' ').title()
        except:
            # If value attribute doesn't exist, use string representation
            payment_type = str(transaction.transaction_type).replace('_', ' ').title()
    
    pdf.set_xy(right_col_x, pdf.get_y() + 2)
    pdf.add_detail_row('Payment Type:', payment_type)
    
    # Reset position for next section
    pdf.ln(5)
    pdf.set_x(left_margin)
    
    # Description if available
    if transaction.description:
        pdf.add_divider()
        pdf.add_detail_row('Description:', transaction.description)
    
    # Transaction Details Section
    pdf.ln(8)
    pdf.add_section('Transaction Details')
    
    # Payer Information
    pdf.set_xy(left_margin, pdf.get_y() + 3)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(70, 70, 70)
    pdf.cell(col_width, 7, 'Payer Information', 0, 1, 'L')
    
    pdf.set_xy(left_margin, pdf.get_y() + 1)
    if hasattr(user, 'full_name') and callable(user.full_name):
        pdf.add_detail_row('Name:', user.full_name())
    else:
        pdf.add_detail_row('Name:', user.username)
    
    pdf.set_xy(left_margin, pdf.get_y() + 1)
    pdf.add_detail_row('Email:', user.email)
    
    # If user has an account_holder relationship with addresses
    try:
        if hasattr(user, 'account_holder') and user.account_holder:
            if hasattr(user.account_holder, 'primary_address') and callable(user.account_holder.primary_address):
                address = user.account_holder.primary_address()
                if address:
                    pdf.set_xy(left_margin, pdf.get_y() + 1)
                    pdf.add_detail_row('Address:', address.formatted())
    except:
        # Address information not available - skip
        pass
    
    # Recipient & Bank Details (exactly matching transaction details page format)
    if (transaction.recipient_name or transaction.recipient_institution or transaction.recipient_account or
         hasattr(transaction, 'recipient_country') and transaction.recipient_country):
        
        pdf.set_xy(right_col_x, pdf.get_y() - 30)  # Position at top of this section but in right column
        
        # Add Recipient & Bank Details header with icon
        pdf.set_fill_color(240, 248, 255)  # Light blue background for section header
        pdf.rect(right_col_x, pdf.get_y(), col_width, 10, 'F')
        
        # Bank icon
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(0, 51, 102)  # Dark blue for header
        pdf.set_xy(right_col_x + 2, pdf.get_y() + 2)
        pdf.cell(6, 6, '🏦', 0, 0, 'L')  # Bank emoji character
        
        # Header title
        pdf.set_xy(right_col_x + 10, pdf.get_y() + 2)
        pdf.cell(col_width - 10, 6, 'Recipient & Bank Details', 0, 1, 'L')
        pdf.set_text_color(0, 0, 0)
        
        # Recipient Name with exact text from UI
        if transaction.recipient_name:
            pdf.set_xy(right_col_x, pdf.get_y() + 4)
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color(70, 70, 70)
            pdf.cell(col_width, 6, 'Recipient Name:', 0, 1, 'L')
            
            pdf.set_xy(right_col_x, pdf.get_y() + 1)
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(col_width, 6, transaction.recipient_name, 0, 1, 'L')
        
        # Add Receiving Bank Information section header
        pdf.set_xy(right_col_x, pdf.get_y() + 3)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(100, 100, 230)  # Blue for section header matching UI
        pdf.cell(col_width, 6, 'Receiving Bank Information:', 0, 1, 'L')
        
        # Processing Institution
        pdf.set_xy(right_col_x, pdf.get_y() + 3)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(70, 70, 70)
        pdf.cell(col_width, 6, 'Processing Institution:', 0, 1, 'L')
        
        pdf.set_xy(right_col_x, pdf.get_y() + 1)
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        institution = transaction.recipient_institution if transaction.recipient_institution else "Not specified"
        pdf.cell(col_width, 6, institution, 0, 1, 'L')
        
        # Beneficiary Bank
        pdf.set_xy(right_col_x, pdf.get_y() + 3)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(70, 70, 70)
        pdf.cell(col_width, 6, 'Beneficiary Bank:', 0, 1, 'L')
        
        pdf.set_xy(right_col_x, pdf.get_y() + 1)
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        beneficiary_bank = "Not specified"
        if hasattr(transaction, 'recipient_bank') and transaction.recipient_bank:
            beneficiary_bank = transaction.recipient_bank
        pdf.cell(col_width, 6, beneficiary_bank, 0, 1, 'L')
        
        # Account Number
        pdf.set_xy(right_col_x, pdf.get_y() + 3)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(70, 70, 70)
        pdf.cell(col_width, 6, 'Account Number:', 0, 1, 'L')
        
        pdf.set_xy(right_col_x, pdf.get_y() + 1)
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        account = "Not specified"
        if transaction.recipient_account:
            # Mask account number for security
            account = transaction.recipient_account
            if len(account) > 4:
                account = '*' * (len(account) - 4) + account[-4:]
        pdf.cell(col_width, 6, account, 0, 1, 'L')
        
        # Country (if available)
        if hasattr(transaction, 'recipient_country') and transaction.recipient_country:
            pdf.set_xy(right_col_x, pdf.get_y() + 3)
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color(70, 70, 70)
            pdf.cell(col_width, 6, 'Country:', 0, 1, 'L')
            
            pdf.set_xy(right_col_x, pdf.get_y() + 1)
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(col_width, 6, transaction.recipient_country, 0, 1, 'L')
    
    # Additional details (optional)
    if hasattr(transaction, 'tx_metadata_json') and transaction.tx_metadata_json:
        try:
            # Try to parse the JSON metadata
            import json
            metadata = json.loads(transaction.tx_metadata_json)
            
            if metadata:
                pdf.ln(8)
                pdf.add_section('Additional Information')
                
                # Add each metadata item
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        # Format the key for display
                        display_key = key.replace('_', ' ').title() + ':'
                        pdf.set_xy(left_margin, pdf.get_y() + 1)
                        pdf.add_detail_row(display_key, str(value))
        except:
            # Failed to parse metadata - skip this section
            pass
    
    # Add Transaction Timeline section
    pdf.ln(10)
    pdf.add_section('Transaction Timeline')
    
    # Timeline event visualization
    pdf.set_xy(left_margin, pdf.get_y() + 5)
    
    # Create a circle with timeline connector
    def add_timeline_event(pdf, y_pos, event_text, timestamp, is_last=False):
        # Draw circle
        pdf.set_fill_color(100, 149, 237)  # Cornflower blue
        pdf.set_draw_color(100, 149, 237)
        circle_x = left_margin + 5
        circle_y = y_pos
        circle_radius = 3
        pdf.circle(circle_x, circle_y, circle_radius, style="F")
        
        # Draw timeline connector line (if not the last event)
        if not is_last:
            pdf.set_draw_color(200, 200, 200)
            pdf.line(circle_x, circle_y + circle_radius, circle_x, circle_y + 20)
        
        # Add event text
        pdf.set_xy(circle_x + 10, y_pos - 3)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(70, 70, 70)
        pdf.cell(100, 6, event_text, 0, 1, 'L')
        
        # Add timestamp
        pdf.set_xy(circle_x + 10, y_pos + 3)
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(100, 6, timestamp, 0, 1, 'L')
    
    # Add created event
    timeline_y = pdf.get_y()
    add_timeline_event(
        pdf, 
        timeline_y, 
        "Transaction was created", 
        transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # Add completed event if transaction is completed
    if hasattr(transaction, 'status') and str(transaction.status).upper() == 'COMPLETED':
        completed_time = transaction.updated_at if hasattr(transaction, 'updated_at') and transaction.updated_at else transaction.created_at
        add_timeline_event(
            pdf,
            timeline_y + 25,
            "Transaction was completed",
            completed_time.strftime('%Y-%m-%d %H:%M:%S'),
            is_last=True
        )
    
    # Add verification section
    pdf.ln(10)
    pdf.add_section('Verification')
    
    # Get the verification URL
    domain = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
    verify_url = f"https://{domain}/payment-history/transaction/{transaction.transaction_id}"
    
    # Add explanatory text
    pdf.set_xy(left_margin, pdf.get_y() + 5)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(70, 70, 70)
    pdf.multi_cell(120, 5, 'Scan the QR code or visit the URL below to verify this transaction online and access your digital receipt:', 0, 'L')
    
    pdf.set_xy(left_margin, pdf.get_y() + 2)
    pdf.set_font('Arial', 'U', 9)
    pdf.set_text_color(0, 0, 255)
    pdf.cell(120, 5, verify_url, 0, 1, 'L')
    
    # Add QR code on the right
    pdf.add_qr_code(verify_url, x=150, y=pdf.get_y() - 25)
    
    # Additional legal text at bottom
    pdf.ln(10)
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(10, pdf.get_y(), 190, 25, 'F')
    
    pdf.set_xy(15, pdf.get_y() + 3)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(180, 4, 
        'This receipt serves as proof of payment for the transaction detailed above. '
        'For questions or concerns regarding this transaction, please contact customer support '
        'with the transaction reference number. All transactions are subject to verification and '
        'the terms and conditions of NVC Banking Platform.', 0, 'L')
    
    # Save PDF to BytesIO
    buffer = BytesIO()
    
    # Get PDF output and write to buffer
    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        buffer.write(pdf_output.encode('latin1'))
    else:
        buffer.write(pdf_output)
    buffer.seek(0)
    
    return buffer


@pdf_receipt_bp.route('/generate/<transaction_id>')
@login_required
def generate_receipt(transaction_id):
    """Generate and download a PDF receipt for a transaction"""
    # Find the transaction
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id, 
        user_id=current_user.id
    ).first_or_404()
    
    # Generate PDF receipt
    pdf_buffer = generate_receipt_pdf(transaction, current_user)
    
    # Return PDF file
    return send_file(
        pdf_buffer, 
        mimetype='application/pdf',
        download_name=f'Receipt-{transaction.transaction_id}.pdf',
        as_attachment=True
    )


@pdf_receipt_bp.route('/email/<transaction_id>')
@login_required
def email_receipt(transaction_id):
    """Generate a PDF receipt and email it to the user"""
    # Find the transaction
    transaction = Transaction.query.filter_by(
        transaction_id=transaction_id, 
        user_id=current_user.id
    ).first_or_404()
    
    # Generate PDF receipt
    pdf_buffer = generate_receipt_pdf(transaction, current_user)
    
    # Convert to base64 for email attachment
    pdf_data = pdf_buffer.getvalue()
    pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
    
    # Log for troubleshooting
    logger.info(f"Generated PDF receipt for transaction {transaction_id}")
    
    # Send email with receipt attachment
    if send_receipt_email(transaction, current_user, pdf_base64):
        flash('Receipt has been sent to your email.', 'success')
        logger.info(f"Receipt email sent successfully to {current_user.email}")
    else:
        flash('Failed to send receipt email. Please try again.', 'danger')
        logger.error(f"Failed to send receipt email for transaction {transaction_id} to {current_user.email}")
    
    # Redirect back to transaction detail page
    return redirect(url_for('payment_history.transaction_detail', transaction_id=transaction_id))