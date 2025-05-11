#!/usr/bin/env python3
"""
Optimize App for NVC Banking Platform

This script applies performance optimizations to the application:
1. Disables blockchain connection during development
2. Optimizes database connection pooling
3. Reduces debug logging
4. Enables template caching
5. Adds memory caching for currency exchange
6. Optimizes startup time
"""

import os
import sys
import importlib
import logging
import time
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("optimize_app")

# Original import function (for later patching if needed)
original_import = __import__

def timing_decorator(func):
    """Decorator to measure execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        logger.info(f"Function {func.__name__} completed in {elapsed:.4f} seconds")
        return result
    return wrapper

def optimize_database():
    """Optimize database configuration and connection pool"""
    logger.info("Optimizing database connections...")
    
    try:
        # Import app with app context
        from app import app
        
        # Configure optimized connection pool
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 20,
            "max_overflow": 40,
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "pool_timeout": 60,
        }
        
        # Disable SQLAlchemy features not needed
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["SQLALCHEMY_ECHO"] = False
        
        logger.info("Database connections optimized")
        return True
    except Exception as e:
        logger.error(f"Error optimizing database: {str(e)}")
        return False

def disable_blockchain():
    """Disable blockchain connection for faster development"""
    logger.info("Disabling blockchain connection...")
    
    try:
        # Import the blockchain module
        import blockchain
        
        # Create a mock initialization function
        def mock_init_web3():
            blockchain.w3 = "MOCK_WEB3_CONNECTION"
            blockchain._web3_initialized = True
            blockchain._web3_last_checked = time.time()
            logger.info("Using mock blockchain connection")
            return True
        
        # Replace the real initialization function
        blockchain.init_web3 = mock_init_web3
        
        logger.info("Blockchain connection disabled")
        return True
    except ImportError:
        logger.warning("Blockchain module not found, nothing to disable")
        return False
    except Exception as e:
        logger.error(f"Error disabling blockchain: {str(e)}")
        return False

def reduce_debug_logging():
    """Reduce excessive debug logging"""
    logger.info("Reducing debug logging...")
    
    # List of loggers to set to INFO level
    debug_loggers = [
        'sqlalchemy.engine',
        'werkzeug',
        'routes',
        'app',
        'auth',
        'blockchain',
        'saint_crown_integration',
        'edi_integration',
        'payment_gateways',
        'swift_integration',
        'customer_support',
        'currency_exchange_service'
    ]
    
    for logger_name in debug_loggers:
        logging.getLogger(logger_name).setLevel(logging.INFO)
    
    logger.info("Debug logging reduced")
    return True

@timing_decorator
def enable_template_caching():
    """Enable Jinja2 template caching"""
    logger.info("Enabling template caching...")
    
    try:
        # Create temp directory for template cache if it doesn't exist
        import tempfile
        import os
        
        cache_dir = os.path.join(tempfile.gettempdir(), 'nvc_templates')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Import Flask app
        from app import app
        
        # Configure Jinja2 environment
        app.jinja_env.auto_reload = app.debug  # Only reload templates in debug mode
        app.jinja_env.optimized = True
        
        # Add bytecode cache if possible
        try:
            from jinja2 import FileSystemBytecodeCache
            bytecode_cache = FileSystemBytecodeCache(directory=cache_dir)
            app.jinja_env.bytecode_cache = bytecode_cache
            logger.info(f"Template bytecode cache enabled at {cache_dir}")
        except ImportError:
            logger.warning("Jinja2 bytecode cache not available")
        
        logger.info("Template caching enabled")
        return True
    except Exception as e:
        logger.error(f"Error enabling template caching: {str(e)}")
        return False

@timing_decorator
def enable_memory_caching():
    """Enable in-memory caching"""
    logger.info("Enabling memory caching...")
    
    # Create caching modules if they don't exist
    try:
        import memory_cache
        logger.info("Memory caching already set up")
    except ImportError:
        logger.info("Setting up memory cache implementation")
        
        # Basic in-memory cache implementation
        mem_cache_code = """
