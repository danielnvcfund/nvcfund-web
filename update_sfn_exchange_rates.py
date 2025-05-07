"""
Update SFN Coin exchange rates for the NVC Banking Platform

This script updates the exchange rates for SFN Coin from Swifin (https://swifin.com/)
based on the current market price. SFN rates are updated against USD, NVCT, and AFD1.
"""

import logging
import sys
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from app import app as flask_app, db
from saint_crown_integration import SaintCrownIntegration
from account_holder_models import CurrencyType
from currency_exchange_service import CurrencyExchangeService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_sfn_exchange_rates():
    """Update SFN exchange rates"""
    with flask_app.app_context():
        try:
            # SFN to USD rate - For now using a fixed rate of $2.50 USD
            # This would normally be fetched from an API or exchange
            sfn_to_usd_rate = 2.50
            
            # Update SFN to USD rate
            CurrencyExchangeService.update_exchange_rate(
                CurrencyType.SFN, 
                CurrencyType.USD, 
                sfn_to_usd_rate, 
                "system_swifin"
            )
            logger.info(f"Updated SFN to USD rate: {sfn_to_usd_rate}")
            
            # Update NVCT to SFN rate (1 NVCT = 1 USD, calculate to SFN)
            nvct_to_sfn_rate = 1.0 / sfn_to_usd_rate
            CurrencyExchangeService.update_exchange_rate(
                CurrencyType.NVCT, 
                CurrencyType.SFN, 
                nvct_to_sfn_rate, 
                "system_swifin"
            )
            logger.info(f"Updated NVCT to SFN rate: {nvct_to_sfn_rate}")
            
            # Get AFD1 value based on gold price
            sc_integration = SaintCrownIntegration()
            gold_price, _ = sc_integration.get_gold_price()
            afd1_unit_value = gold_price * 0.1  # AFD1 = 10% of gold price
            
            # Update SFN to AFD1 rate
            sfn_to_afd1_rate = sfn_to_usd_rate / afd1_unit_value
            CurrencyExchangeService.update_exchange_rate(
                CurrencyType.SFN, 
                CurrencyType.AFD1, 
                sfn_to_afd1_rate, 
                "system_calculated"
            )
            logger.info(f"Updated SFN to AFD1 rate: {sfn_to_afd1_rate}")
            
            # Add other SFN exchange rates as needed
            
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating SFN exchange rates: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating SFN exchange rates: {str(e)}")
            return False

if __name__ == "__main__":
    logger.info("Starting SFN exchange rate update...")
    success = update_sfn_exchange_rates()
    
    if success:
        logger.info("SFN exchange rate update completed successfully!")
        sys.exit(0)
    else:
        logger.error("SFN exchange rate update failed!")
        sys.exit(1)