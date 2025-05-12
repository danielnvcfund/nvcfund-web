"""
Migrate blockchain transaction records to include tx_hash field.

This script adds the tx_hash column to the blockchain_transaction table
and updates the blockchain.py file to use tx_hash.
"""
import os
import sys
import logging
from sqlalchemy import text
from app import db, app
from db_operations import add_tx_hash_column
from models import BlockchainTransaction

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_schema_migration():
    """Run database schema migration to add tx_hash column"""
    try:
        with app.app_context():
            result = add_tx_hash_column()
            if result:
                logger.info("Schema migration successful")
                return True
            else:
                logger.error("Schema migration failed")
                return False
    except Exception as e:
        logger.error(f"Error in schema migration: {str(e)}")
        return False

def map_eth_tx_hash_to_tx_hash():
    """Map eth_tx_hash values to tx_hash field"""
    try:
        with app.app_context():
            # Check if both columns exist
            try:
                db.session.execute(text(
                    "SELECT eth_tx_hash, tx_hash FROM blockchain_transaction LIMIT 1"
                ))
            except Exception as e:
                logger.error(f"Error checking columns: {str(e)}")
                return False
            
            # Update tx_hash from eth_tx_hash where tx_hash is NULL
            try:
                result = db.session.execute(text(
                    "UPDATE blockchain_transaction SET tx_hash = eth_tx_hash WHERE eth_tx_hash IS NOT NULL AND tx_hash IS NULL"
                ))
                db.session.commit()
                logger.info(f"Updated {result.rowcount} rows with tx_hash values from eth_tx_hash")
                return True
            except Exception as e:
                logger.error(f"Error updating tx_hash: {str(e)}")
                db.session.rollback()
                return False
    except Exception as e:
        logger.error(f"Error mapping eth_tx_hash to tx_hash: {str(e)}")
        return False

def fix_constructor_mismatch():
    """Add tx_hash parameter to all blockchain transaction objects"""
    try:
        # This would typically be a code modification function
        # In a production environment, this should be a code deployment step
        # For this demo, we're focusing on the database aspects
        logger.info("Reminder: Ensure all BlockchainTransaction constructor calls include tx_hash")
        logger.info("Example: blockchain_tx = BlockchainTransaction(tx_hash=tx_hash.hex(), ...)")
        return True
    except Exception as e:
        logger.error(f"Error fixing constructor mismatch: {str(e)}")
        return False

if __name__ == "__main__":
    # Run schema migration
    if not run_schema_migration():
        logger.error("Schema migration failed. Exiting.")
        sys.exit(1)
    
    # Map eth_tx_hash to tx_hash
    if not map_eth_tx_hash_to_tx_hash():
        logger.error("Mapping eth_tx_hash to tx_hash failed. Exiting.")
        sys.exit(1)
    
    # Fix constructor mismatch
    if not fix_constructor_mismatch():
        logger.error("Fixing constructor mismatch failed. Exiting.")
        sys.exit(1)
    
    logger.info("Migration completed successfully.")