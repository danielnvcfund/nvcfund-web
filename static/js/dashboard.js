// Dashboard JavaScript for charts and data visualization

document.addEventListener('DOMContentLoaded', function() {
    // Initialize transaction charts if the elements exist
    initTransactionCharts();
    
    // Initialize blockchain balance display
    initBlockchainBalance();
    
    // Set up refresh button functionality
    setupRefreshButtons();
});

// Get analytics data from the page - can be used by any function
function getAnalyticsData() {
    try {
        // First try the analytics-data element
        const analyticsElement = document.getElementById('analytics-data');
        
        if (analyticsElement && analyticsElement.dataset && analyticsElement.dataset.analytics) {
            try {
                return JSON.parse(analyticsElement.dataset.analytics);
            } catch (e) {
                console.error('Error parsing analytics data JSON:', e);
                console.log('Raw analytics data:', analyticsElement.dataset.analytics);
            }
        }
        
        // If that fails, try data attributes on individual charts (legacy approach)
        const charts = ['transactionsByDateChart', 'transactionsByTypeChart', 'transactionsByStatusChart'];
        for (const chartId of charts) {
            const chartEl = document.getElementById(chartId);
            if (chartEl && chartEl.dataset && chartEl.dataset.transactions) {
                try {
                    return JSON.parse(chartEl.dataset.transactions);
                } catch (e) {
                    console.error(`Error parsing data from ${chartId}:`, e);
                }
            }
        }
        
        console.warn('No valid analytics data found');
        return null;
    } catch (e) {
        console.error('Error in getAnalyticsData:', e);
        return null;
    }
}

// Get JWT token from browser storage - used for API authentication
function getJwtToken() {
    try {
        // First try to get token from analytics-data element (if available)
        const analyticsElement = document.getElementById('analytics-data');
        if (analyticsElement && analyticsElement.dataset && analyticsElement.dataset.jwtToken) {
            const token = analyticsElement.dataset.jwtToken;
            if (token && token.length > 10) { // Basic validation
                console.log('Using JWT token from data attribute');
                return token;
            }
        }
        
        // Then try localStorage (persistent across browser sessions)
        const localToken = localStorage.getItem('jwt_token');
        if (localToken && localToken.length > 10) {
            console.log('Using JWT token from localStorage');
            return localToken;
        }
        
        // Then try sessionStorage (cleared when browser tab is closed)
        const sessionToken = sessionStorage.getItem('jwt_token');
        if (sessionToken && sessionToken.length > 10) {
            console.log('Using JWT token from sessionStorage');
            return sessionToken;
        }
        
        console.warn('No JWT token found in storage');
        return null;
    } catch (e) {
        console.error('Error retrieving JWT token:', e);
        return null;
    }
}

// Get Ethereum address from the page - can be used by any function
function getEthereumAddress() {
    try {
        // Try analytics data element first
        const analyticsElement = document.getElementById('analytics-data');
        if (analyticsElement && analyticsElement.dataset && analyticsElement.dataset.ethereumAddress) {
            return analyticsElement.dataset.ethereumAddress;
        }
        
        // Then try the blockchain balance element
        const balanceEl = document.getElementById('blockchainBalance');
        if (balanceEl && balanceEl.dataset && balanceEl.dataset.address) {
            return balanceEl.dataset.address;
        }
        
        // Finally try any of the chart elements
        const charts = ['transactionsByDateChart', 'transactionsByTypeChart', 'transactionsByStatusChart'];
        for (const chartId of charts) {
            const chartEl = document.getElementById(chartId);
            if (chartEl && chartEl.dataset && chartEl.dataset.ethereumAddress) {
                return chartEl.dataset.ethereumAddress;
            }
        }
        
        console.warn('No Ethereum address found');
        return null;
    } catch (e) {
        console.error('Error in getEthereumAddress:', e);
        return null;
    }
}

