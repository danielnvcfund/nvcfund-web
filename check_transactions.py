"""
Check blockchain transactions for missing tx_hash values
"""
from app import app, db
from models import BlockchainTransaction
import json

with app.app_context():
    try:
        # Count all blockchain transactions
        total_count = db.session.query(BlockchainTransaction).count()
        print(f"Total blockchain transactions: {total_count}")
        
        # Check if the tx_hash column exists by querying it
        # This will fail if the column doesn't exist in the DB
        try:
            first_tx = db.session.query(BlockchainTransaction.tx_hash).first()
            print(f"Sample tx_hash: {first_tx[0] if first_tx else 'No transactions found'}")
            print("tx_hash column exists in the database")
        except Exception as e:
            print(f"Error querying tx_hash column: {str(e)}")
            print("tx_hash column may not exist in the database yet")
    
    except Exception as e:
        print(f"Error checking transactions: {str(e)}")