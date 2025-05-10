"""
Account Holder Models for NVC Private Banking
This module provides the database models for account holders, addresses, phone numbers,
and bank accounts.
"""

import enum
from datetime import datetime
from app import db
from sqlalchemy.ext.hybrid import hybrid_property

class ExchangeType(enum.Enum):
    """Types of currency exchanges"""
    NVCT_TO_FIAT = "nvct_to_fiat"
    FIAT_TO_NVCT = "fiat_to_nvct"
    NVCT_TO_CRYPTO = "nvct_to_crypto"
    CRYPTO_TO_NVCT = "crypto_to_nvct"
    FIAT_TO_FIAT = "fiat_to_fiat"
    CRYPTO_TO_CRYPTO = "crypto_to_crypto"
    NVCT_TO_AFD1 = "nvct_to_afd1"
    AFD1_TO_NVCT = "afd1_to_nvct"
    AFD1_TO_FIAT = "afd1_to_fiat"
    FIAT_TO_AFD1 = "fiat_to_afd1"
    NVCT_TO_SFN = "nvct_to_sfn"
    SFN_TO_NVCT = "sfn_to_nvct"
    SFN_TO_FIAT = "sfn_to_fiat"
    FIAT_TO_SFN = "fiat_to_sfn"
    NVCT_TO_AKLUMI = "nvct_to_aklumi"
    AKLUMI_TO_NVCT = "aklumi_to_nvct"
    AKLUMI_TO_FIAT = "aklumi_to_fiat"
    FIAT_TO_AKLUMI = "fiat_to_aklumi"
    
