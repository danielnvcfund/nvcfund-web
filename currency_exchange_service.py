"""
Currency Exchange Service

This module provides functions to handle currency exchange rates and conversions 
for use in the Treasury transaction system and other parts of the application.
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List, Any, Union

from flask import current_app
from sqlalchemy import or_, func, desc

from app import db
from account_holder_models import CurrencyExchangeRate, CurrencyType

logger = logging.getLogger(__name__)

# Path to static currency rates file (for fallback)
RATES_FILE = 'currency_rates.json'

def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """
    Get the exchange rate between two currencies.
    
    Args:
        from_currency: Source currency code
        to_currency: Target currency code
        
    Returns:
        float: The exchange rate (from_currency to to_currency)
    """
    # If currencies are the same, rate is 1.0
    if from_currency == to_currency:
        return 1.0
    
    # Try to get rate from database
    try:
        rate = CurrencyExchangeRate.query.filter(
            CurrencyExchangeRate.from_currency == from_currency,
            CurrencyExchangeRate.to_currency == to_currency,
            CurrencyExchangeRate.is_active == True
        ).order_by(desc(CurrencyExchangeRate.last_updated)).first()
        
        if rate:
            return rate.rate
            
        # Try inverse rate if direct rate not found
        inverse_rate = CurrencyExchangeRate.query.filter(
            CurrencyExchangeRate.from_currency == to_currency,
            CurrencyExchangeRate.to_currency == from_currency,
            CurrencyExchangeRate.is_active == True
        ).order_by(desc(CurrencyExchangeRate.last_updated)).first()
        
        if inverse_rate and inverse_rate.inverse_rate:
            return inverse_rate.inverse_rate
    except Exception as e:
        logger.warning(f"Error accessing database for exchange rates: {str(e)}")
    
    # Fall back to static rates file if database lookup failed
    return get_static_exchange_rate(from_currency, to_currency)

def get_static_exchange_rate(from_currency: str, to_currency: str) -> float:
    """
    Get exchange rate from static file (fallback method).
    
    Args:
        from_currency: Source currency code
        to_currency: Target currency code
        
    Returns:
        float: The exchange rate (from_currency to to_currency)
    """
    try:
        # Load rates from file
        if os.path.exists(RATES_FILE):
            with open(RATES_FILE, 'r') as f:
                rates = json.load(f)
            
            # Try to get direct rate
            rate_key = f"{from_currency}_{to_currency}"
            if rate_key in rates:
                return float(rates[rate_key])
            
            # Try to calculate via USD if direct rate not available
            usd_from_key = f"{from_currency}_USD"
            usd_to_key = f"USD_{to_currency}"
            
            if usd_from_key in rates and usd_to_key in rates:
                # Convert from currency to USD, then USD to target currency
                return float(1.0 / rates[usd_from_key]) * float(rates[usd_to_key])
            
            # Try inverse rate
            inverse_key = f"{to_currency}_{from_currency}"
            if inverse_key in rates:
                return 1.0 / float(rates[inverse_key])
        
        # For special tokens we have hardcoded rates
        if from_currency == "NVCT" and to_currency == "USD":
            return 10.0  # 1 NVCT = $10 USD
        elif from_currency == "USD" and to_currency == "NVCT":
            return 0.1   # $1 USD = 0.1 NVCT
        elif from_currency == "AFD1" and to_currency == "USD":
            return 339.40  # 1 AFD1 = $339.40 USD (based on gold backing)
        elif from_currency == "USD" and to_currency == "AFD1":
            return 1.0 / 339.40
        elif from_currency == "SFN" and to_currency == "NVCT":
            return 1.0  # 1:1 ratio per system configuration
        elif from_currency == "NVCT" and to_currency == "SFN":
            return 1.0
        
        # Default conventional rates for common currencies
        conventional_rates = {
            "USD_EUR": 0.92,
            "EUR_USD": 1.09,
            "USD_GBP": 0.78,
            "GBP_USD": 1.28,
            "USD_JPY": 154.50,
            "JPY_USD": 0.0065,
            "USD_CAD": 1.36,
            "CAD_USD": 0.73,
            "USD_AUD": 1.51,
            "AUD_USD": 0.66,
            "USD_CNY": 7.23,
            "CNY_USD": 0.14,
            "USD_INR": 83.10,
            "INR_USD": 0.012,
            # African currencies
            "USD_NGN": 1385.0,
            "NGN_USD": 0.00072,
            "USD_ZAR": 18.40,
            "ZAR_USD": 0.054,
            "USD_EGP": 47.15,
            "EGP_USD": 0.021,
            # Specialized tokens
            "AKLUMI_USD": 100.0,
            "USD_AKLUMI": 0.01
        }
        
        rate_key = f"{from_currency}_{to_currency}"
        if rate_key in conventional_rates:
            return conventional_rates[rate_key]
        
        inverse_key = f"{to_currency}_{from_currency}"
        if inverse_key in conventional_rates:
            return 1.0 / conventional_rates[inverse_key]
            
    except Exception as e:
        logger.error(f"Error loading static exchange rates: {str(e)}")
    
    # Default fallback rate is 1.0
    logger.warning(f"No exchange rate found for {from_currency} to {to_currency}, using default 1.0")
    return 1.0

def convert_amount(amount: float, from_currency: str, to_currency: str) -> float:
    """
    Convert an amount from one currency to another.
    
    Args:
        amount: The amount to convert
        from_currency: Source currency code
        to_currency: Target currency code
        
    Returns:
        float: The converted amount in the target currency
    """
    if from_currency == to_currency:
        return amount
        
    rate = get_exchange_rate(from_currency, to_currency)
    return amount * rate

def get_all_currency_rates(base_currency: str = "USD") -> Dict[str, float]:
    """
    Get all available exchange rates for a base currency.
    
    Args:
        base_currency: The base currency to get rates for
        
    Returns:
        Dict[str, float]: Dictionary of currency codes to exchange rates
    """
    rates = {}
    
    # Add all rates from the database
    try:
        db_rates = CurrencyExchangeRate.query.filter(
            CurrencyExchangeRate.from_currency == base_currency,
            CurrencyExchangeRate.is_active == True
        ).all()
        
        for rate in db_rates:
            rates[rate.to_currency.name] = rate.rate
            
        # Add inverse rates
        inverse_rates = CurrencyExchangeRate.query.filter(
            CurrencyExchangeRate.to_currency == base_currency,
            CurrencyExchangeRate.is_active == True
        ).all()
        
        for rate in inverse_rates:
            if rate.from_currency.name not in rates and rate.inverse_rate:
                rates[rate.from_currency.name] = rate.inverse_rate
    except Exception as e:
        logger.warning(f"Error accessing database for exchange rates: {str(e)}")
    
    # Fill in missing rates from static data
    for currency in [c.name for c in CurrencyType]:
        if currency not in rates and currency != base_currency:
            rates[currency] = get_static_exchange_rate(base_currency, currency)
    
    return rates