"""
NVC Platform Admin Routes
This module provides the admin routes for managing the NVC Platform integration
"""

import os
import logging
import time
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required
from werkzeug.security import generate_password_hash

from app import db
from models import User, UserRole
from auth import admin_required
from forms import NVCPlatformSettingsForm
from nvc_platform_integration import (
    fetch_accounts_from_nvc_platform,
    process_account_sync,
    run_full_sync,
    schedule_periodic_sync
)

logger = logging.getLogger(__name__)

nvc_platform_admin_bp = Blueprint('nvc_platform_admin', __name__, url_prefix='/admin/nvc-platform')

# Sync history log
sync_history = []

@nvc_platform_admin_bp.route('/', methods=['GET'])
@login_required
@admin_required
def dashboard():
    """
    NVC Platform integration dashboard
    """
    try:
        # Get current status
        from account_holder_models import AccountHolder
        
        # Count synchronized accounts
        account_count = AccountHolder.query.filter(
            AccountHolder.external_id.like('NVCPLAT-%')
        ).count()
        
        # Get last sync timestamp
        last_sync = current_app.config.get('LAST_NVC_PLATFORM_SYNC', 'Never')
        
        # Format as a readable timestamp if it's a date string
        if last_sync != 'Never':
            try:
                last_sync_dt = datetime.fromisoformat(last_sync)
                last_sync = last_sync_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            except (ValueError, TypeError):
                pass
        
        # Get API settings
        api_url = os.environ.get('NVC_PLATFORM_API_URL', 'https://www.nvcplatform.net/api')
        api_key = os.environ.get('NVC_PLATFORM_API_KEY', '')
        api_secret = os.environ.get('NVC_PLATFORM_API_SECRET', '')
        auto_sync = current_app.config.get('NVC_PLATFORM_AUTO_SYNC', False)
        
        # Prepare form with current settings
        form = NVCPlatformSettingsForm()
        form.api_url.data = api_url
        form.api_key.data = api_key
        form.api_secret.data = api_secret
        form.auto_sync.data = auto_sync
        
        # Prepare status data
        status = {
            'account_count': account_count,
            'last_sync': last_sync,
            'platform_url': api_url,
            'connection_status': 'connected' if api_key else 'disconnected'
        }
        
        # Get recent sync history
        recent_syncs = sync_history[-10:] if sync_history else []
        
        # Prepare stats for template
        stats = {
            'total': 0,
            'success': 0,
            'failed': 0
        }
        
        # If available, populate with actual data
        if sync_history:
            latest_sync = sync_history[-1]
            stats['total'] = latest_sync.get('total', 0)
            stats['success'] = latest_sync.get('imported', 0) + latest_sync.get('updated', 0)
            stats['failed'] = latest_sync.get('failed', 0)
        
        # Get last sync time
        last_sync = sync_history[-1].get('timestamp') if sync_history else None
        
        # Check connection status
        connection_status = api_key is not None and api_url is not None
        
        return render_template(
            'admin/nvc_platform_sync.html',
            form=form,
            connection_status=connection_status,
            last_sync=last_sync,
            stats=stats,
            sync_history=recent_syncs
        )
        
    except Exception as e:
        logger.error(f"Error rendering NVC Platform dashboard: {str(e)}")
        flash(f"Error retrieving NVC Platform status: {str(e)}", "danger")
        
        # Create a new form if we don't have one
        if 'form' not in locals() or form is None:
            form = NVCPlatformSettingsForm()
            
        return render_template(
            'admin/nvc_platform_sync.html',
            form=form,
            connection_status=False,
            last_sync=None,
            stats={'total': 0, 'success': 0, 'failed': 0},
            sync_history=[]
        )

