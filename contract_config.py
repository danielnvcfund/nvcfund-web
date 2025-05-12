"""
Contract configuration for NVC Banking Platform
Manages contract addresses for both testnet and mainnet environments
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

# Default contract addresses
# These should be updated with your actual deployed mainnet contract addresses
DEFAULT_CONTRACT_ADDRESSES = {
    "testnet": {
        "settlement_contract": "0xE4eA76e830D1A10df277b9D3a1824F216F8F1A5A",
        "multisig_wallet": "0xB2C857F7AeCB1dEad987ceB5323f88C3Ef0B7C3E",
        "nvc_token": "0xA4Bc40DD1f6d56d5EF6EE6D5c8FE6C2fE10CaA4c"
    },
    "mainnet": {
        "settlement_contract": "",  # To be filled after mainnet deployment
        "multisig_wallet": "",      # To be filled after mainnet deployment
        "nvc_token": ""             # To be filled after mainnet deployment
    }
}

# Try to load contract addresses from environment variables
SETTLEMENT_CONTRACT_MAINNET = os.environ.get("SETTLEMENT_CONTRACT_MAINNET", "")
MULTISIG_WALLET_MAINNET = os.environ.get("MULTISIG_WALLET_MAINNET", "")
NVC_TOKEN_MAINNET = os.environ.get("NVC_TOKEN_MAINNET", "")

# Update mainnet addresses if provided via environment variables
if SETTLEMENT_CONTRACT_MAINNET:
    DEFAULT_CONTRACT_ADDRESSES["mainnet"]["settlement_contract"] = SETTLEMENT_CONTRACT_MAINNET
if MULTISIG_WALLET_MAINNET:
    DEFAULT_CONTRACT_ADDRESSES["mainnet"]["multisig_wallet"] = MULTISIG_WALLET_MAINNET
if NVC_TOKEN_MAINNET:
    DEFAULT_CONTRACT_ADDRESSES["mainnet"]["nvc_token"] = NVC_TOKEN_MAINNET

# Configuration file path (optional)
CONFIG_FILE_PATH = os.environ.get("CONTRACT_CONFIG_PATH", "contract_addresses.json")

# Load contract configuration from file if it exists
def load_contract_config():
    """Load contract configuration from file if available"""
    try:
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded contract configuration from {CONFIG_FILE_PATH}")
                return config
        else:
            logger.info(f"Contract configuration file {CONFIG_FILE_PATH} not found, using defaults")
            return DEFAULT_CONTRACT_ADDRESSES
    except Exception as e:
        logger.error(f"Error loading contract configuration: {str(e)}")
        return DEFAULT_CONTRACT_ADDRESSES

# Save contract configuration to file
def save_contract_config(config):
    """Save contract configuration to file"""
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        logger.info(f"Saved contract configuration to {CONFIG_FILE_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error saving contract configuration: {str(e)}")
        return False

# Update a specific contract address
def update_contract_address(network, contract_name, address):
    """Update a specific contract address in the configuration"""
    config = load_contract_config()
    
    if network not in config:
        config[network] = {}
    
    config[network][contract_name] = address
    
    return save_contract_config(config)

# Get contract address for the current network
def get_contract_address(contract_name, network=None):
    """
    Get the contract address for the specified network
    If network is not specified, use the ETHEREUM_NETWORK env var or default to testnet
    """
    if network is None:
        network = os.environ.get("ETHEREUM_NETWORK", "testnet").lower()
    
    config = load_contract_config()
    
    # Check if the network exists in config
    if network not in config:
        logger.warning(f"Network {network} not found in contract configuration, using testnet")
        network = "testnet"
    
    # Check if the contract exists in the network configuration
    if contract_name not in config[network]:
        logger.error(f"Contract {contract_name} not found in {network} configuration")
        return None
    
    return config[network][contract_name]