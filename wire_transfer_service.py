"""
Wire Transfer Service Module
This module provides functionality for processing wire transfers through correspondent banks.
"""
import json
import logging
import uuid
from datetime import datetime, timedelta
from flask import current_app
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

def _get_badge_class_for_status(status_value):
    """
    Helper function to get the appropriate badge class for a status value
    
    Args:
        status_value (str): The status value as a string
        
    Returns:
        str: The appropriate badge class
    """
    if status_value == 'completed':
        return "badge-success"
    elif status_value == 'rejected':
        return "badge-danger"
    elif status_value == 'cancelled':
        return "badge-secondary"
    elif status_value == 'failed':
        return "badge-danger"
    elif status_value == 'sent':
        return "badge-info"
    elif status_value == 'confirmed':
        return "badge-info"
    elif status_value == 'processing':
        return "badge-primary"
    else:
        return "badge-warning"  # Default for pending and unknown

from models import (
    db, Transaction, WireTransfer, WireTransferStatus, WireTransferStatusHistory, 
    TransactionType, TransactionStatus, CorrespondentBank, User, FinancialInstitution, 
    TreasuryTransaction
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
    message_to_beneficiary=None,
    treasury_transaction_id=None
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
        treasury_transaction_id (int, optional): ID of the associated treasury transaction
        
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
        # Convert decimal to float if needed
        if hasattr(amount, 'to_float'):
            amount_float = amount.to_float()
        elif hasattr(amount, '__float__'):
            amount_float = float(amount)
        else:
            amount_float = amount
            
        # Convert fee percentage to float if needed
        if hasattr(fee_percentage, 'to_float'):
            fee_percentage_float = fee_percentage.to_float()
        elif hasattr(fee_percentage, '__float__'):
            fee_percentage_float = float(fee_percentage)
        else:
            fee_percentage_float = fee_percentage
            
        fee_amount = amount_float * (fee_percentage_float / 100)
        
        # Create the transaction record
        wire_metadata = {
            "wire_transfer": {
                "beneficiary_name": beneficiary_name,
                "beneficiary_account": beneficiary_account,
                "beneficiary_address": beneficiary_address,
                "beneficiary_bank_name": beneficiary_bank_name,
                "beneficiary_bank_swift": beneficiary_bank_swift,
                "beneficiary_bank_routing": beneficiary_bank_routing,
                "intermediary_bank_name": intermediary_bank_name,
                "intermediary_bank_swift": intermediary_bank_swift,
                "purpose": purpose,
                "message_to_beneficiary": message_to_beneficiary,
                "fee_amount": fee_amount,
                "fee_percentage": fee_percentage,
                "institution_id": correspondent_bank.id if correspondent_bank else None
            }
        }
        
        # Create the transaction record first
        try:
            transaction = record_transaction(
                user_id=user_id,
                transaction_type=TransactionType.INTERNATIONAL_WIRE,
                amount=amount,
                currency=currency,
                description=f"Wire transfer to {beneficiary_name} via {correspondent_bank.name}",
                status=TransactionStatus.PENDING,
                metadata=wire_metadata
            )
            
            # Fetch the transaction by ID to ensure we have the latest version from the database
            db.session.refresh(transaction)
            
            logger.info(f"Created transaction with ID: {transaction.id} and transaction_id: {transaction.transaction_id}")
        except Exception as e:
            logger.error(f"Failed to create transaction: {str(e)}")
            return None, None, f"Failed to create transaction: {str(e)}"
        
        # Create the wire transfer record
        reference_number = generate_transfer_id()
        wire_transfer = WireTransfer()
        wire_transfer.reference_number = reference_number
        wire_transfer.correspondent_bank_id = correspondent_bank_id
        # Set the transaction_id to the transaction.transaction_id string
        # This should match the column type and structure in the database
        wire_transfer.transaction_id = transaction.transaction_id
        wire_transfer.treasury_transaction_id = treasury_transaction_id
        wire_transfer.amount = amount
        wire_transfer.currency = currency
        wire_transfer.purpose = purpose or "International Wire Transfer"
        wire_transfer.originator_name = originator_name
        wire_transfer.originator_account = originator_account
        wire_transfer.originator_address = originator_address
        wire_transfer.beneficiary_name = beneficiary_name
        wire_transfer.beneficiary_account = beneficiary_account
        wire_transfer.beneficiary_address = beneficiary_address
        wire_transfer.beneficiary_bank_name = beneficiary_bank_name
        wire_transfer.beneficiary_bank_address = beneficiary_bank_address
        wire_transfer.beneficiary_bank_swift = beneficiary_bank_swift
        wire_transfer.beneficiary_bank_routing = beneficiary_bank_routing
        wire_transfer.intermediary_bank_name = intermediary_bank_name
        wire_transfer.intermediary_bank_swift = intermediary_bank_swift
        wire_transfer.message_to_beneficiary = message_to_beneficiary
        wire_transfer.status = WireTransferStatus.PENDING
        wire_transfer.user_id = user_id
        # Set transfer_id to the reference number for consistency
        # This is required by the database schema
        wire_transfer.transfer_id = reference_number
        
        # Log the transaction information for debugging
        logger.info(f"Wire transfer data: ref={reference_number}, transaction_id={transaction.transaction_id}")
        
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
        wire_transfer.initiated_at = datetime.utcnow()
        
        # Record the status change in history
        success, error = record_status_change(
            wire_transfer_id=wire_transfer_id,
            status=WireTransferStatus.PROCESSING,
            description="Wire transfer is being processed by bank system",
            user_id=current_user.id if current_user and current_user.is_authenticated else None
        )
        
        if not success:
            logger.error(f"Failed to record status change: {error}")
        
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
        wire_transfer.confirmation_receipt = f"CNF-{str(uuid.uuid4())[:8].upper()}"
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
    # Note: confirmation_number parameter is actually stored as confirmation_receipt in the database
    try:
        wire_transfer = WireTransfer.query.get(wire_transfer_id)
        if not wire_transfer:
            return False, "Wire transfer not found"
        
        if wire_transfer.status not in [WireTransferStatus.PROCESSING]:
            return False, f"Wire transfer is not in a processing state (status: {wire_transfer.status.value})"
        
        # Update the reference number if provided
        if reference_number:
            wire_transfer.reference_number = reference_number
        
        # Update the confirmation receipt if provided
        if confirmation_number:
            wire_transfer.confirmation_receipt = confirmation_number
        
        # Record the status change in history to COMPLETED
        success, error = record_status_change(
            wire_transfer_id=wire_transfer_id,
            status=WireTransferStatus.COMPLETED,
            description=f"Wire transfer completed with confirmation {confirmation_number}" if confirmation_number else "Wire transfer completed",
            user_id=current_user.id if current_user and current_user.is_authenticated else None
        )
        
        if not success:
            logger.error(f"Failed to record status change to COMPLETED: {error}")
        
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
        
        logger.info(f"Confirmed wire transfer {wire_transfer_id} with confirmation {wire_transfer.confirmation_receipt}")
        
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
        return WireTransfer.query.filter_by(user_id=user_id).order_by(WireTransfer.created_at.desc()).all()
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
        
def record_status_change(wire_transfer_id, status, description=None, user_id=None):
    """
    Record a status change in the wire transfer status history
    
    Args:
        wire_transfer_id (int): The ID of the wire transfer
        status (WireTransferStatus): The new status
        description (str, optional): Description of the status change
        user_id (int, optional): ID of the user who made the change
        
    Returns:
        tuple: (success, error)
            success (bool): Whether the status change was recorded successfully
            error (str): Error message if any
    """
    try:
        # Check if the wire transfer exists
        wire_transfer = WireTransfer.query.get(wire_transfer_id)
        if not wire_transfer:
            return False, "Wire transfer not found"
        
        # Create a new status history entry
        status_history = WireTransferStatusHistory()
        status_history.wire_transfer_id = wire_transfer_id
        status_history.status = status
        status_history.description = description
        status_history.user_id = user_id
        
        # Update the wire transfer status
        wire_transfer.status = status
        if description:
            wire_transfer.status_description = description
            
        # Update timestamps based on status
        current_time = datetime.utcnow()
        if status == WireTransferStatus.PROCESSING:
            wire_transfer.processed_at = current_time
        elif status == WireTransferStatus.COMPLETED:
            wire_transfer.completed_at = current_time
        
        # Save to database
        db.session.add(status_history)
        db.session.commit()
        
        logger.info(f"Wire transfer {wire_transfer_id} status changed to {status.value}")
        return True, None
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error recording status change: {str(e)}")
        return False, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error recording status change: {str(e)}")
        return False, f"Error: {str(e)}"
        
def get_status_history(wire_transfer_id):
    """
    Get the complete status history for a wire transfer
    
    Args:
        wire_transfer_id (int): The ID of the wire transfer
    
    Returns:
        list: List of status history entries, or empty list if error
    """
    try:
        history = WireTransferStatusHistory.query.filter_by(wire_transfer_id=wire_transfer_id).order_by(WireTransferStatusHistory.timestamp).all()
        return history
    except Exception as e:
        logger.error(f"Error fetching status history: {str(e)}")
        return []
        
def get_status_timestamps(wire_transfer_id):
    """
    Get timestamps for each status change
    
    Args:
        wire_transfer_id (int): The ID of the wire transfer
    
    Returns:
        dict: Dictionary with status values as keys and timestamps as values
    """
    try:
        history = get_status_history(wire_transfer_id)
        timestamps = {}
        
        # Create a dictionary with the latest timestamp for each status
        for entry in history:
            timestamps[entry.status.value] = entry.timestamp
            
        return timestamps
    except Exception as e:
        logger.error(f"Error getting status timestamps: {str(e)}")
        return {}
        
def get_timeline_progress(wire_transfer):
    """
    Calculate the progress of a wire transfer through the standard timeline
    
    Args:
        wire_transfer (WireTransfer): The wire transfer object
    
    Returns:
        int: Progress value (0-5) through the timeline stages:
             0=Not started, 1=Pending, 2=Processing, 3=Sent, 4=Confirmed, 5=Completed
    """
    try:
        # Create a mapping using string values rather than enum members for safety
        status_mapping = {
            'pending': 1,
            'processing': 2,
            'sent': 3,
            'confirmed': 4,
            'completed': 5
        }
        
        # Get status as string
        current_status = wire_transfer.status.value if wire_transfer and wire_transfer.status else None
        
        # Return the numeric progress value for the current status
        # If the status isn't in our mapping (e.g., FAILED), return 0
        if current_status is None:
            return 0
        return status_mapping.get(current_status, 0)
    except Exception as e:
        logger.error(f"Error calculating timeline progress: {str(e)}")
        return 0
        
def estimate_completion_time(wire_transfer):
    """
    Estimate the completion time for a wire transfer based on its current status
    
    Args:
        wire_transfer (WireTransfer): The wire transfer object
    
    Returns:
        datetime: Estimated completion time, or None if not estimable
    """
    try:
        # If the transfer is already complete, failed, or cancelled, no need for estimate
        if wire_transfer.status in [
            WireTransferStatus.COMPLETED, WireTransferStatus.FAILED, 
            WireTransferStatus.CANCELLED, WireTransferStatus.REJECTED
        ]:
            return None
        
        # Get the creation time
        creation_time = wire_transfer.created_at
        
        # Standard processing times (in hours) from creation to completion
        # based on current status
        processing_times = {
            'pending': 24,      # 24 hours total if still pending
            'processing': 20,   # 20 hours total if processing
            'sent': 8,          # 8 hours total if already sent
            'confirmed': 2      # 2 hours total if confirmed
        }
        
        # Get status as string
        current_status = wire_transfer.status.value if wire_transfer and wire_transfer.status else None
        
        # Calculate estimated completion time
        if current_status is None:
            hours_to_add = 24  # Default to 24 hours if status is None
        else:
            hours_to_add = processing_times.get(current_status, 24)
        
        return creation_time + timedelta(hours=hours_to_add)
        
    except Exception as e:
        logger.error(f"Error calculating estimated completion time: {str(e)}")
        return None
        
def get_wire_transfer_with_tracking_data(wire_transfer_id):
    """
    Get a wire transfer with all tracking data needed for the tracking dashboard
    
    Args:
        wire_transfer_id (int): The ID of the wire transfer
    
    Returns:
        tuple: (wire_transfer, tracking_data, error)
            wire_transfer (WireTransfer): The wire transfer object or None if error
            tracking_data (dict): Dictionary with tracking data or empty dict if error 
            error (str): Error message if any
    """
    try:
        # Get the wire transfer
        wire_transfer = WireTransfer.query.get(wire_transfer_id)
        if not wire_transfer:
            return None, [], "Wire transfer not found"
            
        # Create sample data if no history found
        # This ensures tracking dashboard works even before any status changes are recorded
        processed_history = []
        
        # Get all real status history entries
        try:
            history_entries = WireTransferStatusHistory.query.filter_by(wire_transfer_id=wire_transfer_id).order_by(WireTransferStatusHistory.timestamp).all()
        except Exception as e:
            current_app.logger.error(f"Failed to retrieve status history: {str(e)}")
            history_entries = []
            
        # If no history entries exist, create one initial entry for the current status
        if not history_entries:
            current_app.logger.info(f"No status history found for wire transfer {wire_transfer_id}, creating minimal history")
            # Add the current status with current timestamp
            status_value = wire_transfer.status.value if hasattr(wire_transfer.status, 'value') else 'pending'
            
            # Determine badge class
            badge_class = _get_badge_class_for_status(status_value)
            
            # Build an entry with minimal required data
            processed_history.append({
                'status': status_value,
                'timestamp': datetime.utcnow(),
                'description': "Initial status",
                'badge_class': badge_class,
                'user': "System"
            })
        else:
            # Process real history entries for UI display
            for entry in history_entries:
                try:
                    # Extract status value safely
                    if hasattr(entry, 'status') and entry.status:
                        if hasattr(entry.status, 'value'):
                            status_value = entry.status.value
                        else:
                            status_value = str(entry.status)
                    else:
                        status_value = 'unknown'
                    
                    # Determine badge class
                    badge_class = _get_badge_class_for_status(status_value)
                    
                    # Extract timestamp safely - handle both string and datetime
                    timestamp = datetime.utcnow()
                    if hasattr(entry, 'timestamp'):
                        if entry.timestamp:
                            if isinstance(entry.timestamp, datetime):
                                timestamp = entry.timestamp
                            elif isinstance(entry.timestamp, str):
                                try:
                                    # Try parsing the timestamp string
                                    timestamp = datetime.strptime(entry.timestamp, "%Y-%m-%d %H:%M:%S")
                                except (ValueError, TypeError):
                                    # If parsing fails, use current time
                                    timestamp = datetime.utcnow()
                    
                    # Extract description safely
                    if hasattr(entry, 'description') and entry.description:
                        description = entry.description
                    else:
                        description = ""
                    
                    # Extract user safely
                    if hasattr(entry, 'user') and entry.user:
                        if hasattr(entry.user, 'username'):
                            user = entry.user.username
                        else:
                            user = "Unknown User"
                    else:
                        user = "System"
                    
                    # Add processed entry
                    processed_history.append({
                        'status': status_value,
                        'timestamp': timestamp,
                        'description': description,
                        'badge_class': badge_class,
                        'user': user
                    })
                except Exception as e:
                    current_app.logger.error(f"Error processing history entry: {str(e)}")
                    continue
                    
        # Sort history by timestamp with safety checks
        def safe_timestamp_key(entry):
            timestamp = entry.get('timestamp')
            if isinstance(timestamp, datetime):
                return timestamp
            elif isinstance(timestamp, str):
                try:
                    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    return datetime.utcnow()
            else:
                return datetime.utcnow()
                
        processed_history.sort(key=safe_timestamp_key)
        
        # Create a safe version of status_timestamps
        status_timestamps = {}
        try:
            # Extract status timestamps from processed history
            for entry in processed_history:
                status_value = entry['status']
                timestamp_value = entry['timestamp']
                
                # Ensure the timestamp is always a datetime object
                if isinstance(timestamp_value, str):
                    try:
                        # Try to parse string to datetime
                        timestamp_value = datetime.strptime(timestamp_value, "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        # If parsing fails, use current time
                        timestamp_value = datetime.utcnow()
                        
                # Keep only the most recent timestamp for each status
                status_timestamps[status_value] = timestamp_value
        except Exception as e:
            current_app.logger.error(f"Error creating status timestamps: {str(e)}")
        
        # Calculate timeline progress
        timeline_progress = 0
        try:
            timeline_progress = get_timeline_progress(wire_transfer)
        except Exception as e:
            current_app.logger.error(f"Error calculating timeline progress: {str(e)}")
        
        # Estimate completion time if not already completed
        estimated_completion = None
        try:
            estimated_completion = estimate_completion_time(wire_transfer)
        except Exception as e:
            current_app.logger.error(f"Error estimating completion time: {str(e)}")
        
        # Get current status from wire transfer
        current_status = 'pending'
        if wire_transfer and hasattr(wire_transfer, 'status') and wire_transfer.status:
            if hasattr(wire_transfer.status, 'value'):
                current_status = wire_transfer.status.value
            else:
                current_status = str(wire_transfer.status)
                
        # Determine status badge class for display
        status_class = "warning"  # Default for pending
        if current_status == 'completed':
            status_class = "success"
        elif current_status in ['failed', 'rejected']:
            status_class = "danger"
        elif current_status == 'cancelled':
            status_class = "secondary"
        elif current_status == 'processing':
            status_class = "primary"
        elif current_status in ['sent', 'confirmed']:
            status_class = "info"
                
        # Prepare the complete tracking data dictionary
        tracking_data = {
            'status_history': processed_history,
            'status_timestamps': status_timestamps,
            'timeline_progress': timeline_progress,
            'estimated_completion': estimated_completion,
            'status_class': status_class
        }
        
        # Add additional data if available
        if wire_transfer.correspondent_bank_id:
            try:
                correspondent_bank = CorrespondentBank.query.get(wire_transfer.correspondent_bank_id)
                tracking_data['correspondent_bank'] = correspondent_bank
            except Exception as e:
                current_app.logger.error(f"Error retrieving correspondent bank: {str(e)}")
                
        # Add transaction data if available
        if wire_transfer.transaction_id:
            try:
                # Instead of using get() which expects a primary key,
                # use filter_by() with transaction_id which might be a string value
                transaction = Transaction.query.filter_by(transaction_id=wire_transfer.transaction_id).first()
                if transaction:
                    tracking_data['transaction'] = transaction
                else:
                    current_app.logger.warning(f"No transaction found with ID: {wire_transfer.transaction_id}")
            except Exception as e:
                current_app.logger.error(f"Error retrieving transaction: {str(e)}")
        
        return wire_transfer, tracking_data, None
        
    except Exception as e:
        logger.error(f"Error getting wire transfer tracking data: {str(e)}")
        return None, {}, f"Error: {str(e)}"