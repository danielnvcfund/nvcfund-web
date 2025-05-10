#!/usr/bin/env python3
"""
Currency Exchange Service Workaround
This script provides compatibility for all currencies without modifying the database schema.
"""

import logging
import json
import os
from datetime import datetime
from app import app, db
from account_holder_models import CurrencyType, CurrencyExchangeRate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store exchange rates in memory for currencies not in the database
global_exchange_rates = {}

# Exchange rates for world currencies to USD (as of May 2025)
# These will be used when database lookup fails
DEFAULT_WORLD_CURRENCY_RATES = {
    # Major world currencies
    "USD": 1.0,       # US Dollar (base)
    "EUR": 0.93,      # Euro
    "GBP": 0.79,      # British Pound
    "JPY": 157.32,    # Japanese Yen
    "CHF": 0.92,      # Swiss Franc
    "CAD": 1.36,      # Canadian Dollar
    "AUD": 1.51,      # Australian Dollar
    "NZD": 1.65,      # New Zealand Dollar
    "CNY": 7.24,      # Chinese Yuan Renminbi
    "HKD": 7.82,      # Hong Kong Dollar
    "SGD": 1.35,      # Singapore Dollar
    "INR": 83.42,     # Indian Rupee
    "RUB": 91.75,     # Russian Ruble
    "BRL": 5.14,      # Brazilian Real
    "MXN": 16.78,     # Mexican Peso
    "SEK": 10.54,     # Swedish Krona
    "NOK": 10.81,     # Norwegian Krone
    "DKK": 6.93,      # Danish Krone
    "PLN": 3.98,      # Polish Zloty
    "TRY": 32.15,     # Turkish Lira
    
    # African Currencies
    "NGN": 1500.00,   # Nigerian Naira
    "DZD": 134.82,    # Algerian Dinar
    "EGP": 47.25,     # Egyptian Pound
    "LYD": 4.81,      # Libyan Dinar
    "MAD": 9.98,      # Moroccan Dirham
    "SDG": 599.53,    # Sudanese Pound
    "TND": 3.11,      # Tunisian Dinar
    "GHS": 15.34,     # Ghanaian Cedi
    "XOF": 601.25,    # CFA Franc BCEAO
    "GMD": 67.50,     # Gambian Dalasi
    "GNF": 8625.00,   # Guinean Franc
    "LRD": 190.75,    # Liberian Dollar
    "SLL": 19875.00,  # Sierra Leonean Leone
    "SLE": 19.88,     # Sierra Leonean Leone (new)
    "CVE": 101.50,    # Cape Verdean Escudo
    "XAF": 601.25,    # CFA Franc BEAC
    "CDF": 2650.00,   # Congolese Franc
    "STN": 22.65,     # São Tomé and Príncipe Dobra
    "KES": 132.05,    # Kenyan Shilling
    "ETB": 56.93,     # Ethiopian Birr
    "UGX": 3785.00,   # Ugandan Shilling
    "TZS": 2575.00,   # Tanzanian Shilling
    "RWF": 1250.00,   # Rwandan Franc
    "BIF": 2875.00,   # Burundian Franc
    "DJF": 178.50,    # Djiboutian Franc
    "ERN": 15.00,     # Eritrean Nakfa
    "SSP": 985.00,    # South Sudanese Pound
    "SOS": 570.00,    # Somali Shilling
    "ZAR": 18.50,     # South African Rand
    "LSL": 18.50,     # Lesotho Loti
    "NAD": 18.50,     # Namibian Dollar
    "SZL": 18.50,     # Swazi Lilangeni
    "BWP": 13.68,     # Botswana Pula
    "ZMW": 26.42,     # Zambian Kwacha
    "MWK": 1675.00,   # Malawian Kwacha
    "ZWL": 9825.00,   # Zimbabwean Dollar
    "MZN": 63.86,     # Mozambican Metical
    "MGA": 4450.00,   # Malagasy Ariary
    "SCR": 14.15,     # Seychellois Rupee
    "MUR": 45.75,     # Mauritian Rupee
    "AOA": 850.00,    # Angolan Kwanza
    
    # Asia Pacific
    "IDR": 15675.00,  # Indonesian Rupiah
    "MYR": 4.65,      # Malaysian Ringgit
    "PHP": 56.75,     # Philippine Peso
    "THB": 35.68,     # Thai Baht
    "VND": 24650.00,  # Vietnamese Dong
    "KRW": 1345.00,   # South Korean Won
    "TWD": 31.85,     # Taiwan New Dollar
    "PKR": 278.50,    # Pakistani Rupee
    "BDT": 110.25,    # Bangladeshi Taka
    "NPR": 133.45,    # Nepalese Rupee
    "LKR": 312.65,    # Sri Lankan Rupee
    
    # Middle East
    "AED": 3.67,      # UAE Dirham
    "SAR": 3.75,      # Saudi Riyal
    "QAR": 3.64,      # Qatari Riyal
    "OMR": 0.385,     # Omani Rial
    "BHD": 0.376,     # Bahraini Dinar
    "KWD": 0.307,     # Kuwaiti Dinar
    "ILS": 3.65,      # Israeli New Shekel
    "JOD": 0.709,     # Jordanian Dinar
    "LBP": 15000.00,  # Lebanese Pound
    "IRR": 42000.00,  # Iranian Rial
    "IQD": 1310.00,   # Iraqi Dinar
    
    # Latin America & Caribbean
    "ARS": 875.00,    # Argentine Peso
    "CLP": 945.00,    # Chilean Peso
    "COP": 3950.00,   # Colombian Peso
    "PEN": 3.75,      # Peruvian Sol
    "UYU": 39.25,     # Uruguayan Peso
    "VES": 36.50,     # Venezuelan Bolivar Soberano
    "BOB": 6.91,      # Bolivian Boliviano
    "PYG": 7325.00,   # Paraguayan Guarani
    "DOP": 58.75,     # Dominican Peso
    "CRC": 515.00,    # Costa Rican Colon
    "JMD": 155.75,    # Jamaican Dollar
    "TTD": 6.80,      # Trinidad and Tobago Dollar
    
    # Eastern Europe
    "CZK": 23.15,     # Czech Koruna
    "HUF": 356.00,    # Hungarian Forint
    "RON": 4.63,      # Romanian Leu
    "BGN": 1.81,      # Bulgarian Lev
    "HRK": 7.53,      # Croatian Kuna
    "RSD": 109.50,    # Serbian Dinar
    "UAH": 39.85,     # Ukrainian Hryvnia
    "BYN": 3.25,      # Belarusian Ruble
    
    # NVC Tokens and partner currencies
    "NVCT": 1.00,     # NVC Token (1:1 with USD)
    "SPU": 1000.00,   # Special Purpose Unit
    "TU": 10.00,      # Treasury Unit
    "AFD1": 339.40,   # American Federation Dollar (10% of gold price)
    "SFN": 1.00,      # SFN Coin (1:1 with NVCT)
    "AKLUMI": 3.25,   # Ak Lumi currency
    
    # Cryptocurrencies
    "BTC": 0.0000161, # Bitcoin (rate for 1 USD in BTC)
    "ETH": 0.000333,  # Ethereum (rate for 1 USD in ETH)
    "USDT": 1.00,     # Tether
    "USDC": 1.00,     # USD Coin
    "BNB": 0.00163,   # Binance Coin
    "SOL": 0.0074,    # Solana
    "XRP": 1.92,      # XRP (Ripple)
    "ADA": 2.22,      # Cardano
    "AVAX": 0.0286,   # Avalanche
    "DOGE": 6.67,     # Dogecoin
    "DOT": 0.124,     # Polkadot
    "MATIC": 0.625,   # Polygon
    "LTC": 0.0125,    # Litecoin
    "SHIB": 25000.0,  # Shiba Inu
    "DAI": 1.00,      # Dai
    "TRX": 7.69,      # TRON
    "UNI": 0.111,     # Uniswap
    "LINK": 0.0833,   # Chainlink
    "ATOM": 0.0769,   # Cosmos
    "XMR": 0.00323,   # Monero
    "ETC": 0.0333,    # Ethereum Classic
    "FIL": 0.0345,    # Filecoin
    "XLM": 3.85,      # Stellar
    "NEAR": 0.25,     # NEAR Protocol
    "ALGO": 1.75,     # Algorand
    "ZCASH": 0.00323, # Zcash
    "APE": 0.3125,    # ApeCoin
    "ICP": 0.0357,    # Internet Computer
    "FLOW": 0.2,      # Flow
    "VET": 4.0,       # VeChain
}

