#!/usr/bin/env python3
"""
Settlement Contract Deployment Script
This script manually triggers the deployment of the SettlementContract for the NVC Global Payment Gateway.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('contract_deployment')

def deploy_contracts():
    """Deploy settlement contract and related contracts"""
    try:
        # Import these after app is imported to ensure app context is available
        from blockchain import initialize_settlement_contract, initialize_multisig_wallet, initialize_nvc_token, get_web3
        
        # Verify Web3 connection
        w3 = get_web3()
        if not w3:
            logger.error("Failed to initialize Web3 connection. Aborting deployment.")
            return False
            
        logger.info(f"Connected to Ethereum network: {w3.net.version}")
        
        # Deploy smart contracts
        logger.info("Deploying SettlementContract...")
        initialize_settlement_contract()
        
        logger.info("Deploying MultiSigWallet...")
        initialize_multisig_wallet()
        
        logger.info("Deploying NVCToken...")
        initialize_nvc_token()
        
        logger.info("Contract deployment completed.")
        return True
        
    except Exception as e:
        logger.error(f"Error during contract deployment: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting contract deployment process...")
    
    # Import here to make sure application is fully initialized
    from app import app
    
    with app.app_context():        
        success = deploy_contracts()
        
        if success:
            logger.info("All contracts deployed successfully!")
            sys.exit(0)
        else:
            logger.error("Contract deployment failed!")
            sys.exit(1)