/**
 * Treasury Settlement Dashboard JavaScript
 * 
 * This file contains the client-side logic for the Treasury Settlement Dashboard,
 * including refreshing settlement statistics and handling manual settlement operations.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize forms
    const manualSettlementForm = document.getElementById('manualSettlementForm');
    if (manualSettlementForm) {
        manualSettlementForm.addEventListener('submit', function(e) {
            // Validate the form before submission
            const amount = parseFloat(document.getElementById('amount').value);
            if (isNaN(amount) || amount <= 0) {
                e.preventDefault();
                alert('Please enter a valid positive amount');
                return false;
            }
            
            // Confirm before submission
            if (!confirm('Are you sure you want to record this manual settlement?')) {
                e.preventDefault();
                return false;
            }
            
            return true;
        });
    }

    // Settlement processing forms
    const processForms = document.querySelectorAll('form[action*="process_settlements"]');
    processForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Confirm before processing settlements
            if (!confirm('Are you sure you want to process these settlements?')) {
                e.preventDefault();
                return false;
            }
            
            return true;
        });
    });

    // Fetch settlement statistics periodically
    function refreshSettlementStats() {
        fetch('/treasury/settlement/stats')
            .then(response => response.json())
            .then(data => {
                updateStatistics(data);
            })
            .catch(error => {
                console.error('Error fetching settlement statistics:', error);
            });
    }

    function updateStatistics(data) {
        // Update processor statistics
        for (const [processor, stats] of Object.entries(data.processors)) {
            const totalElement = document.getElementById(`${processor}-total-30d`);
            const countElement = document.getElementById(`${processor}-count-30d`);
            
            if (totalElement) {
                totalElement.textContent = formatCurrency(stats.total_30d, stats.currency);
            }
            
            if (countElement) {
                countElement.textContent = stats.count_30d;
            }
        }
        
        // Update total settled amount
        const totalSettledElement = document.getElementById('total-settled-30d');
        if (totalSettledElement) {
            totalSettledElement.textContent = formatCurrency(data.total_settled_30d, 'USD');
        }
        
        // Update most recent settlements
        for (const [processor, tx] of Object.entries(data.most_recent)) {
            const recentElement = document.getElementById(`${processor}-recent`);
            
            if (recentElement && tx) {
                const date = new Date(tx.date);
                recentElement.innerHTML = `
                    <div>${formatDate(date)}</div>
                    <div>${formatCurrency(tx.amount, tx.currency)}</div>
                `;
            }
        }
    }

    // Utility functions
    function formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }
    
    function formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
    }

    // Refresh statistics every 30 seconds
    if (document.querySelector('.settlement-dashboard')) {
        refreshSettlementStats();
        setInterval(refreshSettlementStats, 30000);
    }
});