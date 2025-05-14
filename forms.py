from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, PasswordField, BooleanField, FloatField, SubmitField, HiddenField, DateField, RadioField, IntegerField, MultipleFileField, SelectMultipleField, widgets
from models import TransactionType
from wtforms.validators import DataRequired, Length, Optional, Email, EqualTo, NumberRange, ValidationError, Regexp
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
    transaction_reference = StringField('Transaction Reference', validators=[DataRequired(), Length(min=8, max=16)])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', choices=[
        ('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('CHF', 'CHF'), 
        ('JPY', 'JPY'), ('CNY', 'CNY'), ('CAD', 'CAD'), ('AUD', 'AUD')
    ], validators=[DataRequired()])
    
    # Ordering Customer (field 50)
    ordering_customer_account = StringField('Ordering Customer Account', validators=[DataRequired(), Length(max=35)])
    ordering_customer_name = StringField('Ordering Customer Name', validators=[DataRequired(), Length(max=35)])
    ordering_customer_address = TextAreaField('Ordering Customer Address', validators=[DataRequired(), Length(max=140)])
    
    # Beneficiary (field 59)
    beneficiary_account = StringField('Beneficiary Account', validators=[DataRequired(), Length(max=35)])
    beneficiary_name = StringField('Beneficiary Name', validators=[DataRequired(), Length(max=35)])
    beneficiary_address = TextAreaField('Beneficiary Address', validators=[DataRequired(), Length(max=140)])
    
    # Details of Payment (field 70)
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
            institutions = FinancialInstitution.query.filter_by(active=True).all()
            self.sender_institution_id.choices = [(i.id, i.name) for i in institutions]
            self.receiver_institution_id.choices = [(i.id, i.name) for i in institutions]
        except Exception as e:
            print(f"Error populating Swift transfer form: {str(e)}")


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
    sender_account_id = SelectField('From Account', coerce=int, validators=[DataRequired()])
    recipient_name = StringField('Recipient Name', validators=[DataRequired(), Length(min=2, max=100)])
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
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    
    # Optional fields
    memo = StringField('Memo/Reference', validators=[Optional(), Length(max=50)])
    
    # Transfer category
    category = SelectField('Transfer Category', choices=[
        ('internal', 'Internal Transfer'),
        ('external', 'External Transfer'),
        ('bill_payment', 'Bill Payment'),
        ('payroll', 'Payroll'),
        ('other', 'Other')
    ], validators=[Optional()])
    
    # Transfer timing
    transfer_timing = SelectField('When to Send', choices=[
        ('standard', 'Standard (2-3 business days)'),
        ('same_day', 'Same-Day ACH (additional fee applies)')
    ], default='standard', validators=[DataRequired()])
    
    # Terms agreement
    agree_terms = BooleanField('I confirm this information is correct and authorize this transfer', validators=[DataRequired()])
    
    submit = SubmitField('Submit ACH Transfer')
    
    def __init__(self, *args, **kwargs):
        super(ACHTransferForm, self).__init__(*args, **kwargs)
        from models import Account
        try:
            # Get user accounts for the sender field
            user_id = kwargs.get('user_id')
            if user_id:
                accounts = Account.query.filter_by(user_id=user_id, active=True).all()
                self.sender_account_id.choices = [(a.id, f"{a.account_number} - {a.account_name} ({a.currency})") for a in accounts]
        except Exception as e:
            print(f"Error populating accounts in ACH form: {str(e)}")


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
                                      ('USD Correspondent Account', 'USD Correspondent Account'),
                                      ('EUR Correspondent Account', 'EUR Correspondent Account'),
                                      ('African Currency Accounts', 'African Currency Accounts'),
                                      ('NVCT Stablecoin Account', 'NVCT Stablecoin Account'),
                                      ('Foreign Exchange Services', 'Foreign Exchange Services'),
                                      ('Trade Finance Services', 'Trade Finance Services'),
                                      ('Project Finance Access', 'Project Finance Access'),
                                      ('API Integration', 'API Integration')
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
                                            ('West Africa', 'West Africa'),
                                            ('East Africa', 'East Africa'),
                                            ('Southern Africa', 'Southern Africa'),
                                            ('North Africa', 'North Africa')
                                        ])
    additional_info = TextAreaField('Additional Information', validators=[Optional(), Length(max=1000)])
    
    # Terms and conditions
    terms_agree = BooleanField('I agree to the terms', validators=[DataRequired()])
    
    submit = SubmitField('Submit Application')