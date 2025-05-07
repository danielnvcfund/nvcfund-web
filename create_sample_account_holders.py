#!/usr/bin/env python
"""
Create Sample Account Holders
This script creates a few sample account holders directly in the database.
"""

import logging
from datetime import datetime
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

def create_sample_account_holders():
    """Create a few sample account holders"""
    
    # Sample account holders data
    sample_data = [
        {
            "name": "John Smith",
            "username": "johnsmith",
            "email": "john.smith@example.com",
            "address": {
                "line1": "123 Main Street",
                "city": "New York",
                "region": "NY",
                "zip": "10001",
                "country": "US"
            },
            "phone": "+12125551234",
            "accounts": [
                {"currency": CurrencyType.USD, "balance": 50000.00},
                {"currency": CurrencyType.EUR, "balance": 10000.00},
                {"currency": CurrencyType.NVCT, "balance": 25000.00}
            ]
        },
        {
            "name": "Jane Doe",
            "username": "janedoe",
            "email": "jane.doe@example.com",
            "address": {
                "line1": "456 Park Avenue",
                "city": "Los Angeles",
                "region": "CA",
                "zip": "90001",
                "country": "US"
            },
            "phone": "+13105557890",
            "accounts": [
                {"currency": CurrencyType.USD, "balance": 75000.00},
                {"currency": CurrencyType.GBP, "balance": 15000.00},
                {"currency": CurrencyType.BTC, "balance": 2.5}
            ]
        },
        {
            "name": "Global Enterprises Ltd.",
            "username": "global_ent",
            "email": "contact@globalent.example.com",
            "is_business": True,
            "business_name": "Global Enterprises Ltd.",
            "business_type": "Corporation",
            "address": {
                "line1": "1 Corporate Plaza",
                "city": "London",
                "zip": "EC1A 1BB",
                "country": "GB"
            },
            "phone": "+442071234567",
            "accounts": [
                {"currency": CurrencyType.USD, "balance": 1000000.00},
                {"currency": CurrencyType.EUR, "balance": 750000.00},
                {"currency": CurrencyType.GBP, "balance": 500000.00},
                {"currency": CurrencyType.NVCT, "balance": 250000.00}
            ]
        },
        {
            "name": "Maria Rodriguez",
            "username": "mrodriguez",
            "email": "maria.rodriguez@example.com",
            "address": {
                "line1": "789 Elm Street",
                "city": "Miami",
                "region": "FL",
                "zip": "33101",
                "country": "US"
            },
            "phone": "+13055559876",
            "accounts": [
                {"currency": CurrencyType.USD, "balance": 25000.00},
                {"currency": CurrencyType.NVCT, "balance": 10000.00}
            ]
        },
        {
            "name": "Tech Innovations Inc.",
            "username": "techinnovations",
            "email": "info@techinnovations.example.com",
            "is_business": True,
            "business_name": "Tech Innovations Inc.",
            "business_type": "Technology",
            "address": {
                "line1": "100 Silicon Valley Blvd",
                "city": "San Francisco",
                "region": "CA",
                "zip": "94105",
                "country": "US"
            },
            "phone": "+14155551212",
            "accounts": [
                {"currency": CurrencyType.USD, "balance": 2000000.00},
                {"currency": CurrencyType.BTC, "balance": 15.0},
                {"currency": CurrencyType.ETH, "balance": 150.0},
                {"currency": CurrencyType.NVCT, "balance": 500000.00}
            ]
        }
    ]
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    for data in sample_data:
        try:
            # Check if account holder already exists
            existing = AccountHolder.query.filter_by(username=data['username']).first()
            if existing:
                logger.info(f"Account holder with username {data['username']} already exists. Skipping.")
                skipped_count += 1
                continue
            
            # Create account holder
            account_holder = AccountHolder(
                name=data['name'],
                username=data['username'],
                email=data['email'],
                created_at=datetime.utcnow(),
                is_business=data.get('is_business', False),
                business_name=data.get('business_name', None),
                business_type=data.get('business_type', None),
                kyc_verified=True,
                aml_verified=True
            )
            db.session.add(account_holder)
            
            # Need to flush to get the ID for relationships
            db.session.flush()
            
            # Create address
            if 'address' in data:
                address_data = data['address']
                address = Address(
                    name="Primary Address",
                    line1=address_data.get('line1'),
                    city=address_data.get('city'),
                    region=address_data.get('region'),
                    zip=address_data.get('zip'),
                    country=address_data.get('country'),
                    account_holder_id=account_holder.id
                )
                db.session.add(address)
            
            # Create phone
            if 'phone' in data:
                phone = PhoneNumber(
                    name="Primary Phone",
                    number=data['phone'],
                    is_primary=True,
                    is_mobile=True,
                    account_holder_id=account_holder.id
                )
                db.session.add(phone)
            
            # Create bank accounts
            for account_data in data.get('accounts', []):
                currency = account_data['currency']
                balance = account_data['balance']
                
                account_number = f"{currency.name}-{data['username']}"
                
                bank_account = BankAccount(
                    account_number=account_number,
                    account_name=f"{data['name']} {currency.name} Account",
                    account_type=AccountType.CHECKING,
                    currency=currency,
                    balance=balance,
                    available_balance=balance,
                    status=AccountStatus.ACTIVE,
                    account_holder_id=account_holder.id
                )
                db.session.add(bank_account)
            
            # Commit the transaction
            db.session.commit()
            logger.info(f"Successfully created account holder: {data['name']} ({data['username']})")
            imported_count += 1
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating account holder {data.get('name', 'unknown')}: {str(e)}")
            error_count += 1
    
    # Log summary
    logger.info(f"Creation summary: {imported_count} created, {skipped_count} skipped, {error_count} errors")
    return imported_count, skipped_count, error_count

def main():
    """Main function"""
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Check if database tables exist
            account_holder_table_exists = db.engine.dialect.has_table(db.engine.connect(), 'account_holder')
            if not account_holder_table_exists:
                logger.error("Database tables do not exist. Creating tables...")
                db.create_all()
                logger.info("Database tables created.")
            
            # Create sample account holders
            imported, skipped, errors = create_sample_account_holders()
            
            if errors > 0:
                logger.warning(f"Creation completed with {errors} errors. Please check the logs.")
            else:
                logger.info(f"Creation completed successfully: {imported} created, {skipped} skipped.")
                
        except Exception as e:
            logger.error(f"Error creating sample account holders: {str(e)}")

if __name__ == "__main__":
    main()