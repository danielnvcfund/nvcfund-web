"""
Wire Transfer Service Module
This module provides functionality for processing wire transfers through correspondent banks.
"""
import json
import logging
import uuid
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from models import (
    db, Transaction, WireTransfer, WireTransferStatus, TransactionType, TransactionStatus,
    CorrespondentBank, User, FinancialInstitution, TreasuryTransaction
)
from transaction_service import record_transaction

logger = logging.getLogger(__name__)

def generate_transfer_id():
    """Generate a unique ID for wire transfers"""
    return f"WTR-{str(uuid.uuid4())[:8].upper()}-{datetime.utcnow().strftime('%y%m%d')}"

def get_active_correspondent_banks():
    """Get a list of active correspondent banks that support wire transfers"""
    try:
        banks = CorrespondentBank.query.filter_by(is_active=True, supports_wire=True).all()
        return banks
    except Exception as e:
        logger.error(f"Error fetching correspondent banks: {str(e)}")
        return []

def create_wire_transfer(
    user_id, 
    correspondent_bank_id, 
    amount, 
    currency,
    originator_name,
    originator_account,
    originator_address,
    beneficiary_name,
    beneficiary_account,
    beneficiary_address,
    beneficiary_bank_name,
    beneficiary_bank_address,
    beneficiary_bank_swift=None,
    beneficiary_bank_routing=None,
    intermediary_bank_name=None,
    intermediary_bank_swift=None,
    purpose=None,
    message_to_beneficiary=None
):
    """
    Create a new wire transfer through a correspondent bank
    
    Args:
        user_id (int): The ID of the user initiating the transfer
        correspondent_bank_id (int): The ID of the correspondent bank to use
        amount (float): The amount to transfer
        currency (str): The currency code (e.g., USD, EUR)
        originator_name (str): Name of the sender
        originator_account (str): Account number of the sender
        originator_address (str): Address of the sender
        beneficiary_name (str): Name of the recipient
        beneficiary_account (str): Account number of the recipient
        beneficiary_address (str): Address of the recipient
        beneficiary_bank_name (str): Name of the recipient's bank
        beneficiary_bank_address (str): Address of the recipient's bank
        beneficiary_bank_swift (str, optional): SWIFT/BIC code of the recipient's bank
        beneficiary_bank_routing (str, optional): ABA/Routing number of the recipient's bank
        intermediary_bank_name (str, optional): Name of the intermediary bank
        intermediary_bank_swift (str, optional): SWIFT/BIC code of the intermediary bank
        purpose (str, optional): Purpose of the transfer
        message_to_beneficiary (str, optional): Additional message to the recipient
        
    Returns:
        tuple: (wire_transfer, transaction, error)
            wire_transfer (WireTransfer): The created wire transfer
            transaction (Transaction): The associated transaction
            error (str): Error message if any
    """
    try:
        # Validate the correspondent bank
        correspondent_bank = CorrespondentBank.query.get(correspondent_bank_id)
        if not correspondent_bank:
            return None, None, "Correspondent bank not found"
        
        if not correspondent_bank.supports_wire:
            return None, None, "Selected correspondent bank does not support wire transfers"
        
        user = User.query.get(user_id)
        if not user:
            return None, None, "User not found"
        
        # Calculate the fee (can be based on correspondent bank's settings)
        fee_percentage = correspondent_bank.settlement_fee_percentage
        fee_amount = amount * (fee_percentage / 100)
        
        # Create the transaction record
        transaction = record_transaction(
            user_id=user_id,
            transaction_type=TransactionType.INTERNATIONAL_WIRE,
            amount=amount,
            currency=currency,
            description=f"Wire transfer to {beneficiary_name} via {correspondent_bank.name}",
            status=TransactionStatus.PENDING,
            recipient_name=beneficiary_name,
            recipient_account=beneficiary_account,
            recipient_address=beneficiary_address,
            recipient_bank=beneficiary_bank_name,
            institution_id=correspondent_bank.id if correspondent_bank else None,
            tx_metadata_json=json.dumps({
                "wire_transfer": {
                    "beneficiary_bank_swift": beneficiary_bank_swift,
                    "beneficiary_bank_routing": beneficiary_bank_routing,
                    "intermediary_bank_name": intermediary_bank_name,
                    "intermediary_bank_swift": intermediary_bank_swift,
                    "purpose": purpose,
                    "message_to_beneficiary": message_to_beneficiary,
                    "fee_amount": fee_amount,
                    "fee_percentage": fee_percentage
                }
            })
        )
        
        # Create the wire transfer record
        reference_number = generate_transfer_id()
        wire_transfer = WireTransfer(
            reference_number=reference_number,
            correspondent_bank_id=correspondent_bank_id,
            transaction_id=transaction.id,
            amount=amount,
            currency=currency,
            purpose=purpose or "International Wire Transfer",
            originator_name=originator_name,
            originator_account=originator_account,
            originator_address=originator_address,
            beneficiary_name=beneficiary_name,
            beneficiary_account=beneficiary_account,
            beneficiary_address=beneficiary_address,
            beneficiary_bank_name=beneficiary_bank_name,
            beneficiary_bank_address=beneficiary_bank_address,
            beneficiary_bank_swift=beneficiary_bank_swift,
            beneficiary_bank_routing=beneficiary_bank_routing,
            intermediary_bank_name=intermediary_bank_name,
            intermediary_bank_swift=intermediary_bank_swift,
            message_to_beneficiary=message_to_beneficiary,
            status=WireTransferStatus.PENDING,
            created_by_id=user_id
        )
        
        db.session.add(wire_transfer)
        db.session.commit()
        
        logger.info(f"Created wire transfer {reference_number} for user {user_id}")
        
        return wire_transfer, transaction, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating wire transfer: {str(e)}")
        return None, None, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating wire transfer: {str(e)}")
        return None, None, f"Error: {str(e)}"

