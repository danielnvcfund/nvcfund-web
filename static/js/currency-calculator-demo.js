/**
 * Currency Exchange Calculator with Improved Error Handling
 * 
 * Changes made to fix issues:
 * 1. Added robust error handling for currency metadata
 * 2. Added fallback handling for fee calculation (handles both 'fee' and 'fee_amount' field names)
 * 3. Added multiple fallbacks for the converted amount calculation
 * 
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize calculator elements
    const calculatorForm = document.getElementById('exchange-calculator-form');
    const calculationResult = document.getElementById('calculation-result');
    
    if (!calculatorForm || !calculationResult) {
        console.error("Required calculator elements not found");
        return;
    }
    
    // Currency metadata for display
    const currencyMetadata = {
        'USD': {
            flag: '/static/images/flags/us.svg',
            country: 'United States',
            name: 'US Dollar',
            symbol: '$'
        },
        'EUR': {
            flag: '/static/images/flags/eu.svg',
            country: 'European Union',
            name: 'Euro',
            symbol: '€'
        },
        'GBP': {
            flag: '/static/images/flags/gb.svg',
            country: 'United Kingdom',
            name: 'British Pound',
            symbol: '£'
        },
        'NVCT': {
            flag: '/static/images/nvct.svg',
            country: 'Global',
            name: 'NVC Token',
            symbol: 'NVCT'
        }
    };
    
    // Function to safely get currency metadata with robust error handling
    function getCurrencyMetadata(code) {
        try {
            return currencyMetadata[code] || { 
                flag: '/static/images/flags/globe.svg', 
                country: 'Global',
                name: code
            };
        } catch (error) {
            console.error("Error getting metadata for " + code, error);
            return { 
                flag: '/static/images/flags/globe.svg', 
                country: 'Global',
                name: code
            };
        }
    }
    
    // Form submission
    calculatorForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const fromCurrency = document.getElementById('from-currency').value;
        const toCurrency = document.getElementById('to-currency').value;
        const amount = parseFloat(document.getElementById('amount').value);
        
        // Call API to get exchange rate
        fetch('/api/exchange/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                from_currency: fromCurrency,
                to_currency: toCurrency,
                amount: amount
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log("API response:", data);
            if (data.success) {
                // Display the result
                // Add function to format numbers with comma separators
                function formatNumber(num) {
                    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                }
                
                // Get metadata for currencies
                // Safely get currency metadata with fallbacks
                let fromMeta;
                let toMeta;
                
                try {
                    fromMeta = getCurrencyMetadata(fromCurrency) || { 
                        flag: '/static/images/flags/globe.svg', 
                        country: 'Global',
                        name: fromCurrency
                    };
                } catch (error) {
                    console.error("Error getting metadata for " + fromCurrency, error);
                    fromMeta = { 
                        flag: '/static/images/flags/globe.svg', 
                        country: 'Global',
                        name: fromCurrency
                    };
                }
                
                try {
                    toMeta = getCurrencyMetadata(toCurrency) || {
                        flag: '/static/images/flags/globe.svg', 
                        country: 'Global',
                        name: toCurrency
                    };
                } catch (error) {
                    console.error("Error getting metadata for " + toCurrency, error);
                    toMeta = { 
                        flag: '/static/images/flags/globe.svg', 
                        country: 'Global',
                        name: toCurrency
                    };
                }
                
                // Ensure all required properties are available
                const fromFlag = fromMeta && fromMeta.flag ? fromMeta.flag : '/static/images/flags/globe.svg';
                const fromCountry = fromMeta && fromMeta.country ? fromMeta.country : 'Global';
                
                const toFlag = toMeta && toMeta.flag ? toMeta.flag : '/static/images/flags/globe.svg';
                const toCountry = toMeta && toMeta.country ? toMeta.country : 'Global';
                
                // Build HTML with flags
                const rateHTML = `
                  <span class="currency-display">
                    <img src="${fromFlag}" alt="${fromCountry}" class="currency-flag" width="16" height="16">
                    1 ${fromCurrency}
                  </span> = 
                  <span class="currency-display">
                    <img src="${toFlag}" alt="${toCountry}" class="currency-flag" width="16" height="16">
                    ${formatNumber(data.rate)} ${toCurrency}
                  </span>`;
                  
                const amountHTML = `
                  <span class="currency-display">
                    <img src="${fromFlag}" alt="${fromCountry}" class="currency-flag" width="16" height="16">
                    ${formatNumber(amount)} ${fromCurrency}
                  </span>`;
                  
                // Safely handle fee data
                let fee = 0;
                if (typeof data.fee === 'number') {
                    fee = data.fee;
                } else if (typeof data.fee_amount === 'number') {
                    fee = data.fee_amount;
                }
                
                const feeHTML = `
                  <span class="currency-display">
                    <img src="${fromFlag}" alt="${fromCountry}" class="currency-flag" width="16" height="16">
                    ${formatNumber(fee.toFixed(2))} ${fromCurrency}
                  </span>`;
                  
                // Safely handle converted amount
                let convertedAmount = 0;
                if (typeof data.converted_amount === 'number') {
                    convertedAmount = data.converted_amount;
                } else if (typeof data.to_amount === 'number') {
                    convertedAmount = data.to_amount;
                } else if (typeof data.rate === 'number') {
                    convertedAmount = amount * data.rate;
                }
                
                const finalHTML = `
                  <span class="currency-display">
                    <img src="${toFlag}" alt="${toCountry}" class="currency-flag" width="16" height="16">
                    ${formatNumber(convertedAmount.toFixed(2))} ${toCurrency}
                  </span>`;
                
                document.getElementById('result-rate').innerHTML = rateHTML;
                document.getElementById('result-amount').innerHTML = amountHTML;
                document.getElementById('result-fee').innerHTML = feeHTML;
                document.getElementById('result-final').innerHTML = finalHTML;
                
                // Show the result container
                calculationResult.classList.remove('d-none');
            } else {
                alert(`Error: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while calculating the exchange. Please try again.');
        });
    });
});