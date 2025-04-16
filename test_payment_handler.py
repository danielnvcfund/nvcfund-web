"""
Test payment handling functionality
Separate module to handle payment gateway testing functionality
"""

import logging
from flask import render_template, flash, redirect, url_for, session
from models import User, Transaction, PaymentGateway
from payment_gateways import get_gateway_handler
from forms import TestPaymentForm

logger = logging.getLogger(__name__)

def handle_stripe_test_payment(result, form, user_id):
    """
    Handle the result of a Stripe test payment and render the appropriate template
    """
    logger.info(f"Processing Stripe test payment with scenario: {form.test_scenario.data}")
    
    # Render the test-specific confirmation template with scenario info
    return render_template(
        'test_payment_confirm.html',
        client_secret=result['client_secret'],
        payment_intent_id=result['payment_intent_id'],
        amount=float(form.amount.data),
        currency=form.currency.data,
        transaction_id=result['transaction_id'],
        test_scenario=form.test_scenario.data
    )

def process_test_payment(form, user_id):
    """
    Process a test payment with the specified gateway and scenario
    """
    user = User.query.get(user_id)
    
    # Get recent test transactions for display
    test_transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.description.like('%Test payment%')
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    
    # Get gateway handler
    try:
        gateway_handler = get_gateway_handler(form.gateway_id.data)
    except ValueError as e:
        flash(str(e), 'danger')
        return render_template('payment_test.html', form=form, user=user, test_transactions=test_transactions)
    
    # Create a description that identifies this as a test
    description = f"Test payment: {form.test_scenario.data} - {form.description.data or 'from nvcplatform.net'}"
    
    # Add test parameters based on scenario
    test_metadata = {"test": True, "scenario": form.test_scenario.data}
    
    # Process payment
    result = gateway_handler.process_payment(
        float(form.amount.data), 
        form.currency.data, 
        description, 
        user_id,
        metadata=test_metadata
    )
    
    if result.get('success'):
        flash('Test payment initiated successfully', 'success')
        
        # Different gateways return different data
        if 'hosted_url' in result:  # Coinbase
            return redirect(result['hosted_url'])
        elif 'approval_url' in result:  # PayPal
            return redirect(result['approval_url'])
        elif 'client_secret' in result:  # Stripe
            return handle_stripe_test_payment(result, form, user_id)
        else:
            # Generic success
            return redirect(url_for('main.transaction_details', transaction_id=result['transaction_id']))
    else:
        flash(f"Test payment failed: {result.get('error', 'Unknown error')}", 'danger')
        return render_template('payment_test.html', form=form, user=user, test_transactions=test_transactions)