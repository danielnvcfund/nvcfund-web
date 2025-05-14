import enum
import json
import secrets
from datetime import datetime, timedelta, date
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.hybrid import hybrid_property

# Import account holder models
try:
    from account_holder_models import (
        AccountHolder, Address, PhoneNumber, BankAccount,
        AccountType, AccountStatus, CurrencyType
    )
except ImportError:
    # Models will be imported when the module is available
    pass

class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    API = "api"
    DEVELOPER = "developer"

class PartnerType(enum.Enum):
    FINANCIAL_INSTITUTION = "Financial Institution"
    ASSET_MANAGER = "Asset Manager"
    BUSINESS_PARTNER = "Business Partner"
    CORRESPONDENT_BANK = "Correspondent Bank"
    SETTLEMENT_PARTNER = "Settlement Partner"
    STABLECOIN_ISSUER = "Stablecoin Issuer"
    INDUSTRIAL_BANK = "Industrial Bank"

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

    # Personal information fields
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    organization = db.Column(db.String(150))
    country = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    newsletter = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)

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
        
    @property
    def full_name(self):
        """Return the user's full name or username if not available"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

class TransactionStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    SCHEDULED = "SCHEDULED"  # For future-scheduled transactions

class TransactionType(enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER = "TRANSFER"
    PAYMENT = "PAYMENT"
    PAYOUT = "PAYOUT"                                 # For PayPal payout transactions
    SETTLEMENT = "SETTLEMENT"
    PAYMENT_SETTLEMENT = "PAYMENT_SETTLEMENT"          # For settlements from payment processors to treasury accounts
    SWIFT_LETTER_OF_CREDIT = "SWIFT_LETTER_OF_CREDIT"  # For SWIFT MT760 Letters of Credit
    SWIFT_FUND_TRANSFER = "SWIFT_FUND_TRANSFER"        # For SWIFT MT103 customer fund transfers
    SWIFT_INSTITUTION_TRANSFER = "SWIFT_INSTITUTION_TRANSFER"  # For SWIFT MT202 financial institution transfers
    SWIFT_FREE_FORMAT = "SWIFT_FREE_FORMAT"            # For SWIFT MT799 free format messages
    SWIFT_TRANSFER = "SWIFT_TRANSFER"                  # General SWIFT transfer (legacy)
    SWIFT_GPI_PAYMENT = "SWIFT_GPI_PAYMENT"            # For SWIFT GPI payment messages
    SWIFT_GPI_NOTIFICATION = "SWIFT_GPI_NOTIFICATION"  # For SWIFT GPI status notifications
    INTERNATIONAL_WIRE = "INTERNATIONAL_WIRE"          # For international wire transfers 
    RTGS_TRANSFER = "RTGS_TRANSFER"                   # For Real-Time Gross Settlement transfers
    SERVER_TO_SERVER = "SERVER_TO_SERVER"             # For direct server-to-server transfers
    OFF_LEDGER_TRANSFER = "OFF_LEDGER_TRANSFER"        # For general off-ledger transfers
    TOKEN_EXCHANGE = "TOKEN_EXCHANGE"                  # For AFD1-NVCT token exchange transactions
    EDI_PAYMENT = "EDI_PAYMENT"                        # For Electronic Data Interchange payments
    POS_PAYMENT = "POS_PAYMENT"                        # For Point of Sale payment transactions
    EDI_ACH_TRANSFER = "EDI_ACH_TRANSFER"              # For ACH transfers via EDI
    EDI_WIRE_TRANSFER = "EDI_WIRE_TRANSFER"            # For wire transfers via EDI
    TREASURY_TRANSFER = "TREASURY_TRANSFER"            # For treasury management transfers
    TREASURY_INVESTMENT = "TREASURY_INVESTMENT"        # For treasury investments
    TREASURY_LOAN = "TREASURY_LOAN"                    # For treasury loans
    TREASURY_DEBT_REPAYMENT = "TREASURY_DEBT_REPAYMENT"  # For treasury debt repayments
    SALARY_PAYMENT = "SALARY_PAYMENT"                  # For salary payments to employees
    BILL_PAYMENT = "BILL_PAYMENT"                      # For bill payments to service providers
    CONTRACT_PAYMENT = "CONTRACT_PAYMENT"              # For payments to contractors/vendors under contracts
    BULK_PAYROLL = "BULK_PAYROLL"                      # For processing multiple salary payments at once
    SWIFT_DELIVER_AGAINST_PAYMENT = "SWIFT_DELIVER_AGAINST_PAYMENT" # Added SWIFT MT542
    STABLECOIN_TRANSFER = "STABLECOIN_TRANSFER"        # For NVC Token Stablecoin transfers
    P2P_LEDGER_TRANSFER = "P2P_LEDGER_TRANSFER"        # For Peer-to-Peer ledger transfers
    CORRESPONDENT_SETTLEMENT = "CORRESPONDENT_SETTLEMENT" # For settlements with correspondent banks
    CRYPTO_PAYMENT = "CRYPTO_PAYMENT"                  # For cryptocurrency payments (BTC, ETH, etc.)
    CRYPTO_TRANSFER = "CRYPTO_TRANSFER"                # For cryptocurrency transfers between wallets
    CRYPTO_EXCHANGE = "CRYPTO_EXCHANGE"                # For cryptocurrency exchange transactions
    NVCT_PAYMENT = "NVCT_PAYMENT"                      # For NVC Token specific payments
    AFD1_PAYMENT = "AFD1_PAYMENT"                      # For American Federation Dollar payments


class PaymentMethod(enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    ACH = "ach"
    WIRE = "wire"
    CRYPTOCURRENCY = "cryptocurrency"
    NVCT = "nvct"
    PAYPAL = "paypal"
    SWIFT = "swift"
    RTGS = "rtgs"
    EDI = "edi"
    CASH = "cash"
    CHECK = "check"
    MONEY_ORDER = "money_order"
    STRIPE = "stripe"
    
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

    # Recipient information
    recipient_name = db.Column(db.String(128))
    recipient_institution = db.Column(db.String(128))
    recipient_account = db.Column(db.String(64))
    recipient_address = db.Column(db.String(256))
    recipient_country = db.Column(db.String(64))
    recipient_bank = db.Column(db.String(128))  # Name of the recipient's bank (for RTGS transfers)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('transactions', lazy=True))
    institution = db.relationship('FinancialInstitution', backref=db.backref('transactions', lazy=True))
    gateway = db.relationship('PaymentGateway', backref=db.backref('transactions', lazy=True))

    def get_recipient_details(self):
        """Extract recipient details from either dedicated fields or description"""
        if self.recipient_name:
            return {
                'name': self.recipient_name,
                'institution': self.recipient_institution,
                'account': self.recipient_account,
                'address': self.recipient_address,
                'country': self.recipient_country,
                'bank': self.recipient_bank
            }

        # Legacy extraction from description
        details = {}
        if self.description:
            if ',' in self.description:
                details['name'] = self.description.split(',')[0].strip()
            else:
                details['name'] = self.description

            if 'Account:' in self.description:
                details['account'] = self.description.split('Account:')[1].strip()

        return details

class FinancialInstitutionType(enum.Enum):
    BANK = "bank"
    CREDIT_UNION = "credit_union"
    INVESTMENT_FIRM = "investment_firm"
    CENTRAL_BANK = "central_bank"
    GOVERNMENT = "government"
    OTHER = "other"

class FinancialInstitution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    institution_type = db.Column(db.Enum(FinancialInstitutionType), nullable=False)
    api_endpoint = db.Column(db.String(256))
    api_key = db.Column(db.String(256))
    ethereum_address = db.Column(db.String(64))
    swift_code = db.Column(db.String(11))  # SWIFT/BIC code for the institution
    ach_routing_number = db.Column(db.String(9))  # ACH routing number (ABA RTN) for US institutions
    account_number = db.Column(db.String(64))  # Main account number for the institution
    metadata_json = db.Column(db.Text)  # JSON metadata for various integrations (SWIFT, etc.)
    is_active = db.Column(db.Boolean, default=True)
    # Off-ledger transaction capabilities
    rtgs_enabled = db.Column(db.Boolean, default=False)  # Whether the institution supports RTGS
    s2s_enabled = db.Column(db.Boolean, default=False)   # Whether the institution supports server-to-server transfers
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaymentGatewayType(enum.Enum):
    """Payment gateway types

    Note: XRP_LEDGER is currently not in the database enum, but included here
    for future use. NVC_GLOBAL is in the database as 'nvc_global' (lowercase).
    """
    STRIPE = "stripe"
    PAYPAL = "paypal"
    # Adding additional gateway types as needed
    # Commented out gateway types that aren't in the current database enum
    # SQUARE = "square"
    # COINBASE = "coinbase"
    # XRP_LEDGER = "xrp_ledger"
    # Very important: Using lowercase 'nvc_global' to match the database enum value exactly
    NVC_GLOBAL = "nvc_global"
    CUSTOM = "custom"  # Added CUSTOM type to support existing database entries
    
class TelexMessageStatus(enum.Enum):
    """Telex message status"""
    DRAFT = "DRAFT"
    SENT = "SENT"
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    
class TelexMessage(db.Model):
    """Model for KTT Telex messages"""
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(64), unique=True, nullable=False)
    sender_reference = db.Column(db.String(64), index=True)
    recipient_bic = db.Column(db.String(11), index=True)  # BIC/SWIFT code
    message_type = db.Column(db.String(10), nullable=False)  # FT, FTC, PO, etc.
    message_content = db.Column(db.Text, nullable=False)  # JSON content
    priority = db.Column(db.String(10), default="NORMAL")  # HIGH, NORMAL, LOW
    transaction_id = db.Column(db.String(64), db.ForeignKey('transaction.transaction_id'), nullable=True)
    status = db.Column(db.Enum(TelexMessageStatus), default=TelexMessageStatus.DRAFT)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    received_at = db.Column(db.DateTime, nullable=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with transactions
    transaction = db.relationship('Transaction', backref=db.backref('telex_messages', lazy=True))

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

class AssetType(enum.Enum):
    """Asset types"""
    CASH = "CASH"
    TREASURY_BOND = "TREASURY_BOND"
    CORPORATE_BOND = "CORPORATE_BOND"
    SOVEREIGN_BOND = "SOVEREIGN_BOND"
    EQUITY = "EQUITY"
    REAL_ESTATE = "REAL_ESTATE"
    COMMODITY = "COMMODITY"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    LOAN = "LOAN"
    COLLATERALIZED_DEBT = "COLLATERALIZED_DEBT"
    OTHER = "OTHER"

class Asset(db.Model):
    """Model for assets under management"""
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    asset_type = db.Column(db.Enum(AssetType), nullable=False)
    value = db.Column(db.Numeric(20, 2), nullable=False)  # Numeric for precise financial values
    currency = db.Column(db.String(3), default="USD")
    location = db.Column(db.String(256))
    custodian = db.Column(db.String(256))
    managing_institution_id = db.Column(db.Integer, db.ForeignKey('financial_institution.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    verification_date = db.Column(db.DateTime, nullable=True)
    last_valuation_date = db.Column(db.DateTime, nullable=True)
    last_verified_date = db.Column(db.DateTime, nullable=True)
    documentation_url = db.Column(db.String(512))
    metadata_json = db.Column(db.Text)  # Additional metadata as JSON
    afd1_liquidity_pool_status = db.Column(db.String(32), default="INACTIVE")  # ACTIVE, INACTIVE, PENDING
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    managing_institution = db.relationship('FinancialInstitution', backref=db.backref('managed_assets', lazy=True))

class AssetReporting(db.Model):
    """Model for asset reporting and verification records"""
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(64), db.ForeignKey('asset.asset_id'), nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey('financial_institution.id'), nullable=True)
    report_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    report_type = db.Column(db.String(64), nullable=False)  # VALUATION, VERIFICATION, AUDIT, etc.
    report_status = db.Column(db.String(32), default="PENDING")  # PENDING, COMPLETED, REJECTED

class BlockchainNetwork(enum.Enum):
    """Blockchain networks supported by the platform"""
    MAINNET = "mainnet"
    TESTNET = "testnet"  # Sepolia testnet

class BlockchainTransactionType(enum.Enum):
    """Types of blockchain transactions"""
    TOKEN_TRANSFER = "token_transfer"
    CONTRACT_DEPLOY = "contract_deploy"
    CONTRACT_CALL = "contract_call"
    ETH_TRANSFER = "eth_transfer"
    OTHER = "other"

class SmartContractType(enum.Enum):
    """Types of smart contracts used in the platform"""
    NVC_TOKEN = "nvc_token"
    SETTLEMENT_CONTRACT = "settlement_contract"
    MULTISIG_WALLET = "multisig_wallet"
    STAKING_CONTRACT = "staking_contract"
    OTHER = "other"

class SmartContract(db.Model):
    """Smart contract model for storing contract addresses and ABIs"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    address = db.Column(db.String(42))
    is_active = db.Column(db.Boolean, default=True)
    abi = db.Column(db.Text)  # JSON string of contract ABI
    bytecode = db.Column(db.Text)  # Contract bytecode
    description = db.Column(db.Text)  # Description of contract
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SmartContract {self.name}:{self.address}>"

