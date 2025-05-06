"""
Saint Crown Industrial Bank Integration Routes
Routes for managing and displaying information about NVC Fund assets
under Saint Crown Industrial Bank management and the AFD1 liquidity pool.
"""

import json
import logging
from datetime import datetime
from flask import render_template, request, jsonify, Blueprint, redirect, url_for, flash, current_app

from app import db
from models import Asset, AssetReporting, LiquidityPool, FinancialInstitution
from saint_crown_integration import get_saint_crown_integration, register_assets, generate_afd1_report

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

saint_crown_bp = Blueprint('saint_crown', __name__)

@saint_crown_bp.route('/saint-crown/dashboard')
def dashboard():
    """Saint Crown asset management dashboard"""
    saint_crown = get_saint_crown_integration()
    institution = saint_crown.institution
    
    # Get assets under management
    assets_query = Asset.query.filter_by(
        managing_institution_id=institution.id if institution else None
    )
    
    # Filter by status if provided
    status = request.args.get('status', 'ACTIVE')
    if status != 'ALL':
        assets_query = assets_query.filter_by(afd1_liquidity_pool_status=status)
    
    assets = assets_query.all()
    
    # Get AFD1 liquidity pool
    pool = LiquidityPool.query.filter_by(code="AFD1").first()
    
    # Get current gold price and calculate AFD1 unit value
    gold_price, gold_metadata = saint_crown.get_gold_price()
    afd1_unit_value = gold_price * 0.1  # AFD1 = 10% of gold price
    
    # Calculate total values
    total_value_usd = sum(float(asset.value) for asset in assets if asset.currency == "USD")
    total_value_afd1 = total_value_usd / afd1_unit_value
    
    return render_template(
        'saint_crown/dashboard.html',
        title='Saint Crown Asset Management',
        institution=institution,
        assets=assets,
        pool=pool,
        asset_count=len(assets),
        total_value=total_value_usd,
        total_value_afd1=total_value_afd1,
        gold_price=gold_price,
        gold_metadata=gold_metadata,
        afd1_unit_value=afd1_unit_value,
        status=status
    )

@saint_crown_bp.route('/saint-crown/assets')
def asset_list():
    """List of assets managed by Saint Crown"""
    saint_crown = get_saint_crown_integration()
    institution = saint_crown.institution
    
    # Get assets under management
    assets = Asset.query.filter_by(
        managing_institution_id=institution.id if institution else None
    ).all()
    
    return render_template(
        'saint_crown/asset_list.html',
        title='Saint Crown Managed Assets',
        assets=assets,
        institution=institution
    )

@saint_crown_bp.route('/saint-crown/asset/<asset_id>')
def asset_detail(asset_id):
    """Detail view for a specific asset"""
    asset = Asset.query.filter_by(asset_id=asset_id).first_or_404()
    reports = AssetReporting.query.filter_by(asset_id=asset_id).order_by(AssetReporting.report_date.desc()).all()
    
    return render_template(
        'saint_crown/asset_detail.html',
        title=f'Asset: {asset.name}',
        asset=asset,
        reports=reports
    )

@saint_crown_bp.route('/saint-crown/register-assets', methods=['POST'])
def register_assets_route():
    """Register assets with Saint Crown"""
    try:
        asset_ids = request.form.getlist('asset_ids')
        result = None
        
        if asset_ids:
            # Register selected assets
            service = get_saint_crown_integration()
            result = service.register_assets_with_saint_crown(asset_ids)
        else:
            # Register all eligible assets
            result = register_assets()
        
        if result.get('success'):
            flash(f"Successfully registered {len(result.get('registered_assets', []))} assets with Saint Crown Industrial Bank", "success")
        else:
            flash(f"Error registering assets: {result.get('error', 'Unknown error')}", "danger")
            
    except Exception as e:
        logger.error(f"Error in register_assets_route: {str(e)}")
        flash(f"Error: {str(e)}", "danger")
    
    return redirect(url_for('saint_crown.dashboard'))

@saint_crown_bp.route('/saint-crown/verify-asset/<asset_id>', methods=['POST'])
def verify_asset(asset_id):
    """Verify an asset's status with Saint Crown"""
    try:
        service = get_saint_crown_integration()
        result = service.verify_asset_status(asset_id)
        
        if result.get('error'):
            flash(f"Error verifying asset: {result.get('error')}", "danger")
        else:
            flash(f"Asset verification completed successfully", "success")
            
    except Exception as e:
        logger.error(f"Error in verify_asset: {str(e)}")
        flash(f"Error: {str(e)}", "danger")
    
    return redirect(url_for('saint_crown.asset_detail', asset_id=asset_id))

@saint_crown_bp.route('/saint-crown/afd1-report')
def afd1_report():
    """Generate and display AFD1 liquidity pool report"""
    try:
        report_data = generate_afd1_report()
        
        if report_data.get('error'):
            flash(f"Error generating report: {report_data.get('error')}", "danger")
            return redirect(url_for('saint_crown.dashboard'))
        
        return render_template(
            'saint_crown/afd1_report.html',
            title='AFD1 Liquidity Pool Report',
            report=report_data,
            generated_at=datetime.utcnow()
        )
            
    except Exception as e:
        logger.error(f"Error in afd1_report: {str(e)}")
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('saint_crown.dashboard'))

