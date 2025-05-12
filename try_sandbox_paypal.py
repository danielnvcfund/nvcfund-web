#!/usr/bin/env python3
"""
Test script to try PayPal sandbox authentication
"""

import os
import base64
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_paypal_auth(mode="live"):
    """Test PayPal authentication in either live or sandbox mode"""
    
    # Get credentials from environment variables
    client_id = os.environ.get('PAYPAL_CLIENT_ID')
    client_secret = os.environ.get('PAYPAL_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        logger.error("Missing PayPal credentials in environment variables")
        return False
    
    # Set the API endpoint based on mode
    if mode == "sandbox":
        url = 'https://api.sandbox.paypal.com/v1/oauth2/token'
        logger.info("Testing with SANDBOX endpoint")
    else:
        url = 'https://api.paypal.com/v1/oauth2/token'
        logger.info("Testing with LIVE endpoint")
    
    # Create the Basic Auth string
    auth_string = f"{client_id}:{client_secret}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    
    # Set up headers
    headers = {
        'Accept': 'application/json',
        'Accept-Language': 'en_US',
        'Authorization': f'Basic {encoded_auth}'
    }
    
    # Set up data
    data = {
        'grant_type': 'client_credentials'
    }
    
    logger.info(f"Making OAuth token request to PayPal API ({mode} mode)...")
    
    try:
        # Make the request
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            logger.info(f"Authentication successful in {mode.upper()} mode!")
            return True
        else:
            logger.error(f"Authentication failed in {mode.upper()} mode. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error making request: {str(e)}")
        return False

if __name__ == "__main__":
    print("-" * 50)
    print("PayPal Authentication Test (Live vs Sandbox)")
    print("-" * 50)
    
    # Try live mode first
    print("\nTrying LIVE mode:")
    live_success = test_paypal_auth(mode="live")
    
    # If live failed, try sandbox
    print("\nTrying SANDBOX mode:")
    sandbox_success = test_paypal_auth(mode="sandbox")
    
    print("-" * 50)
    if live_success:
        print("✅ PayPal LIVE mode authentication PASSED")
    else:
        print("❌ PayPal LIVE mode authentication FAILED")
        
    if sandbox_success:
        print("✅ PayPal SANDBOX mode authentication PASSED")
    else:
        print("❌ PayPal SANDBOX mode authentication FAILED")
    
    if sandbox_success and not live_success:
        print("\n‼️ IMPORTANT: Your credentials are for SANDBOX mode only!")
        print("   You need to get LIVE mode credentials for production use.")
    
    print("-" * 50)