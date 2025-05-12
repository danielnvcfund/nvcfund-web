"""
Direct migration using SQLAlchemy to add tx_hash column to blockchain_transaction table
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column, String

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("Error: DATABASE_URL not set in environment")
    sys.exit(1)

try:
    # Create engine
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    # Check if table exists
    if 'blockchain_transaction' not in inspector.get_table_names():
        print("Table blockchain_transaction does not exist, nothing to do")
        sys.exit(0)
    
    # Check if column exists
    columns = [col['name'] for col in inspector.get_columns('blockchain_transaction')]
    if 'tx_hash' in columns:
        print("Column tx_hash already exists in blockchain_transaction table")
        sys.exit(0)
    
    # Add column
    print("Adding tx_hash column to blockchain_transaction table...")
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE blockchain_transaction ADD COLUMN tx_hash VARCHAR(66) UNIQUE;"))
    
    print("Column tx_hash added successfully")
    sys.exit(0)
    
except Exception as e:
    print(f"Migration error: {str(e)}")
    sys.exit(1)