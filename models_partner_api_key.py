import enum
import secrets
from datetime import datetime

from app import db

class PartnerApiKeyAccessLevel(enum.Enum):
    """Access levels for partner API keys"""
    READ = "read"
    READ_WRITE = "read_write"
    FULL = "full"


class PartnerApiKeyType(enum.Enum):
    """Types of partners who can use API keys"""
    FINANCIAL_INSTITUTION = "financial_institution"
    TOKEN_PROVIDER = "token_provider" 
    PAYMENT_PROCESSOR = "payment_processor"
    DATA_PROVIDER = "data_provider"
    OTHER = "other"


class PartnerApiKey(db.Model):
    """API keys for partner institutions like Saint Crowm Bank"""
    id = db.Column(db.Integer, primary_key=True)
    partner_name = db.Column(db.String(128), nullable=False)
    partner_email = db.Column(db.String(128), nullable=False)
    partner_type = db.Column(db.Enum(PartnerApiKeyType), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    access_level = db.Column(db.Enum(PartnerApiKeyAccessLevel), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    last_used = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def generate_api_key(cls) -> str:
        """Generate a secure API key for partner institutions"""
        return f"nvc_partner_{secrets.token_urlsafe(32)}"
    
    @classmethod
    def create_for_saint_crowm_bank(cls):
        """Create a default API key for Saint Crowm Bank if it doesn't exist"""
        # Check if Saint Crowm Bank already has an API key
        existing = cls.query.filter_by(partner_name="Saint Crowm Bank").first()
        if existing:
            return existing
            
        # Generate a new API key
        api_key = cls.generate_api_key()
        
        # Create the API key record
        partner_key = cls(
            partner_name="Saint Crowm Bank",
            partner_email="api@saintcrowmbank.com",
            partner_type=PartnerApiKeyType.TOKEN_PROVIDER,
            api_key=api_key,
            access_level=PartnerApiKeyAccessLevel.FULL,
            description="Official API integration for Saint Crowm Bank as the operators of AFD1 token",
            is_active=True
        )
        
        db.session.add(partner_key)
        db.session.commit()
        
        return partner_key