"""
Email Service Module
This module provides email notification services using SendGrid.
"""

import os
import sys
import logging
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition

# Configure logging
logger = logging.getLogger(__name__)

# Get SendGrid API key from environment
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
DEFAULT_FROM_EMAIL = 'no-reply@nvcplatform.net'


def send_transaction_confirmation_email(transaction, user) -> bool:
    """
    Send a transaction confirmation email to a user
    
    Args:
        transaction: The transaction model instance
        user: The user model instance
        
    Returns:
        Boolean indicating success or failure
    """
    subject = f"Transaction Confirmation - {transaction.transaction_id}"
    
    # Create HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #3498db; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 20px; }}
            .footer {{ font-size: 12px; color: #888; text-align: center; margin-top: 20px; }}
            .details {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
            .button {{ display: inline-block; background-color: #3498db; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Transaction Confirmation</h1>
            </div>
            <div class="content">
                <p>Dear {user.username},</p>
                <p>Your transaction has been processed. Here are the details:</p>
                
                <div class="details">
                    <p><strong>Transaction ID:</strong> {transaction.transaction_id}</p>
                    <p><strong>Amount:</strong> {transaction.currency} {transaction.amount:.2f}</p>
                    <p><strong>Date:</strong> {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Status:</strong> {transaction.status.value}</p>
                    <p><strong>Type:</strong> {transaction.transaction_type.value.replace('_', ' ').title()}</p>
                    <p><strong>Description:</strong> {transaction.description or 'N/A'}</p>
                </div>
                
                <p>You can view the complete transaction details by logging into your account.</p>
                
                <p>If you have any questions or concerns, please contact our support team.</p>
                
                <p>Thank you for using NVC Banking Platform.</p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>&copy; {datetime.now().year} NVC Banking Platform. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Create plain text content
    text_content = f"""
    Transaction Confirmation - {transaction.transaction_id}
    
    Dear {user.username},
    
    Your transaction has been processed. Here are the details:
    
    Transaction ID: {transaction.transaction_id}
    Amount: {transaction.currency} {transaction.amount:.2f}
    Date: {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}
    Status: {transaction.status.value}
    Type: {transaction.transaction_type.value.replace('_', ' ').title()}
    Description: {transaction.description or 'N/A'}
    
    You can view the complete transaction details by logging into your account.
    
    If you have any questions or concerns, please contact our support team.
    
    Thank you for using NVC Banking Platform.
    
    This is an automated message. Please do not reply to this email.
    """
    
    return send_email(
        to_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )


def send_email(
    to_email: str,
    subject: str,
    html_content: str | None = None,
    text_content: str | None = None,
    from_email: str = DEFAULT_FROM_EMAIL,
    attachments=None
) -> bool:
    """
    Send an email using SendGrid
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email (optional)
        text_content: Plain text content of the email (optional)
        from_email: Sender email address (defaults to DEFAULT_FROM_EMAIL)
        attachments: List of dictionaries with attachment data (optional)
        
    Returns:
        Boolean indicating success or failure
    """
    if not SENDGRID_API_KEY:
        logger.error("SendGrid API key not found in environment variables")
        return False
        
    if not html_content and not text_content:
        logger.error("Either html_content or text_content must be provided")
        return False
        
    # Create SendGrid client
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    
    # Create message
    message = Mail(
        from_email=Email(from_email),
        to_emails=To(to_email),
        subject=subject
    )
    
    # Add content (HTML or Plain Text)
    if html_content:
        message.content = Content("text/html", html_content)
    elif text_content:
        message.content = Content("text/plain", text_content)
    
    # Add attachments if any
    if attachments:
        for attachment_data in attachments:
            attachment = Attachment()
            attachment.file_content = FileContent(attachment_data['content'])
            attachment.file_name = FileName(attachment_data['filename'])
            attachment.file_type = FileType(attachment_data['mimetype'])
            attachment.disposition = Disposition('attachment')
            message.add_attachment(attachment)
    
    # Send email
    try:
        response = sg.send(message)
        logger.info(f"Email sent to {to_email}, status code: {response.status_code}")
        return response.status_code >= 200 and response.status_code < 300
    except Exception as e:
        logger.error(f"SendGrid error: {str(e)}")
        return False


def send_payment_confirmation(transaction, user) -> bool:
    """
    Send a payment confirmation email
    
    Args:
        transaction: The Transaction model instance
        user: The User model instance
        
    Returns:
        Boolean indicating success or failure
    """
    subject = f"Payment Confirmation - {transaction.transaction_id}"
    
    # Create HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #3498db; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 20px; }}
            .footer {{ font-size: 12px; color: #888; text-align: center; margin-top: 20px; }}
            .details {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
            .button {{ display: inline-block; background-color: #3498db; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Payment Confirmation</h1>
            </div>
            <div class="content">
                <p>Dear {user.username},</p>
                <p>Your payment has been successfully processed. Here are the details:</p>
                
                <div class="details">
                    <p><strong>Transaction ID:</strong> {transaction.transaction_id}</p>
                    <p><strong>Amount:</strong> {transaction.currency} {transaction.amount:.2f}</p>
                    <p><strong>Date:</strong> {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Status:</strong> {transaction.status.value}</p>
                    <p><strong>Description:</strong> {transaction.description or 'N/A'}</p>
                </div>
                
                <p>You can view the complete transaction details and download a receipt by clicking the button below:</p>
                
                <p style="text-align: center;">
                    <a href="https://{os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]}/payment-history/transaction/{transaction.transaction_id}" class="button">View Transaction</a>
                </p>
                
                <p>If you have any questions or concerns, please contact our support team.</p>
                
                <p>Thank you for using NVC Banking Platform.</p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>&copy; {transaction.created_at.year} NVC Banking Platform. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Create plain text content
    text_content = f"""
    Payment Confirmation - {transaction.transaction_id}
    
    Dear {user.username},
    
    Your payment has been successfully processed. Here are the details:
    
    Transaction ID: {transaction.transaction_id}
    Amount: {transaction.currency} {transaction.amount:.2f}
    Date: {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}
    Status: {transaction.status.value}
    Description: {transaction.description or 'N/A'}
    
    You can view the complete transaction details and download a receipt by visiting:
    https://{os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]}/payment-history/transaction/{transaction.transaction_id}
    
    If you have any questions or concerns, please contact our support team.
    
    Thank you for using NVC Banking Platform.
    
    This is an automated message. Please do not reply to this email.
    """
    
    return send_email(
        to_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )


def send_receipt_email(transaction, user, pdf_content) -> bool:
    """
    Send a receipt email with PDF attachment
    
    Args:
        transaction: The Transaction model instance
        user: The User model instance
        pdf_content: The PDF receipt content as base64 string
        
    Returns:
        Boolean indicating success or failure
    """
    subject = f"Your Receipt - {transaction.transaction_id}"
    
    # Create HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #3498db; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 20px; }}
            .footer {{ font-size: 12px; color: #888; text-align: center; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Your Receipt</h1>
            </div>
            <div class="content">
                <p>Dear {user.username},</p>
                <p>Please find attached the receipt for your recent transaction.</p>
                <p>Transaction ID: {transaction.transaction_id}</p>
                <p>Thank you for using NVC Banking Platform.</p>
                <p>If you have any questions or concerns, please contact our support team.</p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>&copy; {transaction.created_at.year} NVC Banking Platform. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Create plain text content
    text_content = f"""
    Your Receipt - {transaction.transaction_id}
    
    Dear {user.username},
    
    Please find attached the receipt for your recent transaction.
    
    Transaction ID: {transaction.transaction_id}
    
    Thank you for using NVC Banking Platform.
    
    If you have any questions or concerns, please contact our support team.
    
    This is an automated message. Please do not reply to this email.
    """
    
    # Create attachment data
    attachments = [{
        'content': pdf_content,
        'filename': f'Receipt-{transaction.transaction_id}.pdf',
        'mimetype': 'application/pdf'
    }]
    
    return send_email(
        to_email=user.email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        attachments=attachments
    )