class BlockchainTransaction(db.Model):
    """Blockchain transaction model for tracking transactions"""
    __tablename__ = 'blockchain_transaction'
    
    # Define columns exactly as they appear in the database
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer)
    amount = db.Column(db.Float)
    gas_used = db.Column(db.Integer)
    gas_price = db.Column(db.Integer)  # In wei
    block_number = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.Integer)  # 1 for success, 0 for failure, NULL for pending
    eth_tx_hash = db.Column(db.String(66), unique=True, nullable=True)  # Legacy column
    from_address = db.Column(db.String(42))
    to_address = db.Column(db.String(42))
    transaction_type = db.Column(db.String(50))
    tx_metadata = db.Column(db.Text)  # JSON data
    tx_hash = db.Column(db.String(66), unique=True, nullable=True)
    contract_address = db.Column(db.String(42))
    
    # No recorded_by column - it was removed from the database
    
    def __init__(self, **kwargs):
        """
        Initialize a new BlockchainTransaction
        
        Handle backward compatibility with eth_tx_hash parameter
        """
        # Handle eth_tx_hash parameter for backward compatibility
        if 'eth_tx_hash' in kwargs and 'tx_hash' not in kwargs:
            kwargs['tx_hash'] = kwargs.pop('eth_tx_hash')
        
        # Initialize with processed kwargs
        super(BlockchainTransaction, self).__init__(**kwargs)
    
    def __repr__(self):
        """String representation of this model"""
        tx_str = self.tx_hash if self.tx_hash else "Unknown"
        tx_type = self.transaction_type if self.transaction_type else "Unknown Type"
        return f"<BlockchainTransaction {tx_str} - {tx_type}>"

