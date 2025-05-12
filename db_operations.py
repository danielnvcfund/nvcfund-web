"""
Database operations for blockchain transaction management
Used to fix and standardize database schema for blockchain tracking
"""
from sqlalchemy import text
from app import db, app
import logging

logger = logging.getLogger(__name__)

def add_tx_hash_column():
    """Add tx_hash column to blockchain_transaction table"""
    
    try:
        with app.app_context():
            # Check if column exists
            try:
                db.session.execute(text(
                    "SELECT tx_hash FROM blockchain_transaction LIMIT 1"
                ))
                logger.info("tx_hash column already exists in blockchain_transaction table")
                return True
            except Exception:
                logger.info("tx_hash column doesn't exist yet, will add it")
            
            # Add column
            db.session.execute(text(
                "ALTER TABLE blockchain_transaction ADD COLUMN tx_hash VARCHAR(66) UNIQUE;"
            ))
            db.session.commit()
            logger.info("Added tx_hash column to blockchain_transaction table")
            
            # Copy eth_tx_hash values to tx_hash if eth_tx_hash exists
            try:
                db.session.execute(text(
                    "SELECT eth_tx_hash FROM blockchain_transaction LIMIT 1"
                ))
                db.session.execute(text(
                    "UPDATE blockchain_transaction SET tx_hash = eth_tx_hash WHERE eth_tx_hash IS NOT NULL AND tx_hash IS NULL;"
                ))
                db.session.commit()
                logger.info("Copied eth_tx_hash values to tx_hash column")
            except Exception as e:
                logger.warning(f"Could not copy eth_tx_hash values (might not exist): {str(e)}")
            
            return True
    except Exception as e:
        logger.error(f"Error adding tx_hash column: {str(e)}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with app.app_context():
        add_tx_hash_column()