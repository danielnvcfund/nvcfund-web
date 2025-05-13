"""
Treasury Payment Bridge - Integration between Treasury Accounts and Payment Processors
"""
import os
import time
import logging
import stripe
import paypalrestsdk
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import text, desc

from models import db, TreasuryAccount, TreasuryTransaction, PaymentGateway
from models import TransactionType, TransactionStatus, TreasuryAccountType

logger = logging.getLogger(__name__)

class TreasuryPaymentBridge:
    """
    Provides settlement functionality between payment processors and treasury accounts.
    This bridge allows for automatic settlement of funds between payment processors
    (Stripe, PayPal, POS) and dedicated treasury accounts.
    """
    
    def __init__(self):
        self.stripe_api_key = os.environ.get('STRIPE_LIVE_SECRET_KEY') or os.environ.get('STRIPE_SECRET_KEY')
        self.paypal_mode = "live" if os.environ.get('PAYPAL_CLIENT_ID', '').startswith('live') else "sandbox"
        
        # Configure PayPal SDK
        paypalrestsdk.configure({
            "mode": self.paypal_mode,
            "client_id": os.environ.get('PAYPAL_CLIENT_ID'),
            "client_secret": os.environ.get('PAYPAL_CLIENT_SECRET')
        })
        
        # Configure Stripe
        if self.stripe_api_key:
            stripe.api_key = self.stripe_api_key
    
    def get_processor_linked_account(self, processor_type):
        """
        Gets the treasury account linked to a specific payment processor.
        If no account is explicitly linked, it will look for a suitable OPERATING account.
        
        Args:
            processor_type (str): The type of processor ('stripe', 'paypal', 'pos')
            
        Returns:
            TreasuryAccount: The linked treasury account or None if not found
        """
        # First, check for an account with the processor type in the name (case insensitive)
        processor_account = TreasuryAccount.query.filter(
            TreasuryAccount.is_active == True,
            TreasuryAccount.account_type == TreasuryAccountType.OPERATING,
            db.func.lower(TreasuryAccount.name).contains(processor_type.lower())
        ).first()
        
        if processor_account:
            logger.info(f"Found dedicated {processor_type} treasury account: {processor_account.name}")
            return processor_account
        
        # If no specific account found, look for a general operating account
        logger.warning(f"No dedicated {processor_type} treasury account found, looking for general operating account")
        general_account = TreasuryAccount.query.filter(
            TreasuryAccount.is_active == True,
            TreasuryAccount.account_type == TreasuryAccountType.OPERATING
        ).order_by(desc(TreasuryAccount.current_balance)).first()
        
        if general_account:
            logger.info(f"Using general operating treasury account: {general_account.name}")
            return general_account
        
        logger.error(f"No suitable treasury account found for {processor_type} integration")
        return None
    
    def create_processor_linked_account(self, processor_type, initial_balance=0.0, 
                                       currency="USD", institution_id=None):
        """
        Creates a dedicated treasury account for a specific payment processor.
        
        Args:
            processor_type (str): The type of processor ('stripe', 'paypal', 'pos')
            initial_balance (float): Initial balance to set for the account
            currency (str): Currency code for the account
            institution_id (int): ID of the financial institution
            
        Returns:
            TreasuryAccount: The newly created treasury account
        """
        # Format the processor type name for readability
        processor_name = processor_type.title()
        
        # Create a new operating account for this processor
        account = TreasuryAccount(
            name=f"{processor_name} Settlement Account",
            description=f"Dedicated treasury account for {processor_name} payment processing",
            account_type=TreasuryAccountType.OPERATING,
            institution_id=institution_id,
            account_number=f"{processor_type.upper()}-SETTLEMENT-{int(time.time())}",
            currency=currency,
            current_balance=initial_balance,
            available_balance=initial_balance,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(account)
        db.session.commit()
        
        logger.info(f"Created new {processor_name} settlement treasury account: {account.name}")
        return account
    
    def record_settlement_transaction(self, account_id, amount, processor_type, 
                                     external_reference=None, description=None):
        """
        Records a settlement transaction between a payment processor and treasury account.
        
        Args:
            account_id (int): ID of the treasury account
            amount (float): Transaction amount
            processor_type (str): The type of processor ('stripe', 'paypal', 'pos')
            external_reference (str): External reference ID from the processor
            description (str): Transaction description
            
        Returns:
            TreasuryTransaction: The newly created transaction record
        """
        # Generate a descriptive transaction message if none provided
        if not description:
            description = f"Settlement from {processor_type.title()} payment processor"
            if external_reference:
                description += f" (Ref: {external_reference})"
        
        # Create the transaction record
        transaction = TreasuryTransaction(
            from_account_id=None,  # External source
            to_account_id=account_id,
            amount=amount,
            currency=TreasuryAccount.query.get(account_id).currency,
            transaction_type=TransactionType.PAYMENT_SETTLEMENT,
            status=TransactionStatus.COMPLETED,
            description=description,
            external_reference=external_reference,
            transaction_date=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(transaction)
        
        # Update the treasury account balance
        account = TreasuryAccount.query.get(account_id)
        if account:
            account.current_balance += amount
            account.available_balance += amount
            account.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Recorded settlement transaction of {amount} from {processor_type} to treasury account {account_id}")
        return transaction
    
    def process_stripe_settlement(self, days_back=1):
        """
        Processes settlement from Stripe to the linked treasury account.
        Looks for successful charges within the specified timeframe.
        
        Args:
            days_back (int): Number of days back to look for charges
            
        Returns:
            dict: Summary of the settlement process
        """
        if not self.stripe_api_key:
            logger.error("Cannot process Stripe settlement: No API key configured")
            return {"success": False, "error": "No Stripe API key configured"}
        
        # Find the linked treasury account
        account = self.get_processor_linked_account('stripe')
        if not account:
            logger.error("Cannot process Stripe settlement: No linked treasury account found")
            return {"success": False, "error": "No linked treasury account found"}
        
        # Calculate the time window
        end_time = int(time.time())
        start_time = int((datetime.utcnow() - timedelta(days=days_back)).timestamp())
        
        try:
            # Retrieve successful charges within the time window
            charges = stripe.Charge.list(
                created={"gte": start_time, "lte": end_time},
                status="succeeded",
                limit=100
            )
            
            # Process the charges
            total_amount = 0
            count = 0
            
            for charge in charges.auto_paging_iter():
                # Skip charges that have already been settled
                if TreasuryTransaction.query.filter_by(
                    external_reference=charge.id,
                    transaction_type=TransactionType.PAYMENT_SETTLEMENT
                ).first():
                    logger.debug(f"Skipping already settled Stripe charge: {charge.id}")
                    continue
                
                # Convert amount from cents to dollars
                amount = charge.amount / 100.0
                
                # Record the settlement
                self.record_settlement_transaction(
                    account_id=account.id,
                    amount=amount,
                    processor_type='stripe',
                    external_reference=charge.id,
                    description=f"Stripe payment settlement: {charge.description or charge.id}"
                )
                
                total_amount += amount
                count += 1
            
            logger.info(f"Processed {count} Stripe charges for settlement, total: {total_amount}")
            return {
                "success": True,
                "processor": "stripe",
                "count": count,
                "total_amount": total_amount,
                "currency": account.currency,
                "account_id": account.id,
                "account_name": account.name
            }
            
        except Exception as e:
            logger.error(f"Error processing Stripe settlement: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def process_paypal_settlement(self, days_back=1):
        """
        Processes settlement from PayPal to the linked treasury account.
        Looks for successful payments within the specified timeframe.
        
        Args:
            days_back (int): Number of days back to look for payments
            
        Returns:
            dict: Summary of the settlement process
        """
        if not os.environ.get('PAYPAL_CLIENT_ID') or not os.environ.get('PAYPAL_CLIENT_SECRET'):
            logger.error("Cannot process PayPal settlement: No API credentials configured")
            return {"success": False, "error": "No PayPal API credentials configured"}
        
        # Find the linked treasury account
        account = self.get_processor_linked_account('paypal')
        if not account:
            logger.error("Cannot process PayPal settlement: No linked treasury account found")
            return {"success": False, "error": "No linked treasury account found"}
        
        # Calculate the time window
        end_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        try:
            # Retrieve successful payments within the time window
            payment_history = paypalrestsdk.Payment.all({
                "start_time": start_date,
                "end_time": end_date,
                "sort_by": "create_time",
                "sort_order": "desc",
                "count": 100,
                "state": "approved"
            })
            
            # Process the payments
            total_amount = 0
            count = 0
            
            for payment in payment_history.payments:
                # Skip payments that have already been settled
                if TreasuryTransaction.query.filter_by(
                    external_reference=payment.id,
                    transaction_type=TransactionType.PAYMENT_SETTLEMENT
                ).first():
                    logger.debug(f"Skipping already settled PayPal payment: {payment.id}")
                    continue
                
                # Extract transaction data - handle both single and multiple transactions
                transactions = payment.get('transactions', [])
                if not transactions:
                    continue
                
                # For simplicity, we'll process the first transaction in each payment
                transaction = transactions[0]
                amount_data = transaction.get('amount', {})
                amount = float(amount_data.get('total', 0))
                currency = amount_data.get('currency', 'USD')
                
                # Record the settlement
                self.record_settlement_transaction(
                    account_id=account.id,
                    amount=amount,
                    processor_type='paypal',
                    external_reference=payment.id,
                    description=f"PayPal payment settlement: {transaction.get('description', payment.id)}"
                )
                
                total_amount += amount
                count += 1
            
            logger.info(f"Processed {count} PayPal payments for settlement, total: {total_amount}")
            return {
                "success": True,
                "processor": "paypal",
                "count": count,
                "total_amount": total_amount,
                "currency": account.currency,
                "account_id": account.id,
                "account_name": account.name
            }
            
        except Exception as e:
            logger.error(f"Error processing PayPal settlement: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def process_pos_settlement(self, days_back=1):
        """
        Processes settlement from the internal POS system to the linked treasury account.
        Looks for successful POS transactions within the specified timeframe.
        
        Args:
            days_back (int): Number of days back to look for transactions
            
        Returns:
            dict: Summary of the settlement process
        """
        # Find the linked treasury account
        account = self.get_processor_linked_account('pos')
        if not account:
            logger.error("Cannot process POS settlement: No linked treasury account found")
            return {"success": False, "error": "No linked treasury account found"}
        
        try:
            # Calculate the time window
            end_date = datetime.utcnow()
            start_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Retrieve successful POS transactions that haven't been settled
            # This query finds transactions processed through the POS system
            pos_transactions = db.session.execute(
                text("""
                SELECT t.id, t.amount, t.currency, t.external_reference, t.description 
                FROM transaction t
                JOIN payment_gateway pg ON t.gateway_id = pg.id
                WHERE t.status = 'COMPLETED'
                AND t.transaction_type = 'POS_PAYMENT'
                AND t.created_at BETWEEN :start_date AND :end_date
                AND NOT EXISTS (
                    SELECT 1 FROM treasury_transaction tt
                    WHERE tt.external_reference = t.external_reference
                    AND tt.transaction_type = 'PAYMENT_SETTLEMENT'
                )
                LIMIT 100
                """),
                {
                    "start_date": start_date,
                    "end_date": end_date
                }
            ).fetchall()
            
            # Process the POS transactions
            total_amount = 0
            count = 0
            
            for tx in pos_transactions:
                # Record the settlement
                self.record_settlement_transaction(
                    account_id=account.id,
                    amount=tx.amount,
                    processor_type='pos',
                    external_reference=str(tx.id),
                    description=f"POS payment settlement: {tx.description or 'Transaction #' + str(tx.id)}"
                )
                
                total_amount += tx.amount
                count += 1
            
            logger.info(f"Processed {count} POS transactions for settlement, total: {total_amount}")
            return {
                "success": True,
                "processor": "pos",
                "count": count,
                "total_amount": total_amount,
                "currency": account.currency,
                "account_id": account.id,
                "account_name": account.name
            }
            
        except Exception as e:
            logger.error(f"Error processing POS settlement: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def process_all_settlements(self, days_back=1):
        """
        Processes settlement for all payment processors.
        
        Args:
            days_back (int): Number of days back to look for transactions
            
        Returns:
            dict: Summary of all settlement processes
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "days_processed": days_back,
            "processors": []
        }
        
        # Process Stripe settlements
        stripe_result = self.process_stripe_settlement(days_back)
        results["processors"].append(stripe_result)
        
        # Process PayPal settlements
        paypal_result = self.process_paypal_settlement(days_back)
        results["processors"].append(paypal_result)
        
        # Process POS settlements
        pos_result = self.process_pos_settlement(days_back)
        results["processors"].append(pos_result)
        
        # Calculate success metrics
        successful_count = sum(1 for p in results["processors"] if p.get("success", False))
        results["overall_success"] = successful_count == len(results["processors"])
        results["success_rate"] = f"{successful_count}/{len(results['processors'])}"
        
        # Calculate total processed amount
        total_processed = sum(p.get("total_amount", 0) for p in results["processors"] if p.get("success", False))
        results["total_amount_processed"] = total_processed
        
        return results


# Create a bridge singleton
treasury_payment_bridge = TreasuryPaymentBridge()