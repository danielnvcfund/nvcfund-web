import os
import time
import json
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request
from sqlalchemy import text

from app import db
from blockchain import init_web3, get_web3

# Create a Blueprint for status routes
status_bp = Blueprint('status', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

# Blockchain status endpoint
@status_bp.route('/blockchain/status', methods=['GET'])
def blockchain_status():
    """Get the status of the blockchain connection"""
    try:
        web3 = get_web3()
        if web3 and web3.isConnected():
            # Get blockchain details
            try:
                network_id = web3.net.version
                node_info = web3.clientVersion
                latest_block = web3.eth.block_number
                # Calculate block time
                block_time = None
                if latest_block > 0:
                    current_block = web3.eth.get_block(latest_block)
                    previous_block = web3.eth.get_block(latest_block - 1)
                    block_time = current_block.timestamp - previous_block.timestamp
                
                return jsonify({
                    'status': 'ok',
                    'message': 'Blockchain connection established',
                    'details': {
                        'network_id': network_id,
                        'node_info': node_info,
                        'latest_block': latest_block,
                        'block_time': block_time,
                    },
                    'lastChecked': datetime.utcnow().isoformat()
                })
            except Exception as e:
                # Connected but can't get details
                logger.warning(f"Connected to blockchain but encountered an error: {str(e)}")
                return jsonify({
                    'status': 'warning',
                    'message': f'Connected to blockchain but encountered an error: {str(e)}',
                    'lastChecked': datetime.utcnow().isoformat()
                })
        else:
            # Not connected
            return jsonify({
                'status': 'error',
                'message': 'Unable to connect to blockchain',
                'lastChecked': datetime.utcnow().isoformat()
            })
    except Exception as e:
        logger.error(f"Error checking blockchain status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error checking blockchain status: {str(e)}',
            'lastChecked': datetime.utcnow().isoformat()
        })

# Payment gateway status endpoint
@status_bp.route('/payments/gateways/status', methods=['GET'])
def payment_gateways_status():
    """Get the status of all configured payment gateways"""
    try:
        from models import PaymentGateway
        from payment_gateways import check_gateway_status
        
        gateways = PaymentGateway.query.filter_by(is_active=True).all()
        if not gateways:
            return jsonify({
                'status': 'warning',
                'message': 'No active payment gateways configured',
                'gateways': [],
                'lastChecked': datetime.utcnow().isoformat()
            })
        
        gateway_statuses = []
        overall_status = 'ok'
        
        for gateway in gateways:
            status, message = check_gateway_status(gateway)
            gateway_status = {
                'name': gateway.name,
                'type': gateway.gateway_type.value if gateway.gateway_type else 'unknown',
                'status': status,
                'message': message
            }
            gateway_statuses.append(gateway_status)
            
            # Update overall status (ok > warning > error)
            if status == 'error' and overall_status != 'error':
                overall_status = 'error'
            elif status == 'warning' and overall_status == 'ok':
                overall_status = 'warning'
        
        return jsonify({
            'status': overall_status,
            'message': f'{len(gateways)} payment gateways checked',
            'details': {
                'gateways': gateway_statuses,
                'active_count': len(gateways)
            },
            'lastChecked': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error checking payment gateway status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error checking payment gateway status: {str(e)}',
            'lastChecked': datetime.utcnow().isoformat()
        })

# API status endpoint
@status_bp.route('/status', methods=['GET'])
def api_status():
    """Get the status of the API and its components"""
    start_time = time.time()
    
    # Basic API health check
    api_health = {
        'status': 'ok',
        'uptime': os.popen('uptime -p').read().strip() if os.name != 'nt' else 'Available',
        'version': '1.0',
    }
    
    # Check database connection
    db_status = 'ok'
    db_message = 'Database connection established'
    
    try:
        # Execute a simple query to check database connectivity
        db.session.execute(text('SELECT 1'))
        db.session.commit()
    except Exception as e:
        db_status = 'error'
        db_message = f'Database connection error: {str(e)}'
        logger.error(f"Database health check failed: {str(e)}")
    
    # Calculate latency
    latency = round((time.time() - start_time) * 1000, 2)  # in milliseconds
    
    return jsonify({
        'status': 'error' if db_status == 'error' else 'ok',
        'message': 'API is operational' if db_status == 'ok' else 'API operational but database issues detected',
        'latency': latency,
        'version': api_health['version'],
        'details': {
            'uptime': api_health['uptime'],
            'database': db_message,
        },
        'lastChecked': datetime.utcnow().isoformat()
    })

# Database status endpoint
@status_bp.route('/database/status', methods=['GET'])
def database_status():
    """Get the status of the database connection"""
    try:
        # Execute a simple query to check database connectivity
        start_time = time.time()
        result = db.session.execute(text('SELECT version()'))
        db_version = result.scalar()
        db.session.commit()
        
        # Calculate query time
        query_time = round((time.time() - start_time) * 1000, 2)  # in milliseconds
        
        # Get connection pool info
        try:
            engine_status = {
                'pool_size': db.engine.pool.size(),
                'checkedin': db.engine.pool.checkedin(),
                'overflow': db.engine.pool.overflow(),
                'checkedout': db.engine.pool.checkedout(),
            }
        except Exception as e:
            engine_status = {
                'note': f'Could not get pool info: {str(e)}'
            }
        
        return jsonify({
            'status': 'ok',
            'message': 'Database connection established',
            'latency': query_time,
            'details': {
                'version': db_version,
                'connection_pool': engine_status,
            },
            'lastChecked': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error checking database status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Database connection error: {str(e)}',
            'lastChecked': datetime.utcnow().isoformat()
        })