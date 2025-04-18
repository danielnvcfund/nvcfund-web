#!/usr/bin/env python3
"""
Background Deployment Script for Smart Contracts
This script runs the contract deployment as a separate process without affecting the web server.
"""

import os
import sys
import time
import logging
import threading
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('background_deployment')

def deploy_contracts():
    """Deploy all smart contracts in sequence"""
    try:
        # Import modules after app context is established
        from app import app
        from blockchain import initialize_settlement_contract, initialize_multisig_wallet, initialize_nvc_token
        from models import User, UserRole, BlockchainAccount, db
        from blockchain_utils import generate_ethereum_account
        
        with app.app_context():
            # 1. Settlement Contract
            logger.info("Deploying Settlement Contract...")
            settlement_address, settlement_tx = initialize_settlement_contract()
            
            if settlement_address:
                logger.info(f"Settlement Contract deployed at: {settlement_address}")
                logger.info(f"Transaction hash: {settlement_tx}")
            else:
                logger.error("Settlement Contract deployment failed")
                return False
                
            # 2. MultiSig Wallet
            logger.info("Deploying MultiSig Wallet...")
            
            # Get admin users for MultiSig owners
            admins = User.query.filter_by(role=UserRole.ADMIN).all()
            
            # Get ethereum addresses for admins (or create new ones)
            owner_addresses = []
            for admin in admins:
                blockchain_account = BlockchainAccount.query.filter_by(user_id=admin.id).first()
                if blockchain_account:
                    owner_addresses.append(blockchain_account.eth_address)
                else:
                    # Generate a new account if needed
                    new_address, private_key = generate_ethereum_account()
                    owner_addresses.append(new_address)
            
            # Ensure we have at least 3 owners
            while len(owner_addresses) < 3:
                new_address, _ = generate_ethereum_account()
                owner_addresses.append(new_address)
                
            multisig_address, multisig_tx = initialize_multisig_wallet(owner_addresses, 2)
            
            if multisig_address:
                logger.info(f"MultiSig Wallet deployed at: {multisig_address}")
                logger.info(f"Transaction hash: {multisig_tx}")
            else:
                logger.error("MultiSig Wallet deployment failed")
                # Continue to next contract even if this one fails
                
            # 3. NVC Token
            logger.info("Deploying NVC Token...")
            token_address, token_tx = initialize_nvc_token()
            
            if token_address:
                logger.info(f"NVC Token deployed at: {token_address}")
                logger.info(f"Transaction hash: {token_tx}")
            else:
                logger.error("NVC Token deployment failed")
                
            return True
            
    except Exception as e:
        logger.error(f"Error during contract deployment: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting background contract deployment...")
    success = deploy_contracts()
    
    if success:
        logger.info("Contract deployment completed successfully!")
        sys.exit(0)
    else:
        logger.error("Contract deployment failed!")
        sys.exit(1)