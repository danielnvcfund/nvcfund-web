"""
Account Holder Routes for NVC Banking Platform
Routes for managing account holders, their addresses, phone numbers, and bank accounts.
"""

import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, Response, make_response
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from io import BytesIO
from app import db
from account_holder_models import (
    AccountHolder, Address, PhoneNumber, BankAccount,
    AccountType, AccountStatus, CurrencyType
)
from pdf_service import PDFService

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
account_holder_bp = Blueprint('account_holders', __name__, url_prefix='/account-holders')

@account_holder_bp.route('/')
@login_required
def index():
    """List all account holders with optional search and pagination"""
    search_query = request.args.get('q', '')
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    # Ensure per_page is one of the allowed values
    if per_page not in [25, 50, 100]:
        per_page = 25
    
    # Prepare the query based on search terms
    if search_query:
        # Search by name, username, email
        query = AccountHolder.query.filter(
            db.or_(
                AccountHolder.name.ilike(f'%{search_query}%'),
                AccountHolder.username.ilike(f'%{search_query}%'),
                AccountHolder.email.ilike(f'%{search_query}%')
            )
        )
    else:
        # No search query, use all records
        query = AccountHolder.query
    
    # Get paginated results
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    account_holders = pagination.items
    
    # Get account balance information
    account_holders_with_balances = []
    for holder in account_holders:
        total_usd_balance = 0
        # Get the USD account balance (most common)
        usd_account = BankAccount.query.filter_by(
            account_holder_id=holder.id,
            currency=CurrencyType.USD
        ).first()
        
        if usd_account:
            total_usd_balance = usd_account.balance
            
        # Add to our list with balance info
        account_holders_with_balances.append({
            'holder': holder,
            'usd_balance': total_usd_balance,
            'has_usd_account': usd_account is not None
        })
    
    return render_template(
        'account_holders/index.html', 
        account_holders=account_holders_with_balances,
        search_query=search_query,
        pagination=pagination,
        per_page=per_page,
        title="Account Holders"
    )

@account_holder_bp.route('/search')
@login_required
def search():
    """Advanced search for account holders and accounts"""
    search_query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')
    
    results = {
        'account_holders': [],
        'accounts': []
    }
    
    if search_query:
        # Search account holders
        if search_type in ['all', 'account_holder']:
            account_holders = AccountHolder.query.filter(
                db.or_(
                    AccountHolder.name.ilike(f'%{search_query}%'),
                    AccountHolder.username.ilike(f'%{search_query}%'),
                    AccountHolder.email.ilike(f'%{search_query}%')
                )
            ).all()
            results['account_holders'] = account_holders
        
        # Search accounts
        if search_type in ['all', 'account']:
            accounts = BankAccount.query.filter(
                db.or_(
                    BankAccount.account_number.ilike(f'%{search_query}%'),
                    BankAccount.account_name.ilike(f'%{search_query}%')
                )
            ).all()
            results['accounts'] = accounts
    
    return render_template(
        'account_holders/search.html',
        results=results,
        search_query=search_query,
        search_type=search_type,
        title="Search Results"
    )

@account_holder_bp.route('/<int:account_holder_id>')
@login_required
def view(account_holder_id):
    """View a specific account holder"""
    account_holder = AccountHolder.query.get_or_404(account_holder_id)
    return render_template(
        'account_holders/view.html',
        account_holder=account_holder,
        title=f"Account Holder: {account_holder.name}"
    )

@account_holder_bp.route('/<int:account_holder_id>/accounts')
@login_required
def accounts(account_holder_id):
    """View all accounts for an account holder"""
    account_holder = AccountHolder.query.get_or_404(account_holder_id)
    return render_template(
        'account_holders/accounts.html',
        account_holder=account_holder,
        title=f"Accounts for {account_holder.name}"
    )

@account_holder_bp.route('/account/<int:account_id>')
@login_required
def view_account(account_id):
    """View a specific bank account"""
    account = BankAccount.query.get_or_404(account_id)
    return render_template(
        'account_holders/account_details_new.html',
        account=account,
        title=f"Account: {account.account_number}"
    )

# API endpoints for account holders

