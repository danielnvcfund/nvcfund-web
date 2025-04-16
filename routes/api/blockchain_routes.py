"""
Blockchain API Routes
This module handles REST API endpoints for blockchain functionality
"""

import logging
from flask import Blueprint, jsonify, request
from auth import login_required, admin_required
from blockchain import (
    init_web3, 
    get_settlement_contract, 
    get_multisig_wallet, 
    get_nvc_token,
    initialize_settlement_contract,
    initialize_multisig_wallet,
    initialize_nvc_token,
    create_new_settlement,
    settle_payment_via_contract,
    get_transaction_status,
    submit_multisig_transaction,
    confirm_multisig_transaction,
    transfer_nvc_tokens,
    get_nvc_token_balance
)
from blockchain_utils import generate_ethereum_account
from models import BlockchainTransaction, BlockchainAccount, db

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
blockchain_api = Blueprint('blockchain_api', __name__)

@blockchain_api.route('/status', methods=['GET'])
@login_required
def blockchain_status():
    """Get the status of the blockchain connection"""
    try:
        web3 = init_web3()
        
        if web3 and web3.is_connected():
            # Get current block
            current_block = web3.eth.block_number
            
            # Get network name
            chain_id = web3.eth.chain_id
            network_map = {
                1: "Ethereum Mainnet",
                3: "Ropsten Testnet",
                4: "Rinkeby Testnet",
                5: "Goerli Testnet",
                42: "Kovan Testnet",
                11155111: "Sepolia Testnet"
            }
            network_name = network_map.get(chain_id, f"Unknown Network (Chain ID: {chain_id})")
            
            return jsonify({
                'success': True,
                'connected': True,
                'current_block': current_block,
                'network': network_name
            })
        else:
            return jsonify({
                'success': True,
                'connected': False,
                'message': 'Failed to connect to Ethereum node'
            })
    except Exception as e:
        logger.error(f"Error checking blockchain status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/deploy/settlement', methods=['POST'])
@admin_required
def deploy_settlement_contract():
    """Deploy the settlement contract"""
    try:
        contract_address, tx_hash = initialize_settlement_contract()
        
        if contract_address:
            return jsonify({
                'success': True,
                'address': contract_address,
                'tx_hash': tx_hash
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to deploy Settlement Contract'
            }), 500
    except Exception as e:
        logger.error(f"Error deploying settlement contract: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/deploy/multisig', methods=['POST'])
@admin_required
def deploy_multisig_wallet():
    """Deploy the MultiSig wallet contract"""
    try:
        # Get a list of admin users to be owners
        from models import User, UserRole
        admins = User.query.filter_by(role=UserRole.ADMIN).all()
        
        # Use admin ethereum addresses if they exist, otherwise create new ones
        owner_addresses = []
        for admin in admins:
            blockchain_account = BlockchainAccount.query.filter_by(user_id=admin.id).first()
            if blockchain_account:
                owner_addresses.append(blockchain_account.eth_address)
        
        # Add at least 3 addresses if not enough admins
        while len(owner_addresses) < 3:
            new_address, _ = generate_ethereum_account()
            owner_addresses.append(new_address)
        
        # Deploy with 2/3 required confirmations
        contract_address, tx_hash = initialize_multisig_wallet(owner_addresses, 2)
        
        if contract_address:
            return jsonify({
                'success': True,
                'address': contract_address,
                'tx_hash': tx_hash,
                'owners': owner_addresses,
                'required_confirmations': 2
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to deploy MultiSig Wallet'
            }), 500
    except Exception as e:
        logger.error(f"Error deploying multisig wallet: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/deploy/token', methods=['POST'])
@admin_required
def deploy_nvc_token():
    """Deploy the NVC token contract"""
    try:
        contract_address, tx_hash = initialize_nvc_token()
        
        if contract_address:
            return jsonify({
                'success': True,
                'address': contract_address,
                'tx_hash': tx_hash
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to deploy NVC Token'
            }), 500
    except Exception as e:
        logger.error(f"Error deploying NVC token: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/settlement/create', methods=['POST'])
@login_required
def create_settlement():
    """Create a new settlement using the settlement contract"""
    try:
        data = request.get_json()
        
        to_address = data.get('to_address')
        amount = float(data.get('amount'))
        metadata = data.get('metadata', '')
        
        # Get the user's ethereum address
        from flask_login import current_user
        blockchain_account = BlockchainAccount.query.filter_by(user_id=current_user.id).first()
        
        if not blockchain_account:
            # Create a new account if the user doesn't have one
            eth_address, private_key = generate_ethereum_account()
            blockchain_account = BlockchainAccount(
                user_id=current_user.id,
                eth_address=eth_address,
                eth_private_key=private_key
            )
            db.session.add(blockchain_account)
            db.session.commit()
        
        from_address = blockchain_account.eth_address
        private_key = blockchain_account.eth_private_key
        
        # Generate a transaction ID
        import uuid
        transaction_id = str(uuid.uuid4())
        
        # Create the settlement
        tx_hash = create_new_settlement(
            from_address=from_address,
            to_address=to_address,
            amount_in_eth=amount,
            private_key=private_key,
            transaction_id=transaction_id,
            tx_metadata=metadata
        )
        
        if tx_hash:
            # Save the transaction in the database
            blockchain_tx = BlockchainTransaction(
                user_id=current_user.id,
                from_address=from_address,
                to_address=to_address,
                eth_tx_hash=tx_hash,
                amount=amount,
                contract_address=get_settlement_contract().address,
                transaction_type='SETTLEMENT_CREATE',
                status='pending',
                tx_metadata=metadata
            )
            db.session.add(blockchain_tx)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'tx_hash': tx_hash,
                'transaction_id': transaction_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create settlement'
            }), 500
    except Exception as e:
        logger.error(f"Error creating settlement: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/settlement/<settlement_id>', methods=['GET'])
@login_required
def get_settlement(settlement_id):
    """Get details for a specific settlement"""
    try:
        # This would typically involve calling a function to get settlement details from the contract
        # For now, we'll return a mock response
        settlement_contract = get_settlement_contract()
        
        if not settlement_contract:
            return jsonify({
                'success': False,
                'message': 'Settlement contract is not deployed'
            }), 400
        
        # In a real implementation, we would get this from the contract:
        # settlement = settlement_contract.functions.getSettlement(settlement_id).call()
        
        # Mock data for demonstration
        settlement = {
            'id': settlement_id,
            'transactionId': 'tx_' + settlement_id,
            'from': '0x1234567890123456789012345678901234567890',
            'to': '0x0987654321098765432109876543210987654321',
            'amount': 1.5,
            'fee': 0.015,
            'status': 0,  # Pending
            'timestamp': 1617234567,
            'metadata': 'Test settlement'
        }
        
        return jsonify({
            'success': True,
            'settlement': settlement
        })
    except Exception as e:
        logger.error(f"Error getting settlement {settlement_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/settlement/<settlement_id>/complete', methods=['POST'])
@admin_required
def complete_settlement(settlement_id):
    """Complete a pending settlement"""
    try:
        # This would involve calling the contract to complete the settlement
        # For now, we'll return a mock response
        settlement_contract = get_settlement_contract()
        
        if not settlement_contract:
            return jsonify({
                'success': False,
                'message': 'Settlement contract is not deployed'
            }), 400
        
        # In a real implementation:
        # tx_hash = settlement_contract.functions.completeSettlement(settlement_id).transact()
        
        # Mock data
        tx_hash = '0x123456789abcdef123456789abcdef123456789abcdef123456789abcdef1234'
        
        return jsonify({
            'success': True,
            'tx_hash': tx_hash
        })
    except Exception as e:
        logger.error(f"Error completing settlement {settlement_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/settlement/<settlement_id>/cancel', methods=['POST'])
@admin_required
def cancel_settlement(settlement_id):
    """Cancel a pending settlement"""
    try:
        # This would involve calling the contract to cancel the settlement
        # For now, we'll return a mock response
        settlement_contract = get_settlement_contract()
        
        if not settlement_contract:
            return jsonify({
                'success': False,
                'message': 'Settlement contract is not deployed'
            }), 400
        
        # In a real implementation:
        # tx_hash = settlement_contract.functions.cancelSettlement(settlement_id).transact()
        
        # Mock data
        tx_hash = '0xabcdef123456789abcdef123456789abcdef123456789abcdef123456789abcd'
        
        return jsonify({
            'success': True,
            'tx_hash': tx_hash
        })
    except Exception as e:
        logger.error(f"Error cancelling settlement {settlement_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/multisig/submit', methods=['POST'])
@login_required
def submit_multisig():
    """Submit a transaction to the multisig wallet"""
    try:
        data = request.get_json()
        
        destination = data.get('destination')
        amount = float(data.get('amount'))
        tx_data = data.get('data', '0x')
        
        # Get the user's ethereum address
        from flask_login import current_user
        blockchain_account = BlockchainAccount.query.filter_by(user_id=current_user.id).first()
        
        if not blockchain_account:
            return jsonify({
                'success': False,
                'message': 'You do not have an associated Ethereum account'
            }), 400
        
        from_address = blockchain_account.eth_address
        private_key = blockchain_account.eth_private_key
        
        # Generate a transaction ID
        import uuid
        transaction_id = str(uuid.uuid4())
        
        # Submit the transaction to the multisig wallet
        tx_hash = submit_multisig_transaction(
            from_address=from_address,
            to_address=destination,
            amount_in_eth=amount,
            data=tx_data,
            private_key=private_key,
            transaction_id=transaction_id
        )
        
        if tx_hash:
            # Save the transaction in the database
            blockchain_tx = BlockchainTransaction(
                user_id=current_user.id,
                from_address=from_address,
                to_address=destination,
                eth_tx_hash=tx_hash,
                amount=amount,
                contract_address=get_multisig_wallet().address,
                transaction_type='MULTISIG_SUBMIT',
                status='pending',
                tx_metadata=f"Data: {tx_data}"
            )
            db.session.add(blockchain_tx)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'tx_hash': tx_hash,
                'transaction_id': transaction_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to submit transaction to MultiSig wallet'
            }), 500
    except Exception as e:
        logger.error(f"Error submitting multisig transaction: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/multisig/transaction/<tx_id>', methods=['GET'])
@login_required
def get_multisig_transaction(tx_id):
    """Get details for a multisig transaction"""
    try:
        # This would involve calling the contract to get transaction details
        # For now, we'll return a mock response
        multisig_wallet = get_multisig_wallet()
        
        if not multisig_wallet:
            return jsonify({
                'success': False,
                'message': 'MultiSig wallet is not deployed'
            }), 400
        
        # In a real implementation:
        # tx = multisig_wallet.functions.transactions(tx_id).call()
        # confirmations = [
        #     multisig_wallet.functions.getOwner(i).call()
        #     for i in range(multisig_wallet.functions.getConfirmationCount(tx_id).call())
        # ]
        
        # Mock data
        tx = {
            'id': tx_id,
            'destination': '0x1234567890123456789012345678901234567890',
            'value': 1.0,
            'data': '0x',
            'executed': False,
            'confirmations': 1,
            'confirmedBy': ['0xabcdef1234567890abcdef1234567890abcdef12']
        }
        
        return jsonify({
            'success': True,
            'transaction': tx,
            'required_confirmations': 2
        })
    except Exception as e:
        logger.error(f"Error getting multisig transaction {tx_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/multisig/confirm/<tx_id>', methods=['POST'])
@login_required
def confirm_multisig_tx(tx_id):
    """Confirm a multisig transaction"""
    try:
        # Get the user's ethereum address
        from flask_login import current_user
        blockchain_account = BlockchainAccount.query.filter_by(user_id=current_user.id).first()
        
        if not blockchain_account:
            return jsonify({
                'success': False,
                'message': 'You do not have an associated Ethereum account'
            }), 400
        
        from_address = blockchain_account.eth_address
        private_key = blockchain_account.eth_private_key
        
        # Generate a transaction ID for our records
        import uuid
        internal_tx_id = str(uuid.uuid4())
        
        # Confirm the transaction
        tx_hash = confirm_multisig_transaction(
            transaction_id=internal_tx_id,
            from_address=from_address,
            private_key=private_key,
            multisig_tx_id=int(tx_id)
        )
        
        if tx_hash:
            # Save the transaction in the database
            blockchain_tx = BlockchainTransaction(
                user_id=current_user.id,
                from_address=from_address,
                to_address=get_multisig_wallet().address,
                eth_tx_hash=tx_hash,
                amount=0,  # No ETH is transferred for confirmations
                contract_address=get_multisig_wallet().address,
                transaction_type='MULTISIG_CONFIRM',
                status='pending',
                tx_metadata=f"Confirmed transaction {tx_id}"
            )
            db.session.add(blockchain_tx)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'tx_hash': tx_hash
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to confirm transaction'
            }), 500
    except Exception as e:
        logger.error(f"Error confirming multisig transaction {tx_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/multisig/execute/<tx_id>', methods=['POST'])
@login_required
def execute_multisig_tx(tx_id):
    """Execute a multisig transaction that has enough confirmations"""
    try:
        # Get the user's ethereum address
        from flask_login import current_user
        blockchain_account = BlockchainAccount.query.filter_by(user_id=current_user.id).first()
        
        if not blockchain_account:
            return jsonify({
                'success': False,
                'message': 'You do not have an associated Ethereum account'
            }), 400
        
        from_address = blockchain_account.eth_address
        private_key = blockchain_account.eth_private_key
        
        # This would involve calling the contract to execute the transaction
        # For now, we'll return a mock response
        
        # In a real implementation:
        # tx_hash = multisig_wallet.functions.executeTransaction(tx_id).transact({
        #     'from': from_address
        # })
        
        # Mock data
        tx_hash = '0xfedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210'
        
        # Save the transaction in the database
        blockchain_tx = BlockchainTransaction(
            user_id=current_user.id,
            from_address=from_address,
            to_address=get_multisig_wallet().address,
            eth_tx_hash=tx_hash,
            amount=0,  # The execution itself doesn't transfer ETH
            contract_address=get_multisig_wallet().address,
            transaction_type='MULTISIG_EXECUTE',
            status='pending',
            tx_metadata=f"Executed transaction {tx_id}"
        )
        db.session.add(blockchain_tx)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tx_hash': tx_hash
        })
    except Exception as e:
        logger.error(f"Error executing multisig transaction {tx_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/token/transfer', methods=['POST'])
@login_required
def transfer_tokens():
    """Transfer NVC tokens from the user's account to another address"""
    try:
        data = request.get_json()
        
        to_address = data.get('to_address')
        amount = float(data.get('amount'))
        
        # Get the user's ethereum address
        from flask_login import current_user
        blockchain_account = BlockchainAccount.query.filter_by(user_id=current_user.id).first()
        
        if not blockchain_account:
            return jsonify({
                'success': False,
                'message': 'You do not have an associated Ethereum account'
            }), 400
        
        from_address = blockchain_account.eth_address
        private_key = blockchain_account.eth_private_key
        
        # Generate a transaction ID
        import uuid
        transaction_id = str(uuid.uuid4())
        
        # Transfer the tokens
        tx_hash = transfer_nvc_tokens(
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            private_key=private_key,
            transaction_id=transaction_id
        )
        
        if tx_hash:
            # Save the transaction in the database
            blockchain_tx = BlockchainTransaction(
                user_id=current_user.id,
                from_address=from_address,
                to_address=to_address,
                eth_tx_hash=tx_hash,
                amount=amount,
                contract_address=get_nvc_token().address,
                transaction_type='TOKEN_TRANSFER',
                status='pending'
            )
            db.session.add(blockchain_tx)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'tx_hash': tx_hash
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to transfer tokens'
            }), 500
    except Exception as e:
        logger.error(f"Error transferring tokens: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/token/mint', methods=['POST'])
@admin_required
def mint_tokens():
    """Mint new NVC tokens (admin only)"""
    try:
        data = request.get_json()
        
        to_address = data.get('to_address')
        amount = float(data.get('amount'))
        
        # This would involve calling the contract to mint tokens
        # For now, we'll return a mock response
        token_contract = get_nvc_token()
        
        if not token_contract:
            return jsonify({
                'success': False,
                'message': 'NVC Token contract is not deployed'
            }), 400
        
        # In a real implementation:
        # tx_hash = token_contract.functions.mint(to_address, amount).transact()
        
        # Mock data
        tx_hash = '0x1122334455667788991122334455667788991122334455667788991122334455'
        
        return jsonify({
            'success': True,
            'tx_hash': tx_hash
        })
    except Exception as e:
        logger.error(f"Error minting tokens: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/token/burn', methods=['POST'])
@admin_required
def burn_tokens():
    """Burn existing NVC tokens (admin only)"""
    try:
        data = request.get_json()
        
        from_address = data.get('from_address')
        amount = float(data.get('amount'))
        
        # This would involve calling the contract to burn tokens
        # For now, we'll return a mock response
        token_contract = get_nvc_token()
        
        if not token_contract:
            return jsonify({
                'success': False,
                'message': 'NVC Token contract is not deployed'
            }), 400
        
        # In a real implementation:
        # tx_hash = token_contract.functions.burn(from_address, amount).transact()
        
        # Mock data
        tx_hash = '0x5544332211998877665544332211998877665544332211998877665544332211'
        
        return jsonify({
            'success': True,
            'tx_hash': tx_hash
        })
    except Exception as e:
        logger.error(f"Error burning tokens: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500


@blockchain_api.route('/token/balance/<address>', methods=['GET'])
@login_required
def token_balance(address):
    """Get the NVC token balance for an address"""
    try:
        token_contract = get_nvc_token()
        
        if not token_contract:
            return jsonify({
                'success': False,
                'message': 'NVC Token contract is not deployed'
            }), 400
        
        balance = get_nvc_token_balance(address)
        
        return jsonify({
            'success': True,
            'address': address,
            'balance': balance
        })
    except Exception as e:
        logger.error(f"Error getting token balance for {address}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500