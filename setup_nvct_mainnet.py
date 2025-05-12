#!/usr/bin/env python3
"""
NVCT Mainnet Setup Script

This script:
1. Checks if INFURA_API_KEY is configured
2. Enables Ethereum mainnet mode
3. Deploys contracts if necessary
4. Verifies the setup

Usage:
    python setup_nvct_mainnet.py --setup    # Setup mainnet environment
    python setup_nvct_mainnet.py --verify   # Verify mainnet deployment
"""

import os
import sys
import argparse
import logging
import subprocess
from dotenv import load_dotenv, set_key

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, capture_output=True):
    """Run a shell command and return the result"""
    logger.info(f"Running command: {command}")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True,
            text=True,
            capture_output=capture_output
        )
        if capture_output:
            logger.info(f"Command output: {result.stdout}")
        return True, result.stdout if capture_output else ""
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        if capture_output:
            logger.error(f"Error output: {e.stderr}")
        return False, e.stderr if capture_output else ""

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

def check_infura_api_key():
    """Check if INFURA_API_KEY is configured"""
    infura_key = os.environ.get('INFURA_API_KEY')
    if not infura_key:
        logger.error("INFURA_API_KEY is not configured")
        return False
    logger.info("INFURA_API_KEY is configured")
    return True

def enable_mainnet_mode():
    """Enable Ethereum mainnet mode"""
    logger.info("Enabling Ethereum mainnet mode...")
    success, output = run_command("python enable_mainnet.py --force")
    return success

def deploy_contracts():
    """Deploy contracts if they don't exist"""
    # Check current status
    success, output = run_command("python mainnet_migration.py status")
    if not success:
        logger.error("Failed to check contract status")
        return False
    
    # Check if contracts are already deployed
    if "Status: READY FOR MAINNET" in output:
        logger.info("All contracts are already deployed")
        return True
    
    # Deploy settlement contract
    logger.info("Deploying Settlement Contract...")
    success, _ = run_command("python mainnet_migration.py deploy --contract=settlement_contract")
    if not success:
        return False
    
    # Deploy multisig wallet
    logger.info("Deploying MultiSig Wallet...")
    success, _ = run_command("python mainnet_migration.py deploy --contract=multisig_wallet")
    if not success:
        return False
    
    # Deploy NVC token
    logger.info("Deploying NVC Token...")
    success, _ = run_command("python mainnet_migration.py deploy --contract=nvc_token")
    if not success:
        return False
    
    return True

def verify_setup():
    """Verify the mainnet setup"""
    logger.info("Verifying mainnet setup...")
    
    # Check if ETHEREUM_NETWORK is set to mainnet
    network = os.environ.get('ETHEREUM_NETWORK')
    if network != 'mainnet':
        logger.error(f"ETHEREUM_NETWORK is not set to mainnet (current: {network})")
        return False
    
    # Validate contracts
    success, output = run_command("python mainnet_migration.py validate")
    return success

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="NVCT Mainnet Setup Script")
    parser.add_argument("--setup", action="store_true", help="Setup mainnet environment")
    parser.add_argument("--verify", action="store_true", help="Verify mainnet deployment")
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Check arguments
    if not args.setup and not args.verify:
        parser.print_help()
        return 1
    
    # Setup mainnet environment
    if args.setup:
        logger.info("Setting up mainnet environment...")
        
        # Check INFURA_API_KEY
        if not check_infura_api_key():
            logger.error("Please configure INFURA_API_KEY before proceeding")
            return 1
        
        # Enable mainnet mode
        if not enable_mainnet_mode():
            logger.error("Failed to enable mainnet mode")
            return 1
        
        # Deploy contracts
        if not deploy_contracts():
            logger.error("Failed to deploy contracts")
            return 1
        
        logger.info("Mainnet environment setup completed successfully!")
    
    # Verify mainnet deployment
    if args.verify:
        logger.info("Verifying mainnet deployment...")
        if verify_setup():
            logger.info("Mainnet deployment verified successfully!")
        else:
            logger.error("Mainnet deployment verification failed")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())