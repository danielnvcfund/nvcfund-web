"""
NVC Platform Integration
This module provides synchronization between the nvcplatform.net account holders
and the NVC Banking Platform. It provides secure API endpoints and methods for:
1. One-way account holder synchronization from nvcplatform.net
2. Two-way transaction synchronization
3. User authentication bridging
"""

import os
import json
import logging
import requests
import hmac
import hashlib
import time
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app

from models import db, User, UserRole
from account_holder_models import AccountHolder, BankAccount, CurrencyType, AccountType, AccountStatus
from auth import api_key_required, jwt_required

logger = logging.getLogger(__name__)

# Create blueprint for NVC Platform integration API
nvc_platform_bp = Blueprint('nvc_platform', __name__)

# Constants
API_TIMEOUT = 30  # seconds
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500

# Platform connection settings
NVC_PLATFORM_API_URL = os.environ.get('NVC_PLATFORM_API_URL', 'https://www.nvcplatform.net/api')
NVC_PLATFORM_API_KEY = os.environ.get('NVC_PLATFORM_API_KEY', '')
NVC_PLATFORM_API_SECRET = os.environ.get('NVC_PLATFORM_API_SECRET', '')

def generate_signature(data, secret):
    """Generate HMAC-SHA256 signature for API requests"""
    message = json.dumps(data, sort_keys=True).encode('utf-8')
    signature = hmac.new(
        secret.encode('utf-8'),
        message,
        hashlib.sha256
    ).hexdigest()
    return signature

@nvc_platform_bp.route('/sync/status', methods=['GET'])
@api_key_required
def sync_status():
    """
    Get the current synchronization status between platforms
    """
    try:
        # Get count of synchronized accounts
        account_count = AccountHolder.query.filter(
            AccountHolder.external_id.like('NVCPLAT-%')
        ).count()
        
        # Get last sync timestamp from database or settings
        last_sync = current_app.config.get('LAST_NVC_PLATFORM_SYNC', 'Never')
        
        return jsonify({
            'status': 'success',
            'data': {
                'account_count': account_count,
                'last_sync': last_sync,
                'platform_url': NVC_PLATFORM_API_URL,
                'connection_status': 'connected' if NVC_PLATFORM_API_KEY else 'disconnected'
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get synchronization status',
            'error': str(e)
        }), 500

@nvc_platform_bp.route('/sync/accounts', methods=['POST'])
@api_key_required
def sync_accounts():
    """
    Synchronize account holders from NVC Platform to NVC Banking Platform
    """
    try:
        # Get parameters
        params = request.json or {}
        page = params.get('page', 1)
        page_size = min(params.get('page_size', DEFAULT_PAGE_SIZE), MAX_PAGE_SIZE)
        full_sync = params.get('full_sync', False)
        
        # If we have API credentials, get data from the source platform
        if NVC_PLATFORM_API_KEY and NVC_PLATFORM_API_SECRET:
            accounts = fetch_accounts_from_nvc_platform(page, page_size, full_sync)
        else:
            # For testing or if we're receiving a direct push of accounts
            accounts = params.get('accounts', [])
        
        if not accounts:
            return jsonify({
                'status': 'warning',
                'message': 'No accounts to synchronize',
                'data': {
                    'imported': 0,
                    'updated': 0,
                    'failed': 0
                }
            }), 200
            
        # Process the accounts
        results = process_account_sync(accounts)
        
        # Update last sync timestamp
        current_app.config['LAST_NVC_PLATFORM_SYNC'] = datetime.utcnow().isoformat()
        
        return jsonify({
            'status': 'success',
            'message': 'Account synchronization completed',
            'data': results
        }), 200
        
    except Exception as e:
        logger.error(f"Account synchronization error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to synchronize accounts',
            'error': str(e)
        }), 500

