#!/usr/bin/env python
"""
Import Account Holders Script
This script imports account holders from a CSV file into the NVC Banking Platform.
"""

import csv
import os
import sys
import logging
from datetime import datetime
import json
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError
from app import create_app, db
from account_holder_models import (
    AccountHolder, Address, PhoneNumber, BankAccount,
    AccountType, AccountStatus, CurrencyType
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_phone_number(phone_str):
    """Parse phone number string and clean it"""
    if not phone_str:
        return None
        
    # Handle scientific notation that Excel might have added
    if 'E' in phone_str or 'e' in phone_str:
        try:
            # Convert scientific notation to regular number
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

def import_account_holders(csv_filepath):
    """
    Import account holders from CSV file
    
    Args:
        csv_filepath: Path to the CSV file containing account holder data
    """
    try:
        # Use ISO-8859-1 encoding as the file uses this encoding
        with open(csv_filepath, 'r', encoding='ISO-8859-1') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Track stats
            imported_count = 0
            skipped_count = 0
            error_count = 0
            
            for row in reader:
                try:
                    # Check if account holder already exists
                    existing = AccountHolder.query.filter_by(username=row['username']).first()
                    if existing:
                        logger.info(f"Account holder with username {row['username']} already exists. Skipping.")
                        skipped_count += 1
                        continue
                    
                    # Create account holder
                    account_holder = AccountHolder(
                        name=row['name'],
                        username=row['username'],
                        email=row['email'],
                        created_at=datetime.strptime(row['creationdate'], '%m/%d/%Y %H:%M') if row['creationdate'] else datetime.utcnow(),
                        broker=row['broker']
                    )
                    db.session.add(account_holder)
                    
                    # Need to flush to get the ID for relationships
                    db.session.flush()
                    
                    # Create address
                    if row.get('address.line1'):
                        address = Address(
                            name=row.get('address.name', 'Primary Address'),
                            line1=row.get('address.line1'),
                            line2=row.get('address.line2'),
                            pobox=row.get('address.pobox'),
                            neighborhood=row.get('address.neighborhood'),
                            city=row.get('address.city'),
                            region=row.get('address.region'),
                            zip=row.get('address.zip'),
                            country=row.get('address.country'),
                            street=row.get('address.street'),
                            building_number=row.get('address.buildingnumber'),
                            complement=row.get('address.complement'),
                            account_holder_id=account_holder.id
                        )
                        db.session.add(address)
                    
                    # Create mobile phone
                    if row.get('mobile.number'):
                        mobile = PhoneNumber(
                            name=row.get('mobile.name', 'Mobile'),
                            number=parse_phone_number(row.get('mobile.number')),
                            is_primary=True,
                            is_mobile=True,
                            account_holder_id=account_holder.id
                        )
                        db.session.add(mobile)
                    
                    # Create landline phone
                    if row.get('landline.number'):
                        landline = PhoneNumber(
                            name=row.get('landline.name', 'Landline'),
                            number=parse_phone_number(row.get('landline.number')),
                            is_primary=False,
                            is_mobile=False,
                            account_holder_id=account_holder.id
                        )
                        db.session.add(landline)
                    
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
                            
                        try:
                            # Get the appropriate CurrencyType enum value
                            currency_type = CurrencyType[currency_enum_value]
                            
                            # Parse the balance value
                            balance = parse_currency_value(row[column_name])
                            
                            # Skip if balance is 0
                            if balance == 0:
                                continue
                                
                            # Create a random but consistent account number based on username and currency
                            account_number = f"{currency_enum_value}-{row['username']}"
                            
                            # Create the bank account
                            bank_account = BankAccount(
                                account_number=account_number,
                                account_name=f"{row['name']} {currency_enum_value} Account",
                                account_type=AccountType.CHECKING,
                                currency=currency_type,
                                balance=balance,
                                available_balance=balance,
                                status=AccountStatus.ACTIVE,
                                account_holder_id=account_holder.id
                            )
                            db.session.add(bank_account)
                        except KeyError:
                            logger.warning(f"Currency {currency_enum_value} not found in enum. Skipping this account.")
                    
                    # Commit the transaction
                    db.session.commit()
                    logger.info(f"Successfully imported account holder: {row['name']} ({row['username']})")
                    imported_count += 1
                    
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error importing account holder {row.get('name', 'unknown')}: {str(e)}")
                    error_count += 1
            
            # Log summary
            logger.info(f"Import summary: {imported_count} imported, {skipped_count} skipped, {error_count} errors")
            return imported_count, skipped_count, error_count
            
    except Exception as e:
        logger.error(f"Error opening or processing CSV file: {str(e)}")
        return 0, 0, 1

def main():
    """Main function to run the import"""
    if len(sys.argv) != 2:
        logger.error("Usage: python import_account_holders.py <csv_file_path>")
        sys.exit(1)
        
    csv_file_path = sys.argv[1]
    
    if not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
        sys.exit(1)
    
    app = create_app()
    with app.app_context():
        try:
            # Check if database tables exist
            account_holder_table_exists = db.engine.dialect.has_table(db.engine.connect(), 'account_holder')
            if not account_holder_table_exists:
                logger.error("Database tables do not exist. Creating tables...")
                db.create_all()
                logger.info("Database tables created.")
            
            # Run the import
            imported, skipped, errors = import_account_holders(csv_file_path)
            
            if errors > 0:
                logger.warning(f"Import completed with {errors} errors. Please check the logs.")
                sys.exit(1)
            else:
                logger.info(f"Import completed successfully: {imported} imported, {skipped} skipped.")
                sys.exit(0)
                
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    main()