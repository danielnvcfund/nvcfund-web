from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, PasswordField, BooleanField, FloatField, SubmitField, HiddenField, DateField, RadioField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, Email, EqualTo, NumberRange, ValidationError, Regexp
from models import TransactionType, PaymentGatewayType
from account_holder_models import CurrencyType
from datetime import datetime, timedelta


class BaseForm(FlaskForm):
    """Base form class for all forms in the application"""
    class Meta:
        csrf = True  # Enable CSRF protection for all forms

def get_currency_choices():
    """Get list of supported currencies"""
    return [
        # Fiat currencies
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'), 
        ('GBP', 'GBP - British Pound'),
        ('JPY', 'JPY - Japanese Yen'),
        ('CHF', 'CHF - Swiss Franc'),
        ('CNY', 'CNY - Chinese Yuan'),
        ('AUD', 'AUD - Australian Dollar'),
        ('CAD', 'CAD - Canadian Dollar'),
        
        # African Currencies
        ('NGN', 'NGN - Nigerian Naira'),
        ('ZAR', 'ZAR - South African Rand'),
        ('EGP', 'EGP - Egyptian Pound'),
        ('GHS', 'GHS - Ghanaian Cedi'),
        
        # Native Tokens
        ('NVCT', 'NVCT - NVC Token'),
        ('AFD1', 'AFD1 - American Federation Dollar'),
        ('SFN', 'SFN - SFN Coin'),
        ('AKLUMI', 'AKLUMI - Ak Lumi'),
        
        # Cryptocurrencies
        ('ETH', 'ETH - Ethereum'),
        ('BTC', 'BTC - Bitcoin'),
        ('USDT', 'USDT - Tether'),
        ('USDC', 'USDC - USD Coin')
    ]

class FinancialInstitutionForm(FlaskForm):
    name = StringField('Institution Name', validators=[DataRequired(), Length(max=255)])
    swift_code = StringField('SWIFT/BIC Code', validators=[DataRequired(), Length(min=8, max=11)])
    country = StringField('Country', validators=[DataRequired(), Length(max=100)])
    institution_type = SelectField('Institution Type', choices=[
        ('bank', 'Bank'),
        ('central_bank', 'Central Bank'),
        ('investment_firm', 'Investment Firm'),
        ('other', 'Other')
    ], validators=[DataRequired()])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    
class CurrencyExchangeForm(BaseForm):
    """Form for currency exchange operations"""
    from_currency = SelectField('From Currency', validators=[DataRequired()], choices=get_currency_choices())
    to_currency = SelectField('To Currency', validators=[DataRequired()], choices=get_currency_choices())
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=1.0)
    
    # Source and destination accounts
    from_account = SelectField('From Account', validators=[DataRequired()], coerce=int)
    to_account = SelectField('To Account', validators=[DataRequired()], coerce=int)
    
    # Optional fields
    use_custom_rate = BooleanField('Use Custom Rate', default=False)
    custom_rate = DecimalField('Custom Rate', validators=[Optional(), NumberRange(min=0.00001)], default=1.0)
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])

class RegistrationForm(FlaskForm):
    """Combined user registration form for both personal and business accounts"""
    # Account type selection
    account_type = SelectField('Account Type', 
                              choices=[('personal', 'Personal Account'), ('business', 'Business Account')],
                              default='personal',
                              validators=[DataRequired()])
    
    # Basic credentials - required for all accounts
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    
    # Personal information
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[DataRequired()])
    country = StringField('Country', validators=[DataRequired()])
    
    # Business specific fields
    organization = StringField('Company/Organization Name', validators=[Optional()]) 
    business_type = StringField('Business Type', validators=[Optional()])
    tax_id = StringField('Tax ID / Business Registration Number', validators=[Optional()])
    business_address = StringField('Business Address', validators=[Optional()])
    business_website = StringField('Business Website', validators=[Optional()])
    
    # Settings and agreements
    newsletter = BooleanField('Subscribe to Newsletter', default=True)
    invite_code = HiddenField('Invitation Code')
    terms_agree = BooleanField('I agree to the Terms of Service and Privacy Policy', validators=[DataRequired()])

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password')])

class ForgotUsernameForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])

class TransferForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired()])
    recipient = StringField('Recipient Address', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])

class BlockchainTransactionForm(FlaskForm):
    receiver_address = StringField('Receiver Address', validators=[DataRequired(), Length(min=42, max=42)])
    amount = FloatField('Amount (ETH)', validators=[DataRequired()])
    gas_price = FloatField('Gas Price (Gwei)', default=1.0)

class PaymentGatewayForm(FlaskForm):
    name = StringField('Gateway Name', validators=[DataRequired()])
    gateway_type = SelectField('Gateway Type', choices=[], validators=[DataRequired()])
    api_endpoint = StringField('API Endpoint')
    api_key = StringField('API Key')
    webhook_secret = StringField('Webhook Secret')
    ethereum_address = StringField('Ethereum Address')

class InvitationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    invitation_type = SelectField('Invitation Type', choices=[], validators=[DataRequired()])
    organization_name = StringField('Organization Name')
    message = TextAreaField('Personal Message')
    expires_days = SelectField('Expires In', choices=[(7, '7 Days'), (14, '14 Days'), (30, '30 Days')], coerce=int, default=7)

class AcceptInvitationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])

class TestPaymentForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired()])
    currency = SelectField('Currency', choices=[('USD', 'USD'), ('EUR', 'EUR')], validators=[DataRequired()])
    gateway_id = SelectField('Payment Gateway', choices=[], validators=[DataRequired()])
    test_scenario = SelectField('Test Scenario', choices=[
        ('success', 'Success'), 
        ('failed', 'Failed'),
        ('3d_secure', '3D Secure'),
        ('webhook', 'Webhook')
    ], default='success', validators=[DataRequired()])
    description = TextAreaField('Description', default='Test payment from nvcplatform.net')
    success = BooleanField('Simulate Success')
    submit = SubmitField('Submit Payment')

