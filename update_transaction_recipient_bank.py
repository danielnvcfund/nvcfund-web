"""
Script to update the transaction table by adding a recipient_bank column
"""

import os
import sys
from sqlalchemy import text
from app import db

def main():
    """Add recipient_bank column to transaction table"""
    try:
        print("Adding recipient_bank column to transaction table...")
        
        # Check if the column already exists
        check_query = text("SELECT column_name FROM information_schema.columns WHERE table_name='transaction' AND column_name='recipient_bank'")
        result = db.session.execute(check_query)
        if result.fetchone():
            print("Column recipient_bank already exists in the transaction table.")
            return
            
        # Add the new column
        alter_query = text("ALTER TABLE transaction ADD COLUMN recipient_bank VARCHAR(128)")
        db.session.execute(alter_query)
        db.session.commit()
        
        print("Successfully added recipient_bank column to transaction table.")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding column: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()