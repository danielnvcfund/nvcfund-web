"""
Bridge.xyz API Integration Module for NVCT Liquidity Management

This module implements the necessary connectors and handlers to integrate with
Bridge.xyz's off-ramp API services to provide liquidity for NVCT.
"""
import os
import json
import time
import hmac
import hashlib
import base64
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BridgeXYZIntegration:
    """Bridge.xyz API Integration for NVCT"""
    
    API_BASE_URL = "https://api.bridge.xyz"  # Replace with actual API base URL
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize the Bridge.xyz integration.
        
        Args:
            api_key: Bridge.xyz API key
            api_secret: Bridge.xyz API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
    
    def _generate_signature(self, timestamp: int, method: str, endpoint: str, body: Optional[Dict] = None) -> str:
        """
        Generate HMAC signature for API requests.
        
        Args:
            timestamp: Unix timestamp in milliseconds
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            body: Request body for POST requests
            
        Returns:
            HMAC signature string
        """
        message = f"{timestamp}{method}{endpoint}"
        if body:
            message += json.dumps(body)
        
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _get_headers(self, method: str, endpoint: str, body: Optional[Dict] = None) -> Dict[str, str]:
        """
        Generate request headers with authentication.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            body: Request body for POST requests
            
        Returns:
            Dictionary of request headers
        """
        timestamp = int(time.time() * 1000)
        signature = self._generate_signature(timestamp, method, endpoint, body)
        
        return {
            "X-BRIDGE-API-KEY": self.api_key,
            "X-BRIDGE-TIMESTAMP": str(timestamp),
            "X-BRIDGE-SIGNATURE": signature,
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """
        Make an authenticated request to the Bridge.xyz API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: URL parameters for GET requests
            data: Request body for POST requests
            
        Returns:
            API response as dictionary
        """
        url = f"{self.API_BASE_URL}{endpoint}"
        headers = self._get_headers(method, endpoint, data)
        
        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, params=params)
            elif method == "POST":
                response = self.session.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = self.session.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise
    
    # Off-Ramp API Endpoints
    
    def get_supported_currencies(self) -> List[Dict]:
        """
        Get list of supported fiat currencies for off-ramp.
        
        Returns:
            List of currency objects with code, name, and limits
        """
        return self._make_request("GET", "/v1/offramp/currencies")
    
    def get_exchange_rates(self, source_currency: str, target_currencies: List[str]) -> Dict:
        """
        Get current exchange rates for crypto to fiat conversions.
        
        Args:
            source_currency: Source cryptocurrency (e.g., "NVCT")
            target_currencies: List of target fiat currencies (e.g., ["USD", "EUR"])
            
        Returns:
            Dictionary of exchange rates
        """
        params = {
            "source": source_currency,
            "targets": ",".join(target_currencies)
        }
        return self._make_request("GET", "/v1/offramp/rates", params=params)
    
    def create_offramp_transaction(self, 
                                  amount: float,
                                  source_currency: str,
                                  target_currency: str,
                                  beneficiary_id: str,
                                  external_id: Optional[str] = None) -> Dict:
        """
        Create a new off-ramp transaction (crypto to fiat).
        
        Args:
            amount: Amount to convert
            source_currency: Source cryptocurrency (e.g., "NVCT")
            target_currency: Target fiat currency (e.g., "USD")
            beneficiary_id: ID of the beneficiary (bank account)
            external_id: Optional external transaction ID for tracking
            
        Returns:
            Transaction details including ID and payment instructions
        """
        payload = {
            "amount": amount,
            "source_currency": source_currency,
            "target_currency": target_currency,
            "beneficiary_id": beneficiary_id
        }
        
        if external_id:
            payload["external_id"] = external_id
            
        return self._make_request("POST", "/v1/offramp/transactions", data=payload)
    
    def get_transaction_status(self, transaction_id: str) -> Dict:
        """
        Get status of an off-ramp transaction.
        
        Args:
            transaction_id: Bridge.xyz transaction ID
            
        Returns:
            Transaction status and details
        """
        return self._make_request("GET", f"/v1/offramp/transactions/{transaction_id}")
    
    def list_transactions(self, 
                         status: Optional[str] = None,
                         from_date: Optional[datetime] = None,
                         to_date: Optional[datetime] = None,
                         limit: int = 100) -> List[Dict]:
        """
        List off-ramp transactions with optional filters.
        
        Args:
            status: Filter by status (e.g., "pending", "completed")
            from_date: Start date for filtering
            to_date: End date for filtering
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction objects
        """
        params = {"limit": limit}
        
        if status:
            params["status"] = status
        
        if from_date:
            params["from"] = from_date.isoformat()
            
        if to_date:
            params["to"] = to_date.isoformat()
            
        return self._make_request("GET", "/v1/offramp/transactions", params=params)
    
    def create_beneficiary(self, 
                          bank_details: Dict[str, Any],
                          owner_details: Dict[str, Any],
                          currency: str) -> Dict:
        """
        Create a new beneficiary (bank account) for off-ramp transactions.
        
        Args:
            bank_details: Bank account details
            owner_details: Account owner details
            currency: Currency of the bank account
            
        Returns:
            Beneficiary details including ID
        """
        payload = {
            "bank_details": bank_details,
            "owner_details": owner_details,
            "currency": currency
        }
        
        return self._make_request("POST", "/v1/offramp/beneficiaries", data=payload)
    
    def list_beneficiaries(self) -> List[Dict]:
        """
        List all beneficiaries (bank accounts).
        
        Returns:
            List of beneficiary objects
        """
        return self._make_request("GET", "/v1/offramp/beneficiaries")
    
    # Treasury Management Methods
    
    def check_liquidity_status(self, 
                              target_currency: str, 
                              min_liquidity_threshold: float) -> Dict:
        """
        Check if liquidity levels are above the minimum threshold.
        
        Args:
            target_currency: Fiat currency to check
            min_liquidity_threshold: Minimum acceptable liquidity level
            
        Returns:
            Liquidity status details
        """
        # Get account balances
        balances = self._make_request("GET", "/v1/accounts/balances")
        
        # Find the balance for the target currency
        target_balance = next((b for b in balances if b["currency"] == target_currency), None)
        
        if not target_balance:
            return {
                "status": "insufficient",
                "currency": target_currency,
                "current_balance": 0,
                "threshold": min_liquidity_threshold,
                "deficit": min_liquidity_threshold
            }
        
        current_balance = float(target_balance["available"])
        
        if current_balance < min_liquidity_threshold:
            return {
                "status": "insufficient",
                "currency": target_currency,
                "current_balance": current_balance,
                "threshold": min_liquidity_threshold,
                "deficit": min_liquidity_threshold - current_balance
            }
        
        return {
            "status": "sufficient",
            "currency": target_currency,
            "current_balance": current_balance,
            "threshold": min_liquidity_threshold,
            "excess": current_balance - min_liquidity_threshold
        }
    
    def trigger_liquidity_provision(self, 
                                  amount: float,
                                  source_currency: str,
                                  target_currency: str,
                                  beneficiary_id: str) -> Dict:
        """
        Trigger liquidity provision when levels are below threshold.
        
        Args:
            amount: Amount to convert
            source_currency: Source cryptocurrency (e.g., "NVCT")
            target_currency: Target fiat currency (e.g., "USD")
            beneficiary_id: ID of the beneficiary (bank account)
            
        Returns:
            Transaction details
        """
        # Generate a unique external ID for tracking
        external_id = f"liqProvision_{int(time.time())}_{source_currency}_{target_currency}"
        
        # Create the off-ramp transaction
        transaction = self.create_offramp_transaction(
            amount=amount,
            source_currency=source_currency,
            target_currency=target_currency,
            beneficiary_id=beneficiary_id,
            external_id=external_id
        )
        
        # Log the liquidity provision
        logger.info(f"Liquidity provision triggered: {amount} {source_currency} -> {target_currency}")
        logger.info(f"Transaction ID: {transaction['id']}")
        
        return transaction


# Example usage:
if __name__ == "__main__":
    # These would be stored securely and loaded from environment
    BRIDGE_API_KEY = os.getenv("BRIDGE_API_KEY")
    BRIDGE_API_SECRET = os.getenv("BRIDGE_API_SECRET")
    
    if not BRIDGE_API_KEY or not BRIDGE_API_SECRET:
        logger.error("Bridge.xyz API credentials not found in environment")
        exit(1)
    
    # Initialize the integration
    bridge = BridgeXYZIntegration(BRIDGE_API_KEY, BRIDGE_API_SECRET)
    
    # Example: List supported currencies
    try:
        currencies = bridge.get_supported_currencies()
        logger.info(f"Supported currencies: {currencies}")
    except Exception as e:
        logger.error(f"Failed to get supported currencies: {str(e)}")