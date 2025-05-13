"""
Treasury Payment Bridge
-----------------------

This module provides the integration layer between payment processors 
(Stripe, PayPal, POS) and treasury accounts.

It enables:
1. Settlement of payment processor funds to treasury accounts
2. Tracking payment processor balances
3. Reconciliation of payment records with treasury accounts
"""

import logging
import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import func
from decimal import Decimal

from flask import current_app
from flask_sqlalchemy import SQLAlchemy

from app import db
from models import (
    TreasuryAccount, 
    TreasuryTransaction,
    TransactionType,
    TransactionStatus,
    TreasuryAccountType
)
from payment_models import (
    StripePayment,
    PayPalPayment,
    POSPayment,
    Payment
)

logger = logging.getLogger(__name__)

# Configuration - can be moved to environment variables later
DEFAULT_SETTLEMENT_CURRENCY = "USD"
SETTLEMENT_ACCOUNT_PREFIX = {
    "stripe": "STRIPE-SETTLE-",
    "paypal": "PAYPAL-SETTLE-",
    "pos": "POS-SETTLE-"
}

def get_processor_linked_account(processor: str) -> Optional[TreasuryAccount]:
    """
    Get the treasury account linked to a specific payment processor for settlements.
    
    Args:
        processor: The payment processor type ('stripe', 'paypal', 'pos')
        
    Returns:
        The linked TreasuryAccount or None if not found
    """
    if processor not in SETTLEMENT_ACCOUNT_PREFIX:
        logger.error(f"Invalid processor type: {processor}")
        return None
    
    # Look for an account with the appropriate name pattern
    prefix = SETTLEMENT_ACCOUNT_PREFIX[processor]
    account = TreasuryAccount.query.filter(
        TreasuryAccount.name.like(f"{prefix}%"),
        TreasuryAccount.is_active == True
    ).first()
    
    return account

