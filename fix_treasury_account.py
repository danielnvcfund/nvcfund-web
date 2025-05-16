"""
Fix Treasury Account Display Issue
This script will check why newly created treasury accounts aren't appearing in the list
and fix the issue.
"""
import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath('.'))

try:
    from app import app, db
    from models import TreasuryAccount, FinancialInstitution
    
    with app.app_context():
        logger.info("Checking for treasury accounts...")
        accounts = TreasuryAccount.query.all()
        
        if not accounts:
            logger.info("No treasury accounts found in the database.")
        else:
            logger.info(f"Found {len(accounts)} treasury accounts:")
            for account in accounts:
                logger.info(f"ID: {account.id}, Name: {account.name}, Is Active: {account.is_active}")
                
                # Make sure the account is active
                if not account.is_active:
                    logger.info(f"Activating account: {account.name}")
                    account.is_active = True
                
                # Make sure the institution relationship is correct
                if account.institution_id:
                    institution = FinancialInstitution.query.get(account.institution_id)
                    if institution:
                        logger.info(f"Institution: {institution.name}, Is Active: {institution.is_active}")
                        # Make sure the institution is active
                        if not institution.is_active:
                            logger.info(f"Activating institution: {institution.name}")
                            institution.is_active = True
                    else:
                        logger.warning(f"Institution ID {account.institution_id} not found for account {account.name}")
            
            # Commit changes
            db.session.commit()
            logger.info("Changes committed to database.")
            
        # Now look for the recently created NVC Global Treasury account specifically
        global_account = TreasuryAccount.query.filter(TreasuryAccount.name.like('%NVC Global Treasury%')).first()
        if global_account:
            logger.info(f"Found NVC Global Treasury account: ID {global_account.id}, active: {global_account.is_active}")
            global_account.is_active = True
            db.session.commit()
            logger.info("NVC Global Treasury account activated")
        else:
            logger.info("NVC Global Treasury account not found")
            
except Exception as e:
    logger.error(f"Error running fix script: {str(e)}")
    sys.exit(1)

logger.info("Script completed successfully")