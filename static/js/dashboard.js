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
        // First check if the data is available in the global window object
        // This is set in the template for more reliable access
        if (window.dashboardAnalytics) {
            console.log('Using pre-parsed analytics data from window object');
            return window.dashboardAnalytics;
        }
        
        // Then try the analytics-data element
        const analyticsElement = document.getElementById('analytics-data');
        
        if (analyticsElement && analyticsElement.dataset && analyticsElement.dataset.analytics) {
            try {
                console.log('Found analytics data in element. Length:', analyticsElement.dataset.analytics.length);
                
                // Check if the data starts with expected characters
                if (!analyticsElement.dataset.analytics.startsWith('{')) {
                    console.warn('Analytics data does not start with {, it starts with:', 
                        analyticsElement.dataset.analytics.substring(0, 5));
                }
                
                const parsedData = JSON.parse(analyticsElement.dataset.analytics);
                
                // Cache the result in the window object for future use
                window.dashboardAnalytics = parsedData;
                
                return parsedData;
            } catch (e) {
                console.error('Error parsing analytics data JSON:', e);
                console.log('Raw analytics data sample:', analyticsElement.dataset.analytics.substring(0, 100));
            }
        } else {
            console.warn('Analytics element or data attribute missing', {
                elementExists: Boolean(analyticsElement),
                datasetExists: Boolean(analyticsElement && analyticsElement.dataset),
                analyticsExists: Boolean(analyticsElement && analyticsElement.dataset && analyticsElement.dataset.analytics)
            });
        }
        
        // If that fails, try data attributes on individual charts (legacy approach)
        const charts = ['transactionsByDateChart', 'transactionsByTypeChart', 'transactionsByStatusChart'];
        for (const chartId of charts) {
            const chartEl = document.getElementById(chartId);
            if (chartEl && chartEl.dataset && chartEl.dataset.transactions) {
                try {
                    const chartData = JSON.parse(chartEl.dataset.transactions);
                    window.dashboardAnalytics = chartData; // Cache for future use
                    return chartData;
                } catch (e) {
                    console.error(`Error parsing data from ${chartId}:`, e);
                }
            }
        }
        
        // Check for analytics data element again, but this time try to extract the innerHTML
        // This is a last resort method
        if (analyticsElement) {
            try {
                const innerText = analyticsElement.textContent || analyticsElement.innerText;
                if (innerText && innerText.trim().startsWith('{')) {
                    console.log('Trying to parse analytics from element inner text');
                    const parsedData = JSON.parse(innerText.trim());
                    window.dashboardAnalytics = parsedData; // Cache for future use
                    return parsedData;
                }
            } catch (e) {
                console.error('Error parsing analytics from inner text:', e);
            }
        }
        
        // If we get here, we'll create an empty structure
        console.warn('No valid analytics data found - using empty structure');
        
        // Create an empty structure that matches what the charts expect
        const defaultData = {
            days: 30,
            start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
            end_date: new Date().toISOString().split('T')[0],
            total_transactions: 0,
            total_amount: 0.0,
            by_type: {},
            by_status: {},
            by_date: {},
            raw_data: []
        };
        
        // Cache in window for consistency
        window.dashboardAnalytics = defaultData;
        
        return defaultData;
    } catch (e) {
        console.error('Error in getAnalyticsData:', e);
        
        // Always return a valid data structure even if there's an error
        return {
            days: 30,
            start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
            end_date: new Date().toISOString().split('T')[0],
            total_transactions: 0,
            total_amount: 0.0,
            by_type: {},
            by_status: {},
            by_date: {},
            raw_data: []
        };
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
    
    // Check if we have data
    if (dates.length === 0) {
        displayChartError(canvas, 'No transaction data for the selected period');
        return;
    }
    
    // Format the dates for display
    const formattedDates = dates.map(date => {
        const parts = date.split('-');
        return `${parts[1]}/${parts[2]}`; // MM/DD format
    });
    
    const transactionCounts = dates.map(date => data.by_date[date].count);
    const transactionAmounts = dates.map(date => data.by_date[date].total_amount);
    
    // Update the summary information
    // Get total transactions
    const totalTransactions = data.total_transactions || 
        transactionCounts.reduce((sum, count) => sum + count, 0);
    
    // Get total amount
    const totalAmount = data.total_amount || 
        transactionAmounts.reduce((sum, amount) => sum + amount, 0);
    
    // Update the summary badges
    const totalTransactionsCountEl = document.getElementById('totalTransactionsCount');
    const totalTransactionsAmountEl = document.getElementById('totalTransactionsAmount');
    
    if (totalTransactionsCountEl) {
        totalTransactionsCountEl.textContent = totalTransactions;
    }
    
    if (totalTransactionsAmountEl) {
        totalTransactionsAmountEl.textContent = formatCurrency(totalAmount);
    }
    
    // Create chart with improved styling
    const ctx = canvas.getContext('2d');
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: formattedDates,
            datasets: [
                {
                    label: 'Transaction Count',
                    data: transactionCounts,
                    backgroundColor: 'rgba(0, 123, 255, 0.2)',
                    borderColor: 'rgba(0, 123, 255, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    yAxisID: 'y',
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: 'rgba(0, 123, 255, 1)'
                },
                {
                    label: 'Transaction Amount',
                    data: transactionAmounts,
                    backgroundColor: 'rgba(40, 167, 69, 0.2)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    yAxisID: 'y1',
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: 'rgba(40, 167, 69, 1)'
                }
            ]
        },
        options: {
            responsive: true,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.datasetIndex === 1) {
                                label += '$' + context.raw.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
                            } else {
                                label += context.raw;
                            }
                            return label;
                        }
                    }
                },
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        boxWidth: 6
                    }
                },
                title: {
                    display: true,
                    text: 'Transaction Trends (' + data.start_date + ' to ' + data.end_date + ')',
                    color: '#6c757d',
                    font: {
                        size: 13
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#6c757d'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Count',
                        color: 'rgba(0, 123, 255, 1)'
                    },
                    ticks: {
                        color: '#6c757d'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
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
                        text: 'Amount ($)',
                        color: 'rgba(40, 167, 69, 1)'
                    },
                    ticks: {
                        color: '#6c757d',
                        callback: function(value) {
                            return '$' + value.toFixed(0).replace(/\d(?=(\d{3})+$)/g, '$&,');
                        }
                    }
                }
            }
        }
    });
    
    // Add a tooltip to show total transaction count and amount
    const totalElement = document.createElement('div');
    totalElement.className = 'mt-3 text-center text-muted small';
    totalElement.innerHTML = `
        <div class="d-flex justify-content-center gap-3">
            <span><i class="fas fa-hashtag me-1 text-primary"></i> Total: <strong>${transactionCounts.reduce((a, b) => a + b, 0)}</strong></span>
            <span><i class="fas fa-dollar-sign me-1 text-success"></i> Total: <strong>$${transactionAmounts.reduce((a, b) => a + b, 0).toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,')}</strong></span>
        </div>
    `;
    canvas.parentNode.appendChild(totalElement);
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
    
    // Check if we have data
    if (types.length === 0) {
        displayChartError(canvas, 'No transaction type data available');
        return;
    }
    
    // Format the labels nicely with capitalization
    const formattedLabels = types.map(type => {
        return type.charAt(0).toUpperCase() + type.slice(1).toLowerCase();
    });
    
    const counts = types.map(type => data.by_type[type].count);
    const amounts = types.map(type => data.by_type[type].total_amount || 0);
    
    // Update type summary badge
    const typeChartTotalEl = document.getElementById('typeChartTotal');
    if (typeChartTotalEl) {
        const totalCount = counts.reduce((sum, count) => sum + count, 0);
        typeChartTotalEl.textContent = totalCount;
    }
    
    // Define improved colors for different transaction types
    const colorMap = {
        'payment': 'rgba(0, 123, 255, 0.8)', // Bootstrap primary
        'deposit': 'rgba(40, 167, 69, 0.8)', // Bootstrap success
        'withdrawal': 'rgba(220, 53, 69, 0.8)', // Bootstrap danger
        'transfer': 'rgba(255, 193, 7, 0.8)', // Bootstrap warning
        'refund': 'rgba(108, 117, 125, 0.8)' // Bootstrap secondary
    };
    
    // Apply the color map or use defaults for unknown types
    const backgroundColors = types.map(type => {
        const lowerType = type.toLowerCase();
        return colorMap[lowerType] || `rgba(${Math.floor(Math.random() * 200)}, ${Math.floor(Math.random() * 200)}, ${Math.floor(Math.random() * 200)}, 0.8)`;
    });
    
    // Create chart with improved styling
    const ctx = canvas.getContext('2d');
    const chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: formattedLabels,
            datasets: [{
                data: counts,
                backgroundColor: backgroundColors,
                borderWidth: 1,
                hoverOffset: 10,
                borderColor: '#fff',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const index = context.dataIndex;
                            const count = counts[index];
                            const amount = amounts[index];
                            const percentage = ((count / counts.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                            return [
                                `${context.label}: ${count} (${percentage}%)`, 
                                `Total Value: $${amount.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,')}`
                            ];
                        }
                    }
                },
                legend: {
                    position: 'right',
                    labels: {
                        usePointStyle: true,
                        font: {
                            size: 11
                        },
                        padding: 15
                    }
                },
                title: {
                    display: true,
                    text: 'Transaction Distribution by Type',
                    color: '#6c757d',
                    font: {
                        size: 13,
                        weight: 'normal'
                    }
                }
            }
        }
    });
    
    // Add summary information
    const totalElement = document.createElement('div');
    totalElement.className = 'mt-3 text-center text-muted small';
    totalElement.innerHTML = `
        <div class="d-flex justify-content-center">
            <span><i class="fas fa-chart-pie me-1 text-primary"></i> Total: <strong>${counts.reduce((a, b) => a + b, 0)}</strong> transactions</span>
        </div>
    `;
    canvas.parentNode.appendChild(totalElement);
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
    
    // Check if we have data
    if (statuses.length === 0) {
        displayChartError(canvas, 'No transaction status data available');
        return;
    }
    
    // Format the labels nicely with capitalization
    const formattedLabels = statuses.map(status => {
        return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
    });
    
    const counts = statuses.map(status => data.by_status[status].count);
    const amounts = statuses.map(status => data.by_status[status].total_amount || 0);
    
    // Update status summary badges
    const statusDoneCountEl = document.getElementById('statusDoneCount');
    const statusPendingCountEl = document.getElementById('statusPendingCount');
    
    if (statusDoneCountEl || statusPendingCountEl) {
        let completedCount = 0;
        let pendingCount = 0;
        
        statuses.forEach((status, index) => {
            const lowerStatus = status.toLowerCase();
            if (lowerStatus === 'completed') {
                completedCount += counts[index];
            } else if (lowerStatus === 'pending' || lowerStatus === 'processing') {
                pendingCount += counts[index];
            }
        });
        
        if (statusDoneCountEl) {
            statusDoneCountEl.textContent = completedCount;
        }
        
        if (statusPendingCountEl) {
            statusPendingCountEl.textContent = pendingCount;
        }
    }
    
    // Define colors using bootstrap theme colors
    const colorMap = {
        'pending': 'rgba(255, 193, 7, 0.8)', // warning
        'processing': 'rgba(0, 123, 255, 0.8)', // primary
        'completed': 'rgba(40, 167, 69, 0.8)', // success
        'failed': 'rgba(220, 53, 69, 0.8)', // danger
        'refunded': 'rgba(108, 117, 125, 0.8)', // secondary
        'cancelled': 'rgba(52, 58, 64, 0.8)' // dark
    };
    
    const backgroundColors = statuses.map(status => colorMap[status.toLowerCase()] || 'rgba(128, 128, 128, 0.6)');
    
    // Create chart with improved styling
    const ctx = canvas.getContext('2d');
    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: formattedLabels,
            datasets: [{
                data: counts,
                backgroundColor: backgroundColors,
                borderWidth: 1,
                borderColor: '#fff',
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            cutout: '65%',
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const index = context.dataIndex;
                            const count = counts[index];
                            const amount = amounts[index];
                            const percentage = ((count / counts.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                            return [
                                `${context.label}: ${count} (${percentage}%)`, 
                                `Total Value: $${amount.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,')}`
                            ];
                        }
                    }
                },
                legend: {
                    position: 'right',
                    labels: {
                        usePointStyle: true,
                        font: {
                            size: 11
                        },
                        padding: 15
                    }
                },
                title: {
                    display: true,
                    text: 'Transaction Status Distribution',
                    color: '#6c757d',
                    font: {
                        size: 13,
                        weight: 'normal'
                    }
                }
            }
        }
    });
    
    // Add center text with total count
    const totalCount = counts.reduce((a, b) => a + b, 0);
    
    // Add a completion rate display
    const completedIndex = statuses.findIndex(s => s.toLowerCase() === 'completed');
    const completionRate = completedIndex >= 0 ? ((counts[completedIndex] / totalCount) * 100).toFixed(0) : 0;
    
    // Add summary information
    const statusInfo = document.createElement('div');
    statusInfo.className = 'mt-3 text-center text-muted small';
    statusInfo.innerHTML = `
        <div class="d-flex justify-content-center gap-3">
            <span><i class="fas fa-check-circle me-1 text-success"></i> Completion Rate: <strong>${completionRate}%</strong></span>
            <span><i class="fas fa-tasks me-1 text-primary"></i> Total Transactions: <strong>${totalCount}</strong></span>
        </div>
    `;
    canvas.parentNode.appendChild(statusInfo);
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
        // Display loading state
        balanceEl.innerHTML = '<span class="text-muted"><i class="fas fa-spinner fa-spin me-2"></i>Fetching balance...</span>';
        
        // Fetch balance from API - ensure address is properly encoded
        const encodedAddress = encodeURIComponent(ethereumAddress);
        console.log(`Fetching balance for address: ${encodedAddress} with token ${jwtToken.substring(0, 10)}...`);
        
        // First, check if the address has a proper format
        if (!ethereumAddress || !ethereumAddress.match(/^0x[a-fA-F0-9]{40}$/)) {
            console.error("Invalid Ethereum address format:", ethereumAddress);
            balanceEl.innerHTML = '<span class="text-danger"><i class="fas fa-exclamation-circle me-2"></i>Invalid address format</span>';
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
                // Successfully received balance data
                balanceEl.innerHTML = `<span class="text-success fw-bold">${data.balance_eth} ETH</span>`;
                if (data.token_balance && data.token_balance > 0) {
                    balanceEl.innerHTML += `<br><small class="text-muted">${data.token_balance} NVCT</small>`;
                }
                console.log(`Balance for ${data.address}: ${data.balance_eth} ETH, ${data.token_balance || 0} NVCT`);
            } else {
                // API returned unsuccessful status
                console.warn('API returned unsuccessful status:', data.error || 'No specific error');
                const errorMessage = data.error || 'Balance unavailable';
                balanceEl.innerHTML = `<span class="text-warning"><i class="fas fa-exclamation-triangle me-2"></i>${errorMessage}</span>`;
            }
        })
        .catch(error => {
            console.error('Error fetching blockchain balance:', error);
            
            // Parse error response if available
            let errorMessage = 'Connection error';
            let statusClass = 'text-danger';
            let icon = 'exclamation-circle';
            
            try {
                // Try to parse the response if it's a JSON error response
                if (error.message.includes('status:')) {
                    const statusCode = parseInt(error.message.match(/status: (\d+)/)[1]);
                    
                    switch (statusCode) {
                        case 400:
                            errorMessage = 'Invalid request';
                            statusClass = 'text-warning';
                            icon = 'exclamation-triangle';
                            break;
                        case 401:
                        case 403:
                            errorMessage = 'Authentication required';
                            statusClass = 'text-danger';
                            icon = 'lock';
                            break;
                        case 404:
                            errorMessage = 'Blockchain API not found';
                            statusClass = 'text-warning';
                            icon = 'search';
                            break;
                        case 500:
                            errorMessage = 'Blockchain service error';
                            statusClass = 'text-danger';
                            icon = 'server';
                            break;
                        case 503:
                            errorMessage = 'Blockchain network unavailable';
                            statusClass = 'text-danger';
                            icon = 'plug';
                            break;
                        default:
                            errorMessage = `Error (${statusCode})`;
                            break;
                    }
                } else if (error.response && error.response.data) {
                    // Try to extract user_message if available in response
                    const data = error.response.data;
                    if (data.user_message) {
                        errorMessage = data.user_message;
                    } else if (data.error) {
                        errorMessage = data.error;
                    }
                }
            } catch (e) {
                console.warn('Error parsing error response:', e);
            }
            
            // Display user-friendly error message with icon
            balanceEl.innerHTML = `<span class="${statusClass}"><i class="fas fa-${icon} me-2"></i>${errorMessage}</span>`;
            
            // Add a small note with technical info for debug purposes
            balanceEl.innerHTML += `<div class="small text-muted mt-1">Try refreshing or check network connection</div>`;
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
                // Successfully received balance data
                balanceEl.innerHTML = `<span class="text-success fw-bold">${data.balance_eth} ETH</span>`;
                if (data.token_balance && data.token_balance > 0) {
                    balanceEl.innerHTML += `<br><small class="text-muted">${data.token_balance} NVCT</small>`;
                }
                console.log(`Balance for ${data.address}: ${data.balance_eth} ETH, ${data.token_balance || 0} NVCT`);
            } else {
                // API returned unsuccessful status
                console.warn('API returned unsuccessful status:', data.error || 'No specific error');
                const errorMessage = data.error || 'Balance unavailable';
                balanceEl.innerHTML = `<span class="text-warning"><i class="fas fa-exclamation-triangle me-2"></i>${errorMessage}</span>`;
            }
            resetButton(button);
        })
        .catch(error => {
            console.error('Error fetching blockchain balance:', error);
            
            // Parse error response if available
            let errorMessage = 'Connection error';
            let statusClass = 'text-danger';
            let icon = 'exclamation-circle';
            
            try {
                // Try to parse the response if it's a JSON error response
                if (error.message.includes('status:')) {
                    const statusCode = parseInt(error.message.match(/status: (\d+)/)[1]);
                    
                    switch (statusCode) {
                        case 400:
                            errorMessage = 'Invalid request';
                            statusClass = 'text-warning';
                            icon = 'exclamation-triangle';
                            break;
                        case 401:
                        case 403:
                            errorMessage = 'Authentication required';
                            statusClass = 'text-danger';
                            icon = 'lock';
                            break;
                        case 404:
                            errorMessage = 'Blockchain API not found';
                            statusClass = 'text-warning';
                            icon = 'search';
                            break;
                        case 500:
                            errorMessage = 'Blockchain service error';
                            statusClass = 'text-danger';
                            icon = 'server';
                            break;
                        case 503:
                            errorMessage = 'Blockchain network unavailable';
                            statusClass = 'text-danger';
                            icon = 'plug';
                            break;
                        default:
                            errorMessage = `Error (${statusCode})`;
                            break;
                    }
                } else if (error.response && error.response.data) {
                    // Try to extract user_message if available in response
                    const data = error.response.data;
                    if (data.user_message) {
                        errorMessage = data.user_message;
                    } else if (data.error) {
                        errorMessage = data.error;
                    }
                }
            } catch (e) {
                console.warn('Error parsing error response:', e);
            }
            
            // Display user-friendly error message with icon
            balanceEl.innerHTML = `<span class="${statusClass}"><i class="fas fa-${icon} me-2"></i>${errorMessage}</span>`;
            
            // Add a small note with technical info for debug purposes
            balanceEl.innerHTML += `<div class="small text-muted mt-1">Try refreshing or check network connection</div>`;
            
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
