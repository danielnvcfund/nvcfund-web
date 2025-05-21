"""
SWIFT Message Integration Service
This module provides services for creating and processing SWIFT messages
including MT760 (Standby Letter of Credit) and related message types.
"""
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

class SwiftService:
    """Service for handling SWIFT message creation and processing"""
    
    @staticmethod
    def create_mt760_message(sblc):
        """
        Generate an MT760 message for a Standby Letter of Credit
        
        Args:
            sblc: StandbyLetterOfCredit object with all required details
            
        Returns:
            Formatted MT760 message as a string
        """
        try:
            # Format date as YYMMDD
            issue_date = sblc.issue_date.strftime("%y%m%d")
            expiry_date = sblc.expiry_date.strftime("%y%m%d")
            
            # Format amount with 2 decimal places
            amount = f"{float(sblc.amount):.2f}"
            
            # Start building the message
            message_lines = []
            
            # Message Header
            message_lines.append("{1:F01NVCGGLOBAXXX0000000000}")  # Sender's Basic Header
            message_lines.append("{2:I760BENEFICIARYXXX}")  # Application Header
            message_lines.append("{4:")  # Text Block Start
            
            # Mandatory Fields
            message_lines.append(f":27A:{sblc.reference_number}")  # Reference number
            message_lines.append(f":40A:IRREVOCABLE STANDBY")  # Form of documentary credit
            message_lines.append(f":20:{sblc.reference_number}")  # Sender's reference
            message_lines.append(f":31C:{issue_date}")  # Date of issue
            message_lines.append(f":31D:{expiry_date}{sblc.expiry_place[:35]}")  # Date and place of expiry
            message_lines.append(f":50:{sblc.applicant.name[:35]}")  # Applicant
            
            # Applicant address (max 4 lines of 35 chars)
            if sblc.applicant.primary_address():
                address_lines = sblc.applicant.primary_address().formatted().split("\n")
                for i, line in enumerate(address_lines[:4]):
                    if i == 0:
                        message_lines.append(f":50:{line[:35]}")
                    else:
                        message_lines.append(f":{line[:35]}")
            
            # Beneficiary information
            message_lines.append(f":59:{sblc.beneficiary_name[:35]}")  # Beneficiary name
            
            # Beneficiary address (max 4 lines)
            bene_address_lines = sblc.beneficiary_address.split("\n")
            for i, line in enumerate(bene_address_lines[:4]):
                message_lines.append(f":{line[:35]}")
            
            # Currency and amount
            message_lines.append(f":32B:{sblc.currency}{amount}")
            
            # Available with/by
            message_lines.append(":41A:AVAILABLE WITH ANY BANK BY NEGOTIATION")
            
            # Partial shipments / drawings
            if sblc.partial_drawings:
                message_lines.append(":43P:ALLOWED")
            else:
                message_lines.append(":43P:NOT ALLOWED")
                
            # Contract details
            message_lines.append(f":45A:{sblc.contract_name[:35]}")
            message_lines.append(f":45A:DATED {sblc.contract_date.strftime('%B %d, %Y')[:35]}")
            
            # Documents required
            message_lines.append(":46A:DOCUMENTS REQUIRED:")
            message_lines.append("1. BENEFICIARY'S SIGNED STATEMENT CERTIFYING THAT")
            message_lines.append("   THE APPLICANT HAS FAILED TO FULFILL CONTRACTUAL")
            message_lines.append("   OBLIGATIONS UNDER THE REFERENCED CONTRACT.")
            message_lines.append("2. COPY OF COMMERCIAL INVOICE.")
            message_lines.append("3. COPY OF TRANSPORT DOCUMENT.")
            
            # Additional conditions
            message_lines.append(":47A:ADDITIONAL CONDITIONS:")
            message_lines.append("THIS STANDBY LETTER OF CREDIT IS SUBJECT")
            message_lines.append("TO THE INTERNATIONAL STANDBY PRACTICES,")
            message_lines.append("INTERNATIONAL CHAMBER OF COMMERCE")
            message_lines.append("PUBLICATION NO. 590 (ISP98).")
            
            if sblc.special_conditions:
                # Add special conditions, breaking into 35-char lines
                special_lines = sblc.special_conditions.split("\n")
                for line in special_lines:
                    # Break line into chunks of 35 chars
                    chunks = [line[i:i+35] for i in range(0, len(line), 35)]
                    for chunk in chunks:
                        message_lines.append(f":{chunk}")
            
            # Charges
            message_lines.append(":71B:ALL BANKING CHARGES OUTSIDE THE COUNTRY")
            message_lines.append("OF THE ISSUING BANK ARE FOR BENEFICIARY'S")
            message_lines.append("ACCOUNT")
            
            # Period for presentation
            message_lines.append(":48:DOCUMENTS MUST BE PRESENTED WITHIN")
            message_lines.append("21 DAYS AFTER THE EVENT GIVING RISE")
            message_lines.append("TO THE DRAWING BUT NOT LATER THAN THE")
            message_lines.append("EXPIRY DATE OF THIS CREDIT.")
            
            # Confirmation instructions
            message_lines.append(":49:WITHOUT")
            
            # Issuing bank information
            message_lines.append(f":72:{sblc.issuing_bank.name[:35] if sblc.issuing_bank else 'NVC BANKING PLATFORM'}")
            
            # End of message
            message_lines.append("-}")  # Text Block End
            
            # Return the complete message
            return "\n".join(message_lines)
            
        except Exception as e:
            logger.error(f"Error creating MT760 message: {str(e)}")
            return f"ERROR: {str(e)}"
    
    @staticmethod
    def create_mt767_message(amendment):
        """
        Generate an MT767 message for a Letter of Credit Amendment
        
        Args:
            amendment: SBLCAmendment object with all required details
            
        Returns:
            Formatted MT767 message as a string
        """
        # Implementation for amendment messages
        pass
    
    @staticmethod
    def parse_mt760_message(message_text):
        """
        Parse an MT760 message and extract SBLC details
        
        Args:
            message_text: Raw MT760 message text
            
        Returns:
            Dictionary of extracted SBLC details
        """
        # Implementation for parsing incoming messages
        pass