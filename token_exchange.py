"""
Token Exchange API for NVC Banking Platform
Enables pairing, exchange, and trading between AFD1 and NVCT tokens

This module connects to the institutional dashboard API and provides
token exchange functionality.
"""
import os
import json
import logging
import requests
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union

from blockchain import get_nvc_token, get_web3, transfer_nvc_tokens
from models import Transaction, TransactionStatus, TransactionType, User

logger = logging.getLogger(__name__)

# Constants
INSTITUTIONAL_DASHBOARD_URL = "https://93004372-fdb3-49ae-82c5-6b6db3360d7c-00-2wv0hlifh7djg.riker.replit.dev/api/paypal/institutional-dashboard"
DEFAULT_TIMEOUT = 30  # seconds
AFD1_TOKEN_SYMBOL = "AFD1"
NVCT_TOKEN_SYMBOL = "NVCT"

class TokenExchange:
    """Token Exchange class for AFD1-NVCT trading"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the token exchange
        
        Args:
            api_key (str, optional): API key for institutional dashboard
        """
        self.api_key = api_key or os.environ.get("INSTITUTIONAL_DASHBOARD_API_KEY")
        self.base_url = INSTITUTIONAL_DASHBOARD_URL
        
    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests
        
        Returns:
            Dict[str, str]: Headers including API key
        """
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Api-Version": "1.0",
            "X-Platform": "NVC-Banking"
        }
    
    def check_connection(self) -> bool:
        """
        Check connection to institutional dashboard
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error connecting to institutional dashboard: {str(e)}")
            return False
    
    def get_exchange_rate(self) -> Optional[Decimal]:
        """
        Get current exchange rate between AFD1 and NVCT
        
        Returns:
            Decimal: Exchange rate (1 AFD1 = X NVCT)
        """
        try:
            response = requests.get(
                f"{self.base_url}/exchange-rate",
                params={"from": AFD1_TOKEN_SYMBOL, "to": NVCT_TOKEN_SYMBOL},
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                return Decimal(str(data.get("rate", 0)))
            else:
                logger.error(f"Error getting exchange rate: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting exchange rate: {str(e)}")
            return None
    
    def get_token_pair_info(self) -> Optional[Dict]:
        """
        Get information about the AFD1-NVCT token pair
        
        Returns:
            Dict: Token pair information
        """
        try:
            response = requests.get(
                f"{self.base_url}/token-pairs",
                params={"base": AFD1_TOKEN_SYMBOL, "quote": NVCT_TOKEN_SYMBOL},
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting token pair info: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting token pair info: {str(e)}")
            return None
    
    def execute_trade(
        self, 
        user_id: int,
        from_token: str,
        to_token: str,
        amount: Decimal,
        external_wallet_address: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Execute a trade between AFD1 and NVCT
        
        Args:
            user_id (int): User ID
            from_token (str): Source token symbol (AFD1 or NVCT)
            to_token (str): Destination token symbol (AFD1 or NVCT)
            amount (Decimal): Amount to trade in source token
            external_wallet_address (str, optional): External wallet address for receiving tokens
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: 
                (Success, Transaction ID, Error message)
        """
        # Validate token symbols
        if from_token not in [AFD1_TOKEN_SYMBOL, NVCT_TOKEN_SYMBOL]:
            return False, None, f"Invalid source token: {from_token}"
        
        if to_token not in [AFD1_TOKEN_SYMBOL, NVCT_TOKEN_SYMBOL]:
            return False, None, f"Invalid destination token: {to_token}"
        
        if from_token == to_token:
            return False, None, "Source and destination tokens must be different"
        
        # Get current exchange rate
        exchange_rate = self.get_exchange_rate()
        if not exchange_rate:
            return False, None, "Failed to get exchange rate"
        
        # Calculate destination amount
        if from_token == AFD1_TOKEN_SYMBOL:
            to_amount = amount * exchange_rate
        else:
            to_amount = amount / exchange_rate
        
        try:
            # Prepare trade request
            trade_data = {
                "fromToken": from_token,
                "toToken": to_token,
                "fromAmount": str(amount),
                "toAmount": str(to_amount),
                "userIdentifier": str(user_id),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if external_wallet_address:
                trade_data["externalWalletAddress"] = external_wallet_address
            
            # Execute trade through API
            response = requests.post(
                f"{self.base_url}/execute-trade",
                json=trade_data,
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                transaction_id = result.get("transactionId")
                
                # If we're trading to NVCT and it's successful, we need to mint or transfer NVCT
                if to_token == NVCT_TOKEN_SYMBOL and transaction_id:
                    # This would transfer NVCT to the user's account
                    # Implementation would depend on your system design
                    pass
                
                return True, transaction_id, None
            else:
                logger.error(f"Error executing trade: {response.status_code} - {response.text}")
                return False, None, f"Trade execution failed: {response.text}"
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return False, None, f"Trade execution error: {str(e)}"
    
    def get_trade_history(self, user_id: int) -> List[Dict]:
        """
        Get trading history for a user
        
        Args:
            user_id (int): User ID
            
        Returns:
            List[Dict]: List of trades
        """
        try:
            response = requests.get(
                f"{self.base_url}/trade-history",
                params={"userIdentifier": str(user_id)},
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT
            )
            
            if response.status_code == 200:
                return response.json().get("trades", [])
            else:
                logger.error(f"Error getting trade history: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting trade history: {str(e)}")
            return []
    
    def get_token_balance(self, user_id: int, token_symbol: str) -> Optional[Decimal]:
        """
        Get token balance for a user
        
        Args:
            user_id (int): User ID
            token_symbol (str): Token symbol (AFD1 or NVCT)
            
        Returns:
            Decimal: Token balance
        """
        if token_symbol not in [AFD1_TOKEN_SYMBOL, NVCT_TOKEN_SYMBOL]:
            logger.error(f"Invalid token symbol: {token_symbol}")
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/token-balance",
                params={"userIdentifier": str(user_id), "token": token_symbol},
                headers=self._get_headers(),
                timeout=DEFAULT_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                return Decimal(str(data.get("balance", 0)))
            else:
                logger.error(f"Error getting token balance: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting token balance: {str(e)}")
            return None

def create_exchange_transaction(
    user_id: int,
    from_token: str,
    to_token: str,
    from_amount: Decimal,
    to_amount: Decimal,
    external_transaction_id: str
) -> Optional[Transaction]:
    """
    Create a transaction record for a token exchange
    
    Args:
        user_id (int): User ID
        from_token (str): Source token symbol
        to_token (str): Destination token symbol
        from_amount (Decimal): Amount in source token
        to_amount (Decimal): Amount in destination token
        external_transaction_id (str): Transaction ID from institutional dashboard
        
    Returns:
        Transaction: Created transaction
    """
    from app import db
    
    try:
        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            transaction_id=f"EXCHANGE-{external_transaction_id}",
            transaction_type=TransactionType.TOKEN_EXCHANGE,
            amount=float(from_amount),
            fee=0,  # Fees might be handled by the institutional dashboard
            currency=from_token,
            description=f"Exchange {from_amount} {from_token} for {to_amount} {to_token}",
            status=TransactionStatus.COMPLETED,
            recipient_info=f"Exchanged for {to_token}",
            additional_data=json.dumps({
                "from_token": from_token,
                "to_token": to_token,
                "from_amount": str(from_amount),
                "to_amount": str(to_amount),
                "external_transaction_id": external_transaction_id,
                "exchange_rate": str(to_amount / from_amount) if from_amount else "0"
            })
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return transaction
    except Exception as e:
        logger.error(f"Error creating exchange transaction: {str(e)}")
        db.session.rollback()
        return None

# Singleton instance
_token_exchange = None

def get_token_exchange() -> TokenExchange:
    """
    Get singleton instance of TokenExchange
    
    Returns:
        TokenExchange: Token exchange instance
    """
    global _token_exchange
    if _token_exchange is None:
        _token_exchange = TokenExchange()
    return _token_exchange