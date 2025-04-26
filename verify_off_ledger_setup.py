#!/usr/bin/env python3
from flask import Flask
from sqlalchemy import text
from app import db, create_app
import requests

"""
Script to verify that the off-ledger capabilities were successfully
set up in both the database schema and the web interface.
"""

def verify_database_schema():
    """Verify database schema changes"""
    conn = db.engine.connect()
    
    try:
        # Check transaction status enum values
        result = conn.execute(text("""
            SELECT enumlabel FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'transactionstatus'
        """)).fetchall()
        
        tx_status_values = [row[0] for row in result]
        print(f"TransactionStatus enum values: {tx_status_values}")
        
        has_scheduled = 'SCHEDULED' in tx_status_values
        if has_scheduled:
            print("✓ SCHEDULED status is present in TransactionStatus enum")
        else:
            print("✗ SCHEDULED status is missing from TransactionStatus enum")
        
        # Check transaction type enum values
        result = conn.execute(text("""
            SELECT enumlabel FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'transactiontype'
        """)).fetchall()
        
        tx_type_values = [row[0] for row in result]
        print(f"TransactionType enum values: {tx_type_values}")
        
        has_rtgs = 'RTGS_TRANSFER' in tx_type_values
        has_s2s = 'SERVER_TO_SERVER' in tx_type_values
        
        if has_rtgs:
            print("✓ RTGS_TRANSFER type is present in TransactionType enum")
        else:
            print("✗ RTGS_TRANSFER type is missing from TransactionType enum")
            
        if has_s2s:
            print("✓ SERVER_TO_SERVER type is present in TransactionType enum")
        else:
            print("✗ SERVER_TO_SERVER type is missing from TransactionType enum")
        
        # Check financial institution table columns
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'financial_institution'
        """)).fetchall()
        
        fi_columns = [row[0] for row in result]
        print(f"Financial Institution columns: {fi_columns}")
        
        has_rtgs_enabled = 'rtgs_enabled' in fi_columns
        has_s2s_enabled = 's2s_enabled' in fi_columns
        has_swift_code = 'swift_code' in fi_columns
        has_account_number = 'account_number' in fi_columns
        
        if has_rtgs_enabled:
            print("✓ rtgs_enabled column exists in financial_institution table")
        else:
            print("✗ rtgs_enabled column is missing from financial_institution table")
            
        if has_s2s_enabled:
            print("✓ s2s_enabled column exists in financial_institution table")
        else:
            print("✗ s2s_enabled column is missing from financial_institution table")
            
        if has_swift_code:
            print("✓ swift_code column exists in financial_institution table")
        else:
            print("✗ swift_code column is missing from financial_institution table")
            
        if has_account_number:
            print("✓ account_number column exists in financial_institution table")
        else:
            print("✗ account_number column is missing from financial_institution table")
        
        # Verify if any financial institutions have these capabilities enabled
        if has_rtgs_enabled and has_s2s_enabled:
            try:
                result = conn.execute(text("""
                    SELECT id, name, rtgs_enabled, s2s_enabled 
                    FROM financial_institution 
                    WHERE rtgs_enabled = TRUE OR s2s_enabled = TRUE
                """)).fetchall()
                
                if result:
                    print(f"\nFinancial institutions with off-ledger capabilities:")
                    for row in result:
                        print(f"  ID: {row[0]}, Name: {row[1]}, RTGS: {row[2]}, S2S: {row[3]}")
                else:
                    print("\nNo financial institutions have off-ledger capabilities enabled yet.")
            except Exception as e:
                print(f"Error checking financial institutions: {str(e)}")
    except Exception as e:
        print(f"Error verifying database schema: {str(e)}")
    finally:
        conn.close()

def enable_capabilities_for_institutions():
    """Enable off-ledger capabilities for financial institutions"""
    conn = db.engine.connect()
    transaction = conn.begin()
    
    try:
        # Get some financial institutions
        result = conn.execute(text("""
            SELECT id, name FROM financial_institution LIMIT 5
        """)).fetchall()
        
        if not result:
            print("No financial institutions found")
            return
            
        print("\nEnabling off-ledger capabilities for financial institutions:")
        
        # Enable capabilities for each institution
        for inst_id, name in result:
            # Generate example values
            swift_code = f"NVC{inst_id:04d}XX"
            account_number = f"NVC{inst_id:08d}"
            
            # Update the institution with off-ledger capabilities
            conn.execute(
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
            
            print(f"  Enabled for {name} (ID: {inst_id})")
        
        transaction.commit()
        print("Financial institutions updated successfully!")
    except Exception as e:
        transaction.rollback()
        print(f"Error enabling capabilities: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    app = create_app()
    
    with app.app_context():
        print("\n=== Verifying Off-Ledger Transaction Setup ===\n")
        
        print("--- Database Schema Verification ---")
        verify_database_schema()
        
        print("\n--- Enabling Capabilities for Financial Institutions ---")
        enable_capabilities_for_institutions()
        
        print("\n=== Verification Complete ===\n")