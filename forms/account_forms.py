"""
Account Management Forms
This module provides forms for account creation and management.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Length, Optional


class AddressForm(FlaskForm):
    """Form for collecting address information"""
    line1 = StringField('Address Line 1', validators=[DataRequired(), Length(max=255)])
    line2 = StringField('Address Line 2', validators=[Optional(), Length(max=255)])
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    region = StringField('State/Province/Region', validators=[DataRequired(), Length(max=100)])
    zip = StringField('Postal/Zip Code', validators=[DataRequired(), Length(max=20)])
    country = StringField('Country Code (2-letter)', validators=[DataRequired(), Length(min=2, max=2)])
    submit = SubmitField('Save Address')


class PhoneForm(FlaskForm):
    """Form for collecting phone information"""
    number = StringField('Phone Number', validators=[DataRequired(), Length(max=50)])
    is_mobile = BooleanField('Mobile Number')
    is_primary = BooleanField('Primary Number')
    submit = SubmitField('Save Phone')


class AccountForm(FlaskForm):
    """Form for creating new bank accounts"""
    account_name = StringField('Account Name', validators=[Optional(), Length(max=255)])
    account_type = SelectField('Account Type', validators=[DataRequired()])
    currency = SelectField('Currency', validators=[DataRequired()])
    submit = SubmitField('Create Account')


class AccountHolderForm(FlaskForm):
    """Form for creating/updating account holder profile"""
    name = StringField('Full Name', validators=[DataRequired(), Length(max=255)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    is_business = BooleanField('Business Account')
    business_name = StringField('Business Name', validators=[Optional(), Length(max=255)])
    business_type = StringField('Business Type', validators=[Optional(), Length(max=100)])
    tax_id = StringField('Tax ID', validators=[Optional(), Length(max=50)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=50)])
    broker = StringField('Broker Code', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Save Profile')