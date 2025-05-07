#!/usr/bin/env python
"""
Import All Remaining Account Holders
This script imports all account holders from the CSV file without any limit
"""

import import_account_holders_direct
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the import"""
    logger.info("Starting import of ALL remaining account holders...")
    
    # Call the import function with no maximum limit (will import all records)
    csv_file_path = 'attached_assets/NVC PB ACCOUNTS HOLDERS.csv'
    imported, skipped, errors = import_account_holders_direct.import_account_holders_direct(
        csv_file_path, 
        max_records=None  # This ensures all records will be imported
    )
    
    logger.info(f"Import completed: {imported} imported, {skipped} skipped, {errors} errors")
    
    if errors > 0:
        logger.warning("There were errors during import. Please check the logs.")
    else:
        logger.info("All account holders successfully imported!")

if __name__ == "__main__":
    main()