// Initialize transaction charts
function initTransactionCharts() {
    const transactionsByDateEl = document.getElementById('transactionsByDateChart');
    const transactionsByTypeEl = document.getElementById('transactionsByTypeChart');
    const transactionsByStatusEl = document.getElementById('transactionsByStatusChart');
    
    // Get the analytics data from the page
    let analyticsData = getAnalyticsData();
    
    if (!analyticsData) {
        // Display error in charts
        displayChartError(transactionsByDateEl, 'No analytics data available');
        displayChartError(transactionsByTypeEl, 'No analytics data available');
        displayChartError(transactionsByStatusEl, 'No analytics data available');
        return;
    }
    
    // Initialize with an empty structure if something's missing
    if (!analyticsData.by_date || !analyticsData.by_type || !analyticsData.by_status) {
        console.warn('Analytics data is missing expected properties');
        analyticsData = { 
            by_date: analyticsData.by_date || {},
            by_type: analyticsData.by_type || {},
            by_status: analyticsData.by_status || {},
            raw_data: analyticsData.raw_data || []
        };
    }
    
    if (transactionsByDateEl) {
        try {
            initTransactionsByDateChart(transactionsByDateEl, analyticsData);
        } catch (error) {
            console.error('Error initializing transactions by date chart:', error);
            // Display a fallback message in the chart container
            displayChartError(transactionsByDateEl, 'Unable to display transaction chart by date');
        }
    }
    
    if (transactionsByTypeEl) {
        try {
            initTransactionsByTypeChart(transactionsByTypeEl, analyticsData);
        } catch (error) {
            console.error('Error initializing transactions by type chart:', error);
            // Display a fallback message in the chart container
            displayChartError(transactionsByTypeEl, 'Unable to display transaction chart by type');
        }
    }
    
    if (transactionsByStatusEl) {
        try {
            initTransactionsByStatusChart(transactionsByStatusEl, analyticsData);
        } catch (error) {
            console.error('Error initializing transactions by status chart:', error);
            // Display a fallback message in the chart container
            displayChartError(transactionsByStatusEl, 'Unable to display transaction chart by status');
        }
    }
}

// Helper function to display an error message in place of a chart
function displayChartError(container, message) {
    // Clear the canvas
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
    
    // Create and append error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-secondary text-center my-3';
    errorDiv.innerText = message;
    container.appendChild(errorDiv);
}

// Create transactions by date chart
function initTransactionsByDateChart(canvas, data) {
    // Use the data passed from the parent function
    if (!data || !data.by_date) {
        console.error('Missing by_date in transaction data');
        return;
    }
    
    // Prepare data for chart
    const dates = Object.keys(data.by_date).sort();
    const transactionCounts = dates.map(date => data.by_date[date].count);
    const transactionAmounts = dates.map(date => data.by_date[date].total_amount);
    
    // Create chart
    const ctx = canvas.getContext('2d');
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Transaction Count',
                    data: transactionCounts,
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    yAxisID: 'y'
                },
                {
                    label: 'Transaction Amount',
                    data: transactionAmounts,
                    backgroundColor: 'rgba(153, 102, 255, 0.2)',
                    borderColor: 'rgba(153, 102, 255, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Count'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false
                    },
                    title: {
                        display: true,
                        text: 'Amount'
                    }
                }
            }
        }
    });
}

// Create transactions by type chart
function initTransactionsByTypeChart(canvas, data) {
    // Use the data passed from the parent function
    if (!data || !data.by_type) {
        console.error('Missing by_type in transaction data');
        return;
    }
    
    // Prepare data for chart
    const types = Object.keys(data.by_type);
    const counts = types.map(type => data.by_type[type].count);
    
    // Define colors for different transaction types
    const backgroundColors = [
        'rgba(75, 192, 192, 0.6)',
        'rgba(153, 102, 255, 0.6)',
        'rgba(255, 159, 64, 0.6)',
        'rgba(255, 99, 132, 0.6)',
        'rgba(54, 162, 235, 0.6)'
    ];
    
    // Create chart
    const ctx = canvas.getContext('2d');
    const chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: types,
            datasets: [{
                data: counts,
                backgroundColor: backgroundColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right'
                },
                title: {
                    display: true,
                    text: 'Transaction Types'
                }
            }
        }
    });
}

// Create transactions by status chart
function initTransactionsByStatusChart(canvas, data) {
    // Use the data passed from the parent function
    if (!data || !data.by_status) {
        console.error('Missing by_status in transaction data');
        return;
    }
    
    // Prepare data for chart
    const statuses = Object.keys(data.by_status);
    const counts = statuses.map(status => data.by_status[status].count);
    
    // Define colors for different statuses
    const colorMap = {
        'pending': 'rgba(255, 159, 64, 0.6)',
        'processing': 'rgba(54, 162, 235, 0.6)',
        'completed': 'rgba(75, 192, 192, 0.6)',
        'failed': 'rgba(255, 99, 132, 0.6)',
        'refunded': 'rgba(153, 102, 255, 0.6)'
    };
    
    const backgroundColors = statuses.map(status => colorMap[status] || 'rgba(128, 128, 128, 0.6)');
    
    // Create chart
    const ctx = canvas.getContext('2d');
    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: statuses,
            datasets: [{
                data: counts,
                backgroundColor: backgroundColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right'
                },
                title: {
                    display: true,
                    text: 'Transaction Statuses'
                }
            }
        }
    });
}

