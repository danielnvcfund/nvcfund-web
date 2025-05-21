"""
Standby Letter of Credit (SBLC) Models
This module defines the database models for the SBLC issuance system.
"""
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app import db
from models import User
from account_holder_models import AccountHolder, Address
from num2words import num2words

logger = logging.getLogger(__name__)

class SBLCStatus(Enum):
    """Status of a Standby Letter of Credit"""
    DRAFT = "draft"
    ISSUED = "issued"
    AMENDED = "amended"
    DRAWN = "drawn"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class SBLCDrawStatus(Enum):
    """Status of a draw against an SBLC"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class StandbyLetterOfCredit(db.Model):
    """Standby Letter of Credit (SBLC) model"""
    __tablename__ = 'standby_letter_of_credit'
    
    id = Column(Integer, primary_key=True)
    reference_number = Column(String(50), unique=True, nullable=False)
    
    # Parties
    applicant_id = Column(Integer, ForeignKey('account_holder.id'), nullable=False)
    applicant = relationship("AccountHolder", foreign_keys=[applicant_id])
    applicant_account_number = Column(String(50), nullable=False)
    applicant_contact_info = Column(String(255), nullable=True)
    
    beneficiary_name = Column(String(255), nullable=False)
    beneficiary_address = Column(Text, nullable=False)
    beneficiary_account_number = Column(String(50), nullable=True)
    beneficiary_bank_name = Column(String(255), nullable=False)
    beneficiary_bank_swift = Column(String(50), nullable=False)
    beneficiary_bank_address = Column(Text, nullable=True)
    
    # Issuing bank (if not NVC Banking Platform)
    issuing_bank_id = Column(Integer, ForeignKey('financial_institution.id'), nullable=True)
    issuing_bank = relationship("FinancialInstitution", foreign_keys=[issuing_bank_id])
    
    # SBLC details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    issue_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    expiry_date = Column(DateTime, nullable=False)
    expiry_place = Column(String(255), nullable=False, default="New York, NY, USA")
    
    # Contract details
    contract_name = Column(String(255), nullable=False)
    contract_date = Column(DateTime, nullable=False)
    
    # Drawing options
    partial_drawings = Column(Boolean, default=False)
    multiple_drawings = Column(Boolean, default=False)
    
    # Legal and verification
    applicable_law = Column(String(255), nullable=False, default="International Standby Practices ISP98")
    verification_code = Column(String(50), nullable=True)
    special_conditions = Column(Text, nullable=True)
    
    # Tracking
    status = Column(SQLEnum(SBLCStatus), nullable=False, default=SBLCStatus.DRAFT)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    created_by = relationship("User", foreign_keys=[created_by_id])
    last_updated_by_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    last_updated_by = relationship("User", foreign_keys=[last_updated_by_id])
    
    # Relationships
    amendments = relationship("SBLCAmendment", back_populates="sblc", cascade="all, delete-orphan")
    draws = relationship("SBLCDraw", back_populates="sblc", cascade="all, delete-orphan")
    
    def __init__(self, **kwargs):
        """Initialize a new SBLC with a unique reference number"""
        if 'reference_number' not in kwargs:
            # Generate unique reference number: NVC-SBLC-YYMMDD-XXXXX
            today = datetime.utcnow()
            random_part = str(uuid.uuid4().int)[:5]
            kwargs['reference_number'] = f"NVC-SBLC-{today.strftime('%y%m%d')}-{random_part}"
        
        # Set default verification code
        if 'verification_code' not in kwargs:
            kwargs['verification_code'] = str(uuid.uuid4().hex)[:8].upper()
            
        super().__init__(**kwargs)
    
    def days_until_expiry(self):
        """Calculate days remaining until expiry"""
        if not self.expiry_date:
            return None
            
        now = datetime.utcnow()
        if self.expiry_date < now:
            return None  # Already expired
            
        delta = self.expiry_date - now
        return delta.days
    
    def is_expired(self):
        """Check if the SBLC is expired"""
        return self.expiry_date < datetime.utcnow()
    
    def can_be_drawn(self):
        """Check if the SBLC can be drawn"""
        return (
            self.status == SBLCStatus.ISSUED and 
            not self.is_expired() and
            self.remaining_amount() > 0
        )
    
    def remaining_amount(self):
        """Calculate remaining drawable amount"""
        drawn_amount = sum(draw.amount for draw in self.draws if draw.status in [SBLCDrawStatus.APPROVED, SBLCDrawStatus.COMPLETED])
        return self.amount - drawn_amount
    
    def amount_in_words(self):
        """Convert amount to words"""
        try:
            return num2words(self.amount, lang='en', to='currency', currency=self.currency)
        except:
            # Fallback method if num2words fails
            return f"{self.amount} {self.currency}"

class SBLCAmendment(db.Model):
    """Amendment to a Standby Letter of Credit"""
    __tablename__ = 'sblc_amendment'
    
    id = Column(Integer, primary_key=True)
    sblc_id = Column(Integer, ForeignKey('standby_letter_of_credit.id'), nullable=False)
    sblc = relationship("StandbyLetterOfCredit", back_populates="amendments")
    
    amendment_number = Column(String(50), nullable=False)
    issue_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    effective_date = Column(DateTime, nullable=False)
    
    # Amendment details
    changes_description = Column(Text, nullable=False)
    new_amount = Column(Float, nullable=True)  # If amount is changed
    new_expiry_date = Column(DateTime, nullable=True)  # If expiry date is changed
    
    # Additional fields to track other changes
    beneficiary_changed = Column(Boolean, default=False)
    terms_changed = Column(Boolean, default=False)
    drawing_options_changed = Column(Boolean, default=False)
    
    # Changes detail JSON (to store specific changes)
    changes_json = Column(Text, nullable=True)
    
    # Tracking
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    created_by = relationship("User")
    
    def __init__(self, **kwargs):
        """Initialize a new SBLC Amendment with a sequential amendment number"""
        if 'amendment_number' not in kwargs and 'sblc' in kwargs:
            sblc = kwargs['sblc']
            amendment_count = len(sblc.amendments) + 1
            kwargs['amendment_number'] = f"{sblc.reference_number}-A{amendment_count:02d}"
        
        super().__init__(**kwargs)

class SBLCDraw(db.Model):
    """Draw against a Standby Letter of Credit"""
    __tablename__ = 'sblc_draw'
    
    id = Column(Integer, primary_key=True)
    sblc_id = Column(Integer, ForeignKey('standby_letter_of_credit.id'), nullable=False)
    sblc = relationship("StandbyLetterOfCredit", back_populates="draws")
    
    draw_reference = Column(String(50), nullable=False)
    request_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    amount = Column(Float, nullable=False)
    
    # Beneficiary bank account details for the draw
    beneficiary_account = Column(String(255), nullable=False)
    beneficiary_bank = Column(String(255), nullable=False)
    beneficiary_swift = Column(String(50), nullable=False)
    
    # Draw details
    reason = Column(Text, nullable=False)
    supporting_documents = Column(Text, nullable=True)  # JSON list of document references
    
    # Review and approval
    reviewer_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    review_date = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(SQLEnum(SBLCDrawStatus), nullable=False, default=SBLCDrawStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        """Initialize a new SBLC Draw with a unique reference number"""
        if 'draw_reference' not in kwargs and 'sblc' in kwargs:
            sblc = kwargs['sblc']
            draw_count = len(sblc.draws) + 1
            today = datetime.utcnow()
            kwargs['draw_reference'] = f"{sblc.reference_number}-D{draw_count:02d}-{today.strftime('%y%m%d')}"
        
        super().__init__(**kwargs)