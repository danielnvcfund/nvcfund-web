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
    """Custom PDF class for receipt generation"""
    
    def header(self):
        """Create header for the receipt"""
        # Logo
        # Uncomment if you have a logo file
        # self.image('static/img/logo.png', 10, 8, 33)
        
        # Set font
        self.set_font('Arial', 'B', 16)
        # Move right
        self.cell(80)
        # Title
        self.cell(30, 10, 'NVC Banking Platform', 0, 1, 'C')
        # Line break
        self.ln(10)

    def footer(self):
        """Create footer for the receipt"""
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Set font
        self.set_font('Arial', 'I', 8)
        # Add page number
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')
        
    def add_title(self, title):
        """Add a title to the receipt"""
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)
        
    def add_subtitle(self, subtitle):
        """Add a subtitle to the receipt"""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, subtitle, 0, 1, 'L')
        self.ln(2)
        
    def add_detail_row(self, label, value):
        """Add a detail row with label and value"""
        self.set_font('Arial', '', 11)
        self.cell(50, 7, label, 0, 0, 'L')
        self.set_font('Arial', 'B', 11)
        self.cell(0, 7, str(value), 0, 1, 'L')
        
    def add_divider(self):
        """Add a divider line"""
        self.ln(2)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        
    def add_qr_code(self, data, x=None, y=None, w=30, h=30):
        """Add a QR code to the receipt"""
        import qrcode
        from qrcode.image.pil import PilImage
        
        # Create QR code
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
            
        # Add QR code image to PDF
        self.image(buffer, x=x, y=y, w=w, h=h)
        
        # Move position
        if y == self.get_y():
            self.ln(h + 5)


def generate_receipt_pdf(transaction, user):
    """
    Generate a PDF receipt for the transaction
    
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
    pdf.add_subtitle(f'Transaction ID: {transaction.transaction_id}')
    
    # Add receipt details
    pdf.add_divider()
    pdf.add_detail_row('Date:', transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'))
    pdf.add_detail_row('Amount:', f"{transaction.currency} {transaction.amount:.2f}")
    pdf.add_detail_row('Status:', transaction.status.value.title())
    pdf.add_detail_row('Payment Type:', transaction.transaction_type.value.replace('_', ' ').title())
    
    if transaction.description:
        pdf.add_detail_row('Description:', transaction.description)
    
    if transaction.recipient_name:
        pdf.add_detail_row('Recipient:', transaction.recipient_name)
    
    if transaction.recipient_account:
        pdf.add_detail_row('Account:', transaction.recipient_account)
    
    if transaction.recipient_institution:
        pdf.add_detail_row('Institution:', transaction.recipient_institution)
    
    pdf.add_divider()
    
    # Add user details
    pdf.add_subtitle('User Information')
    pdf.add_detail_row('Name:', user.username)
    pdf.add_detail_row('Email:', user.email)
    
    # Add transaction verification QR code
    pdf.ln(10)
    pdf.add_subtitle('Verify Transaction')
    pdf.add_qr_code(
        f"https://{os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]}/payment-history/transaction/{transaction.transaction_id}",
        x=10, y=pdf.get_y()
    )
    
    # Add footer text
    pdf.ln(5)
    pdf.set_font('Arial', 'I', 9)
    pdf.cell(0, 10, f'This receipt was generated on {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC', 0, 1, 'L')
    pdf.cell(0, 10, 'NVC Banking Platform - Official Receipt', 0, 1, 'L')
    
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