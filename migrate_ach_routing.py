"""
Database migration script to add ACH routing number field to FinancialInstitution table
"""
import os
from app import db, create_app
from sqlalchemy import Column, String

def migrate_database():
    """Add ACH routing number field to FinancialInstitution table"""
    print("Starting database migration for ACH routing number...")
    
    # Check if the column already exists
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('financial_institution')]
    
    if 'ach_routing_number' not in columns:
        print("Adding 'ach_routing_number' column to financial_institution table...")
        # Add the column
        db.engine.execute('ALTER TABLE financial_institution ADD COLUMN ach_routing_number VARCHAR(9)')
        print("✓ Column added successfully")
    else:
        print("Column 'ach_routing_number' already exists. Skipping.")
    
    print("Database migration completed successfully!")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        migrate_database()