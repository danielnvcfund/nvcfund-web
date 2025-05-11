"""
Optimized Currency Exchange Rate Initialization

This module provides optimized functions for initializing currency exchange rates.
It uses various performance optimizations to reduce startup time:

1. In-memory caching of exchange rates
2. Selective initialization of only frequently used currencies
3. Asynchronous updates for less commonly used rates
4. Batched database operations
"""

import logging
import time
from datetime import datetime
from functools import lru_cache
import threading
from account_holder_models import CurrencyType, CurrencyExchangeRate

# Set up logging
logger = logging.getLogger(__name__)

# Global cache for exchange rates
_EXCHANGE_RATE_CACHE = {}
_EXCHANGE_CACHE_LOCK = threading.RLock()

def timing_decorator(func):
    """Decorator to measure execution time of a function"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
        return result
    return wrapper

@lru_cache(maxsize=256)
def get_currency_enum(currency_code):
    """Get currency enum value from string code with caching"""
    try:
        return getattr(CurrencyType, currency_code)
    except (AttributeError, KeyError):
        return None

def get_exchange_rate_from_cache(from_currency, to_currency):
    """Get exchange rate from in-memory cache"""
    cache_key = f"{from_currency.name}_{to_currency.name}"
    with _EXCHANGE_CACHE_LOCK:
        return _EXCHANGE_RATE_CACHE.get(cache_key)

def set_exchange_rate_in_cache(from_currency, to_currency, rate, inverse_rate=None):
    """Set exchange rate in in-memory cache"""
    if inverse_rate is None and rate:
        inverse_rate = 1 / rate if rate != 0 else 0
        
    with _EXCHANGE_CACHE_LOCK:
        # Store direct rate
        _EXCHANGE_RATE_CACHE[f"{from_currency.name}_{to_currency.name}"] = {
            'rate': rate,
            'timestamp': datetime.utcnow()
        }
        
        # Store inverse rate
        _EXCHANGE_RATE_CACHE[f"{to_currency.name}_{from_currency.name}"] = {
            'rate': inverse_rate,
            'timestamp': datetime.utcnow()
        }

def batch_update_exchange_rates(rates_data):
    """
    Update multiple exchange rates in a single database transaction
    
    Args:
        rates_data: List of tuples (from_currency, to_currency, rate, source)
    """
    from app import db
    
    # First, update in-memory cache
    for from_currency, to_currency, rate, source in rates_data:
        set_exchange_rate_in_cache(from_currency, to_currency, rate)
    
    # Batch database updates
    try:
        with db.session.begin():
            for from_currency, to_currency, rate, source in rates_data:
                # Calculate inverse rate
                inverse_rate = 1 / rate if rate != 0 else 0
                
                # Check if rate exists in database
                rate_obj = CurrencyExchangeRate.query.filter_by(
                    from_currency=from_currency,
                    to_currency=to_currency
                ).first()
                
                if rate_obj:
                    # Update existing rate
                    rate_obj.rate = rate
                    rate_obj.inverse_rate = inverse_rate
                    rate_obj.source = source
                    rate_obj.last_updated = datetime.utcnow()
                else:
                    # Create new rate
                    new_rate = CurrencyExchangeRate(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=rate,
                        inverse_rate=inverse_rate,
                        source=source,
                        last_updated=datetime.utcnow()
                    )
                    db.session.add(new_rate)
    except Exception as e:
        logger.error(f"Error in batch update of exchange rates: {str(e)}")
        db.session.rollback()
        return False
    
    return True

@timing_decorator
def initialize_rates_on_startup():
    """
    Initialize critical exchange rates on application startup
    
    This function focuses on only the most important currency pairs to
    reduce startup time, while still ensuring core functionality works.
    """
    # Define the core currency codes to initialize
    core_currencies = [
        # Core pairs - always initialize these
        ("NVCT", "USD", 1.0, "system_initialization"),
        ("USD", "EUR", 0.92, "system_initialization"),
        ("USD", "GBP", 0.79, "system_initialization"),
        ("USD", "JPY", 156.75, "system_initialization"),
        ("BTC", "USD", 61452.83, "system_initialization"),
        ("ETH", "USD", 3076.25, "system_initialization"),
        ("NVCT", "AFD1", 0.00294, "system_initialization"),  # Based on AFD1 = $339.40
        ("NVCT", "SFN", 1.0, "system_initialization"),        # 1:1 with NVCT
        ("NVCT", "AKLUMI", 0.307692, "system_initialization") # 1 AKLUMI = $3.25
    ]
    
    # Convert to proper enum values and collect for batch update
    rates_data = []
    for from_code, to_code, rate, source in core_currencies:
        from_currency = get_currency_enum(from_code)
        to_currency = get_currency_enum(to_code)
        
        if from_currency and to_currency:
            rates_data.append((from_currency, to_currency, rate, source))
    
    # Perform batch update
    batch_update_exchange_rates(rates_data)
    
    # Return number of rates initialized
    return len(rates_data)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    num_rates = initialize_rates_on_startup()
    print(f"Initialized {num_rates} critical exchange rates")