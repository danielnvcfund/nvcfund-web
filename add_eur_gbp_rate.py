"""
Add EUR to GBP exchange rate
"""

from flask import Flask
from app import app, db
from account_holder_models import CurrencyType, CurrencyExchangeRate

with app.app_context():
    # Check if the EUR to GBP rate already exists
    existing_rate = CurrencyExchangeRate.query.filter_by(
        from_currency=CurrencyType.EUR,
        to_currency=CurrencyType.GBP
    ).first()
    
    if existing_rate:
        print(f"EUR to GBP rate already exists: {existing_rate.rate}")
    else:
        # Create a new rate (1 EUR = 0.85 GBP)
        rate = 0.85
        inverse_rate = 1.0 / rate if rate > 0 else 0
        
        new_rate = CurrencyExchangeRate(
            from_currency=CurrencyType.EUR,
            to_currency=CurrencyType.GBP,
            rate=rate,
            inverse_rate=inverse_rate,
            source="manual_addition",
            is_active=True
        )
        
        db.session.add(new_rate)
        db.session.commit()
        print(f"EUR to GBP rate added: {rate}")