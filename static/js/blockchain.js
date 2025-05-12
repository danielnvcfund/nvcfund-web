/**
 * NVC Banking Platform - Blockchain Interaction JavaScript
 * This file contains functions for interacting with the blockchain interface
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize refresh button
    const refreshButton = document.getElementById('refresh-status');
    if (refreshButton) {
        refreshButton.addEventListener('click', refreshBlockchainStatus);
    }

    // Initialize Settlement Contract interactions
    const deploySettlementButton = document.getElementById('deploy-settlement');
    if (deploySettlementButton) {
        deploySettlementButton.addEventListener('click', deploySettlementContract);
    }

    const createSettlementForm = document.getElementById('create-settlement-form');
    if (createSettlementForm) {
        createSettlementForm.addEventListener('submit', createNewSettlement);
    }

    // Initialize MultiSig Wallet interactions
    const deployMultisigButton = document.getElementById('deploy-multisig');
    if (deployMultisigButton) {
        deployMultisigButton.addEventListener('click', deployMultiSigWallet);
    }

    const submitMultisigForm = document.getElementById('submit-multisig-form');
    if (submitMultisigForm) {
        submitMultisigForm.addEventListener('submit', submitMultisigTransaction);
    }

    // Initialize Token interactions
    const deployTokenButton = document.getElementById('deploy-token');
    if (deployTokenButton) {
        deployTokenButton.addEventListener('click', deployNVCToken);
    }

    const transferTokenForm = document.getElementById('transfer-token-form');
    if (transferTokenForm) {
        transferTokenForm.addEventListener('submit', transferTokens);
    }

    const mintTokenForm = document.getElementById('mint-token-form');
    if (mintTokenForm) {
        mintTokenForm.addEventListener('submit', mintTokens);
    }

    const burnTokenForm = document.getElementById('burn-token-form');
    if (burnTokenForm) {
        burnTokenForm.addEventListener('submit', burnTokens);
    }

    // Initialize action buttons
    initializeActionButtons();
});

/**
 * Initialize dynamic action buttons
 */
function initializeActionButtons() {
    // Settlement actions
    document.querySelectorAll('.view-settlement').forEach(button => {
        button.addEventListener('click', function() {
            const settlementId = this.getAttribute('data-id');
            viewSettlementDetails(settlementId);
        });
    });

    document.querySelectorAll('.complete-settlement').forEach(button => {
        button.addEventListener('click', function() {
            const settlementId = this.getAttribute('data-id');
            completeSettlement(settlementId);
        });
    });

    document.querySelectorAll('.cancel-settlement').forEach(button => {
        button.addEventListener('click', function() {
            const settlementId = this.getAttribute('data-id');
            cancelSettlement(settlementId);
        });
    });

    // MultiSig actions
    document.querySelectorAll('.view-multisig-tx').forEach(button => {
        button.addEventListener('click', function() {
            const txId = this.getAttribute('data-id');
            viewMultisigTransaction(txId);
        });
    });

    document.querySelectorAll('.confirm-multisig-tx').forEach(button => {
        button.addEventListener('click', function() {
            const txId = this.getAttribute('data-id');
            confirmMultisigTransaction(txId);
        });
    });

    document.querySelectorAll('.execute-multisig-tx').forEach(button => {
        button.addEventListener('click', function() {
            const txId = this.getAttribute('data-id');
            executeMultisigTransaction(txId);
        });
    });
}

/**
 * Refresh blockchain connection status
 */
function refreshBlockchainStatus() {
    showAlert('Refreshing blockchain status...', 'info');
    
    fetch('/api/blockchain/status')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.text();  // Get response as text first
        })
        .then(text => {
            console.log("Raw response:", text);  // Log the raw response
            try {
                const data = JSON.parse(text);  // Then parse it as JSON
                if (data.status === 'ok') {
                    window.location.reload();
                } else {
                    showAlert('Error refreshing blockchain status: ' + data.message, 'danger');
                }
            } catch (e) {
                console.error("JSON parse error:", e);
                showAlert('Error parsing response: ' + e.message + '<br>Raw response: ' + text.substring(0, 100), 'danger');
            }
        })
        .catch(error => {
            console.error("Fetch error:", error);
            showAlert('Error refreshing blockchain status: ' + error.message, 'danger');
        });
}

// Settlement Contract Functions

function deploySettlementContract() {
    if (!confirm('Are you sure you want to deploy the Settlement Contract? This will cost ETH for gas fees.')) {
        return;
    }

    showAlert('Deploying Settlement Contract... This may take a minute.', 'info');
    
    fetch('/api/blockchain/deployment/contract', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            contract_type: 'settlement_contract'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Settlement Contract deployed successfully! Contract address: ' + data.address, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error deploying Settlement Contract: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error deploying Settlement Contract: ' + error.message, 'danger');
    });
}

