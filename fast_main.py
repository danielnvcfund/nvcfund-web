"""
Lightweight version of main.py for faster startup and better performance

This version:
1. Loads only essential components
2. Initializes the database connections more efficiently
3. Defers loading of non-critical modules until needed
4. Implements better caching for templates and static files
"""

import os
import logging
import time
from flask import Flask, send_from_directory

# Configure minimal logging
logging.basicConfig(level=logging.WARNING, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Only show important logs
for module in ['werkzeug', 'sqlalchemy', 'urllib3', 'PIL']:
    logging.getLogger(module).setLevel(logging.WARNING)

# Import the optimized app
try:
    from app import app
    # Apply optimizations from the separate module
    from optimize_performance import optimize_app_settings
    app = optimize_app_settings(app)
    logger.info("Loaded optimized app successfully")
except ImportError:
    # Fallback to creating a minimal app
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_for_testing_only")
    logger.warning("Could not load main app, using minimal app instead")

# Register minimal routes
@app.route('/get-custody-agreement')
def serve_agreement():
    """Serve the custody agreement PDF directly"""
    static_file_path = os.path.join(os.getcwd(), 'static', 'documents', 'NVC_Fund_Bank_Custody_Agreement.pdf')
    return send_from_directory('static/documents', 'NVC_Fund_Bank_Custody_Agreement.pdf', 
                              mimetype='application/pdf', as_attachment=True)

# Register blockchain redirect routes only if needed
try:
    from blockchain_status_redirect import register_blockchain_redirect
    register_blockchain_redirect(app)
    logger.info("Blockchain status direct access routes registered successfully")
except Exception as e:
    logger.warning(f"Error registering blockchain redirect routes: {str(e)}")

# Main entry point with performance optimizations
if __name__ == "__main__":
    # Set Flask to production mode
    os.environ['FLASK_ENV'] = 'production'
    # Run with optimized settings
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)