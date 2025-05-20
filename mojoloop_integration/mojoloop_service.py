"""
Mojoloop Integration Service for NVC Banking Platform

This service acts as a bridge between the NVC Banking Platform and the Mojoloop network,
providing high-level functionality for processing transactions through Mojoloop.
"""

import os
import uuid
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

from mojoloop_integration.mojoloop_client import MojolloopClient
from app import db
from models import Transaction, PaymentGateway, User

# Configure logging
logger = logging.getLogger(__name__)

class MojolloopService:
    """Service for interacting with Mojoloop API and integrating with NVC Banking Platform"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the Mojoloop service
        
        Args:
            config: Configuration dictionary (optional)
        """
        self.config = config or {}
        self.base_url = self.config.get('base_url') or os.environ.get('MOJOLOOP_API_URL')
        self.client_id = self.config.get('client_id') or os.environ.get('MOJOLOOP_CLIENT_ID')
        self.client_secret = self.config.get('client_secret') or os.environ.get('MOJOLOOP_CLIENT_SECRET')
        self.dfsp_id = self.config.get('dfsp_id') or os.environ.get('MOJOLOOP_DFSP_ID')
        
        # Create Mojoloop client
        self.client = MojolloopClient(
            base_url=self.base_url,
            client_id=self.client_id,
            client_secret=self.client_secret,
            dfsp_id=self.dfsp_id
        )
    
    def get_transaction_type_code(self, transaction_type: str) -> str:
        """
        Map NVC transaction types to Mojoloop transaction type codes
        
        Args:
            transaction_type: NVC transaction type
            
        Returns:
            Mojoloop transaction type code
        """
        type_mapping = {
            'payment': 'PAYMENT',
            'transfer': 'TRANSFER',
            'deposit': 'DEPOSIT',
            'withdrawal': 'WITHDRAWAL',
            'refund': 'REFUND',
            'reversal': 'REVERSAL',
        }
        
        return type_mapping.get(transaction_type.lower(), 'TRANSFER')
    
    def get_id_type(self, identifier: str) -> str:
        """
        Determine the type of identifier based on its format
        
        Args:
            identifier: The party identifier
            
        Returns:
            Identifier type (MSISDN, IBAN, etc.)
        """
        if identifier.startswith('+') or identifier.isdigit():
            return 'MSISDN'
        elif identifier.startswith('IBAN'):
            return 'IBAN'
        elif '@' in identifier:
            return 'EMAIL'
        else:
            return 'ACCOUNT_ID'
    
    def format_amount(self, amount: Union[float, int], currency: str) -> Dict[str, Any]:
        """
        Format an amount according to Mojoloop requirements
        
        Args:
            amount: Transaction amount
            currency: Currency code
            
        Returns:
            Formatted amount object
        """
        return {
            'amount': str(amount),
            'currency': currency
        }
    
    def create_mojoloop_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a transaction in the Mojoloop network
        
        Args:
            transaction_data: Transaction details from NVC Banking Platform
            
        Returns:
            Processed transaction details including Mojoloop references
        """
        # Extract and validate required fields
        payer_identifier = transaction_data.get('payer_identifier')
        payee_identifier = transaction_data.get('payee_identifier')
        amount = transaction_data.get('amount')
        currency = transaction_data.get('currency', 'USD')
        transaction_type = transaction_data.get('transaction_type', 'transfer')
        
        if not all([payer_identifier, payee_identifier, amount]):
            raise ValueError("Missing required transaction data: payer, payee, or amount")
        
        # Format transaction for Mojoloop
        mojoloop_transaction = {
            'transactionId': transaction_data.get('transaction_id', str(uuid.uuid4())),
            'payer': {
                'partyIdInfo': {
                    'partyIdType': self.get_id_type(payer_identifier),
                    'partyId': payer_identifier,
                    'fspId': self.dfsp_id
                }
            },
            'payee': {
                'partyIdInfo': {
                    'partyIdType': self.get_id_type(payee_identifier),
                    'partyId': payee_identifier
                }
            },
            'amount': self.format_amount(amount, currency),
            'transactionType': {
                'scenario': self.get_transaction_type_code(transaction_type),
                'initiator': 'PAYER',
                'initiatorType': 'CONSUMER'
            },
            'note': transaction_data.get('note', f'NVC Banking Transaction {transaction_data.get("transaction_id", "")}')
        }
        
        # Process the transaction via Mojoloop client
        result = self.client.create_transaction(mojoloop_transaction)
        
        # Enrich result with additional information
        result.update({
            'nvcTransactionId': transaction_data.get('transaction_id'),
            'processingTimestamp': datetime.utcnow().isoformat(),
            'originalRequest': transaction_data
        })
        
        return result
    
    def save_transaction_to_database(self, transaction_result: Dict[str, Any], user_id: int = None) -> Transaction:
        """
        Save the Mojoloop transaction result to the NVC Banking database
        
        Args:
            transaction_result: Processed transaction result from Mojoloop
            user_id: ID of the user initiating the transaction (optional)
            
        Returns:
            Saved Transaction object
        """
        try:
            # Find or create the Mojoloop payment gateway
            gateway = PaymentGateway.query.filter_by(name='Mojoloop').first()
            if not gateway:
                from models import PaymentGatewayType
                gateway = PaymentGateway()
                gateway.name = 'Mojoloop'
                gateway.description = 'Interoperable digital payments via Mojoloop'
                gateway.gateway_type = PaymentGatewayType.INTEROPERABLE_PAYMENT
                gateway.is_active = True
                gateway.api_endpoint = os.environ.get('MOJOLOOP_API_URL', '')
                db.session.add(gateway)
                db.session.flush()
            
            # Create transaction record
            transaction = Transaction()
            transaction.transaction_id = transaction_result.get('transactionId')
            transaction.external_id = transaction_result.get('transferId')
            transaction.payment_gateway_id = gateway.id
            transaction.user_id = user_id if user_id is not None else None
            transaction.amount = float(transaction_result.get('amount', {}).get('amount', 0))
            transaction.currency = transaction_result.get('amount', {}).get('currency', 'USD')
            transaction.status = transaction_result.get('status', 'PENDING')
            transaction.gateway_response = json.dumps(transaction_result)
            transaction.created_at = datetime.utcnow()
            transaction.payer_info = json.dumps(transaction_result.get('payerDetails', {}))
            transaction.payee_info = json.dumps(transaction_result.get('payeeDetails', {}))
            transaction.description = transaction_result.get('note', '')
            
            db.session.add(transaction)
            db.session.commit()
            
            return transaction
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving Mojoloop transaction to database: {str(e)}")
            raise
    
    def get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get the status of a transaction from Mojoloop
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Transaction status details
        """
        # First check our database
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found in database")
        
        # If we have an external ID, check with Mojoloop
        if transaction.external_id:
            try:
                mojoloop_status = self.client.get_transfer_status(transaction.external_id)
                
                # Update our database with the latest status
                if mojoloop_status.get('status') != transaction.status:
                    transaction.status = mojoloop_status.get('status')
                    transaction.updated_at = datetime.utcnow()
                    transaction.gateway_response = json.dumps(mojoloop_status)
                    db.session.commit()
                
                return {
                    'transaction_id': transaction.transaction_id,
                    'external_id': transaction.external_id,
                    'status': transaction.status,
                    'amount': transaction.amount,
                    'currency': transaction.currency,
                    'created_at': transaction.created_at.isoformat() if transaction.created_at else None,
                    'updated_at': transaction.updated_at.isoformat() if transaction.updated_at else None,
                    'mojoloop_details': mojoloop_status
                }
            
            except Exception as e:
                logger.warning(f"Failed to get Mojoloop status for transaction {transaction_id}: {str(e)}")
                # Return local information if Mojoloop is unreachable
                return {
                    'transaction_id': transaction.transaction_id,
                    'external_id': transaction.external_id,
                    'status': transaction.status,
                    'amount': transaction.amount,
                    'currency': transaction.currency,
                    'created_at': transaction.created_at.isoformat() if transaction.created_at else None,
                    'updated_at': transaction.updated_at.isoformat() if transaction.updated_at else None,
                    'error': str(e)
                }
        
        # If no external ID, just return local information
        return {
            'transaction_id': transaction.transaction_id,
            'status': transaction.status,
            'amount': transaction.amount,
            'currency': transaction.currency,
            'created_at': transaction.created_at.isoformat() if transaction.created_at else None,
            'updated_at': transaction.updated_at.isoformat() if transaction.updated_at else None
        }
    
    def create_and_process_transaction(self, transaction_data: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        """
        Create, process, and save a transaction through Mojoloop
        
        Args:
            transaction_data: Transaction details
            user_id: User ID (optional)
            
        Returns:
            Processed and saved transaction details
        """
        # Create the transaction in Mojoloop
        result = self.create_mojoloop_transaction(transaction_data)
        
        # Save to database
        transaction = self.save_transaction_to_database(result, user_id)
        
        # Return enriched result
        return {
            'transaction_id': transaction.transaction_id,
            'external_id': transaction.external_id,
            'status': transaction.status,
            'amount': transaction.amount,
            'currency': transaction.currency,
            'created_at': transaction.created_at.isoformat() if transaction.created_at else None,
            'mojoloop_details': result
        }