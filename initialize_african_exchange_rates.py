#!/usr/bin/env python3
"""
Initialize African Currency Exchange Rates
This script initializes exchange rates for African currencies with NVCT
"""

import logging
from app import app, db
from currency_exchange_service import CurrencyExchangeService
from account_holder_models import CurrencyExchangeRate, CurrencyType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Exchange rates for African currencies to USD (as of May 2025)
AFRICAN_CURRENCY_RATES = {
    # North Africa
    "DZD": 134.82,      # Algerian Dinar
    "EGP": 47.25,       # Egyptian Pound
    "LYD": 4.81,        # Libyan Dinar
    "MAD": 9.98,        # Moroccan Dirham
    "SDG": 599.53,      # Sudanese Pound
    "TND": 3.11,        # Tunisian Dinar
    
    # West Africa
    "NGN": 1500.00,     # Nigerian Naira (already in system)
    "GHS": 15.34,       # Ghanaian Cedi
    
    # East Africa
    "KES": 132.05,      # Kenyan Shilling
    "ETB": 56.93,       # Ethiopian Birr
    
    # Southern Africa
    "ZAR": 18.50,       # South African Rand
    "BWP": 13.68,       # Botswana Pula
    "ZMW": 26.42,       # Zambian Kwacha
    "MZN": 63.86,       # Mozambican Metical
}

def initialize_african_rates():
    """Initialize exchange rates for major African currencies"""
    logger.info("Initializing exchange rates for African currencies...")
    
    with app.app_context():
        try:
            # Process each African currency
            rates_added = 0
            for currency_code, usd_rate in AFRICAN_CURRENCY_RATES.items():
                try:
                    # Skip currencies that don't exist in our enum
                    if not hasattr(CurrencyType, currency_code):
                        logger.warning(f"Currency code {currency_code} not found in CurrencyType enum")
                        continue
                        
                    # Get the enum value for this currency
                    currency_enum = getattr(CurrencyType, currency_code)
                    
                    # Update USD to currency rate
                    usd_result = CurrencyExchangeService.update_exchange_rate(
                        CurrencyType.USD,
                        currency_enum,
                        usd_rate,
                        "system_african_rates"
                    )
                    
                    if usd_result:
                        logger.info(f"Updated USD to {currency_code} rate: 1 USD = {usd_rate} {currency_code}")
                        rates_added += 1
                    
                    # Update NVCT to currency rate (1:1 with USD)
                    nvct_result = CurrencyExchangeService.update_exchange_rate(
                        CurrencyType.NVCT,
                        currency_enum,
                        usd_rate,
                        "system_african_rates"
                    )
                    
                    if nvct_result:
                        logger.info(f"Updated NVCT to {currency_code} rate: 1 NVCT = {usd_rate} {currency_code}")
                        rates_added += 1
                        
                except Exception as e:
                    logger.error(f"Error processing {currency_code}: {str(e)}")
            
            logger.info(f"Successfully added {rates_added} exchange rates for African currencies")
            return True
        except Exception as e:
            logger.error(f"Error initializing African currency exchange rates: {str(e)}")
            return False

if __name__ == "__main__":
    initialize_african_rates()