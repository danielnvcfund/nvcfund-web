"""
API Bridge for NVCPlatform PHP Banking Software Integration
This module provides an interface for connecting the PHP banking software
with the NVC Global Payment Gateway.
"""

import os
import json
import logging
import requests
import hmac
import hashlib
import time
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

from models import db, User, PaymentGateway, Transaction, TransactionStatus, UserRole
from payment_gateways import get_gateway_handler, get_gateway_by_type, PaymentGatewayType
from auth import api_key_required, jwt_required

logger = logging.getLogger(__name__)

# Create blueprint for PHP integration API
php_bridge = Blueprint('php_bridge', __name__)

# Exempt API routes from CSRF protection
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

@php_bridge.before_request
def disable_csrf():
    # Disable CSRF for all routes in this blueprint
    # This is safe because we're using API key and signature verification instead
    csrf.exempt(php_bridge)

# Constants
API_TIMEOUT = 30  # seconds
SHARED_SECRET = "php_bridge_shared_secret"  # Shared secret for signature verification


def verify_nvcplatform_signature(request_data, signature, shared_secret):
    """
    Verify the signature from the PHP platform
    
    Args:
        request_data (dict): The request data
        signature (str): The signature to verify
        shared_secret (str): The shared secret key
        
    Returns:
        bool: Whether the signature is valid
    """
    # Sort the request data by key to ensure consistent ordering
    sorted_data = {k: request_data[k] for k in sorted(request_data.keys())}
    
    # Create a string from the sorted data
    data_string = '&'.join([f"{k}={v}" for k, v in sorted_data.items()])
    
    # Generate the expected signature using HMAC-SHA256
    expected_signature = hmac.new(
        shared_secret.encode(),
        data_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare the signatures
    return hmac.compare_digest(expected_signature, signature)


@php_bridge.route('/account/sync', methods=['POST'])
@api_key_required
def sync_accounts(user):
    """
    Synchronize user accounts from PHP banking software
    
    Expected format:
    {
        "accounts": [
            {
                "username": "user123",
                "email": "user@example.com",
                "account_number": "ACC12345678",
                "customer_id": "CID9876543",
                "account_type": "savings",
                "balance": 1000.00,
                "currency": "USD",
                "status": "active"
            },
            ...
        ],
        "signature": "hmac_signature"
    }
    """
    # Get request data
    data = request.json
    
    if not data or 'accounts' not in data:
        return jsonify({"success": False, "error": "Missing account data"}), 400
    
    # Verify signature if provided
    if 'signature' in data:
        # Extract signature and verify with our constant shared secret
        signature = data.pop('signature')
        if not verify_nvcplatform_signature(data, signature, SHARED_SECRET):
            return jsonify({"success": False, "error": "Invalid signature"}), 401
    
    # Process account data
    accounts = data['accounts']
    results = {
        "success": True,
        "processed": 0,
        "created": 0,
        "updated": 0,
        "errors": []
    }
    
    try:
        for account in accounts:
            # Extract account data
            username = account.get('username')
            email = account.get('email')
            customer_id = account.get('customer_id')
            account_number = account.get('account_number')
            account_type = account.get('account_type')
            currency = account.get('currency')
            status = account.get('status', 'active')
            
            # Validate required fields
            if not (username and email and customer_id and account_number):
                results['errors'].append(f"Missing required fields for account: {account}")
                continue
            
            # Check if user exists by external customer ID
            user = User.query.filter_by(external_customer_id=customer_id).first()
            
            if user:
                # Update existing user
                user.external_account_id = account_number
                user.external_account_type = account_type
                user.external_account_currency = currency
                user.external_account_status = status
                user.last_sync = datetime.utcnow()
                
                # Update email if changed
                if user.email != email:
                    user.email = email
                
                # Only update username if it's not already in use by another user
                if user.username != username:
                    existing_user = User.query.filter_by(username=username).first()
                    if not existing_user or existing_user.id == user.id:
                        user.username = username
                
                results['updated'] += 1
            else:
                # Check if user exists by email
                user = User.query.filter_by(email=email).first()
                
                if user:
                    # Link existing user to external account
                    user.external_customer_id = customer_id
                    user.external_account_id = account_number
                    user.external_account_type = account_type
                    user.external_account_currency = currency
                    user.external_account_status = status
                    user.last_sync = datetime.utcnow()
                    results['updated'] += 1
                else:
                    # Create new user
                    # Generate a secure random password (will be reset by user)
                    temp_password = hashlib.sha256(os.urandom(32)).hexdigest()[:12]
                    
                    new_user = User(
                        username=username,
                        email=email,
                        role=UserRole.USER,
                        external_customer_id=customer_id,
                        external_account_id=account_number,
                        external_account_type=account_type,
                        external_account_currency=currency,
                        external_account_status=status,
                        last_sync=datetime.utcnow(),
                        is_active=status == 'active'
                    )
                    new_user.set_password(temp_password)
                    
                    db.session.add(new_user)
                    results['created'] += 1
            
            results['processed'] += 1
        
        # Commit all changes
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing accounts: {str(e)}")
        results['success'] = False
        results['error'] = str(e)
    
    return jsonify(results)


@php_bridge.route('/transaction/sync', methods=['POST'])
@api_key_required
def sync_transactions(user):
    """
    Synchronize transactions from PHP banking software
    
    Expected format:
    {
        "transactions": [
            {
                "transaction_id": "TXN123456789",
                "customer_id": "CID9876543",
                "account_number": "ACC12345678",
                "amount": 100.00,
                "currency": "USD",
                "description": "Payment for services",
                "status": "completed",
                "transaction_type": "payment",
                "created_at": "2025-04-18T08:30:00Z"
            },
            ...
        ],
        "signature": "hmac_signature"
    }
    """
    # Get request data
    data = request.json
    
    if not data or 'transactions' not in data:
        return jsonify({"success": False, "error": "Missing transaction data"}), 400
    
    # Verify signature if provided
    if 'signature' in data:
        # Extract signature and verify with our constant shared secret
        signature = data.pop('signature')
        if not verify_nvcplatform_signature(data, signature, SHARED_SECRET):
            return jsonify({"success": False, "error": "Invalid signature"}), 401
    
    # Process transaction data
    transactions = data['transactions']
    results = {
        "success": True,
        "processed": 0,
        "created": 0,
        "updated": 0,
        "errors": []
    }
    
    for txn in transactions:
        try:
            # Find user by external customer ID
            user = User.query.filter_by(external_customer_id=txn['customer_id']).first()
            
            if not user:
                results["errors"].append({
                    "transaction": txn.get('transaction_id'),
                    "error": f"User with customer_id {txn['customer_id']} not found"
                })
                continue
            
            # Check if transaction exists
            transaction = Transaction.query.filter_by(
                external_id=txn['transaction_id']
            ).first()
            
            # Map PHP transaction status to our status
            status_mapping = {
                'pending': TransactionStatus.PENDING,
                'processing': TransactionStatus.PROCESSING,
                'completed': TransactionStatus.COMPLETED,
                'failed': TransactionStatus.FAILED,
                'refunded': TransactionStatus.REFUNDED,
                'cancelled': TransactionStatus.FAILED
            }
            
            transaction_status = status_mapping.get(
                txn['status'].lower(), 
                TransactionStatus.PENDING
            )
            
            if transaction:
                # Update existing transaction
                transaction.amount = txn['amount']
                transaction.currency = txn['currency']
                transaction.description = txn['description']
                transaction.status = transaction_status
                
                db.session.commit()
                results["updated"] += 1
            else:
                # Create new transaction
                new_transaction = Transaction(
                    transaction_id=f"NVC-SYNC-{int(time.time())}-{user.id}",
                    external_id=txn['transaction_id'],
                    user_id=user.id,
                    amount=txn['amount'],
                    currency=txn['currency'],
                    description=f"Imported: {txn['description']}",
                    status=transaction_status,
                    transaction_type=txn['transaction_type'].upper(),
                    gateway_id=get_gateway_by_type(PaymentGatewayType.NVC_GLOBAL).id if get_gateway_by_type(PaymentGatewayType.NVC_GLOBAL) else None,
                    created_at=datetime.fromisoformat(txn['created_at'].replace('Z', '+00:00'))
                )
                
                db.session.add(new_transaction)
                db.session.commit()
                results["created"] += 1
            
            results["processed"] += 1
            
        except Exception as e:
            logger.error(f"Error syncing transaction {txn.get('transaction_id')}: {str(e)}")
            results["errors"].append({
                "transaction": txn.get('transaction_id'),
                "error": str(e)
            })
    
    return jsonify(results), 200


@php_bridge.route('/payment/process', methods=['POST'])
@api_key_required
def process_payment(user):
    """
    Process a payment from PHP banking software through NVC Global
    
    Expected format:
    {
        "customer_id": "CID9876543",
        "amount": 100.00,
        "currency": "USD",
        "description": "Payment for services",
        "recipient": "recipient@example.com",
        "callback_url": "https://phpbanking.example.com/callback",
        "metadata": {
            "invoice_id": "INV12345",
            "product_id": "PROD678"
        },
        "signature": "hmac_signature"
    }
    """
    # Get request data
    data = request.json
    
    if not data:
        return jsonify({"success": False, "error": "Missing payment data"}), 400
    
    required_fields = ['customer_id', 'amount', 'currency', 'description']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return jsonify({
            "success": False, 
            "error": f"Missing required fields: {', '.join(missing_fields)}"
        }), 400
    
    # Verify signature if provided
    if 'signature' in data:
        # Extract signature and verify with our constant shared secret
        signature = data.pop('signature')
        if not verify_nvcplatform_signature(data, signature, SHARED_SECRET):
            return jsonify({"success": False, "error": "Invalid signature"}), 401
    
    # Find user by external customer ID
    user = User.query.filter_by(external_customer_id=data['customer_id']).first()
    
    if not user:
        return jsonify({
            "success": False, 
            "error": f"User with customer_id {data['customer_id']} not found"
        }), 404
    
    # Get NVC Global gateway handler
    nvc_gateway = get_gateway_by_type(PaymentGatewayType.NVC_GLOBAL)
    if not nvc_gateway:
        return jsonify({"success": False, "error": "NVC Global gateway not configured"}), 500
    
    gateway_handler = get_gateway_handler(nvc_gateway.id)
    if not gateway_handler:
        return jsonify({"success": False, "error": "Failed to get NVC Global gateway handler"}), 500
    
    # Process payment
    metadata = data.get('metadata', {})
    metadata['php_bridge'] = True
    metadata['callback_url'] = data.get('callback_url')
    
    result = gateway_handler.process_payment(
        amount=float(data['amount']),
        currency=data['currency'],
        description=data['description'],
        user_id=user.id,
        metadata=metadata
    )
    
    if result.get('success'):
        return jsonify({
            "success": True,
            "message": "Payment processed successfully",
            "transaction_id": result.get('transaction_id'),
            "status": "pending",
            "gateway_reference": result.get('gateway_reference')
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": result.get('error', 'Unknown error processing payment')
        }), 500


@php_bridge.route('/payment/status/<transaction_id>', methods=['GET'])
@api_key_required
def check_payment_status(user, transaction_id):
    """
    Check the status of a payment processed through NVC Global
    
    Args:
        transaction_id (str): The transaction ID to check
        
    Returns:
        JSON response with transaction status
    """
    if not transaction_id:
        return jsonify({"success": False, "error": "Missing transaction ID"}), 400
    
    # Find transaction by ID or external ID
    transaction = Transaction.query.filter(
        (Transaction.transaction_id == transaction_id) | 
        (Transaction.external_id == transaction_id)
    ).first()
    
    if not transaction:
        return jsonify({
            "success": False,
            "error": f"Transaction {transaction_id} not found"
        }), 404
    
    # Map our status to PHP platform status
    status_mapping = {
        TransactionStatus.PENDING: "pending",
        TransactionStatus.PROCESSING: "processing",
        TransactionStatus.COMPLETED: "completed",
        TransactionStatus.FAILED: "failed",
        TransactionStatus.REFUNDED: "refunded"
    }
    
    # Get any metadata as a dictionary
    metadata = {}
    if transaction.tx_metadata_json:
        try:
            metadata = json.loads(transaction.tx_metadata_json)
        except:
            metadata = {}
    
    # Get user information
    user = User.query.get(transaction.user_id)
    
    # Build response
    response = {
        "success": True,
        "transaction_id": transaction.transaction_id,
        "external_id": transaction.external_id,
        "amount": float(transaction.amount),
        "currency": transaction.currency,
        "status": status_mapping.get(transaction.status, "unknown"),
        "description": transaction.description,
        "created_at": transaction.created_at.isoformat(),
        "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
        "metadata": metadata
    }
    
    # Add user information if available
    if user:
        response["user"] = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "external_customer_id": user.external_customer_id,
            "external_account_id": user.external_account_id
        }
    
    # Try to get more detailed status from gateway if available
    if transaction.gateway_id:
        gateway_handler = get_gateway_handler(transaction.gateway_id)
        if gateway_handler:
            try:
                result = gateway_handler.check_payment_status(transaction.transaction_id)
                if result.get('success'):
                    # Update response with gateway specific data
                    response["gateway_status"] = result.get('status')
                    response["gateway_data"] = result.get('gateway_data', {})
            except Exception as e:
                logger.warning(f"Error getting gateway status: {str(e)}")
    
    return jsonify(response), 200


