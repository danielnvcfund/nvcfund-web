#!/usr/bin/env python3
"""
Update SFN exchange rates
This script initializes and updates exchange rates for the SFN coin
"""

import logging
from app import app, db
from currency_exchange_service import CurrencyExchangeService
from account_holder_models import CurrencyExchangeRate, CurrencyType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_sfn_rates():
    """Initialize or update the SFN exchange rates"""
    
    with app.app_context():
        try:
            # SFN to NVCT at 1:1 exchange rate
            sfn_nvct_rate = CurrencyExchangeService.update_exchange_rate(
                CurrencyType.SFN, 
                CurrencyType.NVCT, 
                1.0,  # 1 SFN = 1 NVCT
                "system_fixed_rate"
            )
            
            if sfn_nvct_rate:
                logger.info(f"Updated SFN to NVCT rate: 1 SFN = 1 NVCT")
            else:
                logger.error("Failed to update SFN to NVCT rate")
                
            # Update NVCT to SFN rate if needed (should be 1:1 as well)
            nvct_sfn_rate = CurrencyExchangeService.update_exchange_rate(
                CurrencyType.NVCT, 
                CurrencyType.SFN, 
                1.0,  # 1 NVCT = 1 SFN
                "system_fixed_rate"
            )
            
            if nvct_sfn_rate:
                logger.info(f"Updated NVCT to SFN rate: 1 NVCT = 1 SFN")
            else:
                logger.error("Failed to update NVCT to SFN rate")
                
            logger.info("SFN exchange rates updated successfully")
            
            # Display all current rates
            rates = CurrencyExchangeRate.query.filter(
                (CurrencyExchangeRate.from_currency == CurrencyType.SFN) | 
                (CurrencyExchangeRate.to_currency == CurrencyType.SFN)
            ).all()
            
            logger.info("Current SFN Exchange Rates:")
            for rate in rates:
                logger.info(f"{rate.from_currency.value} to {rate.to_currency.value}: {rate.rate}")
            
            return True
        except Exception as e:
            logger.error(f"Error updating SFN exchange rates: {str(e)}")
            return False

if __name__ == "__main__":
    update_sfn_rates()