#!/usr/bin/env python3
"""
NVCT Mainnet Setup Tool

A simple command-line utility to configure and check NVCT mainnet settings.
This tool helps administrators to:

1. Check current network configuration
2. Configure environment variables for mainnet
3. Verify contract deployments
4. Set up secure key management

Usage:
    python setup_nvct_mainnet.py
"""

import os
import sys
import argparse
import getpass
import logging
import json
from pathlib import Path

# Import python-dotenv with error handling
try:
    from dotenv import load_dotenv, set_key
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("Warning: python-dotenv not installed. Environment file operations will be limited.")
    print("Run: pip install python-dotenv to enable full functionality.")
    
    # Create stub functions that log but don't do anything
    def load_dotenv():
        print("Notice: python-dotenv not available, skipping .env loading")
        return False
        
    def set_key(env_file, key, value):
        print(f"Notice: python-dotenv not available, would set {key}={value} in {env_file}")
        return False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("nvct-setup")

def check_environment():
    """Check the current environment configuration"""
    print("\n=== CURRENT NVCT CONFIGURATION ===\n")
    
    # Check .env file
    env_file = Path('.env')
    if env_file.exists():
        print(f".env file: Found")
        # Load environment variables from .env if dotenv is available
        if DOTENV_AVAILABLE:
            load_dotenv()
        else:
            print("Note: .env file exists but python-dotenv not installed")
    else:
        print(f".env file: Not found")
    
    # Check important environment variables
    variables = [
        ("ETHEREUM_NETWORK", "Network type (mainnet or testnet)"),
        ("INFURA_PROJECT_ID", "Infura API access"),
        ("ADMIN_ETH_PRIVATE_KEY", "Contract deployment"),
        ("NVC_TOKEN_OWNER_ADDRESS", "Token ownership"),
        ("DATABASE_URL", "Database connection")
    ]
    
    print("\nEnvironment Variables:")
    for var, purpose in variables:
        value = os.environ.get(var)
        if value:
            if var == "ADMIN_ETH_PRIVATE_KEY":
                # Don't show the actual key
                print(f"  ✓ {var}: [SECURED] (for {purpose})")
            else:
                # Show first few characters of other variables
                display_value = value[:6] + "..." if len(value) > 10 else value
                print(f"  ✓ {var}: {display_value} (for {purpose})")
        else:
            print(f"  ✗ {var}: Not set (needed for {purpose})")
    
    # Check contract config
    print("\nContract Configuration:")
    try:
        import contract_config
        
        config = contract_config.load_contract_config()
        
        networks = ["testnet", "mainnet"]
        contracts = ["settlement_contract", "multisig_wallet", "nvc_token"]
        
        for network in networks:
            print(f"\n{network.upper()} Contracts:")
            for contract in contracts:
                if network in config and contract in config[network]:
                    address = config[network][contract]
                    if address:
                        print(f"  ✓ {contract}: {address}")
                    else:
                        print(f"  ✗ {contract}: Not deployed")
                else:
                    print(f"  ✗ {contract}: Not configured")
    except ImportError:
        print("  ✗ Contract configuration not found")
    except Exception as e:
        print(f"  ✗ Error checking contract configuration: {str(e)}")
    
    print("\nCurrent Status:")
    network = os.environ.get("ETHEREUM_NETWORK", "testnet").lower()
    if network == "mainnet":
        print("  ✓ System configured for MAINNET")
    else:
        print("  ✗ System configured for TESTNET")
    
    print()

def setup_environment():
    """Set up the environment for NVCT mainnet"""
    print("\n=== NVCT MAINNET CONFIGURATION ===\n")
    
    # Create or update .env file
    env_path = Path('.env')
    if env_path.exists():
        print("Updating existing .env file")
        # Load existing variables
        dotenv.load_dotenv()
    else:
        print("Creating new .env file")
    
    # Collect required information
    print("\nPlease provide the following information:\n")
    
    # Infura Project ID
    infura_id = os.environ.get("INFURA_PROJECT_ID")
    if not infura_id:
        infura_id = input("Infura Project ID: ").strip()
        if not infura_id:
            print("Warning: Infura Project ID is required for Ethereum network access")
    
    # Ask if they want to configure the private key
    configure_private_key = input("\nDo you want to configure the admin Ethereum private key? (yes/no): ").strip().lower()
    admin_key = os.environ.get("ADMIN_ETH_PRIVATE_KEY")
    
    if configure_private_key == "yes" or configure_private_key == "y":
        print("\nWARNING: Private keys should be handled securely.")
        print("This key will be stored in your .env file which should be kept private.")
        admin_key = getpass.getpass("Admin Ethereum Private Key: ").strip()
    
    # Owner address for the token
    owner_address = os.environ.get("NVC_TOKEN_OWNER_ADDRESS")
    if not owner_address:
        owner_address = input("\nToken Owner Address (leave blank to use admin address): ").strip()
    
    # Network selection - default to mainnet for this tool
    mainnet = "mainnet"
    
    # Save the configuration
    print("\nSaving configuration...")
    
    env_vars = {
        "ETHEREUM_NETWORK": mainnet,
    }
    
    if infura_id:
        env_vars["INFURA_PROJECT_ID"] = infura_id
    
    if admin_key:
        env_vars["ADMIN_ETH_PRIVATE_KEY"] = admin_key
    
    if owner_address:
        env_vars["NVC_TOKEN_OWNER_ADDRESS"] = owner_address
    
    # Update .env file
    try:
        for key, value in env_vars.items():
            dotenv.set_key('.env', key, value)
        print("Configuration saved successfully!")
    except Exception as e:
        print(f"Error saving configuration: {str(e)}")
        return False
    
    return True

