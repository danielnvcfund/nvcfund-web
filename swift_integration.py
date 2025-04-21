"""
SWIFT Integration Module for NVC Banking Platform
This module provides functionality for interacting with the SWIFT messaging network
for bank-to-bank communication.

Supported message types:
- MT760: Standby Letter of Credit
- MT103: Single Customer Credit Transfer
- MT202: General Financial Institution Transfer
- MT799: Free Format Message
"""

import json
import uuid
from datetime import datetime, timedelta

from app import db
from models import Transaction, TransactionType, TransactionStatus, FinancialInstitution, User
from transaction_service import record_transaction


class SwiftMessage:
    """Base class for SWIFT messages"""
    def __init__(self, message_type, sender_bic, receiver_bic, reference=None):
        self.message_type = message_type
        self.sender_bic = sender_bic
        self.receiver_bic = receiver_bic
        self.reference = reference or self._generate_reference()
        self.creation_date = datetime.now()
    
    def _generate_reference(self):
        """Generate a unique reference number for SWIFT message"""
        return f"M{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
    
    def to_dict(self):
        """Convert message to dictionary"""
        return {
            'message_type': self.message_type,
            'sender_bic': self.sender_bic,
            'receiver_bic': self.receiver_bic,
            'reference': self.reference,
            'creation_date': self.creation_date.isoformat()
        }
    
    def to_json(self):
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())


class MT760Message(SwiftMessage):
    """SWIFT MT760 - Standby Letter of Credit message"""
    def __init__(self, sender_bic, receiver_bic, reference=None, amount=0.0, 
                 currency='USD', beneficiary='', expiry_date=None, terms_and_conditions=''):
        super().__init__('MT760', sender_bic, receiver_bic, reference)
        self.amount = amount
        self.currency = currency
        self.beneficiary = beneficiary
        self.expiry_date = expiry_date or (datetime.now() + timedelta(days=180))
        self.terms_and_conditions = terms_and_conditions
    
    def to_dict(self):
        """Convert message to dictionary with MT760 specific fields"""
        data = super().to_dict()
        data.update({
            'amount': self.amount,
            'currency': self.currency,
            'beneficiary': self.beneficiary,
            'expiry_date': self.expiry_date.isoformat(),
            'terms_and_conditions': self.terms_and_conditions
        })
        return data


class MT103Message(SwiftMessage):
    """SWIFT MT103 - Single Customer Credit Transfer message"""
    def __init__(self, sender_bic, receiver_bic, reference=None, amount=0.0, 
                 currency='USD', ordering_customer='', beneficiary_customer='', 
                 details_of_payment=''):
        super().__init__('MT103', sender_bic, receiver_bic, reference)
        self.amount = amount
        self.currency = currency
        self.ordering_customer = ordering_customer
        self.beneficiary_customer = beneficiary_customer
        self.details_of_payment = details_of_payment
    
    def to_dict(self):
        """Convert message to dictionary with MT103 specific fields"""
        data = super().to_dict()
        data.update({
            'amount': self.amount,
            'currency': self.currency,
            'ordering_customer': self.ordering_customer,
            'beneficiary_customer': self.beneficiary_customer,
            'details_of_payment': self.details_of_payment
        })
        return data


class MT202Message(SwiftMessage):
    """SWIFT MT202 - General Financial Institution Transfer message"""
    def __init__(self, sender_bic, receiver_bic, reference=None, amount=0.0, 
                 currency='USD', ordering_institution='', beneficiary_institution='', 
                 details_of_payment=''):
        super().__init__('MT202', sender_bic, receiver_bic, reference)
        self.amount = amount
        self.currency = currency
        self.ordering_institution = ordering_institution
        self.beneficiary_institution = beneficiary_institution
        self.details_of_payment = details_of_payment
    
    def to_dict(self):
        """Convert message to dictionary with MT202 specific fields"""
        data = super().to_dict()
        data.update({
            'amount': self.amount,
            'currency': self.currency,
            'ordering_institution': self.ordering_institution,
            'beneficiary_institution': self.beneficiary_institution,
            'details_of_payment': self.details_of_payment
        })
        return data


