/**
 * Connectivity Status Dashboard
 * Provides real-time status of all connected systems
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the connectivity status
    initConnectivityStatus();
    
    // Check connectivity status every 30 seconds
    setInterval(checkConnectivityStatus, 30000);
});

// Initialize connectivity status
function initConnectivityStatus() {
    checkConnectivityStatus();
    
    // Set up the toggle button for the sidebar
    const toggleBtn = document.getElementById('connectivity-toggle');
    const sidebar = document.getElementById('connectivity-sidebar');
    
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('show');
            
            // Update icon
            const icon = toggleBtn.querySelector('i');
            if (sidebar.classList.contains('show')) {
                toggleBtn.setAttribute('aria-expanded', 'true');
                icon.classList.remove('fa-chevron-left');
                icon.classList.add('fa-chevron-right');
            } else {
                toggleBtn.setAttribute('aria-expanded', 'false');
                icon.classList.remove('fa-chevron-right');
                icon.classList.add('fa-chevron-left');
            }
        });
    }
}

// Check the status of all connected systems
function checkConnectivityStatus() {
    // Check blockchain connectivity
    checkBlockchainStatus();
    
    // Check payment gateway status
    checkPaymentGatewayStatus();
    
    // Check API status
    checkAPIStatus();
    
    // Check database status
    checkDatabaseStatus();
}

// Check blockchain connectivity
function checkBlockchainStatus() {
    fetch('/api/blockchain/status')
        .then(response => response.json())
        .then(data => {
            updateStatusIndicator('blockchain-status', data.status);
            updateStatusDetails('blockchain-details', data);
        })
        .catch(error => {
            console.error('Error checking blockchain status:', error);
            updateStatusIndicator('blockchain-status', 'error');
        });
}

// Check payment gateway status
function checkPaymentGatewayStatus() {
    fetch('/api/payments/gateways/status')
        .then(response => response.json())
        .then(data => {
            updateStatusIndicator('payment-status', data.status);
            updateStatusDetails('payment-details', data);
        })
        .catch(error => {
            console.error('Error checking payment gateway status:', error);
            updateStatusIndicator('payment-status', 'error');
        });
}

// Check API connectivity
function checkAPIStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            updateStatusIndicator('api-status', data.status);
            updateStatusDetails('api-details', data);
        })
        .catch(error => {
            console.error('Error checking API status:', error);
            updateStatusIndicator('api-status', 'error');
        });
}

// Check database connectivity
function checkDatabaseStatus() {
    fetch('/api/database/status')
        .then(response => response.json())
        .then(data => {
            updateStatusIndicator('database-status', data.status);
            updateStatusDetails('database-details', data);
        })
        .catch(error => {
            console.error('Error checking database status:', error);
            updateStatusIndicator('database-status', 'error');
        });
}

// Update the status indicator
function updateStatusIndicator(elementId, status) {
    const indicator = document.getElementById(elementId);
    if (!indicator) return;
    
    // Remove all status classes
    indicator.classList.remove('status-ok', 'status-warning', 'status-error');
    
    // Update the icon and color based on status
    let iconClass = 'fas fa-check-circle';
    let statusClass = 'status-ok';
    let statusText = 'Connected';
    
    if (status === 'warning') {
        iconClass = 'fas fa-exclamation-triangle';
        statusClass = 'status-warning';
        statusText = 'Degraded';
    } else if (status === 'error' || status === false) {
        iconClass = 'fas fa-times-circle';
        statusClass = 'status-error';
        statusText = 'Disconnected';
    }
    
    // Update the indicator
    indicator.innerHTML = `<i class="${iconClass}"></i> <span>${statusText}</span>`;
    indicator.classList.add(statusClass);
}

// Update the status details panel
function updateStatusDetails(elementId, data) {
    const detailsElement = document.getElementById(elementId);
    if (!detailsElement) return;
    
    let detailsHtml = '<ul class="status-details-list">';
    
    // Format and display the details
    if (data.message) {
        detailsHtml += `<li><strong>Message:</strong> ${data.message}</li>`;
    }
    
    if (data.latency) {
        detailsHtml += `<li><strong>Latency:</strong> ${data.latency}ms</li>`;
    }
    
    if (data.version) {
        detailsHtml += `<li><strong>Version:</strong> ${data.version}</li>`;
    }
    
    if (data.lastChecked) {
        const lastChecked = new Date(data.lastChecked);
        detailsHtml += `<li><strong>Last Checked:</strong> ${lastChecked.toLocaleTimeString()}</li>`;
    } else {
        const now = new Date();
        detailsHtml += `<li><strong>Last Checked:</strong> ${now.toLocaleTimeString()}</li>`;
    }
    
    // Add additional details if available
    if (data.details) {
        for (const [key, value] of Object.entries(data.details)) {
            detailsHtml += `<li><strong>${key}:</strong> ${value}</li>`;
        }
    }
    
    detailsHtml += '</ul>';
    detailsElement.innerHTML = detailsHtml;
}