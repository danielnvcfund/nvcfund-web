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
            
            # If still no address, return user-friendly error
            if not address:
                return jsonify({
                    'success': False,
                    'error': 'No Ethereum address assigned to your account',
                    'error_code': 'NO_ADDRESS',
                    'user_message': 'You need an Ethereum address to view blockchain balances.'
                }), 400
        
        # Validate Ethereum address format
        if not address.startswith('0x') or len(address) != 42:
            return jsonify({
                'success': False,
                'error': 'Invalid Ethereum address format',
                'error_code': 'INVALID_ADDRESS',
                'user_message': 'The Ethereum address format is not valid.'
            }), 400
        
        # Initialize Web3 with better error handling
        try:
            web3 = init_web3()
            if not web3 or not web3.is_connected():
                return jsonify({
                    'success': False,
                    'error': 'Cannot connect to Ethereum network',
                    'error_code': 'BLOCKCHAIN_CONNECTION_ERROR',
                    'user_message': 'Unable to connect to the blockchain network. Please try again later.'
                }), 503
        except Exception as web3_ex:
            logger.error(f"Failed to initialize Web3 connection: {str(web3_ex)}")
            return jsonify({
                'success': False,
                'error': 'Blockchain service unavailable',
                'error_code': 'BLOCKCHAIN_SERVICE_ERROR',
                'user_message': 'The blockchain service is currently unavailable. Please try again later.'
            }), 503
        
        # Get ETH balance with better error handling
        try:
            # Ensure address is properly checksummed
            checksummed_address = web3.to_checksum_address(address)
            eth_balance = web3.eth.get_balance(checksummed_address)
            eth_balance_in_eth = web3.from_wei(eth_balance, 'ether')
        except ValueError as val_err:
            logger.error(f"Invalid Ethereum address: {str(val_err)}")
            return jsonify({
                'success': False,
                'error': f"Invalid Ethereum address: {str(val_err)}",
                'error_code': 'INVALID_ADDRESS',
                'user_message': 'The Ethereum address provided is not valid.'
            }), 400
        except Exception as balance_ex:
            logger.error(f"Failed to get ETH balance: {str(balance_ex)}")
            return jsonify({
                'success': False,
                'error': f"Failed to retrieve balance: {str(balance_ex)}",
                'error_code': 'BALANCE_FETCH_ERROR',
                'user_message': 'Unable to fetch your Ethereum balance. The network may be congested.'
            }), 500
        
        # Get NVC token balance if the contract is deployed
        token_balance = 0
        token_error = None
        try:
            token_balance = get_nvc_token_balance(checksummed_address)
        except Exception as token_ex:
            token_error = str(token_ex)
            logger.warning(f"Failed to get NVC token balance: {token_error}")
            # Continue with ETH balance even if token balance fails
        
        response_data = {
            'success': True,
            'address': checksummed_address,
            'balance_wei': eth_balance,
            'balance_eth': float(eth_balance_in_eth),
            'token_balance': token_balance
        }
        
        # Add token error info if applicable (but don't make the whole request fail)
        if token_error:
            response_data['token_error'] = 'NVC token balance unavailable'
            response_data['token_error_details'] = token_error
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting blockchain balance: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error getting blockchain balance",
            'error_details': str(e),
            'error_code': 'GENERAL_ERROR',
            'user_message': 'An unexpected error occurred while fetching your blockchain balance. Please try again later.'
        }), 500