class MT799Message(SwiftMessage):
    """SWIFT MT799 - Free Format Message"""
    def __init__(self, sender_bic, receiver_bic, reference=None, narrative_text=''):
        super().__init__('MT799', sender_bic, receiver_bic, reference)
        self.narrative_text = narrative_text
    
    def to_dict(self):
        """Convert message to dictionary with MT799 specific fields"""
        data = super().to_dict()
        data.update({
            'narrative': self.narrative_text
        })
        return data


class SwiftConnection:
    """Handles connection to SWIFT network"""
    def __init__(self, sender_institution_id):
        self.institution = FinancialInstitution.query.get(sender_institution_id)
        if not self.institution:
            raise ValueError(f"Financial institution with ID {sender_institution_id} not found")
        
        self.swift_credentials = self._get_swift_credentials()
    
    def _get_swift_credentials(self):
        """Get SWIFT credentials from institution metadata"""
        if not self.institution.metadata_json:
            return {}
            
        try:
            metadata = json.loads(self.institution.metadata_json)
            return metadata.get('swift', {})
        except json.JSONDecodeError:
            return {}
    
    def send_message(self, message):
        """Send a SWIFT message"""
        # In a real implementation, this would connect to SWIFT network
        # For this demo, we'll simulate sending and return success
        
        # Check if we have the required SWIFT credentials
        if not self.swift_credentials.get('bic'):
            return False, "Missing SWIFT BIC code in institution configuration"
        
        # Simulate sending the message
        # In real implementation, this would use SWIFT SDK or API
        
        # Return success for simulation
        return True, message.reference


