"""
Currency Exchange Routes
This module provides the routes for currency exchange operations between various currencies
with a focus on NVCT as the primary pairing.
"""

import logging
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import User
from account_holder_models import (
    AccountHolder, 
    BankAccount, 
    CurrencyType, 
    CurrencyExchangeRate,
    CurrencyExchangeTransaction,
    ExchangeType,
    ExchangeStatus
)
from currency_exchange_service import CurrencyExchangeService

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
currency_exchange_bp = Blueprint('currency_exchange', __name__, url_prefix='/exchange')

@currency_exchange_bp.route('/')
@login_required
def index():
    """Main currency exchange dashboard"""
    # Get all active exchange rates
    exchange_rates = CurrencyExchangeRate.query.filter_by(is_active=True).all()
    
    # Organize rates by base currency (from_currency)
    organized_rates = {}
    for rate in exchange_rates:
        if rate.from_currency.value not in organized_rates:
            organized_rates[rate.from_currency.value] = []
        
        organized_rates[rate.from_currency.value].append({
            'to_currency': rate.to_currency.value,
            'rate': rate.rate,
            'inverse_rate': rate.inverse_rate,
            'last_updated': rate.last_updated
        })
    
    # Get all currency types for the form
    currency_types = [(c.value, c.value) for c in CurrencyType]
    
    # For emphasis, put NVCT at the top of the list
    nvct_entry = None
    for i, (value, label) in enumerate(currency_types):
        if value == 'NVCT':
            nvct_entry = currency_types.pop(i)
            break
    
    if nvct_entry:
        currency_types.insert(0, nvct_entry)
    
    return render_template(
        'currency_exchange/index.html',
        exchange_rates=organized_rates,
        currency_types=currency_types,
        title="Currency Exchange"
    )

@currency_exchange_bp.route('/rates')
@login_required
def view_rates():
    """View all exchange rates"""
    rates = CurrencyExchangeRate.query.filter_by(is_active=True).all()
    return render_template(
        'currency_exchange/rates.html',
        rates=rates,
        title="Exchange Rates"
    )

