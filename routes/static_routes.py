"""
Static file routes for serving documentation and other static content
"""
import os
from flask import Blueprint, send_from_directory, current_app

static_routes = Blueprint('static_routes', __name__)

@static_routes.route('/documentation')
def documentation_index():
    """Serve the documentation index page"""
    return send_from_directory('docs', 'index.html')

@static_routes.route('/documentation/<path:filename>')
def documentation_file(filename):
    """Serve documentation files"""
    return send_from_directory('docs', filename)

def register_routes(app):
    """Register the static routes with the app"""
    app.register_blueprint(static_routes)
    current_app.logger.info("Static routes registered successfully")