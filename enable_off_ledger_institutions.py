#!/usr/bin/env python3
import sys
import os
import datetime
from flask import Flask
from sqlalchemy import create_engine, text, inspect
from app import db, create_app

"""
Script to enable RTGS and Server-to-Server capabilities for financial institutions.
"""

def enable_off_ledger_for_institutions():
    """Enable RTGS and S2S for financial institutions"""
    conn = db.engine.connect()
    
    try:
        # Get financial institutions
        result = conn.execute(text("SELECT id, name FROM financial_institution LIMIT 5")).fetchall()
        
        if not result:
            print("No financial institutions found.")
            return
            
        # Enable features for each institution
        for institution_id, name in result:
            # Generate sample SWIFT code and account number
            swift_code = f"NVCG{institution_id:04d}XXX"
            account_number = f"NVC{institution_id:06d}"
            
            # Update one institution at a time with individual fields
            conn.execute(
                text("UPDATE financial_institution SET rtgs_enabled = TRUE WHERE id = :id"),
                {"id": institution_id}
            )
            
            conn.execute(
                text("UPDATE financial_institution SET s2s_enabled = TRUE WHERE id = :id"),
                {"id": institution_id}
            )
            
            conn.execute(
                text("UPDATE financial_institution SET swift_code = :swift_code WHERE id = :id"),
                {"id": institution_id, "swift_code": swift_code}
            )
            
            conn.execute(
                text("UPDATE financial_institution SET account_number = :account_number WHERE id = :id"),
                {"id": institution_id, "account_number": account_number}
            )
            
            print(f"Enabled RTGS and S2S capabilities for institution: {name} (ID: {institution_id})")
            
        print("Successfully updated institutions with off-ledger capabilities.")
    except Exception as e:
        print(f"Error enabling off-ledger capabilities: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Create app context
    app = create_app()
    
    with app.app_context():
        print("Starting to enable off-ledger capabilities for institutions...")
        enable_off_ledger_for_institutions()
        print("Update completed.")