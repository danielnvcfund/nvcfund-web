"""
Blockchain Administration Routes for NVC Banking Platform
"""

import os
import logging
import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from models import SmartContract, User, Role, BlockchainTransaction
from auth import admin_required

# Import contract configuration
import contract_config

# Configure logging
logger = logging.getLogger(__name__)

# Create a blueprint for blockchain admin routes
blockchain_admin_bp = Blueprint('blockchain_admin', __name__, url_prefix='/admin/blockchain')

@blockchain_admin_bp.route('/')
@login_required
@admin_required
def index():
    """Blockchain administration dashboard"""
    # Get current network (testnet or mainnet)
    network = os.environ.get("ETHEREUM_NETWORK", "testnet").lower()
    
    # Get contracts from database
    testnet_contracts = SmartContract.query.filter_by(network="testnet").all()
    mainnet_contracts = SmartContract.query.filter_by(network="mainnet").all()
    
    # Also get contracts from config file
    config_contracts = contract_config.load_contract_config()
    
    # Get recent blockchain transactions
    recent_transactions = BlockchainTransaction.query.order_by(
        BlockchainTransaction.id.desc()
    ).limit(10).all()
    
    return render_template(
        'admin/blockchain/index.html',
        current_network=network,
        testnet_contracts=testnet_contracts,
        mainnet_contracts=mainnet_contracts,
        config_contracts=config_contracts,
        recent_transactions=recent_transactions
    )

@blockchain_admin_bp.route('/network/<network>', methods=['POST'])
@login_required
@admin_required
def set_network(network):
    """Set the current blockchain network"""
    if network not in ["testnet", "mainnet"]:
        flash("Invalid network specified", "danger")
        return redirect(url_for('blockchain_admin.index'))
    
    # Set environment variable
    os.environ["ETHEREUM_NETWORK"] = network
    
    # Try to persist in .env file
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
                    if line.strip().split("=")[0] == "ETHEREUM_NETWORK":
                        new_lines.append(f"ETHEREUM_NETWORK={network}\n")
                        var_exists = True
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            # Add variable if it doesn't exist
            if not var_exists:
                new_lines.append(f"ETHEREUM_NETWORK={network}\n")
            
            # Write back
            with open(env_path, "w") as f:
                f.writelines(new_lines)
        else:
            # Create new file
            with open(env_path, "w") as f:
                f.write(f"ETHEREUM_NETWORK={network}\n")
        
        flash(f"Network set to {network.upper()} and saved to .env file", "success")
    except Exception as e:
        logger.error(f"Error setting network in .env file: {str(e)}")
        flash(f"Network set to {network.upper()} but could not save to .env file", "warning")
    
    return redirect(url_for('blockchain_admin.index'))

@blockchain_admin_bp.route('/contracts/update', methods=['POST'])
@login_required
@admin_required
def update_contract():
    """Update a contract address in the configuration"""
    contract_name = request.form.get('contract_name')
    network = request.form.get('network')
    address = request.form.get('address')
    
    if not contract_name or not network or not address:
        flash("Missing required parameters", "danger")
        return redirect(url_for('blockchain_admin.index'))
    
    if network not in ["testnet", "mainnet"]:
        flash("Invalid network specified", "danger")
        return redirect(url_for('blockchain_admin.index'))
    
    # Update configuration
    try:
        contract_config.update_contract_address(network, contract_name, address)
        flash(f"Contract {contract_name} updated for {network}", "success")
        
        # Also update database if it exists
        db_name = None
        if contract_name == "settlement_contract":
            db_name = "SettlementContract"
        elif contract_name == "multisig_wallet":
            db_name = "MultiSigWallet"
        elif contract_name == "nvc_token":
            db_name = "NVCToken"
        
        if db_name:
            # Check if contract exists in database
            contract = SmartContract.query.filter_by(
                name=db_name, 
                network=network
            ).first()
            
            if contract:
                # Update existing record
                contract.address = address
                contract.updated_at = datetime.now()
                db.session.commit()
                flash(f"Database record for {db_name} also updated", "success")
            else:
                # Create new record
                new_contract = SmartContract(
                    name=db_name,
                    address=address,
                    network=network,
                    is_active=True,
                    deployment_date=datetime.now()
                )
                db.session.add(new_contract)
                db.session.commit()
                flash(f"New database record created for {db_name}", "success")
    
    except Exception as e:
        logger.error(f"Error updating contract: {str(e)}")
        flash(f"Error updating contract: {str(e)}", "danger")
    
    return redirect(url_for('blockchain_admin.index'))

@blockchain_admin_bp.route('/deploy')
@login_required
@admin_required
def deploy_page():
    """Show the contract deployment page"""
    return render_template('admin/blockchain/deploy.html')

@blockchain_admin_bp.route('/status')
@login_required
@admin_required
def status():
    """Show blockchain connection status"""
    try:
        from blockchain import get_web3
        
        w3 = get_web3()
        connected = w3 and w3.is_connected()
        
        if connected:
            network_id = w3.net.version
            latest_block = w3.eth.block_number
            gas_price = w3.eth.gas_price
            
            # Get connected accounts
            accounts = []
            admin_key = os.environ.get("ADMIN_ETH_PRIVATE_KEY")
            if admin_key:
                from eth_account import Account
                account = Account.from_key(admin_key)
                
                try:
                    balance = w3.eth.get_balance(account.address)
                    accounts.append({
                        "address": account.address,
                        "balance": w3.from_wei(balance, "ether")
                    })
                except Exception as e:
                    logger.error(f"Error getting account balance: {str(e)}")
                    accounts.append({
                        "address": account.address,
                        "balance": "Error"
                    })
            
            return render_template(
                'admin/blockchain/status.html',
                connected=connected,
                network_id=network_id,
                latest_block=latest_block,
                gas_price=w3.from_wei(gas_price, "gwei"),
                accounts=accounts
            )
        else:
            return render_template(
                'admin/blockchain/status.html',
                connected=False,
                error="Could not connect to Ethereum node"
            )
    
    except Exception as e:
        logger.error(f"Error checking blockchain status: {str(e)}")
        return render_template(
            'admin/blockchain/status.html',
            connected=False,
            error=str(e)
        )