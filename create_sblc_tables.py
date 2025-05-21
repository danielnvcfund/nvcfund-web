"""
Create SBLC database tables script - Lightweight version
"""
import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Get database connection string from environment
database_url = os.environ.get('DATABASE_URL')
print(f"Connecting to database...")

# Create SQLAlchemy engine
engine = create_engine(database_url)
Base = declarative_base()

# Define models directly
class StandbyLetterOfCredit(Base):
    __tablename__ = 'standby_letter_of_credit'
    
    id = Column(Integer, primary_key=True)
    reference_number = Column(String(50), unique=True, nullable=False)
    
    # Parties
    applicant_id = Column(Integer, ForeignKey('account_holder.id'), nullable=False)
    applicant_account_number = Column(String(50), nullable=False)
    applicant_contact_info = Column(String(255), nullable=True)
    
    beneficiary_name = Column(String(255), nullable=False)
    beneficiary_address = Column(Text, nullable=False)
    beneficiary_account_number = Column(String(50), nullable=True)
    beneficiary_bank_name = Column(String(255), nullable=False)
    beneficiary_bank_swift = Column(String(50), nullable=True)
    beneficiary_bank_address = Column(Text, nullable=True)
    
    # Issuing Bank
    issuing_bank_id = Column(Integer, ForeignKey('financial_institution.id'), nullable=True)
    
    # Financial Details
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    
    # Dates and Location
    issue_date = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime, nullable=False)
    expiry_place = Column(String(100), nullable=False)
    
    # Contract Details
    contract_name = Column(String(100), nullable=True)
    contract_date = Column(DateTime, nullable=True)
    
    # Drawing Options
    partial_drawings = Column(Boolean, default=False)
    multiple_drawings = Column(Boolean, default=False)
    
    # Legal Information
    applicable_law = Column(String(255), nullable=True)
    verification_code = Column(String(50), nullable=True)
    special_conditions = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), default="draft", nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('user.id'))
    last_updated_by_id = Column(Integer, ForeignKey('user.id'))

class SBLCAmendment(Base):
    __tablename__ = 'sblc_amendment'
    
    id = Column(Integer, primary_key=True)
    sblc_id = Column(Integer, ForeignKey('standby_letter_of_credit.id'), nullable=False)
    amendment_number = Column(String(20), nullable=False)
    
    # Amendment details
    amount_changed = Column(Boolean, default=False)
    previous_amount = Column(Float, nullable=True)
    new_amount = Column(Float, nullable=True)
    
    expiry_date_changed = Column(Boolean, default=False)
    previous_expiry_date = Column(DateTime, nullable=True)
    new_expiry_date = Column(DateTime, nullable=True)
    
    description = Column(Text, nullable=False)
    amendment_date = Column(DateTime, default=datetime.utcnow)
    
    # Status
    status = Column(String(20), default="pending", nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('user.id'))

class SBLCDraw(Base):
    __tablename__ = 'sblc_draw'
    
    id = Column(Integer, primary_key=True)
    sblc_id = Column(Integer, ForeignKey('standby_letter_of_credit.id'), nullable=False)
    draw_reference = Column(String(50), nullable=False)
    
    # Draw details
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    
    description = Column(Text, nullable=False)
    documents_provided = Column(Text, nullable=True)
    draw_date = Column(DateTime, default=datetime.utcnow)
    
    # Status
    status = Column(String(20), default="pending", nullable=False)
    status_notes = Column(Text, nullable=True)
    
    # Processing details
    processed_date = Column(DateTime, nullable=True)
    processed_by_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('user.id'))

# Create tables
print("Creating SBLC tables...")
try:
    StandbyLetterOfCredit.__table__.create(engine, checkfirst=True)
    SBLCAmendment.__table__.create(engine, checkfirst=True)
    SBLCDraw.__table__.create(engine, checkfirst=True)
    print("SBLC tables created successfully!")
except Exception as e:
    print(f"Error creating tables: {str(e)}")

# Verify the tables were created
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print("Available tables in database:")
for table in tables:
    print(f"- {table}")
    
if 'standby_letter_of_credit' in tables:
    print("\n✅ SBLC tables created successfully!")
else:
    print("\n❌ SBLC tables were not created. Please check the error above.")