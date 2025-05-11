"""
Currency Exchange Service Core for NVC Banking Platform
This module provides the core class for currency conversions and exchange operations,
separated to avoid circular import issues.
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
            logger.warning(f"No exchange rate found for {from_currency} to {to_currency}")
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
            CurrencyExchangeRate: Updated or created rate object or None if failed
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
            fiat_currencies = [CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, CurrencyType.NGN]
            crypto_currencies = [CurrencyType.BTC, CurrencyType.ETH, CurrencyType.ZCASH]
            
            # Set default exchange type
            exchange_type = ExchangeType.FIAT_TO_FIAT
            
            # NVCT exchanges
            if from_account.currency == CurrencyType.NVCT:
                if to_account.currency == CurrencyType.AFD1:
                    exchange_type = ExchangeType.NVCT_TO_AFD1
                elif to_account.currency == CurrencyType.SFN:
                    exchange_type = ExchangeType.NVCT_TO_SFN
                elif to_account.currency == CurrencyType.AKLUMI:
                    exchange_type = ExchangeType.NVCT_TO_AKLUMI
                elif to_account.currency in fiat_currencies:
                    exchange_type = ExchangeType.NVCT_TO_FIAT
                else:
                    exchange_type = ExchangeType.NVCT_TO_CRYPTO
                    
            # AFD1 exchanges
            elif from_account.currency == CurrencyType.AFD1:
                if to_account.currency == CurrencyType.NVCT:
                    exchange_type = ExchangeType.AFD1_TO_NVCT
                elif to_account.currency in fiat_currencies:
                    exchange_type = ExchangeType.AFD1_TO_FIAT
                
            # SFN exchanges
            elif from_account.currency == CurrencyType.SFN:
                if to_account.currency == CurrencyType.NVCT:
                    exchange_type = ExchangeType.SFN_TO_NVCT
                elif to_account.currency in fiat_currencies:
                    exchange_type = ExchangeType.SFN_TO_FIAT
                else:
                    # Default to CRYPTO_TO_CRYPTO for other SFN exchanges
                    exchange_type = ExchangeType.CRYPTO_TO_CRYPTO
            
            # Ak Lumi exchanges
            elif from_account.currency == CurrencyType.AKLUMI:
                if to_account.currency == CurrencyType.NVCT:
                    exchange_type = ExchangeType.AKLUMI_TO_NVCT
                elif to_account.currency in fiat_currencies:
                    exchange_type = ExchangeType.AKLUMI_TO_FIAT
                else:
                    # Default to FIAT_TO_FIAT for other Ak Lumi exchanges
                    exchange_type = ExchangeType.FIAT_TO_FIAT
            
            # Fiat exchanges
            elif from_account.currency in fiat_currencies:
                if to_account.currency == CurrencyType.NVCT:
                    exchange_type = ExchangeType.FIAT_TO_NVCT
                elif to_account.currency == CurrencyType.AFD1:
                    exchange_type = ExchangeType.FIAT_TO_AFD1
                elif to_account.currency == CurrencyType.SFN:
                    exchange_type = ExchangeType.FIAT_TO_SFN
                elif to_account.currency == CurrencyType.AKLUMI:
                    exchange_type = ExchangeType.FIAT_TO_AKLUMI
                elif to_account.currency in fiat_currencies:
                    exchange_type = ExchangeType.FIAT_TO_FIAT
                else:
                    exchange_type = ExchangeType.FIAT_TO_CRYPTO
            
            # Crypto exchanges
            elif from_account.currency in crypto_currencies:
                if to_account.currency == CurrencyType.NVCT:
                    exchange_type = ExchangeType.CRYPTO_TO_NVCT
                elif to_account.currency in fiat_currencies:
                    exchange_type = ExchangeType.CRYPTO_TO_FIAT
                else:
                    exchange_type = ExchangeType.CRYPTO_TO_CRYPTO
            
            # Create transaction record
            reference_number = f"FX-{uuid.uuid4().hex[:8]}"
            
            transaction = CurrencyExchangeTransaction(
                exchange_type=exchange_type,
                from_currency=from_account.currency,
                to_currency=to_account.currency,
                from_amount=amount,
                to_amount=converted_amount,
                rate_applied=rate,
                fee_amount=fee_amount,
                fee_currency=from_account.currency,
                status=ExchangeStatus.PENDING,
                reference_number=reference_number,
                notes=f"Exchange from {from_account.account_number} to {to_account.account_number}",
                account_holder_id=account_holder_id,
                from_account_id=from_account_id,
                to_account_id=to_account_id
            )
            
            db.session.add(transaction)
            
            # Update account balances
            from_account.balance -= amount
            to_account.balance += converted_amount
            
            # Update available balances as well
            from_account.available_balance -= amount
            to_account.available_balance += converted_amount
            
            # Set last transaction time
            current_time = datetime.utcnow()
            from_account.last_transaction_at = current_time
            to_account.last_transaction_at = current_time
            
            # Complete the transaction
            transaction.status = ExchangeStatus.COMPLETED
            transaction.completed_at = current_time
            
            db.session.commit()
            
            return {
                "success": True,
                "transaction": {
                    "id": transaction.id,
                    "reference": reference_number,
                    "from_amount": amount,
                    "from_currency": from_account.currency.value,
                    "to_amount": converted_amount,
                    "to_currency": to_account.currency.value,
                    "rate": rate,
                    "fee": fee_amount,
                    "status": transaction.status.value
                }
            }
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error performing exchange: {str(e)}")
            return {"success": False, "error": f"Database error: {str(e)}"}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error performing exchange: {str(e)}")
            return {"success": False, "error": f"Error: {str(e)}"}