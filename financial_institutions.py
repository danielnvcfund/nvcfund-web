import os
import json
import uuid
import logging
import requests
from datetime import datetime
from app import db
from models import FinancialInstitution, Transaction, TransactionStatus, TransactionType, User

logger = logging.getLogger(__name__)

class FinancialInstitutionInterface:
    """Base interface for financial institution interactions"""
    
    def __init__(self, institution_id):
        self.institution = FinancialInstitution.query.get(institution_id)
        if not self.institution:
            raise ValueError(f"Financial institution with ID {institution_id} not found")
            
        if not self.institution.is_active:
            raise ValueError(f"Financial institution {self.institution.name} is not active")
    
    def initiate_transfer(self, amount, currency, description, user_id, recipient_info=None):
        """Initiate a transfer from the institution"""
        raise NotImplementedError("Subclasses must implement initiate_transfer")
    
    def check_transfer_status(self, transfer_id):
        """Check the status of a transfer"""
        raise NotImplementedError("Subclasses must implement check_transfer_status")
    
    def get_balance(self, user_id):
        """Get the user's balance at the institution"""
        raise NotImplementedError("Subclasses must implement get_balance")
    
    def _create_transaction_record(self, amount, currency, user_id, description, status=TransactionStatus.PENDING):
        """Create a transaction record in the database"""
        transaction_id = str(uuid.uuid4())
        
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            transaction_type=TransactionType.TRANSFER,
            status=status,
            description=description,
            institution_id=self.institution.id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return transaction


class StandardBankAPI(FinancialInstitutionInterface):
    """Standard bank API implementation"""
    
    def initiate_transfer(self, amount, currency, description, user_id, recipient_info=None):
        """Initiate a transfer from the bank"""
        try:
            # Get user details
            user = User.query.get(user_id)
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Create transaction record
            transaction = self._create_transaction_record(
                amount, currency, user_id, description
            )
            
            # Prepare API request to bank
            headers = {
                "Authorization": f"Bearer {self.institution.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "amount": str(amount),
                "currency": currency.upper(),
                "description": description,
                "reference": transaction.transaction_id,
                "sender": {
                    "id": str(user_id),
                    "name": user.username,
                    "email": user.email
                }
            }
            
            if recipient_info:
                payload["recipient"] = recipient_info
            
            # Make API request to bank
            response = requests.post(
                f"{self.institution.api_endpoint}/transfers",
                headers=headers,
                json=payload
            )
            
            data = response.json()
            
            if response.status_code == 200 or response.status_code == 201:
                # Update transaction with bank transfer ID
                transaction.status = TransactionStatus.PROCESSING
                transaction.description = f"{description} (Bank Transfer ID: {data.get('id', 'Unknown')})"
                db.session.commit()
                
                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "transfer_id": data.get("id"),
                    "status": data.get("status"),
                    "amount": amount,
                    "currency": currency
                }
            else:
                # Handle error
                transaction.status = TransactionStatus.FAILED
                transaction.description = f"{description} (Error: {data.get('error', 'Unknown error')})"
                db.session.commit()
                
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": data.get("error", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Error initiating bank transfer: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_transfer_status(self, transfer_id):
        """Check the status of a bank transfer"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=transfer_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Extract bank transfer ID from description
            import re
            match = re.search(r"Bank Transfer ID: ([a-zA-Z0-9-]+)", transaction.description)
            
            if not match:
                return {"success": False, "error": "Bank Transfer ID not found"}
            
            bank_transfer_id = match.group(1)
            
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.institution.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make API request to bank
            response = requests.get(
                f"{self.institution.api_endpoint}/transfers/{bank_transfer_id}",
                headers=headers
            )
            
            data = response.json()
            
            if response.status_code == 200:
                # Map bank status to our status
                status_mapping = {
                    "pending": TransactionStatus.PENDING,
                    "processing": TransactionStatus.PROCESSING,
                    "completed": TransactionStatus.COMPLETED,
                    "failed": TransactionStatus.FAILED,
                    "cancelled": TransactionStatus.FAILED
                }
                
                bank_status = data.get("status", "").lower()
                internal_status = status_mapping.get(bank_status, transaction.status)
                
                # Update transaction status if changed
                if transaction.status != internal_status:
                    transaction.status = internal_status
                    db.session.commit()
                
                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "transfer_id": bank_transfer_id,
                    "status": bank_status,
                    "internal_status": internal_status.value,
                    "amount": transaction.amount,
                    "currency": transaction.currency
                }
            else:
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": data.get("error", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Error checking bank transfer status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_balance(self, user_id):
        """Get the user's balance at the bank"""
        try:
            # Get user details
            user = User.query.get(user_id)
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.institution.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make API request to bank
            response = requests.get(
                f"{self.institution.api_endpoint}/accounts/{user_id}/balances",
                headers=headers
            )
            
            data = response.json()
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "user_id": user_id,
                    "balances": data.get("balances", [])
                }
            else:
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": data.get("error", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Error getting bank balance: {str(e)}")
            return {"success": False, "error": str(e)}


