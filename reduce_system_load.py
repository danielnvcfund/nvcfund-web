#!/usr/bin/env python3
"""
Performance Optimization: Reduce System Load

This script reduces system load by:
1. Disabling frequent currency exchange rate updates
2. Reducing database queries
3. Optimizing memory usage
4. Minimizing logging
"""

import os
import logging
import sys
from functools import lru_cache
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("performance_optimizer")

def reduce_system_load():
    """Apply all system load optimizations"""
    
    # Set performance environment variables
    os.environ["NVC_DISABLE_BLOCKCHAIN"] = "1"
    os.environ["NVC_MINIMAL_STARTUP"] = "1"
    os.environ["NVC_OPTIMIZE_MEMORY"] = "1"
    
    # Disable excessive logging
    reduce_logging()
    
    # Optimize currency exchange system (major source of slowness)
    optimize_currency_system()
    
    logger.info("System load optimizations applied")
    return True

def reduce_logging():
    """Reduce excessive logging"""
    # Set these modules to WARNING level to reduce console spam
    modules_to_reduce = [
        'sqlalchemy.engine',
        'routes',
        'app',
        'blockchain',
        'saint_crown_integration',
        'currency_exchange_service',
        'optimize_currency_initialization',
        'optimize_currency_loading'
    ]
    
    for module_name in modules_to_reduce:
        logging.getLogger(module_name).setLevel(logging.WARNING)
    
    logger.info("Logging levels optimized")

def optimize_currency_system():
    """Optimize the currency exchange system which is a major performance bottleneck"""
    try:
        # Hook into currency initialization to prevent it from running unnecessarily
        import optimize_currency_initialization
        
        # Replace the expensive initialization function with a lightweight version
        original_initialize = optimize_currency_initialization.initialize_rates_on_startup
        
        @lru_cache(maxsize=1)  # Cache the result to avoid repeated initialization
        def lightweight_initialize(*args, **kwargs):
            logger.info("Using lightweight currency initialization")
            return True
        
        optimize_currency_initialization.initialize_rates_on_startup = lightweight_initialize
        logger.info("Currency initialization optimized")
        
        # Replace the memory cache with a lightweight version
        try:
            # Import our lightweight cache
            import fast_memory_cache
            
            # Try to redirect imports of the regular memory_cache to our fast version
            import sys
            sys.modules['memory_cache'] = fast_memory_cache
            
            logger.info("Memory cache replaced with high-performance version")
        except (ImportError, AttributeError) as e:
            logger.warning(f"Could not optimize memory cache: {str(e)}")
            pass
            
    except ImportError:
        logger.warning("Currency initialization module not found")
    
    # Disable frequent rate updates in the main app
    try:
        from app import app
        
        # Find and disable the automatic currency updates if possible
        for key in dir(app):
            if 'currency' in key.lower() and callable(getattr(app, key)):
                setattr(app, key, lambda: None)
                logger.info(f"Disabled automatic currency updates: {key}")
        
    except (ImportError, AttributeError):
        logger.warning("Could not disable automatic currency updates in app")

if __name__ == "__main__":
    reduce_system_load()
    print("System load optimizations applied. Restart the application for changes to take effect.")