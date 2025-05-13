#!/usr/bin/env python3
"""
Blockchain Status Redirect

This script adds a direct route to the blockchain status page
to make it more accessible from any browser tab.
"""

import os
import sys
from flask import Blueprint, redirect, url_for

# Create a blueprint for the blockchain status redirect
blockchain_redirect_bp = Blueprint('blockchain_redirect', __name__)

@blockchain_redirect_bp.route('/blockchain', strict_slashes=False)
def redirect_to_blockchain():
    """Redirect to the blockchain status page"""
    return redirect(url_for('blockchain.index'))

@blockchain_redirect_bp.route('/blockchain/status', strict_slashes=False)
def redirect_to_blockchain_status():
    """Redirect to the blockchain status page"""
    return redirect(url_for('blockchain.index'))

def register_blockchain_redirect(app):
    """Register the blockchain redirect blueprint"""
    app.register_blueprint(blockchain_redirect_bp)
    print("✅ Blockchain status redirect routes registered")
    return True

if __name__ == "__main__":
    print("This script is meant to be imported, not run directly.")
    print("To install the redirect routes, add the following to main.py:")
    print("\nfrom blockchain_status_redirect import register_blockchain_redirect")
    print("register_blockchain_redirect(app)")