def verify_deployment():
    """Verify the deployment of contracts to mainnet"""
    print("\n=== VERIFY MAINNET DEPLOYMENT ===\n")
    
    # Ensure proper environment
    dotenv.load_dotenv()
    
    # Check if we have the necessary tools
    try:
        import mainnet_migration
        print("Migration tool: Found")
    except ImportError:
        print("Migration tool: Not found (mainnet_migration.py required)")
        return False
    
    # Check current network setting
    network = os.environ.get("ETHEREUM_NETWORK", "testnet").lower()
    if network != "mainnet":
        print(f"Warning: Current network is set to {network}, not mainnet")
        set_mainnet = input("Set network to mainnet now? (yes/no): ").strip().lower()
        if set_mainnet == "yes" or set_mainnet == "y":
            dotenv.set_key('.env', "ETHEREUM_NETWORK", "mainnet")
            os.environ["ETHEREUM_NETWORK"] = "mainnet"
            print("Network set to mainnet")
        else:
            print("Keeping current network setting")
    
    # Verify contracts
    print("\nVerifying contracts...")
    try:
        result = mainnet_migration.validate_migration()
        if result:
            print("All contracts successfully verified on mainnet!")
        else:
            print("Contract verification failed. See logs for details.")
            
            # Show deployment command reminder
            print("\nTo deploy contracts, use:")
            print("  python mainnet_migration.py deploy --contract=settlement_contract")
            print("  python mainnet_migration.py deploy --contract=multisig_wallet")
            print("  python mainnet_migration.py deploy --contract=nvc_token")
        
        return result
    except Exception as e:
        print(f"Error during verification: {str(e)}")
        return False

def show_help():
    """Show help information"""
    print("\n=== NVCT MAINNET MIGRATION HELP ===\n")
    print("This tool helps you configure and deploy NVCT to Ethereum mainnet.\n")
    
    print("Main Steps for Migration:")
    print("1. Setup Environment Configuration")
    print("   - Configure Infura API access")
    print("   - Set up secure key management")
    print("   - Configure network settings\n")
    
    print("2. Deploy Smart Contracts")
    print("   - Deploy SettlementContract")
    print("   - Deploy MultiSigWallet")
    print("   - Deploy NVCToken (ERC-20)\n")
    
    print("3. Verify Deployment")
    print("   - Validate contract addresses")
    print("   - Check contract functionality")
    print("   - Monitor initial transactions\n")
    
    print("4. Set Production Mode")
    print("   - Switch to mainnet configuration")
    print("   - Update documentation")
    print("   - Notify users of the migration\n")
    
    print("For detailed instructions, see: static/docs/nvct_mainnet_migration_guide.html")
    print("For technical details, see: static/docs/nvc_mainnet_readiness_assessment.html\n")

def main():
    """Main function to process command line arguments"""
    parser = argparse.ArgumentParser(description="NVCT Mainnet Setup Tool")
    parser.add_argument("--check", action="store_true", help="Check current configuration")
    parser.add_argument("--setup", action="store_true", help="Setup mainnet environment")
    parser.add_argument("--verify", action="store_true", help="Verify mainnet deployment")
    parser.add_argument("--help-guide", action="store_true", help="Show detailed help information")
    
    args = parser.parse_args()
    
    # If no arguments, show interactive menu
    if not (args.check or args.setup or args.verify or args.help_guide):
        while True:
            print("\n=== NVCT MAINNET SETUP TOOL ===")
            print("1. Check Current Configuration")
            print("2. Setup Mainnet Environment")
            print("3. Verify Mainnet Deployment")
            print("4. Show Help Guide")
            print("5. Exit")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                check_environment()
            elif choice == "2":
                setup_environment()
            elif choice == "3":
                verify_deployment()
            elif choice == "4":
                show_help()
            elif choice == "5":
                print("Exiting...")
                return 0
            else:
                print("Invalid choice, please try again.")
            
            input("\nPress Enter to continue...")
    else:
        # Process specific command line arguments
        if args.check:
            check_environment()
        
        if args.setup:
            setup_environment()
        
        if args.verify:
            verify_deployment()
        
        if args.help_guide:
            show_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())