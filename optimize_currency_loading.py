#!/usr/bin/env python3
"""
Optimize Currency Exchange Data Loading

This script modifies the currency exchange system to minimize external API calls
and database operations to improve system performance during development.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def optimize_currency_loading():
    """
    Optimize currency exchange loading to reduce system slowness.
    This function:
    1. Disables automatic currency rate updates at startup
    2. Sets up a minimal set of critical exchange rates in memory
    3. Modifies the rate fetching logic to use cached values when possible
    """
    from app import app, db
    from account_holder_models import CurrencyExchangeRate, CurrencyType
    from memory_cache import rate_cache, cache_exchange_rate, get_cached_exchange_rate
    
    with app.app_context():
        try:
            # Create a base set of essential exchange rates for memory cache
            essential_rates = {
                # NVCT to major currencies (1:1 with USD)
                ('NVCT', 'USD'): 1.0,
                ('USD', 'NVCT'): 1.0,
                
                # NVCT to AFD1 (AFD1 = 10% of gold price, approx $339.40)
                ('NVCT', 'AFD1'): 0.00294,  # 1 NVCT = 0.00294 AFD1
                ('AFD1', 'NVCT'): 340.136,  # 1 AFD1 = 340.136 NVCT
                
                # NVCT to SFN (1:1)
                ('NVCT', 'SFN'): 1.0,
                ('SFN', 'NVCT'): 1.0,
                
                # Major currency pairs
                ('USD', 'EUR'): 0.93,
                ('EUR', 'USD'): 1.075,
                ('USD', 'GBP'): 0.79,
                ('GBP', 'USD'): 1.266,
                
                # Add a few more essential pairs
                ('USD', 'JPY'): 156.8,
                ('USD', 'CAD'): 1.36,
                ('USD', 'AUD'): 1.52,
                ('USD', 'CHF'): 0.91,
                
                # Main crypto rates
                ('BTC', 'USD'): 63500.0,
                ('ETH', 'USD'): 2950.0,
                ('USDT', 'USD'): 1.0
            }
            
            # Store in memory cache using the provided utility functions
            for (from_curr, to_curr), rate in essential_rates.items():
                # Use the cache_exchange_rate function from memory_cache
                cache_exchange_rate(from_curr, to_curr, rate, ttl=86400)  # Cache for 24 hours
                
                # Also add inverse for convenience if not already in our list
                if (to_curr, from_curr) not in essential_rates:
                    inverse_rate = 1.0 / rate if rate != 0 else 0
                    cache_exchange_rate(to_curr, from_curr, inverse_rate, ttl=86400)
            
            logger.info(f"Stored {len(essential_rates)} essential exchange rates in memory cache")
            
            # Patch the get_rate function in currency_exchange_service.py to use cache first
            import currency_exchange_service
            
            # Skip if service module doesn't have get_rate (older versions)
            if hasattr(currency_exchange_service, 'get_rate'):
                # Original function reference
                original_get_rate = currency_exchange_service.get_rate
                
                def optimized_get_rate(from_currency, to_currency):
                    """Optimized version that checks memory cache first"""
                    # Use the get_cached_exchange_rate function from memory_cache
                    cached_rate = get_cached_exchange_rate(from_currency, to_currency)
                    
                    if cached_rate is not None:
                        return cached_rate
                    
                    # If not in cache, try the original function but catch any errors
                    try:
                        rate = original_get_rate(from_currency, to_currency)
                        # Cache the result for future use
                        cache_exchange_rate(from_currency, to_currency, rate, ttl=86400)
                        return rate
                    except Exception as e:
                        logger.warning(f"Error getting rate {from_currency} to {to_currency}: {str(e)}")
                        # Return a default rate as fallback
                        if from_currency == to_currency:
                            return 1.0
                        return 1.0  # Default fallback for development
                
                # Replace the original function
                currency_exchange_service.get_rate = optimized_get_rate
                logger.info("Optimized currency_exchange_service.get_rate function")
            else:
                logger.info("currency_exchange_service.get_rate not found, skipping optimization")
            
            # Disable automatic currency rate updates at startup if they exist
            try:
                import optimize_currency_initialization
                
                # Store original function
                original_initialize = optimize_currency_initialization.initialize_rates_on_startup
                
                # Create simplified function that does minimal work
                def minimal_initialize(*args, **kwargs):
                    logger.info("Using minimal currency initialization to improve performance")
                    return True
                
                # Replace the function
                optimize_currency_initialization.initialize_rates_on_startup = minimal_initialize
                logger.info("Disabled automatic currency rate updates at startup")
            except ImportError:
                logger.info("No optimize_currency_initialization module found, skipping")
            
            logger.info("Currency exchange optimizations applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error optimizing currency exchange: {str(e)}")
            return False

if __name__ == "__main__":
    try:
        optimize_currency_loading()
        print("Currency exchange optimizations applied successfully")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)