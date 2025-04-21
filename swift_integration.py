"""
SWIFT Protocol Integration for NVC Banking Platform
This module enables bank-to-bank messaging using the SWIFT network protocol standards.

Supported message types:
- MT103: Single Customer Credit Transfer
- MT202: General Financial Institution Transfer 
- MT700: Issue of a Documentary Credit
- MT760: Standby Letter of Credit (SBLC)
- MT799: Free Format Message

This integration facilitates secure, standardized communication between 
financial institutions globally for various banking operations.
"""

import os
import logging
import json
import uuid
from datetime import datetime
from enum import Enum
import requests
from typing import Dict, List, Optional, Tuple, Any, Union

from models import User, Transaction, FinancialInstitution
from app import db

logger = logging.getLogger(__name__)

# SWIFT Message Types
class SwiftMessageType(str, Enum):
    MT760 = "MT760"  # Standby Letter of Credit (SBLC)
    MT799 = "MT799"  # Free Format Message
    MT103 = "MT103"  # Single Customer Credit Transfer
    MT202 = "MT202"  # General Financial Institution Transfer
    MT700 = "MT700"  # Issue of a Documentary Credit
    MT710 = "MT710"  # Documentary Credit Notification

# SWIFT Environment Types
class SwiftEnvironment(str, Enum):
    TEST = "test"       # Test/Sandbox environment
    TRAINING = "train"  # Training environment
    PRODUCTION = "prod" # Production environment

# Current SWIFT environment
SWIFT_ENVIRONMENT = os.environ.get("SWIFT_ENVIRONMENT", SwiftEnvironment.TEST)

# SWIFT API configuration
SWIFT_API_BASE_URL = os.environ.get("SWIFT_API_URL", "https://api.swift.com/v1")
SWIFT_API_KEY = os.environ.get("SWIFT_API_KEY", "")

class SwiftCredentials:
    """Stores and manages SWIFT credentials"""
    
    def __init__(self, 
                 bic: str, 
                 institution_name: str,
                 api_key: str = "",
                 username: str = "",
                 password: str = "",
                 certificate_path: str = ""):
        self.bic = bic  # Bank Identifier Code
        self.institution_name = institution_name
        self.api_key = api_key
        self.username = username
        self.password = password
        self.certificate_path = certificate_path
        
    def is_valid(self) -> bool:
        """Check if the credentials are valid for SWIFT connectivity"""
        # BIC is the minimum required credential
        return bool(self.bic and len(self.bic) >= 8)
    
    @classmethod
    def from_financial_institution(cls, institution: FinancialInstitution) -> 'SwiftCredentials':
        """Create SwiftCredentials from a FinancialInstitution model"""
        # Extract SWIFT credentials from institution metadata
        try:
            metadata = json.loads(institution.metadata_json or '{}')
            swift_data = metadata.get('swift', {})
            
            return cls(
                bic=swift_data.get('bic', ''),
                institution_name=institution.name,
                api_key=swift_data.get('api_key', ''),
                username=swift_data.get('username', ''),
                password=swift_data.get('password', ''),
                certificate_path=swift_data.get('certificate_path', '')
            )
        except Exception as e:
            logger.error(f"Error creating SwiftCredentials from institution: {str(e)}")
            return cls('', institution.name)


