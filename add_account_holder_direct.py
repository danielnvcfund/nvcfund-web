#!/usr/bin/env python
"""
Add account holder directly to the database
This script creates a test account holder directly using raw SQL queries
"""

import os
import sys
import logging
import psycopg2
from datetime import datetime

# Get database connection parameters from environment
db_url = os.environ.get('DATABASE_URL')

if not db_url:
    print("Error: DATABASE_URL environment variable not found.")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Connect to the database directly
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # Check if the test account holder already exists
    cursor.execute("SELECT id FROM account_holder WHERE username = 'testaccount'")
    existing = cursor.fetchone()
    
    if existing:
        logger.info("Test account holder already exists. Skipping.")
    else:
        # Get current time for timestamps
        now = datetime.utcnow().isoformat()
        
        # Insert account holder
        cursor.execute("""
            INSERT INTO account_holder 
            (name, username, email, created_at, updated_at, kyc_verified, aml_verified) 
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, ("Test Account", "testaccount", "test@example.com", now, now, True, True))
        
        account_holder_id = cursor.fetchone()[0]
        logger.info(f"Created account holder with ID: {account_holder_id}")
        
        # Insert address
        cursor.execute("""
            INSERT INTO address
            (name, line1, city, region, zip, country, account_holder_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, ("Primary Address", "123 Test Street", "Test City", "Test State", "12345", 
              "US", account_holder_id, now, now))
        
        # Insert phone number
        cursor.execute("""
            INSERT INTO phone_number
            (name, number, is_primary, is_mobile, account_holder_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ("Mobile", "+15551234567", True, True, account_holder_id, now, now))
        
        # Check account_type enum values
        cursor.execute("SELECT unnest(enum_range(NULL::accounttype))::text")
        account_types = cursor.fetchall()
        logger.info(f"Available account types: {account_types}")
        
        # Check currency enum values
        cursor.execute("SELECT unnest(enum_range(NULL::currencytype))::text")
        currency_types = cursor.fetchall()
        logger.info(f"Available currency types: {currency_types}")
        
        # Check account status enum values
        cursor.execute("SELECT unnest(enum_range(NULL::accountstatus))::text")
        account_status_types = cursor.fetchall()
        logger.info(f"Available account status types: {account_status_types}")
        
        # Insert bank accounts - USD
        cursor.execute("""
            INSERT INTO bank_account
            (account_number, account_name, account_type, currency, balance, available_balance, 
             status, account_holder_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, ("USD-testaccount", "Test USD Account", "CHECKING", "USD", 10000.00, 10000.00, 
              "ACTIVE", account_holder_id, now, now))
        
        # Insert bank accounts - NVCT
        cursor.execute("""
            INSERT INTO bank_account
            (account_number, account_name, account_type, currency, balance, available_balance, 
             status, account_holder_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, ("NVCT-testaccount", "Test NVCT Account", "CUSTODY", "NVCT", 5000.00, 5000.00, 
              "ACTIVE", account_holder_id, now, now))
        
        # Commit all changes
        conn.commit()
        logger.info("Successfully added test account holder with address, phone and accounts")

except Exception as e:
    logger.error(f"Error creating account holder: {str(e)}")
    if 'conn' in locals():
        conn.rollback()
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()