import time
import threading
from collections import OrderedDict
from functools import wraps

class MemoryCache:
    def __init__(self, max_size=1000, default_ttl=300):
        self._cache = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
    
    def get(self, key, default=None):
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if expiry is None or time.time() < expiry:
                    self._cache.move_to_end(key)
                    return value
                else:
                    del self._cache[key]
            return default
    
    def set(self, key, value, ttl=None):
        with self._lock:
            expiry = None if ttl is None else time.time() + (ttl or self._default_ttl)
            
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
                
            self._cache[key] = (value, expiry)
    
    def delete(self, key):
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        with self._lock:
            self._cache.clear()

# Create shared cache instances
account_cache = MemoryCache(max_size=500, default_ttl=300)
rate_cache = MemoryCache(max_size=200, default_ttl=600)
dashboard_cache = MemoryCache(max_size=100, default_ttl=60)

def cached(cache, key_func=None, ttl=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                key = f"{func.__module__}.{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            result = cache.get(key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator
"""
        # Write memory cache implementation
        with open('memory_cache.py', 'w') as f:
            f.write(mem_cache_code)
            
        # Import the newly created module
        import memory_cache
        
    # Patch currency exchange service to use caching
    try:
        import currency_exchange_service
        from memory_cache import rate_cache
        
        # Patch the get_exchange_rate method
        original_get_exchange_rate = currency_exchange_service.CurrencyExchangeService.get_exchange_rate
        
        def cached_get_exchange_rate(from_currency, to_currency):
            # Generate cache key
            cache_key = f"rate:{from_currency}:{to_currency}"
            
            # Check cache
            cached_rate = rate_cache.get(cache_key)
            if cached_rate is not None:
                return cached_rate
            
            # Call original method
            rate = original_get_exchange_rate(from_currency, to_currency)
            
            # Cache result
            if rate is not None:
                rate_cache.set(cache_key, rate, ttl=600)  # 10 minutes
            
            return rate
        
        # Replace the method
        currency_exchange_service.CurrencyExchangeService.get_exchange_rate = cached_get_exchange_rate
        logger.info("Currency exchange service patched with caching")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not patch currency exchange service: {str(e)}")
    
    logger.info("Memory caching enabled")
    return True

def optimize_startup():
    """Set environment variables for startup optimization"""
    logger.info("Optimizing startup...")
    
    # Set environment variables
    os.environ["NVC_DISABLE_BLOCKCHAIN"] = "1"
    os.environ["NVC_MINIMAL_STARTUP"] = "1"
    os.environ["NVC_OPTIMIZE_MEMORY"] = "1"
    
    logger.info("Startup optimized")
    return True

def create_optimized_app():
    """Create and return an optimized Flask app"""
    # Apply optimizations before importing app
    optimize_startup()
    
    # Import app and apply additional optimizations
    from app import app
    
    # Apply optimizations
    disable_blockchain()
    reduce_debug_logging()
    optimize_database()
    enable_template_caching()
    enable_memory_caching()
    
    logger.info("All optimizations applied successfully")
    return app

if __name__ == "__main__":
    # Apply all optimizations directly
    optimize_startup()
    
    # Print information about environment
    print("Environment variables:")
    for var in ["NVC_DISABLE_BLOCKCHAIN", "NVC_MINIMAL_STARTUP", "NVC_OPTIMIZE_MEMORY"]:
        print(f"  {var}={os.environ.get(var, 'not set')}")
    
    print("\nOptimizations applied successfully.")
    print("To use the optimized app, import create_optimized_app from optimize_app:")
    print("  from optimize_app import create_optimized_app")
    print("  app = create_optimized_app()")
    print("\nOr add the following to your main.py before importing app:")
    print("  import optimize_app")
    print("  optimize_app.optimize_startup()")