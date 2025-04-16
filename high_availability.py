"""
High-Availability Integration Module for NVC Banking Platform
This module integrates the clustering and high-availability database modules into the application,
providing a resilient architecture for enterprise-scale operations.
"""

import os
import logging
import threading
import time
import json
import random
import socket
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps

from flask import current_app, g, request, session
from sqlalchemy.orm import Session

import cluster
import ha_database
from app import app, db

# Configure logger
logger = logging.getLogger(__name__)

# High-availability status
class HAStatus(Enum):
    """High-availability infrastructure status"""
    ACTIVE = "active"       # Fully functional
    DEGRADED = "degraded"   # Functional with reduced capacity
    INACTIVE = "inactive"   # Not active

# Node types for monitoring
class NodeType(Enum):
    """Types of nodes in the cluster"""
    APPLICATION = "application"  # Application server
    DATABASE = "database"        # Database server
    CACHE = "cache"              # Cache server
    STORAGE = "storage"          # Storage server
    MESSAGE_QUEUE = "queue"      # Message queue
    LOAD_BALANCER = "balancer"   # Load balancer

# HA Configuration
HA_CONFIG = {
    'enabled': os.environ.get('HA_ENABLED', 'false').lower() == 'true',
    'node_id': os.environ.get('HA_NODE_ID', f"node_{socket.gethostname()}_{int(time.time())}"),
    'cluster_port': int(os.environ.get('HA_CLUSTER_PORT', '7000')),
    'seed_nodes': os.environ.get('HA_SEED_NODES', '').split(',') if os.environ.get('HA_SEED_NODES') else [],
    'region': os.environ.get('HA_REGION', 'default'),
    'auto_backup': os.environ.get('HA_AUTO_BACKUP', 'false').lower() == 'true',
    'backup_interval': int(os.environ.get('HA_BACKUP_INTERVAL', '3600')),  # 1 hour
    'health_check_interval': int(os.environ.get('HA_HEALTH_CHECK_INTERVAL', '60')),  # 1 minute
    'db_routing_policy': os.environ.get('HA_DB_ROUTING_POLICY', 'primary_write_replica_read'),
    'read_replicas_enabled': os.environ.get('HA_READ_REPLICAS_ENABLED', 'true').lower() == 'true',
    'failover_timeout': int(os.environ.get('HA_FAILOVER_TIMEOUT', '300')),  # 5 minutes
}

# Global state
_ha_status = HAStatus.INACTIVE
_ha_initialized = False
_ha_monitor_thread = None
_ha_backup_thread = None
_node_health = {}
_running = False
_startup_time = None

def init_high_availability():
    """Initialize high-availability infrastructure for the application"""
    global _ha_status, _ha_initialized, _ha_monitor_thread, _ha_backup_thread, _node_health, _running, _startup_time
    
    if _ha_initialized:
        logger.info("High-availability infrastructure already initialized")
        return
    
    # Check if high-availability is enabled
    if not HA_CONFIG['enabled']:
        logger.info("High-availability infrastructure is disabled in configuration")
        return
    
    logger.info("Initializing high-availability infrastructure")
    
    try:
        # Initialize node health tracking
        _node_health = {
            NodeType.APPLICATION.value: {'status': 'healthy', 'last_checked': datetime.now().isoformat()},
            NodeType.DATABASE.value: {'status': 'unknown', 'last_checked': None},
            NodeType.CACHE.value: {'status': 'unknown', 'last_checked': None},
            NodeType.STORAGE.value: {'status': 'unknown', 'last_checked': None},
            NodeType.MESSAGE_QUEUE.value: {'status': 'unknown', 'last_checked': None},
            NodeType.LOAD_BALANCER.value: {'status': 'unknown', 'last_checked': None},
        }
        
        # Initialize cluster node
        node_id = HA_CONFIG['node_id']
        host = '0.0.0.0'  # Listen on all interfaces
        port = HA_CONFIG['cluster_port']
        
        # Parse seed nodes
        seed_nodes = []
        for seed in HA_CONFIG['seed_nodes']:
            if seed:
                parts = seed.split(':')
                if len(parts) == 2:
                    # Format: host:port
                    seed_host, seed_port = parts
                    seed_id = f"seed_{seed_host}_{seed_port}"
                    seed_nodes.append({
                        'id': seed_id,
                        'host': seed_host,
                        'port': int(seed_port)
                    })
                elif len(parts) == 3:
                    # Format: id:host:port
                    seed_id, seed_host, seed_port = parts
                    seed_nodes.append({
                        'id': seed_id,
                        'host': seed_host,
                        'port': int(seed_port)
                    })
        
        # Initialize cluster
        cluster.init_cluster()
        
        # Initialize high-availability database
        ha_database.init_ha_database()
        
        # Update status
        _ha_status = HAStatus.ACTIVE
        _ha_initialized = True
        _running = True
        _startup_time = datetime.now()
        
        # Start health monitoring
        _ha_monitor_thread = threading.Thread(target=_health_monitor_loop)
        _ha_monitor_thread.daemon = True
        _ha_monitor_thread.start()
        
        # Start automatic backup if enabled
        if HA_CONFIG['auto_backup']:
            _ha_backup_thread = threading.Thread(target=_backup_loop)
            _ha_backup_thread.daemon = True
            _ha_backup_thread.start()
        
        logger.info(f"High-availability infrastructure initialized successfully with node ID {node_id}")
        
        # Register shutdown function with Flask
        app.teardown_appcontext(lambda exc: shutdown_high_availability())
        
        return True
    
    except Exception as e:
        logger.error(f"Error initializing high-availability infrastructure: {str(e)}")
        _ha_status = HAStatus.INACTIVE
        return False