// Initialize blockchain balance display
function initBlockchainBalance() {
    const balanceEl = document.getElementById('blockchainBalance');
    
    if (!balanceEl) {
        console.log('Blockchain balance element not found');
        return;
    }
    
    // Use our helper function to get Ethereum address from any available source
    const ethereumAddress = getEthereumAddress();
    
    if (!ethereumAddress) {
        console.warn('No Ethereum address found in any data attribute');
        balanceEl.textContent = 'No ETH address';
        return;
    }
    
    // Check if the address is null, undefined, or "None" (Python's None converted to string)
    if (ethereumAddress === "None" || ethereumAddress === "null" || ethereumAddress === "undefined" || ethereumAddress.trim() === "") {
        console.warn('No valid Ethereum address available:', ethereumAddress);
        balanceEl.textContent = 'No address assigned';
        const refreshButton = balanceEl.parentElement.querySelector('.btn-refresh');
        if (refreshButton) {
            refreshButton.style.display = 'none';
        }
        return;
    }
    
    // Make sure we have a valid address format
    if (!ethereumAddress.startsWith('0x') || ethereumAddress.length !== 42) {
        console.warn('Invalid Ethereum address format:', ethereumAddress);
        balanceEl.textContent = 'Invalid address';
        return;
    }
    
    // If no JWT token, display appropriate message
    const jwtToken = getJwtToken();
    if (!jwtToken) {
        console.warn('No JWT token available for authenticated API calls');
        balanceEl.textContent = 'Authentication required';
        return;
    }
    
    // Use a try/catch block for the fetch to handle network errors
    try {
        // Fetch balance from API - ensure address is properly encoded
        const encodedAddress = encodeURIComponent(ethereumAddress);
        console.log(`Fetching balance for address: ${encodedAddress} with token ${jwtToken.substring(0, 10)}...`);
        
        // First, check if the address has a proper format
        if (!ethereumAddress || !ethereumAddress.match(/^0x[a-fA-F0-9]{40}$/)) {
            console.error("Invalid Ethereum address format:", ethereumAddress);
            balanceEl.textContent = "Invalid address format";
            return;
        }
        
        // Make sure we're using the proper API endpoint with the correct prefix
        const apiUrl = `/api/blockchain/balances?address=${encodedAddress}`;
        console.log("Fetching balance from URL:", apiUrl);
        
        fetch(apiUrl, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${jwtToken}`,
                'X-API-Test': 'true' // Enable test access if authentication issues persist
            },
            credentials: 'include' // Include cookies for session authentication
        })
        .then(response => {
            // Check if response is ok before trying to parse JSON
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                balanceEl.textContent = `${data.balance_eth} ETH`;
                console.log(`Balance for ${data.address}: ${data.balance_eth} ETH`);
            } else {
                console.warn('API returned unsuccessful status:', data.error || 'No specific error');
                balanceEl.textContent = 'Balance unavailable';
            }
        })
        .catch(error => {
            console.error('Error fetching blockchain balance:', error);
            balanceEl.textContent = 'Error fetching balance';
        });
    } catch (error) {
        console.error('Exception during fetch setup:', error);
        balanceEl.textContent = 'Connection error';
    }
}

// Setup refresh buttons
function setupRefreshButtons() {
    const refreshButtons = document.querySelectorAll('.btn-refresh');
    
    refreshButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('data-target');
            const targetEl = document.getElementById(targetId);
            
            if (!targetEl) {
                return;
            }
            
            // Show loading spinner
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Refreshing...';
            this.disabled = true;
            
            // Refresh the data based on the target
            if (targetId === 'recentTransactions') {
                refreshRecentTransactions(this);
            } else if (targetId === 'blockchainBalance') {
                refreshBlockchainBalance(this);
            } else {
                // Reset button after 1 second if no specific refresh function
                setTimeout(() => {
                    this.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
                    this.disabled = false;
                }, 1000);
            }
        });
    });
}

// Refresh recent transactions
function refreshRecentTransactions(button) {
    fetch('/api/transactions?limit=5', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getJwtToken()}`
        }
    })
    .then(response => response.json())
    .then(data => {
        const transactionsContainer = document.getElementById('recentTransactions');
        
        if (transactionsContainer && data.transactions) {
            // Clear current transactions
            transactionsContainer.innerHTML = '';
            
            // Add new transactions
            if (data.transactions.length === 0) {
                transactionsContainer.innerHTML = '<tr><td colspan="5" class="text-center">No transactions found</td></tr>';
            } else {
                data.transactions.forEach(tx => {
                    const row = document.createElement('tr');
                    
                    // Format date
                    const date = new Date(tx.created_at);
                    const formattedDate = date.toLocaleString();
                    
                    // Create status badge
                    const statusClass = getStatusClass(tx.status);
                    const statusBadge = `<span class="badge ${statusClass}">${tx.status}</span>`;
                    
                    // Create row content
                    row.innerHTML = `
                        <td><a href="/transaction/${tx.transaction_id}">${tx.transaction_id.substring(0, 8)}...</a></td>
                        <td>${tx.type}</td>
                        <td>${tx.amount} ${tx.currency}</td>
                        <td>${statusBadge}</td>
                        <td>${formattedDate}</td>
                    `;
                    
                    transactionsContainer.appendChild(row);
                });
            }
        }
        
        // Reset button
        button.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
        button.disabled = false;
    })
    .catch(error => {
        console.error('Error refreshing transactions:', error);
        button.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
        button.disabled = false;
    });
}