class SwiftService:
    """Service class for SWIFT messaging"""
    
    @staticmethod
    def get_swift_enabled_institutions():
        """Get all institutions that have SWIFT capability"""
        institutions = FinancialInstitution.query.filter_by(is_active=True).all()
        
        # Filter to only those with SWIFT credentials
        swift_institutions = []
        for institution in institutions:
            if not institution.metadata_json:
                continue
                
            try:
                metadata = json.loads(institution.metadata_json)
                if 'swift' in metadata and metadata['swift'].get('bic'):
                    swift_institutions.append(institution)
            except json.JSONDecodeError:
                continue
        
        return swift_institutions
    
    @staticmethod
    def create_standby_letter_of_credit(user_id, receiver_institution_id, amount, currency, 
                                        beneficiary, expiry_date, terms_and_conditions):
        """Create a Standby Letter of Credit via MT760 message"""
        # Get the user and receiver institution
        user = User.query.get(user_id)
        if not user:
            return False, "User not found", None
            
        institution = FinancialInstitution.query.get(receiver_institution_id)
        if not institution:
            return False, "Receiving institution not found", None
        
        # Get receiver SWIFT BIC code
        receiver_bic = SwiftService._get_institution_bic(institution)
        if not receiver_bic:
            return False, "Receiving institution has no SWIFT BIC code configured", None
        
        # Get sender SWIFT BIC code (NVC Global)
        sender_institution = FinancialInstitution.query.filter_by(name="NVC Global").first()
        if not sender_institution:
            return False, "NVC Global institution not found", None
            
        sender_bic = SwiftService._get_institution_bic(sender_institution)
        if not sender_bic:
            return False, "NVC Global has no SWIFT BIC code configured", None
        
        # Create the MT760 message
        expiry_datetime = datetime.combine(expiry_date, datetime.min.time())
        message = MT760Message(
            sender_bic=sender_bic,
            receiver_bic=receiver_bic,
            amount=amount,
            currency=currency,
            beneficiary=beneficiary,
            expiry_date=expiry_datetime,
            terms_and_conditions=terms_and_conditions
        )
        
        # Connect to SWIFT and send the message
        try:
            connection = SwiftConnection(sender_institution.id)
            success, reference = connection.send_message(message)
            
            if not success:
                return False, f"Failed to send SWIFT message: {reference}", None
                
            # Record the transaction
            transaction = record_transaction(
                user_id=user_id,
                transaction_type=TransactionType.LETTER_OF_CREDIT,
                amount=amount,
                currency=currency,
                description=f"Standby Letter of Credit to {institution.name}",
                status=TransactionStatus.PENDING,
                metadata={
                    'swift': message.to_dict(),
                    'receiver_institution_id': receiver_institution_id
                }
            )
            
            return True, "Standby Letter of Credit initiated successfully", transaction
            
        except Exception as e:
            return False, f"Error sending SWIFT message: {str(e)}", None
    
    @staticmethod
    def create_swift_fund_transfer(user_id, receiver_institution_id, amount, currency,
                                  beneficiary_customer, ordering_customer='', 
                                  details_of_payment='', use_mt202=False):
        """Create a SWIFT MT103 or MT202 fund transfer"""
        # Get the user and receiver institution
        user = User.query.get(user_id)
        if not user:
            return False, "User not found", None
            
        institution = FinancialInstitution.query.get(receiver_institution_id)
        if not institution:
            return False, "Receiving institution not found", None
        
        # Get receiver SWIFT BIC code
        receiver_bic = SwiftService._get_institution_bic(institution)
        if not receiver_bic:
            return False, "Receiving institution has no SWIFT BIC code configured", None
        
        # Get sender SWIFT BIC code (NVC Global)
        sender_institution = FinancialInstitution.query.filter_by(name="NVC Global").first()
        if not sender_institution:
            return False, "NVC Global institution not found", None
            
        sender_bic = SwiftService._get_institution_bic(sender_institution)
        if not sender_bic:
            return False, "NVC Global has no SWIFT BIC code configured", None
        
        # Auto-fill ordering customer if not provided
        if not ordering_customer:
            ordering_customer = f"{user.username}\nNVC Global Client\nAccount: {user.id}"
        
        # Create the appropriate message type
        if use_mt202:
            # MT202 for bank-to-bank transfers
            message = MT202Message(
                sender_bic=sender_bic,
                receiver_bic=receiver_bic,
                amount=amount,
                currency=currency,
                ordering_institution="NVC GLOBAL BANK",
                beneficiary_institution=beneficiary_customer,
                details_of_payment=details_of_payment
            )
        else:
            # MT103 for customer transfers
            message = MT103Message(
                sender_bic=sender_bic,
                receiver_bic=receiver_bic,
                amount=amount,
                currency=currency,
                ordering_customer=ordering_customer,
                beneficiary_customer=beneficiary_customer,
                details_of_payment=details_of_payment
            )
        
        # Connect to SWIFT and send the message
        try:
            connection = SwiftConnection(sender_institution.id)
            success, reference = connection.send_message(message)
            
            if not success:
                return False, f"Failed to send SWIFT message: {reference}", None
                
            # Record the transaction
            transaction = record_transaction(
                user_id=user_id,
                transaction_type=TransactionType.SWIFT_TRANSFER,
                amount=amount,
                currency=currency,
                description=f"SWIFT {message.message_type} Transfer to {institution.name}",
                status=TransactionStatus.PENDING,
                metadata={
                    'swift': message.to_dict(),
                    'receiver_institution_id': receiver_institution_id
                }
            )
            
            return True, f"{message.message_type} transfer initiated successfully", transaction
            
        except Exception as e:
            return False, f"Error sending SWIFT message: {str(e)}", None
    
    @staticmethod
    def send_free_format_message(user_id, receiver_institution_id, reference, narrative_text):
        """Send a SWIFT MT799 free format message"""
        # Get the user and receiver institution
        user = User.query.get(user_id)
        if not user:
            return False, "User not found", None
            
        institution = FinancialInstitution.query.get(receiver_institution_id)
        if not institution:
            return False, "Receiving institution not found", None
        
        # Get receiver SWIFT BIC code
        receiver_bic = SwiftService._get_institution_bic(institution)
        if not receiver_bic:
            return False, "Receiving institution has no SWIFT BIC code configured", None
        
        # Get sender SWIFT BIC code (NVC Global)
        sender_institution = FinancialInstitution.query.filter_by(name="NVC Global").first()
        if not sender_institution:
            return False, "NVC Global institution not found", None
            
        sender_bic = SwiftService._get_institution_bic(sender_institution)
        if not sender_bic:
            return False, "NVC Global has no SWIFT BIC code configured", None
        
        # Create the MT799 message
        message = MT799Message(
            sender_bic=sender_bic,
            receiver_bic=receiver_bic,
            reference=reference,
            narrative_text=narrative_text
        )
        
        # Connect to SWIFT and send the message
        try:
            connection = SwiftConnection(sender_institution.id)
            success, reference = connection.send_message(message)
            
            if not success:
                return False, f"Failed to send SWIFT message: {reference}", None
                
            # Record the transaction
            transaction = record_transaction(
                user_id=user_id,
                transaction_type=TransactionType.SWIFT_MESSAGE,
                amount=0.0,  # No amount for free format message
                currency="USD",  # Default currency
                description=f"SWIFT MT799 Message to {institution.name}",
                status=TransactionStatus.PENDING,
                metadata={
                    'swift': message.to_dict(),
                    'receiver_institution_id': receiver_institution_id
                }
            )
            
            return True, "Free format message sent successfully", transaction
            
        except Exception as e:
            return False, f"Error sending SWIFT message: {str(e)}", None
    
    @staticmethod
    def get_swift_message_status(transaction_id):
        """Get status of a SWIFT message"""
        # Get the transaction
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        if not transaction:
            return {
                'success': False,
                'error': 'Transaction not found'
            }
        
        # Check if this is a SWIFT transaction
        if transaction.transaction_type not in [
            TransactionType.LETTER_OF_CREDIT,
            TransactionType.SWIFT_TRANSFER,
            TransactionType.SWIFT_MESSAGE
        ]:
            return {
                'success': False,
                'error': 'Not a SWIFT transaction'
            }
        
        # Get SWIFT data from transaction metadata
        swift_data = {}
        try:
            metadata = json.loads(transaction.tx_metadata_json or '{}')
            swift_data = metadata.get('swift', {})
            
            if not swift_data:
                return {
                    'success': False,
                    'error': 'No SWIFT data found in transaction'
                }
        except:
            return {
                'success': False,
                'error': 'Error parsing transaction metadata'
            }
        
        # In a real implementation, this would query the SWIFT network
        # For this demo, we'll return a simulated status based on transaction status
        
        status_mapping = {
            TransactionStatus.COMPLETED: 'delivered',
            TransactionStatus.PENDING: 'processing',
            TransactionStatus.FAILED: 'failed',
            TransactionStatus.CANCELLED: 'cancelled'
        }
        
        swift_status = status_mapping.get(transaction.status, 'unknown')
        
        # Simulate SWIFT network response
        return {
            'success': True,
            'status': swift_status,
            'reference': swift_data.get('reference', 'unknown'),
            'message_type': swift_data.get('message_type', 'unknown'),
            'details': {
                'sender_bic': swift_data.get('sender_bic', 'unknown'),
                'receiver_bic': swift_data.get('receiver_bic', 'unknown'),
                'creation_date': swift_data.get('creation_date', 'unknown'),
                'delivery_time': datetime.now().isoformat() if transaction.status == TransactionStatus.COMPLETED else None,
                'details': SwiftService._get_status_description(transaction.status)
            }
        }
    
    @staticmethod
    def _get_institution_bic(institution):
        """Get SWIFT BIC code from institution metadata"""
        if not institution.metadata_json:
            return None
            
        try:
            metadata = json.loads(institution.metadata_json)
            return metadata.get('swift', {}).get('bic')
        except json.JSONDecodeError:
            return None
    
    @staticmethod
    def _get_status_description(status):
        """Get human-readable description of SWIFT message status"""
        if status == TransactionStatus.COMPLETED:
            return "The message has been successfully delivered to the recipient institution."
        elif status == TransactionStatus.PENDING:
            return "The message is being processed by the SWIFT network and awaiting delivery."
        elif status == TransactionStatus.FAILED:
            return "The message could not be delivered due to an error. Please contact support."
        elif status == TransactionStatus.CANCELLED:
            return "The message delivery was cancelled."
        else:
            return "The status of this message is unknown."
    
    @staticmethod
    def update_transaction_status(transaction_id, new_status, status_details=None):
        """Update a SWIFT transaction status"""
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        if not transaction:
            return False, "Transaction not found"
            
        transaction.status = new_status
        
        # Update metadata if provided
        if status_details:
            try:
                metadata = json.loads(transaction.tx_metadata_json or '{}')
                metadata['swift_status'] = {
                    'updated_at': datetime.now().isoformat(),
                    'details': status_details
                }
                transaction.tx_metadata_json = json.dumps(metadata)
            except:
                pass
                
        db.session.commit()
        return True, "Transaction status updated successfully"