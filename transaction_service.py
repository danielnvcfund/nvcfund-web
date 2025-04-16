"""
Transaction service for the NVC Banking Platform
This module handles transaction processing, status updates, and notifications
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Union

from app import db
from models import User, Transaction, TransactionStatus, TransactionType
from email_service import send_transaction_confirmation_email

logger = logging.getLogger(__name__)

def create_transaction(
    user_id: int,
    amount: float,
    currency: str,
    transaction_type: Union[str, TransactionType],
    description: Optional[str] = None,
    send_email: bool = True
) -> Tuple[Optional[Transaction], Optional[str]]:
    """
    Create a new transaction record
    
    Args:
        user_id (int): User ID
        amount (float): Transaction amount
        currency (str): Currency code (e.g., USD, EUR)
        transaction_type (str): Transaction type
        description (str, optional): Transaction description
        send_email (bool): Whether to send confirmation email
        
    Returns:
        Tuple[Transaction, Optional[str]]: Transaction object and error message if any
    """
    try:
        # Get user
        user = User.query.get(user_id)
        if not user:
            return None, "User not found"
        
        # Generate unique transaction ID
        transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}-{int(datetime.now().timestamp())}"
        
        # Create transaction
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            transaction_type=transaction_type,
            status=TransactionStatus.PENDING,
            description=description
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        # Send email notification if requested
        if send_email:
            try:
                success = send_transaction_confirmation_email(user, transaction)
                if not success:
                    logger.warning(f"Failed to send transaction confirmation email for {transaction_id}")
            except Exception as e:
                logger.error(f"Error sending transaction email: {str(e)}")
        
        return transaction, None
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating transaction: {str(e)}")
        return None, f"Failed to create transaction: {str(e)}"

def update_transaction_status(
    transaction_id: str,
    status: TransactionStatus,
    eth_transaction_hash: Optional[str] = None,
    send_email: bool = True
) -> Tuple[Optional[Transaction], Optional[str]]:
    """
    Update a transaction's status
    
    Args:
        transaction_id (str): Transaction ID
        status (TransactionStatus): New status
        eth_transaction_hash (str, optional): Ethereum transaction hash
        send_email (bool): Whether to send confirmation email
        
    Returns:
        Tuple[Transaction, Optional[str]]: Transaction object and error message if any
    """
    try:
        # Get transaction
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        if not transaction:
            return None, "Transaction not found"
        
        # Update status
        transaction.status = status
        
        # Set blockchain transaction hash if provided
        if eth_transaction_hash:
            transaction.eth_transaction_hash = eth_transaction_hash
        
        db.session.commit()
        
        # Send email notification if requested and status is final
        if send_email and status in [TransactionStatus.COMPLETED, TransactionStatus.FAILED, TransactionStatus.REFUNDED]:
            user = User.query.get(transaction.user_id)
            if user:
                try:
                    success = send_transaction_confirmation_email(user, transaction)
                    if not success:
                        logger.warning(f"Failed to send transaction status update email for {transaction_id}")
                except Exception as e:
                    logger.error(f"Error sending transaction email: {str(e)}")
        
        return transaction, None
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating transaction status: {str(e)}")
        return None, f"Failed to update transaction: {str(e)}"

def get_transaction(transaction_id: str) -> Tuple[Optional[Transaction], Optional[str]]:
    """
    Get a transaction by ID
    
    Args:
        transaction_id (str): Transaction ID
        
    Returns:
        Tuple[Transaction, Optional[str]]: Transaction object and error message if any
    """
    try:
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        if not transaction:
            return None, "Transaction not found"
        
        return transaction, None
    
    except Exception as e:
        logger.error(f"Error fetching transaction: {str(e)}")
        return None, f"Failed to fetch transaction: {str(e)}"