@currency_exchange_bp.route('/rates/update', methods=['POST'])
@login_required
def update_rate():
    """Update an exchange rate"""
    try:
        from_currency = request.form.get('from_currency')
        to_currency = request.form.get('to_currency')
        rate = float(request.form.get('rate'))
        
        if not from_currency or not to_currency or not rate:
            flash('Missing required fields', 'danger')
            return redirect(url_for('currency_exchange.view_rates'))
            
        # Convert to enums
        from_currency_enum = CurrencyType[from_currency]
        to_currency_enum = CurrencyType[to_currency]
        
        # Check if the currencies are the same
        if from_currency_enum == to_currency_enum:
            flash('Source and destination currencies cannot be the same', 'danger')
            return redirect(url_for('currency_exchange.view_rates'))
            
        # Update the rate
        result = CurrencyExchangeService.update_exchange_rate(
            from_currency_enum, 
            to_currency_enum, 
            rate,
            source="manual_update"
        )
        
        if result:
            flash(f'Exchange rate updated: {from_currency} to {to_currency} = {rate}', 'success')
        else:
            flash('Error updating exchange rate', 'danger')
            
        return redirect(url_for('currency_exchange.view_rates'))
    except (ValueError, KeyError) as e:
        flash(f'Invalid input: {str(e)}', 'danger')
        return redirect(url_for('currency_exchange.view_rates'))
    except Exception as e:
        logger.error(f"Error updating exchange rate: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('currency_exchange.view_rates'))

@currency_exchange_bp.route('/initialize-defaults', methods=['POST'])
@login_required
def initialize_default_rates():
    """Initialize default exchange rates"""
    result = CurrencyExchangeService.initialize_default_rates()
    
    if result:
        flash('Default exchange rates initialized successfully', 'success')
    else:
        flash('Error initializing default exchange rates', 'danger')
        
    return redirect(url_for('currency_exchange.view_rates'))

@currency_exchange_bp.route('/account-holder/<int:account_holder_id>')
@login_required
def account_holder_exchange(account_holder_id):
    """Exchange view for a specific account holder"""
    try:
        # Get the account holder
        account_holder = AccountHolder.query.get_or_404(account_holder_id)
        
        # Get all accounts for this account holder
        accounts = BankAccount.query.filter_by(account_holder_id=account_holder_id).all()
        
        # Get active exchange rates
        exchange_rates = CurrencyExchangeRate.query.filter_by(is_active=True).all()
        
        # Get exchange history
        exchange_history = CurrencyExchangeService.get_exchange_history(account_holder_id)
        
        return render_template(
            'currency_exchange/account_holder_exchange.html',
            account_holder=account_holder,
            accounts=accounts,
            exchange_rates=exchange_rates,
            exchange_history=exchange_history,
            title=f"Currency Exchange for {account_holder.name}"
        )
    except Exception as e:
        logger.error(f"Error loading account holder exchange page: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('account_holders.index'))

@currency_exchange_bp.route('/perform-exchange', methods=['POST'])
@login_required
def perform_exchange():
    """Perform a currency exchange between accounts"""
    try:
        account_holder_id = int(request.form.get('account_holder_id'))
        from_account_id = int(request.form.get('from_account_id'))
        to_account_id = int(request.form.get('to_account_id'))
        amount = float(request.form.get('amount'))
        
        if not account_holder_id or not from_account_id or not to_account_id or not amount:
            flash('Missing required fields', 'danger')
            return redirect(url_for('currency_exchange.account_holder_exchange', account_holder_id=account_holder_id))
            
        # Check if the accounts are the same
        if from_account_id == to_account_id:
            flash('Source and destination accounts cannot be the same', 'danger')
            return redirect(url_for('currency_exchange.account_holder_exchange', account_holder_id=account_holder_id))
            
        # Perform the exchange
        result = CurrencyExchangeService.perform_exchange(
            account_holder_id, 
            from_account_id, 
            to_account_id, 
            amount
        )
        
        if result['success']:
            flash(
                f"Exchange successful: {result['from_amount']} {result['from_currency']} "
                f"to {result['to_amount']} {result['to_currency']} (Reference: {result['reference']})", 
                'success'
            )
        else:
            flash(f"Exchange failed: {result.get('error', 'Unknown error')}", 'danger')
            
        return redirect(url_for('currency_exchange.account_holder_exchange', account_holder_id=account_holder_id))
    except ValueError as e:
        flash(f'Invalid input: {str(e)}', 'danger')
        return redirect(url_for('currency_exchange.index'))
    except Exception as e:
        logger.error(f"Error performing exchange: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('currency_exchange.index'))

# API endpoints

@currency_exchange_bp.route('/api/rates')
@login_required
def api_rates():
    """API endpoint to get all exchange rates"""
    try:
        rates = CurrencyExchangeRate.query.filter_by(is_active=True).all()
        
        result = []
        for rate in rates:
            result.append({
                'id': rate.id,
                'from_currency': rate.from_currency.value,
                'to_currency': rate.to_currency.value,
                'rate': rate.rate,
                'inverse_rate': rate.inverse_rate,
                'last_updated': rate.last_updated.isoformat() if rate.last_updated else None
            })
            
        return jsonify({'success': True, 'rates': result})
    except Exception as e:
        logger.error(f"Error retrieving exchange rates: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@currency_exchange_bp.route('/api/calculate', methods=['POST'])
@login_required
def api_calculate():
    """API endpoint to calculate an exchange without performing it"""
    try:
        data = request.get_json()
        
        from_currency = data.get('from_currency')
        to_currency = data.get('to_currency')
        amount = float(data.get('amount', 0))
        
        if not from_currency or not to_currency or not amount:
            return jsonify({
                'success': False, 
                'error': 'Missing required fields'
            }), 400
            
        # Get exchange rate
        from_currency_enum = CurrencyType[from_currency]
        to_currency_enum = CurrencyType[to_currency]
        
        rate = CurrencyExchangeService.get_exchange_rate(from_currency_enum, to_currency_enum)
        
        if not rate:
            return jsonify({
                'success': False, 
                'error': 'Exchange rate not available for these currencies'
            }), 400
            
        # Calculate converted amount
        converted_amount = amount * rate
        
        # Calculate fee (0.5% by default)
        fee_percentage = 0.5
        fee_amount = (amount * fee_percentage) / 100
        
        # Amount after fee
        amount_after_fee = amount - fee_amount
        final_converted_amount = amount_after_fee * rate
        
        return jsonify({
            'success': True,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'rate': rate,
            'amount': amount,
            'fee_percentage': fee_percentage,
            'fee_amount': fee_amount,
            'amount_after_fee': amount_after_fee,
            'converted_amount': final_converted_amount
        })
    except (ValueError, KeyError) as e:
        return jsonify({'success': False, 'error': f'Invalid input: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error calculating exchange: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@currency_exchange_bp.route('/api/perform', methods=['POST'])
@login_required
def api_perform_exchange():
    """API endpoint to perform a currency exchange"""
    try:
        data = request.get_json()
        
        account_holder_id = int(data.get('account_holder_id'))
        from_account_id = int(data.get('from_account_id'))
        to_account_id = int(data.get('to_account_id'))
        amount = float(data.get('amount', 0))
        
        if not account_holder_id or not from_account_id or not to_account_id or not amount:
            return jsonify({
                'success': False, 
                'error': 'Missing required fields'
            }), 400
            
        # Perform the exchange
        result = CurrencyExchangeService.perform_exchange(
            account_holder_id, 
            from_account_id, 
            to_account_id, 
            amount
        )
        
        return jsonify(result)
    except (ValueError, KeyError) as e:
        return jsonify({'success': False, 'error': f'Invalid input: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error performing exchange: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@currency_exchange_bp.route('/api/history/<int:account_holder_id>')
@login_required
def api_exchange_history(account_holder_id):
    """API endpoint to get exchange history for an account holder"""
    try:
        limit = int(request.args.get('limit', 50))
        
        transactions = CurrencyExchangeService.get_exchange_history(account_holder_id, limit)
        
        result = []
        for tx in transactions:
            result.append({
                'id': tx.id,
                'reference_number': tx.reference_number,
                'exchange_type': tx.exchange_type.value,
                'from_currency': tx.from_currency.value,
                'to_currency': tx.to_currency.value,
                'from_amount': tx.from_amount,
                'to_amount': tx.to_amount,
                'rate_applied': tx.rate_applied,
                'fee_amount': tx.fee_amount,
                'status': tx.status.value,
                'created_at': tx.created_at.isoformat() if tx.created_at else None,
                'completed_at': tx.completed_at.isoformat() if tx.completed_at else None
            })
            
        return jsonify({'success': True, 'transactions': result})
    except Exception as e:
        logger.error(f"Error retrieving exchange history: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def register_currency_exchange_routes(app):
    """Register the currency exchange routes with the Flask app"""
    app.register_blueprint(currency_exchange_bp)
    logger.info("Currency Exchange routes registered successfully")