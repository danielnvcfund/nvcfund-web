import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_jwt_extended import JWTManager
from flask_wtf.csrf import CSRFProtect


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
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

# Enable CSRF protection
csrf = CSRFProtect(app)

# Initialize extensions
jwt = JWTManager(app)
db.init_app(app)

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
    
    logger.info("Application initialized successfully")
