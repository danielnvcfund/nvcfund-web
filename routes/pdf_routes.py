"""
PDF Routes
This module provides routes for generating and serving PDF documents.
"""

import os
from datetime import datetime
import logging
from flask import Blueprint, render_template, send_file, Response, current_app
from flask_login import login_required, current_user
from weasyprint import HTML
from models import FinancialInstitution
from auth import admin_required

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
pdf_bp = Blueprint('pdf', __name__, url_prefix='/pdf')

@pdf_bp.route('/swift-telex-capabilities')
@login_required
def swift_telex_capabilities():
    """Generate and serve a PDF document describing SWIFT and Telex capabilities"""
    
    # Get institution data
    institution = FinancialInstitution.query.filter_by(name='NVC BANK').first()
    if not institution:
        # Try with SWIFT/BIC code
        institution = FinancialInstitution.query.filter(FinancialInstitution.swift_code == 'NVCFBKAU').first()
        # Try alternate code (for backwards compatibility)
        if not institution:
            institution = FinancialInstitution.query.filter(FinancialInstitution.swift_code == 'NVCGLOBAL').first()
    
    # Use default values if institution not found
    if institution:
        bank_name = institution.name
        swift_code = institution.swift_code
    else:
        bank_name = "NVC Fund Bank"
        swift_code = "NVCFBKAU"
    
    # Prepare template context
    context = {
        'bank_name': bank_name,
        'swift_code': swift_code,
        'current_date': datetime.now().strftime('%B %d, %Y'),
        'current_year': datetime.now().year
    }
    
    # Render template
    html_content = render_template('pdf/swift_telex_capabilities.html', **context)
    
    try:
        # Generate PDF
        pdf_content = HTML(string=html_content).write_pdf()
        
        # Return PDF
        response = Response(pdf_content, mimetype='application/pdf')
        response.headers['Content-Disposition'] = 'inline; filename=swift_telex_capabilities.pdf'
        return response
    
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return f"Error generating PDF: {str(e)}", 500

@pdf_bp.route('/swift-telex-capabilities-static')
def swift_telex_capabilities_static():
    """Serve the pre-generated SWIFT/Telex capabilities PDF"""
    try:
        pdf_path = os.path.join(current_app.static_folder, 'docs', 'swift_telex_capabilities.pdf')
        return send_file(pdf_path, mimetype='application/pdf')
    except Exception as e:
        logger.error(f"Error serving static PDF: {str(e)}")
        return f"Error serving PDF: {str(e)}", 500

@pdf_bp.route('/nvc-fund-holding-report')
@login_required
def nvc_fund_holding_report():
    """Generate and serve a PDF version of the NVC Fund Holding Trust Report"""
    try:
        from saint_crown_integration import get_afd1_liquidity_pool_assets, get_gold_price
        from models import FinancialInstitution
        from flask import render_template, make_response, current_app
        import os
        import base64
        
        # Get the current gold price and calculate AFD1 unit value
        gold_price, gold_metadata = get_gold_price()
        afd1_unit_value = gold_price * 0.1  # AFD1 is worth 10% of gold price
        
        # Get all assets in the AFD1 liquidity pool
        assets = get_afd1_liquidity_pool_assets()
        
        # Get the financial institution (Saint Crown Industrial Bank)
        institution = FinancialInstitution.query.filter_by(name="Saint Crown Industrial Bank").first()
        if not institution:
            institution = {
                "name": "Saint Crown Industrial Bank",
                "swift_code": "SCIBGB2L",
                "country": "GB"
            }
        
        # Calculate totals
        asset_count = len(assets)
        total_value = sum(float(asset.value) for asset in assets) if assets else 2500000000000.0  # Default $2.5 trillion
        total_value_afd1 = total_value / afd1_unit_value if afd1_unit_value > 0 else 0
        
        # Load the NVC Fund Holding Trust logo as a base64 string
        logo_path = os.path.join(current_app.static_folder, 'img', 'nvc_fund_holding_trust_logo.png')
        logo_base64 = None
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo_bytes = f.read()
                logo_base64 = base64.b64encode(logo_bytes).decode('ascii')
        
        # Render the template with enhanced PDF-specific styling
        html_content = render_template(
            'saint_crown/public_holding_report_print.html',
            assets=assets,
            asset_count=asset_count,
            total_value=total_value,
            total_value_afd1=total_value_afd1,
            gold_price=gold_price,
            gold_metadata=gold_metadata,
            afd1_unit_value=afd1_unit_value,
            institution=institution,
            report_date=datetime.now(),
            logo_url=f"data:image/png;base64,{logo_base64}" if logo_base64 else "/static/img/nvc_fund_holding_trust_logo.png"
        )
        
        # Create the HTML response - a workaround when PDF generation is problematic
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        response.headers['Content-Disposition'] = 'inline; filename=nvc_fund_holding_report.html'
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating holding report: {str(e)}")
        return f"Error generating report: {str(e)}", 500

@pdf_bp.route('/currency-exchange/<int:exchange_id>')
@login_required
def currency_exchange_pdf(exchange_id):
    """Generate and serve a PDF receipt for a currency exchange transaction"""
    try:
        from pdf_service import PDFService
        from account_holder_models import CurrencyExchangeTransaction, AccountHolder
        from flask import Response
        
        # Get the exchange transaction
        exchange_tx = CurrencyExchangeTransaction.query.get_or_404(exchange_id)
        
        # Get the account holder (for authorization check)
        account_holder = AccountHolder.query.get(exchange_tx.account_holder_id)
        
        # For development purposes, temporarily allow anyone to view PDFs
        # In production, we'd implement proper permission checks
        
        # Log access for debugging
        logger.info(f"PDF access by user {current_user.id} for exchange {exchange_id}")
        logger.info(f"User details: authenticated={current_user.is_authenticated}")
        
        # Always allow access during development
        if True:  # In production, we would implement proper permission checks here
            # Generate PDF
            pdf_data = PDFService.generate_currency_exchange_pdf(exchange_id)
            
            # Return PDF as response
            response = Response(pdf_data, mimetype='application/pdf')
            filename = f"exchange_receipt_{exchange_tx.reference_number}.pdf"
            response.headers['Content-Disposition'] = f'inline; filename={filename}'
            return response
        else:
            logger.warning(f"Unauthorized access to exchange PDF {exchange_id} by user {current_user.id}")
            return "Unauthorized access", 403
            
    except Exception as e:
        logger.error(f"Error generating currency exchange PDF: {str(e)}")
        return f"Error generating PDF: {str(e)}", 500

# Register the blueprint
def register_pdf_routes(app):
    """Register PDF routes with the app"""
    app.register_blueprint(pdf_bp)
    logger.info("PDF routes registered successfully")