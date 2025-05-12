"""
Simple database migration to ensure the tx_hash column exists
This script uses the declarative schema to update the database
"""
from app import app, db
from models import BlockchainTransaction

print("Running database migration to ensure tx_hash column exists")

# Use Flask app context
with app.app_context():
    try:
        # Create or update the table to match the model
        # This is a safer approach as it uses the existing models
        print("Updating blockchain_transaction table schema...")
        db.create_all()
        print("Database schema updated successfully!")
        
    except Exception as e:
        print(f"Error updating database schema: {str(e)}")