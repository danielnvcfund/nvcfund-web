#!/usr/bin/env python
"""
Import Remaining CSV Accounts
This script imports the remaining account holders from the CSV file
by skipping those that already exist.
"""

import csv
import os
import sys
import logging
import psycopg2
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database connection parameters from environment
db_url = os.environ.get('DATABASE_URL')

if not db_url:
    logger.error("Error: DATABASE_URL environment variable not found.")
    sys.exit(1)

def parse_phone_number(phone_str):
    """Parse phone number string and clean it"""
    if not phone_str:
        return None
        
    # Handle scientific notation that Excel might have added
    if 'E' in phone_str or 'e' in phone_str:
        try:
            phone_float = float(phone_str)
            phone_str = str(int(phone_float))
        except ValueError:
            pass
    
    # Remove non-digit characters for standardization
    digits = ''.join(c for c in phone_str if c.isdigit())
    
    # Format consistently based on length
    if len(digits) == 10:  # US number without country code
        return f"+1{digits}"
    elif len(digits) > 10:  # Assume it already has country code
        return f"+{digits}"
    else:
        return digits  # Just return what we have if it doesn't fit patterns

def parse_currency_value(value_str):
    """Parse currency value string to float"""
    if not value_str:
        return 0.0
    
    # Remove commas and other non-numeric characters except decimal point
    clean_str = ''.join(c for c in value_str if c.isdigit() or c == '.')
    
    try:
        return float(clean_str)
    except ValueError:
        return 0.0

