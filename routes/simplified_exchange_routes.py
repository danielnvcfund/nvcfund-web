"""
Simplified Exchange Routes for NVC Banking Platform

This module provides routes for the simplified currency exchange system with NVCT
as the central currency paired with major fiat and digital currencies.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from decimal import Decimal

from app import db, logger
from account_holder_models import AccountHolder, BankAccount, CurrencyType, CurrencyExchangeRate
from account_holder_models import CurrencyExchangeTransaction, ExchangeType, ExchangeStatus
import uuid
from simplified_exchange import get_exchange_rate, calculate_exchange_amount, NVCT_EXCHANGE_RATES

# Create blueprint
exchange_bp = Blueprint('exchange', __name__, url_prefix='/exchange')

@exchange_bp.route('/rates')
@login_required
def view_rates():
    """View simplified exchange rates with NVCT as the central currency"""
    # Get the latest rates from database
    nvct_rates = []
    
    for currency, rate in NVCT_EXCHANGE_RATES.items():
        # Format the rate for display
        if currency == CurrencyType.BTC or currency == CurrencyType.ETH:
            # Show these small rates with more decimal places
            formatted_rate = f"{rate:.8f}"
        else:
            formatted_rate = f"{rate:.4f}"
            
        nvct_rates.append({
            'currency': currency.value,
            'rate': formatted_rate,
            'inverse_rate': f"{(1.0/rate):.4f}" if rate > 0 else "N/A"
        })
    
    return render_template(
        'exchange/rates.html',
        nvct_rates=nvct_rates,
        title="NVCT Exchange Rates"
    )

@exchange_bp.route('/convert', methods=['GET', 'POST'])
@login_required
def convert():
    """Convert between currencies with NVCT as the intermediary"""
    # Get all accounts for the current user
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    if not account_holder:
        flash("No account holder found for this user", "error")
        return redirect(url_for('web.main.dashboard'))
        
    accounts = BankAccount.query.filter_by(
        account_holder_id=account_holder.id,
        status='active'
    ).all()
    
    if request.method == 'POST':
        # Get form data
        from_account_id = request.form.get('from_account')
        to_account_id = request.form.get('to_account')
        amount = request.form.get('amount')
        
        # Validate inputs
        errors = []
        if not from_account_id:
            errors.append("Please select a source account")
        if not to_account_id:
            errors.append("Please select a destination account")
        if not amount:
            errors.append("Please enter an amount to convert")
        else:
            try:
                amount = Decimal(amount)
                if amount <= 0:
                    errors.append("Amount must be greater than zero")
            except:
                errors.append("Amount must be a valid number")
                
        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for('exchange.convert'))
            
        # Get the accounts
        from_account = BankAccount.query.get(from_account_id)
        to_account = BankAccount.query.get(to_account_id)
        
        if not from_account or not to_account:
            flash("One or both accounts not found", "error")
            return redirect(url_for('exchange.convert'))
            
        # Check if accounts belong to the current user
        if from_account.account_holder_id != account_holder.id or to_account.account_holder_id != account_holder.id:
            flash("You can only convert between your own accounts", "error")
            return redirect(url_for('exchange.convert'))
            
        # Check sufficient balance
        if from_account.balance < float(amount):
            flash("Insufficient balance in the source account", "error")
            return redirect(url_for('exchange.convert'))
            
        # Get exchange rate and calculate amount
        converted_amount, rate = calculate_exchange_amount(
            from_account.currency,
            to_account.currency,
            float(amount)
        )
        
        if converted_amount is None or rate is None:
            flash("Currency conversion not available for these currencies", "error")
            return redirect(url_for('exchange.convert'))
            
        # Determine exchange type
        if from_account.currency == CurrencyType.NVCT:
            if to_account.currency in [CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, CurrencyType.NGN]:
                exchange_type = ExchangeType.NVCT_TO_FIAT
            elif to_account.currency in [CurrencyType.BTC, CurrencyType.ETH, CurrencyType.USDT]:
                exchange_type = ExchangeType.NVCT_TO_CRYPTO
            elif to_account.currency == CurrencyType.AFD1:
                exchange_type = ExchangeType.NVCT_TO_AFD1
            elif to_account.currency == CurrencyType.SFN:
                exchange_type = ExchangeType.NVCT_TO_SFN
            elif to_account.currency == CurrencyType.AKLUMI:
                exchange_type = ExchangeType.NVCT_TO_AKLUMI
            else:
                exchange_type = ExchangeType.NVCT_TO_FIAT
        elif to_account.currency == CurrencyType.NVCT:
            if from_account.currency in [CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, CurrencyType.NGN]:
                exchange_type = ExchangeType.FIAT_TO_NVCT
            elif from_account.currency in [CurrencyType.BTC, CurrencyType.ETH, CurrencyType.USDT]:
                exchange_type = ExchangeType.CRYPTO_TO_NVCT
            elif from_account.currency == CurrencyType.AFD1:
                exchange_type = ExchangeType.AFD1_TO_NVCT
            elif from_account.currency == CurrencyType.SFN:
                exchange_type = ExchangeType.SFN_TO_NVCT
            elif from_account.currency == CurrencyType.AKLUMI:
                exchange_type = ExchangeType.AKLUMI_TO_NVCT
            else:
                exchange_type = ExchangeType.FIAT_TO_NVCT
        elif from_account.currency in [CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, CurrencyType.NGN] and \
             to_account.currency in [CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, CurrencyType.NGN]:
            exchange_type = ExchangeType.FIAT_TO_FIAT
        elif from_account.currency in [CurrencyType.BTC, CurrencyType.ETH, CurrencyType.USDT] and \
             to_account.currency in [CurrencyType.BTC, CurrencyType.ETH, CurrencyType.USDT]:
            exchange_type = ExchangeType.CRYPTO_TO_CRYPTO
        else:
            # Default for other combinations
            exchange_type = ExchangeType.FIAT_TO_FIAT
        
        # Create a reference number for the transaction
        reference_number = "EX-" + uuid.uuid4().hex[:8].upper()
        
        try:
            # Create exchange transaction record
            exchange_tx = CurrencyExchangeTransaction(
                exchange_type=exchange_type,
                from_currency=from_account.currency,
                to_currency=to_account.currency,
                from_amount=float(amount),
                to_amount=converted_amount,
                rate_applied=rate,
                fee_amount=0.0,  # No fee for now
                fee_currency=from_account.currency,
                status=ExchangeStatus.COMPLETED,
                reference_number=reference_number,
                notes=f"Currency exchange from {from_account.currency.value} to {to_account.currency.value}",
                account_holder_id=account_holder.id,
                from_account_id=from_account.id,
                to_account_id=to_account.id,
                completed_at=db.func.now()
            )
            
            # Update account balances
            from_account.balance -= float(amount)
            to_account.balance += converted_amount
            
            # Update last transaction timestamp
            from_account.last_transaction_at = db.func.now()
            to_account.last_transaction_at = db.func.now()
            
            # Save changes
            db.session.add(exchange_tx)
            db.session.commit()
            
            flash(f"Successfully converted {amount} {from_account.currency.value} to {converted_amount:.2f} {to_account.currency.value}", "success")
            return redirect(url_for('exchange.history'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing currency exchange: {str(e)}")
            flash("An error occurred while processing your exchange", "error")
            return redirect(url_for('exchange.convert'))
    
    # GET request - show form
    return render_template(
        'exchange/convert.html',
        accounts=accounts,
        title="Convert Currency"
    )

@exchange_bp.route('/history')
@login_required
def history():
    """View exchange transaction history"""
    account_holder = AccountHolder.query.filter_by(user_id=current_user.id).first()
    if not account_holder:
        flash("No account holder found for this user", "error")
        return redirect(url_for('web.main.dashboard'))
        
    # Get exchange transactions for this account holder
    transactions = CurrencyExchangeTransaction.query.filter_by(
        account_holder_id=account_holder.id
    ).order_by(CurrencyExchangeTransaction.created_at.desc()).all()
    
    return render_template(
        'exchange/history.html',
        transactions=transactions,
        title="Exchange History"
    )

@exchange_bp.route('/rate/<from_currency>/<to_currency>')
@login_required
def get_rate(from_currency, to_currency):
    """API endpoint to get exchange rate between two currencies"""
    try:
        # Convert string inputs to enum values
        from_currency_enum = getattr(CurrencyType, from_currency.upper())
        to_currency_enum = getattr(CurrencyType, to_currency.upper())
        
        # Get the rate
        rate = get_exchange_rate(from_currency_enum, to_currency_enum)
        
        if rate is None:
            return jsonify({'success': False, 'error': 'Rate not available'})
            
        return jsonify({
            'success': True,
            'from_currency': from_currency.upper(),
            'to_currency': to_currency.upper(),
            'rate': rate
        })
    except (AttributeError, ValueError) as e:
        return jsonify({'success': False, 'error': f'Invalid currency code: {str(e)}'})
    except Exception as e:
        logger.error(f"Error getting exchange rate: {str(e)}")
        return jsonify({'success': False, 'error': 'System error'})

def register_routes(app):
    """Register the exchange routes with the application"""
    app.register_blueprint(exchange_bp)
    logger.info("Simplified exchange routes registered successfully")