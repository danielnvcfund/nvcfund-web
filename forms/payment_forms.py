"""
Payment Forms
This module provides forms for payment operations like transfers and deposits
"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class TransferForm(FlaskForm):
    """Form for transferring funds between accounts"""
    from_account = SelectField('From Account', validators=[DataRequired()])
    to_account_number = StringField('To Account Number', validators=[DataRequired(), Length(min=10, max=50)])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    description = TextAreaField('Description', validators=[Length(max=255)])
    submit = SubmitField('Transfer Funds')
    
    def __init__(self, *args, **kwargs):
        """Initialize the form with user accounts"""
        user_accounts = kwargs.pop('user_accounts', [])
        super(TransferForm, self).__init__(*args, **kwargs)
        
        # Populate the from_account select field with user accounts
        if user_accounts:
            self.from_account.choices = [
                (
                    account.account_number, 
                    f"{account.account_name} ({account.account_number}) - {account.currency.name} {account.balance:,.2f}"
                ) 
                for account in user_accounts
            ]

class DepositForm(FlaskForm):
    """Form for depositing funds into an account"""
    to_account = SelectField('To Account', validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    payment_method = SelectField('Payment Method', 
                                choices=[
                                    ('BANK_WIRE', 'Bank Wire'), 
                                    ('CASH', 'Cash Deposit'),
                                    ('CHECK', 'Check Deposit'),
                                    ('ACH', 'ACH Transfer'),
                                    ('SWIFT', 'SWIFT Transfer'),
                                    ('INTERNAL', 'Internal Transfer')
                                ],
                                validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Length(max=255)])
    submit = SubmitField('Make Deposit')
    
    def __init__(self, *args, **kwargs):
        """Initialize the form with user accounts"""
        user_accounts = kwargs.pop('user_accounts', [])
        super(DepositForm, self).__init__(*args, **kwargs)
        
        # Populate the to_account select field with user accounts
        if user_accounts:
            self.to_account.choices = [
                (
                    account.account_number, 
                    f"{account.account_name} ({account.account_number}) - {account.currency.name} {account.balance:,.2f}"
                ) 
                for account in user_accounts
            ]