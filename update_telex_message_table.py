"""
Add missing datetime columns to TelexMessage table
This script adds sent_at, received_at, and processed_at columns to the TelexMessage table.
"""

import logging
from datetime import datetime
from app import db, create_app
from models import TelexMessage, TelexMessageStatus
from sqlalchemy import Column, DateTime, text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_columns():
    """Add missing columns to TelexMessage table"""
    # Get database engine
    app = create_app()
    with app.app_context():
        # Check if columns already exist
        engine = db.engine
        inspector = db.inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("telex_message")]
        
        if "sent_at" not in columns:
            logger.info("Adding sent_at column to TelexMessage table")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE telex_message ADD COLUMN sent_at TIMESTAMP"))
                logger.info("sent_at column added successfully")
        else:
            logger.info("sent_at column already exists")
        
        if "received_at" not in columns:
            logger.info("Adding received_at column to TelexMessage table")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE telex_message ADD COLUMN received_at TIMESTAMP"))
                logger.info("received_at column added successfully")
        else:
            logger.info("received_at column already exists")
        
        if "processed_at" not in columns:
            logger.info("Adding processed_at column to TelexMessage table")
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE telex_message ADD COLUMN processed_at TIMESTAMP"))
                logger.info("processed_at column added successfully")
        else:
            logger.info("processed_at column already exists")
        
        logger.info("All columns added successfully")
        
        # Commit changes
        db.session.commit()

if __name__ == "__main__":
    add_columns()