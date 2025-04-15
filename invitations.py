"""
Invitation management module for NVC Banking Platform
Handles the creation, sending, and management of invitations to clients, 
financial institutions, asset managers, and business partners.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any, Union

from flask import url_for, current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import Invitation, InvitationStatus, InvitationType, User, UserRole, FinancialInstitution, FinancialInstitutionType, AssetManager, BusinessPartner, IntegrationType

# Setup logging
logger = logging.getLogger(__name__)

def generate_invite_code() -> str:
    """Generate a unique invitation code"""
    return str(uuid.uuid4())

def create_invitation(
    email: str, 
    invitation_type: InvitationType, 
    invited_by: int, 
    organization_name: str, 
    message: Optional[str] = None,
    expiration_days: int = 14
) -> Tuple[Optional[Invitation], Optional[str]]:
    """
    Create a new invitation
    
    Args:
        email: Email address of the invitee
        invitation_type: Type of invitation (CLIENT, FINANCIAL_INSTITUTION, etc.)
        invited_by: User ID of the inviter
        organization_name: Name of the organization
        message: Optional personal message
        expiration_days: Number of days until the invitation expires
        
    Returns:
        Tuple of (Invitation, error_message)
    """
    try:
        # Check if a valid invitation already exists
        existing_invitation = Invitation.query.filter_by(
            email=email, 
            status=InvitationStatus.PENDING
        ).first()
        
        if existing_invitation and existing_invitation.is_valid():
            return None, "A pending invitation already exists for this email."
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return None, "A user with this email already exists."
        
        # Create new invitation
        invitation = Invitation(
            invite_code=generate_invite_code(),
            email=email,
            invitation_type=invitation_type,
            invited_by=invited_by,
            organization_name=organization_name,
            message=message,
            expires_at=datetime.utcnow() + timedelta(days=expiration_days),
            status=InvitationStatus.PENDING
        )
        
        db.session.add(invitation)
        db.session.commit()
        
        return invitation, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating invitation: {str(e)}")
        return None, "Database error creating invitation."
    except Exception as e:
        logger.error(f"Unexpected error creating invitation: {str(e)}")
        return None, "An unexpected error occurred."

def get_invitation_by_code(invite_code: str) -> Optional[Invitation]:
    """Get an invitation by its unique code"""
    return Invitation.query.filter_by(invite_code=invite_code).first()

def accept_invitation(invite_code: str, user: User) -> Tuple[bool, Optional[str]]:
    """
    Process the acceptance of an invitation
    
    Args:
        invite_code: The unique invitation code
        user: The newly created user
        
    Returns:
        Tuple of (success, error_message)
    """
    invitation = get_invitation_by_code(invite_code)
    
    if not invitation:
        return False, "Invalid invitation code."
    
    if not invitation.is_valid():
        if invitation.status == InvitationStatus.EXPIRED or invitation.is_expired():
            return False, "This invitation has expired."
        elif invitation.status == InvitationStatus.ACCEPTED:
            return False, "This invitation has already been accepted."
        elif invitation.status == InvitationStatus.REVOKED:
            return False, "This invitation has been revoked."
        else:
            return False, "This invitation is no longer valid."
    
    try:
        # Handle the specific type of invitation
        if invitation.invitation_type == InvitationType.FINANCIAL_INSTITUTION:
            # Create financial institution
            institution = FinancialInstitution(
                name=invitation.organization_name,
                institution_type=FinancialInstitutionType.OTHER,  # Default to OTHER, can be updated later
                is_active=True
            )
            db.session.add(institution)
        
        elif invitation.invitation_type == InvitationType.ASSET_MANAGER:
            # Create asset manager
            asset_manager = AssetManager(
                name=invitation.organization_name,
                integration_type=IntegrationType.API,  # Default to API, can be updated later
                is_active=True
            )
            db.session.add(asset_manager)
        
        elif invitation.invitation_type == InvitationType.BUSINESS_PARTNER:
            # Create business partner
            business_partner = BusinessPartner(
                name=invitation.organization_name,
                integration_type=IntegrationType.API,  # Default to API, can be updated later
                is_active=True
            )
            db.session.add(business_partner)
        
        # Update invitation status
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.utcnow()
        
        db.session.commit()
        return True, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error accepting invitation: {str(e)}")
        return False, "Database error accepting invitation."
    except Exception as e:
        logger.error(f"Unexpected error accepting invitation: {str(e)}")
        return False, "An unexpected error occurred."

def revoke_invitation(invite_id: int, admin_user_id: int) -> Tuple[bool, Optional[str]]:
    """
    Revoke an invitation
    
    Args:
        invite_id: ID of the invitation to revoke
        admin_user_id: ID of the admin user revoking the invitation
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        invitation = Invitation.query.get(invite_id)
        
        if not invitation:
            return False, "Invitation not found."
        
        if invitation.status != InvitationStatus.PENDING:
            if invitation.status == InvitationStatus.ACCEPTED:
                return False, "This invitation has already been accepted and cannot be revoked."
            elif invitation.status == InvitationStatus.REVOKED:
                return False, "This invitation has already been revoked."
            elif invitation.status == InvitationStatus.EXPIRED:
                return False, "This invitation has already expired."
        
        invitation.status = InvitationStatus.REVOKED
        db.session.commit()
        
        return True, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error revoking invitation: {str(e)}")
        return False, "Database error revoking invitation."
    except Exception as e:
        logger.error(f"Unexpected error revoking invitation: {str(e)}")
        return False, "An unexpected error occurred."