@php_bridge.route('/payment/callback', methods=['POST'])
def payment_callback():
    """
    Receive callback from NVC Global and forward to PHP application
    """
    # Get request data
    data = request.json
    
    if not data:
        return jsonify({"success": False, "error": "Missing callback data"}), 400
    
    # Get transaction ID
    transaction_id = data.get('transaction_id')
    if not transaction_id:
        return jsonify({"success": False, "error": "Missing transaction_id"}), 400
    
    # Get the transaction
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    
    if not transaction:
        return jsonify({"success": False, "error": "Transaction not found"}), 404
    
    # Get transaction metadata
    try:
        metadata = json.loads(transaction.tx_metadata_json) if transaction.tx_metadata_json else {}
    except:
        metadata = {}
    
    # Check if this is a transaction initiated through the PHP bridge
    if not metadata.get('php_bridge'):
        # Not a PHP bridge transaction, just acknowledge
        return jsonify({"success": True}), 200
    
    # Get callback URL
    callback_url = metadata.get('callback_url')
    if not callback_url:
        logger.warning(f"No callback URL for PHP bridge transaction {transaction_id}")
        return jsonify({"success": True}), 200
    
    # Forward callback to PHP application
    try:
        # Use our constant shared secret for signature generation
        shared_secret = SHARED_SECRET
        
        # Prepare callback data
        callback_data = {
            "transaction_id": transaction.transaction_id,
            "external_id": transaction.external_id,
            "status": transaction.status.value,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "description": transaction.description,
            "created_at": transaction.created_at.isoformat(),
            "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
            "metadata": metadata.get('metadata', {})
        }
        
        # Add signature if shared secret is available
        if shared_secret:
            # Sort the data by key
            sorted_data = {k: callback_data[k] for k in sorted(callback_data.keys())}
            
            # Create a string from the sorted data
            data_string = '&'.join([f"{k}={v}" for k, v in sorted_data.items()])
            
            # Generate signature
            signature = hmac.new(
                shared_secret.encode(),
                data_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            callback_data['signature'] = signature
        
        # Send callback to PHP application
        response = requests.post(
            callback_url,
            json=callback_data,
            headers={'Content-Type': 'application/json'},
            timeout=API_TIMEOUT
        )
        
        # Check response
        if response.status_code == 200:
            logger.info(f"Successfully forwarded callback for transaction {transaction_id}")
            return jsonify({"success": True}), 200
        else:
            logger.warning(
                f"Failed to forward callback for transaction {transaction_id}. "
                f"Status: {response.status_code}, Response: {response.text}"
            )
            return jsonify({
                "success": False,
                "error": f"PHP application returned status {response.status_code}"
            }), 500
            
    except Exception as e:
        logger.error(f"Error forwarding callback for transaction {transaction_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Error forwarding callback: {str(e)}"
        }), 500