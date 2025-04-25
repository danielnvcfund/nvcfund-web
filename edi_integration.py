"""
EDI Integration Module for NVC Banking Platform
Handles Electronic Data Interchange for bank transfers and financial data
"""
import os
import logging
import json
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any

from flask import current_app
import pysftp
import paramiko
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from models import User, Transaction, TransactionStatus, TransactionType, PaymentGateway

# Configure logger
logger = logging.getLogger(__name__)

# Global EDI service instance
edi_service = None

def init_app(app):
    """Initialize EDI integration with the app"""
    global edi_service
    edi_service = EdiService()
    return edi_service

class EdiTransactionType(Enum):
    """EDI transaction set types"""
    # X12 Transaction Sets
    X12_820 = "820"  # Payment Order/Remittance Advice
    X12_835 = "835"  # Healthcare Claim Payment/Advice
    X12_824 = "824"  # Application Advice
    X12_997 = "997"  # Functional Acknowledgment
    
    # EDIFACT Message Types
    EDIFACT_PAYORD = "PAYORD"  # Payment Order message
    EDIFACT_PAYMUL = "PAYMUL"  # Multiple Payment Order message
    EDIFACT_BANSTA = "BANSTA"  # Banking Status message
    
    # Custom Types
    ACH = "ACH"  # Automated Clearing House
    WIRE = "WIRE"  # Wire Transfer
    CUST_PAYMENT = "CUST_PAYMENT"  # Custom Payment Format

class EdiFormat(Enum):
    """EDI format standards"""
    X12 = "X12"
    EDIFACT = "EDIFACT"
    CUSTOM = "CUSTOM"

class EdiPartner:
    """EDI trading partner information"""
    def __init__(
        self, 
        partner_id: str, 
        name: str, 
        routing_number: Optional[str] = None,
        account_number: Optional[str] = None,
        edi_format: EdiFormat = EdiFormat.X12,
        connection_type: str = "SFTP",
        credentials: Optional[Dict[str, str]] = None,
        is_active: bool = True
    ):
        self.partner_id = partner_id
        self.name = name
        self.routing_number = routing_number
        self.account_number = account_number
        self.edi_format = edi_format
        self.connection_type = connection_type
        self.credentials = credentials or {}
        self.is_active = is_active
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "partner_id": self.partner_id,
            "name": self.name,
            "routing_number": self.routing_number,
            "account_number": self.account_number,
            "edi_format": self.edi_format.value,
            "connection_type": self.connection_type,
            "credentials": self.credentials,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EdiPartner':
        """Create from dictionary"""
        return cls(
            partner_id=data["partner_id"],
            name=data["name"],
            routing_number=data.get("routing_number"),
            account_number=data.get("account_number"),
            edi_format=EdiFormat(data["edi_format"]),
            connection_type=data["connection_type"],
            credentials=data.get("credentials", {}),
            is_active=data.get("is_active", True)
        )

class EdiTransaction:
    """Represents an EDI transaction with a financial institution"""
    def __init__(
        self,
        transaction_id: str,
        partner_id: str,
        transaction_type: EdiTransactionType,
        amount: float,
        currency: str,
        originator_info: Dict[str, str],
        beneficiary_info: Dict[str, str],
        reference_number: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        edi_format: EdiFormat = EdiFormat.X12,
        status: str = "pending",
        created_at: Optional[datetime] = None
    ):
        self.transaction_id = transaction_id
        self.partner_id = partner_id
        self.transaction_type = transaction_type
        self.amount = amount
        self.currency = currency
        self.originator_info = originator_info
        self.beneficiary_info = beneficiary_info
        self.reference_number = reference_number or transaction_id
        self.description = description
        self.metadata = metadata or {}
        self.edi_format = edi_format
        self.status = status
        self.created_at = created_at or datetime.now()
        self.edi_message = None  # Will hold the generated EDI message
        self.acknowledgment = None  # Will hold acknowledgment data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "transaction_id": self.transaction_id,
            "partner_id": self.partner_id,
            "transaction_type": self.transaction_type.value,
            "amount": self.amount,
            "currency": self.currency,
            "originator_info": self.originator_info,
            "beneficiary_info": self.beneficiary_info,
            "reference_number": self.reference_number,
            "description": self.description,
            "metadata": self.metadata,
            "edi_format": self.edi_format.value,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "edi_message": self.edi_message,
            "acknowledgment": self.acknowledgment
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EdiTransaction':
        """Create from dictionary"""
        transaction = cls(
            transaction_id=data["transaction_id"],
            partner_id=data["partner_id"],
            transaction_type=EdiTransactionType(data["transaction_type"]),
            amount=data["amount"],
            currency=data["currency"],
            originator_info=data["originator_info"],
            beneficiary_info=data["beneficiary_info"],
            reference_number=data.get("reference_number"),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
            edi_format=EdiFormat(data["edi_format"]),
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"])
        )
        transaction.edi_message = data.get("edi_message")
        transaction.acknowledgment = data.get("acknowledgment")
        return transaction

