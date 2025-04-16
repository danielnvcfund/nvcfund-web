"""
High-Availability Clustering Module for NVC Banking Platform
This module provides clustering, load balancing, and failover capabilities 
for enterprise-scale banking operations.
"""

import os
import time
import logging
import threading
import socket
import json
import hashlib
import random
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set, Callable
from datetime import datetime, timedelta

# Configure logger
logger = logging.getLogger(__name__)

# Cluster roles
class NodeRole(Enum):
    """Roles that a node can take in the cluster"""
    LEADER = "leader"       # Primary node directing cluster operations
    FOLLOWER = "follower"   # Secondary node that follows the leader
    CANDIDATE = "candidate" # Node seeking leadership during election
    OBSERVER = "observer"   # Node monitoring but not participating in consensus

# Cluster states
class ClusterState(Enum):
    """States of the cluster as a whole"""
    INITIALIZING = "initializing"  # Cluster is starting up
    STABLE = "stable"              # Cluster is stable with a leader
    ELECTION = "election"          # Cluster is in election process
    DEGRADED = "degraded"          # Cluster is operating in a degraded state
    SPLIT = "split"                # Network split detected

# Health status
class HealthStatus(Enum):
    """Health status of a node"""
    HEALTHY = "healthy"            # Node is fully operational
    DEGRADED = "degraded"          # Node is operational but with issues
    UNHEALTHY = "unhealthy"        # Node is not operational

