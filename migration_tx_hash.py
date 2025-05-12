"""
Migration script to add tx_hash column to blockchain_transaction table
Run directly from the Flask shell
"""
from sqlalchemy import text
from app import db

def run_migration():
    try:
        # Check if table exists
        result = db.session.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'blockchain_transaction');"
        ))
        
        if not result.scalar():
            print("Table blockchain_transaction does not exist, nothing to do")
            return
        
        # Check if column exists
        result = db.session.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'blockchain_transaction' AND column_name = 'tx_hash');"
        ))
        
        if result.scalar():
            print("Column tx_hash already exists in blockchain_transaction table")
            return
        
        # Add column
        print("Adding tx_hash column to blockchain_transaction table...")
        db.session.execute(text(
            "ALTER TABLE blockchain_transaction ADD COLUMN tx_hash VARCHAR(66) UNIQUE;"
        ))
        db.session.commit()
        print("Column tx_hash added successfully")
        
    except Exception as e:
        db.session.rollback()
        print(f"Migration error: {str(e)}")

# Function will be executed when imported in Flask shell
run_migration()