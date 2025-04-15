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