"""
Account Number Generator for NVC Banking Platform
This module handles the generation and assignment of bank account numbers to new clients.
"""
import random
import string
import datetime
from sqlalchemy.exc import SQLAlchemyError
from app import db, logger
from account_holder_models import BankAccount, AccountType, CurrencyType, AccountStatus, AccountHolder


class AccountNumberGenerator:
    """Generator for new bank account numbers"""
    
    # Constants for account number generation
    BANK_CODE = "NVC"  # Bank identifier
    COUNTRY_CODE = "GL"  # Global code
    
    # Account number formats by type
    FORMATS = {
        AccountType.CHECKING: "CH",
        AccountType.SAVINGS: "SV",
        AccountType.INVESTMENT: "IN",
        AccountType.BUSINESS: "BZ",
        AccountType.CUSTODY: "CU",
        AccountType.CRYPTO: "CR",
        AccountType.INSTITUTIONAL: "IS",
        AccountType.CORRESPONDENT: "CB",
        AccountType.NOSTRO: "NO",
        AccountType.VOSTRO: "VO"
    }
    
    # Default structure: NVC-GL-{TYPE}-{YEAR}{MONTH}-{8_RANDOM_CHARS}
    
    @classmethod
    def generate_account_number(cls, account_type=AccountType.CHECKING):
        """
        Generate a new unique account number
        
        Args:
            account_type: Type of account to generate number for
            
        Returns:
            Unique account number string
        """
        # Get current date components
        now = datetime.datetime.now()
        year = str(now.year)[-2:]  # Last 2 digits of year
        month = str(now.month).zfill(2)  # Month with leading zero if needed
        
        # Get account type code
        type_code = cls.FORMATS.get(account_type, "CH")
        
        # Generate random alphanumeric component (8 characters)
        random_component = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=8))
        
        # Assemble account number
        account_number = f"{cls.BANK_CODE}-{cls.COUNTRY_CODE}-{type_code}-{year}{month}-{random_component}"
        
        # Ensure uniqueness by checking database
        while cls._account_number_exists(account_number):
            # Regenerate random component if duplicate is found
            random_component = ''.join(random.choices(
                string.ascii_uppercase + string.digits, k=8))
            account_number = f"{cls.BANK_CODE}-{cls.COUNTRY_CODE}-{type_code}-{year}{month}-{random_component}"
        
        return account_number
    
    @staticmethod
    def _account_number_exists(account_number):
        """
        Check if an account number already exists in the database
        
        Args:
            account_number: Account number to check
            
        Returns:
            True if exists, False otherwise
        """
        try:
            return db.session.query(BankAccount.query.filter_by(
                account_number=account_number).exists()).scalar()
        except SQLAlchemyError as e:
            logger.error(f"Database error checking account number: {str(e)}")
            # Assume it exists to be safe
            return True


def create_default_accounts_for_holder(account_holder, auto_commit=True):
    """
    Create and assign default accounts for a new account holder
    
    Args:
        account_holder: AccountHolder object to create accounts for
        auto_commit: Whether to commit changes to the database
        
    Returns:
        Dictionary of created accounts by currency
    """
    if not account_holder:
        logger.error("Cannot create accounts: No account holder provided")
        return None
    
    created_accounts = {}
    
    try:
        # Create primary NVCT account (always created)
        nvct_account = BankAccount()
        nvct_account.account_number = AccountNumberGenerator.generate_account_number()
        nvct_account.account_name = f"{account_holder.name} Primary NVCT Account"
        nvct_account.account_type = AccountType.CHECKING
        nvct_account.currency = CurrencyType.NVCT
        nvct_account.balance = 0.0
        nvct_account.available_balance = 0.0
        nvct_account.status = AccountStatus.ACTIVE
        nvct_account.account_holder_id = account_holder.id
        db.session.add(nvct_account)
        created_accounts['NVCT'] = nvct_account
        
        # Create USD account
        usd_account = BankAccount()
        usd_account.account_number = AccountNumberGenerator.generate_account_number()
        usd_account.account_name = f"{account_holder.name} USD Account"
        usd_account.account_type = AccountType.CHECKING
        usd_account.currency = CurrencyType.USD
        usd_account.balance = 0.0
        usd_account.available_balance = 0.0
        usd_account.status = AccountStatus.ACTIVE
        usd_account.account_holder_id = account_holder.id
        db.session.add(usd_account)
        created_accounts['USD'] = usd_account
        
        # Create EUR account (for international clients)
        eur_account = BankAccount()
        eur_account.account_number = AccountNumberGenerator.generate_account_number()
        eur_account.account_name = f"{account_holder.name} EUR Account"
        eur_account.account_type = AccountType.CHECKING
        eur_account.currency = CurrencyType.EUR
        eur_account.balance = 0.0
        eur_account.available_balance = 0.0
        eur_account.status = AccountStatus.ACTIVE
        eur_account.account_holder_id = account_holder.id
        db.session.add(eur_account)
        created_accounts['EUR'] = eur_account
        
        # Create Crypto custody account
        crypto_account = BankAccount()
        crypto_account.account_number = AccountNumberGenerator.generate_account_number(AccountType.CRYPTO)
        crypto_account.account_name = f"{account_holder.name} Crypto Custody Account"
        crypto_account.account_type = AccountType.CRYPTO
        crypto_account.currency = CurrencyType.BTC  # Default crypto display currency
        crypto_account.balance = 0.0
        crypto_account.available_balance = 0.0
        crypto_account.status = AccountStatus.ACTIVE
        crypto_account.account_holder_id = account_holder.id
        db.session.add(crypto_account)
        created_accounts['CRYPTO'] = crypto_account
        
        # For business accounts, create a business account type
        if account_holder.is_business:
            business_account = BankAccount()
            business_account.account_number = AccountNumberGenerator.generate_account_number(AccountType.BUSINESS)
            business_account.account_name = f"{account_holder.business_name} Business Account"
            business_account.account_type = AccountType.BUSINESS
            business_account.currency = CurrencyType.USD  # Default business currency
            business_account.balance = 0.0
            business_account.available_balance = 0.0
            business_account.status = AccountStatus.ACTIVE
            business_account.account_holder_id = account_holder.id
            db.session.add(business_account)
            created_accounts['BUSINESS'] = business_account
        
        if auto_commit:
            db.session.commit()
            logger.info(f"Created default accounts for account holder {account_holder.id}")
    
    except SQLAlchemyError as e:
        if auto_commit:
            db.session.rollback()
        logger.error(f"Database error creating accounts: {str(e)}")
        return None
    
    return created_accounts


