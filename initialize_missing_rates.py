"""
Script to initialize missing exchange rates
"""

import logging
from flask import Flask
from app import app
from account_holder_models import CurrencyType
from currency_exchange_service import CurrencyExchangeService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_missing_exchange_rates():
    """Initialize missing exchange rates"""
    with app.app_context():
        logger.info("Initializing missing exchange rates...")
        
        # EUR to GBP rate (1 EUR = 0.85 GBP)
        CurrencyExchangeService.update_exchange_rate(CurrencyType.EUR, CurrencyType.GBP, 0.85, "system")
        logger.info("EUR to GBP rate initialized")
        
        # EUR to NVCT (1 EUR = 1.08 NVCT since EUR is stronger than USD/NVCT)
        CurrencyExchangeService.update_exchange_rate(CurrencyType.EUR, CurrencyType.NVCT, 1.08, "system")
        logger.info("EUR to NVCT rate initialized")
        
        # GBP to NVCT (1 GBP = 1.27 NVCT since GBP is stronger than USD/NVCT)
        CurrencyExchangeService.update_exchange_rate(CurrencyType.GBP, CurrencyType.NVCT, 1.27, "system")
        logger.info("GBP to NVCT rate initialized")
        
        # Add SFN Coin rates
        # SFN to USD rate (1 SFN = 2.50 USD)
        sfn_to_usd_rate = 2.50
        CurrencyExchangeService.update_exchange_rate(CurrencyType.SFN, CurrencyType.USD, sfn_to_usd_rate, "system_swifin")
        logger.info("SFN to USD rate initialized")
        
        # NVCT to SFN rate
        nvct_to_sfn_rate = 1.0 / sfn_to_usd_rate  # 1 NVCT = 0.4 SFN
        CurrencyExchangeService.update_exchange_rate(CurrencyType.NVCT, CurrencyType.SFN, nvct_to_sfn_rate, "system_swifin")
        logger.info("NVCT to SFN rate initialized")
        
        # Add Ak Lumi rates
        # Ak Lumi to USD rate (1 AKLUMI = 3.25 USD)
        aklumi_to_usd_rate = 3.25
        CurrencyExchangeService.update_exchange_rate(CurrencyType.AKLUMI, CurrencyType.USD, aklumi_to_usd_rate, "system_eco6")
        logger.info("AKLUMI to USD rate initialized")
        
        # NVCT to Ak Lumi rate
        nvct_to_aklumi_rate = 1.0 / aklumi_to_usd_rate  # 1 NVCT = 0.3077 AKLUMI
        CurrencyExchangeService.update_exchange_rate(CurrencyType.NVCT, CurrencyType.AKLUMI, nvct_to_aklumi_rate, "system_eco6")
        logger.info("NVCT to AKLUMI rate initialized")
        
        # Cross-rates for the special currencies
        # Ak Lumi to SFN rate
        aklumi_to_sfn_rate = aklumi_to_usd_rate / sfn_to_usd_rate
        CurrencyExchangeService.update_exchange_rate(CurrencyType.AKLUMI, CurrencyType.SFN, aklumi_to_sfn_rate, "system_calculated")
        logger.info("AKLUMI to SFN rate initialized")
        
        # AFD1 to USD rate (assuming AFD1 = 339.40, which is 10% of gold price at $3,394.00)
        afd1_to_usd_rate = 339.40
        CurrencyExchangeService.update_exchange_rate(CurrencyType.AFD1, CurrencyType.USD, afd1_to_usd_rate, "system_saint_crown")
        logger.info("AFD1 to USD rate initialized")
        
        # NVCT to AFD1 rate
        nvct_to_afd1_rate = 1.0 / afd1_to_usd_rate
        CurrencyExchangeService.update_exchange_rate(CurrencyType.NVCT, CurrencyType.AFD1, nvct_to_afd1_rate, "system_saint_crown")
        logger.info("NVCT to AFD1 rate initialized")
        
        # Ak Lumi to AFD1 rate
        aklumi_to_afd1_rate = aklumi_to_usd_rate / afd1_to_usd_rate
        CurrencyExchangeService.update_exchange_rate(CurrencyType.AKLUMI, CurrencyType.AFD1, aklumi_to_afd1_rate, "system_calculated")
        logger.info("AKLUMI to AFD1 rate initialized")
        
        # SFN to AFD1 rate
        sfn_to_afd1_rate = sfn_to_usd_rate / afd1_to_usd_rate
        CurrencyExchangeService.update_exchange_rate(CurrencyType.SFN, CurrencyType.AFD1, sfn_to_afd1_rate, "system_calculated")
        logger.info("SFN to AFD1 rate initialized")
        
        logger.info("All missing exchange rates initialized successfully")

if __name__ == "__main__":
    initialize_missing_exchange_rates()