"""
Financial Institutions Reference Data

This module provides a comprehensive list of major financial institutions with their
settlement coordinates and RTGS information.

This can be used to populate the database with a consistent set of financial institutions
that can be used for payment and settlement operations.
"""

import json
import logging
from datetime import datetime

from app import app, db
from models import FinancialInstitution, FinancialInstitutionType
from blockchain_utils import generate_ethereum_account

# Define the financial institutions data
# Format:
# {
#     "name": "Institution Name",
#     "institution_type": FinancialInstitutionType.ENUM_VALUE,
#     "swift_code": "SWIFT/BIC code",
#     "country": "Country",
#     "rtgs_system": "RTGS System Name",
#     "rtgs_enabled": True/False,
#     "s2s_enabled": True/False,
#     "is_active": True/False,
#     "category": "Group for organization"
# }

FINANCIAL_INSTITUTIONS = [
    # Central Banks
    {
        "name": "Federal Reserve Bank of the United States",
        "institution_type": FinancialInstitutionType.CENTRAL_BANK,
        "swift_code": "FRNYUS33",
        "country": "United States",
        "rtgs_system": "Fedwire Funds Service",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Central Banks"
    },
    {
        "name": "European Central Bank",
        "institution_type": FinancialInstitutionType.CENTRAL_BANK,
        "swift_code": "ECBFDEFFXXX",
        "country": "European Union",
        "rtgs_system": "TARGET2",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Central Banks"
    },
    {
        "name": "Bank of England",
        "institution_type": FinancialInstitutionType.CENTRAL_BANK,
        "swift_code": "BKENGB2L",
        "country": "United Kingdom",
        "rtgs_system": "CHAPS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Central Banks"
    },
    {
        "name": "Bank of Japan",
        "institution_type": FinancialInstitutionType.CENTRAL_BANK,
        "swift_code": "BOJPJPJT",
        "country": "Japan",
        "rtgs_system": "BOJ-NET",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Central Banks"
    },
    {
        "name": "Bank of Canada",
        "institution_type": FinancialInstitutionType.CENTRAL_BANK,
        "swift_code": "BCANCAAJ",
        "country": "Canada",
        "rtgs_system": "LVTS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Central Banks"
    },
    {
        "name": "Bank of China",
        "institution_type": FinancialInstitutionType.CENTRAL_BANK,
        "swift_code": "BKCHCNBJ",
        "country": "China",
        "rtgs_system": "China National Advanced Payment System (CNAPS)",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Central Banks"
    },
    {
        "name": "Reserve Bank of India",
        "institution_type": FinancialInstitutionType.CENTRAL_BANK,
        "swift_code": "RBISINBB",
        "country": "India",
        "rtgs_system": "Indian RTGS System",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Central Banks"
    },
    {
        "name": "Reserve Bank of Australia",
        "institution_type": FinancialInstitutionType.CENTRAL_BANK,
        "swift_code": "RSBKAU2S",
        "country": "Australia",
        "rtgs_system": "RITS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Central Banks"
    },
    {
        "name": "Swiss National Bank",
        "institution_type": FinancialInstitutionType.CENTRAL_BANK,
        "swift_code": "SNBZCHZZ",
        "country": "Switzerland",
        "rtgs_system": "SIC",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Central Banks"
    },
    {
        "name": "Central Bank of Nigeria",
        "institution_type": FinancialInstitutionType.CENTRAL_BANK,
        "swift_code": "CBNINGLA",
        "country": "Nigeria",
        "rtgs_system": "Nigerian RTGS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Central Banks"
    },
    {
        "name": "South African Reserve Bank",
        "institution_type": FinancialInstitutionType.CENTRAL_BANK,
        "swift_code": "SABPZAJP",
        "country": "South Africa",
        "rtgs_system": "SAMOS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Central Banks"
    },
    
    # International Organizations
    {
        "name": "International Monetary Fund",
        "institution_type": FinancialInstitutionType.OTHER,
        "swift_code": "IMFDUS33",
        "country": "International",
        "rtgs_system": "IMF Funding System",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "International Organizations"
    },
    {
        "name": "World Bank",
        "institution_type": FinancialInstitutionType.OTHER,
        "swift_code": "IBRDUS33",
        "country": "International",
        "rtgs_system": "IBRD Funds Transfer System",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "International Organizations"
    },
    {
        "name": "Bank for International Settlements",
        "institution_type": FinancialInstitutionType.OTHER,
        "swift_code": "BISBCHBB",
        "country": "International/Switzerland",
        "rtgs_system": "BIS Correspondent Banking Services",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "International Organizations"
    },
    {
        "name": "African Development Bank",
        "institution_type": FinancialInstitutionType.OTHER,
        "swift_code": "AFDBCIAB",
        "country": "Pan-African",
        "rtgs_system": "AfDB Regional Payment System",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "International Organizations"
    },
    {
        "name": "Asian Development Bank",
        "institution_type": FinancialInstitutionType.OTHER,
        "swift_code": "ASDBPHMM",
        "country": "International",
        "rtgs_system": "ADB Payment System",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "International Organizations"
    },
    {
        "name": "European Investment Bank",
        "institution_type": FinancialInstitutionType.OTHER,
        "swift_code": "EIBLLU2X",
        "country": "European Union",
        "rtgs_system": "EIB Payment System",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "International Organizations"
    },
    {
        "name": "Inter-American Development Bank",
        "institution_type": FinancialInstitutionType.OTHER,
        "swift_code": "IADBUSW3",
        "country": "International",
        "rtgs_system": "IDB Payment System",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "International Organizations"
    },
    
    # Government Agencies
    {
        "name": "United States Department of the Treasury",
        "institution_type": FinancialInstitutionType.OTHER,
        "swift_code": "TREAS33",
        "country": "United States",
        "rtgs_system": "Fedwire Funds Service",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Government Agencies"
    },
    {
        "name": "HM Treasury",
        "institution_type": FinancialInstitutionType.OTHER,
        "swift_code": "HMTRGB2L",
        "country": "United Kingdom",
        "rtgs_system": "CHAPS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Government Agencies"
    },
    
    # Major US Banks
    {
        "name": "JPMorgan Chase Bank",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "CHASUS33",
        "country": "United States",
        "rtgs_system": "Fedwire Funds Service",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major US Banks"
    },
    {
        "name": "Bank of America",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "BOFAUS3N",
        "country": "United States",
        "rtgs_system": "Fedwire Funds Service",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major US Banks"
    },
    {
        "name": "Citibank",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "CITIUS33",
        "country": "United States",
        "rtgs_system": "Fedwire Funds Service",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major US Banks"
    },
    {
        "name": "Wells Fargo Bank",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "WFBIUS6S",
        "country": "United States",
        "rtgs_system": "Fedwire Funds Service",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major US Banks"
    },
    {
        "name": "Goldman Sachs Bank",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "GSCMUS33",
        "country": "United States",
        "rtgs_system": "Fedwire Funds Service",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major US Banks"
    },
    
    # Major European Banks
    {
        "name": "HSBC Bank",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "MIDLGB22",
        "country": "United Kingdom",
        "rtgs_system": "CHAPS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major European Banks"
    },
    {
        "name": "Barclays Bank",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "BARCGB22",
        "country": "United Kingdom",
        "rtgs_system": "CHAPS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major European Banks"
    },
    {
        "name": "Deutsche Bank",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "DEUTDEFF",
        "country": "Germany",
        "rtgs_system": "TARGET2",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major European Banks"
    },
    {
        "name": "BNP Paribas",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "BNPAFRPP",
        "country": "France",
        "rtgs_system": "TARGET2",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major European Banks"
    },
    {
        "name": "Credit Suisse",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "CRESCHZZ",
        "country": "Switzerland",
        "rtgs_system": "SIC",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major European Banks"
    },
    {
        "name": "UBS",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "UBSWCHZH",
        "country": "Switzerland",
        "rtgs_system": "SIC",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major European Banks"
    },
    
    # Major Asian Banks
    {
        "name": "Mitsubishi UFJ Financial Group",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "BOTKJPJT",
        "country": "Japan",
        "rtgs_system": "BOJ-NET",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major Asian Banks"
    },
    {
        "name": "Industrial and Commercial Bank of China",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "ICBKCNBJ",
        "country": "China",
        "rtgs_system": "China National Advanced Payment System (CNAPS)",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major Asian Banks"
    },
    {
        "name": "China Construction Bank",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "PCBCCNBJ",
        "country": "China",
        "rtgs_system": "China National Advanced Payment System (CNAPS)",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major Asian Banks"
    },
    {
        "name": "State Bank of India",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "SBININBB",
        "country": "India",
        "rtgs_system": "Indian RTGS System",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major Asian Banks"
    },
    {
        "name": "DBS Bank",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "DBSSSGSG",
        "country": "Singapore",
        "rtgs_system": "MEPS+",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major Asian Banks"
    },
    
    # Major Canadian Banks
    {
        "name": "Royal Bank of Canada",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "ROYCCAT2",
        "country": "Canada",
        "rtgs_system": "LVTS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major Canadian Banks"
    },
    {
        "name": "TD Canada Trust",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "TDOMCATTTOR",
        "country": "Canada",
        "rtgs_system": "LVTS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Major Canadian Banks"
    },
    
    # Australian & New Zealand Banks
    {
        "name": "Commonwealth Bank of Australia",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "CTBAAU2S",
        "country": "Australia",
        "rtgs_system": "RITS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Australian & New Zealand Banks"
    },
    {
        "name": "ANZ Banking Group",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "ANZBAU3M",
        "country": "Australia",
        "rtgs_system": "RITS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Australian & New Zealand Banks"
    },
    
    # African Banks
    {
        "name": "Standard Bank of South Africa",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "SBZAZAJJ",
        "country": "South Africa",
        "rtgs_system": "SAMOS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "African Banks"
    },
    {
        "name": "First Bank of Nigeria",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "FBNINGLA",
        "country": "Nigeria",
        "rtgs_system": "Nigerian RTGS",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "African Banks"
    },
    
    # Middle Eastern Banks
    {
        "name": "Qatar National Bank",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "QNBAQAQA",
        "country": "Qatar",
        "rtgs_system": "Qatar Payment System",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Middle Eastern Banks"
    },
    {
        "name": "Emirates NBD",
        "institution_type": FinancialInstitutionType.BANK,
        "swift_code": "EBILAEAD",
        "country": "United Arab Emirates",
        "rtgs_system": "UAE Funds Transfer System",
        "rtgs_enabled": True,
        "s2s_enabled": True,
        "is_active": True,
        "category": "Middle Eastern Banks"
    }
]


