from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, EmailField, SelectField,
    FloatField, TextAreaField, BooleanField, HiddenField, DecimalField
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, Optional
from models import User, PaymentGatewayType, FinancialInstitutionType, TransactionType, InvitationType, InvitationStatus, Invitation

class LoginForm(FlaskForm):
    """Form for user login"""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    """Form for user registration"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class RequestResetForm(FlaskForm):
    """Form for requesting a password reset"""
    email = EmailField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if not user:
            raise ValidationError('There is no account with that email. Please register first.')

class ResetPasswordForm(FlaskForm):
    """Form for resetting password"""
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class ForgotUsernameForm(FlaskForm):
    """Form for recovering username"""
    email = EmailField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Recover Username')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if not user:
            raise ValidationError('There is no account with that email. Please register first.')

class PaymentForm(FlaskForm):
    """Form for payment processing"""
    gateway_id = SelectField('Payment Gateway', validators=[DataRequired()], coerce=int)
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', validators=[DataRequired()], 
                           choices=[('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('JPY', 'JPY'), ('ETH', 'ETH')])
    description = TextAreaField('Description', validators=[Optional(), Length(max=256)])
    submit = SubmitField('Process Payment')

class TransferForm(FlaskForm):
    """Form for transfers between accounts"""
    institution_id = SelectField('Financial Institution', validators=[DataRequired()], coerce=int)
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    currency = SelectField('Currency', validators=[DataRequired()], 
                          choices=[('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP'), ('JPY', 'JPY'), ('ETH', 'ETH')])
    description = TextAreaField('Description', validators=[Optional(), Length(max=256)])
    recipient_info = TextAreaField('Recipient Information', validators=[Optional(), Length(max=256)])
    submit = SubmitField('Initiate Transfer')

class BlockchainTransactionForm(FlaskForm):
    """Form for blockchain transactions"""
    amount = DecimalField('Amount (ETH)', validators=[DataRequired(), NumberRange(min=0.001)])
    to_address = StringField('Recipient Ethereum Address', validators=[DataRequired(), Length(min=42, max=42)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=256)])
    use_contract = BooleanField('Use Settlement Contract', default=False)
    submit = SubmitField('Send Transaction')

class FinancialInstitutionForm(FlaskForm):
    """Form for financial institution management"""
    name = StringField('Institution Name', validators=[DataRequired(), Length(min=3, max=128)])
    institution_type = SelectField('Institution Type', validators=[DataRequired()], 
                                  choices=[(t.name, t.value) for t in FinancialInstitutionType])
    api_endpoint = StringField('API Endpoint', validators=[Optional(), Length(max=256)])
    api_key = StringField('API Key', validators=[Optional(), Length(max=256)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Institution')

class PaymentGatewayForm(FlaskForm):
    """Form for payment gateway management"""
    name = StringField('Gateway Name', validators=[DataRequired(), Length(min=3, max=128)])
    gateway_type = SelectField('Gateway Type', validators=[DataRequired()], 
                              choices=[(t.name, t.value) for t in PaymentGatewayType])
    api_endpoint = StringField('API Endpoint', validators=[Optional(), Length(max=256)])
    api_key = StringField('API Key', validators=[Optional(), Length(max=256)])
    webhook_secret = StringField('Webhook Secret', validators=[Optional(), Length(max=256)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Gateway')

class InvitationForm(FlaskForm):
    """Form for creating invitations"""
    email = EmailField('Email', validators=[DataRequired(), Email()])
    invitation_type = SelectField('Invitation Type', validators=[DataRequired()],
                                choices=[(t.name, t.value) for t in InvitationType])
    organization_name = StringField('Organization Name', validators=[DataRequired(), Length(min=2, max=128)])
    message = TextAreaField('Personal Message', validators=[Optional(), Length(max=500)])
    expiration_days = SelectField('Invitation Expires After', validators=[DataRequired()],
                                choices=[(7, '7 Days'), (14, '14 Days'), (30, '30 Days')],
                                coerce=int, default=14)
    submit = SubmitField('Send Invitation')
    
    def validate_email(self, email):
        """Validate that email is not already in use"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('This email is already registered. Please use a different email.')
        
        # Check if a pending invitation already exists
        invitation = Invitation.query.filter_by(email=email.data, status=InvitationStatus.PENDING).first()
        if invitation and invitation.is_valid():
            raise ValidationError('A pending invitation already exists for this email.')

class AcceptInvitationForm(FlaskForm):
    """Form for accepting invitations"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    terms_agreement = BooleanField('I agree to the Terms of Service', validators=[DataRequired()])
    submit = SubmitField('Complete Registration')
    
    def validate_username(self, username):
        """Validate that username is not already taken"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('This username is already taken. Please choose a different one.')

