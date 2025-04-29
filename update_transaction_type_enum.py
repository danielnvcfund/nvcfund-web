"""
Script to update the transactiontype enum in the database to include RTGS_TRANSFER
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
    cursor.execute("SELECT unnest(enum_range(NULL::transactiontype));")
    existing_values = [row[0] for row in cursor.fetchall()]
    print(f"Existing enum values: {existing_values}")
    
    # Step 2: Add RTGS_TRANSFER if it doesn't exist
    if 'RTGS_TRANSFER' not in existing_values:
        print("Adding 'RTGS_TRANSFER' to enum...")
        cursor.execute("ALTER TYPE transactiontype ADD VALUE 'RTGS_TRANSFER';")
        print("Added 'RTGS_TRANSFER' to the transactiontype enum successfully!")
    else:
        print("'RTGS_TRANSFER' already exists in the enum, no action needed.")
        
    # Add other missing transaction types if needed
    for transaction_type in [
        'SERVER_TO_SERVER',
        'TOKEN_EXCHANGE',
        'EDI_PAYMENT',
        'EDI_ACH_TRANSFER',
        'EDI_WIRE_TRANSFER',
        'TREASURY_TRANSFER',
        'TREASURY_INVESTMENT',
        'TREASURY_LOAN',
        'TREASURY_DEBT_REPAYMENT',
        'SALARY_PAYMENT',
        'BILL_PAYMENT',
        'CONTRACT_PAYMENT',
        'BULK_PAYROLL'
    ]:
        if transaction_type not in existing_values:
            print(f"Adding '{transaction_type}' to enum...")
            cursor.execute(f"ALTER TYPE transactiontype ADD VALUE '{transaction_type}';")
            print(f"Added '{transaction_type}' to the transactiontype enum successfully!")

    # Step 3: Verify the updated enum values
    cursor.execute("SELECT unnest(enum_range(NULL::transactiontype));")
    updated_values = [row[0] for row in cursor.fetchall()]
    print(f"\nUpdated enum values: {updated_values}")
    
    print("\nDatabase enum updated successfully!")
    
    # Close cursor and connection
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error updating enum: {str(e)}", file=sys.stderr)
    sys.exit(1)