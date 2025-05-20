"""
Simplified Exchange System for NVC Banking Platform

This module provides a streamlined currency exchange system with NVCT as the central currency,
paired with major fiat and digital currencies at fixed exchange rates.
"""
from datetime import datetime
from account_holder_models import CurrencyType, CurrencyExchangeRate
from app import db, logger

# Define the base exchange rates for NVCT to major currencies
NVCT_EXCHANGE_RATES = {
    # Fiat currencies
    CurrencyType.USD: 1.0,      # NVCT 1:1 with USD
    CurrencyType.EUR: 0.89,     # NVCT to EUR
    CurrencyType.GBP: 0.75,     # NVCT to GBP
    CurrencyType.NGN: 1550.0,   # NVCT to Nigerian Naira
    
    # Digital currencies
    CurrencyType.BTC: 0.000017, # NVCT to BTC
    CurrencyType.ETH: 0.00033,  # NVCT to ETH
    CurrencyType.USDT: 1.0,     # NVCT to USDT
    
    # Partner currencies
    CurrencyType.AFD1: 339.40,  # NVCT to AFD1
    CurrencyType.SFN: 10.0,     # NVCT to SFN
    CurrencyType.AKLUMI: 100.0  # NVCT to AKLUMI
}

def initialize_simplified_exchange_rates():
    """
    Initialize or update the simplified exchange rates in the database.
    NVCT is used as the central currency and all rates are defined relative to it.
    """
    try:
        current_time = datetime.utcnow()
        count = 0
        
        # Set NVCT as the base currency and define exchange rates to other currencies
        for to_currency, rate in NVCT_EXCHANGE_RATES.items():
            # Skip if to_currency is NVCT itself
            if to_currency == CurrencyType.NVCT:
                continue
                
            # Calculate inverse rate (to convert back to NVCT)
            inverse_rate = 1.0 / rate if rate > 0 else 0.0
            
            # Check if rate exists and update it, or create new rate
            existing_rate = CurrencyExchangeRate.query.filter_by(
                from_currency=CurrencyType.NVCT,
                to_currency=to_currency
            ).first()
            
            if existing_rate:
                existing_rate.rate = rate
                existing_rate.inverse_rate = inverse_rate
                existing_rate.last_updated = current_time
                existing_rate.source = 'simplified_system'
            else:
                new_rate = CurrencyExchangeRate(
                    from_currency=CurrencyType.NVCT,
                    to_currency=to_currency,
                    rate=rate,
                    inverse_rate=inverse_rate,
                    last_updated=current_time,
                    source='simplified_system',
                    is_active=True
                )
                db.session.add(new_rate)
            
            # Also add the inverse rate (to convert back to NVCT)
            inverse_existing_rate = CurrencyExchangeRate.query.filter_by(
                from_currency=to_currency,
                to_currency=CurrencyType.NVCT
            ).first()
            
            if inverse_existing_rate:
                inverse_existing_rate.rate = inverse_rate
                inverse_existing_rate.inverse_rate = rate
                inverse_existing_rate.last_updated = current_time
                inverse_existing_rate.source = 'simplified_system'
            else:
                inverse_new_rate = CurrencyExchangeRate(
                    from_currency=to_currency,
                    to_currency=CurrencyType.NVCT,
                    rate=inverse_rate,
                    inverse_rate=rate,
                    last_updated=current_time,
                    source='simplified_system',
                    is_active=True
                )
                db.session.add(inverse_new_rate)
                
            count += 2  # Count both the direct and inverse rates
        
        db.session.commit()
        logger.info(f"Simplified exchange system initialized with {count} rates")
        return True
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error initializing simplified exchange rates: {str(e)}")
        return False

def get_exchange_rate(from_currency, to_currency):
    """
    Get the exchange rate between two currencies.
    If direct rate is not available, attempt to calculate via NVCT as intermediary.
    
    Args:
        from_currency: Source currency (CurrencyType enum)
        to_currency: Target currency (CurrencyType enum)
        
    Returns:
        Float exchange rate or None if not available
    """
    # If currencies are the same, return 1:1 rate
    if from_currency == to_currency:
        return 1.0
        
    # Try to get direct rate
    direct_rate = CurrencyExchangeRate.query.filter_by(
        from_currency=from_currency,
        to_currency=to_currency,
        is_active=True
    ).first()
    
    if direct_rate:
        return direct_rate.rate
        
    # If direct rate not available, try to get via NVCT
    if from_currency != CurrencyType.NVCT and to_currency != CurrencyType.NVCT:
        # Get rate from source to NVCT
        to_nvct_rate = CurrencyExchangeRate.query.filter_by(
            from_currency=from_currency,
            to_currency=CurrencyType.NVCT,
            is_active=True
        ).first()
        
        # Get rate from NVCT to target
        from_nvct_rate = CurrencyExchangeRate.query.filter_by(
            from_currency=CurrencyType.NVCT,
            to_currency=to_currency,
            is_active=True
        ).first()
        
        if to_nvct_rate and from_nvct_rate:
            # Calculate cross rate
            return to_nvct_rate.rate * from_nvct_rate.rate
    
    # If we couldn't find or calculate a rate, return None
    return None

def calculate_exchange_amount(from_currency, to_currency, amount):
    """
    Calculate the exchange amount between two currencies.
    
    Args:
        from_currency: Source currency (CurrencyType enum)
        to_currency: Target currency (CurrencyType enum)
        amount: Amount to exchange (float)
        
    Returns:
        Tuple of (converted_amount, rate_applied) or (None, None) if exchange not possible
    """
    rate = get_exchange_rate(from_currency, to_currency)
    
    if rate is not None:
        converted_amount = amount * rate
        return (converted_amount, rate)
    
    return (None, None)