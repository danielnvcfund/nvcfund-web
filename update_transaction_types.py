"""
Script to update the transaction_type enum in the database to include new values.
This will alter the enum type to add missing values.
"""
import os
import sys
from sqlalchemy import create_engine, text

def update_transaction_types():
    # Get database connection from environment variable
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Connect to the database
    engine = create_engine(db_url)
    conn = engine.connect()
    
    # Begin a transaction
    trans = conn.begin()
    
    try:
        # Get the current enum values
        result = conn.execute(text(
            "SELECT unnest(enum_range(NULL::transactiontype_new)) AS enum_value"
        ))
        current_values = set(row[0] for row in result)
        
        # Define the required values
        required_values = {
            'DEPOSIT', 'WITHDRAWAL', 'TRANSFER', 'PAYMENT', 'SETTLEMENT', 
            'SWIFT_LETTER_OF_CREDIT', 'SWIFT_FUND_TRANSFER', 'SWIFT_INSTITUTION_TRANSFER',
            'SWIFT_FREE_FORMAT', 'SWIFT_TRANSFER', 'SWIFT_GPI_PAYMENT', 'SWIFT_GPI_NOTIFICATION',
            'INTERNATIONAL_WIRE', 'RTGS_TRANSFER', 'SERVER_TO_SERVER', 'OFF_LEDGER_TRANSFER',
            'TOKEN_EXCHANGE', 'EDI_PAYMENT', 'EDI_ACH_TRANSFER', 'EDI_WIRE_TRANSFER',
            'TREASURY_TRANSFER', 'TREASURY_INVESTMENT', 'TREASURY_LOAN', 'TREASURY_DEBT_REPAYMENT'
        }
        
        # Find missing values
        missing_values = required_values - current_values
        
        if missing_values:
            print(f"Missing transaction types: {', '.join(missing_values)}")
            
            # Temporarily alter the type to be text so we can update data
            conn.execute(text("ALTER TABLE transaction ALTER COLUMN transaction_type TYPE text"))
            
            # Add new enum values
            for missing_value in missing_values:
                conn.execute(text(
                    f"ALTER TYPE transactiontype_new ADD VALUE IF NOT EXISTS '{missing_value}'"
                ))
            
            # Change it back to the enum type
            conn.execute(text("ALTER TABLE transaction ALTER COLUMN transaction_type TYPE transactiontype_new USING transaction_type::transactiontype_new"))
            
            print("Successfully updated transaction_type enum with missing values")
        else:
            print("All required transaction types already exist in the database")
        
        # Commit the transaction
        trans.commit()
        
    except Exception as e:
        # Rollback on error
        trans.rollback()
        print(f"Error updating transaction types: {str(e)}")
        sys.exit(1)
    finally:
        # Close connection
        conn.close()

if __name__ == "__main__":
    update_transaction_types()