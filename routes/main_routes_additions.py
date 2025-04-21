# Routes for SWIFT Standby Letter of Credit functionality

@main.route('/letter_of_credit/new', methods=['GET', 'POST'])
@login_required
def create_letter_of_credit():
    """Create a new Standby Letter of Credit via SWIFT"""
    form = LetterOfCreditForm()
    
    if form.validate_on_submit():
        # Import SWIFT service
        from swift_integration import SwiftService
        
        user_id = session.get('user_id')
        
        # Call the SWIFT service to create the letter of credit
        success, message, transaction = SwiftService.create_standby_letter_of_credit(
            user_id=user_id,
            receiver_institution_id=form.receiver_institution_id.data,
            amount=form.amount.data,
            currency=form.currency.data,
            beneficiary=form.beneficiary.data,
            expiry_date=form.expiry_date.data,
            terms_and_conditions=form.terms_and_conditions.data
        )
        
        if success and transaction:
            flash(f'Standby Letter of Credit issued successfully! Transaction ID: {transaction.transaction_id}', 'success')
            return redirect(url_for('web.main.transaction_details', transaction_id=transaction.transaction_id))
        else:
            flash(f'Error issuing Standby Letter of Credit: {message}', 'danger')
            return render_template('letter_of_credit_form.html', form=form)
    
    # Handle form validation errors
    if form.errors and request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", 'danger')
    
    return render_template('letter_of_credit_form.html', form=form)

@main.route('/letter_of_credit/status/<transaction_id>')
@login_required
def letter_of_credit_status(transaction_id):
    """Check the status of a Letter of Credit transaction"""
    # Import SWIFT service
    from swift_integration import SwiftService
    
    user_id = session.get('user_id')
    
    # First ensure the transaction belongs to the current user
    transaction = Transaction.query.filter_by(transaction_id=transaction_id, user_id=user_id).first()
    
    if not transaction:
        flash('Transaction not found or you do not have permission to access it', 'danger')
        return redirect(url_for('web.main.transactions'))
    
    # Only proceed if this is a Letter of Credit transaction
    if transaction.transaction_type != TransactionType.LETTER_OF_CREDIT:
        flash('This is not a Letter of Credit transaction', 'warning')
        return redirect(url_for('web.main.transaction_details', transaction_id=transaction_id))
    
    # Get status from SWIFT service
    status_data = SwiftService.get_letter_of_credit_status(transaction_id)
    
    # Update status in transaction object if needed
    if status_data.get('success'):
        swift_status = status_data.get('status', 'unknown')
        if swift_status == 'delivered' and transaction.status != TransactionStatus.COMPLETED:
            transaction.status = TransactionStatus.COMPLETED
            db.session.commit()
            flash('Letter of Credit status updated to COMPLETED', 'success')
        elif swift_status == 'failed' and transaction.status != TransactionStatus.FAILED:
            transaction.status = TransactionStatus.FAILED
            db.session.commit()
            flash('Letter of Credit status updated to FAILED', 'warning')
    
    return render_template('letter_of_credit_status.html', 
        transaction=transaction, 
        status_data=status_data,
        swift_data=json.loads(transaction.tx_metadata_json or '{}').get('swift', {})
    )