"""
Routes package for NVC Banking Platform
"""

from flask import Blueprint

# Import API routes
from routes.api.blockchain_routes import blockchain_api
from routes.api.xrp_routes import xrp_api
from routes.api.ha_routes import ha_api

# Create API blueprint
api_blueprint = Blueprint('api', __name__, url_prefix='/api')

# Register API route blueprints
api_blueprint.register_blueprint(blockchain_api, url_prefix='/blockchain')
api_blueprint.register_blueprint(xrp_api, url_prefix='/xrp')
api_blueprint.register_blueprint(ha_api)

# The main routes are imported directly in app.py