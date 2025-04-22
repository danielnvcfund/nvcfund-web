"""
Form Data API Routes
Provides API endpoints for form data management
"""
import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from auth import admin_required
from app import db
from models import FormData

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
form_data = Blueprint('form_data', __name__, url_prefix='/api/form-data')

@form_data.route('/cleanup', methods=['POST'])
@login_required
@admin_required
def cleanup_expired_form_data():
    """Clean up expired form data - admin only"""
    try:
        # Call the cleanup method
        FormData.cleanup_expired()
        return jsonify({'success': True, 'message': 'Expired form data cleaned up successfully'})
    except Exception as e:
        logger.error(f"Error cleaning up expired form data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@form_data.route('/user/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user_form_data(user_id):
    """Get all form data for a user - admin only"""
    try:
        form_data = FormData.get_all_for_user(user_id)
        return jsonify({'success': True, 'data': form_data})
    except Exception as e:
        logger.error(f"Error getting form data for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@form_data.route('/transaction/<transaction_id>/<form_type>', methods=['GET'])
@login_required
def get_transaction_form_data(transaction_id, form_type):
    """Get form data for a transaction"""
    try:
        # Regular users can only get their own form data
        form_data = FormData.get_for_transaction(transaction_id, form_type)
        
        if not form_data:
            return jsonify({'success': False, 'error': 'Form data not found'}), 404
        
        return jsonify({'success': True, 'data': form_data})
    except Exception as e:
        logger.error(f"Error getting form data for transaction {transaction_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500