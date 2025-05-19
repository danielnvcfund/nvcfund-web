"""
Self-Liquidating Loan Models for NVC Banking Platform

This module defines the database models for the proprietary self-liquidating loan system
with inter-company loan servicing and management capabilities.
"""

import enum
from datetime import datetime, timedelta
from sqlalchemy import Enum, ForeignKey, Float, String, Integer, Boolean, DateTime, Text, func
from sqlalchemy.orm import relationship
from app import db
from account_holder_models import CurrencyType


class LoanStatus(enum.Enum):
    """Status types for self-liquidating loans"""
    APPLICATION = "application"
    UNDERWRITING = "underwriting"
    APPROVED = "approved"
    FUNDED = "funded"
    ACTIVE = "active"
    RENEWAL_PENDING = "renewal_pending"
    RENEWED = "renewed"
    LIQUIDATING = "liquidating"
    PAID = "paid"
    DEFAULTED = "defaulted"
    CANCELLED = "cancelled"


class CollateralType(enum.Enum):
    """Types of collateral accepted for self-liquidating loans"""
    PROMISSORY_NOTE = "promissory_note"
    BUSINESS_ASSETS = "business_assets"
    RECEIVABLES = "receivables"
    REAL_ESTATE = "real_estate"
    EQUIPMENT = "equipment"
    INVENTORY = "inventory"
    SECURITIES = "securities"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    OTHER = "other"


class RenewalStatus(enum.Enum):
    """Status types for loan renewals"""
    NOT_ELIGIBLE = "not_eligible"
    ELIGIBLE = "eligible"
    REQUESTED = "requested"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    EXECUTED = "executed"
    DECLINED = "declined"


