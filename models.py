import enum
import json
from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    API = "api"

class PartnerType(enum.Enum):
    FINANCIAL_INSTITUTION = "Financial Institution"
    ASSET_MANAGER = "Asset Manager"
    BUSINESS_PARTNER = "Business Partner"

class IntegrationType(enum.Enum):
    API = "API"
    WEBHOOK = "Webhook"
    FILE_TRANSFER = "File Transfer"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.Enum(UserRole), default=UserRole.USER)
    api_key = db.Column(db.String(64), unique=True)
    ethereum_address = db.Column(db.String(64))
    ethereum_private_key = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # PHP banking integration fields
    external_customer_id = db.Column(db.String(64), index=True)
    external_account_id = db.Column(db.String(64), index=True)  
    external_account_type = db.Column(db.String(32))
    external_account_currency = db.Column(db.String(3))
    external_account_status = db.Column(db.String(16))
    last_sync = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class TransactionType(enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PAYMENT = "payment"
    SETTLEMENT = "settlement"
    LETTER_OF_CREDIT = "letter_of_credit"  # For SWIFT Letters of Credit (LC/SBLC)
    SWIFT_TRANSFER = "swift_transfer"      # For SWIFT MT103/MT202 fund transfers
    SWIFT_MESSAGE = "swift_message"        # For SWIFT MT799 and other free format messages

class GatewayType(enum.Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    BLOCKCHAIN = "blockchain"
    BANK_TRANSFER = "bank_transfer"
    XRP = "xrp"
    CUSTOM = "custom"

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="ETH")
    transaction_type = db.Column(db.Enum(TransactionType), nullable=False)
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    description = db.Column(db.String(256))
    eth_transaction_hash = db.Column(db.String(128))
    institution_id = db.Column(db.Integer, db.ForeignKey('financial_institution.id'))
    gateway_id = db.Column(db.Integer, db.ForeignKey('payment_gateway.id'))
    # PHP banking system integration
    external_id = db.Column(db.String(64), index=True) # To store external transaction IDs
    tx_metadata_json = db.Column(db.Text) # To store additional JSON data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))
    institution = db.relationship('FinancialInstitution', backref=db.backref('transactions', lazy=True))
    gateway = db.relationship('PaymentGateway', backref=db.backref('transactions', lazy=True))

class FinancialInstitutionType(enum.Enum):
    BANK = "bank"
    CREDIT_UNION = "credit_union"
    INVESTMENT_FIRM = "investment_firm"
    OTHER = "other"

class FinancialInstitution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    institution_type = db.Column(db.Enum(FinancialInstitutionType), nullable=False)
    api_endpoint = db.Column(db.String(256))
    api_key = db.Column(db.String(256))
    ethereum_address = db.Column(db.String(64))
    metadata_json = db.Column(db.Text)  # JSON metadata for various integrations (SWIFT, etc.)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaymentGatewayType(enum.Enum):
    """Payment gateway types
    
    Note: XRP_LEDGER is currently not in the database enum, but included here
    for future use. NVC_GLOBAL is in the database as 'nvc_global' (lowercase).
    """
    STRIPE = "stripe"
    PAYPAL = "paypal"
    SQUARE = "square"
    COINBASE = "coinbase"
    XRP_LEDGER = "xrp_ledger"
    # Very important: Using lowercase 'nvc_global' to match the database enum value exactly
    NVC_GLOBAL = "nvc_global"
    CUSTOM = "custom"
    
    @classmethod
    def from_string(cls, value: str):
        """Create enum from string, with extra handling for known special cases"""
        try:
            # Try direct conversion first
            return cls(value)
        except ValueError:
            # Handle specific cases - this shouldn't be needed now but kept for safety
            if value == 'nvc_global':
                return cls.NVC_GLOBAL
            # Add other special cases here if needed in the future
            raise

class PaymentGateway(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    gateway_type = db.Column(db.Enum(PaymentGatewayType), nullable=False)
    api_endpoint = db.Column(db.String(256))
    api_key = db.Column(db.String(256))
    webhook_secret = db.Column(db.String(256))
    ethereum_address = db.Column(db.String(64))
    # These columns might not exist in legacy databases
    # They are handled in payment_gateways.py
    # xrp_address = db.Column(db.String(64))
    # xrp_seed = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BlockchainAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    eth_address = db.Column(db.String(64), nullable=False)
    eth_private_key = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('blockchain_accounts', lazy=True))

class BlockchainTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    eth_tx_hash = db.Column(db.String(128), unique=True, nullable=False)
    from_address = db.Column(db.String(64), nullable=False)
    to_address = db.Column(db.String(64), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    contract_address = db.Column(db.String(64))
    transaction_type = db.Column(db.String(64), nullable=False)
    gas_used = db.Column(db.Integer)
    gas_price = db.Column(db.Float)
    block_number = db.Column(db.Integer)
    status = db.Column(db.String(64), default="pending")
    tx_metadata = db.Column(db.Text)  # Changed from 'metadata' which is reserved in SQLAlchemy
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('blockchain_transactions', lazy=True))
    
    # Optional link to a main application transaction
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    transaction = db.relationship('Transaction', backref=db.backref('blockchain_transactions', lazy=True))

class XRPLedgerTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    xrp_tx_hash = db.Column(db.String(128), unique=True, nullable=False)
    from_address = db.Column(db.String(64), nullable=False)
    to_address = db.Column(db.String(64), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(64), nullable=False)  # Payment, EscrowCreate, EscrowFinish, etc.
    ledger_index = db.Column(db.Integer)
    fee = db.Column(db.Float)
    destination_tag = db.Column(db.Integer)
    status = db.Column(db.String(64), default="pending")
    tx_metadata = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('xrp_transactions', lazy=True))
    
    # Optional link to a main application transaction
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    transaction = db.relationship('Transaction', backref=db.backref('xrp_transactions', lazy=True))

