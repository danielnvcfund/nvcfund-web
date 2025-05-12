#!/usr/bin/env python3
"""
NVCT Mainnet Enabler

A simple script to enable NVCT mainnet operation.
This script:
1. Sets the ETHEREUM_NETWORK environment variable to 'mainnet'
2. Validates mainnet contract addresses if available
3. Provides instructions for deployment if needed

Usage:
    python enable_mainnet.py [--force]
    
Options:
    --force    Force enable mainnet even if contracts are not deployed
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv, set_key
import contract_config
from blockchain import validate_contract_addresses

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def set_environment_variable(name, value):
    """Set an environment variable both in memory and in .env file"""
    os.environ[name] = value
    
    # Update .env file
    try:
        dotenv_path = os.path.join(os.getcwd(), '.env')
        if os.path.exists(dotenv_path):
            set_key(dotenv_path, name, value)
            logger.info(f"Updated {name}={value} in .env file")
    except Exception as e:
        logger.warning(f"Could not update .env file: {str(e)}")
        logger.info(f"Environment variable {name}={value} set in memory only")

def check_contract_addresses():
    """Check if contract addresses are available for mainnet"""
    try:
        # Check each required contract
        for contract_type in contract_config.CONTRACT_TYPES:
            address = contract_config.get_contract_address(contract_type, 'mainnet')
            if not address:
                logger.error(f"No mainnet address found for {contract_type}")
                return False
            logger.info(f"Found mainnet address for {contract_type}: {address}")
        return True
    except Exception as e:
        logger.error(f"Error checking contract addresses: {str(e)}")
        return False

def main():
    """Main function to process command line arguments"""
    parser = argparse.ArgumentParser(description="Enable NVCT mainnet operation")
    parser.add_argument('--force', action='store_true', help="Force enable mainnet even if contracts are not deployed")
    args = parser.parse_args()
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if we're already in mainnet mode
    current_network = os.environ.get('ETHEREUM_NETWORK')
    if current_network == 'mainnet':
        logger.info("Already in mainnet mode")
        
        # Validate contract addresses
        if check_contract_addresses():
            logger.info("All required contract addresses are available for mainnet")
        else:
            logger.warning("Some contract addresses are missing for mainnet")
            logger.info("Please deploy the missing contracts or update their addresses")
            if not args.force:
                return
        return
    
    # Check if mainnet contracts are deployed
    if check_contract_addresses():
        logger.info("All required contract addresses are available for mainnet")
    else:
        logger.warning("Some contract addresses are missing for mainnet")
        logger.info("Please deploy the contracts using:")
        logger.info("  python mainnet_migration.py deploy --contract=settlement_contract")
        logger.info("  python mainnet_migration.py deploy --contract=multisig_wallet")
        logger.info("  python mainnet_migration.py deploy --contract=nvc_token")
        
        if not args.force:
            logger.error("Aborting mainnet enablement. Use --force to override.")
            return
        
        logger.warning("Forcing mainnet mode despite missing contract addresses")
    
    # Set the environment variable
    set_environment_variable('ETHEREUM_NETWORK', 'mainnet')
    logger.info("Mainnet mode enabled")
    
    # Validate contract configuration
    validation = validate_contract_addresses('mainnet')
    if validation:
        logger.info("Contract validation results:")
        for contract_type, status in validation.get('contracts', {}).items():
            valid = "✓" if status.get('valid') else "✗"
            address = status.get('address', 'Not configured')
            logger.info(f"  {valid} {contract_type}: {address}")
    
    logger.info("NVCT is now configured to use Ethereum mainnet")
    logger.info("IMPORTANT: All transactions will use real ETH and affect the main Ethereum network")

if __name__ == "__main__":
    main()