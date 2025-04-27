#!/usr/bin/env python3
"""
Script to add recipient fields to the transaction table
"""
import os
import sys
from datetime import datetime
from app import app, db
from sqlalchemy import text

def add_recipient_fields():
    """Add recipient fields to transaction table"""
    print("Adding recipient fields to transaction table...")
    
    # Connect to the database
    with app.app_context():
        try:
            # Create the new columns if they don't exist
            db.session.execute(text("""
                ALTER TABLE transaction 
                ADD COLUMN IF NOT EXISTS recipient_name VARCHAR(128),
                ADD COLUMN IF NOT EXISTS recipient_institution VARCHAR(128),
                ADD COLUMN IF NOT EXISTS recipient_account VARCHAR(64),
                ADD COLUMN IF NOT EXISTS recipient_address VARCHAR(256),
                ADD COLUMN IF NOT EXISTS recipient_country VARCHAR(64)
            """))
            
            db.session.commit()
            print("Successfully added recipient fields to transaction table")
        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    # Execute the function
    add_recipient_fields()