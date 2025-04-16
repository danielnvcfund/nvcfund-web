"""
XRP Ledger Integration Module for NVC Banking Platform
Handles the connection to the XRP Ledger network, account management, and transaction processing.
"""

import os
import logging
import json
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple, List
import time

from xrpl.clients import JsonRpcClient
from xrpl.wallet import Wallet, generate_faucet_wallet
from xrpl.models.transactions import (
    Payment, 
    EscrowCreate, 
    EscrowFinish, 
    EscrowCancel, 
    CheckCreate, 
    CheckCash
)
from xrpl.models.requests import AccountInfo, AccountTx
from xrpl.models.requests.tx import Tx as TxRequest
from xrpl.models.response import Response
from xrpl.transaction import submit
# Use submit as send_reliable_submission for compatibility
from xrpl.utils import drops_to_xrp, xrp_to_drops
from xrpl.constants import CryptoAlgorithm

# Configure logger
logger = logging.getLogger(__name__)

# XRP Ledger network options
XRPL_NETWORKS = {
    "mainnet": "wss://xrplcluster.com",
    "testnet": "wss://s.altnet.rippletest.net:51233",
    "devnet": "wss://s.devnet.rippletest.net:51233"
}

# Default to testnet for development
DEFAULT_NETWORK = "testnet"

# Cached client connection
_xrpl_client = None

def init_xrpl_client(network: str = None) -> JsonRpcClient:
    """Initialize and return XRP Ledger client connection
    
    Args:
        network: The XRP Ledger network to connect to (mainnet, testnet, devnet)
        
    Returns:
        JsonRpcClient: The connected client
    """
    global _xrpl_client
    
    if _xrpl_client:
        return _xrpl_client
    
    if not network:
        network = os.environ.get('XRPL_NETWORK', DEFAULT_NETWORK)
    
    network_url = XRPL_NETWORKS.get(network.lower())
    if not network_url:
        raise ValueError(f"Unknown XRP Ledger network: {network}")
    
    try:
        logger.info(f"Connecting to XRP Ledger {network} at {network_url}")
        _xrpl_client = JsonRpcClient(network_url)
        return _xrpl_client
    except Exception as e:
        logger.error(f"Failed to connect to XRP Ledger network: {str(e)}")
        raise

def get_account_info(address: str) -> Dict[str, Any]:
    """Get account information from the XRP Ledger
    
    Args:
        address: The XRP Ledger account address
        
    Returns:
        Dict: Account information
    """
    client = init_xrpl_client()
    
    try:
        request = AccountInfo(account=address)
        response = client.request(request)
        
        if response.is_successful():
            return {
                'address': address,
                'balance': drops_to_xrp(response.result['account_data'].get('Balance', '0')),
                'sequence': response.result['account_data'].get('Sequence', 0),
                'flags': response.result['account_data'].get('Flags', 0)
            }
        else:
            logger.error(f"Failed to get account info: {response.result}")
            return {
                'address': address, 
                'error': response.result.get('error_message', 'Unknown error')
            }
    except Exception as e:
        logger.error(f"Error retrieving account info: {str(e)}")
        return {'address': address, 'error': str(e)}

def create_xrpl_wallet(seed: str = None, algorithm: str = "ed25519") -> Dict[str, Any]:
    """Create a new XRP Ledger wallet or load an existing one
    
    Args:
        seed: Optional seed to generate wallet from
        algorithm: The crypto algorithm ("ed25519" or "secp256k1")
    
    Returns:
        Dict: Wallet information
    """
    algo = CryptoAlgorithm.ED25519 if algorithm.lower() == "ed25519" else CryptoAlgorithm.SECP256K1
    
    try:
        if seed:
            wallet = Wallet(seed=seed, algorithm=algo)
            return {
                'address': wallet.classic_address,
                'public_key': wallet.public_key,
                'private_key': wallet.private_key,
                'seed': wallet.seed,
                'algorithm': algorithm
            }
        else:
            # Generate a new wallet
            client = init_xrpl_client()
            
            # Only works on test networks
            if os.environ.get('XRPL_NETWORK', DEFAULT_NETWORK) != "mainnet":
                try:
                    wallet = generate_faucet_wallet(client=client, algorithm=algo)
                    return {
                        'address': wallet.classic_address,
                        'public_key': wallet.public_key,
                        'private_key': wallet.private_key,
                        'seed': wallet.seed,
                        'algorithm': algorithm
                    }
                except Exception as fund_error:
                    logger.error(f"Error funding test wallet: {str(fund_error)}")
                    # Fall back to regular wallet creation
            
            # Create new wallet without funding
            wallet = Wallet.create(algorithm=algo)
            return {
                'address': wallet.classic_address,
                'public_key': wallet.public_key,
                'private_key': wallet.private_key,
                'seed': wallet.seed,
                'algorithm': algorithm,
                'note': "This wallet is not funded. On mainnet, you need to send at least 10 XRP to activate it."
            }
    except Exception as e:
        logger.error(f"Error creating XRP wallet: {str(e)}")
        return {'error': str(e)}

