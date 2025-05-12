#!/usr/bin/env python3
"""
Utility script to check PayPal API credential formats without exposing values.
"""

import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_credential_format():
    """Check format of PayPal credentials"""
    client_id = os.environ.get('PAYPAL_CLIENT_ID', '')
    client_secret = os.environ.get('PAYPAL_CLIENT_SECRET', '')
    
    # Only print length and format patterns, not actual values
    logger.info(f"PAYPAL_CLIENT_ID length: {len(client_id)}")
    if client_id:
        # Check if it matches expected format (alphanumeric with some special chars)
        import re
        if re.match(r'^[A-Za-z0-9_\-]+$', client_id):
            logger.info("PAYPAL_CLIENT_ID format appears valid (alphanumeric)")
        else:
            logger.warning("PAYPAL_CLIENT_ID may contain unexpected characters")
    
    logger.info(f"PAYPAL_CLIENT_SECRET length: {len(client_secret)}")
    if client_secret:
        # Print first 2 characters to check format without exposing value
        logger.info(f"PAYPAL_CLIENT_SECRET starts with: {client_secret[:2]}")
        if client_secret.startswith("E") or client_secret.startswith("A"):
            logger.info("PAYPAL_CLIENT_SECRET prefix appears to be in expected format")
        else:
            logger.warning("PAYPAL_CLIENT_SECRET prefix doesn't match typical pattern")
    
    # Detect if there might be extra whitespace
    if client_id and (client_id[0].isspace() or client_id[-1].isspace()):
        logger.warning("PAYPAL_CLIENT_ID has leading or trailing whitespace")
    
    if client_secret and (client_secret[0].isspace() or client_secret[-1].isspace()):
        logger.warning("PAYPAL_CLIENT_SECRET has leading or trailing whitespace")

if __name__ == "__main__":
    print("-" * 50)
    print("PayPal Credential Format Check")
    print("-" * 50)
    check_credential_format()
    print("-" * 50)