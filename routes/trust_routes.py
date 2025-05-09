"""
Trust Portfolio Routes for NVC Banking Platform
This module provides web routes for viewing and managing trust portfolios.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
import logging
from decimal import Decimal
import json

from app import db
from models import UserRole
from trust_portfolio import (
    TrustFund, TrustPortfolio, TrustAsset, AssetValuation, 
    PortfolioValuation, AssetCategory, AssetStatus
)
from trust_service import (
    initialize_nvc_ghl_fund, get_nvc_ghl_fund, get_nvc_ghl_fund_current_valuation,
    get_portfolio_valuation_history, get_asset_valuation_history,
    update_portfolio_valuation, add_trust_asset,
    get_all_trust_funds, get_trust_fund_portfolios, get_portfolio_assets,
    get_asset, get_portfolio, get_trust_fund, create_nvc_skr_072809_001_asset,
    create_paa_foundation_bond_asset
)

logger = logging.getLogger(__name__)

# Create the blueprint
trust_bp = Blueprint('trust', __name__, url_prefix='/trust')

# Custom decorator for admin access only
def admin_required(func):
    """Decorator for views that require admin access"""
    @login_required
    def decorated_view(*args, **kwargs):
        if not hasattr(current_user, 'role') or current_user.role != UserRole.ADMIN:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('web.main.dashboard'))
        return func(*args, **kwargs)
    
    # Set the name of the decorated function to the original function name
    decorated_view.__name__ = func.__name__
    return decorated_view

@trust_bp.route('/')
@login_required
def index():
    """Trust portfolios main page"""
    trust_funds = get_all_trust_funds()
    return render_template(
        'trust/index.html', 
        title='Trust Portfolios',
        trust_funds=trust_funds
    )

@trust_bp.route('/nvc-ghl-fund')
@login_required
def nvc_ghl_fund():
    """NVC GHL Fund page"""
    # Initialize if needed and get the fund
    fund = get_nvc_ghl_fund()
    if not fund:
        try:
            fund = initialize_nvc_ghl_fund()
            flash('NVC GHL Fund has been initialized.', 'success')
        except Exception as e:
            logger.error(f"Error initializing NVC GHL Fund: {str(e)}")
            flash(f'Error initializing NVC GHL Fund: {str(e)}', 'danger')
            return redirect(url_for('trust.index'))
    
    # Get portfolios and valuation
    portfolios = get_trust_fund_portfolios(fund.id)
    valuation = get_nvc_ghl_fund_current_valuation()
    
    return render_template(
        'trust/nvc_ghl_fund.html',
        title='NVC GHL Fund',
        fund=fund,
        portfolios=portfolios,
        valuation=valuation
    )

@trust_bp.route('/fund/<int:fund_id>')
@login_required
def fund_detail(fund_id):
    """Trust fund detail page"""
    fund = get_trust_fund(fund_id)
    if not fund:
        flash('Trust fund not found.', 'danger')
        return redirect(url_for('trust.index'))
    
    portfolios = get_trust_fund_portfolios(fund.id)
    
    # Calculate total value
    total_value = Decimal('0')
    for portfolio in portfolios:
        valuation = portfolio.current_valuation()
        if valuation:
            total_value += valuation.total_value
    
    return render_template(
        'trust/fund_detail.html',
        title=fund.name,
        fund=fund,
        portfolios=portfolios,
        total_value=float(total_value)
    )

@trust_bp.route('/portfolio/<int:portfolio_id>')
@login_required
def portfolio_detail(portfolio_id):
    """Portfolio detail page"""
    portfolio = get_portfolio(portfolio_id)
    if not portfolio:
        flash('Portfolio not found.', 'danger')
        return redirect(url_for('trust.index'))
    
    # Check if this is a portfolio of the NVC GHL Fund and try to add the SKR asset if it doesn't exist
    fund = get_nvc_ghl_fund()
    if fund and portfolio.trust_fund_id == fund.id:
        try:
            # Create the SKR asset if it doesn't exist already
            skr_asset = create_nvc_skr_072809_001_asset()
            if skr_asset and hasattr(skr_asset, 'id'):
                logger.info(f"SKR 072809-001 asset verified, ID: {skr_asset.id}")
        except Exception as e:
            logger.error(f"Error verifying SKR asset: {str(e)}")
    
    assets = get_portfolio_assets(portfolio.id)
    valuation_history = get_portfolio_valuation_history(portfolio.id)
    
    return render_template(
        'trust/portfolio_detail.html',
        title=portfolio.name,
        portfolio=portfolio,
        assets=assets,
        valuation_history=valuation_history,
        asset_categories=AssetCategory,
        asset_statuses=AssetStatus
    )

@trust_bp.route('/asset/<int:asset_id>')
@login_required
def asset_detail(asset_id):
    """Asset detail page"""
    asset = get_asset(asset_id)
    if not asset:
        flash('Asset not found.', 'danger')
        return redirect(url_for('trust.index'))
    
    valuation_history = get_asset_valuation_history(asset.id)
    metadata = asset.get_metadata()
    
    return render_template(
        'trust/asset_detail.html',
        title=asset.name,
        asset=asset,
        valuation_history=valuation_history,
        metadata=metadata
    )

@trust_bp.route('/portfolio/<int:portfolio_id>/add-asset', methods=['GET', 'POST'])
@login_required
def add_asset(portfolio_id):
    """Add a new asset to a portfolio"""
    portfolio = get_portfolio(portfolio_id)
    if not portfolio:
        flash('Portfolio not found.', 'danger')
        return redirect(url_for('trust.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        value = request.form.get('value')
        currency = request.form.get('currency', 'USD')
        status = request.form.get('status')
        location = request.form.get('location')
        
        if not name or not value or not category:
            flash('Asset name, category, and value are required.', 'danger')
            return redirect(url_for('trust.add_asset', portfolio_id=portfolio.id))
        
        try:
            # Convert string to enum
            asset_category = AssetCategory(category)
            asset_status = AssetStatus(status) if status else AssetStatus.ACTIVE
            
            add_trust_asset(
                portfolio_id=portfolio.id,
                name=name,
                description=description,
                category=asset_category,
                value=value,
                currency=currency,
                status=asset_status,
                location=location
            )
            
            flash(f'Asset "{name}" has been added to the portfolio.', 'success')
            return redirect(url_for('trust.portfolio_detail', portfolio_id=portfolio.id))
        
        except Exception as e:
            logger.error(f"Error adding asset: {str(e)}")
            flash(f'Error adding asset: {str(e)}', 'danger')
    
    return render_template(
        'trust/add_asset.html',
        title='Add Asset',
        portfolio=portfolio,
        asset_categories=[category.value for category in AssetCategory],
        asset_statuses=[status.value for status in AssetStatus]
    )

@trust_bp.route('/portfolio/<int:portfolio_id>/add-nvc-skr-072809', methods=['GET'])
@login_required
def add_nvc_skr_072809(portfolio_id):
    """Add the NVC-SKR-CD ST200602017-082809 asset to the portfolio"""
    try:
        # Create the SKR asset
        asset = create_nvc_skr_072809_001_asset()
        
        if asset:
            flash(f'NVC-SKR-CD ST200602017-082809 asset has been added to the portfolio.', 'success')
            return redirect(url_for('trust.asset_detail', asset_id=asset.id))
        else:
            flash('Failed to create NVC-SKR-CD asset.', 'danger')
            return redirect(url_for('trust.portfolio_detail', portfolio_id=portfolio_id))
            
    except Exception as e:
        logger.error(f"Error adding NVC-SKR-CD asset: {str(e)}")
        flash(f'Error adding NVC-SKR-CD asset: {str(e)}', 'danger')
        return redirect(url_for('trust.portfolio_detail', portfolio_id=portfolio_id))

@trust_bp.route('/portfolio/<int:portfolio_id>/add-paa-foundation-bond', methods=['GET'])
@login_required
def add_paa_foundation_bond(portfolio_id):
    """Add the Pacific Asian Atlantic Foundation Bond asset to the portfolio"""
    try:
        # Create the PAA Foundation Bond asset
        asset = create_paa_foundation_bond_asset()
        
        if asset:
            flash(f'Pacific Asian Atlantic Foundation Bond asset has been added to the portfolio.', 'success')
            return redirect(url_for('trust.asset_detail', asset_id=asset.id))
        else:
            flash('Failed to create Pacific Asian Atlantic Foundation Bond asset.', 'danger')
            return redirect(url_for('trust.portfolio_detail', portfolio_id=portfolio_id))
            
    except Exception as e:
        logger.error(f"Error adding Pacific Asian Atlantic Foundation Bond asset: {str(e)}")
        flash(f'Error adding PAA Foundation Bond asset: {str(e)}', 'danger')
        return redirect(url_for('trust.portfolio_detail', portfolio_id=portfolio_id))

@trust_bp.route('/portfolio/<int:portfolio_id>/add-safekeeping-receipt', methods=['GET', 'POST'])
@login_required
def add_safekeeping_receipt(portfolio_id):
    """Add a safekeeping receipt (SKR) asset to the portfolio"""
    portfolio = get_portfolio(portfolio_id)
    if not portfolio:
        flash('Portfolio not found.', 'danger')
        return redirect(url_for('trust.index'))
    
    if request.method == 'POST':
        skr_number = request.form.get('skr_number')
        amount = request.form.get('amount')
        issuer = request.form.get('issuer')
        issue_date_str = request.form.get('issue_date')
        maturity_date_str = request.form.get('maturity_date')
        beneficiary = request.form.get('beneficiary')
        description = request.form.get('description')
        
        if not skr_number or not amount or not issuer or not issue_date_str or not maturity_date_str or not beneficiary:
            flash('All fields are required.', 'danger')
            return redirect(url_for('trust.add_safekeeping_receipt', portfolio_id=portfolio.id))
        
        try:
            # Convert date strings to date objects
            issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date()
            maturity_date = datetime.strptime(maturity_date_str, '%Y-%m-%d').date()
            
            # Create the SKR asset
            asset = create_safekeeping_receipt_asset(
                portfolio_id=portfolio.id,
                skr_number=skr_number,
                amount=float(amount),
                issuer=issuer,
                issue_date=issue_date,
                maturity_date=maturity_date,
                beneficiary=beneficiary,
                description=description
            )
            
            flash(f'Safekeeping Receipt {skr_number} has been added to the portfolio.', 'success')
            return redirect(url_for('trust.asset_detail', asset_id=asset.id))
        except Exception as e:
            flash(f'Error adding Safekeeping Receipt: {str(e)}', 'danger')
            return redirect(url_for('trust.add_safekeeping_receipt', portfolio_id=portfolio.id))
    
    # For GET requests, display the form
    return render_template(
        'trust/add_safekeeping_receipt.html',
        title='Add Safekeeping Receipt',
        portfolio=portfolio
    )

@trust_bp.route('/portfolio/<int:portfolio_id>/update-valuation', methods=['POST'])
@admin_required
def update_portfolio_valuation_route(portfolio_id):
    """Update portfolio valuation"""
    portfolio = get_portfolio(portfolio_id)
    if not portfolio:
        flash('Portfolio not found.', 'danger')
        return redirect(url_for('trust.index'))
    
    total_value = request.form.get('total_value')
    currency = request.form.get('currency', 'USD')
    valuation_method = request.form.get('valuation_method', 'Manual Update')
    assessor = request.form.get('assessor', current_user.username)
    notes = request.form.get('notes')
    
    if not total_value:
        flash('Total value is required.', 'danger')
        return redirect(url_for('trust.portfolio_detail', portfolio_id=portfolio.id))
    
    try:
        update_portfolio_valuation(
            portfolio_id=portfolio.id,
            total_value=total_value,
            currency=currency,
            valuation_method=valuation_method,
            assessor=assessor,
            notes=notes
        )
        
        flash('Portfolio valuation has been updated.', 'success')
    except Exception as e:
        logger.error(f"Error updating portfolio valuation: {str(e)}")
        flash(f'Error updating portfolio valuation: {str(e)}', 'danger')
    
    return redirect(url_for('trust.portfolio_detail', portfolio_id=portfolio.id))

@trust_bp.route('/asset/<int:asset_id>/update-value', methods=['POST'])
@admin_required
def update_asset_value(asset_id):
    """Update asset value"""
    asset = get_asset(asset_id)
    if not asset:
        flash('Asset not found.', 'danger')
        return redirect(url_for('trust.index'))
    
    value = request.form.get('value')
    currency = request.form.get('currency', 'USD')
    valuation_method = request.form.get('valuation_method', 'Manual Update')
    appraiser = request.form.get('appraiser', current_user.username)
    notes = request.form.get('notes')
    
    if not value:
        flash('Value is required.', 'danger')
        return redirect(url_for('trust.asset_detail', asset_id=asset.id))
    
    try:
        # Create a new asset valuation
        valuation = AssetValuation(
            asset_id=asset.id,
            value=Decimal(str(value)),
            currency=currency,
            valuation_date=datetime.utcnow(),
            valuation_method=valuation_method,
            appraiser=appraiser,
            notes=notes
        )
        db.session.add(valuation)
        
        # Update portfolio valuation
        portfolio = asset.portfolio
        total_value = sum(float(a.current_value() or 0) for a in portfolio.assets)
        
        portfolio_valuation = PortfolioValuation(
            portfolio_id=portfolio.id,
            total_value=Decimal(str(total_value)),
            currency='USD',
            valuation_date=datetime.utcnow(),
            valuation_method='Asset Value Update',
            assessor=appraiser,
            notes=f'Updated after changing value of {asset.name}'
        )
        db.session.add(portfolio_valuation)
        db.session.commit()
        
        flash('Asset value has been updated.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating asset value: {str(e)}")
        flash(f'Error updating asset value: {str(e)}', 'danger')
    
    return redirect(url_for('trust.asset_detail', asset_id=asset.id))

@trust_bp.route('/add-fund', methods=['GET', 'POST'])
@admin_required
def add_fund():
    """Add a new trust fund"""
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        description = request.form.get('description')
        established_date_str = request.form.get('established_date')
        grantor = request.form.get('grantor')
        trustee = request.form.get('trustee')
        co_trustees = request.form.get('co_trustees')
        beneficiary = request.form.get('beneficiary')
        account_number = request.form.get('account_number')
        
        if not name:
            flash('Fund name is required.', 'danger')
            return redirect(url_for('trust.add_fund'))
        
        try:
            # Parse established date if provided
            established_date = None
            if established_date_str:
                established_date = datetime.strptime(established_date_str, '%Y-%m-%d').date()
            
            # Create the fund
            fund = TrustFund(
                name=name,
                code=code,
                description=description,
                established_date=established_date,
                grantor=grantor,
                trustee=trustee,
                co_trustees=co_trustees,
                beneficiary=beneficiary,
                account_number=account_number
            )
            db.session.add(fund)
            db.session.commit()
            
            flash(f'Trust fund "{name}" has been added.', 'success')
            return redirect(url_for('trust.fund_detail', fund_id=fund.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding trust fund: {str(e)}")
            flash(f'Error adding trust fund: {str(e)}', 'danger')
    
    return render_template(
        'trust/add_fund.html',
        title='Add Trust Fund'
    )

@trust_bp.route('/fund/<int:fund_id>/add-portfolio', methods=['GET', 'POST'])
@admin_required
def add_portfolio(fund_id):
    """Add a new portfolio to a trust fund"""
    fund = get_trust_fund(fund_id)
    if not fund:
        flash('Trust fund not found.', 'danger')
        return redirect(url_for('trust.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Portfolio name is required.', 'danger')
            return redirect(url_for('trust.add_portfolio', fund_id=fund.id))
        
        try:
            # Create the portfolio
            portfolio = TrustPortfolio(
                name=name,
                description=description,
                trust_fund_id=fund.id
            )
            db.session.add(portfolio)
            db.session.commit()
            
            # Create initial portfolio valuation
            initial_valuation = PortfolioValuation(
                portfolio_id=portfolio.id,
                total_value=Decimal('0.00'),
                currency='USD',
                valuation_date=datetime.utcnow(),
                valuation_method='Initial Valuation',
                assessor=current_user.username,
                notes='Initial portfolio valuation'
            )
            db.session.add(initial_valuation)
            db.session.commit()
            
            flash(f'Portfolio "{name}" has been added to the trust fund.', 'success')
            return redirect(url_for('trust.portfolio_detail', portfolio_id=portfolio.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding portfolio: {str(e)}")
            flash(f'Error adding portfolio: {str(e)}', 'danger')
    
    return render_template(
        'trust/add_portfolio.html',
        title='Add Portfolio',
        fund=fund
    )

@trust_bp.route('/valuation/nvc-ghl-fund')
def api_nvc_ghl_fund_valuation():
    """API endpoint for NVC GHL Fund valuation"""
    valuation = get_nvc_ghl_fund_current_valuation()
    return jsonify(valuation)