"""
Standby Letter of Credit (SBLC) Models
This module provides database models for Standby Letters of Credit and related entities.
"""
import enum
from datetime import datetime
from sqlalchemy import Enum, Text
from app import db

class SBLCStatus(enum.Enum):
    """Status of a Standby Letter of Credit"""
    DRAFT = "draft"
    ISSUED = "issued"
    AMENDED = "amended"
    DRAWN = "drawn"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    HONORED = "honored"

class SBLCType(enum.Enum):
    """Types of Standby Letters of Credit"""
    PERFORMANCE = "performance"  # Ensures performance of non-financial contractual obligations
    FINANCIAL = "financial"      # Ensures payment of financial obligations
    ADVANCE_PAYMENT = "advance_payment"  # Protects against non-delivery after advance payment
    BID_BOND = "bid_bond"        # Ensures bidder will honor their bid and sign a contract
    DIRECT_PAY = "direct_pay"    # Primary payment method rather than contingent
    CLEAN = "clean"              # No documents required for drawing, just a statement of default
    REVOLVING = "revolving"      # Automatically renews for a set period

class StandbyLetterOfCredit(db.Model):
    """Standby Letter of Credit model for NVC Banking Platform"""
    __tablename__ = 'standby_letter_of_credit'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(64), unique=True, nullable=False)
    
    # Basic SBLC details
    amount = db.Column(db.Numeric(precision=20, scale=2), nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    expiry_place = db.Column(db.String(100), nullable=False)
    applicable_law = db.Column(db.String(100), nullable=False)
    
    # Drawing conditions
    partial_drawings = db.Column(db.Boolean, default=True)
    multiple_drawings = db.Column(db.Boolean, default=True)
    
    # Issuing bank details (NVC)
    issuing_bank_id = db.Column(db.Integer, db.ForeignKey('financial_institution.id'))
    issuing_bank = db.relationship('FinancialInstitution', foreign_keys=[issuing_bank_id])
    
    # Applicant details
    applicant_id = db.Column(db.Integer, db.ForeignKey('account_holder.id'), nullable=False)
    applicant = db.relationship('AccountHolder', foreign_keys=[applicant_id])
    applicant_account_number = db.Column(db.String(50), nullable=False)
    applicant_contact_info = db.Column(db.String(200))
    
    # Beneficiary details
    beneficiary_name = db.Column(db.String(255), nullable=False)
    beneficiary_address = db.Column(db.Text, nullable=False)
    beneficiary_account_number = db.Column(db.String(50))
    beneficiary_bank_name = db.Column(db.String(255), nullable=False)
    beneficiary_bank_swift = db.Column(db.String(11), nullable=False)
    beneficiary_bank_address = db.Column(db.Text)
    
    # Underlying transaction
    contract_name = db.Column(db.String(255), nullable=False)
    contract_date = db.Column(db.Date, nullable=False)
    contract_details = db.Column(db.Text)
    
    # Terms and conditions
    special_conditions = db.Column(db.Text)
    sblc_type = db.Column(Enum(SBLCType), default=SBLCType.PERFORMANCE)
    
    # Status tracking
    status = db.Column(Enum(SBLCStatus), default=SBLCStatus.DRAFT)
    mt760_message = db.Column(db.Text)  # SWIFT MT760 message content
    swift_confirmation = db.Column(db.String(100))  # Confirmation received from SWIFT system
    verification_code = db.Column(db.String(64))  # Code for verifying authenticity
    
    # Timestamps and tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    issued_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    # Drawing details
    drawings = db.relationship('SBLCDrawing', backref='sblc', lazy=True)
    
    def __repr__(self):
        return f"<SBLC {self.reference_number}: {self.currency} {self.amount} - {self.status.value}>"
    
    def amount_in_words(self):
        """Convert the amount to words for formal documents"""
        try:
            from num2words import num2words
            return num2words(float(self.amount), to='currency', currency=self.currency)
        except:
            # Fallback if num2words fails or is not available
            return f"{float(self.amount)} {self.currency}"
    
    def days_until_expiry(self):
        """Calculate days remaining until expiry"""
        if self.expiry_date:
            from datetime import date
            today = date.today()
            if self.expiry_date > today:
                return (self.expiry_date - today).days
            return 0
        return None
    
    def is_active(self):
        """Check if the SBLC is currently active"""
        return self.status in [SBLCStatus.ISSUED, SBLCStatus.AMENDED]
    
    def generate_reference_number(self):
        """Generate a unique reference number for the SBLC"""
        import random
        import string
        from datetime import datetime
        
        # Format: SBLC-YYYYMMDD-XXXXX
        date_part = datetime.utcnow().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        return f"SBLC-{date_part}-{random_part}"

class SBLCDrawing(db.Model):
    """Record of drawings against a Standby Letter of Credit"""
    __tablename__ = 'sblc_drawing'
    
    id = db.Column(db.Integer, primary_key=True)
    sblc_id = db.Column(db.Integer, db.ForeignKey('standby_letter_of_credit.id'), nullable=False)
    
    # Drawing details
    amount = db.Column(db.Numeric(precision=20, scale=2), nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    drawing_date = db.Column(db.Date, nullable=False)
    beneficiary_statement = db.Column(db.Text, nullable=False)  # Beneficiary's statement claiming default
    supporting_documents = db.Column(db.Text)  # Description of supporting docs provided
    
    # Processing details
    is_compliant = db.Column(db.Boolean)  # Whether the drawing request meets requirements
    review_notes = db.Column(db.Text)  # Notes from document review
    decision = db.Column(db.String(20))  # HONORED, REJECTED, PENDING
    payment_date = db.Column(db.Date)  # Date when payment was made
    payment_reference = db.Column(db.String(100))  # Reference for the payment transaction
    
    # Timestamps and tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    processed_by = db.relationship('User')
    
    def __repr__(self):
        return f"<SBLCDrawing {self.id}: {self.currency} {self.amount} - {self.decision}>"

class SBLCAmendment(db.Model):
    """Records of amendments to a Standby Letter of Credit"""
    __tablename__ = 'sblc_amendment'
    
    id = db.Column(db.Integer, primary_key=True)
    sblc_id = db.Column(db.Integer, db.ForeignKey('standby_letter_of_credit.id'), nullable=False)
    sblc = db.relationship('StandbyLetterOfCredit', backref='amendments')
    
    # Amendment details
    amendment_number = db.Column(db.Integer, nullable=False)  # Sequential number for amendments
    amendment_date = db.Column(db.Date, nullable=False)
    
    # Fields that can be amended
    new_expiry_date = db.Column(db.Date)
    new_amount = db.Column(db.Numeric(precision=20, scale=2))
    new_currency = db.Column(db.String(10))
    amendment_text = db.Column(db.Text, nullable=False)  # Detailed description of changes
    
    # Processing details
    is_accepted = db.Column(db.Boolean)  # Whether beneficiary accepted the amendment
    acceptance_date = db.Column(db.Date)
    mt767_message = db.Column(db.Text)  # SWIFT MT767 message content for amendment
    
    # Timestamps and tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.relationship('User')
    
    def __repr__(self):
        return f"<SBLCAmendment {self.amendment_number}: {self.sblc_id}>"