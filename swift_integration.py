"""
SWIFT Integration Module
This module provides functionality for generating and processing SWIFT messages,
including Letters of Credit (MT760), Customer Transfers (MT103), and Financial
Institution Transfers (MT202).
"""
import json
import logging
import uuid
from datetime import datetime, timedelta

from models import (
    db, Transaction, FinancialInstitution, TransactionType, TransactionStatus,
    FormData
)
from transaction_service import record_transaction
from utils import generate_transaction_id

logger = logging.getLogger(__name__)

class SwiftMessage:
    """Base class for all SWIFT message types"""
    
    def __init__(self, user_id, institution_id):
        self.user_id = user_id
        self.institution_id = institution_id
        self.message_id = f"SWIFT{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.message_type = None
        
    def get_sender_bic(self):
        """Get sender BIC code (NVC Global)"""
        return "NVCGGLOBALXXX"
        
    def get_receiver_bic(self):
        """Get receiver BIC code from institution"""
        institution = FinancialInstitution.query.get(self.institution_id)
        if not institution:
            return None
            
        # Try to get BIC from metadata_json if available
        try:
            if institution.metadata_json:
                metadata = json.loads(institution.metadata_json)
                if 'swift' in metadata and 'bic' in metadata['swift']:
                    return metadata['swift']['bic']
        except Exception as e:
            logger.error(f"Error parsing institution metadata: {str(e)}")
        
        # Return a default BIC based on institution name
        sanitized_name = ''.join(c for c in institution.name[:8] if c.isalnum()).upper()
        return f"{sanitized_name}XXXX"
        
    def to_json(self):
        """Convert message to JSON representation"""
        return {}
        
    def generate_transaction(self):
        """Generate a transaction record for this message
        
        Returns:
            Transaction: The created transaction object
        """
        return None

class MT760(SwiftMessage):
    """SWIFT MT760 - Standby Letter of Credit"""
    
    def __init__(self, user_id, institution_id, amount, currency, beneficiary, expiry_date, terms_and_conditions):
        super().__init__(user_id, institution_id)
        self.message_type = "MT760"
        self.amount = amount
        self.currency = currency
        self.beneficiary = beneficiary
        self.expiry_date = expiry_date
        self.terms_and_conditions = terms_and_conditions
        self.reference = f"LC{uuid.uuid4().hex[:10].upper()}"
        
    def to_json(self):
        """Convert letter of credit to JSON representation"""
        return {
            "message_type": self.message_type,
            "reference": self.reference,
            "sender_bic": self.get_sender_bic(),
            "receiver_bic": self.get_receiver_bic(),
            "issuing_bank": "NVC Global Bank",
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
            "expiry_date": self.expiry_date.strftime("%Y-%m-%d") if hasattr(self.expiry_date, 'strftime') else self.expiry_date,
            "amount": self.amount,
            "currency": self.currency,
            "beneficiary": self.beneficiary,
            "terms_and_conditions": self.terms_and_conditions
        }
        
    def generate_transaction(self):
        """Create a transaction record for this letter of credit"""
        description = f"Standby Letter of Credit {self.reference} for {self.amount} {self.currency}"
        
        # Prepare metadata
        metadata = self.to_json()
        metadata["institution_id"] = self.institution_id
        
        # Create the transaction
        transaction = record_transaction(
            user_id=self.user_id,
            amount=self.amount,
            currency=self.currency,
            transaction_type=TransactionType.SWIFT_LETTER_OF_CREDIT,
            status=TransactionStatus.PENDING,
            description=description,
            metadata=metadata
        )
        
        return transaction

