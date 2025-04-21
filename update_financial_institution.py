"""
Database migration script to add metadata_json column to FinancialInstitution table
"""
import os
import sys
from datetime import datetime
from flask import Flask
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
    sys.exit(1)

def run_migration():
    """Add metadata_json column to financial_institution table"""
    logger.info("Starting migration: adding metadata_json column to financial_institution table")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Check if the column already exists
            check_column_sql = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'financial_institution'
                AND column_name = 'metadata_json'
            """)
            
            result = connection.execute(check_column_sql).fetchone()
            
            if result:
                logger.info("Column 'metadata_json' already exists in financial_institution table")
                return
            
            # Add the metadata_json column
            add_column_sql = text("""
                ALTER TABLE financial_institution
                ADD COLUMN metadata_json TEXT
            """)
            
            connection.execute(add_column_sql)
            connection.commit()
            
            logger.info("Column 'metadata_json' added to financial_institution table successfully")
            
            # Add default BIC code to NVC Global for SWIFT capability
            update_institutions_sql = text("""
                UPDATE financial_institution
                SET metadata_json = '{"swift": {"bic": "NVCGGBXXXX"}}'
                WHERE name = 'NVC Global'
            """)
            
            connection.execute(update_institutions_sql)
            connection.commit()
            
            logger.info("Default SWIFT BIC codes added to financial institutions")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
    logger.info("Migration completed successfully")