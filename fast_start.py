#!/usr/bin/env python3
"""
Fast Startup Script for NVC Banking Platform

This script implements various optimizations to dramatically improve startup time
and overall performance of the application.

Key optimizations:
1. Disable unnecessary services during development
2. Lazy loading of resources
3. In-memory caching of frequently accessed data
4. Database connection pooling and optimization
5. Asynchronous loading of secondary resources
"""

import os
import sys
import logging
import time
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("fast_start")

# Track startup performance
startup_begin = time.time()
logger.info("Starting NVC Banking Platform with performance optimizations...")

# Apply optimizations before importing any application modules
def disable_heavy_processing():
    """Set environment variables to disable heavy processing during startup"""
    os.environ["NVC_DISABLE_BLOCKCHAIN"] = "1"
    os.environ["NVC_MINIMAL_STARTUP"] = "1"
    os.environ["NVC_OPTIMIZE_MEMORY"] = "1"
    logger.info("Set optimization environment variables")

def preload_critical_modules():
    """Preload critical modules to avoid import delays during startup"""
    try:
        # Import performance optimization first
        import performance_optimizations
        performance_optimizations.optimize_performance()
        logger.info("Applied performance optimizations")
        
        # Set up the database connection pool before importing models
        from app import db
        logger.info("Database connection pool initialized")
        
        # Preload models (but avoid running any code)
        import account_holder_models
        logger.info("Account holder models preloaded")
        
        # Import currency optimization
        import optimize_currency_initialization
        logger.info("Currency initialization optimized")
        
        return True
    except Exception as e:
        logger.error(f"Error during module preloading: {str(e)}")
        return False

def start_app():
    """Start the Flask application"""
    try:
        # Now import the application
        from app import app
        
        # Apply any final optimizations
        import performance_optimizations
        performance_optimizations.optimize_sqlalchemy()
        
        # Track and report startup time
        startup_time = time.time() - startup_begin
        logger.info(f"Application ready in {startup_time:.2f} seconds")
        
        # Return the app instance for gunicorn
        return app
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}")
        sys.exit(1)

# Apply optimizations and start the application
disable_heavy_processing()
preload_critical_modules()
app = start_app()

# Start background optimization thread
def background_optimizations():
    """Perform background optimizations after app is started"""
    try:
        time.sleep(5)  # Wait for app to fully start
        logger.info("Running background optimizations...")
        
        # Import and apply cache warmup
        try:
            from currency_exchange_service import CurrencyExchangeService
            # Warm up commonly used exchange rates
            CurrencyExchangeService.get_exchange_rate(
                account_holder_models.CurrencyType.NVCT, 
                account_holder_models.CurrencyType.USD
            )
            logger.info("Cache warmup completed")
        except Exception as e:
            logger.error(f"Error in cache warmup: {str(e)}")
    except Exception as e:
        logger.error(f"Error in background optimizations: {str(e)}")

# Start background thread if not in test mode
if __name__ != "__main__":
    bg_thread = threading.Thread(target=background_optimizations)
    bg_thread.daemon = True
    bg_thread.start()

if __name__ == "__main__":
    # This block runs when script is executed directly (not through gunicorn)
    print("This script is intended to be run through gunicorn.")
    print(f"Application startup completed in {time.time() - startup_begin:.2f} seconds")
    sys.exit(0)