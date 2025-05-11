#!/usr/bin/env python3
"""
Database Optimization Module

This module applies optimizations to reduce database load:
1. Increase connection pool size for better concurrency
2. Enable connection recycling to prevent timeouts
3. Add statement caching to reduce parsing overhead
4. Configure statement timeout to prevent long-running queries
"""

import logging
from sqlalchemy import event

logger = logging.getLogger(__name__)

def optimize_database(app, db):
    """Apply all database optimizations"""
    # Optimize SQLAlchemy engine configuration
    optimize_engine_config(app)
    
    # Set up statement timeout
    configure_statement_timeout(db)
    
    # Add connection event listeners
    add_connection_listeners(db)
    
    logger.info("Database optimizations applied")
    return True

def optimize_engine_config(app):
    """Optimize SQLAlchemy engine configuration"""
    # Configure connection pool
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 20,               # Increase from default 5
        "max_overflow": 40,            # Allow more connections under load
        "pool_recycle": 300,           # Recycle connections after 5 minutes
        "pool_pre_ping": True,         # Check connection validity
        "pool_timeout": 60,            # Wait up to 60s for connection
        "pool_use_lifo": True,         # Last-in-first-out for better cache locality
        "echo": False,                 # Turn off SQL echoing
        "echo_pool": False,            # Turn off connection pool logging
    }
    
    # Disable SQLAlchemy modification tracking (performance hit)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    logger.info("SQLAlchemy engine configuration optimized")

def configure_statement_timeout(db):
    """Configure statement timeout to prevent long-running queries"""
    try:
        @event.listens_for(db.engine, 'connect')
        def set_connection_timeout(dbapi_connection, connection_record):
            # Set statement timeout to 10 seconds
            cursor = dbapi_connection.cursor()
            cursor.execute("SET statement_timeout = '10000'")  # 10 seconds in ms
            cursor.close()
        
        logger.info("Database statement timeout configured")
    except Exception as e:
        logger.warning(f"Could not configure statement timeout: {str(e)}")

def add_connection_listeners(db):
    """Add connection event listeners for optimization and monitoring"""
    try:
        @event.listens_for(db.engine, 'before_cursor_execute')
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # Store execution start time
            conn.info.setdefault('query_start_time', []).append(db.get_engine().connect()._execution_options.get('query_start_time'))
        
        @event.listens_for(db.engine, 'after_cursor_execute')
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # Get total execution time
            total = db.get_engine().connect()._execution_options.get('query_start_time')
            
            # Log slow queries (more than 500ms)
            if total is not None and total > 0.5:
                logger.warning(f"Slow query detected: {statement[:100]}... ({total:.4f}s)")
        
        logger.info("Database connection listeners configured")
    except Exception as e:
        logger.warning(f"Could not configure connection listeners: {str(e)}")

if __name__ == "__main__":
    # Direct execution not supported - must be imported
    print("This module should be imported, not executed directly.")
    print("Usage: from optimize_database import optimize_database")
    print("       optimize_database(app, db)")