"""
Contract Configuration for NVC Banking Platform

This module manages the configuration of smart contract addresses for different networks.
It provides a simple interface to store and retrieve contract addresses from the database
and from environment variables.

Usage:
    from contract_config import get_contract_address, set_contract_address
    
    # Get a contract address for a specific network
    settlement_address = get_contract_address('settlement_contract', 'testnet')
    
    # Set a contract address for a specific network
    set_contract_address('settlement_contract', '0x1234...', 'testnet')
"""

import os
import json
import logging
from datetime import datetime
from models import SmartContract

# Configure logging
logger = logging.getLogger(__name__)

# Default contract types
CONTRACT_TYPES = [
    'settlement_contract',
    'multisig_wallet',
    'nvc_token'
]

# Environment variable prefixes for different networks
ENV_PREFIXES = {
    'testnet': 'TESTNET_',
    'mainnet': 'MAINNET_'
}

def get_contract_address(contract_type, network='testnet'):
    """Get a contract address for a specific network
    
    Args:
        contract_type (str): The type of contract (settlement_contract, multisig_wallet, nvc_token)
        network (str): The network (testnet, mainnet)
        
    Returns:
        str: The contract address, or None if not found
    """
    if contract_type not in CONTRACT_TYPES:
        logger.warning(f"Unknown contract type: {contract_type}")
        return None
        
    # Try to get the address from environment variables first
    env_var = f"{ENV_PREFIXES.get(network, '')}{contract_type.upper()}_ADDRESS"
    address = os.environ.get(env_var)
    
    if address:
        logger.debug(f"Found contract address in environment variable {env_var}: {address}")
        return address
        
    # If not in environment, try to get from database
    try:
        contract = SmartContract.query.filter_by(
            contract_type=contract_type,
            network=network,
            is_active=True
        ).order_by(SmartContract.created_at.desc()).first()
        
        if contract:
            logger.debug(f"Found contract address in database: {contract.address}")
            return contract.address
    except Exception as e:
        logger.error(f"Error querying database for contract address: {str(e)}")
    
    logger.warning(f"Contract address not found for {contract_type} on {network}")
    return None

def set_contract_address(contract_type, address, network='testnet'):
    """Set a contract address for a specific network
    
    This function stores the contract address in the database and in environment variables
    for persistence across restarts.
    
    Args:
        contract_type (str): The type of contract (settlement_contract, multisig_wallet, nvc_token)
        address (str): The contract address
        network (str): The network (testnet, mainnet)
    
    Returns:
        bool: True if successful, False otherwise
    """
    if contract_type not in CONTRACT_TYPES:
        logger.warning(f"Unknown contract type: {contract_type}")
        return False
        
    # Set the environment variable
    env_var = f"{ENV_PREFIXES.get(network, '')}{contract_type.upper()}_ADDRESS"
    os.environ[env_var] = address
    
    # Update .env file for persistence
    try:
        from dotenv import load_dotenv, set_key
        dotenv_path = os.path.join(os.getcwd(), '.env')
        if os.path.exists(dotenv_path):
            set_key(dotenv_path, env_var, address)
            logger.debug(f"Updated {env_var} in .env file")
    except Exception as e:
        logger.warning(f"Could not update .env file: {str(e)}")
    
    # Store in database
    try:
        from app import db
        
        # Deactivate any existing contracts of this type on this network
        existing_contracts = SmartContract.query.filter_by(
            contract_type=contract_type,
            network=network,
            is_active=True
        ).all()
        
        for contract in existing_contracts:
            contract.is_active = False
            db.session.add(contract)
        
        # Create a new contract record
        contract = SmartContract(
            name=f"{contract_type} ({network})",
            contract_type=contract_type,
            address=address,
            network=network,
            is_active=True,
            description=f"{contract_type} deployed on {network}",
            created_at=datetime.utcnow()
        )
        
        db.session.add(contract)
        db.session.commit()
        logger.info(f"Updated contract address in database: {contract_type} on {network} = {address}")
        return True
    except Exception as e:
        logger.error(f"Error storing contract address in database: {str(e)}")
        return False

def get_all_contracts(network=None):
    """Get all contract addresses for a specific network or all networks
    
    Args:
        network (str, optional): The network to filter by. If None, returns all networks.
        
    Returns:
        dict: A dictionary of contract addresses by network and type
    """
    result = {}
    
    # First, get from environment variables
    for net, prefix in ENV_PREFIXES.items():
        if network and net != network:
            continue
            
        result[net] = {}
        for contract_type in CONTRACT_TYPES:
            env_var = f"{prefix}{contract_type.upper()}_ADDRESS"
            address = os.environ.get(env_var)
            if address:
                result[net][contract_type] = address
    
    # Then, supplement or override with database values
    try:
        query = SmartContract.query.filter_by(is_active=True)
        if network:
            query = query.filter_by(network=network)
            
        contracts = query.all()
        for contract in contracts:
            if contract.network not in result:
                result[contract.network] = {}
            result[contract.network][contract.contract_type] = contract.address
    except Exception as e:
        logger.error(f"Error querying database for contract addresses: {str(e)}")
    
    return result

def validate_config():
    """Validate the contract configuration
    
    Returns:
        dict: A dictionary with validation results
    """
    current_network = os.environ.get('ETHEREUM_NETWORK', 'testnet')
    result = {
        'status': 'success',
        'network': current_network,
        'contracts': {}
    }
    
    for contract_type in CONTRACT_TYPES:
        address = get_contract_address(contract_type, current_network)
        status = {
            'address': address,
            'valid': bool(address),
            'message': 'Contract address found' if address else 'Contract address not configured'
        }
        result['contracts'][contract_type] = status
    
    # Check if all contracts are configured
    all_configured = all(result['contracts'][ct]['valid'] for ct in CONTRACT_TYPES)
    result['all_configured'] = all_configured
    
    if all_configured:
        result['message'] = f'All contracts are properly configured for {current_network}'
    else:
        result['message'] = f'Some contracts are not configured for {current_network}'
        result['status'] = 'warning'
    
    return result