"""
Create SBLC database tables directly
"""
import os
import sys
from datetime import datetime

# Get the database URL from environment variable
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

print(f"Creating SBLC tables directly in database...")

# Import SQLAlchemy components
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Text, ForeignKey, DateTime, Boolean, Enum
import enum

# Create engine
engine = create_engine(database_url)
metadata = MetaData()

# Define tables directly without ORM
standby_letter_of_credit = Table(
    'standby_letter_of_credit', 
    metadata,
    Column('id', Integer, primary_key=True),
    Column('reference_number', String(50), unique=True, nullable=False),
    Column('applicant_id', Integer, ForeignKey('account_holder.id'), nullable=False),
    Column('applicant_account_number', String(50), nullable=False),
    Column('applicant_contact_info', String(255), nullable=True),
    Column('beneficiary_name', String(255), nullable=False),
    Column('beneficiary_address', Text, nullable=False),
    Column('beneficiary_account_number', String(50), nullable=True),
    Column('beneficiary_bank_name', String(255), nullable=False),
    Column('beneficiary_bank_swift', String(50), nullable=True),
    Column('beneficiary_bank_address', Text, nullable=True),
    Column('issuing_bank_id', Integer, ForeignKey('financial_institution.id'), nullable=True),
    Column('amount', Float, nullable=False),
    Column('currency', String(10), nullable=False),
    Column('issue_date', DateTime, default=datetime.utcnow),
    Column('expiry_date', DateTime, nullable=False),
    Column('expiry_place', String(100), nullable=False),
    Column('contract_name', String(100), nullable=True),
    Column('contract_date', DateTime, nullable=True),
    Column('partial_drawings', Boolean, default=False),
    Column('multiple_drawings', Boolean, default=False),
    Column('applicable_law', String(255), nullable=True),
    Column('verification_code', String(50), nullable=True),
    Column('special_conditions', Text, nullable=True),
    Column('status', String(20), default="draft", nullable=False),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    Column('created_by_id', Integer, ForeignKey('user.id')),
    Column('last_updated_by_id', Integer, ForeignKey('user.id'))
)

sblc_amendment = Table(
    'sblc_amendment', 
    metadata,
    Column('id', Integer, primary_key=True),
    Column('sblc_id', Integer, ForeignKey('standby_letter_of_credit.id'), nullable=False),
    Column('amendment_number', String(20), nullable=False),
    Column('amount_changed', Boolean, default=False),
    Column('previous_amount', Float, nullable=True),
    Column('new_amount', Float, nullable=True),
    Column('expiry_date_changed', Boolean, default=False),
    Column('previous_expiry_date', DateTime, nullable=True),
    Column('new_expiry_date', DateTime, nullable=True),
    Column('description', Text, nullable=False),
    Column('amendment_date', DateTime, default=datetime.utcnow),
    Column('status', String(20), default="pending", nullable=False),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('created_by_id', Integer, ForeignKey('user.id'))
)

sblc_draw = Table(
    'sblc_draw', 
    metadata,
    Column('id', Integer, primary_key=True),
    Column('sblc_id', Integer, ForeignKey('standby_letter_of_credit.id'), nullable=False),
    Column('draw_reference', String(50), nullable=False),
    Column('amount', Float, nullable=False),
    Column('currency', String(10), nullable=False),
    Column('description', Text, nullable=False),
    Column('documents_provided', Text, nullable=True),
    Column('draw_date', DateTime, default=datetime.utcnow),
    Column('status', String(20), default="pending", nullable=False),
    Column('status_notes', Text, nullable=True),
    Column('processed_date', DateTime, nullable=True),
    Column('processed_by_id', Integer, ForeignKey('user.id'), nullable=True),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('created_by_id', Integer, ForeignKey('user.id'))
)

# Create tables
try:
    # Create tables
    print("Creating tables...")
    metadata.create_all(engine, checkfirst=True)
    print("Tables created successfully!")
    
    # Verify tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("\nAvailable tables in database:")
    for table in tables:
        if table in ['standby_letter_of_credit', 'sblc_amendment', 'sblc_draw']:
            print(f"✅ {table}")
    
    if 'standby_letter_of_credit' in tables and 'sblc_amendment' in tables and 'sblc_draw' in tables:
        print("\n✅ All SBLC tables created successfully!")
    else:
        print("\n❌ Some SBLC tables are missing. Please check the error logs.")
    
except Exception as e:
    print(f"Error creating tables: {str(e)}")
    sys.exit(1)