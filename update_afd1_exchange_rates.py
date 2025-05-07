#!/usr/bin/env python3
"""
Update AFD1 exchange rates
This script initializes and updates exchange rates for the AFD1 currency
"""

import logging
from app import app, db
from currency_exchange_service import CurrencyExchangeService
from account_holder_models import CurrencyExchangeRate, CurrencyType
from saint_crown_integration import SaintCrownIntegration

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_afd1_rates():
    """Initialize or update the AFD1 exchange rates"""
    
    with app.app_context():
        try:
            # Get gold price
            sc_integration = SaintCrownIntegration()
            gold_price, metadata = sc_integration.get_gold_price()
            afd1_unit_value = gold_price * 0.1  # AFD1 = 10% of gold price
            
            logger.info(f"Gold price: ${gold_price:,.2f} USD per ounce")
            logger.info(f"AFD1 unit value: ${afd1_unit_value:,.2f} USD")
            
            # Update AFD1 to USD rate
            afd1_usd_rate = CurrencyExchangeService.update_exchange_rate(
                CurrencyType.AFD1, 
                CurrencyType.USD, 
                afd1_unit_value, 
                "system_gold_price"
            )
            
            if afd1_usd_rate:
                logger.info(f"Updated AFD1 to USD rate: 1 AFD1 = {afd1_unit_value} USD")
            else:
                logger.error("Failed to update AFD1 to USD rate")
                
            # Update NVCT to AFD1 rate
            nvct_to_afd1_rate = 1.0 / afd1_unit_value  # 1 NVCT = 1 USD, convert to AFD1
            nvct_afd1_rate = CurrencyExchangeService.update_exchange_rate(
                CurrencyType.NVCT, 
                CurrencyType.AFD1, 
                nvct_to_afd1_rate, 
                "system_gold_price"
            )
            
            if nvct_afd1_rate:
                logger.info(f"Updated NVCT to AFD1 rate: 1 NVCT = {nvct_to_afd1_rate} AFD1")
            else:
                logger.error("Failed to update NVCT to AFD1 rate")
                
            logger.info("AFD1 exchange rates updated successfully")
            
            # Display all current rates
            rates = CurrencyExchangeRate.query.filter(
                (CurrencyExchangeRate.from_currency == CurrencyType.AFD1) | 
                (CurrencyExchangeRate.to_currency == CurrencyType.AFD1)
            ).all()
            
            logger.info("Current AFD1 Exchange Rates:")
            for rate in rates:
                logger.info(f"{rate.from_currency.value} to {rate.to_currency.value}: {rate.rate}")
            
            return True
        except Exception as e:
            logger.error(f"Error updating AFD1 exchange rates: {str(e)}")
            return False

if __name__ == "__main__":
    update_afd1_rates()