def shutdown_high_availability():
    """Shutdown high-availability infrastructure"""
    global _ha_status, _ha_initialized, _ha_monitor_thread, _ha_backup_thread, _running
    
    if not _ha_initialized:
        return
    
    logger.info("Shutting down high-availability infrastructure")
    
    # Stop monitoring threads
    _running = False
    
    if _ha_monitor_thread:
        _ha_monitor_thread.join(timeout=2)
    
    if _ha_backup_thread:
        _ha_backup_thread.join(timeout=2)
    
    # Shutdown database cluster
    ha_database.shutdown_ha_database()
    
    # Shutdown cluster
    cluster.shutdown_cluster()
    
    # Update status
    _ha_status = HAStatus.INACTIVE
    _ha_initialized = False
    
    logger.info("High-availability infrastructure shut down")

def _health_monitor_loop():
    """Monitor health of high-availability components"""
    global _node_health, _ha_status
    
    logger.info("Starting health monitoring")
    
    while _running:
        try:
            # Check database health
            db_cluster = ha_database.get_db_cluster()
            if db_cluster:
                db_status = db_cluster.get_cluster_status()
                
                # Determine overall health based on availability of servers
                if db_status['online_servers'] == 0:
                    db_health = 'unhealthy'
                elif db_status['online_servers'] < db_status['server_count']:
                    db_health = 'degraded'
                else:
                    db_health = 'healthy'
                
                _node_health[NodeType.DATABASE.value] = {
                    'status': db_health,
                    'last_checked': datetime.now().isoformat(),
                    'details': {
                        'online_servers': db_status['online_servers'],
                        'degraded_servers': db_status['degraded_servers'],
                        'offline_servers': db_status['offline_servers'],
                        'primary_id': db_status['primary_id']
                    }
                }
            
            # Check application health (always consider ourselves healthy)
            _node_health[NodeType.APPLICATION.value] = {
                'status': 'healthy',
                'last_checked': datetime.now().isoformat(),
                'details': {
                    'uptime': (datetime.now() - _startup_time).total_seconds() if _startup_time else 0
                }
            }
            
            # Check cluster health if available
            cluster_manager = cluster.get_cluster_manager()
            if cluster_manager:
                cluster_status = cluster_manager.get_cluster_status()
                cluster_health = 'healthy'
                
                if cluster_status['cluster_state'] == 'degraded':
                    cluster_health = 'degraded'
                elif cluster_status['cluster_state'] in ['split', 'initializing']:
                    cluster_health = 'unhealthy'
                
                _node_health['cluster'] = {
                    'status': cluster_health,
                    'last_checked': datetime.now().isoformat(),
                    'details': {
                        'state': cluster_status['cluster_state'],
                        'leader_id': cluster_status['leader_id'],
                        'role': cluster_status['role'],
                        'nodes': len(cluster_status['nodes'])
                    }
                }
            
            # Determine overall HA status
            unhealthy_components = [c for c, info in _node_health.items() 
                                   if info['status'] == 'unhealthy' and c in ['database', 'cluster', 'application']]
            
            degraded_components = [c for c, info in _node_health.items() 
                                   if info['status'] == 'degraded' and c in ['database', 'cluster', 'application']]
            
            if unhealthy_components:
                # Critical components are unhealthy
                _ha_status = HAStatus.DEGRADED
                logger.warning(f"HA infrastructure in DEGRADED state. Unhealthy components: {unhealthy_components}")
            elif degraded_components:
                # Some components are degraded
                _ha_status = HAStatus.DEGRADED
                logger.info(f"HA infrastructure in DEGRADED state. Degraded components: {degraded_components}")
            else:
                # All critical components are healthy
                _ha_status = HAStatus.ACTIVE
            
        except Exception as e:
            logger.error(f"Error in health monitoring: {str(e)}")
            _ha_status = HAStatus.DEGRADED
        
        # Sleep until next check
        for _ in range(HA_CONFIG['health_check_interval']):
            if not _running:
                break
            time.sleep(1)

