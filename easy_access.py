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
        'Blockchain Status Page': f'{base_url}/blockchain/status',
        'Blockchain Admin Dashboard': f'{base_url}/admin/blockchain',
        'Mainnet Readiness': f'{base_url}/admin/blockchain/mainnet_readiness',
        'Gas Estimator': f'{base_url}/admin/blockchain/gas_estimator',
        'Login Page': f'{base_url}/login',
        'Admin Page': f'{base_url}/admin',
        'Main Dashboard': f'{base_url}/'
    }
    
    # Print the links
    print("\n===== DIRECT ACCESS LINKS =====")
    print("(Copy and paste these links into your browser)\n")
    
    for name, url in admin_links.items():
        print(f"{name}:\n{url}\n")
    
    print("==============================")

if __name__ == "__main__":
    generate_links()