@saint_crown_bp.route('/nvc-fund-holding-trust-report.html')
def public_holding_report():
    """Publicly accessible report of NVC Fund assets in the AFD1 liquidity pool"""
    try:
        # Get assets managed by Saint Crown and part of AFD1
        saint_crown = get_saint_crown_integration()
        institution = saint_crown.institution
        
        assets = Asset.query.filter_by(
            managing_institution_id=institution.id if institution else None,
            afd1_liquidity_pool_status="ACTIVE"
        ).all()
        
        # Get current gold price and calculate AFD1 unit value
        gold_price, gold_metadata = saint_crown.get_gold_price()
        afd1_unit_value = gold_price * 0.1  # AFD1 = 10% of gold price
        
        # Use real NVC Fund Holdings value: $2.5 trillion USD
        total_value_usd = 2500000000000  # $2.5 trillion as requested
        total_value_afd1 = total_value_usd / afd1_unit_value
        
        # Format values for better logging
        formatted_total_usd = f"${total_value_usd:,.2f}"
        formatted_total_afd1 = f"{total_value_afd1:,.2f}"
        
        logger.info(f"Public report: {formatted_total_usd} USD = {formatted_total_afd1} AFD1 (Gold at ${gold_price:,.2f}, AFD1 at ${afd1_unit_value:,.2f})")
        
        return render_template(
            'saint_crown/public_holding_report.html',
            title='NVC Fund Holding Trust Report',
            assets=assets,
            total_value=total_value_usd,
            total_value_afd1=total_value_afd1,
            gold_price=gold_price,
            gold_metadata=gold_metadata,
            afd1_unit_value=afd1_unit_value,
            asset_count=len(assets),
            institution=institution,
            report_date=datetime.utcnow()
        )
            
    except Exception as e:
        logger.error(f"Error in public_holding_report: {str(e)}")
        return render_template(
            'error.html',
            error_message="Error generating report. Please try again later."
        )

@saint_crown_bp.route('/api/v1/saint-crown/assets', methods=['GET'])
def api_assets():
    """API endpoint for assets managed by Saint Crown"""
    try:
        saint_crown = get_saint_crown_integration()
        institution = saint_crown.institution
        
        assets = Asset.query.filter_by(
            managing_institution_id=institution.id if institution else None
        ).all()
        
        # Get current gold price and calculate AFD1 unit value
        gold_price, gold_metadata = saint_crown.get_gold_price()
        afd1_unit_value = gold_price * 0.1  # AFD1 = 10% of gold price
        
        # Use real NVC Fund Holdings value: $2.5 trillion USD for total value
        total_value_usd = 2500000000000  # $2.5 trillion as requested
        total_value_afd1 = total_value_usd / afd1_unit_value if afd1_unit_value else 0
        
        asset_list = [{
            "asset_id": asset.asset_id,
            "name": asset.name,
            "value_usd": float(asset.value),
            "value_afd1": float(asset.value) / afd1_unit_value if asset.currency == "USD" and afd1_unit_value else 0,
            "currency": asset.currency,
            "type": asset.asset_type.value,
            "afd1_status": asset.afd1_liquidity_pool_status,
            "last_verified": asset.last_verified_date.isoformat() if asset.last_verified_date else None
        } for asset in assets]
        
        # Add Kitco URL for live gold price reference
        if "kitco_url" in gold_metadata:
            gold_metadata["live_chart_url"] = gold_metadata["kitco_url"]
        elif "source_url" in gold_metadata:
            gold_metadata["live_chart_url"] = gold_metadata["source_url"]
        
        return jsonify({
            "success": True,
            "managing_institution": institution.name if institution else "Saint Crown Industrial Bank",
            "gold_price_usd": gold_price,
            "gold_price_metadata": gold_metadata,
            "afd1_unit_value_usd": afd1_unit_value,
            "assets": asset_list,
            "total_assets": len(asset_list),
            "total_value_usd": total_value_usd,
            "total_value_afd1": total_value_afd1,
            "nvct_usd_ratio": 1.0,  # NVCT is pegged 1:1 to USD
            "nvc_fund_total_holdings_usd": total_value_usd,
            "nvc_fund_total_holdings_afd1": total_value_afd1
        })
            
    except Exception as e:
        logger.error(f"Error in api_assets: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@saint_crown_bp.route('/api/v1/saint-crown/afd1-report', methods=['GET'])
def api_afd1_report():
    """API endpoint for AFD1 liquidity pool report"""
    try:
        report_data = generate_afd1_report()
        
        if report_data.get('error'):
            return jsonify({
                "success": False,
                "error": report_data.get('error')
            }), 400
        
        return jsonify({
            "success": True,
            "report": report_data
        })
            
    except Exception as e:
        logger.error(f"Error in api_afd1_report: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500