function createNewSettlement(event) {
    event.preventDefault();
    
    const recipient = document.getElementById('settlement-recipient').value;
    // Remove commas from the amount before sending
    const formattedAmount = document.getElementById('settlement-amount').value;
    const amount = unformatNumber(formattedAmount);
    const metadata = document.getElementById('settlement-metadata').value;
    
    showAlert('Creating new settlement... This may take a minute.', 'info');
    
    fetch('/api/blockchain/settlement/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            to_address: recipient,
            amount: amount,
            metadata: metadata
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Settlement created successfully! Transaction hash: ' + data.tx_hash, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error creating settlement: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error creating settlement: ' + error.message, 'danger');
    });
}

function viewSettlementDetails(settlementId) {
    fetch(`/api/blockchain/settlement/${settlementId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const settlement = data.settlement;
                
                let detailsHTML = `
                    <h4>Settlement #${settlement.id}</h4>
                    <p><strong>Transaction ID:</strong> ${settlement.transactionId}</p>
                    <p><strong>From:</strong> ${settlement.from}</p>
                    <p><strong>To:</strong> ${settlement.to}</p>
                    <p><strong>Amount:</strong> ${formatNumberInput(settlement.amount)} ETH</p>
                    <p><strong>Fee:</strong> ${formatNumberInput(settlement.fee)} ETH</p>
                    <p><strong>Status:</strong> ${getStatusText(settlement.status)}</p>
                    <p><strong>Timestamp:</strong> ${new Date(settlement.timestamp * 1000).toLocaleString()}</p>
                    <p><strong>Metadata:</strong> ${settlement.metadata || 'None'}</p>
                `;
                
                showModal('Settlement Details', detailsHTML);
            } else {
                showAlert('Error fetching settlement details: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            showAlert('Error fetching settlement details: ' + error.message, 'danger');
        });
}

function completeSettlement(settlementId) {
    if (!confirm('Are you sure you want to complete this settlement? This will transfer funds to the recipient.')) {
        return;
    }
    
    showAlert('Completing settlement... This may take a minute.', 'info');
    
    fetch(`/api/blockchain/settlement/${settlementId}/complete`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Settlement completed successfully! Transaction hash: ' + data.tx_hash, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error completing settlement: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error completing settlement: ' + error.message, 'danger');
    });
}

function cancelSettlement(settlementId) {
    if (!confirm('Are you sure you want to cancel this settlement? This will return funds to the sender.')) {
        return;
    }
    
    showAlert('Cancelling settlement... This may take a minute.', 'info');
    
    fetch(`/api/blockchain/settlement/${settlementId}/cancel`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Settlement cancelled successfully! Transaction hash: ' + data.tx_hash, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error cancelling settlement: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error cancelling settlement: ' + error.message, 'danger');
    });
}

// MultiSig Wallet Functions

function deployMultiSigWallet() {
    if (!confirm('Are you sure you want to deploy the MultiSig Wallet? This will cost ETH for gas fees.')) {
        return;
    }
    
    showAlert('Deploying MultiSig Wallet... This may take a minute.', 'info');
    
    fetch('/api/blockchain/deployment/contract', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            contract_type: 'multisig_wallet'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('MultiSig Wallet deployed successfully! Contract address: ' + data.address, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error deploying MultiSig Wallet: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error deploying MultiSig Wallet: ' + error.message, 'danger');
    });
}

function submitMultisigTransaction(event) {
    event.preventDefault();
    
    const destination = document.getElementById('multisig-destination').value;
    // Remove commas from the amount before sending
    const formattedAmount = document.getElementById('multisig-amount').value;
    const amount = unformatNumber(formattedAmount);
    const data = document.getElementById('multisig-data').value || '0x';
    
    showAlert('Submitting transaction to MultiSig Wallet... This may take a minute.', 'info');
    
    fetch('/api/blockchain/multisig/submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            destination: destination,
            amount: amount,
            data: data
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Transaction submitted successfully! Transaction hash: ' + data.tx_hash, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error submitting transaction: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error submitting transaction: ' + error.message, 'danger');
    });
}

function viewMultisigTransaction(txId) {
    fetch(`/api/blockchain/multisig/transaction/${txId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const tx = data.transaction;
                
                let detailsHTML = `
                    <h4>MultiSig Transaction #${tx.id}</h4>
                    <p><strong>Destination:</strong> ${tx.destination}</p>
                    <p><strong>Value:</strong> ${formatNumberInput(tx.value)} ETH</p>
                    <p><strong>Data:</strong> ${tx.data || '0x'}</p>
                    <p><strong>Confirmations:</strong> ${tx.confirmations} / ${data.required_confirmations}</p>
                    <p><strong>Executed:</strong> ${tx.executed ? 'Yes' : 'No'}</p>
                    <h5 class="mt-3">Confirmations</h5>
                    <ul>
                        ${tx.confirmedBy.map(owner => `<li>${owner}</li>`).join('')}
                    </ul>
                `;
                
                showModal('MultiSig Transaction Details', detailsHTML);
            } else {
                showAlert('Error fetching transaction details: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            showAlert('Error fetching transaction details: ' + error.message, 'danger');
        });
}

function confirmMultisigTransaction(txId) {
    showAlert('Confirming transaction... This may take a minute.', 'info');
    
    fetch(`/api/blockchain/multisig/confirm/${txId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Transaction confirmed successfully! Transaction hash: ' + data.tx_hash, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error confirming transaction: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error confirming transaction: ' + error.message, 'danger');
    });
}

function executeMultisigTransaction(txId) {
    showAlert('Executing transaction... This may take a minute.', 'info');
    
    fetch(`/api/blockchain/multisig/execute/${txId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Transaction executed successfully! Transaction hash: ' + data.tx_hash, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error executing transaction: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error executing transaction: ' + error.message, 'danger');
    });
}

