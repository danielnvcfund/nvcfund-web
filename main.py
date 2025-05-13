from app import app  # noqa: F401
import logging
import threading
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register blockchain redirect routes
try:
    from blockchain_status_redirect import register_blockchain_redirect
    register_blockchain_redirect(app)
    logger.info("Blockchain status direct access routes registered successfully")
except Exception as e:
    logger.error(f"Error registering blockchain redirect routes: {str(e)}")

# Database migration for tx_hash column
def run_tx_hash_migration():
    """Run tx_hash migration in background to avoid blocking startup"""
    try:
        time.sleep(5)  # Let the app start up first
        from db_operations import add_tx_hash_column
        from app import app  # Import app for its context
        
        # Run the migration within the app context
        with app.app_context():
            result = add_tx_hash_column()
            if result:
                logger.info("Blockchain transaction schema migration completed successfully")
            else:
                logger.warning("Blockchain transaction schema migration did not complete")
    except Exception as e:
        logger.error(f"Error running blockchain transaction schema migration: {str(e)}")

# Start migration in background thread to avoid blocking app startup
migration_thread = threading.Thread(target=run_tx_hash_migration)
migration_thread.daemon = True
migration_thread.start()
from flask import send_from_directory
import os

def generate_custody_agreement():
    """Check if custody agreement exists and generate if needed"""
    from generate_custody_agreement import generate_custody_agreement as gen_agreement
    
    # Path to the static PDF file
    static_file_path = os.path.join(os.getcwd(), 'static', 'documents', 'NVC_Fund_Bank_Custody_Agreement.pdf')
    
    # If the file doesn't exist, generate it
    if not os.path.exists(static_file_path):
        static_file_path = gen_agreement()
    
    return static_file_path

@app.route('/get-custody-agreement')
def serve_agreement():
    """Serve the custody agreement PDF directly"""
    # Ensure file exists
    generate_custody_agreement()
    
    # Serve the file directly
    return send_from_directory('static/documents', 'NVC_Fund_Bank_Custody_Agreement.pdf', 
                              mimetype='application/pdf', as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)