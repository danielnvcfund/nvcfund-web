"""
SWIFT Integration Module for Bank-to-Bank Communications
This module provides functionality for creating and processing SWIFT messages
used in international banking communications.
"""
import json
import uuid
import logging
from datetime import datetime, timedelta
from enum import Enum

from models import db, FinancialInstitution, Transaction, TransactionType, TransactionStatus

logger = logging.getLogger(__name__)

class SwiftMessageType(Enum):
    """Swift message types supported by the system"""
    MT103 = "MT103"  # Single Customer Credit Transfer
    MT202 = "MT202"  # General Financial Institution Transfer
    MT760 = "MT760"  # Guarantee/Standby Letter of Credit
    MT799 = "MT799"  # Free Format Message

class SwiftMessage:
    """Base class for SWIFT messages"""
    def __init__(self, sender_bic, receiver_bic, reference=None):
        self.sender_bic = sender_bic
        self.receiver_bic = receiver_bic
        self.reference = reference or f"REF{uuid.uuid4().hex[:8].upper()}"
        self.creation_date = datetime.utcnow().isoformat()
        
    def to_dict(self):
        """Convert message to dictionary"""
        return {
            "sender_bic": self.sender_bic,
            "receiver_bic": self.receiver_bic,
            "reference": self.reference,
            "creation_date": self.creation_date
        }
        
    def to_json(self):
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())

class MT760(SwiftMessage):
    """SWIFT MT760 - Standby Letter of Credit"""
    def __init__(self, sender_bic, receiver_bic, amount, currency, beneficiary, 
                 expiry_date, terms_and_conditions, reference=None):
        super().__init__(sender_bic, receiver_bic, reference)
        self.message_type = SwiftMessageType.MT760.value
        self.amount = amount
        self.currency = currency
        self.beneficiary = beneficiary
        self.expiry_date = expiry_date
        self.terms_and_conditions = terms_and_conditions
        
    def to_dict(self):
        """Convert message to dictionary"""
        result = super().to_dict()
        result.update({
            "message_type": self.message_type,
            "amount": self.amount,
            "currency": self.currency,
            "beneficiary": self.beneficiary,
            "expiry_date": self.expiry_date,
            "terms_and_conditions": self.terms_and_conditions
        })
        return result

class MT103(SwiftMessage):
    """SWIFT MT103 - Single Customer Credit Transfer"""
    def __init__(self, sender_bic, receiver_bic, amount, currency, 
                 ordering_customer, beneficiary_customer, details_of_payment, reference=None):
        super().__init__(sender_bic, receiver_bic, reference)
        self.message_type = SwiftMessageType.MT103.value
        self.amount = amount
        self.currency = currency
        self.ordering_customer = ordering_customer
        self.beneficiary_customer = beneficiary_customer
        self.details_of_payment = details_of_payment
        
    def to_dict(self):
        """Convert message to dictionary"""
        result = super().to_dict()
        result.update({
            "message_type": self.message_type,
            "amount": self.amount,
            "currency": self.currency,
            "ordering_customer": self.ordering_customer,
            "beneficiary_customer": self.beneficiary_customer,
            "details_of_payment": self.details_of_payment
        })
        return result

class MT202(SwiftMessage):
    """SWIFT MT202 - General Financial Institution Transfer"""
    def __init__(self, sender_bic, receiver_bic, amount, currency, 
                 ordering_institution, beneficiary_institution, reference=None):
        super().__init__(sender_bic, receiver_bic, reference)
        self.message_type = SwiftMessageType.MT202.value
        self.amount = amount
        self.currency = currency
        self.ordering_institution = ordering_institution
        self.beneficiary_institution = beneficiary_institution
        
    def to_dict(self):
        """Convert message to dictionary"""
        result = super().to_dict()
        result.update({
            "message_type": self.message_type,
            "amount": self.amount,
            "currency": self.currency,
            "ordering_institution": self.ordering_institution,
            "beneficiary_institution": self.beneficiary_institution
        })
        return result

class MT799(SwiftMessage):
    """SWIFT MT799 - Free Format Message"""
    def __init__(self, sender_bic, receiver_bic, subject, message_body, reference=None):
        super().__init__(sender_bic, receiver_bic, reference)
        self.message_type = SwiftMessageType.MT799.value
        self.subject = subject
        self.message_body = message_body
        
    def to_dict(self):
        """Convert message to dictionary"""
        result = super().to_dict()
        result.update({
            "message_type": self.message_type,
            "subject": self.subject,
            "message_body": self.message_body
        })
        return result

