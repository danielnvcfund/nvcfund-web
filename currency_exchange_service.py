"""
Currency Exchange Service for NVC Banking Platform
This module provides functionality for currency conversions and exchange operations,
particularly focusing on NVCT as the base currency.
Support for all global currencies and cryptocurrencies added via workaround.
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_DOWN
from sqlalchemy.exc import SQLAlchemyError

from app import db
from saint_crown_integration import SaintCrownIntegration
# Import workaround for currency exchange
import currency_exchange_workaround
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
            
            # If database lookup fails, try our workaround for all global currencies
            # Convert enum values to strings
            from_currency_str = from_currency.value if hasattr(from_currency, 'value') else str(from_currency)
            to_currency_str = to_currency.value if hasattr(to_currency, 'value') else str(to_currency)
            
            # Use the workaround to get exchange rate
            workaround_rate = currency_exchange_workaround.get_exchange_rate(from_currency_str, to_currency_str)
            if workaround_rate:
                logger.info(f"Using workaround exchange rate for {from_currency_str} to {to_currency_str}: {workaround_rate}")
                return workaround_rate
            
            # If we're here, no rate was found
            logger.warning(f"No exchange rate found for {from_currency_str} to {to_currency_str}")
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving exchange rate: {str(e)}")
            
            # If database error, try workaround as fallback
            try:
                from_currency_str = from_currency.value if hasattr(from_currency, 'value') else str(from_currency)
                to_currency_str = to_currency.value if hasattr(to_currency, 'value') else str(to_currency)
                
                workaround_rate = currency_exchange_workaround.get_exchange_rate(from_currency_str, to_currency_str)
                if workaround_rate:
                    logger.info(f"Using fallback workaround rate for {from_currency_str} to {to_currency_str}: {workaround_rate}")
                    return workaround_rate
            except Exception as workaround_error:
                logger.error(f"Workaround also failed: {str(workaround_error)}")
            
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
            
            # Add AFD1 rate (AFD1 = 10% of gold price)
            sc_integration = SaintCrownIntegration()
            gold_price, _ = sc_integration.get_gold_price()
            afd1_unit_value = gold_price * 0.1  # AFD1 = 10% of gold price
            
            # Add AFD1 to USD rate (based on gold price) 
            CurrencyExchangeService.update_exchange_rate(CurrencyType.AFD1, CurrencyType.USD, afd1_unit_value, "system")
            
            # Add NVCT to AFD1 rate
            nvct_to_afd1_rate = 1.0 / afd1_unit_value  # 1 NVCT = 1 USD, convert to AFD1
            CurrencyExchangeService.update_exchange_rate(CurrencyType.NVCT, CurrencyType.AFD1, nvct_to_afd1_rate, "system")
            
            # Add SFN Coin rates
            # SFN to USD rate (1 SFN = 2.50 USD)
            sfn_to_usd_rate = 2.50  # Current SFN value in USD
            CurrencyExchangeService.update_exchange_rate(CurrencyType.SFN, CurrencyType.USD, sfn_to_usd_rate, "system_swifin")
            
            # NVCT to SFN rate (1 NVCT = 0.4 SFN since 1 NVCT = 1 USD and 1 SFN = 2.50 USD)
            nvct_to_sfn_rate = 1.0 / sfn_to_usd_rate
            CurrencyExchangeService.update_exchange_rate(CurrencyType.NVCT, CurrencyType.SFN, nvct_to_sfn_rate, "system_swifin")
            
            # SFN to AFD1 rate
            sfn_to_afd1_rate = sfn_to_usd_rate / afd1_unit_value
            CurrencyExchangeService.update_exchange_rate(CurrencyType.SFN, CurrencyType.AFD1, sfn_to_afd1_rate, "system_calculated")
            
            # Add Ak Lumi rates from Eco-6
            # Ak Lumi to USD rate (1 AKLUMI = 3.25 USD)
            aklumi_to_usd_rate = 3.25  # Current Ak Lumi value in USD
            CurrencyExchangeService.update_exchange_rate(CurrencyType.AKLUMI, CurrencyType.USD, aklumi_to_usd_rate, "system_eco6")
            
            # NVCT to Ak Lumi rate (1 NVCT = 0.3077 AKLUMI since 1 NVCT = 1 USD and 1 AKLUMI = 3.25 USD)
            nvct_to_aklumi_rate = 1.0 / aklumi_to_usd_rate
            CurrencyExchangeService.update_exchange_rate(CurrencyType.NVCT, CurrencyType.AKLUMI, nvct_to_aklumi_rate, "system_eco6")
            
            # Ak Lumi to AFD1 rate
            aklumi_to_afd1_rate = aklumi_to_usd_rate / afd1_unit_value
            CurrencyExchangeService.update_exchange_rate(CurrencyType.AKLUMI, CurrencyType.AFD1, aklumi_to_afd1_rate, "system_calculated")
            
            # Ak Lumi to SFN rate
            aklumi_to_sfn_rate = aklumi_to_usd_rate / sfn_to_usd_rate
            CurrencyExchangeService.update_exchange_rate(CurrencyType.AKLUMI, CurrencyType.SFN, aklumi_to_sfn_rate, "system_calculated")
            
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
            fiat_currencies = [CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, CurrencyType.NGN]
            crypto_currencies = [CurrencyType.BTC, CurrencyType.ETH, CurrencyType.ZCASH]
            
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
                else:
                    # Default to FIAT_TO_FIAT for other AFD1 exchanges
                    exchange_type = ExchangeType.FIAT_TO_FIAT
            
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
                    # Default to CRYPTO_TO_CRYPTO for other Ak Lumi exchanges
                    exchange_type = ExchangeType.CRYPTO_TO_CRYPTO
                    
            # Other exchanges
            elif to_account.currency == CurrencyType.NVCT:
                if from_account.currency in fiat_currencies:
                    exchange_type = ExchangeType.FIAT_TO_NVCT
                else:
                    exchange_type = ExchangeType.CRYPTO_TO_NVCT
            elif to_account.currency == CurrencyType.AFD1:
                if from_account.currency in fiat_currencies:
                    exchange_type = ExchangeType.FIAT_TO_AFD1
                else:
                    # Default to FIAT_TO_FIAT for other exchanges to AFD1
                    exchange_type = ExchangeType.FIAT_TO_FIAT
            elif to_account.currency == CurrencyType.SFN:
                if from_account.currency in fiat_currencies:
                    exchange_type = ExchangeType.FIAT_TO_SFN
                else:
                    # Default to CRYPTO_TO_CRYPTO for other exchanges to SFN
                    exchange_type = ExchangeType.CRYPTO_TO_CRYPTO
            elif to_account.currency == CurrencyType.AKLUMI:
                if from_account.currency in fiat_currencies:
                    exchange_type = ExchangeType.FIAT_TO_AKLUMI
                else:
                    # Default to CRYPTO_TO_CRYPTO for other exchanges to Ak Lumi
                    exchange_type = ExchangeType.CRYPTO_TO_CRYPTO
            elif from_account.currency in crypto_currencies and to_account.currency in crypto_currencies:
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