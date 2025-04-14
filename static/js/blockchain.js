// Blockchain JavaScript for blockchain interactions

document.addEventListener('DOMContentLoaded', function() {
    // Initialize transaction hash links
    initTransactionHashLinks();
    
    // Initialize blockchain transaction lookups
    initBlockchainLookup();
    
    // Initialize contract interactions
    initContractInteractions();
    
    // Initialize settlement form if it exists
    initSettlementForm();
});

// Initialize transaction hash links to external blockchain explorers
function initTransactionHashLinks() {
    const txLinks = document.querySelectorAll('.eth-tx-link');
    
    txLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const txHash = this.getAttribute('data-tx-hash');
            
            if (!txHash) {
                return;
            }
            
            // Open in new tab
            window.open(`https://ropsten.etherscan.io/tx/${txHash}`, '_blank');
        });
    });
}

// Initialize blockchain transaction lookup form
function initBlockchainLookup() {
    const lookupForm = document.getElementById('blockchain-lookup-form');
    
    if (lookupForm) {
        lookupForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const txHash = document.getElementById('tx_hash').value.trim();
            
            if (!txHash) {
                showAlert('Error', 'Please enter a transaction hash', 'danger');
                return;
            }
            
            lookupBlockchainTransaction(txHash);
        });
    }
}

// Lookup blockchain transaction
function lookupBlockchainTransaction(txHash) {
    // Show loading state
    const resultContainer = document.getElementById('blockchain-lookup-result');
    
    if (!resultContainer) {
        return;
    }
    
    resultContainer.innerHTML = '<div class="text-center p-3"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Looking up transaction...</p></div>';
    
    // Make API request to get transaction details
    fetch(`/api/blockchain/transaction/${txHash}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getJwtToken()}`
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            resultContainer.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }
        
        // Format and display transaction details
        resultContainer.innerHTML = `
            <div class="card">
                <div class="card-header">
                    Transaction Details
                </div>
                <div class="card-body">
                    <div class="row mb-2">
                        <div class="col-md-4 fw-bold">Transaction Hash:</div>
                        <div class="col-md-8">
                            <a href="https://ropsten.etherscan.io/tx/${data.hash}" target="_blank">${data.hash}</a>
                        </div>
                    </div>
                    <div class="row mb-2">
                        <div class="col-md-4 fw-bold">From:</div>
                        <div class="col-md-8">
                            <a href="https://ropsten.etherscan.io/address/${data.from}" target="_blank">${data.from}</a>
                        </div>
                    </div>
                    <div class="row mb-2">
                        <div class="col-md-4 fw-bold">To:</div>
                        <div class="col-md-8">
                            <a href="https://ropsten.etherscan.io/address/${data.to}" target="_blank">${data.to}</a>
                        </div>
                    </div>
                    <div class="row mb-2">
                        <div class="col-md-4 fw-bold">Value:</div>
                        <div class="col-md-8">${data.value} ETH</div>
                    </div>
                    <div class="row mb-2">
                        <div class="col-md-4 fw-bold">Block Number:</div>
                        <div class="col-md-8">${data.block_number}</div>
                    </div>
                    <div class="row mb-2">
                        <div class="col-md-4 fw-bold">Gas Used:</div>
                        <div class="col-md-8">${data.gas_used}</div>
                    </div>
                    <div class="row mb-2">
                        <div class="col-md-4 fw-bold">Status:</div>
                        <div class="col-md-8">
                            <span class="badge ${data.status === 'confirmed' ? 'bg-success' : 'bg-danger'}">${data.status}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    })
    .catch(error => {
        console.error('Error looking up blockchain transaction:', error);
        resultContainer.innerHTML = '<div class="alert alert-danger">Failed to look up transaction. Please try again.</div>';
    });
}

// Initialize contract interactions
function initContractInteractions() {
    const contractFunctions = document.querySelectorAll('.contract-function');
    
    contractFunctions.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const contractAddress = this.getAttribute('data-contract-address');
            const functionName = this.getAttribute('data-function-name');
            
            if (!contractAddress || !functionName) {
                return;
            }
            
            // Show function form in modal
            showContractFunctionForm(contractAddress, functionName);
        });
    });
}

// Show contract function form in modal
function showContractFunctionForm(contractAddress, functionName) {
    const modalTitle = document.getElementById('contractFunctionModalLabel');
    const modalBody = document.getElementById('contractFunctionModalBody');
    const modal = new bootstrap.Modal(document.getElementById('contractFunctionModal'));
    
    if (!modalTitle || !modalBody) {
        return;
    }
    
    modalTitle.textContent = `Execute ${functionName}`;
    
    // Generate form based on function name
    if (functionName === 'settlePayment') {
        modalBody.innerHTML = `
            <form id="settle-payment-form">
                <div class="mb-3">
                    <label for="recipient" class="form-label">Recipient Address</label>
                    <input type="text" class="form-control" id="recipient" required>
                </div>
                <div class="mb-3">
                    <label for="amount" class="form-label">Amount (ETH)</label>
                    <input type="number" class="form-control" id="amount" step="0.000001" min="0" required>
                </div>
                <div class="mb-3">
                    <label for="transaction-id" class="form-label">Transaction ID</label>
                    <input type="text" class="form-control" id="transaction-id" required>
                </div>
                <input type="hidden" id="contract-address" value="${contractAddress}">
                <button type="submit" class="btn btn-primary">Execute</button>
            </form>
            <div id="function-result" class="mt-3"></div>
        `;
        
        // Setup form submission
        const form = document.getElementById('settle-payment-form');
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const recipient = document.getElementById('recipient').value;
            const amount = document.getElementById('amount').value;
            const transactionId = document.getElementById('transaction-id').value;
            
            // Call contract function
            callSettlePayment(contractAddress, recipient, amount, transactionId);
        });
    } else if (functionName === 'getSettlementStatus') {
        modalBody.innerHTML = `
            <form id="get-settlement-status-form">
                <div class="mb-3">
                    <label for="transaction-id" class="form-label">Transaction ID</label>
                    <input type="text" class="form-control" id="transaction-id" required>
                </div>
                <input type="hidden" id="contract-address" value="${contractAddress}">
                <button type="submit" class="btn btn-primary">Execute</button>
            </form>
            <div id="function-result" class="mt-3"></div>
        `;
        
        // Setup form submission
        const form = document.getElementById('get-settlement-status-form');
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const transactionId = document.getElementById('transaction-id').value;
            
            // Call contract function
            callGetSettlementStatus(contractAddress, transactionId);
        });
    } else {
        modalBody.innerHTML = '<div class="alert alert-warning">Function not supported in the interface.</div>';
    }
    
    modal.show();
}

// Call settlePayment function
function callSettlePayment(contractAddress, recipient, amount, transactionId) {
    const resultContainer = document.getElementById('function-result');
    
    if (!resultContainer) {
        return;
    }
    
    // Show loading state
    resultContainer.innerHTML = '<div class="text-center p-3"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Executing transaction...</p></div>';
    
    // Make API request to call contract function
    fetch('/api/blockchain/transactions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getJwtToken()}`
        },
        body: JSON.stringify({
            to_address: recipient,
            amount: parseFloat(amount),
            description: `Settlement for ${transactionId}`,
            use_contract: true
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            resultContainer.innerHTML = `
                <div class="alert alert-success">
                    <h5>Transaction submitted successfully!</h5>
                    <p>Transaction ID: ${data.transaction_id}</p>
                    <p>Ethereum Transaction Hash: <a href="https://ropsten.etherscan.io/tx/${data.eth_transaction_hash}" target="_blank">${data.eth_transaction_hash}</a></p>
                </div>
            `;
        } else {
            resultContainer.innerHTML = `<div class="alert alert-danger">${data.error || 'Transaction failed'}</div>`;
        }
    })
    .catch(error => {
        console.error('Error calling contract function:', error);
        resultContainer.innerHTML = '<div class="alert alert-danger">Failed to execute function. Please try again.</div>';
    });
}

