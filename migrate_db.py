"""
Database Migration Script for NVC Banking Platform
Used to update database schema with new fields
"""
import os
import sys
import logging
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the app context and db
from app import app, db

def run_migrations():
    """Run database migrations"""
    with app.app_context():
        try:
            # Add new user profile fields
            migrate_user_profile_fields()
            # Add name field to treasury_loan table
            migrate_treasury_loan_fields()
            logger.info("Migrations completed successfully")
        except Exception as e:
            logger.error(f"Migration error: {str(e)}")
            sys.exit(1)
            
def migrate_user_profile_fields():
    """Add profile fields to User model"""
    logger.info("Adding user profile fields")
    
    # Check if any of the new columns already exist
    with db.engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user' 
            AND column_name = 'first_name'
        """))
        
        # If first_name already exists, assume the migration was already done
        if result.rowcount > 0:
            logger.info("User profile fields already exist - skipping migration")
            return
        
        # Add new columns to the user table
        try:
            conn.execute(text("""
                ALTER TABLE "user" 
                ADD COLUMN first_name VARCHAR(100),
                ADD COLUMN last_name VARCHAR(100),
                ADD COLUMN organization VARCHAR(150),
                ADD COLUMN country VARCHAR(100),
                ADD COLUMN phone VARCHAR(50),
                ADD COLUMN newsletter BOOLEAN DEFAULT FALSE,
                ADD COLUMN email_verified BOOLEAN DEFAULT FALSE
            """))
            conn.commit()
            logger.info("User profile fields added successfully")
        except Exception as e:
            logger.error(f"Error adding user profile fields: {str(e)}")
            raise

def migrate_treasury_loan_fields():
    """Add name field to TreasuryLoan model"""
    logger.info("Checking treasury_loan table schema")
    
    # Check if the name column already exists
    with db.engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'treasury_loan' 
            AND column_name = 'name'
        """))
        
        # If name already exists, assume the migration was already done
        if result.rowcount > 0:
            logger.info("Treasury loan 'name' field already exists - skipping migration")
            return
        
        # Add new column to the treasury_loan table
        try:
            conn.execute(text("""
                ALTER TABLE treasury_loan 
                ADD COLUMN name VARCHAR(128) NOT NULL DEFAULT 'Loan'
            """))
            conn.commit()
            logger.info("Treasury loan name field added successfully")
        except Exception as e:
            logger.error(f"Error adding treasury loan name field: {str(e)}")
            raise

if __name__ == "__main__":
    run_migrations()