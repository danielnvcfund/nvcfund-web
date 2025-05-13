#!/usr/bin/env python3
"""
Fix Contract Addresses

This script corrects the EIP-55 checksum format of the contract addresses
in the .env file to prevent Web3.py errors.
"""

import os
import sys
import re
from web3 import Web3

def fix_contract_addresses():
    """Fix contract addresses in the .env file to use proper EIP-55 checksum format"""
    
    # Load the .env file
    env_file = '.env'
    if not os.path.exists(env_file):
        print(f"❌ Error: {env_file} not found.")
        return False
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Define a pattern to find contract addresses
    pattern = r'(SETTLEMENT_CONTRACT_ADDRESS_TESTNET|MULTISIG_WALLET_ADDRESS_TESTNET|NVC_TOKEN_ADDRESS_TESTNET)=(0x[a-fA-F0-9]{40})'
    
    # Find all contract addresses
    matches = re.findall(pattern, content)
    if not matches:
        print("⚠️ No contract addresses found in .env file.")
        return False
    
    # Replace each address with its checksummed version
    new_content = content
    replace_count = 0
    
    for var_name, address in matches:
        try:
            # Convert the address to checksum format
            checksummed_address = Web3.to_checksum_address(address)
            
            # Replace the address in the content
            new_content = new_content.replace(
                f"{var_name}={address}",
                f"{var_name}={checksummed_address}"
            )
            
            print(f"✅ Fixed {var_name}: {address} → {checksummed_address}")
            replace_count += 1
        except Exception as e:
            print(f"❌ Error fixing {var_name}: {str(e)}")
    
    # Only write to the file if changes were made
    if replace_count > 0:
        with open(env_file, 'w') as f:
            f.write(new_content)
        print(f"\nSuccessfully updated {replace_count} contract addresses with proper checksums.")
        return True
    else:
        print("\nNo changes made to the .env file.")
        return False

if __name__ == "__main__":
    print("========== FIXING CONTRACT ADDRESSES ==========")
    result = fix_contract_addresses()
    if result:
        print("\n✅ Contract addresses updated successfully. Restart the application to apply changes.")
    else:
        print("\n⚠️ No changes were made to contract addresses.")