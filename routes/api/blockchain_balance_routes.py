"""
Blockchain Balance API Routes
This module handles REST API endpoints for blockchain balances
"""

import logging
from flask import Blueprint, jsonify, request
from auth import api_test_access
from blockchain import init_web3, get_nvc_token_balance
from models import BlockchainAccount

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
blockchain_balance_api = Blueprint('blockchain_balance_api', __name__)

@blockchain_balance_api.route('/balances', methods=['GET'])
@api_test_access
def get_blockchain_balance(user=None):
    """Get the Ethereum balance for an address"""
    try:
        # Get address from query parameters
        address = request.args.get('address')
        
        if not address:
            # If address not provided in query, try to get the user's address
            if user:
                blockchain_account = BlockchainAccount.query.filter_by(user_id=user.id).first()
                if blockchain_account:
                    address = blockchain_account.eth_address
            
            # If still no address, return error
            if not address:
                return jsonify({
                    'success': False,
                    'error': 'No Ethereum address provided'
                }), 400
        
        # Validate Ethereum address format
        if not address.startswith('0x') or len(address) != 42:
            return jsonify({
                'success': False,
                'error': 'Invalid Ethereum address format'
            }), 400
        
        # Initialize Web3
        web3 = init_web3()
        
        # Get ETH balance
        eth_balance = web3.eth.get_balance(address)
        eth_balance_in_eth = web3.from_wei(eth_balance, 'ether')
        
        # Get NVC token balance if the contract is deployed
        token_balance = 0
        try:
            token_balance = get_nvc_token_balance(address)
        except Exception as token_ex:
            logger.warning(f"Failed to get NVC token balance: {str(token_ex)}")
            # Continue with ETH balance even if token balance fails
        
        return jsonify({
            'success': True,
            'address': address,
            'balance_wei': eth_balance,
            'balance_eth': float(eth_balance_in_eth),
            'token_balance': token_balance
        })
        
    except Exception as e:
        logger.error(f"Error getting blockchain balance: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error getting blockchain balance: {str(e)}"
        }), 500