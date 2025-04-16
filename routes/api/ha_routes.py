"""
High-Availability API Routes for NVC Banking Platform
Provides API endpoints for high-availability clustering operations,
monitoring, and management.
"""

import os
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Blueprint, jsonify, request, abort, current_app, g
from flask_login import login_required, current_user

import cluster
import ha_database
import high_availability
from auth import admin_required, api_key_required

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
ha_api = Blueprint('ha_api', __name__, url_prefix='/api/v1/ha')

@ha_api.route('/status', methods=['GET'])
def get_ha_status():
    """Get high-availability infrastructure status"""
    status = high_availability.get_ha_status()
    # Format the response to match what the frontend JavaScript expects
    response = {
        'success': True,
        'ha_enabled': status.get('initialized', False),
        'ha_status': status.get('status', 'inactive'),
        'database': {
            'status': 'offline' if not status.get('initialized', False) else 'healthy',
            'primary': status.get('database', {}).get('primary', None),
            'replicas': status.get('database', {}).get('replicas', [])
        },
        'cluster': {
            'state': status.get('cluster', {}).get('state', 'inactive'),
            'nodes': status.get('cluster', {}).get('nodes', [])
        }
    }
    return jsonify(response)

@ha_api.route('/node', methods=['GET'])
def get_node_status():
    """Get status of this application node"""
    return jsonify(high_availability.get_app_node_status())

@ha_api.route('/cluster', methods=['GET'])
@api_key_required
def get_cluster_status():
    """Get cluster status"""
    cluster_manager = cluster.get_cluster_manager()
    
    if not cluster_manager:
        return jsonify({
            'error': 'Cluster not initialized',
            'message': 'Cluster manager is not available'
        }), 503
    
    return jsonify(cluster_manager.get_cluster_status())

@ha_api.route('/database', methods=['GET'])
@api_key_required
def get_database_status():
    """Get database cluster status"""
    db_cluster = ha_database.get_db_cluster()
    
    if not db_cluster:
        return jsonify({
            'error': 'Database cluster not initialized',
            'message': 'Database cluster is not available'
        }), 503
    
    return jsonify(db_cluster.get_cluster_status())

@ha_api.route('/nodes', methods=['GET'])
@admin_required
def list_nodes():
    """List all nodes in the cluster"""
    cluster_manager = cluster.get_cluster_manager()
    
    if not cluster_manager:
        return jsonify({
            'error': 'Cluster not initialized',
            'message': 'Cluster manager is not available'
        }), 503
    
    status = cluster_manager.get_cluster_status()
    return jsonify({
        'success': True,
        'node_id': status['node_id'],
        'leader_id': status['leader_id'],
        'nodes': status['nodes']
    })

@ha_api.route('/cluster/nodes', methods=['GET'])
def get_cluster_nodes():
    """Get all nodes in the cluster (for dashboard)"""
    cluster_manager = cluster.get_cluster_manager()
    
    if not cluster_manager:
        ha_status = high_availability.get_ha_status()
        if not ha_status.get('initialized', False):
            # Return a simulated response for demo purposes when HA is disabled
            return jsonify({
                'success': True,
                'nodes': [],
                'message': 'High-availability infrastructure is not enabled'
            })
        return jsonify({
            'success': False,
            'error': 'Cluster not initialized',
            'message': 'Cluster manager is not available'
        })
    
    status = cluster_manager.get_cluster_status()
    # Format the node data for the UI
    nodes = []
    for node_id, node_data in status['nodes'].items():
        nodes.append({
            'id': node_id,
            'address': node_data.get('address', 'N/A'),
            'health': node_data.get('health', 'unknown'),
            'last_seen': node_data.get('last_seen', None)
        })

    return jsonify({
        'success': True,
        'nodes': nodes,
        'leader_id': status['leader_id']
    })

@ha_api.route('/leader', methods=['GET'])
def get_leader():
    """Get the current cluster leader"""
    cluster_manager = cluster.get_cluster_manager()
    
    if not cluster_manager:
        return jsonify({
            'error': 'Cluster not initialized',
            'message': 'Cluster manager is not available'
        }), 503
    
    leader = cluster_manager.get_leader()
    
    if not leader:
        return jsonify({
            'error': 'No leader',
            'message': 'No leader is currently elected in the cluster'
        }), 404
    
    return jsonify(leader)

@ha_api.route('/database/servers', methods=['GET'])
def list_database_servers():
    """List all database servers in the cluster"""
    db_cluster = ha_database.get_db_cluster()
    
    if not db_cluster:
        ha_status = high_availability.get_ha_status()
        if not ha_status.get('initialized', False):
            # Return a simulated response for demo purposes when HA is disabled
            return jsonify({
                'success': True,
                'servers': [],
                'primary': None,
                'routing_policy': 'PRIMARY_ONLY',
                'message': 'High-availability infrastructure is not enabled'
            })
        return jsonify({
            'success': False,
            'error': 'Database cluster not initialized',
            'message': 'Database cluster is not available'
        }), 503
    
    status = db_cluster.get_cluster_status()
    return jsonify({
        'success': True,
        'cluster_id': status['cluster_id'],
        'primary': status['primary_id'],
        'routing_policy': status['routing_policy'],
        'servers': status['servers']
    })

