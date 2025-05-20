"""
Mojoloop API Integration for NVC Banking Platform

This module provides client functionality for interacting with Mojoloop APIs, enabling real-time
payment processing in compliance with the Level One Principles.

Key capabilities:
1. Transaction initiation
2. Quote handling
3. Transfer processing
4. Transaction status tracking
5. Party lookup
"""

import os
import json
import uuid
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

# Configure logging
logger = logging.getLogger(__name__)

class MojolloopClient:
    """Client for interfacing with the Mojoloop API"""
    
    def __init__(self, base_url: str, 
                 client_id: Optional[str] = None, 
                 client_secret: Optional[str] = None,
                 dfsp_id: Optional[str] = None,
                 timeout: int = 30):
        """
        Initialize the Mojoloop client
        
        Args:
            base_url: Base URL for the Mojoloop API
            client_id: Client ID for authentication (optional)
            client_secret: Client secret for authentication (optional)
            dfsp_id: Digital Financial Service Provider ID
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id or os.environ.get("MOJOLOOP_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("MOJOLOOP_CLIENT_SECRET", "")
        self.dfsp_id = dfsp_id or os.environ.get("MOJOLOOP_DFSP_ID", "")
        self.timeout = timeout
        self.auth_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        
        # Validate configuration
        if not self.base_url:
            raise ValueError("Mojoloop API base URL is required")
        
        if not self.dfsp_id:
            raise ValueError("DFSP ID is required for Mojoloop integration")
    
    def _get_headers(self, additional_headers: Dict[str, str] = None) -> Dict[str, str]:
        """
        Get request headers including authentication
        
        Args:
            additional_headers: Additional headers to include in the request
            
        Returns:
            Dictionary of headers
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Date": datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            "FSPIOP-Source": self.dfsp_id,
        }
        
        # Add authorization if available
        if self._get_auth_token():
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        # Add additional headers
        if additional_headers:
            headers.update(additional_headers)
            
        return headers
    
    def _get_auth_token(self) -> str:
        """
        Get authentication token, refreshing if necessary
        
        Returns:
            Current valid authentication token
        """
        # If we have a token and it's not expired, use it
        if self.auth_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            return self.auth_token
        
        # Otherwise, get a new token if credentials are available
        if self.client_id and self.client_secret:
            token_url = f"{self.base_url}/token"
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            try:
                response = requests.post(token_url, json=data, timeout=self.timeout)
                response.raise_for_status()
                token_data = response.json()
                
                self.auth_token = token_data.get("access_token")
                # Set expiry with some buffer time
                expires_in = token_data.get("expires_in", 3600)
                self.token_expiry = datetime.utcnow().fromtimestamp(
                    datetime.utcnow().timestamp() + expires_in - 300  # 5-minute buffer
                )
                
                return self.auth_token
            except Exception as e:
                logger.error(f"Error obtaining Mojoloop authentication token: {str(e)}")
                return None
        
        return None
    
    def _make_request(self, method: str, endpoint: str, data: Any = None, 
                     params: Dict[str, str] = None,
                     headers: Dict[str, str] = None) -> requests.Response:
        """
        Make a request to the Mojoloop API
        
        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            endpoint: API endpoint to call
            data: Request payload
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Response object
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = self._get_headers(headers)
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data if data else None,
                params=params,
                headers=request_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Mojoloop API request failed: {str(e)}")
            raise
    
    def lookup_party(self, id_type: str, id_value: str) -> Dict[str, Any]:
        """
        Look up a party by identifier
        
        Args:
            id_type: Type of identifier (MSISDN, IBAN, etc.)
            id_value: Value of the identifier
            
        Returns:
            Party information if found
        """
        endpoint = f"parties/{id_type}/{id_value}"
        response = self._make_request("GET", endpoint)
        return response.json()
    
    def get_quote(self, quote_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request a quote for a transaction
        
        Args:
            quote_request: Quote request payload
            
        Returns:
            Quote information
        """
        # Generate a quote ID if not provided
        if "quoteId" not in quote_request:
            quote_request["quoteId"] = str(uuid.uuid4())
        
        endpoint = "quotes"
        response = self._make_request("POST", endpoint, data=quote_request)
        return response.json()
    
    def prepare_transfer(self, transfer_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare a transfer
        
        Args:
            transfer_request: Transfer request payload
            
        Returns:
            Transfer preparation response
        """
        # Generate a transfer ID if not provided
        if "transferId" not in transfer_request:
            transfer_request["transferId"] = str(uuid.uuid4())
        
        endpoint = "transfers"
        response = self._make_request("POST", endpoint, data=transfer_request)
        return response.json()
    
    def get_transfer_status(self, transfer_id: str) -> Dict[str, Any]:
        """
        Get the status of a transfer
        
        Args:
            transfer_id: ID of the transfer
            
        Returns:
            Transfer status information
        """
        endpoint = f"transfers/{transfer_id}"
        response = self._make_request("GET", endpoint)
        return response.json()
    
    def create_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create and process a transaction through Mojoloop
        
        This is a higher-level method that handles the entire transaction flow:
        1. Party lookup
        2. Quote request
        3. Transfer preparation
        4. Transfer fulfillment
        
        Args:
            transaction_data: Transaction data including payer, payee, and amount details
            
        Returns:
            Transaction result with all associated data
        """
        try:
            # 1. Lookup payee party if needed
            payee = transaction_data.get("payee", {})
            if payee.get("partyIdInfo", {}).get("partyIdType") and not payee.get("name"):
                payee_id_type = payee["partyIdInfo"]["partyIdType"]
                payee_id_value = payee["partyIdInfo"]["partyId"]
                
                party_info = self.lookup_party(payee_id_type, payee_id_value)
                payee.update(party_info)
                transaction_data["payee"] = payee
            
            # 2. Request quote
            quote_request = {
                "quoteId": str(uuid.uuid4()),
                "transactionId": transaction_data.get("transactionId", str(uuid.uuid4())),
                "payer": transaction_data.get("payer"),
                "payee": transaction_data.get("payee"),
                "amountType": "SEND",
                "amount": transaction_data.get("amount"),
                "transactionType": transaction_data.get("transactionType", {
                    "scenario": "TRANSFER",
                    "initiator": "PAYER",
                    "initiatorType": "CONSUMER"
                }),
                "note": transaction_data.get("note")
            }
            
            quote_response = self.get_quote(quote_request)
            
            # 3. Prepare transfer
            transfer_request = {
                "transferId": str(uuid.uuid4()),
                "quoteId": quote_response.get("quoteId"),
                "payerFsp": self.dfsp_id,
                "payeeFsp": quote_response.get("payeeFsp"),
                "amount": quote_response.get("transferAmount"),
                "ilpPacket": quote_response.get("ilpPacket"),
                "condition": quote_response.get("condition"),
                "expiration": quote_response.get("expiration")
            }
            
            transfer_response = self.prepare_transfer(transfer_request)
            
            # 4. Return compiled transaction result
            return {
                "transactionId": quote_request.get("transactionId"),
                "quoteId": quote_response.get("quoteId"),
                "transferId": transfer_response.get("transferId"),
                "status": transfer_response.get("status", "PENDING"),
                "completedTimestamp": transfer_response.get("completedTimestamp"),
                "payerDetails": transaction_data.get("payer"),
                "payeeDetails": transaction_data.get("payee"),
                "amount": transaction_data.get("amount"),
                "fees": quote_response.get("payeeFspFee"),
                "commission": quote_response.get("payeeFspCommission")
            }
            
        except Exception as e:
            logger.error(f"Error processing Mojoloop transaction: {str(e)}")
            raise