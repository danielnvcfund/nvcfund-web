"""
Treasury Payment Bridge

This module provides automated settlement functionality for payment processors, connecting them
to treasury accounts and creating appropriate transaction records.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Tuple, Optional, List

from sqlalchemy import or_, func, desc
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import TransactionStatus, TreasuryAccount, TreasuryTransaction, TreasuryTransactionType
from payment_models import StripePayment, PayPalPayment, POSPayment

logger = logging.getLogger(__name__)

class SettlementBridge:
    """
    Bridge between payment processors and treasury accounts.
    
    This class handles the automated settlement of payments from various payment processors
    (Stripe, PayPal, POS) into designated treasury accounts.
    """
    
    def __init__(self):
        """Initialize the settlement bridge"""
        self.stripe_account = self._get_settlement_account("Stripe Settlement Account")
        self.paypal_account = self._get_settlement_account("PayPal Settlement Account")
        self.pos_account = self._get_settlement_account("POS Settlement Account")
    
    def _get_settlement_account(self, description: str) -> Optional[TreasuryAccount]:
        """Get or create a settlement account for a payment processor"""
        account = TreasuryAccount.query.filter_by(
            account_type='OPERATING',
            description=description
        ).first()
        
        # If no account exists, log a warning but don't create one - this should be done manually
        if not account:
            logger.warning(f"No settlement account found for {description}")
        
        return account
    
    def settle_stripe_payments(self) -> Tuple[str, float]:
        """
        Settle all unsettled Stripe payments
        
        Returns:
            Tuple of (settlement_id, total_amount)
        """
        # Check if settlement account exists
        if not self.stripe_account:
            logger.error("Cannot settle Stripe payments - no settlement account configured")
            return ("error-no-account", 0.0)
            
        # Find unsettled Stripe payments
        payments = StripePayment.query.filter_by(
            is_settled=False,
            status='succeeded'
        ).all()
        
        if not payments:
            logger.info("No unsettled Stripe payments to settle")
            return ("no-payments", 0.0)
        
        # Calculate total settlement amount
        total_amount = sum(payment.amount for payment in payments)
        
        # Generate a unique settlement reference
        settlement_id = f"STRIPE-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        
        # Create treasury transaction
        try:
            # Begin transaction
            transaction = TreasuryTransaction()
            transaction.transaction_id = settlement_id
            transaction.to_account_id = self.stripe_account.id
            transaction.amount = total_amount
            transaction.currency = "USD"  # Assuming USD for now
            transaction.transaction_type = TransactionType.PAYMENT_SETTLEMENT
            transaction.description = f"Stripe payment processor settlement - {len(payments)} payments"
            transaction.reference_number = settlement_id
            transaction.memo = f"Automated settlement of {len(payments)} Stripe payments"
            transaction.status = TransactionStatus.COMPLETED
            
            db.session.add(transaction)
            
            # Update treasury account balance
            self.stripe_account.current_balance += total_amount
            
            # Mark all payments as settled
            for payment in payments:
                payment.is_settled = True
                payment.settlement_date = datetime.utcnow()
                payment.settlement_reference = settlement_id
            
            # Commit transaction
            db.session.commit()
            
            logger.info(f"Successfully settled {len(payments)} Stripe payments for ${total_amount:.2f}")
            return (settlement_id, total_amount)
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error settling Stripe payments: {str(e)}")
            return ("error", 0.0)
    
    def settle_paypal_payments(self) -> Tuple[str, float]:
        """
        Settle all unsettled PayPal payments
        
        Returns:
            Tuple of (settlement_id, total_amount)
        """
        # Check if settlement account exists
        if not self.paypal_account:
            logger.error("Cannot settle PayPal payments - no settlement account configured")
            return ("error-no-account", 0.0)
            
        # Find unsettled PayPal payments
        payments = PayPalPayment.query.filter_by(
            is_settled=False,
            status='COMPLETED'
        ).all()
        
        if not payments:
            logger.info("No unsettled PayPal payments to settle")
            return ("no-payments", 0.0)
        
        # Calculate total settlement amount
        total_amount = sum(payment.amount for payment in payments)
        
        # Generate a unique settlement reference
        settlement_id = f"PAYPAL-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        
        # Create treasury transaction
        try:
            # Begin transaction
            transaction = TreasuryTransaction()
            transaction.transaction_id = settlement_id
            transaction.to_account_id = self.paypal_account.id
            transaction.amount = total_amount
            transaction.currency = "USD"  # Assuming USD for now
            transaction.transaction_type = TransactionType.PAYMENT_SETTLEMENT
            transaction.description = f"PayPal payment processor settlement - {len(payments)} payments"
            transaction.reference_number = settlement_id
            transaction.memo = f"Automated settlement of {len(payments)} PayPal payments"
            transaction.status = TransactionStatus.COMPLETED
            
            db.session.add(transaction)
            
            # Update treasury account balance
            self.paypal_account.current_balance += total_amount
            
            # Mark all payments as settled
            for payment in payments:
                payment.is_settled = True
                payment.settlement_date = datetime.utcnow()
                payment.settlement_reference = settlement_id
            
            # Commit transaction
            db.session.commit()
            
            logger.info(f"Successfully settled {len(payments)} PayPal payments for ${total_amount:.2f}")
            return (settlement_id, total_amount)
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error settling PayPal payments: {str(e)}")
            return ("error", 0.0)
    
    def settle_pos_payments(self) -> Tuple[str, float]:
        """
        Settle all unsettled POS payments
        
        Returns:
            Tuple of (settlement_id, total_amount)
        """
        # Check if settlement account exists
        if not self.pos_account:
            logger.error("Cannot settle POS payments - no settlement account configured")
            return ("error-no-account", 0.0)
            
        # Find unsettled POS payments
        payments = POSPayment.query.filter_by(
            is_settled=False,
            status='completed'
        ).all()
        
        if not payments:
            logger.info("No unsettled POS payments to settle")
            return ("no-payments", 0.0)
        
        # Calculate total settlement amount
        total_amount = sum(payment.amount for payment in payments)
        
        # Generate a unique settlement reference
        settlement_id = f"POS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        
        # Create treasury transaction
        try:
            # Begin transaction
            transaction = TreasuryTransaction()
            transaction.transaction_id = settlement_id
            transaction.to_account_id = self.pos_account.id
            transaction.amount = total_amount
            transaction.currency = "USD"  # Assuming USD for now
            transaction.transaction_type = TransactionType.PAYMENT_SETTLEMENT
            transaction.description = f"POS payment processor settlement - {len(payments)} payments"
            transaction.reference_number = settlement_id
            transaction.memo = f"Automated settlement of {len(payments)} POS payments"
            transaction.status = TransactionStatus.COMPLETED
            
            db.session.add(transaction)
            
            # Update treasury account balance
            self.pos_account.current_balance += total_amount
            
            # Mark all payments as settled
            for payment in payments:
                payment.is_settled = True
                payment.settlement_date = datetime.utcnow()
                payment.settlement_reference = settlement_id
            
            # Commit transaction
            db.session.commit()
            
            logger.info(f"Successfully settled {len(payments)} POS payments for ${total_amount:.2f}")
            return (settlement_id, total_amount)
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error settling POS payments: {str(e)}")
            return ("error", 0.0)
            
    def get_settlement_statistics(self, days: int = 30) -> dict:
        """
        Get settlement statistics for all payment processors
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with statistics for each payment processor
        """
        stats = {
            'stripe': {'count': 0, 'total': 0.0},
            'paypal': {'count': 0, 'total': 0.0},
            'pos': {'count': 0, 'total': 0.0},
            'total': 0.0
        }
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get Stripe settlement statistics
        stripe_payments = StripePayment.query.filter(
            StripePayment.is_settled == True,
            StripePayment.settlement_date >= cutoff_date
        ).all()
        
        stats['stripe']['count'] = len(stripe_payments)
        stats['stripe']['total'] = sum(payment.amount for payment in stripe_payments)
        
        # Get PayPal settlement statistics
        paypal_payments = PayPalPayment.query.filter(
            PayPalPayment.is_settled == True,
            PayPalPayment.settlement_date >= cutoff_date
        ).all()
        
        stats['paypal']['count'] = len(paypal_payments)
        stats['paypal']['total'] = sum(payment.amount for payment in paypal_payments)
        
        # Get POS settlement statistics
        pos_payments = POSPayment.query.filter(
            POSPayment.is_settled == True,
            POSPayment.settlement_date >= cutoff_date
        ).all()
        
        stats['pos']['count'] = len(pos_payments)
        stats['pos']['total'] = sum(payment.amount for payment in pos_payments)
        
        # Calculate total
        stats['total'] = (
            stats['stripe']['total'] + 
            stats['paypal']['total'] + 
            stats['pos']['total']
        )
        
        return stats