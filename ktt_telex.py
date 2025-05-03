"""
KTT Telex Integration Module
This module provides functionality for integrating with KTT Telex system 
for secure financial messaging.

KTT Telex serves as a communication system for financial institutions, 
allowing them to exchange standardized financial messages.
"""

import os
import logging
import requests
import json
import hashlib
import hmac
import time
from datetime import datetime
from flask import current_app
from models import db, Transaction, TelexMessage, FinancialInstitution, User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for Telex message types
class TelexMessageType:
    FUNDS_TRANSFER = "FT"
    FUNDS_TRANSFER_CONFIRMATION = "FTC"
    PAYMENT_ORDER = "PO"
    PAYMENT_CONFIRMATION = "PC"
    ACCOUNT_STATEMENT = "AS"
    BALANCE_INQUIRY = "BI"
    BALANCE_RESPONSE = "BR"
    STATUS_INQUIRY = "SI"
    STATUS_RESPONSE = "SR"
    GENERAL_MESSAGE = "GM"
    ADVICE_MESSAGE = "AM"


class KTTTelexService:
    """Service for handling KTT Telex communications"""
    
    def __init__(self, api_key=None, api_secret=None, base_url=None):
        """
        Initialize the KTT Telex service
        
        Args:
            api_key (str): API key for KTT Telex
            api_secret (str): API secret for KTT Telex
            base_url (str): Base URL for the KTT Telex API
        """
        self.api_key = api_key or os.environ.get("KTT_TELEX_API_KEY")
        self.api_secret = api_secret or os.environ.get("KTT_TELEX_API_SECRET")
        self.base_url = base_url or os.environ.get("KTT_TELEX_BASE_URL", "https://api.ktt-telex.example.com/v1")
        
        if not all([self.api_key, self.api_secret, self.base_url]):
            logger.warning("KTT Telex credentials or base URL not fully configured")
    
    def _generate_auth_header(self, request_path, method, timestamp=None):
        """
        Generate authentication headers for KTT Telex API
        
        Args:
            request_path (str): API endpoint path
            method (str): HTTP method (GET, POST, etc.)
            timestamp (int, optional): Timestamp for the request
            
        Returns:
            dict: Headers for the request
        """
        timestamp = timestamp or int(time.time() * 1000)
        message = f"{timestamp}{method}{request_path}"
        
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "KTT-API-KEY": self.api_key,
            "KTT-SIGNATURE": signature,
            "KTT-TIMESTAMP": str(timestamp),
            "Content-Type": "application/json"
        }
    
    def send_telex_message(self, sender_reference, recipient_bic, message_type, 
                          message_content, transaction_id=None, priority="NORMAL"):
        """
        Send a Telex message
        
        Args:
            sender_reference (str): Sender's reference number
            recipient_bic (str): BIC code of the recipient institution
            message_type (str): Type of message (use TelexMessageType constants)
            message_content (dict): Content of the message
            transaction_id (str, optional): Associated transaction ID
            priority (str): Message priority (HIGH, NORMAL, LOW)
            
        Returns:
            dict: Response from the KTT Telex API
        """
        endpoint = "/messages"
        url = f"{self.base_url}{endpoint}"
        
        payload = {
            "sender_reference": sender_reference,
            "recipient_bic": recipient_bic,
            "message_type": message_type,
            "message_content": message_content,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if transaction_id:
            payload["transaction_id"] = transaction_id
        
        headers = self._generate_auth_header(endpoint, "POST")
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            # Store the message in the database
            self._store_telex_message(payload, response.json().get("message_id"))
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Telex message: {str(e)}")
            return {"error": str(e), "status": "failed"}
    
    def _store_telex_message(self, message_data, message_id):
        """
        Store a Telex message in the database
        
        Args:
            message_data (dict): Message data
            message_id (str): Message ID from KTT Telex
        """
        try:
            telex_message = TelexMessage(
                message_id=message_id,
                sender_reference=message_data.get("sender_reference"),
                recipient_bic=message_data.get("recipient_bic"),
                message_type=message_data.get("message_type"),
                message_content=json.dumps(message_data.get("message_content")),
                priority=message_data.get("priority"),
                transaction_id=message_data.get("transaction_id"),
                status="SENT",
                created_at=datetime.utcnow()
            )
            
            db.session.add(telex_message)
            db.session.commit()
            logger.info(f"Telex message stored with ID: {message_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing Telex message: {str(e)}")
    
    def get_telex_message(self, message_id):
        """
        Get a Telex message by ID
        
        Args:
            message_id (str): Message ID
            
        Returns:
            dict: Message details from the KTT Telex API
        """
        endpoint = f"/messages/{message_id}"
        url = f"{self.base_url}{endpoint}"
        
        headers = self._generate_auth_header(endpoint, "GET")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting Telex message: {str(e)}")
            return {"error": str(e), "status": "failed"}
    
    def search_telex_messages(self, sender_reference=None, recipient_bic=None, message_type=None,
                            start_date=None, end_date=None, status=None, limit=100):
        """
        Search for Telex messages
        
        Args:
            sender_reference (str, optional): Sender's reference number
            recipient_bic (str, optional): BIC code of the recipient institution
            message_type (str, optional): Type of message
            start_date (str, optional): Start date for search (ISO format)
            end_date (str, optional): End date for search (ISO format)
            status (str, optional): Message status
            limit (int, optional): Maximum number of messages to return
            
        Returns:
            dict: Search results from the KTT Telex API
        """
        endpoint = "/messages/search"
        url = f"{self.base_url}{endpoint}"
        
        params = {"limit": limit}
        if sender_reference:
            params["sender_reference"] = sender_reference
        if recipient_bic:
            params["recipient_bic"] = recipient_bic
        if message_type:
            params["message_type"] = message_type
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if status:
            params["status"] = status
        
        headers = self._generate_auth_header(endpoint, "GET")
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching Telex messages: {str(e)}")
            return {"error": str(e), "status": "failed"}
    
    def create_funds_transfer_message(self, transaction, recipient_institution):
        """
        Create a funds transfer message
        
        Args:
            transaction (Transaction): The transaction object
            recipient_institution (FinancialInstitution): The recipient institution
            
        Returns:
            dict: Response from the KTT Telex API
        """
        if not transaction or not recipient_institution:
            logger.error("Transaction or recipient institution not provided")
            return {"error": "Transaction or recipient institution not provided", "status": "failed"}
        
        # Generate a unique sender reference
        sender_reference = f"FT{transaction.transaction_id[-8:]}{int(time.time())}"
        
        # Prepare message content
        message_content = {
            "transaction_id": transaction.transaction_id,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "value_date": transaction.created_at.strftime("%Y-%m-%d"),
            "sender_account": transaction.sender_account_number,
            "recipient_account": transaction.recipient_account_number,
            "sender_name": transaction.sender_name,
            "recipient_name": transaction.recipient_name,
            "payment_details": transaction.description or "Fund Transfer"
        }
        
        # Send the message
        return self.send_telex_message(
            sender_reference=sender_reference,
            recipient_bic=recipient_institution.swift_code,
            message_type=TelexMessageType.FUNDS_TRANSFER,
            message_content=message_content,
            transaction_id=transaction.transaction_id,
            priority="NORMAL"
        )
    
    def create_payment_confirmation_message(self, transaction, recipient_institution):
        """
        Create a payment confirmation message
        
        Args:
            transaction (Transaction): The transaction object
            recipient_institution (FinancialInstitution): The recipient institution
            
        Returns:
            dict: Response from the KTT Telex API
        """
        if not transaction or not recipient_institution:
            logger.error("Transaction or recipient institution not provided")
            return {"error": "Transaction or recipient institution not provided", "status": "failed"}
        
        # Generate a unique sender reference
        sender_reference = f"PC{transaction.transaction_id[-8:]}{int(time.time())}"
        
        # Prepare message content
        message_content = {
            "transaction_id": transaction.transaction_id,
            "status": "COMPLETED",
            "settlement_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "settlement_time": datetime.utcnow().strftime("%H:%M:%S"),
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "sender_account": transaction.sender_account_number,
            "recipient_account": transaction.recipient_account_number,
            "confirmation_reference": f"CONF-{transaction.transaction_id[-6:]}"
        }
        
        # Send the message
        return self.send_telex_message(
            sender_reference=sender_reference,
            recipient_bic=recipient_institution.swift_code,
            message_type=TelexMessageType.PAYMENT_CONFIRMATION,
            message_content=message_content,
            transaction_id=transaction.transaction_id,
            priority="NORMAL"
        )
    
    def process_incoming_message(self, message_data):
        """
        Process an incoming Telex message
        
        Args:
            message_data (dict): Message data
            
        Returns:
            dict: Processing result
        """
        message_type = message_data.get("message_type")
        message_content = message_data.get("message_content")
        
        if not message_type or not message_content:
            return {"error": "Invalid message format", "status": "failed"}
        
        try:
            # Store the message
            telex_message = TelexMessage(
                message_id=message_data.get("message_id"),
                sender_reference=message_data.get("sender_reference"),
                recipient_bic=message_data.get("recipient_bic"),
                message_type=message_type,
                message_content=json.dumps(message_content),
                priority=message_data.get("priority", "NORMAL"),
                transaction_id=message_content.get("transaction_id"),
                status="RECEIVED",
                created_at=datetime.utcnow()
            )
            
            db.session.add(telex_message)
            db.session.commit()
            
            # Process based on message type
            if message_type == TelexMessageType.FUNDS_TRANSFER:
                return self._process_funds_transfer(message_content)
            elif message_type == TelexMessageType.PAYMENT_CONFIRMATION:
                return self._process_payment_confirmation(message_content)
            else:
                logger.info(f"Received message of type {message_type}, no specific processing required")
                return {"status": "success", "message": "Message received"}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing incoming message: {str(e)}")
            return {"error": str(e), "status": "failed"}
    
    def _process_funds_transfer(self, message_content):
        """
        Process a funds transfer message
        
        Args:
            message_content (dict): Message content
            
        Returns:
            dict: Processing result
        """
        # Implementation would depend on your specific business logic
        # This is a basic example
        
        transaction_id = message_content.get("transaction_id")
        amount = message_content.get("amount")
        currency = message_content.get("currency")
        recipient_account = message_content.get("recipient_account")
        
        logger.info(f"Processing funds transfer: {transaction_id}, {amount} {currency} to {recipient_account}")
        
        # Create a transaction record if it doesn't exist
        # In a real implementation, you would validate the recipient account, check balances, etc.
        
        return {"status": "success", "message": "Funds transfer processed"}
    
    def _process_payment_confirmation(self, message_content):
        """
        Process a payment confirmation message
        
        Args:
            message_content (dict): Message content
            
        Returns:
            dict: Processing result
        """
        transaction_id = message_content.get("transaction_id")
        status = message_content.get("status")
        
        if not transaction_id:
            return {"error": "Transaction ID not provided", "status": "failed"}
        
        try:
            # Update the transaction status
            transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
            
            if transaction:
                if status == "COMPLETED":
                    transaction.status = "COMPLETED"
                elif status == "FAILED":
                    transaction.status = "FAILED"
                else:
                    transaction.status = "PROCESSING"
                
                db.session.commit()
                logger.info(f"Updated transaction {transaction_id} status to {status}")
                return {"status": "success", "message": f"Transaction status updated to {status}"}
            else:
                logger.warning(f"Transaction {transaction_id} not found")
                return {"error": "Transaction not found", "status": "failed"}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating transaction status: {str(e)}")
            return {"error": str(e), "status": "failed"}

# Create a singleton instance
telex_service = KTTTelexService()

def get_telex_service():
    """Get the KTT Telex service instance"""
    return telex_service