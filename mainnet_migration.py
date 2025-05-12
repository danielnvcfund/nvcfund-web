"""
NVCT Mainnet Migration Tool

This script handles the migration of NVCT token from Ethereum testnet (Sepolia) to mainnet.
It provides functions to:
1. Deploy smart contracts to Ethereum mainnet
2. Update configuration with new contract addresses
3. Validate the migration

Usage:
    python mainnet_migration.py deploy --contract=nvc_token
    python mainnet_migration.py validate
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from flask import Flask
from web3 import Web3, HTTPProvider
from eth_account import Account

import contract_config
from blockchain import (
    SETTLEMENT_CONTRACT_ABI, SETTLEMENT_CONTRACT_BYTECODE,
    MULTISIG_WALLET_ABI, MULTISIG_WALLET_BYTECODE,
    NVC_TOKEN_ABI, NVC_TOKEN_BYTECODE
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app context for database operations
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Import models within app context to avoid circular imports
with app.app_context():
    from app import db
    from models import SmartContract, BlockchainTransaction

def get_web3_connection(network="mainnet"):
    """Initialize Web3 connection to Ethereum node for specified network"""
    # Get Infura project ID
    infura_project_id = os.environ.get("INFURA_PROJECT_ID")
    
    if not infura_project_id:
        logger.error("INFURA_PROJECT_ID environment variable not set")
        return None
    
    # Set the appropriate network URL
    if network.lower() == "mainnet":
        node_url = f"https://mainnet.infura.io/v3/{infura_project_id}"
    else:
        node_url = f"https://sepolia.infura.io/v3/{infura_project_id}"
    
    logger.info(f"Connecting to Ethereum {network} at {node_url}")
    
    # Initialize Web3 instance
    w3 = Web3(HTTPProvider(node_url))
    
    # Check connection
    if not w3.is_connected():
        logger.error(f"Failed to connect to Ethereum {network}")
        return None
    
    logger.info(f"Successfully connected to Ethereum {network}. Network ID: {w3.net.version}")
    return w3

def deploy_contract(contract_name, w3, private_key, constructor_args=None):
    """Deploy a contract to the Ethereum network"""
    # Get the appropriate ABI and bytecode
    if contract_name == "settlement_contract":
        abi = SETTLEMENT_CONTRACT_ABI
        bytecode = SETTLEMENT_CONTRACT_BYTECODE
    elif contract_name == "multisig_wallet":
        abi = MULTISIG_WALLET_ABI
        bytecode = MULTISIG_WALLET_BYTECODE
    elif contract_name == "nvc_token":
        abi = NVC_TOKEN_ABI
        bytecode = NVC_TOKEN_BYTECODE
    else:
        logger.error(f"Unknown contract: {contract_name}")
        return None, None
    
    # Get account from private key
    account = Account.from_key(private_key)
    address = account.address
    
    logger.info(f"Deploying {contract_name} from address {address}")
    
    # Create contract instance
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Prepare transaction
    nonce = w3.eth.get_transaction_count(address)
    
    # Estimate gas for deployment
    gas_estimate = None
    try:
        if constructor_args:
            gas_estimate = contract.constructor(*constructor_args).estimate_gas({"from": address})
        else:
            gas_estimate = contract.constructor().estimate_gas({"from": address})
    except Exception as e:
        logger.error(f"Error estimating gas: {str(e)}")
        gas_estimate = 5000000  # Use a reasonable default
    
    # Get current gas price with a slight premium for faster processing
    gas_price = w3.eth.gas_price
    gas_price_with_premium = int(gas_price * 1.1)  # 10% premium
    
    # Build transaction
    tx_params = {
        "from": address,
        "nonce": nonce,
        "gas": gas_estimate,
        "gasPrice": gas_price_with_premium,
    }
    
    try:
        # Build the contract deployment transaction
        if constructor_args:
            tx = contract.constructor(*constructor_args).build_transaction(tx_params)
        else:
            tx = contract.constructor().build_transaction(tx_params)
        
        # Sign the transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
        
        # Send the transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        logger.info(f"Transaction sent: {tx_hash.hex()}")
        logger.info("Waiting for transaction to be mined...")
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600)
        
        contract_address = tx_receipt.contractAddress
        
        logger.info(f"Contract deployed at: {contract_address}")
        logger.info(f"Gas used: {tx_receipt.gasUsed}")
        
        # Save the contract address in our configuration
        network = "mainnet"
        contract_config.update_contract_address(network, contract_name, contract_address)
        
        # Create a database record for the deployed contract
        with app.app_context():
            # Get proper contract name for the database
            if contract_name == "settlement_contract":
                db_contract_name = "SettlementContract"
            elif contract_name == "multisig_wallet":
                db_contract_name = "MultiSigWallet"
            elif contract_name == "nvc_token":
                db_contract_name = "NVCToken"
            
            # Create database record
            contract = SmartContract(
                name=db_contract_name,
                address=contract_address,
                abi=json.dumps(abi),
                network="mainnet",
                is_active=True,
                deployment_date=datetime.now()
            )
            db.session.add(contract)
            
            # Create a blockchain transaction record
            tx_record = BlockchainTransaction(
                transaction_hash=tx_hash.hex(),
                from_address=address,
                to_address=None,  # Contract creation
                contract_address=contract_address,
                amount=0,
                gas_used=tx_receipt.gasUsed,
                gas_price=gas_price_with_premium,
                block_number=tx_receipt.blockNumber,
                status=True if tx_receipt.status == 1 else False,
                transaction_type="CONTRACT_DEPLOYMENT",
                network="mainnet"
            )
            db.session.add(tx_record)
            db.session.commit()
        
        return contract_address, tx_hash.hex()
    
    except Exception as e:
        logger.error(f"Error deploying contract: {str(e)}")
        return None, None

def validate_migration():
    """Validate the NVCT mainnet migration"""
    # Check required contract addresses
    contracts = ["settlement_contract", "multisig_wallet", "nvc_token"]
    missing_contracts = []
    
    for contract in contracts:
        address = contract_config.get_contract_address(contract, "mainnet")
        if not address:
            missing_contracts.append(contract)
    
    if missing_contracts:
        logger.error(f"Missing mainnet contract addresses: {', '.join(missing_contracts)}")
        return False
    
    # Validate Infura connectivity
    w3 = get_web3_connection("mainnet")
    if not w3:
        logger.error("Cannot connect to Ethereum mainnet")
        return False
    
    # Validate contract deployments
    for contract in contracts:
        address = contract_config.get_contract_address(contract, "mainnet")
        if not w3.eth.get_code(address):
            logger.error(f"No contract code found at {contract} address: {address}")
            return False
        else:
            logger.info(f"Validated {contract} at address {address}")
    
    logger.info("All contracts successfully validated on mainnet")
    return True

def show_status():
    """Show the current status of the NVCT migration"""
    # Show network settings
    print("\n=== NVCT NETWORK CONFIGURATION ===")
    print(f"Current network: {os.environ.get('ETHEREUM_NETWORK', 'testnet')}")
    print(f"Infura Project ID: {'Configured' if os.environ.get('INFURA_PROJECT_ID') else 'Not Configured'}")
    
    # Show contract addresses
    print("\n=== CONTRACT ADDRESSES ===")
    networks = ["testnet", "mainnet"]
    contracts = ["settlement_contract", "multisig_wallet", "nvc_token"]
    
    for network in networks:
        print(f"\n{network.upper()}:")
        for contract in contracts:
            address = contract_config.get_contract_address(contract, network) or "Not Deployed"
            print(f"  {contract}: {address}")
    
    # Show deployment status
    print("\n=== DEPLOYMENT STATUS ===")
    all_deployed = True
    for contract in contracts:
        address = contract_config.get_contract_address(contract, "mainnet")
        if not address:
            print(f"  {contract}: NOT DEPLOYED")
            all_deployed = False
        else:
            print(f"  {contract}: DEPLOYED")
    
    if all_deployed:
        print("\nStatus: READY FOR MAINNET")
    else:
        print("\nStatus: PENDING DEPLOYMENT")
    
    print("\n=== NEXT STEPS ===")
    if not all_deployed:
        print("1. Deploy remaining contracts:")
        for contract in contracts:
            if not contract_config.get_contract_address(contract, "mainnet"):
                print(f"   - python mainnet_migration.py deploy --contract={contract}")
        print("2. Run validation: python mainnet_migration.py validate")
        print("3. Switch to mainnet: export ETHEREUM_NETWORK=mainnet")
    else:
        print("1. Switch to mainnet: export ETHEREUM_NETWORK=mainnet")
        print("2. Restart the application")

def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description="NVCT Mainnet Migration Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy contract to mainnet")
    deploy_parser.add_argument("--contract", required=True, choices=["settlement_contract", "multisig_wallet", "nvc_token"],
                               help="Contract to deploy")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate mainnet migration")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show migration status")
    
    args = parser.parse_args()
    
    if args.command == "deploy":
        # Check for admin private key
        admin_private_key = os.environ.get("ADMIN_ETH_PRIVATE_KEY")
        if not admin_private_key:
            logger.error("ADMIN_ETH_PRIVATE_KEY environment variable not set")
            return 1
        
        # Connect to mainnet
        w3 = get_web3_connection("mainnet")
        if not w3:
            return 1
        
        # Prepare constructor arguments if needed
        constructor_args = None
        if args.contract == "nvc_token":
            # For NVC Token, we need initial supply and owner address
            owner_address = os.environ.get("NVC_TOKEN_OWNER_ADDRESS")
            if not owner_address:
                # Use the admin address as owner if not specified
                owner_address = Account.from_key(admin_private_key).address
            
            # Initial supply (e.g., 1 billion tokens with 18 decimals)
            initial_supply = int(1_000_000_000 * (10 ** 18))
            constructor_args = [initial_supply, owner_address]
        
        # Deploy the contract
        address, tx_hash = deploy_contract(args.contract, w3, admin_private_key, constructor_args)
        
        if address:
            print(f"\nSuccessfully deployed {args.contract} to mainnet")
            print(f"Contract address: {address}")
            print(f"Transaction hash: {tx_hash}")
            return 0
        else:
            print(f"\nFailed to deploy {args.contract} to mainnet")
            return 1
    
    elif args.command == "validate":
        if validate_migration():
            print("\nValidation successful! All contracts are properly deployed on mainnet.")
            return 0
        else:
            print("\nValidation failed. See logs for details.")
            return 1
    
    elif args.command == "status":
        show_status()
        return 0
    
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main())