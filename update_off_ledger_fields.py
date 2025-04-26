#!/usr/bin/env python3
import sys
import os
import datetime
from flask import Flask
from sqlalchemy import create_engine, text, inspect
from app import db, create_app

"""
Script to add RTGS and Server-to-Server capabilities to the database.
This script will add the required columns to the financial_institution table.
"""

def add_off_ledger_columns():
    """Add rtgs_enabled and s2s_enabled columns to financial_institution table"""
    conn = db.engine.connect()
    
    # Check if columns already exist
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'financial_institution' 
        AND column_name IN ('rtgs_enabled', 's2s_enabled', 'swift_code', 'account_number')
    """)).fetchall()
    
    existing_columns = [row[0] for row in result]
    
    # Add missing columns
    try:
        if 'rtgs_enabled' not in existing_columns:
            conn.execute(text("ALTER TABLE financial_institution ADD COLUMN rtgs_enabled BOOLEAN DEFAULT FALSE"))
            print("Added rtgs_enabled column to financial_institution table.")
        else:
            print("rtgs_enabled column already exists.")
            
        if 's2s_enabled' not in existing_columns:
            conn.execute(text("ALTER TABLE financial_institution ADD COLUMN s2s_enabled BOOLEAN DEFAULT FALSE"))
            print("Added s2s_enabled column to financial_institution table.")
        else:
            print("s2s_enabled column already exists.")
            
        # Check if swift_code and account_number columns exist
        if 'swift_code' not in existing_columns:
            conn.execute(text("ALTER TABLE financial_institution ADD COLUMN swift_code VARCHAR(11)"))
            print("Added swift_code column to financial_institution table.")
        else:
            print("swift_code column already exists.")
            
        if 'account_number' not in existing_columns:
            conn.execute(text("ALTER TABLE financial_institution ADD COLUMN account_number VARCHAR(64)"))
            print("Added account_number column to financial_institution table.")
        else:
            print("account_number column already exists.")
            
    except Exception as e:
        print(f"Error adding columns: {str(e)}")
    finally:
        conn.close()

def enable_off_ledger_for_institutions():
    """Enable RTGS and S2S for a few example institutions"""
    try:
        # Get some institutions to update as examples
        institutions = db.session.execute(text("""
            SELECT id, name FROM financial_institution 
            LIMIT 5
        """)).fetchall()
        
        if not institutions:
            print("No financial institutions found to enable off-ledger capabilities.")
            return
            
        # Enable RTGS and S2S for these institutions
        for inst_id, name in institutions:
            # Add some sample SWIFT codes and account numbers
            swift_code = f"NVCG{inst_id:04d}XXX"
            account_number = f"NVC{inst_id:06d}"
            
            db.session.execute(
                text("""
                    UPDATE financial_institution 
                    SET rtgs_enabled = TRUE, 
                        s2s_enabled = TRUE,
                        swift_code = :swift_code,
                        account_number = :account_number
                    WHERE id = :id
                """),
                {"id": inst_id, "swift_code": swift_code, "account_number": account_number}
            )
            print(f"Enabled RTGS and S2S for institution: {name} (ID: {inst_id})")
            
        db.session.commit()
        print("Successfully updated institutions with off-ledger capabilities.")
    except Exception as e:
        db.session.rollback()
        print(f"Error enabling off-ledger capabilities: {str(e)}")

if __name__ == "__main__":
    # Create app context
    app = create_app()
    
    with app.app_context():
        print("Starting off-ledger capabilities update...")
        
        # Run updates
        add_off_ledger_columns()
        enable_off_ledger_for_institutions()
        
        print("Update completed successfully!")