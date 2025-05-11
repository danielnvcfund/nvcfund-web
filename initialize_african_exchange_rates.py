#!/usr/bin/env python3
"""
Initialize Exchange Rates for African Currencies
This script initializes exchange rates for African currencies that can't be stored directly in the database
due to database enum limitations. These include XOF (CFA Franc BCEAO) and XAF (CFA Franc BEAC).
"""

import logging
import currency_exchange_workaround

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize African currency exchange rates"""
    try:
        # West African CFA Franc (XOF)
        # Used by 8 countries: Benin, Burkina Faso, Côte d'Ivoire, Guinea-Bissau, Mali, Niger, Senegal, Togo
        currency_exchange_workaround.update_rate("USD", "XOF", 600.0)    # Approx 600 XOF per USD
        currency_exchange_workaround.update_rate("NVCT", "XOF", 600.0)   # Same as USD (NVCT pegged 1:1 to USD)
        currency_exchange_workaround.update_rate("EUR", "XOF", 655.957)  # XOF is pegged to EUR
        
        # Central African CFA Franc (XAF)
        # Used by 6 countries: Cameroon, Central African Republic, Chad, Republic of the Congo, Equatorial Guinea, Gabon
        currency_exchange_workaround.update_rate("USD", "XAF", 600.0)    # Approx 600 XAF per USD
        currency_exchange_workaround.update_rate("NVCT", "XAF", 600.0)   # Same as USD
        currency_exchange_workaround.update_rate("EUR", "XAF", 655.957)  # XAF is pegged to EUR
        
        # Add other African regional currencies as needed
        # CFP Franc (XPF) used in French overseas territories
        currency_exchange_workaround.update_rate("USD", "XPF", 119.0)
        currency_exchange_workaround.update_rate("NVCT", "XPF", 119.0)
        currency_exchange_workaround.update_rate("EUR", "XPF", 119.33)   # XPF is pegged to EUR
        
        # Count available rates
        rates = currency_exchange_workaround.load_rates()
        logger.info(f"Successfully initialized {len(rates)} exchange rates for regional currencies")
        
        return True
    except Exception as e:
        logger.error(f"Error initializing African exchange rates: {str(e)}")
        return False

if __name__ == "__main__":
    main()