class InvestmentFirmAPI(FinancialInstitutionInterface):
    """Investment firm API implementation"""
    
    def initiate_transfer(self, amount, currency, description, user_id, recipient_info=None):
        """Initiate a transfer from the investment firm"""
        try:
            # Get user details
            user = User.query.get(user_id)
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Create transaction record
            transaction = self._create_transaction_record(
                amount, currency, user_id, description
            )
            
            # Prepare API request to investment firm
            headers = {
                "X-API-Key": self.institution.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "amount": amount,
                "currency": currency.upper(),
                "description": description,
                "reference": transaction.transaction_id,
                "client_id": str(user_id),
                "client_name": user.username,
                "client_email": user.email,
                "transaction_type": "withdrawal"
            }
            
            if recipient_info:
                payload["recipient"] = recipient_info
            
            # Make API request to investment firm
            response = requests.post(
                f"{self.institution.api_endpoint}/client/transfers",
                headers=headers,
                json=payload
            )
            
            data = response.json()
            
            if response.status_code == 200 or response.status_code == 201:
                # Update transaction with investment firm transfer ID
                transaction.status = TransactionStatus.PROCESSING
                transaction.description = f"{description} (Investment Transfer ID: {data.get('transfer_id', 'Unknown')})"
                db.session.commit()
                
                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "transfer_id": data.get("transfer_id"),
                    "status": data.get("status"),
                    "amount": amount,
                    "currency": currency
                }
            else:
                # Handle error
                transaction.status = TransactionStatus.FAILED
                transaction.description = f"{description} (Error: {data.get('message', 'Unknown error')})"
                db.session.commit()
                
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": data.get("message", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Error initiating investment firm transfer: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_transfer_status(self, transfer_id):
        """Check the status of an investment firm transfer"""
        try:
            # Find transaction by ID
            transaction = Transaction.query.filter_by(transaction_id=transfer_id).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Extract investment transfer ID from description
            import re
            match = re.search(r"Investment Transfer ID: ([a-zA-Z0-9-]+)", transaction.description)
            
            if not match:
                return {"success": False, "error": "Investment Transfer ID not found"}
            
            investment_transfer_id = match.group(1)
            
            # Prepare API request
            headers = {
                "X-API-Key": self.institution.api_key,
                "Content-Type": "application/json"
            }
            
            # Make API request to investment firm
            response = requests.get(
                f"{self.institution.api_endpoint}/client/transfers/{investment_transfer_id}",
                headers=headers
            )
            
            data = response.json()
            
            if response.status_code == 200:
                # Map investment firm status to our status
                status_mapping = {
                    "initiated": TransactionStatus.PENDING,
                    "processing": TransactionStatus.PROCESSING,
                    "completed": TransactionStatus.COMPLETED,
                    "failed": TransactionStatus.FAILED,
                    "cancelled": TransactionStatus.FAILED
                }
                
                investment_status = data.get("status", "").lower()
                internal_status = status_mapping.get(investment_status, transaction.status)
                
                # Update transaction status if changed
                if transaction.status != internal_status:
                    transaction.status = internal_status
                    db.session.commit()
                
                return {
                    "success": True,
                    "transaction_id": transaction.transaction_id,
                    "transfer_id": investment_transfer_id,
                    "status": investment_status,
                    "internal_status": internal_status.value,
                    "amount": transaction.amount,
                    "currency": transaction.currency
                }
            else:
                return {
                    "success": False,
                    "transaction_id": transaction.transaction_id,
                    "error": data.get("message", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Error checking investment firm transfer status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_balance(self, user_id):
        """Get the user's balance at the investment firm"""
        try:
            # Prepare API request
            headers = {
                "X-API-Key": self.institution.api_key,
                "Content-Type": "application/json"
            }
            
            # Make API request to investment firm
            response = requests.get(
                f"{self.institution.api_endpoint}/client/{user_id}/portfolio",
                headers=headers
            )
            
            data = response.json()
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "user_id": user_id,
                    "portfolio": data.get("portfolio", {}),
                    "cash_balance": data.get("cash_balance", {}),
                    "total_value": data.get("total_value", {})
                }
            else:
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": data.get("message", "Unknown error")
                }
        
        except Exception as e:
            logger.error(f"Error getting investment firm balance: {str(e)}")
            return {"success": False, "error": str(e)}


def get_institution_handler(institution_id):
    """
    Factory function to get the appropriate financial institution handler
    
    Args:
        institution_id (int): ID of the financial institution in the database
    
    Returns:
        FinancialInstitutionInterface: The appropriate financial institution handler
    """
    try:
        institution = FinancialInstitution.query.get(institution_id)
        
        if not institution:
            raise ValueError(f"Financial institution with ID {institution_id} not found")
        
        if not institution.is_active:
            raise ValueError(f"Financial institution {institution.name} is not active")
        
        # Select the appropriate handler based on institution type
        if institution.institution_type.value in ["bank", "credit_union"]:
            return StandardBankAPI(institution_id)
        elif institution.institution_type.value == "investment_firm":
            return InvestmentFirmAPI(institution_id)
        else:
            raise ValueError(f"Unsupported financial institution type: {institution.institution_type.value}")
    
    except Exception as e:
        logger.error(f"Error getting institution handler: {str(e)}")
        raise
