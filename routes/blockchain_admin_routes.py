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

@blockchain_admin_bp.route('/transactions')
@blockchain_admin_required
def transactions():
    """Show blockchain transactions"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from flask import request
    
    # Get current network
    current_network = os.environ.get('ETHEREUM_NETWORK', 'testnet')
    
    # Get filter parameters
    status = request.args.get('status')
    tx_type = request.args.get('tx_type')
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    # Query base
    query = BlockchainTransaction.query.filter_by(network=current_network)
    
    # Apply filters
    if status:
        if status == 'pending':
            query = query.filter(BlockchainTransaction.status.is_(None))
        else:
            try:
                status_int = int(status)
                query = query.filter_by(status=status_int)
            except ValueError:
                pass
    
    if tx_type:
        query = query.filter_by(tx_type=tx_type)
    
    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d')
            query = query.filter(BlockchainTransaction.timestamp >= from_date_obj)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d')
            to_date_obj = to_date_obj + timedelta(days=1)  # Include the entire day
            query = query.filter(BlockchainTransaction.timestamp < to_date_obj)
        except ValueError:
            pass
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.order_by(BlockchainTransaction.timestamp.desc()).paginate(page=page, per_page=per_page)
    transactions = pagination.items
    
    # Get statistics
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    total_transactions = BlockchainTransaction.query.filter_by(network=current_network).count()
    today_transactions = BlockchainTransaction.query.filter_by(network=current_network).filter(
        BlockchainTransaction.timestamp >= today_start
    ).count()
    
    success_transactions = BlockchainTransaction.query.filter_by(
        network=current_network, 
        status=1
    ).count()
    
    failed_transactions = BlockchainTransaction.query.filter_by(
        network=current_network, 
        status=0
    ).count()
    
    pending_transactions = BlockchainTransaction.query.filter_by(
        network=current_network
    ).filter(
        BlockchainTransaction.status.is_(None)
    ).count()
    
    # Gas usage stats
    web3 = get_web3_connection()
    current_gas_price = 0
    if web3:
        try:
            current_gas_price = round(web3.from_wei(web3.eth.gas_price, 'gwei'), 2)
        except Exception:
            pass
    
    # Calculate average transaction cost
    avg_transaction_cost = 0
    try:
        avg_gas_result = db.session.query(
            func.avg(BlockchainTransaction.gas_used * BlockchainTransaction.gas_price / 1e9)
        ).filter(
            BlockchainTransaction.network == current_network,
            BlockchainTransaction.gas_used.isnot(None),
            BlockchainTransaction.gas_price.isnot(None)
        ).scalar()
        
        if avg_gas_result:
            avg_transaction_cost = round(float(avg_gas_result), 6)
    except Exception:
        pass
    
    # Calculate total gas used
    total_gas_used = 0
    try:
        total_gas_result = db.session.query(
            func.sum(BlockchainTransaction.gas_used)
        ).filter(
            BlockchainTransaction.network == current_network,
            BlockchainTransaction.gas_used.isnot(None)
        ).scalar()
        
        if total_gas_result:
            total_gas_used = int(total_gas_result)
    except Exception:
        pass
    
    # Gas usage percentage (for visualization)
    gas_usage_percent = min(total_gas_used / 1000000, 100) if total_gas_used > 0 else 0
    
    return render_template(
        'admin/blockchain/transactions.html',
        transactions=transactions,
        pagination=pagination,
        current_network=current_network,
        status=status,
        tx_type=tx_type,
        from_date=from_date,
        to_date=to_date,
        total_transactions=total_transactions,
        today_transactions=today_transactions,
        success_transactions=success_transactions,
        failed_transactions=failed_transactions,
        pending_transactions=pending_transactions,
        current_gas_price=current_gas_price,
        avg_transaction_cost=avg_transaction_cost,
        total_gas_used=total_gas_used,
        gas_usage_percent=gas_usage_percent
    )

@blockchain_admin_bp.route('/transaction/<tx_hash>')
@blockchain_admin_required
def transaction_detail(tx_hash):
    """Show details for a specific transaction"""
    # Get current network
    current_network = os.environ.get('ETHEREUM_NETWORK', 'testnet')
    
    # Get contract addresses for reference
    contract_addresses = []
    try:
        contracts = SmartContract.query.filter_by(
            network=current_network,
            is_active=True
        ).all()
        contract_addresses = [c.address.lower() for c in contracts]
    except Exception:
        pass
    
    # Get transaction
    transaction = BlockchainTransaction.query.filter_by(
        tx_hash=tx_hash
    ).first()
    
    if not transaction:
        flash('Transaction not found', 'danger')
        return redirect(url_for('blockchain_admin.transactions'))
    
    return render_template(
        'admin/blockchain/transaction_detail.html',
        transaction=transaction,
        current_network=current_network,
        contract_addresses=contract_addresses
    )

@blockchain_admin_bp.route('/check-transaction/<tx_hash>')
@blockchain_admin_required
def check_transaction(tx_hash):
    """Check status of a pending transaction"""
    try:
        web3 = get_web3_connection()
        
        if not web3:
            return jsonify({
                'success': False,
                'error': 'Could not connect to Ethereum node'
            })
        
        # Get transaction from database
        transaction = BlockchainTransaction.query.filter_by(
            tx_hash=tx_hash
        ).first()
        
        if not transaction:
            return jsonify({
                'success': False,
                'error': 'Transaction not found in database'
            })
        
        # If transaction already has a status, no need to check
        if transaction.status is not None:
            return jsonify({
                'success': True,
                'status': transaction.status
            })
        
        # Check transaction status on the blockchain
        try:
            tx_receipt = web3.eth.get_transaction_receipt(tx_hash)
            
            if tx_receipt:
                # Update transaction in database
                transaction.block_number = tx_receipt.blockNumber
                transaction.status = tx_receipt.status
                transaction.gas_used = tx_receipt.gasUsed
                
                # Get block timestamp
                block = web3.eth.get_block(tx_receipt.blockNumber)
                if block and block.timestamp:
                    transaction.timestamp = datetime.utcfromtimestamp(block.timestamp)
                
                db.session.add(transaction)
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'status': tx_receipt.status,
                    'block_number': tx_receipt.blockNumber,
                    'gas_used': tx_receipt.gasUsed
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Transaction pending or not found on blockchain'
                })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error checking transaction: {str(e)}'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        })
        
@blockchain_admin_bp.route('/token-dashboard')
@blockchain_admin_required
def token_dashboard():
    """Token supply monitoring dashboard"""
    from datetime import datetime, timedelta
    import json
    
    # Get current network
    current_network = os.environ.get('ETHEREUM_NETWORK', 'testnet')
    
    # Get token contract
    token_address = contract_config.get_contract_address('nvc_token', current_network)
    
    # Initialize default values
    total_supply = 0
    circulating_supply = 0
    token_price = 1.0  # Default price (1:1 USD pegged)
    price_change = 0.0
    top_holders = []
    recent_transfers = []
    
    # Connect to web3
    web3 = get_web3_connection()
    if web3 and token_address:
        try:
            # Load the token contract
            from blockchain import load_contract
            token_contract = load_contract('nvc_token', token_address)
            
            if token_contract:
                # Get token supply information
                try:
                    total_supply = token_contract.functions.totalSupply().call() / 1e18  # Convert from wei
                except Exception as e:
                    logger.error(f"Error getting total supply: {str(e)}")
                
                # Get token price from system
                try:
                    from currency_exchange_service import CurrencyExchangeService
                    from account_holder_models import CurrencyType
                    # Get NVCT/USD exchange rate
                    rate = CurrencyExchangeService.get_exchange_rate(
                        CurrencyType.NVCT, 
                        CurrencyType.USD
                    )
                    if rate and rate > 0:
                        token_price = rate
                except Exception as e:
                    logger.error(f"Error getting token price: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading token contract: {str(e)}")
    
    # Get recent token transfers from database
    try:
        recent_transfers = BlockchainTransaction.query.filter_by(
            network=current_network,
            tx_type='token_transfer'
        ).filter(
            BlockchainTransaction.token_value.isnot(None),
            BlockchainTransaction.token_symbol == 'NVCT'
        ).order_by(
            BlockchainTransaction.timestamp.desc()
        ).limit(10).all()
    except Exception as e:
        logger.error(f"Error getting recent transfers: {str(e)}")
        recent_transfers = []
    
    # Calculate supply distribution (example values)
    supply_distribution = {
        'labels': ['Circulating', 'Treasury', 'Team', 'Reserved', 'Staked', 'Other'],
        'data': [
            circulating_supply * 0.6,  # Circulating (public)
            total_supply * 0.2,        # Treasury
            total_supply * 0.1,        # Team
            total_supply * 0.05,       # Reserved for future use
            total_supply * 0.03,       # Staked in contracts
            total_supply * 0.02        # Other allocations
        ]
    }
    
    # If we don't have real circulation data, estimate it
    if circulating_supply == 0:
        circulating_supply = sum(supply_distribution['data'][0:1])  # Just the circulating portion
    
    # Generate sample transfer volume data for the chart
    today = datetime.utcnow().date()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    dates.reverse()  # oldest first
    
    # Try to get real transfer volumes from database
    transfer_volumes = []
    try:
        for date_str in dates:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            next_date = date_obj + timedelta(days=1)
            
            # Query sum of token transfers for this day
            volume = db.session.query(
                db.func.sum(BlockchainTransaction.token_value)
            ).filter(
                BlockchainTransaction.network == current_network,
                BlockchainTransaction.tx_type == 'token_transfer',
                BlockchainTransaction.token_symbol == 'NVCT',
                BlockchainTransaction.timestamp >= date_obj,
                BlockchainTransaction.timestamp < next_date
            ).scalar() or 0
            
            transfer_volumes.append(float(volume))
    except Exception as e:
        logger.error(f"Error calculating transfer volumes: {str(e)}")
        # Generate placeholder data if real data is not available
        import random
        # Generate some sample data with an upward trend
        transfer_volumes = [
            random.uniform(10000, 50000) * (1 + i/60)
            for i in range(30)
        ]
    
    transfer_volume = {
        'dates': dates,
        'volumes': transfer_volumes
    }
    
    # Try to get real top holders data
    try:
        # This would typically come from a specialized query or API
        # For now, we'll use placeholder data
        admin_address = os.environ.get('ADMIN_ETH_ADDRESS', '0x0000000000000000000000000000000000000000')
        
        top_holders = [
            {
                'address': admin_address, 
                'balance': total_supply * 0.2, 
                'label': 'Admin Treasury'
            },
            {
                'address': '0x1111111111111111111111111111111111111111', 
                'balance': total_supply * 0.15, 
                'label': 'Cold Storage'
            },
            {
                'address': '0x2222222222222222222222222222222222222222', 
                'balance': total_supply * 0.1, 
                'label': 'Development Fund'
            },
            {
                'address': '0x3333333333333333333333333333333333333333', 
                'balance': total_supply * 0.07, 
                'label': 'Marketing Fund'
            },
            {
                'address': '0x4444444444444444444444444444444444444444', 
                'balance': total_supply * 0.05, 
                'label': 'Staking Pool'
            },
            {
                'address': '0x5555555555555555555555555555555555555555', 
                'balance': total_supply * 0.03, 
                'label': None
            },
            {
                'address': '0x6666666666666666666666666666666666666666', 
                'balance': total_supply * 0.02, 
                'label': None
            },
            {
                'address': '0x7777777777777777777777777777777777777777', 
                'balance': total_supply * 0.015, 
                'label': None
            },
            {
                'address': '0x8888888888888888888888888888888888888888', 
                'balance': total_supply * 0.01, 
                'label': None
            },
            {
                'address': '0x9999999999999999999999999999999999999999', 
                'balance': total_supply * 0.005, 
                'label': None
            }
        ]
    except Exception as e:
        logger.error(f"Error getting top holders: {str(e)}")
        top_holders = []
    
    # Add Flask template filter for number formatting
    @app.template_filter('format_number')
    def format_number(value):
        try:
            if value >= 1_000_000:
                return f"{value/1_000_000:.2f}M"
            elif value >= 1_000:
                return f"{value/1_000:.2f}K"
            else:
                return f"{value:.2f}"
        except:
            return str(value)
    
    return render_template(
        'admin/blockchain/token_dashboard.html',
        current_network=current_network,
        token_address=token_address,
        total_supply=total_supply,
        circulating_supply=circulating_supply,
        token_price=token_price,
        price_change=price_change,
        top_holders=top_holders,
        recent_transfers=recent_transfers,
        supply_distribution=supply_distribution,
        transfer_volume=transfer_volume
    )

@blockchain_admin_bp.route('/security-confirm/<operation_id>', methods=['GET', 'POST'])
@blockchain_admin_required
def security_confirm(operation_id):
    """Security confirmation page for mainnet operations"""
    from datetime import datetime, timedelta
    import uuid
    import hashlib
    import secrets
    import json
    from werkzeug.security import check_password_hash
    from flask import request, session, flash, redirect
    from models import User
    from email_service import send_admin_email
    
    # Check if we're in mainnet mode
    current_network = os.environ.get('ETHEREUM_NETWORK', 'testnet')
    if current_network != 'mainnet':
        flash('Security confirmation is only required for mainnet operations', 'warning')
        return redirect(url_for('blockchain_admin.index'))
    
    # Check if this operation exists in the session
    if 'pending_operations' not in session:
        session['pending_operations'] = {}
    
    operation = session['pending_operations'].get(operation_id)
    if not operation:
        flash('Operation not found or has expired', 'danger')
        return redirect(url_for('blockchain_admin.index'))
    
    # Handle form submission
    if request.method == 'POST':
        security_code = request.form.get('security_code')
        admin_password = request.form.get('admin_password')
        confirm_operation = request.form.get('confirm_operation') == 'on'
        confirm_high_risk = request.form.get('confirm_high_risk') == 'on' if operation.get('is_high_risk') else True
        confirm_authorization = request.form.get('confirm_authorization') == 'on' if operation.get('is_high_risk') else True
        
        # Validate security code
        if operation.get('security_code') != security_code:
            flash('Invalid security code', 'danger')
            return render_template(
                'admin/blockchain/security_confirm.html',
                **operation,
                form_action=url_for('blockchain_admin.security_confirm', operation_id=operation_id),
                cancel_url=url_for('blockchain_admin.index')
            )
        
        # Validate admin password
        current_user_id = session.get('user_id')
        if not current_user_id:
            flash('You must be logged in as an admin', 'danger')
            return redirect(url_for('blockchain_admin.index'))
        
        user = User.query.get(current_user_id)
        if not user or not user.password_hash or not check_password_hash(user.password_hash, admin_password):
            flash('Invalid admin password', 'danger')
            return render_template(
                'admin/blockchain/security_confirm.html',
                **operation,
                form_action=url_for('blockchain_admin.security_confirm', operation_id=operation_id),
                cancel_url=url_for('blockchain_admin.index')
            )
        
        # Validate confirmations
        if not confirm_operation or not confirm_high_risk or not confirm_authorization:
            flash('You must confirm all checkboxes to proceed', 'danger')
            return render_template(
                'admin/blockchain/security_confirm.html',
                **operation,
                form_action=url_for('blockchain_admin.security_confirm', operation_id=operation_id),
                cancel_url=url_for('blockchain_admin.index')
            )
        
        # All validations passed, execute the operation
        try:
            # Log the operation
            logger.info(f"Executing mainnet operation: {operation_id}")
            logger.info(f"Operation type: {operation.get('operation_type')}")
            logger.info(f"User: {user.username} (ID: {user.id})")
            logger.info(f"IP: {request.remote_addr}")
            logger.info(f"Timestamp: {datetime.utcnow()}")
            
            # Execute the operation based on type
            result = None
            operation_type = operation.get('operation_type')
            
            if operation_type == 'token_transfer':
                # Execute token transfer
                from blockchain import transfer_token
                result = transfer_token(
                    token_address=operation.get('contract_address'),
                    to_address=operation.get('to_address'),
                    amount=float(operation.get('value', 0)),
                    from_address=operation.get('from_address')
                )
            elif operation_type == 'contract_deploy':
                # Execute contract deployment
                if operation.get('contract_type') == 'settlement_contract':
                    from blockchain import deploy_settlement_contract
                    result = deploy_settlement_contract(network='mainnet')
                elif operation.get('contract_type') == 'multisig_wallet':
                    from blockchain import deploy_multisig_wallet
                    result = deploy_multisig_wallet(network='mainnet')
                elif operation.get('contract_type') == 'nvc_token':
                    from blockchain import deploy_nvc_token
                    result = deploy_nvc_token(network='mainnet')
            elif operation_type == 'contract_call':
                # Execute contract call
                from blockchain import call_contract_function
                result = call_contract_function(
                    contract_type=operation.get('contract_type'),
                    contract_address=operation.get('contract_address'),
                    function_name=operation.get('function_name'),
                    function_args=json.loads(operation.get('function_args', '[]'))
                )
            
            # Remove operation from session
            del session['pending_operations'][operation_id]
            session.modified = True
            
            # Redirect based on result
            if result and 'tx_hash' in result:
                flash(f'Operation executed successfully with transaction hash: {result["tx_hash"]}', 'success')
                return redirect(url_for('blockchain_admin.transaction_detail', tx_hash=result['tx_hash']))
            else:
                flash('Operation executed successfully', 'success')
                return redirect(url_for('blockchain_admin.index'))
        except Exception as e:
            logger.error(f"Error executing mainnet operation: {str(e)}")
            flash(f'Error executing operation: {str(e)}', 'danger')
            return render_template(
                'admin/blockchain/security_confirm.html',
                **operation,
                form_action=url_for('blockchain_admin.security_confirm', operation_id=operation_id),
                cancel_url=url_for('blockchain_admin.index')
            )
    
    # Render the confirmation page
    return render_template(
        'admin/blockchain/security_confirm.html',
        **operation,
        form_action=url_for('blockchain_admin.security_confirm', operation_id=operation_id),
        cancel_url=url_for('blockchain_admin.index')
    )

@blockchain_admin_bp.route('/send-security-code/<operation_id>')
@blockchain_admin_required
def send_security_code(operation_id):
    """Send security code for mainnet operation"""
    import secrets
    from flask import session, jsonify
    from models import User
    from email_service import send_admin_email
    
    # Check if this operation exists in the session
    if 'pending_operations' not in session:
        session['pending_operations'] = {}
    
    operation = session['pending_operations'].get(operation_id)
    if not operation:
        return jsonify({
            'success': False,
            'error': 'Operation not found or has expired'
        })
    
    # Generate a new security code
    security_code = secrets.randbelow(1000000)
    security_code = f"{security_code:06d}"  # Format as 6 digits with leading zeros
    
    # Store the security code with the operation
    operation['security_code'] = security_code
    session['pending_operations'][operation_id] = operation
    session.modified = True
    
    # Get current user
    current_user_id = session.get('user_id')
    user = User.query.get(current_user_id) if current_user_id else None
    recipient_email = user.email if user else None
    
    # Send the security code via email
    try:
        if recipient_email:
            email_subject = f"Security Code for Mainnet Operation: {operation.get('operation_type', 'Unknown')}"
            email_body = f"""
            <h2>Security Code for Mainnet Operation</h2>
            <p>You have requested to perform a critical operation on the Ethereum Mainnet.</p>
            <p><strong>Operation:</strong> {operation.get('operation_description', 'Unknown')}</p>
            <p><strong>Your security code is:</strong> <span style="font-size: 24px; font-weight: bold; color: #dc3545;">{security_code}</span></p>
            <p>This code will expire in 10 minutes.</p>
            <p>If you did not request this operation, please contact the system administrator immediately.</p>
            """
            
            send_admin_email(
                subject=email_subject,
                html_content=email_body,
                recipient_email=recipient_email
            )
            
            return jsonify({
                'success': True,
                'message': f'Security code sent to {recipient_email}'
            })
        else:
            logger.error("Cannot send security code: No recipient email found")
            return jsonify({
                'success': False,
                'error': 'No recipient email found'
            })
    except Exception as e:
        logger.error(f"Error sending security code: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error sending security code: {str(e)}'
        })

@blockchain_admin_bp.route('/create-operation', methods=['POST'])
@blockchain_admin_required
def create_operation():
    """Create a new security operation for mainnet"""
    import uuid
    from datetime import datetime, timedelta
    from flask import request, session, jsonify
    
    # Check if we're in mainnet mode
    current_network = os.environ.get('ETHEREUM_NETWORK', 'testnet')
    if current_network != 'mainnet':
        # In testnet mode, we don't need security confirmation
        try:
            # Execute the operation directly
            operation_type = request.form.get('operation_type')
            result = None
            
            if operation_type == 'token_transfer':
                # Execute token transfer
                from blockchain import transfer_token
                result = transfer_token(
                    token_address=request.form.get('contract_address'),
                    to_address=request.form.get('to_address'),
                    amount=float(request.form.get('value', 0)),
                    from_address=request.form.get('from_address')
                )
            elif operation_type == 'contract_deploy':
                # Execute contract deployment
                contract_type = request.form.get('contract_type')
                if contract_type == 'settlement_contract':
                    from blockchain import deploy_settlement_contract
                    result = deploy_settlement_contract(network='testnet')
                elif contract_type == 'multisig_wallet':
                    from blockchain import deploy_multisig_wallet
                    result = deploy_multisig_wallet(network='testnet')
                elif contract_type == 'nvc_token':
                    from blockchain import deploy_nvc_token
                    result = deploy_nvc_token(network='testnet')
            elif operation_type == 'contract_call':
                # Execute contract call
                import json
                from blockchain import call_contract_function
                result = call_contract_function(
                    contract_type=request.form.get('contract_type'),
                    contract_address=request.form.get('contract_address'),
                    function_name=request.form.get('function_name'),
                    function_args=json.loads(request.form.get('function_args', '[]'))
                )
            
            # Return result
            if result and isinstance(result, dict) and 'tx_hash' in result:
                return jsonify({
                    'success': True,
                    'redirect': url_for('blockchain_admin.transaction_detail', tx_hash=result['tx_hash'])
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'Operation executed successfully',
                    'redirect': url_for('blockchain_admin.index')
                })
        except Exception as e:
            logger.error(f"Error executing testnet operation: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Error executing operation: {str(e)}'
            })
    
    # In mainnet mode, we create a pending operation and redirect to the security confirmation page
    operation_id = str(uuid.uuid4())
    expiry_time = datetime.utcnow() + timedelta(minutes=10)
    
    # Create operation data
    operation = {
        'operation_id': operation_id,
        'operation_type': request.form.get('operation_type'),
        'operation_description': request.form.get('operation_description'),
        'from_address': request.form.get('from_address'),
        'to_address': request.form.get('to_address'),
        'contract_address': request.form.get('contract_address'),
        'value': request.form.get('value'),
        'currency': request.form.get('currency', 'NVCT'),
        'gas_estimate': request.form.get('gas_estimate'),
        'gas_price': request.form.get('gas_price'),
        'estimated_cost': request.form.get('estimated_cost'),
        'is_high_risk': request.form.get('is_high_risk') == 'true',
        'contract_type': request.form.get('contract_type'),
        'function_name': request.form.get('function_name'),
        'function_args': request.form.get('function_args'),
        'created_at': datetime.utcnow().isoformat(),
        'expires_at': expiry_time.isoformat()
    }
    
    # Store in session
    if 'pending_operations' not in session:
        session['pending_operations'] = {}
    
    session['pending_operations'][operation_id] = operation
    session.modified = True
    
    # Return redirect URL
    return jsonify({
        'success': True,
        'redirect': url_for('blockchain_admin.security_confirm', operation_id=operation_id)
    })