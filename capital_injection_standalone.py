"""
Financial Institution Recapitalization and Equity Injection Program
This module provides standalone access to the financial institution recapitalization
and equity injection features without requiring the models folder structure.
"""
import enum
from datetime import datetime
import uuid
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os

from app import db
from decorators import admin_required, analyst_required


# Enums for capital injection models
class CapitalType(enum.Enum):
    """Types of capital for financial institution recapitalization"""
    TIER1_EQUITY = "tier1_equity"  # Common equity, retained earnings
    TIER1_ADDITIONAL = "tier1_additional"  # Preferred shares, contingent convertibles
    TIER2 = "tier2"  # Subordinated debt, hybrid instruments
    CAPITAL_CONSERVATION_BUFFER = "capital_conservation_buffer"
    COUNTERCYCLICAL_BUFFER = "countercyclical_buffer"
    SYSTEMIC_RISK_BUFFER = "systemic_risk_buffer"


class InstitutionType(enum.Enum):
    """Types of financial institutions for capital injection program"""
    COMMERCIAL_BANK = "commercial_bank"
    INVESTMENT_BANK = "investment_bank"
    CREDIT_UNION = "credit_union"
    MICROFINANCE = "microfinance"
    SAVINGS_BANK = "savings_bank"
    COMMUNITY_BANK = "community_bank"
    COOPERATIVE_BANK = "cooperative_bank"
    REGIONAL_BANK = "regional_bank"
    NATIONAL_BANK = "national_bank"
    INTERNATIONAL_BANK = "international_bank"
    DEVELOPMENT_BANK = "development_bank"
    DIGITAL_BANK = "digital_bank"


