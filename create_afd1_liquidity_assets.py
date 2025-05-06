"""
Script to create assets for the AFD1 liquidity pool with proper structure
and register them with Saint Crown Industrial Bank
"""

import os
import sys
import json
import uuid
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import db, app
from models import Asset, AssetType, FinancialInstitution, FinancialInstitutionType
from saint_crown_integration import get_saint_crown_integration

def create_afd1_liquidity_assets():
    """Create assets for the AFD1 liquidity pool and register them with Saint Crown"""
    
    with app.app_context():
        # Get the Saint Crown Integration service
        saint_crown_service = get_saint_crown_integration()
        institution = saint_crown_service.institution
        
        if not institution:
            logger.error("Saint Crown institution not found")
            return False
        
        logger.info(f"Creating assets for AFD1 liquidity pool managed by {institution.name}")
        
        # Define the pool assets that make up the $2.5 trillion
        afd1_assets = [
            {
                "asset_id": f"NVCF-AFD1-{uuid.uuid4().hex[:8].upper()}",
                "name": "US Treasury Bond Portfolio Series A",
                "description": "Long-term Treasury bonds managed as part of the AFD1 liquidity pool",
                "asset_type": AssetType.TREASURY_BOND,
                "value": 500000000000,  # $500 billion
                "currency": "USD",
                "location": "New York, USA",
                "custodian": "State Street Global Services",
                "is_verified": True,
                "metadata": {
                    "maturity_range": "10-30 years",
                    "average_yield": "3.2%",
                    "risk_rating": "AAA",
                    "strategic_classification": "Core Reserve Asset"
                }
            },
            {
                "asset_id": f"NVCF-AFD1-{uuid.uuid4().hex[:8].upper()}",
                "name": "Sovereign Bond Portfolio",
                "description": "Diversified portfolio of sovereign bonds from multiple nations",
                "asset_type": AssetType.SOVEREIGN_BOND,
                "value": 750000000000,  # $750 billion
                "currency": "USD",
                "location": "London, UK",
                "custodian": "HSBC Global Custody",
                "is_verified": True,
                "metadata": {
                    "countries": "US, UK, Germany, Japan, Canada, Australia",
                    "average_yield": "3.5%",
                    "risk_rating": "AA+",
                    "strategic_classification": "International Reserve"
                }
            },
            {
                "asset_id": f"NVCF-AFD1-{uuid.uuid4().hex[:8].upper()}",
                "name": "Global Gold Reserves",
                "description": "Physical gold reserves stored in multiple secure vaults worldwide",
                "asset_type": AssetType.COMMODITY,
                "value": 325000000000,  # $325 billion
                "currency": "USD",
                "location": "Zurich, Switzerland",
                "custodian": "UBS Asset Servicing",
                "is_verified": True,
                "metadata": {
                    "quantity": "95.7 million troy ounces",
                    "purity": "99.99%",
                    "storage_locations": "Switzerland, UK, Singapore, USA",
                    "strategic_classification": "Hard Asset Reserve"
                }
            },
            {
                "asset_id": f"NVCF-AFD1-{uuid.uuid4().hex[:8].upper()}",
                "name": "Strategic Infrastructure Fund",
                "description": "Investments in critical infrastructure projects worldwide",
                "asset_type": AssetType.INFRASTRUCTURE,
                "value": 425000000000,  # $425 billion
                "currency": "USD",
                "location": "Singapore",
                "custodian": "JP Morgan Custody Services",
                "is_verified": True,
                "metadata": {
                    "sectors": "Energy, Transportation, Communications, Water",
                    "geographic_focus": "Global with emphasis on developing markets",
                    "expected_return": "6.8% annually",
                    "strategic_classification": "Development Asset"
                }
            },
            {
                "asset_id": f"NVCF-AFD1-{uuid.uuid4().hex[:8].upper()}",
                "name": "Cash Equivalent Reserve",
                "description": "Highly liquid cash equivalent assets for immediate liquidity needs",
                "asset_type": AssetType.CASH,
                "value": 500000000000,  # $500 billion
                "currency": "USD",
                "location": "New York, USA",
                "custodian": "Bank of New York Mellon",
                "is_verified": True,
                "metadata": {
                    "instruments": "T-Bills, Commercial Paper, Money Market Funds",
                    "average_maturity": "< 90 days",
                    "risk_rating": "AAA",
                    "strategic_classification": "Liquidity Reserve"
                }
            }
        ]
        
        # Create each asset and add to database
        created_assets = []
        for asset_data in afd1_assets:
            # Check if asset already exists
            existing = Asset.query.filter_by(asset_id=asset_data["asset_id"]).first()
            if existing:
                logger.info(f"Asset already exists: {existing.name}")
                created_assets.append(existing)
                continue
            
            # Create new asset
            asset = Asset(
                asset_id=asset_data["asset_id"],
                name=asset_data["name"],
                description=asset_data["description"],
                asset_type=asset_data["asset_type"],
                value=asset_data["value"],
                currency=asset_data["currency"],
                location=asset_data["location"],
                custodian=asset_data["custodian"],
                is_active=True,
                is_verified=asset_data["is_verified"],
                verification_date=datetime.utcnow() if asset_data["is_verified"] else None,
                last_valuation_date=datetime.utcnow(),
                metadata_json=json.dumps(asset_data["metadata"]),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            try:
                db.session.add(asset)
                db.session.flush()  # Flush to get the id without committing
                logger.info(f"Created asset: {asset.name} - ${float(asset.value):,.2f} USD")
                created_assets.append(asset)
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creating asset {asset_data['name']}: {str(e)}")
        
        try:
            db.session.commit()
            
            # Register assets with Saint Crown
            asset_ids = [asset.asset_id for asset in created_assets]
            if asset_ids:
                result = saint_crown_service.register_assets_with_saint_crown(asset_ids)
                if result.get("success"):
                    logger.info(f"Successfully registered {len(asset_ids)} assets with Saint Crown")
                else:
                    logger.error(f"Error registering assets: {result.get('error', 'Unknown error')}")
            
            # Calculate total value
            total_value = sum(float(asset.value) for asset in created_assets)
            logger.info(f"Total value of AFD1 liquidity pool assets: ${total_value:,.2f} USD")
            
            return created_assets
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error committing assets: {str(e)}")
            return []
            
if __name__ == "__main__":
    # Get count from command line
    assets = create_afd1_liquidity_assets()
    
    if assets:
        print(f"Created and registered {len(assets)} AFD1 liquidity pool assets")
        print(f"Total value: ${sum(float(asset.value) for asset in assets):,.2f} USD")
    else:
        print("Failed to create AFD1 liquidity pool assets. See log for details.")