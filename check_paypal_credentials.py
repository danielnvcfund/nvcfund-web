#!/usr/bin/env python3
"""
Utility script to check if PayPal credentials are properly configured.
This script does not print the actual credentials but validates their existence
and tries to authenticate with PayPal API.
"""

import os
import logging
import paypalrestsdk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_paypal_credentials():
    """Check if PayPal API credentials are correctly configured"""
    # Check environment variables
    client_id = os.environ.get('PAYPAL_CLIENT_ID')
    client_secret = os.environ.get('PAYPAL_CLIENT_SECRET')
    legacy_secret = os.environ.get('PAYPAL_SECRET')
    paypal_mode = os.environ.get('PAYPAL_MODE', 'live')
    
    logger.info(f"PayPal Mode: {paypal_mode}")
    logger.info(f"PAYPAL_CLIENT_ID exists: {bool(client_id)}")
    logger.info(f"PAYPAL_CLIENT_SECRET exists: {bool(client_secret)}")
    logger.info(f"PAYPAL_SECRET exists: {bool(legacy_secret)}")
    
    if not client_id or not client_secret:
        logger.error("Missing PayPal credentials in environment variables")
        return False
    
    # Configure PayPal SDK with the environment variables
    paypalrestsdk.configure({
        "mode": paypal_mode,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    
    # Test authentication by trying to list payment resources
    try:
        logger.info("Testing PayPal API authentication...")
        # Try to access the API - this will fail if credentials are incorrect
        payment_history = paypalrestsdk.Payment.all({"count": 1})
        logger.info("PayPal authentication successful!")
        return True
    except Exception as e:
        logger.error(f"PayPal authentication failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("-" * 50)
    print("PayPal Credentials Check")
    print("-" * 50)
    success = check_paypal_credentials()
    print("-" * 50)
    if success:
        print("✅ PayPal credentials validation PASSED")
    else:
        print("❌ PayPal credentials validation FAILED")
    print("-" * 50)