from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, SelectField, DateField
from wtforms import BooleanField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, ValidationError
from datetime import date, timedelta

class StandbyLetterOfCreditForm(FlaskForm):
    """Form for creating Standby Letter of Credit (SBLC)"""
    # Basic Information
    amount = DecimalField('Amount', validators=[DataRequired()], places=2)
    currency = SelectField('Currency', choices=[
        ('USD', 'US Dollar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'British Pound (GBP)'),
        ('JPY', 'Japanese Yen (JPY)'),
        ('CHF', 'Swiss Franc (CHF)'),
        ('CNY', 'Chinese Yuan (CNY)'),
        ('AUD', 'Australian Dollar (AUD)'),
        ('CAD', 'Canadian Dollar (CAD)'),
        ('SGD', 'Singapore Dollar (SGD)'),
        ('NVCT', 'NVC Token (NVCT)')
    ], validators=[DataRequired()])
    
    issue_date = DateField('Issue Date', validators=[DataRequired()], default=date.today)
    expiry_date = DateField('Expiry Date', validators=[DataRequired()], 
                            default=lambda: date.today() + timedelta(days=365))
    expiry_place = StringField('Place of Expiry', validators=[DataRequired(), Length(max=100)])
    applicable_law = StringField('Applicable Law/Jurisdiction', validators=[DataRequired(), Length(max=100)],
                               default="Laws of England and Wales")
    partial_drawings = BooleanField('Allow Partial Drawings', default=True)
    multiple_drawings = BooleanField('Allow Multiple Drawings', default=True)
    
    # Applicant Information
    applicant_id = SelectField('Applicant', coerce=int, validators=[DataRequired()])
    applicant_account_number = StringField('Applicant Account Number', validators=[DataRequired(), Length(max=50)])
    applicant_contact_info = StringField('Contact Information', validators=[Optional(), Length(max=200)])
    
    # Beneficiary Information
    beneficiary_name = StringField('Beneficiary Name', validators=[DataRequired(), Length(max=255)])
    beneficiary_address = TextAreaField('Beneficiary Address', validators=[DataRequired(), Length(max=500)])
    beneficiary_account_number = StringField('Beneficiary Account Number', validators=[Optional(), Length(max=50)])
    beneficiary_bank_name = StringField("Beneficiary's Bank Name", validators=[DataRequired(), Length(max=255)])
    beneficiary_bank_swift = StringField("Beneficiary's Bank SWIFT Code", validators=[DataRequired(), Length(min=8, max=11)])
    beneficiary_bank_address = TextAreaField("Beneficiary's Bank Address", validators=[Optional(), Length(max=500)])
    
    # Underlying Transaction
    contract_name = StringField('Contract/Agreement Name', validators=[DataRequired(), Length(max=255)])
    contract_date = DateField('Contract/Agreement Date', validators=[DataRequired()], default=date.today)
    contract_details = TextAreaField('Contract/Agreement Details', validators=[Optional(), Length(max=1000)])
    
    # Terms and Conditions
    special_conditions = TextAreaField('Special Conditions', validators=[Optional(), Length(max=2000)])
    confirm_terms = BooleanField('Accept Terms and Conditions', validators=[DataRequired()])
    
    # Hidden field for saving as draft
    is_draft = HiddenField('Is Draft', default='false')
    
    # Submit buttons
    submit = SubmitField('Create SBLC')
    save_draft = SubmitField('Save as Draft')
    
    def validate_expiry_date(self, field):
        """Validate that expiry date is in the future"""
        if field.data <= self.issue_date.data:
            raise ValidationError("Expiry date must be after issue date")
        
        if field.data <= date.today():
            raise ValidationError("Expiry date must be in the future")

    def __init__(self, *args, **kwargs):
        super(StandbyLetterOfCreditForm, self).__init__(*args, **kwargs)
        try:
            from models import AccountHolder
            # Populate applicant choices from account holders
            account_holders = AccountHolder.query.filter_by(kyc_verified=True, aml_verified=True).all()
            self.applicant_id.choices = [(ah.id, ah.name) for ah in account_holders]
            
            # Add empty option
            self.applicant_id.choices.insert(0, (0, '-- Select Applicant --'))
        except Exception as e:
            print(f"Error populating SBLC form: {str(e)}")
            self.applicant_id.choices = [(0, '-- Select Applicant --')]