def load_exchange_rates():
    """Load exchange rates from memory or file"""
    global global_exchange_rates
    
    rates_file = "currency_rates.json"
    
    # Try to load from file
    if os.path.exists(rates_file):
        try:
            with open(rates_file, 'r') as f:
                global_exchange_rates = json.load(f)
                logger.info(f"Loaded {len(global_exchange_rates)} exchange rate pairs from file")
        except Exception as e:
            logger.error(f"Error loading rates from file: {str(e)}")
            global_exchange_rates = {}
    
    # If we couldn't load or no file exists, initialize with default rates
    if not global_exchange_rates:
        logger.info("Initializing exchange rates with default values")
        
        # Fill in our in-memory exchange rate table with USD rates
        for currency_code, usd_rate in DEFAULT_WORLD_CURRENCY_RATES.items():
            if currency_code != "USD":
                # USD to currency
                global_exchange_rates[f"USD_{currency_code}"] = usd_rate
                
                # Currency to USD (inverse rate)
                global_exchange_rates[f"{currency_code}_USD"] = 1.0 / usd_rate if usd_rate != 0 else 0
                
                # NVCT to currency (same as USD since NVCT pegged to USD 1:1)
                global_exchange_rates[f"NVCT_{currency_code}"] = usd_rate
                
                # Currency to NVCT (inverse rate)
                global_exchange_rates[f"{currency_code}_NVCT"] = 1.0 / usd_rate if usd_rate != 0 else 0
        
        # Add a few basic cross-rates for commonly used currency pairs
        cross_pairs = [
            ("EUR", "GBP", 0.85),  # EUR to GBP
            ("GBP", "EUR", 1.176), # GBP to EUR
            ("EUR", "JPY", 169.0), # EUR to JPY
            ("GBP", "JPY", 199.0), # GBP to JPY
        ]
        
        for from_currency, to_currency, rate in cross_pairs:
            global_exchange_rates[f"{from_currency}_{to_currency}"] = rate
            global_exchange_rates[f"{to_currency}_{from_currency}"] = 1.0 / rate if rate != 0 else 0
        
        logger.info(f"Initialized {len(global_exchange_rates)} exchange rate pairs")
        
        # Save to file for future use
        try:
            with open(rates_file, 'w') as f:
                json.dump(global_exchange_rates, f, indent=2)
                logger.info(f"Saved exchange rates to {rates_file}")
        except Exception as e:
            logger.error(f"Error saving rates to file: {str(e)}")

