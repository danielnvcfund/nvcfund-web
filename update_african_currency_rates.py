#!/usr/bin/env python3
"""
Update African Currency Exchange Rates
This script initializes exchange rates for all African currencies with NVCT as the primary pair
"""

import logging
from app import app, db
from currency_exchange_service import CurrencyExchangeService
from account_holder_models import CurrencyExchangeRate, CurrencyType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Exchange rates for African currencies to USD (as of May 2025)
# These rates would ideally come from a reliable financial data API
AFRICAN_CURRENCY_RATES = {
    # North Africa
    "DZD": 134.82,      # Algerian Dinar
    "EGP": 47.25,       # Egyptian Pound
    "LYD": 4.81,        # Libyan Dinar
    "MAD": 9.98,        # Moroccan Dirham
    "SDG": 599.53,      # Sudanese Pound
    "TND": 3.11,        # Tunisian Dinar
    
    # West Africa
    "NGN": 1500.00,     # Nigerian Naira
    "GHS": 15.34,       # Ghanaian Cedi
    "XOF": 601.04,      # CFA Franc BCEAO
    "GMD": 67.50,       # Gambian Dalasi
    "GNF": 8612.43,     # Guinean Franc
    "LRD": 187.10,      # Liberian Dollar
    "SLL": 19842.65,    # Sierra Leonean Leone
    "SLE": 19.84,       # Sierra Leonean Leone (new)
    "CVE": 101.32,      # Cape Verdean Escudo
    
    # Central Africa
    "XAF": 601.04,      # CFA Franc BEAC
    "CDF": 2664.51,     # Congolese Franc
    "STN": 22.55,       # São Tomé and Príncipe Dobra
    
    # East Africa
    "KES": 132.05,      # Kenyan Shilling
    "ETB": 56.93,       # Ethiopian Birr
    "UGX": 3750.52,     # Ugandan Shilling
    "TZS": 2605.43,     # Tanzanian Shilling
    "RWF": 1276.83,     # Rwandan Franc
    "BIF": 2862.42,     # Burundian Franc
    "DJF": 178.03,      # Djiboutian Franc
    "ERN": 15.00,       # Eritrean Nakfa
    "SSP": 982.43,      # South Sudanese Pound
    "SOS": 571.82,      # Somali Shilling
    
    # Southern Africa
    "ZAR": 18.50,       # South African Rand
    "LSL": 18.50,       # Lesotho Loti
    "NAD": 18.50,       # Namibian Dollar
    "SZL": 18.50,       # Swazi Lilangeni
    "BWP": 13.68,       # Botswana Pula
    "ZMW": 26.42,       # Zambian Kwacha
    "MWK": 1682.31,     # Malawian Kwacha
    "ZWL": 5621.32,     # Zimbabwean Dollar
    "MZN": 63.86,       # Mozambican Metical
    "MGA": 4378.24,     # Malagasy Ariary
    "SCR": 14.38,       # Seychellois Rupee
    "MUR": 46.25,       # Mauritian Rupee
    "AOA": 832.25,      # Angolan Kwanza
}

def update_african_currency_rates():
    """Initialize or update exchange rates for all African currencies"""
    logger.info("Updating exchange rates for African currencies...")
    
    with app.app_context():
        try:
            # Get all African currency codes from the dictionary
            african_currencies = list(AFRICAN_CURRENCY_RATES.keys())
            
            # Initialize a counter for successful updates
            successful_updates = 0
            
            # Process each African currency
            for currency_code in african_currencies:
                try:
                    # Get the enum value for this currency
                    currency_enum = getattr(CurrencyType, currency_code)
                    
                    # Get the exchange rate (X units of currency per 1 USD)
                    usd_rate = AFRICAN_CURRENCY_RATES[currency_code]
                    
                    # Update USD to African currency rate
                    usd_to_currency = CurrencyExchangeService.update_exchange_rate(
                        CurrencyType.USD,
                        currency_enum,
                        usd_rate,
                        "system_african_rates"
                    )
                    
                    if usd_to_currency:
                        logger.info(f"Updated USD to {currency_code}: 1 USD = {usd_rate} {currency_code}")
                        successful_updates += 1
                    
                    # Update NVCT to African currency rate (1:1 with USD)
                    nvct_rate = usd_rate  # NVCT has 1:1 peg with USD
                    nvct_to_currency = CurrencyExchangeService.update_exchange_rate(
                        CurrencyType.NVCT,
                        currency_enum,
                        nvct_rate,
                        "system_african_rates"
                    )
                    
                    if nvct_to_currency:
                        logger.info(f"Updated NVCT to {currency_code}: 1 NVCT = {nvct_rate} {currency_code}")
                        successful_updates += 1
                        
                except AttributeError:
                    logger.error(f"Currency code {currency_code} not found in CurrencyType enum")
                except Exception as e:
                    logger.error(f"Error updating rates for {currency_code}: {str(e)}")
            
            logger.info(f"Successfully updated {successful_updates} exchange rates for African currencies")
            
            # Display a summary of all current African currency rates
            try:
                rates = CurrencyExchangeRate.query.filter(
                    (CurrencyExchangeRate.from_currency == CurrencyType.NVCT) &
                    (CurrencyExchangeRate.to_currency.in_([getattr(CurrencyType, code) for code in african_currencies]))
                ).all()
                
                logger.info(f"Summary of NVCT to African currency rates:")
                for rate in rates:
                    logger.info(f"1 NVCT = {rate.rate} {rate.to_currency.value}")
            except Exception as e:
                logger.error(f"Error displaying rate summary: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating African currency exchange rates: {str(e)}")
            return False

if __name__ == "__main__":
    update_african_currency_rates()