from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, PasswordField, BooleanField, FloatField, SubmitField, HiddenField, DateField, RadioField, IntegerField, MultipleFileField, SelectMultipleField, widgets
from models import TransactionType
from wtforms.validators import DataRequired, Length, Optional, Email, EqualTo, NumberRange, ValidationError, Regexp, URL
from datetime import datetime, timedelta
import json

def get_currency_choices():
    """Get list of supported currencies"""
    return [
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'), 
        ('GBP', 'GBP - British Pound'),
        ('JPY', 'JPY - Japanese Yen'),
        ('CHF', 'CHF - Swiss Franc'),
        ('CNY', 'CNY - Chinese Yuan'),
        ('AUD', 'AUD - Australian Dollar'),
        ('CAD', 'CAD - Canadian Dollar')
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

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

    # Optional personal information fields
    first_name = StringField('First Name', validators=[Optional()])
    last_name = StringField('Last Name', validators=[Optional()])
    organization = StringField('Organization/Company', validators=[Optional()])
    country = StringField('Country', validators=[Optional()])
    phone = StringField('Phone Number', validators=[Optional()])

    # Terms and newsletter
    terms_agree = BooleanField('I agree to the Terms of Service and Privacy Policy', validators=[DataRequired()])
    newsletter = BooleanField('Subscribe to newsletter', validators=[Optional()])

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

class BankTransferForm(FlaskForm):
    transaction_id = HiddenField('Transaction ID', validators=[Optional()])

    # Recipient information fields
    recipient_name = StringField('Recipient Name', validators=[DataRequired()])
    recipient_email = StringField('Email Address', validators=[Optional(), Email()])
    recipient_address = TextAreaField('Street Address', validators=[DataRequired()])
    recipient_city = StringField('City', validators=[DataRequired()])
    recipient_state = StringField('State/Province', validators=[Optional()])
    recipient_zip = StringField('ZIP/Postal Code', validators=[DataRequired()])
    recipient_country = StringField('Country', validators=[DataRequired()])
    recipient_phone = StringField('Phone Number', validators=[Optional()])
    recipient_tax_id = StringField('Tax ID/VAT Number', validators=[Optional()])

    # Enhanced beneficiary information for regulatory compliance
    recipient_institution_type = SelectField('Institution Type', choices=[
        ('individual', 'Individual'),
        ('business', 'Business'),
        ('government', 'Government Agency'),
        ('nonprofit', 'Non-profit Organization'),
        ('financial', 'Financial Institution')
    ], default='individual', validators=[DataRequired()])
    recipient_relationship = SelectField('Relationship to Recipient', choices=[
        ('self', 'Self'),
        ('family', 'Family Member'),
        ('business', 'Business Partner'),
        ('vendor', 'Vendor/Supplier'),
        ('client', 'Client/Customer'),
        ('employee', 'Employee'),
        ('other', 'Other')
    ], validators=[Optional()])

    # Bank account information fields
    bank_name = StringField('Bank Name', validators=[DataRequired()])
    account_holder = StringField('Account Holder Name', validators=[DataRequired()])
    account_number = StringField('Account Number', validators=[DataRequired()])
    account_type = SelectField('Account Type', choices=[
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('business', 'Business'),
        ('investment', 'Investment'),
        ('money_market', 'Money Market'),
        ('loan', 'Loan Account'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    transfer_type = SelectField('Transfer Type', choices=[
        ('domestic', 'Domestic'),
        ('international', 'International')
    ], default='domestic', validators=[DataRequired()])
    routing_number = StringField('Routing Number (ABA)', validators=[Optional()])
    swift_bic = StringField('SWIFT/BIC Code', validators=[Optional()])
    iban = StringField('IBAN', validators=[Optional()])
    bank_address = TextAreaField('Bank Address', validators=[DataRequired()])
    bank_city = StringField('City', validators=[DataRequired()])
    bank_state = StringField('State/Province', validators=[Optional()])
    bank_country = StringField('Country', validators=[DataRequired()])
    bank_branch_code = StringField('Branch Code', validators=[Optional()])
    bank_branch_name = StringField('Branch Name', validators=[Optional()])

    # International transfer fields
    currency = SelectField('Currency', choices=[
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound'),
        ('JPY', 'JPY - Japanese Yen'),
        ('CAD', 'CAD - Canadian Dollar'),
        ('AUD', 'AUD - Australian Dollar'),
        ('CHF', 'CHF - Swiss Franc'),
        ('CNY', 'CNY - Chinese Yuan'),
        ('HKD', 'HKD - Hong Kong Dollar'),
        ('SGD', 'SGD - Singapore Dollar'),
        ('INR', 'INR - Indian Rupee'),
        ('ZAR', 'ZAR - South African Rand')
    ], default='USD', validators=[Optional()])
    purpose = SelectField('Purpose of Payment', choices=[
        ('business', 'Business Services'),
        ('personal', 'Personal Transfer'),
        ('property', 'Property Purchase'),
        ('investment', 'Investment'),
        ('education', 'Education'),
        ('medical', 'Medical Expenses'),
        ('tax', 'Tax Payment'),
        ('legal', 'Legal Services'),
        ('consultation', 'Professional Consultation'),
        ('charitable', 'Charitable Donation'),
        ('goods', 'Goods Purchase'),
        ('services', 'Services Payment'),
        ('loan', 'Loan Repayment'),
        ('dividend', 'Dividend Payment'),
        ('salary', 'Salary/Wages'),
        ('other', 'Other (Please Specify)')
    ], validators=[Optional()])
    purpose_detail = StringField('Purpose Details', validators=[Optional()])
    intermediary_bank = StringField('Intermediary Bank', validators=[Optional()])
    intermediary_swift = StringField('Intermediary SWIFT Code', validators=[Optional()])

    # Settlement information
    settlement_method = SelectField('Settlement Method', choices=[
        ('standard', 'Standard (3-5 business days)'),
        ('express', 'Express (1-2 business days)'),
        ('same_day', 'Same Day (where available)'),
        ('wire', 'Wire Transfer'),
        ('ach', 'ACH Transfer'),
        ('rtgs', 'RTGS')
    ], default='standard', validators=[Optional()])
    charge_bearer = SelectField('Fee Payment Option', choices=[
        ('OUR', 'Sender pays all fees (OUR)'),
        ('SHA', 'Shared fees (SHA)'),
        ('BEN', 'Recipient pays all fees (BEN)')
    ], default='SHA', validators=[Optional()])

    # Compliance and regulatory information
    source_of_funds = SelectField('Source of Funds', choices=[
        ('salary', 'Salary/Employment Income'),
        ('business', 'Business Revenue'),
        ('investment', 'Investment Returns'),
        ('savings', 'Personal Savings'),
        ('loan', 'Loan Proceeds'),
        ('gift', 'Gift'),
        ('sale', 'Sale of Asset'),
        ('inheritance', 'Inheritance'),
        ('other', 'Other (Please Specify)')
    ], validators=[Optional()])
    source_of_funds_detail = StringField('Source of Funds Details', validators=[Optional()])

    # Reference information
    reference = StringField('Payment Reference', validators=[Optional()])
    invoice_number = StringField('Invoice Number', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    notes_to_recipient = TextAreaField('Notes to Recipient', validators=[Optional()])
    notes_to_bank = TextAreaField('Instructions to Bank', validators=[Optional()])

    # Terms agreement
    terms_agree = BooleanField('I agree to the terms', validators=[DataRequired()])
    compliance_agree = BooleanField('I confirm this transaction complies with all applicable laws', validators=[DataRequired()])

    amount = HiddenField('Amount')

    def populate_from_stored_data(self, stored_data):
        """Populate form from stored JSON data"""
        if not stored_data:
            return

        try:
            data = json.loads(stored_data)
            for field_name, field_value in data.items():
                if hasattr(self, field_name) and field_name != 'csrf_token':
                    field = getattr(self, field_name)
                    field.data = field_value
        except Exception as e:
            print(f"Error populating form: {str(e)}")


class SwiftFundTransferForm(FlaskForm):
    """Form for SWIFT fund transfer (MT103) message"""
    sender_institution_id = SelectField('Sending Institution', coerce=int, validators=[DataRequired()])
    receiver_institution_id = SelectField('Receiving Institution', coerce=int, validators=[DataRequired()])
    receiver_institution_name = StringField('Receiving Institution Name', validators=[Length(max=140)])
    is_financial_institution = RadioField('Transfer Type', choices=[
        ('0', 'Customer Transfer (MT103)'), 
        ('1', 'Financial Institution Transfer (MT202)')
    ], default='0')
    transaction_reference = StringField('Transaction Reference', validators=[DataRequired(), Length(min=8, max=16)])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=[
        ('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('CHF', 'CHF'), 
        ('JPY', 'JPY'), ('CNY', 'CNY'), ('CAD', 'CAD'), ('AUD', 'AUD')
    ], validators=[DataRequired()])
    
    # Bank Information
    receiving_bank_name = StringField('Receiving Bank Name', validators=[Length(max=140)])
    receiving_bank_address = TextAreaField('Receiving Bank Address', validators=[Length(max=200)])
    receiving_bank_swift = StringField('Receiving Bank SWIFT/BIC', validators=[Length(max=11)])
    receiving_bank_routing = StringField('Receiving Bank Routing Number', validators=[Length(max=35)])
    
    # Account Holder Details
    account_holder_name = StringField('Account Holder Name', validators=[Length(max=140)])
    account_number = StringField('Account Number/IBAN', validators=[Length(max=35)])
    
    # Correspondent & Intermediary Banks
    correspondent_bank_name = StringField('Correspondent Bank Name', validators=[Length(max=140)])
    correspondent_bank_swift = StringField('Correspondent Bank SWIFT/BIC', validators=[Length(max=11)])
    intermediary_bank_name = StringField('Intermediary Bank Name', validators=[Length(max=140)])
    intermediary_bank_swift = StringField('Intermediary Bank SWIFT/BIC', validators=[Length(max=11)])
    
    # Ordering Customer information
    ordering_customer = TextAreaField('Sender Details', validators=[Length(max=140)])
    ordering_customer_account = StringField('Ordering Customer Account', validators=[Length(max=35)])
    ordering_customer_name = StringField('Ordering Customer Name', validators=[Length(max=35)])
    ordering_customer_address = TextAreaField('Ordering Customer Address', validators=[Length(max=140)])
    
    # Beneficiary information
    beneficiary_customer = TextAreaField('Beneficiary Details', validators=[Length(max=140)])
    beneficiary_account = StringField('Beneficiary Account', validators=[Length(max=35)])
    beneficiary_name = StringField('Beneficiary Name', validators=[Length(max=35)])
    beneficiary_address = TextAreaField('Beneficiary Address', validators=[Length(max=140)])
    
    # Details of Payment (field 70)
    details_of_payment = TextAreaField('Payment Details', validators=[Length(max=140)])
    
    # Older field names for backward compatibility
    payment_details = TextAreaField('Payment Details', validators=[DataRequired(), Length(max=140)])
    
    # Charges (field 71A)
    charges = SelectField('Charges', choices=[
        ('OUR', 'OUR - All charges paid by the sender'),
        ('SHA', 'SHA - Shared charges'),
        ('BEN', 'BEN - All charges paid by the beneficiary')
    ], validators=[DataRequired()])
    
    submit = SubmitField('Submit SWIFT Transfer')
    
    def __init__(self, *args, **kwargs):
        super(SwiftFundTransferForm, self).__init__(*args, **kwargs)
        try:
            from models import FinancialInstitution
            # Use is_active instead of active for the filter
            institutions = FinancialInstitution.query.filter_by(is_active=True).all()
            self.sender_institution_id.choices = [(i.id, i.name) for i in institutions]
            self.receiver_institution_id.choices = [(i.id, i.name) for i in institutions]
        except Exception as e:
            print(f"Error populating Swift transfer form: {str(e)}")
            # Provide default empty list
            self.sender_institution_id.choices = [(1, 'Default Institution')]
            self.receiver_institution_id.choices = [(1, 'Default Institution')]


class SwiftFreeFormatMessageForm(FlaskForm):
    """Form for SWIFT free format message (MT999)"""
    sender_institution_id = SelectField('Sending Institution', coerce=int, validators=[DataRequired()])
    receiver_institution_id = SelectField('Receiving Institution', coerce=int, validators=[DataRequired()])
    transaction_reference = StringField('Transaction Reference', validators=[DataRequired(), Length(min=8, max=16)])
    
    # Message Text (field 79)
    message_text = TextAreaField('Message Text', validators=[DataRequired(), Length(max=1800)])
    
    submit = SubmitField('Send Free Format Message')
    
    def __init__(self, *args, **kwargs):
        super(SwiftFreeFormatMessageForm, self).__init__(*args, **kwargs)
        try:
            from models import FinancialInstitution
            institutions = FinancialInstitution.query.filter_by(active=True).all()
            self.sender_institution_id.choices = [(i.id, i.name) for i in institutions]
            self.receiver_institution_id.choices = [(i.id, i.name) for i in institutions]
        except Exception as e:
            print(f"Error populating Swift message form: {str(e)}")


class ACHTransferForm(FlaskForm):
    """Form for ACH transfers within the US banking system"""
    # Sender information
    sender_account_type = SelectField('Sender Account Type', choices=[
        ('checking', 'Checking Account'),
        ('savings', 'Savings Account'),
        ('business', 'Business Account')
    ], validators=[DataRequired()])
    
    # Recipient information
    recipient_name = StringField('Recipient Name', validators=[DataRequired(), Length(min=2, max=100)])
    recipient_address_line1 = StringField('Address Line 1', validators=[DataRequired(), Length(max=100)])
    recipient_address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=100)])
    recipient_city = StringField('City', validators=[DataRequired(), Length(max=100)])
    recipient_state = StringField('State', validators=[DataRequired(), Length(max=2)])
    recipient_zip = StringField('ZIP Code', validators=[DataRequired(), Length(min=5, max=10)])
    
    # Bank information
    recipient_bank_name = StringField('Bank Name', validators=[DataRequired(), Length(max=100)])
    recipient_bank_address = StringField('Bank Address', validators=[Optional(), Length(max=200)])
    recipient_account_type = SelectField('Account Type', choices=[
        ('checking', 'Checking Account'),
        ('savings', 'Savings Account'),
        ('business', 'Business Account')
    ], validators=[DataRequired()])
    recipient_routing_number = StringField('Routing Number (ABA)', validators=[
        DataRequired(), 
        Length(min=9, max=9),
        # Digit-only validator
        Regexp(r'^\d+$', message="Routing number must contain only digits")
    ])
    recipient_account_number = StringField('Account Number', validators=[
        DataRequired(),
        Length(min=4, max=17),
        # Digit-only validator
        Regexp(r'^\d+$', message="Account number must contain only digits")
    ])
    
    # Transaction details
    amount = FloatField('Amount (USD)', validators=[DataRequired(), NumberRange(min=0.01)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=140)])
    
    # ACH specific fields
    entry_class_code = SelectField('Entry Class Code', choices=[
        ('PPD', 'PPD - Personal Payment'),
        ('CCD', 'CCD - Corporate Credit or Debit'),
        ('WEB', 'WEB - Internet Initiated Entry'),
        ('TEL', 'TEL - Telephone Initiated Entry'),
        ('IAT', 'IAT - International ACH Transaction')
    ], default='PPD', validators=[DataRequired()])
    company_entry_description = StringField('Company Entry Description', validators=[Optional(), Length(max=10)])
    effective_date = DateField('Effective Date', validators=[Optional()], format='%Y-%m-%d')
    
    # Recurring options
    recurring = BooleanField('Set as Recurring Payment', default=False)
    recurring_frequency = SelectField('Frequency', choices=[
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly')
    ], validators=[Optional()])
    
    # Terms agreement
    agree_terms = BooleanField('I confirm this information is correct and authorize this transfer', validators=[DataRequired()])
    
    submit = SubmitField('Submit ACH Transfer')
    
    def __init__(self, *args, **kwargs):
        super(ACHTransferForm, self).__init__(*args, **kwargs)
        # Set default effective date to next business day
        if not self.effective_date.data:
            next_business_day = datetime.now() + timedelta(days=1)
            # If next business day is weekend, move to Monday
            if next_business_day.weekday() >= 5:  # 5=Saturday, 6=Sunday
                next_business_day += timedelta(days=7 - next_business_day.weekday())
            self.effective_date.data = next_business_day


class ApiAccessRequestForm(FlaskForm):
    """Form for API access request"""
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=2, max=100)])
    website = StringField('Website', validators=[DataRequired(), URL()])
    contact_name = StringField('Contact Name', validators=[DataRequired(), Length(min=2, max=100)])
    contact_email = StringField('Contact Email', validators=[DataRequired(), Email()])
    contact_phone = StringField('Contact Phone', validators=[DataRequired(), Length(min=10, max=20)])
    
    # API access details
    access_reason = TextAreaField('Reason for API Access', validators=[DataRequired(), Length(min=20, max=1000)])
    intended_use = TextAreaField('Intended Use', validators=[DataRequired(), Length(min=20, max=1000)])
    expected_volume = SelectField('Expected Transaction Volume (monthly)', choices=[
        ('', '-- Select --'),
        ('low', 'Low (< 1,000 transactions)'),
        ('medium', 'Medium (1,000 - 10,000 transactions)'),
        ('high', 'High (10,000 - 100,000 transactions)'),
        ('very_high', 'Very High (> 100,000 transactions)')
    ], validators=[DataRequired()])
    
    # Technical contact
    technical_contact_name = StringField('Technical Contact Name', validators=[DataRequired(), Length(min=2, max=100)])
    technical_contact_email = StringField('Technical Contact Email', validators=[DataRequired(), Email()])
    
    # API endpoints
    api_endpoints = SelectMultipleField('Required API Endpoints', choices=[
        ('payments', 'Payment Processing'),
        ('accounts', 'Account Information'),
        ('transfers', 'Fund Transfers'),
        ('custody', 'Custody Services'),
        ('exchange', 'Currency Exchange'),
        ('blockchain', 'Blockchain Integration')
    ], validators=[DataRequired()])
    
    # Security
    ip_addresses = TextAreaField('IP Addresses (one per line)', validators=[DataRequired(), Length(min=7, max=1000)])
    
    # Agreement
    terms_agree = BooleanField('I agree to the API Terms of Service and Privacy Policy', validators=[DataRequired()])
    
    submit = SubmitField('Submit Request')


