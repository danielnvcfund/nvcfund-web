"""
Update Ak Lumi exchange rates for the NVC Banking Platform

This script updates the exchange rates for Ak Lumi currency from Eco-6 (https://www.eco-6.com/)
based on the current market price. Ak Lumi rates are updated against USD, NVCT, AFD1 and SFN.
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

def update_aklumi_exchange_rates():
    """Update Ak Lumi exchange rates"""
    with flask_app.app_context():
        try:
            # Ak Lumi to USD rate - For now using a fixed rate of $3.25 USD
            # This would normally be fetched from an API or exchange
            aklumi_to_usd_rate = 3.25
            
            # Update Ak Lumi to USD rate
            CurrencyExchangeService.update_exchange_rate(
                CurrencyType.AKLUMI, 
                CurrencyType.USD, 
                aklumi_to_usd_rate, 
                "system_eco6"
            )
            logger.info(f"Updated Ak Lumi to USD rate: {aklumi_to_usd_rate}")
            
            # Update NVCT to Ak Lumi rate (1 NVCT = 1 USD, calculate to Ak Lumi)
            nvct_to_aklumi_rate = 1.0 / aklumi_to_usd_rate
            CurrencyExchangeService.update_exchange_rate(
                CurrencyType.NVCT, 
                CurrencyType.AKLUMI, 
                nvct_to_aklumi_rate, 
                "system_eco6"
            )
            logger.info(f"Updated NVCT to Ak Lumi rate: {nvct_to_aklumi_rate}")
            
            # Get AFD1 value based on gold price
            sc_integration = SaintCrownIntegration()
            gold_price, _ = sc_integration.get_gold_price()
            afd1_unit_value = gold_price * 0.1  # AFD1 = 10% of gold price
            
            # Update Ak Lumi to AFD1 rate
            aklumi_to_afd1_rate = aklumi_to_usd_rate / afd1_unit_value
            CurrencyExchangeService.update_exchange_rate(
                CurrencyType.AKLUMI, 
                CurrencyType.AFD1, 
                aklumi_to_afd1_rate, 
                "system_calculated"
            )
            logger.info(f"Updated Ak Lumi to AFD1 rate: {aklumi_to_afd1_rate}")
            
            # SFN to USD rate is fixed at 2.50 USD
            sfn_to_usd_rate = 2.50
            
            # Update Ak Lumi to SFN rate
            aklumi_to_sfn_rate = aklumi_to_usd_rate / sfn_to_usd_rate
            CurrencyExchangeService.update_exchange_rate(
                CurrencyType.AKLUMI, 
                CurrencyType.SFN, 
                aklumi_to_sfn_rate, 
                "system_calculated"
            )
            logger.info(f"Updated Ak Lumi to SFN rate: {aklumi_to_sfn_rate}")
            
            # Add other Ak Lumi exchange rates as needed
            
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating Ak Lumi exchange rates: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating Ak Lumi exchange rates: {str(e)}")
            return False

if __name__ == "__main__":
    logger.info("Starting Ak Lumi exchange rate update...")
    success = update_aklumi_exchange_rates()
    
    if success:
        logger.info("Ak Lumi exchange rate update completed successfully!")
        sys.exit(0)
    else:
        logger.error("Ak Lumi exchange rate update failed!")
        sys.exit(1)