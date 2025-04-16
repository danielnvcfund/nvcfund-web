// High Availability Dashboard JavaScript
// Get CSRF token from meta tag
const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

// Utility functions
function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    let uptimeString = '';
    if (days > 0) {
        uptimeString += `${days}d `;
    }
    if (hours > 0 || days > 0) {
        uptimeString += `${hours}h `;
    }
    if (minutes > 0 || hours > 0 || days > 0) {
        uptimeString += `${minutes}m `;
    }
    uptimeString += `${remainingSeconds}s`;
    
    return uptimeString;
}

function formatDateTime(timestamp) {
    if (!timestamp) return 'N/A';
    
    const date = new Date(timestamp);
    return date.toLocaleString();
}

// Notification helper
function showNotification(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    alertContainer.appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 500);
    }, 5000);
}

// Dashboard functions
function refreshHAStatus() {
    // Add loading indicators
    document.getElementById('ha-status').innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Loading...';
    document.getElementById('database-status').innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Loading...';
    document.getElementById('cluster-status').innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Loading...';
    
    // Clear existing status
    document.getElementById('ha-status-badge').textContent = 'Unknown';
    document.getElementById('db-status-badge').textContent = 'Unknown';
    document.getElementById('cluster-status-badge').textContent = 'Unknown';
    
    document.getElementById('ha-status-alert').className = 'alert alert-secondary';
    document.getElementById('database-status-alert').className = 'alert alert-secondary';
    document.getElementById('cluster-status-alert').className = 'alert alert-secondary';
    
    fetch('/api/v1/ha/status')
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const haStatus = document.getElementById('ha-status');
            const haStatusAlert = document.getElementById('ha-status-alert');
            const haStatusBadge = document.getElementById('ha-status-badge');
            
            const dbStatus = document.getElementById('database-status');
            const dbStatusAlert = document.getElementById('database-status-alert');
            const dbStatusBadge = document.getElementById('db-status-badge');
            
            const clusterStatus = document.getElementById('cluster-status');
            const clusterStatusAlert = document.getElementById('cluster-status-alert');
            const clusterStatusBadge = document.getElementById('cluster-status-badge');
            
            // Update HA status
            haStatus.textContent = data.ha_enabled ? 'Enabled' : 'Disabled';
            haStatusAlert.className = data.ha_enabled ? 'alert alert-success' : 'alert alert-warning';
            haStatusBadge.textContent = data.ha_enabled ? 'Enabled' : 'Disabled';
            haStatusBadge.className = data.ha_enabled ? 'badge bg-success' : 'badge bg-warning';
            
            // Update database status
            dbStatus.textContent = data.database.status;
            dbStatusBadge.textContent = data.database.status;
            
            if (data.database.status === 'healthy') {
                dbStatusAlert.className = 'alert alert-success';
                dbStatusBadge.className = 'badge bg-success';
            } else if (data.database.status === 'degraded') {
                dbStatusAlert.className = 'alert alert-warning';
                dbStatusBadge.className = 'badge bg-warning';
            } else {
                dbStatusAlert.className = 'alert alert-danger';
                dbStatusBadge.className = 'badge bg-danger';
            }
            
            // Update cluster status
            const clusterState = data.cluster.state;
            clusterStatus.textContent = clusterState.charAt(0).toUpperCase() + clusterState.slice(1);
            clusterStatusBadge.textContent = clusterState.charAt(0).toUpperCase() + clusterState.slice(1);
            
            if (clusterState === 'stable') {
                clusterStatusAlert.className = 'alert alert-success';
                clusterStatusBadge.className = 'badge bg-success';
            } else if (clusterState === 'election' || clusterState === 'initializing') {
                clusterStatusAlert.className = 'alert alert-warning';
                clusterStatusBadge.className = 'badge bg-warning';
            } else {
                clusterStatusAlert.className = 'alert alert-danger';
                clusterStatusBadge.className = 'badge bg-danger';
            }
        } else {
            console.error('Error fetching HA status:', data.message);
            showNotification(`Error fetching HA status: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error fetching HA status:', error);
        showNotification('Failed to load HA status. See console for details.', 'danger');
        
        document.getElementById('ha-status').textContent = 'Error loading';
        document.getElementById('database-status').textContent = 'Error loading';
        document.getElementById('cluster-status').textContent = 'Error loading';
    });
}

function refreshNodeInfo() {
    fetch('/api/v1/ha/node')
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Update node information
            document.getElementById('node-id').textContent = data.node_id || 'N/A';
            document.getElementById('node-hostname').textContent = data.hostname || 'N/A';
            document.getElementById('node-region').textContent = data.region || 'N/A';
            document.getElementById('node-uptime').textContent = data.uptime ? formatUptime(data.uptime) : 'N/A';
            document.getElementById('node-role').textContent = data.role || 'N/A';
            
            // Update leader information
            if (data.is_leader) {
                document.getElementById('leader-id').textContent = data.node_id;
                document.getElementById('leader-address').textContent = `${data.hostname}:${data.port}`;
            } else if (data.leader) {
                document.getElementById('leader-id').textContent = data.leader.id || 'Unknown';
                document.getElementById('leader-address').textContent = data.leader.address || 'Unknown';
                document.getElementById('leader-term').textContent = data.leader.term || 'N/A';
                document.getElementById('leader-commit-index').textContent = data.leader.commit_index || 'N/A';
            } else {
                document.getElementById('leader-id').textContent = 'No leader';
                document.getElementById('leader-address').textContent = 'N/A';
                document.getElementById('leader-term').textContent = 'N/A';
                document.getElementById('leader-commit-index').textContent = 'N/A';
            }
        } else {
            console.error('Error fetching node info:', data.message);
            showNotification(`Error fetching node info: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error fetching node info:', error);
        showNotification('Failed to load node information. See console for details.', 'danger');
    });
}