class InterestPaymentFrequency(enum.Enum):
    """Frequency of interest payments"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"


class SelfLiquidatingLoan(db.Model):
    """Main model for loans"""
    # Underwriting fields
    underwriting_score = db.Column(db.Integer)
    underwriting_grade = db.Column(db.String(50))
    underwriting_start_date = db.Column(db.DateTime)
    underwriting_data_json = db.Column(db.Text)
    
    # Additional fields from comprehensive form
    requested_amount = db.Column(db.Float)
    preferred_term_years = db.Column(db.Integer)
    preferred_interest_rate = db.Column(db.Float)
    preferred_payment_frequency = db.Column(db.String(50))
    
    # Business details
    industry = db.Column(db.String(100))
    years_in_business = db.Column(db.Integer)
    number_of_employees = db.Column(db.Integer)
    annual_revenue = db.Column(db.Float)
    annual_net_income = db.Column(db.Float)
    loan_purpose = db.Column(db.Text)
    
    # Additional data as JSON
    additional_contacts_json = db.Column(db.Text)
    management_team_json = db.Column(db.Text)
    financial_history_json = db.Column(db.Text)
    additional_documents_json = db.Column(db.Text)
    
    # Collateral information
    collateral_value = db.Column(db.Float, default=0.0)
    collateral_description = db.Column(db.Text)
    has_personal_guarantee = db.Column(db.Boolean, default=False)
    
    # Business plan
    has_business_plan = db.Column(db.Boolean, default=False)
    business_plan_summary = db.Column(db.Text)
    market_analysis = db.Column(db.Text)
    id = db.Column(db.Integer, primary_key=True)
    loan_number = db.Column(db.String(64), unique=True, nullable=False)

    # Loan Basic Information
    loan_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(Enum(CurrencyType),
                         default=CurrencyType.USD,
                         nullable=False)
    interest_rate = db.Column(
        db.Float, nullable=False)  # Stored as percentage (e.g., 5.75)
    term_years = db.Column(db.Integer, default=10, nullable=False)
    renewal_options = db.Column(db.Integer,
                                default=2)  # Number of possible renewals
    renewals_used = db.Column(db.Integer,
                              default=0)  # Number of renewals already used

    # Loan Dates
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    approval_date = db.Column(db.DateTime)
    funding_date = db.Column(db.DateTime)
    maturity_date = db.Column(db.DateTime)
    next_interest_payment_date = db.Column(db.DateTime)
    last_payment_date = db.Column(db.DateTime)

    # Loan Parties
    borrower_name = db.Column(db.String(255), nullable=False)
    borrower_entity_type = db.Column(db.String(100))  # Corporation, LLC, etc.
    borrower_tax_id = db.Column(db.String(50))
    borrower_address = db.Column(db.Text)
    borrower_contact_name = db.Column(db.String(255))
    borrower_contact_email = db.Column(db.String(255))
    borrower_contact_phone = db.Column(db.String(50))

    # Loan Status and Financial Details
    status = db.Column(Enum(LoanStatus), default=LoanStatus.APPLICATION)
    renewal_status = db.Column(Enum(RenewalStatus),
                               default=RenewalStatus.NOT_ELIGIBLE)
    current_principal_balance = db.Column(db.Float)
    total_interest_paid = db.Column(db.Float, default=0.0)
    total_principal_paid = db.Column(db.Float, default=0.0)
    remaining_payments = db.Column(db.Integer)
    interest_payment_frequency = db.Column(
        Enum(InterestPaymentFrequency),
        default=InterestPaymentFrequency.QUARTERLY)

    # Loan Documents and Metadata
    loan_agreement_document_id = db.Column(db.String(255))
    promissory_note_document_id = db.Column(db.String(255))
    collateral_documents_json = db.Column(
        db.Text)  # JSON array of document IDs

    # Self-Liquidating Specifics
    liquidation_mechanism_description = db.Column(db.Text)
    inter_company_loan_servicing_id = db.Column(db.String(255))
    internal_collateral_management_id = db.Column(db.String(255))

    # Correspondent Banking Integration
    is_available_to_correspondents = db.Column(db.Boolean, default=False)
    off_taker_availability_date = db.Column(db.DateTime)

    # Foreign Keys
    originating_institution_id = db.Column(
        db.Integer, db.ForeignKey('financial_institution.id'))
    servicing_institution_id = db.Column(
        db.Integer, db.ForeignKey('financial_institution.id'))

    # System and Audit Fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.utcnow,
                           onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f"<SelfLiquidatingLoan {self.loan_number}: {self.loan_amount} {self.currency.name} at {self.interest_rate}%>"

    def calculate_maturity_date(self):
        """Calculate the maturity date based on funding date and term"""
        if self.funding_date:
            return self.funding_date + timedelta(days=self.term_years * 365)
        return None

    def calculate_next_interest_payment(self):
        """Calculate the next interest payment date based on frequency"""
        if not self.next_interest_payment_date:
            if not self.funding_date:
                return None

            base_date = self.funding_date
        else:
            base_date = self.next_interest_payment_date

        if self.interest_payment_frequency == InterestPaymentFrequency.MONTHLY:
            return base_date + timedelta(days=30)
        elif self.interest_payment_frequency == InterestPaymentFrequency.QUARTERLY:
            return base_date + timedelta(days=90)
        elif self.interest_payment_frequency == InterestPaymentFrequency.SEMI_ANNUALLY:
            return base_date + timedelta(days=182)
        elif self.interest_payment_frequency == InterestPaymentFrequency.ANNUALLY:
            return base_date + timedelta(days=365)

        return None

    def calculate_interest_payment_amount(self):
        """Calculate the interest payment amount based on current principal and rate"""
        if not self.current_principal_balance:
            return 0

        annual_interest = self.current_principal_balance * (
            self.interest_rate / 100)

        # Adjust based on payment frequency
        if self.interest_payment_frequency == InterestPaymentFrequency.MONTHLY:
            return annual_interest / 12
        elif self.interest_payment_frequency == InterestPaymentFrequency.QUARTERLY:
            return annual_interest / 4
        elif self.interest_payment_frequency == InterestPaymentFrequency.SEMI_ANNUALLY:
            return annual_interest / 2
        elif self.interest_payment_frequency == InterestPaymentFrequency.ANNUALLY:
            return annual_interest

        return 0

    def is_eligible_for_renewal(self):
        """Check if loan is eligible for renewal"""
        return (self.status == LoanStatus.ACTIVE
                and self.renewals_used < self.renewal_options
                and (self.maturity_date - datetime.utcnow()).days <=
                180  # Within 6 months of maturity
                )


class LoanCollateral(db.Model):
    """Collateral items for self-liquidating loans"""
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer,
                        db.ForeignKey('self_liquidating_loan.id'),
                        nullable=False)

    # Collateral Details
    collateral_type = db.Column(Enum(CollateralType), nullable=False)
    description = db.Column(db.Text, nullable=False)
    value = db.Column(db.Float, nullable=False)
    valuation_date = db.Column(db.DateTime, default=datetime.utcnow)
    valuation_source = db.Column(db.String(255))
    location = db.Column(db.Text)

    # Promissory Note Specific
    note_issuer = db.Column(db.String(255))
    note_maturity_date = db.Column(db.DateTime)
    note_interest_rate = db.Column(db.Float)

    # Business Assets/Receivables Specific
    asset_type = db.Column(db.String(255))
    receivables_aging = db.Column(
        db.String(50))  # e.g., "0-30 days", "31-60 days"

    # Document References
    collateral_document_id = db.Column(db.String(255))
    appraisal_document_id = db.Column(db.String(255))
    perfection_document_id = db.Column(db.String(255))  # UCC filing, etc.

    # System Fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LoanCollateral: {self.collateral_type.name} - {self.value}>"


class LoanPayment(db.Model):
    """Payment records for loans"""
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer,
                        db.ForeignKey('self_liquidating_loan.id'),
                        nullable=False)

    # Payment Details
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_amount = db.Column(db.Float, nullable=False)
    principal_amount = db.Column(db.Float, default=0.0)
    interest_amount = db.Column(db.Float, default=0.0)
    fees_amount = db.Column(db.Float, default=0.0)

    # Payment Method
    payment_method = db.Column(db.String(100))  # Wire, ACH, Internal transfer
    payment_reference = db.Column(db.String(255))
    payment_status = db.Column(db.String(50), default="completed")

    # Self-Liquidating Specific
    liquidation_source = db.Column(
        db.String(255))  # Source of liquidation funds
    is_self_liquidating_payment = db.Column(db.Boolean, default=False)
    
    # Documents
    payment_document_id = db.Column(db.String(255))

    # System Fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f"<LoanPayment: {self.payment_amount} on {self.payment_date}>"


class LoanRenewal(db.Model):
    """Renewal records for self-liquidating loans"""
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer,
                        db.ForeignKey('self_liquidating_loan.id'),
                        nullable=False)

    # Renewal Details
    renewal_number = db.Column(db.Integer, nullable=False)  # 1st, 2nd renewal
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    approval_date = db.Column(db.DateTime)
    effective_date = db.Column(db.DateTime)
    new_maturity_date = db.Column(db.DateTime)

    # Terms
    previous_interest_rate = db.Column(db.Float)
    new_interest_rate = db.Column(db.Float)
    additional_terms_json = db.Column(
        db.Text)  # JSON with any additional terms

    # Status
    status = db.Column(Enum(RenewalStatus), default=RenewalStatus.REQUESTED)
    status_reason = db.Column(db.Text)

    # Document References
    renewal_agreement_document_id = db.Column(db.String(255))

    # System Fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.utcnow,
                           onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f"<LoanRenewal #{self.renewal_number}: Status - {self.status.name}>"


class LoanCorrespondentAvailability(db.Model):
    """Tracks availability of loans to correspondent banks"""
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer,
                        db.ForeignKey('self_liquidating_loan.id'),
                        nullable=False)
    correspondent_bank_id = db.Column(db.Integer,
                                      db.ForeignKey('correspondent_bank.id'),
                                      nullable=False)

    # Availability Details
    offered_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiration_date = db.Column(db.DateTime)
    participation_percentage = db.Column(
        db.Float)  # % of loan available to this correspondent
    participation_amount = db.Column(
        db.Float)  # Amount available to this correspondent
    special_terms = db.Column(db.Text)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    accepted = db.Column(db.Boolean, default=False)
    acceptance_date = db.Column(db.DateTime)

    # System Fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,
                           default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LoanCorrespondentAvailability: {self.participation_amount} to Bank ID {self.correspondent_bank_id}>"
