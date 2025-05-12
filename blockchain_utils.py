"""
Utility functions for blockchain operations
Particularly focused on ensuring proper transaction tracking
"""
from app import db
from models import BlockchainTransaction
import logging
from eth_account import Account
import secrets

logger = logging.getLogger(__name__)

def generate_ethereum_account():
    """
    Generate a new Ethereum account
    
    Returns:
        tuple: (private_key, address)
    """
    # Generate a private key
    priv = secrets.token_hex(32)
    private_key = "0x" + priv
    
    # Get account from private key
    account = Account.from_key(private_key)
    
    return private_key, account.address

def update_tx_hash_for_transaction(transaction_id, tx_hash):
    """
    Update tx_hash for a blockchain transaction
    
    Args:
        transaction_id: ID of the transaction
        tx_hash: Transaction hash from the blockchain
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # First, try to find the transaction by its ID
        transaction = BlockchainTransaction.query.filter_by(id=transaction_id).first()
        if transaction:
            # Update the tx_hash field
            transaction.tx_hash = tx_hash if isinstance(tx_hash, str) else tx_hash.hex()
            db.session.commit()
            logger.info(f"Updated transaction {transaction_id} with tx_hash {tx_hash}")
            return True
        
        # Try to find by eth_tx_hash if available
        if hasattr(BlockchainTransaction, 'eth_tx_hash'):
            eth_hash = tx_hash if isinstance(tx_hash, str) else tx_hash.hex()
            transaction = BlockchainTransaction.query.filter_by(eth_tx_hash=eth_hash).first()
            if transaction:
                transaction.tx_hash = eth_hash
                db.session.commit()
                logger.info(f"Updated transaction with eth_tx_hash {eth_hash} with tx_hash")
                return True
        
        logger.warning(f"Could not find transaction with ID {transaction_id} to update tx_hash")
        return False
        
    except Exception as e:
        logger.error(f"Error updating tx_hash for transaction {transaction_id}: {str(e)}")
        db.session.rollback()
        return False