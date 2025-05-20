"""
Account Forms Module
This module provides forms for account creation and management
"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

from account_holder_models import AccountType, CurrencyType


class AddressForm(FlaskForm):
    """Form for collecting address information"""
    line1 = StringField('Address Line 1', validators=[DataRequired(), Length(max=255)])
    line2 = StringField('Address Line 2', validators=[Optional(), Length(max=255)])
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    region = StringField('State/Province', validators=[DataRequired(), Length(max=100)])
    zip = StringField('Postal Code', validators=[DataRequired(), Length(max=20)])
    country = SelectField('Country', choices=[
        ('US', 'United States'),
        ('CA', 'Canada'),
        ('GB', 'United Kingdom'),
        ('AU', 'Australia'),
        ('DE', 'Germany'),
        ('FR', 'France'),
        ('JP', 'Japan'),
        ('CN', 'China'),
        ('IN', 'India'),
        ('BR', 'Brazil'),
        ('RU', 'Russia'),
        ('MX', 'Mexico'),
        ('IT', 'Italy'),
        ('ES', 'Spain'),
        ('KR', 'South Korea'),
        ('NG', 'Nigeria'),
        ('ZA', 'South Africa'),
        ('AE', 'United Arab Emirates'),
        ('SG', 'Singapore'),
        ('CH', 'Switzerland'),
        ('SA', 'Saudi Arabia'),
        ('GL', 'Global')
    ], validators=[DataRequired()])


class PhoneForm(FlaskForm):
    """Form for collecting phone number information"""
    name = SelectField('Phone Type', choices=[
        ('Mobile', 'Mobile'),
        ('Home', 'Home'),
        ('Work', 'Work'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    number = StringField('Phone Number', validators=[DataRequired(), Length(max=50)])
    is_primary = BooleanField('Primary Phone Number')
    is_mobile = BooleanField('This is a mobile number')


class AccountHolderForm(FlaskForm):
    """Form for creating/editing an account holder"""
    name = StringField('Full Name', validators=[DataRequired(), Length(max=255)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    is_business = BooleanField('This is a business account')
    business_name = StringField('Business Name', validators=[Optional(), Length(max=255)])
    business_type = SelectField('Business Type', choices=[
        ('', 'Select business type'),
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('partnership', 'Partnership'),
        ('corporation', 'Corporation'),
        ('llc', 'Limited Liability Company (LLC)'),
        ('nonprofit', 'Non-profit Organization'),
        ('financial_institution', 'Financial Institution'),
        ('government', 'Government Entity'),
        ('other', 'Other')
    ], validators=[Optional()])
    tax_id = StringField('Tax ID / EIN', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Create Account Holder')


class AccountForm(FlaskForm):
    """Form for creating a new bank account"""
    account_name = StringField('Account Name (Optional)', validators=[Optional(), Length(max=255)])
    account_type = SelectField('Account Type', choices=[], validators=[DataRequired()])
    currency = SelectField('Currency', choices=[], validators=[DataRequired()])
    submit = SubmitField('Open Account')