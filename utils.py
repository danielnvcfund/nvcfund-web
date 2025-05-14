import os
import uuid
import secrets
import logging
import string
import json
import locale
from datetime import datetime, timedelta
from flask import abort, current_app, session
from flask_login import current_user
from app import db
from models import User, TransactionStatus, UserRole

# Set locale for currency formatting
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    # Fallback if locale is not available
    pass

logger = logging.getLogger(__name__)

def generate_transaction_id():
    """Generate a unique transaction ID"""
    return str(uuid.uuid4())

def generate_uuid():
    """Generate a unique UUID string"""
    return str(uuid.uuid4())
    
def generate_unique_id(prefix=''):
    """Generate a unique ID with optional prefix"""
    unique_id = str(uuid.uuid4()).replace('-', '')[:16].upper()
    if prefix:
        return f"{prefix}-{unique_id}"
    return unique_id

def generate_api_key():
    """Generate a secure API key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(64))

def format_currency(amount, currency):
    """Format currency amount with symbol and thousand separators"""
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
        return f"{symbol}{amount:,.2f}"
    elif currency.upper() in ['JPY', 'CNY']:
        return f"{symbol}{int(amount):,}"
    elif currency.upper() in ['ETH', 'BTC']:
        return f"{symbol}{amount:,.8f}"
    else:
        return f"{amount:,.2f} {currency.upper()}"

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
    import decimal
    import json
    
    # Default empty structure that matches what the dashboard.js expects
    default_analytics = {
        'days': days,
        'start_date': (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d'),
        'end_date': datetime.utcnow().strftime('%Y-%m-%d'),
        'total_transactions': 0,
        'total_amount': 0.0,  # Use float
        'by_type': {},
        'by_status': {},
        'by_date': {},
        'raw_data': []
    }
    
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
        
        # If no results, return the default structure
        if not results:
            logger.info(f"No transaction analytics data found for user {user_id}")
            return default_analytics
        
        # Helper function to convert decimals to float for JSON serialization
        def decimal_to_float(obj):
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            return obj
        
        # Organize results with safe conversion of decimal values
        analytics = {
            'days': days,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_transactions': sum(r.count for r in results),
            'total_amount': 0.0,  # Initialize with float instead of potentially Decimal
            'by_type': {},
            'by_status': {},
            'by_date': {},
            'raw_data': []
        }
        
        # Calculate total amount with explicit conversion to float
        try:
            total_sum = sum(decimal_to_float(r.total_amount or 0) for r in results)
            analytics['total_amount'] = float(total_sum) if total_sum is not None else 0.0
        except (TypeError, ValueError, decimal.InvalidOperation) as e:
            logger.error(f"Error calculating total amount: {str(e)}")
            analytics['total_amount'] = 0.0
        
        # Process results
        for r in results:
            # Convert enums to strings and handle possible None values
            type_str = r.transaction_type.value if r.transaction_type else 'unknown'
            status_str = r.status.value if r.status else 'unknown'
            date_str = r.date.strftime('%Y-%m-%d') if r.date else 'unknown'
            count = r.count or 0
            total_amount = decimal_to_float(r.total_amount or 0)
            
            # By type
            if type_str not in analytics['by_type']:
                analytics['by_type'][type_str] = {
                    'count': 0,
                    'total_amount': 0.0  # Initialize with float
                }
            analytics['by_type'][type_str]['count'] += count
            analytics['by_type'][type_str]['total_amount'] = float(analytics['by_type'][type_str]['total_amount'] + total_amount)
            
            # By status
            if status_str not in analytics['by_status']:
                analytics['by_status'][status_str] = {
                    'count': 0,
                    'total_amount': 0.0  # Initialize with float
                }
            analytics['by_status'][status_str]['count'] += count
            analytics['by_status'][status_str]['total_amount'] = float(analytics['by_status'][status_str]['total_amount'] + total_amount)
            
            # By date
            if date_str not in analytics['by_date']:
                analytics['by_date'][date_str] = {
                    'count': 0,
                    'total_amount': 0.0,  # Initialize with float
                    'by_type': {}
                }
            analytics['by_date'][date_str]['count'] += count
            analytics['by_date'][date_str]['total_amount'] = float(analytics['by_date'][date_str]['total_amount'] + total_amount)
            
            # By date and type
            if type_str not in analytics['by_date'][date_str]['by_type']:
                analytics['by_date'][date_str]['by_type'][type_str] = {
                    'count': 0,
                    'total_amount': 0.0  # Initialize with float
                }
            analytics['by_date'][date_str]['by_type'][type_str]['count'] += count
            analytics['by_date'][date_str]['by_type'][type_str]['total_amount'] = float(analytics['by_date'][date_str]['by_type'][type_str]['total_amount'] + total_amount)
            
            # Raw data
            analytics['raw_data'].append({
                'date': date_str,
                'type': type_str,
                'status': status_str,
                'count': count,
                'total_amount': float(total_amount)  # Ensure float in raw data
            })
        
        # Ensure we have data for all days in the range, even if no transactions
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            if date_str not in analytics['by_date']:
                analytics['by_date'][date_str] = {
                    'count': 0,
                    'total_amount': 0.0,  # Initialize with float
                    'by_type': {}
                }
            current_date += timedelta(days=1)
        
        # Final check to ensure all amounts are floats before returning
        try:
            # Verify all nested amounts are floats
            for type_key in analytics['by_type']:
                analytics['by_type'][type_key]['total_amount'] = float(analytics['by_type'][type_key]['total_amount'])
            
            for status_key in analytics['by_status']:
                analytics['by_status'][status_key]['total_amount'] = float(analytics['by_status'][status_key]['total_amount'])
            
            for date_key in analytics['by_date']:
                analytics['by_date'][date_key]['total_amount'] = float(analytics['by_date'][date_key]['total_amount'])
                for type_key in analytics['by_date'][date_key].get('by_type', {}):
                    if 'total_amount' in analytics['by_date'][date_key]['by_type'][type_key]:
                        analytics['by_date'][date_key]['by_type'][type_key]['total_amount'] = float(
                            analytics['by_date'][date_key]['by_type'][type_key]['total_amount']
                        )
            
            # Ensure total_amount is a float
            analytics['total_amount'] = float(analytics['total_amount'])
            
            logger.debug("Successfully converted all decimal values to float in analytics")
        except Exception as e:
            logger.error(f"Error converting decimal values in analytics: {str(e)}")
            # Continue with the data as is - we've done our best to convert values
        
        return analytics
    
    except Exception as e:
        logger.error(f"Error getting transaction analytics: {str(e)}")
        # Return a minimal structure instead of None to avoid template errors
        return {
            'days': days,
            'start_date': (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'total_transactions': 0,
            'total_amount': 0.0,  # Use float
            'by_type': {},
            'by_status': {},
            'by_date': {},
            'raw_data': []
        }

def get_or_404(model, id):
    """Get a database object by ID or return 404"""
    item = model.query.get(id)
    if item is None:
        abort(404)
    return item

def is_admin(user):
    """Check if user has admin role"""
    return user.role in [UserRole.ADMIN, UserRole.DEVELOPER]

def is_developer(user):
    """Check if user has developer role"""
    return user.role == UserRole.DEVELOPER

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
    
def get_transaction_metadata(transaction):
    """
    Safely parse and return transaction metadata from JSON
    
    Args:
        transaction: Transaction object with tx_metadata_json attribute
        
    Returns:
        dict: Parsed metadata or empty dict if parsing fails
    """
    if not transaction or not hasattr(transaction, 'tx_metadata_json') or not transaction.tx_metadata_json:
        return {}
        
    try:
        return json.loads(transaction.tx_metadata_json)
    except json.JSONDecodeError:
        try:
            # Try to fix common issues with malformed JSON
            fixed_json = transaction.tx_metadata_json.strip()
            if fixed_json.startswith('"') and fixed_json.endswith('"'):
                # Handle double-encoded JSON string
                fixed_json = fixed_json[1:-1].replace('\\"', '"')
            return json.loads(fixed_json)
        except (json.JSONDecodeError, Exception):
            return {}

def get_institution_metadata(institution):
    """
    Safely parse and return institution metadata from JSON
    
    Args:
        institution: FinancialInstitution object with metadata_json attribute
        
    Returns:
        dict: Parsed metadata or empty dict if parsing fails
    """
    if not institution or not hasattr(institution, 'metadata_json') or not institution.metadata_json:
        return {}
        
    try:
        return json.loads(institution.metadata_json)
    except json.JSONDecodeError:
        try:
            # Try to fix common issues with malformed JSON
            fixed_json = institution.metadata_json.strip()
            if fixed_json.startswith('"') and fixed_json.endswith('"'):
                # Handle double-encoded JSON string
                fixed_json = fixed_json[1:-1].replace('\\"', '"')
            return json.loads(fixed_json)
        except (json.JSONDecodeError, Exception):
            return {}
    
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

def format_currency(amount, currency='USD'):
    """Format a monetary amount with currency symbol and 2 decimal places
    
    Args:
        amount (float): The monetary amount to format
        currency (str): The currency code (e.g. 'USD', 'EUR')
        
    Returns:
        str: Formatted currency string (e.g. '$1,234.56')
    """
    if amount is None:
        return f"{currency} 0.00"
        
    # Handle common currency symbols
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'CAD': 'C$',
        'AUD': 'A$',
        'CHF': 'CHF',
    }
    
    # Get symbol or use currency code
    symbol = currency_symbols.get(currency, currency)
    
    # Format with thousands separator and 2 decimal places
    if currency == 'JPY':  # JPY traditionally has no decimal places
        formatted = f"{symbol}{int(amount):,}"
    else:
        formatted = f"{symbol}{amount:,.2f}"
        
    return formatted

def format_transaction_type(transaction_type):
    """
    Format transaction type for display in a user-friendly way
    
    Args:
        transaction_type: TransactionType enum value or string
        
    Returns:
        str: Formatted transaction type for display
    """
    # Using a logger instead of print for debugging
    logger.debug(f"format_transaction_type called with {transaction_type}")
    # Convert to string if it's an enum
    if hasattr(transaction_type, 'value'):
        type_value = transaction_type.value
    else:
        type_value = str(transaction_type)
    
    # Define friendly names for transaction types
    friendly_names = {
        'RTGS_TRANSFER': 'Real Time Gross Settlement (RTGS) Transaction',
        'SERVER_TO_SERVER': 'Server-to-Server Transfer',
        'SWIFT_TRANSFER': 'SWIFT Transfer',
        'SWIFT_GPI_PAYMENT': 'SWIFT GPI Payment',
        'SWIFT_LETTER_OF_CREDIT': 'SWIFT Letter of Credit',
        'SWIFT_FUND_TRANSFER': 'SWIFT Fund Transfer (MT103)',
        'SWIFT_INSTITUTION_TRANSFER': 'SWIFT Institution Transfer (MT202)',
        'SWIFT_FREE_FORMAT': 'SWIFT Free Format Message (MT799)',
        'INTERNATIONAL_WIRE': 'International Wire Transfer',
        'OFF_LEDGER_TRANSFER': 'Off-Ledger Transfer',
        'TOKEN_EXCHANGE': 'Token Exchange',
        'EDI_PAYMENT': 'EDI Payment',
        'EDI_ACH_TRANSFER': 'EDI ACH Transfer',
        'EDI_WIRE_TRANSFER': 'EDI Wire Transfer',
        'TREASURY_TRANSFER': 'Treasury Transfer',
        'TREASURY_INVESTMENT': 'Treasury Investment',
        'TREASURY_LOAN': 'Treasury Loan',
        'TREASURY_DEBT_REPAYMENT': 'Treasury Debt Repayment',
        'SALARY_PAYMENT': 'Salary Payment',
        'BILL_PAYMENT': 'Bill Payment',
        'CONTRACT_PAYMENT': 'Contract Payment',
        'BULK_PAYROLL': 'Bulk Payroll Processing',
        'DEPOSIT': 'Deposit',
        'WITHDRAWAL': 'Withdrawal',
        'TRANSFER': 'Transfer',
        'PAYMENT': 'Payment',
        'SETTLEMENT': 'Settlement'
    }
    
    # Return friendly name or formatted original if not found
    return friendly_names.get(type_value, type_value.replace('_', ' ').title())


def save_form_data_to_session(form, prefix="form_"):
    """
    Save form data to session to restore later if there's an error
    
    Args:
        form: The form object containing the data
        prefix: Prefix to use for the session keys to avoid conflicts
    """
    form_data = {}
    
    # Iterate through form fields
    for field_name, field in form._fields.items():
        # Skip CSRF token, submit buttons and hidden fields
        if field_name in ('csrf_token', 'submit') or field.type == 'HiddenField':
            continue
        
        # Save the field data with type information
        if field.data is not None:
            # Convert numeric types to strings for safer storage in session
            if field.type in ('DecimalField', 'FloatField', 'IntegerField'):
                # Store as string but remember field type
                form_data[field_name] = {
                    'value': str(field.data),
                    'type': field.type
                }
            else:
                form_data[field_name] = {
                    'value': field.data,
                    'type': field.type
                }
    
    # Store in session
    session[f"{prefix}{form.__class__.__name__}"] = form_data


def restore_form_data_from_session(form, prefix="form_", clear=False):
    """
    Restore form data from session
    
    Args:
        form: The form object to populate
        prefix: Prefix used for the session keys
        clear: Whether to clear the data from session after restoring
    
    Returns:
        bool: True if data was restored, False if no data found
    """
    session_key = f"{prefix}{form.__class__.__name__}"
    
    if session_key not in session:
        return False
    
    form_data = session[session_key]
    
    # Check if we're using the old or new format
    is_new_format = all(isinstance(v, dict) and 'value' in v for v in form_data.values() if v is not None)
    
    # Populate form fields
    for field_name, field_info in form_data.items():
        if field_name in form._fields:
            field = form._fields[field_name]
            
            # Skip select fields as they need special handling
            if field.type == 'SelectField':
                continue
            
            if is_new_format:
                # New format with type information
                value = field_info.get('value')
                field_type = field_info.get('type')
                
                # Handle numeric fields
                if field_type in ('DecimalField', 'FloatField', 'IntegerField'):
                    try:
                        if value is not None:
                            if field_type == 'IntegerField':
                                field.data = int(value)
                            else:
                                field.data = float(value)
                    except (ValueError, TypeError):
                        # If conversion fails, leave as default
                        pass
                else:
                    # For non-numeric fields
                    field.data = value
            else:
                # Old format (backward compatibility)
                value = field_info
                
                # Handle numeric fields
                if field.type in ('DecimalField', 'FloatField', 'IntegerField'):
                    try:
                        if value is not None:
                            if field.type == 'IntegerField':
                                field.data = int(value)
                            else:
                                field.data = float(value)
                    except (ValueError, TypeError):
                        # If conversion fails, leave as default
                        pass
                else:
                    # For non-numeric fields
                    field.data = value
    
    # Optionally clear the data
    if clear:
        session.pop(session_key, None)
    
    return True


def clear_form_data_from_session(form_class, prefix="form_"):
    """
    Clear form data from session
    
    Args:
        form_class: The form class
        prefix: Prefix used for the session keys
    """
    session_key = f"{prefix}{form_class.__name__}"
    if session_key in session:
        session.pop(session_key, None)
