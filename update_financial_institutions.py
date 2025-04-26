#!/usr/bin/env python3
from flask import Flask
from sqlalchemy import text
from app import db, create_app

"""
Focused script to update the financial_institution table with the required columns
for off-ledger transactions (RTGS and Server-to-Server).
"""

def add_columns_to_financial_institution():
    """Add columns to financial_institution table for off-ledger capabilities"""
    conn = db.engine.connect()
    transaction = conn.begin()
    
    try:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'financial_institution'
        """)).fetchall()
        
        existing_columns = [row[0] for row in result]
        print(f"Existing columns in financial_institution: {existing_columns}")
        
        # Add rtgs_enabled column if it doesn't exist
        if 'rtgs_enabled' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE financial_institution 
                ADD COLUMN rtgs_enabled BOOLEAN DEFAULT FALSE
            """))
            print("Added rtgs_enabled column")
        else:
            print("rtgs_enabled column already exists")
        
        # Add s2s_enabled column if it doesn't exist
        if 's2s_enabled' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE financial_institution 
                ADD COLUMN s2s_enabled BOOLEAN DEFAULT FALSE
            """))
            print("Added s2s_enabled column")
        else:
            print("s2s_enabled column already exists")
        
        # Add swift_code column if it doesn't exist
        if 'swift_code' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE financial_institution 
                ADD COLUMN swift_code VARCHAR(11)
            """))
            print("Added swift_code column")
        else:
            print("swift_code column already exists")
        
        # Add account_number column if it doesn't exist
        if 'account_number' not in existing_columns:
            conn.execute(text("""
                ALTER TABLE financial_institution 
                ADD COLUMN account_number VARCHAR(64)
            """))
            print("Added account_number column")
        else:
            print("account_number column already exists")
        
        transaction.commit()
        print("Schema update completed successfully!")
    except Exception as e:
        transaction.rollback()
        print(f"Error updating schema: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    app = create_app()
    
    with app.app_context():
        print("Starting financial institution table update...")
        add_columns_to_financial_institution()
        print("Update completed.")