def populate_financial_institutions(batch_size=5):
    """Populate the database with a comprehensive list of financial institutions
    
    Args:
        batch_size (int): Number of institutions to process in each batch
                         to avoid timeouts with blockchain operations
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting to populate financial institutions")
    
    # Use Flask application context
    with app.app_context():
        # Keep track of statistics
        total = len(FINANCIAL_INSTITUTIONS)
        added = 0
        existing = 0
        failed = 0
        
        # Process in batches to avoid timeouts
        for i in range(0, len(FINANCIAL_INSTITUTIONS), batch_size):
            batch = FINANCIAL_INSTITUTIONS[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size} ({len(batch)} institutions)")
            
            for institution_data in batch:
                # Check if institution already exists
                existing_institution = FinancialInstitution.query.filter_by(name=institution_data["name"]).first()
                if existing_institution:
                    logger.info(f"Institution '{institution_data['name']}' already exists (ID: {existing_institution.id})")
                    print(f"Institution '{institution_data['name']}' already exists (ID: {existing_institution.id})")
                    existing += 1
                    continue

                # Generate Ethereum address for the institution
                eth_address, _ = generate_ethereum_account()
                if not eth_address:
                    logger.error(f"Failed to generate Ethereum address for {institution_data['name']}")
                    print(f"Failed to generate Ethereum address for {institution_data['name']}")
                    failed += 1
                    continue

                # Prepare metadata with country, RTGS information, and category
                metadata = {
                    "country": institution_data["country"],
                    "rtgs_system": institution_data["rtgs_system"],
                    "category": institution_data.get("category", "Other"),
                    "added_at": datetime.utcnow().isoformat()
                }

                # Add SWIFT info if available
                if institution_data["swift_code"]:
                    metadata["swift"] = {"bic": institution_data["swift_code"]}

                # Create new institution
                institution = FinancialInstitution(
                    name=institution_data["name"],
                    institution_type=institution_data["institution_type"],
                    ethereum_address=eth_address,
                    swift_code=institution_data["swift_code"],
                    rtgs_enabled=institution_data["rtgs_enabled"],
                    s2s_enabled=institution_data["s2s_enabled"],
                    is_active=institution_data["is_active"],
                    metadata_json=json.dumps(metadata)
                )

                db.session.add(institution)
                try:
                    db.session.commit()
                    logger.info(f"Added {institution_data['name']} successfully (ID: {institution.id})")
                    print(f"Added {institution_data['name']} successfully")
                    added += 1
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error adding {institution_data['name']}: {str(e)}")
                    print(f"Error adding {institution_data['name']}: {str(e)}")
                    failed += 1
            
            # Print batch progress
            print(f"Batch {i//batch_size + 1} completed: Added {added} so far")
        
        # Log summary
        logger.info(f"Financial institutions population completed")
        logger.info(f"Total: {total}, Added: {added}, Already Existing: {existing}, Failed: {failed}")
        
        # Print summary to console
        print(f"\nFinancial institutions population completed")
        print(f"Total: {total}, Added: {added}, Already Existing: {existing}, Failed: {failed}")
        
        return {
            "total": total,
            "added": added,
            "existing": existing,
            "failed": failed
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    print("Populating financial institutions...")
    result = populate_financial_institutions()
    print(f"Done! Added {result['added']} new institutions out of {result['total']} total.")