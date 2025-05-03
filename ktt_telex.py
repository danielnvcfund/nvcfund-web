"""
KTT Telex Integration Module
This module provides functionality for sending and receiving messages via the KTT Telex network.
"""

import json
import logging
import os
import secrets
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union

import requests
from flask import current_app

from models import db, TelexMessage, TelexMessageStatus, Transaction, FinancialInstitution

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelexMessageType:
    """KTT Telex message types"""
    FT = "FT"  # Funds Transfer
    FTC = "FTC"  # Funds Transfer Confirmation
    PO = "PO"  # Payment Order
    PC = "PC"  # Payment Confirmation
    BI = "BI"  # Balance Inquiry
    BR = "BR"  # Balance Response
    GM = "GM"  # General Message
    

class TelexService:
    """Service for interfacing with the KTT Telex network"""
    
    def __init__(self):
        """Initialize the Telex service"""
        self.api_key = os.environ.get('KTT_TELEX_API_KEY', '')
        self.api_secret = os.environ.get('KTT_TELEX_API_SECRET', '')
        self.base_url = os.environ.get('KTT_TELEX_BASE_URL', 'https://api.ktt-telex.example.com/v1')
        self.webhook_secret = os.environ.get('KTT_TELEX_WEBHOOK_SECRET', '')
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests
        
        Returns:
            Dict[str, str]: Headers for the request
        """
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(8)
        
        # In a real implementation, this would create a proper signature
        signature = "demo_signature"  # Placeholder
        
        return {
            "X-KTT-API-Key": self.api_key,
            "X-KTT-Timestamp": timestamp,
            "X-KTT-Nonce": nonce,
            "X-KTT-Signature": signature,
            "Content-Type": "application/json"
        }
    
    def send_telex_message(
        self,
        sender_reference: str,
        recipient_bic: str,
        message_type: str,
        message_content: Dict[str, Any],
        transaction_id: Optional[str] = None,
        priority: str = "NORMAL"
    ) -> Dict[str, Any]:
        """
        Send a message via KTT Telex
        
        Args:
            sender_reference (str): Sender's reference
            recipient_bic (str): Recipient's BIC code
            message_type (str): Type of message (FT, FTC, etc.)
            message_content (Dict[str, Any]): Message content
            transaction_id (Optional[str]): Associated transaction ID
            priority (str): Message priority (HIGH, NORMAL, LOW)
            
        Returns:
            Dict[str, Any]: Response from the API
        """
        logger.info(f"Sending Telex message to {recipient_bic}, type: {message_type}")
        
        # Generate a unique message ID
        message_id = f"KTT-{uuid.uuid4()}"
        
        # Create message record in database
        telex_message = TelexMessage(
            message_id=message_id,
            sender_reference=sender_reference,
            recipient_bic=recipient_bic,
            message_type=message_type,
            message_content=json.dumps(message_content),
            status=TelexMessageStatus.DRAFT,
            priority=priority,
            transaction_id=transaction_id,
        )
        
        try:
            db.session.add(telex_message)
            db.session.commit()
            logger.info(f"Created Telex message record: {message_id}")
        except Exception as e:
            logger.error(f"Error creating Telex message record: {str(e)}")
            return {"error": f"Database error: {str(e)}"}
        
        # In a real implementation, this would send the message to the KTT Telex API
        # For now, we'll just simulate success and update the message status
        
        # Simulate API success response
        telex_message.status = TelexMessageStatus.SENT
        telex_message.sent_at = datetime.utcnow()
        
        try:
            db.session.commit()
            logger.info(f"Updated Telex message status to SENT: {message_id}")
        except Exception as e:
            logger.error(f"Error updating Telex message status: {str(e)}")
            return {"error": f"Database error: {str(e)}"}
        
        # Return success response
        return {
            "success": True,
            "message_id": message_id,
            "status": "SENT"
        }
    
    def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get the status of a message
        
        Args:
            message_id (str): Message ID
            
        Returns:
            Dict[str, Any]: Message status
        """
        logger.info(f"Getting status for Telex message: {message_id}")
        
        # Query the message from the database
        telex_message = TelexMessage.query.filter_by(message_id=message_id).first()
        
        if not telex_message:
            logger.warning(f"Telex message not found: {message_id}")
            return {"error": "Message not found"}
        
        # Return message status
        return {
            "message_id": telex_message.message_id,
            "status": telex_message.status.value,
            "created_at": telex_message.created_at.isoformat() if telex_message.created_at else None,
            "sent_at": telex_message.sent_at.isoformat() if telex_message.sent_at else None,
            "processed_at": telex_message.processed_at.isoformat() if telex_message.processed_at else None
        }
    
    def process_incoming_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming message from the webhook
        
        Args:
            message_data (Dict[str, Any]): Message data
            
        Returns:
            Dict[str, Any]: Processing result
        """
        logger.info(f"Processing incoming Telex message")
        
        # Extract message details
        try:
            message_id = message_data.get('message_id')
            sender_reference = message_data.get('sender_reference')
            sender_bic = message_data.get('sender_bic')
            message_type = message_data.get('message_type')
            message_content = message_data.get('content')
            
            if not all([message_id, sender_reference, sender_bic, message_type, message_content]):
                logger.error("Missing required fields in incoming message")
                return {"error": "Missing required fields"}
            
            # Check if message already exists
            existing_message = TelexMessage.query.filter_by(message_id=message_id).first()
            if existing_message:
                logger.warning(f"Duplicate message received: {message_id}")
                return {"error": "Duplicate message", "message_id": message_id}
            
            # Create new message record
            telex_message = TelexMessage(
                message_id=message_id,
                sender_reference=sender_reference,
                recipient_bic="SELF",  # This is a message to us
                message_type=message_type,
                message_content=json.dumps(message_content) if isinstance(message_content, dict) else message_content,
                status=TelexMessageStatus.RECEIVED,
                priority=message_data.get('priority', 'NORMAL'),
                received_at=datetime.utcnow()
            )
            
            db.session.add(telex_message)
            db.session.commit()
            logger.info(f"Saved incoming Telex message: {message_id}")
            
            # Process message based on type
            if message_type == TelexMessageType.FT:
                # Process funds transfer message
                self._process_funds_transfer(telex_message, message_content)
            elif message_type == TelexMessageType.FTC:
                # Process funds transfer confirmation
                self._process_funds_transfer_confirmation(telex_message, message_content)
            
            return {
                "success": True,
                "message_id": message_id,
                "status": "PROCESSED"
            }
            
        except Exception as e:
            logger.error(f"Error processing incoming message: {str(e)}")
            return {"error": f"Processing error: {str(e)}"}
    
    def _process_funds_transfer(self, message: TelexMessage, content: Dict[str, Any]) -> None:
        """
        Process a funds transfer message
        
        Args:
            message (TelexMessage): The message object
            content (Dict[str, Any]): Message content
        """
        logger.info(f"Processing funds transfer message: {message.message_id}")
        
        # In a real implementation, this would create a transaction record
        # and initiate the funds transfer process
        
        # Update message status
        message.status = TelexMessageStatus.PROCESSED
        message.processed_at = datetime.utcnow()
        
        try:
            db.session.commit()
            logger.info(f"Updated Telex message status to PROCESSED: {message.message_id}")
        except Exception as e:
            logger.error(f"Error updating Telex message status: {str(e)}")
            db.session.rollback()
    
    def _process_funds_transfer_confirmation(self, message: TelexMessage, content: Dict[str, Any]) -> None:
        """
        Process a funds transfer confirmation message
        
        Args:
            message (TelexMessage): The message object
            content (Dict[str, Any]): Message content
        """
        logger.info(f"Processing funds transfer confirmation message: {message.message_id}")
        
        # Find the associated transaction by reference
        reference = content.get('reference')
        if reference:
            # Update transaction status if found
            transaction = Transaction.query.filter_by(reference_id=reference).first()
            if transaction:
                logger.info(f"Found associated transaction: {transaction.transaction_id}")
                
                # Update transaction status
                status = content.get('status')
                if status == 'COMPLETED':
                    transaction.status = 'COMPLETED'
                elif status == 'FAILED':
                    transaction.status = 'FAILED'
                
                # Update message and transaction
                message.transaction_id = transaction.transaction_id
                message.status = TelexMessageStatus.PROCESSED
                message.processed_at = datetime.utcnow()
                
                try:
                    db.session.commit()
                    logger.info(f"Updated transaction status: {transaction.transaction_id}")
                except Exception as e:
                    logger.error(f"Error updating transaction status: {str(e)}")
                    db.session.rollback()
            else:
                logger.warning(f"No transaction found for reference: {reference}")
        else:
            logger.warning("No reference in funds transfer confirmation message")
    
    def create_funds_transfer_message(self, transaction: Transaction, recipient_institution: FinancialInstitution) -> Dict[str, Any]:
        """
        Create and send a funds transfer message for a transaction
        
        Args:
            transaction (Transaction): The transaction
            recipient_institution (FinancialInstitution): The recipient institution
            
        Returns:
            Dict[str, Any]: Response from the send_telex_message method
        """
        logger.info(f"Creating funds transfer message for transaction: {transaction.transaction_id}")
        
        # Generate a reference
        reference = f"FT-{transaction.transaction_id}"
        
        # Create message content
        content = {
            "reference": reference,
            "transaction_id": transaction.transaction_id,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "sender_name": transaction.sender_name,
            "sender_account": transaction.sender_account_number if hasattr(transaction, 'sender_account_number') else None,
            "recipient_name": transaction.recipient_name,
            "recipient_account": transaction.recipient_account_number if hasattr(transaction, 'recipient_account_number') else None,
            "value_date": datetime.utcnow().strftime('%Y-%m-%d'),
            "details": transaction.description,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Update transaction reference ID
        transaction.reference_id = reference
        
        try:
            db.session.commit()
            logger.info(f"Updated transaction reference ID: {reference}")
        except Exception as e:
            logger.error(f"Error updating transaction reference ID: {str(e)}")
            db.session.rollback()
            return {"error": f"Database error: {str(e)}"}
        
        # Send the message
        return self.send_telex_message(
            sender_reference=reference,
            recipient_bic=recipient_institution.swift_code,
            message_type=TelexMessageType.FT,
            message_content=content,
            transaction_id=transaction.transaction_id,
            priority="HIGH"
        )
    
    def create_payment_confirmation_message(self, transaction: Transaction, recipient_institution: FinancialInstitution) -> Dict[str, Any]:
        """
        Create and send a payment confirmation message for a transaction
        
        Args:
            transaction (Transaction): The transaction
            recipient_institution (FinancialInstitution): The recipient institution
            
        Returns:
            Dict[str, Any]: Response from the send_telex_message method
        """
        logger.info(f"Creating payment confirmation message for transaction: {transaction.transaction_id}")
        
        # Generate a reference
        reference = f"PC-{transaction.transaction_id}"
        
        # Create message content
        content = {
            "reference": reference,
            "transaction_id": transaction.transaction_id,
            "original_reference": transaction.reference_id,
            "status": transaction.status,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "settlement_date": datetime.utcnow().strftime('%Y-%m-%d'),
            "settlement_time": datetime.utcnow().strftime('%H:%M:%S'),
            "recipient_name": transaction.recipient_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send the message
        return self.send_telex_message(
            sender_reference=reference,
            recipient_bic=recipient_institution.swift_code,
            message_type=TelexMessageType.PC,
            message_content=content,
            transaction_id=transaction.transaction_id,
            priority="NORMAL"
        )


# Instance cache
_telex_service = None

def get_telex_service() -> TelexService:
    """
    Get the KTT Telex service instance
    
    Returns:
        TelexService: The service instance
    """
    global _telex_service
    
    if _telex_service is None:
        _telex_service = TelexService()
    
    return _telex_service