@ha_api.route('/database/primary', methods=['GET'])
def get_primary_database():
    """Get the current primary database server"""
    db_cluster = ha_database.get_db_cluster()
    
    if not db_cluster:
        return jsonify({
            'error': 'Database cluster not initialized',
            'message': 'Database cluster is not available'
        }), 503
    
    status = db_cluster.get_cluster_status()
    primary_id = status['primary_id']
    
    if not primary_id or primary_id not in status['servers']:
        return jsonify({
            'error': 'No primary database',
            'message': 'No primary database server is currently available'
        }), 404
    
    return jsonify(status['servers'][primary_id])

@ha_api.route('/test', methods=['GET'])
def ha_test():
    """Test if high-availability infrastructure is working"""
    if high_availability.is_ha_active():
        # Run a test distributed transaction
        cluster_manager = cluster.get_cluster_manager()
        
        if cluster_manager:
            test_tx = {
                'type': 'test',
                'timestamp': datetime.now().isoformat(),
                'message': 'Testing distributed transaction'
            }
            
            success, message, tx_id = cluster_manager.execute_transaction(test_tx)
            
            # Test database connection
            db_healthy = False
            try:
                with high_availability.ha_read_session() as session:
                    if session:
                        result = session.execute("SELECT 1").fetchone()
                        db_healthy = result[0] == 1
            except Exception as e:
                return jsonify({
                    'success': False,
                    'cluster_healthy': success,
                    'database_healthy': False,
                    'error': str(e)
                })
            
            return jsonify({
                'success': True,
                'ha_status': high_availability.get_ha_status()['status'],
                'cluster_healthy': success,
                'database_healthy': db_healthy,
                'message': message,
                'transaction_id': tx_id
            })
        else:
            return jsonify({
                'success': False,
                'ha_status': high_availability.get_ha_status()['status'],
                'error': 'Cluster manager not available'
            })
    else:
        return jsonify({
            'success': False,
            'ha_status': high_availability.get_ha_status()['status'],
            'error': 'High-availability infrastructure is not active'
        })

@ha_api.route('/database/failover', methods=['POST'])
@admin_required
def initiate_database_failover():
    """Manually initiate a database failover"""
    db_cluster = ha_database.get_db_cluster()
    
    if not db_cluster:
        return jsonify({
            'error': 'Database cluster not initialized',
            'message': 'Database cluster is not available'
        }), 503
    
    try:
        # Get current primary
        old_primary = db_cluster.primary_id
        
        # Select new primary
        new_primary = db_cluster._select_new_primary()
        
        if not new_primary:
            return jsonify({
                'success': False,
                'error': 'Failed to select new primary',
                'message': 'No suitable replica found to promote to primary'
            }), 500
        
        return jsonify({
            'success': True,
            'old_primary': old_primary,
            'new_primary': new_primary,
            'message': f'Successfully promoted {new_primary} to primary'
        })
    
    except Exception as e:
        logger.error(f"Error during manual failover: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failover error',
            'message': str(e)
        }), 500

@ha_api.route('/database/routing-policy', methods=['PUT'])
@admin_required
def update_routing_policy():
    """Update database routing policy"""
    db_cluster = ha_database.get_db_cluster()
    
    if not db_cluster:
        return jsonify({
            'error': 'Database cluster not initialized',
            'message': 'Database cluster is not available'
        }), 503
    
    data = request.get_json()
    
    if not data or 'policy' not in data:
        return jsonify({
            'error': 'Invalid request',
            'message': 'Missing required parameter: policy'
        }), 400
    
    policy = data['policy']
    
    try:
        # Convert string to enum
        routing_policy = ha_database.RoutingPolicy[policy.upper()]
        db_cluster.routing_policy = routing_policy
        
        return jsonify({
            'success': True,
            'message': f'Routing policy updated to {routing_policy.value}',
            'policy': routing_policy.value
        })
    
    except KeyError:
        return jsonify({
            'success': False,
            'error': 'Invalid policy',
            'message': f'Invalid routing policy: {policy}',
            'valid_policies': [p.value for p in ha_database.RoutingPolicy]
        }), 400
    
    except Exception as e:
        logger.error(f"Error updating routing policy: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Update error',
            'message': str(e)
        }), 500

@ha_api.route('/transactions/<tx_id>', methods=['GET'])
@api_key_required
def get_transaction_status(tx_id):
    """Get status of a distributed transaction"""
    cluster_manager = cluster.get_cluster_manager()
    
    if not cluster_manager:
        return jsonify({
            'error': 'Cluster not initialized',
            'message': 'Cluster manager is not available'
        }), 503
    
    status = cluster_manager.get_transaction_status(tx_id)
    
    if not status:
        return jsonify({
            'error': 'Transaction not found',
            'message': f'No transaction found with ID {tx_id}'
        }), 404
    
    return jsonify(status)

