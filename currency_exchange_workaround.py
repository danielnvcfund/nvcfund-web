"""
Currency Exchange Workaround
This module provides a workaround for database limitations with certain currency codes
"""
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# File to store exchange rates
RATES_FILE = 'currency_rates.json'

def load_rates():
    """Load exchange rates from the JSON file"""
    try:
        if os.path.exists(RATES_FILE):
            with open(RATES_FILE, 'r') as f:
                rates = json.load(f)
                logger.info(f"Loaded {len(rates)} exchange rate pairs from file")
                return rates
        return {}
    except Exception as e:
        logger.error(f"Error loading rates from file: {str(e)}")
        return {}

def save_rates(rates):
    """Save exchange rates to the JSON file"""
    try:
        with open(RATES_FILE, 'w') as f:
            json.dump(rates, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving rates to file: {str(e)}")
        return False

def get_rate(from_currency, to_currency):
    """Get exchange rate from file-based storage"""
    rates = load_rates()
    key = f"{from_currency}_{to_currency}"
    
    if key in rates:
        return rates[key]['rate'], rates[key]['updated']
    
    # Check if inverse rate exists and calculate
    inverse_key = f"{to_currency}_{from_currency}"
    if inverse_key in rates:
        inverse_rate = rates[inverse_key]['rate']
        if inverse_rate > 0:
            return 1.0 / inverse_rate, rates[inverse_key]['updated']
    
    return None, None

def get_exchange_rate(from_currency, to_currency):
    """Get exchange rate (compatibility method for service calls)"""
    rate, _ = get_rate(from_currency, to_currency)
    return rate

def update_rate(from_currency, to_currency, rate):
    """Update exchange rate in file-based storage"""
    rates = load_rates()
    key = f"{from_currency}_{to_currency}"
    
    rates[key] = {
        'rate': rate,
        'updated': datetime.utcnow().isoformat(),
        'from': from_currency,
        'to': to_currency
    }
    
    # Also update inverse rate for convenience
    if rate > 0:
        inverse_key = f"{to_currency}_{from_currency}"
        rates[inverse_key] = {
            'rate': 1.0 / rate,
            'updated': datetime.utcnow().isoformat(),
            'from': to_currency, 
            'to': from_currency
        }
    
    return save_rates(rates)

def is_problematic_currency(currency_code):
    """Check if a currency code is known to cause database issues"""
    problematic_currencies = [
        "XOF", "XAF", "XPF", "XUA", "XDR", "XTS", "XXX"
    ]
    return currency_code in problematic_currencies

def initialize_african_currency_rates():
    """Initialize exchange rates for African currencies that can't be stored in the database"""
    # CFA Franc BCEAO - 8 West African countries
    update_rate("USD", "XOF", 600.0)    # Approx 600 XOF per USD
    update_rate("NVCT", "XOF", 600.0)   # Same as USD (NVCT pegged 1:1 to USD)
    
    # CFA Franc BEAC - 6 Central African countries
    update_rate("USD", "XAF", 600.0)    # Approx 600 XAF per USD
    update_rate("NVCT", "XAF", 600.0)   # Same as USD
    
    logger.info(f"African currency exchange rates initialized")