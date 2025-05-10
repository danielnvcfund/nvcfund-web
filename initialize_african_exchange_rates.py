#!/usr/bin/env python3
"""
Initialize African Currency Exchange Rates
This script uses the workaround to test currency exchange rates for African currencies
"""

import logging
from app import app
from currency_exchange_service import CurrencyExchangeService
from account_holder_models import CurrencyType
import currency_exchange_workaround

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test exchange rates for a selection of African currencies
TEST_CURRENCIES = [
    # North Africa
    "DZD",    # Algerian Dinar
    "EGP",    # Egyptian Pound
    "LYD",    # Libyan Dinar
    
    # West Africa
    "NGN",    # Nigerian Naira
    "GHS",    # Ghanaian Cedi
    "XOF",    # CFA Franc BCEAO
    
    # Central Africa
    "XAF",    # CFA Franc BEAC
    "CDF",    # Congolese Franc
    
    # East Africa
    "KES",    # Kenyan Shilling
    "ETB",    # Ethiopian Birr
    "UGX",    # Ugandan Shilling
    
    # Southern Africa
    "ZAR",    # South African Rand
    "BWP",    # Botswana Pula
    "ZMW",    # Zambian Kwacha
]

def test_african_rates():
    """Test exchange rates for African currencies using the workaround"""
    logger.info("Testing exchange rates for African currencies with workaround...")
    
    # Test USD to African currency rates
    print("USD to African Currencies:")
    for currency_code in TEST_CURRENCIES:
        rate = currency_exchange_workaround.get_exchange_rate("USD", currency_code)
        print(f"1 USD = {rate:.4f} {currency_code}")
    
    print("\nNVCT to African Currencies:")
    for currency_code in TEST_CURRENCIES:
        rate = currency_exchange_workaround.get_exchange_rate("NVCT", currency_code)
        print(f"1 NVCT = {rate:.4f} {currency_code}")
    
    # Test a few African cross-rates
    print("\nAfrican Cross-Rates:")
    cross_pairs = [
        ("NGN", "ZAR"),
        ("EGP", "KES"),
        ("ZAR", "XOF"),
        ("GHS", "BWP"),
    ]
    
    for from_curr, to_curr in cross_pairs:
        rate = currency_exchange_workaround.get_exchange_rate(from_curr, to_curr)
        print(f"1 {from_curr} = {rate:.6f} {to_curr}")
    
    return True

# When run directly, test the rates
if __name__ == "__main__":
    test_african_rates()