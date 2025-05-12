"""
Database operations for schema migrations and other database-related tasks
"""
import logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app import db

logger = logging.getLogger(__name__)

def add_tx_hash_column():
    """
    Add tx_hash column to blockchain_transaction table if it doesn't exist
    Returns True if operation was successful, False otherwise
    """
    connection = None
    transaction = None
    
    try:
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Check if column exists
        check_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='blockchain_transaction' AND column_name='tx_hash'
        """)
        result = connection.execute(check_sql)
        column_exists = result.fetchone() is not None
        
        if column_exists:
            logger.info("tx_hash column already exists in blockchain_transaction table")
            transaction.commit()
            return True
        
        # Add the column
        add_column_sql = text("""
            ALTER TABLE blockchain_transaction 
            ADD COLUMN tx_hash VARCHAR(255)
        """)
        connection.execute(add_column_sql)
        
        # Copy data from eth_tx_hash to tx_hash if eth_tx_hash exists
        check_eth_tx_hash_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='blockchain_transaction' AND column_name='eth_tx_hash'
        """)
        result = connection.execute(check_eth_tx_hash_sql)
        eth_tx_hash_exists = result.fetchone() is not None
        
        if eth_tx_hash_exists:
            copy_data_sql = text("""
                UPDATE blockchain_transaction 
                SET tx_hash = eth_tx_hash 
                WHERE eth_tx_hash IS NOT NULL
            """)
            connection.execute(copy_data_sql)
            logger.info("Copied data from eth_tx_hash to tx_hash")
        
        # Create index on tx_hash for faster lookups
        create_index_sql = text("""
            CREATE INDEX IF NOT EXISTS ix_blockchain_transaction_tx_hash 
            ON blockchain_transaction(tx_hash)
        """)
        connection.execute(create_index_sql)
        
        transaction.commit()
        logger.info("Successfully added tx_hash column to blockchain_transaction table")
        return True
        
    except SQLAlchemyError as e:
        if transaction:
            transaction.rollback()
        logger.error(f"Error adding tx_hash column: {str(e)}")
        return False
        
    finally:
        if connection:
            connection.close()

def check_table_exists(table_name):
    """
    Check if a table exists in the database
    Returns True if table exists, False otherwise
    """
    try:
        sql = text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            )
        """)
        result = db.session.execute(sql)
        return result.scalar()
    except SQLAlchemyError as e:
        logger.error(f"Error checking if table {table_name} exists: {str(e)}")
        return False

def check_column_exists(table_name, column_name):
    """
    Check if a column exists in a table
    Returns True if column exists, False otherwise
    """
    try:
        sql = text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = '{table_name}' AND column_name = '{column_name}'
            )
        """)
        result = db.session.execute(sql)
        return result.scalar()
    except SQLAlchemyError as e:
        logger.error(f"Error checking if column {column_name} exists in table {table_name}: {str(e)}")
        return False

def get_row_count(table_name):
    """
    Get the number of rows in a table
    Returns the row count or 0 if an error occurs
    """
    try:
        sql = text(f"SELECT COUNT(*) FROM {table_name}")
        result = db.session.execute(sql)
        return result.scalar() or 0
    except SQLAlchemyError as e:
        logger.error(f"Error getting row count for table {table_name}: {str(e)}")
        return 0