class EdiService:
    """Service for handling EDI transactions"""
    def __init__(self):
        self.partners = {}  # Dictionary to store EDI partners
        
        # Try to load partners from the config
        self._load_partners()
    
    def _load_partners(self):
        """Load EDI partners from configuration"""
        try:
            partners_file = os.path.join(os.path.dirname(__file__), 'config', 'edi_partners.json')
            if os.path.exists(partners_file):
                with open(partners_file, 'r') as f:
                    partners_data = json.load(f)
                    for partner_data in partners_data:
                        partner = EdiPartner.from_dict(partner_data)
                        self.partners[partner.partner_id] = partner
                    logger.info(f"Loaded {len(self.partners)} EDI partners from configuration")
            else:
                logger.warning("EDI partners configuration file not found")
        except Exception as e:
            logger.error(f"Error loading EDI partners: {str(e)}")
    
    def save_partners(self):
        """Save EDI partners to configuration"""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), 'config')
            os.makedirs(config_dir, exist_ok=True)
            
            partners_file = os.path.join(config_dir, 'edi_partners.json')
            with open(partners_file, 'w') as f:
                json.dump([p.to_dict() for p in self.partners.values()], f, indent=2)
            logger.info(f"Saved {len(self.partners)} EDI partners to configuration")
        except Exception as e:
            logger.error(f"Error saving EDI partners: {str(e)}")
    
    def add_partner(self, partner: EdiPartner):
        """Add or update an EDI partner"""
        self.partners[partner.partner_id] = partner
        self.save_partners()
    
    def get_partner(self, partner_id: str) -> Optional[EdiPartner]:
        """Get an EDI partner by ID"""
        return self.partners.get(partner_id)
    
    def list_partners(self) -> List[EdiPartner]:
        """List all EDI partners"""
        return list(self.partners.values())
    
    def delete_partner(self, partner_id: str) -> bool:
        """Delete an EDI partner"""
        if partner_id in self.partners:
            del self.partners[partner_id]
            self.save_partners()
            return True
        return False
    
    def create_edi_transaction(
        self, 
        partner_id: str,
        transaction_type: EdiTransactionType,
        amount: float,
        currency: str,
        originator_info: Dict[str, str],
        beneficiary_info: Dict[str, str],
        reference_number: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[EdiTransaction]:
        """Create a new EDI transaction"""
        # Check if partner exists
        partner = self.get_partner(partner_id)
        if not partner:
            logger.error(f"Partner ID {partner_id} not found")
            return None
        
        # Generate transaction ID
        from utils import generate_uuid
        transaction_id = generate_uuid()
        
        # Create the transaction
        transaction = EdiTransaction(
            transaction_id=transaction_id,
            partner_id=partner_id,
            transaction_type=transaction_type,
            amount=amount,
            currency=currency,
            originator_info=originator_info,
            beneficiary_info=beneficiary_info,
            reference_number=reference_number,
            description=description,
            metadata=metadata,
            edi_format=partner.edi_format
        )
        
        # Generate EDI message based on format
        self._generate_edi_message(transaction, partner)
        
        return transaction
    
    def _generate_edi_message(self, transaction: EdiTransaction, partner: EdiPartner):
        """Generate EDI message based on format and transaction type"""
        if transaction.edi_format == EdiFormat.X12:
            transaction.edi_message = self._generate_x12_message(transaction, partner)
        elif transaction.edi_format == EdiFormat.EDIFACT:
            transaction.edi_message = self._generate_edifact_message(transaction, partner)
        elif transaction.edi_format == EdiFormat.CUSTOM:
            transaction.edi_message = self._generate_custom_message(transaction, partner)
    
    def _generate_x12_message(self, transaction: EdiTransaction, partner: EdiPartner) -> str:
        """Generate X12 EDI message"""
        if transaction.transaction_type == EdiTransactionType.X12_820:
            return self._generate_x12_820_payment(transaction, partner)
        # Add other X12 transaction types as needed
        
        logger.warning(f"Unsupported X12 transaction type: {transaction.transaction_type}")
        return ""
    
    def _generate_x12_820_payment(self, transaction: EdiTransaction, partner: EdiPartner) -> str:
        """Generate X12 820 Payment Order/Remittance Advice"""
        # Get current date in EDI format
        current_date = datetime.now().strftime('%Y%m%d')
        current_time = datetime.now().strftime('%H%M')
        
        # Extract information
        originator = transaction.originator_info
        beneficiary = transaction.beneficiary_info
        
        # Basic X12 820 structure
        segments = []
        
        # ISA - Interchange Control Header
        isa = "ISA*00*          *00*          *ZZ*NVC_GLOBAL     *ZZ*" + \
              partner.partner_id.ljust(15) + "*" + current_date + "*" + current_time + \
              "*U*00401*000000001*0*P*>"
        segments.append(isa)
        
        # GS - Functional Group Header
        gs = f"GS*RA*NVC_GLOBAL*{partner.partner_id}*{current_date}*{current_time}*1*X*004010"
        segments.append(gs)
        
        # ST - Transaction Set Header
        st = f"ST*820*0001"
        segments.append(st)
        
        # BPR - Beginning Segment for Payment Order/Remittance Advice
        bpr = "BPR*C*" + str(transaction.amount) + "*C*ACH*CCD*" + \
              "01*" + originator.get('routing_number', '') + "*DA*" + \
              originator.get('account_number', '') + "*01*" + \
              beneficiary.get('routing_number', '') + "*DA*" + \
              beneficiary.get('account_number', '') + "*" + current_date
        segments.append(bpr)
        
        # TRN - Trace
        trn = f"TRN*1*{transaction.reference_number}*NVC_GLOBAL"
        segments.append(trn)
        
        # CUR - Currency
        cur = f"CUR*RB*{transaction.currency}"
        segments.append(cur)
        
        # N1 - Name - Originator
        n1_org = f"N1*PR*{originator.get('name', 'NVC Global')}*91*{originator.get('id', 'NVC001')}"
        segments.append(n1_org)
        
        # N1 - Name - Beneficiary
        n1_ben = f"N1*PE*{beneficiary.get('name', '')}*91*{beneficiary.get('id', '')}"
        segments.append(n1_ben)
        
        # RMR - Remittance Advice
        rmr = f"RMR*IV*{transaction.reference_number}**{transaction.amount}"
        segments.append(rmr)
        
        # SE - Transaction Set Trailer
        se = f"SE*{len(segments) - 2}*0001"
        segments.append(se)
        
        # GE - Functional Group Trailer
        ge = "GE*1*1"
        segments.append(ge)
        
        # IEA - Interchange Control Trailer
        iea = "IEA*1*000000001"
        segments.append(iea)
        
        # Join segments with segment terminator and return
        return "\n".join(segments)
    
    def _generate_edifact_message(self, transaction: EdiTransaction, partner: EdiPartner) -> str:
        """Generate EDIFACT message"""
        if transaction.transaction_type == EdiTransactionType.EDIFACT_PAYORD:
            return self._generate_edifact_payord(transaction, partner)
        # Add other EDIFACT message types as needed
        
        logger.warning(f"Unsupported EDIFACT message type: {transaction.transaction_type}")
        return ""
    
    def _generate_edifact_payord(self, transaction: EdiTransaction, partner: EdiPartner) -> str:
        """Generate EDIFACT PAYORD (Payment Order) message"""
        # Current date/time in EDIFACT format
        current_date = datetime.now().strftime('%y%m%d')
        current_time = datetime.now().strftime('%H%M')
        
        # Extract information
        originator = transaction.originator_info
        beneficiary = transaction.beneficiary_info
        
        # Basic EDIFACT PAYORD structure
        segments = []
        
        # UNB - Interchange Header
        unb = f"UNB+UNOA:2+NVC_GLOBAL:{current_date}:{current_time}+{partner.partner_id}:{current_date}:{current_time}+1+++++1'"
        segments.append(unb)
        
        # UNH - Message Header
        unh = f"UNH+1+PAYORD:D:96A:UN'"
        segments.append(unh)
        
        # BGM - Beginning of Message
        bgm = f"BGM+450+{transaction.reference_number}+9'"
        segments.append(bgm)
        
        # DTM - Date/Time/Period for document date
        dtm_doc = f"DTM+137:{current_date}:102'"
        segments.append(dtm_doc)
        
        # FII - Financial Institution Information for ordering customer
        fii_org = f"FII+MS+{originator.get('account_number', '')}:{originator.get('bank_id', '')}:25'"
        segments.append(fii_org)
        
        # NAD - Name and Address for ordering customer
        nad_org = f"NAD+MS++{originator.get('name', 'NVC Global')}'"
        segments.append(nad_org)
        
        # FII - Financial Institution Information for beneficiary
        fii_ben = f"FII+BE+{beneficiary.get('account_number', '')}:{beneficiary.get('bank_id', '')}:25'"
        segments.append(fii_ben)
        
        # NAD - Name and Address for beneficiary
        nad_ben = f"NAD+BE++{beneficiary.get('name', '')}'"
        segments.append(nad_ben)
        
        # MOA - Monetary Amount
        moa = f"MOA+9:{transaction.amount}'"
        segments.append(moa)
        
        # FTX - Free Text for payment details
        ftx = f"FTX+PMD+++{transaction.description or 'Payment'}'"
        segments.append(ftx)
        
        # UNT - Message Trailer
        unt = f"UNT+{len(segments) - 1}+1'"
        segments.append(unt)
        
        # UNZ - Interchange Trailer
        unz = f"UNZ+1+1'"
        segments.append(unz)
        
        # Join segments and return
        return "\n".join(segments)
    
    def _generate_custom_message(self, transaction: EdiTransaction, partner: EdiPartner) -> str:
        """Generate custom format message"""
        # Default to JSON format for custom messages
        custom_data = {
            "transaction_id": transaction.transaction_id,
            "reference_number": transaction.reference_number,
            "transaction_type": transaction.transaction_type.value,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "originator": transaction.originator_info,
            "beneficiary": transaction.beneficiary_info,
            "description": transaction.description,
            "created_at": transaction.created_at.isoformat(),
            "metadata": transaction.metadata
        }
        
        return json.dumps(custom_data, indent=2)
    
    def send_edi_transaction(self, transaction: EdiTransaction) -> bool:
        """Send EDI transaction to partner"""
        partner = self.get_partner(transaction.partner_id)
        if not partner:
            logger.error(f"Partner ID {transaction.partner_id} not found")
            return False
        
        if not transaction.edi_message:
            logger.error(f"No EDI message generated for transaction {transaction.transaction_id}")
            return False
        
        # Create temporary file with EDI message
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        file_name = f"{transaction.transaction_id}.edi"
        file_path = os.path.join(temp_dir, file_name)
        
        try:
            with open(file_path, 'w') as f:
                f.write(transaction.edi_message)
            
            # Send via configured connection type
            if partner.connection_type == "SFTP":
                return self._send_via_sftp(file_path, file_name, partner)
            # Add other connection types as needed
            
            logger.warning(f"Unsupported connection type: {partner.connection_type}")
            return False
        except Exception as e:
            logger.error(f"Error sending EDI transaction: {str(e)}")
            return False
        finally:
            # Clean up temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def _send_via_sftp(self, file_path: str, file_name: str, partner: EdiPartner) -> bool:
        """Send file via SFTP"""
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None  # Disable host key checking in development
        
        # Get SFTP credentials from partner
        host = partner.credentials.get('sftp_host')
        port = int(partner.credentials.get('sftp_port', 22))
        username = partner.credentials.get('sftp_username')
        password = partner.credentials.get('sftp_password')
        private_key = partner.credentials.get('sftp_private_key')
        
        if not host or not username:
            logger.error(f"Missing SFTP credentials for partner {partner.partner_id}")
            return False
        
        try:
            # Connect with password or private key
            if private_key:
                with pysftp.Connection(host=host, username=username, 
                                      private_key=private_key, port=port, cnopts=cnopts) as sftp:
                    self._upload_file(sftp, file_path, file_name, partner)
            else:
                with pysftp.Connection(host=host, username=username, 
                                      password=password, port=port, cnopts=cnopts) as sftp:
                    self._upload_file(sftp, file_path, file_name, partner)
            
            logger.info(f"Successfully sent EDI file {file_name} to {partner.name}")
            return True
        except Exception as e:
            logger.error(f"SFTP upload error: {str(e)}")
            return False
    
    def _upload_file(self, sftp, file_path: str, file_name: str, partner: EdiPartner):
        """Upload file via SFTP connection"""
        # Get remote directory from partner config or use default
        remote_dir = partner.credentials.get('sftp_remote_dir', '/incoming/')
        
        # Ensure the remote directory exists
        try:
            if not sftp.exists(remote_dir):
                sftp.makedirs(remote_dir)
        except:
            # If we can't create it, just try to use it anyway
            pass
        
        # Change to the remote directory
        try:
            sftp.cwd(remote_dir)
        except:
            # If we can't change to it, log warning but continue
            logger.warning(f"Could not change to directory {remote_dir}, using current directory")
        
        # Upload the file
        sftp.put(file_path, file_name)
    
    def process_edi_acknowledgment(self, partner_id: str, file_content: str) -> Dict[str, Any]:
        """Process EDI acknowledgment from partner"""
        partner = self.get_partner(partner_id)
        if not partner:
            logger.error(f"Partner ID {partner_id} not found")
            return {"success": False, "error": "Partner not found"}
        
        # Process based on format
        if partner.edi_format == EdiFormat.X12:
            return self._process_x12_acknowledgment(file_content)
        elif partner.edi_format == EdiFormat.EDIFACT:
            return self._process_edifact_acknowledgment(file_content)
        elif partner.edi_format == EdiFormat.CUSTOM:
            return self._process_custom_acknowledgment(file_content)
        
        return {"success": False, "error": "Unsupported EDI format"}
    
    def _process_x12_acknowledgment(self, file_content: str) -> Dict[str, Any]:
        """Process X12 acknowledgment (997)"""
        # Basic parsing of 997 functional acknowledgment
        lines = file_content.strip().split('\n')
        
        # Initialize result
        result = {
            "success": False,
            "format": "X12",
            "transactions": [],
            "errors": []
        }
        
        try:
            # Find ST segment for 997
            st_segment = None
            for line in lines:
                if line.startswith('ST*997*'):
                    st_segment = line
                    break
            
            if not st_segment:
                result["errors"].append("No 997 acknowledgment found")
                return result
            
            # Look for AK segments
            ack_segments = [line for line in lines if line.startswith('AK')]
            
            # Process each AK2/AK5 pair
            current_transaction = None
            for segment in ack_segments:
                if segment.startswith('AK2'):
                    # Start of new transaction acknowledgment
                    parts = segment.split('*')
                    if len(parts) >= 3:
                        transaction_set = parts[1]
                        transaction_number = parts[2]
                        current_transaction = {
                            "transaction_set": transaction_set,
                            "transaction_number": transaction_number,
                            "status": "unknown"
                        }
                        result["transactions"].append(current_transaction)
                
                elif segment.startswith('AK5') and current_transaction:
                    # Transaction acknowledgment status
                    parts = segment.split('*')
                    if len(parts) >= 2:
                        status_code = parts[1]
                        if status_code == 'A':
                            current_transaction["status"] = "accepted"
                        elif status_code == 'E':
                            current_transaction["status"] = "accepted_with_errors"
                        elif status_code == 'R':
                            current_transaction["status"] = "rejected"
                        else:
                            current_transaction["status"] = f"unknown_{status_code}"
            
            # Check if we found any transactions
            if not result["transactions"]:
                result["errors"].append("No transaction acknowledgments found")
                return result
            
            # If we got here, consider it a success
            result["success"] = True
            
            # Check if any transactions were rejected
            if any(t["status"] == "rejected" for t in result["transactions"]):
                result["success"] = False
                result["errors"].append("One or more transactions were rejected")
            
            return result
        
        except Exception as e:
            logger.error(f"Error processing X12 acknowledgment: {str(e)}")
            result["errors"].append(f"Processing error: {str(e)}")
            return result
    
    def _process_edifact_acknowledgment(self, file_content: str) -> Dict[str, Any]:
        """Process EDIFACT acknowledgment (CONTRL)"""
        # Basic parsing of CONTRL message
        lines = file_content.strip().split('\n')
        
        # Initialize result
        result = {
            "success": False,
            "format": "EDIFACT",
            "transactions": [],
            "errors": []
        }
        
        try:
            # Find UNH segment for CONTRL
            unh_segment = None
            for line in lines:
                if "UNH+" in line and "+CONTRL:" in line:
                    unh_segment = line
                    break
            
            if not unh_segment:
                result["errors"].append("No CONTRL message found")
                return result
            
            # Look for UCI segments (interchange response)
            uci_segments = [line for line in lines if "UCI+" in line]
            
            # Process each UCI segment
            for segment in uci_segments:
                # Basic parsing of UCI segment
                parts = segment.split('+')
                
                if len(parts) >= 3:
                    # Extract reference number and status
                    ref_number = parts[1]
                    status_part = parts[2]
                    
                    status = "unknown"
                    if status_part.startswith('1'):
                        status = "accepted"
                    elif status_part.startswith('4'):
                        status = "rejected"
                    elif status_part.startswith('7'):
                        status = "partially_accepted"
                    
                    transaction = {
                        "reference": ref_number,
                        "status": status
                    }
                    
                    result["transactions"].append(transaction)
            
            # Check if we found any transactions
            if not result["transactions"]:
                result["errors"].append("No transaction responses found")
                return result
            
            # If we got here, consider it a success
            result["success"] = True
            
            # Check if any transactions were rejected
            if any(t["status"] == "rejected" for t in result["transactions"]):
                result["success"] = False
                result["errors"].append("One or more transactions were rejected")
            
            return result
        
        except Exception as e:
            logger.error(f"Error processing EDIFACT acknowledgment: {str(e)}")
            result["errors"].append(f"Processing error: {str(e)}")
            return result
    
    def _process_custom_acknowledgment(self, file_content: str) -> Dict[str, Any]:
        """Process custom format acknowledgment"""
        # Try to parse as JSON first
        result = {
            "success": False,
            "format": "CUSTOM",
            "data": None,
            "errors": []
        }
        
        try:
            data = json.loads(file_content)
            result["data"] = data
            
            # Check for success indication in the JSON
            if isinstance(data, dict):
                if data.get('success') is True:
                    result["success"] = True
                
                if 'transactions' in data:
                    result["transactions"] = data['transactions']
                
                if 'errors' in data and data['errors']:
                    result["errors"].extend(data['errors'])
                    result["success"] = False
            
            return result
        except json.JSONDecodeError:
            # Not JSON, try simple text parsing
            result["data"] = file_content
            
            # Check for simple success/failure indicators
            if "SUCCESS" in file_content.upper():
                result["success"] = True
            elif "FAILURE" in file_content.upper() or "ERROR" in file_content.upper():
                result["success"] = False
                result["errors"].append("Failure indicated in response")
            else:
                result["errors"].append("Could not determine success/failure from response")
            
            return result

# Global instance for use throughout the application
edi_service = EdiService()

def init_app(app):
    """Initialize the EDI service with the Flask app"""
    # Register with the app if needed
    pass

# Functions to integrate with our transaction system

def create_edi_transaction_from_nvc_transaction(transaction, partner_id):
    """Create an EDI transaction from an NVC Banking Platform transaction"""
    # Get required information from the transaction
    user = User.query.get(transaction.user_id)
    if not user:
        logger.error(f"User not found for transaction {transaction.transaction_id}")
        return None
    
    # Map transaction types
    edi_transaction_type = None
    if transaction.transaction_type == TransactionType.BANK_TRANSFER:
        edi_transaction_type = EdiTransactionType.X12_820
    elif transaction.transaction_type == TransactionType.WIRE_TRANSFER:
        edi_transaction_type = EdiTransactionType.WIRE
    elif transaction.transaction_type == TransactionType.ACH_TRANSFER:
        edi_transaction_type = EdiTransactionType.ACH
    else:
        # Default to custom payment format
        edi_transaction_type = EdiTransactionType.CUST_PAYMENT
    
    # Get partner to determine format
    partner = edi_service.get_partner(partner_id)
    if not partner:
        logger.error(f"EDI partner {partner_id} not found")
        return None
    
    # Prepare originator info
    originator_info = {
        "name": "NVC Global Banking Platform",
        "id": "NVC001",
        "bank_id": "NVCBANK001",
        "routing_number": "021000021",  # Example routing number
        "account_number": "1234567890"  # Example account number
    }
    
    # Prepare beneficiary info from transaction recipient details
    beneficiary_info = {
        "name": transaction.recipient_name if hasattr(transaction, 'recipient_name') else "Recipient",
        "bank_name": transaction.bank_name if hasattr(transaction, 'bank_name') else "",
        "routing_number": transaction.routing_number if hasattr(transaction, 'routing_number') else "",
        "account_number": transaction.account_number if hasattr(transaction, 'account_number') else "",
        "address": transaction.recipient_address if hasattr(transaction, 'recipient_address') else ""
    }
    
    # Create EDI transaction
    edi_transaction = edi_service.create_edi_transaction(
        partner_id=partner_id,
        transaction_type=edi_transaction_type,
        amount=float(transaction.amount),
        currency=transaction.currency,
        originator_info=originator_info,
        beneficiary_info=beneficiary_info,
        reference_number=transaction.transaction_id,
        description=transaction.description,
        metadata={
            "nvc_transaction_id": transaction.transaction_id,
            "user_id": user.id,
            "username": user.username
        }
    )
    
    return edi_transaction

def process_edi_transaction(nvc_transaction, partner_id):
    """Process a transaction via EDI"""
    # Create EDI transaction
    edi_transaction = create_edi_transaction_from_nvc_transaction(nvc_transaction, partner_id)
    if not edi_transaction:
        logger.error(f"Failed to create EDI transaction for {nvc_transaction.transaction_id}")
        return False
    
    # Send the transaction
    success = edi_service.send_edi_transaction(edi_transaction)
    
    # Update the original transaction status
    if success:
        nvc_transaction.status = TransactionStatus.PROCESSING
        nvc_transaction.notes = nvc_transaction.notes or ""
        nvc_transaction.notes += f"\nEDI transaction {edi_transaction.transaction_id} sent successfully."
    else:
        nvc_transaction.status = TransactionStatus.FAILED
        nvc_transaction.notes = nvc_transaction.notes or ""
        nvc_transaction.notes += f"\nEDI transaction failed to send."
    
    # Save to database
    from app import db
    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"Error updating transaction status: {str(e)}")
        db.session.rollback()
    
    return success

