"""
Blockchain Administration Routes for NVC Banking Platform
These routes provide administrative tools for managing blockchain contracts and settings.
"""

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from functools import wraps
from models import User, Role, SmartContract, BlockchainTransaction
from auth import admin_required, jwt_required
from blockchain import (
    get_web3_connection, 
    get_network_status, 
    deploy_settlement_contract,
    deploy_multisig_wallet,
    deploy_nvc_token,
    validate_contract_addresses
)
import contract_config

# Create blueprint
blockchain_admin_bp = Blueprint('blockchain_admin', __name__, url_prefix='/admin/blockchain')

def blockchain_admin_required(f):
    """Decorator to require blockchain admin access"""
    @wraps(f)
    @admin_required
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

@blockchain_admin_bp.route('/')
@blockchain_admin_required
def index():
    """Blockchain administration dashboard"""
    # Get current network status
    current_network = os.environ.get('ETHEREUM_NETWORK', 'testnet')
    is_mainnet = current_network == 'mainnet'
    
    # Get contract addresses
    settlement_contract_address = contract_config.get_contract_address('settlement_contract', current_network)
    multisig_wallet_address = contract_config.get_contract_address('multisig_wallet', current_network)
    nvc_token_address = contract_config.get_contract_address('nvc_token', current_network)
    
    # Check connection status
    try:
        web3 = get_web3_connection()
        is_connected = web3 is not None
    except Exception:
        is_connected = False
    
    # Get recent blockchain transactions
    try:
        recent_transactions = BlockchainTransaction.query.order_by(
            BlockchainTransaction.timestamp.desc()
        ).limit(10).all()
    except Exception:
        recent_transactions = []
    
    return render_template(
        'admin/blockchain/index.html',
        current_network=current_network,
        is_mainnet=is_mainnet,
        is_connected=is_connected,
        settlement_contract_address=settlement_contract_address,
        multisig_wallet_address=multisig_wallet_address,
        nvc_token_address=nvc_token_address,
        recent_transactions=recent_transactions
    )

@blockchain_admin_bp.route('/set-network/<network>', methods=['POST'])
@blockchain_admin_required
def set_network(network):
    """Set the current blockchain network"""
    if network not in ['testnet', 'mainnet']:
        flash('Invalid network specified', 'danger')
        return redirect(url_for('blockchain_admin.index'))
    
    # Update the environment variable
    os.environ['ETHEREUM_NETWORK'] = network
    
    # Update .env file for persistence across restarts
    try:
        from dotenv import load_dotenv, set_key
        dotenv_path = os.path.join(os.getcwd(), '.env')
        set_key(dotenv_path, 'ETHEREUM_NETWORK', network)
        flash(f'Network set to {network.upper()}', 'success')
    except Exception as e:
        flash(f'Network temporarily set to {network.upper()}, but could not update .env file: {str(e)}', 'warning')
    
    return redirect(url_for('blockchain_admin.index'))

@blockchain_admin_bp.route('/contracts/update', methods=['POST'])
@blockchain_admin_required
def update_contract():
    """Update a contract address in the configuration"""
    contract_type = request.form.get('contract_type')
    network = request.form.get('network', 'testnet')
    address = request.form.get('address')
    
    if not contract_type or not address:
        flash('Contract type and address are required', 'danger')
        return redirect(url_for('blockchain_admin.index'))
    
    try:
        # Validate the address format
        web3 = get_web3_connection()
        if not web3.is_address(address):
            flash('Invalid Ethereum address format', 'danger')
            return redirect(url_for('blockchain_admin.index'))
        
        # Store the contract in the database
        contract = SmartContract(
            name=contract_type,
            address=address,
            network=network,
            is_active=True,
            contract_type=contract_type,
            description=f"{contract_type} on {network}"
        )
        
        from app import db
        db.session.add(contract)
        db.session.commit()
        
        # Update the contract_config
        contract_config.set_contract_address(contract_type, address, network)
        
        flash(f'{contract_type} contract address updated for {network}', 'success')
    except Exception as e:
        flash(f'Error updating contract address: {str(e)}', 'danger')
    
    return redirect(url_for('blockchain_admin.index'))

@blockchain_admin_bp.route('/deploy')
@blockchain_admin_required
def deploy_page():
    """Show the contract deployment page"""
    return render_template('admin/blockchain/deploy.html')

@blockchain_admin_bp.route('/status')
@blockchain_admin_required
def status():
    """Show blockchain connection status"""
    try:
        web3 = get_web3_connection()
        status_data = {
            'is_connected': web3 is not None,
            'network': os.environ.get('ETHEREUM_NETWORK', 'testnet'),
            'chain_id': web3.net.version if web3 else None,
            'current_block': web3.eth.block_number if web3 else None,
            'gas_price': web3.from_wei(web3.eth.gas_price, 'gwei') if web3 else None
        }
        
        # Get admin account balance
        admin_address = os.environ.get('ADMIN_ETH_ADDRESS')
        if admin_address and web3:
            balance_wei = web3.eth.get_balance(admin_address)
            status_data['admin_balance'] = web3.from_wei(balance_wei, 'ether')
            status_data['admin_address'] = admin_address
    except Exception as e:
        status_data = {
            'is_connected': False,
            'error': str(e)
        }
    
    return jsonify(status_data)

@blockchain_admin_bp.route('/validate-contracts')
@blockchain_admin_required
def validate_contracts():
    """Validate contract addresses"""
    network = os.environ.get('ETHEREUM_NETWORK', 'testnet')
    
    try:
        validation_results = validate_contract_addresses(network)
        return jsonify({
            'status': 'success',
            'validation': validation_results
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })