"""
ACH (Automated Clearing House) Service
This module provides functionality for processing ACH transfers within the US banking system.
"""
import json
import logging
import uuid
import os
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from models import Transaction, TransactionStatus, TransactionType, User, db
from utils import generate_uuid
from email_service import send_transaction_confirmation_email
from pdf_service import pdf_service

logger = logging.getLogger(__name__)

# ACH Entry Class Codes
ACH_ENTRY_CLASSES = {
    'PPD': 'Prearranged Payment and Deposit',
    'CCD': 'Corporate Credit or Debit',
    'WEB': 'Internet-Initiated/Mobile Entry',
    'TEL': 'Telephone-Initiated Entry',
    'CIE': 'Customer Initiated Entry',
    'BOC': 'Back Office Conversion',
    'POP': 'Point-of-Purchase Entry',
    'ARC': 'Accounts Receivable Entry'
}

# ACH Transaction Codes
ACH_TRANSACTION_CODES = {
    '22': 'Checking Account Credit',
    '23': 'Checking Account Debit (Pre-note)',
    '27': 'Checking Account Debit',
    '32': 'Savings Account Credit',
    '33': 'Savings Account Credit (Pre-note)',
    '37': 'Savings Account Debit',
    '52': 'Business Account Credit',
    '53': 'Business Account Credit (Pre-note)',
    '57': 'Business Account Debit'
}

