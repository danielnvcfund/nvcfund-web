"""
Financial Institutions Reference Data

This module provides a comprehensive list of major financial institutions with their
settlement coordinates and RTGS information.

This can be used to populate the database with a consistent set of financial institutions
that can be used for payment and settlement operations.
"""

import logging
from typing import Dict, List

from models import FinancialInstitution, FinancialInstitutionType, db

logger = logging.getLogger(__name__)

# Dictionary of financial institutions by category
# Each category contains a list of institution dictionaries with their details
FINANCIAL_INSTITUTIONS_REFERENCE = {
    "Central Banks": [
        {
            "name": "Federal Reserve Bank of the United States",
            "swift_code": "FRNYUS33",
            "rtgs_system": "Fedwire Funds Service",
            "country": "USA",
            "type": "CENTRAL_BANK"
        },
        {
            "name": "European Central Bank",
            "swift_code": "ECBFDEFFXXX",
            "rtgs_system": "TARGET2",
            "country": "European Union",
            "type": "CENTRAL_BANK"
        },
        {
            "name": "Bank of England",
            "swift_code": "BKENGB2L",
            "rtgs_system": "CHAPS",
            "country": "United Kingdom",
            "type": "CENTRAL_BANK"
        },
        {
            "name": "Bank of Japan",
            "swift_code": "BOJPJPJT",
            "rtgs_system": "BOJ-NET",
            "country": "Japan",
            "type": "CENTRAL_BANK"
        },
        {
            "name": "Bank of Canada",
            "swift_code": "BOFCCAT2",
            "rtgs_system": "LVTS",
            "country": "Canada",
            "type": "CENTRAL_BANK"
        },
        {
            "name": "People's Bank of China",
            "swift_code": "BKCHCNBJ",
            "rtgs_system": "CNAPS",
            "country": "China",
            "type": "CENTRAL_BANK"
        },
        {
            "name": "Reserve Bank of Australia",
            "swift_code": "RSBKAU2S",
            "rtgs_system": "RITS",
            "country": "Australia",
            "type": "CENTRAL_BANK"
        },
        {
            "name": "Reserve Bank of India",
            "swift_code": "RBISINBB",
            "rtgs_system": "RTGS",
            "country": "India",
            "type": "CENTRAL_BANK"
        },
        {
            "name": "Central Bank of Brazil",
            "swift_code": "BCBRBRRJ",
            "rtgs_system": "STR",
            "country": "Brazil",
            "type": "CENTRAL_BANK"
        },
        {
            "name": "South African Reserve Bank",
            "swift_code": "SABPZAJX",
            "rtgs_system": "SAMOS",
            "country": "South Africa",
            "type": "CENTRAL_BANK"
        }
    ],
    "International Organizations": [
        {
            "name": "World Bank",
            "swift_code": "IBRDUS33",
            "rtgs_system": "Fedwire (via FRB)",
            "country": "International",
            "type": "BANK"
        },
        {
            "name": "International Monetary Fund",
            "swift_code": "IMFDUS33",
            "rtgs_system": "Fedwire (via FRB)",
            "country": "International",
            "type": "BANK"
        },
        {
            "name": "Bank for International Settlements",
            "swift_code": "BISBCHBB",
            "rtgs_system": "SIC",
            "country": "International",
            "type": "BANK"
        },
        {
            "name": "African Development Bank",
            "swift_code": "AFDBCIAB",
            "rtgs_system": "Regional Settlement Systems",
            "country": "Pan-African",
            "type": "BANK"
        },
        {
            "name": "Asian Development Bank",
            "swift_code": "ASDBPHMM",
            "rtgs_system": "Regional Settlement Systems",
            "country": "International",
            "type": "BANK"
        },
    ],
    "Government Agencies": [
        {
            "name": "United States Department of the Treasury",
            "swift_code": "TREAS33",
            "rtgs_system": "Fedwire Funds Service",
            "country": "USA",
            "type": "GOVERNMENT"
        },
        {
            "name": "HM Treasury",
            "swift_code": "HMTRGB2L",
            "rtgs_system": "CHAPS",
            "country": "United Kingdom",
            "type": "GOVERNMENT"
        },
        {
            "name": "Federal Finance Administration of Switzerland",
            "swift_code": "EFVCHE31",
            "rtgs_system": "SIC",
            "country": "Switzerland",
            "type": "GOVERNMENT"
        },
    ],
    "Major Commercial Banks": [
        {
            "name": "JPMorgan Chase Bank",
            "swift_code": "CHASUS33",
            "rtgs_system": "Fedwire Funds Service",
            "country": "USA",
            "type": "BANK"
        },
        {
            "name": "Bank of America",
            "swift_code": "BOFAUS3N",
            "rtgs_system": "Fedwire Funds Service",
            "country": "USA",
            "type": "BANK"
        },
        {
            "name": "Citibank",
            "swift_code": "CITIUS33",
            "rtgs_system": "Fedwire Funds Service",
            "country": "USA",
            "type": "BANK"
        },
        {
            "name": "Wells Fargo Bank",
            "swift_code": "WFBIUS6S",
            "rtgs_system": "Fedwire Funds Service",
            "country": "USA",
            "type": "BANK"
        },
        {
            "name": "HSBC Bank",
            "swift_code": "HSBCGB2L",
            "rtgs_system": "CHAPS",
            "country": "United Kingdom",
            "type": "BANK"
        },
        {
            "name": "Deutsche Bank",
            "swift_code": "DEUTDEFF",
            "rtgs_system": "TARGET2",
            "country": "Germany",
            "type": "BANK"
        },
        {
            "name": "Barclays Bank",
            "swift_code": "BARCGB22",
            "rtgs_system": "CHAPS",
            "country": "United Kingdom",
            "type": "BANK"
        },
        {
            "name": "BNP Paribas",
            "swift_code": "BNPAFRPP",
            "rtgs_system": "TARGET2",
            "country": "France",
            "type": "BANK"
        },
        {
            "name": "Société Générale",
            "swift_code": "SOGEFRPP",
            "rtgs_system": "TARGET2",
            "country": "France",
            "type": "BANK"
        },
        {
            "name": "Crédit Agricole",
            "swift_code": "AGRIFRPP",
            "rtgs_system": "TARGET2",
            "country": "France",
            "type": "BANK"
        },
        {
            "name": "UBS Group AG",
            "swift_code": "UBSWCHZH",
            "rtgs_system": "SIC",
            "country": "Switzerland",
            "type": "BANK"
        },
        {
            "name": "Credit Suisse",
            "swift_code": "CRESCHZZ",
            "rtgs_system": "SIC",
            "country": "Switzerland",
            "type": "BANK"
        },
        {
            "name": "Mitsubishi UFJ Financial Group",
            "swift_code": "BOTKJPJT",
            "rtgs_system": "BOJ-NET",
            "country": "Japan",
            "type": "BANK"
        },
        {
            "name": "Industrial and Commercial Bank of China",
            "swift_code": "ICBKCNBJ",
            "rtgs_system": "CNAPS",
            "country": "China",
            "type": "BANK"
        },
        {
            "name": "China Construction Bank",
            "swift_code": "PCBCCNBJ",
            "rtgs_system": "CNAPS",
            "country": "China",
            "type": "BANK"
        }
    ],
    "Regional Banks": [
        {
            "name": "TD Canada Trust",
            "swift_code": "TDOMCATTTOR",
            "rtgs_system": "LVTS",
            "country": "Canada",
            "type": "BANK"
        },
        {
            "name": "Royal Bank of Canada",
            "swift_code": "ROYCCAT2",
            "rtgs_system": "LVTS",
            "country": "Canada",
            "type": "BANK"
        },
        {
            "name": "National Australia Bank",
            "swift_code": "NATAAU33",
            "rtgs_system": "RITS",
            "country": "Australia",
            "type": "BANK"
        },
        {
            "name": "Commonwealth Bank of Australia",
            "swift_code": "CTBAAU2S",
            "rtgs_system": "RITS",
            "country": "Australia",
            "type": "BANK"
        },
        {
            "name": "State Bank of India",
            "swift_code": "SBININBB",
            "rtgs_system": "RTGS",
            "country": "India",
            "type": "BANK"
        },
        {
            "name": "ICICI Bank",
            "swift_code": "ICICINBB",
            "rtgs_system": "RTGS",
            "country": "India",
            "type": "BANK"
        },
        {
            "name": "Banco do Brasil",
            "swift_code": "BRASBRRJ",
            "rtgs_system": "STR",
            "country": "Brazil",
            "type": "BANK"
        },
        {
            "name": "Standard Bank",
            "swift_code": "SBZAZAJJ",
            "rtgs_system": "SAMOS",
            "country": "South Africa",
            "type": "BANK"
        },
        {
            "name": "First National Bank South Africa",
            "swift_code": "FIRNZAJJ",
            "rtgs_system": "SAMOS",
            "country": "South Africa",
            "type": "BANK"
        },
        {
            "name": "Qatar National Bank",
            "swift_code": "QNBAQAQA",
            "rtgs_system": "QATCH",
            "country": "Qatar",
            "type": "BANK"
        },
        {
            "name": "Emirates NBD",
            "swift_code": "EBILAEAD",
            "rtgs_system": "UAEFTS",
            "country": "United Arab Emirates",
            "type": "BANK"
        },
        {
            "name": "FirstRand Bank",
            "swift_code": "FIRNZAJJ",
            "rtgs_system": "SAMOS",
            "country": "South Africa",
            "type": "BANK"
        }
    ]
}