// NVC Token Functions

function deployNVCToken() {
    if (!confirm('Are you sure you want to deploy the NVC Token? This will cost ETH for gas fees.')) {
        return;
    }
    
    showAlert('Deploying NVC Token... This may take a minute.', 'info');
    
    fetch('/api/blockchain/deploy/token', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('NVC Token deployed successfully! Contract address: ' + data.address, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error deploying NVC Token: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error deploying NVC Token: ' + error.message, 'danger');
    });
}

/**
 * Format number input with commas as thousands separators
 * @param {string} value - Input value to format
 * @return {string} Formatted value with commas
 */
function formatNumberInput(value) {
    // Remove any non-digit characters except decimal point
    let numberOnly = value.replace(/[^\d.]/g, '');
    
    // Ensure only one decimal point
    const decimalParts = numberOnly.split('.');
    if (decimalParts.length > 2) {
        numberOnly = decimalParts[0] + '.' + decimalParts.slice(1).join('');
    }
    
    // Split into whole and decimal parts
    const parts = numberOnly.split('.');
    let wholePart = parts[0];
    const decimalPart = parts.length > 1 ? parts[1] : '';
    
    // Add commas to the whole part
    wholePart = wholePart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    
    // Reconstruct the number with decimal part if exists
    return decimalPart.length > 0 ? wholePart + '.' + decimalPart : wholePart;
}

/**
 * Remove commas from a formatted number string
 * @param {string} formattedValue - Input value with commas
 * @return {string} Value without commas
 */
function unformatNumber(formattedValue) {
    return formattedValue.replace(/,/g, '');
}

function transferTokens(event) {
    event.preventDefault();
    
    const recipient = document.getElementById('token-recipient').value;
    // Remove commas from the amount before sending
    const formattedAmount = document.getElementById('token-amount').value;
    const amount = unformatNumber(formattedAmount);
    
    showAlert('Transferring tokens... This may take a minute.', 'info');
    
    fetch('/api/blockchain/token/transfer', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            to_address: recipient,
            amount: amount
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Tokens transferred successfully! Transaction hash: ' + data.tx_hash, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error transferring tokens: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error transferring tokens: ' + error.message, 'danger');
    });
}

function mintTokens(event) {
    event.preventDefault();
    
    const recipient = document.getElementById('mint-recipient').value;
    // Remove commas from the amount before sending
    const formattedAmount = document.getElementById('mint-amount').value;
    const amount = unformatNumber(formattedAmount);
    
    showAlert('Minting tokens... This may take a minute.', 'info');
    
    fetch('/api/blockchain/token/mint', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            to_address: recipient,
            amount: amount
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Tokens minted successfully! Transaction hash: ' + data.tx_hash, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error minting tokens: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error minting tokens: ' + error.message, 'danger');
    });
}

function burnTokens(event) {
    event.preventDefault();
    
    const fromAddress = document.getElementById('burn-address').value;
    // Remove commas from the amount before sending
    const formattedAmount = document.getElementById('burn-amount').value;
    const amount = unformatNumber(formattedAmount);
    
    showAlert('Burning tokens... This may take a minute.', 'info');
    
    fetch('/api/blockchain/token/burn', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            from_address: fromAddress,
            amount: amount
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Tokens burned successfully! Transaction hash: ' + data.tx_hash, 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Error burning tokens: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Error burning tokens: ' + error.message, 'danger');
    });
}

// Helper Functions

function getStatusText(status) {
    const statusMap = {
        0: 'Pending',
        1: 'Completed',
        2: 'Cancelled',
        3: 'Disputed',
        4: 'Resolved'
    };
    return statusMap[status] || 'Unknown';
}

function showAlert(message, type) {
    const alertContainer = document.getElementById('alert-container');
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    alertContainer.appendChild(alertDiv);
    
    // Auto-dismiss after 30 seconds (increased for better error visibility)
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertDiv);
        bsAlert.close();
    }, 30000);
}

function showModal(title, content) {
    // Check if modal already exists
    let modalElement = document.getElementById('dynamicModal');
    
    // If it doesn't exist, create it
    if (!modalElement) {
        modalElement = document.createElement('div');
        modalElement.className = 'modal fade';
        modalElement.id = 'dynamicModal';
        modalElement.setAttribute('tabindex', '-1');
        modalElement.setAttribute('aria-labelledby', 'dynamicModalLabel');
        modalElement.setAttribute('aria-hidden', 'true');
        
        modalElement.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="dynamicModalLabel"></h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body"></div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modalElement);
    }
    
    // Set the content
    modalElement.querySelector('.modal-title').textContent = title;
    modalElement.querySelector('.modal-body').innerHTML = content;
    
    // Show the modal
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}