"""
High-Availability Database Module for NVC Banking Platform
Provides resilient database connections, read-write splitting, and failover capabilities
for enterprise-scale banking operations.
"""

import os
import time
import logging
import threading
import random
import json
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set, Callable, Union
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from sqlalchemy import create_engine, exc, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

import cluster

# Configure logger
logger = logging.getLogger(__name__)

class DatabaseRole(Enum):
    """Database server roles in high-availability setup"""
    PRIMARY = "primary"       # Primary read-write database
    REPLICA = "replica"       # Read-only replica
    ANALYTICS = "analytics"   # Analytics-optimized replica

class DatabaseStatus(Enum):
    """Status of a database server in the cluster"""
    ONLINE = "online"         # Fully operational
    DEGRADED = "degraded"     # Operational with issues
    OFFLINE = "offline"       # Not operational
    SYNCING = "syncing"       # Syncing with primary

class TransactionType(Enum):
    """Types of database transactions"""
    READ = "read"             # Read-only transaction
    WRITE = "write"           # Read-write transaction
    BATCH = "batch"           # Batch processing transaction
    ANALYTICS = "analytics"   # Analytics/reporting transaction

class RoutingPolicy(Enum):
    """Policies for routing database connections"""
    PRIMARY_ONLY = "primary_only"             # All transactions to primary
    PRIMARY_WRITE_REPLICA_READ = "primary_write_replica_read"  # Write to primary, read from replicas
    LEAST_LOADED = "least_loaded"             # Route to least loaded server
    CLOSEST_REGION = "closest_region"         # Route to closest server by region
    RANDOM_REPLICA = "random_replica"         # Random replica for reads

