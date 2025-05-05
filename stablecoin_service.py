"""
NVC Token Stablecoin Service

This module provides functionality for managing the closed-loop peer-to-peer
ledger transaction settlement and payment ecosystem using NVC Token Stablecoin.

The NVC Token Stablecoin (NVCT) is fully backed by a $10 trillion portfolio of 
high-quality assets and cash equivalents maintained by NVC Fund Bank, ensuring 
a stable 1:1 USD peg and providing unparalleled security and liquidity for 
global settlement operations.
"""

import logging
import secrets
from datetime import datetime
from decimal import Decimal

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import (
    StablecoinAccount, 
    LedgerEntry, 
    CorrespondentBank,
    SettlementBatch, 
    Transaction, 
    TransactionStatus, 
    TransactionType,
    User
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_stablecoin_account(user_id, account_type="INDIVIDUAL", initial_balance=0.0):
    """Create a new stablecoin account for a user"""
    try:
        # Generate unique account number
        account_number = f"NVCT-{secrets.token_hex(6).upper()}"
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User with ID {user_id} not found")
            return None, "User not found"
        
        # Create account
        account = StablecoinAccount(
            account_number=account_number,
            user_id=user_id,
            balance=float(initial_balance),
            account_type=account_type
        )
        
        db.session.add(account)
        db.session.commit()
        
        logger.info(f"Created stablecoin account {account_number} for user {user_id}")
        return account, None
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating stablecoin account: {str(e)}")
        return None, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating stablecoin account: {str(e)}")
        return None, f"Error: {str(e)}"

def get_account_balance(account_id):
    """Get the current balance of a stablecoin account"""
    try:
        account = StablecoinAccount.query.get(account_id)
        if not account:
            return None, "Account not found"
        
        return account.balance, None
    
    except Exception as e:
        logger.error(f"Error retrieving account balance: {str(e)}")
        return None, f"Error: {str(e)}"

def transfer_stablecoins(from_account_id, to_account_id, amount, description=None):
    """Transfer stablecoins between accounts"""
    try:
        # Convert amount to float with 2 decimal precision
        amount = float(Decimal(str(amount)).quantize(Decimal('0.01')))
        
        if amount <= 0:
            return None, "Transfer amount must be positive"
        
        # Get source and destination accounts
        source_account = StablecoinAccount.query.get(from_account_id)
        if not source_account:
            return None, "Source account not found"
        
        destination_account = StablecoinAccount.query.get(to_account_id)
        if not destination_account:
            return None, "Destination account not found"
        
        # Check if accounts are active
        if not source_account.is_active:
            return None, "Source account is inactive"
        
        if not destination_account.is_active:
            return None, "Destination account is inactive"
        
        # Check sufficient balance
        if source_account.balance < amount:
            return None, "Insufficient funds"
        
        # Generate unique transaction ID
        transaction_id = secrets.token_hex(16)
        
        # Create transaction record
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=source_account.user_id,
            amount=amount,
            currency=source_account.currency,
            transaction_type=TransactionType.STABLECOIN_TRANSFER,
            status=TransactionStatus.COMPLETED,
            description=description or f"Transfer to {destination_account.account_number}",
            recipient_name=f"Account: {destination_account.account_number}",
            recipient_account=destination_account.account_number
        )
        
        # Update account balances
        source_account.balance -= amount
        destination_account.balance += amount
        
        # Create ledger entries
        source_balance_after = source_account.balance
        dest_balance_after = destination_account.balance
        
        debit_entry = LedgerEntry(
            transaction_id=transaction_id,
            account_id=source_account.id,
            entry_type='DEBIT',
            amount=amount,
            balance_after=source_balance_after,
            description=f"Transfer to {destination_account.account_number}"
        )
        
        credit_entry = LedgerEntry(
            transaction_id=transaction_id,
            account_id=destination_account.id,
            entry_type='CREDIT',
            amount=amount,
            balance_after=dest_balance_after,
            description=f"Transfer from {source_account.account_number}"
        )
        
        # Save everything to database
        db.session.add(transaction)
        db.session.add(debit_entry)
        db.session.add(credit_entry)
        db.session.commit()
        
        logger.info(f"Completed stablecoin transfer of {amount} {source_account.currency} from {source_account.account_number} to {destination_account.account_number}")
        return transaction, None
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during stablecoin transfer: {str(e)}")
        return None, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing stablecoin transfer: {str(e)}")
        return None, f"Error: {str(e)}"

