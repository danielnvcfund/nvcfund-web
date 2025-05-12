"""
Run the migration to add tx_hash column to blockchain_transaction table
"""
from app import app, db
from sqlalchemy import text

def run_migration():
    with app.app_context():
        try:
            # Check if table exists
            result = db.session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'blockchain_transaction');"
            ))
            
            if not result.scalar():
                print("Table blockchain_transaction does not exist, nothing to do")
                return
            
            # Check if column exists
            result = db.session.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'blockchain_transaction' AND column_name = 'tx_hash');"
            ))
            
            if result.scalar():
                print("Column tx_hash already exists in blockchain_transaction table")
                return
            
            # Add column
            print("Adding tx_hash column to blockchain_transaction table...")
            db.session.execute(text(
                "ALTER TABLE blockchain_transaction ADD COLUMN tx_hash VARCHAR(66) UNIQUE;"
            ))
            db.session.commit()
            print("Column tx_hash added successfully")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration error: {str(e)}")

if __name__ == "__main__":
    run_migration()