class ExchangeStatus(enum.Enum):
    """Status of currency exchange transactions"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AccountType(enum.Enum):
    """Account types for banking accounts"""
    CHECKING = "checking"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    BUSINESS = "business"
    CUSTODY = "custody"
    CRYPTO = "crypto"
    
class CurrencyType(enum.Enum):
    """Currency types for banking accounts"""
    # NVC Tokens and partner currencies
    NVCT = "NVCT"  # NVC Token (primary native currency)
    SPU = "SPU"    # Special Purpose Unit
    TU = "TU"      # Treasury Unit
    AFD1 = "AFD1"  # American Federation Dollar
    SFN = "SFN"    # SFN Coin from Swifin
    AKLUMI = "AKLUMI"  # Ak Lumi currency from Eco-6
    
    # Major World Currencies
    USD = "USD"    # US Dollar
    EUR = "EUR"    # Euro
    GBP = "GBP"    # British Pound
    JPY = "JPY"    # Japanese Yen
    CHF = "CHF"    # Swiss Franc
    CAD = "CAD"    # Canadian Dollar
    AUD = "AUD"    # Australian Dollar
    NZD = "NZD"    # New Zealand Dollar
    CNY = "CNY"    # Chinese Yuan Renminbi
    HKD = "HKD"    # Hong Kong Dollar
    SGD = "SGD"    # Singapore Dollar
    INR = "INR"    # Indian Rupee
    RUB = "RUB"    # Russian Ruble
    BRL = "BRL"    # Brazilian Real
    MXN = "MXN"    # Mexican Peso
    SEK = "SEK"    # Swedish Krona
    NOK = "NOK"    # Norwegian Krone
    DKK = "DKK"    # Danish Krone
    PLN = "PLN"    # Polish Zloty
    TRY = "TRY"    # Turkish Lira
    
    # African Currencies
    # North Africa
    DZD = "DZD"    # Algerian Dinar
    EGP = "EGP"    # Egyptian Pound
    LYD = "LYD"    # Libyan Dinar
    MAD = "MAD"    # Moroccan Dirham
    SDG = "SDG"    # Sudanese Pound
    TND = "TND"    # Tunisian Dinar
    
    # West Africa
    NGN = "NGN"    # Nigerian Naira
    GHS = "GHS"    # Ghanaian Cedi
    XOF = "XOF"    # CFA Franc BCEAO (Benin, Burkina Faso, Côte d'Ivoire, Guinea-Bissau, Mali, Niger, Senegal, Togo)
    GMD = "GMD"    # Gambian Dalasi
    GNF = "GNF"    # Guinean Franc
    LRD = "LRD"    # Liberian Dollar
    SLL = "SLL"    # Sierra Leonean Leone
    SLE = "SLE"    # Sierra Leonean Leone (new)
    CVE = "CVE"    # Cape Verdean Escudo
    
    # Central Africa
    XAF = "XAF"    # CFA Franc BEAC (Cameroon, Central African Republic, Chad, Republic of the Congo, Equatorial Guinea, Gabon)
    CDF = "CDF"    # Congolese Franc
    STN = "STN"    # São Tomé and Príncipe Dobra
    
    # East Africa
    KES = "KES"    # Kenyan Shilling
    ETB = "ETB"    # Ethiopian Birr
    UGX = "UGX"    # Ugandan Shilling
    TZS = "TZS"    # Tanzanian Shilling
    RWF = "RWF"    # Rwandan Franc
    BIF = "BIF"    # Burundian Franc
    DJF = "DJF"    # Djiboutian Franc
    ERN = "ERN"    # Eritrean Nakfa
    SSP = "SSP"    # South Sudanese Pound
    SOS = "SOS"    # Somali Shilling
    
    # Southern Africa
    ZAR = "ZAR"    # South African Rand
    LSL = "LSL"    # Lesotho Loti
    NAD = "NAD"    # Namibian Dollar
    SZL = "SZL"    # Swazi Lilangeni
    BWP = "BWP"    # Botswana Pula
    ZMW = "ZMW"    # Zambian Kwacha
    MWK = "MWK"    # Malawian Kwacha
    ZWL = "ZWL"    # Zimbabwean Dollar
    MZN = "MZN"    # Mozambican Metical
    MGA = "MGA"    # Malagasy Ariary
    SCR = "SCR"    # Seychellois Rupee
    MUR = "MUR"    # Mauritian Rupee
    AOA = "AOA"    # Angolan Kwanza
    
    # Asia Pacific Currencies
    IDR = "IDR"    # Indonesian Rupiah
    MYR = "MYR"    # Malaysian Ringgit
    PHP = "PHP"    # Philippine Peso
    THB = "THB"    # Thai Baht
    VND = "VND"    # Vietnamese Dong
    KRW = "KRW"    # South Korean Won
    TWD = "TWD"    # Taiwan New Dollar
    PKR = "PKR"    # Pakistani Rupee
    BDT = "BDT"    # Bangladeshi Taka
    NPR = "NPR"    # Nepalese Rupee
    LKR = "LKR"    # Sri Lankan Rupee
    
    # Middle East Currencies
    AED = "AED"    # UAE Dirham
    SAR = "SAR"    # Saudi Riyal
    QAR = "QAR"    # Qatari Riyal
    OMR = "OMR"    # Omani Rial
    BHD = "BHD"    # Bahraini Dinar
    KWD = "KWD"    # Kuwaiti Dinar
    ILS = "ILS"    # Israeli New Shekel
    JOD = "JOD"    # Jordanian Dinar
    LBP = "LBP"    # Lebanese Pound
    IRR = "IRR"    # Iranian Rial
    IQD = "IQD"    # Iraqi Dinar
    
    # Latin America & Caribbean Currencies
    ARS = "ARS"    # Argentine Peso
    CLP = "CLP"    # Chilean Peso
    COP = "COP"    # Colombian Peso
    PEN = "PEN"    # Peruvian Sol
    UYU = "UYU"    # Uruguayan Peso
    VES = "VES"    # Venezuelan Bolivar Soberano
    BOB = "BOB"    # Bolivian Boliviano
    PYG = "PYG"    # Paraguayan Guarani
    DOP = "DOP"    # Dominican Peso
    CRC = "CRC"    # Costa Rican Colon
    JMD = "JMD"    # Jamaican Dollar
    TTD = "TTD"    # Trinidad and Tobago Dollar
    
    # Eastern European Currencies
    CZK = "CZK"    # Czech Koruna
    HUF = "HUF"    # Hungarian Forint
    RON = "RON"    # Romanian Leu
    BGN = "BGN"    # Bulgarian Lev
    HRK = "HRK"    # Croatian Kuna
    RSD = "RSD"    # Serbian Dinar
    UAH = "UAH"    # Ukrainian Hryvnia
    BYN = "BYN"    # Belarusian Ruble
    
    # Top 30 Cryptocurrencies
    BTC = "BTC"    # Bitcoin
    ETH = "ETH"    # Ethereum
    USDT = "USDT"  # Tether
    BNB = "BNB"    # Binance Coin
    SOL = "SOL"    # Solana
    XRP = "XRP"    # XRP (Ripple)
    USDC = "USDC"  # USD Coin
    ADA = "ADA"    # Cardano
    AVAX = "AVAX"  # Avalanche
    DOGE = "DOGE"  # Dogecoin
    DOT = "DOT"    # Polkadot
    MATIC = "MATIC" # Polygon
    LTC = "LTC"    # Litecoin
    SHIB = "SHIB"  # Shiba Inu
    DAI = "DAI"    # Dai
    TRX = "TRX"    # TRON
    UNI = "UNI"    # Uniswap
    LINK = "LINK"  # Chainlink
    ATOM = "ATOM"  # Cosmos
    XMR = "XMR"    # Monero
    ETC = "ETC"    # Ethereum Classic
    FIL = "FIL"    # Filecoin
    XLM = "XLM"    # Stellar
    NEAR = "NEAR"  # NEAR Protocol
    ALGO = "ALGO"  # Algorand
    ZCASH = "ZCASH" # Zcash
    APE = "APE"    # ApeCoin
    ICP = "ICP"    # Internet Computer
    FLOW = "FLOW"  # Flow
    VET = "VET"    # VeChain

class AccountStatus(enum.Enum):
    """Status types for banking accounts"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    PENDING = "pending"

