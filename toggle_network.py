#!/usr/bin/env python3
"""
NVCT Network Toggle Tool

This script allows switching between Ethereum networks (mainnet/testnet) for NVCT operations.
It provides a simple way to test functionality in both environments before committing to mainnet.

Usage:
    python toggle_network.py [--mainnet|--testnet]
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv, set_key
import contract_config

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

def switch_to_network(network):
    """Switch to the specified Ethereum network
    
    Args:
        network (str): Network to switch to - 'mainnet' or 'testnet'
    """
    if network not in ['mainnet', 'testnet']:
        logger.error(f"Invalid network: {network}")
        return False
    
    current_network = os.environ.get('ETHEREUM_NETWORK', 'testnet')
    if current_network == network:
        logger.info(f"Already on {network} network")
        return True
    
    # Check if contract addresses are available for target network
    contracts_available = True
    for contract_type in contract_config.CONTRACT_TYPES:
        address = contract_config.get_contract_address(contract_type, network)
        if not address:
            logger.warning(f"No {network} address found for {contract_type}")
            contracts_available = False
        else:
            logger.info(f"Found {network} address for {contract_type}: {address}")
    
    if not contracts_available:
        logger.warning(f"Some contracts are not configured for {network}")
        logger.warning(f"Switching anyway, but functionality may be limited")
    
    # Set the environment variable
    set_environment_variable('ETHEREUM_NETWORK', network)
    logger.info(f"Switched to {network} network")
    
    # Provide information about the current state
    if network == 'mainnet':
        logger.info("NVCT is now configured to use Ethereum mainnet")
        logger.info("IMPORTANT: All transactions will use real ETH and affect the main Ethereum network")
    else:
        logger.info("NVCT is now configured to use Ethereum testnet (Sepolia)")
        logger.info("All transactions will use test ETH and won't affect the main Ethereum network")
    
    return True

def main():
    """Main function to process command line arguments"""
    parser = argparse.ArgumentParser(description="NVCT Network Toggle Tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--mainnet', action='store_true', help="Switch to Ethereum mainnet")
    group.add_argument('--testnet', action='store_true', help="Switch to Ethereum testnet (Sepolia)")
    args = parser.parse_args()
    
    # Load environment variables from .env file
    load_dotenv()
    
    if args.mainnet:
        return 0 if switch_to_network('mainnet') else 1
    elif args.testnet:
        return 0 if switch_to_network('testnet') else 1
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())