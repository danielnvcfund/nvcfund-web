"""
Trust Portfolio Models for NVC Banking Platform
This module provides database models for trust portfolios, assets, and valuations.
"""
from datetime import datetime
from decimal import Decimal
from app import db
from enum import Enum
import json


class AssetCategory(Enum):
    """Categories of assets in trust portfolios"""
    MINERAL_RIGHTS = "mineral_rights"
    PRECIOUS_METALS = "precious_metals"
    EQUITY = "equity"
    FINANCIAL_INSTRUMENT = "financial_instrument"
    TREASURY_INSTRUMENT = "treasury_instrument"
    REAL_ESTATE = "real_estate"
    CASHIERS_CHECK = "cashiers_check"
    CURRENCY = "currency"
    OTHER = "other"


class AssetStatus(Enum):
    """Status of assets in trust portfolios"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SECURED = "secured"
    ALLOCATED = "allocated"
    RESERVED = "reserved"


class TrustFund(db.Model):
    """Trust fund model for NVC Banking Platform"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(64), unique=True)
    description = db.Column(db.Text)
    established_date = db.Column(db.Date)
    parent_trust_id = db.Column(db.Integer, db.ForeignKey('trust_fund.id'), nullable=True)
    is_subsidiary = db.Column(db.Boolean, default=False)
    grantor = db.Column(db.String(255))
    trustee = db.Column(db.String(255))
    co_trustees = db.Column(db.String(512))  # Comma-separated list of co-trustees
    beneficiary = db.Column(db.String(255))
    account_number = db.Column(db.String(64))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent_trust = db.relationship('TrustFund', remote_side=[id], backref='subsidiary_trusts')
    portfolios = db.relationship('TrustPortfolio', backref='trust_fund', lazy=True)
    
    def __repr__(self):
        return f"<TrustFund {self.name}>"


class TrustPortfolio(db.Model):
    """Trust portfolio model for NVC Banking Platform"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    trust_fund_id = db.Column(db.Integer, db.ForeignKey('trust_fund.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assets = db.relationship('TrustAsset', backref='portfolio', lazy=True)
    valuations = db.relationship('PortfolioValuation', backref='portfolio', lazy=True)
    
    def __repr__(self):
        return f"<TrustPortfolio {self.name}>"
    
    def current_valuation(self):
        """Get the most recent valuation for this portfolio"""
        return PortfolioValuation.query.filter_by(portfolio_id=self.id).order_by(PortfolioValuation.valuation_date.desc()).first()
    
    def total_value(self):
        """Calculate the total value of all assets in this portfolio"""
        return sum(asset.current_value() for asset in self.assets if asset.current_value())


class TrustAsset(db.Model):
    """Trust asset model for NVC Banking Platform"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    asset_category = db.Column(db.Enum(AssetCategory), nullable=False)
    status = db.Column(db.Enum(AssetStatus), default=AssetStatus.ACTIVE)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('trust_portfolio.id'), nullable=False)
    acquisition_date = db.Column(db.Date)
    acquisition_value = db.Column(db.Numeric(20, 2))  # Using high precision for large values
    currency = db.Column(db.String(3), default="USD")
    location = db.Column(db.String(255))
    asset_metadata = db.Column(db.Text)  # JSON data for additional asset metadata
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    valuations = db.relationship('AssetValuation', backref='asset', lazy=True)
    
    def __repr__(self):
        return f"<TrustAsset {self.name} ({self.asset_category})>"
    
    def current_value(self):
        """Get the most recent valuation for this asset"""
        valuation = AssetValuation.query.filter_by(asset_id=self.id).order_by(AssetValuation.valuation_date.desc()).first()
        return valuation.value if valuation else self.acquisition_value
    
    def get_metadata(self):
        """Parse the metadata JSON string"""
        if self.asset_metadata:
            try:
                return json.loads(self.asset_metadata)
            except:
                return {}
        return {}


class AssetValuation(db.Model):
    """Asset valuation model for NVC Banking Platform"""
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('trust_asset.id'), nullable=False)
    value = db.Column(db.Numeric(20, 2))  # Using high precision for large values
    currency = db.Column(db.String(3), default="USD")
    valuation_date = db.Column(db.DateTime, default=datetime.utcnow)
    valuation_method = db.Column(db.String(100))
    appraiser = db.Column(db.String(255))
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AssetValuation {self.asset_id}: {self.value} {self.currency} on {self.valuation_date}>"


class PortfolioValuation(db.Model):
    """Portfolio valuation model for NVC Banking Platform"""
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('trust_portfolio.id'), nullable=False)
    total_value = db.Column(db.Numeric(20, 2))  # Using high precision for large values
    currency = db.Column(db.String(3), default="USD")
    valuation_date = db.Column(db.DateTime, default=datetime.utcnow)
    valuation_method = db.Column(db.String(100))
    assessor = db.Column(db.String(255))
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PortfolioValuation {self.portfolio_id}: {self.total_value} {self.currency} on {self.valuation_date}>"