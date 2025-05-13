"""
Fast-loading application module for NVC Banking Platform
This module provides a lightweight Flask application with optimized performance
for the most frequently accessed routes
"""

import os
import sys
import logging
import importlib
from datetime import datetime, timedelta
from flask import Flask, request, redirect, url_for, send_from_directory, jsonify

# Configure minimal logging for production
logging.basicConfig(level=logging.WARNING,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FastApp")

# Create minimal Flask app
fast_app = Flask(__name__)
fast_app.config['ENV'] = 'production'
fast_app.config['DEBUG'] = False
fast_app.secret_key = os.environ.get("SESSION_SECRET", os.urandom(24))

# ==========================================
# Minimal database setup - only if required
# ==========================================

def initialize_minimal_db():
    """Set up minimal database connection only if needed"""
    # Only import SQLAlchemy if a database route is accessed
    db = None
    try:
        from flask_sqlalchemy import SQLAlchemy
        
        # Configure database
        fast_app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
        fast_app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'pool_size': 10,
            'max_overflow': 20,
        }
        
        # Initialize db
        db = SQLAlchemy(fast_app)
        logger.info("Minimal database initialized")
        return db
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return None

# ==========================================
# Static file serving with optimized caching
# ==========================================

@fast_app.route('/static/<path:filename>')
def optimized_static(filename):
    """Serve static files with aggressive caching"""
    cache_timeout = 3600  # 1 hour 
    return send_from_directory('static', filename, cache_timeout=cache_timeout)

@fast_app.route('/assets/<path:filename>')
def optimized_assets(filename):
    """Serve asset files with aggressive caching"""
    cache_timeout = 3600  # 1 hour
    return send_from_directory('assets', filename, cache_timeout=cache_timeout)

@fast_app.route('/favicon.ico')
def favicon():
    """Serve favicon with long cache time"""
    return send_from_directory('static', 'favicon.ico', cache_timeout=86400)  # 1 day

# ==========================================
# Fast health checks and status endpoints
# ==========================================

@fast_app.route('/healthcheck')
def fast_healthcheck():
    """Quick healthcheck endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'NVC Banking Platform'
    })

@fast_app.route('/api/status')
def api_status():
    """Quick API status check"""
    return jsonify({
        'status': 'available',
        'timestamp': datetime.utcnow().isoformat(),
        'api_version': '1.0'
    })

# ==========================================
# Redirect to main application for other routes
# ==========================================

@fast_app.route('/', defaults={'path': ''})
@fast_app.route('/<path:path>')
def catch_all(path):
    """Redirect non-optimized routes to main application"""
    # Specific fast routes could be added here
    
    # Default: redirect to main app
    return redirect(request.url)

# ==========================================
# Application performance optimization
# ==========================================

def optimize_fast_app():
    """Apply performance optimizations"""
    try:
        # Import and apply optimizations
        from optimize_performance import optimize_app_settings
        optimize_app_settings(fast_app)
        logger.info("Performance optimizations applied")
    except Exception as e:
        logger.error(f"Error applying optimizations: {str(e)}")

# Apply optimizations when imported
optimize_fast_app()

# Main entry point when run directly
if __name__ == "__main__":
    # Start optimized server
    fast_app.run(host='0.0.0.0', port=5001, threaded=True)