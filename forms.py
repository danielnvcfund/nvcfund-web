from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, TextAreaField, HiddenField, FloatField, DateField, validators
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from datetime import datetime, timedelta
from models import FinancialInstitution, TransactionType
import json

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])

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
    
class FinancialInstitutionForm(FlaskForm):
    name = StringField('Institution Name', validators=[DataRequired()])
    institution_type = SelectField('Institution Type', choices=[], validators=[DataRequired()])
    api_endpoint = StringField('API Endpoint')
    api_key = StringField('API Key')
    ethereum_address = StringField('Ethereum Address')
    
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
    success = BooleanField('Simulate Success')

class PaymentForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired()])
    currency = SelectField('Currency', choices=[('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('ETH', 'ETH'), ('XRP', 'XRP')], validators=[DataRequired()])
    transaction_type = SelectField('Transaction Type', choices=[], validators=[DataRequired()])
    gateway = SelectField('Payment Gateway', choices=[], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    
    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)
        # Dynamically load transaction types from the Enum
        self.transaction_type.choices = [(t.name, t.value) for t in TransactionType]

class BankTransferForm(FlaskForm):
    transaction_id = HiddenField('Transaction ID', validators=[Optional()])
    bank_name = StringField('Bank Name', validators=[DataRequired()])
    account_holder = StringField('Account Holder Name', validators=[DataRequired()])
    account_number = StringField('Account Number', validators=[DataRequired()])
    routing_number = StringField('Routing Number', validators=[DataRequired()])
    swift_code = StringField('SWIFT/BIC Code', validators=[DataRequired()])
    bank_address = TextAreaField('Bank Address', validators=[DataRequired()])
    reference = StringField('Payment Reference', validators=[DataRequired()])
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