def process_wire_transfer(wire_transfer_id):
    """
    Process a wire transfer and send it to the correspondent bank
    
    Args:
        wire_transfer_id (int): The ID of the transfer to process
        
    Returns:
        tuple: (success, error)
            success (bool): Whether the transfer was processed successfully
            error (str): Error message if any
    """
    try:
        wire_transfer = WireTransfer.query.get(wire_transfer_id)
        if not wire_transfer:
            return False, "Wire transfer not found"
        
        if wire_transfer.status != WireTransferStatus.PENDING:
            return False, f"Wire transfer has already been processed (status: {wire_transfer.status.value})"
        
        # Update the status to processing
        wire_transfer.status = WireTransferStatus.PROCESSING
        wire_transfer.initiated_at = datetime.utcnow()
        db.session.commit()
        
        # Get the associated transaction and update its status
        transaction = Transaction.query.get(wire_transfer.transaction_id) if wire_transfer.transaction_id else None
        if transaction:
            transaction.status = TransactionStatus.PROCESSING
            db.session.commit()
        
        # Get the correspondent bank
        correspondent_bank = CorrespondentBank.query.get(wire_transfer.correspondent_bank_id)
        if not correspondent_bank:
            wire_transfer.status = WireTransferStatus.FAILED
            wire_transfer.status_description = "Correspondent bank not found"
            db.session.commit()
            return False, "Correspondent bank not found"
        
        # In a real system, here we would call the API of the correspondent bank
        # For now, we will simulate success and update the status
        
        # Simulate sending the transfer to the correspondent bank
        # In a real implementation, this would call the bank's API or use SWIFT messaging
        # Generate a reference number if one isn't already set
        if not wire_transfer.reference_number:
            wire_transfer.reference_number = f"REF-{str(uuid.uuid4())[:12].upper()}"
        
        # Update with completion confirmation
        wire_transfer.status = WireTransferStatus.PROCESSING
        wire_transfer.confirmation_number = f"CNF-{str(uuid.uuid4())[:8].upper()}"
        db.session.commit()
        
        # Update the transaction status as well
        if transaction:
            transaction.status = TransactionStatus.PROCESSING
            transaction.external_id = wire_transfer.reference_number
            db.session.commit()
        
        logger.info(f"Processed wire transfer {wire_transfer_id} with reference {wire_transfer.reference_number}")
        
        return True, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error processing wire transfer: {str(e)}")
        return False, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing wire transfer: {str(e)}")
        return False, f"Error: {str(e)}"

def confirm_wire_transfer(wire_transfer_id, reference_number=None, confirmation_number=None):
    """
    Confirm that a wire transfer has been completed by the correspondent bank
    
    Args:
        wire_transfer_id (int): The ID of the transfer to confirm
        reference_number (str, optional): The reference number from the correspondent bank
        confirmation_number (str, optional): The confirmation number from the correspondent bank
        
    Returns:
        tuple: (success, error)
            success (bool): Whether the transfer was confirmed successfully
            error (str): Error message if any
    """
    try:
        wire_transfer = WireTransfer.query.get(wire_transfer_id)
        if not wire_transfer:
            return False, "Wire transfer not found"
        
        if wire_transfer.status not in [WireTransferStatus.PROCESSING]:
            return False, f"Wire transfer is not in a processing state (status: {wire_transfer.status.value})"
        
        # Update the reference number if provided
        if reference_number:
            wire_transfer.reference_number = reference_number
        
        # Update the confirmation number if provided
        if confirmation_number:
            wire_transfer.confirmation_number = confirmation_number
        
        # Update the status to confirmed/completed
        wire_transfer.status = WireTransferStatus.COMPLETED
        wire_transfer.completed_at = datetime.utcnow()
        db.session.commit()
        
        # Get the associated transaction and update its status
        transaction = Transaction.query.get(wire_transfer.transaction_id) if wire_transfer.transaction_id else None
        if transaction:
            transaction.status = TransactionStatus.COMPLETED
            if reference_number:
                transaction.external_id = reference_number
            db.session.commit()
            
        # Get the associated treasury transaction and update its status
        treasury_tx = TreasuryTransaction.query.get(wire_transfer.treasury_transaction_id) if wire_transfer.treasury_transaction_id else None
        if treasury_tx:
            treasury_tx.status = "completed"
            db.session.commit()
        
        logger.info(f"Confirmed wire transfer {wire_transfer_id} with confirmation {wire_transfer.confirmation_number}")
        
        return True, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error confirming wire transfer: {str(e)}")
        return False, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error confirming wire transfer: {str(e)}")
        return False, f"Error: {str(e)}"

