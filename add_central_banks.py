#!/usr/bin/env python3
"""
Script to add the Federal Reserve Bank and Bank of China to the RTGS-enabled institutions
"""
import sys
import json
from datetime import datetime
from app import app, db
from models import FinancialInstitution, FinancialInstitutionType
from blockchain_utils import generate_ethereum_account

def add_central_banks():
    """Add the Federal Reserve and Bank of China to the RTGS-enabled institutions"""
    # Use Flask application context
    with app.app_context():
        # Define the banks to add
        banks = [
            {
                "name": "Federal Reserve Bank of the United States",
                "institution_type": FinancialInstitutionType.CENTRAL_BANK,
                "swift_code": "FRNYUS33",
                "country": "United States",
                "rtgs_system": "Fedwire Funds Service",
                "rtgs_enabled": True,
                "s2s_enabled": True,
                "is_active": True
            },
            {
                "name": "Bank of China",
                "institution_type": FinancialInstitutionType.BANK,
                "swift_code": "BKCHCNBJ",
                "country": "China",
                "rtgs_system": "China National Advanced Payment System (CNAPS)",
                "rtgs_enabled": True,
                "s2s_enabled": True,
                "is_active": True
            }
        ]

        for bank_data in banks:
            # Check if bank already exists
            existing_bank = FinancialInstitution.query.filter_by(name=bank_data["name"]).first()
            if existing_bank:
                print(f"Bank '{bank_data['name']}' already exists (ID: {existing_bank.id})")
                continue

            # Generate Ethereum address for the institution
            eth_address, _ = generate_ethereum_account()
            if not eth_address:
                print(f"Failed to generate Ethereum address for {bank_data['name']}")
                continue

            # Prepare metadata with country and RTGS information
            metadata = {
                "country": bank_data["country"],
                "rtgs_system": bank_data["rtgs_system"],
                "added_at": datetime.utcnow().isoformat()
            }

            # Add SWIFT info if available
            if bank_data["swift_code"]:
                metadata["swift"] = {"bic": bank_data["swift_code"]}

            # Create new institution
            institution = FinancialInstitution(
                name=bank_data["name"],
                institution_type=bank_data["institution_type"],
                ethereum_address=eth_address,
                swift_code=bank_data["swift_code"],
                rtgs_enabled=bank_data["rtgs_enabled"],
                s2s_enabled=bank_data["s2s_enabled"],
                is_active=bank_data["is_active"],
                metadata_json=json.dumps(metadata)
            )

            db.session.add(institution)
            try:
                db.session.commit()
                print(f"Added {bank_data['name']} successfully (ID: {institution.id})")
            except Exception as e:
                db.session.rollback()
                print(f"Error adding {bank_data['name']}: {str(e)}")

if __name__ == "__main__":
    print("Adding central banks to the system...")
    add_central_banks()
    print("Done!")