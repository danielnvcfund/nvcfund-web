#!/usr/bin/env python3
"""
Initialize exchange rates for NVC Banking Platform
This script sets up the default exchange rates including AFD1 rates
"""

import logging
from app import app
from currency_exchange_service import CurrencyExchangeService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize the exchange rates"""
    with app.app_context():
        logger.info("Initializing default exchange rates...")
        result = CurrencyExchangeService.initialize_default_rates()
        if result:
            logger.info("Successfully initialized exchange rates!")
        else:
            logger.error("Failed to initialize exchange rates")

if __name__ == "__main__":
    main()