class PartnerApiKeyForm(FlaskForm):
    """Form for managing partner API keys"""
    partner_id = SelectField('Partner', coerce=int, validators=[DataRequired()])
    api_key_type = SelectField('API Key Type', choices=[
        ('read', 'Read Only'),
        ('write', 'Read & Write'),
        ('admin', 'Administrative')
    ], validators=[DataRequired()])
    
    expiration_date = DateField('Expiration Date', format='%Y-%m-%d', validators=[Optional()])
    
    rate_limit = IntegerField('Rate Limit (requests per minute)', 
                            validators=[DataRequired(), NumberRange(min=1, max=10000)],
                            default=60)
    
    daily_limit = IntegerField('Daily Limit (requests)', 
                            validators=[DataRequired(), NumberRange(min=1, max=1000000)],
                            default=10000)
    
    ip_restriction = BooleanField('Enable IP Restriction', default=False)
    allowed_ips = TextAreaField('Allowed IP Addresses (one per line)', validators=[Optional()])
    
    enabled = BooleanField('Enabled', default=True)
    
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    
    submit = SubmitField('Generate API Key')
    
    def __init__(self, *args, **kwargs):
        super(PartnerApiKeyForm, self).__init__(*args, **kwargs)
        try:
            from models import Partner
            partners = Partner.query.filter_by(active=True).order_by(Partner.name).all()
            self.partner_id.choices = [(p.id, p.name) for p in partners]
            
            # Set default expiration date to 1 year from today
            if not self.expiration_date.data:
                self.expiration_date.data = datetime.now() + timedelta(days=365)
        except Exception as e:
            print(f"Error populating partner list: {str(e)}")


