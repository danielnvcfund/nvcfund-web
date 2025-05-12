#!/usr/bin/env python3
"""
Gas Estimator for Ethereum Transactions

This module provides utilities for estimating gas costs for Ethereum transactions, 
particularly focused on contract deployments and interactions. It retrieves real-time
gas prices from the Ethereum network and estimates costs in both ETH and USD.
"""

import os
import json
import logging
import requests
from decimal import Decimal
from web3 import Web3
from blockchain import connect_to_ethereum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Approximate gas limits for different operations
GAS_LIMITS = {
    'erc20_deploy': 2500000,  # ERC-20 token deployment
    'erc20_transfer': 65000,  # ERC-20 token transfer
    'multisig_deploy': 4000000,  # MultiSig wallet deployment
    'multisig_submit': 250000,  # MultiSig submit transaction
    'multisig_confirm': 120000,  # MultiSig confirm transaction
    'settlement_deploy': 3000000,  # Settlement contract deployment
    'settlement_process': 300000,  # Settlement contract process transaction
}

# Cache for ETH price - refreshed every hour
ETH_PRICE_USD = None
LAST_ETH_PRICE_UPDATE = 0

def get_eth_price_usd():
    """Get the current ETH price in USD"""
    global ETH_PRICE_USD, LAST_ETH_PRICE_UPDATE
    import time
    
    current_time = time.time()
    # If we have a cached price less than 1 hour old, use it
    if ETH_PRICE_USD and current_time - LAST_ETH_PRICE_UPDATE < 3600:
        return ETH_PRICE_USD
    
    try:
        # Try CoinGecko API first (no API key needed)
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            ETH_PRICE_USD = Decimal(str(data['ethereum']['usd']))
            LAST_ETH_PRICE_UPDATE = current_time
            return ETH_PRICE_USD
            
        # If CoinGecko fails, try alternative API
        response = requests.get(
            "https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USD",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            ETH_PRICE_USD = Decimal(str(data['USD']))
            LAST_ETH_PRICE_UPDATE = current_time
            return ETH_PRICE_USD
    
    except Exception as e:
        logger.error(f"Error getting ETH price: {str(e)}")
        # If all fails, use a reasonable default
        return Decimal('2500.00')  # Default fallback price
    
    # If we got here, use the default
    return Decimal('2500.00')  # Default fallback price

def get_current_gas_price(network='mainnet'):
    """Get current gas price from the Ethereum network in Wei"""
    try:
        w3 = connect_to_ethereum(network=network)
        if not w3:
            logger.error(f"Could not connect to {network}")
            return None
        
        # Get current gas price
        gas_price = w3.eth.gas_price
        
        # For mainnet, also try to get EIP-1559 fees
        if network == 'mainnet':
            try:
                fee_history = w3.eth.fee_history(1, 'latest', [10, 50, 90])
                
                # If we have fee history, use it for more accurate estimates
                if fee_history and 'baseFeePerGas' in fee_history and fee_history['baseFeePerGas']:
                    base_fee = fee_history['baseFeePerGas'][0]
                    priority_fees = fee_history['reward'][0]
                    
                    # Return both legacy and EIP-1559 gas prices
                    return {
                        'legacy': gas_price,
                        'eip1559': {
                            'base_fee': base_fee,
                            'priority_fees': {
                                'slow': priority_fees[0],
                                'medium': priority_fees[1],
                                'fast': priority_fees[2]
                            },
                            'max_fee_slow': base_fee + priority_fees[0],
                            'max_fee_medium': base_fee + priority_fees[1],
                            'max_fee_fast': base_fee + priority_fees[2]
                        }
                    }
            except Exception as e:
                logger.warning(f"Error getting EIP-1559 fees: {str(e)}")
        
        # Return just legacy gas price if EIP-1559 fails or if we're on testnet
        return {'legacy': gas_price}
    
    except Exception as e:
        logger.error(f"Error getting gas price: {str(e)}")
        return None

def calculate_tx_cost(gas_limit, gas_price_data, speed='medium'):
    """Calculate transaction cost in ETH and USD"""
    result = {}
    
    # If we have EIP-1559 data and this is for mainnet, use it
    if 'eip1559' in gas_price_data:
        # Select the right priority fee based on speed
        if speed == 'slow':
            max_fee = gas_price_data['eip1559']['max_fee_slow']
        elif speed == 'medium':
            max_fee = gas_price_data['eip1559']['max_fee_medium']
        else:  # fast
            max_fee = gas_price_data['eip1559']['max_fee_fast']
        
        # Calculate costs
        gas_price_gwei = max_fee / 1e9
        gas_price_eth = max_fee / 1e18
        cost_eth = Decimal(str(gas_limit * gas_price_eth))
        eth_price = get_eth_price_usd()
        cost_usd = cost_eth * eth_price
        
        result = {
            'type': 'eip1559',
            'gas_limit': gas_limit,
            'gas_price_wei': max_fee,
            'gas_price_gwei': gas_price_gwei,
            'cost_eth': cost_eth,
            'cost_usd': cost_usd,
            'speed': speed
        }
    else:
        # Legacy transaction
        gas_price = gas_price_data['legacy']
        gas_price_gwei = gas_price / 1e9
        gas_price_eth = gas_price / 1e18
        cost_eth = Decimal(str(gas_limit * gas_price_eth))
        eth_price = get_eth_price_usd()
        cost_usd = cost_eth * eth_price
        
        result = {
            'type': 'legacy',
            'gas_limit': gas_limit,
            'gas_price_wei': gas_price,
            'gas_price_gwei': gas_price_gwei,
            'cost_eth': cost_eth,
            'cost_usd': cost_usd
        }
    
    return result

def format_cost_estimate(cost_data):
    """Format cost estimate for display"""
    if not cost_data:
        return "Could not estimate cost"
    
    cost_eth = cost_data['cost_eth']
    cost_usd = cost_data['cost_usd']
    gas_price_gwei = cost_data['gas_price_gwei']
    
    if cost_data['type'] == 'eip1559':
        return (
            f"Estimated Cost ({cost_data['speed']} speed):\n"
            f"  Gas Limit: {cost_data['gas_limit']:,} units\n"
            f"  Max Fee: {gas_price_gwei:.2f} Gwei\n"
            f"  Cost: {float(cost_eth):.6f} ETH (${float(cost_usd):.2f})\n"
        )
    else:
        return (
            f"Estimated Cost:\n"
            f"  Gas Limit: {cost_data['gas_limit']:,} units\n"
            f"  Gas Price: {gas_price_gwei:.2f} Gwei\n"
            f"  Cost: {float(cost_eth):.6f} ETH (${float(cost_usd):.2f})\n"
        )

def estimate_deployment_cost(contract_type, network='mainnet', speed='medium'):
    """Estimate the cost of deploying a contract"""
    if contract_type == 'nvc_token':
        gas_limit = GAS_LIMITS['erc20_deploy']
    elif contract_type == 'multisig_wallet':
        gas_limit = GAS_LIMITS['multisig_deploy']
    elif contract_type == 'settlement_contract':
        gas_limit = GAS_LIMITS['settlement_deploy']
    else:
        logger.error(f"Unknown contract type: {contract_type}")
        return None
    
    gas_price_data = get_current_gas_price(network)
    if not gas_price_data:
        return None
    
    return calculate_tx_cost(gas_limit, gas_price_data, speed)

def estimate_contract_interaction_cost(interaction_type, network='mainnet', speed='medium'):
    """Estimate the cost of interacting with a contract"""
    if interaction_type not in GAS_LIMITS:
        logger.error(f"Unknown interaction type: {interaction_type}")
        return None
    
    gas_limit = GAS_LIMITS[interaction_type]
    gas_price_data = get_current_gas_price(network)
    if not gas_price_data:
        return None
    
    return calculate_tx_cost(gas_limit, gas_price_data, speed)

def estimate_all_deployment_costs(network='mainnet'):
    """Estimate costs for all contract deployments"""
    results = {}
    
    for contract_type in ['nvc_token', 'multisig_wallet', 'settlement_contract']:
        slow_estimate = estimate_deployment_cost(contract_type, network, 'slow')
        medium_estimate = estimate_deployment_cost(contract_type, network, 'medium')
        fast_estimate = estimate_deployment_cost(contract_type, network, 'fast')
        
        results[contract_type] = {
            'slow': slow_estimate,
            'medium': medium_estimate,
            'fast': fast_estimate
        }
    
    # Calculate total costs
    total_eth_slow = sum(Decimal(str(results[ct]['slow']['cost_eth'])) for ct in results)
    total_eth_medium = sum(Decimal(str(results[ct]['medium']['cost_eth'])) for ct in results)
    total_eth_fast = sum(Decimal(str(results[ct]['fast']['cost_eth'])) for ct in results)
    
    eth_price = get_eth_price_usd()
    total_usd_slow = total_eth_slow * eth_price
    total_usd_medium = total_eth_medium * eth_price
    total_usd_fast = total_eth_fast * eth_price
    
    results['total'] = {
        'slow': {'cost_eth': total_eth_slow, 'cost_usd': total_usd_slow},
        'medium': {'cost_eth': total_eth_medium, 'cost_usd': total_usd_medium},
        'fast': {'cost_eth': total_eth_fast, 'cost_usd': total_usd_fast}
    }
    
    return results

def get_admin_eth_balance(network='mainnet'):
    """Get the current ETH balance of the admin account"""
    try:
        admin_address = os.environ.get('ADMIN_ETH_ADDRESS')
        if not admin_address:
            logger.error("Admin ETH address not set in environment variables")
            return None
        
        w3 = connect_to_ethereum(network=network)
        if not w3:
            logger.error(f"Could not connect to {network}")
            return None
        
        # Check if the address is valid
        if not w3.is_address(admin_address):
            logger.error(f"Invalid Ethereum address: {admin_address}")
            return None
        
        # Get the balance
        balance_wei = w3.eth.get_balance(admin_address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        
        # Get USD value
        eth_price = get_eth_price_usd()
        balance_usd = Decimal(str(balance_eth)) * eth_price
        
        return {
            'address': admin_address,
            'balance_wei': balance_wei,
            'balance_eth': Decimal(str(balance_eth)),
            'balance_usd': balance_usd
        }
    
    except Exception as e:
        logger.error(f"Error getting admin ETH balance: {str(e)}")
        return None

if __name__ == "__main__":
    # Simple command line interface for testing
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'price':
            price = get_eth_price_usd()
            print(f"Current ETH price: ${float(price):.2f} USD")
        
        elif command == 'gas':
            network = sys.argv[2] if len(sys.argv) > 2 else 'mainnet'
            gas_data = get_current_gas_price(network)
            if gas_data:
                if 'eip1559' in gas_data:
                    print(f"EIP-1559 Base Fee: {gas_data['eip1559']['base_fee'] / 1e9:.2f} Gwei")
                    print(f"Slow Priority Fee: {gas_data['eip1559']['priority_fees']['slow'] / 1e9:.2f} Gwei")
                    print(f"Medium Priority Fee: {gas_data['eip1559']['priority_fees']['medium'] / 1e9:.2f} Gwei")
                    print(f"Fast Priority Fee: {gas_data['eip1559']['priority_fees']['fast'] / 1e9:.2f} Gwei")
                print(f"Legacy Gas Price: {gas_data['legacy'] / 1e9:.2f} Gwei")
            else:
                print("Could not get gas price")
        
        elif command == 'estimate':
            contract_type = sys.argv[2] if len(sys.argv) > 2 else 'nvc_token'
            network = sys.argv[3] if len(sys.argv) > 3 else 'mainnet'
            
            print(f"Estimating deployment cost for {contract_type} on {network}...")
            
            slow_estimate = estimate_deployment_cost(contract_type, network, 'slow')
            medium_estimate = estimate_deployment_cost(contract_type, network, 'medium')
            fast_estimate = estimate_deployment_cost(contract_type, network, 'fast')
            
            print("Slow:")
            print(format_cost_estimate(slow_estimate))
            print("Medium:")
            print(format_cost_estimate(medium_estimate))
            print("Fast:")
            print(format_cost_estimate(fast_estimate))
        
        elif command == 'balance':
            network = sys.argv[2] if len(sys.argv) > 2 else 'mainnet'
            balance_data = get_admin_eth_balance(network)
            
            if balance_data:
                print(f"Admin ETH Balance on {network}:")
                print(f"  Address: {balance_data['address']}")
                print(f"  Balance: {float(balance_data['balance_eth']):.6f} ETH (${float(balance_data['balance_usd']):.2f})")
            else:
                print("Could not get admin ETH balance")
        
        elif command == 'all':
            network = sys.argv[2] if len(sys.argv) > 2 else 'mainnet'
            print(f"Estimating all deployment costs on {network}...")
            
            all_costs = estimate_all_deployment_costs(network)
            
            for contract_type in ['nvc_token', 'multisig_wallet', 'settlement_contract']:
                print(f"\n{contract_type.upper()} DEPLOYMENT:")
                print("Slow:")
                print(format_cost_estimate(all_costs[contract_type]['slow']))
                print("Medium:")
                print(format_cost_estimate(all_costs[contract_type]['medium']))
                print("Fast:")
                print(format_cost_estimate(all_costs[contract_type]['fast']))
            
            total = all_costs['total']
            print("\nTOTAL DEPLOYMENT COSTS:")
            print(f"  Slow: {float(total['slow']['cost_eth']):.6f} ETH (${float(total['slow']['cost_usd']):.2f})")
            print(f"  Medium: {float(total['medium']['cost_eth']):.6f} ETH (${float(total['medium']['cost_usd']):.2f})")
            print(f"  Fast: {float(total['fast']['cost_eth']):.6f} ETH (${float(total['fast']['cost_usd']):.2f})")
        
        else:
            print("Unknown command")
            print("Available commands: price, gas, estimate, balance, all")
    
    else:
        print("ETH Gas Estimator CLI")
        print("Available commands: price, gas, estimate, balance, all")