"""
Currency Exchange Service for NVC Banking Platform
This module provides a service for currency exchange operations between various currencies.
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from account_holder_models import CurrencyType, ExchangeType, ExchangeStatus, CurrencyExchangeRate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CurrencyExchangeService:
    """Service for handling currency exchange operations"""
    
    def __init__(self, db=None):
        """Initialize the currency exchange service"""
        self.db = db
        self.rates_cache = {}
        self.rates_timestamp = {}
        self.load_fallback_rates()
    
    def load_fallback_rates(self) -> None:
        """Load fallback exchange rates from a local JSON file"""
        try:
            with open('currency_rates.json', 'r') as f:
                self.fallback_rates = json.load(f)
                logger.info(f"Loaded {len(self.fallback_rates)} fallback currency rates")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading fallback rates: {str(e)}")
            self.fallback_rates = {}
    
    def get_rate_key(self, from_currency: CurrencyType, to_currency: CurrencyType) -> str:
        """Create a key for the rates cache"""
        return f"{from_currency.value}_{to_currency.value}"
    
    def get_exchange_rate(self, from_currency: CurrencyType, to_currency: CurrencyType) -> float:
        """
        Get the exchange rate between two currencies.
        First checks the database, then external APIs, then fallback rates.
        """
        # If same currency, rate is 1
        if from_currency == to_currency:
            return 1.0
        
        # Try to get from database if available
        if self.db:
            try:
                rate = CurrencyExchangeRate.query.filter_by(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    is_active=True
                ).order_by(CurrencyExchangeRate.last_updated.desc()).first()
                
                if rate:
                    logger.info(f"Found exchange rate in database: {from_currency.value} -> {to_currency.value} = {rate.rate}")
                    return rate.rate
            except Exception as e:
                logger.error(f"Error getting rate from database: {str(e)}")
        
        # Check if we have a recent cached rate
        rate_key = self.get_rate_key(from_currency, to_currency)
        cache_timestamp = self.rates_timestamp.get(rate_key)
        
        if cache_timestamp and (datetime.now() - cache_timestamp).total_seconds() < 3600:  # Cache for 1 hour
            return self.rates_cache.get(rate_key, 1.0)
        
        # Otherwise, try external API
        rate = self._fetch_external_rate(from_currency, to_currency)
        if rate:
            # Store in cache
            self.rates_cache[rate_key] = rate
            self.rates_timestamp[rate_key] = datetime.now()
            
            # Store in database if available
            if self.db:
                self._store_rate_in_db(from_currency, to_currency, rate)
            
            return rate
        
        # Fallback to stored rates
        return self._get_fallback_rate(from_currency, to_currency)
    
    def _fetch_external_rate(self, from_currency: CurrencyType, to_currency: CurrencyType) -> Optional[float]:
        """Fetch exchange rate from external API"""
        # Skip for non-standard currencies that likely won't be in public APIs
        non_standard_currencies = ["NVCT", "AFD1", "SPU", "TU", "SFN", "AKLUMI"]
        if from_currency.value in non_standard_currencies or to_currency.value in non_standard_currencies:
            return None
        
        try:
            # Example using free exchange rate API - replace with your preferred provider
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.value}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if "rates" in data and to_currency.value in data["rates"]:
                    rate = data["rates"][to_currency.value]
                    logger.info(f"Fetched external rate: {from_currency.value} -> {to_currency.value} = {rate}")
                    return rate
            
            logger.warning(f"Failed to fetch external rate for {from_currency.value} -> {to_currency.value}")
            return None
        
        except Exception as e:
            logger.error(f"Error fetching external rate: {str(e)}")
            return None
    
    def _store_rate_in_db(self, from_currency: CurrencyType, to_currency: CurrencyType, rate: float) -> None:
        """Store exchange rate in database"""
        try:
            # Calculate inverse rate
            inverse_rate = 1 / rate if rate != 0 else 0
            
            # Create new exchange rate record
            exchange_rate = CurrencyExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                inverse_rate=inverse_rate,
                source="external_api",
                is_active=True
            )
            
            self.db.session.add(exchange_rate)
            self.db.session.commit()
            logger.info(f"Stored rate in database: {from_currency.value} -> {to_currency.value} = {rate}")
        
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error storing rate in database: {str(e)}")
    
    def _get_fallback_rate(self, from_currency: CurrencyType, to_currency: CurrencyType) -> float:
        """Get fallback exchange rate from local storage"""
        rate_key = self.get_rate_key(from_currency, to_currency)
        
        if rate_key in self.fallback_rates:
            logger.info(f"Using fallback rate: {from_currency.value} -> {to_currency.value} = {self.fallback_rates[rate_key]}")
            return self.fallback_rates[rate_key]
        
        # Try inverse conversion
        inverse_key = self.get_rate_key(to_currency, from_currency)
        if inverse_key in self.fallback_rates:
            inverse_rate = self.fallback_rates[inverse_key]
            if inverse_rate != 0:
                calculated_rate = 1 / inverse_rate
                logger.info(f"Using calculated inverse fallback rate: {from_currency.value} -> {to_currency.value} = {calculated_rate}")
                return calculated_rate
        
        # If all else fails, return 1.0 as default
        logger.warning(f"No rate found for {from_currency.value} -> {to_currency.value}, using default (1.0)")
        return 1.0
    
    def convert_amount(self, amount: float, from_currency: CurrencyType, to_currency: CurrencyType) -> float:
        """Convert an amount from one currency to another"""
        if from_currency == to_currency:
            return amount
        
        rate = self.get_exchange_rate(from_currency, to_currency)
        converted_amount = amount * rate
        logger.info(f"Converted {amount} {from_currency.value} to {converted_amount} {to_currency.value} at rate {rate}")
        return converted_amount
    
    def calculate_fee(self, amount: float, currency: CurrencyType, fee_percentage: float = 0.5) -> float:
        """Calculate fee for currency exchange based on percentage"""
        fee = amount * (fee_percentage / 100)
        logger.info(f"Calculated fee: {fee} {currency.value} ({fee_percentage}% of {amount})")
        return fee
    
    def update_exchange_rates(self) -> int:
        """Update all exchange rates in the database from external sources"""
        if not self.db:
            logger.error("Database not available for updating exchange rates")
            return 0
        
        updated_count = 0
        currency_pairs = []
        
        # Generate pairs for major currencies
        major_currencies = [
            CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, 
            CurrencyType.JPY, CurrencyType.CHF, CurrencyType.CAD,
            CurrencyType.AUD, CurrencyType.CNY
        ]
        
        for base in major_currencies:
            for target in major_currencies:
                if base != target:
                    currency_pairs.append((base, target))
        
        # Add pairs for native tokens
        native_tokens = [
            CurrencyType.NVCT, CurrencyType.AFD1, CurrencyType.SFN, CurrencyType.AKLUMI
        ]
        
        for token in native_tokens:
            for currency in major_currencies:
                currency_pairs.append((token, currency))
                currency_pairs.append((currency, token))
        
        # Update each pair
        for from_currency, to_currency in currency_pairs:
            # Skip if using fallback for non-standard currencies
            if (from_currency.value in ["NVCT", "AFD1", "SPU", "TU", "SFN", "AKLUMI"] or 
                to_currency.value in ["NVCT", "AFD1", "SPU", "TU", "SFN", "AKLUMI"]):
                rate_key = self.get_rate_key(from_currency, to_currency)
                if rate_key in self.fallback_rates:
                    # Use fallback rate
                    rate = self.fallback_rates[rate_key]
                    inverse_rate = 1 / rate if rate != 0 else 0
                    
                    # Create new exchange rate record
                    exchange_rate = CurrencyExchangeRate(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=rate,
                        inverse_rate=inverse_rate,
                        source="fallback",
                        is_active=True
                    )
                    
                    self.db.session.add(exchange_rate)
                    updated_count += 1
            else:
                # Try external API
                rate = self._fetch_external_rate(from_currency, to_currency)
                if rate:
                    inverse_rate = 1 / rate if rate != 0 else 0
                    
                    # Create new exchange rate record
                    exchange_rate = CurrencyExchangeRate(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=rate,
                        inverse_rate=inverse_rate,
                        source="external_api",
                        is_active=True
                    )
                    
                    self.db.session.add(exchange_rate)
                    updated_count += 1
        
        try:
            self.db.session.commit()
            logger.info(f"Updated {updated_count} exchange rates")
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error committing exchange rate updates: {str(e)}")
        
        return updated_count

# Create global instance
exchange_service = CurrencyExchangeService()