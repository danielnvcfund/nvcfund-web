#!/usr/bin/env python3
"""
Update the database to include all currency exchange rates
This script runs the migration using SQLAlchemy ORM
"""

import logging
import enum
import time
from sqlalchemy import Column, Integer, Float, Enum, String, DateTime, Boolean, text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app import app, db
from account_holder_models import CurrencyType, CurrencyExchangeRate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_exchange_rate(from_currency_str, to_currency_str, rate, source="system_migration"):
    """Add exchange rate directly to the database using SQLAlchemy ORM"""
    try:
        # Convert string currency codes to enum members
        from_currency = getattr(CurrencyType, from_currency_str)
        to_currency = getattr(CurrencyType, to_currency_str)
        
        # Check if rate already exists
        existing_rate = db.session.query(CurrencyExchangeRate).filter_by(
            from_currency=from_currency,
            to_currency=to_currency
        ).first()
        
        if existing_rate:
            # Update existing rate
            existing_rate.rate = rate
            existing_rate.inverse_rate = 1.0 / rate if rate != 0 else 0
            existing_rate.last_updated = datetime.utcnow()
            existing_rate.source = source
            db.session.commit()
            logger.info(f"Updated exchange rate: 1 {from_currency_str} = {rate} {to_currency_str}")
        else:
            # Create new rate
            new_rate = CurrencyExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                inverse_rate=1.0 / rate if rate != 0 else 0,
                source=source,
                last_updated=datetime.utcnow(),
                is_active=True
            )
            db.session.add(new_rate)
            db.session.commit()
            logger.info(f"Added new exchange rate: 1 {from_currency_str} = {rate} {to_currency_str}")
        
        # Also add the inverse rate
        inverse_rate = 1.0 / rate if rate != 0 else 0
        
        # Check if inverse rate already exists
        existing_inverse = db.session.query(CurrencyExchangeRate).filter_by(
            from_currency=to_currency,
            to_currency=from_currency
        ).first()
        
        if existing_inverse:
            # Update existing inverse rate
            existing_inverse.rate = inverse_rate
            existing_inverse.inverse_rate = rate
            existing_inverse.last_updated = datetime.utcnow()
            existing_inverse.source = source
            db.session.commit()
        else:
            # Create new inverse rate
            new_inverse = CurrencyExchangeRate(
                from_currency=to_currency,
                to_currency=from_currency,
                rate=inverse_rate,
                inverse_rate=rate,
                source=source,
                last_updated=datetime.utcnow(),
                is_active=True
            )
            db.session.add(new_inverse)
            db.session.commit()
        
        return True
    except Exception as e:
        logger.error(f"Error adding exchange rate {from_currency_str} to {to_currency_str}: {str(e)}")
        db.session.rollback()
        return False

def migrate_currencies():
    """Run the migration to add currency exchange rates"""
    logger.info("Starting currency exchange rates migration...")
    
    with app.app_context():
        try:
            # Update PostgreSQL enum type
            db.session.execute(text("BEGIN;"))
            
            # Get current enum values
            result = db.session.execute(text("""
                SELECT enumlabel
                FROM pg_enum
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
                WHERE pg_type.typname = 'currencytype'
                ORDER BY enumsortorder;
            """))
            
            current_enum_values = [row[0] for row in result]
            logger.info(f"Current enum values: {current_enum_values}")
            
            # Get all values from CurrencyType enum
            enum_values = [currency.value for currency in CurrencyType]
            logger.info(f"Required enum values: {enum_values}")
            
            # Find missing values
            missing_values = [value for value in enum_values if value not in current_enum_values]
            logger.info(f"Missing enum values: {missing_values}")
            
            if missing_values:
                # Create temporary tables
                db.session.execute(text("""
                    CREATE TABLE currency_exchange_rate_backup AS 
                    SELECT * FROM currency_exchange_rate;
                """))
                
                # Drop constraints
                db.session.execute(text("""
                    ALTER TABLE currency_exchange_rate 
                    DROP CONSTRAINT IF EXISTS currency_exchange_rate_from_currency_fkey,
                    DROP CONSTRAINT IF EXISTS currency_exchange_rate_to_currency_fkey;
                """))
                
                # Drop and recreate the enum type
                db.session.execute(text("""
                    DROP TABLE currency_exchange_rate;
                """))
                
                db.session.execute(text("""
                    DROP TYPE IF EXISTS currencytype CASCADE;
                """))
                
                # Create new enum with all values
                enum_values_sql = ", ".join([f"'{value}'" for value in enum_values])
                db.session.execute(text(f"""
                    CREATE TYPE currencytype AS ENUM ({enum_values_sql});
                """))
                
                # Recreate the currency_exchange_rate table
                db.session.execute(text("""
                    CREATE TABLE currency_exchange_rate (
                        id SERIAL PRIMARY KEY,
                        from_currency currencytype NOT NULL,
                        to_currency currencytype NOT NULL,
                        rate FLOAT NOT NULL,
                        inverse_rate FLOAT,
                        last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
                        source VARCHAR(100),
                        is_active BOOLEAN DEFAULT true
                    );
                """))
                
                # Migrate data that can be migrated (for existing enum values)
                logger.info("Migrating existing exchange rate data...")
                db.session.execute(text("""
                    INSERT INTO currency_exchange_rate (
                        id, from_currency, to_currency, rate, inverse_rate, 
                        last_updated, source, is_active
                    )
                    SELECT 
                        id, from_currency::text::currencytype, to_currency::text::currencytype, 
                        rate, inverse_rate, last_updated, source, is_active
                    FROM currency_exchange_rate_backup
                    WHERE from_currency::text IN ({}) AND to_currency::text IN ({});
                """.format(
                    ", ".join([f"'{value}'" for value in current_enum_values]),
                    ", ".join([f"'{value}'" for value in current_enum_values])
                )))
                
                # Drop backup table
                db.session.execute(text("""
                    DROP TABLE currency_exchange_rate_backup;
                """))
                
                db.session.execute(text("COMMIT;"))
                logger.info("Database schema updated successfully with new currency types")
            else:
                db.session.execute(text("COMMIT;"))
                logger.info("No schema changes needed - all currency types already exist")
            
            # Initialize essential exchange rates
            logger.info("Initializing essential exchange rates...")
            
            # NVCT pegged to USD 1:1
            add_exchange_rate("NVCT", "USD", 1.0, "system_migration")
            
            # Major currencies
            add_exchange_rate("USD", "EUR", 0.93, "system_migration")
            add_exchange_rate("USD", "GBP", 0.79, "system_migration")
            
            # Partner currencies
            add_exchange_rate("NVCT", "AFD1", 339.40 / 1000, "system_migration")  # 1 AFD1 = 10% of gold price
            add_exchange_rate("NVCT", "SFN", 1.0, "system_migration")  # 1:1 ratio as specified
            add_exchange_rate("NVCT", "AKLUMI", 0.307, "system_migration")  # 1 AKLUMI = $3.25 USD
            
            # Sample cryptocurrencies
            add_exchange_rate("USD", "BTC", 1/62000.0, "system_migration")  # Bitcoin price in USD
            add_exchange_rate("USD", "ETH", 1/3000.0, "system_migration")  # Ethereum price in USD
            
            logger.info("Essential exchange rates initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during migration: {str(e)}")
            db.session.execute(text("ROLLBACK;"))
            return False

if __name__ == "__main__":
    migrate_currencies()