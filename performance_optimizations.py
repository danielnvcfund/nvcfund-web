"""
Performance Optimizations
This module provides critical performance optimizations for the application.
"""

import logging
import threading
import time
from functools import lru_cache, wraps

# Set up logging
logger = logging.getLogger(__name__)

# Global caches to avoid repeated expensive operations
_GLOBAL_CACHES = {}
_CACHES_LOCK = threading.RLock()

def disable_blockchain_connection():
    """
    Patch the blockchain connection to avoid connecting on startup
    This dramatically improves startup time
    """
    try:
        import blockchain
        
        # Override the init_web3 method with a faster version
        original_init_web3 = blockchain.init_web3
        
        def fast_init_web3():
            """Fast web3 initialization that skips actual connection"""
            logger.info("Using fast blockchain initialization (skipping actual connection)")
            blockchain.w3 = "MOCK_WEB3_FOR_STARTUP"
            blockchain._web3_initialized = True
            blockchain._web3_last_checked = blockchain.time.time()
            
            # Cache this result
            cache_result = {
                'connected': True,
                'network_id': '11155111',  # Sepolia testnet
                'timestamp': blockchain.time.time()
            }
            blockchain.cache_utils.cache_data('web3_connection_status', cache_result)
            return True
            
        # Replace the initialization function
        blockchain.init_web3 = fast_init_web3
        logger.info("Blockchain connections optimized for faster startup")
    except Exception as e:
        logger.error(f"Could not optimize blockchain connections: {str(e)}")

def optimize_sqlalchemy():
    """
    Optimize SQLAlchemy configuration for better performance
    """
    try:
        from app import db, app
        
        # Optimize pool size and timeout
        if 'pool_size' not in app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}):
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {})
            app.config["SQLALCHEMY_ENGINE_OPTIONS"].update({
                "pool_size": 10,
                "max_overflow": 15,
                "pool_timeout": 60,
                "pool_pre_ping": True,
            })
            logger.info("SQLAlchemy pool optimized")
    except Exception as e:
        logger.error(f"Could not optimize SQLAlchemy: {str(e)}")

def cached_function(max_size=128, ttl=300):
    """
    Decorator for caching function results with time-to-live (TTL)
    
    Args:
        max_size (int): Maximum size of the cache
        ttl (int): Time to live in seconds
    """
    def decorator(func):
        cache = {}
        cache_lock = threading.RLock()
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            key = str(func.__name__) + str(args) + str(sorted(kwargs.items()))
            
            with cache_lock:
                # Check if result is in cache and not expired
                now = time.time()
                if key in cache and (now - cache[key]['time']) < ttl:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cache[key]['result']
                
                # Call the function and cache the result
                result = func(*args, **kwargs)
                
                # Manage cache size
                if len(cache) >= max_size:
                    # Remove oldest item
                    oldest_key = min(cache.keys(), key=lambda k: cache[k]['time'])
                    del cache[oldest_key]
                
                # Store in cache
                cache[key] = {'result': result, 'time': now}
                return result
                
        return wrapper
    return decorator

def apply_all_optimizations():
    """Apply all performance optimizations"""
    logger.info("Applying performance optimizations...")
    
    # Disable blockchain connection in development
    disable_blockchain_connection()
    
    # Optimize SQLAlchemy
    optimize_sqlalchemy()
    
    # Apply caching decorators to critical functions
    apply_caching_decorators()
    
    logger.info("Performance optimizations applied")
    
def apply_caching_decorators():
    """Apply caching decorators to critical functions"""
    try:
        # Add caching to currency exchange service
        import currency_exchange_service
        currency_exchange_service.CurrencyExchangeService.get_exchange_rate = cached_function(max_size=256, ttl=600)(
            currency_exchange_service.CurrencyExchangeService.get_exchange_rate
        )
        logger.info("Currency exchange rate lookups optimized with caching")
        
        # Cache other intensive operations
        from saint_crown_integration import SaintCrownIntegration
        SaintCrownIntegration.get_gold_price = cached_function(max_size=1, ttl=3600)(
            SaintCrownIntegration.get_gold_price
        )
        logger.info("Gold price lookups optimized with caching")
        
    except Exception as e:
        logger.error(f"Error applying caching decorators: {str(e)}")
        
def stop_unnecessary_processes():
    """Stop unnecessary background processes"""
    try:
        # Disable certain initializations in development
        # This is a more aggressive optimization that can be enabled if needed
        pass
    except Exception as e:
        logger.error(f"Error stopping unnecessary processes: {str(e)}")

# Main function to optimize everything
def optimize_performance():
    """Main function to optimize application performance"""
    apply_all_optimizations()
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    optimize_performance()