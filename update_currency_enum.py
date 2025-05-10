#!/usr/bin/env python3
"""
Update Currency Enum in Database
This script updates the PostgreSQL database to accept the new African currency values
"""

import logging
from app import app, db
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_currency_enum():
    """Update the currency enum in the database"""
    logger.info("Updating currency enum in database to include African currencies...")
    
    with app.app_context():
        try:
            # Get all existing enum values
            result = db.session.execute(text("""
                SELECT enum_range(NULL::currencytype)
            """))
            current_values = result.fetchone()[0]
            logger.info(f"Current currency enum values: {current_values}")
            
            # Create temporary type with all values
            db.session.execute(text("""
                -- Create a new enum type with all the necessary values
                CREATE TYPE currencytype_new AS ENUM (
                    'USD', 'EUR', 'GBP', 'BTC', 'ETH', 'NVCT', 'SPU', 'TU', 'ZCASH', 'NGN', 'AFD1', 'SFN', 'AKLUMI',
                    'DZD', 'EGP', 'LYD', 'MAD', 'SDG', 'TND', 
                    'GHS', 'XOF', 'GMD', 'GNF', 'LRD', 'SLL', 'SLE', 'CVE',
                    'XAF', 'CDF', 'STN',
                    'KES', 'ETB', 'UGX', 'TZS', 'RWF', 'BIF', 'DJF', 'ERN', 'SSP', 'SOS',
                    'ZAR', 'LSL', 'NAD', 'SZL', 'BWP', 'ZMW', 'MWK', 'ZWL', 'MZN', 'MGA', 'SCR', 'MUR', 'AOA'
                );
            """))
            logger.info("Created new currency enum type")
            
            # Create temp table to help with migration
            db.session.execute(text("""
                -- Create temporary tables for the affected tables
                CREATE TEMP TABLE temp_currency_exchange_rate AS 
                SELECT * FROM currency_exchange_rate;
                
                -- Drop constraints and indexes that reference the enum
                ALTER TABLE currency_exchange_rate DROP CONSTRAINT currency_exchange_rate_pkey;
            """))
            logger.info("Created temporary tables and dropped constraints")
            
            # Alter the column types
            db.session.execute(text("""
                -- Drop the original tables
                DROP TABLE currency_exchange_rate;
                
                -- Recreate tables with the new enum type
                CREATE TABLE currency_exchange_rate (
                    id INTEGER PRIMARY KEY,
                    from_currency currencytype_new NOT NULL,
                    to_currency currencytype_new NOT NULL,
                    rate DOUBLE PRECISION NOT NULL,
                    inverse_rate DOUBLE PRECISION,
                    last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
                    source VARCHAR(100),
                    is_active BOOLEAN DEFAULT true
                );
                
                -- Reinsert the data with a cast to the new enum type
                INSERT INTO currency_exchange_rate 
                SELECT id, 
                       from_currency::text::currencytype_new, 
                       to_currency::text::currencytype_new, 
                       rate, 
                       inverse_rate, 
                       last_updated, 
                       source, 
                       is_active 
                FROM temp_currency_exchange_rate;
            """))
            logger.info("Recreated tables with new enum type")
            
            # Drop the old type and rename the new one
            db.session.execute(text("""
                -- Drop the old enum type and rename the new one
                DROP TYPE currencytype CASCADE;
                ALTER TYPE currencytype_new RENAME TO currencytype;
            """))
            logger.info("Renamed enum type")
            
            # Commit all changes
            db.session.commit()
            logger.info("Successfully updated currency enum in database")
            
            # Verify the update
            result = db.session.execute(text("""
                SELECT enum_range(NULL::currencytype)
            """))
            new_values = result.fetchone()[0]
            logger.info(f"New currency enum values: {new_values}")
            
            african_currencies = ['NGN', 'KES', 'ZAR', 'EGP', 'GHS', 'XOF', 'XAF']
            for currency in african_currencies:
                if currency in new_values:
                    logger.info(f"√ {currency} is now available in the enum")
                else:
                    logger.warning(f"× {currency} is not in the enum")
            
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating currency enum: {str(e)}")
            return False

if __name__ == "__main__":
    update_currency_enum()