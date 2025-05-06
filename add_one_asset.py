"""
Script to add a single asset
"""

import json
from datetime import datetime

from app import create_app, db
from models import Asset, AssetType

app = create_app()
with app.app_context():
    # Create a single asset
    asset = Asset(
        asset_id="NVCF-AFD1DEMO1",
        name="NVC Fund Government Bond Portfolio A",
        description="High-value sovereign bond representing NVC Fund's investment in international development projects.",
        asset_type=AssetType.SOVEREIGN_BOND,
        value=1500000000.00,
        currency="USD",
        location="Geneva, Switzerland",
        custodian="Bank of New York Mellon",
        is_active=True,
        is_verified=True,
        verification_date=datetime.utcnow(),
        last_valuation_date=datetime.utcnow(),
        documentation_url="https://docs.nvcfund.example.com/assets/NVCF-AFD1DEMO1",
        metadata_json=json.dumps({
            "risk_rating": "AAA",
            "source": "International Treaty",
            "strategic_classification": "Core Asset"
        }),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.session.add(asset)
    db.session.commit()
    
    print(f"Created asset: {asset.name} with value ${float(asset.value):,.2f} USD")