@ha_api.route('/backup', methods=['POST'])
@admin_required
def initiate_backup():
    """Manually initiate a database backup"""
    try:
        success = high_availability._perform_database_backup()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Database backup initiated successfully',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Backup failed',
                'message': 'Failed to perform database backup'
            }), 500
    
    except Exception as e:
        logger.error(f"Error initiating database backup: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Backup error',
            'message': str(e)
        }), 500

@ha_api.route('/regions', methods=['GET'])
def list_regions():
    """List all available regions"""
    regions = set()
    
    # Add the current region
    regions.add(high_availability.HA_CONFIG['region'])
    
    # Add regions from database servers
    db_cluster = ha_database.get_db_cluster()
    if db_cluster:
        for server_id, server in db_cluster.servers.items():
            regions.add(server.region)
    
    # Add regions from cluster nodes
    cluster_manager = cluster.get_cluster_manager()
    if cluster_manager:
        status = cluster_manager.get_cluster_status()
        for node_id, node in status['nodes'].items():
            if 'region' in node:
                regions.add(node['region'])
    
    return jsonify({
        'regions': list(regions),
        'current_region': high_availability.HA_CONFIG['region']
    })

@ha_api.route('/metrics', methods=['GET'])
def get_metrics():
    """Get metrics for high-availability infrastructure"""
    metrics = {
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'app_metrics': {},
        'db_metrics': {},
        'cluster_metrics': {}
    }
    
    # Application metrics
    app_status = high_availability.get_app_node_status()
    metrics['app_metrics'] = {
        'node_id': app_status['node_id'],
        'uptime': app_status['uptime'],
        'ha_status': app_status['ha_status']
    }
    
    # Database metrics
    db_cluster = ha_database.get_db_cluster()
    if db_cluster:
        db_status = db_cluster.get_cluster_status()
        metrics['db_metrics'] = {
            'online_servers': db_status['online_servers'],
            'degraded_servers': db_status['degraded_servers'],
            'offline_servers': db_status['offline_servers'],
            'primary_id': db_status['primary_id'],
            'primary_connections': (
                db_status['servers'][db_status['primary_id']]['current_connections']
                if db_status['primary_id'] in db_status['servers'] else 0
            ),
            'primary_latency': (
                db_status['servers'][db_status['primary_id']]['latency_ms']
                if db_status['primary_id'] in db_status['servers'] else 0
            ),
            'replica_connections': sum(
                server['current_connections'] for server_id, server in db_status['servers'].items()
                if server_id != db_status['primary_id']
            ),
            'avg_replica_latency': (
                sum(server['latency_ms'] for server_id, server in db_status['servers'].items()
                    if server_id != db_status['primary_id']) /
                max(1, sum(1 for server_id in db_status['servers'] if server_id != db_status['primary_id']))
            ),
            'avg_replication_lag': (
                sum(server['replication_lag'] for server_id, server in db_status['servers'].items()
                    if server_id != db_status['primary_id'] and 'replication_lag' in server) /
                max(1, sum(1 for server_id, server in db_status['servers'].items()
                          if server_id != db_status['primary_id'] and 'replication_lag' in server))
            )
        }
    else:
        # Add some placeholder metrics for when HA is disabled
        metrics['db_metrics'] = {
            'online_servers': 0,
            'degraded_servers': 0,
            'offline_servers': 0,
            'primary_id': None,
            'message': 'High-availability infrastructure is not enabled'
        }
    
    # Cluster metrics
    cluster_manager = cluster.get_cluster_manager()
    if cluster_manager:
        status = cluster_manager.get_cluster_status()
        healthy_nodes = sum(1 for node_id, node in status['nodes'].items()
                          if node['health'] == 'healthy')
        metrics['cluster_metrics'] = {
            'total_nodes': len(status['nodes']),
            'healthy_nodes': healthy_nodes,
            'leader_id': status['leader_id'],
            'term': status['term'],
            'is_leader': status['role'] == 'leader',
            'commit_index': status['commit_index'],
            'log_size': status['log_size']
        }
    else:
        # Add some placeholder metrics for when HA is disabled
        metrics['cluster_metrics'] = {
            'total_nodes': 0,
            'healthy_nodes': 0,
            'leader_id': None,
            'message': 'High-availability infrastructure is not enabled'
        }
    
    return jsonify(metrics)

@ha_api.route('/reset', methods=['POST'])
@admin_required
def reset_ha_infrastructure():
    """Reset high-availability infrastructure"""
    try:
        # Shutdown current infrastructure
        high_availability.shutdown_high_availability()
        
        # Reinitialize
        success = high_availability.init_high_availability()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'High-availability infrastructure reset successfully',
                'status': high_availability.get_ha_status()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Reset failed',
                'message': 'Failed to reinitialize high-availability infrastructure'
            }), 500
    
    except Exception as e:
        logger.error(f"Error resetting high-availability infrastructure: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Reset error',
            'message': str(e)
        }), 500