class SecurityOperation(db.Model):
    """Security operation model for tracking sensitive mainnet operations"""
    id = db.Column(db.Integer, primary_key=True)
    operation_id = db.Column(db.String(36), unique=True, nullable=False)  # UUID
    operation_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, completed, failed, cancelled
    
    # Operation details
    from_address = db.Column(db.String(42))
    to_address = db.Column(db.String(42))
    contract_address = db.Column(db.String(42))
    value = db.Column(db.Float)
    currency = db.Column(db.String(10))
    gas_estimate = db.Column(db.Integer)
    gas_price = db.Column(db.Integer)
    is_high_risk = db.Column(db.Boolean, default=False)
    
    # For contract operations
    contract_type = db.Column(db.String(50))
    function_name = db.Column(db.String(100))
    function_args = db.Column(db.Text)  # JSON string
    
    # Security
    security_code = db.Column(db.String(10))
    security_code_expires_at = db.Column(db.DateTime)
    verified_at = db.Column(db.DateTime)
    verified_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    verified_by_ip = db.Column(db.String(45))
    
    # Result
    result_tx_hash = db.Column(db.String(66))
    error = db.Column(db.Text)
    
    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by_ip = db.Column(db.String(45))
    
    # Relationships
    verified_by_user = db.relationship('User', foreign_keys=[verified_by_user_id])
    created_by_user = db.relationship('User', foreign_keys=[created_by_user_id])

