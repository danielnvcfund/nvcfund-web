"""
Email service module for the NVC Banking Platform
Uses SendGrid to send transactional emails
"""
import os
import logging
from typing import Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, TemplateId, Personalization
from flask import current_app, url_for

logger = logging.getLogger(__name__)

# Constants
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = 'notifications@nvcplatform.net'  # Replace with your verified sender
FROM_NAME = 'NVC Banking Platform'

# Email templates
TEMPLATES = {
    'welcome': 'd-xxxxxxxxxxxxxxxxxxxxxxxx',  # Replace with actual template ID when available
    'password_reset': 'd-xxxxxxxxxxxxxxxxxxxxxxxx',  # Replace with actual template ID when available
    'account_verification': 'd-xxxxxxxxxxxxxxxxxxxxxxxx',  # Replace with actual template ID when available
    'invitation': 'd-xxxxxxxxxxxxxxxxxxxxxxxx'  # Replace with actual template ID when available
}

def send_email(
    to_email: str,
    subject: str,
    text_content: Optional[str] = None,
    html_content: Optional[str] = None,
    template_id: Optional[str] = None,
    dynamic_template_data: Optional[dict] = None
) -> bool:
    """
    Send an email using SendGrid
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        text_content (str, optional): Plain text content. Required if template_id is not provided.
        html_content (str, optional): HTML content. If not provided, text_content will be used.
        template_id (str, optional): SendGrid template ID. If provided, content will be ignored.
        dynamic_template_data (dict, optional): Data for template. Required if template_id is provided.
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not SENDGRID_API_KEY:
        logger.error("SendGrid API key is not configured")
        return False
    
    if not template_id and not (text_content or html_content):
        logger.error("Either template_id or content (text or html) must be provided")
        return False
    
    if template_id and not dynamic_template_data:
        logger.warning("Template ID provided without dynamic template data")
    
    message = Mail(
        from_email=Email(FROM_EMAIL, FROM_NAME),
        to_emails=To(to_email),
        subject=subject
    )
    
    if template_id:
        message.template_id = TemplateId(template_id)
        
        if dynamic_template_data:
            personalization = Personalization()
            personalization.add_to(To(to_email))
            for key, value in dynamic_template_data.items():
                personalization.dynamic_template_data = {
                    key: value
                }
            message.add_personalization(personalization)
    else:
        if html_content:
            message.content = Content("text/html", html_content)
        elif text_content:
            message.content = Content("text/plain", text_content)
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"Email sent successfully to {to_email}")
            return True
        else:
            logger.error(f"Failed to send email to {to_email}. Status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"SendGrid error: {str(e)}")
        return False

def send_password_reset_email(user, token):
    """
    Send password reset email
    
    Args:
        user: User object with email and username
        token: Password reset token
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    reset_url = url_for('web.main.reset_password', token=token, _external=True)
    
    subject = "Password Reset Request - NVC Banking Platform"
    html_content = f"""
    <html>
        <body>
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
                <h2 style="color: #4A6FFF;">Password Reset Request</h2>
                <p>Hello {user.username},</p>
                <p>You recently requested to reset your password for your NVC Banking Platform account. Click the button below to reset it:</p>
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{reset_url}" style="background-color: #4A6FFF; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Your Password</a>
                </div>
                <p>If you did not request a password reset, please ignore this email or contact support if you have questions.</p>
                <p>This link will expire in 1 hour.</p>
                <p>Regards,<br>The NVC Banking Platform Team</p>
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #888;">
                    <p>If you're having trouble clicking the button, copy and paste this URL into your web browser:</p>
                    <p>{reset_url}</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    return send_email(
        to_email=user.email,
        subject=subject,
        html_content=html_content
    )

def send_username_reminder_email(user):
    """
    Send username reminder email
    
    Args:
        user: User object with email and username
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    login_url = url_for('web.main.login', _external=True)
    
    subject = "Username Reminder - NVC Banking Platform"
    html_content = f"""
    <html>
        <body>
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
                <h2 style="color: #4A6FFF;">Username Reminder</h2>
                <p>Hello,</p>
                <p>You recently requested a reminder of your username for the NVC Banking Platform.</p>
                <p>Your username is: <strong>{user.username}</strong></p>
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{login_url}" style="background-color: #4A6FFF; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Sign In Now</a>
                </div>
                <p>If you did not request this information, please contact our support team immediately.</p>
                <p>Regards,<br>The NVC Banking Platform Team</p>
            </div>
        </body>
    </html>
    """
    
    return send_email(
        to_email=user.email,
        subject=subject,
        html_content=html_content
    )