def create_settlement_account(processor: str, currency: str = DEFAULT_SETTLEMENT_CURRENCY) -> Optional[TreasuryAccount]:
    """
    Create a new treasury account for a payment processor settlement.
    
    Args:
        processor: The payment processor type ('stripe', 'paypal', 'pos')
        currency: The currency for the account
        
    Returns:
        The newly created TreasuryAccount or None if failed
    """
    if processor not in SETTLEMENT_ACCOUNT_PREFIX:
        logger.error(f"Invalid processor type: {processor}")
        return None
    
    # Check if account already exists
    existing = get_processor_linked_account(processor)
    if existing:
        logger.info(f"Settlement account for {processor} already exists: {existing.name}")
        return existing
    
    # Generate a unique account name and number
    prefix = SETTLEMENT_ACCOUNT_PREFIX[processor]
    timestamp = datetime.datetime.now().strftime("%Y%m%d")
    account_name = f"{prefix}{timestamp}"
    account_number = f"{prefix}{timestamp}-{processor.upper()}"
    
    try:
        # Create new treasury account
        account = TreasuryAccount(
            name=account_name,
            account_number=account_number,
            account_type=TreasuryAccountType.OPERATING,
            financial_institution="NVC Banking Platform",
            description=f"Settlement account for {processor} payments",
            current_balance=0.0,
            currency=currency,
            is_active=True,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        
        db.session.add(account)
        db.session.commit()
        
        logger.info(f"Created new settlement account for {processor}: {account_name}")
        return account
    
    except Exception as e:
        logger.error(f"Error creating settlement account for {processor}: {str(e)}")
        db.session.rollback()
        return None

def record_settlement_transaction(
    to_account: TreasuryAccount,
    amount: float,
    processor_type: str,
    currency: str = None,
    reference: str = None,
    description: str = None
) -> Optional[TreasuryTransaction]:
    """
    Record a settlement transaction from a payment processor to a treasury account.
    
    Args:
        to_account: The treasury account to settle funds to
        amount: The amount to settle
        processor_type: The payment processor type ('stripe', 'paypal', 'pos')
        currency: The currency of the settlement (defaults to account currency)
        reference: External reference number
        description: Optional description
        
    Returns:
        The created TreasuryTransaction or None if failed
    """
    if not to_account:
        logger.error("Cannot record settlement: No target account provided")
        return None
    
    if amount <= 0:
        logger.error(f"Invalid settlement amount: {amount}")
        return None
    
    # Use account currency if not specified
    if not currency:
        currency = to_account.currency
    
    # Generate a descriptive transaction description if not provided
    if not description:
        description = f"Settlement from {processor_type.upper()} payment processor"
    
    try:
        # Create the transaction
        transaction = TreasuryTransaction(
            to_account_id=to_account.id,
            amount=amount,
            currency=currency,
            transaction_type=TransactionType.PAYMENT_SETTLEMENT,
            description=description,
            external_reference=reference,
            status=TransactionStatus.COMPLETED,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        
        # Update the account balance
        to_account.current_balance += amount
        to_account.updated_at = datetime.datetime.utcnow()
        
        # Save changes
        db.session.add(transaction)
        db.session.add(to_account)
        db.session.commit()
        
        logger.info(f"Recorded settlement from {processor_type} to account {to_account.name}: {amount} {currency}")
        return transaction
    
    except Exception as e:
        logger.error(f"Error recording settlement transaction: {str(e)}")
        db.session.rollback()
        return None

def process_stripe_settlements(days_back: int = 1) -> Tuple[int, float]:
    """
    Process unsettled Stripe payments from the past N days.
    
    Args:
        days_back: Number of days to look back for unsettled payments
        
    Returns:
        Tuple of (number of settlements processed, total amount settled)
    """
    # Get the settlement account
    settlement_account = get_processor_linked_account('stripe')
    if not settlement_account:
        logger.error("No Stripe settlement account found. Please create one first.")
        return (0, 0.0)
    
    # Calculate the cutoff date
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_back)
    
    # Find all successful Stripe payments from the past N days that haven't been marked as settled
    unsettled_payments = StripePayment.query.filter(
        StripePayment.created_at >= cutoff_date,
        StripePayment.status == 'succeeded',
        StripePayment.is_settled == False
    ).all()
    
    if not unsettled_payments:
        logger.info(f"No unsettled Stripe payments found in the past {days_back} days")
        return (0, 0.0)
    
    # Process each payment
    settlement_count = 0
    total_settled = 0.0
    
    for payment in unsettled_payments:
        # Record the settlement
        transaction = record_settlement_transaction(
            to_account=settlement_account,
            amount=payment.amount,
            processor_type='stripe',
            currency=payment.currency,
            reference=payment.stripe_payment_id,
            description=f"Stripe payment settlement: {payment.stripe_payment_id}"
        )
        
        if transaction:
            # Mark the payment as settled
            payment.is_settled = True
            payment.settlement_date = datetime.datetime.utcnow()
            payment.settlement_reference = str(transaction.id)
            db.session.add(payment)
            
            settlement_count += 1
            total_settled += payment.amount
    
    # Commit all changes
    try:
        db.session.commit()
        logger.info(f"Processed {settlement_count} Stripe settlements totaling {total_settled} {settlement_account.currency}")
    except Exception as e:
        logger.error(f"Error finalizing Stripe settlements: {str(e)}")
        db.session.rollback()
        return (0, 0.0)
    
    return (settlement_count, total_settled)

def process_paypal_settlements(days_back: int = 1) -> Tuple[int, float]:
    """
    Process unsettled PayPal payments from the past N days.
    
    Args:
        days_back: Number of days to look back for unsettled payments
        
    Returns:
        Tuple of (number of settlements processed, total amount settled)
    """
    # Get the settlement account
    settlement_account = get_processor_linked_account('paypal')
    if not settlement_account:
        logger.error("No PayPal settlement account found. Please create one first.")
        return (0, 0.0)
    
    # Calculate the cutoff date
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_back)
    
    # Find all completed PayPal payments from the past N days that haven't been marked as settled
    unsettled_payments = PayPalPayment.query.filter(
        PayPalPayment.created_at >= cutoff_date,
        PayPalPayment.status == 'COMPLETED',
        PayPalPayment.is_settled == False
    ).all()
    
    if not unsettled_payments:
        logger.info(f"No unsettled PayPal payments found in the past {days_back} days")
        return (0, 0.0)
    
    # Process each payment
    settlement_count = 0
    total_settled = 0.0
    
    for payment in unsettled_payments:
        # Record the settlement
        transaction = record_settlement_transaction(
            to_account=settlement_account,
            amount=payment.amount,
            processor_type='paypal',
            currency=payment.currency,
            reference=payment.paypal_id,
            description=f"PayPal payment settlement: {payment.paypal_id}"
        )
        
        if transaction:
            # Mark the payment as settled
            payment.is_settled = True
            payment.settlement_date = datetime.datetime.utcnow()
            payment.settlement_reference = str(transaction.id)
            db.session.add(payment)
            
            settlement_count += 1
            total_settled += payment.amount
    
    # Commit all changes
    try:
        db.session.commit()
        logger.info(f"Processed {settlement_count} PayPal settlements totaling {total_settled} {settlement_account.currency}")
    except Exception as e:
        logger.error(f"Error finalizing PayPal settlements: {str(e)}")
        db.session.rollback()
        return (0, 0.0)
    
    return (settlement_count, total_settled)

