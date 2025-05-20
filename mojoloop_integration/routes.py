"""
Mojoloop API Routes for NVC Banking Platform

This module provides Flask routes for interacting with the Mojoloop API.
"""

import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, g, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
import os

from mojoloop_integration.mojoloop_service import MojolloopService
from decorators import admin_required
from models import User, Transaction, PaymentGateway, TransactionStatus

# Create blueprints
mojoloop_bp = Blueprint('mojoloop', __name__, url_prefix='/api/mojoloop')
mojoloop_web_bp = Blueprint('mojoloop_web', __name__, url_prefix='/mojoloop')

# Initialize service on first request
@mojoloop_bp.before_request
def initialize_service():
    """Initialize Mojoloop service before handling request"""
    if not hasattr(g, 'mojoloop_service'):
        g.mojoloop_service = MojolloopService()

@mojoloop_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Mojoloop API integration
    
    Returns:
        Health status of the Mojoloop API integration
    """
    try:
        # Basic connectivity check to the service
        # We don't actually call the Mojoloop API to avoid unnecessary traffic
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'Mojoloop API Integration',
            'version': '1.0.0'
        }), 200
    except Exception as e:
        current_app.logger.error(f"Mojoloop health check failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@mojoloop_bp.route('/transactions', methods=['POST'])
@jwt_required()
def create_transaction():
    """
    Create a new transaction through Mojoloop
    
    Returns:
        Created transaction details
    """
    try:
        # Get authenticated user
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        # Validate incoming data
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No request data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['payer_identifier', 'payee_identifier', 'amount', 'currency']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Generate transaction ID if not provided
        if 'transaction_id' not in data:
            data['transaction_id'] = f"ML-{str(uuid.uuid4())}"
        
        # Create and process the transaction
        result = g.mojoloop_service.create_and_process_transaction(data, user_id)
        
        return jsonify({
            'status': 'success',
            'message': 'Transaction created successfully',
            'data': result
        }), 201
        
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Error creating Mojoloop transaction: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to create transaction: {str(e)}'
        }), 500

@mojoloop_bp.route('/transactions/<transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction(transaction_id):
    """
    Get transaction status from Mojoloop
    
    Args:
        transaction_id: Transaction ID to check
    
    Returns:
        Transaction status details
    """
    try:
        # Get transaction status
        result = g.mojoloop_service.get_transaction_status(transaction_id)
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        current_app.logger.error(f"Error getting Mojoloop transaction status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get transaction status: {str(e)}'
        }), 500

@mojoloop_bp.route('/callbacks/transfers', methods=['POST'])
def transfer_callback():
    """
    Callback endpoint for Mojoloop transfer notifications
    
    This endpoint receives notifications from Mojoloop when a transfer
    status changes, allowing us to update our records accordingly.
    
    Returns:
        Acknowledgment of the callback
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No callback data provided'
            }), 400
        
        # Log the callback for debugging
        current_app.logger.info(f"Received Mojoloop transfer callback: {json.dumps(data)}")
        
        # Extract transfer ID and status
        transfer_id = data.get('transferId')
        status = data.get('transferState')
        
        if not transfer_id:
            return jsonify({
                'status': 'error',
                'message': 'Missing transferId in callback data'
            }), 400
        
        # Update transaction status in our database
        transaction = Transaction.query.filter_by(external_id=transfer_id).first()
        
        if transaction:
            # Map Mojoloop status to our status values
            status_mapping = {
                'RECEIVED': 'PENDING',
                'PENDING': 'PENDING',
                'ACCEPTED': 'PROCESSING',
                'REJECTED': 'FAILED',
                'COMMITTED': 'COMPLETED',
                'ABORTED': 'FAILED'
            }
            
            transaction.status = status_mapping.get(status, transaction.status)
            transaction.updated_at = datetime.utcnow()
            transaction.gateway_response = json.dumps(data)
            
            # Commit the changes
            from app import db
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'Transaction {transaction.transaction_id} status updated to {transaction.status}'
            }), 200
        else:
            # If we can't find the transaction, still acknowledge but log a warning
            current_app.logger.warning(f"Received callback for unknown transfer ID: {transfer_id}")
            return jsonify({
                'status': 'success',
                'message': 'Callback received, but no matching transaction found'
            }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error processing Mojoloop callback: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to process callback: {str(e)}'
        }), 500