# Helper functions for routes
def create_edi_transaction_from_nvc_transaction(transaction, partner_id):
    """Create an EDI transaction from a NVC Banking transaction"""
    if not transaction:
        logger.error("No transaction provided")
        return None
    
    if not edi_service:
        logger.error("EDI service not initialized")
        return None
    
    # Get partner
    partner = edi_service.get_partner(partner_id)
    if not partner:
        logger.error(f"Partner ID {partner_id} not found")
        return None
    
    # Determine transaction type
    if transaction.transaction_type == TransactionType.EDI_PAYMENT:
        edi_type = EdiTransactionType.CUST_PAYMENT
    elif transaction.transaction_type == TransactionType.EDI_ACH_TRANSFER:
        edi_type = EdiTransactionType.ACH
    elif transaction.transaction_type == TransactionType.EDI_WIRE_TRANSFER:
        edi_type = EdiTransactionType.WIRE
    else:
        # Default to a standard payment
        edi_type = EdiTransactionType.X12_820 if partner.edi_format == EdiFormat.X12 else \
                  EdiTransactionType.EDIFACT_PAYORD if partner.edi_format == EdiFormat.EDIFACT else \
                  EdiTransactionType.CUST_PAYMENT
    
    # Get user information
    user = User.query.get(transaction.user_id)
    
    # Construct originator info
    originator_info = {
        "name": user.organization or f"{user.first_name} {user.last_name}" if user else "NVC Banking Client",
        "id": f"NVC{user.id}" if user else "NVC000",
        "bank_id": "NVCBANK001",
        "routing_number": "021000021",  # Example routing number
        "account_number": "1234567890"  # Example account number
    }
    
    # Construct beneficiary info from transaction metadata if available
    metadata = {}
    if transaction.tx_metadata_json:
        try:
            metadata = json.loads(transaction.tx_metadata_json)
        except:
            pass
    
    beneficiary_info = {
        "name": metadata.get("recipient_name", partner.name),
        "bank_id": partner.partner_id,
        "routing_number": partner.routing_number or metadata.get("routing_number"),
        "account_number": partner.account_number or metadata.get("account_number")
    }
    
    # Create the EDI transaction
    edi_transaction = edi_service.create_edi_transaction(
        partner_id=partner_id,
        transaction_type=edi_type,
        amount=transaction.amount,
        currency=transaction.currency,
        originator_info=originator_info,
        beneficiary_info=beneficiary_info,
        reference_number=transaction.transaction_id,
        description=transaction.description or "Payment from NVC Banking Platform",
        metadata={"source_transaction_id": transaction.transaction_id}
    )
    
    return edi_transaction