def fetch_accounts_from_nvc_platform(page=1, page_size=DEFAULT_PAGE_SIZE, full_sync=False):
    """
    Fetch accounts from NVC Platform API
    """
    try:
        # Prepare request data
        data = {
            'api_key': NVC_PLATFORM_API_KEY,
            'timestamp': int(time.time()),
            'page': page,
            'page_size': page_size,
            'full_sync': full_sync
        }
        
        # Generate signature
        signature = generate_signature(data, NVC_PLATFORM_API_SECRET)
        data['signature'] = signature
        
        # Make API request to NVC Platform
        url = f"{NVC_PLATFORM_API_URL}/account-holders"
        response = requests.post(
            url,
            json=data,
            timeout=API_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.error(f"NVC Platform API error: {response.status_code} - {response.text}")
            return []
            
        result = response.json()
        
        if result.get('status') != 'success':
            logger.error(f"NVC Platform API returned error: {result.get('message')}")
            return []
            
        return result.get('data', {}).get('accounts', [])
        
    except Exception as e:
        logger.error(f"Error fetching accounts from NVC Platform: {str(e)}")
        return []

def process_account_sync(accounts):
    """
    Process account data from NVC Platform and create/update account holders
    in the NVC Banking Platform
    """
    imported_count = 0
    updated_count = 0
    failed_count = 0
    
    for account_data in accounts:
        try:
            # Check if we need to import or update
            external_id = f"NVCPLAT-{account_data.get('id')}"
            
            # Lookup by external ID first
            account_holder = AccountHolder.query.filter_by(external_id=external_id).first()
            
            # If not found by external ID, try by username
            if not account_holder and 'username' in account_data:
                account_holder = AccountHolder.query.filter_by(username=account_data.get('username')).first()
            
            # If not found by username, try by email
            if not account_holder and 'email' in account_data:
                account_holder = AccountHolder.query.filter_by(email=account_data.get('email')).first()
            
            if account_holder:
                # Update existing account holder
                update_account_holder(account_holder, account_data)
                updated_count += 1
                logger.info(f"Updated account holder: {account_holder.username} (ID: {account_holder.id})")
            else:
                # Create new account holder
                account_holder = create_account_holder(account_data, external_id)
                imported_count += 1
                logger.info(f"Created account holder: {account_holder.username} (ID: {account_holder.id})")
            
            # Create or update bank accounts if provided
            if 'accounts' in account_data:
                sync_bank_accounts(account_holder, account_data.get('accounts', []))
            
        except Exception as e:
            failed_count += 1
            logger.error(f"Error processing account {account_data.get('username', 'unknown')}: {str(e)}")
    
    return {
        'imported': imported_count,
        'updated': updated_count,
        'failed': failed_count
    }

def update_account_holder(account_holder, account_data):
    """
    Update an existing account holder with data from NVC Platform
    """
    # Only update fields that are provided and not empty
    if 'name' in account_data and account_data['name']:
        account_holder.name = account_data['name']
        
    if 'email' in account_data and account_data['email']:
        account_holder.email = account_data['email']
    
    if 'username' in account_data and account_data['username']:
        account_holder.username = account_data['username']
        
    # Set the external ID if not already set
    if not account_holder.external_id.startswith('NVCPLAT-') and 'id' in account_data:
        account_holder.external_id = f"NVCPLAT-{account_data['id']}"
    
    # Handle business info
    if 'is_business' in account_data:
        account_holder.is_business = account_data['is_business']
        
        if account_holder.is_business:
            if 'business_name' in account_data:
                account_holder.business_name = account_data.get('business_name')
                
            if 'business_type' in account_data:
                account_holder.business_type = account_data.get('business_type')
                
            if 'tax_id' in account_data:
                account_holder.tax_id = account_data.get('tax_id')
    
    # Handle KYC info
    if 'kyc_verified' in account_data:
        account_holder.kyc_verified = account_data['kyc_verified']
        
    if 'aml_verified' in account_data:
        account_holder.aml_verified = account_data['aml_verified']
    
    if 'kyc_documents' in account_data:
        account_holder.kyc_documents_json = json.dumps(account_data['kyc_documents'])
    
    # Handle broker info
    if 'broker' in account_data:
        account_holder.broker = account_data.get('broker')
    
    # Update timestamp
    account_holder.updated_at = datetime.utcnow()
    
    # Commit changes
    db.session.commit()
    
    return account_holder

def create_account_holder(account_data, external_id):
    """
    Create a new account holder from NVC Platform data
    """
    account_holder = AccountHolder(
        external_id=external_id,
        name=account_data.get('name', 'Unknown Name'),
        username=account_data.get('username', f"nvcplat-{account_data.get('id', 'unknown')}"),
        email=account_data.get('email', f"nvcplat-{account_data.get('id', 'unknown')}@nvcplatform.net"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Optional fields
    if 'is_business' in account_data:
        account_holder.is_business = account_data['is_business']
        
        if account_holder.is_business:
            account_holder.business_name = account_data.get('business_name')
            account_holder.business_type = account_data.get('business_type')
            account_holder.tax_id = account_data.get('tax_id')
    
    if 'kyc_verified' in account_data:
        account_holder.kyc_verified = account_data['kyc_verified']
        
    if 'aml_verified' in account_data:
        account_holder.aml_verified = account_data['aml_verified']
    
    if 'kyc_documents' in account_data:
        account_holder.kyc_documents_json = json.dumps(account_data['kyc_documents'])
    
    if 'broker' in account_data:
        account_holder.broker = account_data.get('broker')
    
    # Add to database
    db.session.add(account_holder)
    db.session.commit()
    
    return account_holder

def sync_bank_accounts(account_holder, accounts):
    """
    Synchronize bank accounts for an account holder
    """
    for account_data in accounts:
        try:
            # Get required fields
            currency_str = account_data.get('currency', 'USD')
            
            # Try to convert to enum value
            try:
                currency_enum = getattr(CurrencyType, currency_str)
            except (AttributeError, ValueError):
                logger.warning(f"Invalid currency {currency_str}, defaulting to USD")
                currency_enum = CurrencyType.USD
            
            # Check if account already exists
            account_number = account_data.get('account_number', f"{currency_str}-{account_holder.username}")
            
            bank_account = BankAccount.query.filter_by(
                account_holder_id=account_holder.id,
                account_number=account_number
            ).first()
            
            if bank_account:
                # Update existing account
                if 'balance' in account_data:
                    bank_account.balance = float(account_data['balance'])
                    bank_account.available_balance = float(account_data['balance'])
                
                if 'account_name' in account_data:
                    bank_account.account_name = account_data['account_name']
                
                if 'account_type' in account_data:
                    try:
                        bank_account.account_type = getattr(AccountType, account_data['account_type'].upper())
                    except (AttributeError, ValueError):
                        pass
                
                if 'status' in account_data:
                    try:
                        bank_account.status = getattr(AccountStatus, account_data['status'].upper())
                    except (AttributeError, ValueError):
                        pass
                
                bank_account.updated_at = datetime.utcnow()
                
            else:
                # Create new account
                account_name = account_data.get('account_name', f"{account_holder.name} {currency_str} Account")
                
                # Determine account type
                account_type_str = account_data.get('account_type', 'CHECKING').upper()
                try:
                    account_type = getattr(AccountType, account_type_str)
                except (AttributeError, ValueError):
                    account_type = AccountType.CHECKING
                
                # Determine account status
                status_str = account_data.get('status', 'ACTIVE').upper()
                try:
                    status = getattr(AccountStatus, status_str)
                except (AttributeError, ValueError):
                    status = AccountStatus.ACTIVE
                
                # Create bank account
                bank_account = BankAccount(
                    account_number=account_number,
                    account_name=account_name,
                    account_type=account_type,
                    currency=currency_enum,
                    balance=float(account_data.get('balance', 0.0)),
                    available_balance=float(account_data.get('balance', 0.0)),
                    status=status,
                    account_holder_id=account_holder.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                db.session.add(bank_account)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing bank account for {account_holder.username}: {str(e)}")

@nvc_platform_bp.route('/sync/one-way-pull', methods=['POST'])
@api_key_required
def one_way_pull():
    """
    One-way synchronization from NVC Platform to NVC Banking Platform
    """
    try:
        # Validate API key and permissions
        # Get parameters
        params = request.json or {}
        
        # Run synchronization process
        imported, updated, failed = run_full_sync()
        
        return jsonify({
            'status': 'success',
            'message': 'One-way synchronization completed',
            'data': {
                'imported': imported,
                'updated': updated,
                'failed': failed
            }
        }), 200
        
    except Exception as e:
        logger.error(f"One-way synchronization error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to complete one-way synchronization',
            'error': str(e)
        }), 500

def run_full_sync():
    """
    Run a full synchronization process
    This is a more comprehensive process that pulls all data
    from the NVC Platform in batches
    """
    total_imported = 0
    total_updated = 0
    total_failed = 0
    
    page = 1
    more_data = True
    
    # Process in batches until no more data
    while more_data:
        accounts = fetch_accounts_from_nvc_platform(page, DEFAULT_PAGE_SIZE, True)
        
        if not accounts:
            more_data = False
            break
            
        results = process_account_sync(accounts)
        
        total_imported += results['imported']
        total_updated += results['updated']
        total_failed += results['failed']
        
        # Move to next page
        page += 1
        
        # Safety limit to prevent infinite loops
        if page > 100:
            break
    
    return total_imported, total_updated, total_failed

# Background task for periodic synchronization
def schedule_periodic_sync():
    """
    Configure a background task to periodically sync accounts
    """
    import threading
    
    def background_sync():
        while True:
            try:
                logger.info("Starting periodic account synchronization...")
                run_full_sync()
                logger.info("Periodic account synchronization completed")
            except Exception as e:
                logger.error(f"Error in periodic sync: {str(e)}")
            
            # Sleep for 1 hour between syncs
            time.sleep(3600)
    
    # Start the background thread
    sync_thread = threading.Thread(target=background_sync, daemon=True)
    sync_thread.start()
    
    logger.info("Periodic account synchronization scheduled")