// Call getSettlementStatus function
function callGetSettlementStatus(contractAddress, transactionId) {
    const resultContainer = document.getElementById('function-result');
    
    if (!resultContainer) {
        return;
    }
    
    // Show loading state
    resultContainer.innerHTML = '<div class="text-center p-3"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Getting status...</p></div>';
    
    // Make API request to call contract function
    fetch(`/api/blockchain/settlement_status/${transactionId}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getJwtToken()}`
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            resultContainer.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }
        
        // Format and display result
        resultContainer.innerHTML = `
            <div class="card">
                <div class="card-header">Settlement Status</div>
                <div class="card-body">
                    <div class="row mb-2">
                        <div class="col-md-4 fw-bold">Status:</div>
                        <div class="col-md-8">${data.status}</div>
                    </div>
                    <div class="row mb-2">
                        <div class="col-md-4 fw-bold">Timestamp:</div>
                        <div class="col-md-8">${new Date(data.timestamp * 1000).toLocaleString()}</div>
                    </div>
                </div>
            </div>
        `;
    })
    .catch(error => {
        console.error('Error calling contract function:', error);
        resultContainer.innerHTML = '<div class="alert alert-danger">Failed to get status. Please try again.</div>';
    });
}

// Initialize settlement form
function initSettlementForm() {
    const settlementForm = document.getElementById('settlement-form');
    
    if (settlementForm) {
        settlementForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const recipientAddress = document.getElementById('recipient_address').value;
            const amount = document.getElementById('amount').value;
            const description = document.getElementById('description').value;
            const useContract = document.getElementById('use_contract').checked;
            
            // Validate inputs
            if (!recipientAddress || !amount) {
                showAlert('Error', 'Please fill in all required fields', 'danger');
                return;
            }
            
            // Validate Ethereum address format
            if (!recipientAddress.match(/^0x[a-fA-F0-9]{40}$/)) {
                showAlert('Error', 'Invalid Ethereum address format', 'danger');
                return;
            }
            
            // Submit settlement transaction
            submitSettlementTransaction(recipientAddress, amount, description, useContract);
        });
    }
}

// Submit settlement transaction
function submitSettlementTransaction(recipientAddress, amount, description, useContract) {
    // Show loading state
    const submitButton = document.querySelector('#settlement-form button[type="submit"]');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    submitButton.disabled = true;
    
    // Make API request to create blockchain transaction
    fetch('/api/blockchain/transactions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getJwtToken()}`
        },
        body: JSON.stringify({
            to_address: recipientAddress,
            amount: parseFloat(amount),
            description: description || 'Settlement payment',
            use_contract: useContract
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Success', 'Settlement transaction initiated successfully', 'success');
            
            // Redirect to transaction details page
            window.location.href = `/transaction/${data.transaction_id}`;
        } else {
            showAlert('Error', data.error || 'Failed to initiate settlement', 'danger');
            
            // Reset button
            submitButton.innerHTML = originalText;
            submitButton.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error submitting settlement transaction:', error);
        showAlert('Error', 'Failed to initiate settlement', 'danger');
        
        // Reset button
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    });
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
