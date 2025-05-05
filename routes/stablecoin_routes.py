"""
Routes for the NVC Token Stablecoin peer-to-peer ledger system
"""

import logging
import json
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import (
    StablecoinAccount, 
    LedgerEntry, 
    CorrespondentBank,
    SettlementBatch, 
    Transaction, 
    TransactionStatus, 
    TransactionType
)
import stablecoin_service

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a blueprint for stablecoin routes
stablecoin_bp = Blueprint('stablecoin', __name__, url_prefix='/stablecoin')

@stablecoin_bp.route('/')
@login_required
def index():
    """Stablecoin dashboard page"""
    # Get the user's stablecoin accounts
    accounts = StablecoinAccount.query.filter_by(user_id=current_user.id).all()
    
    # Get correspondent banks (for admin users)
    correspondent_banks = None
    if current_user.role.name == 'ADMIN':
        correspondent_banks = CorrespondentBank.query.filter_by(is_active=True).all()
    
    return render_template(
        'stablecoin/index.html',
        accounts=accounts,
        correspondent_banks=correspondent_banks
    )

@stablecoin_bp.route('/accounts')
@login_required
def accounts():
    """View user's stablecoin accounts"""
    # Get the user's stablecoin accounts
    accounts = StablecoinAccount.query.filter_by(user_id=current_user.id).all()
    
    return render_template(
        'stablecoin/accounts.html',
        accounts=accounts
    )

@stablecoin_bp.route('/accounts/create', methods=['GET', 'POST'])
@login_required
def create_account():
    """Create a new stablecoin account"""
    if request.method == 'POST':
        account_type = request.form.get('account_type', 'INDIVIDUAL')
        
        # Create the account
        account, error = stablecoin_service.create_stablecoin_account(
            user_id=current_user.id,
            account_type=account_type
        )
        
        if error:
            flash(f"Error creating account: {error}", 'danger')
            return redirect(url_for('stablecoin.accounts'))
        
        flash(f"Account {account.account_number} created successfully", 'success')
        return redirect(url_for('stablecoin.accounts'))
    
    return render_template('stablecoin/create_account.html')

@stablecoin_bp.route('/accounts/<int:account_id>')
@login_required
def account_details(account_id):
    """View details of a specific stablecoin account"""
    # Get the account
    account = StablecoinAccount.query.get_or_404(account_id)
    
    # Check if the account belongs to the current user
    if account.user_id != current_user.id and current_user.role.name != 'ADMIN':
        flash("You don't have permission to view this account", 'danger')
        return redirect(url_for('stablecoin.accounts'))
    
    # Get recent transactions
    transactions, error = stablecoin_service.get_account_transactions(account_id, limit=10)
    if error:
        flash(f"Error retrieving transactions: {error}", 'warning')
        transactions = []
    
    return render_template(
        'stablecoin/account_details.html',
        account=account,
        transactions=transactions
    )

@stablecoin_bp.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    """Transfer stablecoins between accounts"""
    # Get the user's stablecoin accounts
    accounts = StablecoinAccount.query.filter_by(
        user_id=current_user.id, 
        is_active=True
    ).all()
    
    if request.method == 'POST':
        from_account_id = request.form.get('from_account_id')
        to_account_number = request.form.get('to_account_number')
        amount = request.form.get('amount')
        description = request.form.get('description')
        
        # Validate inputs
        if not from_account_id or not to_account_number or not amount:
            flash("Please fill in all required fields", 'danger')
            return render_template(
                'stablecoin/transfer.html', 
                accounts=accounts
            )
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            flash("Invalid amount", 'danger')
            return render_template(
                'stablecoin/transfer.html', 
                accounts=accounts
            )
        
        # Get source account
        source_account = StablecoinAccount.query.get(from_account_id)
        if not source_account or source_account.user_id != current_user.id:
            flash("Invalid source account", 'danger')
            return render_template(
                'stablecoin/transfer.html', 
                accounts=accounts
            )
        
        # Find destination account by account number
        destination_account = StablecoinAccount.query.filter_by(
            account_number=to_account_number, 
            is_active=True
        ).first()
        
        if not destination_account:
            flash("Destination account not found", 'danger')
            return render_template(
                'stablecoin/transfer.html', 
                accounts=accounts
            )
        
        # Perform the transfer
        transaction, error = stablecoin_service.transfer_stablecoins(
            from_account_id=source_account.id,
            to_account_id=destination_account.id,
            amount=amount,
            description=description
        )
        
        if error:
            flash(f"Transfer failed: {error}", 'danger')
            return render_template(
                'stablecoin/transfer.html', 
                accounts=accounts
            )
        
        flash("Transfer completed successfully", 'success')
        return redirect(url_for('stablecoin.account_details', account_id=source_account.id))
    
    return render_template(
        'stablecoin/transfer.html', 
        accounts=accounts
    )

