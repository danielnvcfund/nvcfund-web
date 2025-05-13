"""
Performance optimization script for NVC Banking Platform

This script analyzes the application for performance bottlenecks and
applies optimizations to improve:
1. Database connection pooling
2. Cache settings
3. Template rendering speed
4. Static file handling
"""

import os
import logging
import importlib
from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def optimize_app_settings(app):
    """Apply performance optimizations to Flask app"""
    # Disable debug mode in production
    app.config['DEBUG'] = False
    
    # Optimize SQLAlchemy settings
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 15,
        "pool_timeout": 60,
    }

    # Disable SQLAlchemy modification tracking
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Set optimal template caching
    app.config['EXPLAIN_TEMPLATE_LOADING'] = False
    app.jinja_env.cache = {}
    
    # Set static file caching
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400  # 1 day in seconds
    
    logger.info("Applied Flask application performance optimizations")
    return app

def optimize_database(db_instance):
    """Optimize database connections and queries"""
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    
    # Enable connection pooling events
    @event.listens_for(Engine, "connect")
    def optimize_sqlite_connection(dbapi_connection, connection_record):
        # Enable WAL mode for SQLite if used
        if hasattr(dbapi_connection, 'execute'):
            try:
                dbapi_connection.execute('PRAGMA journal_mode=WAL')
                dbapi_connection.execute('PRAGMA synchronous=NORMAL')
                dbapi_connection.execute('PRAGMA cache_size=10000')
                dbapi_connection.execute('PRAGMA temp_store=MEMORY')
                logger.info("Applied SQLite optimizations")
            except:
                # Not a SQLite connection
                pass
    
    logger.info("Applied database performance optimizations")
    return db_instance

def disable_excessive_logging():
    """Reduce logging overhead in production"""
    for logger_name in ['sqlalchemy.engine', 'werkzeug', 'urllib3']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    logger.info("Disabled excessive logging")

def optimize_all():
    """Apply all performance optimizations"""
    # Disable excessive logging
    disable_excessive_logging()
    
    # Import app and modules only if present
    try:
        from app import app, db
        app = optimize_app_settings(app)
        db = optimize_database(db)
        logger.info("Successfully applied all performance optimizations")
        return True
    except ImportError:
        logger.warning("Could not import app or db. Skipping optimizations.")
        return False

if __name__ == "__main__":
    success = optimize_all()
    if success:
        print("Performance optimizations applied successfully!")
    else:
        print("Failed to apply some performance optimizations. Check logs for details.")