#!/usr/bin/env python3
"""
Add El Banco Espaniol Isabel II Treasury Account
This script adds the specified institutional treasury account.
"""

import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_banco_isabel():
    """Add El Banco Espaniol Isabel II Treasury Account"""
    from app import app, db
    from models import Institution
    from financial_institutions import FinancialInstitutionType
    from account_holder_models import CurrencyType, AccountStatus
    from treasury_loan import TreasuryAccount
    
    with app.app_context():
        # Check if institution exists
        existing = Institution.query.filter_by(name="El Banco Espaniol Isabel II").first()
        if existing:
            logger.info(f"Institution already exists with ID: {existing.id}")
            institution_id = existing.id
        else:
            # Create institution
            institution = Institution(
                name="El Banco Espaniol Isabel II",
                code="EBEIII",
                institution_type=FinancialInstitutionType.COMMERCIAL_BANK.value,
                country="ES",
                website="https://bancoisabel.es",
                description=(
                    "El Banco Espanol Filipino de Isabel-II, established on August 01, 1851, "
                    "manages substantial capital entrusted to NVC Fund Holding Trust."
                ),
                is_active=True,
                swift_code="EBEIES2X"
            )
            db.session.add(institution)
            db.session.flush()
            institution_id = institution.id
            logger.info(f"Created new institution with ID: {institution_id}")
        
        # Create treasury account
        treasury_account = TreasuryAccount(
            account_number="TRESBEI001",
            account_name="El Banco Espaniol Isabel II - Treasury Investment",
            institution_id=institution_id,
            balance=5000000000000.0,  # 5 trillion NVCT
            available_balance=5000000000000.0,
            currency=CurrencyType.NVCT.value,
            is_active=True,
            status=AccountStatus.ACTIVE.value,
            open_date=datetime.utcnow(),
            notes=(
                "El Banco Espanol Filipino de Isabel-II Treasury Investment Account. "
                "Based on balance sheet dated Dec 31, 2024. "
                "Assets reported as over $11.3 quadrillion."
            )
        )
        
        db.session.add(treasury_account)
        
        try:
            db.session.commit()
            logger.info(f"Successfully created treasury account with account number: {treasury_account.account_number}")
            return treasury_account
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating treasury account: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        account = add_banco_isabel()
        print(f"Successfully created treasury account: {account.account_number}")
        print(f"Account name: {account.account_name}")
        print(f"Balance: {account.balance:,.2f} {account.currency}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)