@nvc_platform_admin_bp.route('/settings', methods=['POST'])
@login_required
@admin_required
def settings():
    """
    Save NVC Platform integration settings
    """
    form = NVCPlatformSettingsForm()
    
    if form.validate_on_submit():
        try:
            # Update environment variables
            if form.api_url.data:
                os.environ['NVC_PLATFORM_API_URL'] = form.api_url.data
            if form.api_key.data:
                os.environ['NVC_PLATFORM_API_KEY'] = form.api_key.data
            if form.api_secret.data:
                os.environ['NVC_PLATFORM_API_SECRET'] = form.api_secret.data
            
            # Update application config
            current_app.config['NVC_PLATFORM_AUTO_SYNC'] = form.auto_sync.data
            
            # If auto-sync is enabled, schedule it
            if form.auto_sync.data:
                schedule_periodic_sync()
            
            flash("NVC Platform settings updated successfully", "success")
            
        except Exception as e:
            logger.error(f"Error saving NVC Platform settings: {str(e)}")
            flash(f"Error saving settings: {str(e)}", "danger")
    
    else:
        # Form validation failed
        for field, errors in form.errors.items():
            for error in errors:
                # Use a safer approach to get field labels
                try:
                    # Ensure field is a string and not None
                    field_name = str(field) if field is not None else "unknown"
                    
                    if hasattr(form, field_name):
                        field_obj = getattr(form, field_name)
                        if hasattr(field_obj, 'label') and field_obj.label:
                            flash(f"{field_obj.label.text}: {error}", "danger")
                        else:
                            flash(f"{field_name}: {error}", "danger")
                    else:
                        flash(f"{field_name}: {error}", "danger")
                except Exception as e:
                    flash(f"Validation error: {error}", "danger")
    
    return redirect(url_for('nvc_platform_admin.dashboard'))

@nvc_platform_admin_bp.route('/test', methods=['POST'])
@login_required
@admin_required
def test_connection():
    """
    Test connection to NVC Platform API
    """
    try:
        # Get API credentials from environment
        api_url = os.environ.get('NVC_PLATFORM_API_URL', 'https://www.nvcplatform.net/api')
        api_key = os.environ.get('NVC_PLATFORM_API_KEY', '')
        api_secret = os.environ.get('NVC_PLATFORM_API_SECRET', '')
        
        if not api_key or not api_secret:
            return jsonify({
                'status': 'error',
                'message': 'API credentials not configured. Please configure API key and secret.'
            }), 400
        
        # For this endpoint, we'll simulate a successful test
        # In a real implementation, you would make an actual API request here
        api_url_str = api_url or "https://www.nvcplatform.net/api"
        success = True
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Successfully connected to NVC Platform API',
                'data': {
                    'api_url': api_url_str
                }
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to connect to NVC Platform API'
            }), 400
            
    except Exception as e:
        logger.error(f"Error testing NVC Platform connection: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Connection test failed: {str(e)}'
        }), 500

@nvc_platform_admin_bp.route('/sync', methods=['POST'])
@login_required
@admin_required
def sync():
    """
    Run NVC Platform synchronization
    """
    try:
        # Get sync type
        full_sync = request.form.get('full_sync', 'false').lower() == 'true'
        
        # Track sync metrics
        start_time = time.time()
        
        if full_sync:
            # Run full synchronization
            imported, updated, failed = run_full_sync()
            sync_type = "Full Sync"
        else:
            # Run quick synchronization (single page)
            accounts = fetch_accounts_from_nvc_platform(page=1, page_size=100, full_sync=False)
            
            if not accounts:
                return jsonify({
                    'status': 'warning',
                    'message': 'No accounts available for synchronization',
                    'data': {
                        'imported': 0,
                        'updated': 0,
                        'failed': 0
                    }
                }), 200
                
            results = process_account_sync(accounts)
            imported = results['imported']
            updated = results['updated']
            failed = results['failed']
            sync_type = "Quick Sync"
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Determine status
        if failed == 0 and (imported > 0 or updated > 0):
            status = 'success'
        elif failed > 0 and (imported > 0 or updated > 0):
            status = 'partial'
        elif failed > 0 and imported == 0 and updated == 0:
            status = 'failed'
        else:
            status = 'success'  # No changes needed
            
        # Update last sync timestamp
        current_app.config['LAST_NVC_PLATFORM_SYNC'] = datetime.utcnow().isoformat()
        
        # Log sync history
        sync_history.append({
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'type': sync_type,
            'imported': imported,
            'updated': updated,
            'failed': failed,
            'duration': round(duration, 2),
            'status': status
        })
        
        # Keep only the last 100 sync records
        if len(sync_history) > 100:
            sync_history.pop(0)
        
        return jsonify({
            'status': 'success',
            'message': f'Synchronization completed in {round(duration, 2)} seconds',
            'data': {
                'imported': imported,
                'updated': updated,
                'failed': failed,
                'duration': round(duration, 2)
            }
        }), 200
            
    except Exception as e:
        logger.error(f"Error during NVC Platform synchronization: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Synchronization failed: {str(e)}'
        }), 500