def _backup_loop():
    """Perform automatic backups"""
    logger.info("Starting automatic backup loop")
    
    while _running:
        try:
            # Perform database backup if we're the leader or standalone
            cluster_manager = cluster.get_cluster_manager()
            
            if not cluster_manager or cluster_manager.is_leader():
                logger.info("Initiating automatic database backup")
                
                success = _perform_database_backup()
                
                if success:
                    logger.info("Automatic database backup completed successfully")
                else:
                    logger.error("Automatic database backup failed")
        
        except Exception as e:
            logger.error(f"Error in backup loop: {str(e)}")
        
        # Sleep until next backup
        for _ in range(HA_CONFIG['backup_interval']):
            if not _running:
                break
            time.sleep(1)

def _perform_database_backup() -> bool:
    """
    Perform a database backup
    
    Returns:
        bool: Whether backup was successful
    """
    try:
        # Get the main database URL
        db_url = os.environ.get('DATABASE_URL')
        
        if not db_url:
            logger.error("DATABASE_URL not set, cannot perform backup")
            return False
        
        # Parse database URL to extract information
        # Example: postgresql://user:password@host:port/database
        parsed_url = db_url.split("://")[1]
        auth, rest = parsed_url.split("@")
        
        if ':' in auth:
            user, password = auth.split(":")
        else:
            user, password = auth, ""
        
        if '/' in rest:
            host_port, database = rest.split("/")
        else:
            host_port, database = rest, ""
        
        if ':' in host_port:
            host, port = host_port.split(":")
        else:
            host, port = host_port, "5432"
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(os.getcwd(), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_file = os.path.join(backup_dir, f"backup_{database}_{timestamp}.sql")
        
        # Build pg_dump command
        # Note: In a real implementation, we would use subprocess to execute this
        # For simulation purposes, we'll just log the command
        pg_dump_cmd = (
            f"PGPASSWORD='{password}' pg_dump -h {host} -p {port} -U {user} "
            f"-d {database} -F p -f {backup_file}"
        )
        
        logger.info(f"Backup command: {pg_dump_cmd}")
        
        # Simulate backup success
        with open(backup_file, 'w') as f:
            f.write(f"# Database backup for {database} created at {timestamp}\n")
            f.write(f"# This is a simulated backup for development purposes\n")
        
        # Register backup with cluster if available
        cluster_manager = cluster.get_cluster_manager()
        if cluster_manager:
            backup_record = {
                'type': 'database_backup',
                'database': database,
                'timestamp': timestamp,
                'file': backup_file,
                'node_id': HA_CONFIG['node_id']
            }
            
            success, message, tx_id = cluster_manager.execute_transaction(backup_record)
            logger.info(f"Registered backup with cluster: {message}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error performing database backup: {str(e)}")
        return False

def get_ha_status() -> Dict[str, Any]:
    """
    Get the current status of high-availability infrastructure
    
    Returns:
        dict: Status information
    """
    global _ha_status, _node_health
    
    # Basic status information
    status = {
        'status': _ha_status.value,
        'initialized': _ha_initialized,
        'startup_time': _startup_time.isoformat() if _startup_time else None,
        'uptime': (datetime.now() - _startup_time).total_seconds() if _startup_time else 0,
        'node_id': HA_CONFIG['node_id'],
        'region': HA_CONFIG['region'],
        'components': _node_health
    }
    
    # Add cluster information if available
    cluster_manager = cluster.get_cluster_manager()
    if cluster_manager:
        status['cluster'] = cluster_manager.get_cluster_status()
    
    # Add database information if available
    db_cluster = ha_database.get_db_cluster()
    if db_cluster:
        status['database'] = db_cluster.get_cluster_status()
    
    return status

def is_ha_active() -> bool:
    """
    Check if high-availability infrastructure is active
    
    Returns:
        bool: Whether HA is active
    """
    return _ha_status == HAStatus.ACTIVE

def is_ha_degraded() -> bool:
    """
    Check if high-availability infrastructure is in degraded state
    
    Returns:
        bool: Whether HA is degraded
    """
    return _ha_status == HAStatus.DEGRADED

def get_app_node_status() -> Dict[str, Any]:
    """
    Get the status of this application node
    
    Returns:
        dict: Application node status
    """
    node_status = {
        'node_id': HA_CONFIG['node_id'],
        'hostname': socket.gethostname(),
        'region': HA_CONFIG['region'],
        'startup_time': _startup_time.isoformat() if _startup_time else None,
        'uptime': (datetime.now() - _startup_time).total_seconds() if _startup_time else 0,
        'ha_status': _ha_status.value,
        'is_cluster_leader': False
    }
    
    # Check if we're the cluster leader
    cluster_manager = cluster.get_cluster_manager()
    if cluster_manager:
        node_status['is_cluster_leader'] = cluster_manager.is_leader()
        node_status['cluster_leader'] = cluster_manager.get_leader()
    
    return node_status

def ha_read_session() -> ha_database.HASession:
    """
    Get a high-availability database session for read operations
    
    Returns:
        HASession: High-availability database session
    """
    return ha_database.get_db_session(ha_database.TransactionType.READ)

def ha_write_session() -> ha_database.HASession:
    """
    Get a high-availability database session for write operations
    
    Returns:
        HASession: High-availability database session
    """
    return ha_database.get_db_session(ha_database.TransactionType.WRITE)

def ha_analytics_session() -> ha_database.HASession:
    """
    Get a high-availability database session for analytics operations
    
    Returns:
        HASession: High-availability database session
    """
    return ha_database.get_db_session(ha_database.TransactionType.ANALYTICS)

def ha_require_healthy(f):
    """
    Decorator to require that high-availability infrastructure is healthy
    Will return a 503 Service Unavailable response if HA is not active
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not _ha_initialized:
            # Initialize if not already done
            init_high_availability()
        
        if not is_ha_active():
            from flask import jsonify
            return jsonify({
                'error': 'Service temporarily unavailable',
                'message': 'High-availability infrastructure is in degraded state',
                'status': _ha_status.value
            }), 503
        
        return f(*args, **kwargs)
    
    return decorated_function

def ha_distributed_transaction(tx_type: str):
    """
    Decorator to execute a function with distributed transaction consensus
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get cluster manager
            manager = cluster.get_cluster_manager()
            
            if not manager:
                # No cluster manager, execute directly
                return f(*args, **kwargs)
            
            # Check if we're the leader
            if manager.is_leader():
                # We're the leader, execute directly
                return f(*args, **kwargs)
            
            # Get request data for transaction
            if request:
                request_data = {}
                
                if request.is_json:
                    request_data = request.get_json()
                elif request.form:
                    request_data = {key: request.form[key] for key in request.form}
                elif request.args:
                    request_data = {key: request.args[key] for key in request.args}
                
                # Create transaction record
                tx_id = f"{tx_type}_{int(time.time())}_{random.randint(1000, 9999)}"
                tx_data = {
                    'id': tx_id,
                    'type': tx_type,
                    'function': f.__name__,
                    'args': args,
                    'kwargs': kwargs,
                    'request_data': request_data,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Execute with distributed consensus
                success, msg, tx_id = manager.execute_transaction(tx_data)
                
                if success:
                    # Transaction submitted successfully
                    return f(*args, **kwargs)
                else:
                    # Forward to leader
                    leader_info = manager.get_leader()
                    
                    if leader_info:
                        from flask import jsonify
                        return jsonify({
                            'status': 'redirect',
                            'message': 'Operation must be performed on leader node',
                            'leader': leader_info
                        }), 307
                    else:
                        from flask import jsonify
                        return jsonify({
                            'error': 'Service temporarily unavailable',
                            'message': 'No cluster leader available for distributed transaction',
                        }), 503
            
            # No request context or no data to forward, just execute
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator
    
# Flask extension to integrate high-availability with SQLAlchemy
class HADatabaseExtension:
    """
    Flask extension to integrate high-availability with SQLAlchemy
    """
    
    def __init__(self, app=None):
        """
        Initialize the extension
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        Initialize the extension with a Flask application
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Initialize high-availability infrastructure
        init_high_availability()
        
        # Register teardown function
        app.teardown_appcontext(self.teardown)
        
        # Add health check endpoint
        @app.route('/api/v1/ha/status')
        def ha_status():
            from flask import jsonify
            return jsonify(get_ha_status())
        
        @app.route('/api/v1/ha/node')
        def ha_node():
            from flask import jsonify
            return jsonify(get_app_node_status())
    
    def teardown(self, exception):
        """Clean up resources"""
        pass

# Initialize on import
if not _ha_initialized and HA_CONFIG['enabled']:
    init_high_availability()