def send_welcome_email(user):
    """
    Send welcome email to new users
    
    Args:
        user: User object with email and username
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    dashboard_url = url_for('web.main.dashboard', _external=True)
    
    subject = "Welcome to NVC Banking Platform"
    html_content = f"""
    <html>
        <body>
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
                <h2 style="color: #4A6FFF;">Welcome to NVC Banking Platform!</h2>
                <p>Hello {user.username},</p>
                <p>Thank you for registering with NVC Banking Platform. We're excited to have you on board!</p>
                <p>With your new account, you can:</p>
                <ul>
                    <li>Process secure blockchain-based transactions</li>
                    <li>Connect with financial institutions</li>
                    <li>Use multiple payment gateways</li>
                    <li>Monitor your transactions in real-time</li>
                </ul>
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{dashboard_url}" style="background-color: #4A6FFF; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Go to Your Dashboard</a>
                </div>
                <p>If you have any questions, please don't hesitate to contact our support team.</p>
                <p>Regards,<br>The NVC Banking Platform Team</p>
            </div>
        </body>
    </html>
    """
    
    return send_email(
        to_email=user.email,
        subject=subject,
        html_content=html_content
    )

def send_invitation_email(invitation, invitation_url):
    """
    Send invitation email
    
    Args:
        invitation: Invitation object
        invitation_url: URL for accepting invitation
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    subject = f"You've been invited to join NVC Banking Platform by {invitation.invited_by_user.username}"
    
    html_content = f"""
    <html>
        <body>
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
                <h2 style="color: #4A6FFF;">You've Been Invited!</h2>
                <p>Hello,</p>
                <p>You have been invited to join the NVC Banking Platform by {invitation.invited_by_user.username} from {invitation.organization_name}.</p>
                
                {f"<p>Message from {invitation.invited_by_user.username}:</p><blockquote style='border-left: 3px solid #ddd; padding-left: 15px; margin-left: 10px; color: #555;'>{invitation.message}</blockquote>" if invitation.message else ""}
                
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{invitation_url}" style="background-color: #4A6FFF; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Accept Invitation</a>
                </div>
                <p>This invitation will expire in {invitation.expiration_days} days.</p>
                <p>Regards,<br>The NVC Banking Platform Team</p>
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #888;">
                    <p>If you're having trouble clicking the button, copy and paste this URL into your web browser:</p>
                    <p>{invitation_url}</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    return send_email(
        to_email=invitation.email,
        subject=subject,
        html_content=html_content
    )

def send_transaction_confirmation_email(user, transaction):
    """
    Send transaction confirmation email
    
    Args:
        user: User object with email and username
        transaction: Transaction object with details
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    transaction_url = url_for('web.main.transaction_details', transaction_id=transaction.transaction_id, _external=True)
    
    subject = f"Transaction Confirmation #{transaction.transaction_id}"
    
    # Format amount with currency symbol
    if transaction.currency == 'USD':
        formatted_amount = f"${transaction.amount:.2f}"
    elif transaction.currency == 'EUR':
        formatted_amount = f"€{transaction.amount:.2f}"
    elif transaction.currency == 'GBP':
        formatted_amount = f"£{transaction.amount:.2f}"
    else:
        formatted_amount = f"{transaction.amount:.2f} {transaction.currency}"
    
    # Get transaction type in a readable format
    transaction_type = transaction.transaction_type.name.replace('_', ' ').title()
    
    html_content = f"""
    <html>
        <body>
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; font-family: Arial, sans-serif;">
                <h2 style="color: #4A6FFF;">Transaction Confirmation</h2>
                <p>Hello {user.username},</p>
                <p>Your {transaction_type.lower()} transaction has been processed successfully:</p>
                
                <div style="background-color: #f8f9fa; border-radius: 5px; padding: 15px; margin: 20px 0;">
                    <p><strong>Transaction ID:</strong> {transaction.transaction_id}</p>
                    <p><strong>Type:</strong> {transaction_type}</p>
                    <p><strong>Amount:</strong> {formatted_amount}</p>
                    <p><strong>Date:</strong> {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Status:</strong> {transaction.status.name.replace('_', ' ').title()}</p>
                    
                    {f"<p><strong>Description:</strong> {transaction.description}</p>" if transaction.description else ""}
                    
                    {f"<p><strong>Blockchain Transaction Hash:</strong> {transaction.eth_transaction_hash}</p>" if transaction.eth_transaction_hash else ""}
                </div>
                
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{transaction_url}" style="background-color: #4A6FFF; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Transaction Details</a>
                </div>
                
                <p>If you did not authorize this transaction, please contact our support team immediately.</p>
                <p>Regards,<br>The NVC Banking Platform Team</p>
            </div>
        </body>
    </html>
    """
    
    return send_email(
        to_email=user.email,
        subject=subject,
        html_content=html_content
    )