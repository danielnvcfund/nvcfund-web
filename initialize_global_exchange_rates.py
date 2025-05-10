#!/usr/bin/env python3
"""
Initialize Global Currency Exchange Rates
This script initializes exchange rates for major world currencies with NVCT
"""

import logging
from app import app, db
from currency_exchange_service import CurrencyExchangeService
from account_holder_models import CurrencyExchangeRate, CurrencyType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Exchange rates for major world currencies to USD (as of May 2025)
GLOBAL_CURRENCY_RATES = {
    # Major world currencies (currently in the system)
    "EUR": 0.93,      # Euro
    "GBP": 0.79,      # British Pound
    "NGN": 1500.00,   # Nigerian Naira
    
    # Additional major world currencies
    "JPY": 157.32,    # Japanese Yen
    "CHF": 0.92,      # Swiss Franc
    "CAD": 1.36,      # Canadian Dollar
    "AUD": 1.51,      # Australian Dollar
    "CNY": 7.24,      # Chinese Yuan Renminbi
    "INR": 83.42,     # Indian Rupee
    "BRL": 5.14,      # Brazilian Real
    "ZAR": 18.50,     # South African Rand
    
    # Cryptocurrencies (currently in the system)
    "BTC": 62000.00,   # Bitcoin (USD per 1 BTC)
    "ETH": 3000.00,    # Ethereum (USD per 1 ETH)
    
    # Additional top cryptocurrencies
    "USDT": 1.00,      # Tether
    "USDC": 1.00,      # USD Coin
    "BNB": 615.00,     # Binance Coin
    "SOL": 135.00,     # Solana
    "XRP": 0.52,       # XRP (Ripple)
    "ADA": 0.45,       # Cardano
    "AVAX": 35.00,     # Avalanche
    "DOGE": 0.15,      # Dogecoin
}

def initialize_global_rates():
    """Initialize exchange rates for major global currencies"""
    logger.info("Initializing exchange rates for major global currencies...")
    
    with app.app_context():
        try:
            # Initialize USD to NVCT rate first (1:1 peg)
            CurrencyExchangeService.update_exchange_rate(
                CurrencyType.USD,
                CurrencyType.NVCT,
                1.0,
                "system_global_rates"
            )
            logger.info("Set USD to NVCT rate: 1:1")
            
            # Process each global currency
            rates_added = 0
            for currency_code, usd_rate in GLOBAL_CURRENCY_RATES.items():
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
                        "system_global_rates"
                    )
                    
                    if usd_result:
                        logger.info(f"Updated USD to {currency_code} rate: 1 USD = {usd_rate} {currency_code}")
                        rates_added += 1
                    
                    # Update NVCT to currency rate (1:1 with USD)
                    nvct_result = CurrencyExchangeService.update_exchange_rate(
                        CurrencyType.NVCT,
                        currency_enum,
                        usd_rate,
                        "system_global_rates"
                    )
                    
                    if nvct_result:
                        logger.info(f"Updated NVCT to {currency_code} rate: 1 NVCT = {usd_rate} {currency_code}")
                        rates_added += 1
                        
                except Exception as e:
                    logger.error(f"Error processing {currency_code}: {str(e)}")
            
            logger.info(f"Successfully added {rates_added} exchange rates for global currencies")
            return True
        except Exception as e:
            logger.error(f"Error initializing global currency exchange rates: {str(e)}")
            return False

if __name__ == "__main__":
    initialize_global_rates()