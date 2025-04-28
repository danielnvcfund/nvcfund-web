"""
Script to update the financialinstitutiontype enum in the database
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
    
    # Check existing enum values
    cursor.execute("SELECT unnest(enum_range(NULL::financialinstitutiontype));")
    existing_values = [row[0].lower() for row in cursor.fetchall()]
    
    print(f"Existing enum values: {existing_values}")
    
    # Add new enum values if they don't exist
    if 'central_bank' not in existing_values:
        print("Adding 'central_bank' to enum...")
        cursor.execute("ALTER TYPE financialinstitutiontype ADD VALUE 'central_bank';")
        
    if 'government' not in existing_values:
        print("Adding 'government' to enum...")
        cursor.execute("ALTER TYPE financialinstitutiontype ADD VALUE 'government';")
    
    print("Enum update completed successfully!")
    
    # Close cursor and connection
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error updating enum: {str(e)}", file=sys.stderr)
    sys.exit(1)