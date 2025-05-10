#!/usr/bin/env python3
"""
Generate SQL statements to update the database schema for new currencies
"""

import logging
from account_holder_models import CurrencyType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_sql_statements():
    """Generate SQL statements to update the currency types enum"""
    try:
        # Get all values from CurrencyType enum
        enum_values = [currency.value for currency in CurrencyType]
        logger.info(f"Found {len(enum_values)} currency values")
        
        # Generate enum values string
        enum_values_sql = ", ".join([f"'{value}'" for value in enum_values])
        
        # SQL statements
        sql_statements = [
            "-- Backup existing data",
            "CREATE TABLE currency_exchange_rate_backup AS SELECT * FROM currency_exchange_rate;",
            "",
            "-- Drop constraints and table",
            "ALTER TABLE currency_exchange_rate DROP CONSTRAINT IF EXISTS currency_exchange_rate_from_currency_fkey;",
            "ALTER TABLE currency_exchange_rate DROP CONSTRAINT IF EXISTS currency_exchange_rate_to_currency_fkey;",
            "DROP TABLE currency_exchange_rate;",
            "",
            "-- Drop and recreate the enum type",
            "DROP TYPE IF EXISTS currencytype CASCADE;",
            "",
            f"-- Create new enum with all {len(enum_values)} values",
            f"CREATE TYPE currencytype AS ENUM ({enum_values_sql});",
            "",
            "-- Recreate the currency_exchange_rate table",
            """CREATE TABLE currency_exchange_rate (
                id SERIAL PRIMARY KEY,
                from_currency currencytype NOT NULL,
                to_currency currencytype NOT NULL,
                rate FLOAT NOT NULL,
                inverse_rate FLOAT,
                last_updated TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
                source VARCHAR(100),
                is_active BOOLEAN DEFAULT true
            );""",
            "",
            "-- Insert basic exchange rates",
            "-- NVCT to USD (1:1 peg)",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('NVCT', 'USD', 1.0, 1.0, 'system_migration', true);",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('USD', 'NVCT', 1.0, 1.0, 'system_migration', true);",
            "",
            "-- Major currencies",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('USD', 'EUR', 0.93, 1.075, 'system_migration', true);",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('EUR', 'USD', 1.075, 0.93, 'system_migration', true);",
            "",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('USD', 'GBP', 0.79, 1.266, 'system_migration', true);",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('GBP', 'USD', 1.266, 0.79, 'system_migration', true);",
            "",
            "-- Partner currencies",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('NVCT', 'AFD1', 0.3394, 2.946, 'system_migration', true);",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('AFD1', 'NVCT', 2.946, 0.3394, 'system_migration', true);",
            "",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('NVCT', 'SFN', 1.0, 1.0, 'system_migration', true);",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('SFN', 'NVCT', 1.0, 1.0, 'system_migration', true);",
            "",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('NVCT', 'AKLUMI', 0.307, 3.25, 'system_migration', true);",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('AKLUMI', 'NVCT', 3.25, 0.307, 'system_migration', true);",
            "",
            "-- Cryptocurrencies",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('USD', 'BTC', 0.0000161, 62000.0, 'system_migration', true);",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('BTC', 'USD', 62000.0, 0.0000161, 'system_migration', true);",
            "",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('USD', 'ETH', 0.000333, 3000.0, 'system_migration', true);",
            "INSERT INTO currency_exchange_rate (from_currency, to_currency, rate, inverse_rate, source, is_active) VALUES ('ETH', 'USD', 3000.0, 0.000333, 'system_migration', true);",
        ]
        
        return "\n".join(sql_statements)
    except Exception as e:
        logger.error(f"Error generating SQL statements: {str(e)}")
        return ""

if __name__ == "__main__":
    sql = generate_sql_statements()
    print(sql)