class NVCPlatformSettingsForm(FlaskForm):
    """Form for platform settings"""
    platform_name = StringField('Platform Name', validators=[DataRequired(), Length(min=3, max=50)])
    support_email = StringField('Support Email', validators=[DataRequired(), Email()])
    admin_email = StringField('Admin Email', validators=[DataRequired(), Email()])
    
    # Transaction settings
    min_transaction_amount = DecimalField('Minimum Transaction Amount', 
                                        validators=[DataRequired(), NumberRange(min=0)],
                                        default=0.01)
    
    max_transaction_amount = DecimalField('Maximum Transaction Amount', 
                                        validators=[DataRequired(), NumberRange(min=1)],
                                        default=1000000.00)
    
    default_transaction_fee = DecimalField('Default Transaction Fee (%)', 
                                        validators=[DataRequired(), NumberRange(min=0, max=100)],
                                        default=1.5)
    
    # Blockchain settings
    gas_price_buffer = IntegerField('Gas Price Buffer (%)', 
                                 validators=[DataRequired(), NumberRange(min=0, max=200)],
                                 default=20)
    
    # Security settings
    session_timeout = IntegerField('Session Timeout (minutes)', 
                                validators=[DataRequired(), NumberRange(min=5, max=1440)],
                                default=60)
    
    failed_login_attempts = IntegerField('Max Failed Login Attempts', 
                                      validators=[DataRequired(), NumberRange(min=3, max=10)],
                                      default=5)
    
    # Email settings
    enable_email_notifications = BooleanField('Enable Email Notifications', default=True)
    
    # Maintenance mode
    maintenance_mode = BooleanField('Maintenance Mode', default=False)
    maintenance_message = TextAreaField('Maintenance Message', validators=[Optional(), Length(max=500)])
    
    submit = SubmitField('Save Settings')


class EdiPartnerForm(FlaskForm):
    """Form for managing EDI partners"""
    partner_name = StringField('Partner Name', validators=[DataRequired(), Length(min=2, max=100)])
    partner_code = StringField('Partner Code', validators=[DataRequired(), Length(min=2, max=20)])
    
    # Connection details
    connection_type = SelectField('Connection Type', choices=[
        ('ftp', 'FTP/SFTP'),
        ('api', 'API/Web Service'),
        ('as2', 'AS2'),
        ('email', 'Email')
    ], validators=[DataRequired()])
    
    host = StringField('Host/Server', validators=[Optional(), Length(max=255)])
    port = IntegerField('Port', validators=[Optional(), NumberRange(min=1, max=65535)])
    username = StringField('Username', validators=[Optional(), Length(max=100)])
    password = PasswordField('Password', validators=[Optional(), Length(max=100)])
    
    # File settings
    inbound_directory = StringField('Inbound Directory', validators=[Optional(), Length(max=255)])
    outbound_directory = StringField('Outbound Directory', validators=[Optional(), Length(max=255)])
    file_pattern = StringField('File Pattern', validators=[Optional(), Length(max=100)])
    
    # Processing options
    auto_process = BooleanField('Auto Process', default=True)
    processing_interval = IntegerField('Processing Interval (minutes)', validators=[Optional(), NumberRange(min=1, max=1440)])
    
    # EDI Standards
    edi_standard = SelectField('EDI Standard', choices=[
        ('x12', 'ANSI X12'),
        ('edifact', 'UN/EDIFACT'),
        ('tradacoms', 'TRADACOMS'),
        ('proprietary', 'Proprietary Format')
    ], validators=[DataRequired()])
    
    # Contact information
    contact_name = StringField('Contact Name', validators=[Optional(), Length(max=100)])
    contact_email = StringField('Contact Email', validators=[Optional(), Email()])
    contact_phone = StringField('Contact Phone', validators=[Optional(), Length(max=20)])
    
    active = BooleanField('Active', default=True)
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    
    submit = SubmitField('Save Partner')


