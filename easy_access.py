#!/usr/bin/env python3
"""
Easy Access - Direct Links Generator

This script provides direct links to important admin pages that can be accessed
without going through the full navigation flow.
"""

import os
import sys
from urllib.parse import urlparse

def generate_links():
    """Generate direct links for admin pages"""
    
    # Get the domain from the Replit environment
    domain = os.environ.get('REPLIT_DOMAINS', '').split(',')[0] if os.environ.get('REPLIT_DOMAINS') else 'localhost:5000'
    
    # Create the base URL
    if 'localhost' in domain:
        base_url = f'http://{domain}'
    else:
        base_url = f'https://{domain}'
    
    # Generate links for admin pages
    admin_links = {
        '🔧 MAIN BLOCKCHAIN DASHBOARD (WHAT YOU\'RE LOOKING FOR)': f'{base_url}/admin/blockchain',
        '✨ Blockchain Features Guide': f'{base_url}/blockchain/guide',
        '📊 Blockchain Status Page': f'{base_url}/blockchain/status',
        '✅ Mainnet Readiness': f'{base_url}/admin/blockchain/mainnet_readiness',
        '⛽ Gas Estimator': f'{base_url}/admin/blockchain/gas_estimator',
        '🔑 Login Page': f'{base_url}/login',
        '🛡️ Admin Page': f'{base_url}/admin',
        '🏠 Main Dashboard': f'{base_url}/'
    }
    
    # Alternative URLs that also work (redirects)
    alt_links = {
        'Alternate URL: /main/blockchain': f'{base_url}/main/blockchain',
        'Alternate URL: /blockchain': f'{base_url}/blockchain'
    }
    
    # Print the links
    print("\n===== DIRECT ACCESS LINKS =====")
    print("(Copy and paste these links into your browser)\n")
    
    for name, url in admin_links.items():
        print(f"{name}:\n{url}\n")
    
    print("----- ALTERNATIVE URLS -----")
    print("These URLs also work as redirects to the blockchain pages\n")
    
    for name, url in alt_links.items():
        print(f"{name}:\n{url}\n")
    
    print("===============================")

if __name__ == "__main__":
    generate_links()