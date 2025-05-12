"""
Add missing tx_hash column to blockchain_transaction table
"""
import os
import sys
from flask import Flask
from sqlalchemy import text
from app import db, app

def add_tx_hash_column():
    """Add tx_hash column to blockchain_transaction table if it doesn't exist"""
    
    with app.app_context():
        try:
            # Check if the column already exists
            result = db.session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'blockchain_transaction' AND column_name = 'tx_hash');"
            ))
            column_exists = result.scalar()
            
            if column_exists:
                print("Column tx_hash already exists in blockchain_transaction table")
                return True
            
            # Add the column
            print("Adding tx_hash column to blockchain_transaction table...")
            db.session.execute(text(
                "ALTER TABLE blockchain_transaction ADD COLUMN tx_hash VARCHAR(66) UNIQUE;"
            ))
            db.session.commit()
            
            print("Column tx_hash added successfully")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")
            return False

if __name__ == "__main__":
    result = add_tx_hash_column()
    sys.exit(0 if result else 1)