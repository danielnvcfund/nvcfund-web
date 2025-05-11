#!/usr/bin/env python3
"""
Optimize Currency Exchange Initialization
This module provides optimization for the currency exchange initialization process
to reduce startup time and improve overall performance.
"""

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def timed_execution(func):
    """Decorator to time execution of a function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Function {func.__name__} executed in {elapsed_time:.4f} seconds")
        return result
    return wrapper

@timed_execution
def initialize_rates_on_startup():
    """Initialize all exchange rates at startup in an optimized way"""
    import currency_exchange_workaround
    from account_holder_models import CurrencyType
    
    # Pre-populate the memory cache with base rates
    rates = {}
    
    # Add basic rates for USD and NVCT (1:1 peg)
    rates["USD_NVCT"] = {
        'rate': 1.0,
        'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'from': "USD", 
        'to': "NVCT"
    }
    
    rates["NVCT_USD"] = {
        'rate': 1.0,
        'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        'from': "NVCT", 
        'to': "USD"
    }
    
    # Add basic rates for problematic African currencies
    problematic_currencies = ["XOF", "XAF", "XPF", "XUA", "XDR", "XTS", "XXX"]
    
    # West African CFA Franc (XOF)
    rates["USD_XOF"] = {'rate': 601.04, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "USD", 'to': "XOF"}
    rates["NVCT_XOF"] = {'rate': 601.04, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "NVCT", 'to': "XOF"}
    rates["XOF_USD"] = {'rate': 1/601.04, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "XOF", 'to': "USD"}
    rates["XOF_NVCT"] = {'rate': 1/601.04, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "XOF", 'to': "NVCT"}
    
    # Central African CFA Franc (XAF) 
    rates["USD_XAF"] = {'rate': 601.04, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "USD", 'to': "XAF"}
    rates["NVCT_XAF"] = {'rate': 601.04, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "NVCT", 'to': "XAF"}
    rates["XAF_USD"] = {'rate': 1/601.04, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "XAF", 'to': "USD"}
    rates["XAF_NVCT"] = {'rate': 1/601.04, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "XAF", 'to': "NVCT"}
    
    # Add specialized rates for AFD1, SFN, AKLUMI
    afd1_rate = 339.40  # 10% of gold price at $3,394/oz
    rates["USD_AFD1"] = {'rate': 1/afd1_rate, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "USD", 'to': "AFD1"}
    rates["AFD1_USD"] = {'rate': afd1_rate, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "AFD1", 'to': "USD"}
    rates["NVCT_AFD1"] = {'rate': 1/afd1_rate, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "NVCT", 'to': "AFD1"}
    rates["AFD1_NVCT"] = {'rate': afd1_rate, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "AFD1", 'to': "NVCT"}
    
    # SFN at 1:1 with NVCT
    rates["USD_SFN"] = {'rate': 1.0, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "USD", 'to': "SFN"}
    rates["SFN_USD"] = {'rate': 1.0, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "SFN", 'to': "USD"}
    rates["NVCT_SFN"] = {'rate': 1.0, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "NVCT", 'to': "SFN"}
    rates["SFN_NVCT"] = {'rate': 1.0, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "SFN", 'to': "NVCT"}
    
    # AKLUMI at 3.25 USD
    rates["USD_AKLUMI"] = {'rate': 1/3.25, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "USD", 'to': "AKLUMI"}
    rates["AKLUMI_USD"] = {'rate': 3.25, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "AKLUMI", 'to': "USD"}
    rates["NVCT_AKLUMI"] = {'rate': 1/3.25, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "NVCT", 'to': "AKLUMI"}
    rates["AKLUMI_NVCT"] = {'rate': 3.25, 'updated': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), 'from': "AKLUMI", 'to': "NVCT"}
    
    # Set these rates directly in memory cache
    currency_exchange_workaround._RATES_CACHE = rates
    currency_exchange_workaround._CACHE_LOADED = True
    
    # Save to disk in background
    currency_exchange_workaround.save_rates(rates)
    
    # Measure what's been accomplished
    num_rates = len(rates)
    logger.info(f"Optimized initialization complete. Set {num_rates} exchange rates.")
    return num_rates

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = initialize_rates_on_startup()
    print(f"Initialized {count} exchange rates")