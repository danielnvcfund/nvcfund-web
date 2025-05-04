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
    
    def __init__(self, user_id, institution_id, amount, currency, beneficiary, expiry_date, terms_and_conditions, metadata=None):
        super().__init__(user_id, institution_id)
        self.message_type = "MT760"
        self.amount = amount
        self.currency = currency
        self.beneficiary = beneficiary
        self.expiry_date = expiry_date
        self.terms_and_conditions = terms_and_conditions
        self.metadata = metadata
        self.reference = f"LC{uuid.uuid4().hex[:10].upper()}"
        
    def to_json(self):
        """Convert letter of credit to JSON representation"""
        # Start with the standard fields
        json_data = {
            "message_type": self.message_type,
            "reference": self.reference,
            "sender_bic": self.get_sender_bic(),
            "receiver_bic": self.get_receiver_bic(),
            "issuing_bank": "NVC Global Bank",
            "issue_date": datetime.now().strftime("%Y-%m-%d"),
            "expiry_date": self.expiry_date.strftime("%Y-%m-%d") if hasattr(self.expiry_date, 'strftime') else self.expiry_date,
            "amount": self.amount,
            "currency": self.currency
        }
        
        # Handle beneficiary data - parse if it's a string
        if isinstance(self.beneficiary, str):
            try:
                json_data["beneficiary"] = json.loads(self.beneficiary)
            except json.JSONDecodeError:
                json_data["beneficiary"] = {"full_info": self.beneficiary}
        else:
            json_data["beneficiary"] = self.beneficiary
            
        # Handle terms and conditions data - parse if it's a string
        if isinstance(self.terms_and_conditions, str):
            try:
                json_data["terms_and_conditions"] = json.loads(self.terms_and_conditions)
            except json.JSONDecodeError:
                json_data["terms_and_conditions"] = {"full_text": self.terms_and_conditions}
        else:
            json_data["terms_and_conditions"] = self.terms_and_conditions
            
        # Add any additional metadata if provided
        if self.metadata:
            try:
                # If metadata is a JSON string, parse it
                if isinstance(self.metadata, str):
                    metadata_dict = json.loads(self.metadata)
                else:
                    metadata_dict = self.metadata
                    
                # Add applicant information from metadata if available
                if "applicant" in metadata_dict:
                    json_data["applicant"] = metadata_dict["applicant"]
                    
                # Add advising bank information
                if "advising_bank_id" in metadata_dict:
                    json_data["advising_bank_id"] = metadata_dict["advising_bank_id"]
                    
                # Add available with information
                if "available_with" in metadata_dict:
                    json_data["available_with"] = metadata_dict["available_with"]
                    
                # Add place of expiry
                if "expiry_place" in metadata_dict:
                    json_data["expiry_place"] = metadata_dict["expiry_place"]
                    
                # Add transaction type (standby, commercial, etc.)
                if "transaction_type" in metadata_dict:
                    json_data["transaction_type"] = metadata_dict["transaction_type"]
                    
                # Add goods/services description
                if "goods_description" in metadata_dict:
                    json_data["goods_description"] = metadata_dict["goods_description"]
                    
                # Add documents required information
                if "documents_required" in metadata_dict:
                    json_data["documents_required"] = metadata_dict["documents_required"]
                    
                # Add charges information
                if "charges" in metadata_dict:
                    json_data["charges"] = metadata_dict["charges"]
                    
                # Add additional fields
                if "transferable" in metadata_dict:
                    json_data["transferable"] = metadata_dict["transferable"]
                    
                if "confirmation_instructions" in metadata_dict:
                    json_data["confirmation_instructions"] = metadata_dict["confirmation_instructions"]
                    
                if "presentation_period" in metadata_dict:
                    json_data["presentation_period"] = metadata_dict["presentation_period"]
                    
                # Add any other fields from metadata that don't conflict with existing fields
                for key, value in metadata_dict.items():
                    if key not in json_data and key not in ["message_type", "reference", "amount", "currency"]:
                        json_data[key] = value
                        
            except Exception as e:
                logger.error(f"Error processing metadata in MT760: {str(e)}")
                
        return json_data
        
    def generate_transaction(self):
        """Create a transaction record for this letter of credit"""
        # Get beneficiary name for the description
        beneficiary_name = "Unknown Beneficiary"
        try:
            if isinstance(self.beneficiary, str):
                ben_data = json.loads(self.beneficiary)
                if "name" in ben_data:
                    beneficiary_name = ben_data["name"]
            elif isinstance(self.beneficiary, dict) and "name" in self.beneficiary:
                beneficiary_name = self.beneficiary["name"]
        except Exception:
            pass
            
        description = f"Standby Letter of Credit {self.reference} for {beneficiary_name} - {self.amount} {self.currency}"
        
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
    
    def __init__(self, user_id, institution_id, amount, currency, ordering_customer, beneficiary_customer, details_of_payment, 
                 correspondent_bank_name=None, correspondent_bank_swift=None, intermediary_bank_name=None, intermediary_bank_swift=None,
                 receiving_bank_name=None, receiving_bank_address=None, receiving_bank_swift=None, receiving_bank_routing=None,
                 receiving_bank_officer=None, account_holder_name=None, account_number=None):
        super().__init__(user_id, institution_id)
        self.message_type = "MT103"
        self.amount = amount
        self.currency = currency
        self.ordering_customer = ordering_customer
        self.beneficiary_customer = beneficiary_customer
        self.details_of_payment = details_of_payment
        
        # Correspondent and intermediary bank information
        self.correspondent_bank_name = correspondent_bank_name
        self.correspondent_bank_swift = correspondent_bank_swift
        self.intermediary_bank_name = intermediary_bank_name
        self.intermediary_bank_swift = intermediary_bank_swift
        
        # Receiving bank details
        self.receiving_bank_name = receiving_bank_name
        self.receiving_bank_address = receiving_bank_address
        self.receiving_bank_swift = receiving_bank_swift
        self.receiving_bank_routing = receiving_bank_routing
        self.receiving_bank_officer = receiving_bank_officer
        
        # Account holder details
        self.account_holder_name = account_holder_name
        self.account_number = account_number
        
        self.reference = f"FT{uuid.uuid4().hex[:10].upper()}"
        
    def to_json(self):
        """Convert fund transfer to JSON representation"""
        institution = FinancialInstitution.query.get(self.institution_id)
        institution_name = institution.name if institution else "Unknown Institution"
        
        result = {
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
        
        # Add receiving bank details if provided
        if any([self.receiving_bank_name, self.receiving_bank_address, self.receiving_bank_swift, self.receiving_bank_routing, self.receiving_bank_officer]):
            result["receiving_bank"] = {
                "name": self.receiving_bank_name,
                "address": self.receiving_bank_address,
                "swift": self.receiving_bank_swift,
                "routing": self.receiving_bank_routing,
                "officer": self.receiving_bank_officer
            }
            
        # Add account holder details if provided
        if any([self.account_holder_name, self.account_number]):
            result["account_holder"] = {
                "name": self.account_holder_name,
                "account_number": self.account_number
            }
        
        # Add correspondent bank information if provided
        if self.correspondent_bank_name or self.correspondent_bank_swift:
            result["correspondent_bank"] = {
                "name": self.correspondent_bank_name,
                "swift": self.correspondent_bank_swift
            }
            
        # Add intermediary bank information if provided
        if self.intermediary_bank_name or self.intermediary_bank_swift:
            result["intermediary_bank"] = {
                "name": self.intermediary_bank_name,
                "swift": self.intermediary_bank_swift
            }
            
        return result
        
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
    
    def __init__(self, user_id, institution_id, amount, currency, ordering_customer, beneficiary_customer, details_of_payment, 
                 correspondent_bank_name=None, correspondent_bank_swift=None, intermediary_bank_name=None, intermediary_bank_swift=None,
                 receiving_bank_name=None, receiving_bank_address=None, receiving_bank_swift=None, receiving_bank_routing=None,
                 receiving_bank_officer=None, account_holder_name=None, account_number=None):
        super().__init__(user_id, institution_id)
        self.message_type = "MT202"
        self.amount = amount
        self.currency = currency
        self.ordering_customer = ordering_customer
        self.beneficiary_customer = beneficiary_customer
        self.details_of_payment = details_of_payment
        
        # Correspondent and intermediary bank information
        self.correspondent_bank_name = correspondent_bank_name
        self.correspondent_bank_swift = correspondent_bank_swift
        self.intermediary_bank_name = intermediary_bank_name
        self.intermediary_bank_swift = intermediary_bank_swift
        
        # Receiving bank details
        self.receiving_bank_name = receiving_bank_name
        self.receiving_bank_address = receiving_bank_address
        self.receiving_bank_swift = receiving_bank_swift
        self.receiving_bank_routing = receiving_bank_routing
        self.receiving_bank_officer = receiving_bank_officer
        
        # Account holder details
        self.account_holder_name = account_holder_name
        self.account_number = account_number
        
        self.reference = f"IT{uuid.uuid4().hex[:10].upper()}"
        
    def to_json(self):
        """Convert institution transfer to JSON representation"""
        institution = FinancialInstitution.query.get(self.institution_id)
        institution_name = institution.name if institution else "Unknown Institution"
        
        result = {
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
        
        # Add receiving bank details if provided
        if any([self.receiving_bank_name, self.receiving_bank_address, self.receiving_bank_swift, self.receiving_bank_routing, self.receiving_bank_officer]):
            result["receiving_bank"] = {
                "name": self.receiving_bank_name,
                "address": self.receiving_bank_address,
                "swift": self.receiving_bank_swift,
                "routing": self.receiving_bank_routing,
                "officer": self.receiving_bank_officer
            }
            
        # Add account holder details if provided
        if any([self.account_holder_name, self.account_number]):
            result["account_holder"] = {
                "name": self.account_holder_name,
                "account_number": self.account_number
            }
        
        # Add correspondent bank information if provided
        if self.correspondent_bank_name or self.correspondent_bank_swift:
            result["correspondent_bank"] = {
                "name": self.correspondent_bank_name,
                "swift": self.correspondent_bank_swift
            }
            
        # Add intermediary bank information if provided
        if self.intermediary_bank_name or self.intermediary_bank_swift:
            result["intermediary_bank"] = {
                "name": self.intermediary_bank_name,
                "swift": self.intermediary_bank_swift
            }
            
        return result
        
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

class MT542(SwiftMessage):
    """SWIFT MT542 - Deliver Against Payment"""
    
    def __init__(self, user_id, institution_id, trade_details, financial_instrument, settlement_details):
        super().__init__(user_id, institution_id)
        self.message_type = "MT542"
        self.trade_details = trade_details
        self.financial_instrument = financial_instrument
        self.settlement_details = settlement_details
        self.reference = f"DAP{uuid.uuid4().hex[:10].upper()}"
        
    def to_json(self):
        """Convert deliver against payment to JSON representation"""
        institution = FinancialInstitution.query.get(self.institution_id)
        institution_name = institution.name if institution else "Unknown Institution"
        
        return {
            "message_type": self.message_type,
            "reference": self.reference,
            "sender_bic": self.get_sender_bic(),
            "receiver_bic": self.get_receiver_bic(),
            "trade_details": self.trade_details,
            "financial_instrument": self.financial_instrument,
            "settlement_details": self.settlement_details,
            "sender_institution": "NVC Global Bank",
            "receiver_institution": institution_name,
            "creation_date": datetime.now().strftime("%Y-%m-%d")
        }
        
    def generate_transaction(self):
        """Create a transaction record for this deliver against payment"""
        description = f"SWIFT MT542 Deliver Against Payment {self.reference}"
        
        # Prepare metadata
        metadata = self.to_json()
        metadata["institution_id"] = self.institution_id
        
        # Create the transaction
        transaction = record_transaction(
            user_id=self.user_id,
            amount=float(self.trade_details.get('amount', 0)),
            currency=self.trade_details.get('currency', 'USD'),
            transaction_type=TransactionType.SWIFT_DELIVER_AGAINST_PAYMENT,
            status=TransactionStatus.PENDING,
            description=description,
            metadata=metadata
        )
        
        return transaction

class MT199(SwiftMessage):
    """SWIFT MT199 - Free Format Message"""
    
    def __init__(self, user_id, institution_id, related_reference, message_text):
        super().__init__(user_id, institution_id)
        self.message_type = "MT199"
        self.related_reference = related_reference
        self.message_text = message_text
        self.reference = f"FF{uuid.uuid4().hex[:10].upper()}"
        
    def to_json(self):
        """Convert free format message to JSON representation"""
        institution = FinancialInstitution.query.get(self.institution_id)
        institution_name = institution.name if institution else "Unknown Institution"
        
        return {
            "message_type": self.message_type,
            "reference": self.reference,
            "related_reference": self.related_reference,
            "sender_bic": self.get_sender_bic(),
            "receiver_bic": self.get_receiver_bic(),
            "sender_institution": "NVC Global Bank",
            "receiver_institution": institution_name,
            "creation_date": datetime.now().strftime("%Y-%m-%d"),
            "message_text": self.message_text
        }
        
    def generate_transaction(self):
        """Create a transaction record for this free format message"""
        description = f"SWIFT MT199 Free Format Message {self.reference}"
        
        # Prepare metadata
        metadata = self.to_json()
        metadata["institution_id"] = self.institution_id
        
        # Create the transaction
        transaction = record_transaction(
            user_id=self.user_id,
            amount=0.0,  # Free format messages don't have amounts
            currency="USD",  # Default currency
            transaction_type=TransactionType.SWIFT_FREE_FORMAT,
            status=TransactionStatus.PENDING,
            description=description,
            metadata=metadata
        )
        
        return transaction

class MT799(SwiftMessage):
    """SWIFT MT799 - Free Format Message"""
    
    def __init__(self, user_id, institution_id, subject, message_body, **kwargs):
        super().__init__(user_id, institution_id)
        self.message_type = "MT799"
        self.subject = subject
        self.message_body = message_body
        
        # Use provided reference number or generate one
        self.reference = kwargs.get('reference_number') or f"FM{uuid.uuid4().hex[:10].upper()}"
        self.related_reference = kwargs.get('related_reference')
        
        # Beneficiary information
        self.beneficiary_name = kwargs.get('beneficiary_name')
        self.beneficiary_account = kwargs.get('beneficiary_account')
        self.beneficiary_bank = kwargs.get('beneficiary_bank')
        self.beneficiary_bank_swift = kwargs.get('beneficiary_bank_swift')
        
        # Processing institution
        self.processing_institution = kwargs.get('processing_institution')
        
        # Custom institution details (if provided)
        self.custom_institution_name = kwargs.get('custom_institution_name')
        self.custom_swift_code = kwargs.get('custom_swift_code')
        
    def to_json(self):
        """Convert free format message to JSON representation"""
        institution = FinancialInstitution.query.get(self.institution_id)
        
        # Use custom institution details if provided, otherwise use the db record
        institution_name = self.custom_institution_name or (institution.name if institution else "Unknown Institution")
        institution_swift = self.custom_swift_code or (institution.swift_code if institution else None)
        
        # Build the complete metadata structure
        data = {
            "message_type": self.message_type,
            "reference": self.reference,
            "sender_bic": self.get_sender_bic(),
            "receiver_bic": institution_swift or self.get_receiver_bic(),
            "sender_institution": "NVC Global Bank",
            "receiver_institution": institution_name,
            "creation_date": datetime.now().strftime("%Y-%m-%d"),
            "subject": self.subject,
            "message_body": self.message_body
        }
        
        # Add beneficiary information if provided
        if self.beneficiary_name or self.beneficiary_account or self.beneficiary_bank:
            data["beneficiary"] = {
                "name": self.beneficiary_name,
                "account": self.beneficiary_account,
                "bank": {
                    "name": self.beneficiary_bank,
                    "swift": self.beneficiary_bank_swift
                }
            }
        
        # Add related reference if provided
        if self.related_reference:
            data["related_reference"] = self.related_reference
            
        # Add processing institution if provided
        if self.processing_institution:
            data["processing_institution"] = self.processing_institution
            
        return data
        
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
    def create_letter_of_credit(user_id, receiver_institution_id, amount, currency, beneficiary, expiry_date, 
                               terms_and_conditions, metadata=None):
        """Create a new Standby Letter of Credit (MT760)"""
        try:
            # Create MT760 message with enhanced fields
            mt760 = MT760(
                user_id=user_id,
                institution_id=receiver_institution_id,
                amount=amount,
                currency=currency,
                beneficiary=beneficiary,
                expiry_date=expiry_date,
                terms_and_conditions=terms_and_conditions,
                metadata=metadata
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
    def create_swift_fund_transfer(user_id, receiver_institution_id, receiver_institution_name=None, amount=0, currency='USD', 
                                   ordering_customer='', beneficiary_customer='', details_of_payment='', is_financial_institution=False,
                                   correspondent_bank_name=None, correspondent_bank_swift=None, 
                                   intermediary_bank_name=None, intermediary_bank_swift=None,
                                   receiving_bank_name=None, receiving_bank_address=None, receiving_bank_swift=None, receiving_bank_routing=None,
                                   receiving_bank_officer=None, account_holder_name=None, account_number=None):
        """Create a new SWIFT fund transfer (MT103 or MT202)"""
        try:
            # Get the institution from the database
            institution = FinancialInstitution.query.get(receiver_institution_id)
            
            # Store the provided institution name in the institution's metadata
            if institution and receiver_institution_name:
                try:
                    metadata = json.loads(institution.metadata_json) if institution.metadata_json else {}
                except json.JSONDecodeError:
                    metadata = {}
                
                # Add or update the custom_name field
                if 'swift' not in metadata:
                    metadata['swift'] = {}
                    
                metadata['swift']['custom_name'] = receiver_institution_name
                
                # Save the updated metadata
                institution.metadata_json = json.dumps(metadata)
                db.session.commit()
                
                logger.info(f"Updated institution {institution.id} with custom name: {receiver_institution_name}")
            
            # Create either MT103 or MT202 message based on is_financial_institution flag
            if is_financial_institution:
                message = MT202(
                    user_id=user_id,
                    institution_id=receiver_institution_id,
                    amount=amount,
                    currency=currency,
                    ordering_customer=ordering_customer, 
                    beneficiary_customer=beneficiary_customer,
                    details_of_payment=details_of_payment,
                    correspondent_bank_name=correspondent_bank_name,
                    correspondent_bank_swift=correspondent_bank_swift,
                    intermediary_bank_name=intermediary_bank_name,
                    intermediary_bank_swift=intermediary_bank_swift,
                    receiving_bank_name=receiving_bank_name,
                    receiving_bank_address=receiving_bank_address,
                    receiving_bank_swift=receiving_bank_swift,
                    receiving_bank_routing=receiving_bank_routing,
                    account_holder_name=account_holder_name,
                    account_number=account_number
                )
            else:
                message = MT103(
                    user_id=user_id,
                    institution_id=receiver_institution_id,
                    amount=amount,
                    currency=currency,
                    ordering_customer=ordering_customer,
                    beneficiary_customer=beneficiary_customer,
                    details_of_payment=details_of_payment,
                    correspondent_bank_name=correspondent_bank_name,
                    correspondent_bank_swift=correspondent_bank_swift,
                    intermediary_bank_name=intermediary_bank_name,
                    intermediary_bank_swift=intermediary_bank_swift,
                    receiving_bank_name=receiving_bank_name,
                    receiving_bank_address=receiving_bank_address,
                    receiving_bank_swift=receiving_bank_swift,
                    receiving_bank_routing=receiving_bank_routing,
                    account_holder_name=account_holder_name,
                    account_number=account_number
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
    def create_free_format_message(user_id, receiver_institution_id, subject, message_body, 
                                  reference_number=None, related_reference=None, 
                                  beneficiary_name=None, beneficiary_account=None,
                                  beneficiary_bank=None, beneficiary_bank_swift=None,
                                  processing_institution=None,
                                  custom_institution_name=None, custom_swift_code=None):
        """Create a new SWIFT free format message (MT799) with enhanced information"""
        try:
            # Create MT799 message with all available optional parameters
            mt799 = MT799(
                user_id=user_id,
                institution_id=receiver_institution_id,
                subject=subject,
                message_body=message_body,
                reference_number=reference_number,
                related_reference=related_reference,
                beneficiary_name=beneficiary_name,
                beneficiary_account=beneficiary_account,
                beneficiary_bank=beneficiary_bank,
                beneficiary_bank_swift=beneficiary_bank_swift,
                processing_institution=processing_institution,
                custom_institution_name=custom_institution_name,
                custom_swift_code=custom_swift_code
            )
            
            # Generate transaction from the message
            transaction = mt799.generate_transaction()
            
            # In a real system, we would send this to SWIFT network
            # For now, simulate successful submission
            logger.info(f"Enhanced free format message created: {transaction.transaction_id}")
            
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