def create_additional_account(account_holder, currency, account_type=AccountType.CHECKING, auto_commit=True):
    """
    Create an additional account for an existing account holder
    
    Args:
        account_holder: AccountHolder object to create account for
        currency: Currency for the new account
        account_type: Type of account to create
        auto_commit: Whether to commit changes to the database
        
    Returns:
        Created BankAccount object or None on error
    """
    if not account_holder:
        logger.error("Cannot create account: No account holder provided")
        return None
    
    try:
        # Generate a descriptive name based on currency and account type
        account_name = f"{account_holder.name} {currency.name} {account_type.name.capitalize()} Account"
        
        # Create the new account
        new_account = BankAccount()
        new_account.account_number = AccountNumberGenerator.generate_account_number(account_type)
        new_account.account_name = account_name
        new_account.account_type = account_type
        new_account.currency = currency
        new_account.balance = 0.0
        new_account.available_balance = 0.0
        new_account.status = AccountStatus.ACTIVE
        new_account.account_holder_id = account_holder.id
        
        db.session.add(new_account)
        
        if auto_commit:
            db.session.commit()
            logger.info(f"Created additional {currency.name} account for account holder {account_holder.id}")
        
        return new_account
    
    except SQLAlchemyError as e:
        if auto_commit:
            db.session.rollback()
        logger.error(f"Database error creating additional account: {str(e)}")
        return None


def create_institutional_account(account_holder, currency=CurrencyType.USD, auto_commit=True):
    """
    Create an institutional account for a financial institution
    
    Args:
        account_holder: AccountHolder object to create account for
        currency: Currency for the new account (either CurrencyType enum or string)
        auto_commit: Whether to commit changes to the database
        
    Returns:
        Created BankAccount object or None on error
    """
    if not account_holder:
        logger.error("Cannot create institutional account: No account holder provided")
        return None
        
    # Handle string currency
    if isinstance(currency, str):
        try:
            currency = getattr(CurrencyType, currency)
        except (AttributeError, TypeError):
            logger.error(f"Invalid currency: {currency}")
            return None
        
    try:
        # Generate a specialized name for institutional accounts
        account_name = f"{account_holder.name} Institutional {currency.name} Account"
        
        # Create the institutional account
        inst_account = BankAccount()
        inst_account.account_number = AccountNumberGenerator.generate_account_number(AccountType.INSTITUTIONAL)
        inst_account.account_name = account_name
        inst_account.account_type = AccountType.INSTITUTIONAL
        inst_account.currency = currency
        inst_account.balance = 0.0
        inst_account.available_balance = 0.0
        inst_account.status = AccountStatus.ACTIVE
        inst_account.account_holder_id = account_holder.id
        
        db.session.add(inst_account)
        
        if auto_commit:
            db.session.commit()
            logger.info(f"Created institutional {currency.name} account for account holder {account_holder.id}")
        
        return inst_account
        
    except SQLAlchemyError as e:
        if auto_commit:
            db.session.rollback()
        logger.error(f"Database error creating institutional account: {str(e)}")
        return None
    
    
def create_correspondent_account(account_holder, currency=CurrencyType.USD, nostro=True, auto_commit=True):
    """
    Create a correspondent banking account
    
    Args:
        account_holder: AccountHolder object to create account for
        currency: Currency for the new account (either CurrencyType enum or string)
        nostro: If True, creates a nostro account (we hold with them), 
                otherwise creates a vostro account (they hold with us)
        auto_commit: Whether to commit changes to the database
        
    Returns:
        Created BankAccount object or None on error
    """
    if not account_holder:
        logger.error("Cannot create correspondent account: No account holder provided")
        return None
    
    # Handle string currency
    if isinstance(currency, str):
        try:
            currency = getattr(CurrencyType, currency)
        except (AttributeError, TypeError):
            logger.error(f"Invalid currency: {currency}")
            return None
    
    account_type = AccountType.NOSTRO if nostro else AccountType.VOSTRO
    
    try:
        # Special naming for correspondent accounts
        type_name = "Nostro" if nostro else "Vostro"
        account_name = f"{account_holder.name} {currency.name} {type_name} Account"
        
        # Create the correspondent account
        corr_account = BankAccount()
        corr_account.account_number = AccountNumberGenerator.generate_account_number(account_type)
        corr_account.account_name = account_name
        corr_account.account_type = account_type
        corr_account.currency = currency
        corr_account.balance = 0.0
        corr_account.available_balance = 0.0
        corr_account.status = AccountStatus.ACTIVE
        corr_account.account_holder_id = account_holder.id
        
        db.session.add(corr_account)
        
        if auto_commit:
            db.session.commit()
            logger.info(f"Created {type_name} correspondent {currency.name} account for account holder {account_holder.id}")
        
        return corr_account
        
    except SQLAlchemyError as e:
        if auto_commit:
            db.session.rollback()
        logger.error(f"Database error creating correspondent account: {str(e)}")
        return None