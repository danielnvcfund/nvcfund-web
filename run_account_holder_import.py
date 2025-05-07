#!/usr/bin/env python
"""
Run Account Holder Import
This script runs the import_account_holders.py script to import account holders from the CSV file.
"""

import os
import sys
import logging
from app import create_app

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function"""
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Import the import_test_account_holder function
            from import_account_holders import import_test_account_holder
            
            # Run the test import function
            imported, skipped, errors = import_test_account_holder()
            
            # Log the result
            logger.info(f"Test import completed: {imported} imported, {skipped} skipped, {errors} errors")
            
            if errors > 0:
                logger.warning("Test import completed with errors. Please check the logs.")
                sys.exit(1)
            else:
                logger.info("Test import completed successfully!")
                sys.exit(0)
                
        except Exception as e:
            logger.error(f"Error running import: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    main()