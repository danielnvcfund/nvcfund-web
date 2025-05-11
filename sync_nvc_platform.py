#!/usr/bin/env python3
"""
NVC Platform Synchronization Tool
This script allows administrators to manually sync account holders from nvcplatform.net
to the NVC Banking Platform.

Usage:
    python sync_nvc_platform.py [options]

Options:
    --full     Perform a full synchronization of all accounts
    --test     Test connection to nvcplatform.net without syncing
    --status   Show current synchronization status
    --cron     Run as a scheduled task (no output)
"""

import sys
import os
import logging
import argparse
import requests
import json
import time
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import application context
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, db
from nvc_platform_integration import (
    fetch_accounts_from_nvc_platform,
    process_account_sync,
    run_full_sync
)

def test_connection():
    """Test API connection to NVC Platform"""
    try:
        # Get API credentials from environment
        api_url = os.environ.get('NVC_PLATFORM_API_URL', 'https://www.nvcplatform.net/api')
        api_key = os.environ.get('NVC_PLATFORM_API_KEY', '')
        api_secret = os.environ.get('NVC_PLATFORM_API_SECRET', '')
        
        if not api_key or not api_secret:
            print("✗ Error: API credentials not configured")
            print("  Set NVC_PLATFORM_API_KEY and NVC_PLATFORM_API_SECRET environment variables")
            return False
        
        # Try to connect
        print(f"Testing connection to {api_url}...")
        
        # Make a simple status request
        response = requests.get(
            f"{api_url}/status",
            params={'api_key': api_key},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"✗ Error: Failed to connect (HTTP {response.status_code})")
            print(f"  Response: {response.text}")
            return False
        
        result = response.json()
        
        if result.get('status') != 'success':
            print(f"✗ Error: API returned error - {result.get('message', 'Unknown error')}")
            return False
        
        print("✓ Connection successful")
        print(f"  Platform: {result.get('data', {}).get('name', 'NVC Platform')}")
        print(f"  Version: {result.get('data', {}).get('version', 'Unknown')}")
        return True
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False

def show_status():
    """Show current synchronization status"""
    with app.app_context():
        from account_holder_models import AccountHolder
        
        # Count synchronized accounts
        platform_accounts = AccountHolder.query.filter(
            AccountHolder.external_id.like('NVCPLAT-%')
        ).count()
        
        # Count total accounts
        total_accounts = AccountHolder.query.count()
        
        # Get last sync time
        last_sync = app.config.get('LAST_NVC_PLATFORM_SYNC', 'Never')
        
        # Format as a readable string if it's a timestamp
        if last_sync != 'Never':
            try:
                last_sync_dt = datetime.fromisoformat(last_sync)
                last_sync = last_sync_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            except (ValueError, TypeError):
                pass
        
        print("NVC Platform Synchronization Status")
        print("==================================")
        print(f"Total account holders: {total_accounts}")
        print(f"Synchronized from nvcplatform.net: {platform_accounts}")
        print(f"Last synchronization: {last_sync}")
        
        # Show API connection status
        api_url = os.environ.get('NVC_PLATFORM_API_URL', 'https://www.nvcplatform.net/api')
        api_key = os.environ.get('NVC_PLATFORM_API_KEY', '')
        
        if api_key:
            print(f"API Endpoint: {api_url}")
            print("API Key: Configured")
        else:
            print("API Key: Not configured")
            print("  To enable automatic synchronization, set NVC_PLATFORM_API_KEY and NVC_PLATFORM_API_SECRET")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="NVC Platform Synchronization Tool")
    parser.add_argument('--full', action='store_true', help='Perform a full synchronization')
    parser.add_argument('--test', action='store_true', help='Test connection without syncing')
    parser.add_argument('--status', action='store_true', help='Show current synchronization status')
    parser.add_argument('--cron', action='store_true', help='Run as a scheduled task (minimal output)')
    
    args = parser.parse_args()
    
    # Handle --test flag
    if args.test:
        return test_connection()
    
    # Handle --status flag
    if args.status:
        return show_status()
    
    # Regular sync process
    start_time = time.time()
    
    if not args.cron:
        print("Starting NVC Platform synchronization...")
    
    with app.app_context():
        if args.full:
            imported, updated, failed = run_full_sync()
        else:
            # Default to a single page sync
            accounts = fetch_accounts_from_nvc_platform(page=1, page_size=100, full_sync=False)
            
            if not accounts:
                if not args.cron:
                    print("No accounts available for synchronization")
                return False
                
            results = process_account_sync(accounts)
            imported = results['imported']
            updated = results['updated'] 
            failed = results['failed']
        
        # Update last sync timestamp
        app.config['LAST_NVC_PLATFORM_SYNC'] = datetime.utcnow().isoformat()
        
        duration = time.time() - start_time
        
        if not args.cron:
            print(f"Synchronization completed in {duration:.2f} seconds")
            print(f"Accounts imported: {imported}")
            print(f"Accounts updated: {updated}")
            print(f"Accounts failed: {failed}")
            
            if failed > 0:
                print("Check application logs for details on failures")
        
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)