class SwiftMessageParser:
    """Parser for SWIFT messages received from external sources"""
    @staticmethod
    def parse_message(message_data):
        """Parse a SWIFT message from data dictionary or JSON string"""
        if isinstance(message_data, str):
            try:
                message_data = json.loads(message_data)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON format in SWIFT message")
                
        message_type = message_data.get("message_type")
        if not message_type:
            raise ValueError("Missing message_type in SWIFT message")
            
        if message_type == SwiftMessageType.MT760.value:
            return MT760(
                sender_bic=message_data.get("sender_bic"),
                receiver_bic=message_data.get("receiver_bic"),
                amount=message_data.get("amount"),
                currency=message_data.get("currency"),
                beneficiary=message_data.get("beneficiary"),
                expiry_date=message_data.get("expiry_date"),
                terms_and_conditions=message_data.get("terms_and_conditions"),
                reference=message_data.get("reference")
            )
        elif message_type == SwiftMessageType.MT103.value:
            return MT103(
                sender_bic=message_data.get("sender_bic"),
                receiver_bic=message_data.get("receiver_bic"),
                amount=message_data.get("amount"),
                currency=message_data.get("currency"),
                ordering_customer=message_data.get("ordering_customer"),
                beneficiary_customer=message_data.get("beneficiary_customer"),
                details_of_payment=message_data.get("details_of_payment"),
                reference=message_data.get("reference")
            )
        elif message_type == SwiftMessageType.MT202.value:
            return MT202(
                sender_bic=message_data.get("sender_bic"),
                receiver_bic=message_data.get("receiver_bic"),
                amount=message_data.get("amount"),
                currency=message_data.get("currency"),
                ordering_institution=message_data.get("ordering_institution"),
                beneficiary_institution=message_data.get("beneficiary_institution"),
                reference=message_data.get("reference")
            )
        elif message_type == SwiftMessageType.MT799.value:
            return MT799(
                sender_bic=message_data.get("sender_bic"),
                receiver_bic=message_data.get("receiver_bic"),
                subject=message_data.get("subject"),
                message_body=message_data.get("message_body"),
                reference=message_data.get("reference")
            )
        else:
            raise ValueError(f"Unsupported SWIFT message type: {message_type}")

