from app import app, db
from models import User, Transaction, TransactionStatus, TransactionType
from sqlalchemy import text

def run_migration():
    with app.app_context():
        # Add new columns to the User table
        try:
            db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS external_customer_id VARCHAR(64)"))
            db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS external_account_id VARCHAR(64)"))
            db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS external_account_type VARCHAR(32)"))
            db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS external_account_currency VARCHAR(3)"))
            db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS external_account_status VARCHAR(16)"))
            db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN IF NOT EXISTS last_sync TIMESTAMP"))
            
            # Add new columns to the Transaction table
            db.session.execute(text("ALTER TABLE transaction ADD COLUMN IF NOT EXISTS external_id VARCHAR(64)"))
            db.session.execute(text("ALTER TABLE transaction ADD COLUMN IF NOT EXISTS tx_metadata_json TEXT"))
            
            # Create indexes
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_external_customer_id ON \"user\" (external_customer_id)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_external_account_id ON \"user\" (external_account_id)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_transaction_external_id ON transaction (external_id)"))
            
            db.session.commit()
            print("Migration completed successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {e}")

if __name__ == "__main__":
    run_migration()
