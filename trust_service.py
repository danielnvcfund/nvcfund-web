"""
Trust Portfolio Service for NVC Banking Platform
This module provides functionality for managing trust portfolios and valuations.
"""
from datetime import datetime, date
from decimal import Decimal
import logging
import json
import os
from sqlalchemy import desc

from app import db
from trust_portfolio import (
    TrustFund, TrustPortfolio, TrustAsset, AssetValuation, 
    PortfolioValuation, AssetCategory, AssetStatus
)

logger = logging.getLogger(__name__)

def initialize_nvc_ghl_fund():
    """
    Initialize the NVC GHL Fund if it doesn't exist
    Returns the trust fund record
    """
    # Check if the fund already exists
    nvc_ghl_fund = TrustFund.query.filter_by(code="NVC100B/GHL-HSBC").first()
    
    if not nvc_ghl_fund:
        try:
            # Create the NVC Fund Holding Trust first as parent
            nvc_fund_holding = TrustFund.query.filter_by(name="NVC Fund Holding Trust").first()
            
            if not nvc_fund_holding:
                nvc_fund_holding = TrustFund(
                    name="NVC Fund Holding Trust",
                    code="NVCFUND-HT",
                    description="The primary trust holding entity for NVC Fund assets globally",
                    established_date=date(1958, 9, 6),
                    grantor="The Frank Ekejija Estate Trust",
                    trustee="Sir Richard A Newman",
                    beneficiary="NVCFUND Holding Trust Certificate Holders",
                )
                db.session.add(nvc_fund_holding)
                db.session.flush()  # Flush to get the ID without committing
            
            # Create the NVC GHL Fund as a subsidiary
            nvc_ghl_fund = TrustFund(
                name="NVC GHL Fund",
                code="NVC100B/GHL-HSBC",
                description="A subsidiary asset management trust within the NVCFUND Holdings Group",
                established_date=date(2015, 10, 28),
                parent_trust_id=nvc_fund_holding.id,
                is_subsidiary=True,
                grantor="The Frank Ekejija Estate Trust",
                trustee="Sir Richard A Newman",
                co_trustees="Clifton M. Dugas, II; Antoinette D Coltrane Graves",
                beneficiary="NVCFUND Holding Trust Certificate Holders",
                account_number="NVC100B/GHL-HSBC"
            )
            db.session.add(nvc_ghl_fund)
            
            # Create a default portfolio
            primary_portfolio = TrustPortfolio(
                name="NVC GHL Primary Portfolio",
                description="Primary investment portfolio for NVC GHL Fund",
                trust_fund_id=nvc_ghl_fund.id
            )
            db.session.add(primary_portfolio)
            
            # Add initial assets as per the documents
            # Start with the cashier's checks mentioned in the appointment document
            cashiers_check_asset = TrustAsset(
                name="Treasury-Backed Cashiers Checks",
                description="One hundred billion in cashiers checks conveyed to the trust account",
                asset_category=AssetCategory.CASHIERS_CHECK,
                status=AssetStatus.SECURED,
                portfolio_id=primary_portfolio.id,
                acquisition_date=date(2015, 10, 28),
                acquisition_value=Decimal('100000000000.00'),
                currency="USD",
                location="NVC Fund Ledger Settlement Account"
            )
            db.session.add(cashiers_check_asset)
            
            # Add initial valuation
            initial_valuation = AssetValuation(
                asset_id=cashiers_check_asset.id,
                value=Decimal('100000000000.00'),
                currency="USD",
                valuation_date=date(2015, 10, 28),
                valuation_method="Face Value",
                appraiser="NVC Fund Treasury",
                notes="Initial valuation at face value of cashiers checks"
            )
            db.session.add(initial_valuation)
            
            # Add portfolio valuation
            portfolio_val = PortfolioValuation(
                portfolio_id=primary_portfolio.id,
                total_value=Decimal('100000000000.00'),
                currency="USD",
                valuation_date=date(2015, 10, 28),
                valuation_method="Asset Summation",
                assessor="NVC Fund Treasury",
                notes="Initial portfolio valuation"
            )
            db.session.add(portfolio_val)
            
            # Commit all changes
            db.session.commit()
            logger.info(f"NVC GHL Fund created with initial portfolio and assets")
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error initializing NVC GHL Fund: {str(e)}")
            raise
    
    return nvc_ghl_fund

def get_nvc_ghl_fund():
    """
    Get the NVC GHL Fund
    Returns the trust fund record or None if not found
    """
    return TrustFund.query.filter_by(code="NVC100B/GHL-HSBC").first()