class PaymentForm(FlaskForm):
    transaction_id = HiddenField('Transaction ID', validators=[Optional()])
    amount = FloatField('Amount', validators=[DataRequired()])
    currency = SelectField('Currency', choices=[('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('ETH', 'ETH'), ('XRP', 'XRP')], validators=[DataRequired()])
    transaction_type = SelectField('Transaction Type', choices=[], validators=[DataRequired()])
    gateway_id = SelectField('Payment Gateway', choices=[], validators=[DataRequired()])
    recipient_name = StringField('Recipient Name', validators=[DataRequired(), Length(max=128)])
    recipient_institution = StringField('Receiving Institution', validators=[DataRequired(), Length(max=128)])
    recipient_account = StringField('Account Number', validators=[DataRequired(), Length(max=64)])
    description = TextAreaField('Description', validators=[DataRequired()], default='Payment from nvcplatform.net')
    submit = SubmitField('Submit Payment')

    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)
        # Dynamically load transaction types from the Enum
        self.transaction_type.choices = [(t.name, t.value) for t in TransactionType]
        
class PayPalPaymentForm(FlaskForm):
    """Form for PayPal payments"""
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than 0.01")])
    currency = SelectField('Currency', choices=[
        # Fiat currencies
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound'),
        ('CAD', 'CAD - Canadian Dollar'),
        ('AUD', 'AUD - Australian Dollar'),
        ('JPY', 'JPY - Japanese Yen'),
        
        # Cryptocurrencies
        ('NVCT', 'NVCT - NVC Token'),
        ('ETH', 'ETH - Ethereum'),
        ('BTC', 'BTC - Bitcoin'),
        ('USDT', 'USDT - Tether'),
        ('USDC', 'USDC - USD Coin'),
        ('AFD1', 'AFD1 - American Federation Dollar')
    ], default='USD', validators=[DataRequired()])
    recipient_email = StringField('Recipient PayPal Email', validators=[
        DataRequired(),
        Email(message="Please enter a valid email address"),
        Length(max=120, message="Email must be 120 characters or less")
    ])
    description = TextAreaField('Payment Description', validators=[
        DataRequired(),
        Length(max=250, message="Description must be 250 characters or less")
    ], default='Payment from NVC Banking Platform')
    notes = TextAreaField('Notes to Recipient (Optional)', validators=[
        Optional(),
        Length(max=500, message="Notes must be 500 characters or less")
    ])
    submit = SubmitField('Process PayPal Payment')
    
class PayPalPayoutForm(FlaskForm):
    """Form for PayPal payouts (sending money)"""
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than 0.01")])
    currency = SelectField('Currency', choices=[
        # Fiat currencies
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound'),
        ('CAD', 'CAD - Canadian Dollar'),
        ('AUD', 'AUD - Australian Dollar'),
        ('JPY', 'JPY - Japanese Yen'),
        
        # Cryptocurrencies
        ('NVCT', 'NVCT - NVC Token'),
        ('ETH', 'ETH - Ethereum'),
        ('BTC', 'BTC - Bitcoin'),
        ('USDT', 'USDT - Tether'),
        ('USDC', 'USDC - USD Coin'),
        ('AFD1', 'AFD1 - American Federation Dollar')
    ], default='USD', validators=[DataRequired()])
    recipient_email = StringField('Recipient PayPal Email', validators=[
        DataRequired(),
        Email(message="Please enter a valid email address"),
        Length(max=120, message="Email must be 120 characters or less")
    ])
    note = TextAreaField('Note to Recipient', validators=[
        DataRequired(),
        Length(max=250, message="Note must be 250 characters or less")
    ], default='Payout from NVC Banking Platform')
    email_subject = StringField('Email Subject', validators=[
        Optional(),
        Length(max=100, message="Subject must be 100 characters or less")
    ], default='You have received a payment from NVC Banking Platform')
    email_message = TextAreaField('Email Message', validators=[
        Optional(),
        Length(max=500, message="Message must be 500 characters or less")
    ])
    submit = SubmitField('Send PayPal Payout')


class POSPaymentForm(BaseForm):
    """Form for accepting credit card payments via POS"""
    amount = FloatField('Amount', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Amount must be greater than 0.01")
    ])
    currency = SelectField('Currency', choices=[
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound'),
        ('NVCT', 'NVCT - NVC Token')
    ], default='USD', validators=[DataRequired()])
    customer_name = StringField('Customer Name', validators=[
        DataRequired(),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters")
    ])
    customer_email = StringField('Customer Email (Optional)', validators=[
        Optional(),
        Email(message="Please enter a valid email address"),
        Length(max=120, message="Email must be 120 characters or less")
    ])
    description = TextAreaField('Description (Optional)', validators=[
        Optional(),
        Length(max=250, message="Description must be 250 characters or less")
    ])


class POSSendPaymentForm(BaseForm):
    """Form for sending money to credit cards via POS"""
    amount = FloatField('Amount', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Amount must be greater than 0.01")
    ])
    currency = SelectField('Currency', choices=[
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound'),
        ('NVCT', 'NVCT - NVC Token')
    ], default='USD', validators=[DataRequired()])
    recipient_name = StringField('Recipient Name', validators=[
        DataRequired(),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters")
    ])
    recipient_email = StringField('Recipient Email (Optional)', validators=[
        Optional(),
        Email(message="Please enter a valid email address"),
        Length(max=120, message="Email must be 120 characters or less")
    ])
    card_number = StringField('Last 4 Digits of Card', validators=[
        DataRequired(),
        Length(min=4, max=4, message="Please enter exactly 4 digits"),
        Regexp(r'^\d{4}$', message="Please enter only digits")
    ])
    description = TextAreaField('Description (Optional)', validators=[
        Optional(),
        Length(max=250, message="Description must be 250 characters or less")
    ])
    
