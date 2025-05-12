#!/usr/bin/env python3
"""
Alternative PayPal credential test using the requests library directly
rather than the paypalrestsdk.
"""

import os
import base64
import logging
import requests
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_paypal_auth():
    """Test PayPal authentication using direct API requests"""
    
    # Get credentials from environment variables
    client_id = os.environ.get('PAYPAL_CLIENT_ID')
    client_secret = os.environ.get('PAYPAL_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        logger.error("Missing PayPal credentials in environment variables")
        return False
    
    # Endpoint for OAuth token (same for sandbox and live)
    url = 'https://api.paypal.com/v1/oauth2/token'
    
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
    
    logger.info("Making direct OAuth token request to PayPal API...")
    
    try:
        # Make the request
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            logger.info("Authentication successful! Received OAuth token.")
            token_info = response.json()
            logger.info(f"Token expires in {token_info.get('expires_in')} seconds")
            logger.info(f"Token scope: {token_info.get('scope')}")
            return True
        else:
            logger.error(f"Authentication failed. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            
            # Check for common errors
            if response.status_code == 401:
                logger.error("ERROR 401: Unauthorized - Invalid client credentials")
                # Parse the response for more details
                try:
                    error_data = response.json()
                    error = error_data.get('error', '')
                    desc = error_data.get('error_description', '')
                    logger.error(f"Error type: {error}")
                    logger.error(f"Error description: {desc}")
                    
                    if error == 'invalid_client':
                        logger.error("DIAGNOSIS: Client ID and/or Client Secret are incorrect")
                        # Print first few chars of credentials to help debug
                        if client_id:
                            logger.info(f"Client ID starts with: {client_id[:4]}...")
                        if client_secret:
                            logger.info(f"Client Secret starts with: {client_secret[:4]}...")
                except:
                    logger.error("Could not parse error response")
            
            return False
    except Exception as e:
        logger.error(f"Error making request: {str(e)}")
        return False

if __name__ == "__main__":
    print("-" * 50)
    print("PayPal Authentication Test (Direct API)")
    print("-" * 50)
    
    # Check if credentials exist
    client_id = os.environ.get('PAYPAL_CLIENT_ID')
    client_secret = os.environ.get('PAYPAL_CLIENT_SECRET')
    
    logger.info(f"PAYPAL_CLIENT_ID exists: {bool(client_id)}")
    logger.info(f"PAYPAL_CLIENT_SECRET exists: {bool(client_secret)}")
    
    # Run the test
    success = test_paypal_auth()
    
    print("-" * 50)
    if success:
        print("✅ PayPal authentication test PASSED")
    else:
        print("❌ PayPal authentication test FAILED")
    print("-" * 50)