def get_portfolio_valuation_history(portfolio_id):
    """
    Get valuation history for a portfolio
    Returns a list of portfolio valuations
    """
    return PortfolioValuation.query.filter_by(portfolio_id=portfolio_id).order_by(desc(PortfolioValuation.valuation_date)).all()

def get_asset_valuation_history(asset_id):
    """
    Get valuation history for an asset
    Returns a list of asset valuations
    """
    return AssetValuation.query.filter_by(asset_id=asset_id).order_by(desc(AssetValuation.valuation_date)).all()

def update_portfolio_valuation(portfolio_id, total_value, currency="USD", 
                              valuation_method="Asset Summation", assessor="NVC Fund Treasury",
                              notes=None):
    """
    Add a new valuation record for a portfolio
    Returns the new valuation record
    """
    try:
        valuation = PortfolioValuation(
            portfolio_id=portfolio_id,
            total_value=Decimal(str(total_value)),
            currency=currency,
            valuation_date=datetime.utcnow(),
            valuation_method=valuation_method,
            assessor=assessor,
            notes=notes
        )
        db.session.add(valuation)
        db.session.commit()
        logger.info(f"Added new valuation for portfolio {portfolio_id}: {total_value} {currency}")
        return valuation
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding portfolio valuation: {str(e)}")
        raise

def get_nvc_ghl_fund_current_valuation():
    """
    Get the current total valuation of the NVC GHL Fund
    Returns a dictionary with valuation details
    """
    try:
        # Get the fund
        fund = get_nvc_ghl_fund() 
        if not fund:
            fund = initialize_nvc_ghl_fund()
        
        # Get all portfolios for the fund
        portfolios = TrustPortfolio.query.filter_by(trust_fund_id=fund.id).all()
        
        # Get latest valuation for each portfolio
        total_value = Decimal('0')
        portfolio_values = []
        
        for portfolio in portfolios:
            latest_valuation = portfolio.current_valuation()
            if latest_valuation:
                portfolio_values.append({
                    'portfolio_id': portfolio.id,
                    'portfolio_name': portfolio.name,
                    'value': float(latest_valuation.total_value),
                    'currency': latest_valuation.currency,
                    'valuation_date': latest_valuation.valuation_date.strftime('%Y-%m-%d'),
                    'valuation_method': latest_valuation.valuation_method
                })
                total_value += latest_valuation.total_value
        
        # Prepare result
        result = {
            'fund_id': fund.id,
            'fund_name': fund.name,
            'fund_code': fund.code,
            'total_value': float(total_value),
            'currency': 'USD',  # Assuming all valuations are in USD
            'as_of_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'portfolios': portfolio_values
        }
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting NVC GHL Fund valuation: {str(e)}")
        return {
            'error': str(e),
            'fund_name': 'NVC GHL Fund',
            'total_value': None
        }

def add_trust_asset(portfolio_id, name, description, category, value, 
                   currency="USD", acquisition_date=None, status=AssetStatus.ACTIVE,
                   location=None, metadata=None):
    """
    Add a new asset to a trust portfolio
    Returns the new asset record
    """
    try:
        # Create asset
        asset = TrustAsset(
            name=name,
            description=description,
            asset_category=category,
            status=status,
            portfolio_id=portfolio_id,
            acquisition_date=acquisition_date or date.today(),
            acquisition_value=Decimal(str(value)),
            currency=currency,
            location=location,
            asset_metadata=json.dumps(metadata) if metadata else None
        )
        db.session.add(asset)
        db.session.flush()  # Flush to get the asset ID
        
        # Add initial valuation
        valuation = AssetValuation(
            asset_id=asset.id,
            value=Decimal(str(value)),
            currency=currency,
            valuation_date=datetime.utcnow(),
            valuation_method="Initial Value",
            notes="Initial asset valuation"
        )
        db.session.add(valuation)
        
        # Update portfolio valuation
        portfolio = TrustPortfolio.query.get(portfolio_id)
        total_value = sum(float(a.current_value() or 0) for a in portfolio.assets) + float(value)
        
        portfolio_valuation = PortfolioValuation(
            portfolio_id=portfolio_id,
            total_value=Decimal(str(total_value)),
            currency=currency,
            valuation_date=datetime.utcnow(),
            valuation_method="Asset Summation",
            notes=f"Updated after adding {name}"
        )
        db.session.add(portfolio_valuation)
        
        db.session.commit()
        logger.info(f"Added new asset {name} to portfolio {portfolio_id} with value {value} {currency}")
        return asset
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding trust asset: {str(e)}")
        raise

def get_all_trust_funds():
    """Get all trust funds"""
    return TrustFund.query.all()