class Address(db.Model):
    """Address model for account holders"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="Primary Address")  # Name/label for this address
    line1 = db.Column(db.String(255))
    line2 = db.Column(db.String(255))
    pobox = db.Column(db.String(50))
    neighborhood = db.Column(db.String(100))
    city = db.Column(db.String(100))
    region = db.Column(db.String(100))  # State/Province
    zip = db.Column(db.String(20))
    country = db.Column(db.String(2))   # 2-letter country code
    street = db.Column(db.String(255))
    building_number = db.Column(db.String(50))
    complement = db.Column(db.String(255))
    
    # Foreign keys
    account_holder_id = db.Column(db.Integer, db.ForeignKey('account_holder.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Address {self.line1}, {self.city}, {self.country}>"
    
    @property
    def formatted(self):
        """Return a formatted address string"""
        parts = []
        if self.line1:
            parts.append(self.line1)
        if self.line2:
            parts.append(self.line2)
        city_parts = []
        if self.city:
            city_parts.append(self.city)
        if self.region:
            city_parts.append(self.region)
        if self.zip:
            city_parts.append(self.zip)
        if city_parts:
            parts.append(", ".join(city_parts))
        if self.country:
            parts.append(self.country)
        return "\n".join(parts)

class PhoneNumber(db.Model):
    """Phone number model for account holders"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))  # Type of phone (e.g. "Mobile", "Landline")
    number = db.Column(db.String(50))
    is_primary = db.Column(db.Boolean, default=False)
    is_mobile = db.Column(db.Boolean, default=False)
    verified = db.Column(db.Boolean, default=False)
    
    # Foreign keys
    account_holder_id = db.Column(db.Integer, db.ForeignKey('account_holder.id'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PhoneNumber {self.name}: {self.number}>"

class AccountHolder(db.Model):
    """Account holder model for NVC Private Banking"""
    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(64), index=True, unique=True)  # External identifier
    name = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Entity type (individual, corporate, etc.)
    is_business = db.Column(db.Boolean, default=False)
    business_name = db.Column(db.String(255))
    business_type = db.Column(db.String(100))
    tax_id = db.Column(db.String(50))
    
    # KYC/AML status
    kyc_verified = db.Column(db.Boolean, default=False)
    aml_verified = db.Column(db.Boolean, default=False)
    kyc_documents_json = db.Column(db.Text)  # JSON data for KYC documents
    
    # Broker information
    broker = db.Column(db.String(255))
    
    # Relationships
    addresses = db.relationship('Address', backref='account_holder', lazy=True)
    phone_numbers = db.relationship('PhoneNumber', backref='account_holder', lazy=True)
    accounts = db.relationship('BankAccount', backref='account_holder', lazy=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('account_holder', uselist=False))
    
    @hybrid_property
    def full_name(self):
        """Return full name of account holder"""
        return self.name
        
    @hybrid_property
    def primary_address(self):
        """Return primary address of account holder"""
        return Address.query.filter_by(account_holder_id=self.id).first()
    
    @hybrid_property
    def primary_phone(self):
        """Return primary phone of account holder"""
        primary = PhoneNumber.query.filter_by(account_holder_id=self.id, is_primary=True).first()
        if primary:
            return primary
        return PhoneNumber.query.filter_by(account_holder_id=self.id).first()
    
    def __repr__(self):
        return f"<AccountHolder {self.name} ({self.email})>"

class CurrencyExchangeRate(db.Model):
    """Currency exchange rates for the NVCT exchange system"""
    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.Enum(CurrencyType), nullable=False)
    to_currency = db.Column(db.Enum(CurrencyType), nullable=False)
    rate = db.Column(db.Float, nullable=False)  # Rate from_currency -> to_currency
    inverse_rate = db.Column(db.Float)  # Rate to_currency -> from_currency (calculated)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = db.Column(db.String(100))  # Source of rate (e.g., "internal", "external_api")
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f"<CurrencyExchangeRate {self.from_currency.value} -> {self.to_currency.value}: {self.rate}>"