def process_pos_settlements(days_back: int = 1) -> Tuple[int, float]:
    """
    Process unsettled POS payments from the past N days.
    
    Args:
        days_back: Number of days to look back for unsettled payments
        
    Returns:
        Tuple of (number of settlements processed, total amount settled)
    """
    # Get the settlement account
    settlement_account = get_processor_linked_account('pos')
    if not settlement_account:
        logger.error("No POS settlement account found. Please create one first.")
        return (0, 0.0)
    
    # Calculate the cutoff date
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_back)
    
    # Find all completed POS payments from the past N days that haven't been marked as settled
    unsettled_payments = POSPayment.query.filter(
        POSPayment.created_at >= cutoff_date,
        POSPayment.status == 'completed',
        POSPayment.is_settled == False
    ).all()
    
    if not unsettled_payments:
        logger.info(f"No unsettled POS payments found in the past {days_back} days")
        return (0, 0.0)
    
    # Process each payment
    settlement_count = 0
    total_settled = 0.0
    
    for payment in unsettled_payments:
        # Record the settlement
        transaction = record_settlement_transaction(
            to_account=settlement_account,
            amount=payment.amount,
            processor_type='pos',
            currency=payment.currency,
            reference=payment.transaction_id,
            description=f"POS payment settlement: {payment.transaction_id}"
        )
        
        if transaction:
            # Mark the payment as settled
            payment.is_settled = True
            payment.settlement_date = datetime.datetime.utcnow()
            payment.settlement_reference = str(transaction.id)
            db.session.add(payment)
            
            settlement_count += 1
            total_settled += payment.amount
    
    # Commit all changes
    try:
        db.session.commit()
        logger.info(f"Processed {settlement_count} POS settlements totaling {total_settled} {settlement_account.currency}")
    except Exception as e:
        logger.error(f"Error finalizing POS settlements: {str(e)}")
        db.session.rollback()
        return (0, 0.0)
    
    return (settlement_count, total_settled)

def process_all_settlements(days_back: int = 1) -> Dict[str, Tuple[int, float]]:
    """
    Process settlements for all payment processors.
    
    Args:
        days_back: Number of days to look back for unsettled payments
        
    Returns:
        Dictionary of processor: (settlement_count, total_amount) pairs
    """
    results = {}
    
    # Process each payment processor
    results['stripe'] = process_stripe_settlements(days_back)
    results['paypal'] = process_paypal_settlements(days_back)
    results['pos'] = process_pos_settlements(days_back)
    
    # Calculate totals
    total_count = sum(count for count, _ in results.values())
    total_amount = sum(amount for _, amount in results.values())
    
    logger.info(f"Processed {total_count} total settlements across all processors, totaling approximately {total_amount} USD")
    
    return results

