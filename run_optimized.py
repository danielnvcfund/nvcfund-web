#!/usr/bin/env python3
"""
Run Optimized Server for NVC Banking Platform

This script starts the application with performance optimizations.
"""

import os
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("run_optimized")

# Record startup time
start_time = time.time()

# Apply optimizations
logger.info("Starting NVC Banking Platform with optimizations...")

# Set performance environment variables
os.environ["NVC_DISABLE_BLOCKCHAIN"] = "1"
os.environ["NVC_MINIMAL_STARTUP"] = "1"
os.environ["NVC_OPTIMIZE_MEMORY"] = "1"

# Import optimization module
try:
    import optimize_app
    optimize_app.optimize_startup()
    optimize_app.reduce_debug_logging()
    logger.info("Applied startup optimizations")
except ImportError:
    logger.warning("optimize_app module not found, continuing without optimizations")
except Exception as e:
    logger.warning(f"Error applying optimizations: {str(e)}")

# Import app
try:
    from app import app, db
    
    # Apply core optimizations from optimize_app
    try:
        optimize_app.disable_blockchain()
        optimize_app.optimize_database()
    except (ImportError, AttributeError):
        pass
    
    # Additional runtime optimizations
    try:
        # Set SQLAlchemy echo to False (disable query logging)
        app.config["SQLALCHEMY_ECHO"] = False
        
        # Disable template auto-reload in production
        if not app.debug:
            app.jinja_env.auto_reload = False
            
        # Set up template cache if supported
        try:
            import tempfile
            from jinja2 import FileSystemBytecodeCache
            
            cache_dir = os.path.join(tempfile.gettempdir(), 'nvc_templates')
            os.makedirs(cache_dir, exist_ok=True)
            
            app.jinja_env.bytecode_cache = FileSystemBytecodeCache(directory=cache_dir)
            logger.info(f"Template cache enabled at {cache_dir}")
        except (ImportError, AttributeError):
            pass
    except Exception as e:
        logger.warning(f"Error applying runtime optimizations: {str(e)}")
        
    # Print startup time
    elapsed = time.time() - start_time
    logger.info(f"Application loaded in {elapsed:.2f} seconds")
    
    # Set up optimized database indices
    try:
        with app.app_context():
            # Execute raw SQL to add missing indices
            from sqlalchemy import text
            
            # List of SQL statements to create indices
            index_statements = [
                "CREATE INDEX IF NOT EXISTS ix_bank_account_account_holder_id ON bank_account(account_holder_id)",
                "CREATE INDEX IF NOT EXISTS ix_currency_exchange_rate_from_to_currency ON currency_exchange_rate(from_currency, to_currency)",
                "CREATE INDEX IF NOT EXISTS ix_currency_exchange_rate_last_updated ON currency_exchange_rate(last_updated)",
                "CREATE INDEX IF NOT EXISTS ix_phone_number_account_holder_id ON phone_number(account_holder_id)",
                "CREATE INDEX IF NOT EXISTS ix_address_account_holder_id ON address(account_holder_id)",
                "CREATE INDEX IF NOT EXISTS ix_currency_exchange_transaction_created_at ON currency_exchange_transaction(created_at)",
                "CREATE INDEX IF NOT EXISTS ix_currency_exchange_transaction_account_holder_id ON currency_exchange_transaction(account_holder_id)"
            ]
            
            with db.engine.connect() as conn:
                for stmt in index_statements:
                    try:
                        conn.execute(text(stmt))
                        logger.info(f"Created index: {stmt}")
                    except Exception as e:
                        logger.warning(f"Error creating index: {str(e)}")
                conn.commit()
    except Exception as e:
        logger.warning(f"Error setting up database indices: {str(e)}")
    
    # Run the application with gunicorn
    if __name__ == "__main__":
        import gunicorn.app.base
        
        class StandaloneApplication(gunicorn.app.base.BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()
            
            def load_config(self):
                for key, value in self.options.items():
                    if key in self.cfg.settings and value is not None:
                        self.cfg.set(key.lower(), value)
            
            def load(self):
                return self.application
        
        options = {
            'bind': '0.0.0.0:5000',
            'workers': 4,
            'worker_class': 'sync',
            'timeout': 120,
            'reuse_port': True,
            'preload_app': True
        }
        
        StandaloneApplication(app, options).run()
    
except Exception as e:
    logger.error(f"Error starting application: {str(e)}")
    import traceback
    traceback.print_exc()