class SmartContract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    address = db.Column(db.String(64), unique=True, nullable=False)
    abi = db.Column(db.Text, nullable=False)
    bytecode = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AssetManager(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    integration_type = db.Column(db.Enum(IntegrationType), nullable=False)
    api_endpoint = db.Column(db.String(256))
    api_key = db.Column(db.String(256))
    webhook_url = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BusinessPartner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    integration_type = db.Column(db.Enum(IntegrationType), nullable=False)
    api_endpoint = db.Column(db.String(256))
    api_key = db.Column(db.String(256))
    webhook_url = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Webhook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(64), nullable=False)
    destination_url = db.Column(db.String(256), nullable=False)
    partner_id = db.Column(db.Integer)  # Can be from any partner type
    partner_type = db.Column(db.Enum(PartnerType))  # Type of partner this webhook is for
    secret = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"

class InvitationType(enum.Enum):
    CLIENT = "client"
    FINANCIAL_INSTITUTION = "financial_institution"
    ASSET_MANAGER = "asset_manager"
    BUSINESS_PARTNER = "business_partner"

class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invite_code = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    invitation_type = db.Column(db.Enum(InvitationType), nullable=False)
    status = db.Column(db.Enum(InvitationStatus), default=InvitationStatus.PENDING)
    invited_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organization_name = db.Column(db.String(128))
    message = db.Column(db.Text)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    accepted_at = db.Column(db.DateTime)
    
    # The user who created the invitation
    inviter = db.relationship('User', foreign_keys=[invited_by], backref=db.backref('sent_invitations', lazy=True))
    
    def is_expired(self):
        """Check if the invitation has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Check if the invitation is valid (not expired, not accepted, not revoked)"""
        return self.status == InvitationStatus.PENDING and not self.is_expired()

class FormData(db.Model):
    """
    Temporary storage for form data to allow recovery after errors
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_id = db.Column(db.String(64), nullable=False, index=True)
    form_type = db.Column(db.String(64), nullable=False)  # e.g., 'bank_transfer'
    form_data = db.Column(db.Text, nullable=False)  # JSON serialized form data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    user = db.relationship('User', backref=db.backref('form_data', lazy=True))
    
    @classmethod
    def create_from_form(cls, user_id, transaction_id, form_type, form_data, expiry_hours=24):
        """
        Create a new FormData entry from a form object
        
        Args:
            user_id (int): The user ID
            transaction_id (str): The transaction ID
            form_type (str): The type of form
            form_data (dict): The form data
            expiry_hours (int): Hours until this data expires
            
        Returns:
            FormData: The created FormData object
        """
        # Convert form data to JSON
        form_data_json = json.dumps(form_data)
        
        # Set expiry time
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        # Check if we already have a form for this transaction
        existing = cls.query.filter_by(
            transaction_id=transaction_id,
            form_type=form_type
        ).first()
        
        if existing:
            # Update existing record
            existing.form_data = form_data_json
            existing.expires_at = expires_at
            existing.created_at = datetime.utcnow()
            return existing
        
        # Create new record
        form_data_obj = cls(
            user_id=user_id,
            transaction_id=transaction_id,
            form_type=form_type,
            form_data=form_data_json,
            expires_at=expires_at
        )
        
        db.session.add(form_data_obj)
        return form_data_obj
    
    @classmethod
    def get_for_transaction(cls, transaction_id, form_type):
        """
        Get form data for a transaction
        
        Args:
            transaction_id (str): The transaction ID
            form_type (str): The type of form
            
        Returns:
            dict: The form data, or None if not found
        """
        # Find the most recent form data for this transaction
        form_data = cls.query.filter_by(
            transaction_id=transaction_id,
            form_type=form_type
        ).filter(
            cls.expires_at > datetime.utcnow()
        ).order_by(cls.created_at.desc()).first()
        
        if not form_data:
            return None
        
        # Parse JSON
        try:
            return json.loads(form_data.form_data)
        except json.JSONDecodeError:
            return None
    
    @classmethod
    def cleanup_expired(cls):
        """Remove all expired form data"""
        expired = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        for item in expired:
            db.session.delete(item)
        db.session.commit()
