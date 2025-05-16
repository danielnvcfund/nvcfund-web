"""
Documentation Routes
"""
import os
from flask import Blueprint, send_from_directory, current_app, render_template

docs_routes = Blueprint('docs', __name__, url_prefix='/docs')

@docs_routes.route('/')
def index():
    """Serve documentation index page"""
    return send_from_directory('docs', 'index.html')

@docs_routes.route('/<path:filename>')
def documentation_file(filename):
    """Serve documentation files"""
    return send_from_directory('docs', filename)

@docs_routes.route('/download')
def download_documentation():
    """Provide download link for documentation package"""
    return render_template('documentation_download.html')

def register_routes(app):
    """Register the documentation routes with the app"""
    app.register_blueprint(docs_routes)
    current_app.logger.info("Documentation routes registered successfully")