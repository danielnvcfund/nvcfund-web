"""
Client Dashboard Routes
This module contains routes for the client dashboard interface
"""

import logging
import json
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required

from app import db
from models import (
    User, Transaction, TransactionStatus, TransactionType, 
    FinancialInstitution, FinancialInstitutionType
)
from account_holder_models import (
    AccountHolder, BankAccount, Address, PhoneNumber
)
from auth import generate_jwt_token

logger = logging.getLogger(__name__)

# Create blueprint
client_dashboard_bp = Blueprint('client_dashboard', __name__, url_prefix='/client')

# Custom JSON encoder to handle Decimal values
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super(DecimalEncoder, self).default(obj)

@client_dashboard_bp.route('/dashboard')
@login_required
def client_dashboard():
    """Client dashboard route"""
    # Get the user from current_user (provided by Flask-Login)
    user = current_user
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=user.id)\
        .order_by(Transaction.created_at.desc())\
        .limit(5).all()
    
    # Get total transactions
    total_transactions = Transaction.query.filter_by(user_id=user.id).count()
    
    # Get account holders associated with this user (if any)
    account_holders = AccountHolder.query.filter_by(user_id=user.id).all()
    
    # Generate a fresh JWT token for the user
    jwt_token = generate_jwt_token(user.id)
    
    # Get current date for analytics display
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)
    
    # Create basic analytics structure
    analytics = {
        'days': 30,
        'start_date': thirty_days_ago.strftime('%Y-%m-%d'),
        'end_date': today.strftime('%Y-%m-%d'),
        'total_transactions': total_transactions,
        'by_type': {},
        'by_status': {},
        'by_date': {},
        'raw_data': []
    }
    
    # Pre-serialize the analytics data
    try:
        analytics_json = json.dumps(analytics, cls=DecimalEncoder)
    except Exception as e:
        logger.error(f"Error serializing analytics data: {str(e)}")
        analytics_json = json.dumps({
            'days': 30,
            'start_date': thirty_days_ago.strftime('%Y-%m-%d'),
            'end_date': today.strftime('%Y-%m-%d'),
            'total_transactions': 0,
            'by_type': {},
            'by_status': {},
            'by_date': {},
            'raw_data': []
        })
    
    return render_template(
        'client_dashboard.html',
        user=user,
        recent_transactions=recent_transactions,
        account_holders=account_holders,
        analytics_json=analytics_json,
        jwt_token=jwt_token
    )

def register_client_dashboard_routes(app):
    """Register client dashboard routes with the app"""
    app.register_blueprint(client_dashboard_bp)
    logger.info("Client dashboard routes registered successfully")