function refreshDatabaseServers() {
    const tableBody = document.getElementById('db-servers-table');
    tableBody.innerHTML = '<tr><td colspan="8" class="text-center"><div class="spinner-border" role="status"></div><span class="ms-2">Loading database servers...</span></td></tr>';
    
    fetch('/api/v1/ha/database/servers')
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            tableBody.innerHTML = '';
            
            if (data.servers && data.servers.length > 0) {
                data.servers.forEach(server => {
                    const row = document.createElement('tr');
                    row.className = 'server-row'; // Add class for styling and selection
                    
                    const idCell = document.createElement('td');
                    idCell.textContent = server.id || 'N/A';
                    
                    const roleCell = document.createElement('td');
                    const roleBadge = document.createElement('span');
                    roleBadge.textContent = server.role || 'unknown';
                    roleBadge.className = server.role === 'primary' ? 'badge bg-primary' : 'badge bg-secondary';
                    roleCell.appendChild(roleBadge);
                    
                    const hostCell = document.createElement('td');
                    hostCell.textContent = server.host || 'N/A';
                    
                    const regionCell = document.createElement('td');
                    regionCell.textContent = server.region || 'N/A';
                    
                    const statusCell = document.createElement('td');
                    const statusBadge = document.createElement('span');
                    statusBadge.textContent = server.status || 'unknown';
                    if (server.status === 'online') {
                        statusBadge.className = 'badge bg-success';
                    } else if (server.status === 'degraded') {
                        statusBadge.className = 'badge bg-warning';
                    } else {
                        statusBadge.className = 'badge bg-danger';
                    }
                    statusCell.appendChild(statusBadge);
                    
                    const connectionsCell = document.createElement('td');
                    connectionsCell.textContent = server.connections || '0';
                    
                    const latencyCell = document.createElement('td');
                    latencyCell.textContent = server.latency ? `${server.latency} ms` : 'N/A';
                    
                    const lagCell = document.createElement('td');
                    lagCell.textContent = server.replication_lag || 'N/A';
                    
                    row.appendChild(idCell);
                    row.appendChild(roleCell);
                    row.appendChild(hostCell);
                    row.appendChild(regionCell);
                    row.appendChild(statusCell);
                    row.appendChild(connectionsCell);
                    row.appendChild(latencyCell);
                    row.appendChild(lagCell);
                    
                    tableBody.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                const emptyCell = document.createElement('td');
                emptyCell.colSpan = 8;
                emptyCell.className = 'text-center';
                emptyCell.textContent = 'No database servers found';
                row.appendChild(emptyCell);
                tableBody.appendChild(row);
            }
            
            showNotification('Database servers refreshed successfully', 'success');
        } else {
            console.error('Error fetching database servers:', data.message);
            showNotification(`Error fetching database servers: ${data.message}`, 'danger');
            
            tableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Error loading database servers: ${data.message}</td></tr>`;
        }
    })
    .catch(error => {
        console.error('Error fetching database servers:', error);
        showNotification('Failed to load database servers. See console for details.', 'danger');
        
        tableBody.innerHTML = '<tr><td colspan="8" class="text-center text-danger">Failed to load database servers</td></tr>';
    });
}

function refreshClusterNodes() {
    const tableBody = document.getElementById('cluster-nodes-table');
    tableBody.innerHTML = '<tr><td colspan="4" class="text-center"><div class="spinner-border" role="status"></div><span class="ms-2">Loading cluster nodes...</span></td></tr>';
    
    fetch('/api/v1/ha/cluster/nodes')
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            tableBody.innerHTML = '';
            
            if (data.nodes && data.nodes.length > 0) {
                data.nodes.forEach(node => {
                    const row = document.createElement('tr');
                    row.className = 'node-row'; // Add class for styling and selection
                    
                    const idCell = document.createElement('td');
                    idCell.textContent = node.id || 'N/A';
                    
                    const addressCell = document.createElement('td');
                    addressCell.textContent = node.address || 'N/A';
                    
                    const healthCell = document.createElement('td');
                    const healthBadge = document.createElement('span');
                    healthBadge.textContent = node.health || 'unknown';
                    if (node.health === 'healthy') {
                        healthBadge.className = 'badge bg-success';
                    } else if (node.health === 'degraded') {
                        healthBadge.className = 'badge bg-warning';
                    } else {
                        healthBadge.className = 'badge bg-danger';
                    }
                    healthCell.appendChild(healthBadge);
                    
                    const lastSeenCell = document.createElement('td');
                    lastSeenCell.textContent = node.last_seen ? formatDateTime(node.last_seen) : 'N/A';
                    
                    row.appendChild(idCell);
                    row.appendChild(addressCell);
                    row.appendChild(healthCell);
                    row.appendChild(lastSeenCell);
                    
                    tableBody.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                const emptyCell = document.createElement('td');
                emptyCell.colSpan = 4;
                emptyCell.className = 'text-center';
                emptyCell.textContent = 'No cluster nodes found';
                row.appendChild(emptyCell);
                tableBody.appendChild(row);
            }
            
            showNotification('Cluster nodes refreshed successfully', 'success');
        } else {
            console.error('Error fetching cluster nodes:', data.message);
            showNotification(`Error fetching cluster nodes: ${data.message}`, 'danger');
            
            tableBody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Error loading cluster nodes: ${data.message}</td></tr>`;
        }
    })
    .catch(error => {
        console.error('Error fetching cluster nodes:', error);
        showNotification('Failed to load cluster nodes. See console for details.', 'danger');
        
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Failed to load cluster nodes</td></tr>';
    });
}