class SwiftService:
    """Service for handling SWIFT message operations"""
    @staticmethod
    def get_swift_enabled_institutions():
        """Get all institutions with SWIFT information"""
        institutions = FinancialInstitution.query.filter_by(is_active=True).all()
        return [inst for inst in institutions if inst.metadata_json]
    
    @staticmethod
    def get_institution_bic(institution_id):
        """Get the BIC code for an institution"""
        institution = FinancialInstitution.query.get(institution_id)
        if not institution or not institution.metadata_json:
            return None
            
        try:
            metadata = json.loads(institution.metadata_json)
            return metadata.get("swift", {}).get("bic")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in metadata_json for institution {institution_id}")
            return None
    
    @staticmethod
    def create_letter_of_credit(user_id, receiver_institution_id, amount, currency, 
                               beneficiary, expiry_date, terms_and_conditions):
        """Create a Letter of Credit using SWIFT MT760"""
        # Get the NVC Global institution for sending
        nvc_institution = FinancialInstitution.query.filter_by(name="NVC Global").first()
        if not nvc_institution:
            raise ValueError("NVC Global institution not found")
            
        # Get the receiving institution
        receiver_institution = FinancialInstitution.query.get(receiver_institution_id)
        if not receiver_institution:
            raise ValueError(f"Receiver institution not found: {receiver_institution_id}")
            
        # Get BIC codes
        sender_bic = SwiftService.get_institution_bic(nvc_institution.id)
        receiver_bic = SwiftService.get_institution_bic(receiver_institution_id)
        
        if not sender_bic:
            raise ValueError("Sender BIC code not found")
        if not receiver_bic:
            raise ValueError("Receiver BIC code not found")
            
        # Create the MT760 message
        message = MT760(
            sender_bic=sender_bic,
            receiver_bic=receiver_bic,
            amount=amount,
            currency=currency,
            beneficiary=beneficiary,
            expiry_date=expiry_date.isoformat() if isinstance(expiry_date, datetime) else expiry_date,
            terms_and_conditions=terms_and_conditions
        )
        
        # Create a transaction record
        transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.SWIFT_LETTER_OF_CREDIT,
            amount=amount,
            currency=currency,
            status=TransactionStatus.PENDING,
            recipient=f"{receiver_institution.name} (BIC: {receiver_bic})",
            description=f"SWIFT MT760 Letter of Credit - {message.reference}",
            tx_metadata_json=json.dumps(message.to_dict())
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return transaction
    
    @staticmethod
    def create_swift_fund_transfer(user_id, receiver_institution_id, amount, currency,
                                  ordering_customer, beneficiary_customer, details_of_payment,
                                  is_financial_institution=False):
        """Create a SWIFT fund transfer using MT103 or MT202"""
        # Get the NVC Global institution for sending
        nvc_institution = FinancialInstitution.query.filter_by(name="NVC Global").first()
        if not nvc_institution:
            raise ValueError("NVC Global institution not found")
            
        # Get the receiving institution
        receiver_institution = FinancialInstitution.query.get(receiver_institution_id)
        if not receiver_institution:
            raise ValueError(f"Receiver institution not found: {receiver_institution_id}")
            
        # Get BIC codes
        sender_bic = SwiftService.get_institution_bic(nvc_institution.id)
        receiver_bic = SwiftService.get_institution_bic(receiver_institution_id)
        
        if not sender_bic:
            raise ValueError("Sender BIC code not found")
        if not receiver_bic:
            raise ValueError("Receiver BIC code not found")
            
        # Create the appropriate message based on whether it's a financial institution transfer
        if is_financial_institution:
            # Use MT202 for financial institution transfers
            message = MT202(
                sender_bic=sender_bic,
                receiver_bic=receiver_bic,
                amount=amount,
                currency=currency,
                ordering_institution=ordering_customer,
                beneficiary_institution=beneficiary_customer
            )
            transaction_type = TransactionType.SWIFT_INSTITUTION_TRANSFER
            description = f"SWIFT MT202 Financial Institution Transfer - {message.reference}"
        else:
            # Use MT103 for customer transfers
            message = MT103(
                sender_bic=sender_bic,
                receiver_bic=receiver_bic,
                amount=amount,
                currency=currency,
                ordering_customer=ordering_customer,
                beneficiary_customer=beneficiary_customer,
                details_of_payment=details_of_payment
            )
            transaction_type = TransactionType.SWIFT_FUND_TRANSFER
            description = f"SWIFT MT103 Fund Transfer - {message.reference}"
        
        # Create a transaction record
        transaction = Transaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            currency=currency,
            status=TransactionStatus.PENDING,
            recipient=f"{receiver_institution.name} (BIC: {receiver_bic})",
            description=description,
            tx_metadata_json=json.dumps(message.to_dict())
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return transaction
    
    @staticmethod
    def create_free_format_message(user_id, receiver_institution_id, subject, message_body):
        """Create a free format SWIFT message using MT799"""
        # Get the NVC Global institution for sending
        nvc_institution = FinancialInstitution.query.filter_by(name="NVC Global").first()
        if not nvc_institution:
            raise ValueError("NVC Global institution not found")
            
        # Get the receiving institution
        receiver_institution = FinancialInstitution.query.get(receiver_institution_id)
        if not receiver_institution:
            raise ValueError(f"Receiver institution not found: {receiver_institution_id}")
            
        # Get BIC codes
        sender_bic = SwiftService.get_institution_bic(nvc_institution.id)
        receiver_bic = SwiftService.get_institution_bic(receiver_institution_id)
        
        if not sender_bic:
            raise ValueError("Sender BIC code not found")
        if not receiver_bic:
            raise ValueError("Receiver BIC code not found")
            
        # Create the MT799 message
        message = MT799(
            sender_bic=sender_bic,
            receiver_bic=receiver_bic,
            subject=subject,
            message_body=message_body
        )
        
        # Create a transaction record (with zero amount since it's just a message)
        transaction = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.SWIFT_FREE_FORMAT,
            amount=0.0,
            currency="USD",  # Default currency for record-keeping
            status=TransactionStatus.PENDING,
            recipient=f"{receiver_institution.name} (BIC: {receiver_bic})",
            description=f"SWIFT MT799 Free Format Message - {message.reference}",
            tx_metadata_json=json.dumps(message.to_dict())
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return transaction
    
    @staticmethod
    def get_letter_of_credit_status(transaction_id):
        """Get the status of a Letter of Credit"""
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {"success": False, "error": "Transaction not found"}
            
        if transaction.transaction_type != TransactionType.SWIFT_LETTER_OF_CREDIT:
            return {"success": False, "error": "Not a Letter of Credit transaction"}
            
        # In a real-world scenario, we would check the actual SWIFT network status
        # For now, we'll simulate a response based on transaction creation time
        created_delta = datetime.utcnow() - transaction.created_at
        
        # Parse the metadata to get the SWIFT message details
        try:
            swift_data = json.loads(transaction.tx_metadata_json)
        except (json.JSONDecodeError, TypeError):
            return {"success": False, "error": "Invalid SWIFT message data"}
            
        # Simulate different statuses based on time since creation
        if created_delta < timedelta(minutes=5):
            status = "processing"
            details = {
                "details": "The Letter of Credit has been submitted to the SWIFT network and is being processed.",
                "estimated_completion": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
            }
        else:
            status = "delivered"
            details = {
                "details": f"The Letter of Credit with reference {swift_data.get('reference')} has been delivered to the beneficiary institution.",
                "delivery_time": (transaction.created_at + timedelta(minutes=5)).isoformat()
            }
            
            # If it's been delivered and transaction is still pending, update it
            if transaction.status == TransactionStatus.PENDING:
                transaction.status = TransactionStatus.COMPLETED
                db.session.commit()
        
        return {
            "success": True,
            "status": status,
            "details": details
        }
    
    @staticmethod
    def get_fund_transfer_status(transaction_id):
        """Get the status of a Fund Transfer"""
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {"success": False, "error": "Transaction not found"}
            
        if transaction.transaction_type not in [TransactionType.SWIFT_FUND_TRANSFER, TransactionType.SWIFT_INSTITUTION_TRANSFER]:
            return {"success": False, "error": "Not a Fund Transfer transaction"}
            
        # Similar logic to letter of credit status
        created_delta = datetime.utcnow() - transaction.created_at
        
        try:
            swift_data = json.loads(transaction.tx_metadata_json)
        except (json.JSONDecodeError, TypeError):
            return {"success": False, "error": "Invalid SWIFT message data"}
            
        # Simulate different statuses based on time
        if created_delta < timedelta(minutes=3):
            status = "processing"
            details = {
                "details": "The Fund Transfer has been submitted to the SWIFT network and is being processed.",
                "estimated_completion": (datetime.utcnow() + timedelta(minutes=3)).isoformat()
            }
        else:
            status = "settled"
            details = {
                "details": f"The Fund Transfer with reference {swift_data.get('reference')} has been settled.",
                "settlement_time": (transaction.created_at + timedelta(minutes=3)).isoformat()
            }
            
            # Update transaction status if needed
            if transaction.status == TransactionStatus.PENDING:
                transaction.status = TransactionStatus.COMPLETED
                db.session.commit()
        
        return {
            "success": True,
            "status": status,
            "details": details
        }
    
    @staticmethod
    def get_free_format_message_status(transaction_id):
        """Get the status of a Free Format Message"""
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return {"success": False, "error": "Transaction not found"}
            
        if transaction.transaction_type != TransactionType.SWIFT_FREE_FORMAT:
            return {"success": False, "error": "Not a Free Format Message transaction"}
            
        # Similar approach to the other status methods
        created_delta = datetime.utcnow() - transaction.created_at
        
        try:
            swift_data = json.loads(transaction.tx_metadata_json)
        except (json.JSONDecodeError, TypeError):
            return {"success": False, "error": "Invalid SWIFT message data"}
            
        # Free format messages are typically delivered more quickly
        if created_delta < timedelta(minutes=2):
            status = "processing"
            details = {
                "details": "The message has been submitted to the SWIFT network and is being processed.",
                "estimated_delivery": (datetime.utcnow() + timedelta(minutes=2)).isoformat()
            }
        else:
            status = "delivered"
            details = {
                "details": f"The message with reference {swift_data.get('reference')} has been delivered to the recipient institution.",
                "delivery_time": (transaction.created_at + timedelta(minutes=2)).isoformat()
            }
            
            # Update transaction status if needed
            if transaction.status == TransactionStatus.PENDING:
                transaction.status = TransactionStatus.COMPLETED
                db.session.commit()
        
        return {
            "success": True,
            "status": status,
            "details": details
        }