class LiquidityPool(db.Model):
    """Model for liquidity pools like AFD1"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    code = db.Column(db.String(32), unique=True, nullable=False)  # Like "AFD1"
    description = db.Column(db.Text)
    manager_institution_id = db.Column(db.Integer, db.ForeignKey('financial_institution.id'), nullable=True)
    total_value = db.Column(db.Numeric(24, 2))  # Total value of assets in the pool
    currency = db.Column(db.String(3), default="USD")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    manager_institution = db.relationship('FinancialInstitution', backref=db.backref('managed_liquidity_pools', lazy=True))

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
    
class StablecoinAccount(db.Model):
    """Account for NVC Token Stablecoin within the closed-loop system"""
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default="NVCT")
    is_active = db.Column(db.Boolean, default=True)
    account_type = db.Column(db.String(20), default="INDIVIDUAL")  # INDIVIDUAL, BUSINESS, INSTITUTION, PARTNER
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('stablecoin_accounts', lazy=True))
    
    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balance += amount
        self.updated_at = datetime.utcnow()
        
    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount
        self.updated_at = datetime.utcnow()
        
    def transfer(self, destination_account, amount, description=None):
        """Transfer stablecoins to another account"""
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient funds")
            
        self.withdraw(amount)
        destination_account.deposit(amount)
        
        # Create transfer transaction record
        from app import db
        transaction_id = secrets.token_hex(16)
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=self.user_id,
            amount=amount,
            currency=self.currency,
            transaction_type=TransactionType.STABLECOIN_TRANSFER,
            status=TransactionStatus.COMPLETED,
            description=description or f"Transfer to {destination_account.account_number}",
            recipient_name=f"Account: {destination_account.account_number}",
            recipient_account=destination_account.account_number
        )
        db.session.add(transaction)
        
        # Create ledger entries
        debit_entry = LedgerEntry(
            transaction_id=transaction_id,
            account_id=self.id,
            entry_type='DEBIT',
            amount=amount,
            description=f"Transfer to {destination_account.account_number}"
        )
        db.session.add(debit_entry)
        
        credit_entry = LedgerEntry(
            transaction_id=transaction_id,
            account_id=destination_account.id,
            entry_type='CREDIT',
            amount=amount,
            description=f"Transfer from {self.account_number}"
        )
        db.session.add(credit_entry)
        
        return transaction
    
class CorrespondentBank(db.Model):
    """Model for correspondent banks in the closed-loop system"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    bank_code = db.Column(db.String(20), unique=True, nullable=False)
    swift_code = db.Column(db.String(11))
    ach_routing_number = db.Column(db.String(9))
    clearing_account_number = db.Column(db.String(64))
    stablecoin_account_id = db.Column(db.Integer, db.ForeignKey('stablecoin_account.id'))
    settlement_threshold = db.Column(db.Float, default=10000.0)  # Threshold for settlement with external system
    settlement_fee_percentage = db.Column(db.Float, default=0.5)  # Fee percentage for settlement
    is_active = db.Column(db.Boolean, default=True)
    supports_ach = db.Column(db.Boolean, default=False)
    supports_swift = db.Column(db.Boolean, default=False)
    supports_wire = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    stablecoin_account = db.relationship('StablecoinAccount', backref=db.backref('correspondent_bank', uselist=False))
    wire_transfers = db.relationship('WireTransfer', backref='correspondent_bank', lazy=True)
    
class WireTransferStatus(enum.Enum):
    """Status for wire transfers"""
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
# Wire Transfer model moved to line ~1693
    
class LedgerEntry(db.Model):
    """Double-entry accounting ledger for the closed-loop system"""
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(64), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('stablecoin_account.id'), nullable=False)
    entry_type = db.Column(db.String(10), nullable=False)  # DEBIT or CREDIT
    amount = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float)  # Running balance after this entry
    description = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    account = db.relationship('StablecoinAccount', backref=db.backref('ledger_entries', lazy=True))
    
