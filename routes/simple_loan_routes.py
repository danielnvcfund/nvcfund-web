"""
Simple Loan Routes for NVC Banking Platform

This module provides simplified routes for the loan system without relying on complex ORM models.
"""

import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import text
from app import db

# Create Blueprint
simple_loan_bp = Blueprint('simple_loan', __name__, url_prefix='/simple-loans')

@simple_loan_bp.route('/')
def index():
    """Display the main loans index page"""
    
    # We'll use a direct SQL query to get loan data
    # This avoids ORM model issues with enums
    loans = []
    loan_info = None
    
    try:
        # Get loans from database using raw SQL with proper text() wrapper
        from sqlalchemy import text
        loan_info = db.session.execute(
            text("""
            SELECT id, loan_number, borrower_name, 
                   loan_amount, currency, status, created_at
            FROM self_liquidating_loan 
            ORDER BY created_at DESC
            """)
        ).fetchall()
        
        if loan_info:
            for loan in loan_info:
                loans.append({
                    'id': loan.id,
                    'loan_number': loan.loan_number,
                    'borrower_name': loan.borrower_name,
                    'loan_amount': loan.loan_amount,
                    'currency': loan.currency,
                    'status': loan.status,
                    'created_at': loan.created_at
                })
    except Exception as e:
        # If there's a database error, we'll still show the page
        # but with a message and no loans
        flash(f"Could not load loan data: {str(e)}", "warning")
    
    # Render the template with the loan data
    return render_template('loans/loan_list.html', loans=loans, recent_activity=[])

@simple_loan_bp.route('/detail/<int:loan_id>')
def loan_detail(loan_id):
    """Display detailed information for a specific loan"""
    
    try:
        # Fetch loan details using raw SQL to avoid ORM issues
        from sqlalchemy import text
        loan_query = db.session.execute(
            text("""
            SELECT * FROM self_liquidating_loan 
            WHERE id = :loan_id
            """),
            {"loan_id": loan_id}
        ).fetchone()
        
        if not loan_query:
            flash("Loan not found", "error")
            return redirect(url_for('simple_loan.index'))
            
        loan = dict(loan_query)
        
        # Get collateral information
        collateral_query = db.session.execute(
            text("""
            SELECT * FROM loan_collateral
            WHERE loan_id = :loan_id
            """),
            {"loan_id": loan_id}
        ).fetchall()
        
        collateral = [dict(item) for item in collateral_query] if collateral_query else []
        
        # Get payment history
        payment_query = db.session.execute(
            text("""
            SELECT * FROM loan_payment
            WHERE loan_id = :loan_id
            ORDER BY payment_date DESC
            """),
            {"loan_id": loan_id}
        ).fetchall()
        
        payments = [dict(item) for item in payment_query] if payment_query else []
        
        return render_template(
            'loans/detail.html',
            loan=loan,
            collateral=collateral,
            payments=payments
        )
        
    except Exception as e:
        flash(f"Error loading loan details: {str(e)}", "error")
        return redirect(url_for('simple_loan.index'))

@simple_loan_bp.route('/dashboard')
@login_required
def loan_dashboard():
    """Display a dashboard with loan statistics"""
    
    try:
        # Get overall loan statistics
        stats_query = db.session.execute(
            text("""
            SELECT 
                COUNT(*) as total_loans,
                SUM(loan_amount) as total_loan_amount,
                AVG(loan_amount) as avg_loan_amount,
                COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_loans,
                COUNT(CASE WHEN status = 'PAID' THEN 1 END) as paid_loans
            FROM self_liquidating_loan
            """)
        ).fetchone()
        
        stats = dict(stats_query) if stats_query else {
            'total_loans': 0,
            'total_loan_amount': 0,
            'avg_loan_amount': 0,
            'active_loans': 0,
            'paid_loans': 0
        }
        
        return render_template('loans/dashboard.html', stats=stats)
        
    except Exception as e:
        flash(f"Error loading loan dashboard: {str(e)}", "error")
        return redirect(url_for('simple_loan.index'))

@simple_loan_bp.route('/new', methods=['GET', 'POST'])
def new_loan():
    """Create a new loan application"""
    
    if request.method == 'POST':
        try:
            # Extract loan information from form
            borrower_name = request.form.get('borrower_name')
            loan_amount = request.form.get('loan_amount')
            currency = request.form.get('currency')
            loan_term = request.form.get('loan_term')
            interest_rate = request.form.get('interest_rate')
            purpose = request.form.get('purpose')
            
            # Generate a unique loan number 
            current_year = datetime.utcnow().year
            
            # Get the current max loan number for this year to create sequential numbering
            max_loan_num_query = db.session.execute(
                text("""
                SELECT MAX(SUBSTRING(loan_number, -4)) as max_num
                FROM self_liquidating_loan
                WHERE loan_number LIKE :year_prefix
                """),
                {"year_prefix": f"SLL-{current_year}-%"}
            ).fetchone()
            
            max_num = max_loan_num_query.max_num if max_loan_num_query and max_loan_num_query.max_num else 0
            next_num = int(max_num) + 1 if max_num else 1
            loan_number = f"SLL-{current_year}-{next_num:04d}"
            
            # Insert the new loan into the database
            db.session.execute(
                text("""
                INSERT INTO self_liquidating_loan (
                    loan_number, borrower_name, loan_amount, currency, 
                    term_months, interest_rate, purpose, status, created_at
                ) VALUES (
                    :loan_number, :borrower_name, :loan_amount, :currency,
                    :term_months, :interest_rate, :purpose, 'APPLICATION', NOW()
                )
                """),
                {
                    "loan_number": loan_number,
                    "borrower_name": borrower_name,
                    "loan_amount": float(loan_amount),
                    "currency": currency,
                    "term_months": int(loan_term),
                    "interest_rate": float(interest_rate),
                    "purpose": purpose
                }
            )
            db.session.commit()
            
            flash(f"Loan application {loan_number} created successfully", "success")
            return redirect(url_for('simple_loan.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating loan: {str(e)}", "error")
    
    # For GET requests, display the application form
    return render_template('loans/new_loan.html')