// Refresh blockchain balance
function refreshBlockchainBalance(button) {
    const balanceEl = document.getElementById('blockchainBalance');
    
    if (!balanceEl) {
        console.log('Blockchain balance element not found');
        resetButton(button);
        return;
    }
    
    // Use our helper function to get Ethereum address from any available source
    const ethereumAddress = getEthereumAddress();
    
    if (!ethereumAddress) {
        console.warn('No Ethereum address found in any data attribute');
        balanceEl.textContent = 'No ETH address';
        resetButton(button);
        return;
    }
    
    // Check if the address is null, undefined, or "None" (Python's None converted to string)
    if (ethereumAddress === "None" || ethereumAddress === "null" || ethereumAddress === "undefined" || ethereumAddress.trim() === "") {
        console.warn('No valid Ethereum address available:', ethereumAddress);
        balanceEl.textContent = 'No address assigned';
        resetButton(button);
        button.style.display = 'none';
        return;
    }
    
    // Make sure we have a valid address format
    if (!ethereumAddress.startsWith('0x') || ethereumAddress.length !== 42) {
        console.warn('Invalid Ethereum address format:', ethereumAddress);
        balanceEl.textContent = 'Invalid address';
        resetButton(button);
        return;
    }
    
    // If no JWT token, display appropriate message
    if (!getJwtToken()) {
        console.warn('No JWT token available for authenticated API calls');
        balanceEl.textContent = 'Authentication required';
        resetButton(button);
        return;
    }
    
    // Use a try/catch block for the fetch to handle network errors
    try {
        // Fetch balance from API - ensure address is properly encoded
        const encodedAddress = encodeURIComponent(ethereumAddress);
        
        // Make sure we're using the proper API endpoint with the correct prefix
        const apiUrl = `/api/blockchain/balances?address=${encodedAddress}`;
        console.log("Refreshing balance from URL:", apiUrl);
        
        fetch(apiUrl, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getJwtToken()}`,
                'X-API-Test': 'true' // Enable test access if authentication issues persist
            },
            credentials: 'include' // Include cookies for session authentication
        })
        .then(response => {
            // Check if response is ok before trying to parse JSON
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                balanceEl.textContent = `${data.balance_eth} ETH`;
            } else {
                console.warn('API returned unsuccessful status:', data.error || 'No specific error');
                balanceEl.textContent = 'Balance unavailable';
            }
            resetButton(button);
        })
        .catch(error => {
            console.error('Error fetching blockchain balance:', error);
            balanceEl.textContent = 'Error fetching balance';
            resetButton(button);
        });
    } catch (error) {
        console.error('Exception during fetch setup:', error);
        balanceEl.textContent = 'Connection error';
        resetButton(button);
    }
}

// Helper function to reset button state
function resetButton(button) {
    if (button) {
        button.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
        button.disabled = false;
    }
}

// Get JWT token from localStorage or sessionStorage
function getJwtToken() {
    // Try to get the token from localStorage first
    let token = localStorage.getItem('jwt_token');
    
    // If not in localStorage, try sessionStorage
    if (!token) {
        token = sessionStorage.getItem('jwt_token');
    }
    
    // Check for null, undefined, or empty string
    if (!token) {
        console.warn('No JWT token found in storage');
        
        // Try to extract from cookie as fallback (some older implementations used cookies)
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith('jwt_token=')) {
                token = cookie.substring('jwt_token='.length, cookie.length);
                console.log('Found JWT token in cookie');
                break;
            }
        }
    }
    
    return token || '';
}

// Get CSS class for status badge
function getStatusClass(status) {
    // If status is null or undefined, return a default class
    if (!status) {
        console.warn('Null or undefined transaction status');
        return 'bg-secondary';
    }
    
    try {
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
            case 'cancelled':
                return 'bg-secondary';
            default:
                console.log('Unknown transaction status:', status);
                return 'bg-secondary';
        }
    } catch (error) {
        console.error('Error processing transaction status:', error);
        return 'bg-secondary';
    }
}