class ACHService:
    """Service for handling ACH transfers"""
    
    @staticmethod
    def create_ach_transfer(
            user_id,
            amount,
            currency="USD",
            recipient_name=None,
            recipient_address_line1=None,
            recipient_address_line2=None,
            recipient_city=None,
            recipient_state=None,
            recipient_zip=None,
            recipient_bank_name=None,
            recipient_bank_address=None,
            recipient_account_number=None,
            recipient_routing_number=None,
            recipient_account_type="checking",
            entry_class_code="PPD",
            effective_date=None,
            description=None,
            recurring=False,
            recurring_frequency=None,
            company_entry_description=None,
            sender_account_type="checking",
            sender_name=None,
            sender_identification=None,
            batch_id=None,
            **additional_metadata
        ):
        """
        Create a new ACH transfer
        
        Args:
            user_id (int): User ID initiating the transfer
            amount (float): Amount to transfer
            currency (str): Currency code (default: USD)
            recipient_name (str): Name of the recipient
            recipient_address_line1 (str): First line of recipient's address
            recipient_address_line2 (str): Second line of recipient's address
            recipient_city (str): Recipient's city
            recipient_state (str): Recipient's state or province
            recipient_zip (str): Recipient's ZIP or postal code
            recipient_bank_name (str): Name of the recipient's bank
            recipient_bank_address (str): Address of the recipient's bank
            recipient_account_number (str): Account number of the recipient
            recipient_routing_number (str): Routing number of the recipient's bank
            recipient_account_type (str): Type of the recipient's account (checking, savings)
            entry_class_code (str): ACH Entry Class Code (PPD, CCD, etc.)
            effective_date (datetime): Date when the transfer should be processed
            description (str): Description of the transfer
            recurring (bool): Whether this is a recurring transfer
            recurring_frequency (str): Frequency for recurring transfers (daily, weekly, monthly)
            company_entry_description (str): Description that appears on the recipient's statement
            sender_account_type (str): Type of the sender's account (checking, savings)
            sender_name (str): Name of the sender
            sender_identification (str): Identification of the sender (tax ID, etc.)
            batch_id (str): ID for batch processing
            **additional_metadata: Additional metadata for the transfer
            
        Returns:
            Transaction: Created transaction object
        """
        try:
            # Validate input parameters
            if not recipient_routing_number or len(recipient_routing_number) != 9:
                raise ValueError("Invalid routing number. Must be 9 digits.")
            
            if not recipient_account_number:
                raise ValueError("Recipient account number is required.")
            
            if entry_class_code not in ACH_ENTRY_CLASSES:
                raise ValueError(f"Invalid entry class code: {entry_class_code}")
            
            # Generate transaction ID
            transaction_id = generate_uuid()
            
            # Set default effective date if not provided
            if not effective_date:
                # ACH typically takes 1-3 business days to process
                effective_date = datetime.utcnow() + timedelta(days=2)
            
            # Determine transaction code based on account type
            transaction_code = None
            if recipient_account_type.lower() == "checking":
                transaction_code = "22"  # Checking credit
            elif recipient_account_type.lower() == "savings":
                transaction_code = "32"  # Savings credit
            elif recipient_account_type.lower() == "business":
                transaction_code = "52"  # Business credit
            
            # Set default company entry description
            if not company_entry_description:
                company_entry_description = description[:10] if description else "PAYMENT"
            
            # Create metadata dictionary
            metadata = {
                # Recipient Details
                "recipient_address_line1": recipient_address_line1,
                "recipient_address_line2": recipient_address_line2,
                "recipient_city": recipient_city,
                "recipient_state": recipient_state,
                "recipient_zip": recipient_zip,
                "recipient_bank_name": recipient_bank_name,
                "recipient_bank_address": recipient_bank_address,
                
                # ACH Transaction Details
                "entry_class_code": entry_class_code,
                "transaction_code": transaction_code,
                "recipient_account_type": recipient_account_type,
                "recipient_routing_number": recipient_routing_number,
                "effective_date": effective_date.isoformat() if effective_date else None,
                "recurring": recurring,
                "recurring_frequency": recurring_frequency,
                "company_entry_description": company_entry_description,
                "sender_account_type": sender_account_type,
                "sender_name": sender_name,
                "sender_identification": sender_identification,
                "batch_id": batch_id,
            }
            
            # Add any additional metadata
            metadata.update(additional_metadata)
            
            # Create the transaction
            transaction = Transaction(
                transaction_id=transaction_id,
                user_id=user_id,
                amount=amount,
                currency=currency,
                transaction_type=TransactionType.EDI_ACH_TRANSFER,
                status=TransactionStatus.PENDING,
                description=description,
                recipient_name=recipient_name,
                recipient_account=recipient_account_number,
                tx_metadata_json=json.dumps(metadata)
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            # Send confirmation email to the user
            try:
                user = User.query.get(user_id)
                if user:
                    send_transaction_confirmation_email(user, transaction)
            except Exception as e:
                logger.error(f"Failed to send confirmation email: {str(e)}")
            
            return transaction
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating ACH transfer: {str(e)}")
            raise
    
    @staticmethod
    def get_ach_transfer_status(transaction_id):
        """
        Get the status of an ACH transfer
        
        Args:
            transaction_id (str): Transaction ID
            
        Returns:
            dict: Status of the transfer
        """
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            logger.error(f"Transaction not found: {transaction_id}")
            return {"status": "ERROR", "message": "Transaction not found"}
        
        if transaction.transaction_type != TransactionType.EDI_ACH_TRANSFER:
            logger.error(f"Transaction is not an ACH transfer: {transaction_id}")
            return {"status": "ERROR", "message": "Transaction is not an ACH transfer"}
        
        # Extract metadata
        metadata = {}
        if transaction.tx_metadata_json:
            try:
                metadata = json.loads(transaction.tx_metadata_json)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse transaction metadata for {transaction_id}")
        
        # Get the effective date from metadata
        effective_date = None
        if metadata.get("effective_date"):
            try:
                effective_date = datetime.fromisoformat(metadata["effective_date"])
            except ValueError:
                logger.error(f"Invalid effective date format for {transaction_id}")
        
        # For simplicity, we're just returning the transaction status
        # In a real system, you would query the ACH network for real-time status
        status_info = {
            "status": transaction.status.value,
            "transaction_id": transaction.transaction_id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            
            # Recipient Personal Info
            "recipient": transaction.recipient_name,
            "recipient_address_line1": metadata.get("recipient_address_line1"),
            "recipient_address_line2": metadata.get("recipient_address_line2"),
            "recipient_city": metadata.get("recipient_city"),
            "recipient_state": metadata.get("recipient_state"),
            "recipient_zip": metadata.get("recipient_zip"),
            
            # Recipient Bank Info
            "recipient_bank_name": metadata.get("recipient_bank_name"),
            "recipient_bank_address": metadata.get("recipient_bank_address"),
            
            # Transaction Details
            "description": transaction.description,
            "entry_class_code": metadata.get("entry_class_code"),
            "transaction_code": metadata.get("transaction_code"),
            "effective_date": effective_date.strftime('%Y-%m-%d') if effective_date else None,
            "trace_number": metadata.get("trace_number"),
            "created_at": transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "updated_at": transaction.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add routing transit number (masked for security)
        if metadata.get("recipient_routing_number"):
            routing_number = metadata["recipient_routing_number"]
            masked_routing = f"{routing_number[:3]}****{routing_number[-2:]}"
            status_info["routing_number"] = masked_routing
        
        # Add estimated completion time
        if transaction.status == TransactionStatus.PENDING and effective_date:
            status_info["estimated_completion"] = effective_date.strftime('%Y-%m-%d')
        
        return status_info
    
    @staticmethod
    def cancel_ach_transfer(transaction_id, user_id):
        """
        Cancel an ACH transfer if it's still pending
        
        Args:
            transaction_id (str): Transaction ID
            user_id (int): User ID making the cancellation request
            
        Returns:
            bool: True if cancelled successfully, False otherwise
        """
        transaction = Transaction.query.filter_by(
            transaction_id=transaction_id, 
            user_id=user_id
        ).first()
        
        if not transaction:
            logger.error(f"Transaction not found or not owned by user: {transaction_id}, {user_id}")
            return False
        
        if transaction.transaction_type != TransactionType.EDI_ACH_TRANSFER:
            logger.error(f"Transaction is not an ACH transfer: {transaction_id}")
            return False
        
        if transaction.status != TransactionStatus.PENDING:
            logger.error(f"Cannot cancel transaction that is not pending: {transaction_id}")
            return False
        
        try:
            # In a real system, you would also need to submit a cancellation to the ACH network
            # Cancel the transaction
            transaction.status = TransactionStatus.CANCELLED
            db.session.commit()
            
            # Log the cancellation
            logger.info(f"ACH transfer cancelled: {transaction_id} by user {user_id}")
            
            # Notify the user
            try:
                user = User.query.get(user_id)
                if user:
                    # This would typically send an email notification
                    pass
            except Exception as e:
                logger.error(f"Failed to notify user of cancellation: {str(e)}")
            
            return True
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cancelling ACH transfer: {str(e)}")
            return False
    
    @staticmethod
    def validate_routing_number(routing_number):
        """
        Validate an ABA routing number using the checksum algorithm
        
        Args:
            routing_number (str): Routing number to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not routing_number or not routing_number.isdigit() or len(routing_number) != 9:
            return False
        
        # ABA routing number validation algorithm
        d = [int(routing_number[i]) for i in range(9)]
        
        checksum = (
            3 * (d[0] + d[3] + d[6]) +
            7 * (d[1] + d[4] + d[7]) +
            (d[2] + d[5] + d[8])
        ) % 10
        
        return checksum == 0
    
    @staticmethod
    def generate_transaction_pdf(transaction_id, save_path=None):
        """
        Generate a PDF receipt for an ACH transaction
        
        Args:
            transaction_id (str): Transaction ID
            save_path (str, optional): Path to save the PDF. If None, the PDF is returned as bytes.
            
        Returns:
            bytes or str: PDF document as bytes or path where the PDF was saved
        """
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            logger.error(f"Transaction not found: {transaction_id}")
            raise ValueError(f"Transaction not found: {transaction_id}")
        
        if transaction.transaction_type != TransactionType.EDI_ACH_TRANSFER:
            logger.error(f"Transaction is not an ACH transfer: {transaction_id}")
            raise ValueError(f"Transaction is not an ACH transfer: {transaction_id}")
        
        try:
            # Get the user who initiated the transaction
            user = User.query.get(transaction.user_id)
            sender_name = f"{user.first_name} {user.last_name}" if user and user.first_name and user.last_name else None
            
            # Extract metadata
            metadata = {}
            if transaction.tx_metadata_json:
                try:
                    metadata = json.loads(transaction.tx_metadata_json)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse transaction metadata for {transaction_id}")
            
            # Add sender info to metadata if available
            if sender_name:
                metadata["sender_name"] = sender_name
            
            # Set entry class code description
            if metadata.get("entry_class_code") in ACH_ENTRY_CLASSES:
                metadata["entry_class_code_description"] = ACH_ENTRY_CLASSES[metadata["entry_class_code"]]
            
            # Set transaction code description
            if metadata.get("transaction_code") in ACH_TRANSACTION_CODES:
                metadata["transaction_code_description"] = ACH_TRANSACTION_CODES[metadata["transaction_code"]]
            
            # Generate the PDF
            pdf_data = pdf_service.generate_ach_transaction_pdf(transaction, metadata)
            
            # If save_path is provided, save the PDF to disk
            if save_path:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
                
                # If no extension provided, add .pdf
                if not save_path.lower().endswith('.pdf'):
                    save_path += '.pdf'
                
                # Save the PDF
                with open(save_path, 'wb') as f:
                    f.write(pdf_data)
                
                logger.info(f"ACH transaction PDF saved to {save_path}")
                return save_path
            
            # Otherwise return the PDF data
            return pdf_data
            
        except Exception as e:
            logger.error(f"Error generating ACH transaction PDF: {str(e)}")
            raise

# Create a global instance
ach_service = ACHService()