def get_trust_fund_portfolios(trust_fund_id):
    """Get all portfolios for a trust fund"""
    return TrustPortfolio.query.filter_by(trust_fund_id=trust_fund_id).all()

def get_portfolio_assets(portfolio_id):
    """Get all assets for a portfolio"""
    return TrustAsset.query.filter_by(portfolio_id=portfolio_id).all()

def get_asset(asset_id):
    """Get a specific asset"""
    return TrustAsset.query.get(asset_id)

def get_portfolio(portfolio_id):
    """Get a specific portfolio"""
    return TrustPortfolio.query.get(portfolio_id)

def get_trust_fund(trust_fund_id):
    """Get a specific trust fund"""
    return TrustFund.query.get(trust_fund_id)

def create_safekeeping_receipt_asset(portfolio_id, skr_number, amount, issuer, issue_date, maturity_date, beneficiary, description=None):
    """Create an asset record for a Safekeeping Receipt (SKR)"""
    try:
        # Find the portfolio
        portfolio = get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio with ID {portfolio_id} not found")
        
        # Create the asset
        asset = TrustAsset(
            name=f"Safekeeping Receipt {skr_number}",
            description=description or f"Custodial Safekeeping Receipt issued by {issuer} to {beneficiary}",
            asset_category=AssetCategory.FINANCIAL_INSTRUMENT,
            status=AssetStatus.SECURED,
            portfolio_id=portfolio_id,
            acquisition_date=issue_date,
            acquisition_value=Decimal(str(amount)),
            currency="USD",
            location=f"Held at {issuer}",
            asset_metadata=json.dumps({
                "skr_number": skr_number,
                "issuer": issuer,
                "issue_date": issue_date.strftime('%Y-%m-%d'),
                "maturity_date": maturity_date.strftime('%Y-%m-%d'),
                "beneficiary": beneficiary
            })
        )
        db.session.add(asset)
        db.session.flush()
        
        # Add initial valuation
        valuation = AssetValuation(
            asset_id=asset.id,
            value=Decimal(str(amount)),
            currency="USD",
            valuation_date=datetime.utcnow(),
            valuation_method="Face Value",
            appraiser="System",
            notes=f"Initial valuation based on face value of SKR {skr_number}"
        )
        db.session.add(valuation)
        
        # Update portfolio valuation
        total_value = sum(float(a.current_value() or 0) for a in portfolio.assets) + float(amount)
        
        portfolio_valuation = PortfolioValuation(
            portfolio_id=portfolio.id,
            total_value=Decimal(str(total_value)),
            currency="USD",
            valuation_date=datetime.utcnow(),
            valuation_method="Asset Addition",
            assessor="System",
            notes=f"Updated after adding SKR {skr_number}"
        )
        db.session.add(portfolio_valuation)
        db.session.commit()
        
        logger.info(f"Created SKR asset {skr_number} with value {amount} USD")
        return asset
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating SKR asset: {str(e)}")
        raise

def create_nvc_skr_072809_001_asset():
    """Create asset record for the NVC-SKR-CD ST200602017-082809 document"""
    try:
        # Get the NVC GHL Fund
        fund = get_nvc_ghl_fund()
        if not fund:
            fund = initialize_nvc_ghl_fund()
        
        # Get the primary portfolio
        portfolio = TrustPortfolio.query.filter_by(trust_fund_id=fund.id).first()
        if not portfolio:
            raise ValueError("Primary portfolio for NVC GHL Fund not found")
        
        # Check if this asset already exists
        existing_asset = TrustAsset.query.filter(
            TrustAsset.portfolio_id == portfolio.id,
            TrustAsset.asset_metadata.like('%"skr_number": "072809-001"%')
        ).first()
        
        if existing_asset:
            logger.info(f"SKR 072809-001 asset already exists with ID {existing_asset.id}")
            return existing_asset
        
        # Create the asset using the SKR document information
        return create_safekeeping_receipt_asset(
            portfolio_id=portfolio.id,
            skr_number="072809-001",
            amount=84075000000.00,  # $84,075,000,000.00 as per the document
            issuer="Sovereign Trust",
            issue_date=date(2009, 7, 28),
            maturity_date=date(2010, 9, 30),
            beneficiary="NVCFUND HOLDING TRUST",
            description="Custodial Safekeeping Receipt (SKR) No. SKR072809-001 for Trust Certificate Units valued at $84,075,000,000.00 held by Sovereign Trust for NVCFUND HOLDING TRUST."
        )
    except Exception as e:
        logger.error(f"Error creating NVC SKR 072809-001 asset: {str(e)}")
        raise