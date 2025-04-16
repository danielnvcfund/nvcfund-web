"""
XRP Ledger API Routes for NVC Banking Platform
Provides HTTP API endpoints for interacting with the XRP Ledger
"""

import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required

from app import db
from auth import api_key_required, jwt_required
from models import User, Transaction, TransactionType, PaymentGateway, PaymentGatewayType, XRPLedgerTransaction
import xrp_integration

# Create a blueprint for XRP Ledger API routes
xrp_api = Blueprint('xrp_api', __name__)

@xrp_api.route('/info', methods=['GET'])
def get_xrp_info():
    """Get basic information about XRP Ledger integration"""
    try:
        # Get the XRP Gateway
        xrp_gateway = PaymentGateway.query.filter_by(
            gateway_type=PaymentGatewayType.XRP_LEDGER,
            is_active=True
        ).first()
        
        if not xrp_gateway:
            return jsonify({
                'success': False,
                'message': 'XRP Ledger gateway not initialized',
                'status': 'disabled'
            }), 404
        
        return jsonify({
            'success': True,
            'status': 'active',
            'gateway': {
                'name': xrp_gateway.name,
                'type': xrp_gateway.gateway_type.value,
                'network_url': xrp_gateway.api_endpoint,
                'address': xrp_gateway.xrp_address
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_xrp_info: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

@xrp_api.route('/wallet', methods=['GET'])
@login_required
def get_user_wallet():
    """Get the current user's XRP wallet information"""
    try:
        user_id = current_user.id
        
        # Ensure the user has an XRP wallet
        success, error = xrp_integration.ensure_user_has_xrp_wallet(user_id)
        if not success:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        # Get the user's XRP balance
        balance, error = xrp_integration.get_user_xrp_balance(user_id)
        if error:
            # Return the wallet info even if balance check failed
            return jsonify({
                'success': True,
                'wallet': {
                    'address': current_user.xrp_address,
                    'balance': 0.0,
                    'balance_error': error
                }
            })
        
        return jsonify({
            'success': True,
            'wallet': {
                'address': current_user.xrp_address,
                'balance': balance
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_user_wallet: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

@xrp_api.route('/wallet/<user_id>', methods=['GET'])
@jwt_required
def get_specific_user_wallet(user_id):
    """Get a specific user's XRP wallet information (admin only)"""
    try:
        # Admin check happens in the jwt_required decorator
        
        # Ensure the user has an XRP wallet
        success, error = xrp_integration.ensure_user_has_xrp_wallet(int(user_id))
        if not success:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        # Get the user
        user = User.query.get(int(user_id))
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Get the user's XRP balance
        balance, error = xrp_integration.get_user_xrp_balance(int(user_id))
        if error:
            # Return the wallet info even if balance check failed
            return jsonify({
                'success': True,
                'user_id': user.id,
                'username': user.username,
                'wallet': {
                    'address': user.xrp_address,
                    'balance': 0.0,
                    'balance_error': error
                }
            })
        
        return jsonify({
            'success': True,
            'user_id': user.id,
            'username': user.username,
            'wallet': {
                'address': user.xrp_address,
                'balance': balance
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_specific_user_wallet: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

@xrp_api.route('/transactions', methods=['GET'])
@login_required
def get_user_transactions():
    """Get the current user's XRP transactions"""
    try:
        user_id = current_user.id
        limit = request.args.get('limit', 10, type=int)
        
        # Get the user's XRP transactions
        transactions, error = xrp_integration.get_user_xrp_transactions(user_id, limit)
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'transactions': transactions
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_user_transactions: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

@xrp_api.route('/transactions/<user_id>', methods=['GET'])
@jwt_required
def get_specific_user_transactions(user_id):
    """Get a specific user's XRP transactions (admin only)"""
    try:
        # Admin check happens in the jwt_required decorator
        limit = request.args.get('limit', 10, type=int)
        
        # Get the user's XRP transactions
        transactions, error = xrp_integration.get_user_xrp_transactions(int(user_id), limit)
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'user_id': int(user_id),
            'transactions': transactions
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_specific_user_transactions: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

@xrp_api.route('/payment', methods=['POST'])
@login_required
def create_payment():
    """Create an XRP payment from the current user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Missing request data'
            }), 400
        
        # Validate required fields
        required_fields = ['to_address', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Get optional fields
        description = data.get('description')
        destination_tag = data.get('destination_tag')
        memo = data.get('memo')
        
        # Parse transaction type
        tx_type_str = data.get('transaction_type', 'PAYMENT').upper()
        try:
            tx_type = TransactionType[tx_type_str]
        except KeyError:
            tx_type = TransactionType.PAYMENT
        
        # Create the XRP payment
        payment, error = xrp_integration.create_xrp_payment(
            user_id=current_user.id,
            to_address=data['to_address'],
            amount=float(data['amount']),
            description=description,
            destination_tag=destination_tag,
            transaction_type=tx_type,
            memo=memo
        )
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'payment': payment
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in create_payment: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

@xrp_api.route('/payment/<user_id>', methods=['POST'])
@jwt_required
def create_payment_for_user(user_id):
    """Create an XRP payment for a specific user (admin only)"""
    try:
        # Admin check happens in the jwt_required decorator
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Missing request data'
            }), 400
        
        # Validate required fields
        required_fields = ['to_address', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Get optional fields
        description = data.get('description')
        destination_tag = data.get('destination_tag')
        memo = data.get('memo')
        
        # Parse transaction type
        tx_type_str = data.get('transaction_type', 'PAYMENT').upper()
        try:
            tx_type = TransactionType[tx_type_str]
        except KeyError:
            tx_type = TransactionType.PAYMENT
        
        # Create the XRP payment
        payment, error = xrp_integration.create_xrp_payment(
            user_id=int(user_id),
            to_address=data['to_address'],
            amount=float(data['amount']),
            description=description,
            destination_tag=destination_tag,
            transaction_type=tx_type,
            memo=memo
        )
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'user_id': int(user_id),
            'payment': payment
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in create_payment_for_user: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

@xrp_api.route('/transaction/<tx_hash>/status', methods=['GET'])
@login_required
def check_transaction_status(tx_hash):
    """Check the status of an XRP transaction"""
    try:
        # Get the transaction status
        status, error = xrp_integration.check_xrp_transaction_status(tx_hash)
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in check_transaction_status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

@xrp_api.route('/escrow', methods=['POST'])
@login_required
def create_escrow():
    """Create an XRP escrow payment from the current user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Missing request data'
            }), 400
        
        # Validate required fields
        required_fields = ['to_address', 'amount', 'release_time']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Get optional fields
        description = data.get('description')
        cancel_after = data.get('cancel_after')
        condition = data.get('condition')
        
        # Create the XRP escrow
        escrow, error = xrp_integration.create_xrp_escrow(
            user_id=current_user.id,
            to_address=data['to_address'],
            amount=float(data['amount']),
            release_time=int(data['release_time']),
            cancel_after=int(cancel_after) if cancel_after else None,
            description=description,
            condition=condition
        )
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'escrow': escrow
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in create_escrow: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

@xrp_api.route('/escrow/finish', methods=['POST'])
@login_required
def finish_escrow():
    """Finish an XRP escrow payment to release funds to the recipient"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Missing request data'
            }), 400
        
        # Validate required fields
        required_fields = ['owner_address', 'escrow_sequence']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Get optional field
        fulfillment = data.get('fulfillment')
        
        # Finish the XRP escrow
        result, error = xrp_integration.finish_xrp_escrow(
            user_id=current_user.id,
            owner_address=data['owner_address'],
            escrow_sequence=int(data['escrow_sequence']),
            fulfillment=fulfillment
        )
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in finish_escrow: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

@xrp_api.route('/escrow/cancel', methods=['POST'])
@login_required
def cancel_escrow():
    """Cancel an XRP escrow payment to return funds to the sender"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Missing request data'
            }), 400
        
        # Validate required fields
        required_fields = ['owner_address', 'escrow_sequence']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Cancel the XRP escrow
        result, error = xrp_integration.cancel_xrp_escrow(
            user_id=current_user.id,
            owner_address=data['owner_address'],
            escrow_sequence=int(data['escrow_sequence'])
        )
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in cancel_escrow: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500