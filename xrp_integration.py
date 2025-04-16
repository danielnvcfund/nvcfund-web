"""
XRP Ledger Integration Module for NVC Banking Platform
This module serves as a bridge between the xrp_ledger.py utility functions and the application.
It provides high-level business logic for using XRP Ledger in the banking platform.
"""

import os
import logging
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from app import db
from models import (
    User, 
    Transaction, 
    TransactionStatus, 
    TransactionType, 
    PaymentGateway,
    PaymentGatewayType,
    XRPLedgerTransaction
)
import xrp_ledger

# Configure logger
logger = logging.getLogger(__name__)

def init_xrp_gateway() -> PaymentGateway:
    """
    Initialize or retrieve the XRP Ledger payment gateway
    Creates a new gateway if one doesn't exist
    
    Returns:
        PaymentGateway: The XRP Ledger payment gateway
    """
    xrp_gateway = PaymentGateway.query.filter_by(
        gateway_type=PaymentGatewayType.XRP_LEDGER,
        is_active=True
    ).first()
    
    if not xrp_gateway:
        # Create a new XRP wallet for the gateway
        try:
            wallet = xrp_ledger.create_xrpl_wallet()
            if 'error' in wallet:
                logger.error(f"Failed to create XRP wallet: {wallet.get('error')}")
                raise Exception(f"Failed to create XRP wallet: {wallet.get('error')}")
                
            xrp_gateway = PaymentGateway(
                name="XRP Ledger Gateway",
                gateway_type=PaymentGatewayType.XRP_LEDGER,
                api_endpoint=xrp_ledger.XRPL_NETWORKS.get(
                    os.environ.get('XRPL_NETWORK', xrp_ledger.DEFAULT_NETWORK)
                ),
                xrp_address=wallet.get('address'),
                xrp_seed=wallet.get('seed'),
                is_active=True
            )
            
            db.session.add(xrp_gateway)
            db.session.commit()
            
            logger.info(f"Created new XRP Ledger gateway with address: {wallet.get('address')}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error initializing XRP gateway: {str(e)}")
            raise
    
    return xrp_gateway

def ensure_user_has_xrp_wallet(user_id: int) -> Tuple[bool, Optional[str]]:
    """
    Ensure a user has an XRP wallet
    Creates a new wallet if one doesn't exist
    
    Args:
        user_id: The user ID to check or create a wallet for
        
    Returns:
        Tuple[bool, Optional[str]]: Success status and error message if any
    """
    user = User.query.get(user_id)
    if not user:
        return False, "User not found"
    
    if user.xrp_address and user.xrp_seed:
        # User already has an XRP wallet
        return True, None
    
    try:
        # Create a new XRP wallet for the user
        wallet = xrp_ledger.create_xrpl_wallet()
        if 'error' in wallet:
            return False, f"Failed to create XRP wallet: {wallet.get('error')}"
        
        user.xrp_address = wallet.get('address')
        user.xrp_seed = wallet.get('seed')
        
        db.session.commit()
        logger.info(f"Created new XRP wallet for user {user_id}: {wallet.get('address')}")
        
        return True, None
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error creating XRP wallet: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def get_xrp_balance(xrp_address: str) -> Tuple[float, Optional[str]]:
    """
    Get the XRP balance for an address
    
    Args:
        xrp_address: The XRP address to check
        
    Returns:
        Tuple[float, Optional[str]]: Balance in XRP and error message if any
    """
    try:
        account_info = xrp_ledger.get_account_info(xrp_address)
        if 'error' in account_info:
            return 0.0, account_info.get('error')
        
        balance = float(account_info.get('balance', 0.0))
        return balance, None
    except Exception as e:
        error_msg = f"Error getting XRP balance: {str(e)}"
        logger.error(error_msg)
        return 0.0, error_msg