class TestPaymentForm(FlaskForm):
    """Form for testing payment gateway integrations"""
    gateway_id = SelectField('Payment Gateway', validators=[DataRequired()], coerce=int)
    test_scenario = SelectField('Test Scenario', validators=[DataRequired()], 
                             choices=[
                                 ('success', 'Successful Payment'),
                                 ('failure', 'Failed Payment'),
                                 ('3ds', '3D Secure Authentication'),
                                 ('webhook', 'Webhook Processing')
                             ])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)], default=10.00)
    currency = SelectField('Currency', validators=[DataRequired()],
                        choices=[
                            ('USD', 'US Dollar (USD)'),
                            ('EUR', 'Euro (EUR)'),
                            ('GBP', 'British Pound (GBP)'),
                            ('JPY', 'Japanese Yen (JPY)'),
                            ('ETH', 'Ethereum (ETH)'),
                            ('BTC', 'Bitcoin (BTC)')
                        ], default='USD')
    description = TextAreaField('Description', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Start Test Payment')
    
class BankTransferForm(FlaskForm):
    """Form for bank transfers through NVC Global Payment Gateway"""
    # Hidden fields
    transaction_id = HiddenField('Transaction ID', validators=[DataRequired()])
    amount = HiddenField('Amount', validators=[DataRequired()])
    
    # Recipient Information
    recipient_name = StringField('Full Legal Name', validators=[DataRequired(), Length(max=128)])
    recipient_email = EmailField('Email Address', validators=[Optional(), Email()])
    recipient_address = StringField('Address', validators=[DataRequired(), Length(max=256)])
    recipient_city = StringField('City', validators=[DataRequired(), Length(max=64)])
    recipient_state = StringField('State/Province', validators=[Optional(), Length(max=64)])
    recipient_zip = StringField('Postal Code', validators=[DataRequired(), Length(max=16)])
    recipient_country = StringField('Country', validators=[DataRequired(), Length(max=64)])
    
    # Bank Account Information
    bank_name = StringField('Bank Name', validators=[DataRequired(), Length(max=128)])
    account_number = StringField('Account Number', validators=[DataRequired(), Length(max=64)])
    account_type = SelectField('Account Type', validators=[DataRequired()], 
                              choices=[('checking', 'Checking'), ('savings', 'Savings'), 
                                       ('business', 'Business'), ('other', 'Other')])
    transfer_type = SelectField('Transfer Type', validators=[DataRequired()],
                              choices=[('domestic', 'Domestic (Same Country)'), 
                                       ('international', 'International')])
    
    # Domestic Transfer Fields
    routing_number = StringField('Routing/Sort Code', validators=[Optional(), Length(max=64)])
    
    # International Transfer Fields
    swift_bic = StringField('SWIFT/BIC Code', validators=[Optional(), Length(max=32)])
    iban = StringField('IBAN', validators=[Optional(), Length(max=64)])
    
    # Bank Address
    bank_address = StringField('Bank Address', validators=[DataRequired(), Length(max=256)])
    bank_city = StringField('Bank City', validators=[DataRequired(), Length(max=64)])
    bank_state = StringField('Bank State/Province', validators=[Optional(), Length(max=64)])
    bank_country = StringField('Bank Country', validators=[DataRequired(), Length(max=64)])
    
    # Additional International Transfer Information
    intermediary_bank = StringField('Intermediary Bank Name', validators=[Optional(), Length(max=128)])
    intermediary_swift = StringField('Intermediary SWIFT/BIC', validators=[Optional(), Length(max=32)])
    currency = SelectField('Currency for Receipt', validators=[Optional()],
                          choices=[('USD', 'USD - US Dollar'), ('EUR', 'EUR - Euro'), 
                                  ('GBP', 'GBP - British Pound'), ('CAD', 'CAD - Canadian Dollar'),
                                  ('JPY', 'JPY - Japanese Yen'), ('AUD', 'AUD - Australian Dollar'),
                                  ('CHF', 'CHF - Swiss Franc'), ('CNY', 'CNY - Chinese Yuan'),
                                  ('local', 'Local Currency of Recipient\'s Country')])
    purpose = SelectField('Purpose of Payment', validators=[Optional()],
                         choices=[('goods', 'Goods/Services Payment'), ('family', 'Family Support'),
                                 ('gift', 'Gift'), ('investment', 'Investment'),
                                 ('loan', 'Loan Repayment'), ('other', 'Other (Specify)')])
    purpose_detail = StringField('Specify Purpose', validators=[Optional(), Length(max=128)])
    
    # Reference Information
    reference = StringField('Payment Reference', validators=[Optional(), Length(max=128)])
    description = TextAreaField('Payment Note', validators=[Optional(), Length(max=256)])
    
    # Terms Agreement
    terms_agree = BooleanField('Terms Agreement', validators=[DataRequired()])