def get_settlement_statistics() -> Dict[str, Any]:
    """
    Get statistics about payment settlements.
    
    Returns:
        Dictionary containing settlement statistics
    """
    stats = {}
    
    # Get today and 30 days ago for calculations
    today = datetime.datetime.utcnow()
    thirty_days_ago = today - datetime.timedelta(days=30)
    
    # Get total settlements by processor in the last 30 days
    processor_totals = {}
    for processor in ['stripe', 'paypal', 'pos']:
        account = get_processor_linked_account(processor)
        
        if account:
            # Get total settlement amount in last 30 days
            total = db.session.query(
                func.sum(TreasuryTransaction.amount)
            ).filter(
                TreasuryTransaction.to_account_id == account.id,
                TreasuryTransaction.transaction_type == TransactionType.PAYMENT_SETTLEMENT,
                TreasuryTransaction.created_at >= thirty_days_ago
            ).scalar() or 0.0
            
            # Get count of settlements in last 30 days
            count = db.session.query(
                func.count(TreasuryTransaction.id)
            ).filter(
                TreasuryTransaction.to_account_id == account.id,
                TreasuryTransaction.transaction_type == TransactionType.PAYMENT_SETTLEMENT,
                TreasuryTransaction.created_at >= thirty_days_ago
            ).scalar() or 0
            
            processor_totals[processor] = {
                'account': account,
                'total_30d': float(total),
                'count_30d': count,
                'currency': account.currency
            }
        else:
            processor_totals[processor] = {
                'account': None,
                'total_30d': 0.0,
                'count_30d': 0,
                'currency': DEFAULT_SETTLEMENT_CURRENCY
            }
    
    stats['processor_totals'] = processor_totals
    
    # Get total settled amount across all processors
    total_settled = sum(details['total_30d'] for details in processor_totals.values())
    stats['total_settled_30d'] = total_settled
    
    # Get the most recent settlement for each processor
    most_recent = {}
    for processor in ['stripe', 'paypal', 'pos']:
        account = get_processor_linked_account(processor)
        
        if account:
            recent = TreasuryTransaction.query.filter(
                TreasuryTransaction.to_account_id == account.id,
                TreasuryTransaction.transaction_type == TransactionType.PAYMENT_SETTLEMENT
            ).order_by(
                TreasuryTransaction.created_at.desc()
            ).first()
            
            most_recent[processor] = recent
        else:
            most_recent[processor] = None
    
    stats['most_recent'] = most_recent
    
    return stats

def manual_settlement(
    account_id: int,
    processor_type: str,
    amount: float,
    currency: str,
    reference: str = None,
    description: str = None
) -> Optional[TreasuryTransaction]:
    """
    Record a manual settlement from a payment processor to a treasury account.
    
    Args:
        account_id: ID of the treasury account to settle funds to
        processor_type: The payment processor type ('stripe', 'paypal', 'pos', 'other')
        amount: The amount to settle
        currency: The currency of the settlement
        reference: External reference number
        description: Optional description
        
    Returns:
        The created TreasuryTransaction or None if failed
    """
    try:
        # Get the account
        account = TreasuryAccount.query.get(account_id)
        if not account:
            logger.error(f"Account with ID {account_id} not found")
            return None
        
        # Generate a descriptive transaction description if not provided
        if not description:
            description = f"Manual settlement from {processor_type.upper()} payment processor"
        
        # Record the settlement
        transaction = record_settlement_transaction(
            to_account=account,
            amount=amount,
            processor_type=processor_type,
            currency=currency,
            reference=reference,
            description=description
        )
        
        return transaction
        
    except Exception as e:
        logger.error(f"Error recording manual settlement: {str(e)}")
        db.session.rollback()
        return None