def resend_invitation(invite_id: int, admin_user_id: int) -> Tuple[bool, Optional[str], Optional[Invitation]]:
    """
    Resend an invitation by creating a new one with the same details
    
    Args:
        invite_id: ID of the original invitation
        admin_user_id: ID of the admin user resending the invitation
        
    Returns:
        Tuple of (success, error_message, new_invitation)
    """
    try:
        original_invitation = Invitation.query.get(invite_id)
        
        if not original_invitation:
            return False, "Invitation not found.", None
        
        # Create a new invitation with the same details
        new_invitation, error = create_invitation(
            email=original_invitation.email,
            invitation_type=original_invitation.invitation_type,
            invited_by=admin_user_id,
            organization_name=original_invitation.organization_name,
            message=original_invitation.message,
            expiration_days=14  # Default to 14 days
        )
        
        if error:
            return False, error, None
        
        # If the original invitation is still pending, mark it as revoked
        if original_invitation.status == InvitationStatus.PENDING:
            original_invitation.status = InvitationStatus.REVOKED
            db.session.commit()
        
        return True, None, new_invitation
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error resending invitation: {str(e)}")
        return False, "Database error resending invitation.", None
    except Exception as e:
        logger.error(f"Unexpected error resending invitation: {str(e)}")
        return False, "An unexpected error occurred.", None

def get_invitation_url(invitation: Invitation) -> str:
    """Generate the full URL for an invitation"""
    return url_for('register_with_invitation', invite_code=invitation.invite_code, _external=True)

def get_all_invitations(status_filter: Optional[InvitationStatus] = None, 
                        type_filter: Optional[InvitationType] = None,
                        page: int = 1, 
                        per_page: int = 20) -> Dict[str, Any]:
    """
    Get all invitations with optional filtering
    
    Args:
        status_filter: Filter by invitation status
        type_filter: Filter by invitation type
        page: Page number for pagination
        per_page: Results per page
        
    Returns:
        Dictionary with pagination information and results
    """
    query = Invitation.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if type_filter:
        query = query.filter_by(invitation_type=type_filter)
    
    # Order by creation date (newest first)
    query = query.order_by(Invitation.created_at.desc())
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page)
    
    return {
        'invitations': pagination.items,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'next_page': page + 1 if pagination.has_next else None,
        'prev_page': page - 1 if pagination.has_prev else None
    }

def send_invitation_email(invitation: Invitation) -> bool:
    """
    Send an invitation email to the invitee
    
    Args:
        invitation: The invitation to send
        
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Import here to avoid circular imports
        from utils import send_email
        
        invite_url = get_invitation_url(invitation)
        
        # Get inviter name
        inviter = User.query.get(invitation.invited_by)
        inviter_name = inviter.username if inviter else "The NVC Platform Team"
        
        # Customize subject based on invitation type
        invitation_type_name = invitation.invitation_type.value.replace('_', ' ').title()
        subject = f"Invitation to Join NVC Platform as a {invitation_type_name}"
        
        # Create HTML email content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4a6da7; color: white; padding: 15px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .footer {{ text-align: center; padding: 10px; font-size: 12px; color: #777; }}
                .button {{ display: inline-block; background-color: #4a6da7; color: white; text-decoration: none; padding: 10px 20px; border-radius: 4px; margin-top: 15px; }}
                .message {{ background-color: #eef2f7; padding: 15px; margin: 15px 0; border-left: 4px solid #4a6da7; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>NVC Platform Invitation</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>You have been invited by <strong>{inviter_name}</strong> to join the NVC Banking Platform as a <strong>{invitation_type_name}</strong> for <strong>{invitation.organization_name}</strong>.</p>
                    
                    {f'<div class="message"><p>"{invitation.message}"</p></div>' if invitation.message else ''}
                    
                    <p>The NVC Platform provides secure, blockchain-based payment and settlement solutions connecting financial institutions worldwide.</p>
                    
                    <p>Your invitation is valid until <strong>{invitation.expires_at.strftime('%B %d, %Y')}</strong>.</p>
                    
                    <p style="text-align: center;">
                        <a href="{invite_url}" class="button">Accept Invitation</a>
                    </p>
                    
                    <p>If the button above doesn't work, copy and paste the following URL into your browser:</p>
                    <p style="word-break: break-all;">{invite_url}</p>
                </div>
                <div class="footer">
                    <p>If you did not expect this invitation, you can safely ignore this email.</p>
                    <p>&copy; 2025 NVC Banking Platform. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version as fallback
        text_content = f"""
        Hello,
        
        You have been invited by {inviter_name} to join the NVC Banking Platform as a {invitation_type_name} for {invitation.organization_name}.
        
        {f'Personal message: "{invitation.message}"' if invitation.message else ''}
        
        The NVC Platform provides secure, blockchain-based payment and settlement solutions connecting financial institutions worldwide.
        
        Your invitation is valid until {invitation.expires_at.strftime('%B %d, %Y')}.
        
        To accept this invitation, please visit:
        {invite_url}
        
        If you did not expect this invitation, you can safely ignore this email.
        
        © 2025 NVC Banking Platform. All rights reserved.
        """
        
        # Send the email
        return send_email(
            to_email=invitation.email,
            from_email="invitations@nvcplatform.net",
            subject=subject,
            text_content=text_content,
            html_content=html_content
        )
    
    except Exception as e:
        logger.error(f"Error sending invitation email: {str(e)}")
        return False