function refreshMetrics() {
    document.getElementById('app-metrics').innerHTML = '<tr><td colspan="2" class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div></td></tr>';
    document.getElementById('db-metrics').innerHTML = '<tr><td colspan="2" class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div></td></tr>';
    document.getElementById('cluster-metrics').innerHTML = '<tr><td colspan="2" class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div></td></tr>';
    
    fetch('/api/v1/ha/metrics')
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // App metrics
            const appMetricsTable = document.getElementById('app-metrics');
            appMetricsTable.innerHTML = '';
            
            if (data.app_metrics && Object.keys(data.app_metrics).length > 0) {
                Object.entries(data.app_metrics).forEach(([key, value]) => {
                    const row = document.createElement('tr');
                    const keyCell = document.createElement('td');
                    keyCell.textContent = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                    const valueCell = document.createElement('td');
                    valueCell.textContent = value;
                    row.appendChild(keyCell);
                    row.appendChild(valueCell);
                    appMetricsTable.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                const emptyCell = document.createElement('td');
                emptyCell.colSpan = 2;
                emptyCell.className = 'text-center';
                emptyCell.textContent = 'No metrics available';
                row.appendChild(emptyCell);
                appMetricsTable.appendChild(row);
            }
            
            // DB metrics
            const dbMetricsTable = document.getElementById('db-metrics');
            dbMetricsTable.innerHTML = '';
            
            if (data.db_metrics && Object.keys(data.db_metrics).length > 0) {
                Object.entries(data.db_metrics).forEach(([key, value]) => {
                    const row = document.createElement('tr');
                    const keyCell = document.createElement('td');
                    keyCell.textContent = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                    const valueCell = document.createElement('td');
                    valueCell.textContent = value;
                    row.appendChild(keyCell);
                    row.appendChild(valueCell);
                    dbMetricsTable.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                const emptyCell = document.createElement('td');
                emptyCell.colSpan = 2;
                emptyCell.className = 'text-center';
                emptyCell.textContent = 'No metrics available';
                row.appendChild(emptyCell);
                dbMetricsTable.appendChild(row);
            }
            
            // Cluster metrics
            const clusterMetricsTable = document.getElementById('cluster-metrics');
            clusterMetricsTable.innerHTML = '';
            
            if (data.cluster_metrics && Object.keys(data.cluster_metrics).length > 0) {
                Object.entries(data.cluster_metrics).forEach(([key, value]) => {
                    const row = document.createElement('tr');
                    const keyCell = document.createElement('td');
                    keyCell.textContent = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                    const valueCell = document.createElement('td');
                    valueCell.textContent = value;
                    row.appendChild(keyCell);
                    row.appendChild(valueCell);
                    clusterMetricsTable.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                const emptyCell = document.createElement('td');
                emptyCell.colSpan = 2;
                emptyCell.className = 'text-center';
                emptyCell.textContent = 'No metrics available';
                row.appendChild(emptyCell);
                clusterMetricsTable.appendChild(row);
            }
            
            showNotification('Metrics refreshed successfully', 'success');
        } else {
            console.error('Error fetching metrics:', data.message);
            showNotification(`Error fetching metrics: ${data.message}`, 'danger');
            
            document.getElementById('app-metrics').innerHTML = '<tr><td colspan="2" class="text-center text-danger">Error loading metrics</td></tr>';
            document.getElementById('db-metrics').innerHTML = '<tr><td colspan="2" class="text-center text-danger">Error loading metrics</td></tr>';
            document.getElementById('cluster-metrics').innerHTML = '<tr><td colspan="2" class="text-center text-danger">Error loading metrics</td></tr>';
        }
    })
    .catch(error => {
        console.error('Error fetching metrics:', error);
        showNotification('Failed to load metrics. See console for details.', 'danger');
        
        document.getElementById('app-metrics').innerHTML = '<tr><td colspan="2" class="text-center text-danger">Error loading metrics</td></tr>';
        document.getElementById('db-metrics').innerHTML = '<tr><td colspan="2" class="text-center text-danger">Error loading metrics</td></tr>';
        document.getElementById('cluster-metrics').innerHTML = '<tr><td colspan="2" class="text-center text-danger">Error loading metrics</td></tr>';
    });
}

function initiateFailover() {
    fetch('/api/v1/ha/database/failover', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showNotification(`Failover successful! New primary: ${data.new_primary}`, 'success');
            // Refresh database servers
            refreshDatabaseServers();
        } else {
            showNotification(`Failover failed: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error initiating failover:', error);
        showNotification('Error initiating failover. See console for details.', 'danger');
    });
}

function updateRoutingPolicy(policy) {
    fetch('/api/v1/ha/database/routing-policy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        credentials: 'same-origin',
        body: JSON.stringify({ policy: policy })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showNotification(`Policy updated to ${policy}`, 'success');
        } else {
            showNotification(`Failed to update policy: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error updating routing policy:', error);
        showNotification('Error updating routing policy. See console for details.', 'danger');
    });
}

function initiateBackup() {
    const statusElement = document.getElementById('backup-status');
    statusElement.innerHTML = '<div class="spinner-border spinner-border-sm me-2" role="status"></div> Initiating backup...';
    
    fetch('/api/v1/ha/database/backup', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            statusElement.innerHTML = `<div class="alert alert-success mt-2">Backup initiated successfully.<br>Timestamp: ${formatDateTime(data.timestamp)}</div>`;
            showNotification('Backup initiated successfully', 'success');
        } else {
            statusElement.innerHTML = `<div class="alert alert-danger mt-2">Backup failed: ${data.message}</div>`;
            showNotification(`Backup failed: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error initiating backup:', error);
        statusElement.innerHTML = '<div class="alert alert-danger mt-2">Error initiating backup. See console for details.</div>';
        showNotification('Error initiating backup. See console for details.', 'danger');
    });
}

function resetHAInfrastructure() {
    const statusElement = document.getElementById('reset-status');
    statusElement.innerHTML = '<div class="spinner-border spinner-border-sm me-2" role="status"></div> Resetting HA infrastructure...';
    
    fetch('/api/v1/ha/reset', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            statusElement.innerHTML = '<div class="alert alert-success mt-2">HA infrastructure reset successfully. Page will reload in 5 seconds...</div>';
            showNotification('HA infrastructure reset successfully. Page will reload in 5 seconds.', 'success');
            setTimeout(() => window.location.reload(), 5000);
        } else {
            statusElement.innerHTML = `<div class="alert alert-danger mt-2">Reset failed: ${data.message}</div>`;
            showNotification(`Reset failed: ${data.message}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error resetting HA infrastructure:', error);
        statusElement.innerHTML = '<div class="alert alert-danger mt-2">Error resetting infrastructure. See console for details.</div>';
        showNotification('Error resetting infrastructure. See console for details.', 'danger');
    });
}

function refreshAll() {
    refreshHAStatus();
    refreshNodeInfo();
    refreshDatabaseServers();
    refreshClusterNodes();
    refreshMetrics();
    
    // Show notification
    showNotification('All data refreshed successfully', 'success');
}

// Variables for refresh handling
let refreshInterval;
let isAutoRefreshEnabled = true;

function toggleAutoRefresh() {
    const toggleButton = document.getElementById('toggle-refresh');
    
    if (isAutoRefreshEnabled) {
        // Disable auto-refresh
        clearInterval(refreshInterval);
        isAutoRefreshEnabled = false;
        toggleButton.innerHTML = '<i class="fas fa-play"></i> Resume Auto-Refresh';
        toggleButton.classList.remove('btn-danger');
        toggleButton.classList.add('btn-success');
        showNotification('Auto-refresh paused', 'info');
    } else {
        // Enable auto-refresh
        startAutoRefresh();
        isAutoRefreshEnabled = true;
        toggleButton.innerHTML = '<i class="fas fa-pause"></i> Pause Auto-Refresh';
        toggleButton.classList.remove('btn-success');
        toggleButton.classList.add('btn-danger');
        showNotification('Auto-refresh resumed', 'info');
    }
}

function startAutoRefresh() {
    // Clear any existing interval
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    // Set new interval - refresh every 30 seconds
    refreshInterval = setInterval(refreshAll, 30000);
}

// Initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initial data load
    refreshAll();
    
    // Set up refresh triggers
    document.getElementById('refresh-all').addEventListener('click', function() {
        showNotification('Refreshing all data...', 'info');
        refreshAll();
    });
    
    document.getElementById('refresh-db-servers').addEventListener('click', function() {
        showNotification('Refreshing database servers...', 'info');
        refreshDatabaseServers();
    });
    
    document.getElementById('refresh-cluster-nodes').addEventListener('click', function() {
        showNotification('Refreshing cluster nodes...', 'info');
        refreshClusterNodes();
    });
    
    document.getElementById('refresh-metrics').addEventListener('click', function() {
        showNotification('Refreshing metrics...', 'info');
        refreshMetrics();
    });
    
    // Add toggle auto-refresh button under the main status card
    const statusCard = document.querySelector('.row.mb-4 .col-12 .card .card-header');
    if (statusCard) {
        const toggleButton = document.createElement('button');
        toggleButton.id = 'toggle-refresh';
        toggleButton.className = 'btn btn-danger btn-sm ms-2';
        toggleButton.innerHTML = '<i class="fas fa-pause"></i> Pause Auto-Refresh';
        toggleButton.addEventListener('click', toggleAutoRefresh);
        
        const refreshButton = document.getElementById('refresh-all');
        refreshButton.parentNode.insertBefore(toggleButton, refreshButton.nextSibling);
    }
    
    // Admin actions
    const failoverButton = document.getElementById('manual-failover');
    if (failoverButton) {
        failoverButton.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('failoverModal'));
            modal.show();
        });
    }
    
    const confirmFailoverButton = document.getElementById('confirm-failover');
    if (confirmFailoverButton) {
        confirmFailoverButton.addEventListener('click', function() {
            const modal = bootstrap.Modal.getInstance(document.getElementById('failoverModal'));
            modal.hide();
            initiateFailover();
        });
    }
    
    // Routing policy form
    const routingPolicyForm = document.getElementById('routing-policy-form');
    if (routingPolicyForm) {
        routingPolicyForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const policy = document.getElementById('routing-policy').value;
            updateRoutingPolicy(policy);
        });
    }
    
    // Backup button
    const backupButton = document.getElementById('initiate-backup');
    if (backupButton) {
        backupButton.addEventListener('click', initiateBackup);
    }
    
    // Reset button
    const resetButton = document.getElementById('reset-ha');
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            const modal = new bootstrap.Modal(document.getElementById('resetModal'));
            modal.show();
        });
    }
    
    const confirmResetButton = document.getElementById('confirm-reset');
    if (confirmResetButton) {
        confirmResetButton.addEventListener('click', function() {
            const modal = bootstrap.Modal.getInstance(document.getElementById('resetModal'));
            modal.hide();
            resetHAInfrastructure();
        });
    }
    
    // Start auto-refresh
    startAutoRefresh();
    
    // Clean up intervals when leaving the page
    window.addEventListener('beforeunload', function() {
        if (refreshInterval) {
            clearInterval(refreshInterval);
        }
    });
});