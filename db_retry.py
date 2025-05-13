"""
Database connection retry mechanism for increased resilience
"""
import time
import logging
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from flask import g

logger = logging.getLogger(__name__)

def setup_db_retry_handlers(app, db):
    """Setup database retry handlers for the Flask app"""
    
    @app.before_request
    def ensure_db_connection():
        """Ensure database connection is alive before processing requests"""
        # Skip for static files
        if '/static/' in request.path:
            return
            
        max_retries = 3
        retry_count = 0
        retry_delay = 1  # seconds
        
        while retry_count < max_retries:
            try:
                # Test connection with a simple query
                db.session.execute("SELECT 1")
                # Connection is good, return None to continue request processing
                return None
            except (OperationalError, SQLAlchemyError) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    app.logger.error(f"Database connection failed after {max_retries} attempts: {str(e)}")
                    # We're out of retries, show error page
                    return render_template('error.html', 
                        error="Database connection error. Please try again later.",
                        title="Database Error"), 500
                
                app.logger.warning(f"Database connection error (attempt {retry_count}): {str(e)}")
                # Wait before retry with exponential backoff
                time.sleep(retry_delay)
                retry_delay *= 2
                
                # Make sure we have a fresh session
                db.session.rollback()
                db.session.remove()
                
    @app.teardown_request
    def close_db_session(exception=None):
        """Close database session after each request"""
        if exception:
            db.session.rollback()
        db.session.remove()

def initialize_database_with_retry(app, db):
    """Initialize database with retry mechanism"""
    max_retries = 5
    retry_count = 0
    retry_delay = 2  # seconds
    
    while retry_count < max_retries:
        try:
            with app.app_context():
                # Test database connection before initializing
                db.engine.connect().close()
                logger.info("Database connection established")
                
                # Import models to ensure they're registered
                import models  # noqa: F401
                import account_holder_models  # noqa: F401
                
                # Create any missing tables
                db.create_all()
                logger.info("Database tables initialized successfully")
                
                return True
        except (OperationalError, SQLAlchemyError) as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"Failed to initialize database after {max_retries} attempts: {str(e)}")
                return False
                
            logger.warning(f"Database initialization error (attempt {retry_count}): {str(e)}")
            time.sleep(retry_delay)
            retry_delay *= 2
            
    return False