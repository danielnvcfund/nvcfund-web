import os
import logging

from flask import Flask, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_jwt_extended import JWTManager
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass


# Create extension instances
db = SQLAlchemy(model_class=Base)
csrf = CSRFProtect()
jwt = JWTManager()
login_manager = LoginManager()
login_manager.login_view = 'web.main.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))


# The global Flask app instance
app = None

def create_app():
    global app
    # Create the app
    app = Flask(__name__)
    # Set a default secret key if SESSION_SECRET environment variable isn't available
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_for_testing_only")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

    # Configure the database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Configure session 
    app.config["SESSION_COOKIE_SECURE"] = False  # Allow non-HTTPS for development
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = 2592000  # 30 days
    app.config["SESSION_TYPE"] = "filesystem"
    # Make sessions permanent by default
    app.config["SESSION_PERMANENT"] = True
    
    # Configure Flask-Login
    app.config["REMEMBER_COOKIE_DURATION"] = 86400  # 24 hours
    app.config["REMEMBER_COOKIE_SECURE"] = False  # Allow non-HTTPS for development
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"
    app.config["LOGIN_DISABLED"] = False
    app.config["SESSION_PROTECTION"] = "strong"

    # Configure JWT
    app.config["JWT_SECRET_KEY"] = os.environ.get("SESSION_SECRET", "dev_secret_key_for_testing_only")  # Using same secret for simplicity
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600  # 1 hour

    # Initialize extensions with app
    db.init_app(app)
    
    # Disable CSRF protection completely for API testing
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Initialize extensions
    csrf.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    # login_view is already set in the global login_manager configuration
    
    # Add custom filters
    from utils import format_currency, format_transaction_type
    app.jinja_env.filters['format_currency'] = lambda amount, currency='USD': format_currency(amount, currency)
    app.jinja_env.filters['format_transaction_type'] = format_transaction_type

    # Set debug mode to True
    app.config['DEBUG'] = True
    
    # Global error handlers
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Global exception handler to log errors"""
        app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return render_template('error.html', error=str(e)), 500
        
    @app.errorhandler(404)
    def page_not_found(e):
        """Custom 404 error handler"""
        app.logger.error(f"404 error: {str(e)}")
        return render_template(
            'error.html', 
            error="The requested page could not be found.", 
            code=404, 
            title="Page Not Found"
        ), 404
    
    # Add direct routes to handle common paths
    @app.route('/')
    def root():
        """Root route - redirects to the index"""
        try:
            # Use the real index template
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering index: {str(e)}")
            return f"Error: {str(e)}", 500
    
    # Add direct access to funds transfer guide
    @app.route('/funds-transfer-guide')
    def funds_transfer_guide_direct():
        """Direct access to funds transfer guide"""
        try:
            # Use redirect from the imported Flask functions
            return redirect('/documents/nvc_funds_transfer_guide')
        except Exception as e:
            logger.error(f"Error redirecting to funds transfer guide: {str(e)}")
            return f"Error: {str(e)}", 500
    
    @app.route('/main')
    def main_index():
        """Main index route"""
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering main index: {str(e)}")
            return f"Error: {str(e)}", 500
            
    @app.route('/main/index')
    def main_explicit_index():
        """Explicit main index route"""
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering explicit main index: {str(e)}")
            return f"Error: {str(e)}", 500

    @app.route('/routes')
    def list_routes():
        """List all registered routes for debugging"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': ','.join([method for method in rule.methods if method not in ('HEAD', 'OPTIONS')]),
                'url': str(rule)
            })
        return {'routes': routes}

    with app.app_context():
        # Import models to ensure tables are created
        import models  # noqa: F401
        
        # Create database tables
        db.create_all()
        
        # Initialize blockchain connection (make it optional to allow app to start without blockchain)
        try:
            from blockchain import init_web3
            init_web3()
            logger.info("Blockchain initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing blockchain: {str(e)}")
            logger.warning("Application will run without blockchain functionality")
        
        # High-availability infrastructure has been removed as requested
        logger.info("High-availability infrastructure is disabled")
        
        # Initialize payment gateways
        try:
            from payment_gateways import init_payment_gateways
            if init_payment_gateways():
                logger.info("Payment gateways initialized successfully")
            else:
                logger.warning("Failed to initialize payment gateways")
        except Exception as e:
            logger.error(f"Error initializing payment gateways: {str(e)}")
            logger.warning("Application will run without payment gateway functionality")
        
        # Import routes module to register Flask route decorators
        import routes
        
        # Import and register blueprints
        from routes import api_blueprint, web_blueprint, api_access_bp
        app.register_blueprint(api_blueprint)
        app.register_blueprint(web_blueprint)
        app.register_blueprint(api_access_bp)
        
        # Register Documentation routes
        from routes.documentation_routes import documentation_bp
        app.register_blueprint(documentation_bp, url_prefix='/documentation')
        
        # Register Admin routes
        from routes.admin import admin
        app.register_blueprint(admin)
        
        # Register EDI Integration routes
        from routes.edi_routes import edi
        app.register_blueprint(edi)
        
        # Register Treasury Management System routes
        from routes.treasury_routes import treasury_bp
        app.register_blueprint(treasury_bp)
        
        # Register Document routes
        from routes.document_routes import document_routes
        app.register_blueprint(document_routes, url_prefix='/documents')
        
        # Register SWIFT GPI routes
        try:
            from routes.swift_gpi_routes import swift_gpi_routes
            app.register_blueprint(swift_gpi_routes)
            logger.info("SWIFT GPI routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering SWIFT GPI routes: {str(e)}")
            logger.warning("Application will run without SWIFT GPI functionality")
        
        # Register Server-to-Server routes
        try:
            from routes.server_to_server_routes import server_to_server_routes
            app.register_blueprint(server_to_server_routes)
            logger.info("Server-to-Server routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Server-to-Server routes: {str(e)}")
            logger.warning("Application will run without Server-to-Server functionality")
        
        # Register RTGS routes
        try:
            from routes.rtgs_routes import rtgs_routes
            app.register_blueprint(rtgs_routes)
            logger.info("RTGS routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering RTGS routes: {str(e)}")
            logger.warning("Application will run without RTGS functionality")
        
        # Register API routes
        from routes.api import api_bp as main_api_bp
        app.register_blueprint(main_api_bp)
        
        # Initialize EDI Service
        try:
            from edi_integration import init_app as init_edi
            init_edi(app)
            logger.info("EDI Integration module initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing EDI Integration: {str(e)}")
            logger.warning("Application will run without EDI functionality")
        
        # Admin API Keys routes are registered through the admin blueprint
        # No need to register them separately
        
        # Register Customer Support routes
        try:
            from routes.customer_support_routes import customer_support_bp
            app.register_blueprint(customer_support_bp)
            logger.info("Customer Support routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Customer Support routes: {str(e)}")
            logger.warning("Application will run without AI Customer Support functionality")
            
        # Register Admin Tools routes
        try:
            from routes.admin_tools_routes import admin_tools_bp
            app.register_blueprint(admin_tools_bp)
            logger.info("Admin Tools routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Admin Tools routes: {str(e)}")
            logger.warning("Application will run without Admin Tools functionality")
            
        # Register Payment Processor routes
        try:
            from routes.payment_processor_routes import register_payment_processor_routes
            register_payment_processor_routes(app)
            logger.info("Payment Processor routes registered successfully")
        except Exception as e:
            logger.error(f"Error registering Payment Processor routes: {str(e)}")
            logger.warning("Application will run without Payment Processor functionality")

        # Create PHP test integration user
        try:
            from auth import create_php_test_user
            php_test_user = create_php_test_user()
            if php_test_user:
                logger.info(f"PHP test integration user ready with API key: php_test_api_key")
            else:
                logger.warning("Failed to create PHP test integration user")
        except Exception as e:
            logger.error(f"Error creating PHP test user: {str(e)}")
        
        logger.info("Application initialized successfully")

    return app

# Initialize the app instance
app = create_app()
