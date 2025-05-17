"""
Forms for Capital Injection and Bank Recapitalization
This module provides forms for financial institution recapitalization
and equity injection programs.
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, FloatField, IntegerField, SelectField, TextAreaField,
    BooleanField, DateField, SubmitField, MultipleFileField, RadioField,
    DecimalField
)
from wtforms.validators import DataRequired, Optional, NumberRange, Email, Length, ValidationError
from models.capital_injection import (
    CapitalType, InstitutionType, InvestmentStructure, 
    RegulatoryConcern, RegulatoryFramework
)


class FinancialInstitutionProfileForm(FlaskForm):
    """Form for financial institution profile for capital injection program"""
    # Institution information
    institution_name = StringField('Institution Name', validators=[DataRequired(), Length(min=2, max=255)])
    institution_type = SelectField('Institution Type', validators=[DataRequired()], 
                                   choices=[(t.value, t.value.replace('_', ' ').title()) for t in InstitutionType])
    registration_number = StringField('Registration Number', validators=[Optional(), Length(max=100)])
    tax_id = StringField('Tax ID', validators=[Optional(), Length(max=100)])
    year_established = IntegerField('Year Established', validators=[Optional(), NumberRange(min=1800, max=2025)])
    headquarters_country = StringField('Headquarters Country', validators=[DataRequired(), Length(max=100)])
    headquarters_city = StringField('Headquarters City', validators=[DataRequired(), Length(max=100)])
    
    # Contact information
    primary_contact_name = StringField('Primary Contact Name', validators=[DataRequired(), Length(max=255)])
    primary_contact_title = StringField('Primary Contact Title', validators=[DataRequired(), Length(max=255)])
    primary_contact_email = StringField('Primary Contact Email', validators=[DataRequired(), Email(), Length(max=255)])
    primary_contact_phone = StringField('Primary Contact Phone', validators=[DataRequired(), Length(max=50)])
    
    # Financial information
    total_assets = FloatField('Total Assets (USD millions)', validators=[DataRequired(), NumberRange(min=0)])
    total_liabilities = FloatField('Total Liabilities (USD millions)', validators=[DataRequired(), NumberRange(min=0)])
    total_equity = FloatField('Total Equity (USD millions)', validators=[Optional(), NumberRange(min=0)])
    tier1_capital = FloatField('Tier 1 Capital (USD millions)', validators=[Optional(), NumberRange(min=0)])
    tier2_capital = FloatField('Tier 2 Capital (USD millions)', validators=[Optional(), NumberRange(min=0)])
    risk_weighted_assets = FloatField('Risk Weighted Assets (USD millions)', validators=[Optional(), NumberRange(min=0)])
    
    # Regulatory information
    primary_regulator = StringField('Primary Regulator', validators=[DataRequired(), Length(max=255)])
    regulatory_framework = SelectField('Regulatory Framework', validators=[DataRequired()],
                                       choices=[(t.value, t.value.replace('_', ' ').title()) for t in RegulatoryFramework])
    current_capital_ratio = FloatField('Current Total Capital Ratio (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    current_tier1_ratio = FloatField('Current Tier 1 Capital Ratio (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    current_leverage_ratio = FloatField('Current Leverage Ratio (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    required_capital_ratio = FloatField('Required Capital Ratio (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    
    # Documents
    financial_statements = MultipleFileField('Financial Statements (Last 3 Years)', validators=[Optional()])
    regulatory_reports = MultipleFileField('Recent Regulatory Reports', validators=[Optional()])
    organizational_chart = MultipleFileField('Organizational Chart', validators=[Optional()])
    banking_license = MultipleFileField('Banking License', validators=[Optional()])
    
    submit = SubmitField('Save Institution Profile')
    
    def validate_total_equity(self, field):
        """Validate that total equity matches assets minus liabilities"""
        if field.data is not None and self.total_assets.data is not None and self.total_liabilities.data is not None:
            expected_equity = self.total_assets.data - self.total_liabilities.data
            if abs(field.data - expected_equity) > 0.01 * expected_equity:  # Allow 1% deviation
                raise ValidationError('Total equity should approximately equal total assets minus total liabilities')


class CapitalInjectionApplicationForm(FlaskForm):
    """Form for capital injection application"""
    # Application details
    capital_type = SelectField('Capital Type', validators=[DataRequired()],
                              choices=[(t.value, t.value.replace('_', ' ').title()) for t in CapitalType])
    investment_structure = SelectField('Investment Structure', validators=[DataRequired()],
                                      choices=[(t.value, t.value.replace('_', ' ').title()) for t in InvestmentStructure])
    
    # Financial request
    requested_amount = DecimalField('Requested Amount (USD millions)', 
                                  validators=[DataRequired(), NumberRange(min=10, max=10000)],
                                  places=2)
    minimum_acceptable_amount = DecimalField('Minimum Acceptable Amount (USD millions)', 
                                           validators=[Optional(), NumberRange(min=10, max=10000)],
                                           places=2)
    term_years = IntegerField('Term (Years)', validators=[Optional(), NumberRange(min=1, max=30)])
    proposed_interest_rate = FloatField('Proposed Interest Rate (%)', validators=[Optional(), NumberRange(min=0, max=20)])
    proposed_dividend_rate = FloatField('Proposed Dividend Rate (%)', validators=[Optional(), NumberRange(min=0, max=20)])
    
    # Regulatory information
    regulatory_concern = SelectField('Primary Regulatory Concern', validators=[Optional()],
                                    choices=[('', 'Select Concern')] + 
                                    [(t.value, t.value.replace('_', ' ').title()) for t in RegulatoryConcern])
    target_capital_ratio = FloatField('Target Capital Ratio (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    regulator_approval_required = BooleanField('Regulator Approval Required', default=True)
    regulator_approval_received = BooleanField('Regulator Approval Already Received', default=False)
    regulator_approval_date = DateField('Regulator Approval Date', validators=[Optional()])
    
    # Use of funds
    use_of_funds = TextAreaField('Use of Funds', validators=[DataRequired(), Length(min=100, max=5000)])
    business_plan_summary = TextAreaField('Business Plan Summary', validators=[DataRequired(), Length(min=100, max=10000)])
    expected_impact = TextAreaField('Expected Impact on Institution', validators=[DataRequired(), Length(min=100, max=5000)])
    
    # Risk assessment
    risk_assessment = TextAreaField('Risk Assessment', validators=[Optional(), Length(max=5000)])
    mitigating_factors = TextAreaField('Mitigating Factors', validators=[Optional(), Length(max=5000)])
    
    # Documents
    capital_plan = MultipleFileField('Capital Plan', validators=[Optional()])
    business_plan = MultipleFileField('Business Plan', validators=[Optional()])
    financial_projections = MultipleFileField('Financial Projections', validators=[Optional()])
    regulator_correspondence = MultipleFileField('Regulator Correspondence', validators=[Optional()])
    
    # Submission options
    save_draft = SubmitField('Save as Draft')
    submit_application = SubmitField('Submit Application')
    
    def validate_minimum_acceptable_amount(self, field):
        """Validate that minimum amount is less than requested amount"""
        if field.data is not None and self.requested_amount.data is not None:
            if field.data > self.requested_amount.data:
                raise ValidationError('Minimum acceptable amount cannot be greater than requested amount')


class ApplicationReviewForm(FlaskForm):
    """Form for reviewing capital injection applications"""
    status = SelectField('Update Status', validators=[DataRequired()])
    analyst_notes = TextAreaField('Analyst Notes', validators=[Optional(), Length(max=5000)])
    committee_notes = TextAreaField('Committee Notes', validators=[Optional(), Length(max=5000)])
    approved_amount = FloatField('Approved Amount (USD millions)', validators=[Optional(), NumberRange(min=10, max=10000)])
    
    # Approval terms
    interest_rate = FloatField('Interest Rate (%)', validators=[Optional(), NumberRange(min=0, max=20)])
    dividend_rate = FloatField('Dividend Rate (%)', validators=[Optional(), NumberRange(min=0, max=20)])
    approved_term_years = IntegerField('Approved Term (Years)', validators=[Optional(), NumberRange(min=1, max=30)])
    special_conditions = TextAreaField('Special Conditions', validators=[Optional(), Length(max=5000)])
    
    update = SubmitField('Update Application')
    approve = SubmitField('Approve Application')
    reject = SubmitField('Reject Application')
    request_info = SubmitField('Request Additional Information')


class DocumentUploadForm(FlaskForm):
    """Form for uploading documents related to capital injection"""
    document_type = SelectField('Document Type', validators=[DataRequired()], 
                               choices=[
                                   ('financial_statement', 'Financial Statement'),
                                   ('regulatory_report', 'Regulatory Report'),
                                   ('business_plan', 'Business Plan'),
                                   ('capital_plan', 'Capital Plan'),
                                   ('regulator_correspondence', 'Regulator Correspondence'),
                                   ('financial_projections', 'Financial Projections'),
                                   ('organizational_chart', 'Organizational Chart'),
                                   ('banking_license', 'Banking License'),
                                   ('other', 'Other Document')
                               ])
    document_name = StringField('Document Name', validators=[DataRequired(), Length(max=255)])
    document_file = MultipleFileField('Document File', validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=1000)])
    upload = SubmitField('Upload Document')


class CapitalInjectionTermsForm(FlaskForm):
    """Form for creating capital injection terms"""
    capital_type = SelectField('Capital Type', validators=[DataRequired()],
                              choices=[(t.value, t.value.replace('_', ' ').title()) for t in CapitalType])
    investment_structure = SelectField('Investment Structure', validators=[DataRequired()],
                                      choices=[(t.value, t.value.replace('_', ' ').title()) for t in InvestmentStructure])
    min_amount = FloatField('Minimum Amount (USD millions)', validators=[DataRequired(), NumberRange(min=10, max=10000)])
    max_amount = FloatField('Maximum Amount (USD millions)', validators=[DataRequired(), NumberRange(min=10, max=10000)])
    min_term_years = IntegerField('Minimum Term (Years)', validators=[Optional(), NumberRange(min=1, max=30)])
    max_term_years = IntegerField('Maximum Term (Years)', validators=[Optional(), NumberRange(min=1, max=30)])
    interest_rate_range_min = FloatField('Minimum Interest Rate (%)', validators=[Optional(), NumberRange(min=0, max=20)])
    interest_rate_range_max = FloatField('Maximum Interest Rate (%)', validators=[Optional(), NumberRange(min=0, max=20)])
    dividend_rate_range_min = FloatField('Minimum Dividend Rate (%)', validators=[Optional(), NumberRange(min=0, max=20)])
    dividend_rate_range_max = FloatField('Maximum Dividend Rate (%)', validators=[Optional(), NumberRange(min=0, max=20)])
    is_active = BooleanField('Active', default=True)
    details = TextAreaField('Additional Terms and Conditions', validators=[Optional(), Length(max=10000)])
    terms_document = MultipleFileField('Terms Document', validators=[Optional()])
    
    save = SubmitField('Save Terms')