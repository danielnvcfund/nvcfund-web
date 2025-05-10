
import os
import sys
import logging
import signal
from app import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("main")

# Ensure this file properly sets up the Flask application for gunicorn
app = app

# Set up signal handlers for graceful shutdown
def handle_sigterm(signum, frame):
    """Handle SIGTERM signal - log and exit gracefully"""
    logger.info("Received SIGTERM. Shutting down gracefully...")
    sys.exit(0)

def handle_sigint(signum, frame):
    """Handle SIGINT signal - log and exit gracefully"""
    logger.info("Received SIGINT. Shutting down gracefully...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigint)

if __name__ == "__main__":
    try:
        # Log startup information
        logger.info("NVC Banking Platform starting up...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Running in directory: {os.getcwd()}")
        
        # Check if database URL is set
        if not os.environ.get("DATABASE_URL"):
            logger.warning("DATABASE_URL environment variable not set!")
        
        # Use the PORT environment variable provided by Replit if available, default to 5000
        port = int(os.environ.get("PORT", 5000))
        logger.info(f"Starting Flask server on port {port}")
        
        # Start the application
        app.run(host="0.0.0.0", port=port, debug=True)
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}", exc_info=True)
        sys.exit(1)
