"""
Database Optimization Script for NVC Banking Platform

This script improves database performance by:
1. Adding missing indices for commonly accessed fields
2. Optimizing query execution with proper indices
3. Improving transaction processing speed
"""

import os
import sys
import time
import logging
from datetime import datetime
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DBOptimizer")

# Import db engine from main application
try:
    from app import db
    logger.info("Successfully imported database connection from app")
except ImportError:
    logger.error("Failed to import database connection - exiting")
    sys.exit(1)

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

def create_index(table_name, column_name):
    """Create an index on the specified table and column"""
    # Create a unique index name
    index_name = f"idx_{table_name}_{column_name}"
    
    # Check if index already exists
    check_query = text(f"""
        SELECT EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE indexname = :index_name
        );
    """)
    
    try:
        with db.engine.connect() as conn:
            result = conn.execute(check_query, {"index_name": index_name})
            exists = result.scalar()
            
            if exists:
                logger.info(f"Index {index_name} already exists - skipping")
                return True
                
            # Index doesn't exist, create it
            create_query = text(f"""
                CREATE INDEX {index_name}
                ON {table_name} ({column_name});
            """)
            
            start_time = time.time()
            conn.execute(create_query)
            conn.commit()
            end_time = time.time()
            
            logger.info(f"Created index {index_name} in {end_time - start_time:.2f} seconds")
            return True
            
    except Exception as e:
        logger.error(f"Error creating index {index_name}: {str(e)}")
        return False

def optimize_database():
    """Apply all database optimizations"""
    logger.info("Starting database optimization")
    
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
        
        logger.info(f"Adding index on {table}.{column}")
        success = create_index(table, column)
        
        if success:
            stats["indices_added"] += 1
        else:
            stats["indices_failed"] += 1
            
    # Run ANALYZE to update statistics
    logger.info("Running ANALYZE to update database statistics")
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ANALYZE;"))
            conn.commit()
    except Exception as e:
        logger.error(f"Error running ANALYZE: {str(e)}")
    
    # Calculate total time
    end_time = time.time()
    stats["total_time"] = end_time - start_time
    
    # Print summary
    logger.info("=" * 60)
    logger.info("DATABASE OPTIMIZATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Indices added: {stats['indices_added']}")
    logger.info(f"Indices failed: {stats['indices_failed']}")
    logger.info(f"Total time: {stats['total_time']:.2f} seconds")
    logger.info("=" * 60)
    
    return stats

if __name__ == "__main__":
    optimize_database()