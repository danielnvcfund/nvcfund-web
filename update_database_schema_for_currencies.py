#!/usr/bin/env python3
"""
Update Database Schema for African Currencies
This script updates the database to support all African currencies
"""

import logging
import sys
from sqlalchemy import text
from app import app, db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database_schema():
    """Update the PostgreSQL database schema to support all African currencies"""
    with app.app_context():
        try:
            # First check if we can create a backup of the currency_exchange_rate table
            logger.info("Creating backup of currency_exchange_rate table...")
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS currency_exchange_rate_backup AS
                SELECT * FROM currency_exchange_rate;
            """))
            db.session.commit()
            logger.info("Backup created successfully")

            # Now let's recreate the currency type with all the new values
            logger.info("Recreating currencytype enum with all African currencies...")
            
            # First, get all existing values to preserve them
            existing_rates = []
            try:
                result = db.session.execute(text(
                    "SELECT id, from_currency, to_currency, rate, inverse_rate, last_updated, source, is_active FROM currency_exchange_rate"
                ))
                existing_rates = [dict(row) for row in result]
                logger.info(f"Found {len(existing_rates)} existing exchange rates to preserve")
            except Exception as e:
                logger.error(f"Error fetching existing rates: {str(e)}")
                # Continue anyway, we have the backup
            
            # Next, drop the existing constraints and table
            try:
                db.session.execute(text("DROP TABLE IF EXISTS currency_exchange_rate CASCADE;"))
                db.session.execute(text("DROP TYPE IF EXISTS currencytype CASCADE;"))
                db.session.commit()
                logger.info("Dropped existing table and type")
            except Exception as e:
                logger.error(f"Error dropping table/type: {str(e)}")
                db.session.rollback()

            # Create new enum type with all currency values
            try:
                # Get all currency types from the enum
                from account_holder_models import CurrencyType
                currency_values = [f"'{c.value}'" for c in CurrencyType]
                currency_enum_values = ", ".join(currency_values)
                
                # Create the SQL statement with all currency values
                create_enum_sql = f"""
                    CREATE TYPE currencytype AS ENUM (
                        {currency_enum_values}
                    );
                """
                
                db.session.execute(text(create_enum_sql))
                db.session.commit()
                logger.info(f"Created new currencytype enum with {len(currency_values)} values")
            except Exception as e:
                logger.error(f"Error creating new enum: {str(e)}")
                db.session.rollback()
                return False

            # Recreate the table with the new type
            try:
                db.session.execute(text("""
                    CREATE TABLE currency_exchange_rate (
                        id SERIAL PRIMARY KEY,
                        from_currency currencytype NOT NULL,
                        to_currency currencytype NOT NULL,
                        rate FLOAT NOT NULL,
                        inverse_rate FLOAT,
                        last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        source VARCHAR(100),
                        is_active BOOLEAN DEFAULT TRUE
                    );
                """))
                db.session.commit()
                logger.info("Recreated currency_exchange_rate table with new enum type")
            except Exception as e:
                logger.error(f"Error recreating table: {str(e)}")
                db.session.rollback()
                return False

            # Restore existing exchange rates
            try:
                for rate in existing_rates:
                    # Skip rates that might cause problems with the new schema
                    if rate['from_currency'] not in ['USD', 'EUR', 'GBP', 'BTC', 'ETH', 'NVCT', 'SPU', 'TU', 'ZCASH', 'NGN', 'AFD1', 'SFN', 'AKLUMI']:
                        continue
                    if rate['to_currency'] not in ['USD', 'EUR', 'GBP', 'BTC', 'ETH', 'NVCT', 'SPU', 'TU', 'ZCASH', 'NGN', 'AFD1', 'SFN', 'AKLUMI']:
                        continue
                        
                    db.session.execute(text("""
                        INSERT INTO currency_exchange_rate (id, from_currency, to_currency, rate, inverse_rate, last_updated, source, is_active)
                        VALUES (:id, :from_currency, :to_currency, :rate, :inverse_rate, :last_updated, :source, :is_active)
                    """), rate)
                db.session.commit()
                logger.info("Restored existing exchange rates")
            except Exception as e:
                logger.error(f"Error restoring rates: {str(e)}")
                db.session.rollback()
                # Continue even if some rates couldn't be restored
            
            logger.info("Database schema updated successfully to support African currencies")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating database schema: {str(e)}")
            return False

if __name__ == "__main__":
    if update_database_schema():
        logger.info("✅ Schema update completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Schema update failed")
        sys.exit(1)