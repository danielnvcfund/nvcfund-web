"""
Healthcheck Routes
This module provides routes for application health monitoring and system status.
"""
import time
import datetime
import logging
import os
import gc
from flask import Blueprint, jsonify, current_app

# Configure logger
logger = logging.getLogger(__name__)

# Create Blueprint
healthcheck_bp = Blueprint('healthcheck', __name__, url_prefix='/health')

# Global variable to track application start time
START_TIME = time.time()

@healthcheck_bp.route('/', methods=['GET'])
def healthcheck():
    """Basic healthcheck endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'uptime_seconds': int(time.time() - START_TIME)
    }), 200

@healthcheck_bp.route('/ready', methods=['GET'])
def readiness():
    """Readiness probe that checks if the application is ready to serve requests"""
    # Check database connection
    try:
        # Import here to avoid circular imports
        from app import db
        from sqlalchemy import text
        # Try a simple database query
        db.session.execute(text("SELECT 1")).scalar()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = f"error: {str(e)}"
        return jsonify({
            'status': 'error',
            'database': db_status,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }), 503

    return jsonify({
        'status': 'ready',
        'database': db_status,
        'timestamp': datetime.datetime.utcnow().isoformat()
    }), 200

@healthcheck_bp.route('/system', methods=['GET'])
def system_status():
    """System status endpoint for resource monitoring"""
    # Get garbage collection stats
    gc_counts = gc.get_count()
    
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'uptime_seconds': int(time.time() - START_TIME),
        'process': {
            'pid': os.getpid(),
            'python_version': os.environ.get('PYTHON_VERSION', 'Unknown'),
            'env': current_app.config.get('ENV', 'production'),
            'debug': current_app.debug
        },
        'memory': {
            'gc_counts': gc_counts,
            'gc_objects': len(gc.get_objects()),
        },
        'database': {
            'status': 'connected' if current_app.extensions.get('sqlalchemy') else 'unknown',
            'pooling': bool(current_app.config.get('SQLALCHEMY_ENGINE_OPTIONS'))
        }
    }), 200

def register_healthcheck_routes(app):
    """Register healthcheck routes with the Flask app"""
    app.register_blueprint(healthcheck_bp)
    logger.info("Healthcheck routes registered successfully")