def cancel_wire_transfer(wire_transfer_id, reason=None):
    """
    Cancel a wire transfer
    
    Args:
        wire_transfer_id (int): The ID of the transfer to cancel
        reason (str, optional): The reason for cancellation
        
    Returns:
        tuple: (success, error)
            success (bool): Whether the transfer was cancelled successfully
            error (str): Error message if any
    """
    try:
        wire_transfer = WireTransfer.query.get(wire_transfer_id)
        if not wire_transfer:
            return False, "Wire transfer not found"
        
        if wire_transfer.status in [WireTransferStatus.COMPLETED, WireTransferStatus.FAILED, WireTransferStatus.CANCELLED]:
            return False, f"Wire transfer cannot be cancelled (status: {wire_transfer.status.value})"
        
        # Update the status to cancelled
        wire_transfer.status = WireTransferStatus.CANCELLED
        wire_transfer.cancelled_at = datetime.utcnow()
        wire_transfer.status_description = reason if reason else "Cancelled by user"
        db.session.commit()
        
        # Get the associated transaction and update its status
        transaction = Transaction.query.get(wire_transfer.transaction_id) if wire_transfer.transaction_id else None
        if transaction:
            transaction.status = TransactionStatus.CANCELLED
            db.session.commit()
            
        # Get the associated treasury transaction and update its status
        treasury_tx = TreasuryTransaction.query.get(wire_transfer.treasury_transaction_id) if wire_transfer.treasury_transaction_id else None
        if treasury_tx:
            treasury_tx.status = "cancelled"
            db.session.commit()
        
        logger.info(f"Cancelled wire transfer {wire_transfer_id}: {reason or 'No reason provided'}")
        
        return True, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error cancelling wire transfer: {str(e)}")
        return False, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cancelling wire transfer: {str(e)}")
        return False, f"Error: {str(e)}"

def reject_wire_transfer(wire_transfer_id, reason):
    """
    Reject a wire transfer
    
    Args:
        wire_transfer_id (int): The ID of the transfer to reject
        reason (str): The reason for rejection
        
    Returns:
        tuple: (success, error)
            success (bool): Whether the transfer was rejected successfully
            error (str): Error message if any
    """
    try:
        wire_transfer = WireTransfer.query.get(wire_transfer_id)
        if not wire_transfer:
            return False, "Wire transfer not found"
        
        if wire_transfer.status not in [WireTransferStatus.PENDING, WireTransferStatus.PROCESSING]:
            return False, f"Wire transfer cannot be rejected (status: {wire_transfer.status.value})"
        
        # Update the status to rejected
        wire_transfer.status = WireTransferStatus.REJECTED
        wire_transfer.status_description = reason
        db.session.commit()
        
        # Get the associated transaction and update its status
        transaction = Transaction.query.get(wire_transfer.transaction_id) if wire_transfer.transaction_id else None
        if transaction:
            transaction.status = TransactionStatus.REJECTED
            db.session.commit()
            
        # Get the associated treasury transaction and update its status
        treasury_tx = TreasuryTransaction.query.get(wire_transfer.treasury_transaction_id) if wire_transfer.treasury_transaction_id else None
        if treasury_tx:
            treasury_tx.status = "rejected"
            db.session.commit()
        
        logger.info(f"Rejected wire transfer {wire_transfer_id}: {reason}")
        
        return True, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error rejecting wire transfer: {str(e)}")
        return False, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error rejecting wire transfer: {str(e)}")
        return False, f"Error: {str(e)}"

def get_wire_transfer(wire_transfer_id):
    """
    Get a wire transfer by ID
    
    Args:
        wire_transfer_id (int): The ID of the transfer
        
    Returns:
        WireTransfer: The wire transfer object
    """
    try:
        return WireTransfer.query.get(wire_transfer_id)
    except Exception as e:
        logger.error(f"Error getting wire transfer: {str(e)}")
        return None

def get_user_wire_transfers(user_id):
    """
    Get all wire transfers for a user
    
    Args:
        user_id (int): The ID of the user
        
    Returns:
        list: List of wire transfer objects
    """
    try:
        return WireTransfer.query.filter_by(created_by_id=user_id).order_by(WireTransfer.created_at.desc()).all()
    except Exception as e:
        logger.error(f"Error getting user wire transfers: {str(e)}")
        return []
        
def get_wire_transfers_by_treasury_transaction(treasury_transaction_id):
    """
    Get wire transfers associated with a treasury transaction
    
    Args:
        treasury_transaction_id (int): The ID of the treasury transaction
        
    Returns:
        list: List of wire transfer objects
    """
    try:
        return WireTransfer.query.filter_by(treasury_transaction_id=treasury_transaction_id).all()
    except Exception as e:
        logger.error(f"Error getting wire transfers for treasury transaction: {str(e)}")
        return []