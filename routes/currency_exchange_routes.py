"""
Currency Exchange Routes
This module provides routes for currency exchange operations
"""

import logging
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from account_holder_models import CurrencyType, ExchangeType, ExchangeStatus, CurrencyExchangeTransaction
from currency_exchange_service import CurrencyExchangeService
from app import db
from forms import CurrencyExchangeForm
from models import TreasuryAccount  # For account selection

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blueprint for currency exchange
currency_exchange = Blueprint('currency_exchange', __name__, url_prefix='/currency-exchange')

@currency_exchange.route('/')
@login_required
def index():
    """Display the currency exchange main page"""
    exchange_form = CurrencyExchangeForm()
    
    # Fetch recent exchange transactions
    recent_transactions = CurrencyExchangeTransaction.query.filter_by(
        account_holder_id=current_user.account_holder.id
    ).order_by(CurrencyExchangeTransaction.created_at.desc()).limit(10).all()
    
    return render_template('currency_exchange/index.html', 
                          form=exchange_form, 
                          transactions=recent_transactions,
                          title="Currency Exchange")

@currency_exchange.route('/get_rate', methods=['POST'])
@login_required
def get_rate():
    """API endpoint to get exchange rate"""
    from_currency = request.form.get('from_currency')
    to_currency = request.form.get('to_currency')
    amount = float(request.form.get('amount', 1.0))
    
    if not from_currency or not to_currency:
        return jsonify({'error': 'Missing currency parameters'}), 400
    
    try:
        # Convert string to enum
        from_currency_enum = CurrencyType[from_currency]
        to_currency_enum = CurrencyType[to_currency]
        
        # Create a local exchange service instance
        local_exchange_service = CurrencyExchangeService(db)
        
        # Get exchange rate
        rate = local_exchange_service.get_exchange_rate(from_currency_enum, to_currency_enum)
        converted_amount = amount * rate
        fee = local_exchange_service.calculate_fee(amount, from_currency_enum)
        net_amount = converted_amount - fee if from_currency == to_currency else converted_amount
        
        return jsonify({
            'rate': rate,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'amount': amount,
            'converted_amount': converted_amount,
            'fee': fee,
            'net_amount': net_amount,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error getting exchange rate: {str(e)}")
        return jsonify({'error': str(e)}), 500

@currency_exchange.route('/convert', methods=['POST'])
@login_required
def convert():
    """Process currency exchange"""
    form = CurrencyExchangeForm()
    
    if form.validate_on_submit():
        try:
            # Get form data
            from_currency = CurrencyType[form.from_currency.data]
            to_currency = CurrencyType[form.to_currency.data]
            amount = float(form.amount.data)
            
            # Get accounts
            from_account = form.from_account.data
            to_account = form.to_account.data
            
            # Create a local exchange service instance
            local_exchange_service = CurrencyExchangeService(db)
            
            # Get exchange rate
            rate = local_exchange_service.get_exchange_rate(from_currency, to_currency)
            converted_amount = amount * rate
            fee = local_exchange_service.calculate_fee(amount, from_currency)
            
            # Create transaction record
            exchange_tx = CurrencyExchangeTransaction(
                account_holder_id=current_user.account_holder.id,
                from_account_id=from_account,
                to_account_id=to_account,
                exchange_type=get_exchange_type(from_currency, to_currency),
                from_currency=from_currency,
                to_currency=to_currency,
                from_amount=amount,
                to_amount=converted_amount,
                rate_applied=rate,
                fee_amount=fee,
                fee_currency=from_currency,
                status=ExchangeStatus.PENDING,
                reference_number=f"EX-{datetime.now().strftime('%Y%m%d%H%M%S')}-{current_user.id}",
                notes=form.notes.data
            )
            
            db.session.add(exchange_tx)
            db.session.commit()
            
            # Update account balances
            # This would be where you update the balances for the accounts
            # This is a simplified version - in production, you'd want to use proper
            # transaction isolation and rollback mechanisms
            
            # Mark transaction as completed
            exchange_tx.status = ExchangeStatus.COMPLETED
            exchange_tx.completed_at = datetime.now()
            db.session.commit()
            
            flash(f"Successfully exchanged {amount} {from_currency.value} to {converted_amount} {to_currency.value}", "success")
            return redirect(url_for('currency_exchange.index'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing currency exchange: {str(e)}")
            flash(f"Error processing exchange: {str(e)}", "danger")
    
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")
    
    return redirect(url_for('currency_exchange.index'))

@currency_exchange.route('/rates')
@login_required
def rates():
    """Display exchange rates"""
    # Get major currencies
    major_currencies = [
        CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, 
        CurrencyType.JPY, CurrencyType.CAD, CurrencyType.CHF,
        CurrencyType.NVCT, CurrencyType.AFD1, CurrencyType.SFN
    ]
    
    # Create a local exchange service instance
    local_exchange_service = CurrencyExchangeService(db)
    
    # Create a matrix of rates
    rate_matrix = []
    
    for base in major_currencies:
        rates_row = {'base': base.value, 'rates': {}}
        for target in major_currencies:
            if base != target:
                rate = local_exchange_service.get_exchange_rate(base, target)
                rates_row['rates'][target.value] = rate
        
        rate_matrix.append(rates_row)
    
    return render_template('currency_exchange/rates.html', 
                          rate_matrix=rate_matrix,
                          currencies=major_currencies,
                          title="Exchange Rates")

@currency_exchange.route('/transactions')
@login_required
def transactions():
    """Display transaction history"""
    # Get transaction status filter
    status_filter = request.args.get('status', None)
    
    # Base query
    query = CurrencyExchangeTransaction.query.filter_by(
        account_holder_id=current_user.account_holder.id
    )
    
    # Apply status filter if provided
    if status_filter and status_filter != 'all':
        query = query.filter_by(status=ExchangeStatus[status_filter])
    
    # Fetch transactions with pagination
    page = int(request.args.get('page', 1))
    per_page = 20
    pagination = query.order_by(CurrencyExchangeTransaction.created_at.desc()).paginate(
        page=page, per_page=per_page
    )
    
    return render_template('currency_exchange/transactions.html',
                          pagination=pagination,
                          title="Exchange Transactions",
                          status_options=ExchangeStatus)

def get_exchange_type(from_currency: CurrencyType, to_currency: CurrencyType) -> ExchangeType:
    """Determine exchange type based on currencies"""
    # Standard Fiat currencies
    fiat_currencies = [
        CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, 
        CurrencyType.JPY, CurrencyType.CHF, CurrencyType.CAD,
        # And other fiat currencies...
    ]
    
    # Crypto currencies
    crypto_currencies = [
        CurrencyType.BTC, CurrencyType.ETH, CurrencyType.USDT,
        CurrencyType.BNB, CurrencyType.SOL, CurrencyType.XRP,
        # And other cryptocurrencies...
    ]
    
    # Determine exchange type
    if from_currency == CurrencyType.NVCT and to_currency in fiat_currencies:
        return ExchangeType.NVCT_TO_FIAT
    elif from_currency in fiat_currencies and to_currency == CurrencyType.NVCT:
        return ExchangeType.FIAT_TO_NVCT
    elif from_currency == CurrencyType.NVCT and to_currency in crypto_currencies:
        return ExchangeType.NVCT_TO_CRYPTO
    elif from_currency in crypto_currencies and to_currency == CurrencyType.NVCT:
        return ExchangeType.CRYPTO_TO_NVCT
    elif from_currency in fiat_currencies and to_currency in fiat_currencies:
        return ExchangeType.FIAT_TO_FIAT
    elif from_currency in crypto_currencies and to_currency in crypto_currencies:
        return ExchangeType.CRYPTO_TO_CRYPTO
    elif from_currency == CurrencyType.NVCT and to_currency == CurrencyType.AFD1:
        return ExchangeType.NVCT_TO_AFD1
    elif from_currency == CurrencyType.AFD1 and to_currency == CurrencyType.NVCT:
        return ExchangeType.AFD1_TO_NVCT
    elif from_currency == CurrencyType.AFD1 and to_currency in fiat_currencies:
        return ExchangeType.AFD1_TO_FIAT
    elif from_currency in fiat_currencies and to_currency == CurrencyType.AFD1:
        return ExchangeType.FIAT_TO_AFD1
    elif from_currency == CurrencyType.NVCT and to_currency == CurrencyType.SFN:
        return ExchangeType.NVCT_TO_SFN
    elif from_currency == CurrencyType.SFN and to_currency == CurrencyType.NVCT:
        return ExchangeType.SFN_TO_NVCT
    elif from_currency == CurrencyType.SFN and to_currency in fiat_currencies:
        return ExchangeType.SFN_TO_FIAT
    elif from_currency in fiat_currencies and to_currency == CurrencyType.SFN:
        return ExchangeType.FIAT_TO_SFN
    elif from_currency == CurrencyType.NVCT and to_currency == CurrencyType.AKLUMI:
        return ExchangeType.NVCT_TO_AKLUMI
    elif from_currency == CurrencyType.AKLUMI and to_currency == CurrencyType.NVCT:
        return ExchangeType.AKLUMI_TO_NVCT
    elif from_currency == CurrencyType.AKLUMI and to_currency in fiat_currencies:
        return ExchangeType.AKLUMI_TO_FIAT
    elif from_currency in fiat_currencies and to_currency == CurrencyType.AKLUMI:
        return ExchangeType.FIAT_TO_AKLUMI
    else:
        # Default to FIAT_TO_FIAT
        return ExchangeType.FIAT_TO_FIAT


@currency_exchange.route('/get_accounts/<string:currency>')
@login_required
def get_accounts_by_currency(currency):
    """Get accounts based on currency"""
    try:
        currency_enum = CurrencyType[currency]
        accounts = TreasuryAccount.query.filter_by(
            account_holder_id=current_user.account_holder.id,
            currency=currency_enum
        ).all()
        
        result = [{'id': acc.id, 'name': acc.name, 'balance': float(acc.available_balance)} for acc in accounts]
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting accounts for currency {currency}: {str(e)}")
        return jsonify({'error': str(e)}), 500


# This function is called from app.py to register all routes
def register_currency_exchange_routes(app):
    """Register currency exchange routes with the Flask app"""
    # Initialize the exchange service
    try:
        # Register the blueprint
        app.register_blueprint(currency_exchange)
        
        # Define API routes that should be available outside the blueprint
        
        # Add API endpoints
        @app.route('/api/exchange/rates', methods=['GET'])
        def api_get_rates():
            """API endpoint to get all exchange rates"""
            try:
                # Get major currencies
                major_currencies = [
                    CurrencyType.USD, CurrencyType.EUR, CurrencyType.GBP, 
                    CurrencyType.JPY, CurrencyType.NVCT, CurrencyType.AFD1
                ]
                
                # Create a local exchange service instance
                local_exchange_service = CurrencyExchangeService(db)
                
                # Create rate matrix
                rates = {}
                for base in major_currencies:
                    rates[base.value] = {}
                    for target in major_currencies:
                        if base != target:
                            rate = local_exchange_service.get_exchange_rate(base, target)
                            rates[base.value][target.value] = rate
                
                return jsonify({
                    'status': 'success',
                    'rates': rates,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"API error getting exchange rates: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        # Initialize default rates if needed
        @app.route('/admin/currency/initialize-rates', methods=['POST'])
        @login_required
        def initialize_default_rates():
            """Initialize default exchange rates"""
            try:
                # Check if user is admin
                if not current_user.is_admin():
                    flash("Admin access required", "danger")
                    return redirect(url_for('index'))
                
                # Initialize rates
                count = CurrencyExchangeService.initialize_default_rates(db)
                
                flash(f"Successfully initialized {count} default exchange rates", "success")
                return redirect(url_for('currency_exchange.rates'))
            except Exception as e:
                logger.error(f"Error initializing default rates: {str(e)}")
                flash(f"Error initializing rates: {str(e)}", "danger")
                return redirect(url_for('currency_exchange.rates'))
        
        logger.info("Currency exchange routes registered successfully")
        return True
    except Exception as e:
        logger.error(f"Error registering currency exchange routes: {str(e)}")
        return False