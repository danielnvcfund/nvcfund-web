"""
Simple script to add the name column to the treasury_loan table
"""
import os
import logging
from sqlalchemy import create_engine, text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect directly to database
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    logger.error("DATABASE_URL environment variable not set")
    exit(1)

try:
    # Create engine and connect
    engine = create_engine(database_url)
    
    # Check if column exists
    with engine.connect() as conn:
        logger.info("Checking if column exists...")
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'treasury_loan' 
            AND column_name = 'name'
        """))
        
        if result.rowcount > 0:
            logger.info("Column 'name' already exists in treasury_loan table")
            exit(0)
            
        # Add column
        logger.info("Adding 'name' column to treasury_loan table...")
        conn.execute(text("""
            ALTER TABLE treasury_loan 
            ADD COLUMN name VARCHAR(128) NOT NULL DEFAULT 'Loan'
        """))
        conn.commit()
        logger.info("Column added successfully")
        
except Exception as e:
    logger.error(f"Error: {str(e)}")
    exit(1)