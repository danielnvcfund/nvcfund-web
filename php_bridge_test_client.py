#!/usr/bin/env python3
"""
PHP Bridge Test Client

This script simulates the PHP banking software making API calls to the NVC Global Payment Gateway
through the PHP Bridge API.

Usage:
    python php_bridge_test_client.py [operation] [params]

Operations:
    sync_accounts - Synchronize accounts from PHP to NVC
    sync_transactions - Synchronize transactions from PHP to NVC
    process_payment - Process a payment through NVC Global
    check_status [transaction_id] - Check status of a payment

Examples:
    python php_bridge_test_client.py sync_accounts
    python php_bridge_test_client.py process_payment
    python php_bridge_test_client.py check_status NVC-12345-67890
"""

import os
import sys
import json
import time
import hmac
import hashlib
import argparse
import requests
from datetime import datetime, timedelta
from urllib.parse import urljoin

# Configuration
BASE_URL = "http://localhost:5000/api/php-bridge/"
API_KEY = "php_test_api_key"  # Replace with your actual API key
SHARED_SECRET = "your_shared_secret"  # Replace with your actual shared secret

# Endpoints
ACCOUNT_SYNC_ENDPOINT = "account/sync"
TRANSACTION_SYNC_ENDPOINT = "transaction/sync"
PAYMENT_PROCESS_ENDPOINT = "payment/process"
PAYMENT_STATUS_ENDPOINT = "payment/status/"

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='PHP Bridge Test Client')
    parser.add_argument('operation', choices=['sync_accounts', 'sync_transactions', 'process_payment', 'check_status'],
                     help='Operation to perform')
    parser.add_argument('params', nargs='*', help='Optional parameters for the operation')
    parser.add_argument('--api-key', help='API Key to use (overrides default)')
    parser.add_argument('--shared-secret', help='Shared secret to use (overrides default)')
    return parser.parse_args()

def generate_signature(data):
    """Generate HMAC signature for data"""
    # Sort the data by key
    sorted_data = {k: data[k] for k in sorted(data.keys())}
    
    # Create a string from the sorted data
    data_string = '&'.join([f"{k}={v}" for k, v in sorted_data.items()])
    
    # Generate signature
    signature = hmac.new(
        SHARED_SECRET.encode(),
        data_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature

def make_request(endpoint, method="GET", data=None):
    """Make a request to the API endpoint"""
    url = urljoin(BASE_URL, endpoint)
    headers = {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    
    print(f"\n📤 Making {method} request to {url}")
    
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        print(f"📦 Request data: {json.dumps(data, indent=2)}")
        response = requests.post(url, headers=headers, json=data)
    
    print(f"📥 Response status: {response.status_code}")
    
    if response.status_code >= 200 and response.status_code < 300:
        result = response.json()
        print(f"📄 Response data: {json.dumps(result, indent=2)}")
        return result
    else:
        print(f"❌ Error: {response.text}")
        return None

def sync_accounts():
    """Synchronize accounts from PHP to NVC"""
    # Sample account data
    accounts = [
        {
            "username": "phpuser1",
            "email": "phpuser1@example.com",
            "account_number": "PHP-ACC-001",
            "customer_id": "PHP-CID-001",
            "account_type": "checking",
            "balance": 5000.00,
            "currency": "USD",
            "status": "active"
        },
        {
            "username": "phpuser2",
            "email": "phpuser2@example.com",
            "account_number": "PHP-ACC-002",
            "customer_id": "PHP-CID-002",
            "account_type": "savings",
            "balance": 12500.00,
            "currency": "EUR",
            "status": "active"
        }
    ]
    
    data = {"accounts": accounts}
    
    # Add signature
    signature = generate_signature(data)
    data["signature"] = signature
    
    # Make the request
    result = make_request(ACCOUNT_SYNC_ENDPOINT, "POST", data)
    return result

def sync_transactions():
    """Synchronize transactions from PHP to NVC"""
    # Sample transaction data
    transactions = [
        {
            "transaction_id": f"PHP-TXN-{int(time.time())}-001",
            "customer_id": "PHP-CID-001",
            "account_number": "PHP-ACC-001",
            "amount": 150.00,
            "currency": "USD",
            "description": "Monthly subscription payment",
            "status": "completed",
            "transaction_type": "payment",
            "created_at": datetime.utcnow().isoformat() + "Z"
        },
        {
            "transaction_id": f"PHP-TXN-{int(time.time())}-002",
            "customer_id": "PHP-CID-002",
            "account_number": "PHP-ACC-002",
            "amount": 75.50,
            "currency": "EUR",
            "description": "Online purchase",
            "status": "pending",
            "transaction_type": "payment",
            "created_at": (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        }
    ]
    
    data = {"transactions": transactions}
    
    # Add signature
    signature = generate_signature(data)
    data["signature"] = signature
    
    # Make the request
    result = make_request(TRANSACTION_SYNC_ENDPOINT, "POST", data)
    return result

def process_payment():
    """Process a payment through NVC Global"""
    # Sample payment data
    payment_data = {
        "customer_id": "PHP-CID-001",
        "amount": 199.99,
        "currency": "USD",
        "description": "Premium service payment",
        "recipient": "merchant@example.com",
        "callback_url": "https://phpbanking.example.com/callback",
        "metadata": {
            "invoice_id": f"INV-{int(time.time())}",
            "product_id": "PREMIUM-SERVICE",
            "customer_note": "Annual subscription"
        }
    }
    
    # Add signature
    signature = generate_signature(payment_data)
    payment_data["signature"] = signature
    
    # Make the request
    result = make_request(PAYMENT_PROCESS_ENDPOINT, "POST", payment_data)
    return result

def check_status(transaction_id):
    """Check status of a payment"""
    if not transaction_id:
        print("❌ Error: Transaction ID is required")
        return None
    
    # Make the request
    result = make_request(PAYMENT_STATUS_ENDPOINT + transaction_id)
    return result

def main():
    """Main function"""
    args = parse_args()
    
    # Override config if provided in args
    global API_KEY, SHARED_SECRET
    if args.api_key:
        API_KEY = args.api_key
    if args.shared_secret:
        SHARED_SECRET = args.shared_secret
    
    print("🌟 PHP Bridge Test Client")
    print(f"🔑 Using API Key: {API_KEY}")
    
    # Execute the requested operation
    operation = args.operation
    if operation == "sync_accounts":
        print("\n📋 Synchronizing accounts...")
        sync_accounts()
    elif operation == "sync_transactions":
        print("\n📋 Synchronizing transactions...")
        sync_transactions()
    elif operation == "process_payment":
        print("\n💰 Processing payment...")
        process_payment()
    elif operation == "check_status":
        if len(args.params) < 1:
            print("❌ Error: Transaction ID is required for check_status operation")
            sys.exit(1)
        transaction_id = args.params[0]
        print(f"\n🔍 Checking status for transaction: {transaction_id}")
        check_status(transaction_id)

if __name__ == "__main__":
    main()