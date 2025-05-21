"""
Account Holder API Routes
Provides API endpoints for accessing account holder data
"""
import logging
from flask import Blueprint, jsonify
from account_holder_models import AccountHolder, BankAccount

logger = logging.getLogger(__name__)

account_holder_api = Blueprint('account_holder_api', __name__, url_prefix='/account-holder')

@account_holder_api.route('/<int:account_holder_id>/accounts', methods=['GET'])
def get_accounts(account_holder_id):
    """Get all accounts for an account holder"""
    try:
        # Get the account holder
        account_holder = AccountHolder.query.get(account_holder_id)
        if not account_holder:
            return jsonify({
                'success': False,
                'message': 'Account holder not found',
                'accounts': []
            }), 404
        
        # Get the accounts for the account holder
        accounts = BankAccount.query.filter_by(account_holder_id=account_holder_id).all()
        
        # Format the accounts
        account_list = []
        for account in accounts:
            account_list.append({
                'id': account.id,
                'account_number': account.account_number,
                'account_type': account.account_type.value if hasattr(account, 'account_type') and account.account_type else 'Unknown',
                'currency': account.currency,
                'balance': float(account.balance) if hasattr(account, 'balance') else 0.0
            })
        
        # Return the accounts
        return jsonify({
            'success': True,
            'message': 'Accounts retrieved successfully',
            'accounts': account_list
        })
    except Exception as e:
        logger.error(f"Error getting accounts for account holder {account_holder_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error getting accounts: {str(e)}",
            'accounts': []
        }), 500