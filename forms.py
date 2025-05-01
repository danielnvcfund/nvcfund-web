from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, PasswordField, BooleanField, FloatField, SubmitField, HiddenField, DateField, RadioField, IntegerField
from models import TransactionType
from wtforms.validators import DataRequired, Length, Optional, Email, EqualTo

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
        # Load available financial institutions that support SWIFT
        from swift_integration import SwiftService
        swift_institutions = SwiftService.get_swift_enabled_institutions()
        if not swift_institutions:
            # If no SWIFT-enabled institutions are found, fall back to all active institutions
            swift_institutions = FinancialInstitution.query.filter_by(is_active=True).all()

        self.receiver_institution_id.choices = [(i.id, i.name) for i in swift_institutions]

        # Set default expiry date to 6 months from now
        if not self.expiry_date.data:
            self.expiry_date.data = datetime.now() + timedelta(days=180)

    def validate_expiry_date(self, field):
        """Ensure expiry date is in the future"""
        if field.data <= datetime.now().date():
            raise ValidationError('Expiry date must be in the future')

        # Validate maximum expiry period (2 years)
        max_date = datetime.now().date() + timedelta(days=730)
        if field.data > max_date:
            raise ValidationError('Maximum expiry period is 2 years from today')


class SwiftFundTransferForm(FlaskForm):
    """Form for creating a SWIFT MT103/MT202 fund transfer"""
    receiver_institution_id = SelectField('Receiving Institution ID', coerce=int, validators=[DataRequired()])
    receiver_institution_name = StringField('Receiving Institution Name', 
                                          validators=[DataRequired(), Length(min=2, max=100)],
                                          description="The full name of the receiving institution")
    amount = FloatField('Amount', validators=[DataRequired()])
    currency = SelectField('Currency', choices=get_currency_choices(), validators=[DataRequired()])
    beneficiary_customer = TextAreaField('Beneficiary Details', 
                                      validators=[DataRequired(), Length(min=5, max=500)],
                                      description="Name, account number, and address of the recipient")
    ordering_customer = TextAreaField('Sender Details', validators=[DataRequired(), Length(min=5, max=500)],
                                    description="Name, account number, and address of the sender")
    details_of_payment = TextAreaField('Payment Details/Purpose', 
                                     validators=[DataRequired(), Length(max=300)],
                                     description="Reason for transfer (invoice number, purpose, etc.)")
    is_financial_institution = RadioField('Transfer Type', 
                                       choices=[(0, 'MT103 - Customer Credit Transfer'), 
                                                (1, 'MT202 - Financial Institution Transfer')],
                                       coerce=int,
                                       default=0,
                                       validators=[DataRequired()])
    submit = SubmitField('Submit Fund Transfer')

    def __init__(self, *args, **kwargs):
        super(SwiftFundTransferForm, self).__init__(*args, **kwargs)
        # Load available financial institutions that support SWIFT
        from swift_integration import SwiftService
        swift_institutions = SwiftService.get_swift_enabled_institutions()
        if not swift_institutions:
            # If no SWIFT-enabled institutions are found, fall back to all active institutions
            swift_institutions = FinancialInstitution.query.filter_by(is_active=True).all()

        self.receiver_institution_id.choices = [(i.id, i.name) for i in swift_institutions]