@stablecoin_bp.route('/correspondent-banks')
@login_required
def correspondent_banks():
    """View correspondent banks (admin only)"""
    if current_user.role.name != 'ADMIN':
        flash("Access denied", 'danger')
        return redirect(url_for('stablecoin.index'))
    
    banks = CorrespondentBank.query.all()
    
    return render_template(
        'stablecoin/correspondent_banks.html',
        banks=banks
    )

@stablecoin_bp.route('/correspondent-banks/create', methods=['GET', 'POST'])
@login_required
def create_correspondent_bank():
    """Create a new correspondent bank (admin only)"""
    if current_user.role.name != 'ADMIN':
        flash("Access denied", 'danger')
        return redirect(url_for('stablecoin.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        bank_code = request.form.get('bank_code')
        swift_code = request.form.get('swift_code')
        ach_routing_number = request.form.get('ach_routing_number')
        
        # Validate inputs
        if not name or not bank_code:
            flash("Name and bank code are required", 'danger')
            return render_template('stablecoin/create_correspondent_bank.html')
        
        # Create the correspondent bank
        bank, error = stablecoin_service.create_correspondent_bank(
            name=name,
            bank_code=bank_code,
            swift_code=swift_code,
            ach_routing_number=ach_routing_number
        )
        
        if error:
            flash(f"Error creating correspondent bank: {error}", 'danger')
            return render_template('stablecoin/create_correspondent_bank.html')
        
        flash(f"Correspondent bank {name} created successfully", 'success')
        return redirect(url_for('stablecoin.correspondent_banks'))
    
    return render_template('stablecoin/create_correspondent_bank.html')

@stablecoin_bp.route('/settlements')
@login_required
def settlements():
    """View settlement batches (admin only)"""
    if current_user.role.name != 'ADMIN':
        flash("Access denied", 'danger')
        return redirect(url_for('stablecoin.index'))
    
    batches = SettlementBatch.query.order_by(SettlementBatch.created_at.desc()).all()
    
    return render_template(
        'stablecoin/settlements.html',
        batches=batches
    )

@stablecoin_bp.route('/settlements/create', methods=['GET', 'POST'])
@login_required
def create_settlement():
    """Create a new settlement batch (admin only)"""
    if current_user.role.name != 'ADMIN':
        flash("Access denied", 'danger')
        return redirect(url_for('stablecoin.index'))
    
    banks = CorrespondentBank.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        correspondent_bank_id = request.form.get('correspondent_bank_id')
        total_amount = request.form.get('total_amount')
        settlement_method = request.form.get('settlement_method', 'ACH')
        
        # Validate inputs
        if not correspondent_bank_id or not total_amount:
            flash("Correspondent bank and amount are required", 'danger')
            return render_template(
                'stablecoin/create_settlement.html',
                banks=banks
            )
        
        try:
            total_amount = float(total_amount)
            if total_amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            flash("Invalid amount", 'danger')
            return render_template(
                'stablecoin/create_settlement.html',
                banks=banks
            )
        
        # Create the settlement batch
        batch, error = stablecoin_service.create_settlement_batch(
            correspondent_bank_id=correspondent_bank_id,
            total_amount=total_amount,
            settlement_method=settlement_method
        )
        
        if error:
            flash(f"Error creating settlement batch: {error}", 'danger')
            return render_template(
                'stablecoin/create_settlement.html',
                banks=banks
            )
        
        flash(f"Settlement batch {batch.batch_id} created successfully", 'success')
        return redirect(url_for('stablecoin.settlements'))
    
    return render_template(
        'stablecoin/create_settlement.html',
        banks=banks
    )

@stablecoin_bp.route('/settlements/<batch_id>/complete', methods=['POST'])
@login_required
def complete_settlement(batch_id):
    """Mark a settlement batch as completed (admin only)"""
    if current_user.role.name != 'ADMIN':
        flash("Access denied", 'danger')
        return redirect(url_for('stablecoin.index'))
    
    external_reference = request.form.get('external_reference')
    
    if not external_reference:
        flash("External reference is required", 'danger')
        return redirect(url_for('stablecoin.settlements'))
    
    # Complete the settlement batch
    batch, error = stablecoin_service.complete_settlement_batch(
        batch_id=batch_id,
        external_reference=external_reference
    )
    
    if error:
        flash(f"Error completing settlement batch: {error}", 'danger')
        return redirect(url_for('stablecoin.settlements'))
    
    flash(f"Settlement batch {batch_id} completed successfully", 'success')
    return redirect(url_for('stablecoin.settlements'))

# API endpoints
@stablecoin_bp.route('/api/accounts', methods=['GET'])
@login_required
def api_get_accounts():
    """API endpoint to get user's stablecoin accounts"""
    accounts = StablecoinAccount.query.filter_by(user_id=current_user.id).all()
    
    accounts_data = [{
        'id': account.id,
        'account_number': account.account_number,
        'balance': account.balance,
        'currency': account.currency,
        'account_type': account.account_type,
        'is_active': account.is_active,
        'created_at': account.created_at.isoformat()
    } for account in accounts]
    
    return jsonify({
        'success': True,
        'accounts': accounts_data
    })

@stablecoin_bp.route('/api/accounts/<int:account_id>/transactions', methods=['GET'])
@login_required
def api_get_account_transactions(account_id):
    """API endpoint to get transactions for a stablecoin account"""
    # Get the account
    account = StablecoinAccount.query.get_or_404(account_id)
    
    # Check if the account belongs to the current user
    if account.user_id != current_user.id and current_user.role.name != 'ADMIN':
        return jsonify({
            'success': False,
            'error': "You don't have permission to view this account"
        }), 403
    
    # Get transactions
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    transactions, error = stablecoin_service.get_account_transactions(
        account_id=account_id,
        limit=limit,
        offset=offset
    )
    
    if error:
        return jsonify({
            'success': False,
            'error': error
        }), 400
    
    # Format response
    transactions_data = []
    for item in transactions:
        entry = item['entry']
        tx = item['transaction']
        transactions_data.append({
            'transaction_id': tx.transaction_id,
            'entry_type': entry.entry_type,
            'amount': entry.amount,
            'balance_after': entry.balance_after,
            'description': entry.description,
            'created_at': entry.created_at.isoformat(),
            'transaction': {
                'status': tx.status.name,
                'currency': tx.currency,
                'transaction_type': tx.transaction_type.name,
                'recipient_name': tx.recipient_name,
                'recipient_account': tx.recipient_account
            }
        })
    
    return jsonify({
        'success': True,
        'account': {
            'account_number': account.account_number,
            'balance': account.balance,
            'currency': account.currency
        },
        'transactions': transactions_data
    })

@stablecoin_bp.route('/api/transfer', methods=['POST'])
@login_required
def api_transfer():
    """API endpoint to transfer stablecoins"""
    data = request.json
    
    if not data:
        return jsonify({
            'success': False,
            'error': "Invalid request data"
        }), 400
    
    from_account_id = data.get('from_account_id')
    to_account_number = data.get('to_account_number')
    amount = data.get('amount')
    description = data.get('description')
    
    # Validate inputs
    if not from_account_id or not to_account_number or not amount:
        return jsonify({
            'success': False,
            'error': "Missing required fields"
        }), 400
    
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        return jsonify({
            'success': False,
            'error': "Invalid amount"
        }), 400
    
    # Get source account
    source_account = StablecoinAccount.query.get(from_account_id)
    if not source_account or source_account.user_id != current_user.id:
        return jsonify({
            'success': False,
            'error': "Invalid source account"
        }), 403
    
    # Find destination account by account number
    destination_account = StablecoinAccount.query.filter_by(
        account_number=to_account_number, 
        is_active=True
    ).first()
    
    if not destination_account:
        return jsonify({
            'success': False,
            'error': "Destination account not found"
        }), 404
    
    # Perform the transfer
    transaction, error = stablecoin_service.transfer_stablecoins(
        from_account_id=source_account.id,
        to_account_id=destination_account.id,
        amount=amount,
        description=description
    )
    
    if error:
        return jsonify({
            'success': False,
            'error': error
        }), 400
    
    return jsonify({
        'success': True,
        'transaction': {
            'transaction_id': transaction.transaction_id,
            'amount': transaction.amount,
            'currency': transaction.currency,
            'status': transaction.status.name,
            'created_at': transaction.created_at.isoformat()
        }
    })

def register_routes(app):
    """Register stablecoin routes with the Flask app"""
    app.register_blueprint(stablecoin_bp)
    logger.info("Stablecoin routes registered successfully")