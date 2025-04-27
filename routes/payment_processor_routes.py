"""
Payment Processor Routes
This module contains routes for salary payments, bill payments, 
and contract payments processing.
"""

import json
import secrets
from datetime import datetime, date, timedelta
from io import BytesIO

from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, current_app, send_file
from sqlalchemy import desc, func, or_
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user

from app import db
from models import (
    TransactionStatus, TransactionType, Transaction, 
    PaymentFrequency, BillCategory, ContractType,
    Employee, PayrollBatch, SalaryPayment, 
    Vendor, Bill, Contract, ContractPayment,
    User, FinancialInstitution
)
from auth import admin_required
from utils import generate_transaction_id, get_or_404, is_admin, is_developer

payment_processor_bp = Blueprint('payment_processor', __name__, url_prefix='/payment-processor')

# Set correct index route for redirects
INDEX_ROUTE = 'main_explicit_index'


# Helper functions
def generate_random_id(prefix, length=16):
    """Generate a random ID with specified prefix"""
    random_part = secrets.token_hex(length//2)
    return f"{prefix}_{random_part.upper()}"


def format_currency(amount, currency="USD"):
    """Format currency with commas and currency symbol"""
    if currency == "USD":
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"


# ============================================================
# Employee and Salary Payment Routes
# ============================================================

@payment_processor_bp.route('/employees')
@login_required
def employee_list():
    """List all employees"""
    employees = Employee.query.order_by(Employee.last_name).all()
    return render_template(
        'payment_processor/employees/list.html', 
        employees=employees,
        title="Employee Management"
    )


@payment_processor_bp.route('/employees/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_employee():
    """Add a new employee"""
    if request.method == 'POST':
        # Generate a unique employee ID
        employee_id = generate_random_id("EMP")
        
        # Check if email already exists
        email = request.form.get('email')
        existing_employee = Employee.query.filter_by(email=email).first()
        if existing_employee:
            flash("An employee with this email already exists", "danger")
            return redirect(url_for('payment_processor.new_employee'))
        
        # Create a new employee
        employee = Employee(
            employee_id=employee_id,
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            email=email,
            phone=request.form.get('phone'),
            position=request.form.get('position'),
            department=request.form.get('department'),
            hire_date=datetime.strptime(request.form.get('hire_date'), '%Y-%m-%d').date() if request.form.get('hire_date') else date.today(),
            bank_account_number=request.form.get('bank_account_number'),
            bank_routing_number=request.form.get('bank_routing_number'),
            bank_name=request.form.get('bank_name'),
            payment_method=request.form.get('payment_method'),
            salary_amount=float(request.form.get('salary_amount', 0)),
            salary_frequency=PaymentFrequency(request.form.get('salary_frequency'))
        )
        
        # Link to user account if ID is provided
        user_id = request.form.get('user_id')
        if user_id:
            employee.user_id = int(user_id)
        
        # Add metadata if needed
        metadata = {}
        if request.form.get('tax_id'):
            metadata['tax_id'] = request.form.get('tax_id')
        if request.form.get('emergency_contact'):
            metadata['emergency_contact'] = request.form.get('emergency_contact')
        
        if metadata:
            employee.metadata_json = json.dumps(metadata)
        
        db.session.add(employee)
        db.session.commit()
        
        flash(f"Employee {employee.get_full_name()} added successfully", "success")
        return redirect(url_for('payment_processor.employee_list'))
    
    # Get all users for linking
    users = User.query.order_by(User.username).all()
    
    return render_template(
        'payment_processor/employees/new.html', 
        users=users,
        payment_frequencies=[f.value for f in PaymentFrequency],
        title="Add New Employee"
    )


@payment_processor_bp.route('/employees/<int:employee_id>')
@login_required
def employee_details(employee_id):
    """View employee details"""
    employee = get_or_404(Employee, employee_id)
    recent_payments = SalaryPayment.query.filter_by(employee_id=employee_id).order_by(SalaryPayment.payment_date.desc()).limit(5).all()
    
    return render_template(
        'payment_processor/employees/details.html', 
        employee=employee,
        recent_payments=recent_payments,
        title=f"Employee: {employee.get_full_name()}"
    )


@payment_processor_bp.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_employee(employee_id):
    """Edit an employee's information"""
    employee = get_or_404(Employee, employee_id)
    
    if request.method == 'POST':
        # Update employee information
        employee.first_name = request.form.get('first_name')
        employee.last_name = request.form.get('last_name')
        employee.email = request.form.get('email')
        employee.phone = request.form.get('phone')
        employee.position = request.form.get('position')
        employee.department = request.form.get('department')
        
        if request.form.get('hire_date'):
            employee.hire_date = datetime.strptime(request.form.get('hire_date'), '%Y-%m-%d').date()
        
        employee.bank_account_number = request.form.get('bank_account_number')
        employee.bank_routing_number = request.form.get('bank_routing_number')
        employee.bank_name = request.form.get('bank_name')
        employee.payment_method = request.form.get('payment_method')
        
        if request.form.get('salary_amount'):
            employee.salary_amount = float(request.form.get('salary_amount'))
        
        employee.salary_frequency = PaymentFrequency(request.form.get('salary_frequency'))
        
        # Link to user account if ID is provided
        user_id = request.form.get('user_id')
        if user_id:
            employee.user_id = int(user_id)
        else:
            employee.user_id = None
        
        # Update metadata
        metadata = employee.get_metadata()
        
        if request.form.get('tax_id'):
            metadata['tax_id'] = request.form.get('tax_id')
        
        if request.form.get('emergency_contact'):
            metadata['emergency_contact'] = request.form.get('emergency_contact')
        
        employee.metadata_json = json.dumps(metadata)
        
        db.session.commit()
        
        flash(f"Employee {employee.get_full_name()} updated successfully", "success")
        return redirect(url_for('payment_processor.employee_details', employee_id=employee.id))
    
    # Get all users for linking
    users = User.query.order_by(User.username).all()
    
    # Get employee metadata
    metadata = employee.get_metadata()
    
    return render_template(
        'payment_processor/employees/edit.html', 
        employee=employee,
        users=users,
        metadata=metadata,
        payment_frequencies=[f.value for f in PaymentFrequency],
        title=f"Edit Employee: {employee.get_full_name()}"
    )


@payment_processor_bp.route('/payroll')
@login_required
@admin_required
def payroll_list():
    """List all payroll batches"""
    payroll_batches = PayrollBatch.query.order_by(PayrollBatch.payment_date.desc()).all()
    
    # Calculate total amount by status
    pending_total = sum(batch.total_amount for batch in payroll_batches if batch.status == TransactionStatus.PENDING)
    processing_total = sum(batch.total_amount for batch in payroll_batches if batch.status == TransactionStatus.PROCESSING)
    completed_total = sum(batch.total_amount for batch in payroll_batches if batch.status == TransactionStatus.COMPLETED)
    
    return render_template(
        'payment_processor/payroll/list.html', 
        payroll_batches=payroll_batches,
        pending_total=pending_total,
        processing_total=processing_total,
        completed_total=completed_total,
        title="Payroll Management"
    )


@payment_processor_bp.route('/payroll/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_payroll_batch():
    """Create a new payroll batch"""
    if request.method == 'POST':
        # Generate unique batch ID
        batch_id = generate_random_id("PAY")
        
        # Get form data
        payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date()
        description = request.form.get('description')
        institution_id = int(request.form.get('institution_id')) if request.form.get('institution_id') else None
        payment_method = request.form.get('payment_method')
        
        # Get selected employees
        selected_employee_ids = request.form.getlist('employee_ids')
        
        if not selected_employee_ids:
            flash("Please select at least one employee for the payroll batch", "danger")
            return redirect(url_for('payment_processor.new_payroll_batch'))
        
        # Calculate total amount
        employees = Employee.query.filter(Employee.id.in_(selected_employee_ids)).all()
        total_amount = sum(e.salary_amount for e in employees if e.salary_amount)
        
        # Create payroll batch
        payroll_batch = PayrollBatch(
            batch_id=batch_id,
            description=description,
            payment_date=payment_date,
            total_amount=total_amount,
            currency="USD",  # Default currency
            status=TransactionStatus.PENDING,
            processed_by=current_user.id,
            institution_id=institution_id,
            payment_method=payment_method
        )
        
        db.session.add(payroll_batch)
        db.session.commit()
        
        # Create salary payments for each employee
        for employee_id in selected_employee_ids:
            employee = Employee.query.get(employee_id)
            
            if not employee:
                continue
                
            # Calculate period start/end based on frequency
            period_end = payment_date - timedelta(days=1)  # Day before payment
            
            if employee.salary_frequency == PaymentFrequency.WEEKLY:
                period_start = period_end - timedelta(days=6)
            elif employee.salary_frequency == PaymentFrequency.BI_WEEKLY:
                period_start = period_end - timedelta(days=13)
            elif employee.salary_frequency == PaymentFrequency.MONTHLY:
                # Approximate month
                period_start = period_end.replace(day=1)
            else:
                # Default to 2 weeks
                period_start = period_end - timedelta(days=13)
            
            # Create salary payment record
            payment = SalaryPayment(
                employee_id=employee.id,
                payroll_batch_id=payroll_batch.id,
                payment_date=payment_date,
                amount=employee.salary_amount,
                currency="USD",  # Default currency
                payment_method=employee.payment_method or payment_method,
                status=TransactionStatus.PENDING,
                period_start=period_start,
                period_end=period_end,
                description=f"Salary payment for {period_start} to {period_end}"
            )
            
            db.session.add(payment)
        
        db.session.commit()
        
        flash(f"Payroll batch created with {len(selected_employee_ids)} employee payments", "success")
        return redirect(url_for('payment_processor.payroll_batch_details', batch_id=payroll_batch.id))
    
    # Get data for the form
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.last_name).all()
    institutions = FinancialInstitution.query.filter_by(is_active=True).all()
    
    return render_template(
        'payment_processor/payroll/new.html', 
        employees=employees,
        institutions=institutions,
        payment_methods=["direct_deposit", "check", "cash", "bank_transfer"],
        title="Create New Payroll Batch"
    )


@payment_processor_bp.route('/payroll/<int:batch_id>')
@login_required
@admin_required
def payroll_batch_details(batch_id):
    """View payroll batch details"""
    batch = get_or_404(PayrollBatch, batch_id)
    
    # Get all salary payments for this batch
    payments = SalaryPayment.query.filter_by(payroll_batch_id=batch_id).all()
    
    return render_template(
        'payment_processor/payroll/details.html', 
        batch=batch,
        payments=payments,
        title=f"Payroll Batch: {batch.batch_id}"
    )


@payment_processor_bp.route('/payroll/<int:batch_id>/process', methods=['POST'])
@login_required
@admin_required
def process_payroll_batch(batch_id):
    """Process a payroll batch"""
    batch = get_or_404(PayrollBatch, batch_id)
    
    if batch.status != TransactionStatus.PENDING:
        flash("This payroll batch has already been processed", "warning")
        return redirect(url_for('payment_processor.payroll_batch_details', batch_id=batch_id))
    
    # Set batch to processing
    batch.status = TransactionStatus.PROCESSING
    db.session.commit()
    
    # Get all pending salary payments for this batch
    payments = SalaryPayment.query.filter_by(
        payroll_batch_id=batch_id, 
        status=TransactionStatus.PENDING
    ).all()
    
    # Create transaction records for each payment
    for payment in payments:
        # Generate a transaction ID
        transaction_id = generate_transaction_id()
        
        # Create transaction record
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=current_user.id,
            amount=payment.amount,
            currency=payment.currency,
            transaction_type=TransactionType.SALARY_PAYMENT,
            status=TransactionStatus.PROCESSING,
            description=f"Salary payment to {payment.employee.get_full_name()} - {payment.description}",
            institution_id=batch.institution_id
        )
        
        # Add metadata
        metadata = {
            "employee_id": payment.employee.employee_id,
            "employee_name": payment.employee.get_full_name(),
            "payroll_batch_id": batch.batch_id,
            "payment_method": payment.payment_method,
            "period_start": payment.period_start.isoformat() if payment.period_start else None,
            "period_end": payment.period_end.isoformat() if payment.period_end else None,
            "bank_account": payment.employee.bank_account_number,
            "bank_routing": payment.employee.bank_routing_number,
            "bank_name": payment.employee.bank_name
        }
        
        transaction.tx_metadata_json = json.dumps(metadata)
        
        db.session.add(transaction)
        db.session.commit()
        
        # Link transaction to payment
        payment.transaction_id = transaction.id
        payment.status = TransactionStatus.PROCESSING
        db.session.commit()
    
    # For demo purposes, we'll simulate successful processing
    # In a real application, this would communicate with a payment provider
    batch.status = TransactionStatus.COMPLETED
    
    # Update all payments to completed
    for payment in payments:
        payment.status = TransactionStatus.COMPLETED
        
        # Update associated transaction
        if payment.transaction:
            payment.transaction.status = TransactionStatus.COMPLETED
    
    db.session.commit()
    
    flash(f"Payroll batch {batch.batch_id} processed successfully", "success")
    return redirect(url_for('payment_processor.payroll_batch_details', batch_id=batch_id))


# ============================================================
# Vendor and Bill Payment Routes
# ============================================================

@payment_processor_bp.route('/vendors')
@login_required
def vendor_list():
    """List all vendors"""
    vendors = Vendor.query.order_by(Vendor.name).all()
    return render_template(
        'payment_processor/vendors/list.html', 
        vendors=vendors,
        title="Vendor Management"
    )


@payment_processor_bp.route('/vendors/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_vendor():
    """Add a new vendor"""
    if request.method == 'POST':
        # Generate a unique vendor ID
        vendor_id = generate_random_id("VEN")
        
        # Create a new vendor
        vendor = Vendor(
            vendor_id=vendor_id,
            name=request.form.get('name'),
            contact_name=request.form.get('contact_name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            website=request.form.get('website'),
            payment_terms=request.form.get('payment_terms'),
            bank_account_number=request.form.get('bank_account_number'),
            bank_routing_number=request.form.get('bank_routing_number'),
            bank_name=request.form.get('bank_name'),
            payment_method=request.form.get('payment_method'),
            tax_id=request.form.get('tax_id')
        )
        
        # Add metadata if needed
        metadata = {}
        if request.form.get('notes'):
            metadata['notes'] = request.form.get('notes')
        if request.form.get('categories'):
            metadata['categories'] = request.form.get('categories').split(',')
        
        if metadata:
            vendor.metadata_json = json.dumps(metadata)
        
        db.session.add(vendor)
        db.session.commit()
        
        flash(f"Vendor {vendor.name} added successfully", "success")
        return redirect(url_for('payment_processor.vendor_list'))
    
    return render_template(
        'payment_processor/vendors/new.html',
        payment_methods=["bank_transfer", "check", "ach", "wire"],
        payment_terms=["Net 15", "Net 30", "Net 60", "Due on Receipt"],
        title="Add New Vendor"
    )


@payment_processor_bp.route('/vendors/<int:vendor_id>')
@login_required
def vendor_details(vendor_id):
    """View vendor details"""
    vendor = get_or_404(Vendor, vendor_id)
    
    # Get recent bills and contracts
    recent_bills = Bill.query.filter_by(vendor_id=vendor_id).order_by(Bill.due_date.desc()).limit(5).all()
    contracts = Contract.query.filter_by(vendor_id=vendor_id).order_by(Contract.start_date.desc()).all()
    
    return render_template(
        'payment_processor/vendors/details.html', 
        vendor=vendor,
        recent_bills=recent_bills,
        contracts=contracts,
        title=f"Vendor: {vendor.name}"
    )


@payment_processor_bp.route('/bills')
@login_required
def bill_list():
    """List all bills"""
    # Filter options
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')
    vendor_filter = request.args.get('vendor_id')
    
    # Build query
    query = Bill.query
    
    if status_filter:
        query = query.filter(Bill.status == TransactionStatus(status_filter))
    
    if category_filter:
        query = query.filter(Bill.category == BillCategory(category_filter))
    
    if vendor_filter:
        query = query.filter(Bill.vendor_id == int(vendor_filter))
    
    # Get bills ordered by due date (most urgent first)
    bills = query.order_by(Bill.due_date).all()
    
    # Get vendors for filter dropdown
    vendors = Vendor.query.order_by(Vendor.name).all()
    
    # Calculate totals
    pending_total = sum(bill.amount for bill in bills if bill.status == TransactionStatus.PENDING)
    overdue_total = sum(bill.amount for bill in bills if bill.status == TransactionStatus.PENDING and bill.due_date < date.today())
    
    return render_template(
        'payment_processor/bills/list.html', 
        bills=bills,
        vendors=vendors,
        categories=[c.value for c in BillCategory],
        statuses=[s.value for s in TransactionStatus],
        pending_total=pending_total,
        overdue_total=overdue_total,
        selected_status=status_filter,
        selected_category=category_filter,
        selected_vendor=vendor_filter,
        title="Bill Management",
        today=date.today()
    )


@payment_processor_bp.route('/bills/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_bill():
    """Add a new bill"""
    if request.method == 'POST':
        # Generate a unique bill number
        bill_number = generate_random_id("BILL")
        
        # Parse dates
        issue_date = datetime.strptime(request.form.get('issue_date'), '%Y-%m-%d').date()
        due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        
        # Determine if recurring
        recurring = 'recurring' in request.form
        
        # Create a new bill
        bill = Bill(
            bill_number=bill_number,
            vendor_id=int(request.form.get('vendor_id')),
            category=BillCategory(request.form.get('category')),
            amount=float(request.form.get('amount')),
            currency=request.form.get('currency', 'USD'),
            issue_date=issue_date,
            due_date=due_date,
            status=TransactionStatus.PENDING,
            description=request.form.get('description'),
            recurring=recurring
        )
        
        # Set frequency if recurring
        if recurring:
            bill.frequency = PaymentFrequency(request.form.get('frequency'))
        
        # Add metadata for line items if provided
        if request.form.get('line_items'):
            try:
                line_items = json.loads(request.form.get('line_items'))
                bill.metadata_json = json.dumps({"line_items": line_items})
            except:
                # If JSON is invalid, just store as text
                bill.metadata_json = json.dumps({"line_items_text": request.form.get('line_items')})
        
        db.session.add(bill)
        db.session.commit()
        
        flash(f"Bill {bill.bill_number} added successfully", "success")
        return redirect(url_for('payment_processor.bill_list'))
    
    # Get vendors for the dropdown
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()
    
    return render_template(
        'payment_processor/bills/new.html', 
        vendors=vendors,
        categories=[c.value for c in BillCategory],
        frequencies=[f.value for f in PaymentFrequency],
        currencies=["USD", "EUR", "GBP", "CAD", "AUD"],
        title="Add New Bill"
    )


@payment_processor_bp.route('/bills/<int:bill_id>')
@login_required
def bill_details(bill_id):
    """View bill details"""
    bill = get_or_404(Bill, bill_id)
    
    # Get payment transaction if exists
    transaction = bill.transaction
    
    return render_template(
        'payment_processor/bills/details.html', 
        bill=bill,
        transaction=transaction,
        title=f"Bill: {bill.bill_number}",
        today=date.today()
    )


@payment_processor_bp.route('/bills/<int:bill_id>/pay', methods=['GET', 'POST'])
@login_required
@admin_required
def pay_bill(bill_id):
    """Pay a bill"""
    bill = get_or_404(Bill, bill_id)
    
    if bill.status != TransactionStatus.PENDING:
        flash("This bill has already been processed", "warning")
        return redirect(url_for('payment_processor.bill_details', bill_id=bill_id))
    
    if request.method == 'POST':
        # Get payment details
        payment_method = request.form.get('payment_method')
        institution_id = int(request.form.get('institution_id')) if request.form.get('institution_id') else None
        payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date()
        
        # Generate a transaction ID
        transaction_id = generate_transaction_id()
        
        # Create transaction record
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=current_user.id,
            amount=bill.amount,
            currency=bill.currency,
            transaction_type=TransactionType.BILL_PAYMENT,
            status=TransactionStatus.PROCESSING,
            description=f"Payment for bill {bill.bill_number} to {bill.vendor.name}",
            institution_id=institution_id
        )
        
        # Add metadata
        metadata = {
            "bill_number": bill.bill_number,
            "vendor_id": bill.vendor.vendor_id,
            "vendor_name": bill.vendor.name,
            "payment_method": payment_method,
            "category": bill.category.value,
            "bank_account": bill.vendor.bank_account_number,
            "bank_routing": bill.vendor.bank_routing_number,
            "bank_name": bill.vendor.bank_name
        }
        
        transaction.tx_metadata_json = json.dumps(metadata)
        
        db.session.add(transaction)
        db.session.commit()
        
        # Update bill
        bill.transaction_id = transaction.id
        bill.status = TransactionStatus.PROCESSING
        bill.payment_date = payment_date
        
        # For demo purposes, we'll simulate successful processing
        # In a real application, this would communicate with a payment provider
        bill.status = TransactionStatus.COMPLETED
        transaction.status = TransactionStatus.COMPLETED
        
        db.session.commit()
        
        flash(f"Bill {bill.bill_number} paid successfully", "success")
        return redirect(url_for('payment_processor.bill_details', bill_id=bill_id))
    
    # Get institutions for payment
    institutions = FinancialInstitution.query.filter_by(is_active=True).all()
    
    return render_template(
        'payment_processor/bills/pay.html', 
        bill=bill,
        institutions=institutions,
        payment_methods=["bank_transfer", "check", "ach", "wire"],
        title=f"Pay Bill: {bill.bill_number}"
    )


# ============================================================
# Contract Management Routes
# ============================================================

@payment_processor_bp.route('/contracts')
@login_required
def contract_list():
    """List all contracts"""
    # Filter options
    status_filter = request.args.get('status')
    contract_type_filter = request.args.get('contract_type')
    vendor_filter = request.args.get('vendor_id')
    
    # Build query
    query = Contract.query
    
    if status_filter:
        query = query.filter(Contract.status == status_filter)
    
    if contract_type_filter:
        query = query.filter(Contract.contract_type == ContractType(contract_type_filter))
    
    if vendor_filter:
        query = query.filter(Contract.vendor_id == int(vendor_filter))
    
    # Get contracts ordered by start date (most recent first)
    contracts = query.order_by(Contract.start_date.desc()).all()
    
    # Get vendors for filter dropdown
    vendors = Vendor.query.order_by(Vendor.name).all()
    
    # Calculate active contract total value
    active_total = sum(c.total_value for c in contracts if c.status == "active" and c.total_value)
    
    return render_template(
        'payment_processor/contracts/list.html', 
        contracts=contracts,
        vendors=vendors,
        contract_types=[c.value for c in ContractType],
        statuses=["active", "completed", "terminated"],
        active_total=active_total,
        selected_status=status_filter,
        selected_contract_type=contract_type_filter,
        selected_vendor=vendor_filter,
        title="Contract Management"
    )


@payment_processor_bp.route('/contracts/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_contract():
    """Add a new contract"""
    if request.method == 'POST':
        # Generate a unique contract number
        contract_number = generate_random_id("CONT")
        
        # Parse dates
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date() if request.form.get('end_date') else None
        
        # Create a new contract
        contract = Contract(
            contract_number=contract_number,
            vendor_id=int(request.form.get('vendor_id')),
            title=request.form.get('title'),
            description=request.form.get('description'),
            contract_type=ContractType(request.form.get('contract_type')),
            start_date=start_date,
            end_date=end_date,
            total_value=float(request.form.get('total_value')) if request.form.get('total_value') else None,
            currency=request.form.get('currency', 'USD'),
            payment_terms=request.form.get('payment_terms'),
            status="active"
        )
        
        # Handle file upload if provided
        if 'contract_file' in request.files:
            file = request.files['contract_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = f"contracts/{contract_number}_{filename}"
                
                # In a real application, save the file to storage
                # For demo, we'll just store the path
                contract.file_path = file_path
        
        db.session.add(contract)
        db.session.commit()
        
        flash(f"Contract {contract.contract_number} added successfully", "success")
        return redirect(url_for('payment_processor.contract_list'))
    
    # Get vendors for the dropdown
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()
    
    return render_template(
        'payment_processor/contracts/new.html', 
        vendors=vendors,
        contract_types=[c.value for c in ContractType],
        currencies=["USD", "EUR", "GBP", "CAD", "AUD"],
        payment_terms=["Net 15", "Net 30", "Net 60", "Due on Receipt", "Milestone-based"],
        title="Add New Contract"
    )


@payment_processor_bp.route('/contracts/<int:contract_id>')
@login_required
def contract_details(contract_id):
    """View contract details"""
    # Check if user is admin or has contract management permissions
    if not is_admin(current_user):
        flash("You don't have permission to view contract information", "danger")
        return redirect(url_for(INDEX_ROUTE))
    
    contract = get_or_404(Contract, contract_id)
    
    # Get contract payments
    payments = ContractPayment.query.filter_by(contract_id=contract_id).order_by(ContractPayment.due_date).all()
    
    # Calculate payment stats
    paid_amount = sum(p.amount for p in payments if p.status == TransactionStatus.COMPLETED)
    pending_amount = sum(p.amount for p in payments if p.status == TransactionStatus.PENDING)
    
    return render_template(
        'payment_processor/contracts/details.html', 
        contract=contract,
        payments=payments,
        paid_amount=paid_amount,
        pending_amount=pending_amount,
        title=f"Contract: {contract.contract_number}"
    )


@payment_processor_bp.route('/contracts/<int:contract_id>/add-payment', methods=['GET', 'POST'])
@login_required
@admin_required
def add_contract_payment(contract_id):
    """Add a payment schedule to a contract"""
    contract = get_or_404(Contract, contract_id)
    
    if request.method == 'POST':
        # Generate a unique payment number
        payment_number = generate_random_id("CPAY")
        
        # Parse dates
        due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        
        # Create contract payment
        payment = ContractPayment(
            contract_id=contract_id,
            payment_number=payment_number,
            amount=float(request.form.get('amount')),
            currency=contract.currency,
            due_date=due_date,
            description=request.form.get('description'),
            milestone=request.form.get('milestone'),
            status=TransactionStatus.PENDING
        )
        
        db.session.add(payment)
        db.session.commit()
        
        flash(f"Payment schedule added to contract {contract.contract_number}", "success")
        return redirect(url_for('payment_processor.contract_details', contract_id=contract_id))
    
    return render_template(
        'payment_processor/contracts/add_payment.html',
        contract=contract,
        title=f"Add Payment to Contract: {contract.contract_number}"
    )


@payment_processor_bp.route('/contracts/<int:contract_id>/payments/<int:payment_id>/process', methods=['GET', 'POST'])
@login_required
@admin_required
def process_contract_payment(contract_id, payment_id):
    """Process a contract payment"""
    contract = get_or_404(Contract, contract_id)
    payment = get_or_404(ContractPayment, payment_id)
    
    if payment.contract_id != contract_id:
        flash("Invalid payment for this contract", "danger")
        return redirect(url_for('payment_processor.contract_details', contract_id=contract_id))
    
    if payment.status != TransactionStatus.PENDING:
        flash("This payment has already been processed", "warning")
        return redirect(url_for('payment_processor.contract_details', contract_id=contract_id))
    
    if request.method == 'POST':
        # Get payment details
        payment_method = request.form.get('payment_method')
        institution_id = int(request.form.get('institution_id')) if request.form.get('institution_id') else None
        payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date()
        
        # Generate a transaction ID
        transaction_id = generate_transaction_id()
        
        # Create transaction record
        transaction = Transaction(
            transaction_id=transaction_id,
            user_id=current_user.id,
            amount=payment.amount,
            currency=payment.currency,
            transaction_type=TransactionType.CONTRACT_PAYMENT,
            status=TransactionStatus.PROCESSING,
            description=f"Payment {payment.payment_number} for contract {contract.contract_number} to {contract.vendor.name}",
            institution_id=institution_id
        )
        
        # Add metadata
        metadata = {
            "contract_number": contract.contract_number,
            "payment_number": payment.payment_number,
            "vendor_id": contract.vendor.vendor_id,
            "vendor_name": contract.vendor.name,
            "payment_method": payment_method,
            "milestone": payment.milestone,
            "bank_account": contract.vendor.bank_account_number,
            "bank_routing": contract.vendor.bank_routing_number,
            "bank_name": contract.vendor.bank_name
        }
        
        transaction.tx_metadata_json = json.dumps(metadata)
        
        db.session.add(transaction)
        db.session.commit()
        
        # Update payment
        payment.transaction_id = transaction.id
        payment.status = TransactionStatus.PROCESSING
        payment.payment_date = payment_date
        
        # For demo purposes, we'll simulate successful processing
        # In a real application, this would communicate with a payment provider
        payment.status = TransactionStatus.COMPLETED
        transaction.status = TransactionStatus.COMPLETED
        
        db.session.commit()
        
        flash(f"Contract payment {payment.payment_number} processed successfully", "success")
        return redirect(url_for('payment_processor.contract_details', contract_id=contract_id))
    
    # Get institutions for payment
    institutions = FinancialInstitution.query.filter_by(is_active=True).all()
    
    return render_template(
        'payment_processor/contracts/process_payment.html', 
        contract=contract,
        payment=payment,
        institutions=institutions,
        payment_methods=["bank_transfer", "check", "ach", "wire"],
        title=f"Process Contract Payment: {payment.payment_number}"
    )


# Register the blueprint
def register_payment_processor_routes(app):
    app.register_blueprint(payment_processor_bp)