class MT103Message:
    """
    Represents a SWIFT MT103 message (Single Customer Credit Transfer)
    
    MT103 Structure:
    - Basic Header: Sender information
    - Application Header: Message type, receiver, etc.
    - User Header: Banking priority, etc.
    - Text Block: Transaction details
    """
    
    def __init__(self,
                 sender_bic: str,
                 receiver_bic: str,
                 transaction_reference: str,
                 amount: float,
                 currency: str,
                 value_date: datetime,
                 ordering_customer: str,  # Name and address of the ordering customer
                 ordering_institution: str,  # BIC of the ordering institution
                 beneficiary_customer: str,  # Name and account of the beneficiary
                 beneficiary_institution: str,  # BIC of the beneficiary's institution
                 details_of_payment: str = ""
                ):
        
        self.message_type = SwiftMessageType.MT103
        self.sender_bic = sender_bic
        self.receiver_bic = receiver_bic
        self.transaction_reference = transaction_reference
        self.amount = amount
        self.currency = currency
        self.value_date = value_date
        self.ordering_customer = ordering_customer
        self.ordering_institution = ordering_institution
        self.beneficiary_customer = beneficiary_customer
        self.beneficiary_institution = beneficiary_institution
        self.details_of_payment = details_of_payment
        
    def format_swift_message(self) -> str:
        """Format the data into a valid SWIFT MT103 message"""
        # Format date according to SWIFT standards (YYMMDD)
        value_date_str = self.value_date.strftime("%y%m%d")
        
        # Format amount according to SWIFT standards
        amount_str = f"{self.amount:.2f}"
        
        # Build the message blocks
        message = [
            # Block 1: Basic Header Block
            "{1:F01" + self.sender_bic + "XXXX0000000000}",
            
            # Block 2: Application Header Block
            "{2:I103" + self.receiver_bic + "XXXXN}",
            
            # Block 4: Text Block
            "{4:",
            # Mandatory Fields
            f":20:{self.transaction_reference}",  # Reference assigned by the sender
            f":23B:CRED",  # Bank Operation Code (CRED = Credit Transfer)
            f":32A:{value_date_str}{self.currency}{amount_str}",  # Value Date, Currency, Amount
            f":50K:{self.ordering_customer}",  # Ordering Customer
            f":52A:{self.ordering_institution}",  # Ordering Institution
            f":57A:{self.beneficiary_institution}",  # Account With Institution
            f":59:{self.beneficiary_customer}",  # Beneficiary Customer
            
            # Optional Fields
            f":70:{self.details_of_payment}",  # Details of Payment
            "-}"
        ]
        
        return "\n".join(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the MT103 message to a dictionary for API requests"""
        return {
            "message_type": self.message_type,
            "sender": self.sender_bic,
            "receiver": self.receiver_bic,
            "transaction_reference": self.transaction_reference,
            "currency": self.currency,
            "amount": self.amount,
            "value_date": self.value_date.isoformat(),
            "ordering_customer": self.ordering_customer,
            "ordering_institution": self.ordering_institution,
            "beneficiary_customer": self.beneficiary_customer,
            "beneficiary_institution": self.beneficiary_institution,
            "details_of_payment": self.details_of_payment
        }
        
        
class MT202Message:
    """
    Represents a SWIFT MT202 message (General Financial Institution Transfer)
    
    MT202 Structure:
    - Basic Header: Sender information
    - Application Header: Message type, receiver, etc.
    - User Header: Banking priority, etc.
    - Text Block: Transaction details
    """
    
    def __init__(self,
                 sender_bic: str,
                 receiver_bic: str,
                 transaction_reference: str,
                 related_reference: str,
                 amount: float,
                 currency: str,
                 value_date: datetime,
                 sender_correspondent: str,  # BIC of the sender's correspondent
                 receiver_correspondent: str,  # BIC of the receiver's correspondent
                 details_of_payment: str = ""
                ):
        
        self.message_type = SwiftMessageType.MT202
        self.sender_bic = sender_bic
        self.receiver_bic = receiver_bic
        self.transaction_reference = transaction_reference
        self.related_reference = related_reference
        self.amount = amount
        self.currency = currency
        self.value_date = value_date
        self.sender_correspondent = sender_correspondent
        self.receiver_correspondent = receiver_correspondent
        self.details_of_payment = details_of_payment
        
    def format_swift_message(self) -> str:
        """Format the data into a valid SWIFT MT202 message"""
        # Format date according to SWIFT standards (YYMMDD)
        value_date_str = self.value_date.strftime("%y%m%d")
        
        # Format amount according to SWIFT standards
        amount_str = f"{self.amount:.2f}"
        
        # Build the message blocks
        message = [
            # Block 1: Basic Header Block
            "{1:F01" + self.sender_bic + "XXXX0000000000}",
            
            # Block 2: Application Header Block
            "{2:I202" + self.receiver_bic + "XXXXN}",
            
            # Block 4: Text Block
            "{4:",
            # Mandatory Fields
            f":20:{self.transaction_reference}",  # Transaction Reference
            f":21:{self.related_reference}",  # Related Reference
            f":32A:{value_date_str}{self.currency}{amount_str}",  # Value Date, Currency, Amount
            f":53A:{self.sender_correspondent}",  # Sender's Correspondent
            f":58A:{self.receiver_correspondent}",  # Receiver's Correspondent
            
            # Optional Fields
            f":72:{self.details_of_payment}",  # Sender to Receiver Information
            "-}"
        ]
        
        return "\n".join(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the MT202 message to a dictionary for API requests"""
        return {
            "message_type": self.message_type,
            "sender": self.sender_bic,
            "receiver": self.receiver_bic,
            "transaction_reference": self.transaction_reference,
            "related_reference": self.related_reference,
            "currency": self.currency,
            "amount": self.amount,
            "value_date": self.value_date.isoformat(),
            "sender_correspondent": self.sender_correspondent,
            "receiver_correspondent": self.receiver_correspondent,
            "details_of_payment": self.details_of_payment
        }


class MT799Message:
    """
    Represents a SWIFT MT799 message (Free Format Message)
    
    MT799 is a free format message type used for communication between
    financial institutions when no specific message type is available.
    """
    
    def __init__(self,
                 sender_bic: str,
                 receiver_bic: str,
                 reference: str,
                 narrative_text: str):
        
        self.message_type = SwiftMessageType.MT799
        self.sender_bic = sender_bic
        self.receiver_bic = receiver_bic
        self.reference = reference
        self.narrative_text = narrative_text
        
    def format_swift_message(self) -> str:
        """Format the data into a valid SWIFT MT799 message"""
        # Build the message blocks
        message = [
            # Block 1: Basic Header Block
            "{1:F01" + self.sender_bic + "XXXX0000000000}",
            
            # Block 2: Application Header Block
            "{2:I799" + self.receiver_bic + "XXXXN}",
            
            # Block 4: Text Block
            "{4:",
            f":20:{self.reference}",  # Reference
            f":79:{self.narrative_text.replace('\n', '\r\n')}",  # Narrative
            "-}"
        ]
        
        return "\n".join(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the MT799 message to a dictionary for API requests"""
        return {
            "message_type": self.message_type,
            "sender": self.sender_bic,
            "receiver": self.receiver_bic,
            "reference": self.reference,
            "narrative_text": self.narrative_text
        }


class MT760Message:
    """
    Represents a SWIFT MT760 message (Standby Letter of Credit)
    
    MT760 Structure:
    - Sequence A: General Information
    - Sequence B: Details of Standby Letter of Credit
    """
    
    def __init__(self,
                 sender_bic: str,
                 receiver_bic: str,
                 reference: str,
                 issue_date: datetime,
                 expiry_date: datetime,
                 amount: float,
                 currency: str,
                 applicant: str,
                 beneficiary: str,
                 terms_and_conditions: str):
        
        self.message_type = SwiftMessageType.MT760
        self.sender_bic = sender_bic
        self.receiver_bic = receiver_bic
        self.reference = reference
        self.issue_date = issue_date
        self.expiry_date = expiry_date
        self.amount = amount
        self.currency = currency
        self.applicant = applicant
        self.beneficiary = beneficiary
        self.terms_and_conditions = terms_and_conditions
        
    def format_swift_message(self) -> str:
        """Format the data into a valid SWIFT MT760 message"""
        # Format dates according to SWIFT standards (YYMMDD)
        issue_date_str = self.issue_date.strftime("%y%m%d")
        expiry_date_str = self.expiry_date.strftime("%y%m%d")
        
        # Format amount according to SWIFT standards
        amount_str = f"{self.amount:.2f}"
        
        # Build the message blocks
        message = [
            # Block 1: Basic Header Block
            "{1:F01" + self.sender_bic + "XXXX0000000000}",
            
            # Block 2: Application Header Block
            "{2:I760" + self.receiver_bic + "XXXXN}",
            
            # Block 4: Text Block
            "{4:",
            # Sequence A: General Information
            ":27A:1",
            f":20:{self.reference}",
            f":23X:SBLC",
            f":31C:{issue_date_str}",
            f":31D:{expiry_date_str}",
            f":50:{self.applicant}",
            f":59:{self.beneficiary}",
            f":32B:{self.currency}{amount_str}",
            
            # Sequence B: Terms and Conditions
            ":77D:" + self.terms_and_conditions.replace("\n", "\r\n"),
            "-}"
        ]
        
        return "\n".join(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the MT760 message to a dictionary for API requests"""
        return {
            "message_type": self.message_type,
            "sender": self.sender_bic,
            "receiver": self.receiver_bic,
            "reference": self.reference,
            "issue_date": self.issue_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat(),
            "currency": self.currency,
            "amount": self.amount,
            "applicant": self.applicant,
            "beneficiary": self.beneficiary,
            "terms_and_conditions": self.terms_and_conditions
        }


class SwiftConnection:
    """Manages connection to the SWIFT network via API or direct integration"""
    
    def __init__(self, credentials: SwiftCredentials, environment: SwiftEnvironment = SwiftEnvironment.TEST):
        self.credentials = credentials
        self.environment = environment
        self.base_url = SWIFT_API_BASE_URL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {credentials.api_key or SWIFT_API_KEY}",
            "X-Swift-BIC": credentials.bic
        }
        
    def test_connection(self) -> Tuple[bool, str]:
        """Test connection to SWIFT network"""
        # Skip real API call in test environment
        if self.environment == SwiftEnvironment.TEST and not self.credentials.api_key:
            logger.info("Test environment: Simulating successful SWIFT connectivity")
            return True, "Connection successful (TEST environment)"
            
        try:
            response = requests.get(
                f"{self.base_url}/status",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return True, "Connection successful"
            else:
                return False, f"Connection failed: {response.status_code} - {response.text}"
                
        except Exception as e:
            logger.error(f"SWIFT connection test failed: {str(e)}")
            return False, f"Connection error: {str(e)}"
            
    def send_message(self, message_obj: Union[MT103Message, MT202Message, MT760Message, MT799Message]) -> Tuple[bool, str, Optional[str]]:
        """
        Send any SWIFT message type via the SWIFT network
        
        Args:
            message_obj: A message object (MT103, MT202, MT760, MT799) 
            
        Returns:
            Tuple containing:
            - Success status (bool)
            - Message (str)
            - Message ID if successful (str or None)
        """
        message_type = message_obj.message_type
        message_type_code = message_type.value.lower()  # Convert MT103 to mt103, etc.
        
        # Skip real API call in test environment
        if self.environment == SwiftEnvironment.TEST and not self.credentials.api_key:
            logger.info(f"Test environment: Simulating successful {message_type} transmission")
            message_id = f"{message_type}-TEST-{uuid.uuid4()}"
            return True, f"{message_type} sent successfully (TEST environment) - Reference: {message_id}", message_id
            
        try:
            # Prepare message data
            swift_text = message_obj.format_swift_message()
            message_data = {
                "message_type": message_type_code,
                "sender": message_obj.sender_bic,
                "receiver": message_obj.receiver_bic,
                "message_text": swift_text,
                "priority": "normal"
            }
            
            # Send message
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=message_data
            )
            
            if response.status_code in (200, 201, 202):
                response_data = response.json()
                message_id = response_data.get("message_id", "")
                return True, f"{message_type} sent successfully - Reference: {message_id}", message_id
            else:
                return False, f"Failed to send {message_type}: {response.status_code} - {response.text}", None
                
        except Exception as e:
            logger.error(f"Error sending {message_type} message: {str(e)}")
            return False, f"Error sending {message_type}: {str(e)}", None
            
    def send_mt103(self, message: MT103Message) -> Tuple[bool, str, Optional[str]]:
        """Send MT103 (Single Customer Credit Transfer) message via SWIFT"""
        return self.send_message(message)
        
    def send_mt202(self, message: MT202Message) -> Tuple[bool, str, Optional[str]]:
        """Send MT202 (General Financial Institution Transfer) message via SWIFT"""
        return self.send_message(message)
        
    def send_mt760(self, message: MT760Message) -> Tuple[bool, str, Optional[str]]:
        """Send MT760 (Standby Letter of Credit) message via SWIFT"""
        return self.send_message(message)
        
    def send_mt799(self, message: MT799Message) -> Tuple[bool, str, Optional[str]]:
        """Send MT799 (Free Format Message) message via SWIFT"""
        return self.send_message(message)
    
    def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """Get status of a sent SWIFT message"""
        # Skip real API call in test environment
        if self.environment == SwiftEnvironment.TEST and not self.credentials.api_key:
            logger.info(f"Test environment: Simulating message status check for {message_id}")
            return {
                "message_id": message_id,
                "status": "delivered",
                "delivery_time": datetime.now().isoformat(),
                "details": "Message delivered successfully (TEST environment)"
            }
            
        try:
            response = requests.get(
                f"{self.base_url}/messages/{message_id}/status",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get message status: {response.status_code} - {response.text}")
                return {
                    "message_id": message_id,
                    "status": "unknown",
                    "error": f"Failed to retrieve status: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error getting message status: {str(e)}")
            return {
                "message_id": message_id,
                "status": "error",
                "error": str(e)
            }


class SwiftService:
    """Service for managing SWIFT operations in the NVC Banking Platform"""
    
    @staticmethod
    def get_swift_enabled_institutions() -> List[FinancialInstitution]:
        """Get all financial institutions with SWIFT capabilities"""
        institutions = FinancialInstitution.query.filter_by(is_active=True).all()
        swift_institutions = []
        
        for institution in institutions:
            try:
                metadata = json.loads(institution.metadata_json or '{}')
                if metadata.get('swift', {}).get('bic'):
                    swift_institutions.append(institution)
            except:
                pass
                
        return swift_institutions
    
    @staticmethod
    def create_standby_letter_of_credit(
        user_id: int,
        receiver_institution_id: int,
        amount: float,
        currency: str,
        beneficiary: str,
        expiry_date: datetime,
        terms_and_conditions: str
    ) -> Tuple[bool, str, Optional[Transaction]]:
        """Create and send a Standby Letter of Credit (SBLC) via SWIFT MT760"""
        try:
            # Get user and institution
            user = User.query.get(user_id)
            institution = FinancialInstitution.query.get(receiver_institution_id)
            
            if not user or not institution:
                return False, "User or financial institution not found", None
                
            # Get SWIFT credentials for sender and receiver
            sender_credentials = SwiftCredentials(
                bic=os.environ.get("NVC_SWIFT_BIC", "NVCGGB2L"),
                institution_name="NVC Global Banking"
            )
            
            receiver_credentials = SwiftCredentials.from_financial_institution(institution)
            
            if not receiver_credentials.is_valid():
                return False, f"Institution {institution.name} does not have valid SWIFT credentials", None
                
            # Generate a reference number for the SBLC
            reference = f"SBLC{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
            
            # Create MT760 message
            mt760 = MT760Message(
                sender_bic=sender_credentials.bic,
                receiver_bic=receiver_credentials.bic,
                reference=reference,
                issue_date=datetime.now(),
                expiry_date=expiry_date,
                amount=amount,
                currency=currency,
                applicant=f"//{user.username}\n{user.email}",
                beneficiary=beneficiary,
                terms_and_conditions=terms_and_conditions
            )
            
            # Initialize SWIFT connection and send message
            env = SwiftEnvironment(SWIFT_ENVIRONMENT) if isinstance(SWIFT_ENVIRONMENT, str) else SWIFT_ENVIRONMENT
            connection = SwiftConnection(sender_credentials, env)
            success, message, message_id = connection.send_mt760(mt760)
            
            if not success:
                return False, message, None
                
            # Create transaction record
            from models import TransactionType, TransactionStatus
            
            transaction = Transaction(
                user_id=user_id,
                transaction_id=f"SWIFT-{uuid.uuid4().hex[:8]}",
                transaction_type=TransactionType.LETTER_OF_CREDIT,
                amount=amount,
                currency=currency,
                status=TransactionStatus.COMPLETED if success else TransactionStatus.FAILED,
                description=f"Standby Letter of Credit to {institution.name} - Ref: {reference}",
                eth_transaction_hash=message_id,
                institution_id=receiver_institution_id
            )
            
            # Store SWIFT-specific data in metadata
            metadata = {
                "swift": {
                    "message_type": "MT760",
                    "reference": reference,
                    "sender_bic": sender_credentials.bic,
                    "receiver_bic": receiver_credentials.bic,
                    "message_id": message_id,
                    "beneficiary": beneficiary,
                    "expiry_date": expiry_date.isoformat()
                }
            }
            transaction.tx_metadata_json = json.dumps(metadata)
            
            # Save to database
            db.session.add(transaction)
            db.session.commit()
            
            return True, f"Standby Letter of Credit sent successfully - Reference: {reference}", transaction
            
        except Exception as e:
            logger.error(f"Error creating standby letter of credit: {str(e)}")
            db.session.rollback()
            return False, f"Error: {str(e)}", None
    
    @staticmethod
    def create_swift_fund_transfer(
        user_id: int,
        receiver_institution_id: int,
        amount: float,
        currency: str,
        beneficiary_customer: str,  # Name and account of beneficiary
        ordering_customer: str = "",  # Sender details (optional)
        details_of_payment: str = "",  # Payment details/reason
        use_mt202: bool = False  # Whether to use MT202 (institution transfer) instead of MT103 (customer transfer)
    ) -> Tuple[bool, str, Optional[Transaction]]:
        """Create and send a SWIFT fund transfer via MT103/MT202"""
        try:
            # Get user and institution
            user = User.query.get(user_id)
            institution = FinancialInstitution.query.get(receiver_institution_id)
            
            if not user or not institution:
                return False, "User or financial institution not found", None
                
            # Get SWIFT credentials for sender and receiver
            sender_credentials = SwiftCredentials(
                bic=os.environ.get("NVC_SWIFT_BIC", "NVCGGB2L"),
                institution_name="NVC Global Banking"
            )
            
            receiver_credentials = SwiftCredentials.from_financial_institution(institution)
            
            if not receiver_credentials.is_valid():
                return False, f"Institution {institution.name} does not have valid SWIFT credentials", None
                
            # Generate a reference number for the transfer
            message_type = "MT202" if use_mt202 else "MT103"
            reference = f"TRF{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
            
            # Set defaults if not provided
            if not ordering_customer:
                ordering_customer = f"//{user.username}\n{user.email}"
                
            # Initialize SWIFT connection
            env = SwiftEnvironment(SWIFT_ENVIRONMENT) if isinstance(SWIFT_ENVIRONMENT, str) else SWIFT_ENVIRONMENT
            connection = SwiftConnection(sender_credentials, env)
            
            success = False
            message = ""
            message_id = None
            
            # Create and send appropriate message type
            if use_mt202:
                # MT202 - Financial Institution Transfer
                mt202 = MT202Message(
                    sender_bic=sender_credentials.bic,
                    receiver_bic=receiver_credentials.bic,
                    transaction_reference=reference,
                    related_reference=f"REL-{reference}",
                    amount=amount,
                    currency=currency,
                    value_date=datetime.now(),
                    sender_correspondent=sender_credentials.bic,
                    receiver_correspondent=receiver_credentials.bic,
                    details_of_payment=details_of_payment
                )
                success, message, message_id = connection.send_mt202(mt202)
                metadata_msg_type = "MT202"
            else:
                # MT103 - Customer Credit Transfer
                mt103 = MT103Message(
                    sender_bic=sender_credentials.bic,
                    receiver_bic=receiver_credentials.bic,
                    transaction_reference=reference,
                    amount=amount,
                    currency=currency,
                    value_date=datetime.now(),
                    ordering_customer=ordering_customer,
                    ordering_institution=sender_credentials.bic,
                    beneficiary_customer=beneficiary_customer,
                    beneficiary_institution=receiver_credentials.bic,
                    details_of_payment=details_of_payment
                )
                success, message, message_id = connection.send_mt103(mt103)
                metadata_msg_type = "MT103"
            
            if not success:
                return False, message, None
                
            # Create transaction record
            from models import TransactionType, TransactionStatus
            
            transaction = Transaction(
                user_id=user_id,
                transaction_id=f"SWIFT-{uuid.uuid4().hex[:8]}",
                transaction_type=TransactionType.SWIFT_TRANSFER,
                amount=amount,
                currency=currency,
                status=TransactionStatus.COMPLETED if success else TransactionStatus.FAILED,
                description=f"SWIFT {message_type} Transfer to {institution.name} - Ref: {reference}",
                eth_transaction_hash=message_id,
                institution_id=receiver_institution_id
            )
            
            # Store SWIFT-specific data in metadata
            metadata = {
                "swift": {
                    "message_type": metadata_msg_type,
                    "reference": reference,
                    "sender_bic": sender_credentials.bic,
                    "receiver_bic": receiver_credentials.bic,
                    "message_id": message_id,
                    "beneficiary": beneficiary_customer,
                    "details": details_of_payment
                }
            }
            transaction.tx_metadata_json = json.dumps(metadata)
            
            # Save to database
            db.session.add(transaction)
            db.session.commit()
            
            return True, f"SWIFT {message_type} Transfer initiated successfully - Reference: {reference}", transaction
            
        except Exception as e:
            logger.error(f"Error creating SWIFT fund transfer: {str(e)}")
            db.session.rollback()
            return False, f"Error: {str(e)}", None
            
    @staticmethod
    def send_free_format_message(
        user_id: int,
        receiver_institution_id: int,
        reference: str,
        narrative_text: str
    ) -> Tuple[bool, str, Optional[Transaction]]:
        """Send a free format MT799 message to a financial institution"""
        try:
            # Get user and institution
            user = User.query.get(user_id)
            institution = FinancialInstitution.query.get(receiver_institution_id)
            
            if not user or not institution:
                return False, "User or financial institution not found", None
                
            # Get SWIFT credentials for sender and receiver
            sender_credentials = SwiftCredentials(
                bic=os.environ.get("NVC_SWIFT_BIC", "NVCGGB2L"),
                institution_name="NVC Global Banking"
            )
            
            receiver_credentials = SwiftCredentials.from_financial_institution(institution)
            
            if not receiver_credentials.is_valid():
                return False, f"Institution {institution.name} does not have valid SWIFT credentials", None
                
            # Create MT799 message
            mt799 = MT799Message(
                sender_bic=sender_credentials.bic,
                receiver_bic=receiver_credentials.bic,
                reference=reference,
                narrative_text=narrative_text
            )
            
            # Initialize SWIFT connection and send message
            env = SwiftEnvironment(SWIFT_ENVIRONMENT) if isinstance(SWIFT_ENVIRONMENT, str) else SWIFT_ENVIRONMENT
            connection = SwiftConnection(sender_credentials, env)
            success, message, message_id = connection.send_mt799(mt799)
            
            if not success:
                return False, message, None
                
            # Create transaction record
            from models import TransactionType, TransactionStatus
            
            transaction = Transaction(
                user_id=user_id,
                transaction_id=f"SWIFT-{uuid.uuid4().hex[:8]}",
                transaction_type=TransactionType.SWIFT_MESSAGE,
                amount=0.0,  # No amount for a message
                currency="USD",  # Default currency
                status=TransactionStatus.COMPLETED if success else TransactionStatus.FAILED,
                description=f"SWIFT MT799 Message to {institution.name} - Ref: {reference}",
                eth_transaction_hash=message_id,
                institution_id=receiver_institution_id
            )
            
            # Store SWIFT-specific data in metadata
            metadata = {
                "swift": {
                    "message_type": "MT799",
                    "reference": reference,
                    "sender_bic": sender_credentials.bic,
                    "receiver_bic": receiver_credentials.bic,
                    "message_id": message_id,
                    "narrative": narrative_text[:100] + "..." if len(narrative_text) > 100 else narrative_text
                }
            }
            transaction.tx_metadata_json = json.dumps(metadata)
            
            # Save to database
            db.session.add(transaction)
            db.session.commit()
            
            return True, f"SWIFT MT799 Message sent successfully - Reference: {reference}", transaction
            
        except Exception as e:
            logger.error(f"Error sending SWIFT free format message: {str(e)}")
            db.session.rollback()
            return False, f"Error: {str(e)}", None
    
    @staticmethod
    def get_swift_message_status(transaction_id: str) -> Dict[str, Any]:
        """Check the status of any SWIFT message transaction"""
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            return {
                "success": False,
                "error": "Transaction not found"
            }
            
        try:
            # Check if this is a SWIFT transaction
            metadata = json.loads(transaction.tx_metadata_json or '{}')
            swift_data = metadata.get('swift', {})
            
            if not swift_data:
                return {
                    "success": False,
                    "error": "Not a SWIFT transaction"
                }
                
            # Initialize SWIFT connection
            sender_credentials = SwiftCredentials(
                bic=os.environ.get("NVC_SWIFT_BIC", "NVCGGB2L"),
                institution_name="NVC Global Banking"
            )
            
            env = SwiftEnvironment(SWIFT_ENVIRONMENT) if isinstance(SWIFT_ENVIRONMENT, str) else SWIFT_ENVIRONMENT
            connection = SwiftConnection(sender_credentials, env)
            
            # Get message status from SWIFT
            message_id = swift_data.get('message_id')
            if not message_id:
                return {
                    "success": False,
                    "error": "No SWIFT message ID found"
                }
                
            status_data = connection.get_message_status(message_id)
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "swift_reference": swift_data.get('reference', ''),
                "message_type": swift_data.get('message_type', ''),
                "status": status_data.get('status', 'unknown'),
                "details": status_data
            }
            
        except Exception as e:
            logger.error(f"Error getting SWIFT message status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
            
    # Alias for backward compatibility
    get_letter_of_credit_status = get_swift_message_status