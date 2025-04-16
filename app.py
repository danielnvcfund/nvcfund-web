import os
import logging

from flask import Flask, render_template
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
login_manager.login_view = 'login'
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

    # Configure JWT
    app.config["JWT_SECRET_KEY"] = os.environ.get("SESSION_SECRET", "dev_secret_key_for_testing_only")  # Using same secret for simplicity
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600  # 1 hour

    # Initialize extensions with app
    db.init_app(app)
    csrf.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)

    # Add a direct route to index for testing
    @app.route('/')
    def index():
        """Homepage route"""
        return render_template('index.html')

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
        
        # Initialize high-availability infrastructure (make it optional to allow app to start without HA)
        try:
            from high_availability import init_high_availability
            if os.environ.get('HA_ENABLED', 'false').lower() == 'true':
                init_high_availability()
                logger.info("High-availability infrastructure initialized successfully")
            else:
                logger.info("High-availability infrastructure is disabled")
        except Exception as e:
            logger.error(f"Error initializing high-availability infrastructure: {str(e)}")
            logger.warning("Application will run without high-availability functionality")
        
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
        from routes import api_blueprint, web_blueprint
        app.register_blueprint(api_blueprint)
        app.register_blueprint(web_blueprint)
        
        logger.info("Application initialized successfully")

    return app

# Initialize the app instance
app = create_app()
