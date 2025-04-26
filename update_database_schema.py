#!/usr/bin/env python3
import sys
import os
import datetime
from flask import Flask
from sqlalchemy import create_engine, text, inspect
from app import db, create_app

"""
Script to update the database schema for off-ledger capabilities.
This will:
1. Add new values to TransactionStatus enum if needed
2. Add new columns to financial_institution table
3. Update existing institutions with off-ledger capabilities
"""

def update_transaction_status_enum():
    """Add missing values to transaction_status enum type"""
    conn = db.engine.connect()
    
    try:
        # Get current enum values
        result = conn.execute(text("""
            SELECT enumlabel FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'transactionstatus'
        """)).fetchall()
        
        current_values = [row[0] for row in result]
        print(f"Current transaction status values: {current_values}")
        
        # Define missing values
        missing_values = []
        for value in ['CANCELLED', 'REJECTED', 'SCHEDULED']:
            if value not in current_values:
                missing_values.append(value)
        
        if missing_values:
            for value in missing_values:
                conn.execute(text(f"""
                    ALTER TYPE transactionstatus ADD VALUE '{value}'
                """))
                print(f"Added '{value}' to transactionstatus enum")
        else:
            print("No missing values to add to transactionstatus enum")
    except Exception as e:
        print(f"Error updating transaction status enum: {str(e)}")
    finally:
        conn.close()

def update_transaction_type_enum():
    """Add missing values to transaction_type enum type"""
    conn = db.engine.connect()
    
    try:
        # Get current enum values
        result = conn.execute(text("""
            SELECT enumlabel FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'transactiontype'
        """)).fetchall()
        
        current_values = [row[0] for row in result]
        print(f"Current transaction type values: {current_values}")
        
        # Define missing values
        missing_values = []
        for value in ['RTGS_TRANSFER', 'SERVER_TO_SERVER']:
            if value not in current_values:
                missing_values.append(value)
        
        if missing_values:
            for value in missing_values:
                conn.execute(text(f"""
                    ALTER TYPE transactiontype ADD VALUE '{value}'
                """))
                print(f"Added '{value}' to transactiontype enum")
        else:
            print("No missing values to add to transactiontype enum")
    except Exception as e:
        print(f"Error updating transaction type enum: {str(e)}")
    finally:
        conn.close()

def add_columns_to_financial_institution():
    """Add missing columns to financial_institution table"""
    conn = db.engine.connect()
    
    try:
        # Check if columns already exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'financial_institution'
        """)).fetchall()
        
        existing_columns = [row[0] for row in result]
        print(f"Existing columns in financial_institution: {existing_columns}")
        
        # Define columns to add
        columns_to_add = {
            'rtgs_enabled': 'BOOLEAN DEFAULT FALSE',
            's2s_enabled': 'BOOLEAN DEFAULT FALSE',
            'swift_code': 'VARCHAR(11)',
            'account_number': 'VARCHAR(64)'
        }
        
        # Add missing columns
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                conn.execute(text(f"""
                    ALTER TABLE financial_institution 
                    ADD COLUMN {column_name} {column_type}
                """))
                print(f"Added {column_name} column to financial_institution table")
            else:
                print(f"{column_name} column already exists")
    except Exception as e:
        print(f"Error adding columns: {str(e)}")
    finally:
        conn.close()

def update_financial_institutions():
    """Update existing financial institutions with off-ledger capabilities"""
    conn = db.engine.connect()
    
    try:
        # Get financial institutions
        result = conn.execute(text("""
            SELECT id, name FROM financial_institution LIMIT 5
        """)).fetchall()
        
        if not result:
            print("No financial institutions found")
            return
        
        print(f"Found {len(result)} financial institutions to update")
        
        # Update institutions one by one
        for institution_id, name in result:
            # Generate SWIFT code and account number based on ID
            swift_code = f"NVC{institution_id:04d}XX"
            account_number = f"NVC{institution_id:08d}"
            
            # We'll use individual updates to avoid errors if any column is missing
            try:
                conn.execute(text("""
                    UPDATE financial_institution 
                    SET rtgs_enabled = TRUE 
                    WHERE id = :id
                """), {"id": institution_id})
                
                conn.execute(text("""
                    UPDATE financial_institution 
                    SET s2s_enabled = TRUE 
                    WHERE id = :id
                """), {"id": institution_id})
                
                conn.execute(text("""
                    UPDATE financial_institution 
                    SET swift_code = :swift_code 
                    WHERE id = :id
                """), {"id": institution_id, "swift_code": swift_code})
                
                conn.execute(text("""
                    UPDATE financial_institution 
                    SET account_number = :account_number 
                    WHERE id = :id
                """), {"id": institution_id, "account_number": account_number})
                
                print(f"Updated institution: {name} (ID: {institution_id}) with off-ledger capabilities")
            except Exception as e:
                print(f"Error updating institution {name} (ID: {institution_id}): {str(e)}")
                
        conn.commit()
        print("Financial institutions updated successfully")
    except Exception as e:
        print(f"Error updating financial institutions: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Create app context
    app = create_app()
    
    with app.app_context():
        print("\n=== Starting database schema update ===\n")
        
        # Step 1: Update TransactionStatus enum
        print("\n--- Updating TransactionStatus enum ---")
        update_transaction_status_enum()
        
        # Step 2: Update TransactionType enum
        print("\n--- Updating TransactionType enum ---")
        update_transaction_type_enum()
        
        # Step 3: Add columns to financial_institution table
        print("\n--- Adding columns to financial_institution table ---")
        add_columns_to_financial_institution()
        
        # Step 4: Update financial institutions
        print("\n--- Updating financial institutions ---")
        update_financial_institutions()
        
        print("\n=== Database schema update completed ===\n")