def get_user_xrp_balance(user_id: int) -> Tuple[float, Optional[str]]:
    """
    Get the XRP balance for a user
    
    Args:
        user_id: The user ID to check the balance for
        
    Returns:
        Tuple[float, Optional[str]]: Balance in XRP and error message if any
    """
    user = User.query.get(user_id)
    if not user:
        return 0.0, "User not found"
    
    if not user.xrp_address:
        return 0.0, "User does not have an XRP wallet"
    
    return get_xrp_balance(user.xrp_address)

def get_user_xrp_transactions(user_id: int, limit: int = 10) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Get recent XRP transactions for a user
    
    Args:
        user_id: The user ID to get transactions for
        limit: Maximum number of transactions to retrieve
        
    Returns:
        Tuple[List[Dict[str, Any]], Optional[str]]: Transactions and error message if any
    """
    user = User.query.get(user_id)
    if not user:
        return [], "User not found"
    
    if not user.xrp_address:
        return [], "User does not have an XRP wallet"
    
    try:
        # First get transactions from the database
        db_transactions = XRPLedgerTransaction.query.filter_by(
            user_id=user_id
        ).order_by(XRPLedgerTransaction.created_at.desc()).limit(limit).all()
        
        # Then get transactions from the XRP Ledger
        xrp_transactions = xrp_ledger.get_account_transactions(user.xrp_address, limit)
        
        # Combine and format the results
        transactions = []
        
        # Add database transactions
        for tx in db_transactions:
            transactions.append({
                'id': tx.id,
                'hash': tx.xrp_tx_hash,
                'from_address': tx.from_address,
                'to_address': tx.to_address,
                'amount': tx.amount,
                'type': tx.transaction_type,
                'status': tx.status,
                'date': tx.created_at.isoformat() if tx.created_at else None,
                'fee': tx.fee,
                'ledger_index': tx.ledger_index,
                'source': 'database'
            })
        
        # Add any ledger transactions not already in the database
        db_tx_hashes = {tx.xrp_tx_hash for tx in db_transactions}
        for tx in xrp_transactions:
            if 'error' in tx:
                continue
                
            if tx.get('hash') not in db_tx_hashes:
                transactions.append({
                    'id': None,
                    'hash': tx.get('hash'),
                    'from_address': tx.get('from'),
                    'to_address': tx.get('to'),
                    'amount': tx.get('amount'),
                    'type': tx.get('type'),
                    'status': 'completed' if tx.get('validated') else 'pending',
                    'date': tx.get('date'),
                    'fee': None,
                    'ledger_index': tx.get('ledger_index'),
                    'source': 'ledger'
                })
        
        # Sort by date (recent first)
        transactions.sort(key=lambda x: x.get('date') or '', reverse=True)
        
        # Limit the number of transactions
        return transactions[:limit], None
        
    except Exception as e:
        error_msg = f"Error getting XRP transactions: {str(e)}"
        logger.error(error_msg)
        return [], error_msg

def create_xrp_payment(
    user_id: int,
    to_address: str,
    amount: float,
    description: str = None,
    destination_tag: int = None,
    transaction_type: TransactionType = TransactionType.PAYMENT,
    memo: str = None
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Create an XRP payment from a user to a recipient
    
    Args:
        user_id: The user ID making the payment
        to_address: The recipient's XRP address
        amount: The amount in XRP to send
        description: An optional description for the transaction
        destination_tag: An optional destination tag for the recipient
        transaction_type: The type of transaction
        memo: An optional memo to include with the transaction
        
    Returns:
        Tuple[Dict[str, Any], Optional[str]]: Transaction details and error message if any
    """
    user = User.query.get(user_id)
    if not user:
        return {}, "User not found"
    
    if not user.xrp_address or not user.xrp_seed:
        return {}, "User does not have an XRP wallet"
    
    # Validate amount
    if amount <= 0:
        return {}, "Amount must be greater than zero"
    
    # Validate balance
    balance, error = get_xrp_balance(user.xrp_address)
    if error:
        return {}, f"Error checking balance: {error}"
    
    if balance < amount:
        return {}, f"Insufficient funds: {balance} XRP available, {amount} XRP required"
    
    try:
        # Generate a unique transaction ID
        transaction_id = str(uuid.uuid4())
        
        # Create the transaction in the database
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            amount=amount,
            currency="XRP",
            transaction_type=transaction_type,
            status=TransactionStatus.PENDING,
            description=description or "XRP Payment"
        )
        
        db.session.add(transaction)
        db.session.flush()  # Get the transaction ID without committing
        
        # Create metadata
        metadata = {
            'transaction_id': transaction_id,
            'description': description,
            'memo': memo,
            'destination_tag': destination_tag
        }
        
        # Send the XRP payment
        payment_result = xrp_ledger.send_xrp_payment(
            from_address=user.xrp_address,
            to_address=to_address,
            amount_in_xrp=amount,
            seed=user.xrp_seed,
            memo=memo,
            tx_metadata=json.dumps(metadata),
            destination_tag=destination_tag
        )
        
        if 'error' in payment_result:
            # Payment failed
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
            
            return {}, f"Payment failed: {payment_result.get('error')}"
        
        # Payment submitted successfully
        # Create an XRP Ledger transaction record
        xrp_tx = XRPLedgerTransaction(
            user_id=user_id,
            xrp_tx_hash=payment_result.get('hash'),
            from_address=user.xrp_address,
            to_address=to_address,
            amount=amount,
            transaction_type='Payment',
            ledger_index=payment_result.get('ledger_index'),
            fee=payment_result.get('fee'),
            destination_tag=destination_tag,
            status=payment_result.get('status', 'pending').lower(),
            tx_metadata=json.dumps(metadata),
            transaction_id=transaction.id
        )
        
        db.session.add(xrp_tx)
        
        # Update the main transaction status
        if payment_result.get('status') == 'VALIDATED':
            transaction.status = TransactionStatus.COMPLETED
        else:
            transaction.status = TransactionStatus.PROCESSING
        
        db.session.commit()
        
        return {
            'transaction_id': transaction_id,
            'xrp_tx_hash': payment_result.get('hash'),
            'amount': amount,
            'from_address': user.xrp_address,
            'to_address': to_address,
            'status': transaction.status.value,
            'date': datetime.utcnow().isoformat()
        }, None
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error creating XRP payment: {str(e)}"
        logger.error(error_msg)
        return {}, error_msg

