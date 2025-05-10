"""
Static Routes Module
This module handles static file routes that need special handling.
"""
import os
import logging
from flask import Blueprint, send_from_directory, current_app, redirect, url_for

# Configure logger
logger = logging.getLogger(__name__)

# Create Blueprint
static_bp = Blueprint('static_routes', __name__)

@static_bp.route('/favicon.ico')
def favicon():
    """
    Route to serve favicon.ico from the correct location
    This prevents 404 errors when browsers look for /favicon.ico
    """
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'images'),
        'nvc_logo_white.png',
        mimetype='image/png'
    )

@static_bp.route('/robots.txt')
def robots():
    """Serve robots.txt file"""
    return send_from_directory(
        os.path.join(current_app.root_path, 'static'),
        'robots.txt',
        mimetype='text/plain'
    )

def register_static_routes(app):
    """Register static routes with the Flask app"""
    app.register_blueprint(static_bp)
    logger.info("Static routes registered successfully")