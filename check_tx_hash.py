"""
Check if the blockchain_transaction table has the tx_hash column and verify data.
"""
import logging
from app import app, db
from models import BlockchainTransaction
from sqlalchemy import text, inspect

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.error(f"Error checking if column {column_name} exists in table {table_name}: {str(e)}")
        return False

def check_tx_hash():
    """Check if tx_hash column exists and has data"""
    with app.app_context():
        # First check if the column exists
        if not check_column_exists('blockchain_transaction', 'tx_hash'):
            logger.error("tx_hash column does not exist in blockchain_transaction table")
            return False
        
        logger.info("✓ tx_hash column exists in blockchain_transaction table")
        
        # Try to get some blockchain transaction data
        try:
            transactions = BlockchainTransaction.query.limit(5).all()
            logger.info(f"Found {len(transactions)} transactions in database")
            
            for tx in transactions:
                logger.info(f"Transaction {tx.id}: tx_hash = {tx.tx_hash}")
            
            # Count transactions with and without tx_hash
            try:
                result = db.session.execute(text(
                    "SELECT COUNT(*) as total, "
                    "SUM(CASE WHEN tx_hash IS NULL THEN 1 ELSE 0 END) as null_count, "
                    "SUM(CASE WHEN tx_hash IS NOT NULL THEN 1 ELSE 0 END) as filled_count "
                    "FROM blockchain_transaction"
                ))
                row = result.fetchone()
                
                if row:
                    total, null_count, filled_count = row
                    logger.info(f"Total transactions: {total}")
                    logger.info(f"Transactions with tx_hash: {filled_count}")
                    logger.info(f"Transactions without tx_hash: {null_count}")
                    
                    if null_count > 0:
                        logger.warning(f"{null_count} transactions don't have tx_hash values - these may need to be migrated")
                
            except Exception as e:
                logger.error(f"Error counting transactions: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error retrieving transactions: {str(e)}")
            return False

if __name__ == "__main__":
    check_tx_hash()