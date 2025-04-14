// Payment Form JavaScript for payment processing

document.addEventListener('DOMContentLoaded', function() {
    // Initialize payment gateway selection
    initGatewaySelection();
    
    // Initialize payment form validation
    initFormValidation();
    
    // Initialize Stripe Elements if needed
    initStripeElements();
    
    // Initialize currency selector
    initCurrencySelector();
});

// Initialize payment gateway selection
function initGatewaySelection() {
    const gatewaySelect = document.getElementById('gateway_id');
    const gatewayInfoCards = document.querySelectorAll('.gateway-info');
    
    if (gatewaySelect && gatewayInfoCards.length > 0) {
        // Show info for selected gateway
        const updateSelectedGateway = () => {
            const selectedGatewayId = gatewaySelect.value;
            
            // Hide all gateway info cards
            gatewayInfoCards.forEach(card => {
                card.classList.add('d-none');
            });
            
            // Show selected gateway info
            const selectedCard = document.getElementById(`gateway-info-${selectedGatewayId}`);
            if (selectedCard) {
                selectedCard.classList.remove('d-none');
            }
        };
        
        // Initial update
        updateSelectedGateway();
        
        // Update on change
        gatewaySelect.addEventListener('change', updateSelectedGateway);
    }
}

// Initialize payment form validation
function initFormValidation() {
    const paymentForm = document.getElementById('payment-form');
    
    if (paymentForm) {
        paymentForm.addEventListener('submit', function(e) {
            const gatewayId = document.getElementById('gateway_id').value;
            const amount = document.getElementById('amount').value;
            
            // Basic validation
            if (!gatewayId) {
                e.preventDefault();
                showAlert('Error', 'Please select a payment gateway', 'danger');
                return;
            }
            
            if (!amount || parseFloat(amount) <= 0) {
                e.preventDefault();
                showAlert('Error', 'Please enter a valid amount', 'danger');
                return;
            }
            
            // Show loading state
            const submitButton = this.querySelector('button[type="submit"]');
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            submitButton.disabled = true;
            
            // Let the form submit normally - the server will handle the payment
        });
    }
}

// Initialize Stripe Elements for client-side payment processing
function initStripeElements() {
    const stripePublicKey = document.getElementById('stripe-public-key');
    const clientSecret = document.getElementById('client-secret');
    
    if (stripePublicKey && clientSecret) {
        const stripe = Stripe(stripePublicKey.value);
        const elements = stripe.elements();
        
        // Create card element
        const cardElement = elements.create('card');
        cardElement.mount('#card-element');
        
        // Handle form submission
        const paymentForm = document.getElementById('stripe-payment-form');
        
        if (paymentForm) {
            paymentForm.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                // Disable the submit button to prevent repeated clicks
                const submitButton = this.querySelector('button[type="submit"]');
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
                
                const { error, paymentIntent } = await stripe.confirmCardPayment(
                    clientSecret.value,
                    {
                        payment_method: {
                            card: cardElement,
                            billing_details: {
                                name: document.getElementById('cardholder-name').value
                            }
                        }
                    }
                );
                
                if (error) {
                    // Show error message
                    const errorElement = document.getElementById('card-errors');
                    errorElement.textContent = error.message;
                    
                    // Reset button
                    submitButton.disabled = false;
                    submitButton.textContent = 'Pay';
                } else if (paymentIntent.status === 'succeeded') {
                    // Payment succeeded, redirect to success page
                    window.location.href = `/transaction/${document.getElementById('transaction-id').value}`;
                }
            });
        }
        
        // Handle card element errors
        cardElement.on('change', ({ error }) => {
            const displayError = document.getElementById('card-errors');
            if (error) {
                displayError.textContent = error.message;
            } else {
                displayError.textContent = '';
            }
        });
    }
}

// Initialize currency selector
function initCurrencySelector() {
    const currencySelect = document.getElementById('currency');
    const currencySymbolSpan = document.getElementById('currency-symbol');
    
    if (currencySelect && currencySymbolSpan) {
        // Update currency symbol when currency changes
        const updateCurrencySymbol = () => {
            const currency = currencySelect.value;
            let symbol = '';
            
            // Set currency symbol based on selected currency
            switch (currency) {
                case 'USD':
                    symbol = '$';
                    break;
                case 'EUR':
                    symbol = '€';
                    break;
                case 'GBP':
                    symbol = '£';
                    break;
                case 'JPY':
                    symbol = '¥';
                    break;
                case 'ETH':
                    symbol = 'Ξ';
                    break;
                case 'BTC':
                    symbol = '₿';
                    break;
                default:
                    symbol = currency;
            }
            
            currencySymbolSpan.textContent = symbol;
        };
        
        // Initial update
        updateCurrencySymbol();
        
        // Update on change
        currencySelect.addEventListener('change', updateCurrencySymbol);
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
