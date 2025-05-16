#!/usr/bin/env python3
"""
Simple script to add global correspondent banks to expand the geographical reach
of the NVC banking platform beyond Africa.
"""
import json
from datetime import datetime
from app import app, db
from models import FinancialInstitution, FinancialInstitutionType

def add_global_banks():
    """Add major international banks to the system"""
    with app.app_context():
        # Define banks by region
        global_banks = [
            # North America
            {
                "name": "JPMorgan Chase",
                "swift_code": "CHASUS33",
                "country": "United States",
                "region": "North America",
                "rtgs_system": "Fedwire"
            },
            {
                "name": "Bank of America",
                "swift_code": "BOFAUS3N",
                "country": "United States",
                "region": "North America",
                "rtgs_system": "Fedwire"
            },
            {
                "name": "Royal Bank of Canada",
                "swift_code": "ROYCCAT2",
                "country": "Canada",
                "region": "North America",
                "rtgs_system": "LVTS"
            },
            
            # Europe
            {
                "name": "Deutsche Bank",
                "swift_code": "DEUTDEFF",
                "country": "Germany",
                "region": "Europe",
                "rtgs_system": "TARGET2"
            },
            {
                "name": "BNP Paribas",
                "swift_code": "BNPAFRPP",
                "country": "France",
                "region": "Europe",
                "rtgs_system": "TARGET2"
            },
            {
                "name": "HSBC UK",
                "swift_code": "HBUKGB4B",
                "country": "United Kingdom",
                "region": "Europe",
                "rtgs_system": "CHAPS"
            },
            {
                "name": "UBS Switzerland",
                "swift_code": "UBSWCHZH",
                "country": "Switzerland",
                "region": "Europe",
                "rtgs_system": "SIC"
            },
            
            # Asia
            {
                "name": "MUFG Bank (Japan)",
                "swift_code": "BOTKJPJT",
                "country": "Japan",
                "region": "Asia",
                "rtgs_system": "BOJ-NET"
            },
            {
                "name": "Industrial and Commercial Bank of China",
                "swift_code": "ICBKCNBJ",
                "country": "China",
                "region": "Asia",
                "rtgs_system": "CNAPS"
            },
            {
                "name": "DBS Bank",
                "swift_code": "DBSSSGSG",
                "country": "Singapore",
                "region": "Asia",
                "rtgs_system": "MEPS+"
            },
            {
                "name": "State Bank of India",
                "swift_code": "SBININBB",
                "country": "India",
                "region": "Asia",
                "rtgs_system": "RTGS"
            },
            
            # Middle East
            {
                "name": "Emirates NBD",
                "swift_code": "EBILAEAD",
                "country": "United Arab Emirates",
                "region": "Middle East",
                "rtgs_system": "UAEFTS"
            },
            {
                "name": "Qatar National Bank",
                "swift_code": "QNBAQAQA",
                "country": "Qatar",
                "region": "Middle East",
                "rtgs_system": "QATCH"
            },
            
            # South America
            {
                "name": "Banco do Brasil",
                "swift_code": "BRASBRRJ",
                "country": "Brazil",
                "region": "South America",
                "rtgs_system": "STR"
            },
            {
                "name": "Banco Santander Brasil",
                "swift_code": "BSCHBRSP",
                "country": "Brazil",
                "region": "South America",
                "rtgs_system": "STR"
            },
            
            # Oceania
            {
                "name": "Commonwealth Bank of Australia",
                "swift_code": "CTBAAU2S",
                "country": "Australia",
                "region": "Oceania",
                "rtgs_system": "RITS"
            },
            {
                "name": "ANZ Bank New Zealand",
                "swift_code": "ANZBNZ22",
                "country": "New Zealand",
                "region": "Oceania",
                "rtgs_system": "ESAS"
            },
            
            # Africa (adding more global African banks)
            {
                "name": "Standard Bank Group",
                "swift_code": "SBZAZAJJ",
                "country": "South Africa",
                "region": "Africa",
                "rtgs_system": "SAMOS"
            },
            {
                "name": "Ecobank Transnational",
                "swift_code": "ECOCGHAC",
                "country": "Pan-African",
                "region": "Africa",
                "rtgs_system": "Various"
            }
        ]
        
        added_count = 0
        skipped_count = 0
        
        # Add each bank directly to financial institutions
        for bank in global_banks:
            # Check if bank already exists
            existing = FinancialInstitution.query.filter_by(swift_code=bank["swift_code"]).first()
            if existing:
                print(f"Bank {bank['name']} already exists (ID: {existing.id})")
                skipped_count += 1
                continue
            
            # Prepare metadata
            metadata = {
                "country": bank["country"],
                "region": bank["region"],
                "rtgs_system": bank["rtgs_system"],
                "added_at": datetime.utcnow().isoformat(),
                "global_expansion": True
            }
            
            # Create new institution
            new_bank = FinancialInstitution(
                name=bank["name"],
                swift_code=bank["swift_code"],
                institution_type=FinancialInstitutionType.BANK,
                rtgs_enabled=True,
                s2s_enabled=True,
                is_active=True,
                metadata_json=json.dumps(metadata)
            )
            
            db.session.add(new_bank)
            print(f"Added global bank: {bank['name']} ({bank['region']})")
            added_count += 1
            
            # Commit every few banks to avoid timeouts
            if added_count % 3 == 0:
                db.session.commit()
                print(f"Committed batch of {added_count} banks")
                
        # Final commit if needed
        if added_count % 3 != 0:
            db.session.commit()
            
        print(f"\n=== Global Banking Expansion Complete ===")
        print(f"Total banks added: {added_count}")
        print(f"Total banks skipped: {skipped_count}")
        
if __name__ == "__main__":
    add_global_banks()