def import_remaining_accounts(csv_filepath):
    """
    Import the remaining account holders from CSV file
    
    Args:
        csv_filepath: Path to the CSV file containing account holder data
    """
    try:
        # Connect to the database directly
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Create a temporary file to log errors
        error_log_file = "import_errors.log"
        with open(error_log_file, "w") as error_file:
            # Track stats
            imported_count = 0
            skipped_count = 0
            error_count = 0
            
            # Get existing usernames to avoid querying for each row
            cursor.execute("SELECT username FROM account_holder")
            existing_usernames = set([r[0] for r in cursor.fetchall()])
            
            # Get existing emails to avoid duplicates
            cursor.execute("SELECT email FROM account_holder")
            existing_emails = set([r[0] for r in cursor.fetchall()])
            
            logger.info(f"Found {len(existing_usernames)} existing account holders")
            
            # Use ISO-8859-1 encoding as the file uses this encoding
            with open(csv_filepath, 'r', encoding='ISO-8859-1') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    # Check if account holder already exists by username
                    if row['username'] in existing_usernames:
                        skipped_count += 1
                        continue
                    
                    # Check if email already exists
                    if row['email'] in existing_emails:
                        skipped_count += 1
                        error_file.write(f"Skipping {row.get('name', 'unknown')}: Email {row['email']} already exists.\n")
                        continue
                    
                    try:
                        # Get current time for timestamps
                        try:
                            created_at = datetime.strptime(row['creationdate'], '%m/%d/%Y %H:%M')
                        except (ValueError, KeyError):
                            created_at = datetime.utcnow()
                        
                        now = datetime.utcnow().isoformat()
                        
                        # Insert account holder
                        cursor.execute("""
                            INSERT INTO account_holder 
                            (name, username, email, created_at, updated_at, broker, kyc_verified, aml_verified) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                        """, (
                            row['name'],
                            row['username'],
                            row['email'],
                            created_at,
                            created_at,
                            row.get('broker', ''),
                            True,
                            True
                        ))
                        
                        account_holder_id = cursor.fetchone()[0]
                        
                        # Update our local cache of existing data
                        existing_usernames.add(row['username'])
                        existing_emails.add(row['email'])
                        
                        # Insert address
                        if row.get('address.line1'):
                            cursor.execute("""
                                INSERT INTO address
                                (name, line1, line2, pobox, neighborhood, city, region, zip, country, 
                                 street, building_number, complement, account_holder_id, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                row.get('address.name', 'Primary Address'),
                                row.get('address.line1', ''),
                                row.get('address.line2', ''),
                                row.get('address.pobox', ''),
                                row.get('address.neighborhood', ''),
                                row.get('address.city', ''),
                                row.get('address.region', ''),
                                row.get('address.zip', ''),
                                row.get('address.country', 'US'),
                                row.get('address.street', ''),
                                row.get('address.buildingnumber', ''),
                                row.get('address.complement', ''),
                                account_holder_id,
                                now,
                                now
                            ))
                        
                        # Insert mobile phone
                        if row.get('mobile.number'):
                            cursor.execute("""
                                INSERT INTO phone_number
                                (name, number, is_primary, is_mobile, account_holder_id, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (
                                row.get('mobile.name', 'Mobile'),
                                parse_phone_number(row.get('mobile.number', '')),
                                True,
                                True,
                                account_holder_id,
                                now,
                                now
                            ))
                        
                        # Insert landline phone
                        if row.get('landline.number'):
                            cursor.execute("""
                                INSERT INTO phone_number
                                (name, number, is_primary, is_mobile, account_holder_id, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (
                                row.get('landline.name', 'Landline'),
                                parse_phone_number(row.get('landline.number', '')),
                                False,
                                False,
                                account_holder_id,
                                now,
                                now
                            ))
                        
                        # Create bank accounts
                        currencies = [
                            'USD', 'EUR', 'GBP', 'BTC', 'NGN', 
                            'SPU', 'TU', 'ZCASH', 'NVC-Coin'
                        ]
                        
                        for currency in currencies:
                            # Get the corresponding column name
                            column_name = f'Member Account {currency}'
                            
                            # Skip if the column doesn't exist or balance is 0
                            if column_name not in row or not row[column_name]:
                                continue
                                
                            # Map NVC-Coin to NVCT for our enum
                            currency_enum_value = currency
                            if currency == 'NVC-Coin':
                                currency_enum_value = 'NVCT'
                                
                            # Parse the balance value
                            balance = parse_currency_value(row[column_name])
                            
                            # Skip if balance is 0
                            if balance == 0:
                                continue
                                
                            # Create a consistent account number based on username and currency
                            account_number = f"{currency_enum_value}-{row['username']}"
                            account_name = f"{row['name']} {currency_enum_value} Account"
                            
                            cursor.execute("""
                                INSERT INTO bank_account
                                (account_number, account_name, account_type, currency, balance, available_balance, 
                                 status, account_holder_id, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                account_number,
                                account_name,
                                "CHECKING",
                                currency_enum_value,
                                balance,
                                balance,
                                "ACTIVE",
                                account_holder_id,
                                now,
                                now
                            ))
                        
                        # Commit all changes
                        conn.commit()
                        logger.info(f"Successfully imported account holder: {row['name']} ({row['username']})")
                        imported_count += 1
                        
                        # Print progress every 10 records
                        if imported_count % 10 == 0:
                            logger.info(f"Progress: {imported_count} imported, {skipped_count} skipped, {error_count} errors")
                        
                    except Exception as e:
                        conn.rollback()
                        error_msg = f"Error importing account holder {row.get('name', 'unknown')}: {str(e)}"
                        logger.error(error_msg)
                        error_file.write(f"{error_msg}\n")
                        error_count += 1
                
        # Log summary
        logger.info(f"Import summary: {imported_count} imported, {skipped_count} skipped, {error_count} errors")
        logger.info(f"Error details written to {error_log_file}")
        return imported_count, skipped_count, error_count
            
    except Exception as e:
        logger.error(f"Error in import process: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return 0, 0, 1
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

def main():
    """Main function to run the import"""
    csv_file_path = 'attached_assets/NVC PB ACCOUNTS HOLDERS.csv'
    
    if not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
        sys.exit(1)
    
    try:
        # Run the import for all records (more efficient version)
        logger.info("Starting import of ALL remaining account holders from CSV file...")
        imported, skipped, errors = import_remaining_accounts(csv_file_path)
        
        if errors > 0:
            logger.warning(f"Import completed with {errors} errors. Please check the logs.")
            sys.exit(1)
        else:
            logger.info(f"Import completed successfully: {imported} imported, {skipped} skipped.")
            sys.exit(0)
                
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()