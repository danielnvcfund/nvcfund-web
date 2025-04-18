#!/usr/bin/env python3
"""
API Testing Script for Smart Contract Deployment API
This script demonstrates the usage of the blockchain API endpoints
for deploying and monitoring smart contracts.
"""

import requests
import json
import time
import argparse

BASE_URL = "http://localhost:5000"
SESSION = requests.Session()

def login(username, password):
    """Login to the NVC Banking Platform"""
    login_url = f"{BASE_URL}/main/login"
    login_data = {
        "username": username,
        "password": password
    }
    
    # First get the login page to obtain any CSRF tokens
    response = SESSION.get(login_url)
    
    # Now submit the login form
    response = SESSION.post(login_url, data=login_data, allow_redirects=True)
    
    if response.status_code == 200 and "Dashboard" in response.text:
        print("✅ Login successful")
        return True
    else:
        print("❌ Login failed")
        return False

def check_blockchain_status():
    """Check the blockchain connection status"""
    status_url = f"{BASE_URL}/api/v1/blockchain/status"
    response = SESSION.get(status_url)
    
    if response.status_code == 200:
        data = response.json()
        print("\n🔍 Blockchain Status:")
        print(f"Connected: {data.get('connected', False)}")
        print(f"Network: {data.get('network', 'Unknown')}")
        print(f"Current Block: {data.get('current_block', 'Unknown')}")
        return data
    else:
        print(f"❌ Failed to get blockchain status. Status code: {response.status_code}")
        return None

def get_deployment_status():
    """Get the status of contract deployments"""
    status_url = f"{BASE_URL}/api/v1/blockchain/deploy/status"
    response = SESSION.get(status_url)
    
    if response.status_code == 200:
        data = response.json()
        print("\n📊 Contract Deployment Status:")
        
        if 'status' in data:
            for contract, info in data['status'].items():
                status = info.get('status', 'unknown')
                address = info.get('address', 'N/A')
                
                status_icon = "✅" if status == "completed" else "⏳" if status in ["pending", "in_progress"] else "❌"
                print(f"{status_icon} {contract}: {status.upper()} - Address: {address}")
        return data
    else:
        print(f"❌ Failed to get deployment status. Status code: {response.status_code}")
        return None

def start_deployment():
    """Start the deployment of all contracts"""
    deploy_url = f"{BASE_URL}/api/v1/blockchain/deploy/all"
    response = SESSION.post(deploy_url)
    
    if response.status_code == 200:
        data = response.json()
        print("\n🚀 Started contract deployment")
        print(f"Message: {data.get('message', 'No message')}")
        return data
    else:
        print(f"❌ Failed to start deployment. Status code: {response.status_code}")
        return None

def deploy_contract(contract_type):
    """Deploy a specific contract type"""
    if contract_type not in ["settlement", "multisig", "token"]:
        print("❌ Invalid contract type. Must be 'settlement', 'multisig', or 'token'")
        return None
    
    deploy_url = f"{BASE_URL}/api/v1/blockchain/deploy/{contract_type}"
    response = SESSION.post(deploy_url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n🚀 Started {contract_type} contract deployment")
        if data.get('success', False):
            print(f"Contract Address: {data.get('address', 'Unknown')}")
            print(f"Transaction Hash: {data.get('tx_hash', 'Unknown')}")
        else:
            print(f"Message: {data.get('message', 'Unknown error')}")
        return data
    else:
        print(f"❌ Failed to deploy {contract_type} contract. Status code: {response.status_code}")
        return None

def monitor_deployment(interval=5, max_checks=12):
    """Monitor the deployment progress until completion or timeout"""
    print("\n⏳ Monitoring deployment progress...")
    checks = 0
    all_completed = False
    
    while checks < max_checks and not all_completed:
        data = get_deployment_status()
        
        if data and 'status' in data:
            statuses = [info.get('status') for info in data['status'].values()]
            all_completed = all(status == "completed" for status in statuses)
            
            if all_completed:
                print("\n✅ All contracts deployed successfully!")
                break
                
            if "failed" in statuses:
                print("\n❌ One or more contract deployments failed.")
                break
                
        print(f"Checking again in {interval} seconds...")
        time.sleep(interval)
        checks += 1
        
    if checks >= max_checks and not all_completed:
        print("\n⚠️ Monitoring timed out. Deployments may still be in progress.")

def main():
    parser = argparse.ArgumentParser(description="NVC Banking Platform Blockchain API Test Client")
    parser.add_argument('--username', default="admin", help="Username for login")
    parser.add_argument('--password', default="Admin123!", help="Password for login")
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    subparsers.add_parser('status', help='Check blockchain status')
    subparsers.add_parser('deployment_status', help='Check deployment status')
    
    deploy_parser = subparsers.add_parser('deploy', help='Deploy contracts')
    deploy_parser.add_argument('--type', choices=['all', 'settlement', 'multisig', 'token'], 
                               default='all', help='Contract type to deploy')
    
    monitor_parser = subparsers.add_parser('monitor', help='Monitor deployment progress')
    monitor_parser.add_argument('--interval', type=int, default=5, 
                               help='Check interval in seconds')
    monitor_parser.add_argument('--max-checks', type=int, default=12,
                               help='Maximum number of status checks before timeout')
    
    args = parser.parse_args()
    
    # Login first
    if not login(args.username, args.password):
        return
    
    # Execute the requested command
    if args.command == 'status':
        check_blockchain_status()
    elif args.command == 'deployment_status':
        get_deployment_status()
    elif args.command == 'deploy':
        if args.type == 'all':
            start_deployment()
        else:
            deploy_contract(args.type)
    elif args.command == 'monitor':
        monitor_deployment(args.interval, args.max_checks)
    else:
        # Default action if no command specified
        print("\n📋 Blockchain API Test Sequence:")
        check_blockchain_status()
        get_deployment_status()
        
        print("\nDo you want to start contract deployment? (y/n): ", end="")
        choice = input().strip().lower()
        
        if choice == 'y':
            start_deployment()
            monitor_deployment()

if __name__ == "__main__":
    main()