@account_holder_bp.route('/api/search')
@login_required
def api_search():
    """API endpoint for searching account holders and accounts"""
    try:
        search_query = request.args.get('q', '')
        search_type = request.args.get('type', 'all')
        
        results = {
            'account_holders': [],
            'accounts': []
        }
        
        if not search_query:
            return jsonify({'success': True, 'results': results, 'message': 'No search query provided'})
            
        # Search account holders
        if search_type in ['all', 'account_holder']:
            account_holders = AccountHolder.query.filter(
                db.or_(
                    AccountHolder.name.ilike(f'%{search_query}%'),
                    AccountHolder.username.ilike(f'%{search_query}%'),
                    AccountHolder.email.ilike(f'%{search_query}%')
                )
            ).limit(50).all()
            
            for holder in account_holders:
                results['account_holders'].append({
                    'id': holder.id,
                    'name': holder.name,
                    'email': holder.email,
                    'username': holder.username,
                    'broker': holder.broker,
                    'created_at': holder.created_at.isoformat() if holder.created_at else None
                })
        
        # Search accounts
        if search_type in ['all', 'account']:
            accounts = BankAccount.query.filter(
                db.or_(
                    BankAccount.account_number.ilike(f'%{search_query}%'),
                    BankAccount.account_name.ilike(f'%{search_query}%')
                )
            ).limit(50).all()
            
            for account in accounts:
                results['accounts'].append({
                    'id': account.id,
                    'account_number': account.account_number,
                    'account_name': account.account_name,
                    'account_type': account.account_type.value,
                    'currency': account.currency.value,
                    'balance': account.balance,
                    'account_holder': {
                        'id': account.account_holder.id,
                        'name': account.account_holder.name
                    }
                })
        
        return jsonify({
            'success': True, 
            'results': results,
            'search_query': search_query,
            'search_type': search_type
        })
    except Exception as e:
        logger.error(f"Error searching: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@account_holder_bp.route('/api/account-holders')
@login_required
def api_account_holders():
    """API endpoint to get all account holders"""
    try:
        account_holders = AccountHolder.query.all()
        result = []
        for holder in account_holders:
            result.append({
                'id': holder.id,
                'name': holder.name,
                'email': holder.email,
                'username': holder.username,
                'broker': holder.broker,
                'created_at': holder.created_at.isoformat() if holder.created_at else None
            })
        return jsonify({'success': True, 'account_holders': result})
    except Exception as e:
        logger.error(f"Error retrieving account holders: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@account_holder_bp.route('/api/account-holder/<int:account_holder_id>')
@login_required
def api_account_holder(account_holder_id):
    """API endpoint to get a specific account holder with their accounts"""
    try:
        holder = AccountHolder.query.get_or_404(account_holder_id)
        
        # Get addresses
        addresses = []
        for address in holder.addresses:
            addresses.append({
                'id': address.id,
                'name': address.name,
                'line1': address.line1,
                'line2': address.line2,
                'city': address.city,
                'region': address.region,
                'zip': address.zip,
                'country': address.country,
                'formatted': address.formatted
            })
        
        # Get phone numbers
        phones = []
        for phone in holder.phone_numbers:
            phones.append({
                'id': phone.id,
                'name': phone.name,
                'number': phone.number,
                'is_primary': phone.is_primary,
                'is_mobile': phone.is_mobile
            })
        
        # Get accounts
        accounts = []
        for account in holder.accounts:
            accounts.append({
                'id': account.id,
                'account_number': account.account_number,
                'account_name': account.account_name,
                'account_type': account.account_type.value,
                'currency': account.currency.value,
                'balance': account.balance,
                'available_balance': account.available_balance,
                'status': account.status.value
            })
        
        # Compile result
        result = {
            'id': holder.id,
            'name': holder.name,
            'email': holder.email,
            'username': holder.username,
            'broker': holder.broker,
            'addresses': addresses,
            'phones': phones,
            'accounts': accounts,
            'created_at': holder.created_at.isoformat() if holder.created_at else None
        }
        
        return jsonify({'success': True, 'account_holder': result})
    except Exception as e:
        logger.error(f"Error retrieving account holder {account_holder_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@account_holder_bp.route('/account/<int:account_id>/statement')
@login_required
def account_statement(account_id):
    """Generate a PDF statement for a bank account"""
    try:
        # Get the bank account
        account = BankAccount.query.get_or_404(account_id)
        account_holder = AccountHolder.query.get(account.account_holder_id)
        
        # Parse date range parameters (if provided)
        try:
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        except (ValueError, TypeError):
            # Invalid date format, use defaults (last 30 days)
            start_date = None
            end_date = None
        
        # Generate the PDF
        pdf_data = PDFService.generate_account_statement_pdf(account_id, start_date, end_date)
        
        if not pdf_data:
            flash('Error generating account statement. Please try again.', 'danger')
            return redirect(url_for('account_holders.view_account', account_id=account_id))
        
        # Create a response with the PDF data
        filename = f"account_statement_{account.account_number}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Convert PDF data to a BytesIO object
        pdf_io = BytesIO(pdf_data)
        pdf_io.seek(0)
        
        # Create a response with the PDF
        response = make_response(send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        ))
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating account statement: {str(e)}")
        flash(f"Error generating account statement: {str(e)}", 'danger')
        return redirect(url_for('account_holders.view_account', account_id=account_id))

@account_holder_bp.route('/api/account/<int:account_id>/statement')
@login_required
def api_account_statement(account_id):
    """API endpoint to generate a PDF statement for a bank account"""
    try:
        # Parse date range parameters (if provided)
        try:
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        except (ValueError, TypeError):
            # Invalid date format, use defaults (last 30 days)
            start_date = None
            end_date = None
        
        # Generate the PDF
        pdf_data = PDFService.generate_account_statement_pdf(account_id, start_date, end_date)
        
        if not pdf_data:
            return jsonify({'success': False, 'error': 'Error generating account statement'}), 500
        
        # Convert PDF to base64 for API response
        import base64
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        return jsonify({
            'success': True,
            'account_id': account_id,
            'pdf_data': pdf_base64,
            'start_date': start_date.strftime('%Y-%m-%d') if start_date else None,
            'end_date': end_date.strftime('%Y-%m-%d') if end_date else None
        })
        
    except Exception as e:
        logger.error(f"Error generating account statement via API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@account_holder_bp.route('/api/accounts/<int:account_id>')
@login_required
def api_account(account_id):
    """API endpoint to get a specific bank account"""
    try:
        account = BankAccount.query.get_or_404(account_id)
        
        result = {
            'id': account.id,
            'account_number': account.account_number,
            'account_name': account.account_name,
            'account_type': account.account_type.value,
            'currency': account.currency.value,
            'balance': account.balance,
            'available_balance': account.available_balance,
            'status': account.status.value,
            'created_at': account.created_at.isoformat() if account.created_at else None,
            'account_holder': {
                'id': account.account_holder.id,
                'name': account.account_holder.name
            }
        }
        
        return jsonify({'success': True, 'account': result})
    except Exception as e:
        logger.error(f"Error retrieving account {account_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def register_account_holder_routes(app):
    """Register the account holder routes with the Flask app"""
    app.register_blueprint(account_holder_bp)
    logger.info("Account Holder routes registered successfully")