class TreasuryAccountForm(FlaskForm):
    """Form for creating or updating a Treasury Account"""
    name = StringField('Account Name', validators=[DataRequired(), Length(min=3, max=100)])
    account_name = StringField('Account Name', validators=[DataRequired(), Length(min=3, max=100)])  # Duplicate to match template
    account_type = SelectField('Account Type', coerce=str, validators=[DataRequired()])
    institution_id = SelectField('Financial Institution', coerce=int, validators=[DataRequired()])
    account_number = StringField('Account Number', validators=[DataRequired(), Length(min=5, max=50)])
    routing_number = StringField('Routing Number', validators=[Optional(), Length(min=9, max=9)])
    swift_code = StringField('SWIFT Code', validators=[Optional(), Length(min=8, max=11)])
    iban = StringField('IBAN', validators=[Optional(), Length(min=15, max=34)])
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    initial_balance = DecimalField('Initial Balance', validators=[DataRequired(), NumberRange(min=0)], default=0.0)
    opening_balance = DecimalField('Opening Balance', validators=[DataRequired(), NumberRange(min=0)], default=0.0)  # Duplicate to match template
    credit_limit = DecimalField('Credit Limit', validators=[Optional(), NumberRange(min=0)], default=0.0)
    target_balance = DecimalField('Target Balance', validators=[Optional(), NumberRange(min=0)], default=0.0)
    minimum_balance = DecimalField('Minimum Balance', validators=[Optional(), NumberRange(min=0)], default=0.0)
    maximum_balance = DecimalField('Maximum Balance', validators=[Optional(), NumberRange(min=0)], default=0.0)
    is_active = BooleanField('Active', default=True)
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])  # Duplicate to match template
    submit = SubmitField('Save Account')

    def __init__(self, *args, **kwargs):
        super(TreasuryAccountForm, self).__init__(*args, **kwargs)
        try:
            from models import TreasuryAccountType, FinancialInstitution
            # Use enum values directly for account types
            self.account_type.choices = [
                (TreasuryAccountType.OPERATING.value, 'Operating Account'),
                (TreasuryAccountType.INVESTMENT.value, 'Investment Account'),
                (TreasuryAccountType.RESERVE.value, 'Reserve Account'),
                (TreasuryAccountType.PAYROLL.value, 'Payroll Account'),
                (TreasuryAccountType.TAX.value, 'Tax Account'),
                (TreasuryAccountType.DEBT_SERVICE.value, 'Debt Service Account')
            ]
            self.institution_id.choices = [(i.id, i.name) for i in 
                                         FinancialInstitution.query.filter_by(is_active=True).order_by(FinancialInstitution.name).all()]
        except Exception as e:
            print(f"Error loading form data: {str(e)}")