class MT103(SwiftMessage):
    """SWIFT MT103 - Customer Credit Transfer"""
    
    def __init__(self, user_id, institution_id, amount, currency, ordering_customer, beneficiary_customer, details_of_payment):
        super().__init__(user_id, institution_id)
        self.message_type = "MT103"
        self.amount = amount
        self.currency = currency
        self.ordering_customer = ordering_customer
        self.beneficiary_customer = beneficiary_customer
        self.details_of_payment = details_of_payment
        self.reference = f"FT{uuid.uuid4().hex[:10].upper()}"
        
    def to_json(self):
        """Convert fund transfer to JSON representation"""
        institution = FinancialInstitution.query.get(self.institution_id)
        institution_name = institution.name if institution else "Unknown Institution"
        
        return {
            "message_type": self.message_type,
            "reference": self.reference,
            "sender_bic": self.get_sender_bic(),
            "receiver_bic": self.get_receiver_bic(),
            "sender_institution": "NVC Global Bank",
            "receiver_institution": institution_name,
            "execution_date": datetime.now().strftime("%Y-%m-%d"),
            "amount": self.amount,
            "currency": self.currency,
            "ordering_customer": self.ordering_customer,
            "beneficiary_customer": self.beneficiary_customer,
            "details_of_payment": self.details_of_payment
        }
        
    def generate_transaction(self):
        """Create a transaction record for this fund transfer"""
        description = f"SWIFT MT103 Fund Transfer {self.reference} for {self.amount} {self.currency}"
        
        # Prepare metadata
        metadata = self.to_json()
        metadata["institution_id"] = self.institution_id
        
        # Create the transaction
        transaction = record_transaction(
            user_id=self.user_id,
            amount=self.amount,
            currency=self.currency,
            transaction_type=TransactionType.SWIFT_FUND_TRANSFER,
            status=TransactionStatus.PENDING,
            description=description,
            metadata=metadata
        )
        
        return transaction

class MT202(SwiftMessage):
    """SWIFT MT202 - General Financial Institution Transfer"""
    
    def __init__(self, user_id, institution_id, amount, currency, ordering_customer, beneficiary_customer, details_of_payment):
        super().__init__(user_id, institution_id)
        self.message_type = "MT202"
        self.amount = amount
        self.currency = currency
        self.ordering_customer = ordering_customer
        self.beneficiary_customer = beneficiary_customer
        self.details_of_payment = details_of_payment
        self.reference = f"IT{uuid.uuid4().hex[:10].upper()}"
        
    def to_json(self):
        """Convert institution transfer to JSON representation"""
        institution = FinancialInstitution.query.get(self.institution_id)
        institution_name = institution.name if institution else "Unknown Institution"
        
        return {
            "message_type": self.message_type,
            "reference": self.reference,
            "sender_bic": self.get_sender_bic(),
            "receiver_bic": self.get_receiver_bic(),
            "sender_institution": "NVC Global Bank",
            "receiver_institution": institution_name,
            "execution_date": datetime.now().strftime("%Y-%m-%d"),
            "amount": self.amount,
            "currency": self.currency,
            "ordering_institution": self.ordering_customer,
            "beneficiary_institution": self.beneficiary_customer,
            "details_of_payment": self.details_of_payment
        }
        
    def generate_transaction(self):
        """Create a transaction record for this institution transfer"""
        description = f"SWIFT MT202 Financial Institution Transfer {self.reference} for {self.amount} {self.currency}"
        
        # Prepare metadata
        metadata = self.to_json()
        metadata["institution_id"] = self.institution_id
        
        # Create the transaction
        transaction = record_transaction(
            user_id=self.user_id,
            amount=self.amount,
            currency=self.currency,
            transaction_type=TransactionType.SWIFT_INSTITUTION_TRANSFER,
            status=TransactionStatus.PENDING,
            description=description,
            metadata=metadata
        )
        
        return transaction