@mojoloop_bp.route('/callbacks/quotes', methods=['POST'])
def quote_callback():
    """
    Callback endpoint for Mojoloop quote notifications
    
    This endpoint receives notifications from Mojoloop when a quote
    is created or updated, allowing us to update our records accordingly.
    
    Returns:
        Acknowledgment of the callback
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No callback data provided'
            }), 400
        
        # Log the callback for debugging
        current_app.logger.info(f"Received Mojoloop quote callback: {json.dumps(data)}")
        
        # Since quotes are part of the transaction flow but not directly
        # represented in our database, we just acknowledge the callback
        return jsonify({
            'status': 'success',
            'message': 'Quote callback received and processed'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error processing Mojoloop quote callback: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to process quote callback: {str(e)}'
        }), 500

# Web interface routes
@mojoloop_web_bp.route('/', methods=['GET'])
@admin_required
def dashboard():
    """
    Mojoloop API integration dashboard
    
    Returns:
        Dashboard with transaction list and statistics
    """
    try:
        # Get the Mojoloop payment gateway
        gateway = PaymentGateway.query.filter_by(name='Mojoloop').first()
        gateway_id = gateway.id if gateway else None
        
        # Get transactions
        if gateway_id:
            transactions = Transaction.query.filter_by(
                payment_gateway_id=gateway_id
            ).order_by(
                Transaction.created_at.desc()
            ).limit(20).all()
        else:
            transactions = []
            
        # Get transaction statistics
        total_transactions = len(transactions)
        completed_transactions = sum(1 for tx in transactions if tx.status == TransactionStatus.COMPLETED.value)
        pending_transactions = sum(1 for tx in transactions if tx.status == TransactionStatus.PENDING.value)
        failed_transactions = sum(1 for tx in transactions if tx.status == TransactionStatus.FAILED.value)
        
        # Get API URL
        api_url = os.environ.get('MOJOLOOP_API_URL', 'Not configured')
        
        return render_template('mojoloop/dashboard.html',
                              transactions=transactions,
                              total_transactions=total_transactions,
                              completed_transactions=completed_transactions,
                              pending_transactions=pending_transactions,
                              failed_transactions=failed_transactions,
                              api_url=api_url)
    except Exception as e:
        current_app.logger.error(f"Error rendering Mojoloop dashboard: {str(e)}")
        return render_template('error.html', 
                              error_message="Failed to load Mojoloop dashboard",
                              details=str(e))

# Admin endpoints

@mojoloop_bp.route('/admin/transactions', methods=['GET'])
@jwt_required()
@admin_required
def list_transactions():
    """
    List Mojoloop transactions (admin only)
    
    Returns:
        List of Mojoloop transactions
    """
    try:
        # Get transactions from the database
        transactions = Transaction.query.join(
            Transaction.payment_gateway
        ).filter(
            Transaction.payment_gateway.has(name='Mojoloop')
        ).order_by(
            Transaction.created_at.desc()
        ).limit(100).all()
        
        result = []
        for tx in transactions:
            result.append({
                'transaction_id': tx.transaction_id,
                'external_id': tx.external_id,
                'amount': float(tx.amount),
                'currency': tx.currency,
                'status': tx.status,
                'created_at': tx.created_at.isoformat() if tx.created_at else None,
                'updated_at': tx.updated_at.isoformat() if tx.updated_at else None
            })
        
        return jsonify({
            'status': 'success',
            'count': len(result),
            'data': result
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error listing Mojoloop transactions: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to list transactions: {str(e)}'
        }), 500