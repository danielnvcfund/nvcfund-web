"""
Direct Database Optimization Script for NVC Banking Platform

This script improves database performance by adding missing indices
using a direct database connection instead of the ORM.
"""

import os
import sys
import time
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DBOptimizer")

# Critical indices to add (focusing on most important for performance)
CRITICAL_INDICES = [
    # Transaction-related indices (highest priority)
    {"table": "blockchain_transaction", "column": "transaction_id"},
    {"table": "blockchain_transaction", "column": "user_id"},
    {"table": "transaction", "column": "user_id"},
    {"table": "treasury_transaction", "column": "reference_number"},
    {"table": "treasury_transaction", "column": "from_account_id"},
    {"table": "treasury_transaction", "column": "to_account_id"},
    
    # Account-related indices
    {"table": "account_holder", "column": "user_id"},
    {"table": "financial_institution", "column": "account_number"},
    {"table": "treasury_account", "column": "account_number"},
    {"table": "trust_fund", "column": "account_number"},
    
    # Exchange-related indices
    {"table": "currency_exchange_transaction", "column": "from_account_id"},
    {"table": "currency_exchange_transaction", "column": "to_account_id"},
]

def get_db_connection():
    """Connect to the database using environment variables"""
    db_url = os.environ.get("DATABASE_URL")
    
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
        
    try:
        conn = psycopg2.connect(db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        logger.info("Connected to database successfully")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        sys.exit(1)

def create_index(conn, table_name, column_name):
    """Create an index on the specified table and column"""
    # Create a unique index name
    index_name = f"idx_{table_name}_{column_name}"
    
    # Check if index already exists
    check_query = f"""
        SELECT EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE indexname = '{index_name}'
        );
    """
    
    try:
        with conn.cursor() as cursor:
            # Check if index exists
            cursor.execute(check_query)
            exists = cursor.fetchone()[0]
            
            if exists:
                logger.info(f"Index {index_name} already exists - skipping")
                return True
                
            # Index doesn't exist, create it
            create_query = f"""
                CREATE INDEX {index_name}
                ON {table_name} ({column_name});
            """
            
            start_time = time.time()
            cursor.execute(create_query)
            end_time = time.time()
            
            logger.info(f"Created index {index_name} in {end_time - start_time:.2f} seconds")
            return True
            
    except Exception as e:
        logger.error(f"Error creating index {index_name}: {str(e)}")
        return False

def check_table_exists(conn, table_name):
    """Check if a table exists in the database"""
    query = f"""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = '{table_name}'
        );
    """
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Error checking if table {table_name} exists: {str(e)}")
        return False

def optimize_database():
    """Apply all database optimizations"""
    logger.info("Starting database optimization")
    
    # Connect to the database
    conn = get_db_connection()
    
    # Track statistics
    stats = {
        "indices_added": 0,
        "indices_skipped": 0,
        "indices_failed": 0,
        "total_time": 0
    }
    
    # Add critical indices
    start_time = time.time()
    for index in CRITICAL_INDICES:
        table = index["table"]
        column = index["column"]
        
        # Check if table exists
        if not check_table_exists(conn, table):
            logger.warning(f"Table {table} does not exist - skipping")
            stats["indices_skipped"] += 1
            continue
        
        logger.info(f"Adding index on {table}.{column}")
        success = create_index(conn, table, column)
        
        if success:
            stats["indices_added"] += 1
        else:
            stats["indices_failed"] += 1
            
    # Run ANALYZE to update statistics
    logger.info("Running ANALYZE to update database statistics")
    try:
        with conn.cursor() as cursor:
            cursor.execute("ANALYZE;")
    except Exception as e:
        logger.error(f"Error running ANALYZE: {str(e)}")
    
    # Close database connection
    conn.close()
    
    # Calculate total time
    end_time = time.time()
    stats["total_time"] = end_time - start_time
    
    # Print summary
    logger.info("=" * 60)
    logger.info("DATABASE OPTIMIZATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Indices added: {stats['indices_added']}")
    logger.info(f"Indices skipped: {stats['indices_skipped']}")
    logger.info(f"Indices failed: {stats['indices_failed']}")
    logger.info(f"Total time: {stats['total_time']:.2f} seconds")
    logger.info("=" * 60)
    
    return stats

if __name__ == "__main__":
    optimize_database()