class TreasuryTransactionForm(FlaskForm):
    """Form for creating a Treasury transaction"""
    transaction_type = SelectField('Transaction Type', coerce=str, validators=[DataRequired()])
    source_account_id = SelectField('Source Account', coerce=int, validators=[DataRequired()])
    destination_account_id = SelectField('Destination Account', coerce=int, validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=0.0)
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    exchange_rate = DecimalField('Exchange Rate', validators=[Optional(), NumberRange(min=0.000001)], default=1.0)
    value_date = DateField('Value Date', format='%Y-%m-%d', validators=[DataRequired()])
    reference = StringField('Reference', validators=[DataRequired(), Length(min=3, max=50)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    metadata = TextAreaField('Metadata (JSON)', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Execute Transaction')

    def __init__(self, *args, **kwargs):
        super(TreasuryTransactionForm, self).__init__(*args, **kwargs)
        try:
            from models import TreasuryTransactionType, TreasuryAccount
            # Use enum values directly for transaction types
            self.transaction_type.choices = [
                (TreasuryTransactionType.INTERNAL_TRANSFER.value, 'Internal Transfer'),
                (TreasuryTransactionType.EXTERNAL_TRANSFER.value, 'External Transfer'),
                (TreasuryTransactionType.INVESTMENT_PURCHASE.value, 'Investment Purchase'),
                (TreasuryTransactionType.INVESTMENT_MATURITY.value, 'Investment Maturity'),
                (TreasuryTransactionType.LOAN_PAYMENT.value, 'Loan Payment'),
                (TreasuryTransactionType.LOAN_DISBURSEMENT.value, 'Loan Disbursement'),
                (TreasuryTransactionType.INTEREST_PAYMENT.value, 'Interest Payment'),
                (TreasuryTransactionType.FEE_PAYMENT.value, 'Fee Payment')
            ]
            accounts = TreasuryAccount.query.filter_by(is_active=True).all()
            self.source_account_id.choices = [(a.id, f"{a.name} ({a.currency})") for a in accounts]
            self.destination_account_id.choices = [(a.id, f"{a.name} ({a.currency})") for a in accounts]
            
            # Set default value date to today
            if not self.value_date.data:
                self.value_date.data = datetime.now().date()
        except Exception as e:
            print(f"Error loading form data: {str(e)}")


class TreasuryInvestmentForm(FlaskForm):
    """Form for creating or updating a Treasury Investment"""
    account_id = SelectField('Treasury Account', coerce=int, validators=[DataRequired()])
    investment_type = SelectField('Investment Type', coerce=str, validators=[DataRequired()])
    institution_id = SelectField('Financial Institution', coerce=int, validators=[DataRequired()])
    name = StringField('Investment Name', validators=[DataRequired(), Length(min=3, max=100)])
    investment_name = StringField('Investment Name', validators=[DataRequired(), Length(min=3, max=100)])  # Duplicate to match template
    amount = DecimalField('Investment Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=0.0)
    principal_amount = DecimalField('Principal Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=0.0)  # Duplicate to match template
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    interest_rate = DecimalField('Interest Rate (%)', validators=[DataRequired(), NumberRange(min=0)], default=0.0)
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    maturity_date = DateField('Maturity Date', format='%Y-%m-%d', validators=[Optional()])
    term_days = IntegerField('Term (Days)', validators=[Optional(), NumberRange(min=1)], default=0)
    auto_renew = BooleanField('Auto Renew', default=False)
    counterparty = StringField('Counterparty', validators=[Optional(), Length(max=100)])
    risk_rating = SelectField('Risk Rating', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])  # Added to match template
    submit = SubmitField('Save Investment')

    def __init__(self, *args, **kwargs):
        super(TreasuryInvestmentForm, self).__init__(*args, **kwargs)
        try:
            from models import TreasuryAccount, InvestmentType, FinancialInstitution
            accounts = TreasuryAccount.query.filter_by(is_active=True).all()
            self.account_id.choices = [(a.id, f"{a.name} ({a.currency})") for a in accounts]
            
            institutions = FinancialInstitution.query.filter_by(is_active=True).order_by(FinancialInstitution.name).all()
            self.institution_id.choices = [(i.id, i.name) for i in institutions]
            # Investment type is an Enum, not a database model, so we handle it differently
            self.investment_type.choices = [
                (InvestmentType.CERTIFICATE_OF_DEPOSIT.value, 'Certificate of Deposit'),
                (InvestmentType.MONEY_MARKET.value, 'Money Market'),
                (InvestmentType.TREASURY_BILL.value, 'Treasury Bill'),
                (InvestmentType.BOND.value, 'Bond'),
                (InvestmentType.COMMERCIAL_PAPER.value, 'Commercial Paper'),
                (InvestmentType.OVERNIGHT_INVESTMENT.value, 'Overnight Investment'),
                (InvestmentType.TIME_DEPOSIT.value, 'Time Deposit')
            ]
            
            # Set default start date to today
            if not self.start_date.data:
                self.start_date.data = datetime.now().date()
                
            # Calculate maturity date based on term days if provided
            if self.term_days.data and self.term_days.data > 0 and self.start_date.data:
                self.maturity_date.data = self.start_date.data + timedelta(days=self.term_days.data)
        except Exception as e:
            print(f"Error loading form data: {str(e)}")


class TreasuryLoanForm(FlaskForm):
    """Form for creating or updating a Treasury Loan"""
    account_id = SelectField('Treasury Account', coerce=int, validators=[DataRequired()])
    loan_type = SelectField('Loan Type', coerce=str, validators=[DataRequired()])
    name = StringField('Loan Name', validators=[DataRequired(), Length(min=3, max=100)])
    principal_amount = DecimalField('Principal Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=0.0)
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    interest_type = SelectField('Interest Type', coerce=str, validators=[DataRequired()])
    interest_rate = DecimalField('Interest Rate (%)', validators=[DataRequired(), NumberRange(min=0)], default=0.0)
    reference_rate = StringField('Reference Rate', validators=[Optional(), Length(max=64)])
    margin = DecimalField('Margin (%)', validators=[Optional(), NumberRange(min=0)], default=0.0)
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    maturity_date = DateField('Maturity Date', format='%Y-%m-%d', validators=[DataRequired()])
    payment_frequency = SelectField('Payment Frequency', choices=[
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('bullet', 'Bullet (At Maturity)')
    ], validators=[DataRequired()])
    first_payment_date = DateField('First Payment Date', format='%Y-%m-%d', validators=[Optional()])
    payment_amount = DecimalField('Payment Amount', validators=[Optional(), NumberRange(min=0)], default=0.0)
    num_payments = IntegerField('Number of Payments', validators=[Optional(), NumberRange(min=1)], default=0)
    prepayment_penalty = DecimalField('Prepayment Penalty (%)', validators=[Optional(), NumberRange(min=0, max=100)], default=0.0)
    collateral = TextAreaField('Collateral Description', validators=[Optional(), Length(max=500)])
    collateral_description = TextAreaField('Additional Collateral Details', validators=[Optional(), Length(max=500)])
    borrower = StringField('Borrower', validators=[Optional(), Length(max=100)])
    lender = StringField('Lender', validators=[Optional(), Length(max=100)])
    lender_institution_id = SelectField('Lender Institution', coerce=int, validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    loan_id = StringField('Loan ID', validators=[Optional(), Length(max=64)])
    status = SelectField('Status', coerce=str, validators=[Optional()], default='active')
    submit = SubmitField('Save Loan')

    def __init__(self, *args, **kwargs):
        super(TreasuryLoanForm, self).__init__(*args, **kwargs)
        try:
            from models import TreasuryAccount, LoanType, InterestType, LoanStatus, PaymentFrequency, FinancialInstitution
            accounts = TreasuryAccount.query.filter_by(is_active=True).all()
            self.account_id.choices = [(a.id, f"{a.name} ({a.currency})") for a in accounts]
            
            # LoanType and InterestType are enums, not DB models
            self.loan_type.choices = [(t.value, t.name.replace('_', ' ').title()) for t in LoanType]
            self.interest_type.choices = [(t.value, t.name.title()) for t in InterestType]
            self.status.choices = [(s.value, s.name.title()) for s in LoanStatus]
            
            # Ensure payment_frequency values match the PaymentFrequency enum
            self.payment_frequency.choices = [(p.value, p.name.replace('_', ' ').title()) for p in PaymentFrequency]
            
            # Add financial institutions for lender dropdown
            institutions = FinancialInstitution.query.filter_by(is_active=True).order_by(FinancialInstitution.name).all()
            self.lender_institution_id.choices = [(0, 'None')] + [(i.id, i.name) for i in institutions]
            
            # Set default start date to today
            if not self.start_date.data:
                self.start_date.data = datetime.now().date()
                
            # Set default maturity date to 1 year from start date
            if not self.maturity_date.data and self.start_date.data:
                self.maturity_date.data = self.start_date.data + timedelta(days=365)
                
            # Calculate number of payments if not provided
            if (not self.num_payments.data or self.num_payments.data == 0) and self.payment_frequency.data:
                if self.start_date.data and self.maturity_date.data:
                    days = (self.maturity_date.data - self.start_date.data).days
                    if self.payment_frequency.data == 'monthly':
                        self.num_payments.data = max(1, int(days / 30))
                    elif self.payment_frequency.data == 'quarterly':
                        self.num_payments.data = max(1, int(days / 90))
                    elif self.payment_frequency.data == 'semi_annual':
                        self.num_payments.data = max(1, int(days / 180))
                    elif self.payment_frequency.data == 'annual':
                        self.num_payments.data = max(1, int(days / 365))
                    elif self.payment_frequency.data == 'bullet':
                        self.num_payments.data = 1
        except Exception as e:
            print(f"Error loading form data: {str(e)}")


class LoanPaymentForm(FlaskForm):
    """Form for making a loan payment"""
    payment_type = SelectField('Payment Type', choices=[
        ('regular', 'Regular Payment'),
        ('interest_only', 'Interest Only'),
        ('principal_only', 'Principal Only'),
        ('prepayment', 'Prepayment')
    ], validators=[DataRequired()])
    
    payment_amount = DecimalField('Payment Amount', validators=[Optional(), NumberRange(min=0.01)], default=0.0)
    payment_date = DateField('Payment Date', format='%Y-%m-%d', validators=[DataRequired()])
    calculate_amount = BooleanField('Calculate Amount Automatically', default=True)
    
    source_account_id = SelectField('Source Account', coerce=int, validators=[DataRequired()])
    principal_amount = DecimalField('Principal Amount', validators=[Optional(), NumberRange(min=0.01)], default=0.0)
    interest_amount = DecimalField('Interest Amount', validators=[Optional(), NumberRange(min=0.0)], default=0.0)
    
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Make Payment')

    def __init__(self, *args, **kwargs):
        super(LoanPaymentForm, self).__init__(*args, **kwargs)
        # Set default payment date to today
        if not self.payment_date.data:
            self.payment_date.data = datetime.now().date()


class PayPalPayoutForm(FlaskForm):
    """Form for PayPal payouts"""
    recipient_email = StringField('Recipient Email', validators=[DataRequired(), Email()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=1.0)
    currency = SelectField('Currency', choices=[
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('CAD', 'Canadian Dollar (CAD)'),
        ('AUD', 'Australian Dollar (AUD)'),
        ('JPY', 'Japanese Yen (JPY)')
    ], validators=[DataRequired()], default='USD')
    
    note = StringField('Note to Recipient', validators=[Optional(), Length(max=255)])
    reference_id = StringField('Reference ID', validators=[Optional(), Length(max=50)])
    
    # Sender information
    sender_name = StringField('Sender Name', validators=[Optional(), Length(max=100)])
    sender_account = StringField('Sender Account', validators=[Optional(), Length(max=100)])
    
    # Batch options
    batch_id = HiddenField('Batch ID')
    
    submit = SubmitField('Send Payout')


class PayPalPaymentForm(FlaskForm):
    """Form for PayPal payments"""
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=1.0)
    currency = SelectField('Currency', choices=[
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('CAD', 'Canadian Dollar (CAD)'),
        ('AUD', 'Australian Dollar (AUD)'),
        ('JPY', 'Japanese Yen (JPY)')
    ], validators=[DataRequired()], default='USD')
    
    description = StringField('Payment Description', validators=[DataRequired(), Length(min=3, max=127)])
    invoice_id = StringField('Invoice ID', validators=[Optional(), Length(max=127)])
    
    customer_name = StringField('Customer Name', validators=[DataRequired(), Length(min=2, max=100)])
    customer_email = StringField('Customer Email', validators=[DataRequired(), Email()])
    
    return_url = HiddenField('Return URL')
    cancel_url = HiddenField('Cancel URL')
    
    submit = SubmitField('Proceed to PayPal')


class WireTransferForm(FlaskForm):
    """Form for wire transfers"""
    sender_name = StringField('Sender Name', validators=[DataRequired(), Length(min=2, max=100)])
    sender_account = StringField('Sender Account', validators=[DataRequired(), Length(min=5, max=50)])
    sender_bank = StringField('Sending Bank', validators=[DataRequired(), Length(min=2, max=100)])
    sender_swift = StringField('Sender SWIFT/BIC', validators=[DataRequired(), Length(min=8, max=11)])
    
    recipient_name = StringField('Recipient Name', validators=[DataRequired(), Length(min=2, max=100)])
    recipient_account = StringField('Recipient Account/IBAN', validators=[DataRequired(), Length(min=5, max=50)])
    recipient_bank = StringField('Recipient Bank', validators=[DataRequired(), Length(min=2, max=100)])
    recipient_swift = StringField('Recipient SWIFT/BIC', validators=[DataRequired(), Length(min=8, max=11)])
    recipient_address = TextAreaField('Recipient Address', validators=[DataRequired(), Length(min=5, max=200)])
    
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=0.0)
    currency = SelectField('Currency', choices=[
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('CAD', 'Canadian Dollar (CAD)'),
        ('AUD', 'Australian Dollar (AUD)'),
        ('JPY', 'Japanese Yen (JPY)')
    ], validators=[DataRequired()], default='USD')
    
    transfer_purpose = TextAreaField('Purpose of Transfer', validators=[DataRequired(), Length(min=5, max=200)])
    reference = StringField('Reference Number', validators=[DataRequired(), Length(min=3, max=35)])
    
    # Intermediary bank (if any)
    intermediary_bank = StringField('Intermediary Bank', validators=[Optional(), Length(max=100)])
    intermediary_swift = StringField('Intermediary SWIFT/BIC', validators=[Optional(), Length(min=8, max=11)])
    
    # Fee options
    fee_option = SelectField('Fee Option', choices=[
        ('OUR', 'OUR - Sender pays all fees'),
        ('SHA', 'SHA - Shared fees'),
        ('BEN', 'BEN - Beneficiary pays all fees')
    ], validators=[DataRequired()], default='SHA')
    
    # Compliance information
    compliance_purpose = SelectField('Purpose Category', choices=[
        ('', '-- Select Purpose --'),
        ('TRADE', 'Trade Payment'),
        ('SALA', 'Salary Payment'),
        ('INTC', 'Intra-Company Payment'),
        ('CORT', 'Corporate Trade'),
        ('TREA', 'Treasury Payment'),
        ('CASH', 'Cash Management Transfer'),
        ('DIVI', 'Dividend Payment'),
        ('GOVT', 'Government Payment'),
        ('PENS', 'Pension Payment'),
        ('TAXS', 'Tax Payment'),
        ('OTHR', 'Other')
    ], validators=[DataRequired()])
    
    compliance_source = TextAreaField('Source of Funds', validators=[DataRequired(), Length(min=5, max=200)])
    compliance_relationship = TextAreaField('Relationship to Beneficiary', validators=[DataRequired(), Length(min=5, max=200)])
    
    terms_agree = BooleanField('I confirm all details are correct and consent to this wire transfer', validators=[DataRequired()])
    
    submit = SubmitField('Submit Wire Transfer')


class POSPayoutForm(FlaskForm):
    """Form for POS (Point of Sale) payouts"""
    recipient_name = StringField('Recipient Name', validators=[DataRequired(), Length(min=2, max=100)])
    recipient_id = StringField('Recipient ID', validators=[Optional(), Length(max=50)])
    recipient_email = StringField('Recipient Email', validators=[Optional(), Email()])
    recipient_phone = StringField('Recipient Phone', validators=[Optional(), Length(max=20)])
    
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=1.0)
    currency = SelectField('Currency', choices=[
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('NGN', 'Nigerian Naira (NGN)'),
        ('KES', 'Kenyan Shilling (KES)'),
        ('ZAR', 'South African Rand (ZAR)'),
        ('GHS', 'Ghanaian Cedi (GHS)')
    ], validators=[DataRequired()], default='USD')
    
    reference = StringField('Reference', validators=[Optional(), Length(max=100)])
    description = StringField('Description', validators=[Optional(), Length(max=255)])
    
    # Payout method
    payout_method = SelectField('Payout Method', choices=[
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('crypto', 'Cryptocurrency'),
        ('nvct', 'NVC Token')
    ], validators=[DataRequired()], default='cash')
    
    # Bank transfer details
    bank_name = StringField('Bank Name', validators=[Optional(), Length(max=100)])
    account_number = StringField('Account Number', validators=[Optional(), Length(max=50)])
    routing_number = StringField('Routing/Swift Number', validators=[Optional(), Length(max=30)])
    
    # Mobile money details
    mobile_number = StringField('Mobile Number', validators=[Optional(), Length(min=10, max=15)])
    mobile_provider = SelectField('Mobile Provider', choices=[
        ('', '-- Select Provider --'),
        ('mtn', 'MTN'),
        ('airtel', 'Airtel'),
        ('vodafone', 'Vodafone'),
        ('orange', 'Orange'),
        ('mpesa', 'M-Pesa'),
        ('other', 'Other')
    ], validators=[Optional()])
    
    # Africa-specific fields
    region = SelectField('Region', choices=[
        ('', '-- Select Region --'),
        ('west_africa', 'West Africa'),
        ('east_africa', 'East Africa'),
        ('central_africa', 'Central Africa'),
        ('southern_africa', 'Southern Africa'),
        ('north_africa', 'North Africa')
    ], validators=[Optional()])
    
    # Authorization
    authorized_by = StringField('Authorized By', validators=[Optional(), Length(max=100)])
    authorization_code = StringField('Authorization Code', validators=[Optional(), Length(max=50)])
    
    submit = SubmitField('Process Payout')


class POSPaymentForm(FlaskForm):
    """Form for POS (Point of Sale) payments"""
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=1.0)
    currency = SelectField('Currency', choices=[
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('NGN', 'Nigerian Naira (NGN)'),
        ('KES', 'Kenyan Shilling (KES)'),
        ('ZAR', 'South African Rand (ZAR)'),
        ('GHS', 'Ghanaian Cedi (GHS)')
    ], validators=[DataRequired()], default='USD')
    
    reference = StringField('Reference', validators=[Optional(), Length(max=100)])
    description = StringField('Description', validators=[Optional(), Length(max=255)])
    
    # Customer information
    customer_name = StringField('Customer Name', validators=[DataRequired(), Length(min=2, max=100)])
    customer_email = StringField('Customer Email', validators=[Optional(), Email()])
    customer_phone = StringField('Customer Phone', validators=[Optional(), Length(max=20)])
    
    # Receipt options
    send_receipt = BooleanField('Send Receipt', default=True)
    receipt_email = StringField('Receipt Email', validators=[Optional(), Email()])
    
    # Payment method
    payment_method = SelectField('Payment Method', choices=[
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile_money', 'Mobile Money'),
        ('crypto', 'Cryptocurrency'),
        ('nvct', 'NVC Token')
    ], validators=[DataRequired()], default='card')
    
    # Card details (if card payment)
    card_number = StringField('Card Number', validators=[Optional(), Length(min=13, max=19)])
    card_expiry = StringField('Expiry (MM/YY)', validators=[Optional(), Length(min=5, max=5)])
    card_cvv = StringField('CVV', validators=[Optional(), Length(min=3, max=4)])
    
    # Mobile money details (if mobile_money payment)
    mobile_number = StringField('Mobile Number', validators=[Optional(), Length(min=10, max=15)])
    mobile_provider = SelectField('Mobile Provider', choices=[
        ('', '-- Select Provider --'),
        ('mtn', 'MTN'),
        ('airtel', 'Airtel'),
        ('vodafone', 'Vodafone'),
        ('orange', 'Orange'),
        ('mpesa', 'M-Pesa'),
        ('other', 'Other')
    ], validators=[Optional()])
    
    # Africa-specific payment fields
    region = SelectField('Region', choices=[
        ('', '-- Select Region --'),
        ('west_africa', 'West Africa'),
        ('east_africa', 'East Africa'),
        ('central_africa', 'Central Africa'),
        ('southern_africa', 'Southern Africa'),
        ('north_africa', 'North Africa')
    ], validators=[Optional()])
    
    store_location = StringField('Store Location', validators=[Optional(), Length(max=100)])
    
    # Terminal information (admin only)
    terminal_id = HiddenField('Terminal ID')
    merchant_id = HiddenField('Merchant ID')
    
    submit = SubmitField('Process Payment')


class CurrencyExchangeForm(FlaskForm):
    """Form for currency exchange"""
    source_currency = SelectField('From Currency', choices=get_currency_choices(), validators=[DataRequired()])
    target_currency = SelectField('To Currency', choices=get_currency_choices(), validators=[DataRequired()])
    
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=100.0)
    
    # Display only fields (calculated in real-time via JS)
    exchange_rate = HiddenField('Exchange Rate')
    fee_percentage = HiddenField('Fee Percentage')
    fee_amount = HiddenField('Fee Amount')
    total_amount = HiddenField('Total Amount')
    
    source_account_id = SelectField('Source Account', coerce=int, validators=[DataRequired()])
    target_account_id = SelectField('Target Account', coerce=int, validators=[Optional()])
    
    create_new_account = BooleanField('Create New Account for Target Currency', default=False)
    
    terms_agree = BooleanField('I agree to the exchange rate and fees', validators=[DataRequired()])
    
    submit = SubmitField('Exchange Currency')
    
    def __init__(self, *args, **kwargs):
        super(CurrencyExchangeForm, self).__init__(*args, **kwargs)
        try:
            from models import TreasuryAccount
            # Populate account choices from the database
            if current_user and current_user.is_authenticated:
                accounts = TreasuryAccount.query.filter_by(
                    is_active=True
                ).order_by(TreasuryAccount.name).all()
                
                self.source_account_id.choices = [(a.id, f"{a.name} ({a.currency})") for a in accounts]
                self.target_account_id.choices = [('', '-- Select Account --')] + [
                    (a.id, f"{a.name} ({a.currency})") for a in accounts
                ]
        except Exception as e:
            print(f"Error loading accounts for currency exchange form: {str(e)}")


class CashFlowForecastForm(FlaskForm):
    """Form for creating or updating a Cash Flow Forecast"""
    account_id = SelectField('Treasury Account', coerce=int, validators=[DataRequired()])
    flow_direction = SelectField('Flow Direction', choices=[
        ('inflow', 'Inflow'),
        ('outflow', 'Outflow')
    ], validators=[DataRequired()])
    
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=0.0)
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    
    description = StringField('Description', validators=[DataRequired(), Length(min=3, max=100)])
    forecast_date = DateField('Forecast Date', format='%Y-%m-%d', validators=[DataRequired()])
    
    category = SelectField('Category', choices=[
        ('operational', 'Operational'),
        ('investment', 'Investment'),
        ('financing', 'Financing'),
        ('tax', 'Tax'),
        ('extraordinary', 'Extraordinary'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    
    probability = SelectField('Probability', choices=[
        ('certain', 'Certain (100%)'),
        ('likely', 'Likely (75%)'),
        ('possible', 'Possible (50%)'),
        ('unlikely', 'Unlikely (25%)'),
        ('remote', 'Remote (<10%)')
    ], validators=[DataRequired()])
    
    is_recurring = BooleanField('Recurring', default=False)
    recurrence_type = SelectField('Recurrence Type', choices=[
        ('', '-- Select --'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual')
    ], validators=[Optional()])
    
    recurrence_end_date = DateField('Recurrence End Date', format='%Y-%m-%d', validators=[Optional()])
    
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save Forecast')

    def __init__(self, *args, **kwargs):
        super(CashFlowForecastForm, self).__init__(*args, **kwargs)
        try:
            from models import TreasuryAccount
            accounts = TreasuryAccount.query.filter_by(is_active=True).all()
            self.account_id.choices = [(a.id, f"{a.name} ({a.currency})") for a in accounts]
            
            # Set default forecast date to today
            if not self.forecast_date.data:
                self.forecast_date.data = datetime.now().date()
                
            # Set default recurrence end date to 1 year from forecast date
            if not self.recurrence_end_date.data and self.forecast_date.data and self.is_recurring.data:
                self.recurrence_end_date.data = self.forecast_date.data + timedelta(days=365)
        except Exception as e:
            print(f"Error loading form data: {str(e)}")


class EDITransactionForm(FlaskForm):
    """Form for EDI transaction creation/processing"""
    partner_id = SelectField('EDI Partner', coerce=int, validators=[DataRequired()])
    
    transaction_type = SelectField('Transaction Type', choices=[
        ('850', 'Purchase Order (850)'),
        ('810', 'Invoice (810)'),
        ('856', 'Advanced Shipping Notice (856)'),
        ('820', 'Payment Order (820)'),
        ('997', 'Functional Acknowledgment (997)'),
        ('custom', 'Custom Transaction')
    ], validators=[DataRequired()])
    
    direction = SelectField('Direction', choices=[
        ('inbound', 'Inbound (Partner to NVC)'),
        ('outbound', 'Outbound (NVC to Partner)')
    ], validators=[DataRequired()])
    
    transmission_method = SelectField('Transmission Method', choices=[
        ('automatic', 'Automatic (Use Partner Settings)'),
        ('manual', 'Manual Upload/Download')
    ], validators=[DataRequired()])
    
    file_content = TextAreaField('EDI File Content', validators=[Optional(), Length(max=100000)])
    file_upload = MultipleFileField('Upload EDI Files', validators=[Optional()])
    
    process_immediately = BooleanField('Process Immediately', default=True)
    
    notes = TextAreaField('Processing Notes', validators=[Optional(), Length(max=500)])
    
    submit = SubmitField('Process Transaction')
    
    def __init__(self, *args, **kwargs):
        super(EDITransactionForm, self).__init__(*args, **kwargs)
        try:
            from models import EdiPartner
            partners = EdiPartner.query.filter_by(active=True).order_by(EdiPartner.partner_name).all()
            self.partner_id.choices = [(p.id, p.partner_name) for p in partners]
        except Exception as e:
            print(f"Error populating EDI partner list: {str(e)}")


class ApiAccessReviewForm(FlaskForm):
    """Form for reviewing API access requests"""
    status = SelectField('Application Status', choices=[
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('more_info', 'Request More Information')
    ], validators=[DataRequired()])
    
    api_key = StringField('API Key', validators=[Optional(), Length(min=32, max=64)])
    api_secret = StringField('API Secret', validators=[Optional(), Length(min=64, max=128)])
    
    rate_limit = IntegerField('Rate Limit (requests per minute)', validators=[Optional(), NumberRange(min=1, max=10000)])
    daily_limit = IntegerField('Daily Limit (requests per day)', validators=[Optional(), NumberRange(min=1, max=1000000)])
    
    allowed_endpoints = SelectMultipleField('Allowed Endpoints', choices=[
        ('payments', 'Payment Processing'),
        ('accounts', 'Account Information'),
        ('transfers', 'Fund Transfers'),
        ('custody', 'Custody Services'),
        ('exchange', 'Currency Exchange'),
        ('blockchain', 'Blockchain Integration')
    ], validators=[Optional()])
    
    expiration_date = DateField('Access Expiration Date', format='%Y-%m-%d', validators=[Optional()])
    
    reviewer_notes = TextAreaField('Reviewer Notes', validators=[Optional(), Length(max=1000)])
    
    submit = SubmitField('Update Status')
    
    def __init__(self, *args, **kwargs):
        super(ApiAccessReviewForm, self).__init__(*args, **kwargs)
        # Set default expiration date to 1 year from now
        if not self.expiration_date.data:
            self.expiration_date.data = datetime.now() + timedelta(days=365)


class SwiftMT542Form(FlaskForm):
    """Form for SWIFT MT542 (Deliver Against Payment) message"""
    sender_institution_id = SelectField('Sending Institution', coerce=int, validators=[DataRequired()])
    receiver_institution_id = SelectField('Receiving Institution', coerce=int, validators=[DataRequired()])
    transaction_reference = StringField('Transaction Reference', validators=[DataRequired(), Length(min=8, max=16)])
    
    # Linkage (field 20C)
    related_reference = StringField('Related Reference', validators=[Optional(), Length(max=16)])
    
    # Trade Date (field 98A)
    trade_date = DateField('Trade Date', validators=[DataRequired()], format='%Y-%m-%d')
    
    # Settlement Date (field 98A)
    settlement_date = DateField('Settlement Date', validators=[DataRequired()], format='%Y-%m-%d')
    
    # Financial Instrument (field 35B)
    security_identifier = StringField('Security Identifier (ISIN)', validators=[DataRequired(), Length(min=12, max=12)])
    security_description = StringField('Security Description', validators=[DataRequired(), Length(max=35)])
    
    # Quantity (field 36B)
    quantity = FloatField('Quantity', validators=[DataRequired(), NumberRange(min=0.01)])
    
    # Amount (field 19A)
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=[
        ('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('CHF', 'CHF')
    ], validators=[DataRequired()])
    
    # Account (field 97A)
    safekeeping_account = StringField('Safekeeping Account', validators=[DataRequired(), Length(max=35)])
    cash_account = StringField('Cash Account', validators=[DataRequired(), Length(max=35)])
    
    # Settlement Parties (field 95)
    delivering_agent = StringField('Delivering Agent BIC', validators=[DataRequired(), Length(min=8, max=11)])
    receiving_agent = StringField('Receiving Agent BIC', validators=[DataRequired(), Length(min=8, max=11)])
    
    submit = SubmitField('Submit MT542 Instruction')
    
    def __init__(self, *args, **kwargs):
        super(SwiftMT542Form, self).__init__(*args, **kwargs)
        try:
            from models import FinancialInstitution
            institutions = FinancialInstitution.query.filter_by(active=True).all()
            self.sender_institution_id.choices = [(i.id, i.name) for i in institutions]
            self.receiver_institution_id.choices = [(i.id, i.name) for i in institutions]
        except Exception as e:
            print(f"Error populating MT542 form: {str(e)}")


class LetterOfCreditForm(FlaskForm):
    """Form for creating a Standby Letter of Credit (SBLC) via SWIFT"""
    receiver_institution_id = SelectField('Financial Institution', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    currency = SelectField('Currency', choices=[
        ('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('CHF', 'CHF'), 
        ('JPY', 'JPY'), ('CNY', 'CNY'), ('CAD', 'CAD'), ('AUD', 'AUD')
    ], validators=[DataRequired()])
    beneficiary = TextAreaField('Beneficiary', validators=[DataRequired(), Length(min=5, max=200)], 
                               description="Name and address of the beneficiary")
    expiry_date = DateField('Expiry Date', validators=[DataRequired()], 
                           format='%Y-%m-%d')
    terms_and_conditions = TextAreaField('Terms and Conditions', 
                                        validators=[DataRequired(), Length(min=10, max=2000)],
                                        description="Full terms and conditions of the letter of credit")

    def __init__(self, *args, **kwargs):
        super(LetterOfCreditForm, self).__init__(*args, **kwargs)
        # Set default expiry date to 6 months from now
        if not self.expiry_date.data:
            self.expiry_date.data = datetime.now() + timedelta(days=180)


class ClientRegistrationForm(FlaskForm):
    """Form for client registration"""
    # Basic account information
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

    # Client details
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    organization = StringField('Organization/Company', validators=[Optional()])
    country = SelectField('Country', choices=[
        ('', 'Select your country'),
        ('US', 'United States'),
        ('GB', 'United Kingdom'),
        ('CA', 'Canada'),
        ('AU', 'Australia'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('JP', 'Japan'),
        ('CH', 'Switzerland'),
        ('SG', 'Singapore'),
        ('AE', 'United Arab Emirates'),
        # Add more countries as needed
    ], validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[DataRequired()])

    # Business details
    business_type = SelectField('Business Type', choices=[
        ('', 'Select business type (if applicable)'),
        ('individual', 'Individual'),
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('partnership', 'Partnership'),
        ('llc', 'Limited Liability Company (LLC)'),
        ('corporation', 'Corporation'),
        ('nonprofit', 'Non-profit Organization'),
        ('government', 'Government Entity'),
        ('other', 'Other')
    ], validators=[Optional()])
    tax_id = StringField('Tax ID / EIN', validators=[Optional()])
    business_address = TextAreaField('Business Address', validators=[Optional()])
    website = StringField('Website', validators=[Optional()])

    # Banking preferences
    preferred_currency = SelectField('Preferred Currency', choices=[
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound'),
        ('CHF', 'CHF - Swiss Franc'),
        ('JPY', 'JPY - Japanese Yen'),
        ('CAD', 'CAD - Canadian Dollar'),
        ('AUD', 'AUD - Australian Dollar'),
        ('CNY', 'CNY - Chinese Yuan')
    ], validators=[DataRequired()])

    # Agreement and opt-ins
    terms_agree = BooleanField('I agree to the Terms of Service and Privacy Policy', validators=[DataRequired()])
    newsletter = BooleanField('I would like to receive updates about new features and services', default=True)

    # Optional invite code
    invite_code = StringField('Invitation Code (if any)', validators=[Optional()])

    # Reference information
    referral_source = SelectField('How did you hear about us?', choices=[
        ('', 'Select an option'),
        ('search', 'Search Engine'),
        ('social', 'Social Media'),
        ('referral', 'Referred by Someone'),
        ('advertisement', 'Advertisement'),
        ('news', 'News Article'),
        ('other', 'Other')
    ], validators=[Optional()])

    submit = SubmitField('Complete Registration')


class PartnerRegistrationForm(FlaskForm):
    """Form for partner registration"""
    name = StringField('Institution Name', validators=[DataRequired(), Length(min=2, max=100)])
    partner_type = SelectField('Partner Type', choices=[
        ('', '-- Select --'),
        ('Financial Institution', 'Financial Institution'),
        ('Asset Manager', 'Asset Manager'),
        ('Business Partner', 'Business Partner'),
        ('Correspondent Bank', 'Correspondent Bank'),
        ('Settlement Partner', 'Settlement Partner'),
        ('Stablecoin Issuer', 'Stablecoin Issuer'),
        ('Industrial Bank', 'Industrial Bank')
    ], validators=[DataRequired()])
    website = StringField('Website', validators=[Optional(), Length(max=255)])
    country = StringField('Country', validators=[DataRequired(), Length(max=100)])
    
    # Contact information
    primary_contact = StringField('Primary Contact Name', validators=[DataRequired(), Length(min=2, max=100)])
    primary_email = StringField('Primary Email', validators=[DataRequired(), Email()])
    primary_phone = StringField('Primary Phone', validators=[Optional(), Length(max=50)])
    
    # Partnership details
    notes = TextAreaField('Additional Information', validators=[Optional(), Length(max=1000)])
    
    # Terms agreement
    terms_agree = BooleanField('I agree to the terms', validators=[DataRequired()])
    
    submit = SubmitField('Submit Registration')


class CorrespondentBankApplicationForm(FlaskForm):
    """Form for correspondent bank application"""
    institution_name = StringField('Institution Name', validators=[DataRequired(), Length(min=2, max=100)])
    country = StringField('Country of Incorporation', validators=[DataRequired(), Length(min=2, max=100)])
    swift_code = StringField('SWIFT/BIC Code', validators=[Optional(), Length(max=11)])
    institution_type = SelectField('Type of Institution', validators=[DataRequired()], 
                                  choices=[
                                      ('', '-- Select --'),
                                      ('Commercial Bank', 'Commercial Bank'),
                                      ('Investment Bank', 'Investment Bank'),
                                      ('Central Bank', 'Central Bank'),
                                      ('Credit Union', 'Credit Union'),
                                      ('Microfinance Institution', 'Microfinance Institution'),
                                      ('Regional Development Bank', 'Regional Development Bank'),
                                      ('Other Financial Institution', 'Other Financial Institution')
                                  ])
    regulatory_authority = StringField('Primary Regulatory Authority', validators=[DataRequired(), Length(min=2, max=100)])
    
    # Contact information
    contact_name = StringField('Primary Contact Name', validators=[DataRequired(), Length(min=2, max=100)])
    contact_title = StringField('Title/Position', validators=[DataRequired(), Length(min=2, max=100)])
    contact_email = StringField('Email Address', validators=[DataRequired(), Email()])
    contact_phone = StringField('Phone Number', validators=[DataRequired(), Length(min=5, max=30)])
    
    # Services and preferences
    services = SelectMultipleField('Services of Interest',
                                  choices=[
                                      ('USD_correspondent', 'USD Correspondent Account'),
                                      ('EUR_correspondent', 'EUR Correspondent Account'),
                                      ('african_currencies', 'African Currency Accounts'),
                                      ('nvct_stablecoin', 'NVCT Stablecoin Account'),
                                      ('forex_services', 'Foreign Exchange Services'),
                                      ('trade_finance', 'Trade Finance Services'),
                                      ('project_finance', 'Project Finance Access'),
                                      ('api_integration', 'API Integration')
                                  ])
    expected_volume = SelectField('Expected Monthly Transaction Volume',
                                 choices=[
                                     ('', '-- Select --'),
                                     ('Less than $1 million', 'Less than $1 million'),
                                     ('$1 million - $5 million', '$1 million - $5 million'),
                                     ('$5 million - $10 million', '$5 million - $10 million'),
                                     ('$10 million - $25 million', '$10 million - $25 million'),
                                     ('$25 million - $50 million', '$25 million - $50 million'),
                                     ('$50 million - $100 million', '$50 million - $100 million'),
                                     ('Over $100 million', 'Over $100 million')
                                 ], 
                                 validators=[DataRequired()])
    african_regions = SelectMultipleField('African Regions of Interest',
                                        choices=[
                                            ('west_africa', 'West Africa'),
                                            ('east_africa', 'East Africa'),
                                            ('southern_africa', 'Southern Africa'),
                                            ('north_africa', 'North Africa')
                                        ])
    additional_info = TextAreaField('Additional Information', validators=[Optional(), Length(max=1000)])
    
    # Terms and conditions
    terms_agree = BooleanField('I agree to the terms', validators=[DataRequired()])
    
    submit = SubmitField('Submit Application')