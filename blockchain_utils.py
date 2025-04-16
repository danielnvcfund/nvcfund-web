"""
Utility functions for blockchain operations.
This module is separated to avoid circular imports.
"""
import os
import logging
from eth_account import Account

logger = logging.getLogger(__name__)

def generate_ethereum_account():
    """
    Generate a new Ethereum account
    
    Returns:
        tuple: (address, private_key)
    """
    try:
        account = Account.create()
        return account.address, account.key.hex()
    
    except Exception as e:
        logger.error(f"Error generating Ethereum account: {str(e)}")
        return None, None