def process_edi_transaction(transaction, partner_id):
    """Process a transaction via EDI"""
    if not transaction:
        logger.error("No transaction provided")
        return False
    
    if not edi_service:
        logger.error("EDI service not initialized")
        return False
    
    # Convert to EDI transaction
    edi_transaction = create_edi_transaction_from_nvc_transaction(transaction, partner_id)
    if not edi_transaction:
        return False
    
    # Get partner
    partner = edi_service.get_partner(partner_id)
    if not partner:
        logger.error(f"Partner ID {partner_id} not found")
        return False
    
    # Send the transaction
    result = edi_service.send_transaction(edi_transaction)
    
    if not result.get("success"):
        logger.error(f"Failed to send EDI transaction: {result.get('error')}")
        return False
    
    # Update the transaction with EDI processing info
    try:
        # Update transaction notes
        notes = transaction.description or ""
        if notes:
            notes += " | "
        notes += f"EDI transaction processed with partner {partner.name} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        transaction.description = notes
        
        # Update transaction metadata
        metadata = {}
        if transaction.tx_metadata_json:
            try:
                metadata = json.loads(transaction.tx_metadata_json)
            except:
                pass
        
        metadata["edi_processed"] = True
        metadata["edi_partner_id"] = partner_id
        metadata["edi_partner_name"] = partner.name
        metadata["edi_transaction_id"] = edi_transaction.transaction_id
        metadata["edi_format"] = edi_transaction.edi_format.value
        metadata["edi_processed_at"] = datetime.now().isoformat()
        metadata["edi_status"] = result.get("is_delivered", False)
        
        transaction.tx_metadata_json = json.dumps(metadata)
        
        # Save changes
        db.session.commit()
        
        logger.info(f"Transaction {transaction.transaction_id} processed via EDI with partner {partner.name}")
        return True
    except Exception as e:
        logger.error(f"Error updating transaction with EDI information: {str(e)}")
        return False