class SettlementBatch(db.Model):
    """Model for batched settlements with correspondent banks"""
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String(64), unique=True, nullable=False)
    correspondent_bank_id = db.Column(db.Integer, db.ForeignKey('correspondent_bank.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    fee_amount = db.Column(db.Float, nullable=False)
    net_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="USD")
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    settlement_method = db.Column(db.String(20))  # ACH, SWIFT, WIRE
    external_reference = db.Column(db.String(64))  # Reference from external system
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    correspondent_bank = db.relationship('CorrespondentBank', backref=db.backref('settlement_batches', lazy=True))

class SwiftMessageStatus(enum.Enum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    RECONCILED = "RECONCILED"
    FAILED = "FAILED"
    PENDING = "PENDING"

class SwiftMessage(db.Model):
    """Model for storing SWIFT messages imported from various sources including GPI"""
    id = db.Column(db.Integer, primary_key=True)
    message_type = db.Column(db.String(10), nullable=False)  # 103, 202, 760, etc.
    sender_bic = db.Column(db.String(15), nullable=False)
    receiver_bic = db.Column(db.String(15), nullable=False)
    reference = db.Column(db.String(35), nullable=False, index=True)
    related_reference = db.Column(db.String(35))
    amount = db.Column(db.Float)
    currency = db.Column(db.String(3))
    value_date = db.Column(db.Date)
    message_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="RECEIVED", index=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    file_source = db.Column(db.String(255))
    source_type = db.Column(db.String(50), default="MANUAL_UPLOAD")  # MANUAL_UPLOAD, API, SFTP, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to the user who uploaded the message
    user = db.relationship('User', backref=db.backref('swift_messages', lazy=True))

# BlockchainTransaction model is already defined above
# Legacy model has been replaced with the new one that supports mainnet/testnet

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

# SmartContract model is already defined above
# Legacy model has been replaced with the new one that supports contract types and networks

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

class ApiAccessRequestStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved" 
    REJECTED = "rejected"

class ApiAccessRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_reason = db.Column(db.Text, nullable=False)
    integration_purpose = db.Column(db.String(256), nullable=False)
    company_name = db.Column(db.String(128))
    website = db.Column(db.String(256))
    status = db.Column(db.Enum(ApiAccessRequestStatus), default=ApiAccessRequestStatus.PENDING)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewer_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('api_access_requests', lazy=True))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref=db.backref('reviewed_requests', lazy=True))

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
    transaction_id = db.Column(db.String(64), nullable=True, index=True)  # Can be null for draft forms
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
    def get_for_transaction_admin(cls, transaction_id, form_type):
        """
        Get form data for any transaction (admin method)
        This method allows admins to retrieve form data for any transaction

        Args:
            transaction_id (str): The transaction ID
            form_type (str): The type of form

        Returns:
            dict: The form data and user details, or None if not found
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

        # Get user info
        user = User.query.get(form_data.user_id)
        user_info = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email
        } if user else {'user_id': form_data.user_id}

        # Parse JSON
        try:
            form_data_dict = json.loads(form_data.form_data)
            return {
                'form_data': form_data_dict,
                'user': user_info,
                'created_at': form_data.created_at.isoformat(),
                'expires_at': form_data.expires_at.isoformat()
            }
        except json.JSONDecodeError:
            return None

    @classmethod
    def get_all_for_user(cls, user_id):
        """
        Get all form data for a user

        Args:
            user_id (int): The user ID

        Returns:
            list: List of form data objects with transaction information
        """
        # Find all non-expired form data for this user
        form_data_items = cls.query.filter_by(
            user_id=user_id
        ).filter(
            cls.expires_at > datetime.utcnow()
        ).order_by(cls.created_at.desc()).all()

        result = []
        for item in form_data_items:
            try:
                data_dict = json.loads(item.form_data)
                result.append({
                    'transaction_id': item.transaction_id,
                    'form_type': item.form_type,
                    'created_at': item.created_at.isoformat(),
                    'expires_at': item.expires_at.isoformat(),
                    'form_data': data_dict
                })
            except json.JSONDecodeError:
                continue

        return result

    @classmethod
    def cleanup_expired(cls):
        """Remove all expired form data"""
        expired = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        for item in expired:
            db.session.delete(item)
        db.session.commit()

    @classmethod
    def save_form_data(cls, user_id, form_type, form_data, transaction_id=None, expires_at=None):
        """
        Save or update form data without requiring a transaction ID (for drafts)

        Args:
            user_id (int): The user ID
            form_type (str): The type of form
            form_data (dict): The form data
            transaction_id (str, optional): The transaction ID if exists
            expires_at (datetime, optional): Expiry time, defaults to 24 hours

        Returns:
            FormData: The new or updated FormData object
        """
        # Convert form data to JSON
        form_data_json = json.dumps(form_data)

        # Set default expiry time if not provided
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(hours=24)

        # If transaction_id is provided, check if we have an existing record
        if transaction_id:
            existing = cls.query.filter_by(
                user_id=user_id,
                transaction_id=transaction_id,
                form_type=form_type
            ).first()
        else:
            # If no transaction_id (draft form), find by user_id and form_type
            existing = cls.query.filter_by(
                user_id=user_id,
                transaction_id=None,  # Only find draft forms with no transaction ID
                form_type=form_type
            ).order_by(cls.created_at.desc()).first()

        if existing:
            # Update existing record
            existing.form_data = form_data_json
            existing.expires_at = expires_at
            existing.created_at = datetime.utcnow()
            return existing

        #        # Create new record
        form_data_obj = cls(
            user_id=user_id,
            transaction_id=transaction_id,  # Can be None for draft
            form_type=form_type,
            form_data=form_data_json,
            expires_at=expires_at
        )

        db.session.add(form_data_obj)
        return form_data_obj
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
    DEVELOPER = "developer"
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationship to User model
    user = db.relationship('User', backref=db.backref('partner_api_keys', lazy=True))

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


# Treasury Management System Models
class TreasuryAccountType(enum.Enum):
    OPERATING = "operating"
    INVESTMENT = "investment"
    RESERVE = "reserve"
    PAYROLL = "payroll"
    TAX = "tax"
    DEBT_SERVICE = "debt_service"

class TreasuryAccount(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(256))
    account_type = db.Column(db.Enum(TreasuryAccountType), nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey('financial_institution.id'))
    account_number = db.Column(db.String(64))
    currency = db.Column(db.String(10), default="USD")
    current_balance = db.Column(db.Float, default=0.0)
    target_balance = db.Column(db.Float)
    minimum_balance = db.Column(db.Float, default=0.0)
    maximum_balance = db.Column(db.Float)
    available_balance = db.Column(db.Float, default=0.0)
    organization_id = db.Column(db.Integer)  # For multi-organization support
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_reconciled = db.Column(db.DateTime)

    # Relationships
    institution = db.relationship('FinancialInstitution', backref=db.backref('treasury_accounts', lazy=True))

    def update_balance(self, amount, transaction_type=None):
        """Update account balance based on transaction type"""
        if transaction_type in [TransactionType.DEPOSIT, TransactionType.TREASURY_TRANSFER]:
            self.current_balance += amount
            self.available_balance += amount
        elif transaction_type in [TransactionType.WITHDRAWAL]:
            self.current_balance -= amount
            self.available_balance -= amount

    def is_within_limits(self):
        """Check if account balance is within defined limits"""
        if self.minimum_balance is not None and self.current_balance < self.minimum_balance:
            return False
        if self.maximum_balance is not None and self.current_balance > self.maximum_balance:
            return False
        return True

class InvestmentType(enum.Enum):
    CERTIFICATE_OF_DEPOSIT = "certificate_of_deposit"
    MONEY_MARKET = "money_market"
    TREASURY_BILL = "treasury_bill"
    BOND = "bond"
    COMMERCIAL_PAPER = "commercial_paper"
    OVERNIGHT_INVESTMENT = "overnight_investment"
    TIME_DEPOSIT = "time_deposit"

class InvestmentStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELED = "canceled"

class CashFlowDirection(enum.Enum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"

class RecurrenceType(enum.Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"

class TreasuryInvestment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    investment_id = db.Column(db.String(64), unique=True, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('treasury_account.id'))
    investment_type = db.Column(db.Enum(InvestmentType), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="USD")
    interest_rate = db.Column(db.Float)
    start_date = db.Column(db.DateTime, nullable=False)
    maturity_date = db.Column(db.DateTime, nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey('financial_institution.id'))
    status = db.Column(db.Enum(InvestmentStatus), default=InvestmentStatus.PENDING)
    description = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = db.relationship('TreasuryAccount', backref=db.backref('investments', lazy=True))
    institution = db.relationship('FinancialInstitution', backref=db.backref('investments', lazy=True))

    def calculate_maturity_value(self):
        """Calculate the value at maturity based on interest rate"""
        if not self.interest_rate:
            return self.amount

        days = (self.maturity_date - self.start_date).days
        annual_rate = self.interest_rate / 100

        # Simple interest calculation
        interest = self.amount * annual_rate * (days / 365)
        return self.amount + interest

class CashFlowForecast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('treasury_account.id'))
    direction = db.Column(db.Enum(CashFlowDirection), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default="USD")
    transaction_date = db.Column(db.DateTime, nullable=False)
    recurrence_type = db.Column(db.Enum(RecurrenceType), default=RecurrenceType.NONE)
    recurrence_end_date = db.Column(db.DateTime)
    source_description = db.Column(db.String(256))
    category = db.Column(db.String(128))
    probability = db.Column(db.Float, default=100.0)  # Percentage probability of occurring
    forecast_type = db.Column(db.String(64), default="projected")  # projected or actual
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = db.relationship('TreasuryAccount', backref=db.backref('cash_flow_forecasts', lazy=True))

class TreasuryTransactionType(enum.Enum):
    INTERNAL_TRANSFER = "internal_transfer"
    EXTERNAL_TRANSFER = "external_transfer"
    INVESTMENT_PURCHASE = "investment_purchase"
    INVESTMENT_MATURITY = "investment_maturity"
    LOAN_PAYMENT = "loan_payment"
    LOAN_DISBURSEMENT = "loan_disbursement"
    INTEREST_PAYMENT = "interest_payment"
    FEE_PAYMENT = "fee_payment"

class TreasuryTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(64), unique=True, nullable=False)
    from_account_id = db.Column(db.Integer, db.ForeignKey('treasury_account.id'))
    to_account_id = db.Column(db.Integer, db.ForeignKey('treasury_account.id'))
    transaction_type = db.Column(db.Enum(TreasuryTransactionType), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="USD")
    exchange_rate = db.Column(db.Float, default=1.0)
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    execution_date = db.Column(db.DateTime)
    description = db.Column(db.String(256))
    approval_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    approval_date = db.Column(db.DateTime)
    transaction_fees = db.Column(db.Float, default=0.0)
    reference_number = db.Column(db.String(64))
    memo = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    from_account = db.relationship('TreasuryAccount', foreign_keys=[from_account_id], backref=db.backref('outgoing_transactions', lazy=True))
    to_account = db.relationship('TreasuryAccount', foreign_keys=[to_account_id], backref=db.backref('incoming_transactions', lazy=True))
    approved_by = db.relationship('User', foreign_keys=[approval_user_id], backref=db.backref('approved_treasury_transactions', lazy=True))
    created_by_user = db.relationship('User', foreign_keys=[created_by], backref=db.backref('created_treasury_transactions', lazy=True))

    # Optional link to a main application transaction
    nvc_transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    nvc_transaction = db.relationship('Transaction', backref=db.backref('treasury_transactions', lazy=True))

    def get_exchange_amount(self):
        """Calculate amount with exchange rate applied"""
        return self.amount * self.exchange_rate

    def process_transaction(self):
        """Process the transaction and update account balances"""
        if self.status != TransactionStatus.PENDING:
            return False

        if self.from_account:
            self.from_account.update_balance(-self.amount, TransactionType.WITHDRAWAL)

        if self.to_account:
            self.to_account.update_balance(self.amount * self.exchange_rate, TransactionType.DEPOSIT)

        self.execution_date = datetime.utcnow()
        self.status = TransactionStatus.COMPLETED
        return True

class LoanType(enum.Enum):
    TERM_LOAN = "term_loan"
    REVOLVING_CREDIT = "revolving_credit"
    BRIDGE_LOAN = "bridge_loan"
    SYNDICATED_LOAN = "syndicated_loan"

class LoanStatus(enum.Enum):
    ACTIVE = "active"
    PAID = "paid"
    DEFAULTED = "defaulted"
    RESTRUCTURED = "restructured"

class InterestType(enum.Enum):
    FIXED = "fixed"
    VARIABLE = "variable"

class PaymentFrequency(enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi-annual"
    ANNUAL = "annual"

class TreasuryLoan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('treasury_account.id'))
    loan_type = db.Column(db.Enum(LoanType), nullable=False)
    principal_amount = db.Column(db.Float, nullable=False)
    outstanding_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default="USD")
    interest_type = db.Column(db.Enum(InterestType), nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    reference_rate = db.Column(db.String(64))  # For variable rate loans (e.g. LIBOR, SOFR)
    margin = db.Column(db.Float)  # Added to reference rate for variable loans
    start_date = db.Column(db.DateTime, nullable=False)
    maturity_date = db.Column(db.DateTime, nullable=False)
    payment_frequency = db.Column(db.Enum(PaymentFrequency), nullable=False)
    next_payment_date = db.Column(db.DateTime)
    next_payment_amount = db.Column(db.Float)
    lender_institution_id = db.Column(db.Integer, db.ForeignKey('financial_institution.id'))
    status = db.Column(db.Enum(LoanStatus), default=LoanStatus.ACTIVE)
    description = db.Column(db.String(256))
    collateral_description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    account = db.relationship('TreasuryAccount', backref=db.backref('loans', lazy=True))
    lender = db.relationship('FinancialInstitution', backref=db.backref('provided_loans', lazy=True))

    def calculate_interest_due(self, as_of_date=None):
        """Calculate interest due as of a specific date"""
        if not as_of_date:
            as_of_date = datetime.utcnow()

        # Simple interest calculation for demonstration
        days_since_last_payment = (as_of_date - self.start_date).days
        daily_rate = self.interest_rate / 36500  # Daily rate based on annual rate

        interest_due = self.outstanding_amount * daily_rate * days_since_last_payment
        return interest_due

    def make_payment(self, payment_amount, payment_date=None):
        """Record a loan payment"""
        if not payment_date:
            payment_date = datetime.utcnow()

        # Calculate interest portion
        interest_due = self.calculate_interest_due(payment_date)

        # Apply payment to interest first, then principal
        principal_payment = max(0, payment_amount - interest_due)
        self.outstanding_amount -= principal_payment

        # Update payment schedule
        if self.payment_frequency == PaymentFrequency.MONTHLY:
            self.next_payment_date = payment_date + timedelta(days=30)
        elif self.payment_frequency == PaymentFrequency.QUARTERLY:
            self.next_payment_date = payment_date + timedelta(days=90)
        elif self.payment_frequency == PaymentFrequency.ANNUALLY:
            self.next_payment_date = payment_date + timedelta(days=365)

        # Create a payment record
        payment = TreasuryLoanPayment(
            loan_id=self.id,
            payment_amount=payment_amount,
            principal_amount=principal_payment,
            interest_amount=min(interest_due, payment_amount),
            payment_date=payment_date
        )

        return payment

class TreasuryLoanPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('treasury_loan.id'))
    payment_amount = db.Column(db.Float, nullable=False)
    principal_amount = db.Column(db.Float, nullable=False)
    interest_amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('treasury_transaction.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    loan = db.relationship('TreasuryLoan', backref=db.backref('payments', lazy=True))
    transaction = db.relationship('TreasuryTransaction', backref=db.backref('loan_payments', lazy=True))

# Payment processing systems

class PaymentFrequency(enum.Enum):
    ONE_TIME = "one_time"
    DAILY = "daily"
    WEEKLY = "weekly"
    BI_WEEKLY = "bi-weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    CUSTOM = "custom"

class BillCategory(enum.Enum):
    UTILITY = "utility"
    RENT = "rent"
    MORTGAGE = "mortgage"
    INSURANCE = "insurance"
    TAX = "tax"
    GOVERNMENT = "government"
    SUBSCRIPTION = "subscription"
    SERVICE = "service"
    OTHER = "other"

class ContractType(enum.Enum):
    FIXED_PRICE = "fixed_price"
    HOURLY = "hourly"
    RETAINER = "retainer"
    MILESTONE_BASED = "milestone_based"
    SUBSCRIPTION = "subscription"
    OTHER = "other"

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    employee_id = db.Column(db.String(64), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    position = db.Column(db.String(100))
    department = db.Column(db.String(100))
    hire_date = db.Column(db.Date, default=date.today)
    bank_account_number = db.Column(db.String(100))
    bank_routing_number = db.Column(db.String(100))
    bank_name = db.Column(db.String(150))
    payment_method = db.Column(db.String(50), default="direct_deposit")
    salary_amount = db.Column(db.Float)
    salary_frequency = db.Column(db.Enum(PaymentFrequency), default=PaymentFrequency.MONTHLY)
    is_active = db.Column(db.Boolean, default=True)
    metadata_json = db.Column(db.Text)  # For additional custom employee data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('employee_profile', uselist=False))

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_metadata(self):
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except:
            return {}

class PayrollBatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256))
    payment_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="USD")
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    processed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    institution_id = db.Column(db.Integer, db.ForeignKey('financial_institution.id'))
    payment_method = db.Column(db.String(50), default="direct_deposit")
    metadata_json = db.Column(db.Text)  # For additional batch processing data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    processed_by_user = db.relationship('User', backref=db.backref('processed_payrolls', lazy=True))
    institution = db.relationship('FinancialInstitution', backref=db.backref('payroll_batches', lazy=True))

    def get_metadata(self):
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except:
            return {}

class SalaryPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    payroll_batch_id = db.Column(db.Integer, db.ForeignKey('payroll_batch.id'))
    payment_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="USD")
    payment_method = db.Column(db.String(50), default="direct_deposit")
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    description = db.Column(db.String(256))
    metadata_json = db.Column(db.Text)  # For tax details, deductions, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee', backref=db.backref('salary_payments', lazy=True))
    transaction = db.relationship('Transaction', backref=db.backref('salary_payment', uselist=False))
    payroll_batch = db.relationship('PayrollBatch', backref=db.backref('salary_payments', lazy=True))

    def get_metadata(self):
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except:
            return {}

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    contact_name = db.Column(db.String(150))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    address = db.Column(db.String(256))
    website = db.Column(db.String(150))
    payment_terms = db.Column(db.String(100))  # Net 30, Net 60, etc.
    bank_account_number = db.Column(db.String(100))
    bank_routing_number = db.Column(db.String(100))
    bank_name = db.Column(db.String(150))
    payment_method = db.Column(db.String(50), default="bank_transfer")
    tax_id = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    metadata_json = db.Column(db.Text)  # For additional vendor data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_metadata(self):
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except:
            return {}

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(64), unique=True, nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    category = db.Column(db.Enum(BillCategory), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="USD")
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    payment_date = db.Column(db.Date)
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    description = db.Column(db.String(256))
    recurring = db.Column(db.Boolean, default=False)
    frequency = db.Column(db.Enum(PaymentFrequency), default=PaymentFrequency.ONE_TIME)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    metadata_json = db.Column(db.Text)  # For invoice details, line items, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vendor = db.relationship('Vendor', backref=db.backref('bills', lazy=True))
    transaction = db.relationship('Transaction', backref=db.backref('bill', uselist=False))

    def get_metadata(self):
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except:
            return {}

    def days_until_due(self):
        if self.due_date:
            return (self.due_date - date.today()).days
        return None

class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contract_number = db.Column(db.String(64), unique=True, nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    contract_type = db.Column(db.Enum(ContractType), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    total_value = db.Column(db.Float)
    currency = db.Column(db.String(10), default="USD")
    payment_terms = db.Column(db.String(100))
    status = db.Column(db.String(50), default="active")  # active, completed, terminated
    file_path = db.Column(db.String(256))  # Path to stored contract document
    is_active = db.Column(db.Boolean, default=True)
    metadata_json = db.Column(db.Text)  # For additional contract details
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vendor = db.relationship('Vendor', backref=db.backref('contracts', lazy=True))

    def get_metadata(self):
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except:
            return {}

class ContractPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    payment_number = db.Column(db.String(64), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="USD")
    payment_date = db.Column(db.Date)
    due_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(256))
    milestone = db.Column(db.String(200))  # For milestone-based payments
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    metadata_json = db.Column(db.Text)  # For additional payment details
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract = db.relationship('Contract', backref=db.backref('payments', lazy=True))
    transaction = db.relationship('Transaction', backref=db.backref('contract_payment', uselist=False))

    def get_metadata(self):
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except:
            return {}


class WireTransferStatus(enum.Enum):
    """Status for wire transfers"""
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WireTransfer(db.Model):
    """Model for wire transfers through correspondent banks"""
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(64), unique=True, nullable=False)
    correspondent_bank_id = db.Column(db.Integer, db.ForeignKey('correspondent_bank.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    treasury_transaction_id = db.Column(db.Integer, db.ForeignKey('treasury_transaction.id'))
    
    # Financial Details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.String(256), nullable=False)
    message_to_beneficiary = db.Column(db.Text)
    
    # Originator Information (Sender)
    originator_name = db.Column(db.String(256), nullable=False)
    originator_account = db.Column(db.String(128), nullable=False)
    originator_address = db.Column(db.Text, nullable=False)
    
    # Beneficiary Information (Recipient)
    beneficiary_name = db.Column(db.String(256), nullable=False)
    beneficiary_account = db.Column(db.String(128), nullable=False)
    beneficiary_address = db.Column(db.Text, nullable=False)
    
    # Beneficiary Bank Information
    beneficiary_bank_name = db.Column(db.String(256), nullable=False)
    beneficiary_bank_address = db.Column(db.Text, nullable=False)
    beneficiary_bank_swift = db.Column(db.String(11))
    beneficiary_bank_routing = db.Column(db.String(20))
    
    # Intermediary Bank (Optional)
    intermediary_bank_name = db.Column(db.String(256))
    intermediary_bank_swift = db.Column(db.String(11))
    
    # Status and Tracking
    status = db.Column(db.Enum(WireTransferStatus), default=WireTransferStatus.PENDING)
    status_description = db.Column(db.String(256))
    confirmation_receipt = db.Column(db.String(128))  # Called "confirmation_receipt" in the database
    fed_reference_number = db.Column(db.String(128))  # Federal Reserve reference number for US wires
    
    # Attachments and Metadata
    attachments_json = db.Column(db.Text)  # JSON array of attachment file paths
    metadata_json = db.Column(db.Text)  # Additional wire transfer details
    
    # Timestamps and Tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    initiated_at = db.Column(db.DateTime)  # When transfer was sent to correspondent bank
    completed_at = db.Column(db.DateTime)  # When transfer was confirmed completed
    cancelled_at = db.Column(db.DateTime)  # When transfer was cancelled
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    transaction = db.relationship('Transaction', backref=db.backref('wire_transfer', uselist=False))
    treasury_transaction = db.relationship('TreasuryTransaction', backref=db.backref('wire_transfer', uselist=False))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    
    def get_metadata(self):
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except:
            return {}
    
    def get_attachments(self):
        if not self.attachments_json:
            return []
        try:
            return json.loads(self.attachments_json)
        except:
            return []
    
    def add_attachment(self, file_path):
        """Add a file attachment to the wire transfer"""
        attachments = self.get_attachments()
        attachments.append(file_path)
        self.attachments_json = json.dumps(attachments)
        
    def __repr__(self):
        return f"<WireTransfer {self.reference_number}: {self.currency} {self.amount:.2f} to {self.beneficiary_name}>"