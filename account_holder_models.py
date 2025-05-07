"""
Account Holder Models for NVC Private Banking
This module provides the database models for account holders, addresses, phone numbers,
and bank accounts.
"""

import enum
from datetime import datetime
from app import db
from sqlalchemy.ext.hybrid import hybrid_property

class AccountType(enum.Enum):
    """Account types for banking accounts"""
    CHECKING = "checking"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    BUSINESS = "business"
    CUSTODY = "custody"
    CRYPTO = "crypto"
    
class CurrencyType(enum.Enum):
    """Currency types for banking accounts"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    BTC = "BTC"
    ETH = "ETH"
    NVCT = "NVCT"  # NVC Token
    SPU = "SPU"    # Special Purpose Unit
    TU = "TU"      # Treasury Unit
    ZCASH = "ZCASH"
    NGN = "NGN"    # Nigerian Naira

class AccountStatus(enum.Enum):
    """Status types for banking accounts"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    PENDING = "pending"

class Address(db.Model):
    """Address model for account holders"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="Primary Address")  # Name/label for this address
    line1 = db.Column(db.String(255))
    line2 = db.Column(db.String(255))
    pobox = db.Column(db.String(50))
    neighborhood = db.Column(db.String(100))
    city = db.Column(db.String(100))
    region = db.Column(db.String(100))  # State/Province
    zip = db.Column(db.String(20))
    country = db.Column(db.String(2))   # 2-letter country code
    street = db.Column(db.String(255))
    building_number = db.Column(db.String(50))
    complement = db.Column(db.String(255))
    
    # Foreign keys
    account_holder_id = db.Column(db.Integer, db.ForeignKey('account_holder.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Address {self.line1}, {self.city}, {self.country}>"
    
    @property
    def formatted(self):
        """Return a formatted address string"""
        parts = []
        if self.line1:
            parts.append(self.line1)
        if self.line2:
            parts.append(self.line2)
        city_parts = []
        if self.city:
            city_parts.append(self.city)
        if self.region:
            city_parts.append(self.region)
        if self.zip:
            city_parts.append(self.zip)
        if city_parts:
            parts.append(", ".join(city_parts))
        if self.country:
            parts.append(self.country)
        return "\n".join(parts)

class PhoneNumber(db.Model):
    """Phone number model for account holders"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))  # Type of phone (e.g. "Mobile", "Landline")
    number = db.Column(db.String(50))
    is_primary = db.Column(db.Boolean, default=False)
    is_mobile = db.Column(db.Boolean, default=False)
    verified = db.Column(db.Boolean, default=False)
    
    # Foreign keys
    account_holder_id = db.Column(db.Integer, db.ForeignKey('account_holder.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PhoneNumber {self.name}: {self.number}>"

class AccountHolder(db.Model):
    """Account holder model for NVC Private Banking"""
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(64), index=True, unique=True)  # External identifier
    name = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Entity type (individual, corporate, etc.)
    is_business = db.Column(db.Boolean, default=False)
    business_name = db.Column(db.String(255))
    business_type = db.Column(db.String(100))
    tax_id = db.Column(db.String(50))
    
    # KYC/AML status
    kyc_verified = db.Column(db.Boolean, default=False)
    aml_verified = db.Column(db.Boolean, default=False)
    kyc_documents_json = db.Column(db.Text)  # JSON data for KYC documents
    
    # Broker information
    broker = db.Column(db.String(255))
    
    # Relationships
    addresses = db.relationship('Address', backref='account_holder', lazy=True)
    phone_numbers = db.relationship('PhoneNumber', backref='account_holder', lazy=True)
    accounts = db.relationship('BankAccount', backref='account_holder', lazy=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('account_holder', uselist=False))
    
    @hybrid_property
    def full_name(self):
        """Return full name of account holder"""
        return self.name
        
    @hybrid_property
    def primary_address(self):
        """Return primary address of account holder"""
        return Address.query.filter_by(account_holder_id=self.id).first()
    
    @hybrid_property
    def primary_phone(self):
        """Return primary phone of account holder"""
        primary = PhoneNumber.query.filter_by(account_holder_id=self.id, is_primary=True).first()
        if primary:
            return primary
        return PhoneNumber.query.filter_by(account_holder_id=self.id).first()
    
    def __repr__(self):
        return f"<AccountHolder {self.name} ({self.email})>"

class BankAccount(db.Model):
    """Bank account model for NVC Private Banking"""
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(64), unique=True, nullable=False)
    account_name = db.Column(db.String(255))
    account_type = db.Column(db.Enum(AccountType), default=AccountType.CHECKING)
    currency = db.Column(db.Enum(CurrencyType), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    available_balance = db.Column(db.Float, default=0.0)
    status = db.Column(db.Enum(AccountStatus), default=AccountStatus.ACTIVE)
    
    # Foreign keys
    account_holder_id = db.Column(db.Integer, db.ForeignKey('account_holder.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_transaction_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f"<BankAccount {self.account_number} ({self.currency.value}): {self.balance}>"