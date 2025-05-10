#!/usr/bin/env python3
"""
Update the database to include all African currency exchange rates
This script runs the migration using SQLAlchemy ORM
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

def add_exchange_rate(from_currency_str, to_currency_str, rate, source="system_african_rates"):
    """Add exchange rate directly to the database using SQLAlchemy ORM"""
    try:
        # Check if record already exists
        existing = db.session.query(CurrencyExchangeRate).filter_by(
            from_currency=from_currency_str,
            to_currency=to_currency_str
        ).first()
        
        if existing:
            # Update existing record
            existing.rate = rate
            existing.inverse_rate = 1.0 / rate if rate > 0 else 0
            existing.source = source
            existing.last_updated = db.func.now()
            existing.is_active = True
            logger.info(f"Updated rate: 1 {from_currency_str} = {rate} {to_currency_str}")
        else:
            # Create new record
            new_rate = CurrencyExchangeRate(
                from_currency=from_currency_str,
                to_currency=to_currency_str,
                rate=rate,
                inverse_rate=1.0 / rate if rate > 0 else 0,
                source=source,
                is_active=True
            )
            db.session.add(new_rate)
            logger.info(f"Added rate: 1 {from_currency_str} = {rate} {to_currency_str}")
        
        # Add inverse rate as well
        inverse_rate = 1.0 / rate if rate > 0 else 0
        existing_inverse = db.session.query(CurrencyExchangeRate).filter_by(
            from_currency=to_currency_str,
            to_currency=from_currency_str
        ).first()
        
        if existing_inverse:
            # Update existing inverse record
            existing_inverse.rate = inverse_rate
            existing_inverse.inverse_rate = rate
            existing_inverse.source = source
            existing_inverse.last_updated = db.func.now()
            existing_inverse.is_active = True
        else:
            # Create new inverse record
            new_inverse = CurrencyExchangeRate(
                from_currency=to_currency_str,
                to_currency=from_currency_str,
                rate=inverse_rate,
                inverse_rate=rate,
                source=source,
                is_active=True
            )
            db.session.add(new_inverse)
        
        return True
    except Exception as e:
        logger.error(f"Error adding exchange rate {from_currency_str} to {to_currency_str}: {str(e)}")
        return False

def migrate_currencies():
    """Run the migration to add African currency exchange rates"""
    logger.info("Starting migration for African currency exchange rates...")
    
    with app.app_context():
        try:
            # Process each African currency
            rates_added = 0
            for currency_code, usd_rate in AFRICAN_CURRENCY_RATES.items():
                try:
                    # Add USD to African currency rate
                    if add_exchange_rate('USD', currency_code, usd_rate):
                        rates_added += 1
                    
                    # Add NVCT to African currency rate (1:1 with USD)
                    nvct_rate = usd_rate  # NVCT has 1:1 peg with USD
                    if add_exchange_rate('NVCT', currency_code, nvct_rate):
                        rates_added += 1
                except Exception as e:
                    logger.error(f"Error processing {currency_code}: {str(e)}")
            
            # Commit all changes
            db.session.commit()
            logger.info(f"Successfully added {rates_added} exchange rates for African currencies")
            
            # Verify some key rates
            key_currencies = ['NGN', 'ZAR', 'KES', 'EGP', 'GHS']
            for currency in key_currencies:
                rate = db.session.query(CurrencyExchangeRate).filter_by(
                    from_currency='USD',
                    to_currency=currency
                ).first()
                
                if rate:
                    logger.info(f"Verified: 1 USD = {rate.rate} {currency}")
                else:
                    logger.warning(f"Rate not found: USD to {currency}")
            
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in migration: {str(e)}")
            return False

if __name__ == "__main__":
    migrate_currencies()