class DatabaseServer:
    """
    Represents a database server in the high-availability cluster
    """
    
    def __init__(
        self,
        server_id: str,
        connection_url: str,
        role: DatabaseRole = DatabaseRole.REPLICA,
        region: str = "default",
        weight: int = 1,
        max_connections: int = 100
    ):
        """
        Initialize a database server entry
        
        Args:
            server_id: Unique identifier for this server
            connection_url: SQLAlchemy connection URL
            role: Role of this server in the HA setup
            region: Geographical region of this server
            weight: Routing weight for load balancing
            max_connections: Maximum number of connections
        """
        self.server_id = server_id
        self.connection_url = connection_url
        self.role = role
        self.region = region
        self.weight = weight
        self.max_connections = max_connections
        
        # Parse connection URL to extract host info
        parsed_url = urlparse(connection_url)
        self.host = parsed_url.hostname
        self.port = parsed_url.port
        self.username = parsed_url.username
        self.database_name = parsed_url.path.lstrip('/') if parsed_url.path else None
        
        # Runtime state
        self.status = DatabaseStatus.OFFLINE
        self.current_connections = 0
        self.last_checked = datetime.now()
        self.latency = 0.0  # in milliseconds
        self.error_rate = 0.0  # percentage of failed queries
        self.replication_lag = 0.0  # in seconds (for replicas)
        
        # SQLAlchemy engine
        self.engine = None
        self.session_factory = None
        
        # Health check thread
        self.health_check_thread = None
        self.health_check_interval = 30  # seconds
        self.running = False
        
        # Statistics
        self.stats = {
            'queries_total': 0,
            'queries_successful': 0,
            'queries_failed': 0,
            'last_error': None,
            'last_error_time': None,
            'avg_query_time': 0.0,
            'connections_created': 0,
            'connections_closed': 0
        }
    
    def initialize(self) -> bool:
        """
        Initialize the database server connection
        
        Returns:
            bool: Whether initialization was successful
        """
        try:
            # Create SQLAlchemy engine with connection pooling
            self.engine = create_engine(
                self.connection_url,
                poolclass=QueuePool,
                pool_size=min(20, self.max_connections // 5),
                max_overflow=min(10, self.max_connections // 10),
                pool_timeout=30,
                pool_recycle=300,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 10}
            )
            
            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)
            
            # Test connection
            self._check_connection()
            
            # Start health check thread
            self.running = True
            self.health_check_thread = threading.Thread(target=self._health_check_loop)
            self.health_check_thread.daemon = True
            self.health_check_thread.start()
            
            logger.info(f"Database server {self.server_id} ({self.host}:{self.port}) initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database server {self.server_id}: {str(e)}")
            self.status = DatabaseStatus.OFFLINE
            self.stats['last_error'] = str(e)
            self.stats['last_error_time'] = datetime.now().isoformat()
            return False
    
    def shutdown(self) -> None:
        """Shutdown the database server connection"""
        self.running = False
        
        if self.health_check_thread:
            self.health_check_thread.join(timeout=2)
        
        if self.engine:
            self.engine.dispose()
            
        logger.info(f"Database server {self.server_id} shut down")
    
    def _check_connection(self) -> bool:
        """
        Check if the database server is accessible
        
        Returns:
            bool: Whether the connection is working
        """
        try:
            start_time = time.time()
            with self.engine.connect() as conn:
                # Simple query to check connection
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000
            
            # Update statistics
            self.latency = elapsed_ms
            self.last_checked = datetime.now()
            self.status = DatabaseStatus.ONLINE
            self.stats['queries_total'] += 1
            self.stats['queries_successful'] += 1
            
            # Update error rate
            if self.stats['queries_total'] > 0:
                self.error_rate = (self.stats['queries_failed'] / self.stats['queries_total']) * 100
            
            # Get connection count
            with self.engine.connect() as conn:
                if 'postgresql' in self.connection_url.lower():
                    result = conn.execute(text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = :db_name"
                    ), {"db_name": self.database_name})
                    self.current_connections = result.scalar() or 0
                
                # Check replication lag for replicas
                if self.role == DatabaseRole.REPLICA and 'postgresql' in self.connection_url.lower():
                    try:
                        result = conn.execute(text(
                            "SELECT extract(epoch from now() - pg_last_xact_replay_timestamp()) as lag"
                        ))
                        self.replication_lag = result.scalar() or 0
                    except Exception as e:
                        logger.warning(f"Could not check replication lag for {self.server_id}: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Connection check failed for {self.server_id}: {str(e)}")
            self.status = DatabaseStatus.OFFLINE
            self.stats['queries_total'] += 1
            self.stats['queries_failed'] += 1
            self.stats['last_error'] = str(e)
            self.stats['last_error_time'] = datetime.now().isoformat()
            
            # Update error rate
            if self.stats['queries_total'] > 0:
                self.error_rate = (self.stats['queries_failed'] / self.stats['queries_total']) * 100
            
            return False
    
    def _health_check_loop(self) -> None:
        """Periodically check database health"""
        while self.running:
            try:
                self._check_connection()
                
                # Adjust status based on metrics
                if self.status == DatabaseStatus.ONLINE:
                    if self.error_rate > 10.0 or self.latency > 500:
                        self.status = DatabaseStatus.DEGRADED
                    elif self.role == DatabaseRole.REPLICA and self.replication_lag > 300:
                        self.status = DatabaseStatus.DEGRADED
                elif self.status == DatabaseStatus.DEGRADED:
                    if self.error_rate < 5.0 and self.latency < 200:
                        if self.role != DatabaseRole.REPLICA or self.replication_lag < 60:
                            self.status = DatabaseStatus.ONLINE
                
            except Exception as e:
                logger.error(f"Health check error for {self.server_id}: {str(e)}")
            
            # Sleep until next check
            for _ in range(self.health_check_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def get_session(self) -> Optional[Session]:
        """
        Get a database session
        
        Returns:
            Session: SQLAlchemy session or None if not available
        """
        if not self.engine or self.status == DatabaseStatus.OFFLINE:
            return None
        
        try:
            session = self.session_factory()
            self.current_connections += 1
            self.stats['connections_created'] += 1
            return session
        except Exception as e:
            logger.error(f"Error creating session for {self.server_id}: {str(e)}")
            self.stats['last_error'] = str(e)
            self.stats['last_error_time'] = datetime.now().isoformat()
            return None
    
    def release_session(self, session: Session) -> None:
        """
        Release a database session
        
        Args:
            session: SQLAlchemy session to release
        """
        try:
            session.close()
            self.current_connections = max(0, self.current_connections - 1)
            self.stats['connections_closed'] += 1
        except Exception as e:
            logger.error(f"Error releasing session for {self.server_id}: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of this database server
        
        Returns:
            dict: Status information
        """
        return {
            'server_id': self.server_id,
            'host': self.host,
            'port': self.port,
            'role': self.role.value,
            'region': self.region,
            'status': self.status.value,
            'current_connections': self.current_connections,
            'max_connections': self.max_connections,
            'latency_ms': self.latency,
            'error_rate': self.error_rate,
            'replication_lag': self.replication_lag,
            'last_checked': self.last_checked.isoformat(),
            'stats': self.stats
        }


class DatabaseCluster:
    """
    Manages a cluster of database servers for high-availability operations
    """
    
    def __init__(
        self,
        cluster_id: str,
        routing_policy: RoutingPolicy = RoutingPolicy.PRIMARY_WRITE_REPLICA_READ
    ):
        """
        Initialize a database cluster
        
        Args:
            cluster_id: Unique identifier for this cluster
            routing_policy: Policy for routing connections
        """
        self.cluster_id = cluster_id
        self.routing_policy = routing_policy
        self.servers = {}  # Dict[server_id, DatabaseServer]
        self.primary_id = None
        
        # Server grouping by role for efficient routing
        self.servers_by_role = {role: [] for role in DatabaseRole}
        self.servers_by_region = {}  # Dict[region, List[server_id]]
        
        # Current user region for geo-routing
        self.current_region = os.environ.get('DATABASE_REGION', 'default')
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Cluster state
        self.running = False
        self.auto_failover = True
        self.failover_monitor = None
        self.failover_check_interval = 60  # seconds
        
        # Last failover info
        self.last_failover = {
            'time': None,
            'from_server': None,
            'to_server': None,
            'reason': None
        }
        
        # Transaction handling
        self.transaction_counter = 0
        self.distributed_transactions = {}  # Dict[tx_id, transaction_info]
        
        logger.info(f"Database cluster {cluster_id} initialized with routing policy {routing_policy.value}")
    
    def add_server(self, server: DatabaseServer) -> bool:
        """
        Add a database server to the cluster
        
        Args:
            server: DatabaseServer instance to add
            
        Returns:
            bool: Whether the server was added successfully
        """
        with self.lock:
            server_id = server.server_id
            
            if server_id in self.servers:
                logger.warning(f"Server {server_id} already exists in cluster")
                return False
            
            # Initialize the server
            if not server.initialize():
                logger.error(f"Failed to initialize server {server_id}")
                return False
            
            # Add to server collections
            self.servers[server_id] = server
            self.servers_by_role[server.role].append(server_id)
            
            if server.region not in self.servers_by_region:
                self.servers_by_region[server.region] = []
            self.servers_by_region[server.region].append(server_id)
            
            # Set as primary if applicable
            if server.role == DatabaseRole.PRIMARY and not self.primary_id:
                self.primary_id = server_id
                logger.info(f"Set {server_id} as primary database server")
            
            logger.info(f"Added server {server_id} ({server.role.value}) to cluster {self.cluster_id}")
            return True
    
    def remove_server(self, server_id: str) -> bool:
        """
        Remove a database server from the cluster
        
        Args:
            server_id: ID of the server to remove
            
        Returns:
            bool: Whether the server was removed
        """
        with self.lock:
            if server_id not in self.servers:
                logger.warning(f"Server {server_id} does not exist in cluster")
                return False
            
            server = self.servers[server_id]
            
            # Remove from collections
            self.servers_by_role[server.role].remove(server_id)
            if server.region in self.servers_by_region:
                self.servers_by_region[server.region].remove(server_id)
            
            # If removing primary, select a new one
            if server_id == self.primary_id:
                self._select_new_primary()
            
            # Shutdown the server
            server.shutdown()
            
            # Remove from servers dict
            del self.servers[server_id]
            
            logger.info(f"Removed server {server_id} from cluster {self.cluster_id}")
            return True
    
    def start(self) -> bool:
        """
        Start the database cluster
        
        Returns:
            bool: Whether startup was successful
        """
        with self.lock:
            if self.running:
                logger.warning(f"Cluster {self.cluster_id} is already running")
                return True
            
            logger.info(f"Starting database cluster {self.cluster_id}")
            
            # Ensure we have at least one server
            if not self.servers:
                logger.error(f"Cannot start cluster {self.cluster_id} - no servers configured")
                return False
            
            # Find a primary if we don't have one
            if not self.primary_id:
                self._select_new_primary()
                
                if not self.primary_id:
                    logger.error(f"Cannot start cluster {self.cluster_id} - no primary server available")
                    return False
            
            # Start failover monitoring
            self.running = True
            if self.auto_failover:
                self.failover_monitor = threading.Thread(target=self._failover_monitor_loop)
                self.failover_monitor.daemon = True
                self.failover_monitor.start()
            
            logger.info(f"Database cluster {self.cluster_id} started with primary {self.primary_id}")
            return True
    
    def stop(self) -> None:
        """Stop the database cluster"""
        with self.lock:
            if not self.running:
                return
            
            logger.info(f"Stopping database cluster {self.cluster_id}")
            
            # Stop failover monitoring
            self.running = False
            if self.failover_monitor:
                self.failover_monitor.join(timeout=2)
            
            # Shutdown all servers
            for server_id, server in self.servers.items():
                try:
                    server.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down server {server_id}: {str(e)}")
            
            logger.info(f"Database cluster {self.cluster_id} stopped")
    
    def _select_new_primary(self) -> Optional[str]:
        """
        Select a new primary server from available replicas
        
        Returns:
            str: ID of the new primary server, or None if no suitable server found
        """
        # Find online replicas that can be promoted
        candidates = []
        for server_id in self.servers:
            server = self.servers[server_id]
            
            # Skip servers that can't be promoted
            if (server.role != DatabaseRole.REPLICA or 
                server.status == DatabaseStatus.OFFLINE or
                server.status == DatabaseStatus.SYNCING):
                continue
            
            # Add to candidates
            candidates.append((
                server_id,
                server.status == DatabaseStatus.ONLINE,  # Prefer ONLINE over DEGRADED
                -server.replication_lag,  # Prefer servers with lower replication lag
                -server.latency  # Prefer servers with lower latency
            ))
        
        if not candidates:
            logger.error(f"No suitable replica found to promote to primary in cluster {self.cluster_id}")
            self.primary_id = None
            return None
        
        # Sort by our criteria (online status, replication lag, latency)
        candidates.sort(key=lambda x: x[1:], reverse=True)
        new_primary_id = candidates[0][0]
        
        # Get the server
        new_primary = self.servers[new_primary_id]
        
        # Update roles
        old_primary_id = self.primary_id
        self.primary_id = new_primary_id
        
        # Update server roles
        if old_primary_id in self.servers:
            old_primary = self.servers[old_primary_id]
            # Remove from primary list
            self.servers_by_role[DatabaseRole.PRIMARY].remove(old_primary_id)
            # Change role to replica
            old_primary.role = DatabaseRole.REPLICA
            # Add to replica list
            self.servers_by_role[DatabaseRole.REPLICA].append(old_primary_id)
            
            logger.info(f"Changed {old_primary_id} from PRIMARY to REPLICA")
        
        # Remove from replica list
        self.servers_by_role[DatabaseRole.REPLICA].remove(new_primary_id)
        # Change role to primary
        new_primary.role = DatabaseRole.PRIMARY
        # Add to primary list
        self.servers_by_role[DatabaseRole.PRIMARY].append(new_primary_id)
        
        # Record the failover
        self.last_failover = {
            'time': datetime.now().isoformat(),
            'from_server': old_primary_id,
            'to_server': new_primary_id,
            'reason': "Manual failover" if old_primary_id else "Initial primary selection"
        }
        
        logger.info(f"Promoted {new_primary_id} to PRIMARY")
        
        # Notify cluster about the failover
        if cluster.get_cluster_manager():
            cluster_tx = {
                'type': 'db_failover',
                'cluster_id': self.cluster_id,
                'old_primary': old_primary_id,
                'new_primary': new_primary_id,
                'timestamp': datetime.now().isoformat()
            }
            success, msg, tx_id = cluster.get_cluster_manager().execute_transaction(cluster_tx)
            logger.info(f"Notified cluster of database failover: {msg}")
        
        return new_primary_id
    
    def _failover_monitor_loop(self) -> None:
        """Monitor primary health and trigger automatic failover if needed"""
        while self.running:
            try:
                with self.lock:
                    if not self.primary_id or self.primary_id not in self.servers:
                        logger.warning("No primary server found, selecting new primary")
                        self._select_new_primary()
                    else:
                        primary = self.servers[self.primary_id]
                        
                        # Check if primary is healthy
                        if primary.status == DatabaseStatus.OFFLINE:
                            logger.warning(f"Primary server {self.primary_id} is offline, initiating failover")
                            self._select_new_primary()
                        elif primary.status == DatabaseStatus.DEGRADED:
                            # Check if there's a healthier replica we should promote
                            degraded_duration = (datetime.now() - primary.last_checked).total_seconds()
                            
                            # If primary has been degraded for too long, consider failover
                            if degraded_duration > 300:  # 5 minutes
                                logger.warning(
                                    f"Primary server {self.primary_id} has been degraded for {degraded_duration}s, "
                                    "considering failover"
                                )
                                
                                # Check if we have a healthier replica
                                for server_id in self.servers_by_role[DatabaseRole.REPLICA]:
                                    server = self.servers[server_id]
                                    if server.status == DatabaseStatus.ONLINE and server.replication_lag < 60:
                                        logger.warning(
                                            f"Found healthier replica {server_id}, initiating failover from degraded primary"
                                        )
                                        self._select_new_primary()
                                        break
            
            except Exception as e:
                logger.error(f"Error in failover monitor: {str(e)}")
            
            # Sleep until next check
            for _ in range(self.failover_check_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def get_server_for_transaction(
        self,
        transaction_type: TransactionType,
        region: str = None
    ) -> Optional[DatabaseServer]:
        """
        Get the appropriate server for a transaction based on routing policy
        
        Args:
            transaction_type: Type of transaction
            region: Optional region preference
            
        Returns:
            DatabaseServer: Selected server or None if no suitable server found
        """
        with self.lock:
            if not self.servers:
                logger.error("No servers available in the cluster")
                return None
            
            region = region or self.current_region
            
            # WRITE transactions always go to primary
            if transaction_type == TransactionType.WRITE:
                if not self.primary_id or self.primary_id not in self.servers:
                    logger.error("No primary server available for write transaction")
                    return None
                
                primary = self.servers[self.primary_id]
                if primary.status == DatabaseStatus.OFFLINE:
                    logger.error("Primary server is offline, cannot process write transaction")
                    return None
                
                return primary
            
            # For READ transactions, apply routing policy
            if transaction_type == TransactionType.READ:
                if self.routing_policy == RoutingPolicy.PRIMARY_ONLY:
                    # Send all reads to primary
                    if not self.primary_id or self.primary_id not in self.servers:
                        logger.error("No primary server available for read transaction")
                        return None
                    
                    return self.servers[self.primary_id]
                
                elif self.routing_policy == RoutingPolicy.PRIMARY_WRITE_REPLICA_READ:
                    # Try to find a healthy replica
                    replicas = self.servers_by_role[DatabaseRole.REPLICA]
                    healthy_replicas = [r for r in replicas if self.servers[r].status == DatabaseStatus.ONLINE]
                    
                    if healthy_replicas:
                        # First try replicas in the same region
                        region_replicas = [
                            r for r in healthy_replicas 
                            if self.servers[r].region == region
                        ]
                        
                        if region_replicas:
                            # Use a random replica in the same region
                            server_id = random.choice(region_replicas)
                            return self.servers[server_id]
                        
                        # Otherwise use any healthy replica
                        server_id = random.choice(healthy_replicas)
                        return self.servers[server_id]
                    
                    # Fall back to primary if no healthy replicas
                    if self.primary_id and self.primary_id in self.servers:
                        return self.servers[self.primary_id]
                
                elif self.routing_policy == RoutingPolicy.LEAST_LOADED:
                    # Find the least loaded server
                    candidates = []
                    
                    # Consider primary and replicas for reads
                    server_ids = [self.primary_id] if self.primary_id else []
                    server_ids.extend(self.servers_by_role[DatabaseRole.REPLICA])
                    
                    for server_id in server_ids:
                        if server_id not in self.servers:
                            continue
                            
                        server = self.servers[server_id]
                        
                        # Skip offline servers
                        if server.status == DatabaseStatus.OFFLINE:
                            continue
                        
                        # Calculate load score (lower is better)
                        # We consider connection percentage, latency, and error rate
                        connection_pct = server.current_connections / server.max_connections if server.max_connections > 0 else 1.0
                        latency_factor = min(1.0, server.latency / 1000.0)  # Normalize to 0-1 range
                        error_factor = min(1.0, server.error_rate / 100.0)  # Normalize to 0-1 range
                        
                        # For replicas, also consider replication lag
                        replication_factor = 0.0
                        if server.role == DatabaseRole.REPLICA:
                            replication_factor = min(1.0, server.replication_lag / 300.0)  # Normalize to 0-1 range
                        
                        # Calculate overall load score (0-1 range, lower is better)
                        load_score = (
                            0.4 * connection_pct + 
                            0.2 * latency_factor + 
                            0.3 * error_factor + 
                            0.1 * replication_factor
                        )
                        
                        # Add regional preference
                        if server.region == region:
                            load_score -= 0.1  # Prefer servers in the same region
                        
                        candidates.append((server_id, load_score))
                    
                    if candidates:
                        # Sort by load score (ascending)
                        candidates.sort(key=lambda x: x[1])
                        server_id = candidates[0][0]
                        return self.servers[server_id]
                
                elif self.routing_policy == RoutingPolicy.CLOSEST_REGION:
                    # Prioritize servers in the closest region
                    # For this simulation, we'll just look for servers in the same region
                    
                    if region in self.servers_by_region:
                        region_servers = self.servers_by_region[region]
                        healthy_servers = [
                            s for s in region_servers
                            if self.servers[s].status != DatabaseStatus.OFFLINE
                        ]
                        
                        if healthy_servers:
                            # Prioritize replicas for reads
                            replicas = [
                                s for s in healthy_servers
                                if self.servers[s].role == DatabaseRole.REPLICA
                            ]
                            
                            if replicas:
                                server_id = random.choice(replicas)
                                return self.servers[server_id]
                            
                            # Fall back to any server in the region
                            server_id = random.choice(healthy_servers)
                            return self.servers[server_id]
                    
                    # If no servers in the same region, fall back to any healthy server
                    healthy_servers = [
                        s for s in self.servers
                        if self.servers[s].status != DatabaseStatus.OFFLINE
                    ]
                    
                    if healthy_servers:
                        server_id = random.choice(healthy_servers)
                        return self.servers[server_id]
                
                elif self.routing_policy == RoutingPolicy.RANDOM_REPLICA:
                    # Use a random replica for reads
                    replicas = self.servers_by_role[DatabaseRole.REPLICA]
                    healthy_replicas = [
                        r for r in replicas
                        if self.servers[r].status != DatabaseStatus.OFFLINE
                    ]
                    
                    if healthy_replicas:
                        server_id = random.choice(healthy_replicas)
                        return self.servers[server_id]
                    
                    # Fall back to primary
                    if self.primary_id and self.primary_id in self.servers:
                        primary = self.servers[self.primary_id]
                        if primary.status != DatabaseStatus.OFFLINE:
                            return primary
            
            # For ANALYTICS transactions, use analytics servers if available, otherwise replicas
            elif transaction_type == TransactionType.ANALYTICS:
                analytics_servers = self.servers_by_role[DatabaseRole.ANALYTICS]
                healthy_analytics = [
                    s for s in analytics_servers
                    if self.servers[s].status != DatabaseStatus.OFFLINE
                ]
                
                if healthy_analytics:
                    server_id = random.choice(healthy_analytics)
                    return self.servers[server_id]
                
                # Fall back to replicas for analytics
                replicas = self.servers_by_role[DatabaseRole.REPLICA]
                healthy_replicas = [
                    r for r in replicas
                    if self.servers[r].status != DatabaseStatus.OFFLINE
                ]
                
                if healthy_replicas:
                    server_id = random.choice(healthy_replicas)
                    return self.servers[server_id]
            
            # For BATCH transactions, prefer primary or least loaded server
            elif transaction_type == TransactionType.BATCH:
                # Start with primary for consistency
                if self.primary_id and self.primary_id in self.servers:
                    primary = self.servers[self.primary_id]
                    if primary.status != DatabaseStatus.OFFLINE:
                        # Check if primary is not too loaded
                        if primary.current_connections < (primary.max_connections * 0.8):
                            return primary
                
                # Find least loaded server as fallback
                candidates = []
                for server_id, server in self.servers.items():
                    if server.status == DatabaseStatus.OFFLINE:
                        continue
                    
                    # Calculate load percentage
                    load_pct = server.current_connections / server.max_connections if server.max_connections > 0 else 1.0
                    candidates.append((server_id, load_pct))
                
                if candidates:
                    # Sort by load percentage (ascending)
                    candidates.sort(key=lambda x: x[1])
                    server_id = candidates[0][0]
                    return self.servers[server_id]
            
            # If we get here, we couldn't find a suitable server
            logger.error(
                f"No suitable server found for {transaction_type.value} transaction "
                f"with policy {self.routing_policy.value}"
            )
            return None
    
    def get_session(
        self,
        transaction_type: TransactionType = TransactionType.READ,
        region: str = None
    ) -> Tuple[Optional[Session], Optional[str]]:
        """
        Get a database session from an appropriate server
        
        Args:
            transaction_type: Type of transaction
            region: Optional region preference
            
        Returns:
            tuple: (session, server_id) or (None, None) if no session available
        """
        server = self.get_server_for_transaction(transaction_type, region)
        
        if not server:
            return None, None
        
        session = server.get_session()
        
        if not session:
            logger.error(f"Failed to get session from server {server.server_id}")
            return None, None
        
        return session, server.server_id
    
    def release_session(self, session: Session, server_id: str) -> None:
        """
        Release a database session
        
        Args:
            session: SQLAlchemy session to release
            server_id: ID of the server that provided the session
        """
        if server_id not in self.servers:
            # Server might have been removed
            session.close()
            return
        
        server = self.servers[server_id]
        server.release_session(session)
    
    def execute_distributed_transaction(
        self,
        tx_id: str,
        operations: List[Dict[str, Any]],
        callback: Callable = None
    ) -> Dict[str, Any]:
        """
        Execute a distributed transaction across the cluster
        
        Args:
            tx_id: Transaction ID
            operations: List of operations to perform
            callback: Optional callback function to call when transaction completes
            
        Returns:
            dict: Transaction result
        """
        # Submit to cluster manager for distributed consensus
        if cluster.get_cluster_manager():
            tx_data = {
                'id': tx_id,
                'type': 'db_transaction',
                'cluster_id': self.cluster_id,
                'operations': operations,
                'timestamp': datetime.now().isoformat()
            }
            
            success, message, tx_id = cluster.get_cluster_manager().execute_transaction(tx_data)
            
            if success:
                # Transaction submitted successfully
                result = {
                    'status': 'submitted',
                    'message': message,
                    'transaction_id': tx_id
                }
                
                # Register callback if provided
                if callback:
                    cluster.get_cluster_manager().register_transaction_callback(tx_id, callback)
                
                return result
            else:
                # Forward to leader if needed
                leader_info = cluster.get_cluster_manager().get_leader()
                
                if leader_info:
                    return {
                        'status': 'forward',
                        'message': message,
                        'leader': leader_info
                    }
                else:
                    return {
                        'status': 'error',
                        'message': f"Failed to submit transaction and no leader available: {message}"
                    }
        else:
            # No cluster manager, execute locally
            try:
                # Get session from primary
                session, server_id = self.get_session(TransactionType.WRITE)
                
                if not session:
                    return {
                        'status': 'error',
                        'message': "Failed to get database session from primary"
                    }
                
                try:
                    # Start transaction
                    session.begin()
                    
                    # Execute operations
                    results = []
                    for op in operations:
                        op_type = op.get('type')
                        
                        if op_type == 'execute':
                            # Execute raw SQL
                            sql = op.get('sql')
                            params = op.get('params', {})
                            
                            if not sql:
                                raise ValueError("No SQL provided for execute operation")
                            
                            result = session.execute(text(sql), params)
                            
                            if op.get('fetch_one', False):
                                row = result.fetchone()
                                results.append(row._asdict() if row else None)
                            elif op.get('fetch_all', False):
                                rows = result.fetchall()
                                results.append([row._asdict() for row in rows])
                            else:
                                results.append({'rowcount': result.rowcount})
                        
                        elif op_type == 'commit':
                            # Commit transaction
                            session.commit()
                            results.append({'committed': True})
                        
                        elif op_type == 'rollback':
                            # Rollback transaction
                            session.rollback()
                            results.append({'rolled_back': True})
                    
                    # Commit if no explicit commit/rollback
                    if all(op.get('type') not in ('commit', 'rollback') for op in operations):
                        session.commit()
                    
                    return {
                        'status': 'success',
                        'transaction_id': tx_id,
                        'results': results
                    }
                
                except Exception as e:
                    # Rollback on error
                    try:
                        session.rollback()
                    except:
                        pass
                    
                    logger.error(f"Error executing transaction {tx_id}: {str(e)}")
                    
                    return {
                        'status': 'error',
                        'transaction_id': tx_id,
                        'message': str(e)
                    }
                
                finally:
                    # Release session
                    self.release_session(session, server_id)
            
            except Exception as e:
                logger.error(f"Error setting up transaction {tx_id}: {str(e)}")
                
                return {
                    'status': 'error',
                    'transaction_id': tx_id,
                    'message': str(e)
                }
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """
        Get the status of the database cluster
        
        Returns:
            dict: Cluster status information
        """
        with self.lock:
            status = {
                'cluster_id': self.cluster_id,
                'routing_policy': self.routing_policy.value,
                'primary_id': self.primary_id,
                'server_count': len(self.servers),
                'online_servers': sum(1 for s in self.servers.values() if s.status == DatabaseStatus.ONLINE),
                'degraded_servers': sum(1 for s in self.servers.values() if s.status == DatabaseStatus.DEGRADED),
                'offline_servers': sum(1 for s in self.servers.values() if s.status == DatabaseStatus.OFFLINE),
                'last_failover': self.last_failover,
                'servers': {
                    server_id: server.get_status()
                    for server_id, server in self.servers.items()
                }
            }
            
            return status


class HASession:
    """
    High-availability database session wrapper
    Provides automatic routing and failover handling
    """
    
    def __init__(self, cluster: DatabaseCluster, transaction_type: TransactionType = TransactionType.READ):
        """
        Initialize a high-availability session
        
        Args:
            cluster: DatabaseCluster instance
            transaction_type: Type of transaction
        """
        self.cluster = cluster
        self.transaction_type = transaction_type
        self.session = None
        self.server_id = None
        self.is_transaction_active = False
    
    def __enter__(self):
        """Context manager entry"""
        self.session, self.server_id = self.cluster.get_session(self.transaction_type)
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            # Rollback if exception occurred
            if exc_type and self.is_transaction_active:
                try:
                    self.session.rollback()
                except:
                    pass
            
            # Release session
            self.cluster.release_session(self.session, self.server_id)
            self.session = None
            self.server_id = None
            self.is_transaction_active = False
    
    def begin(self):
        """Begin a transaction"""
        if self.session:
            self.session.begin()
            self.is_transaction_active = True
    
    def commit(self):
        """Commit the transaction"""
        if self.session:
            self.session.commit()
            self.is_transaction_active = False
    
    def rollback(self):
        """Rollback the transaction"""
        if self.session:
            self.session.rollback()
            self.is_transaction_active = False


# Global database cluster instance
_db_cluster = None

def get_db_cluster() -> Optional[DatabaseCluster]:
    """
    Get the global database cluster instance
    
    Returns:
        DatabaseCluster: The global database cluster instance
    """
    return _db_cluster

def init_ha_database():
    """Initialize the high-availability database cluster"""
    global _db_cluster
    
    if _db_cluster:
        return _db_cluster
    
    # Read configuration from environment
    routing_policy_str = os.environ.get('DB_ROUTING_POLICY', 'primary_write_replica_read')
    routing_policy = RoutingPolicy[routing_policy_str.upper()] if routing_policy_str.upper() in RoutingPolicy.__members__ else RoutingPolicy.PRIMARY_WRITE_REPLICA_READ
    
    # Create the cluster
    _db_cluster = DatabaseCluster(
        cluster_id="main_db_cluster",
        routing_policy=routing_policy
    )
    
    # Add primary server (required)
    primary_url = os.environ.get('DATABASE_URL')
    
    if not primary_url:
        logger.error("DATABASE_URL environment variable not set, cannot initialize database cluster")
        return None
    
    # Add primary server
    primary = DatabaseServer(
        server_id="primary",
        connection_url=primary_url,
        role=DatabaseRole.PRIMARY,
        region=os.environ.get('DATABASE_REGION', 'default')
    )
    
    _db_cluster.add_server(primary)
    
    # Add replica servers if configured
    replica_urls = os.environ.get('DATABASE_REPLICA_URLS')
    if replica_urls:
        replicas = replica_urls.split(',')
        for i, replica_url in enumerate(replicas):
            replica = DatabaseServer(
                server_id=f"replica_{i+1}",
                connection_url=replica_url.strip(),
                role=DatabaseRole.REPLICA,
                region=os.environ.get(f'DATABASE_REPLICA_{i+1}_REGION', os.environ.get('DATABASE_REGION', 'default'))
            )
            _db_cluster.add_server(replica)
    
    # Add analytics servers if configured
    analytics_urls = os.environ.get('DATABASE_ANALYTICS_URLS')
    if analytics_urls:
        analytics_servers = analytics_urls.split(',')
        for i, analytics_url in enumerate(analytics_servers):
            analytics = DatabaseServer(
                server_id=f"analytics_{i+1}",
                connection_url=analytics_url.strip(),
                role=DatabaseRole.ANALYTICS,
                region=os.environ.get(f'DATABASE_ANALYTICS_{i+1}_REGION', os.environ.get('DATABASE_REGION', 'default'))
            )
            _db_cluster.add_server(analytics)
    
    # Start the cluster
    _db_cluster.start()
    
    logger.info(f"Initialized high-availability database cluster with routing policy {routing_policy.value}")
    return _db_cluster

def shutdown_ha_database():
    """Shutdown the high-availability database cluster"""
    global _db_cluster
    
    if _db_cluster:
        logger.info("Shutting down high-availability database cluster")
        _db_cluster.stop()
        _db_cluster = None

def get_db_session(transaction_type: TransactionType = TransactionType.READ) -> HASession:
    """
    Get a high-availability database session
    
    Args:
        transaction_type: Type of transaction
        
    Returns:
        HASession: High-availability session wrapper
    """
    cluster = get_db_cluster()
    
    if not cluster:
        # Initialize if not already done
        cluster = init_ha_database()
        
        if not cluster:
            raise RuntimeError("Failed to initialize database cluster")
    
    return HASession(cluster, transaction_type)

def execute_distributed_sql(sql: str, params: Dict[str, Any] = None, tx_id: str = None) -> Dict[str, Any]:
    """
    Execute a SQL statement with distributed consensus
    
    Args:
        sql: SQL statement to execute
        params: SQL parameters
        tx_id: Optional transaction ID
        
    Returns:
        dict: Result of the operation
    """
    cluster = get_db_cluster()
    
    if not cluster:
        raise RuntimeError("Database cluster not initialized")
    
    # Generate transaction ID if not provided
    if not tx_id:
        tx_id = f"sql_{int(time.time())}_{random.randint(1000, 9999)}"
    
    # Define the operation
    operations = [{
        'type': 'execute',
        'sql': sql,
        'params': params or {},
        'fetch_all': True
    }]
    
    # Execute with distributed consensus
    return cluster.execute_distributed_transaction(tx_id, operations)