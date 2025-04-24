"""
API routes for token exchange functionality
Handles AFD1-NVCT token pairing, exchange, and trading
"""
import json
import logging
from decimal import Decimal
from flask import Blueprint, request, jsonify, current_app

from app import db
from auth import jwt_required, api_key_required
from models import User, Transaction, TransactionStatus, TransactionType
from token_exchange import get_token_exchange, create_exchange_transaction
from utils import validate_api_request

logger = logging.getLogger(__name__)

# Create blueprint
token_exchange_api = Blueprint('token_exchange_api', __name__)

@token_exchange_api.route('/health', methods=['GET'])
def health_check():
    """
    Check health of token exchange API
    
    Returns:
        JSON: Health status
    """
    exchange = get_token_exchange()
    connected = exchange.check_connection()
    
    return jsonify({
        "status": "ok" if connected else "error",
        "message": "Token exchange service is operational" if connected else "Token exchange service is unavailable",
        "connected_to_dashboard": connected
    }), 200 if connected else 503

@token_exchange_api.route('/exchange-rate', methods=['GET'])
@api_key_required
def get_exchange_rate(user=None):
    """
    Get exchange rate between AFD1 and NVCT
    
    Args:
        user: User object injected by the api_key_required decorator
    
    Returns:
        JSON: Exchange rate information
    """
    exchange = get_token_exchange()
    rate = exchange.get_exchange_rate()
    
    if rate is not None:
        pair_info = exchange.get_token_pair_info()
        timestamp = pair_info.get("timestamp") if pair_info else None
        
        return jsonify({
            "status": "success",
            "from_token": "AFD1",
            "to_token": "NVCT",
            "rate": float(rate),
            "timestamp": timestamp
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve exchange rate"
        }), 500

@token_exchange_api.route('/token-pair-info', methods=['GET'])
@api_key_required
def token_pair_info(user=None):
    """
    Get information about the AFD1-NVCT token pair
    
    Args:
        user: User object injected by the api_key_required decorator
        
    Returns:
        JSON: Token pair information
    """
    exchange = get_token_exchange()
    pair_info = exchange.get_token_pair_info()
    
    if pair_info:
        return jsonify({
            "status": "success",
            "pair_info": pair_info
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve token pair information"
        }), 500

@token_exchange_api.route('/execute-trade', methods=['POST'])
@jwt_required
def execute_trade():
    """
    Execute a trade between AFD1 and NVCT
    
    Request body:
        from_token (str): Source token symbol (AFD1 or NVCT)
        to_token (str): Destination token symbol (AFD1 or NVCT)
        amount (float): Amount to trade in source token
        external_wallet_address (str, optional): External wallet address
    
    Returns:
        JSON: Trade result
    """
    try:
        data = request.get_json()
        
        # Validate request
        required_fields = ['from_token', 'to_token', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "status": "error",
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Get user ID from JWT token
        user_id = request.user.id
        
        # Parse amount as Decimal
        try:
            amount = Decimal(str(data['amount']))
        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "message": "Invalid amount format"
            }), 400
        
        # Execute trade
        exchange = get_token_exchange()
        success, tx_id, error = exchange.execute_trade(
            user_id=user_id,
            from_token=data['from_token'],
            to_token=data['to_token'],
            amount=amount,
            external_wallet_address=data.get('external_wallet_address')
        )
        
        if success and tx_id:
            # Calculate destination amount based on exchange rate
            rate = exchange.get_exchange_rate()
            if rate is None:
                return jsonify({
                    "status": "error",
                    "message": "Failed to get exchange rate for transaction recording"
                }), 500
            
            if data['from_token'] == "AFD1":
                to_amount = amount * rate
            else:
                to_amount = amount / rate
            
            # Create transaction record
            transaction = create_exchange_transaction(
                user_id=user_id,
                from_token=data['from_token'],
                to_token=data['to_token'],
                from_amount=amount,
                to_amount=to_amount,
                external_transaction_id=tx_id
            )
            
            return jsonify({
                "status": "success",
                "message": "Trade executed successfully",
                "transaction_id": transaction.transaction_id if transaction else None,
                "external_transaction_id": tx_id,
                "from_token": data['from_token'],
                "to_token": data['to_token'],
                "from_amount": float(amount),
                "to_amount": float(to_amount)
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": error or "Trade execution failed"
            }), 500
    except Exception as e:
        logger.error(f"Error executing trade: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500

@token_exchange_api.route('/trade-history', methods=['GET'])
@jwt_required
def get_trade_history():
    """
    Get trading history for the current user
    
    Returns:
        JSON: List of trades
    """
    user_id = request.user.id
    
    # Get trade history from both local database and institutional dashboard
    exchange = get_token_exchange()
    external_trades = exchange.get_trade_history(user_id)
    
    # Get local transaction records
    local_trades = Transaction.query.filter_by(
        user_id=user_id,
        transaction_type=TransactionType.TOKEN_EXCHANGE
    ).order_by(Transaction.created_at.desc()).all()
    
    # Format local trades
    formatted_local_trades = []
    for trade in local_trades:
        metadata = json.loads(trade.tx_metadata_json) if trade.tx_metadata_json else {}
        
        formatted_local_trades.append({
            "transaction_id": trade.transaction_id,
            "external_transaction_id": trade.external_id,
            "from_token": metadata.get("from_token", trade.currency),
            "to_token": metadata.get("to_token"),
            "from_amount": float(metadata.get("from_amount", trade.amount)),
            "to_amount": float(metadata.get("to_amount", 0)),
            "status": trade.status.name,
            "timestamp": trade.created_at.isoformat(),
            "description": trade.description
        })
    
    return jsonify({
        "status": "success",
        "local_trades": formatted_local_trades,
        "external_trades": external_trades
    }), 200

@token_exchange_api.route('/token-balance', methods=['GET'])
@jwt_required
def get_token_balance():
    """
    Get token balance for the current user
    
    Query parameters:
        token (str): Token symbol (AFD1 or NVCT)
    
    Returns:
        JSON: Token balance
    """
    user_id = request.user.id
    token_symbol = request.args.get('token')
    
    if not token_symbol:
        return jsonify({
            "status": "error",
            "message": "Missing token parameter"
        }), 400
    
    if token_symbol not in ["AFD1", "NVCT"]:
        return jsonify({
            "status": "error",
            "message": f"Invalid token symbol: {token_symbol}"
        }), 400
    
    exchange = get_token_exchange()
    balance = exchange.get_token_balance(user_id, token_symbol)
    
    if balance is not None:
        return jsonify({
            "status": "success",
            "token": token_symbol,
            "balance": float(balance)
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve {token_symbol} balance"
        }), 500