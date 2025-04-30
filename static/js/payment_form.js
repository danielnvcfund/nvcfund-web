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
    const descriptionField = document.getElementById('description');

    if (gatewaySelect && gatewayInfoCards.length > 0) {
        // Update description when gateway changes
        gatewaySelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const gatewayName = selectedOption.text;

            // Get base description or use default
            let baseDescription = descriptionField.value || 'Payment from nvcplatform.net';

            // Add gateway info if not already present
            if (!baseDescription.includes('via')) {
                descriptionField.value = `${baseDescription} (via ${gatewayName})`;
            } else {
                // Replace existing gateway info
                descriptionField.value = baseDescription.replace(/\(via [^)]+\)/, `(via ${gatewayName})`);
            }
        });

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
        const cardElement = elements.create('card', {
            hidePostalCode: false, // Enable postal code for AVS checks
            style: {
                base: {
                    fontSize: '16px',
                    color: '#495057',
                    '::placeholder': {
                        color: '#6c757d',
                    },
                },
                invalid: {
                    color: '#dc3545',
                    iconColor: '#dc3545',
                },
            },
        });
        cardElement.mount('#card-element');

        // Handle form submission
        const paymentForm = document.getElementById('stripe-payment-form');

        if (paymentForm) {
            paymentForm.addEventListener('submit', async function(e) {
                e.preventDefault();

                // Get scenario from hidden field if it exists (for test page)
                const testScenarioField = document.getElementById('test-scenario');
                const isTestMode = testScenarioField !== null;
                const testScenario = isTestMode ? testScenarioField.value : null;

                // Disable the submit button to prevent repeated clicks
                const submitButton = this.querySelector('button[type="submit"]');
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';

                // Add test card numbers based on scenario if in test mode
                let testCardNumber = null;
                if (isTestMode && testScenario) {
                    switch (testScenario) {
                        case 'failure':
                            testCardNumber = '4000000000000002'; // Always declined
                            break;
                        case '3ds':
                            testCardNumber = '4000000000003220'; // Requires 3D Secure
                            break;
                        case 'success':
                        default:
                            testCardNumber = '4242424242424242'; // Always succeeds
                    }

                    // Log for testing
                    console.log(`Test mode active with scenario: ${testScenario}, using card: ${testCardNumber}`);
                }

                // Start the payment flow with Stripe
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

                    // For test mode, show additional context
                    if (isTestMode) {
                        errorElement.innerHTML += `<div class="mt-2 small text-muted">Test Error: ${error.code || 'unknown'}</div>`;
                    }

                    // Reset button
                    submitButton.disabled = false;
                    submitButton.textContent = 'Pay';
                } else if (paymentIntent.status === 'succeeded') {
                    // Payment succeeded, redirect to success page
                    window.location.href = `/transaction/${document.getElementById('transaction-id').value}`;
                } else if (paymentIntent.status === 'requires_action') {
                    // Handle 3D Secure authentication
                    const { error, paymentIntent: updatedIntent } = 
                        await stripe.confirmCardPayment(clientSecret.value);

                    if (error) {
                        // Show error message for 3DS failure
                        const errorElement = document.getElementById('card-errors');
                        errorElement.textContent = '3D Secure authentication failed: ' + error.message;

                        // Reset button
                        submitButton.disabled = false;
                        submitButton.textContent = 'Try Again';
                    } else if (updatedIntent.status === 'succeeded') {
                        // 3DS successful
                        window.location.href = `/transaction/${document.getElementById('transaction-id').value}`;
                    } else {
                        // Unexpected status
                        const errorElement = document.getElementById('card-errors');
                        errorElement.textContent = `Unexpected payment status: ${updatedIntent.status}`;

                        // Reset button
                        submitButton.disabled = false;
                        submitButton.textContent = 'Try Again';
                    }
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