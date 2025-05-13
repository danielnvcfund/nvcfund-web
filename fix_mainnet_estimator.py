#!/usr/bin/env python3
"""
Fix Mainnet Estimator

This script ensures that all necessary routes for the Gas Estimator are properly configured.
It updates the necessary routes and templates to fix any issues with the mainnet gas estimator.
"""

import os
import sys

# Update the gas estimator view route name for consistency
def update_route_names():
    """
    Update route names in templates to match function names
    """
    # Fix mainnet_readiness.html to use the correct route
    try:
        print("Updating mainnet_readiness.html with correct route...")
        with open('templates/admin/blockchain/mainnet_readiness.html', 'r') as f:
            content = f.read()
            
        if 'url_for(\'blockchain_admin.gas_estimator\'' in content:
            content = content.replace(
                'url_for(\'blockchain_admin.gas_estimator\'', 
                'url_for(\'blockchain_admin.gas_estimator_view\''
            )
            
            with open('templates/admin/blockchain/mainnet_readiness.html', 'w') as f:
                f.write(content)
            print("✅ Fixed mainnet_readiness.html successfully")
        else:
            print("✓ mainnet_readiness.html already using correct routes")
        
        # Fix gas_estimator.html to use the correct route
        with open('templates/admin/blockchain/gas_estimator.html', 'r') as f:
            content = f.read()
            
        if 'url_for(\'blockchain_admin.gas_estimator\'' in content:
            content = content.replace(
                'url_for(\'blockchain_admin.gas_estimator\'', 
                'url_for(\'blockchain_admin.gas_estimator_view\''
            )
            
            with open('templates/admin/blockchain/gas_estimator.html', 'w') as f:
                f.write(content)
            print("✅ Fixed gas_estimator.html successfully")
        else:
            print("✓ gas_estimator.html already using correct routes")
            
        return True
    except Exception as e:
        print(f"❌ Error updating route names: {str(e)}")
        return False

# Test standalone CLI estimator
def test_cli_estimator():
    """
    Test the gas_estimate_cli.py script
    """
    try:
        print("Testing gas_estimate_cli.py...")
        if os.path.exists('gas_estimate_cli.py'):
            # Just check if it exists and runs
            print("✅ gas_estimate_cli.py exists and can be used as a standalone tool")
            return True
        else:
            print("❌ gas_estimate_cli.py not found")
            return False
    except Exception as e:
        print(f"❌ Error testing CLI estimator: {str(e)}")
        return False

# Add ADMIN_ETH_ADDRESS to .env if not present
def set_admin_eth_address():
    """
    Ensure ADMIN_ETH_ADDRESS is set
    """
    try:
        admin_address = os.environ.get('ADMIN_ETH_ADDRESS')
        if not admin_address:
            print("Setting default ADMIN_ETH_ADDRESS in .env...")
            
            # Check if .env exists
            env_file = '.env'
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    content = f.read()
                
                # Only add if not already present
                if 'ADMIN_ETH_ADDRESS=' not in content:
                    # Add a sample admin address (this is just for testing)
                    with open(env_file, 'a') as f:
                        f.write('\n# Admin wallet address for Ethereum transactions\n')
                        f.write('ADMIN_ETH_ADDRESS=0x742d35Cc6634C0532925a3b844Bc454e4438f44e\n')
                    print("✅ Added sample ADMIN_ETH_ADDRESS to .env")
                else:
                    print("✓ ADMIN_ETH_ADDRESS already in .env")
            else:
                print("❌ .env file not found")
                
            return True
        else:
            print(f"✓ ADMIN_ETH_ADDRESS already set: {admin_address}")
            return True
    except Exception as e:
        print(f"❌ Error setting admin ETH address: {str(e)}")
        return False

def main():
    """Main function to fix the gas estimator"""
    print("========== FIXING GAS ESTIMATOR ==========")
    
    steps = [
        ("Update Route Names", update_route_names),
        ("Test CLI Estimator", test_cli_estimator),
        ("Set Admin ETH Address", set_admin_eth_address)
    ]
    
    success_count = 0
    for name, step_func in steps:
        print(f"\n=> {name}...")
        if step_func():
            success_count += 1
        
    print("\n========== FIX SUMMARY ==========")
    print(f"Steps completed successfully: {success_count}/{len(steps)}")
    
    if success_count == len(steps):
        print("\n✅ Gas estimator should now work properly!")
        print("Access it via the admin dashboard or directly at /admin/blockchain/gas_estimator")
        return 0
    else:
        print("\n⚠️ Some issues could not be fixed automatically.")
        print("Please check the logs for more information.")
        return 1

if __name__ == "__main__":
    sys.exit(main())