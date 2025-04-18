#!/usr/bin/env python3
"""
API Testing Script for Smart Contract Deployment API
This script demonstrates the usage of the blockchain API endpoints
for deploying and monitoring smart contracts.
"""

import sys
import time
import json
import logging
import argparse
import requests
from requests.auth import HTTPBasicAuth

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('api_test')

# API configuration
API_HOST = "http://localhost:5000"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "Admin123!"

# Authentication session
SESSION = requests.Session()

def login(username, password):
    """Login to the NVC Banking Platform"""
    try:
        # Skip login for now, we don't have proper cookies management
        # Instead, we'll rely on the direct API access for the tests
        print("✅ Login successful (simulated)\n")
        return True
    except Exception as e:
        print(f"❌ Error during login: {str(e)}")
        return False

def check_blockchain_status():
    """Check the blockchain connection status"""
    try:
        response = SESSION.get(f"{API_HOST}/api/v1/blockchain/status")
        
        if response.status_code == 200:
            status = response.json()
            print("\n🔗 Blockchain Connection Status:")
            print(f"Connected: {'✅' if status.get('connected', False) else '❌'}")
            print(f"Network: {status.get('network', 'Unknown')}")
            print(f"Current Block: {status.get('current_block', 'Unknown')}")
            return status.get('connected', False)
        else:
            print(f"❌ Failed to check blockchain status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking blockchain status: {str(e)}")
        return False

def get_deployment_status():
    """Get the status of contract deployments"""
    try:
        response = SESSION.get(f"{API_HOST}/api/v1/blockchain/deployment/status")
        
        if response.status_code == 200:
            status = response.json()
            print("\n📊 Contract Deployment Status:")
            for contract, info in status.items():
                status_emoji = "✅" if info.get('status') == "COMPLETED" else "❌"
                print(f"{status_emoji} {contract}: {info.get('status')} - Address: {info.get('address')}")
            return status
        else:
            print(f"❌ Failed to get deployment status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting deployment status: {str(e)}")
        return None

def start_deployment():
    """Start the deployment of all contracts"""
    try:
        response = SESSION.post(f"{API_HOST}/api/v1/blockchain/deployment/start")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success', False):
                print("\n🚀 Deployment process started successfully!")
                print(f"Message: {result.get('message')}")
                return True
            else:
                print(f"\n❌ Deployment start failed: {result.get('message')}")
                return False
        else:
            print(f"\n❌ Failed to start deployment: {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Error starting deployment: {str(e)}")
        return False

def deploy_contract(contract_type):
    """Deploy a specific contract type"""
    try:
        response = SESSION.post(
            f"{API_HOST}/api/v1/blockchain/deployment/contract",
            json={"contract_type": contract_type}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success', False):
                print(f"\n🚀 {contract_type} deployment initiated!")
                print(f"Message: {result.get('message')}")
                return True
            else:
                print(f"\n❌ {contract_type} deployment failed: {result.get('message')}")
                return False
        else:
            print(f"\n❌ Failed to deploy {contract_type}: {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Error deploying {contract_type}: {str(e)}")
        return False

def monitor_deployment(interval=5, max_checks=12):
    """Monitor the deployment progress until completion or timeout"""
    print(f"\n⏳ Monitoring deployment progress (checking every {interval} seconds, max {max_checks} times)...")
    
    checks = 0
    all_completed = False
    
    while checks < max_checks and not all_completed:
        time.sleep(interval)
        
        status = get_deployment_status()
        if not status:
            print("❌ Failed to get status update")
            continue
            
        # Check if all contracts are deployed
        all_completed = all(
            info.get('status') == "COMPLETED" 
            for info in status.values()
        )
        
        checks += 1
        
        if all_completed:
            print("\n✅ All contracts successfully deployed!")
            return True
            
    if not all_completed:
        print("\n⚠️ Deployment monitoring timed out")
        print("The deployment may still be in progress. Please check status endpoint later.")
    
    return all_completed

def check_token_balance(address):
    """Check NVC token balance for an address"""
    try:
        response = SESSION.get(
            f"{API_HOST}/api/blockchain/token/balance",
            params={"address": address}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n💰 NVC Token Balance for {address}:")
            print(f"Balance: {result.get('balance')} NVCT")
            return result.get('balance')
        else:
            print(f"\n❌ Failed to check token balance: {response.status_code}")
            return None
    except Exception as e:
        print(f"\n❌ Error checking token balance: {str(e)}")
        return None

def check_settlement_fee():
    """Check the current settlement contract fee percentage"""
    try:
        response = SESSION.get(f"{API_HOST}/api/blockchain/settlement/fee")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n💸 Settlement Contract Fee Information:")
            print(f"Fee Percentage: {result.get('fee_percentage')}%")
            print(f"Fee Collector: {result.get('fee_collector')}")
            return result
        else:
            print(f"\n❌ Failed to check settlement fee: {response.status_code}")
            return None
    except Exception as e:
        print(f"\n❌ Error checking settlement fee: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Test NVC Banking Platform API')
    parser.add_argument('action', nargs='?', default='all',
                        choices=['status', 'deployment_status', 'start_deployment', 
                                 'deploy_settlement', 'deploy_multisig', 'deploy_token',
                                 'monitor', 'all'],
                        help='Action to perform')
    parser.add_argument('--username', default=DEFAULT_USERNAME, help='Login username')
    parser.add_argument('--password', default=DEFAULT_PASSWORD, help='Login password')
    
    args = parser.parse_args()
    
    # Login first
    if not login(args.username, args.password):
        sys.exit(1)
    
    # Execute requested action
    if args.action == 'status':
        check_blockchain_status()
    elif args.action == 'deployment_status':
        get_deployment_status()
    elif args.action == 'start_deployment':
        start_deployment()
    elif args.action == 'deploy_settlement':
        deploy_contract('settlement_contract')
    elif args.action == 'deploy_multisig':
        deploy_contract('multisig_wallet')
    elif args.action == 'deploy_token':
        deploy_contract('nvc_token')
    elif args.action == 'monitor':
        monitor_deployment()
    elif args.action == 'all':
        # Run the full test sequence
        if check_blockchain_status():
            print("\n=== Starting Full Deployment Test ===")
            if start_deployment():
                monitor_deployment()
            
            # Check final status
            get_deployment_status()

if __name__ == "__main__":
    main()