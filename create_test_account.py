#!/usr/bin/env python
"""
Create a test account holder for the system
"""

from app import create_app
from import_account_holders import import_test_account_holder

def main():
    app = create_app()
    with app.app_context():
        imported, skipped, errors = import_test_account_holder()
        
        if errors:
            print(f"Error creating test account holder. Please check the logs.")
        elif skipped:
            print(f"Test account holder already exists.")
        else:
            print(f"Successfully created test account holder.")

if __name__ == "__main__":
    main()