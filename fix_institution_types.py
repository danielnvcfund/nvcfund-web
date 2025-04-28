"""
Script to update existing financial institutions with lowercase enum values
to use uppercase enum values to match our enum definition.
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
    
    # Set isolation level to autocommit
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    # Create a cursor
    cursor = conn.cursor()
    
    # Update lowercase 'central_bank' to uppercase 'CENTRAL_BANK'
    print("Updating 'central_bank' to 'CENTRAL_BANK'...")
    cursor.execute("UPDATE financial_institution SET institution_type = 'CENTRAL_BANK' WHERE institution_type = 'central_bank'")
    central_bank_count = cursor.rowcount
    
    # Update lowercase 'government' to uppercase 'GOVERNMENT'
    print("Updating 'government' to 'GOVERNMENT'...")
    cursor.execute("UPDATE financial_institution SET institution_type = 'GOVERNMENT' WHERE institution_type = 'government'")
    government_count = cursor.rowcount
    
    print(f"Updated {central_bank_count} records from 'central_bank' to 'CENTRAL_BANK'")
    print(f"Updated {government_count} records from 'government' to 'GOVERNMENT'")
    print("Database update completed successfully!")
    
    # Close cursor and connection
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error updating records: {str(e)}", file=sys.stderr)
    sys.exit(1)