// Transactions JavaScript for transaction management

document.addEventListener('DOMContentLoaded', function() {
    // Initialize date filters
    initDateFilters();
    
    // Initialize transaction filters
    initTransactionFilters();
    
    // Initialize transaction status updates
    initStatusUpdates();
    
    // Setup filter form submission
    setupFilterForm();
});

// Initialize date filters with date pickers
function initDateFilters() {
    const startDateInput = document.getElementById('start_date');
    const endDateInput = document.getElementById('end_date');
    
    if (startDateInput && endDateInput) {
        // Get current query params
        const urlParams = new URLSearchParams(window.location.search);
        
        // Set input values if in URL params
        if (urlParams.has('start_date')) {
            startDateInput.value = urlParams.get('start_date');
        }
        
        if (urlParams.has('end_date')) {
            endDateInput.value = urlParams.get('end_date');
        }
    }
}

// Initialize transaction filters
function initTransactionFilters() {
    const typeSelect = document.getElementById('transaction_type');
    const statusSelect = document.getElementById('transaction_status');
    
    if (typeSelect && statusSelect) {
        // Get current query params
        const urlParams = new URLSearchParams(window.location.search);
        
        // Set select values if in URL params
        if (urlParams.has('type')) {
            typeSelect.value = urlParams.get('type');
        }
        
        if (urlParams.has('status')) {
            statusSelect.value = urlParams.get('status');
        }
    }
}

// Initialize transaction status updates for admins
function initStatusUpdates() {
    const statusButtons = document.querySelectorAll('.transaction-status-update');
    
    statusButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const transactionId = this.getAttribute('data-transaction-id');
            const newStatus = this.getAttribute('data-status');
            
            if (!transactionId || !newStatus) {
                return;
            }
            
            updateTransactionStatus(transactionId, newStatus, this);
        });
    });
}

// Update transaction status
function updateTransactionStatus(transactionId, newStatus, button) {
    // Show loading state
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Updating...';
    button.disabled = true;
    
    // Make API request to update status
    fetch(`/api/transactions/${transactionId}/status`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getJwtToken()}`
        },
        body: JSON.stringify({
            status: newStatus
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            showAlert('Success', `Transaction status updated to ${newStatus}`, 'success');
            
            // Update status badge in the UI
            const statusBadge = document.querySelector(`#transaction-${transactionId} .status-badge`);
            if (statusBadge) {
                statusBadge.textContent = newStatus;
                statusBadge.className = `badge status-badge ${getStatusClass(newStatus)}`;
            }
        } else {
            showAlert('Error', data.error || 'Failed to update status', 'danger');
        }
        
        // Reset button
        button.innerHTML = originalText;
        button.disabled = false;
    })
    .catch(error => {
        console.error('Error updating transaction status:', error);
        showAlert('Error', 'Failed to update status', 'danger');
        
        // Reset button
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// Setup filter form submission
function setupFilterForm() {
    const filterForm = document.getElementById('transaction-filter-form');
    
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form values
            const type = document.getElementById('transaction_type').value;
            const status = document.getElementById('transaction_status').value;
            const startDate = document.getElementById('start_date').value;
            const endDate = document.getElementById('end_date').value;
            
            // Build query params
            const params = new URLSearchParams();
            
            if (type) {
                params.append('type', type);
            }
            
            if (status) {
                params.append('status', status);
            }
            
            if (startDate) {
                params.append('start_date', startDate);
            }
            
            if (endDate) {
                params.append('end_date', endDate);
            }
            
            // Redirect with query params
            window.location.href = `/transactions?${params.toString()}`;
        });
    }
}

// Show alert message
function showAlert(title, message, type) {
    const alertContainer = document.getElementById('alert-container');
    
    if (!alertContainer) {
        return;
    }
    
    // Create alert element
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type} alert-dismissible fade show`;
    alertElement.role = 'alert';
    
    alertElement.innerHTML = `
        <strong>${title}</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to container
    alertContainer.appendChild(alertElement);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertElement.classList.remove('show');
        setTimeout(() => {
            alertElement.remove();
        }, 150);
    }, 5000);
}

// Get JWT token from localStorage
function getJwtToken() {
    return localStorage.getItem('jwt_token') || '';
}

// Get CSS class for status badge
function getStatusClass(status) {
    switch (status.toLowerCase()) {
        case 'completed':
            return 'bg-success';
        case 'pending':
            return 'bg-warning text-dark';
        case 'processing':
            return 'bg-info text-dark';
        case 'failed':
            return 'bg-danger';
        case 'refunded':
            return 'bg-secondary';
        default:
            return 'bg-secondary';
    }
}

// Export functions
window.transactionsModule = {
    showAlert,
    getStatusClass
};
