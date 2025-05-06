"""
Script to create sample assets for testing the Saint Crown integration
"""

import os
import sys
import json
import uuid
import random
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from app import db
from models import Asset, AssetType

def create_sample_assets(count=10):
    """Create sample assets for testing"""
    
    logger.info(f"Creating {count} sample assets for testing")
    
    # Asset name templates
    asset_name_templates = [
        "NVC Fund Government Bond Portfolio {series}",
        "Sovereign Infrastructure Project {id}",
        "African Union Development Fund {year}",
        "ECO Treaty Reserve Asset {series}",
        "Global Humanitarian Project {id}",
        "Supranational Collateral Bond {year}-{series}",
        "International Development Project {id}",
        "Strategic Resource Reserve {type} {id}",
        "Multilateral Infrastructure Fund {year}",
        "Joint Sovereign Treasury {type} {id}"
    ]
    
    # Location templates
    locations = [
        "Geneva, Switzerland",
        "New York, USA",
        "London, UK",
        "Singapore",
        "Tokyo, Japan",
        "Frankfurt, Germany",
        "Paris, France",
        "Johannesburg, South Africa",
        "Dubai, UAE",
        "Hong Kong SAR"
    ]
    
    # Asset types weighted toward sovereign bonds and treasury bonds
    asset_types = [
        AssetType.SOVEREIGN_BOND,
        AssetType.SOVEREIGN_BOND,
        AssetType.TREASURY_BOND,
        AssetType.TREASURY_BOND,
        AssetType.TREASURY_BOND,
        AssetType.CORPORATE_BOND,
        AssetType.INFRASTRUCTURE,
        AssetType.CASH,
        AssetType.EQUITY,
        AssetType.COLLATERALIZED_DEBT
    ]
    
    # Custodian templates
    custodians = [
        "Bank of New York Mellon",
        "HSBC Global Custody",
        "JP Morgan Custody Services",
        "State Street Global Services",
        "Northern Trust Corporation",
        "BNP Paribas Securities Services",
        "Citibank Global Custody",
        "UBS Asset Servicing",
        "Deutsche Bank Trust Company",
        "Standard Chartered Custody Services"
    ]
    
    created_assets = []
    
    for i in range(count):
        # Generate basic asset information
        asset_id = f"NVCF-{uuid.uuid4().hex[:8].upper()}"
        asset_type = random.choice(asset_types)
        
        # Generate asset name
        name_template = random.choice(asset_name_templates)
        year = random.randint(2020, 2025)
        series = random.choice(["A", "B", "C", "D", "E", "AA", "BB", "CC"])
        asset_id_short = str(random.randint(1000, 9999))
        asset_type_name = asset_type.value.replace("_", " ").title()
        
        name = name_template.format(
            id=asset_id_short,
            year=year,
            series=series,
            type=asset_type_name
        )
        
        # Generate value (weighted toward larger values)
        # Values in millions, most between 100M and 5B
        if random.random() < 0.7:  # 70% chance for large assets
            value = random.uniform(100, 5000) * 1_000_000
        else:
            value = random.uniform(10, 100) * 1_000_000
        
        # Round to 2 decimal places
        value = round(value, 2)
        
        # Create asset description
        descriptions = [
            f"High-value {asset_type.value.lower().replace('_', ' ')} representing NVC Fund's investment in sovereign development projects.",
            f"Strategic asset classified as {asset_type.value.lower().replace('_', ' ')} with long-term value appreciation potential.",
            f"Core holding in the NVC Fund portfolio, this {asset_type.value.lower().replace('_', ' ')} provides stability and consistent returns.",
            f"Premium {asset_type.value.lower().replace('_', ' ')} asset acquired through strategic international partnerships.",
            f"Flagship {asset_type.value.lower().replace('_', ' ')} representing significant economic development initiatives."
        ]
        
        # Dates
        creation_date = datetime.utcnow() - timedelta(days=random.randint(30, 365))
        last_valuation = creation_date + timedelta(days=random.randint(7, 30))
        
        # Create asset object
        asset = Asset(
            asset_id=asset_id,
            name=name,
            description=random.choice(descriptions),
            asset_type=asset_type,
            value=value,
            currency="USD",
            location=random.choice(locations),
            custodian=random.choice(custodians),
            is_active=True,
            is_verified=random.random() > 0.3,  # 70% chance of being verified
            verification_date=last_valuation if random.random() > 0.3 else None,
            last_valuation_date=last_valuation,
            documentation_url=f"https://docs.nvcfund.example.com/assets/{asset_id}",
            metadata_json=json.dumps({
                "acquisition_date": creation_date.isoformat(),
                "maturity_date": (creation_date + timedelta(days=random.randint(365, 3650))).isoformat(),
                "risk_rating": random.choice(["AAA", "AA+", "AA", "AA-", "A+"]),
                "source": random.choice([
                    "International Treaty", 
                    "Sovereign Agreement", 
                    "Multilateral Fund", 
                    "Development Bank", 
                    "Central Bank Partnership"
                ]),
                "annual_yield": round(random.uniform(2.0, 5.5), 2),
                "strategic_classification": random.choice([
                    "Core Asset", 
                    "Strategic Reserve", 
                    "Development Fund", 
                    "Environmental Project", 
                    "Infrastructure Initiative"
                ])
            }),
            created_at=creation_date,
            updated_at=last_valuation
        )
        
        try:
            db.session.add(asset)
            created_assets.append(asset)
        except Exception as e:
            logger.error(f"Error creating asset {asset_id}: {str(e)}")
    
    try:
        db.session.commit()
        logger.info(f"Successfully created {len(created_assets)} sample assets")
        
        # Print asset summary
        total_value = sum(float(asset.value) for asset in created_assets)
        logger.info(f"Total value of created assets: ${total_value:,.2f} USD")
        
        return created_assets
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error committing sample assets: {str(e)}")
        return []

if __name__ == "__main__":
    from main import app
    
    with app.app_context():
        # Check if assets already exist
        existing_count = Asset.query.count()
        if existing_count > 0:
            logger.info(f"{existing_count} assets already exist in the database")
            choice = input("Do you want to create additional sample assets? (y/n): ")
            if choice.lower() != 'y':
                logger.info("Exiting without creating additional assets")
                sys.exit(0)
        
        # Get count from command line
        count = 10
        if len(sys.argv) > 1:
            try:
                count = int(sys.argv[1])
            except ValueError:
                logger.error(f"Invalid count: {sys.argv[1]}. Using default count of 10.")
        
        # Create assets
        assets = create_sample_assets(count)
        
        if assets:
            print(f"Created {len(assets)} sample assets with a total value of ${sum(float(asset.value) for asset in assets):,.2f} USD")
        else:
            print("Failed to create sample assets. See log for details.")