class MT799(SwiftMessage):
    """SWIFT MT799 - Free Format Message"""
    
    def __init__(self, user_id, institution_id, subject, message_body):
        super().__init__(user_id, institution_id)
        self.message_type = "MT799"
        self.subject = subject
        self.message_body = message_body
        self.reference = f"FM{uuid.uuid4().hex[:10].upper()}"
        
    def to_json(self):
        """Convert free format message to JSON representation"""
        institution = FinancialInstitution.query.get(self.institution_id)
        institution_name = institution.name if institution else "Unknown Institution"
        
        return {
            "message_type": self.message_type,
            "reference": self.reference,
            "sender_bic": self.get_sender_bic(),
            "receiver_bic": self.get_receiver_bic(),
            "sender_institution": "NVC Global Bank",
            "receiver_institution": institution_name,
            "creation_date": datetime.now().strftime("%Y-%m-%d"),
            "subject": self.subject,
            "message_body": self.message_body
        }
        
    def generate_transaction(self):
        """Create a transaction record for this free format message"""
        # No amount for free format messages, use placeholder
        amount = 0.0
        description = f"SWIFT MT799 Free Format Message: {self.subject}"
        
        # Prepare metadata
        metadata = self.to_json()
        metadata["institution_id"] = self.institution_id
        
        # Create the transaction
        transaction = record_transaction(
            user_id=self.user_id,
            amount=amount,
            currency="USD",  # Default currency
            transaction_type=TransactionType.SWIFT_FREE_FORMAT,
            status=TransactionStatus.PENDING,
            description=description,
            metadata=metadata
        )
        
        return transaction

class SwiftMessageParser:
    """Parser for incoming SWIFT messages"""
    
    @staticmethod
    def parse_mt760(message_text):
        """Parse incoming MT760 message"""
        # Implementation for parsing MT760 messages
        pass
        
    @staticmethod
    def parse_mt103(message_text):
        """Parse incoming MT103 message"""
        # Implementation for parsing MT103 messages
        pass
        
    @staticmethod
    def parse_mt202(message_text):
        """Parse incoming MT202 message"""
        # Implementation for parsing MT202 messages
        pass
        
    @staticmethod
    def parse_mt799(message_text):
        """Parse incoming MT799 message"""
        # Implementation for parsing MT799 messages
        pass

