
import os
import sys
import logging
import signal
import time

# Configure logging immediately
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("main")

# Record startup time
startup_start_time = time.time()
logger.info("NVC Banking Platform starting up (optimized version)...")

# Set performance environment variables
os.environ["NVC_DISABLE_BLOCKCHAIN"] = "1"
os.environ["NVC_MINIMAL_STARTUP"] = "1"
os.environ["NVC_OPTIMIZE_MEMORY"] = "1"

# Apply all available optimizations BEFORE importing app
try:
    # Try first optimizations script
    try:
        import optimize_app
        optimize_app.optimize_startup()
        optimize_app.reduce_debug_logging()
        logger.info("Applied startup optimizations from optimize_app")
    except ImportError:
        pass
        
    # Try original optimizations as well
    try:
        from performance_optimizations import optimize_performance
        optimize_performance()
        logger.info("Applied optimizations from performance_optimizations")
    except ImportError:
        pass
except Exception as e:
    logger.error(f"Could not apply performance optimizations: {str(e)}")

# Now import the app
from app import app

# Apply post-import optimizations
try:
    # Disable blockchain for faster startup
    try:
        import blockchain
        
        # Create a mock initialization function
        def mock_init_web3():
            blockchain.w3 = "MOCK_WEB3_CONNECTION"
            blockchain._web3_initialized = True
            blockchain._web3_last_checked = time.time()
            logger.info("Using mock blockchain connection")
            return True
        
        # Replace the real initialization function
        blockchain.init_web3 = mock_init_web3
        logger.info("Blockchain connection optimized")
    except (ImportError, AttributeError):
        pass
        
    # Apply database index optimizations
    try:
        # Disable SQLAlchemy echo
        app.config["SQLALCHEMY_ECHO"] = False
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        logger.info("SQLAlchemy optimized")
    except Exception:
        pass
        
    # Apply currency exchange optimizations
    try:
        import optimize_currency_loading
        optimize_currency_loading.optimize_currency_loading()
        logger.info("Currency exchange operations optimized")
    except (ImportError, Exception) as e:
        logger.warning(f"Could not optimize currency exchange: {str(e)}")
except Exception as e:
    logger.error(f"Error applying post-import optimizations: {str(e)}")

# Track and log startup time
startup_time = time.time() - startup_start_time
logger.info(f"Application startup completed in {startup_time:.2f} seconds")

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
