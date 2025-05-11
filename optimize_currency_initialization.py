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
        # Make sure we're working with the enum, not a string
        if isinstance(currency_code, CurrencyType):
            return currency_code
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
    
    # Store successful rates for memory-only operation
    memory_only_rates = []
    
    # Batch database updates
    try:
        with db.session.begin():
            for from_currency, to_currency, rate, source in rates_data:
                # Make sure we have actual enum values, not strings
                if isinstance(from_currency, str):
                    from_currency = get_currency_enum(from_currency)
                if isinstance(to_currency, str):
                    to_currency = get_currency_enum(to_currency)
                
                # Skip if we couldn't get proper enum values
                if not from_currency or not to_currency:
                    logger.warning(f"Skipping rate update for invalid currency codes")
                    memory_only_rates.append((
                        str(from_currency) if from_currency else "unknown", 
                        str(to_currency) if to_currency else "unknown",
                        rate, source
                    ))
                    continue
                    
                # Calculate inverse rate
                inverse_rate = 1 / rate if rate != 0 else 0
                
                try:
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
                        # Create new rate using constructor without direct parameters
                        new_rate = CurrencyExchangeRate()
                        new_rate.from_currency = from_currency
                        new_rate.to_currency = to_currency
                        new_rate.rate = rate
                        new_rate.inverse_rate = inverse_rate
                        new_rate.source = source
                        new_rate.last_updated = datetime.utcnow()
                        new_rate.is_active = True
                        db.session.add(new_rate)
                except Exception as rate_error:
                    logger.warning(f"Skipping problematic rate {from_currency} to {to_currency}: {str(rate_error)}")
                    memory_only_rates.append((str(from_currency), str(to_currency), rate, source))
                    
    except Exception as e:
        logger.error(f"Error in batch update of exchange rates: {str(e)}")
        db.session.rollback()
        
        # Still keep rates in memory even if database fails
        for from_currency, to_currency, rate, source in rates_data:
            memory_only_rates.append((str(from_currency), str(to_currency), rate, source))
        
        logger.info(f"Stored {len(memory_only_rates)} rates in memory cache despite database error")
        return False
    
    # Log any memory-only rates
    if memory_only_rates:
        logger.info(f"Stored {len(memory_only_rates)} rates in memory cache only")
        
    return True

@timing_decorator
def initialize_rates_on_startup():
    """
    Initialize critical exchange rates on application startup
    
    This function focuses on only the most important currency pairs to
    reduce startup time, while still ensuring core functionality works.
    """
    # First, load in-memory cache only without database operations
    initialize_memory_cache()
    
    # Then add essential rates to the database with careful validation
    initialize_database_rates()
    
    return len(_EXCHANGE_RATE_CACHE)

def initialize_memory_cache():
    """Initialize a larger set of rates in memory only for fast lookups"""
    # Define the core currency codes to initialize in memory
    memory_currencies = [
        # Core pairs - always initialize these in memory
        ("NVCT", "USD", 1.0),
        ("USD", "EUR", 0.92),
        ("USD", "GBP", 0.79),
        ("USD", "JPY", 156.75),
        ("USD", "CHF", 0.91),
        ("USD", "CAD", 1.37),
        ("USD", "AUD", 1.52),
        ("USD", "CNY", 7.23),
        ("USD", "HKD", 7.82),
        ("BTC", "USD", 61452.83),
        ("ETH", "USD", 3076.25),
        ("NVCT", "AFD1", 0.00294),  # Based on AFD1 = $339.40
        ("NVCT", "SFN", 1.0),        # 1:1 with NVCT
        ("NVCT", "AKLUMI", 0.307692), # 1 AKLUMI = $3.25
        # African currencies
        ("USD", "NGN", 1500.00),
        ("USD", "ZAR", 18.50),
        ("USD", "EGP", 47.25),
        ("USD", "GHS", 15.34),
        # Other cryptocurrencies
        ("BNB", "USD", 577.32),
        ("SOL", "USD", 146.12),
        ("XRP", "USD", 0.51),
    ]
    
    # Update memory cache directly
    for from_code, to_code, rate in memory_currencies:
        try:
            from_currency = get_currency_enum(from_code)
            to_currency = get_currency_enum(to_code)
            
            if from_currency and to_currency:
                # Only update memory cache, skip database
                set_exchange_rate_in_cache(from_currency, to_currency, rate)
                
                # Also store inverse rates
                inverse_rate = 1 / rate if rate != 0 else 0
                set_exchange_rate_in_cache(to_currency, from_currency, inverse_rate)
        except Exception as e:
            logger.warning(f"Error caching rate {from_code}/{to_code}: {str(e)}")
    
    logger.info(f"Initialized {len(_EXCHANGE_RATE_CACHE)} rates in memory cache")
    return len(_EXCHANGE_RATE_CACHE)

def initialize_database_rates():
    """Initialize only verified essential rates in the database"""
    from app import db
    from account_holder_models import CurrencyExchangeRate, CurrencyType
    
    # List of definitively valid rates we know will work
    essential_rates = [
        (CurrencyType.NVCT, CurrencyType.USD, 1.0, "system_initialization"),
        (CurrencyType.NVCT, CurrencyType.AFD1, 0.00294, "system_initialization"),
        (CurrencyType.NVCT, CurrencyType.SFN, 1.0, "system_initialization"),
    ]
    
    # Update each rate individually with careful error handling
    successful = 0
    
    for from_currency, to_currency, rate, source in essential_rates:
        try:
            # Calculate inverse rate
            inverse_rate = 1 / rate if rate != 0 else 0
            
            # Use a new session for each rate to isolate errors
            with db.session.begin():
                # Try to fetch existing rate
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
                    # Create new rate using attribute assignment
                    new_rate = CurrencyExchangeRate()
                    new_rate.from_currency = from_currency
                    new_rate.to_currency = to_currency
                    new_rate.rate = rate
                    new_rate.inverse_rate = inverse_rate
                    new_rate.source = source
                    new_rate.is_active = True
                    new_rate.last_updated = datetime.utcnow()
                    db.session.add(new_rate)
                    
            successful += 1
        except Exception as e:
            logger.error(f"Error updating rate {from_currency} to {to_currency}: {str(e)}")
    
    logger.info(f"Successfully updated {successful} essential rates in database")
    return successful

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    num_rates = initialize_rates_on_startup()
    print(f"Initialized {num_rates} critical exchange rates")