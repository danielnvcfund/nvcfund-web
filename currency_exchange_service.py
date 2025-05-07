"""
Currency Exchange Service for NVC Banking Platform
This module provides functionality for currency conversions and exchange operations,
particularly focusing on NVCT as the base currency.
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_DOWN
from sqlalchemy.exc import SQLAlchemyError

from app import db
from account_holder_models import (
    CurrencyType, 
    ExchangeType, 
    ExchangeStatus,
    BankAccount, 
    AccountHolder,
    CurrencyExchangeRate, 
    CurrencyExchangeTransaction
)

# Set up logging
logger = logging.getLogger(__name__)

class CurrencyExchangeService:
    """Service for handling currency exchanges between various currencies with NVCT as primary pair"""
    
    @staticmethod
    def get_exchange_rate(from_currency, to_currency):
        """
        Get the current exchange rate between two currencies
        
        Args:
            from_currency (CurrencyType): Source currency
            to_currency (CurrencyType): Target currency
            
        Returns:
            float: Exchange rate or None if not found
        """
        try:
            # First try direct rate
            rate = CurrencyExchangeRate.query.filter_by(
                from_currency=from_currency,
                to_currency=to_currency,
                is_active=True
            ).order_by(CurrencyExchangeRate.last_updated.desc()).first()
            
            if rate:
                return rate.rate
            
            # Try inverse rate
            inverse_rate = CurrencyExchangeRate.query.filter_by(
                from_currency=to_currency,
                to_currency=from_currency,
                is_active=True
            ).order_by(CurrencyExchangeRate.last_updated.desc()).first()
            
            if inverse_rate and inverse_rate.inverse_rate:
                return inverse_rate.inverse_rate
                
            # If still not found, try to calculate via NVCT (if neither is NVCT)
            if from_currency != CurrencyType.NVCT and to_currency != CurrencyType.NVCT:
                # Get rates for from_currency -> NVCT and NVCT -> to_currency
                from_to_nvct = CurrencyExchangeService.get_exchange_rate(from_currency, CurrencyType.NVCT)
                nvct_to_to = CurrencyExchangeService.get_exchange_rate(CurrencyType.NVCT, to_currency)
                
                if from_to_nvct and nvct_to_to:
                    # Calculate the cross rate
                    return from_to_nvct * nvct_to_to
            
            # If we're here, no rate was found
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving exchange rate: {str(e)}")
            return None
    
    @staticmethod
    def update_exchange_rate(from_currency, to_currency, rate, source="internal"):
        """
        Update or create an exchange rate
        
        Args:
            from_currency (CurrencyType): Source currency
            to_currency (CurrencyType): Target currency
            rate (float): Exchange rate value
            source (str): Source of the rate update
            
        Returns:
            CurrencyExchangeRate: Updated or created rate object
        """
        try:
            # Calculate inverse rate
            if rate > 0:
                inverse_rate = 1.0 / rate
            else:
                inverse_rate = 0
                
            # Check if rate exists
            existing_rate = CurrencyExchangeRate.query.filter_by(
                from_currency=from_currency,
                to_currency=to_currency
            ).first()
            
            if existing_rate:
                # Update existing rate
                existing_rate.rate = rate
                existing_rate.inverse_rate = inverse_rate
                existing_rate.source = source
                existing_rate.last_updated = datetime.utcnow()
                existing_rate.is_active = True
                
                db.session.commit()
                return existing_rate
            else:
                # Create new rate
                new_rate = CurrencyExchangeRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate,
                    inverse_rate=inverse_rate,
                    source=source,
                    is_active=True
                )
                
                db.session.add(new_rate)
                db.session.commit()
                return new_rate
                
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating exchange rate: {str(e)}")
            return None
    
    @staticmethod
    def initialize_default_rates():
        """
        Initialize default exchange rates, particularly for NVCT
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # For NVCT stablecoin (1:1 with USD)
            CurrencyExchangeService.update_exchange_rate(CurrencyType.NVCT, CurrencyType.USD, 1.0, "system")
            
            # Other common fiat currency rates (sample values, should be updated with real market rates)
            CurrencyExchangeService.update_exchange_rate(CurrencyType.USD, CurrencyType.EUR, 0.93, "system")
            CurrencyExchangeService.update_exchange_rate(CurrencyType.USD, CurrencyType.GBP, 0.79, "system")
            CurrencyExchangeService.update_exchange_rate(CurrencyType.USD, CurrencyType.NGN, 1500.0, "system")
            
            # Crypto rates (sample values, should be updated with real market rates)
            CurrencyExchangeService.update_exchange_rate(CurrencyType.BTC, CurrencyType.USD, 62000.0, "system")
            CurrencyExchangeService.update_exchange_rate(CurrencyType.ETH, CurrencyType.USD, 3000.0, "system")
            
            return True
        except Exception as e:
            logger.error(f"Error initializing default exchange rates: {str(e)}")
            return False
    
    @staticmethod
    def perform_exchange(
        account_holder_id,
        from_account_id,
        to_account_id,
        amount,
        apply_fee=True,
        fee_percentage=0.5
    ):
        """
        Perform a currency exchange between two accounts
        
        Args:
            account_holder_id (int): ID of the account holder
            from_account_id (int): ID of the source account
            to_account_id (int): ID of the target account
            amount (float): Amount to exchange (in from_currency)
            apply_fee (bool): Whether to apply exchange fee
            fee_percentage (float): Fee percentage to apply (0.5 = 0.5%)
            
        Returns:
            dict: Result with success status and transaction details
        """
        try:
            # Get the accounts
            from_account = BankAccount.query.get(from_account_id)
            to_account = BankAccount.query.get(to_account_id)
            
            if not from_account or not to_account:
                return {"success": False, "error": "One or both accounts not found"}
                
            # Verify account holder owns both accounts
            if from_account.account_holder_id != account_holder_id or to_account.account_holder_id != account_holder_id:
                return {"success": False, "error": "Account holder does not own one or both accounts"}
                
            # Verify sufficient balance
            if from_account.balance < amount:
                return {"success": False, "error": "Insufficient balance in source account"}
                
            # Get exchange rate
            rate = CurrencyExchangeService.get_exchange_rate(from_account.currency, to_account.currency)
            
            if not rate:
                return {"success": False, "error": "Exchange rate not available for these currencies"}
                
            # Calculate converted amount
            converted_amount = amount * rate
            
            # Apply fee if needed
            fee_amount = 0
            if apply_fee and fee_percentage > 0:
                fee_amount = (amount * fee_percentage) / 100
                amount_after_fee = amount - fee_amount
                converted_amount = amount_after_fee * rate
                
            # Determine exchange type
            if from_account.currency == CurrencyType.NVCT:
                exchange_type = ExchangeType.NVCT_TO_FIAT if to_account.currency in [CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, CurrencyType.NGN] else ExchangeType.NVCT_TO_CRYPTO
            elif to_account.currency == CurrencyType.NVCT:
                exchange_type = ExchangeType.FIAT_TO_NVCT if from_account.currency in [CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, CurrencyType.NGN] else ExchangeType.CRYPTO_TO_NVCT
            elif from_account.currency in [CurrencyType.BTC, CurrencyType.ETH, CurrencyType.ZCASH] and to_account.currency in [CurrencyType.BTC, CurrencyType.ETH, CurrencyType.ZCASH]:
                exchange_type = ExchangeType.CRYPTO_TO_CRYPTO
            else:
                exchange_type = ExchangeType.FIAT_TO_FIAT
                
            # Generate reference number
            reference = f"EX-{uuid.uuid4().hex[:8].upper()}"
            
            # Create exchange transaction record
            exchange_tx = CurrencyExchangeTransaction(
                exchange_type=exchange_type,
                from_currency=from_account.currency,
                to_currency=to_account.currency,
                from_amount=amount,
                to_amount=converted_amount,
                rate_applied=rate,
                fee_amount=fee_amount,
                fee_currency=from_account.currency,
                status=ExchangeStatus.PENDING,
                reference_number=reference,
                account_holder_id=account_holder_id,
                from_account_id=from_account_id,
                to_account_id=to_account_id
            )
            
            db.session.add(exchange_tx)
            
            # Update account balances
            from_account.balance -= amount
            from_account.last_transaction_at = datetime.utcnow()
            
            to_account.balance += converted_amount
            to_account.last_transaction_at = datetime.utcnow()
            
            # Mark exchange as completed
            exchange_tx.status = ExchangeStatus.COMPLETED
            exchange_tx.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                "success": True,
                "transaction_id": exchange_tx.id,
                "reference": reference,
                "from_amount": amount,
                "from_currency": from_account.currency.value,
                "to_amount": converted_amount,
                "to_currency": to_account.currency.value,
                "rate": rate,
                "fee": fee_amount,
                "exchange_type": exchange_type.value
            }
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error performing exchange: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error performing exchange: {str(e)}")
            return {"success": False, "error": str(e)}
            
    @staticmethod
    def get_exchange_history(account_holder_id, limit=50):
        """
        Get exchange history for an account holder
        
        Args:
            account_holder_id (int): ID of the account holder
            limit (int): Maximum number of records to return
            
        Returns:
            list: List of exchange transactions
        """
        try:
            transactions = CurrencyExchangeTransaction.query.filter_by(
                account_holder_id=account_holder_id
            ).order_by(CurrencyExchangeTransaction.created_at.desc()).limit(limit).all()
            
            return transactions
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving exchange history: {str(e)}")
            return []