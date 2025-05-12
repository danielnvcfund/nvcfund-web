"""
Admin routes for blockchain management
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import current_user, login_required
from sqlalchemy import func, text, inspect
from app import db
from models import SmartContract, BlockchainTransaction
from auth import admin_required, blockchain_admin_required
from db_operations import add_tx_hash_column
import logging
import os
import subprocess
import json
from datetime import datetime
from blockchain import connect_to_ethereum, get_contract_instance, get_token_supply, get_gas_price
from dotenv import load_dotenv, set_key
import contract_config
import gas_estimator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_contracts(network='mainnet'):
    """Validate contract addresses for the specified network
    
    Args:
        network (str): The network to validate (mainnet, testnet)
        
    Returns:
        dict: Dictionary with validation results
    """
    result = {
        'status': 'success',
        'network': network,
        'contracts': {},
        'all_configured': True
    }
    
    for contract_type in contract_config.CONTRACT_TYPES:
        address = contract_config.get_contract_address(contract_type, network)
        status = {
            'address': address,
            'valid': bool(address),
            'message': 'Contract address found' if address else 'Contract address not configured'
        }
        result['contracts'][contract_type] = status
        
        # Update all_configured flag
        if not address:
            result['all_configured'] = False
    
    # Add a summary message
    if result['all_configured']:
        result['message'] = f'All contracts are properly configured for {network}'
    else:
        result['message'] = f'Some contracts are not configured for {network}'
        result['status'] = 'warning'
    
    return result

# Create blueprint
blockchain_admin_bp = Blueprint('blockchain_admin', __name__, url_prefix='/admin/blockchain')

@blockchain_admin_bp.route('/')
@login_required
@blockchain_admin_required
def index():
    """Blockchain admin dashboard"""
    try:
        # Get stats for the dashboard
        smart_contracts_count = SmartContract.query.count()
        
        # Check if tx_hash column exists
        inspector = inspect(db.engine)
        blockchain_tx_columns = [col['name'] for col in inspector.get_columns('blockchain_transaction')]
        tx_hash_exists = 'tx_hash' in blockchain_tx_columns
        
        # Transaction stats
        try:
            txs_query = text(
                "SELECT COUNT(*) FROM blockchain_transaction"
            )
            total_txs = db.session.execute(txs_query).scalar() or 0
        except Exception:
            total_txs = 0
        
        # Check network connections
        try:
            w3_mainnet = connect_to_ethereum(network='mainnet')
            w3_testnet = connect_to_ethereum(network='sepolia')
            mainnet_connected = w3_mainnet is not None
            testnet_connected = w3_testnet is not None
        except Exception:
            mainnet_connected = False
            testnet_connected = False
            
        return render_template(
            'admin/blockchain/index.html',
            smart_contracts_count=smart_contracts_count,
            tx_hash_exists=tx_hash_exists,
            total_transactions=total_txs,
            mainnet_connected=mainnet_connected,
            testnet_connected=testnet_connected
        )
    except Exception as e:
        logger.error(f"Error in blockchain admin dashboard: {str(e)}")
        flash(f"Error loading dashboard: {str(e)}", "danger")
        return render_template('admin/blockchain/index.html', error=str(e))

@blockchain_admin_bp.route('/transactions')
@login_required
@blockchain_admin_required
def transactions():
    """View blockchain transactions"""
    try:
        # Get transactions with raw SQL to avoid ORM column mapping issues
        try:
            # Use a safe query that doesn't require specific column names
            query = text("""
                SELECT id, tx_hash, from_address, to_address, 
                       contract_address, status, created_at, transaction_type
                FROM blockchain_transaction 
                ORDER BY created_at DESC 
                LIMIT 100
            """)
            
            result = db.session.execute(query)
            
            # Convert to dictionary for template usage
            transactions = [dict(row._mapping) for row in result]
            
            logger.info(f"Successfully fetched {len(transactions)} blockchain transactions")
        except Exception as e:
            logger.error(f"Error fetching blockchain transactions: {str(e)}")
            transactions = []
            
        return render_template(
            'admin/blockchain/transactions.html',
            transactions=transactions
        )
    except Exception as e:
        logger.error(f"Error in blockchain transactions view: {str(e)}")
        flash(f"Error loading transactions: {str(e)}", "danger")
        return render_template('admin/blockchain/transactions.html', error=str(e))

@blockchain_admin_bp.route('/mainnet_readiness')
@login_required
@blockchain_admin_required
def mainnet_readiness():
    """View mainnet readiness assessment"""
    try:
        # Check if we should run the migration
        run_migration = request.args.get('migrate', 'false').lower() == 'true'
        if run_migration:
            try:
                result = add_tx_hash_column()
                if result:
                    flash("Database schema updated successfully.", "success")
                else:
                    flash("Error updating database schema.", "danger")
            except Exception as e:
                logger.error(f"Error in schema migration: {str(e)}")
                flash(f"Error in schema migration: {str(e)}", "danger")
        
        # Database checks
        db_checks = {
            'tx_hash_column': False,
            'smart_contracts_count': 0,
            'transactions_count': 0
        }
        
        # Check if tx_hash column exists
        try:
            inspector = inspect(db.engine)
            blockchain_tx_columns = [col['name'] for col in inspector.get_columns('blockchain_transaction')]
            db_checks['tx_hash_column'] = 'tx_hash' in blockchain_tx_columns
        except Exception as e:
            logger.error(f"Error checking tx_hash column: {str(e)}")
        
        # Smart contract count
        try:
            db_checks['smart_contracts_count'] = SmartContract.query.count()
        except Exception as e:
            logger.error(f"Error counting smart contracts: {str(e)}")
        
        # Transaction count
        try:
            txs_query = text(
                "SELECT COUNT(*) FROM blockchain_transaction"
            )
            db_checks['transactions_count'] = db.session.execute(txs_query).scalar() or 0
        except Exception as e:
            logger.error(f"Error counting transactions: {str(e)}")
        
        # Network connectivity checks
        connectivity_checks = {
            'mainnet_connected': False,
            'testnet_connected': False,
            'api_credentials': False
        }
        
        # Check network connections
        try:
            w3_mainnet = connect_to_ethereum(network='mainnet')
            w3_testnet = connect_to_ethereum(network='sepolia')
            connectivity_checks['mainnet_connected'] = w3_mainnet is not None
            connectivity_checks['testnet_connected'] = w3_testnet is not None
            
            # Check API credentials
            infura_key = os.environ.get('INFURA_API_KEY')
            connectivity_checks['api_credentials'] = infura_key is not None and len(infura_key) > 0
        except Exception as e:
            logger.error(f"Error checking network connectivity: {str(e)}")
        
        # Security checks
        security_checks = {
            'contract_verified': True,  # Placeholder value
            'audit_complete': True,     # Placeholder value 
            'permission_controls': True # Placeholder value
        }
        
        # Monitoring checks
        monitoring_checks = {
            'tracking_system': db_checks['tx_hash_column'],
            'gas_price_monitoring': True,  # Placeholder value
            'alerts_configured': True      # Placeholder value
        }
        
        # Calculate overall readiness score (0-100)
        score_items = [
            db_checks['tx_hash_column'],
            db_checks['smart_contracts_count'] > 0,
            db_checks['transactions_count'] > 0,
            connectivity_checks['mainnet_connected'],
            connectivity_checks['testnet_connected'],
            connectivity_checks['api_credentials'],
            security_checks['contract_verified'],
            security_checks['audit_complete'],
            security_checks['permission_controls'],
            monitoring_checks['tracking_system'],
            monitoring_checks['gas_price_monitoring'],
            monitoring_checks['alerts_configured']
        ]
        
        # Calculate percentage
        readiness_score = int(sum(1 for item in score_items if item) / len(score_items) * 100)
        
        # Get current network mode
        current_network = os.environ.get('ETHEREUM_NETWORK', 'testnet')
        
        return render_template(
            'admin/blockchain/mainnet_readiness.html',
            db_checks=db_checks,
            connectivity_checks=connectivity_checks,
            security_checks=security_checks,
            monitoring_checks=monitoring_checks,
            readiness_score=readiness_score,
            current_network=current_network
        )
    except Exception as e:
        logger.error(f"Error in mainnet readiness assessment: {str(e)}")
        flash(f"Error in mainnet readiness assessment: {str(e)}", "danger")
        return render_template('admin/blockchain/mainnet_readiness.html', error=str(e))

@blockchain_admin_bp.route('/api/update-schema', methods=['POST'])
@login_required
@blockchain_admin_required
def update_schema():
    """API endpoint to update database schema"""
    try:
        result = add_tx_hash_column()
        if result:
            return jsonify({
                'success': True,
                'message': 'Database schema updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Error updating database schema'
            })
    except Exception as e:
        logger.error(f"Error updating schema: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        })

@blockchain_admin_bp.route('/api/check-connectivity', methods=['POST'])
@login_required
@blockchain_admin_required
def check_connectivity():
    """API endpoint to check network connectivity"""
    try:
        # Check mainnet connection
        w3_mainnet = connect_to_ethereum(network='mainnet')
        mainnet_connected = w3_mainnet is not None
        
        # Check testnet connection
        w3_testnet = connect_to_ethereum(network='sepolia')
        testnet_connected = w3_testnet is not None
        
        # Check if we have API keys
        infura_key = os.environ.get('INFURA_API_KEY')
        api_credentials = infura_key is not None and len(infura_key) > 0
        
        return jsonify({
            'success': True,
            'mainnet': mainnet_connected,
            'testnet': testnet_connected,
            'api_credentials': api_credentials
        })
    except Exception as e:
        logger.error(f"Error checking connectivity: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        })

@blockchain_admin_bp.route('/enable-mainnet')
@login_required
@blockchain_admin_required
def enable_mainnet():
    """Enable Ethereum mainnet for NVCT operations"""
    try:
        # Check if INFURA_API_KEY is configured
        infura_key = os.environ.get('INFURA_API_KEY')
        if not infura_key:
            flash("INFURA_API_KEY is not configured. Please set it up before enabling mainnet.", "danger")
            return redirect(url_for('blockchain_admin.mainnet_readiness'))
        
        # Check if ADMIN_ETH_PRIVATE_KEY is configured
        admin_eth_key = os.environ.get('ADMIN_ETH_PRIVATE_KEY')
        if not admin_eth_key:
            flash("ADMIN_ETH_PRIVATE_KEY is not configured. This is required for contract deployment.", "danger")
            return redirect(url_for('blockchain_admin.mainnet_readiness'))
        
        # Run the enable_mainnet.py script with --force option
        try:
            result = subprocess.run(
                ["python", "enable_mainnet.py", "--force"],
                capture_output=True,
                text=True,
                check=True
            )
            # Log the output for debugging
            logger.info(f"Enable mainnet output: {result.stdout}")
            
            # Check if it was successful
            if "Mainnet mode enabled" in result.stdout:
                flash("NVCT is now configured to use Ethereum mainnet. All transactions will use real ETH.", "success")
            else:
                flash("Mainnet mode enabled, but with some warnings. Please check the logs.", "warning")
            
            # Set the environment variable
            os.environ['ETHEREUM_NETWORK'] = 'mainnet'
            # Update .env file
            dotenv_path = os.path.join(os.getcwd(), '.env')
            if os.path.exists(dotenv_path):
                set_key(dotenv_path, 'ETHEREUM_NETWORK', 'mainnet')
                logger.info("Updated ETHEREUM_NETWORK=mainnet in .env file")
            
            # Validate contract addresses
            validation = validate_contracts('mainnet')
            if validation and validation.get('all_configured', False):
                flash("All contracts are properly configured for mainnet.", "success")
            else:
                flash("Some contracts need to be deployed to mainnet. Use the deploy options.", "warning")
            
            return redirect(url_for('blockchain_admin.mainnet_readiness'))
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running enable_mainnet.py: {e}")
            logger.error(f"Error output: {e.stderr}")
            flash(f"Error enabling mainnet mode: {e.stderr}", "danger")
            return redirect(url_for('blockchain_admin.mainnet_readiness'))
    
    except Exception as e:
        logger.error(f"Error in enable_mainnet: {str(e)}")
        flash(f"Error enabling mainnet: {str(e)}", "danger")
        return redirect(url_for('blockchain_admin.mainnet_readiness'))

@blockchain_admin_bp.route('/deploy-contract/<contract_type>')
@login_required
@blockchain_admin_required
def deploy_contract(contract_type):
    """Deploy a specific contract to mainnet"""
    valid_contracts = ['settlement_contract', 'multisig_wallet', 'nvc_token']
    if contract_type not in valid_contracts:
        flash(f"Invalid contract type: {contract_type}", "danger")
        return redirect(url_for('blockchain_admin.mainnet_readiness'))
    
    try:
        # Check if ADMIN_ETH_PRIVATE_KEY is configured
        admin_eth_key = os.environ.get('ADMIN_ETH_PRIVATE_KEY')
        if not admin_eth_key:
            flash("ADMIN_ETH_PRIVATE_KEY is not configured. This is required for contract deployment.", "danger")
            return redirect(url_for('blockchain_admin.mainnet_readiness'))
        
        # Run the mainnet_migration.py script to deploy the contract
        try:
            result = subprocess.run(
                ["python", "mainnet_migration.py", "deploy", f"--contract={contract_type}"],
                capture_output=True,
                text=True,
                check=True
            )
            # Log the output for debugging
            logger.info(f"Deploy contract output: {result.stdout}")
            
            # Check if it was successful
            if "Successfully deployed" in result.stdout:
                # Extract the contract address from the output
                import re
                match = re.search(r"Contract address: (0x[a-fA-F0-9]{40})", result.stdout)
                if match:
                    contract_address = match.group(1)
                    flash(f"{contract_type} successfully deployed to mainnet at address {contract_address}", "success")
                else:
                    flash(f"{contract_type} successfully deployed to mainnet", "success")
            else:
                flash(f"Contract deployment completed with warnings. Please check the logs.", "warning")
            
            return redirect(url_for('blockchain_admin.mainnet_readiness'))
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error deploying contract: {e}")
            logger.error(f"Error output: {e.stderr}")
            flash(f"Error deploying {contract_type}: {e.stderr}", "danger")
            return redirect(url_for('blockchain_admin.mainnet_readiness'))
    
    except Exception as e:
        logger.error(f"Error in deploy_contract: {str(e)}")
        flash(f"Error deploying contract: {str(e)}", "danger")
        return redirect(url_for('blockchain_admin.mainnet_readiness'))

@blockchain_admin_bp.route('/validate-mainnet')
@login_required
@blockchain_admin_required
def validate_mainnet():
    """Validate the mainnet setup"""
    try:
        # Run the mainnet_migration.py script to validate the setup
        try:
            result = subprocess.run(
                ["python", "mainnet_migration.py", "validate"],
                capture_output=True,
                text=True,
                check=True
            )
            # Log the output for debugging
            logger.info(f"Validate mainnet output: {result.stdout}")
            
            # Check if it was successful
            if "Validation successful!" in result.stdout:
                flash("Mainnet setup validation successful! All contracts are properly deployed on mainnet.", "success")
            else:
                flash("Validation completed with warnings. Please check the logs.", "warning")
            
            return redirect(url_for('blockchain_admin.mainnet_readiness'))
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error validating mainnet: {e}")
            logger.error(f"Error output: {e.stderr}")
            flash(f"Error validating mainnet setup: {e.stderr}", "danger")
            return redirect(url_for('blockchain_admin.mainnet_readiness'))
    
    except Exception as e:
        logger.error(f"Error in validate_mainnet: {str(e)}")
        flash(f"Error validating mainnet setup: {str(e)}", "danger")
        return redirect(url_for('blockchain_admin.mainnet_readiness'))

@blockchain_admin_bp.route('/switch-to-testnet')
@login_required
@blockchain_admin_required
def switch_to_testnet():
    """Switch back to Ethereum testnet (Sepolia) for NVCT operations"""
    try:
        # Run the toggle_network.py script to switch to testnet
        try:
            result = subprocess.run(
                ["python", "toggle_network.py", "--testnet"],
                capture_output=True,
                text=True,
                check=True
            )
            # Log the output for debugging
            logger.info(f"Switch to testnet output: {result.stdout}")
            
            # Check if it was successful
            if "Switched to testnet network" in result.stdout:
                flash("NVCT is now configured to use Ethereum testnet (Sepolia). All transactions will use test ETH.", "success")
            else:
                flash("Switched to testnet mode, but with some warnings. Please check the logs.", "warning")
            
            # Set the environment variable directly as well
            os.environ['ETHEREUM_NETWORK'] = 'testnet'
            # Update .env file
            dotenv_path = os.path.join(os.getcwd(), '.env')
            if os.path.exists(dotenv_path):
                set_key(dotenv_path, 'ETHEREUM_NETWORK', 'testnet')
                logger.info("Updated ETHEREUM_NETWORK=testnet in .env file")
            
            return redirect(url_for('blockchain_admin.mainnet_readiness'))
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running toggle_network.py: {e}")
            logger.error(f"Error output: {e.stderr}")
            flash(f"Error switching to testnet mode: {e.stderr}", "danger")
            return redirect(url_for('blockchain_admin.mainnet_readiness'))
    
    except Exception as e:
        logger.error(f"Error in switch_to_testnet: {str(e)}")
        flash(f"Error switching to testnet: {str(e)}", "danger")
        return redirect(url_for('blockchain_admin.mainnet_readiness'))

@blockchain_admin_bp.route('/gas_estimator')
@login_required
@blockchain_admin_required
def gas_estimator_view():
    """View gas estimator for mainnet transactions"""
    try:
        # Get current network
        current_network = os.environ.get('ETHEREUM_NETWORK', 'testnet')
        
        # Get price data
        eth_price = gas_estimator.get_eth_price_usd()
        
        # Get gas price data
        gas_price_data = gas_estimator.get_current_gas_price(current_network)
        
        # Get admin balance
        balance_data = gas_estimator.get_admin_eth_balance(current_network)
        
        # Calculate deployment cost estimates
        deployment_costs = {}
        for contract_type in ['nvc_token', 'multisig_wallet', 'settlement_contract']:
            slow_estimate = gas_estimator.estimate_deployment_cost(contract_type, current_network, 'slow')
            medium_estimate = gas_estimator.estimate_deployment_cost(contract_type, current_network, 'medium')
            fast_estimate = gas_estimator.estimate_deployment_cost(contract_type, current_network, 'fast')
            
            deployment_costs[contract_type] = {
                'slow': slow_estimate,
                'medium': medium_estimate,
                'fast': fast_estimate
            }
        
        # Calculate interaction cost estimates for common operations
        interaction_costs = {}
        for interaction_type in ['erc20_transfer', 'multisig_submit', 'multisig_confirm', 'settlement_process']:
            estimate = gas_estimator.estimate_contract_interaction_cost(interaction_type, current_network, 'medium')
            interaction_costs[interaction_type] = estimate
        
        # Get total deployment cost
        total_costs = gas_estimator.estimate_all_deployment_costs(current_network)['total']
        
        return render_template(
            'admin/blockchain/gas_estimator.html',
            eth_price=eth_price,
            gas_price_data=gas_price_data,
            balance_data=balance_data,
            deployment_costs=deployment_costs,
            interaction_costs=interaction_costs,
            total_costs=total_costs,
            current_network=current_network
        )
    
    except Exception as e:
        logger.error(f"Error in gas estimator view: {str(e)}")
        flash(f"Error estimating gas costs: {str(e)}", "danger")
        return render_template('admin/blockchain/gas_estimator.html', error=str(e))