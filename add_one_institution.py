#!/usr/bin/env python3
"""
Simplified script to add just one institution to verify the process works
"""
import json
from datetime import datetime
from app import app, db
from models import FinancialInstitution, FinancialInstitutionType
from blockchain_utils import generate_ethereum_account

def add_federal_reserve():
    """Add the Federal Reserve to the RTGS-enabled institutions"""
    with app.app_context():
        # Define the bank to add
        bank_data = {
            "name": "Federal Reserve Bank of the United States",
            "institution_type": FinancialInstitutionType.CENTRAL_BANK,
            "swift_code": "FRNYUS33",
            "country": "United States",
            "rtgs_system": "Fedwire Funds Service"
        }
        
        # Check if bank already exists
        existing_bank = FinancialInstitution.query.filter_by(name=bank_data["name"]).first()
        if existing_bank:
            print(f"Bank '{bank_data['name']}' already exists (ID: {existing_bank.id})")
            return
            
        # Generate Ethereum address for the institution
        eth_address, _ = generate_ethereum_account()
        if not eth_address:
            print(f"Failed to generate Ethereum address for {bank_data['name']}")
            return
            
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
            rtgs_enabled=True,
            s2s_enabled=True,
            is_active=True,
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
    print("Adding Federal Reserve Bank to the system...")
    add_federal_reserve()
    print("Done!")