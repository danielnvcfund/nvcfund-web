"""
Script to create sample assets for the Saint Crown AFD1 liquidity pool
"""

from app import app, db
from saint_crown_integration import SaintCrownIntegration
from models import Asset, FinancialInstitution, AssetType
from datetime import datetime

def create_afd1_assets():
    """Create sample assets for the Saint Crown AFD1 liquidity pool"""
    with app.app_context():
        # Get or create Saint Crown institution
        saint_crown = SaintCrownIntegration()._get_saint_crown_institution()
        if not saint_crown:
            saint_crown = FinancialInstitution(
                name='Saint Crown Industrial Bank',
                swift_code='SCIBUSAA',
                institution_type='INVESTMENT_BANK',
                country='US',
                is_rtgs_enabled=True
            )
            db.session.add(saint_crown)
            db.session.commit()
            print(f"Created institution: {saint_crown.name}")
        
        # Define sample assets for the AFD1 liquidity pool
        # These assets represent the $2.5 trillion in NVC Fund holdings
        assets = [
            Asset(
                asset_id='ASSET-SCB-001',
                name='US Treasury Bonds 2045',
                value='500000000000',
                currency='USD',
                asset_type=AssetType.BOND,
                managing_institution_id=saint_crown.id,
                afd1_liquidity_pool_status='ACTIVE',
                last_verified_date=datetime.utcnow()
            ),
            Asset(
                asset_id='ASSET-SCB-002',
                name='Federal Reserve Note Holdings',
                value='750000000000',
                currency='USD',
                asset_type=AssetType.CASH_EQUIVALENT,
                managing_institution_id=saint_crown.id,
                afd1_liquidity_pool_status='ACTIVE',
                last_verified_date=datetime.utcnow()
            ),
            Asset(
                asset_id='ASSET-SCB-003',
                name='Global Infrastructure Fund',
                value='125000000000',
                currency='USD',
                asset_type=AssetType.FUND,
                managing_institution_id=saint_crown.id,
                afd1_liquidity_pool_status='ACTIVE',
                last_verified_date=datetime.utcnow()
            ),
            Asset(
                asset_id='ASSET-SCB-004',
                name='Sovereign Gold Reserves',
                value='325000000000',
                currency='USD',
                asset_type=AssetType.COMMODITY,
                managing_institution_id=saint_crown.id,
                afd1_liquidity_pool_status='ACTIVE',
                last_verified_date=datetime.utcnow()
            ),
            Asset(
                asset_id='ASSET-SCB-005',
                name='Strategic Petroleum Reserve',
                value='800000000000',
                currency='USD',
                asset_type=AssetType.COMMODITY,
                managing_institution_id=saint_crown.id,
                afd1_liquidity_pool_status='ACTIVE',
                last_verified_date=datetime.utcnow()
            )
        ]
        
        # Add assets if they don't already exist
        total_value = 0
        for asset in assets:
            existing = Asset.query.filter_by(asset_id=asset.asset_id).first()
            if not existing:
                db.session.add(asset)
                db.session.commit()
                print(f"Created asset: {asset.name} - ${float(asset.value):,.2f} USD")
            total_value += float(asset.value)
        
        print(f"Total assets in AFD1 liquidity pool: ${total_value:,.2f} USD")

if __name__ == "__main__":
    create_afd1_assets()