class NVCPlatformSettingsForm(FlaskForm):
    """Form for NVC Platform integration settings"""
    api_url = StringField('API URL', validators=[
        DataRequired(),
        Length(max=255, message="URL must be 255 characters or less")
    ])
    api_key = StringField('API Key', validators=[
        Optional(),
        Length(max=255, message="API Key must be 255 characters or less")
    ])
    api_secret = PasswordField('API Secret', validators=[
        Optional(),
        Length(max=255, message="API Secret must be 255 characters or less")
    ])
    auto_sync = BooleanField('Enable Automatic Synchronization', default=False)

class ClientRegistrationForm(FlaskForm):
    """Form for client registration"""
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    organization = StringField('Company/Organization', validators=[Optional(), Length(max=100)])
    country = StringField('Country', validators=[Optional(), Length(max=100)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    newsletter = BooleanField('Subscribe to Newsletter', default=True)
    invite_code = HiddenField('Invitation Code')
    terms_agree = BooleanField('I agree to the Terms of Service and Privacy Policy', validators=[DataRequired()])

class PartnerRegistrationForm(FlaskForm):
    """Form for partner program registration"""
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    company_name = StringField('Company/Organization', validators=[DataRequired(), Length(max=100)])
    partner_type = SelectField('Partner Type', choices=[
        ('payment_processor', 'Payment Processor'),
        ('financial_institution', 'Financial Institution'),
        ('service_provider', 'Service Provider'),
        ('technology_partner', 'Technology Partner'),
        ('consultant', 'Consultant/Advisory')
    ], validators=[DataRequired()])
    website = StringField('Website', validators=[Optional(), Length(max=255)])
    country = StringField('Country', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    company_size = SelectField('Company Size', choices=[
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201-1000', '201-1000 employees'),
        ('1000+', '1000+ employees')
    ], validators=[DataRequired()])
    partnership_goals = TextAreaField('Partnership Goals', validators=[DataRequired(), Length(max=500)])
    invite_code = HiddenField('Invitation Code')
    newsletter = BooleanField('Subscribe to Newsletter', default=True)
    terms_agree = BooleanField('I agree to the Terms of Service and Privacy Policy', validators=[DataRequired()])

class CreditCardPaymentForm(FlaskForm):
    """Form for accepting credit card payments"""
    amount = FloatField('Amount', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Amount must be greater than 0.01")
    ])
    currency = SelectField('Currency', choices=get_currency_choices(), default='USD', validators=[DataRequired()])
    description = TextAreaField('Payment Description', validators=[
        DataRequired(),
        Length(max=255, message="Description must be 255 characters or less")
    ], default='Payment to NVC Banking Platform')
    customer_email = StringField('Customer Email (for receipt)', validators=[
        Optional(),
        Email(message="Please enter a valid email address")
    ])
    account_holder_id = SelectField('Associated Account Holder', coerce=int, validators=[DataRequired()])
    save_card = BooleanField('Save card for future payments', default=False)
    submit = SubmitField('Process Payment')

class CreditCardPayoutForm(FlaskForm):
    """Form for sending money to credit cards"""
    account_holder_id = SelectField('Account Holder', coerce=int, validators=[DataRequired()])
    account_id = SelectField('From Account', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount to Send', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Amount must be greater than 0.01")
    ])
    currency = SelectField('Currency', choices=get_currency_choices(), default='USD', validators=[DataRequired()])
    recipient_name = StringField('Recipient Name', validators=[
        DataRequired(),
        Length(max=128, message="Name must be 128 characters or less")
    ])
    # Card token will be set by Stripe.js
    card_token = HiddenField('Card Token')
    description = TextAreaField('Payment Description', validators=[
        DataRequired(),
        Length(max=255, message="Description must be 255 characters or less")
    ], default='Payment from NVC Banking Platform')
    save_recipient = BooleanField('Save recipient for future payments', default=False)
    submit = SubmitField('Send Payment')

class BankTransferForm(FlaskForm):
    transaction_id = HiddenField('Transaction ID', validators=[Optional()])
    recipient_name = StringField('Recipient Name', validators=[DataRequired()])
    bank_name = StringField('Bank Name', validators=[DataRequired()])
    account_number = StringField('Account Number', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])

