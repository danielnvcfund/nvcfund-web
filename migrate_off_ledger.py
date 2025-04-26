#!/usr/bin/env python3
import sys
import os
import datetime
from flask import Flask
from sqlalchemy import create_engine, text
from app import db, create_app

"""
Migration script to add RTGS and Server-to-Server capabilities to the database.
This script will:
1. Add SCHEDULED to the transaction_status enum if it doesn't exist
2. Add rtgs_enabled and s2s_enabled columns to the financial_institution table
"""

def migrate_transaction_status_enum():
    """Add SCHEDULED to transaction_status enum type if not already present"""
    conn = db.engine.connect()
    
    # Check if SCHEDULED is already in the enum
    result = conn.execute(text("SELECT enum_range(NULL::transaction_status)")).fetchone()[0]
    if 'SCHEDULED' in result:
        print("SCHEDULED status already exists in transaction_status enum.")
        conn.close()
        return
    
    # Add SCHEDULED to the enum
    try:
        conn.execute(text("ALTER TYPE transaction_status ADD VALUE 'SCHEDULED'"))
        print("Successfully added SCHEDULED to transaction_status enum.")
    except Exception as e:
        print(f"Error adding SCHEDULED to enum: {str(e)}")
    finally:
        conn.close()

def add_off_ledger_columns():
    """Add rtgs_enabled and s2s_enabled columns to financial_institution table"""
    conn = db.engine.connect()
    
    # Check if columns already exist
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'financial_institution' 
        AND column_name IN ('rtgs_enabled', 's2s_enabled')
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
            WHERE institution_type IN ('bank', 'central_bank') 
            LIMIT 5
        """)).fetchall()
        
        if not institutions:
            print("No suitable institutions found to enable off-ledger capabilities.")
            return
            
        # Enable RTGS and S2S for these institutions
        for inst_id, name in institutions:
            db.session.execute(
                text("UPDATE financial_institution SET rtgs_enabled = TRUE, s2s_enabled = TRUE WHERE id = :id"),
                {"id": inst_id}
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
        print("Starting off-ledger capabilities migration...")
        
        # Run migrations
        migrate_transaction_status_enum()
        add_off_ledger_columns()
        enable_off_ledger_for_institutions()
        
        print("Migration completed successfully!")