def populate_financial_institutions(batch_size=5):
    """Populate the database with a comprehensive list of financial institutions
    
    Args:
        batch_size (int): Number of institutions to process in each batch
                         to avoid timeouts with blockchain operations
    """
    existing_institutions = FinancialInstitution.query.all()
    existing_swift_codes = {inst.swift_code for inst in existing_institutions if inst.swift_code}
    
    total_added = 0
    total_skipped = 0
    
    for category, institutions in FINANCIAL_INSTITUTIONS_REFERENCE.items():
        logger.info(f"Processing category: {category}")
        
        for i, inst_data in enumerate(institutions):
            # Skip if already exists
            if inst_data.get('swift_code') in existing_swift_codes:
                logger.info(f"Skipping existing institution: {inst_data.get('name')}")
                total_skipped += 1
                continue
            
            try:
                # Create new institution
                new_institution = FinancialInstitution(
                    name=inst_data.get('name'),
                    swift_code=inst_data.get('swift_code'),
                    institution_type=FinancialInstitutionType[inst_data.get('type', 'BANK')],
                    is_rtgs_enabled=True,
                    rtgs_system=inst_data.get('rtgs_system'),
                    ethereum_address='',  # Default empty, would be populated separately
                    api_endpoint='',  # Default empty, would be populated separately
                    metadata_json='{"country": "' + inst_data.get('country', '') + '"}'
                )
                
                db.session.add(new_institution)
                total_added += 1
                
                # Commit in batches to avoid long transactions
                if i % batch_size == 0:
                    db.session.commit()
                    logger.info(f"Committed batch of {batch_size} institutions")
            
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adding institution {inst_data.get('name')}: {e}")
    
    # Final commit for any remaining institutions
    db.session.commit()
    logger.info(f"Financial institutions population complete. Added: {total_added}, Skipped: {total_skipped}")
    return total_added, total_skipped