class LetterOfCreditForm(FlaskForm):
    """Form for creating a standby letter of credit via SWIFT MT760"""
    # Issuing Bank Information
    issuing_bank_id = SelectField('Issuing Bank', coerce=int, validators=[DataRequired()],
                                 description="The financial institution that will issue the Letter of Credit")
    
    # Advising Bank Information
    advising_bank_id = SelectField('Advising Bank', coerce=int, validators=[DataRequired()],
                                  description="The bank that will advise the beneficiary of the Letter of Credit")
    
    # Application Information
    applicant_name = StringField('Applicant Name', validators=[DataRequired(), Length(max=100)],
                                description="Full legal name of the party requesting the Letter of Credit")
    applicant_address = TextAreaField('Applicant Address', validators=[DataRequired()],
                                     description="Complete address of the applicant")
    applicant_reference = StringField('Applicant Reference', validators=[Optional(), Length(max=35)],
                                     description="Your reference number for this transaction")
    
    # Beneficiary Information
    beneficiary_name = StringField('Beneficiary Name', validators=[DataRequired(), Length(max=100)],
                                  description="Full legal name of the party receiving the Letter of Credit")
    beneficiary_address = TextAreaField('Beneficiary Address', validators=[DataRequired()],
                                       description="Complete address of the beneficiary")
    beneficiary_account = StringField('Beneficiary Account/IBAN', validators=[Optional(), Length(max=34)],
                                     description="Account number or IBAN of the beneficiary")
    beneficiary_bank = StringField('Beneficiary Bank', validators=[Optional(), Length(max=100)],
                                  description="Name of the beneficiary's bank")
    beneficiary_bank_swift = StringField('Beneficiary Bank SWIFT', validators=[Optional(), Length(min=8, max=11)],
                                        description="SWIFT/BIC code of the beneficiary's bank")
    
    # Financial Information
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)],
                       description="Monetary value of the Letter of Credit")
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()],
                          description="Currency of the Letter of Credit")
    available_with = SelectField('Available With', choices=[
        ('issuing', 'Issuing Bank'),
        ('advising', 'Advising Bank'),
        ('any', 'Any Bank')
    ], validators=[DataRequired()],
    description="Where the Letter of Credit can be negotiated")
    
    # Date Information
    issue_date = DateField('Issue Date', validators=[Optional()],
                          description="Date when the Letter of Credit is issued")
    expiry_date = DateField('Expiry Date', validators=[DataRequired()],
                           description="The date until which the Letter of Credit is valid")
    expiry_place = StringField('Place of Expiry', validators=[Optional(), Length(max=100)],
                              description="Location where the Letter of Credit expires")
    
    # Transaction Information
    transaction_type = SelectField('Transaction Type', choices=[
        ('standby', 'Standby Letter of Credit'),
        ('commercial', 'Commercial Letter of Credit'),
        ('performance', 'Performance Guarantee'),
        ('advance_payment', 'Advance Payment Guarantee'),
        ('bid_bond', 'Bid Bond')
    ], validators=[DataRequired()],
    description="Type of Letter of Credit or guarantee")
    
    # Goods/Services Information
    goods_description = TextAreaField('Goods/Services Description', validators=[DataRequired()],
                                     description="Description of the goods or services covered by this Letter of Credit")
    
    # Documents Required
    documents_required = TextAreaField('Documents Required', validators=[Optional()],
                                      description="List of documents that must be presented for payment")
    
    # Terms and Conditions
    special_conditions = TextAreaField('Special Terms and Conditions', validators=[Optional()],
                                      description="Any special terms or conditions beyond standard boilerplate")
    
    # Additional Fields
    charges = SelectField('Bank Charges', choices=[
        ('applicant', 'All charges for Applicant account'),
        ('beneficiary', 'All charges for Beneficiary account'),
        ('shared', 'Charges shared between parties')
    ], validators=[Optional()],
    description="Who will pay the bank charges")
    
    partial_shipments = SelectField('Partial Shipments', choices=[
        ('allowed', 'Allowed'),
        ('not_allowed', 'Not Allowed')
    ], validators=[Optional()],
    description="Whether partial shipments are permitted")
    
    transferable = SelectField('Transferable', choices=[
        ('yes', 'Yes'),
        ('no', 'No')
    ], default='no', validators=[Optional()],
    description="Whether this Letter of Credit can be transferred to another beneficiary")
    
    confirmation_instructions = SelectField('Confirmation Instructions', choices=[
        ('confirm', 'Confirm'),
        ('may_add', 'May Add'),
        ('without', 'Without')
    ], validators=[Optional()],
    description="Instructions regarding confirmation of the Letter of Credit")
    
    presentation_period = StringField('Presentation Period', validators=[Optional(), Length(max=50)],
                                     description="Period after shipment within which documents must be presented")
    
    remarks = TextAreaField('Additional Remarks', validators=[Optional()],
                           description="Any additional information relevant to this Letter of Credit")
    
    submit = SubmitField('Issue Letter of Credit')

class SwiftFundTransferForm(FlaskForm):
    """Form for creating a SWIFT MT103/MT202 fund transfer"""
    # Receiving Institution Information
    receiver_institution_id = SelectField('Receiving Institution', coerce=int, validators=[DataRequired()])
    receiver_institution_name = StringField('Institution Name', validators=[DataRequired()])
    
    # Receiving Bank Details
    receiving_bank_name = StringField('Receiving Bank Name', validators=[DataRequired()])
    receiving_bank_address = TextAreaField('Receiving Bank Address', validators=[DataRequired()])
    receiving_bank_swift = StringField('Receiving Bank SWIFT/BIC Code', validators=[DataRequired()])
    receiving_bank_routing = StringField('Receiving Bank Routing Number/ABA', validators=[Optional()])
    receiving_bank_officer = StringField('Bank Officer Contact', validators=[Optional()], 
                                         description="Name and contact details of a bank officer for tracing transfers")
    
    # Account Holder Details
    account_holder_name = StringField('Account Holder Name', validators=[DataRequired()])
    account_number = StringField('Account Number/IBAN', validators=[DataRequired()])
    
    # Correspondent & Intermediary Banks
    correspondent_bank_name = StringField('Correspondent Bank Name', validators=[Optional()])
    correspondent_bank_swift = StringField('Correspondent Bank SWIFT/BIC', validators=[Optional()])
    intermediary_bank_name = StringField('Intermediary Bank Name', validators=[Optional()])
    intermediary_bank_swift = StringField('Intermediary Bank SWIFT/BIC', validators=[Optional()])
    
    # Transfer Details
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    
    # Sender & Recipient Information
    ordering_customer = TextAreaField('Ordering Customer/Institution', validators=[DataRequired()])
    beneficiary_customer = TextAreaField('Beneficiary Customer/Institution', validators=[DataRequired()])
    details_of_payment = TextAreaField('Payment Details', validators=[DataRequired()])
    
    # Transfer Type
    is_financial_institution = RadioField('Transfer Type', choices=[
        (0, 'Customer Transfer (MT103)'),
        (1, 'Financial Institution Transfer (MT202)')
    ], coerce=int, default=0)
    
    submit = SubmitField('Create Fund Transfer')

