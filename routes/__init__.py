"""
Routes package for NVC Banking Platform
"""

from flask import Blueprint

# Import API routes
from routes.api.blockchain_routes import blockchain_api
from routes.api.xrp_routes import xrp_api
from routes.api.ha_routes import ha_api
from routes.api.status_routes import status_bp
from routes.api.form_data_routes import form_data
from routes.api.form_save_routes import form_save
from routes.api.token_exchange_routes import token_exchange_api
from routes.api.treasury_api import treasury_api_bp
from routes.high_availability_routes import ha_web
from routes.main_routes import main
from routes.swift_routes import swift
from routes.api_access_routes import api_access_bp

# Import PHP Bridge routes
from api_bridge import php_bridge

# Create API blueprint
api_blueprint = Blueprint('api', __name__, url_prefix='/api')

# Create Web blueprint (for pages that should be under a prefix)
web_blueprint = Blueprint('web', __name__)

# Register API route blueprints
api_blueprint.register_blueprint(blockchain_api, url_prefix='/blockchain')
api_blueprint.register_blueprint(xrp_api, url_prefix='/v1/xrp')
api_blueprint.register_blueprint(ha_api, url_prefix='/v1/ha')
api_blueprint.register_blueprint(status_bp)
api_blueprint.register_blueprint(php_bridge, url_prefix='/php-bridge')
api_blueprint.register_blueprint(form_data)
api_blueprint.register_blueprint(form_save)
api_blueprint.register_blueprint(token_exchange_api, url_prefix='/v1/token-exchange')
api_blueprint.register_blueprint(treasury_api_bp, url_prefix='/treasury')

# Register Web route blueprints
web_blueprint.register_blueprint(ha_web, url_prefix='/ha')
web_blueprint.register_blueprint(main, url_prefix='/main')
web_blueprint.register_blueprint(swift, url_prefix='/swift')