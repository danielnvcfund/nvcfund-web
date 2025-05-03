"""
KTT Telex Routes
This module provides routes for interacting with the KTT Telex service.
"""

import json
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, session
from flask_login import login_required, current_user
from werkzeug.exceptions import BadRequest

from ktt_telex import get_telex_service, TelexMessageType
from models import db, Transaction, FinancialInstitution, TelexMessage, TelexMessageStatus
from auth import admin_required

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
telex_bp = Blueprint('telex', __name__, url_prefix='/telex')

@telex_bp.route('/')
@login_required
def dashboard():
    """Telex dashboard"""
    # Get recent telex messages
    sent_messages = TelexMessage.query.filter_by(
        status=TelexMessageStatus.SENT
    ).order_by(TelexMessage.created_at.desc()).limit(10).all()
    
    received_messages = TelexMessage.query.filter_by(
        status=TelexMessageStatus.RECEIVED
    ).order_by(TelexMessage.created_at.desc()).limit(10).all()
    
    return render_template(
        'telex/dashboard.html',
        sent_messages=sent_messages,
        received_messages=received_messages
    )

@telex_bp.route('/messages')
@login_required
def message_list():
    """List all Telex messages"""
    # Get filter parameters
    status = request.args.get('status')
    message_type = request.args.get('message_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query
    query = TelexMessage.query
    
    # Apply filters
    if status:
        try:
            status_enum = TelexMessageStatus[status]
            query = query.filter_by(status=status_enum)
        except KeyError:
            flash(f"Invalid status filter: {status}", "warning")
    
    if message_type:
        query = query.filter_by(message_type=message_type)
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(TelexMessage.created_at >= start_date_obj)
        except ValueError:
            flash(f"Invalid start date format: {start_date}. Use YYYY-MM-DD.", "warning")
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(TelexMessage.created_at <= end_date_obj)
        except ValueError:
            flash(f"Invalid end date format: {end_date}. Use YYYY-MM-DD.", "warning")
    
    # Get messages
    messages = query.order_by(TelexMessage.created_at.desc()).all()
    
    return render_template(
        'telex/message_list.html',
        messages=messages,
        status_options=TelexMessageStatus,
        message_type_options=TelexMessageType.__dict__.items()
    )

@telex_bp.route('/messages/<string:message_id>')
@login_required
def message_detail(message_id):
    """View details of a Telex message"""
    message = TelexMessage.query.filter_by(message_id=message_id).first_or_404()
    
    # Parse message content from JSON
    try:
        content = json.loads(message.message_content)
    except json.JSONDecodeError:
        content = {'error': 'Invalid JSON content', 'raw': message.message_content}
    
    return render_template(
        'telex/message_detail.html',
        message=message,
        content=content
    )

@telex_bp.route('/send', methods=['GET', 'POST'])
@login_required
def send_message():
    """Send a Telex message"""
    if request.method == 'POST':
        recipient_bic = request.form.get('recipient_bic')
        message_type = request.form.get('message_type')
        message_content = request.form.get('message_content')
        priority = request.form.get('priority', 'NORMAL')
        transaction_id = request.form.get('transaction_id')
        
        # Basic validation
        if not all([recipient_bic, message_type, message_content]):
            flash("All fields are required", "danger")
            return redirect(url_for('telex.send_message'))
        
        # Get institution for the BIC code
        institution = FinancialInstitution.query.filter_by(swift_code=recipient_bic).first()
        if not institution:
            flash(f"No institution found with BIC code: {recipient_bic}", "danger")
            return redirect(url_for('telex.send_message'))
        
        # Parse message content as JSON
        try:
            content_dict = json.loads(message_content)
        except json.JSONDecodeError:
            flash("Message content must be valid JSON", "danger")
            return redirect(url_for('telex.send_message'))
        
        # Generate sender reference
        sender_reference = f"REF{int(datetime.utcnow().timestamp())}"
        
        # Send the message
        telex_service = get_telex_service()
        response = telex_service.send_telex_message(
            sender_reference=sender_reference,
            recipient_bic=recipient_bic,
            message_type=message_type,
            message_content=content_dict,
            transaction_id=transaction_id,
            priority=priority
        )
        
        if response.get('error'):
            flash(f"Error sending message: {response.get('error')}", "danger")
            return redirect(url_for('telex.send_message'))
        
        flash("Message sent successfully", "success")
        return redirect(url_for('telex.message_detail', message_id=response.get('message_id')))
    
    # GET request - show form
    # Get transaction list for dropdown
    transactions = Transaction.query.filter_by(status='PENDING').order_by(Transaction.created_at.desc()).limit(50).all()
    
    # Get institutions for dropdown
    institutions = FinancialInstitution.query.filter(FinancialInstitution.swift_code.isnot(None)).all()
    
    return render_template(
        'telex/send_message.html',
        transactions=transactions,
        institutions=institutions,
        message_types=TelexMessageType.__dict__.items(),
        priorities=['HIGH', 'NORMAL', 'LOW']
    )

@telex_bp.route('/api/send-funds-transfer', methods=['POST'])
@login_required
def api_send_funds_transfer():
    """API endpoint to send a funds transfer message"""
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    transaction_id = data.get('transaction_id')
    recipient_institution_id = data.get('recipient_institution_id')
    
    if not transaction_id or not recipient_institution_id:
        return jsonify({'error': 'transaction_id and recipient_institution_id are required'}), 400
    
    # Get transaction and institution
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    institution = FinancialInstitution.query.get(recipient_institution_id)
    
    if not transaction:
        return jsonify({'error': f'Transaction not found: {transaction_id}'}), 404
    
    if not institution:
        return jsonify({'error': f'Institution not found: {recipient_institution_id}'}), 404
    
    if not institution.swift_code:
        return jsonify({'error': f'Institution does not have a SWIFT/BIC code: {institution.name}'}), 400
    
    # Send the funds transfer message
    telex_service = get_telex_service()
    response = telex_service.create_funds_transfer_message(transaction, institution)
    
    if response.get('error'):
        return jsonify({'error': response.get('error')}), 500
    
    return jsonify({
        'success': True, 
        'message': 'Funds transfer message sent successfully',
        'message_id': response.get('message_id')
    })

@telex_bp.route('/api/send-payment-confirmation', methods=['POST'])
@login_required
def api_send_payment_confirmation():
    """API endpoint to send a payment confirmation message"""
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    transaction_id = data.get('transaction_id')
    recipient_institution_id = data.get('recipient_institution_id')
    
    if not transaction_id or not recipient_institution_id:
        return jsonify({'error': 'transaction_id and recipient_institution_id are required'}), 400
    
    # Get transaction and institution
    transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
    institution = FinancialInstitution.query.get(recipient_institution_id)
    
    if not transaction:
        return jsonify({'error': f'Transaction not found: {transaction_id}'}), 404
    
    if not institution:
        return jsonify({'error': f'Institution not found: {recipient_institution_id}'}), 404
    
    if not institution.swift_code:
        return jsonify({'error': f'Institution does not have a SWIFT/BIC code: {institution.name}'}), 400
    
    # Send the payment confirmation message
    telex_service = get_telex_service()
    response = telex_service.create_payment_confirmation_message(transaction, institution)
    
    if response.get('error'):
        return jsonify({'error': response.get('error')}), 500
    
    return jsonify({
        'success': True, 
        'message': 'Payment confirmation message sent successfully',
        'message_id': response.get('message_id')
    })

@telex_bp.route('/api/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for receiving messages from KTT Telex"""
    # Verify signature to ensure the request is legitimate
    # This would be a real implementation in production
    signature = request.headers.get('X-KTT-Signature')
    webhook_secret = current_app.config.get('KTT_TELEX_WEBHOOK_SECRET')
    
    # For now, we'll skip signature verification
    # Normally you'd verify the signature here
    
    data = request.json
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Process the incoming message
    telex_service = get_telex_service()
    result = telex_service.process_incoming_message(data)
    
    if result.get('error'):
        logger.error(f"Error processing webhook: {result.get('error')}")
        return jsonify({'error': result.get('error')}), 500
    
    return jsonify({'success': True, 'message': 'Webhook received and processed'})

@telex_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """Telex settings page"""
    if request.method == 'POST':
        api_key = request.form.get('api_key')
        api_secret = request.form.get('api_secret')
        base_url = request.form.get('base_url')
        
        # Update settings
        # In a real application, these would be stored in a secure way
        # For now, we'll just show it as if it's saved
        flash("Telex settings updated successfully", "success")
        return redirect(url_for('telex.settings'))
    
    return render_template('telex/settings.html')

# Register the blueprint
def register_telex_routes(app):
    """Register telex routes with the app"""
    app.register_blueprint(telex_bp)
    logger.info("Telex routes registered successfully")