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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nvct-mainnet")

def set_environment_variable(name, value):
    """Set an environment variable both in memory and in .env file"""
    os.environ[name] = value
    
    # Also try to add to .env file for persistence
    try:
        env_path = ".env"
        
        # Check if file exists
        env_exists = os.path.exists(env_path)
        
        if env_exists:
            # Read existing content
            with open(env_path, "r") as f:
                lines = f.readlines()
            
            # Check if variable already exists
            var_exists = False
            new_lines = []
            
            for line in lines:
                if line.strip() and not line.strip().startswith("#"):
                    if line.strip().split("=")[0] == name:
                        new_lines.append(f"{name}={value}\n")
                        var_exists = True
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            # Add variable if it doesn't exist
            if not var_exists:
                new_lines.append(f"{name}={value}\n")
            
            # Write back
            with open(env_path, "w") as f:
                f.writelines(new_lines)
        else:
            # Create new file
            with open(env_path, "w") as f:
                f.write(f"{name}={value}\n")
        
        logger.info(f"Environment variable {name}={value} set in .env file")
        return True
    
    except Exception as e:
        logger.error(f"Error setting environment variable in .env file: {str(e)}")
        return False

def check_contract_addresses():
    """Check if contract addresses are available for mainnet"""
    try:
        import contract_config
        
        # Check the three required contracts
        contracts = ["settlement_contract", "multisig_wallet", "nvc_token"]
        missing_contracts = []
        
        for contract in contracts:
            address = contract_config.get_contract_address(contract, "mainnet")
            if not address:
                missing_contracts.append(contract)
        
        if missing_contracts:
            logger.warning(f"Missing mainnet contract addresses: {', '.join(missing_contracts)}")
            return False
        
        return True
    
    except ImportError:
        logger.error("contract_config module not available")
        return False
    
    except Exception as e:
        logger.error(f"Error checking contract addresses: {str(e)}")
        return False

def main():
    """Main function to process command line arguments"""
    parser = argparse.ArgumentParser(description="NVCT Mainnet Enabler")
    parser.add_argument("--force", action="store_true", 
                      help="Force enable mainnet even if contracts are not deployed")
    
    args = parser.parse_args()
    
    print("\n===== NVCT MAINNET ENABLER =====\n")
    
    # Check current network setting
    current_network = os.environ.get("ETHEREUM_NETWORK", "testnet").lower()
    
    if current_network == "mainnet":
        print("Mainnet is already enabled.")
        print(f"Current ETHEREUM_NETWORK value: {current_network}")
        return 0
    
    # Check if contracts are available if not forcing
    if not args.force:
        contracts_available = check_contract_addresses()
        
        if not contracts_available:
            print("\nWARNING: Not all mainnet contracts appear to be deployed.")
            print("You should deploy contracts before enabling mainnet.")
            print("\nTo deploy contracts, use:")
            print("  python mainnet_migration.py deploy --contract=settlement_contract")
            print("  python mainnet_migration.py deploy --contract=multisig_wallet")
            print("  python mainnet_migration.py deploy --contract=nvc_token")
            print("\nIf you want to enable mainnet anyway, use the --force flag:")
            print("  python enable_mainnet.py --force")
            return 1
    
    # Enable mainnet
    success = set_environment_variable("ETHEREUM_NETWORK", "mainnet")
    
    if success:
        print("\nSuccess! NVCT mainnet has been enabled.")
        print("\nImportant next steps:")
        print("1. Restart the application to apply changes")
        print("2. Verify functionality with the new mainnet contracts")
        print("3. Monitor initial transactions closely")
        
        if args.force:
            print("\nNOTE: Mainnet was enabled with the --force flag.")
            print("      Make sure to deploy all contracts if not already done.")
        
        return 0
    else:
        print("\nError enabling mainnet. See log for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())