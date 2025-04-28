"""
Script to fix the financialinstitutiontype enum in the database
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect directly using the DATABASE_URL
db_url = os.environ.get('DATABASE_URL')
print(f"Using database URL: {db_url}")

try:
    # Connect directly using the DATABASE_URL
    conn = psycopg2.connect(db_url)
    
    # Set isolation level to autocommit - required for ALTER TYPE statements
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    # Create a cursor
    cursor = conn.cursor()
    
    # Step 1: Get existing enum values
    cursor.execute("SELECT unnest(enum_range(NULL::financialinstitutiontype));")
    existing_values = [row[0] for row in cursor.fetchall()]
    print(f"Existing enum values: {existing_values}")
    
    # Step 2: Check if we have a consistent format for enum values
    # Enum values are currently mixed case: 'BANK', 'central_bank', etc.
    # We need to ensure everything is uppercase
    
    # Add new uppercase enum values if needed
    if 'CENTRAL_BANK' not in existing_values:
        print("Adding 'CENTRAL_BANK' to enum...")
        cursor.execute("ALTER TYPE financialinstitutiontype ADD VALUE 'CENTRAL_BANK';")
        
    if 'GOVERNMENT' not in existing_values:
        print("Adding 'GOVERNMENT' to enum...")
        cursor.execute("ALTER TYPE financialinstitutiontype ADD VALUE 'GOVERNMENT';")

    # Make sure 'BANK' is among the enum values
    if 'BANK' not in existing_values:
        print("Adding 'BANK' to enum...")
        cursor.execute("ALTER TYPE financialinstitutiontype ADD VALUE 'BANK';")
        
    # Step 3: Update existing records to use uppercase values
    print("\nUpdating existing records to use uppercase enum values...")
    
    # Update lowercase 'central_bank' to uppercase 'CENTRAL_BANK'
    cursor.execute("UPDATE financial_institution SET institution_type = 'CENTRAL_BANK' WHERE institution_type = 'central_bank'")
    central_bank_count = cursor.rowcount
    print(f"Updated {central_bank_count} records from 'central_bank' to 'CENTRAL_BANK'")
    
    # Update lowercase 'government' to uppercase 'GOVERNMENT'
    cursor.execute("UPDATE financial_institution SET institution_type = 'GOVERNMENT' WHERE institution_type = 'government'")
    government_count = cursor.rowcount
    print(f"Updated {government_count} records from 'government' to 'GOVERNMENT'")
    
    # Update lowercase 'bank' to uppercase 'BANK'
    cursor.execute("UPDATE financial_institution SET institution_type = 'BANK' WHERE institution_type = 'bank'")
    bank_count = cursor.rowcount
    print(f"Updated {bank_count} records from 'bank' to 'BANK'")
    
    print("\nDatabase enum and records updated successfully!")
    
    # Close cursor and connection
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error updating enum: {str(e)}", file=sys.stderr)
    sys.exit(1)