def send_xrp_payment(
    from_address: str, 
    to_address: str, 
    amount_in_xrp: float,
    seed: str,
    memo: str = None,
    tx_metadata: str = None,
    destination_tag: int = None
) -> Dict[str, Any]:
    """
    Send XRP from one account to another
    
    Args:
        from_address: Sender's XRP Ledger address
        to_address: Recipient's XRP Ledger address
        amount_in_xrp: Amount in XRP to send
        seed: Sender's seed for signing
        memo: Optional memo to include
        tx_metadata: Additional transaction metadata
        destination_tag: Optional destination tag for the recipient
        
    Returns:
        Dict: Transaction result with hash and status
    """
    client = init_xrpl_client()
    
    try:
        wallet = Wallet(seed=seed)
        if wallet.classic_address != from_address:
            return {'error': 'Provided seed does not match sender address'}
        
        # Convert XRP to drops
        amount_in_drops = xrp_to_drops(amount_in_xrp)
        
        # Build payment transaction
        payment = Payment(
            account=from_address,
            destination=to_address,
            amount=amount_in_drops
        )
        
        # Add destination tag if provided
        if destination_tag is not None:
            payment.destination_tag = destination_tag
        
        # Add memo if provided
        if memo:
            from xrpl.models.transactions.memo import Memo
            payment.memos = [Memo(memo_data=bytes(memo, "utf-8").hex())]
        
        # Submit payment reliably (with retry logic)
        try:
            response = submit(payment, wallet, client)
        except Exception as submit_error:
            logger.error(f"Payment submission error: {str(submit_error)}")
            return {'error': str(submit_error)}
        
        result = response.result
        
        if response.is_successful():
            # Store transaction details in platform's database
            tx_hash = result.get('hash', '')
            
            # Wait for validation if specified
            status = "SUBMITTED"
            validated = result.get('validated', False)
            if validated:
                status = "VALIDATED"
            
            return {
                'hash': tx_hash,
                'status': status,
                'ledger_index': result.get('ledger_index'),
                'amount': amount_in_xrp,
                'fee': drops_to_xrp(result.get('fee', '0')),
                'date': result.get('date'),
                'source': from_address,
                'destination': to_address,
                'metadata': tx_metadata,
            }
        else:
            error_msg = result.get('error_message', 'Unknown error')
            logger.error(f"Payment failed: {error_msg}")
            return {'error': error_msg}
    
    except Exception as e:
        logger.error(f"Error processing XRP payment: {str(e)}")
        return {'error': str(e)}

def get_transaction_status(tx_hash: str) -> Dict[str, Any]:
    """
    Get the status of an XRP Ledger transaction
    
    Args:
        tx_hash: XRP Ledger transaction hash
    
    Returns:
        Dict: Transaction details and status
    """
    client = init_xrpl_client()
    
    try:
        tx_request = TxRequest(transaction=tx_hash)
        response = client.request(tx_request)
        
        if response.is_successful():
            result = response.result
            validated = result.get('validated', False)
            status = "VALIDATED" if validated else "PENDING"
            
            # If validated, check meta field for outcome
            if validated:
                if result.get('meta', {}).get('TransactionResult') == "tesSUCCESS":
                    status = "CONFIRMED"
                else:
                    status = "FAILED"
                    
            return {
                'hash': tx_hash,
                'status': status,
                'ledger_index': result.get('ledger_index'),
                'type': result.get('TransactionType'),
                'account': result.get('Account'),
                'destination': result.get('Destination'),
                'amount': drops_to_xrp(result.get('Amount', '0')) if not isinstance(result.get('Amount'), dict) else result.get('Amount'),
                'fee': drops_to_xrp(result.get('Fee', '0')),
                'date': result.get('date'),
                'result': result.get('meta', {}).get('TransactionResult'),
            }
        else:
            error_msg = response.result.get('error_message', 'Unknown error')
            logger.error(f"Failed to fetch transaction {tx_hash}: {error_msg}")
            return {'hash': tx_hash, 'status': 'UNKNOWN', 'error': error_msg}
    
    except Exception as e:
        logger.error(f"Error checking transaction status: {str(e)}")
        return {'hash': tx_hash, 'status': 'ERROR', 'error': str(e)}

