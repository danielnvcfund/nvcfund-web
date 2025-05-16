#!/usr/bin/env python3
"""
Script to add global correspondent banks to expand the geographical reach
of the NVC banking platform beyond Africa.
"""
import sys
import json
import time
from datetime import datetime
from app import app, db
from models import FinancialInstitution, FinancialInstitutionType, CorrespondentBank
from blockchain_utils import generate_ethereum_account

# Group banks by region to process in smaller batches
BANKS_BY_REGION = {
    "North America": [
        {
            "name": "JPMorgan Chase",
            "bank_code": "CHASUS33",
            "swift_code": "CHASUS33",
            "ach_routing_number": "021000021",
            "supports_ach": True,
            "supports_swift": True,
            "supports_wire": True,
            "region": "North America"
        },
        {
            "name": "Bank of America",
            "bank_code": "BOFAUS3N",
            "swift_code": "BOFAUS3N",
            "ach_routing_number": "026009593",
            "supports_ach": True,
            "supports_swift": True,
            "supports_wire": True,
            "region": "North America"
        },
        {
            "name": "Royal Bank of Canada",
            "bank_code": "ROYCCAT2",
            "swift_code": "ROYCCAT2",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "North America"
        }
    ],
    "Europe": [
        {
            "name": "Deutsche Bank",
            "bank_code": "DEUTDEFF",
            "swift_code": "DEUTDEFF",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Europe"
        },
        {
            "name": "BNP Paribas",
            "bank_code": "BNPAFRPP",
            "swift_code": "BNPAFRPP",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Europe"
        },
        {
            "name": "HSBC UK",
            "bank_code": "HBUKGB4B",
            "swift_code": "HBUKGB4B",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Europe"
        },
        {
            "name": "UBS Switzerland",
            "bank_code": "UBSWCHZH",
            "swift_code": "UBSWCHZH",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Europe"
        }
    ],
    "Asia": [
        {
            "name": "MUFG Bank (Japan)",
            "bank_code": "BOTKJPJT",
            "swift_code": "BOTKJPJT",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Asia"
        },
        {
            "name": "Industrial and Commercial Bank of China",
            "bank_code": "ICBKCNBJ",
            "swift_code": "ICBKCNBJ",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Asia"
        },
        {
            "name": "DBS Bank (Singapore)",
            "bank_code": "DBSSSGSG",
            "swift_code": "DBSSSGSG",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Asia"
        },
        {
            "name": "State Bank of India",
            "bank_code": "SBININBB",
            "swift_code": "SBININBB",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Asia"
        }
    ],
    "Middle East": [
        {
            "name": "Emirates NBD",
            "bank_code": "EBILAEAD",
            "swift_code": "EBILAEAD",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Middle East"
        },
        {
            "name": "Qatar National Bank",
            "bank_code": "QNBAQAQA",
            "swift_code": "QNBAQAQA",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Middle East"
        }
    ],
    "South America": [
        {
            "name": "Banco do Brasil",
            "bank_code": "BRASBRRJ",
            "swift_code": "BRASBRRJ",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "South America"
        },
        {
            "name": "Banco Santander Brasil",
            "bank_code": "BSCHBRSP",
            "swift_code": "BSCHBRSP",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "South America"
        }
    ],
    "Oceania": [
        {
            "name": "Commonwealth Bank of Australia",
            "bank_code": "CTBAAU2S",
            "swift_code": "CTBAAU2S",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Oceania"
        },
        {
            "name": "ANZ Bank New Zealand",
            "bank_code": "ANZBNZ22",
            "swift_code": "ANZBNZ22",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Oceania"
        }
    ],
    "Africa": [
        {
            "name": "Standard Bank Group",
            "bank_code": "SBZAZAJJ",
            "swift_code": "SBZAZAJJ",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Africa"
        },
        {
            "name": "Ecobank Transnational",
            "bank_code": "ECOCGHAC",
            "swift_code": "ECOCGHAC",
            "ach_routing_number": "",
            "supports_ach": False,
            "supports_swift": True,
            "supports_wire": True,
            "region": "Africa"
        }
    ]
}

