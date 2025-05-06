"""
Simplified script to create a few sample assets for testing
"""

import json
import uuid
from datetime import datetime, timedelta

from main import app
from app import db
from models import Asset, AssetType

# Sample asset data
sample_assets = [
    {
        "name": "NVC Fund Government Bond Portfolio A",
        "asset_type": AssetType.SOVEREIGN_BOND,
        "value": 1500000000.00,
        "description": "High-value sovereign bond representing NVC Fund's investment in international development projects."
    },
    {
        "name": "African Union Development Fund 2024",
        "asset_type": AssetType.TREASURY_BOND,
        "value": 750000000.00,
        "description": "Strategic asset classified as treasury bond with long-term value appreciation potential."
    },
    {
        "name": "ECO Treaty Reserve Asset B",
        "asset_type": AssetType.COLLATERALIZED_DEBT,
        "value": 950000000.00,
        "description": "Core holding in the NVC Fund portfolio, providing stability and consistent returns."
    },
    {
        "name": "Global Humanitarian Project 2025",
        "asset_type": AssetType.INFRASTRUCTURE,
        "value": 630000000.00,
        "description": "Premium infrastructure asset acquired through strategic international partnerships."
    },
    {
        "name": "Supranational Collateral Bond 2024-AA",
        "asset_type": AssetType.CORPORATE_BOND,
        "value": 1250000000.00,
        "description": "Flagship corporate bond representing significant economic development initiatives."
    }
]

def create_assets():
    """Create the sample assets"""
    print("Creating sample assets...")
    created_assets = []
    
    for asset_data in sample_assets:
        # Generate asset ID
        asset_id = f"NVCF-{uuid.uuid4().hex[:8].upper()}"
        creation_date = datetime.utcnow() - timedelta(days=30)
        last_valuation = creation_date + timedelta(days=15)
        
        # Create asset object
        asset = Asset(
            asset_id=asset_id,
            name=asset_data["name"],
            description=asset_data["description"],
            asset_type=asset_data["asset_type"],
            value=asset_data["value"],
            currency="USD",
            location="Geneva, Switzerland",
            custodian="Bank of New York Mellon",
            is_active=True,
            is_verified=True,
            verification_date=last_valuation,
            last_valuation_date=last_valuation,
            documentation_url=f"https://docs.nvcfund.example.com/assets/{asset_id}",
            metadata_json=json.dumps({
                "acquisition_date": creation_date.isoformat(),
                "maturity_date": (creation_date + timedelta(days=3650)).isoformat(),
                "risk_rating": "AAA",
                "source": "International Treaty",
                "annual_yield": 4.25,
                "strategic_classification": "Core Asset"
            }),
            created_at=creation_date,
            updated_at=last_valuation
        )
        
        db.session.add(asset)
        created_assets.append(asset)
    
    # Commit the changes
    db.session.commit()
    print(f"Successfully created {len(created_assets)} sample assets")
    
    # Print asset summary
    total_value = sum(float(asset.value) for asset in created_assets)
    print(f"Total value of created assets: ${total_value:,.2f} USD")
    
    return created_assets

if __name__ == "__main__":
    with app.app_context():
        # Check if assets already exist
        existing_count = Asset.query.count()
        if existing_count > 0:
            print(f"{existing_count} assets already exist in the database")
            choice = input("Do you want to create additional sample assets? (y/n): ")
            if choice.lower() != 'y':
                print("Exiting without creating additional assets")
                exit(0)
                
        # Create assets
        assets = create_assets()
        
        if assets:
            print("Sample assets created successfully")
            for asset in assets:
                print(f"- {asset.name}: ${float(asset.value):,.2f} USD")
        else:
            print("Failed to create sample assets")