def check_xrp_transaction_status(tx_hash: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Check the status of an XRP Ledger transaction
    Updates the local database record if needed
    
    Args:
        tx_hash: The XRP transaction hash to check
        
    Returns:
        Tuple[Dict[str, Any], Optional[str]]: Transaction status and error message if any
    """
    try:
        # Get the transaction from the database
        xrp_tx = XRPLedgerTransaction.query.filter_by(xrp_tx_hash=tx_hash).first()
        
        # Get the transaction status from the XRP Ledger
        tx_status = xrp_ledger.get_transaction_status(tx_hash)
        
        if 'error' in tx_status:
            return {}, f"Error checking transaction status: {tx_status.get('error')}"
        
        # If we have a database record, update it
        if xrp_tx:
            new_status = tx_status.get('status', '').lower()
            
            if new_status in ['confirmed', 'validated']:
                # Transaction is confirmed, update the database
                xrp_tx.status = 'completed'
                xrp_tx.ledger_index = tx_status.get('ledger_index')
                xrp_tx.fee = tx_status.get('fee')
                
                # Update the main transaction as well
                if xrp_tx.transaction_id:
                    transaction = Transaction.query.get(xrp_tx.transaction_id)
                    if transaction:
                        transaction.status = TransactionStatus.COMPLETED
                
                db.session.commit()
            elif new_status == 'failed':
                # Transaction failed, update the database
                xrp_tx.status = 'failed'
                
                # Update the main transaction as well
                if xrp_tx.transaction_id:
                    transaction = Transaction.query.get(xrp_tx.transaction_id)
                    if transaction:
                        transaction.status = TransactionStatus.FAILED
                
                db.session.commit()
        
        # Format the status response
        formatted_status = {
            'tx_hash': tx_hash,
            'status': tx_status.get('status', '').lower(),
            'from_address': tx_status.get('account'),
            'to_address': tx_status.get('destination'),
            'amount': tx_status.get('amount'),
            'ledger_index': tx_status.get('ledger_index'),
            'date': tx_status.get('date'),
            'result': tx_status.get('result')
        }
        
        return formatted_status, None
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error checking XRP transaction status: {str(e)}"
        logger.error(error_msg)
        return {}, error_msg

def create_xrp_escrow(
    user_id: int,
    to_address: str,
    amount: float,
    release_time: int,  # Unix timestamp
    cancel_after: int = None,  # Optional cancel-after time
    description: str = None,
    condition: str = None  # Optional crypto-condition
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Create an XRP escrow payment from a user to a recipient
    
    Args:
        user_id: The user ID creating the escrow
        to_address: The recipient's XRP address
        amount: The amount in XRP to escrow
        release_time: Time when the escrowed XRP can be released (Unix timestamp)
        cancel_after: Optional time when the escrow can be cancelled if not finished
        description: An optional description for the transaction
        condition: Optional crypto-condition for the escrow
        
    Returns:
        Tuple[Dict[str, Any], Optional[str]]: Escrow details and error message if any
    """
    user = User.query.get(user_id)
    if not user:
        return {}, "User not found"
    
    if not user.xrp_address or not user.xrp_seed:
        return {}, "User does not have an XRP wallet"
    
    # Validate amount
    if amount <= 0:
        return {}, "Amount must be greater than zero"
    
    # Validate balance
    balance, error = get_xrp_balance(user.xrp_address)
    if error:
        return {}, f"Error checking balance: {error}"
    
    if balance < amount:
        return {}, f"Insufficient funds: {balance} XRP available, {amount} XRP required"
    
    try:
        # Generate a unique transaction ID
        transaction_id = str(uuid.uuid4())
        
        # Create the transaction in the database
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            amount=amount,
            currency="XRP",
            transaction_type=TransactionType.SETTLEMENT,
            status=TransactionStatus.PENDING,
            description=description or "XRP Escrow"
        )
        
        db.session.add(transaction)
        db.session.flush()  # Get the transaction ID without committing
        
        # Create metadata
        metadata = {
            'transaction_id': transaction_id,
            'description': description,
            'release_time': release_time,
            'cancel_after': cancel_after,
            'condition': condition
        }
        
        # Create the XRP escrow
        escrow_result = xrp_ledger.create_escrow_payment(
            from_address=user.xrp_address,
            to_address=to_address,
            amount_in_xrp=amount,
            release_time=release_time,
            seed=user.xrp_seed,
            cancel_after=cancel_after,
            condition=condition,
            tx_metadata=json.dumps(metadata)
        )
        
        if 'error' in escrow_result:
            # Escrow creation failed
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
            
            return {}, f"Escrow creation failed: {escrow_result.get('error')}"
        
        # Escrow created successfully
        # Create an XRP Ledger transaction record
        xrp_tx = XRPLedgerTransaction(
            user_id=user_id,
            xrp_tx_hash=escrow_result.get('hash'),
            from_address=user.xrp_address,
            to_address=to_address,
            amount=amount,
            transaction_type='EscrowCreate',
            ledger_index=escrow_result.get('ledger_index'),
            fee=escrow_result.get('fee'),
            status=escrow_result.get('status', 'pending').lower(),
            tx_metadata=json.dumps({
                **metadata,
                'sequence': escrow_result.get('sequence')  # Store sequence for finishing/cancelling
            }),
            transaction_id=transaction.id
        )
        
        db.session.add(xrp_tx)
        
        # Update the main transaction status
        transaction.status = TransactionStatus.PROCESSING
        
        db.session.commit()
        
        return {
            'transaction_id': transaction_id,
            'xrp_tx_hash': escrow_result.get('hash'),
            'amount': amount,
            'from_address': user.xrp_address,
            'to_address': to_address,
            'status': transaction.status.value,
            'release_time': release_time,
            'cancel_after': cancel_after,
            'sequence': escrow_result.get('sequence'),
            'date': datetime.utcnow().isoformat()
        }, None
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error creating XRP escrow: {str(e)}"
        logger.error(error_msg)
        return {}, error_msg

