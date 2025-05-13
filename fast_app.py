"""
Lightweight version of the main application with performance optimizations
This version reduces startup time and memory usage
"""

import os
import logging
from flask import Flask, render_template, redirect, url_for, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)

# Set a secret key
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_for_testing_only")

# Simplified routes
@app.route('/')
def home():
    """Simplified home route"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "NVC Banking Platform"})

@app.route('/treasury')
def treasury_redirect():
    """Redirect to treasury dashboard"""
    return redirect('/treasury/dashboard')

@app.route('/blockchain')
def blockchain_redirect():
    """Redirect to blockchain dashboard"""
    return redirect('/admin/blockchain')

# Custom error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Custom 404 error handler"""
    return render_template('error.html', 
                          error="The requested page could not be found.", 
                          code=404, 
                          title="Page Not Found"), 404

@app.errorhandler(500)
def server_error(e):
    """Custom 500 error handler"""
    return render_template('error.html',
                          error="An internal server error occurred.", 
                          code=500,
                          title="Server Error"), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)