# Temporarily commented out RTGS form
"""
class SwiftMT542Form(FlaskForm):
    Form for sending a SWIFT MT542 Deliver Against Payment message
    receiver_institution_id = SelectField('Receiving Institution', coerce=int, validators=[DataRequired()])
    trade_date = DateField('Trade Date', validators=[DataRequired()])
    settlement_date = DateField('Settlement Date', validators=[DataRequired()])
    security_details = StringField('Security Details', validators=[DataRequired(), Length(max=500)])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired()])
    currency = SelectField('Currency', choices=[('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP')], validators=[DataRequired()])
    submit = SubmitField('Submit MT542')

    def __init__(self, *args, **kwargs):
        super(SwiftMT542Form, self).__init__(*args, **kwargs)
        # Load available financial institutions
        from swift_integration import SwiftService
        swift_institutions = SwiftService.get_swift_enabled_institutions()
        self.receiver_institution_id.choices = [(i.id, i.name) for i in swift_institutions]

class SwiftFreeFormatMessageForm(FlaskForm):
    """Form for sending a SWIFT MT799 free format message"""
    receiver_institution_id = SelectField('Receiving Institution', coerce=int, validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired(), Length(min=5, max=100)],
                         description="A clear subject for your message")
    message_body = TextAreaField('Message Content', 
                               validators=[DataRequired(), Length(min=10, max=2000)],
                               description="Content of your message to the institution")
    submit = SubmitField('Send Message')

    def __init__(self, *args, **kwargs):
        super(SwiftFreeFormatMessageForm, self).__init__(*args, **kwargs)
        # Load available financial institutions that support SWIFT
        from swift_integration import SwiftService
        swift_institutions = SwiftService.get_swift_enabled_institutions()
        if not swift_institutions:
            # If no SWIFT-enabled institutions are found, fall back to all active institutions
            swift_institutions = FinancialInstitution.query.filter_by(is_active=True).all()

        self.receiver_institution_id.choices = [(i.id, i.name) for i in swift_institutions]
class ApiAccessRequestForm(FlaskForm):
    """Form for requesting API access"""
    request_reason = TextAreaField("Why do you need API access?", validators=[
        DataRequired(),
        Length(min=20, max=500, message="Please provide at least 20 characters explaining your need for API access")
    ])
    integration_purpose = SelectField("Primary purpose of integration", validators=[DataRequired()], choices=[
        ("payment_processing", "Payment Processing"),
        ("account_management", "Account Management"),
        ("data_analytics", "Data Analytics"),
        ("reporting", "Reporting and Dashboards"),
        ("automation", "Workflow Automation"),
        ("other", "Other (please specify in your request reason)")
    ])
    company_name = StringField("Company/Organization Name", validators=[Optional(), Length(max=128)])
    website = StringField("Website", validators=[Optional(), Length(max=256)])
    terms_agree = BooleanField("I agree to use the API according to the terms of service", validators=[
        DataRequired(message="You must agree to the terms of service")
    ])
    submit = SubmitField("Submit Request")

class ApiAccessReviewForm(FlaskForm):
    """Form for admins to review API access requests"""
    status = SelectField("Decision", validators=[DataRequired()], choices=[
        ("pending", "Keep Pending"),
        ("approved", "Approve"),
        ("rejected", "Reject")
    ])
    reviewer_notes = TextAreaField("Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Submit Review")

class PartnerApiKeyForm(FlaskForm):
    """Form for creating and editing partner API keys"""
    partner_name = StringField("Partner/Institution Name", validators=[DataRequired(), Length(min=2, max=128)])
    partner_email = StringField("Contact Email", validators=[DataRequired(), Email()])
    partner_type = SelectField("Partner Type", validators=[DataRequired()], choices=[
        ("financial_institution", "Financial Institution"),
        ("token_provider", "Token Provider"),
        ("payment_processor", "Payment Processor"),
        ("data_provider", "Data Provider"),
        ("other", "Other")
    ])
    access_level = SelectField("Access Level", validators=[DataRequired()], choices=[
        ("read", "Read Only"),
        ("read_write", "Read & Write"),
        ("full", "Full Access")
    ])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save")

class EdiPartnerForm(FlaskForm):
    """Form for creating and editing EDI partners"""
    partner_id = StringField("Partner ID", validators=[DataRequired(), Length(min=2, max=64)])
    name = StringField("Institution Name", validators=[DataRequired(), Length(min=2, max=128)])
    routing_number = StringField("Routing Number", validators=[Optional(), Length(max=20)])
    account_number = StringField("Account Number", validators=[Optional(), Length(max=30)])

    edi_format = SelectField("EDI Format", validators=[DataRequired()], choices=[
        ("X12", "X12 (ANSI X12)"),
        ("EDIFACT", "EDIFACT (UN/EDIFACT)"),
        ("CUSTOM", "Custom Format")
    ])

    connection_type = SelectField("Connection Type", validators=[DataRequired()], choices=[
        ("SFTP", "SFTP Transfer"),
        ("API", "API Integration"),
        ("EMAIL", "Secure Email")
    ])

    # SFTP credentials
    sftp_host = StringField("SFTP Host", validators=[Optional(), Length(max=256)])
    sftp_port = StringField("SFTP Port", validators=[Optional(), Length(max=5)], default="22")
    sftp_username = StringField("SFTP Username", validators=[Optional(), Length(max=64)])
    sftp_password = PasswordField("SFTP Password", validators=[Optional(), Length(max=128)])
    sftp_remote_dir = StringField("Remote Directory", validators=[Optional(), Length(max=256)], default="/incoming")

    is_active = BooleanField("Partner is Active", default=True)
    submit = SubmitField("Save Partner")

class EDITransactionForm(FlaskForm):
    """Form for creating EDI transactions"""
    partner_id = SelectField("EDI Partner", validators=[DataRequired()])
    transaction_type = SelectField("Transaction Type", validators=[DataRequired()], choices=[
        ("EDI_PAYMENT", "Standard EDI Payment"),
        ("EDI_ACH_TRANSFER", "ACH Transfer"),
        ("EDI_WIRE_TRANSFER", "Wire Transfer")
    ])

    amount = FloatField("Amount", validators=[DataRequired()])
    currency = SelectField("Currency", validators=[DataRequired()])

    recipient_name = StringField("Recipient Name", validators=[DataRequired(), Length(min=2, max=128)])
    recipient_account = StringField("Recipient Account", validators=[Optional(), Length(max=30)])
    recipient_routing = StringField("Recipient Routing #", validators=[Optional(), Length(max=20)])

    description = TextAreaField("Description/Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Process Transaction")

# Treasury Management System Forms
class TreasuryAccountForm(FlaskForm):
    """Form for creating or editing a treasury account"""
    name = StringField('Account Name', validators=[DataRequired(), Length(max=128)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=256)])
    account_type = SelectField('Account Type', validators=[DataRequired()], choices=[
        (t.name, t.value.title()) for t in TreasuryAccountType
    ])
    institution_id = SelectField('Financial Institution', validators=[DataRequired()], coerce=int)
    account_number = StringField('Account Number', validators=[Optional(), Length(max=64)])
    currency = SelectField('Currency', validators=[DataRequired()], choices=get_currency_choices())
    initial_balance = FloatField('Initial Balance', validators=[DataRequired()], default=0.0)
    target_balance = FloatField('Target Balance', validators=[Optional()])
    minimum_balance = FloatField('Minimum Balance', validators=[Optional()], default=0.0)
    maximum_balance = FloatField('Maximum Balance', validators=[Optional()])
    submit = SubmitField('Save Account')

    def validate_initial_balance(self, field):
        """Validate initial balance is not negative"""
        if field.data < 0:
            raise ValidationError('Initial balance cannot be negative')

    def validate_target_balance(self, field):
        """Validate target balance if provided"""
        if field.data is not None and field.data < 0:
            raise ValidationError('Target balance cannot be negative')

class TreasuryInvestmentForm(FlaskForm):
    """Form for creating an investment"""
    name = StringField('Investment Name', validators=[DataRequired(), Length(max=128)])
    account_id = SelectField('Source Account', validators=[DataRequired()], coerce=int)
    investment_type = SelectField('Investment Type', validators=[DataRequired()], choices=[
        (t.name, t.value.replace('_', ' ').title()) for t in InvestmentType
    ])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', validators=[DataRequired()], choices=get_currency_choices())
    interest_rate = FloatField('Interest Rate (%)', validators=[Optional()], default=0.0)
    start_date = DateField('Start Date', validators=[DataRequired()], default=datetime.utcnow)
    maturity_date = DateField('Maturity Date', validators=[DataRequired()])
    institution_id = SelectField('Financial Institution', validators=[DataRequired()], coerce=int)
    description = TextAreaField('Description', validators=[Optional(), Length(max=256)])
    is_active = BooleanField('Investment is Active', default=True)
    submit = SubmitField('Create Investment')

    def validate_maturity_date(self, field):
        """Validate maturity date is after start date"""
        if self.start_date.data and field.data <= self.start_date.data:
            raise ValidationError('Maturity date must be after start date')

    def validate_interest_rate(self, field):
        """Validate interest rate is not negative"""
        if field.data is not None and field.data < 0:
            raise ValidationError('Interest rate cannot be negative')

class TreasuryTransactionForm(FlaskForm):
    """Form for creating a treasury transaction"""
    from_account_id = SelectField('From Account', validators=[DataRequired()], coerce=int)
    to_account_id = SelectField('To Account', validators=[DataRequired()], coerce=int)
    transaction_type = SelectField('Transaction Type', validators=[DataRequired()], choices=[
        (t.name, t.value.replace('_', ' ').title()) for t in TreasuryTransactionType
    ])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', validators=[DataRequired()], choices=get_currency_choices())
    exchange_rate = FloatField('Exchange Rate', validators=[Optional()], default=1.0)
    reference_number = StringField('Reference Number', validators=[Optional(), Length(max=64)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=256)])
    memo = TextAreaField('Memo / Notes', validators=[Optional()])
    submit = SubmitField('Create Transaction')

    def validate_to_account_id(self, field):
        """Validate to_account is different from from_account"""
        if field.data == self.from_account_id.data and field.data != 0:
            raise ValidationError('Source and destination accounts cannot be the same')

class CashFlowForecastForm(FlaskForm):
    """Form for creating a cash flow forecast"""
    account_id = SelectField('Account', validators=[DataRequired()], coerce=int)
    direction = SelectField('Direction', validators=[DataRequired()], choices=[
        (d.name, d.value.title()) for d in CashFlowDirection
    ])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', validators=[DataRequired()], choices=get_currency_choices())
    transaction_date = DateField('Transaction Date', validators=[DataRequired()], default=datetime.utcnow)
    recurrence_type = SelectField('Recurrence', validators=[DataRequired()], choices=[
        (r.name, r.value.title()) for r in RecurrenceType
    ], default=RecurrenceType.NONE.name)
    recurrence_end_date = DateField('Recurrence End Date', validators=[Optional()])
    source_description = StringField('Source / Recipient', validators=[DataRequired(), Length(max=256)])
    category = StringField('Category', validators=[Optional(), Length(max=128)])
    probability = FloatField('Probability (%)', validators=[Optional()], default=100.0)
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Cash Flow')

    def validate_probability(self, field):
        """Validate probability is between 0 and 100"""
        if field.data < 0 or field.data > 100:
            raise ValidationError('Probability must be between 0 and 100')

    def validate_recurrence_end_date(self, field):
        """Validate recurrence end date if provided"""
        if self.recurrence_type.data != RecurrenceType.NONE.name and field.data is None:
            raise ValidationError('Recurrence end date is required for recurring cash flows')
        if field.data and self.transaction_date.data and field.data <= self.transaction_date.data:
            raise ValidationError('Recurrence end date must be after transaction date')

class TreasuryLoanForm(FlaskForm):
    """Form for creating a treasury loan"""
    name = StringField('Loan Name', validators=[DataRequired(), Length(max=128)])
    loan_id = StringField('Loan ID', validators=[Optional(), Length(max=64)])
    account_id = SelectField('Associated Account', validators=[DataRequired()], coerce=int)
    loan_type = SelectField('Loan Type', validators=[DataRequired()], choices=[
        (t.name, t.value.replace('_', ' ').title()) for t in LoanType
    ])
    principal_amount = FloatField('Principal Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', validators=[DataRequired()], choices=get_currency_choices())
    interest_type = SelectField('Interest Type', validators=[DataRequired()], choices=[
        (t.name, t.value.title()) for t in InterestType
    ])
    interest_rate = FloatField('Interest Rate (%)', validators=[DataRequired(), NumberRange(min=0)])
    reference_rate = StringField('Reference Rate', validators=[Optional(), Length(max=64)])
    margin = FloatField('Margin (%)', validators=[Optional()])
    start_date = DateField('Start Date', validators=[DataRequired()], default=datetime.utcnow)
    maturity_date = DateField('Maturity Date', validators=[DataRequired()])
    payment_frequency = SelectField('Payment Frequency', validators=[DataRequired()], choices=[
        (f.name, f.value.replace('_', ' ').title()) for f in PaymentFrequency
    ])
    first_payment_date = DateField('First Payment Date', validators=[DataRequired()])
    payment_amount = FloatField('Payment Amount', validators=[Optional()])
    lender_institution_id = SelectField('Lender Institution', validators=[DataRequired()], coerce=int)
    status = SelectField('Status', validators=[DataRequired()], choices=[
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('paid', 'Paid'),
        ('defaulted', 'Defaulted')
    ], default='active')
    description = TextAreaField('Description', validators=[Optional(), Length(max=256)])
    collateral_description = TextAreaField('Collateral Description', validators=[Optional()])
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

class LoanPaymentForm(FlaskForm):
    """Form for making a loan payment"""
    from_account_id = SelectField('From Account', validators=[DataRequired()], coerce=int)
    payment_amount = FloatField('Payment Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    payment_date = DateField('Payment Date', validators=[DataRequired()], default=datetime.utcnow)
    principal_amount = FloatField('Principal Amount', validators=[Optional()], render_kw={'readonly': True})
    interest_amount = FloatField('Interest Amount', validators=[Optional()], render_kw={'readonly': True})
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Make Payment')