class ApplicationStatus(enum.Enum):
    """Status types for capital injection applications"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ADDITIONAL_INFO_REQUIRED = "additional_info_required"
    APPROVED = "approved"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    FUNDING_IN_PROGRESS = "funding_in_progress"
    FUNDED = "funded"
    CLOSED = "closed"


class InvestmentStructure(enum.Enum):
    """Investment structure types for capital injections"""
    COMMON_EQUITY = "common_equity"
    PREFERRED_SHARES = "preferred_shares"
    SUBORDINATED_DEBT = "subordinated_debt"
    CONVERTIBLE_DEBT = "convertible_debt"
    CONTINGENT_CONVERTIBLE = "contingent_convertible"
    PERPETUAL_BOND = "perpetual_bond"
    HYBRID_INSTRUMENT = "hybrid_instrument"
    EQUITY_INVESTMENT = "equity_investment"
    TERM_LOAN = "term_loan"


class RegulatoryConcern(enum.Enum):
    """Regulatory concern types for financial institutions"""
    CAPITAL_ADEQUACY = "capital_adequacy"
    LIQUIDITY = "liquidity"
    ASSET_QUALITY = "asset_quality"
    MANAGEMENT = "management"
    EARNINGS = "earnings"
    SENSITIVITY_TO_MARKET_RISK = "sensitivity_to_market_risk"
    COMPLIANCE = "compliance"
    OPERATIONAL_RISK = "operational_risk"
    SYSTEMIC_RISK = "systemic_risk"


class RegulatoryFramework(enum.Enum):
    """Regulatory frameworks for capital requirements"""
    BASEL_III = "basel_iii"
    BASEL_IV = "basel_iv"
    DODD_FRANK = "dodd_frank"
    EU_CRD_IV = "eu_crd_iv"
    UK_PRA = "uk_pra"
    AUSTRALIA_APRA = "australia_apra"
    CANADA_OSFI = "canada_osfi"
    JAPAN_FSA = "japan_fsa"
    CHINA_CBRC = "china_cbrc"
    INDIA_RBI = "india_rbi"
    AFRICAN_REGIONAL = "african_regional"
    NATIONAL_SPECIFIC = "national_specific"


# Define the models for our database tables
class FinancialInstitutionProfile(db.Model):
    """Financial institution profile for capital injection program"""
    id = db.Column(db.Integer, primary_key=True)
    institution_name = db.Column(db.String(255), nullable=False)
    institution_type = db.Column(db.Enum(InstitutionType), nullable=False)
    registration_number = db.Column(db.String(100))
    tax_id = db.Column(db.String(100))
    year_established = db.Column(db.Integer)
    headquarters_country = db.Column(db.String(100))
    headquarters_city = db.Column(db.String(100))
    
    # Contact information
    primary_contact_name = db.Column(db.String(255))
    primary_contact_title = db.Column(db.String(255))
    primary_contact_email = db.Column(db.String(255))
    primary_contact_phone = db.Column(db.String(50))
    
    # Financial information
    total_assets = db.Column(db.Float)  # In USD millions
    total_liabilities = db.Column(db.Float)  # In USD millions
    total_equity = db.Column(db.Float)  # In USD millions
    tier1_capital = db.Column(db.Float)  # In USD millions
    tier2_capital = db.Column(db.Float)  # In USD millions
    risk_weighted_assets = db.Column(db.Float)  # In USD millions
    
    # Regulatory information
    primary_regulator = db.Column(db.String(255))
    regulatory_framework = db.Column(db.Enum(RegulatoryFramework))
    current_capital_ratio = db.Column(db.Float)  # Total capital ratio
    current_tier1_ratio = db.Column(db.Float)  # Tier 1 capital ratio
    current_leverage_ratio = db.Column(db.Float)  # Leverage ratio
    required_capital_ratio = db.Column(db.Float)  # Required by regulator
    
    # Profile verification
    is_verified = db.Column(db.Boolean, default=False)
    verification_date = db.Column(db.DateTime)
    verification_notes = db.Column(db.Text)
    
    # User tracking
    created_by = db.Column(db.Integer)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = db.relationship('InstitutionDocument', backref='institution_profile', lazy=True, 
                               foreign_keys='InstitutionDocument.institution_id')
    applications = db.relationship('CapitalInjectionApplication', backref='institution_profile', lazy=True,
                                  foreign_keys='CapitalInjectionApplication.institution_id')
    
    def __repr__(self):
        return f"<FinancialInstitutionProfile {self.institution_name}>"
    
    def calculate_capital_shortfall(self):
        """Calculate the capital shortfall based on regulatory requirements"""
        if not self.required_capital_ratio or not self.risk_weighted_assets or not self.total_capital:
            return None
        
        required_capital = self.required_capital_ratio * self.risk_weighted_assets / 100
        current_capital = self.tier1_capital + self.tier2_capital
        
        return max(0, required_capital - current_capital)
    
    @property
    def total_capital(self):
        """Calculate total capital (Tier 1 + Tier 2)"""
        if self.tier1_capital is None or self.tier2_capital is None:
            return None
        return self.tier1_capital + self.tier2_capital


class InstitutionDocument(db.Model):
    """Documents submitted by financial institutions"""
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('financial_institution_profile.id'), nullable=False)
    document_type = db.Column(db.String(100), nullable=False)  # e.g., "financial_statement", "regulatory_report"
    document_name = db.Column(db.String(255), nullable=False)
    document_path = db.Column(db.String(512))  # Path to stored document
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    verification_date = db.Column(db.DateTime)
    verification_notes = db.Column(db.Text)
    
    def __repr__(self):
        return f"<InstitutionDocument {self.document_name}>"


class CapitalInjectionApplication(db.Model):
    """Application for capital injection and recapitalization"""
    id = db.Column(db.Integer, primary_key=True)
    application_number = db.Column(db.String(64), unique=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('financial_institution_profile.id'), nullable=False)
    
    # Application details
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum(ApplicationStatus), default=ApplicationStatus.DRAFT)
    capital_type = db.Column(db.Enum(CapitalType), nullable=False)
    investment_structure = db.Column(db.Enum(InvestmentStructure), nullable=False)
    
    # Financial request
    requested_amount = db.Column(db.Float, nullable=False)  # In USD millions
    minimum_acceptable_amount = db.Column(db.Float)  # In USD millions
    term_years = db.Column(db.Integer)  # Term in years, if applicable
    proposed_interest_rate = db.Column(db.Float)  # For debt instruments
    proposed_dividend_rate = db.Column(db.Float)  # For equity instruments
    
    # Regulatory information
    regulatory_concern = db.Column(db.Enum(RegulatoryConcern))
    target_capital_ratio = db.Column(db.Float)  # Desired capital ratio after injection
    regulator_approval_required = db.Column(db.Boolean, default=True)
    regulator_approval_received = db.Column(db.Boolean, default=False)
    regulator_approval_date = db.Column(db.DateTime)
    
    # Use of funds
    use_of_funds = db.Column(db.Text)
    business_plan_summary = db.Column(db.Text)
    expected_impact = db.Column(db.Text)
    
    # Risk assessment
    risk_assessment = db.Column(db.Text)
    mitigating_factors = db.Column(db.Text)
    stress_test_results = db.Column(db.Text)
    
    # Internal processing
    assigned_analyst_id = db.Column(db.Integer)
    analyst_notes = db.Column(db.Text)
    committee_review_date = db.Column(db.DateTime)
    committee_decision = db.Column(db.String(100))
    committee_notes = db.Column(db.Text)
    
    # Approval details
    approved_amount = db.Column(db.Float)  # In USD millions
    approved_terms = db.Column(db.Text)  # JSON string of terms
    approval_date = db.Column(db.DateTime)
    
    # Funding details
    funding_date = db.Column(db.DateTime)
    funding_amount = db.Column(db.Float)  # Actual amount funded
    funding_transaction_id = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    application_updates = db.relationship('ApplicationStatusUpdate', backref='application', lazy=True)
    
    def __init__(self, **kwargs):
        super(CapitalInjectionApplication, self).__init__(**kwargs)
        if not self.application_number:
            self.application_number = f"CAP-{uuid.uuid4().hex[:8].upper()}"
    
    def __repr__(self):
        return f"<CapitalInjectionApplication {self.application_number}>"
    
    @property
    def approved_terms_dict(self):
        """Return approved terms as a dictionary"""
        if not self.approved_terms:
            return {}
        try:
            return json.loads(self.approved_terms)
        except:
            return {}
    
    @approved_terms_dict.setter
    def approved_terms_dict(self, terms_dict):
        """Set approved terms from dictionary"""
        if terms_dict:
            self.approved_terms = json.dumps(terms_dict)
        else:
            self.approved_terms = None


class ApplicationStatusUpdate(db.Model):
    """History of status updates for capital injection applications"""
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('capital_injection_application.id'), nullable=False)
    previous_status = db.Column(db.Enum(ApplicationStatus))
    new_status = db.Column(db.Enum(ApplicationStatus), nullable=False)
    update_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.String(255))
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f"<ApplicationStatusUpdate {self.application_id} - {self.new_status}>"


class CapitalInjectionTerm(db.Model):
    """Terms for capital injections and recapitalization programs"""
    id = db.Column(db.Integer, primary_key=True)
    capital_type = db.Column(db.Enum(CapitalType), nullable=False)
    investment_structure = db.Column(db.Enum(InvestmentStructure), nullable=False)
    min_amount = db.Column(db.Float, nullable=False)  # Minimum amount in USD millions
    max_amount = db.Column(db.Float, nullable=False)  # Maximum amount in USD millions
    min_term_years = db.Column(db.Integer)  # Minimum term in years
    max_term_years = db.Column(db.Integer)  # Maximum term in years
    interest_rate_range_min = db.Column(db.Float)  # Minimum interest rate
    interest_rate_range_max = db.Column(db.Float)  # Maximum interest rate
    dividend_rate_range_min = db.Column(db.Float)  # Minimum dividend rate
    dividend_rate_range_max = db.Column(db.Float)  # Maximum dividend rate
    is_active = db.Column(db.Boolean, default=True)
    terms_document = db.Column(db.String(512))  # Path to terms document
    details = db.Column(db.Text)  # Additional terms and conditions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<CapitalInjectionTerm {self.capital_type.value} - {self.investment_structure.value}>"


# Create blueprint for the capital injection feature
capital_injection = Blueprint('capital_injection', __name__, url_prefix='/capital-injection')


# Define allowed file extensions and upload folder
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'capital_injection')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@capital_injection.route('/')
@login_required
def index():
    """Capital injection home page with placeholder data for demo"""
    # Display a simplified version of the page for now
    return render_template('capital_injection/index.html',
                           profiles=[],
                           pending_apps=[],
                           approved_apps=[],
                           funded_apps=[],
                           other_apps=[],
                           is_admin=True,
                           is_analyst=True)


@capital_injection.route('/placeholder')
@login_required
def placeholder():
    """Placeholder page with info about the capital injection program"""
    return render_template('capital_injection/placeholder.html')