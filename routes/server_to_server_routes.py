"""
Server-to-Server Transfer Integration Routes
Routes for handling high-volume server-to-server transfers between institutions
"""

import os
import uuid
import json
import datetime
import tempfile
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc
from weasyprint import HTML

from app import db
from auth import admin_required
from models import Transaction, TransactionStatus, TransactionType, User, FinancialInstitution, FinancialInstitutionType
import utils
from utils import get_institution_metadata, get_transaction_metadata

# Create the blueprint
server_to_server_routes = Blueprint('server_to_server', __name__, url_prefix='/s2s')

@server_to_server_routes.route('/dashboard')
@login_required
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
            metadata = {
                'institution_id': institution.id,
                'transfer_type': transfer_type,
                'reference_code': reference_code,
                'initiated_at': datetime.datetime.utcnow().isoformat(),
                's2s_transfer_id': str(uuid.uuid4()),
                'recipient_name': institution.name,
                'recipient_account': institution.account_number or 'Unknown',
                'recipient_bank_name': institution.name,
                'recipient_bank_swift': institution.swift_code or 'Unknown'
            }
            
            transaction = Transaction(
                transaction_id=utils.generate_transaction_id(),
                user_id=current_user.id,
                transaction_type=TransactionType.SERVER_TO_SERVER,
                amount=amount,
                currency=currency,
                status=TransactionStatus.PENDING,
                description=description or f"Server-to-Server transfer to {institution.name}",
                institution_id=institution.id,
                tx_metadata_json=json.dumps(metadata)
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
        metadata = {
            'institution_id': institution.id,
            'transfer_type': data.get('transfer_type', 'CREDIT'),
            'reference_code': data.get('reference_code', ''),
            'initiated_at': datetime.datetime.utcnow().isoformat(),
            's2s_transfer_id': str(uuid.uuid4()),
            'api_initiated': True,
            'recipient_name': institution.name,
            'recipient_account': institution.account_number or 'Unknown',
            'recipient_bank_name': institution.name,
            'recipient_bank_swift': institution.swift_code or 'Unknown'
        }
        
        transaction = Transaction(
            transaction_id=utils.generate_transaction_id(),
            user_id=current_user.id,
            transaction_type=TransactionType.SERVER_TO_SERVER,
            amount=float(data['amount']),
            currency=data['currency'],
            status=TransactionStatus.PENDING,
            description=data.get('description') or f"Server-to-Server transfer to {institution.name}",
            institution_id=institution.id,
            tx_metadata_json=json.dumps(metadata)
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
        metadata = {
            'institution_id': institution.id,
            'transfer_type': data.get('transfer_type', 'CREDIT'),
            'reference_code': data.get('reference_code', ''),
            'initiated_at': datetime.datetime.utcnow().isoformat(),
            'scheduled_for': schedule_date.isoformat(),
            's2s_transfer_id': str(uuid.uuid4()),
            'scheduled': True,
            'recipient_name': institution.name,
            'recipient_account': institution.account_number or 'Unknown',
            'recipient_bank_name': institution.name,
            'recipient_bank_swift': institution.swift_code or 'Unknown'
        }
        
        transaction = Transaction(
            transaction_id=utils.generate_transaction_id(),
            user_id=current_user.id,
            transaction_type=TransactionType.SERVER_TO_SERVER,
            amount=float(data['amount']),
            currency=data['currency'],
            status=TransactionStatus.SCHEDULED,  # Use SCHEDULED status
            description=data.get('description') or f"Scheduled S2S transfer to {institution.name}",
            institution_id=institution.id,
            # Store recipient details in dedicated fields
            recipient_name=institution.name,
            recipient_institution=institution.name,
            recipient_account=institution.account_number or 'N/A',
            recipient_country=get_institution_metadata(institution).get('country', ''),
            tx_metadata_json=json.dumps(metadata)
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
        
@server_to_server_routes.route('/api/status/<transaction_id>', methods=['GET'])
@login_required
def check_status(transaction_id):
    """Check the status of a Server-to-Server transfer"""
    try:
        transaction = Transaction.query.filter_by(
            transaction_id=transaction_id,
            transaction_type=TransactionType.SERVER_TO_SERVER
        ).first()
        
        if not transaction:
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
        
        # Check if user has permission to view this transaction
        if transaction.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Get recipient info from metadata
        metadata = get_transaction_metadata(transaction)
        
        # Format response json
        response_data = {
            'success': True,
            'transaction_id': transaction.transaction_id,
            'status': transaction.status.value,
            'initiated_at': transaction.created_at.isoformat(),
            'updated_at': transaction.updated_at.isoformat() if hasattr(transaction, 'updated_at') else None,
            'amount': transaction.amount,
            'currency': transaction.currency,
            'recipient_name': metadata.get('recipient_name', ''),
            'recipient_account': metadata.get('recipient_account', ''),
            'recipient_bank_name': metadata.get('recipient_bank_name', ''),
            'metadata': metadata
        }
        
        # Check if HTML format is requested
        format_param = request.args.get('format', 'json')
        if format_param == 'html':
            # Render the enhanced viewer template with the transaction data
            return render_template(
                'server_to_server/api_viewer.html',
                transaction=transaction,
                metadata=metadata,
                json_data=json.dumps(response_data, indent=2)
            )
        elif format_param == 'pdf':
            # Generate PDF of the API response
            
            # Create HTML content for the PDF
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Server-to-Server Transaction {transaction.transaction_id}</title>
                <style>
                    body {{ font-family: 'Helvetica', 'Arial', sans-serif; padding: 20px; }}
                    h1 {{ color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
                    h2 {{ color: #3498db; margin-top: 20px; }}
                    .transaction-info {{ margin-bottom: 20px; }}
                    .json-data {{ 
                        font-family: 'Courier New', 'Consolas', monospace; 
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-radius: 5px;
                        white-space: pre-wrap;
                        font-size: 12px;
                        line-height: 1.4;
                    }}
                    .badge {{
                        display: inline-block;
                        padding: 5px 10px;
                        border-radius: 4px;
                        font-weight: bold;
                        color: white;
                    }}
                    .badge-PENDING {{ background-color: #ffc107; color: #212529; }}
                    .badge-COMPLETED {{ background-color: #28a745; }}
                    .badge-FAILED {{ background-color: #dc3545; }}
                    .badge-CANCELLED {{ background-color: #6c757d; }}
                    .badge-SCHEDULED {{ background-color: #17a2b8; }}
                    .field-label {{ font-weight: bold; min-width: 150px; display: inline-block; }}
                    .field-value {{ display: inline-block; }}
                    .status-field {{ margin-bottom: 10px; }}
                    .footer {{ 
                        margin-top: 30px;
                        font-size: 10px;
                        color: #6c757d;
                        text-align: center;
                        border-top: 1px solid #eee;
                        padding-top: 10px;
                    }}
                </style>
            </head>
            <body>
                <h1>Server-to-Server Transaction Details</h1>
                
                <div class="transaction-info">
                    <div class="status-field">
                        <span class="field-label">Status:</span>
                        <span class="badge badge-{transaction.status.value}">{transaction.status.value}</span>
                    </div>
                    <div>
                        <span class="field-label">Transaction ID:</span>
                        <span class="field-value">{transaction.transaction_id}</span>
                    </div>
                    <div>
                        <span class="field-label">Created:</span>
                        <span class="field-value">{transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
                    </div>
                    <div>
                        <span class="field-label">Amount:</span>
                        <span class="field-value">{transaction.amount:,.2f} {transaction.currency}</span>
                    </div>
                    <div>
                        <span class="field-label">Recipient:</span>
                        <span class="field-value">{metadata.get('recipient_name', 'N/A')}</span>
                    </div>
                    <div>
                        <span class="field-label">Recipient Bank:</span>
                        <span class="field-value">{metadata.get('recipient_bank_name', 'N/A')}</span>
                    </div>
                    <div>
                        <span class="field-label">Account Number:</span>
                        <span class="field-value">{metadata.get('recipient_account', 'N/A')}</span>
                    </div>
                </div>
                
                <h2>Complete API Response</h2>
                <pre class="json-data">{json.dumps(response_data, indent=2)}</pre>
                
                <div class="footer">
                    <p>Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | NVC Global Server-to-Server System</p>
                    <p>Page 1</p>
                </div>
            </body>
            </html>
            """
            
            # Create PDF
            pdf_file = tempfile.NamedTemporaryFile(suffix='.pdf')
            HTML(string=html_content).write_pdf(pdf_file.name)
            
            # Return the PDF as a response
            with open(pdf_file.name, 'rb') as f:
                binary_pdf = f.read()
            
            response = current_app.response_class(
                binary_pdf,
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename=s2s-transaction-{transaction.transaction_id}.pdf'}
            )
            return response
        
        # Default: Return JSON response
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error checking Server-to-Server transfer status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@server_to_server_routes.route('/add-institution', methods=['POST'])
@login_required
def add_institution():
    """Add a new financial institution"""
    try:
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Get form data
        name = request.form.get('name')
        institution_type = request.form.get('institution_type', 'BANK')
        swift_code = request.form.get('swift_code')
        account_number = request.form.get('account_number')
        routing_number = request.form.get('routing_number')
        country = request.form.get('country')
        description = request.form.get('description')
        
        # Parse checkboxes
        supports_s2s = request.form.get('supports_s2s') == 'true'
        supports_rtgs = request.form.get('supports_rtgs') == 'true'
        supports_swift = request.form.get('supports_swift') == 'true'
        
        # Get redirect URL if provided
        redirect_to = request.form.get('redirect_to')
        
        # Validate required data
        if not name:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Institution name is required'}), 400
            flash('Institution name is required', 'danger')
            return redirect(url_for('server_to_server.new_transfer'))
        
        # Create new institution
        institution = FinancialInstitution(
            name=name,
            institution_type=FinancialInstitutionType[institution_type],
            swift_code=swift_code,
            account_number=account_number,
            s2s_enabled=supports_s2s,
            rtgs_enabled=supports_rtgs
        )
        
        # Add metadata
        metadata = {}
        if country:
            metadata['country'] = country
        if routing_number:
            metadata['routing_number'] = routing_number
        if description:
            metadata['description'] = description
        if supports_swift:
            metadata['swift_enabled'] = True
            
        # Store metadata as JSON
        if metadata:
            institution.metadata_json = json.dumps(metadata)
        
        db.session.add(institution)
        db.session.commit()
        
        # Log the creation
        current_app.logger.info(f"New financial institution created: {name} (ID: {institution.id})")
        
        if is_ajax:
            # Return JSON response for AJAX requests
            return jsonify({
                'success': True,
                'institution': {
                    'id': institution.id,
                    'name': institution.name,
                    'swift_code': institution.swift_code,
                    'institution_type': institution.institution_type.value
                },
                'message': 'Institution created successfully'
            })
        
        # Add success message
        flash(f'Financial institution "{name}" created successfully', 'success')
        
        # Redirect back to the referring page
        if redirect_to:
            return redirect(url_for(redirect_to))
        return redirect(url_for('server_to_server.new_transfer'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating financial institution: {str(e)}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': str(e)}), 500
        
        flash(f'Error creating institution: {str(e)}', 'danger')
        return redirect(url_for('server_to_server.new_transfer'))

@server_to_server_routes.route('/export/<transaction_id>', methods=['GET'])
@login_required
def export_transaction_pdf(transaction_id):
    """Export a transaction as PDF"""
    try:
        # Get the transaction
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        
        if not transaction:
            flash('Transaction not found', 'danger')
            return redirect(url_for('server_to_server.dashboard'))
        
        # Security check - only allow admins or transaction owners to view
        if transaction.user_id != current_user.id and not current_user.is_admin:
            flash('You do not have permission to view this transaction', 'danger')
            return redirect(url_for('server_to_server.dashboard'))
            
        # Ensure it's a Server-to-Server transaction
        if transaction.transaction_type != TransactionType.SERVER_TO_SERVER:
            flash('This is not a Server-to-Server transaction', 'danger')
            return redirect(url_for('server_to_server.dashboard'))
        
        # Get institution
        institution = None
        if transaction.institution_id:
            institution = FinancialInstitution.query.get(transaction.institution_id)
            
        # Format the amount with commas using the format_currency utility
        from utils import format_currency
        # Keep the old method for compatibility but also pass transaction to template
        formatted_amount = f"{transaction.currency} {'{:,.2f}'.format(transaction.amount)}"
            
        # Get metadata if available
        metadata = {}
        if transaction.tx_metadata_json:
            try:
                metadata = json.loads(transaction.tx_metadata_json)
            except:
                current_app.logger.error(f"Error parsing transaction metadata for {transaction_id}")
        
        # Prepare HTML for PDF
        html = render_template('server_to_server/transaction_pdf.html',
                            transaction=transaction,
                            institution=institution,
                            formatted_amount=formatted_amount,
                            metadata=metadata)
                            
        # Generate PDF
        pdf = weasyprint.HTML(string=html).write_pdf()
        
        # Create response
        response = current_app.response_class(
            pdf,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment;filename=transaction_{transaction_id}.pdf'}
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting transaction PDF: {str(e)}")
        flash(f'Error generating PDF: {str(e)}', 'danger')
        return redirect(url_for('server_to_server.dashboard'))