class ACHTransferForm(FlaskForm):
    """Form for creating an ACH (Automated Clearing House) transfer"""
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than 0.01")])
    
    # Recipient Personal Information
    recipient_name = StringField('Recipient Name', validators=[
        DataRequired(), 
        Length(min=2, max=100, message="Recipient name must be between 2 and 100 characters")
    ])
    
    recipient_address_line1 = StringField('Recipient Address Line 1', validators=[
        Optional(),
        Length(min=2, max=100, message="Address must be between 2 and 100 characters")
    ])
    
    recipient_address_line2 = StringField('Recipient Address Line 2', validators=[
        Optional(),
        Length(max=100, message="Address must be 100 characters or less")
    ])
    
    recipient_city = StringField('Recipient City', validators=[
        Optional(),
        Length(min=2, max=50, message="City must be between 2 and 50 characters")
    ])
    
    recipient_state = StringField('Recipient State/Province', validators=[
        Optional(),
        Length(min=2, max=20, message="State must be between 2 and 20 characters")
    ])
    
    recipient_zip = StringField('Recipient ZIP/Postal Code', validators=[
        Optional(),
        Length(min=5, max=10, message="ZIP/Postal code must be between 5 and 10 characters")
    ])
    
    # Recipient Bank Information
    recipient_bank_name = StringField('Recipient Bank Name', validators=[
        DataRequired(),
        Length(min=2, max=100, message="Bank name must be between 2 and 100 characters")
    ])
    
    recipient_bank_address = StringField('Recipient Bank Address', validators=[
        Optional(),
        Length(max=150, message="Bank address must be 150 characters or less")
    ])
    
    recipient_account_number = StringField('Recipient Account Number', validators=[
        DataRequired(),
        Length(min=4, max=17, message="Account number must be between 4 and 17 digits"),
        Regexp(r'^\d+$', message="Account number must contain only digits")
    ])
    
    recipient_routing_number = StringField('Recipient Routing Number', validators=[
        DataRequired(),
        Length(min=9, max=9, message="Routing number must be exactly 9 digits"),
        Regexp(r'^\d{9}$', message="Routing number must be exactly 9 digits")
    ])
    
    recipient_account_type = SelectField('Recipient Account Type', choices=[
        ('checking', 'Checking Account'),
        ('savings', 'Savings Account'),
        ('business', 'Business Account')
    ], validators=[DataRequired()])
    
    # ACH Transaction Details
    entry_class_code = SelectField('ACH Entry Class Code', choices=[
        ('PPD', 'PPD - Personal Payments'),
        ('CCD', 'CCD - Corporate Payments'),
        ('WEB', 'WEB - Internet Payments'),
        ('TEL', 'TEL - Telephone Payments'),
        ('CIE', 'CIE - Customer-Initiated Entries'),
        ('BOC', 'BOC - Back Office Conversion'),
        ('POP', 'POP - Point-of-Purchase')
    ], validators=[DataRequired()])
    
    effective_date = DateField('Effective Date', validators=[Optional()], 
                              description="Optional. If left blank, the system will use the earliest possible date.")
    
    recurring = BooleanField('Make Recurring Payment', default=False)
    
    recurring_frequency = SelectField('Recurring Frequency', choices=[
        ('', 'Select frequency'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly')
    ], validators=[Optional()], default='')
    
    sender_account_type = SelectField('Your Account Type', choices=[
        ('checking', 'Checking Account'),
        ('savings', 'Savings Account'),
        ('business', 'Business Account')
    ], validators=[DataRequired()], default='checking')
    
    company_entry_description = StringField('Company Entry Description', validators=[
        Optional(),
        Length(max=10, message="Description must be 10 characters or less")
    ], description="This appears on recipient's bank statement (max 10 chars)")
    
    description = TextAreaField('Payment Details', validators=[
        Optional(),
        Length(max=140, message="Description must be 140 characters or less")
    ])
    
    submit = SubmitField('Create ACH Transfer')
    
    def validate_effective_date(self, field):
        """Validate the effective date is not in the past"""
        if field.data and field.data < datetime.now().date():
            raise ValidationError("Effective date cannot be in the past")
        
        # ACH transfers typically need at least one business day for processing
        if field.data and field.data < (datetime.now() + timedelta(days=1)).date():
            raise ValidationError("Effective date must be at least 1 business day in the future")

class SwiftFreeFormatMessageForm(FlaskForm):
    """Form for creating a SWIFT MT799 free format message"""
    # Receiver Institution
    receiver_institution_id = SelectField('Receiver Institution', coerce=int, validators=[DataRequired()])
    # Specify a custom swift code if not in the dropdown
    custom_institution_name = StringField('Custom Institution Name (Optional)', validators=[Optional(), Length(max=100)])
    custom_swift_code = StringField('Custom SWIFT Code (Optional)', validators=[Optional(), Length(max=11)])
    
    # Message Details
    subject = StringField('Subject', validators=[DataRequired(), Length(max=100)])
    message_body = TextAreaField('Message Text', validators=[DataRequired()])
    
    # Beneficiary Information
    beneficiary_name = StringField('Beneficiary Name', validators=[Optional(), Length(max=100)])
    beneficiary_account = StringField('Beneficiary Account Number', validators=[Optional(), Length(max=50)])
    beneficiary_bank = StringField('Beneficiary Bank Name', validators=[Optional(), Length(max=100)])
    beneficiary_bank_swift = StringField('Beneficiary Bank SWIFT Code', validators=[Optional(), Length(max=11)])
    
    # Processing Institution Details
    processing_institution = StringField('Processing Institution', validators=[Optional(), Length(max=100)])
    
    # Reference Numbers
    reference_number = StringField('Reference Number (Optional)', validators=[Optional(), Length(max=35)])
    related_reference = StringField('Related Reference (Optional)', validators=[Optional(), Length(max=35)])
    
    submit = SubmitField('Send Free Format Message')

class SwiftMT542Form(FlaskForm):
    """Form for creating a SWIFT MT542 deliver against payment message"""
    trade_date = DateField('Trade Date', validators=[DataRequired()])
    settlement_date = DateField('Settlement Date', validators=[DataRequired()])
    security_code = StringField('Security Code (ISIN)', validators=[DataRequired()])
    security_description = StringField('Security Description', validators=[DataRequired()])
    quantity = FloatField('Quantity', validators=[DataRequired(), NumberRange(min=0.01)])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    safekeeping_account = StringField('Safekeeping Account', validators=[DataRequired()])
    delivering_agent = SelectField('Delivering Agent', coerce=int, validators=[DataRequired()])
    receiving_agent = SelectField('Receiving Agent', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create Deliver Against Payment')

class ApiAccessRequestForm(FlaskForm):
    """Form for requesting API access"""
    company_name = StringField('Company Name', validators=[DataRequired(), Length(max=100)])
    api_usage = TextAreaField('Intended API Usage', validators=[DataRequired(), Length(max=1000)])
    technical_contact_name = StringField('Technical Contact Name', validators=[DataRequired(), Length(max=100)])
    technical_contact_email = StringField('Technical Contact Email', validators=[DataRequired(), Email()])
    access_level = SelectField('Access Level Requested', choices=[
        ('read_only', 'Read Only'),
        ('standard', 'Standard - Read and Write'),
        ('advanced', 'Advanced - Full Access')
    ], validators=[DataRequired()])
    terms_agree = BooleanField('I agree to the API Terms of Service and Usage Policy', validators=[DataRequired()])
    submit = SubmitField('Submit Request')

class ApiAccessReviewForm(FlaskForm):
    """Form for admins to review API access requests"""
    status = SelectField('Status', choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], validators=[DataRequired()])
    admin_notes = TextAreaField('Admin Notes', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Update Request')

class PartnerApiKeyForm(FlaskForm):
    """Form for managing partner API keys"""
    partner_name = StringField('Partner Name', validators=[DataRequired(), Length(max=100)])
    partner_email = StringField('Partner Email', validators=[DataRequired(), Email(), Length(max=120)])
    partner_type = SelectField('Partner Type', choices=[], validators=[DataRequired()])
    key_type = SelectField('Key Type', choices=[], validators=[DataRequired()])
    access_level = SelectField('Access Level', choices=[], validators=[DataRequired()])
    expiry_date = DateField('Expiry Date', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Generate API Key')
    
    def __init__(self, *args, **kwargs):
        super(PartnerApiKeyForm, self).__init__(*args, **kwargs)
        # These would typically be populated from Enum values in the model
        self.key_type.choices = [
            ('payment', 'Payment Processing'),
            ('data', 'Data Access'),
            ('admin', 'Administrative'),
            ('integration', 'Integration')
        ]
        self.access_level.choices = [
            ('read_only', 'Read Only'),
            ('standard', 'Standard'),
            ('elevated', 'Elevated'),
            ('admin', 'Admin')
        ]
        self.partner_type.choices = [
            ('payment_processor', 'Payment Processor'),
            ('financial_institution', 'Financial Institution'),
            ('service_provider', 'Service Provider'),
            ('technology_partner', 'Technology Partner'),
            ('consultant', 'Consultant/Advisory')
        ]

class EdiPartnerForm(FlaskForm):
    """Form for creating or updating an EDI partner"""
    partner_name = StringField('Partner Name', validators=[DataRequired(), Length(max=100)])
    partner_id = StringField('Partner ID', validators=[DataRequired(), Length(max=50)])
    connection_type = SelectField('Connection Type', choices=[
        ('ftp', 'FTP'),
        ('sftp', 'SFTP'),
        ('api', 'API'),
        ('as2', 'AS2')
    ], validators=[DataRequired()])
    server_address = StringField('Server Address', validators=[Optional(), Length(max=255)])
    username = StringField('Username', validators=[Optional(), Length(max=100)])
    password = PasswordField('Password', validators=[Optional(), Length(max=100)])
    directory_path = StringField('Directory Path', validators=[Optional(), Length(max=255)])
    active = BooleanField('Active', default=True)
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save Partner')

class EDITransactionForm(FlaskForm):
    """Form for creating an EDI transaction"""
    partner_id = SelectField('EDI Partner', validators=[DataRequired()], coerce=int)
    transaction_type = SelectField('Transaction Type', choices=[
        ('850', '850 - Purchase Order'),
        ('855', '855 - Purchase Order Acknowledgment'),
        ('856', '856 - Advance Ship Notice'),
        ('810', '810 - Invoice'),
        ('820', '820 - Payment Order'),
        ('997', '997 - Functional Acknowledgment')
    ], validators=[DataRequired()])
    format = SelectField('Format', choices=[
        ('x12', 'X12'),
        ('edifact', 'EDIFACT'),
        ('xml', 'XML'),
        ('json', 'JSON')
    ], validators=[DataRequired()])
    content = TextAreaField('EDI Content', validators=[DataRequired()])
    test_mode = BooleanField('Test Mode', default=True)
    submit = SubmitField('Send Transaction')

class TreasuryAccountForm(FlaskForm):
    """Form for creating a treasury account"""
    account_name = StringField('Account Name', validators=[DataRequired(), Length(max=100)])
    account_number = StringField('Account Number', validators=[DataRequired(), Length(max=50)])
    institution_id = SelectField('Financial Institution', validators=[DataRequired()], coerce=int)
    account_type = SelectField('Account Type', choices=[
        ('OPERATING', 'Operating Account'),
        ('INVESTMENT', 'Investment Account'),
        ('RESERVE', 'Reserve Account'),
        ('PAYROLL', 'Payroll Account'),
        ('TAX', 'Tax Account'),
        ('DEBT_SERVICE', 'Debt Service Account')
    ], validators=[DataRequired()])
    currency = SelectField('Currency', choices=[
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('NVCT', 'NVC Token (NVCT)'),
        ('AFD1', 'American Federation Dollar (AFD1)'),
        ('AKLUMI', 'AK Lumi (AKLUMI)'),
        ('SFN', 'SFN Coin (SFN)'),
        ('NGN', 'Nigerian Naira (NGN)')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    current_balance = FloatField('Current Balance', validators=[Optional()])
    opening_balance = FloatField('Opening Balance', validators=[Optional()])
    target_balance = FloatField('Target Balance', validators=[Optional(), NumberRange(min=0)])
    minimum_balance = FloatField('Minimum Balance', validators=[Optional(), NumberRange(min=0)])
    maximum_balance = FloatField('Maximum Balance', validators=[Optional(), NumberRange(min=0)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Account')
    
class TreasurySettlementForm(FlaskForm):
    """Form for recording a manual settlement from a payment processor to a treasury account"""
    account_id = SelectField('Treasury Account', validators=[DataRequired()], coerce=int)
    processor_type = SelectField('Payment Processor', choices=[
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('pos', 'Point of Sale (POS)'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    reference = StringField('External Reference', validators=[Optional(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Record Settlement')

class TreasuryTransactionForm(FlaskForm):
    """Form for creating a treasury transaction"""
    transaction_date = DateField('Transaction Date', validators=[DataRequired()], default=datetime.utcnow)
    from_account_id = SelectField('From Account', validators=[DataRequired()], coerce=int)
    to_account_id = SelectField('To Account', validators=[DataRequired()], coerce=int)
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', validators=[DataRequired()], choices=[
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('NVCT', 'NVC Token (NVCT)'),
        ('AFD1', 'American Federation Dollar (AFD1)'),
        ('AKLUMI', 'AK Lumi (AKLUMI)'),
        ('SFN', 'SFN Coin (SFN)'),
        ('NGN', 'Nigerian Naira (NGN)'),
        ('CAD', 'Canadian Dollar (CAD)'),
        ('AUD', 'Australian Dollar (AUD)'),
        ('JPY', 'Japanese Yen (JPY)'),
        ('CNY', 'Chinese Yuan (CNY)'),
        ('INR', 'Indian Rupee (INR)'),
        ('BRL', 'Brazilian Real (BRL)'),
        ('ZAR', 'South African Rand (ZAR)')
    ])
    transaction_type = SelectField('Transaction Type', choices=[
        ('INTERNAL_TRANSFER', 'Internal Transfer'),
        ('EXTERNAL_TRANSFER', 'External Transfer'),
        ('INVESTMENT_PURCHASE', 'Investment Purchase'),
        ('INVESTMENT_MATURITY', 'Investment Maturity'),
        ('LOAN_PAYMENT', 'Loan Payment'),
        ('LOAN_DISBURSEMENT', 'Loan Disbursement'),
        ('INTEREST_PAYMENT', 'Interest Payment'),
        ('FEE_PAYMENT', 'Fee Payment')
    ], validators=[DataRequired()])
    reference_number = StringField('Reference Number', validators=[Optional(), Length(max=50)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    exchange_rate = FloatField('Exchange Rate', validators=[Optional(), NumberRange(min=0.00001)])
    submit = SubmitField('Create Transaction')

class TreasuryInvestmentForm(FlaskForm):
    """Form for creating a treasury investment"""
    investment_name = StringField('Investment Name', validators=[DataRequired(), Length(max=100)])
    account_id = SelectField('Account', validators=[DataRequired()], coerce=int)
    investment_type = SelectField('Investment Type', choices=[
        ('bond', 'Bond'),
        ('cd', 'Certificate of Deposit'),
        ('commercial_paper', 'Commercial Paper'),
        ('money_market', 'Money Market'),
        ('treasury_bill', 'Treasury Bill'),
        ('mutual_fund', 'Mutual Fund')
    ], validators=[DataRequired()])
    principal_amount = FloatField('Principal Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    interest_rate = FloatField('Interest Rate (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    maturity_date = DateField('Maturity Date', validators=[DataRequired()])
    institution_id = SelectField('Institution', validators=[DataRequired()], coerce=int)
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    is_auto_renewal = BooleanField('Auto Renewal', default=False)
    currency = SelectField('Currency', choices=[], validators=[DataRequired()])
    submit = SubmitField('Create Investment')
    
    def validate_maturity_date(self, field):
        """Validate maturity date is after start date"""
        if self.start_date.data and field.data <= self.start_date.data:
            raise ValidationError('Maturity date must be after start date')

class TreasuryLoanForm(FlaskForm):
    """Form for creating a treasury loan"""
    loan_name = StringField('Loan Name', validators=[DataRequired(), Length(max=100)])
    account_id = SelectField('Account', validators=[DataRequired()], coerce=int)
    loan_type = SelectField('Loan Type', choices=[
        ('term_loan', 'Term Loan'),
        ('revolving_credit', 'Revolving Credit'),
        ('bridge_loan', 'Bridge Loan'),
        ('bond', 'Bond Issuance'),
        ('commercial_paper', 'Commercial Paper')
    ], validators=[DataRequired()])
    principal_amount = FloatField('Principal Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    interest_rate = FloatField('Interest Rate (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    interest_type = SelectField('Interest Type', choices=[
        ('fixed', 'Fixed Rate'),
        ('variable', 'Variable Rate'),
        ('libor_plus', 'LIBOR Plus'),
        ('prime_plus', 'Prime Plus')
    ], validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    maturity_date = DateField('Maturity Date', validators=[DataRequired()])
    payment_frequency = SelectField('Payment Frequency', choices=[
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('at_maturity', 'At Maturity')
    ], validators=[DataRequired()])
    first_payment_date = DateField('First Payment Date', validators=[DataRequired()])
    lender_id = SelectField('Lender Institution', validators=[DataRequired()], coerce=int)
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Create Loan')
    
    def validate_maturity_date(self, field):
        """Validate maturity date is after start date"""
        if self.start_date.data and field.data <= self.start_date.data:
            raise ValidationError('Maturity date must be after start date')
            
    def validate_first_payment_date(self, field):
        """Validate first payment date is after start date"""
        if self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('First payment date must be on or after start date')
        if self.maturity_date.data and field.data > self.maturity_date.data:
            raise ValidationError('First payment date must be before maturity date')

class CashFlowForecastForm(FlaskForm):
    """Form for creating a cash flow forecast"""
    title = StringField('Forecast Title', validators=[DataRequired(), Length(max=100)])
    account_id = SelectField('Account', validators=[DataRequired()], coerce=int)
    cash_flow_direction = SelectField('Direction', choices=[
        ('inflow', 'Cash Inflow'),
        ('outflow', 'Cash Outflow')
    ], validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[Optional()])
    recurrence_type = SelectField('Recurrence', choices=[
        ('one_time', 'One Time'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    confidence_level = SelectField('Confidence Level', choices=[
        ('high', 'High (90-100%)'),
        ('medium', 'Medium (50-90%)'),
        ('low', 'Low (0-50%)')
    ], validators=[DataRequired()])
    currency = SelectField('Currency', choices=[], validators=[DataRequired()])
    submit = SubmitField('Create Forecast')

class LoanPaymentForm(FlaskForm):
    """Form for making a loan payment"""
    from_account_id = SelectField('From Account', validators=[DataRequired()], coerce=int)
    payment_amount = FloatField('Payment Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    payment_date = DateField('Payment Date', validators=[DataRequired()], default=datetime.utcnow)
    principal_amount = FloatField('Principal Amount', validators=[Optional()], render_kw={'readonly': True})
    interest_amount = FloatField('Interest Amount', validators=[Optional()], render_kw={'readonly': True})
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Make Payment')


class PayPalPaymentForm(FlaskForm):
    """Form for making a PayPal payment"""
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=get_currency_choices, validators=[DataRequired()])
    recipient_email = StringField('Recipient Email', validators=[DataRequired(), Email()])
    description = TextAreaField('Payment Description', validators=[DataRequired(), Length(max=127)])
    notes = TextAreaField('Notes (for your records only)', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Continue to PayPal')


class PayPalPayoutForm(FlaskForm):
    """Form for creating a PayPal payout"""
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=get_currency_choices, validators=[DataRequired()])
    recipient_email = StringField('Recipient Email', validators=[DataRequired(), Email()])
    note = TextAreaField('Note to Recipient', validators=[DataRequired(), Length(max=127)])
    email_subject = StringField('Email Subject', validators=[Optional(), Length(max=255)])
    email_message = TextAreaField('Email Message', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Send Payout')


class POSPaymentForm(FlaskForm):
    """Form for accepting a credit card payment via POS system"""
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=[
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('NVCT', 'NVC Token (NVCT)'),
        ('AFD1', 'American Federation Dollar (AFD1)'),
        ('AKLUMI', 'AK Lumi (AKLUMI)'),
        ('SFN', 'SFN Coin (SFN)'),
        ('NGN', 'Nigerian Naira (NGN)')
    ], validators=[DataRequired()])
    customer_name = StringField('Customer Name', validators=[DataRequired(), Length(max=100)])
    customer_email = StringField('Customer Email', validators=[Optional(), Email()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Continue to Payment')


class POSPayoutForm(FlaskForm):
    """Form for sending money to a card via POS system"""
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=[
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('NVCT', 'NVC Token (NVCT)'),
        ('AFD1', 'American Federation Dollar (AFD1)'),
        ('AKLUMI', 'AK Lumi (AKLUMI)'),
        ('SFN', 'SFN Coin (SFN)'),
        ('NGN', 'Nigerian Naira (NGN)')
    ], validators=[DataRequired()])
    recipient_name = StringField('Recipient Name', validators=[DataRequired(), Length(max=100)])
    recipient_email = StringField('Recipient Email', validators=[Optional(), Email()])
    card_last4 = StringField('Last 4 digits of card', validators=[
        DataRequired(), 
        Length(min=4, max=4), 
        Regexp('^[0-9]{4}$', message='Last 4 digits must be exactly 4 numbers')
    ])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Send Money')


class POSTransactionFilterForm(FlaskForm):
    """Form for filtering POS transactions"""
    date_from = DateField('From Date', format='%Y-%m-%d', validators=[Optional()])
    date_to = DateField('To Date', format='%Y-%m-%d', validators=[Optional()])
    transaction_type = SelectField('Transaction Type', choices=[
        ('', 'All Types'),
        ('PAYMENT', 'All Transactions')
    ], validators=[Optional()])
    status = SelectField('Status', choices=[
        ('', 'All Statuses'),
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled')
    ], validators=[Optional()])
    min_amount = FloatField('Min Amount', validators=[Optional(), NumberRange(min=0)])
    max_amount = FloatField('Max Amount', validators=[Optional(), NumberRange(min=0)])
    currency = SelectField('Currency', choices=[
        ('', 'All Currencies'),
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('NVCT', 'NVC Token (NVCT)'),
        ('AFD1', 'American Federation Dollar (AFD1)'),
        ('AKLUMI', 'AK Lumi (AKLUMI)'),
        ('SFN', 'SFN Coin (SFN)'),
        ('NGN', 'Nigerian Naira (NGN)')
    ], validators=[Optional()])
    search = StringField('Search', validators=[Optional()])
    submit = SubmitField('Filter')