def get_account_transactions(address: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent transactions for an XRP Ledger account
    
    Args:
        address: XRP Ledger account address
        limit: Maximum number of transactions to retrieve
        
    Returns:
        List[Dict]: List of transaction details
    """
    client = init_xrpl_client()
    
    try:
        request = AccountTx(account=address, limit=limit)
        response = client.request(request)
        
        if response.is_successful():
            transactions = []
            for tx in response.result.get('transactions', []):
                tx_type = tx.get('tx', {}).get('TransactionType')
                
                # Extract basic transaction info
                transaction = {
                    'hash': tx.get('tx', {}).get('hash'),
                    'type': tx_type,
                    'date': tx.get('tx', {}).get('date'),
                    'ledger_index': tx.get('tx', {}).get('ledger_index'),
                    'validated': tx.get('validated', False)
                }
                
                # Add transaction-specific details
                if tx_type == 'Payment':
                    transaction.update({
                        'from': tx.get('tx', {}).get('Account'),
                        'to': tx.get('tx', {}).get('Destination'),
                        'amount': drops_to_xrp(tx.get('tx', {}).get('Amount', '0')) 
                                if not isinstance(tx.get('tx', {}).get('Amount'), dict) 
                                else tx.get('tx', {}).get('Amount'),
                        'fee': drops_to_xrp(tx.get('tx', {}).get('Fee', '0')),
                    })
                
                transactions.append(transaction)
            
            return transactions
        else:
            error_msg = response.result.get('error_message', 'Unknown error')
            logger.error(f"Failed to fetch account transactions: {error_msg}")
            return [{'error': error_msg}]
    
    except Exception as e:
        logger.error(f"Error retrieving account transactions: {str(e)}")
        return [{'error': str(e)}]

def create_escrow_payment(
    from_address: str,
    to_address: str,
    amount_in_xrp: float,
    release_time: int,  # Unix timestamp
    seed: str,
    cancel_after: int = None,  # Optional cancel-after time
    condition: str = None,  # Optional crypto-condition
    tx_metadata: str = None
) -> Dict[str, Any]:
    """
    Create an escrow payment on the XRP Ledger
    
    Args:
        from_address: Sender's XRP Ledger address
        to_address: Recipient's XRP Ledger address
        amount_in_xrp: Amount in XRP to escrow
        release_time: Time when the escrowed XRP can be released (Unix timestamp)
        seed: Sender's seed for signing
        cancel_after: Optional time when the escrow can be cancelled if not finished
        condition: Optional crypto-condition for the escrow
        tx_metadata: Additional transaction metadata
        
    Returns:
        Dict: Transaction result with hash, status and sequence number
    """
    client = init_xrpl_client()
    
    try:
        wallet = Wallet(seed=seed)
        if wallet.classic_address != from_address:
            return {'error': 'Provided seed does not match sender address'}
        
        # Convert XRP to drops
        amount_in_drops = xrp_to_drops(amount_in_xrp)
        
        # Build escrow create transaction
        escrow_tx = EscrowCreate(
            account=from_address,
            destination=to_address,
            amount=amount_in_drops,
            finish_after=release_time
        )
        
        # Add cancel_after if provided
        if cancel_after:
            escrow_tx.cancel_after = cancel_after
        
        # Add condition if provided
        if condition:
            escrow_tx.condition = condition
        
        # Submit transaction
        try:
            response = submit(escrow_tx, wallet, client)
        except Exception as submit_error:
            logger.error(f"Escrow submission error: {str(submit_error)}")
            return {'error': str(submit_error)}
        
        result = response.result
        
        if response.is_successful():
            tx_hash = result.get('hash', '')
            
            # We need the sequence number to identify this escrow later
            sequence = result.get('Sequence', 0)
            if not sequence:
                # Try to get it from the transaction itself
                sequence = escrow_tx.sequence
            
            return {
                'hash': tx_hash,
                'status': "SUBMITTED",
                'sequence': sequence,  # Important for finishing the escrow later
                'ledger_index': result.get('ledger_index'),
                'amount': amount_in_xrp,
                'fee': drops_to_xrp(result.get('fee', '0')),
                'date': result.get('date'),
                'source': from_address,
                'destination': to_address,
                'release_time': release_time,
                'cancel_after': cancel_after,
                'metadata': tx_metadata,
            }
        else:
            error_msg = result.get('error_message', 'Unknown error')
            logger.error(f"Escrow create failed: {error_msg}")
            return {'error': error_msg}
    
    except Exception as e:
        logger.error(f"Error creating escrow payment: {str(e)}")
        return {'error': str(e)}

def finish_escrow_payment(
    owner_address: str,  # Original sender of the escrow
    escrow_sequence: int,  # Sequence number of the EscrowCreate transaction
    signer_address: str,  # Account finishing the escrow (can be sender or recipient)
    signer_seed: str,
    fulfillment: str = None,  # Required if the escrow had a condition
    tx_metadata: str = None
) -> Dict[str, Any]:
    """
    Finish an escrow on the XRP Ledger to release funds to the recipient
    
    Args:
        owner_address: Address of the account that created the escrow
        escrow_sequence: Sequence number of the EscrowCreate transaction
        signer_address: Address of the account finishing the escrow
        signer_seed: Seed of the account finishing the escrow
        fulfillment: Optional fulfillment for crypto-condition (if required)
        tx_metadata: Additional transaction metadata
        
    Returns:
        Dict: Transaction result with hash and status
    """
    client = init_xrpl_client()
    
    try:
        wallet = Wallet(seed=signer_seed)
        if wallet.classic_address != signer_address:
            return {'error': 'Provided seed does not match signer address'}
        
        # Build escrow finish transaction
        escrow_finish = EscrowFinish(
            account=signer_address,
            owner=owner_address,
            offer_sequence=escrow_sequence
        )
        
        # Add fulfillment if provided
        if fulfillment:
            escrow_finish.fulfillment = fulfillment
        
        # Submit transaction
        try:
            response = submit(escrow_finish, wallet, client)
        except Exception as submit_error:
            logger.error(f"Escrow finish submission error: {str(submit_error)}")
            return {'error': str(submit_error)}
        
        result = response.result
        
        if response.is_successful():
            tx_hash = result.get('hash', '')
            
            return {
                'hash': tx_hash,
                'status': "SUBMITTED",
                'ledger_index': result.get('ledger_index'),
                'fee': drops_to_xrp(result.get('fee', '0')),
                'date': result.get('date'),
                'source': signer_address,
                'owner': owner_address,
                'sequence': escrow_sequence,
                'metadata': tx_metadata,
            }
        else:
            error_msg = result.get('error_message', 'Unknown error')
            logger.error(f"Escrow finish failed: {error_msg}")
            return {'error': error_msg}
    
    except Exception as e:
        logger.error(f"Error finishing escrow payment: {str(e)}")
        return {'error': str(e)}

def cancel_escrow_payment(
    owner_address: str,  # Original sender of the escrow
    escrow_sequence: int,  # Sequence number of the EscrowCreate transaction
    signer_address: str,  # Account cancelling the escrow
    signer_seed: str,
    tx_metadata: str = None
) -> Dict[str, Any]:
    """
    Cancel an escrow on the XRP Ledger to return funds to the sender
    
    Args:
        owner_address: Address of the account that created the escrow
        escrow_sequence: Sequence number of the EscrowCreate transaction
        signer_address: Address of the account cancelling the escrow
        signer_seed: Seed of the account cancelling the escrow
        tx_metadata: Additional transaction metadata
        
    Returns:
        Dict: Transaction result with hash and status
    """
    client = init_xrpl_client()
    
    try:
        wallet = Wallet(seed=signer_seed)
        if wallet.classic_address != signer_address:
            return {'error': 'Provided seed does not match signer address'}
        
        # Build escrow cancel transaction
        escrow_cancel = EscrowCancel(
            account=signer_address,
            owner=owner_address,
            offer_sequence=escrow_sequence
        )
        
        # Submit transaction
        try:
            response = submit(escrow_cancel, wallet, client)
        except Exception as submit_error:
            logger.error(f"Escrow cancel submission error: {str(submit_error)}")
            return {'error': str(submit_error)}
        
        result = response.result
        
        if response.is_successful():
            tx_hash = result.get('hash', '')
            
            return {
                'hash': tx_hash,
                'status': "SUBMITTED",
                'ledger_index': result.get('ledger_index'),
                'fee': drops_to_xrp(result.get('fee', '0')),
                'date': result.get('date'),
                'source': signer_address,
                'owner': owner_address,
                'sequence': escrow_sequence,
                'metadata': tx_metadata,
            }
        else:
            error_msg = result.get('error_message', 'Unknown error')
            logger.error(f"Escrow cancel failed: {error_msg}")
            return {'error': error_msg}
    
    except Exception as e:
        logger.error(f"Error cancelling escrow payment: {str(e)}")
        return {'error': str(e)}