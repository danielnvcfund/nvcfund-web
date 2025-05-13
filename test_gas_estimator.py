#!/usr/bin/env python3
"""
Test script for the gas estimator functionality
"""

import os
import sys
from decimal import Decimal
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our gas estimator module
from gas_estimator import (
    get_eth_price_usd,
    get_current_gas_price,
    estimate_deployment_cost,
    get_admin_eth_balance,
    estimate_all_deployment_costs,
    format_cost_estimate
)

def test_eth_price():
    """Test getting ETH price"""
    price = get_eth_price_usd()
    logger.info(f"Current ETH price: ${float(price):.2f} USD")
    return price is not None

def test_gas_price(network='sepolia'):
    """Test getting gas prices"""
    gas_data = get_current_gas_price(network)
    if not gas_data:
        logger.error(f"Could not get gas price for {network}")
        return False
    
    logger.info(f"Gas price data for {network}:")
    if 'legacy' in gas_data:
        logger.info(f"  Legacy Gas Price: {gas_data['legacy'] / 1e9:.2f} Gwei")
    
    if 'eip1559' in gas_data:
        base_fee = gas_data['eip1559']['base_fee']
        logger.info(f"  EIP-1559 Base Fee: {base_fee / 1e9:.2f} Gwei")
        logger.info(f"  Priority Fee (Slow): {gas_data['eip1559']['priority_fees']['slow'] / 1e9:.2f} Gwei")
        logger.info(f"  Priority Fee (Medium): {gas_data['eip1559']['priority_fees']['medium'] / 1e9:.2f} Gwei")
        logger.info(f"  Priority Fee (Fast): {gas_data['eip1559']['priority_fees']['fast'] / 1e9:.2f} Gwei")
    
    return True

def test_deployment_cost(contract_type='nvc_token', network='sepolia'):
    """Test estimating deployment costs"""
    cost_data = estimate_deployment_cost(contract_type, network, 'medium')
    if not cost_data:
        logger.error(f"Could not estimate deployment cost for {contract_type} on {network}")
        return False
    
    logger.info(f"Deployment cost estimate for {contract_type} on {network}:")
    logger.info(format_cost_estimate(cost_data))
    return True

def test_admin_balance(network='sepolia'):
    """Test getting admin ETH balance"""
    balance_data = get_admin_eth_balance(network)
    if not balance_data:
        logger.error(f"Could not get admin ETH balance on {network}")
        return False
    
    logger.info(f"Admin ETH Balance on {network}:")
    logger.info(f"  Address: {balance_data['address']}")
    logger.info(f"  Balance: {float(balance_data['balance_eth']):.6f} ETH (${float(balance_data['balance_usd']):.2f})")
    return True

def test_all_deployment_costs(network='sepolia'):
    """Test estimating all deployment costs"""
    all_costs = estimate_all_deployment_costs(network)
    if not all_costs:
        logger.error(f"Could not estimate all deployment costs on {network}")
        return False
    
    logger.info(f"Total deployment costs on {network}:")
    for speed in ['slow', 'medium', 'fast']:
        cost_eth = all_costs['total'][speed]['cost_eth']
        cost_usd = all_costs['total'][speed]['cost_usd']
        logger.info(f"  {speed.capitalize()}: {float(cost_eth):.6f} ETH (${float(cost_usd):.2f})")
    
    return True

def run_all_tests():
    """Run all tests"""
    logger.info("=========== GAS ESTIMATOR TESTS ===========")
    
    tests = [
        ("ETH Price", test_eth_price),
        ("Gas Price (Sepolia)", lambda: test_gas_price('sepolia')),
        ("Gas Price (Mainnet)", lambda: test_gas_price('mainnet')),
        ("NVC Token Deployment Cost", lambda: test_deployment_cost('nvc_token', 'sepolia')),
        ("MultiSig Wallet Deployment Cost", lambda: test_deployment_cost('multisig_wallet', 'sepolia')),
        ("Settlement Contract Deployment Cost", lambda: test_deployment_cost('settlement_contract', 'sepolia')),
        ("Admin ETH Balance", lambda: test_admin_balance('sepolia')),
        ("All Deployment Costs", lambda: test_all_deployment_costs('sepolia'))
    ]
    
    success_count = 0
    for name, test_func in tests:
        logger.info(f"\nRunning test: {name}")
        try:
            result = test_func()
            if result:
                logger.info(f"✅ {name}: PASSED")
                success_count += 1
            else:
                logger.error(f"❌ {name}: FAILED")
        except Exception as e:
            logger.exception(f"❌ {name}: ERROR - {str(e)}")
    
    logger.info(f"\n===========  TEST SUMMARY  ===========")
    logger.info(f"Tests passed: {success_count}/{len(tests)}")
    
    return success_count == len(tests)

if __name__ == "__main__":
    result = run_all_tests()
    sys.exit(0 if result else 1)