def add_correspondent_banks_by_region(region_name):
    """Add correspondent banks for a specific region"""
    with app.app_context():
        banks = BANKS_BY_REGION.get(region_name, [])
        if not banks:
            print(f"No banks found for region: {region_name}")
            return 0, 0
        
        added_count = 0
        skipped_count = 0
        
        print(f"\n--- Processing {region_name} Correspondent Banks ---")
        
        for bank_data in banks:
            # Check if bank already exists
            existing_bank = CorrespondentBank.query.filter_by(bank_code=bank_data["bank_code"]).first()
            if existing_bank:
                print(f"Bank '{bank_data['name']}' already exists (ID: {existing_bank.id})")
                skipped_count += 1
                continue

            # Create new correspondent bank
            bank = CorrespondentBank(
                name=bank_data["name"],
                bank_code=bank_data["bank_code"],
                swift_code=bank_data["swift_code"],
                ach_routing_number=bank_data["ach_routing_number"],
                supports_ach=bank_data["supports_ach"],
                supports_swift=bank_data["supports_swift"],
                supports_wire=bank_data["supports_wire"],
                settlement_threshold=50000.0,  # Higher threshold for international correspondent banks
                settlement_fee_percentage=0.25  # Competitive fee for international transfers
            )
            
            db.session.add(bank)
            print(f"Added correspondent bank: {bank_data['name']} ({bank_data['region']})")
            added_count += 1
        
        # Commit all changes for this region
        db.session.commit()
        print(f"Committed {added_count} banks for {region_name}")
        
        return added_count, skipped_count

def add_financial_institutions_by_region(region_name):
    """Add correspondent banks as financial institutions for a specific region"""
    with app.app_context():
        banks = BANKS_BY_REGION.get(region_name, [])
        if not banks:
            print(f"No banks found for region: {region_name}")
            return 0, 0
        
        added_count = 0
        skipped_count = 0
        
        print(f"\n--- Processing {region_name} Financial Institutions ---")
        
        for bank_data in banks:
            # Check if financial institution already exists
            existing_institution = FinancialInstitution.query.filter_by(swift_code=bank_data["swift_code"]).first()
            if existing_institution:
                print(f"Institution '{bank_data['name']}' already exists (ID: {existing_institution.id})")
                skipped_count += 1
                continue
                
            # Generate Ethereum address for the institution
            eth_address, _ = generate_ethereum_account()
            if not eth_address:
                print(f"Failed to generate Ethereum address for {bank_data['name']}")
                continue
                
            # Prepare metadata
            metadata = {
                "region": bank_data["region"],
                "supports_swift": bank_data["supports_swift"],
                "supports_wire": bank_data["supports_wire"],
                "added_at": datetime.utcnow().isoformat()
            }
            
            # Create financial institution
            institution = FinancialInstitution(
                name=bank_data["name"],
                institution_type=FinancialInstitutionType.BANK,
                ethereum_address=eth_address,
                swift_code=bank_data["swift_code"],
                rtgs_enabled=True,
                s2s_enabled=True,
                is_active=True,
                metadata_json=json.dumps(metadata)
            )
            
            db.session.add(institution)
            print(f"Added financial institution: {bank_data['name']} ({bank_data['region']})")
            added_count += 1
        
        # Commit all changes for this region
        db.session.commit()
        print(f"Committed {added_count} financial institutions for {region_name}")
        
        return added_count, skipped_count

def add_global_correspondent_banks():
    """Add major correspondent banks from all regions of the world
    
    Expands the NVC banking network globally across:
    - Europe
    - North America
    - South America
    - Asia
    - Middle East
    - Oceania
    """
    total_banks_added = 0
    total_banks_skipped = 0
    total_institutions_added = 0
    total_institutions_skipped = 0
    
    # Process one region at a time
    for region in BANKS_BY_REGION.keys():
        print(f"\nProcessing region: {region}")
        
        # Add correspondent banks for this region
        banks_added, banks_skipped = add_correspondent_banks_by_region(region)
        total_banks_added += banks_added
        total_banks_skipped += banks_skipped
        
        # Add financial institutions for this region
        institutions_added, institutions_skipped = add_financial_institutions_by_region(region)
        total_institutions_added += institutions_added
        total_institutions_skipped += institutions_skipped
        
        # Pause between regions to avoid overloading
        print(f"Completed processing for {region}, pausing before next region...")
        time.sleep(1)
    
    print(f"\n=== Global Correspondent Banking Expansion Complete ===")
    print(f"Total correspondent banks added: {total_banks_added}")
    print(f"Total correspondent banks skipped: {total_banks_skipped}")
    print(f"Total financial institutions added: {total_institutions_added}")
    print(f"Total financial institutions skipped: {total_institutions_skipped}")

def add_single_region(region_name):
    """Process just a single region - useful for running specific regions that failed"""
    print(f"Processing only {region_name} region")
    
    banks_added, banks_skipped = add_correspondent_banks_by_region(region_name)
    institutions_added, institutions_skipped = add_financial_institutions_by_region(region_name)
    
    print(f"\n=== {region_name} Processing Complete ===")
    print(f"Correspondent banks added: {banks_added}")
    print(f"Correspondent banks skipped: {banks_skipped}")
    print(f"Financial institutions added: {institutions_added}")
    print(f"Financial institutions skipped: {institutions_skipped}")

if __name__ == "__main__":
    # Check if a specific region was specified as command line argument
    if len(sys.argv) > 1 and sys.argv[1] in BANKS_BY_REGION:
        add_single_region(sys.argv[1])
    else:
        add_global_correspondent_banks()