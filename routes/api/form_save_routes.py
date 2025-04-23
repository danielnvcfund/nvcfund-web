"""
Form Data API Routes
Provides API endpoints for form data management
"""
import logging
import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app import db
from models import FormData

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
form_save = Blueprint('form_save', __name__, url_prefix='/api')

@form_save.route('/save_form_data', methods=['POST'])
@login_required
def save_form_data():
    """Save form data for the current user"""
    try:
        # Log that we're attempting to save form data
        logger.info(f"Attempting to save form data for user {current_user.id}")
        
        # Get request data
        data = request.get_json()
        if not data:
            logger.warning("No JSON data provided in request")
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        form_name = data.get('form_name')
        form_data = data.get('form_data')
        
        logger.info(f"Received form data for form: {form_name}")
        
        if not form_name or not form_data:
            logger.warning(f"Missing required fields: form_name={form_name}, form_data present={form_data is not None}")
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            
        # Ensure data is JSON serializable
        try:
            json.dumps(form_data)
        except (TypeError, ValueError) as e:
            logger.error(f"Form data is not JSON serializable: {str(e)}")
            return jsonify({'success': False, 'error': 'Form data is not JSON serializable'}), 400
            
        # Make sure institution name is included
        if form_name == 'swift_fund_transfer_form' and 'receiver_institution_name' in form_data:
            logger.info(f"Institution name in form data: {form_data['receiver_institution_name']}")
        
        # Save form data
        form_data_obj = FormData.save_form_data(
            user_id=current_user.id,
            form_type=form_name,
            form_data=form_data,
            transaction_id=None,  # No transaction ID for in-progress forms
            expires_at=datetime.utcnow() + timedelta(days=1)  # Expire after 1 day
        )
        
        db.session.commit()
        logger.info(f"Form data saved successfully for user {current_user.id}, form {form_name}")
        
        return jsonify({'success': True, 'message': 'Form data saved successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving form data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
@form_save.route('/load_form_data/<form_name>', methods=['GET'])
@login_required
def load_form_data(form_name):
    """Load form data for the current user"""
    try:
        # Get form data
        form_data = FormData.query.filter_by(
            user_id=current_user.id,
            form_type=form_name,
            transaction_id=None  # Only get in-progress forms
        ).filter(
            FormData.expires_at > datetime.utcnow()
        ).order_by(FormData.created_at.desc()).first()
        
        if not form_data:
            return jsonify({'success': False, 'error': 'No saved form data found'}), 404
            
        # Parse JSON
        try:
            form_data_dict = json.loads(form_data.form_data)
            return jsonify({'success': True, 'data': form_data_dict})
        except json.JSONDecodeError:
            return jsonify({'success': False, 'error': 'Invalid form data format'}), 500
    except Exception as e:
        logger.error(f"Error loading form data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500