def create_correspondent_bank(name, bank_code, swift_code=None, ach_routing_number=None):
    """Create a new correspondent bank in the closed-loop system"""
    try:
        # Generate a stablecoin account for the correspondent bank
        account, error = create_stablecoin_account(
            # Use the admin user's ID (assuming ID 1 is admin)
            user_id=1,
            account_type="INSTITUTION",
            initial_balance=0.0
        )
        
        if error:
            return None, f"Failed to create stablecoin account: {error}"
        
        # Create the correspondent bank
        bank = CorrespondentBank(
            name=name,
            bank_code=bank_code,
            swift_code=swift_code,
            ach_routing_number=ach_routing_number,
            stablecoin_account_id=account.id,
            supports_ach=bool(ach_routing_number),
            supports_swift=bool(swift_code)
        )
        
        db.session.add(bank)
        db.session.commit()
        
        logger.info(f"Created correspondent bank {name} with code {bank_code}")
        return bank, None
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating correspondent bank: {str(e)}")
        return None, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating correspondent bank: {str(e)}")
        return None, f"Error: {str(e)}"

def create_settlement_batch(correspondent_bank_id, total_amount, settlement_method="ACH"):
    """Create a new settlement batch for a correspondent bank"""
    try:
        # Get the correspondent bank
        bank = CorrespondentBank.query.get(correspondent_bank_id)
        if not bank:
            return None, "Correspondent bank not found"
        
        # Calculate fee amount based on bank's fee percentage
        fee_percentage = bank.settlement_fee_percentage
        fee_amount = total_amount * (fee_percentage / 100.0)
        net_amount = total_amount - fee_amount
        
        # Generate unique batch ID
        batch_id = f"SETTLE-{secrets.token_hex(8).upper()}"
        
        # Create the settlement batch
        batch = SettlementBatch(
            batch_id=batch_id,
            correspondent_bank_id=correspondent_bank_id,
            total_amount=total_amount,
            fee_amount=fee_amount,
            net_amount=net_amount,
            settlement_method=settlement_method,
            status=TransactionStatus.PENDING
        )
        
        db.session.add(batch)
        db.session.commit()
        
        logger.info(f"Created settlement batch {batch_id} for {bank.name} with total amount {total_amount}")
        return batch, None
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating settlement batch: {str(e)}")
        return None, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating settlement batch: {str(e)}")
        return None, f"Error: {str(e)}"

def complete_settlement_batch(batch_id, external_reference):
    """Mark a settlement batch as completed after external processing"""
    try:
        # Get the batch
        batch = SettlementBatch.query.filter_by(batch_id=batch_id).first()
        if not batch:
            return None, "Settlement batch not found"
        
        # Update batch status
        batch.status = TransactionStatus.COMPLETED
        batch.external_reference = external_reference
        batch.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Completed settlement batch {batch_id} with external reference {external_reference}")
        return batch, None
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error completing settlement batch: {str(e)}")
        return None, f"Database error: {str(e)}"
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error completing settlement batch: {str(e)}")
        return None, f"Error: {str(e)}"

def get_account_transactions(account_id, limit=50, offset=0):
    """Get transactions for a stablecoin account"""
    try:
        # Get the account
        account = StablecoinAccount.query.get(account_id)
        if not account:
            return None, "Account not found"
        
        # Get ledger entries for the account
        entries = LedgerEntry.query.filter_by(account_id=account_id)\
            .order_by(LedgerEntry.created_at.desc())\
            .limit(limit).offset(offset).all()
        
        # Get transaction IDs from the entries
        transaction_ids = [entry.transaction_id for entry in entries]
        
        # Get the transactions
        transactions = Transaction.query.filter(
            Transaction.transaction_id.in_(transaction_ids)
        ).all()
        
        # Create a mapping of transaction_id to transaction
        tx_map = {tx.transaction_id: tx for tx in transactions}
        
        # Combine entries with their transactions
        results = []
        for entry in entries:
            tx = tx_map.get(entry.transaction_id)
            if tx:
                results.append({
                    'entry': entry,
                    'transaction': tx
                })
        
        return results, None
    
    except Exception as e:
        logger.error(f"Error retrieving account transactions: {str(e)}")
        return None, f"Error: {str(e)}"