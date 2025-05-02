from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, PasswordField, BooleanField, FloatField, SubmitField, HiddenField, DateField, RadioField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, Email, EqualTo, NumberRange, ValidationError, Regexp
from models import TransactionType
from datetime import datetime, timedelta

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
    first_name = StringField('First Name', validators=[Optional()])
    last_name = StringField('Last Name', validators=[Optional()])
    organization = StringField('Company/Organization', validators=[Optional()])
    country = StringField('Country', validators=[Optional()])
    phone = StringField('Phone Number', validators=[Optional()])
    newsletter = BooleanField('Subscribe to Newsletter', default=True)
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

class BankTransferForm(FlaskForm):
    transaction_id = HiddenField('Transaction ID', validators=[Optional()])
    recipient_name = StringField('Recipient Name', validators=[DataRequired()])
    bank_name = StringField('Bank Name', validators=[DataRequired()])
    account_number = StringField('Account Number', validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired()])
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])

class LetterOfCreditForm(FlaskForm):
    """Form for creating a letter of credit"""
    applicant_name = StringField('Applicant Name', validators=[DataRequired()])
    beneficiary_name = StringField('Beneficiary Name', validators=[DataRequired()])
    issuing_bank = SelectField('Issuing Bank', coerce=int, validators=[DataRequired()])
    advising_bank = SelectField('Advising Bank', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    expiry_date = DateField('Expiry Date', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    goods_description = TextAreaField('Goods Description', validators=[DataRequired()])
    terms_conditions = TextAreaField('Terms and Conditions', validators=[DataRequired()])
    submit = SubmitField('Create Letter of Credit')

class SwiftFundTransferForm(FlaskForm):
    """Form for creating a SWIFT MT103/MT202 fund transfer"""
    receiver_institution_id = SelectField('Receiving Institution', coerce=int, validators=[DataRequired()])
    receiver_institution_name = StringField('Institution Name', validators=[DataRequired()])
    correspondent_bank_name = StringField('Correspondent Bank Name', validators=[Optional()])
    correspondent_bank_swift = StringField('Correspondent Bank SWIFT/BIC', validators=[Optional()])
    intermediary_bank_name = StringField('Intermediary Bank Name', validators=[Optional()])
    intermediary_bank_swift = StringField('Intermediary Bank SWIFT/BIC', validators=[Optional()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    ordering_customer = TextAreaField('Ordering Customer/Institution', validators=[DataRequired()])
    beneficiary_customer = TextAreaField('Beneficiary Customer/Institution', validators=[DataRequired()])
    details_of_payment = TextAreaField('Payment Details', validators=[DataRequired()])
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
    receiver_institution_id = SelectField('Receiver Institution', coerce=int, validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=100)])
    message_body = TextAreaField('Message Text', validators=[DataRequired()])
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
    key_type = SelectField('Key Type', choices=[], validators=[DataRequired()])
    access_level = SelectField('Access Level', choices=[], validators=[DataRequired()])
    expiry_date = DateField('Expiry Date', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
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
        ('operating', 'Operating Account'),
        ('investment', 'Investment Account'),
        ('reserve', 'Reserve Account'),
        ('escrow', 'Escrow Account'),
        ('settlement', 'Settlement Account')
    ], validators=[DataRequired()])
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    opening_balance = FloatField('Opening Balance', validators=[DataRequired(), NumberRange(min=0)])
    interest_rate = FloatField('Interest Rate (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Create Account')

class TreasuryTransactionForm(FlaskForm):
    """Form for creating a treasury transaction"""
    transaction_date = DateField('Transaction Date', validators=[DataRequired()], default=datetime.utcnow)
    from_account_id = SelectField('From Account', validators=[DataRequired()], coerce=int)
    to_account_id = SelectField('To Account', validators=[DataRequired()], coerce=int)
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    transaction_type = SelectField('Transaction Type', choices=[
        ('transfer', 'Internal Transfer'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('interest', 'Interest Payment'),
        ('fee', 'Fee Payment')
    ], validators=[DataRequired()])
    reference_number = StringField('Reference Number', validators=[Optional(), Length(max=50)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
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