def get_exchange_rate(from_currency_str, to_currency_str):
    """Get exchange rate from database or memory if not in database"""
    try:
        with app.app_context():
            # Try to get the enum values (will fail for currencies not in DB schema)
            try:
                from_currency = getattr(CurrencyType, from_currency_str)
                to_currency = getattr(CurrencyType, to_currency_str)
                
                # Currency type exists in enum, try to get from database
                existing_rate = db.session.query(CurrencyExchangeRate).filter_by(
                    from_currency=from_currency,
                    to_currency=to_currency
                ).first()
                
                if existing_rate and existing_rate.is_active:
                    return existing_rate.rate
            except (AttributeError, ValueError) as e:
                logger.debug(f"Currency enum lookup failed: {str(e)}")
            
            # If we get here, either the currency is not in the enum or not in the database
            # Use our in-memory rate table
            rate_key = f"{from_currency_str}_{to_currency_str}"
            if rate_key in global_exchange_rates:
                return global_exchange_rates[rate_key]
            
            # If direct rate not found, try calculating via USD
            if from_currency_str != "USD" and to_currency_str != "USD":
                # Try from -> USD -> to
                from_to_usd_key = f"{from_currency_str}_USD"
                usd_to_to_key = f"USD_{to_currency_str}"
                
                if from_to_usd_key in global_exchange_rates and usd_to_to_key in global_exchange_rates:
                    from_to_usd = global_exchange_rates[from_to_usd_key]
                    usd_to_to = global_exchange_rates[usd_to_to_key]
                    calculated_rate = from_to_usd * usd_to_to
                    
                    # Cache this calculated rate for future use
                    global_exchange_rates[rate_key] = calculated_rate
                    return calculated_rate
            
            # If all else fails, return a default rate of 1:1
            logger.warning(f"No exchange rate found for {from_currency_str} to {to_currency_str}, using default 1:1")
            return 1.0
            
    except Exception as e:
        logger.error(f"Error getting exchange rate {from_currency_str} to {to_currency_str}: {str(e)}")
        return 1.0  # Default to 1:1 in case of errors

def calculate_exchange(from_currency_str, to_currency_str, amount):
    """Calculate currency exchange amount"""
    rate = get_exchange_rate(from_currency_str, to_currency_str)
    return amount * rate

def convert_all_currencies():
    """Test conversion between all currencies"""
    all_currencies = list(DEFAULT_WORLD_CURRENCY_RATES.keys())
    
    print(f"Testing conversions between {len(all_currencies)} currencies:")
    for from_curr in ["USD", "NVCT", "EUR", "BTC", "NGN", "AFD1", "SFN"]:
        print(f"\nFrom {from_curr}:")
        for to_curr in ["USD", "NVCT", "EUR", "BTC", "NGN", "AFD1", "SFN"]:
            if from_curr != to_curr:
                rate = get_exchange_rate(from_curr, to_curr)
                print(f"  1 {from_curr} = {rate:.6f} {to_curr}")

# Initialize the exchange rates when module is imported
load_exchange_rates()

if __name__ == "__main__":
    # When run directly, test the currency conversions
    convert_all_currencies()