class CurrencyExchangeTransaction(db.Model):
    """Record of currency exchange transactions"""
    id = db.Column(db.Integer, primary_key=True)
    exchange_type = db.Column(db.Enum(ExchangeType), nullable=False)
    from_currency = db.Column(db.Enum(CurrencyType), nullable=False)
    to_currency = db.Column(db.Enum(CurrencyType), nullable=False)
    from_amount = db.Column(db.Float, nullable=False)
    to_amount = db.Column(db.Float, nullable=False)
    rate_applied = db.Column(db.Float, nullable=False)
    fee_amount = db.Column(db.Float, default=0.0)
    fee_currency = db.Column(db.Enum(CurrencyType))
    status = db.Column(db.Enum(ExchangeStatus), default=ExchangeStatus.PENDING)
    reference_number = db.Column(db.String(50), unique=True)
    notes = db.Column(db.Text)
    
    # Transaction timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Foreign keys
    account_holder_id = db.Column(db.Integer, db.ForeignKey('account_holder.id'), nullable=False)
    from_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'), nullable=False)
    to_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'), nullable=False)
    rate_id = db.Column(db.Integer, db.ForeignKey('currency_exchange_rate.id'))
    
    # Relationships
    account_holder = db.relationship('AccountHolder', backref='exchange_transactions')
    from_account = db.relationship('BankAccount', foreign_keys=[from_account_id])
    to_account = db.relationship('BankAccount', foreign_keys=[to_account_id])
    exchange_rate = db.relationship('CurrencyExchangeRate')
    
    def __repr__(self):
        return f"<CurrencyExchange {self.from_currency.value} {self.from_amount} -> {self.to_currency.value} {self.to_amount}>"

class BankAccount(db.Model):
    """Bank account model for NVC Private Banking"""
    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(64), unique=True, nullable=False)
    account_name = db.Column(db.String(255))
    account_type = db.Column(db.Enum(AccountType), default=AccountType.CHECKING)
    currency = db.Column(db.Enum(CurrencyType), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    available_balance = db.Column(db.Float, default=0.0)
    status = db.Column(db.Enum(AccountStatus), default=AccountStatus.ACTIVE)
    
    # Foreign keys
    account_holder_id = db.Column(db.Integer, db.ForeignKey('account_holder.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_transaction_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f"<BankAccount {self.account_number} ({self.currency.value}): {self.balance}>"