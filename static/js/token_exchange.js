/**
 * Token Exchange JavaScript
 * Handles token exchange functionality between AFD1 and NVCT tokens
 */

document.addEventListener('DOMContentLoaded', function () {
    // Elements
    const exchangeRateElement = document.getElementById('exchange-rate');
    const rateTimestampElement = document.getElementById('rate-timestamp');
    const afd1BalanceElement = document.getElementById('afd1-balance');
    const nvctBalanceElement = document.getElementById('nvct-balance');
    const fromTokenSelect = document.getElementById('from-token');
    const toTokenSelect = document.getElementById('to-token');
    const amountInput = document.getElementById('amount');
    const amountTokenSpan = document.getElementById('amount-token');
    const toAmountInput = document.getElementById('to-amount');
    const toAmountTokenSpan = document.getElementById('to-amount-token');
    const exchangeForm = document.getElementById('exchange-form');
    const exchangeButton = document.getElementById('exchange-button');
    const exchangeButtonText = document.getElementById('exchange-button-text');
    const exchangeSpinner = document.getElementById('exchange-spinner');
    const exchangeInfo = document.getElementById('exchange-info');
    const refreshHistoryButton = document.getElementById('refresh-history');
    const transactionHistory = document.getElementById('transaction-history');
    const historyLoading = document.getElementById('history-loading');
    const noTransactions = document.getElementById('no-transactions');

    // State
    let exchangeRate = 0;
    let afd1Balance = 0;
    let nvctBalance = 0;

    // Initialize
    fetchExchangeRate();
    fetchBalances();
    fetchTransactionHistory();

    // Event listeners
    fromTokenSelect.addEventListener('change', handleTokenSelectChange);
    toTokenSelect.addEventListener('change', handleTokenSelectChange);
    amountInput.addEventListener('input', calculateToAmount);
    exchangeForm.addEventListener('submit', handleExchange);
    refreshHistoryButton.addEventListener('click', fetchTransactionHistory);

    /**
     * Fetch current exchange rate
     */
    function fetchExchangeRate() {
        exchangeRateElement.textContent = 'Loading...';
        rateTimestampElement.textContent = 'Retrieving latest rate';

        fetch('/api/v1/token-exchange/exchange-rate')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    exchangeRate = data.rate;
                    exchangeRateElement.textContent = `1 AFD1 = ${exchangeRate.toFixed(6)} NVCT`;
                    
                    if (data.timestamp) {
                        const timestamp = new Date(data.timestamp);
                        rateTimestampElement.textContent = `As of ${timestamp.toLocaleString()}`;
                    } else {
                        rateTimestampElement.textContent = 'Current market rate';
                    }

                    // Initialize calculation
                    calculateToAmount();
                } else {
                    exchangeRateElement.textContent = 'Rate unavailable';
                    rateTimestampElement.textContent = 'Could not retrieve current rate';
                    showError('Failed to fetch exchange rate. Please try again later.');
                }
            })
            .catch(error => {
                console.error('Error fetching exchange rate:', error);
                exchangeRateElement.textContent = 'Rate unavailable';
                rateTimestampElement.textContent = 'Could not connect to exchange service';
            });
    }

    /**
     * Fetch user token balances
     */
    function fetchBalances() {
        // Fetch AFD1 balance
        fetch('/api/v1/token-exchange/token-balance?token=AFD1')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    afd1Balance = data.balance;
                    afd1BalanceElement.textContent = afd1Balance.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 6
                    });
                } else {
                    afd1BalanceElement.textContent = 'Unavailable';
                }
            })
            .catch(error => {
                console.error('Error fetching AFD1 balance:', error);
                afd1BalanceElement.textContent = 'Unavailable';
            });

        // Fetch NVCT balance
        fetch('/api/v1/token-exchange/token-balance?token=NVCT')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    nvctBalance = data.balance;
                    nvctBalanceElement.textContent = nvctBalance.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 6
                    });
                } else {
                    nvctBalanceElement.textContent = 'Unavailable';
                }
            })
            .catch(error => {
                console.error('Error fetching NVCT balance:', error);
                nvctBalanceElement.textContent = 'Unavailable';
            });
    }

    /**
     * Handle token select change
     */
    function handleTokenSelectChange() {
        const fromToken = fromTokenSelect.value;
        const toToken = toTokenSelect.value;

        // If both are same, swap them
        if (fromToken === toToken) {
            if (this === fromTokenSelect) {
                toTokenSelect.value = fromToken === 'AFD1' ? 'NVCT' : 'AFD1';
            } else {
                fromTokenSelect.value = toToken === 'AFD1' ? 'NVCT' : 'AFD1';
            }
        }

        // Update UI elements
        amountTokenSpan.textContent = fromTokenSelect.value;
        toAmountTokenSpan.textContent = toTokenSelect.value;

        // Recalculate
        calculateToAmount();
    }

    /**
     * Calculate destination amount based on current exchange rate
     */
    function calculateToAmount() {
        const amount = parseFloat(amountInput.value) || 0;
        const fromToken = fromTokenSelect.value;
        const toToken = toTokenSelect.value;
        
        let toAmount = 0;
        
        if (amount > 0 && exchangeRate > 0) {
            if (fromToken === 'AFD1' && toToken === 'NVCT') {
                toAmount = amount * exchangeRate;
            } else if (fromToken === 'NVCT' && toToken === 'AFD1') {
                toAmount = amount / exchangeRate;
            }
            
            toAmountInput.value = toAmount.toFixed(6);
            
            // Update info text
            if (fromToken === 'AFD1') {
                exchangeInfo.textContent = `You are exchanging ${amount.toFixed(2)} AFD1 for approximately ${toAmount.toFixed(6)} NVCT.`;
            } else {
                exchangeInfo.textContent = `You are exchanging ${amount.toFixed(2)} NVCT for approximately ${toAmount.toFixed(6)} AFD1.`;
            }
            
            // Check if user has sufficient balance
            const userBalance = fromToken === 'AFD1' ? afd1Balance : nvctBalance;
            if (amount > userBalance) {
                exchangeInfo.innerHTML = `<span class="text-danger">Insufficient ${fromToken} balance. You have ${userBalance.toFixed(6)} ${fromToken} available.</span>`;
                exchangeButton.disabled = true;
            } else {
                exchangeButton.disabled = false;
            }
        } else {
            toAmountInput.value = '0.00';
            exchangeInfo.textContent = 'Enter an amount to see the conversion.';
            exchangeButton.disabled = amount <= 0;
        }
    }

    /**
     * Handle token exchange
     */
    function handleExchange(event) {
        event.preventDefault();
        
        const fromToken = fromTokenSelect.value;
        const toToken = toTokenSelect.value;
        const amount = parseFloat(amountInput.value) || 0;
        
        if (amount <= 0) {
            showError('Please enter a valid amount to exchange.');
            return;
        }
        
        // Disable form and show spinner
        setFormLoading(true);
        
        // Execute trade
        fetch('/api/v1/token-exchange/execute-trade', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                from_token: fromToken,
                to_token: toToken,
                amount: amount
            })
        })
        .then(response => {
            return response.json().then(data => {
                return { status: response.status, data };
            });
        })
        .then(({ status, data }) => {
            setFormLoading(false);
            
            if (status === 200 && data.status === 'success') {
                // Show success message
                showSuccess(`Exchange successful! You received ${parseFloat(data.to_amount).toFixed(6)} ${toToken}.`);
                
                // Reset form
                amountInput.value = '';
                toAmountInput.value = '';
                
                // Update balances and history
                fetchBalances();
                fetchTransactionHistory();
            } else {
                // Show error message
                showError(data.message || 'Failed to execute exchange. Please try again later.');
            }
        })
        .catch(error => {
            console.error('Error executing exchange:', error);
            setFormLoading(false);
            showError('An error occurred while processing your exchange. Please try again later.');
        });
    }

    /**
     * Fetch transaction history
     */
    function fetchTransactionHistory() {
        // Show loading state
        historyLoading.classList.remove('d-none');
        noTransactions.classList.add('d-none');
        
        // Remove existing history rows except loading
        const rows = transactionHistory.querySelectorAll('tr:not(#history-loading)');
        rows.forEach(row => row.remove());
        
        fetch('/api/v1/token-exchange/trade-history')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Hide loading state
                historyLoading.classList.add('d-none');
                
                if (data.status === 'success') {
                    const localTrades = data.local_trades || [];
                    
                    if (localTrades.length === 0) {
                        noTransactions.classList.remove('d-none');
                        return;
                    }
                    
                    // Populate table
                    localTrades.forEach(trade => {
                        const row = document.createElement('tr');
                        
                        // Format date
                        const date = new Date(trade.timestamp);
                        const formattedDate = date.toLocaleString();
                        
                        // Create row
                        row.innerHTML = `
                            <td>${formattedDate}</td>
                            <td>${trade.from_amount.toFixed(6)} ${trade.from_token}</td>
                            <td>${trade.to_amount.toFixed(6)} ${trade.to_token}</td>
                            <td>${trade.from_amount.toFixed(6)} ${trade.from_token}</td>
                            <td><span class="badge ${getBadgeClass(trade.status)}">${trade.status}</span></td>
                        `;
                        
                        transactionHistory.appendChild(row);
                    });
                } else {
                    showError('Failed to load transaction history.');
                    noTransactions.classList.remove('d-none');
                }
            })
            .catch(error => {
                console.error('Error fetching transaction history:', error);
                historyLoading.classList.add('d-none');
                noTransactions.classList.remove('d-none');
                showError('Failed to load transaction history.');
            });
    }

    /**
     * Helper: Set form loading state
     */
    function setFormLoading(isLoading) {
        if (isLoading) {
            exchangeButton.disabled = true;
            exchangeSpinner.classList.remove('d-none');
            exchangeButtonText.textContent = 'Processing...';
            amountInput.disabled = true;
            fromTokenSelect.disabled = true;
            toTokenSelect.disabled = true;
        } else {
            exchangeButton.disabled = false;
            exchangeSpinner.classList.add('d-none');
            exchangeButtonText.textContent = 'Exchange Tokens';
            amountInput.disabled = false;
            fromTokenSelect.disabled = false;
            toTokenSelect.disabled = false;
        }
    }

    /**
     * Helper: Show error message
     */
    function showError(message) {
        // Create alert element
        const alertElement = document.createElement('div');
        alertElement.className = 'alert alert-danger alert-dismissible fade show';
        alertElement.role = 'alert';
        alertElement.innerHTML = `
            <strong>Error:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insert before the form
        exchangeForm.parentNode.insertBefore(alertElement, exchangeForm);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertElement.classList.remove('show');
            setTimeout(() => alertElement.remove(), 150);
        }, 5000);
    }

    /**
     * Helper: Show success message
     */
    function showSuccess(message) {
        // Create alert element
        const alertElement = document.createElement('div');
        alertElement.className = 'alert alert-success alert-dismissible fade show';
        alertElement.role = 'alert';
        alertElement.innerHTML = `
            <strong>Success:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Insert before the form
        exchangeForm.parentNode.insertBefore(alertElement, exchangeForm);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alertElement.classList.remove('show');
            setTimeout(() => alertElement.remove(), 150);
        }, 5000);
    }

    /**
     * Helper: Get badge class based on status
     */
    function getBadgeClass(status) {
        switch (status) {
            case 'COMPLETED':
                return 'bg-success';
            case 'PENDING':
                return 'bg-warning';
            case 'FAILED':
                return 'bg-danger';
            default:
                return 'bg-secondary';
        }
    }
});