"""
Server-to-Server Transfer Integration Routes
Routes for handling high-volume server-to-server transfers between institutions
"""

import os
import uuid
import json
import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc

from app import db
from auth import admin_required
from models import Transaction, TransactionStatus, TransactionType, User, FinancialInstitution
import utils

# Create the blueprint
server_to_server_routes = Blueprint('server_to_server', __name__, url_prefix='/s2s')

@server_to_server_routes.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Server-to-Server Transfer Dashboard"""
    # Get recent transactions
    transactions = Transaction.query.filter_by(
        transaction_type=TransactionType.SERVER_TO_SERVER
    ).order_by(desc(Transaction.created_at)).limit(20).all()
    
    # Count transactions by status
    total_count = Transaction.query.filter_by(
        transaction_type=TransactionType.SERVER_TO_SERVER
    ).count()
    
    completed_count = Transaction.query.filter_by(
        transaction_type=TransactionType.SERVER_TO_SERVER,
        status=TransactionStatus.COMPLETED
    ).count()
    
    pending_count = Transaction.query.filter_by(
        transaction_type=TransactionType.SERVER_TO_SERVER,
        status=TransactionStatus.PENDING
    ).count()
    
    failed_count = Transaction.query.filter_by(
        transaction_type=TransactionType.SERVER_TO_SERVER,
        status=TransactionStatus.FAILED
    ).count()
    
    # Get connected institutions
    institutions = FinancialInstitution.query.filter_by(s2s_enabled=True).all()
    
    return render_template('server_to_server/dashboard.html',
                          transactions=transactions,
                          total_count=total_count,
                          completed_count=completed_count,
                          pending_count=pending_count,
                          failed_count=failed_count,
                          institutions=institutions)

@server_to_server_routes.route('/new-transfer', methods=['GET', 'POST'])
@login_required
@admin_required
def new_transfer():
    """Create a new Server-to-Server transfer"""
    if request.method == 'POST':
        try:
            # Get form data
            institution_id = request.form.get('institution_id')
            amount = float(request.form.get('amount', 0))
            currency = request.form.get('currency', 'USD')
            transfer_type = request.form.get('transfer_type', 'CREDIT')
            description = request.form.get('description', '')
            reference_code = request.form.get('reference_code', '')
            
            # Validate data
            if not institution_id:
                flash('Please select an institution', 'danger')
                return redirect(url_for('server_to_server.new_transfer'))
            
            if amount <= 0:
                flash('Amount must be greater than zero', 'danger')
                return redirect(url_for('server_to_server.new_transfer'))
            
            # Get institution
            institution = FinancialInstitution.query.get(institution_id)
            if not institution:
                flash('Institution not found', 'danger')
                return redirect(url_for('server_to_server.new_transfer'))
            
            if not institution.s2s_enabled:
                flash('This institution does not support Server-to-Server transfers', 'danger')
                return redirect(url_for('server_to_server.new_transfer'))
            
            # Create transaction record
            transaction = Transaction(
                transaction_id=utils.generate_transaction_id(),
                user_id=current_user.id,
                transaction_type=TransactionType.SERVER_TO_SERVER,
                amount=amount,
                currency=currency,
                status=TransactionStatus.PENDING,
                description=description or f"Server-to-Server transfer to {institution.name}",
                recipient_name=institution.name,
                recipient_account=institution.account_number or 'Unknown',
                recipient_bank_name=institution.name,
                recipient_bank_swift=institution.swift_code or 'Unknown',
                metadata={
                    'institution_id': institution.id,
                    'transfer_type': transfer_type,
                    'reference_code': reference_code,
                    'initiated_at': datetime.datetime.utcnow().isoformat(),
                    's2s_transfer_id': str(uuid.uuid4())
                }
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            flash(f'Server-to-Server transfer initiated. Transaction ID: {transaction.transaction_id}', 'success')
            return redirect(url_for('server_to_server.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating Server-to-Server transfer: {str(e)}")
            flash(f'Error creating transfer: {str(e)}', 'danger')
            return redirect(url_for('server_to_server.new_transfer'))
    
    # GET request - show form
    institutions = FinancialInstitution.query.filter_by(s2s_enabled=True).all()
    return render_template('server_to_server/new_transfer.html',
                          institutions=institutions)

@server_to_server_routes.route('/api/transfer', methods=['POST'])
@login_required
@admin_required
def api_transfer():
    """API endpoint for Server-to-Server transfers"""
    try:
        data = request.json
        
        # Validate request
        required_fields = ['institution_id', 'amount', 'currency']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Get institution
        institution = FinancialInstitution.query.get(data['institution_id'])
        if not institution:
            return jsonify({'success': False, 'error': 'Institution not found'}), 404
        
        if not institution.s2s_enabled:
            return jsonify({'success': False, 'error': 'This institution does not support Server-to-Server transfers'}), 400
        
        # Create transaction
        transaction = Transaction(
            transaction_id=utils.generate_transaction_id(),
            user_id=current_user.id,
            transaction_type=TransactionType.SERVER_TO_SERVER,
            amount=float(data['amount']),
            currency=data['currency'],
            status=TransactionStatus.PENDING,
            description=data.get('description') or f"Server-to-Server transfer to {institution.name}",
            recipient_name=institution.name,
            recipient_account=institution.account_number or 'Unknown',
            recipient_bank_name=institution.name,
            recipient_bank_swift=institution.swift_code or 'Unknown',
            metadata={
                'institution_id': institution.id,
                'transfer_type': data.get('transfer_type', 'CREDIT'),
                'reference_code': data.get('reference_code', ''),
                'initiated_at': datetime.datetime.utcnow().isoformat(),
                's2s_transfer_id': str(uuid.uuid4()),
                'api_initiated': True
            }
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'transaction_id': transaction.transaction_id,
            'status': transaction.status.value,
            'message': 'Server-to-Server transfer initiated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in S2S API transfer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_to_server_routes.route('/api/schedule', methods=['POST'])
@login_required
@admin_required
def schedule_transfer():
    """Schedule a Server-to-Server transfer for future execution"""
    try:
        data = request.json
        
        # Validate request
        required_fields = ['institution_id', 'amount', 'currency', 'schedule_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Parse schedule date
        try:
            schedule_date = datetime.datetime.fromisoformat(data['schedule_date'])
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid schedule date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        # Check if date is in the future
        if schedule_date <= datetime.datetime.utcnow():
            return jsonify({'success': False, 'error': 'Schedule date must be in the future'}), 400
        
        # Get institution
        institution = FinancialInstitution.query.get(data['institution_id'])
        if not institution:
            return jsonify({'success': False, 'error': 'Institution not found'}), 404
        
        if not institution.s2s_enabled:
            return jsonify({'success': False, 'error': 'This institution does not support Server-to-Server transfers'}), 400
        
        # Create transaction with scheduled status
        transaction = Transaction(
            transaction_id=utils.generate_transaction_id(),
            user_id=current_user.id,
            transaction_type=TransactionType.SERVER_TO_SERVER,
            amount=float(data['amount']),
            currency=data['currency'],
            status=TransactionStatus.SCHEDULED,  # Use SCHEDULED status
            description=data.get('description') or f"Scheduled S2S transfer to {institution.name}",
            recipient_name=institution.name,
            recipient_account=institution.account_number or 'Unknown',
            recipient_bank_name=institution.name,
            recipient_bank_swift=institution.swift_code or 'Unknown',
            metadata={
                'institution_id': institution.id,
                'transfer_type': data.get('transfer_type', 'CREDIT'),
                'reference_code': data.get('reference_code', ''),
                'initiated_at': datetime.datetime.utcnow().isoformat(),
                'scheduled_for': schedule_date.isoformat(),
                's2s_transfer_id': str(uuid.uuid4()),
                'scheduled': True
            }
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'transaction_id': transaction.transaction_id,
            'status': transaction.status.value,
            'scheduled_for': schedule_date.isoformat(),
            'message': 'Server-to-Server transfer scheduled successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error scheduling S2S transfer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500