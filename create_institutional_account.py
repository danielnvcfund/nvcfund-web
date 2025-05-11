#!/usr/bin/env python3
"""
Create Institutional Treasury Investment Account for El Banco Espaniol Isabel II

This script creates a new institutional account holder and treasury investment account
based on the provided balance sheet data.
"""

import os
import sys
import logging
import uuid
import random
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("institutional_setup")

# Import modules with app context
def create_institutional_account():
    """Create institutional account with app context"""
    from app import app, db
    from models import User, Institution, FinancialInstitution
    from financial_institutions import FinancialInstitutionType
    from account_holder_models import (
        AccountHolder, 
        BankAccount,
        AccountType,
        AccountStatus,
        CurrencyType,
        Address,
        PhoneNumber
    )
    from treasury_loan import TreasuryAccount, TreasuryInvestment
    
    with app.app_context():
        # Check if institution already exists
        existing_institution = FinancialInstitution.query.filter_by(
            name="El Banco Espaniol Isabel II"
        ).first()
        
        if existing_institution:
            logger.info(f"Institution already exists with ID: {existing_institution.id}")
            return existing_institution
        
        # Create a new financial institution
        new_institution = FinancialInstitution(
            name="El Banco Espaniol Isabel II",
            code="EBEIII",
            institution_type=FinancialInstitutionType.COMMERCIAL_BANK,
            country="ES",  # Spain
            is_active=True,
            swift_code="EBEIES2X",  # Example SWIFT code
            website="https://bancoisabel.es",
            description="""El Banco Espanol Filipino de Isabel-II, established on August 01, 1851,
            manages substantial capital entrusted to NVC Fund Holding Trust.""",
            is_central_bank=False,
            is_correspondent=True,
            integration_level="API",
            api_endpoint="https://api.bancoisabel.es/v1"
        )
        
        logger.info("Creating new financial institution: El Banco Espaniol Isabel II")
        db.session.add(new_institution)
        db.session.flush()  # Get ID without committing
        
        # Create a unique username and email
        username = f"banco_isabel_{new_institution.id}"
        email = f"treasury@bancoisabel.es"
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            logger.info(f"User already exists with ID: {existing_user.id}")
        else:
            # Create a new user account
            new_user = User(
                username=username,
                email=email,
                password_hash="$pbkdf2-sha256$29000$n5MyBmBMKWXsvff.P0fImQ$1t8iyB2J.kfC9D6BmCkNUP9YR09TotkTMYiCxvJLgmo",  # Placeholder, will require reset
                role="institutional",
                first_name="Treasury",
                last_name="Department",
                organization="El Banco Espaniol Isabel II",
                country="ES",
                phone="+34 91 123 4567",
                email_verified=True,
                is_active=True
            )
            
            logger.info("Creating new user account for institution")
            db.session.add(new_user)
            db.session.flush()  # Get ID without committing
            
            existing_user = new_user
        
        # Create account holder
        account_holder = AccountHolder(
            name="El Banco Espaniol Isabel II",
            username=username,
            email=email,
            external_id=f"EBEIII-{uuid.uuid4().hex[:8].upper()}",
            is_business=True,
            business_name="El Banco Espaniol Isabel II",
            business_type="Financial Institution",
            tax_id="A12345678",  # Example Spanish tax ID
            kyc_verified=True,
            aml_verified=True,
            user_id=existing_user.id,
            broker="NVC Fund Bank"
        )
        
        logger.info("Creating new account holder record")
        db.session.add(account_holder)
        db.session.flush()  # Get ID without committing
        
        # Create address for account holder
        address = Address(
            name="Headquarters",
            line1="Calle de Alcalá, 48",
            city="Madrid",
            region="Madrid",
            zip="28014",
            country="ES",
            account_holder_id=account_holder.id
        )
        
        logger.info("Adding address information")
        db.session.add(address)
        
        # Create phone number for account holder
        phone = PhoneNumber(
            name="Main Office",
            number="+34 91 123 4567",
            is_primary=True,
            verified=True,
            account_holder_id=account_holder.id
        )
        
        logger.info("Adding phone information")
        db.session.add(phone)
        
        # Create primary NVCT bank account
        nvct_account = BankAccount(
            account_number=f"NVCT-{random.randint(10000000, 99999999)}",
            account_name="El Banco Espaniol Isabel II - Investment Account",
            account_type=AccountType.INVESTMENT,
            currency=CurrencyType.NVCT,
            balance=5000000000.0,  # 5 billion NVCT tokens
            available_balance=5000000000.0,
            status=AccountStatus.ACTIVE,
            account_holder_id=account_holder.id
        )
        
        logger.info("Creating NVCT investment account")
        db.session.add(nvct_account)
        
        # Create USD bank account
        usd_account = BankAccount(
            account_number=f"USD-{random.randint(10000000, 99999999)}",
            account_name="El Banco Espaniol Isabel II - USD Account",
            account_type=AccountType.INVESTMENT,
            currency=CurrencyType.USD,
            balance=5000000000.0,  # 5 billion USD
            available_balance=5000000000.0,
            status=AccountStatus.ACTIVE,
            account_holder_id=account_holder.id
        )
        
        logger.info("Creating USD investment account")
        db.session.add(usd_account)
        db.session.flush()  # Get IDs without committing
        
        # Create Treasury Account
        treasury_account = TreasuryAccount(
            account_number=f"TRES-{random.randint(10000000, 99999999)}",
            account_name="El Banco Espaniol Isabel II - Treasury",
            institution_id=new_institution.id,
            account_holder_id=account_holder.id,
            balance=10000000000.0,  # 10 billion
            available_balance=10000000000.0,
            currency=CurrencyType.NVCT,
            is_active=True,
            notes="""Treasury account for El Banco Espaniol Isabel II, entrusted to NVC Fund Holding Trust.
            Based on balance sheet dated Dec 31, 2024."""
        )
        
        logger.info("Creating Treasury account")
        db.session.add(treasury_account)
        db.session.flush()  # Get ID without committing
        
        # Create Treasury Investment
        investment = TreasuryInvestment(
            investment_id=f"INV-{uuid.uuid4().hex[:12].upper()}",
            account_id=treasury_account.id,
            amount=5000000000.0,  # 5 billion
            currency=CurrencyType.NVCT,
            interest_rate=3.25,  # 3.25%
            start_date=datetime.utcnow(),
            maturity_date=datetime.utcnow() + timedelta(days=365),  # 1 year
            is_active=True,
            investment_type="Term Deposit",
            notes="""El Banco Espaniol Isabel II investment based on balance sheet dated Dec 31, 2024.
            Entrusted to NVC Fund Holding Trust. Total assets reported as over $11.3 quadrillion."""
        )
        
        logger.info("Creating Treasury investment")
        db.session.add(investment)
        
        # Commit all changes
        try:
            db.session.commit()
            logger.info(f"Successfully created institutional account for El Banco Espaniol Isabel II")
            logger.info(f"Bank Account Numbers: NVCT: {nvct_account.account_number}, USD: {usd_account.account_number}")
            logger.info(f"Treasury Account: {treasury_account.account_number}")
            logger.info(f"Investment ID: {investment.investment_id}")
            
            return new_institution
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating institutional account: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        create_institutional_account()
        print("Successfully created institutional account for El Banco Espaniol Isabel II")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)