class ClusterNode:
    """
    Represents a node in the high-availability cluster.
    Implements the Raft consensus algorithm for leader election and replication.
    """
    
    def __init__(
        self, 
        node_id: str, 
        host: str, 
        port: int,
        cluster_nodes: Dict[str, Dict[str, Any]] = None,
        data_dir: str = None,
        heartbeat_interval: float = 0.5,
        election_timeout_min: float = 1.5,
        election_timeout_max: float = 3.0
    ):
        """
        Initialize a cluster node
        
        Args:
            node_id: Unique identifier for this node
            host: Host where this node is running
            port: Port where this node is listening
            cluster_nodes: Dictionary of other nodes in the cluster
            data_dir: Directory to store cluster state data
            heartbeat_interval: Time between heartbeats (in seconds)
            election_timeout_min: Minimum election timeout (in seconds)
            election_timeout_max: Maximum election timeout (in seconds)
        """
        self.node_id = node_id
        self.host = host
        self.port = port
        self.address = f"{host}:{port}"
        self.data_dir = data_dir or os.path.join(os.getcwd(), "cluster_data")
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Cluster membership
        self.cluster_nodes = cluster_nodes or {}
        if node_id not in self.cluster_nodes:
            self.cluster_nodes[node_id] = {
                "host": host,
                "port": port,
                "address": self.address,
                "last_seen": datetime.now().isoformat(),
                "health": HealthStatus.HEALTHY.value
            }
        
        # Raft state
        self.current_term = 0
        self.voted_for = None
        self.log = []
        self.commit_index = 0
        self.last_applied = 0
        
        # Leader state
        self.next_index = {}  # For each node, index of the next log entry to send
        self.match_index = {}  # For each node, index of highest log entry known to be replicated
        
        # Leader election
        self.role = NodeRole.FOLLOWER
        self.leader_id = None
        self.heartbeat_interval = heartbeat_interval
        self.election_timeout_min = election_timeout_min
        self.election_timeout_max = election_timeout_max
        self.election_timeout = self._generate_election_timeout()
        self.last_heartbeat_time = time.time()
        
        # Cluster state
        self.cluster_state = ClusterState.INITIALIZING
        self.health_status = HealthStatus.HEALTHY
        
        # Thread control
        self.running = False
        self.election_timer = None
        self.heartbeat_timer = None
        self.state_persistor_timer = None
        
        # Transaction cache for distributed consensus
        self.transaction_cache = {}
        self.transaction_lock = threading.Lock()
        
        # Load saved state if available
        self._load_state()
        
        logger.info(f"Node {node_id} initialized at {self.address}")
    
    def _generate_election_timeout(self) -> float:
        """Generate a random election timeout"""
        return random.uniform(self.election_timeout_min, self.election_timeout_max)
    
    def _load_state(self) -> None:
        """Load persisted state if available"""
        state_file = os.path.join(self.data_dir, f"node_{self.node_id}_state.json")
        try:
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.current_term = state.get('current_term', 0)
                    self.voted_for = state.get('voted_for')
                    self.log = state.get('log', [])
                    logger.info(f"Node {self.node_id} loaded persistent state. Term: {self.current_term}")
            else:
                logger.info(f"No persistent state found for node {self.node_id}, starting fresh")
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
    
    def _save_state(self) -> None:
        """Save persistent state to disk"""
        state_file = os.path.join(self.data_dir, f"node_{self.node_id}_state.json")
        try:
            state = {
                'current_term': self.current_term,
                'voted_for': self.voted_for,
                'log': self.log
            }
            with open(state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
    
    def start(self) -> None:
        """Start the node's operation in the cluster"""
        if self.running:
            logger.warning(f"Node {self.node_id} is already running")
            return
        
        self.running = True
        logger.info(f"Starting node {self.node_id} in {self.role.value} role")
        
        # Start election timer
        self._reset_election_timer()
        
        # Start state persistor thread
        self.state_persistor_timer = threading.Timer(5.0, self._state_persistor_loop)
        self.state_persistor_timer.daemon = True
        self.state_persistor_timer.start()
    
    def stop(self) -> None:
        """Stop the node's operation in the cluster"""
        logger.info(f"Stopping node {self.node_id}")
        self.running = False
        
        # Cancel timers
        if self.election_timer:
            self.election_timer.cancel()
        
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
            
        if self.state_persistor_timer:
            self.state_persistor_timer.cancel()
        
        # Save state before stopping
        self._save_state()
    
    def _reset_election_timer(self) -> None:
        """Reset the election timeout"""
        if self.election_timer:
            self.election_timer.cancel()
        
        if not self.running:
            return
        
        if self.role != NodeRole.LEADER:
            self.election_timeout = self._generate_election_timeout()
            self.election_timer = threading.Timer(self.election_timeout, self._start_election)
            self.election_timer.daemon = True
            self.election_timer.start()
    
    def _start_election(self) -> None:
        """Start a leader election"""
        if not self.running or self.role == NodeRole.LEADER:
            return
        
        self.role = NodeRole.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id  # Vote for self
        self.cluster_state = ClusterState.ELECTION
        
        logger.info(f"Node {self.node_id} starting election for term {self.current_term}")
        
        # Reset election timer
        self._reset_election_timer()
        
        # Request votes from all nodes
        votes_received = 1  # Count own vote
        votes_needed = (len(self.cluster_nodes) // 2) + 1
        
        # Prepare request vote message
        last_log_index = len(self.log) - 1 if self.log else -1
        last_log_term = self.log[last_log_index]['term'] if last_log_index >= 0 else 0
        
        for node_id, node_info in self.cluster_nodes.items():
            if node_id == self.node_id:
                continue
            
            # In a real implementation, you would send RPC to the node
            # Here we'll simulate with a direct function call
            granted = self._simulate_request_vote(node_id, {
                'term': self.current_term, 
                'candidate_id': self.node_id,
                'last_log_index': last_log_index,
                'last_log_term': last_log_term
            })
            
            if granted:
                votes_received += 1
            
            if votes_received >= votes_needed:
                self._become_leader()
                break
    
    def _simulate_request_vote(self, target_node_id: str, request: Dict[str, Any]) -> bool:
        """
        Simulate sending request vote RPC to another node
        In a real implementation, this would be a network call
        
        Args:
            target_node_id: ID of the node to request vote from
            request: Vote request parameters
            
        Returns:
            bool: Whether vote was granted
        """
        # This is a simulation - in a real implementation, send an RPC and wait for a response
        # Here we'll randomly decide whether the vote was granted based on health
        target_health = self.cluster_nodes.get(target_node_id, {}).get('health', HealthStatus.UNHEALTHY.value)
        
        if target_health == HealthStatus.UNHEALTHY.value:
            # Unhealthy nodes can't vote
            return False
        
        # Simulate a successful vote with high probability for healthy nodes
        if target_health == HealthStatus.HEALTHY.value:
            return random.random() < 0.8  # 80% chance of success
        else:
            return random.random() < 0.4  # 40% chance if degraded
    
    def _become_leader(self) -> None:
        """Become the leader of the cluster"""
        if not self.running:
            return
        
        logger.info(f"Node {self.node_id} becoming leader for term {self.current_term}")
        self.role = NodeRole.LEADER
        self.leader_id = self.node_id
        self.cluster_state = ClusterState.STABLE
        
        # Initialize leader state
        for node_id in self.cluster_nodes:
            self.next_index[node_id] = len(self.log)
            self.match_index[node_id] = 0
        
        # Cancel election timer
        if self.election_timer:
            self.election_timer.cancel()
        
        # Start sending heartbeats
        self._send_heartbeats()
    
    def _send_heartbeats(self) -> None:
        """Send heartbeats to all followers"""
        if not self.running or self.role != NodeRole.LEADER:
            return
        
        logger.debug(f"Leader {self.node_id} sending heartbeats")
        
        for node_id, node_info in self.cluster_nodes.items():
            if node_id == self.node_id:
                continue
            
            # In a real implementation, you would send append entries RPC to the node
            # Here we'll simulate with a direct function call
            self._simulate_append_entries(node_id, {
                'term': self.current_term,
                'leader_id': self.node_id,
                'prev_log_index': self.next_index[node_id] - 1,
                'prev_log_term': self.log[self.next_index[node_id] - 1]['term'] if self.next_index[node_id] > 0 and self.log else 0,
                'entries': [],  # No entries for heartbeat
                'leader_commit': self.commit_index
            })
        
        # Schedule next heartbeat
        if self.running and self.role == NodeRole.LEADER:
            self.heartbeat_timer = threading.Timer(self.heartbeat_interval, self._send_heartbeats)
            self.heartbeat_timer.daemon = True
            self.heartbeat_timer.start()
    
    def _simulate_append_entries(self, target_node_id: str, request: Dict[str, Any]) -> bool:
        """
        Simulate sending append entries RPC to another node
        In a real implementation, this would be a network call
        
        Args:
            target_node_id: ID of the node to send entries to
            request: Append entries request parameters
            
        Returns:
            bool: Whether entries were appended successfully
        """
        # Update last seen time for the target node
        if target_node_id in self.cluster_nodes:
            self.cluster_nodes[target_node_id]['last_seen'] = datetime.now().isoformat()
        
        # This is a simulation - in a real implementation, send an RPC and wait for a response
        # Here we'll randomly decide whether the append entries succeeded based on health
        target_health = self.cluster_nodes.get(target_node_id, {}).get('health', HealthStatus.UNHEALTHY.value)
        
        if target_health == HealthStatus.UNHEALTHY.value:
            return False
        
        # Simulate successful append with high probability for healthy nodes
        if target_health == HealthStatus.HEALTHY.value:
            return random.random() < 0.95  # 95% chance of success
        else:
            return random.random() < 0.6   # 60% chance if degraded
    
    def _receive_append_entries(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an append entries request from a leader
        
        Args:
            request: The append entries request
            
        Returns:
            dict: The response
        """
        term = request.get('term', 0)
        leader_id = request.get('leader_id')
        prev_log_index = request.get('prev_log_index', 0)
        prev_log_term = request.get('prev_log_term', 0)
        entries = request.get('entries', [])
        leader_commit = request.get('leader_commit', 0)
        
        response = {'term': self.current_term, 'success': False}
        
        # If term is older, reject
        if term < self.current_term:
            return response
        
        # If this is a newer term, update our term and step down if we're a leader or candidate
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None
            if self.role in (NodeRole.LEADER, NodeRole.CANDIDATE):
                self.role = NodeRole.FOLLOWER
        
        # This is a valid append entries from the current leader
        self.last_heartbeat_time = time.time()
        self._reset_election_timer()
        
        if self.role != NodeRole.FOLLOWER:
            self.role = NodeRole.FOLLOWER
        
        self.leader_id = leader_id
        self.cluster_state = ClusterState.STABLE
        
        # Check if our log is consistent with the leader's
        log_ok = (prev_log_index == 0) or (
            prev_log_index > 0 and 
            prev_log_index <= len(self.log) and 
            (prev_log_index == 0 or self.log[prev_log_index - 1]['term'] == prev_log_term)
        )
        
        if not log_ok:
            # Our log doesn't match the leader's, we need to fix it
            return response
        
        # If we have conflicting entries, remove them
        if entries and prev_log_index < len(self.log):
            self.log = self.log[:prev_log_index]
        
        # Append new entries to our log
        for entry in entries:
            self.log.append(entry)
        
        # Update commit index if leader committed more entries
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log))
        
        response['success'] = True
        return response
    
    def _state_persistor_loop(self) -> None:
        """Periodically save state to disk"""
        if not self.running:
            return
        
        self._save_state()
        
        # Check health of other nodes
        self._check_node_health()
        
        # Schedule next run
        if self.running:
            self.state_persistor_timer = threading.Timer(5.0, self._state_persistor_loop)
            self.state_persistor_timer.daemon = True
            self.state_persistor_timer.start()
    
    def _check_node_health(self) -> None:
        """Check the health of all nodes in the cluster"""
        now = datetime.now()
        unhealthy_threshold = now - timedelta(seconds=10)
        degraded_threshold = now - timedelta(seconds=5)
        
        unhealthy_nodes = 0
        total_nodes = len(self.cluster_nodes)
        
        for node_id, node_info in self.cluster_nodes.items():
            if node_id == self.node_id:
                continue  # Skip self
            
            last_seen_str = node_info.get('last_seen')
            if not last_seen_str:
                node_info['health'] = HealthStatus.UNHEALTHY.value
                unhealthy_nodes += 1
                continue
            
            try:
                last_seen = datetime.fromisoformat(last_seen_str)
                
                if last_seen < unhealthy_threshold:
                    node_info['health'] = HealthStatus.UNHEALTHY.value
                    unhealthy_nodes += 1
                elif last_seen < degraded_threshold:
                    node_info['health'] = HealthStatus.DEGRADED.value
                else:
                    node_info['health'] = HealthStatus.HEALTHY.value
            except ValueError:
                node_info['health'] = HealthStatus.UNHEALTHY.value
                unhealthy_nodes += 1
        
        # Update cluster state based on health
        if unhealthy_nodes > (total_nodes // 2):
            self.cluster_state = ClusterState.DEGRADED
        elif unhealthy_nodes > 0:
            # Some nodes are unhealthy but majority is still functioning
            if self.cluster_state != ClusterState.ELECTION:
                self.cluster_state = ClusterState.STABLE
        else:
            # All nodes are healthy
            if self.cluster_state != ClusterState.ELECTION:
                self.cluster_state = ClusterState.STABLE
    
    def apply_transaction(self, transaction: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Apply a transaction to the cluster
        
        Args:
            transaction: Transaction data to apply
            
        Returns:
            tuple: (success, message)
        """
        if not self.running:
            return False, "Node is not running"
        
        if self.role != NodeRole.LEADER:
            if self.leader_id and self.leader_id in self.cluster_nodes:
                leader_addr = f"{self.cluster_nodes[self.leader_id]['host']}:{self.cluster_nodes[self.leader_id]['port']}"
                return False, f"Not the leader. Forward to {leader_addr}"
            else:
                return False, "Not the leader and no leader is known"
        
        # Generate a unique transaction ID if not provided
        tx_id = transaction.get('id')
        if not tx_id:
            tx_id = hashlib.sha256(f"{time.time()}:{json.dumps(transaction)}".encode()).hexdigest()
            transaction['id'] = tx_id
        
        # Add entry to log
        log_entry = {
            'term': self.current_term,
            'command': transaction,
            'timestamp': datetime.now().isoformat()
        }
        
        with self.transaction_lock:
            self.log.append(log_entry)
            log_index = len(self.log) - 1
            
            # Save to transaction cache for tracking
            self.transaction_cache[tx_id] = {
                'status': 'pending',
                'index': log_index,
                'timestamp': datetime.now().isoformat()
            }
        
        # Replicate to followers and wait for majority confirmation
        # In a real implementation, this would be asynchronous
        # For simplicity, we'll simulate direct responses
        
        success_count = 1  # Count self
        needed_count = (len(self.cluster_nodes) // 2) + 1
        
        for node_id, node_info in self.cluster_nodes.items():
            if node_id == self.node_id:
                continue
            
            # Simulate appending to follower
            if self._simulate_append_entries(node_id, {
                'term': self.current_term,
                'leader_id': self.node_id,
                'prev_log_index': log_index - 1,
                'prev_log_term': self.log[log_index - 1]['term'] if log_index > 0 else 0,
                'entries': [log_entry],
                'leader_commit': self.commit_index
            }):
                success_count += 1
                self.match_index[node_id] = log_index
                self.next_index[node_id] = log_index + 1
            else:
                # If append fails, we would decrement next_index and retry in a real implementation
                # For simplicity, we'll just note the failure
                logger.warning(f"Failed to replicate transaction {tx_id} to node {node_id}")
        
        # Check if we have replicated to a majority
        if success_count >= needed_count:
            # Update commit index to include this entry
            if log_index > self.commit_index:
                self.commit_index = log_index
            
            # Mark transaction as committed
            with self.transaction_lock:
                self.transaction_cache[tx_id]['status'] = 'committed'
            
            return True, f"Transaction {tx_id} committed"
        else:
            # Mark transaction as failed
            with self.transaction_lock:
                self.transaction_cache[tx_id]['status'] = 'failed'
            
            return False, f"Failed to replicate transaction {tx_id} to majority of nodes"
    
    def get_transaction_status(self, tx_id: str) -> Dict[str, Any]:
        """
        Get the status of a transaction
        
        Args:
            tx_id: Transaction ID
            
        Returns:
            dict: Transaction status or None if not found
        """
        with self.transaction_lock:
            return self.transaction_cache.get(tx_id)
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """
        Get the status of the cluster
        
        Returns:
            dict: Cluster status information
        """
        return {
            'node_id': self.node_id,
            'role': self.role.value,
            'leader_id': self.leader_id,
            'term': self.current_term,
            'cluster_state': self.cluster_state.value,
            'health': self.health_status.value,
            'commit_index': self.commit_index,
            'last_applied': self.last_applied,
            'log_size': len(self.log),
            'nodes': {
                node_id: {
                    'address': info['address'],
                    'health': info['health'],
                    'last_seen': info['last_seen']
                } for node_id, info in self.cluster_nodes.items()
            }
        }


class ClusterManager:
    """
    Manages a cluster of nodes for high-availability operations.
    Provides interfaces for client applications to interact with the cluster.
    """
    
    def __init__(
        self, 
        node_id: str, 
        host: str, 
        port: int,
        seed_nodes: List[Dict[str, Any]] = None,
        data_dir: str = None
    ):
        """
        Initialize the cluster manager
        
        Args:
            node_id: Unique identifier for this node
            host: Host where this node is running
            port: Port where this node is listening
            seed_nodes: List of seed nodes to join the cluster
            data_dir: Directory to store cluster state data
        """
        self.node_id = node_id
        self.host = host
        self.port = port
        
        # Initialize cluster nodes from seed nodes
        cluster_nodes = {}
        if seed_nodes:
            for node in seed_nodes:
                node_id = node.get('id')
                if node_id:
                    cluster_nodes[node_id] = {
                        'host': node.get('host', 'localhost'),
                        'port': node.get('port', 7000),
                        'address': f"{node.get('host', 'localhost')}:{node.get('port', 7000)}",
                        'last_seen': datetime.now().isoformat(),
                        'health': HealthStatus.HEALTHY.value
                    }
        
        # Create the node instance
        self.node = ClusterNode(
            node_id=node_id,
            host=host,
            port=port,
            cluster_nodes=cluster_nodes,
            data_dir=data_dir
        )
        
        # Transaction callback registry for distributed transactions
        self.transaction_callbacks = {}
        
        # Cache of known leaders for routing client requests
        self.leader_cache = {
            'id': None,
            'address': None,
            'last_updated': None
        }
        
        logger.info(f"Cluster manager initialized for node {node_id}")
    
    def start(self) -> None:
        """Start the cluster node"""
        self.node.start()
    
    def stop(self) -> None:
        """Stop the cluster node"""
        self.node.stop()
    
    def join_cluster(self, seed_address: str) -> bool:
        """
        Join an existing cluster using a seed node
        
        Args:
            seed_address: Address of a node in the cluster to join
            
        Returns:
            bool: Whether join was successful
        """
        if not self.node.running:
            logger.error("Cannot join cluster - node is not running")
            return False
        
        try:
            # In a real implementation, we would connect to the seed node and get the cluster information
            # For this simulation, we'll just add a fake node
            
            # Parse seed address
            parts = seed_address.split(':')
            if len(parts) != 2:
                logger.error(f"Invalid seed address format: {seed_address}")
                return False
            
            seed_host, seed_port = parts
            seed_port = int(seed_port)
            
            # Generate a seed node ID
            seed_id = f"seed_node_{seed_host}_{seed_port}"
            
            # Add seed node to our cluster nodes
            self.node.cluster_nodes[seed_id] = {
                'host': seed_host,
                'port': seed_port,
                'address': seed_address,
                'last_seen': datetime.now().isoformat(),
                'health': HealthStatus.HEALTHY.value
            }
            
            logger.info(f"Node {self.node_id} joined cluster via seed node {seed_address}")
            return True
            
        except Exception as e:
            logger.error(f"Error joining cluster: {str(e)}")
            return False
    
    def execute_transaction(self, transaction_data: Dict[str, Any], callback: Callable = None) -> Tuple[bool, str, Optional[str]]:
        """
        Execute a transaction across the cluster
        
        Args:
            transaction_data: The transaction data to execute
            callback: Optional callback function to call when transaction completes
            
        Returns:
            tuple: (success, message, transaction_id)
        """
        # Generate transaction ID if not provided
        tx_id = transaction_data.get('id')
        if not tx_id:
            tx_id = hashlib.sha256(f"{time.time()}:{json.dumps(transaction_data)}".encode()).hexdigest()
            transaction_data['id'] = tx_id
        
        # If we're the leader, apply directly
        if self.node.role == NodeRole.LEADER:
            success, message = self.node.apply_transaction(transaction_data)
            
            if callback:
                self.transaction_callbacks[tx_id] = callback
            
            return success, message, tx_id
        
        # Otherwise, forward to the leader if known
        if self.node.leader_id and self.node.leader_id in self.node.cluster_nodes:
            leader_info = self.node.cluster_nodes[self.node.leader_id]
            leader_addr = f"{leader_info['host']}:{leader_info['port']}"
            
            # Update leader cache
            self.leader_cache = {
                'id': self.node.leader_id,
                'address': leader_addr,
                'last_updated': datetime.now().isoformat()
            }
            
            # In a real implementation, we would forward to the leader
            # For this simulation, we'll just return the forward info
            if callback:
                self.transaction_callbacks[tx_id] = callback
                
            return False, f"Not the leader. Forward to {leader_addr}", tx_id
        
        # No leader known, transaction cannot be processed
        return False, "Cannot process transaction - no leader known", tx_id
    
    def get_transaction_status(self, tx_id: str) -> Dict[str, Any]:
        """
        Get the status of a transaction
        
        Args:
            tx_id: Transaction ID
            
        Returns:
            dict: Transaction status information
        """
        status = self.node.get_transaction_status(tx_id)
        
        if not status and self.node.leader_id and self.node.leader_id in self.node.cluster_nodes:
            # Transaction not found locally, might be on the leader
            leader_info = self.node.cluster_nodes[self.node.leader_id]
            leader_addr = f"{leader_info['host']}:{leader_info['port']}"
            
            # In a real implementation, we would forward the request to the leader
            # For this simulation, we'll just return that it should be forwarded
            return {'status': 'unknown', 'message': f"Transaction not found. Try leader at {leader_addr}"}
        
        return status or {'status': 'unknown', 'message': "Transaction not found"}
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """
        Get the status of the cluster
        
        Returns:
            dict: Cluster status information
        """
        return self.node.get_cluster_status()
    
    def is_leader(self) -> bool:
        """
        Check if this node is the leader
        
        Returns:
            bool: Whether this node is the leader
        """
        return self.node.role == NodeRole.LEADER
    
    def get_leader(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current leader
        
        Returns:
            dict: Leader information or None if no leader known
        """
        if self.node.leader_id and self.node.leader_id in self.node.cluster_nodes:
            leader_info = self.node.cluster_nodes[self.node.leader_id]
            return {
                'id': self.node.leader_id,
                'address': f"{leader_info['host']}:{leader_info['port']}",
                'host': leader_info['host'],
                'port': leader_info['port']
            }
        return None
    
    def register_transaction_callback(self, tx_id: str, callback: Callable) -> None:
        """
        Register a callback for a transaction
        
        Args:
            tx_id: Transaction ID
            callback: Callback function to call when transaction status changes
        """
        self.transaction_callbacks[tx_id] = callback


def initialize_cluster_node(
    node_id: str = None, 
    host: str = None, 
    port: int = None,
    seed_nodes: List[Dict[str, Any]] = None
) -> ClusterManager:
    """
    Initialize a cluster node with default values if not provided
    
    Args:
        node_id: Unique identifier for this node
        host: Host where this node is running
        port: Port where this node is listening
        seed_nodes: List of seed nodes to join the cluster
        
    Returns:
        ClusterManager: Initialized cluster manager instance
    """
    # Generate node ID if not provided
    if not node_id:
        hostname = socket.gethostname()
        node_id = f"node_{hostname}_{int(time.time())}"
    
    # Default host and port
    host = host or "0.0.0.0"
    port = port or 7000
    
    # Create and start the cluster manager
    manager = ClusterManager(
        node_id=node_id,
        host=host,
        port=port,
        seed_nodes=seed_nodes
    )
    
    return manager


# Global cluster manager instance for the application
_cluster_manager = None

def get_cluster_manager() -> Optional[ClusterManager]:
    """
    Get the global cluster manager instance
    
    Returns:
        ClusterManager: The global cluster manager instance
    """
    return _cluster_manager

def init_cluster():
    """Initialize the cluster manager for the application"""
    global _cluster_manager
    
    if _cluster_manager:
        return _cluster_manager
    
    # Read configuration from environment
    node_id = os.environ.get('CLUSTER_NODE_ID')
    host = os.environ.get('CLUSTER_HOST', '0.0.0.0')
    port = int(os.environ.get('CLUSTER_PORT', '7000'))
    
    # Parse seed nodes if provided
    seed_nodes = None
    seed_nodes_str = os.environ.get('CLUSTER_SEED_NODES')
    if seed_nodes_str:
        try:
            seed_nodes = []
            for node_info in seed_nodes_str.split(','):
                parts = node_info.split(':')
                if len(parts) == 3:  # id:host:port format
                    seed_nodes.append({
                        'id': parts[0],
                        'host': parts[1],
                        'port': int(parts[2])
                    })
                elif len(parts) == 2:  # host:port format
                    host, port = parts
                    seed_id = f"seed_{host}_{port}"
                    seed_nodes.append({
                        'id': seed_id,
                        'host': host,
                        'port': int(port)
                    })
        except Exception as e:
            logger.error(f"Error parsing seed nodes: {str(e)}")
    
    # Initialize cluster manager
    _cluster_manager = initialize_cluster_node(
        node_id=node_id,
        host=host,
        port=port,
        seed_nodes=seed_nodes
    )
    
    # Start the node
    _cluster_manager.start()
    
    # Join cluster if seed nodes provided
    if seed_nodes and seed_nodes[0]:
        seed = seed_nodes[0]
        seed_address = f"{seed['host']}:{seed['port']}"
        _cluster_manager.join_cluster(seed_address)
    
    logger.info(f"Initialized cluster manager with node ID {_cluster_manager.node_id}")
    return _cluster_manager

def shutdown_cluster():
    """Shutdown the cluster manager"""
    global _cluster_manager
    
    if _cluster_manager:
        logger.info("Shutting down cluster manager")
        _cluster_manager.stop()
        _cluster_manager = None
