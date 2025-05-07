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
            # Import both the test account function and the CSV import function
            from import_account_holders import import_test_account_holder, import_account_holders
            
            # First, run the test import function
            test_imported, test_skipped, test_errors = import_test_account_holder()
            
            # Log the test result
            logger.info(f"Test import completed: {test_imported} imported, {test_skipped} skipped, {test_errors} errors")
            
            # Now import the real data from CSV
            csv_file_path = 'attached_assets/NVC PB ACCOUNTS HOLDERS.csv'
            
            if not os.path.exists(csv_file_path):
                logger.error(f"CSV file not found: {csv_file_path}")
                sys.exit(1)
            
            # Run the actual import from CSV
            logger.info(f"Starting import from CSV file: {csv_file_path}")
            imported, skipped, errors = import_account_holders(csv_file_path)
            
            # Log the result
            logger.info(f"CSV import completed: {imported} imported, {skipped} skipped, {errors} errors")
            
            total_errors = test_errors + errors
            if total_errors > 0:
                logger.warning(f"Import completed with {total_errors} errors. Please check the logs.")
                sys.exit(1)
            else:
                logger.info(f"All imports completed successfully! Total: {test_imported + imported} accounts imported.")
                sys.exit(0)
                
        except Exception as e:
            logger.error(f"Error running import: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    main()