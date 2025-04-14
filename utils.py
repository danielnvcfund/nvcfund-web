import os
import uuid
import secrets
import logging
import string
import json
from datetime import datetime, timedelta
from app import db
from models import User, TransactionStatus

logger = logging.getLogger(__name__)

def generate_transaction_id():
    """Generate a unique transaction ID"""
    return str(uuid.uuid4())

def generate_api_key():
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(64))

def format_currency(amount, currency):
    """Format currency amount with symbol"""
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'CNY': '¥',
        'ETH': 'Ξ',
        'BTC': '₿'
    }
    
    symbol = symbols.get(currency.upper(), '')
    
    if currency.upper() in ['USD', 'EUR', 'GBP']:
        return f"{symbol}{amount:.2f}"
    elif currency.upper() in ['JPY', 'CNY']:
        return f"{symbol}{int(amount)}"
    elif currency.upper() in ['ETH', 'BTC']:
        return f"{symbol}{amount:.8f}"
    else:
        return f"{amount} {currency.upper()}"

def calculate_transaction_fee(amount, transaction_type):
    """Calculate transaction fee based on amount and type"""
    fee_structure = {
        'payment': 0.029,      # 2.9%
        'transfer': 0.01,      # 1.0%
        'settlement': 0.005,   # 0.5%
        'withdrawal': 0.015,   # 1.5%
        'deposit': 0.0        # 0.0%
    }
    
    fee_percentage = fee_structure.get(transaction_type.lower(), 0.01)
    fee_amount = amount * fee_percentage
    
    # Minimum fee of $0.30 for payment and $0.10 for others
    if transaction_type.lower() == 'payment':
        min_fee = 0.30
    else:
        min_fee = 0.10
    
    return max(fee_amount, min_fee)

def get_transaction_analytics(user_id=None, days=30):
    """Get transaction analytics for the specified period"""
    from models import Transaction, TransactionType
    from sqlalchemy import func
    
    try:
        # Set time period
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Base query
        query = db.session.query(
            func.date(Transaction.created_at).label('date'),
            Transaction.transaction_type,
            Transaction.status,
            func.count().label('count'),
            func.sum(Transaction.amount).label('total_amount')
        )
        
        # Filter by date range
        query = query.filter(
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date
        )
        
        # Filter by user if specified
        if user_id:
            query = query.filter(Transaction.user_id == user_id)
        
        # Group by date, type, and status
        query = query.group_by(
            func.date(Transaction.created_at),
            Transaction.transaction_type,
            Transaction.status
        )
        
        # Sort by date
        query = query.order_by(func.date(Transaction.created_at))
        
        # Execute query
        results = query.all()
        
        # Organize results
        analytics = {
            'days': days,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_transactions': sum(r.count for r in results),
            'total_amount': sum(r.total_amount for r in results),
            'by_type': {},
            'by_status': {},
            'by_date': {},
            'raw_data': []
        }
        
        # Process results
        for r in results:
            # Convert enums to strings
            type_str = r.transaction_type.value
            status_str = r.status.value
            date_str = r.date.strftime('%Y-%m-%d')
            
            # By type
            if type_str not in analytics['by_type']:
                analytics['by_type'][type_str] = {
                    'count': 0,
                    'total_amount': 0
                }
            analytics['by_type'][type_str]['count'] += r.count
            analytics['by_type'][type_str]['total_amount'] += r.total_amount
            
            # By status
            if status_str not in analytics['by_status']:
                analytics['by_status'][status_str] = {
                    'count': 0,
                    'total_amount': 0
                }
            analytics['by_status'][status_str]['count'] += r.count
            analytics['by_status'][status_str]['total_amount'] += r.total_amount
            
            # By date
            if date_str not in analytics['by_date']:
                analytics['by_date'][date_str] = {
                    'count': 0,
                    'total_amount': 0,
                    'by_type': {}
                }
            analytics['by_date'][date_str]['count'] += r.count
            analytics['by_date'][date_str]['total_amount'] += r.total_amount
            
            # By date and type
            if type_str not in analytics['by_date'][date_str]['by_type']:
                analytics['by_date'][date_str]['by_type'][type_str] = {
                    'count': 0,
                    'total_amount': 0
                }
            analytics['by_date'][date_str]['by_type'][type_str]['count'] += r.count
            analytics['by_date'][date_str]['by_type'][type_str]['total_amount'] += r.total_amount
            
            # Raw data
            analytics['raw_data'].append({
                'date': date_str,
                'type': type_str,
                'status': status_str,
                'count': r.count,
                'total_amount': r.total_amount
            })
        
        return analytics
    
    except Exception as e:
        logger.error(f"Error getting transaction analytics: {str(e)}")
        return None

def check_pending_transactions():
    """Check and update status of pending transactions"""
    from models import Transaction
    from blockchain import get_transaction_status
    
    try:
        # Get pending transactions with blockchain hash
        pending_txs = Transaction.query.filter(
            Transaction.status.in_([TransactionStatus.PENDING, TransactionStatus.PROCESSING]),
            Transaction.eth_transaction_hash.isnot(None)
        ).all()
        
        updated = 0
        
        for tx in pending_txs:
            try:
                # Get blockchain transaction status
                status = get_transaction_status(tx.eth_transaction_hash)
                
                if status.get('error'):
                    logger.warning(f"Error checking status for transaction {tx.transaction_id}: {status['error']}")
                    continue
                
                # Update transaction status
                if status.get('status') == 'confirmed':
                    tx.status = TransactionStatus.COMPLETED
                    db.session.commit()
                    updated += 1
                elif status.get('status') == 'failed':
                    tx.status = TransactionStatus.FAILED
                    db.session.commit()
                    updated += 1
            
            except Exception as e:
                logger.error(f"Error updating transaction {tx.transaction_id}: {str(e)}")
                continue
        
        return updated
    
    except Exception as e:
        logger.error(f"Error checking pending transactions: {str(e)}")
        return 0

def validate_ethereum_address(address):
    """Validate Ethereum address format"""
    # Basic validation: check if address is a string and has the correct format
    if not isinstance(address, str):
        return False
    
    # Check length (42 characters including '0x')
    if len(address) != 42:
        return False
    
    # Check if it starts with '0x'
    if not address.startswith('0x'):
        return False
    
    # Check if the rest are hex characters
    try:
        int(address[2:], 16)
        return True
    except ValueError:
        return False

def validate_api_request(data, required_fields, optional_fields=None):
    """Validate API request data"""
    if not data:
        return False, "No data provided"
    
    # Check required fields
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Initialize result
    result = {}
    
    # Process required fields
    for field in required_fields:
        result[field] = data[field]
    
    # Process optional fields
    if optional_fields:
        for field, default in optional_fields.items():
            result[field] = data.get(field, default)
    
    return True, result