def finish_xrp_escrow(
    user_id: int,
    owner_address: str,
    escrow_sequence: int,
    fulfillment: str = None  # Required if the escrow had a condition
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Finish an XRP escrow to release funds to the recipient
    
    Args:
        user_id: The user ID finishing the escrow
        owner_address: Address of the account that created the escrow
        escrow_sequence: Sequence number of the EscrowCreate transaction
        fulfillment: Optional fulfillment for crypto-condition (if required)
        
    Returns:
        Tuple[Dict[str, Any], Optional[str]]: Transaction details and error message if any
    """
    user = User.query.get(user_id)
    if not user:
        return {}, "User not found"
    
    if not user.xrp_address or not user.xrp_seed:
        return {}, "User does not have an XRP wallet"
    
    try:
        # Find the original escrow transaction
        original_tx = XRPLedgerTransaction.query.filter(
            XRPLedgerTransaction.tx_metadata.like(f'%"sequence": {escrow_sequence}%'),
            XRPLedgerTransaction.transaction_type == 'EscrowCreate'
        ).first()
        
        # Generate a unique transaction ID
        transaction_id = str(uuid.uuid4())
        
        # Create the transaction in the database
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            amount=original_tx.amount if original_tx else 0.0,
            currency="XRP",
            transaction_type=TransactionType.SETTLEMENT,
            status=TransactionStatus.PENDING,
            description="Finish XRP Escrow"
        )
        
        db.session.add(transaction)
        db.session.flush()  # Get the transaction ID without committing
        
        # Create metadata
        metadata = {
            'transaction_id': transaction_id,
            'escrow_sequence': escrow_sequence,
            'owner_address': owner_address,
            'original_tx_id': original_tx.id if original_tx else None
        }
        
        # Finish the XRP escrow
        finish_result = xrp_ledger.finish_escrow_payment(
            owner_address=owner_address,
            escrow_sequence=escrow_sequence,
            signer_address=user.xrp_address,
            signer_seed=user.xrp_seed,
            fulfillment=fulfillment,
            tx_metadata=json.dumps(metadata)
        )
        
        if 'error' in finish_result:
            # Escrow finish failed
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
            
            return {}, f"Escrow finish failed: {finish_result.get('error')}"
        
        # Escrow finished successfully
        # Create an XRP Ledger transaction record
        xrp_tx = XRPLedgerTransaction(
            user_id=user_id,
            xrp_tx_hash=finish_result.get('hash'),
            from_address=user.xrp_address,
            to_address=owner_address,  # The "to" address is the owner in this case
            amount=original_tx.amount if original_tx else 0.0,
            transaction_type='EscrowFinish',
            ledger_index=finish_result.get('ledger_index'),
            fee=finish_result.get('fee'),
            status=finish_result.get('status', 'pending').lower(),
            tx_metadata=json.dumps(metadata),
            transaction_id=transaction.id
        )
        
        db.session.add(xrp_tx)
        
        # Update the main transaction status
        transaction.status = TransactionStatus.PROCESSING
        
        # If we have the original transaction, update it
        if original_tx and original_tx.transaction_id:
            original_main_tx = Transaction.query.get(original_tx.transaction_id)
            if original_main_tx:
                original_main_tx.status = TransactionStatus.COMPLETED
        
        db.session.commit()
        
        return {
            'transaction_id': transaction_id,
            'xrp_tx_hash': finish_result.get('hash'),
            'amount': original_tx.amount if original_tx else 0.0,
            'signer_address': user.xrp_address,
            'owner_address': owner_address,
            'status': transaction.status.value,
            'date': datetime.utcnow().isoformat()
        }, None
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error finishing XRP escrow: {str(e)}"
        logger.error(error_msg)
        return {}, error_msg

def cancel_xrp_escrow(
    user_id: int,
    owner_address: str,
    escrow_sequence: int
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Cancel an XRP escrow to return funds to the sender
    
    Args:
        user_id: The user ID cancelling the escrow
        owner_address: Address of the account that created the escrow
        escrow_sequence: Sequence number of the EscrowCreate transaction
        
    Returns:
        Tuple[Dict[str, Any], Optional[str]]: Transaction details and error message if any
    """
    user = User.query.get(user_id)
    if not user:
        return {}, "User not found"
    
    if not user.xrp_address or not user.xrp_seed:
        return {}, "User does not have an XRP wallet"
    
    try:
        # Find the original escrow transaction
        original_tx = XRPLedgerTransaction.query.filter(
            XRPLedgerTransaction.tx_metadata.like(f'%"sequence": {escrow_sequence}%'),
            XRPLedgerTransaction.transaction_type == 'EscrowCreate'
        ).first()
        
        # Generate a unique transaction ID
        transaction_id = str(uuid.uuid4())
        
        # Create the transaction in the database
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            amount=original_tx.amount if original_tx else 0.0,
            currency="XRP",
            transaction_type=TransactionType.SETTLEMENT,
            status=TransactionStatus.PENDING,
            description="Cancel XRP Escrow"
        )
        
        db.session.add(transaction)
        db.session.flush()  # Get the transaction ID without committing
        
        # Create metadata
        metadata = {
            'transaction_id': transaction_id,
            'escrow_sequence': escrow_sequence,
            'owner_address': owner_address,
            'original_tx_id': original_tx.id if original_tx else None
        }
        
        # Cancel the XRP escrow
        cancel_result = xrp_ledger.cancel_escrow_payment(
            owner_address=owner_address,
            escrow_sequence=escrow_sequence,
            signer_address=user.xrp_address,
            signer_seed=user.xrp_seed,
            tx_metadata=json.dumps(metadata)
        )
        
        if 'error' in cancel_result:
            # Escrow cancel failed
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
            
            return {}, f"Escrow cancellation failed: {cancel_result.get('error')}"
        
        # Escrow cancelled successfully
        # Create an XRP Ledger transaction record
        xrp_tx = XRPLedgerTransaction(
            user_id=user_id,
            xrp_tx_hash=cancel_result.get('hash'),
            from_address=user.xrp_address,
            to_address=owner_address,  # The "to" address is the owner in this case
            amount=original_tx.amount if original_tx else 0.0,
            transaction_type='EscrowCancel',
            ledger_index=cancel_result.get('ledger_index'),
            fee=cancel_result.get('fee'),
            status=cancel_result.get('status', 'pending').lower(),
            tx_metadata=json.dumps(metadata),
            transaction_id=transaction.id
        )
        
        db.session.add(xrp_tx)
        
        # Update the main transaction status
        transaction.status = TransactionStatus.PROCESSING
        
        # If we have the original transaction, update it
        if original_tx and original_tx.transaction_id:
            original_main_tx = Transaction.query.get(original_tx.transaction_id)
            if original_main_tx:
                original_main_tx.status = TransactionStatus.FAILED
                original_main_tx.description += " (Cancelled)"
        
        db.session.commit()
        
        return {
            'transaction_id': transaction_id,
            'xrp_tx_hash': cancel_result.get('hash'),
            'amount': original_tx.amount if original_tx else 0.0,
            'signer_address': user.xrp_address,
            'owner_address': owner_address,
            'status': transaction.status.value,
            'date': datetime.utcnow().isoformat()
        }, None
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error cancelling XRP escrow: {str(e)}"
        logger.error(error_msg)
        return {}, error_msg