class SwiftService:
    """Main service for SWIFT messaging operations"""
    
    @staticmethod
    def get_swift_enabled_institutions():
        """Get institutions with SWIFT capability"""
        # Initially, all institutions are considered SWIFT-enabled
        # In a real system, we would check for specific SWIFT credentials
        institutions = FinancialInstitution.query.filter_by(is_active=True).all()
        return institutions
    
    @staticmethod
    def create_letter_of_credit(user_id, receiver_institution_id, amount, currency, beneficiary, expiry_date, terms_and_conditions):
        """Create a new Standby Letter of Credit (MT760)"""
        try:
            # Create MT760 message
            mt760 = MT760(
                user_id=user_id,
                institution_id=receiver_institution_id,
                amount=amount,
                currency=currency,
                beneficiary=beneficiary,
                expiry_date=expiry_date,
                terms_and_conditions=terms_and_conditions
            )
            
            # Generate transaction from the message
            transaction = mt760.generate_transaction()
            
            # In a real system, we would send this to SWIFT network
            # For now, simulate successful submission
            logger.info(f"Letter of Credit created: {transaction.transaction_id}")
            
            # Clear any saved form data for this user
            SwiftService._clear_saved_form_data(user_id, "letter_of_credit_form")
            
            return transaction
        except Exception as e:
            logger.error(f"Error creating Letter of Credit: {str(e)}")
            raise
    
    @staticmethod
    def create_swift_fund_transfer(user_id, receiver_institution_id, amount, currency, ordering_customer, beneficiary_customer, details_of_payment, is_financial_institution=False):
        """Create a new SWIFT fund transfer (MT103 or MT202)"""
        try:
            # Create either MT103 or MT202 message based on is_financial_institution flag
            if is_financial_institution:
                message = MT202(
                    user_id=user_id,
                    institution_id=receiver_institution_id,
                    amount=amount,
                    currency=currency,
                    ordering_customer=ordering_customer, 
                    beneficiary_customer=beneficiary_customer,
                    details_of_payment=details_of_payment
                )
            else:
                message = MT103(
                    user_id=user_id,
                    institution_id=receiver_institution_id,
                    amount=amount,
                    currency=currency,
                    ordering_customer=ordering_customer,
                    beneficiary_customer=beneficiary_customer,
                    details_of_payment=details_of_payment
                )
            
            # Generate transaction from the message
            transaction = message.generate_transaction()
            
            # In a real system, we would send this to SWIFT network
            # For now, simulate successful submission
            logger.info(f"Fund transfer created: {transaction.transaction_id}")
            
            # Clear any saved form data for this user
            SwiftService._clear_saved_form_data(user_id, "swift_fund_transfer_form")
            
            return transaction
        except Exception as e:
            logger.error(f"Error creating fund transfer: {str(e)}")
            raise
    
    @staticmethod
    def create_free_format_message(user_id, receiver_institution_id, subject, message_body):
        """Create a new SWIFT free format message (MT799)"""
        try:
            # Create MT799 message
            mt799 = MT799(
                user_id=user_id,
                institution_id=receiver_institution_id,
                subject=subject,
                message_body=message_body
            )
            
            # Generate transaction from the message
            transaction = mt799.generate_transaction()
            
            # In a real system, we would send this to SWIFT network
            # For now, simulate successful submission
            logger.info(f"Free format message created: {transaction.transaction_id}")
            
            # Clear any saved form data for this user
            SwiftService._clear_saved_form_data(user_id, "swift_free_format_form")
            
            return transaction
        except Exception as e:
            logger.error(f"Error creating free format message: {str(e)}")
            raise
    
    @staticmethod
    def get_letter_of_credit_status(transaction_id):
        """Get status of a Letter of Credit"""
        try:
            # In a real system, we would query the SWIFT network for status
            # For now, return simulated status
            return {
                "success": True,
                "status": "confirmed",
                "details": {
                    "message": "Letter of Credit has been confirmed by the receiving institution.",
                    "confirmation_time": (datetime.now() - timedelta(hours=2)).isoformat(),
                    "confirmation_reference": f"REF{uuid.uuid4().hex[:8].upper()}"
                }
            }
        except Exception as e:
            logger.error(f"Error retrieving Letter of Credit status: {str(e)}")
            return {
                "success": False,
                "error": "Unable to retrieve status at this time."
            }
    
    @staticmethod
    def get_fund_transfer_status(transaction_id):
        """Get status of a fund transfer"""
        try:
            # In a real system, we would query the SWIFT network for status
            # For now, return simulated status
            return {
                "success": True,
                "status": "processing",
                "details": {
                    "message": "Fund transfer is being processed by the receiving institution.",
                    "expected_settlement": (datetime.now() + timedelta(days=1)).isoformat(),
                    "tracking_reference": f"TRK{uuid.uuid4().hex[:8].upper()}"
                }
            }
        except Exception as e:
            logger.error(f"Error retrieving fund transfer status: {str(e)}")
            return {
                "success": False,
                "error": "Unable to retrieve status at this time."
            }
    
    @staticmethod
    def get_free_format_message_status(transaction_id):
        """Get status of a free format message"""
        try:
            # In a real system, we would query the SWIFT network for status
            # For now, return simulated status
            return {
                "success": True,
                "status": "delivered",
                "details": {
                    "details": "Free format message has been delivered to the receiving institution.",
                    "delivery_time": (datetime.now() - timedelta(hours=1)).isoformat(),
                    "delivery_reference": f"DLV{uuid.uuid4().hex[:8].upper()}"
                }
            }
        except Exception as e:
            logger.error(f"Error retrieving free format message status: {str(e)}")
            return {
                "success": False,
                "error": "Unable to retrieve status at this time."
            }
    
    @staticmethod
    def _clear_saved_form_data(user_id, form_type):
        """Clear saved form data after successful submission"""
        try:
            form_data = FormData.query.filter_by(
                user_id=user_id,
                form_type=form_type
            ).first()
            
            if form_data:
                db.session.delete(form_data)
                db.session.commit()
                logger.info(f"Cleared saved form data for user {user_id}, form type {form_type}")
        except Exception as e:
            logger.error(f"Error clearing saved form data: {str(e)}")