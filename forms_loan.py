"""
Forms for Loan Management System
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, FloatField, IntegerField, 
    BooleanField, DateField, HiddenField, FileField, SubmitField,
    FieldList, FormField, RadioField, DecimalField
)
from wtforms.validators import DataRequired, Email, Optional, NumberRange, Length, ValidationError
from account_holder_models import CurrencyType
from self_liquidating_loan import (
    LoanStatus, CollateralType, InterestPaymentFrequency, RenewalStatus
)
from loan_underwriting import CreditRating, IndustryRiskCategory, CollateralQuality

# Industry choices for the form
INDUSTRY_CHOICES = [
    ('technology', 'Technology'),
    ('healthcare', 'Healthcare'),
    ('pharmaceuticals', 'Pharmaceuticals'),
    ('utilities', 'Utilities'),
    ('consumer_staples', 'Consumer Staples'),
    ('telecommunications', 'Telecommunications'),
    ('financial_services', 'Financial Services'),
    ('insurance', 'Insurance'),
    ('manufacturing', 'Manufacturing'),
    ('transportation', 'Transportation'),
    ('retail', 'Retail'),
    ('wholesale', 'Wholesale'),
    ('professional_services', 'Professional Services'),
    ('real_estate', 'Real Estate'),
    ('construction', 'Construction'),
    ('energy', 'Energy'),
    ('mining', 'Mining'),
    ('agriculture', 'Agriculture'),
    ('hospitality', 'Hospitality'),
    ('entertainment', 'Entertainment'),
    ('restaurants', 'Restaurants'),
    ('tourism', 'Tourism'),
    ('gambling', 'Gambling'),
    ('cryptocurrency', 'Cryptocurrency'),
    ('other', 'Other')
]

class BorrowerContactForm(FlaskForm):
    """Form for borrower contact information"""
    name = StringField(
        'Contact Name', 
        validators=[Optional(), Length(max=255)]
    )
    title = StringField(
        'Title/Position',
        validators=[Optional(), Length(max=100)]
    )
    email = StringField(
        'Email',
        validators=[Optional(), Email(), Length(max=255)]
    )
    phone = StringField(
        'Phone',
        validators=[Optional(), Length(max=50)]
    )
    is_primary = BooleanField('Primary Contact', default=False)
    
    class Meta:
        csrf = False  # No CSRF for nested forms

class BusinessFinancialForm(FlaskForm):
    """Form for business financial information"""
    fiscal_year = IntegerField(
        'Fiscal Year',
        validators=[Optional(), NumberRange(min=2000, max=2100)]
    )
    annual_revenue = FloatField(
        'Annual Revenue ($)',
        validators=[Optional(), NumberRange(min=0)]
    )
    annual_net_income = FloatField(
        'Annual Net Income ($)',
        validators=[Optional(), NumberRange(min=-1000000000000)]
    )
    annual_debt = FloatField(
        'Total Debt ($)',
        validators=[Optional(), NumberRange(min=0)]
    )
    annual_debt_payments = FloatField(
        'Annual Debt Payments ($)',
        validators=[Optional(), NumberRange(min=0)]
    )
    total_assets = FloatField(
        'Total Assets ($)',
        validators=[Optional(), NumberRange(min=0)]
    )
    total_liabilities = FloatField(
        'Total Liabilities ($)',
        validators=[Optional(), NumberRange(min=0)]
    )
    current_assets = FloatField(
        'Current Assets ($)',
        validators=[Optional(), NumberRange(min=0)]
    )
    current_liabilities = FloatField(
        'Current Liabilities ($)',
        validators=[Optional(), NumberRange(min=0)]
    )
    cash_and_equivalents = FloatField(
        'Cash and Equivalents ($)',
        validators=[Optional(), NumberRange(min=0)]
    )
    
    class Meta:
        csrf = False  # No CSRF for nested forms

class ManagementTeamMemberForm(FlaskForm):
    """Form for management team member information"""
    name = StringField(
        'Name',
        validators=[Optional(), Length(max=255)]
    )
    title = StringField(
        'Title/Position',
        validators=[Optional(), Length(max=100)]
    )
    years_experience = IntegerField(
        'Years of Experience',
        validators=[Optional(), NumberRange(min=0, max=75)]
    )
    education = StringField(
        'Education',
        validators=[Optional(), Length(max=255)]
    )
    previous_companies = StringField(
        'Previous Companies',
        validators=[Optional(), Length(max=255)]
    )
    
    class Meta:
        csrf = False  # No CSRF for nested forms

class CustomizedTermsForm(FlaskForm):
    """Form for customizable loan terms"""
    requested_amount = FloatField(
        'Requested Loan Amount ($)',
        validators=[DataRequired(), NumberRange(min=1000000, max=100000000000)],
        description="Requested loan amount between $1M and $100B"
    )
    preferred_term_years = IntegerField(
        'Preferred Term (Years)',
        validators=[DataRequired(), NumberRange(min=1, max=30)],
        default=10,
        description="Preferred loan term length from 1-30 years"
    )
    preferred_interest_rate = FloatField(
        'Preferred Interest Rate (%)',
        validators=[Optional(), NumberRange(min=0, max=20)],
        description="Your preferred interest rate (if any)"
    )
    preferred_payment_frequency = SelectField(
        'Preferred Payment Frequency',
        choices=[
            (InterestPaymentFrequency.MONTHLY.name, "Monthly"),
            (InterestPaymentFrequency.QUARTERLY.name, "Quarterly"),
            (InterestPaymentFrequency.SEMI_ANNUALLY.name, "Semi-Annually"),
            (InterestPaymentFrequency.ANNUALLY.name, "Annually"),
        ],
        default=InterestPaymentFrequency.QUARTERLY.name
    )
    needs_interest_only_period = BooleanField(
        'Interest-Only Period Needed',
        default=False
    )
    interest_only_period_months = IntegerField(
        'Interest-Only Period (Months)',
        validators=[Optional(), NumberRange(min=0, max=60)],
        default=0,
        description="Number of months for interest-only payments at beginning of loan"
    )
    
    class Meta:
        csrf = False  # No CSRF for nested forms

class ComprehensiveLoanApplicationForm(FlaskForm):
    """Comprehensive form for detailed loan applications"""
    # Basic Loan Information
    loan_amount = FloatField(
        'Loan Amount ($)', 
        validators=[DataRequired(), NumberRange(min=1000000, max=100000000000)],
        description="Loan amount between $1M and $100B"
    )
    
    loan_purpose = TextAreaField(
        'Loan Purpose',
        validators=[DataRequired(), Length(min=10, max=5000)],
        description="Detailed description of how loan proceeds will be used"
    )
    
    currency = SelectField(
        'Currency',
        choices=[(c.name, c.name) for c in CurrencyType if c.name in ["USD", "EUR", "GBP", "CAD", "AUD", "CHF", "JPY"]],
        default="USD",
        validators=[DataRequired()]
    )
    
    interest_rate = FloatField(
        'Interest Rate (%)',
        validators=[Optional(), NumberRange(min=0.0, max=20.0)],
        description="Annual interest rate (if left blank, will be determined by underwriting)"
    )
    
    term_years = IntegerField(
        'Term (Years)',
        validators=[DataRequired(), NumberRange(min=1, max=30)],
        default=10,
        description="Loan term from 1-30 years"
    )
    
    interest_payment_frequency = SelectField(
        'Interest Payment Frequency',
        choices=[
            (InterestPaymentFrequency.MONTHLY.name, "Monthly"),
            (InterestPaymentFrequency.QUARTERLY.name, "Quarterly"),
            (InterestPaymentFrequency.SEMI_ANNUALLY.name, "Semi-Annually"),
            (InterestPaymentFrequency.ANNUALLY.name, "Annually"),
        ],
        default=InterestPaymentFrequency.QUARTERLY.name
    )
    
    # Borrower Information
    borrower_name = StringField(
        'Borrower Legal Name',
        validators=[DataRequired(), Length(min=3, max=255)]
    )
    
    borrower_entity_type = SelectField(
        'Entity Type',
        choices=[
            ('corporation', 'Corporation'),
            ('llc', 'Limited Liability Company (LLC)'),
            ('partnership', 'Partnership'),
            ('limited_partnership', 'Limited Partnership (LP)'),
            ('trust', 'Trust'),
            ('sole_proprietorship', 'Sole Proprietorship'),
            ('non_profit', 'Non-Profit Organization'),
            ('government', 'Government Entity'),
            ('other', 'Other')
        ],
        validators=[DataRequired()]
    )
    
    borrower_industry = SelectField(
        'Primary Industry',
        choices=INDUSTRY_CHOICES,
        validators=[DataRequired()]
    )
    
    years_in_business = IntegerField(
        'Years in Business',
        validators=[DataRequired(), NumberRange(min=0)],
        description="Number of years this business has been operating"
    )
    
    number_of_employees = IntegerField(
        'Number of Employees',
        validators=[Optional(), NumberRange(min=0)],
        description="Total number of current employees"
    )
    
    borrower_tax_id = StringField(
        'Tax ID / EIN',
        validators=[DataRequired(), Length(min=9, max=20)]
    )
    
    borrower_website = StringField(
        'Company Website',
        validators=[Optional(), Length(max=255)]
    )
    
    borrower_address = TextAreaField(
        'Business Address',
        validators=[DataRequired()]
    )
    
    borrower_contact_name = StringField(
        'Primary Contact Name',
        validators=[DataRequired()]
    )
    
    borrower_contact_email = StringField(
        'Contact Email',
        validators=[DataRequired(), Email()]
    )
    
    borrower_contact_phone = StringField(
        'Contact Phone',
        validators=[DataRequired()]
    )
    
    # Additional Contacts
    additional_contacts = FieldList(
        FormField(BorrowerContactForm),
        min_entries=0,
        max_entries=5,
        label="Additional Contacts"
    )
    
    # Business Financial Information
    annual_revenue = FloatField(
        'Annual Revenue ($)',
        validators=[DataRequired(), NumberRange(min=0)],
        description="Annual revenue from most recent fiscal year"
    )
    
    annual_net_income = FloatField(
        'Annual Net Income ($)',
        validators=[DataRequired()],
        description="Annual net income from most recent fiscal year"
    )
    
    years_profitable = IntegerField(
        'Years Profitable',
        validators=[DataRequired(), NumberRange(min=0)],
        description="Number of consecutive years with positive net income"
    )
    
    # Financial History
    financial_history = FieldList(
        FormField(BusinessFinancialForm),
        min_entries=0,
        max_entries=5,
        label="Financial History (Last 5 Years)"
    )
    
    # Credit Information
    credit_rating = SelectField(
        'Credit Rating',
        choices=[
            (CreditRating.AAA.name, "AAA - Highest Rating"),
            (CreditRating.AA.name, "AA - Very High Quality"),
            (CreditRating.A.name, "A - High Quality"),
            (CreditRating.BBB.name, "BBB - Medium Quality"),
            (CreditRating.BB.name, "BB - Somewhat Speculative"),
            (CreditRating.B.name, "B - Speculative"),
            (CreditRating.CCC.name, "CCC - Highly Speculative"),
            (CreditRating.CC.name, "CC - Substantial Risk"),
            (CreditRating.C.name, "C - Extremely Speculative"),
            (CreditRating.D.name, "D - In Default")
        ],
        default=CreditRating.BBB.name,
        validators=[Optional()]
    )
    
    has_previous_bankruptcy = BooleanField(
        'Previous Bankruptcy',
        default=False,
        description="Has the borrower declared bankruptcy in the last 10 years?"
    )
    
    bankruptcy_details = TextAreaField(
        'Bankruptcy Details',
        validators=[Optional(), Length(max=1000)],
        description="If applicable, provide details about any previous bankruptcies"
    )
    
    has_previous_defaults = BooleanField(
        'Previous Defaults',
        default=False,
        description="Has the borrower defaulted on any loans in the last 5 years?"
    )
    
    default_details = TextAreaField(
        'Default Details',
        validators=[Optional(), Length(max=1000)],
        description="If applicable, provide details about any previous defaults"
    )
    
    # Management Team
    management_team = FieldList(
        FormField(ManagementTeamMemberForm),
        min_entries=0,
        max_entries=10,
        label="Management Team"
    )
    
    management_experience_years = IntegerField(
        'Management Experience (Years)',
        validators=[Optional(), NumberRange(min=0, max=75)],
        description="Years of combined relevant experience of key management team"
    )
    
    # Customizable Terms
    customized_terms = FormField(
        CustomizedTermsForm,
        label="Customized Loan Terms"
    )
    
    # Collateral Information
    collateral_available = BooleanField(
        'Collateral Available',
        default=True,
        description="Is collateral available to secure this loan?"
    )
    
    collateral_description = TextAreaField(
        'Collateral Description',
        validators=[Optional(), Length(max=2000)],
        description="Describe the collateral that will secure this loan"
    )
    
    collateral_value = FloatField(
        'Estimated Collateral Value ($)',
        validators=[Optional(), NumberRange(min=0)],
        description="Estimated total value of all collateral"
    )
    
    collateral_types = SelectField(
        'Primary Collateral Type',
        choices=[
            (CollateralType.PROMISSORY_NOTE.name, "Promissory Note"),
            (CollateralType.BUSINESS_ASSETS.name, "Business Assets"),
            (CollateralType.RECEIVABLES.name, "Receivables"),
            (CollateralType.REAL_ESTATE.name, "Real Estate"),
            (CollateralType.EQUIPMENT.name, "Equipment"),
            (CollateralType.INVENTORY.name, "Inventory"),
            (CollateralType.SECURITIES.name, "Securities"),
            (CollateralType.INTELLECTUAL_PROPERTY.name, "Intellectual Property"),
            (CollateralType.OTHER.name, "Other")
        ],
        validators=[Optional()]
    )
    
    has_personal_guarantee = BooleanField(
        'Personal Guarantee Available',
        default=False,
        description="Is a personal guarantee available from the business owner(s)?"
    )
    
    # Business Plan
    has_business_plan = BooleanField(
        'Business Plan Available',
        default=False
    )
    
    business_plan_summary = TextAreaField(
        'Business Plan Summary',
        validators=[Optional(), Length(max=5000)],
        description="Provide a summary of your business plan or growth strategy"
    )
    
    market_analysis = TextAreaField(
        'Market Analysis',
        validators=[Optional(), Length(max=2000)],
        description="Provide a brief analysis of your market position and competition"
    )
    
    # Self-Liquidating Mechanism
    liquidation_mechanism_description = TextAreaField(
        'Liquidation Mechanism Description',
        validators=[Optional()],
        description="Describe any self-liquidating mechanism for this loan"
    )
    
    # Correspondent Banking
    is_available_to_correspondents = BooleanField(
        'Make Available to Correspondent Banks',
        default=True,
        description="Allow offering this loan to correspondent banks"
    )
    
    # Documents
    business_registration_document = FileField('Business Registration Document')
    financial_statements_document = FileField('Financial Statements')
    tax_returns_document = FileField('Tax Returns')
    loan_agreement_document = FileField('Loan Agreement Document')
    promissory_note_document = FileField('Promissory Note Document')
    business_plan_document = FileField('Business Plan Document')
    collateral_document = FileField('Collateral Documentation')
    
    # Additional Information
    additional_information = TextAreaField(
        'Additional Information',
        validators=[Optional(), Length(max=5000)],
        description="Provide any additional information relevant to this loan application"
    )
    
    # Certifications
    certifies_information_accurate = BooleanField(
        'I certify that all information provided is accurate and complete',
        validators=[DataRequired()],
        default=False
    )
    
    certifies_authority = BooleanField(
        'I certify that I have the authority to apply for this loan on behalf of the named entity',
        validators=[DataRequired()],
        default=False
    )
    
    submit = SubmitField('Submit Loan Application')


class LoanCollateralForm(FlaskForm):
    """Form for adding collateral to a loan"""
    loan_id = HiddenField('Loan ID', validators=[DataRequired()])
    
    collateral_type = SelectField(
        'Collateral Type',
        choices=[
            (CollateralType.PROMISSORY_NOTE.name, "Promissory Note"),
            (CollateralType.BUSINESS_ASSETS.name, "Business Assets"),
            (CollateralType.RECEIVABLES.name, "Receivables"),
            (CollateralType.REAL_ESTATE.name, "Real Estate"),
            (CollateralType.EQUIPMENT.name, "Equipment"),
            (CollateralType.INVENTORY.name, "Inventory"),
            (CollateralType.SECURITIES.name, "Securities"),
            (CollateralType.INTELLECTUAL_PROPERTY.name, "Intellectual Property"),
            (CollateralType.OTHER.name, "Other")
        ],
        validators=[DataRequired()]
    )
    
    description = TextAreaField(
        'Description',
        validators=[DataRequired()],
        description="Detailed description of the collateral"
    )
    
    value = FloatField(
        'Collateral Value',
        validators=[DataRequired(), NumberRange(min=0)],
        description="Estimated value in loan currency"
    )
    
    valuation_date = DateField(
        'Valuation Date',
        validators=[DataRequired()],
        description="Date when the collateral was valued"
    )
    
    valuation_source = StringField(
        'Valuation Source',
        validators=[DataRequired()],
        description="Who provided the valuation (e.g., independent appraiser)"
    )
    
    location = TextAreaField(
        'Location',
        validators=[Optional()],
        description="Physical location of the collateral, if applicable"
    )
    
    # Promissory Note Specific Fields
    note_issuer = StringField(
        'Note Issuer',
        validators=[Optional()],
        description="Entity that issued the promissory note"
    )
    
    note_maturity_date = DateField(
        'Note Maturity Date',
        validators=[Optional()],
        description="Maturity date of the promissory note"
    )
    
    note_interest_rate = FloatField(
        'Note Interest Rate',
        validators=[Optional(), NumberRange(min=0)],
        description="Interest rate of the promissory note"
    )
    
    # Business Assets/Receivables Specific Fields
    asset_type = StringField(
        'Asset Type',
        validators=[Optional()],
        description="Type of business asset (for Business Assets collateral)"
    )
    
    receivables_aging = StringField(
        'Receivables Aging',
        validators=[Optional()],
        description="Age of receivables (e.g., 0-30 days, 31-60 days)"
    )
    
    # Documents
    collateral_document = FileField('Collateral Document')
    appraisal_document = FileField('Appraisal Document')
    perfection_document = FileField('Perfection Document (UCC Filing)')
    
    submit = SubmitField('Add Collateral')


class LoanStatusUpdateForm(FlaskForm):
    """Form for updating the status of a loan"""
    loan_id = HiddenField('Loan ID', validators=[DataRequired()])
    
    status = SelectField(
        'Loan Status',
        choices=[
            (LoanStatus.APPLICATION.name, "Application"),
            (LoanStatus.UNDERWRITING.name, "Underwriting"),
            (LoanStatus.APPROVED.name, "Approved"),
            (LoanStatus.FUNDED.name, "Funded"),
            (LoanStatus.ACTIVE.name, "Active"),
            (LoanStatus.RENEWAL_PENDING.name, "Renewal Pending"),
            (LoanStatus.RENEWED.name, "Renewed"),
            (LoanStatus.LIQUIDATING.name, "Liquidating"),
            (LoanStatus.PAID.name, "Paid"),
            (LoanStatus.DEFAULTED.name, "Defaulted"),
            (LoanStatus.CANCELLED.name, "Cancelled")
        ],
        validators=[DataRequired()]
    )
    
    notes = TextAreaField(
        'Status Change Notes',
        validators=[Optional()],
        description="Explanation for the status change"
    )
    
    # Date Fields for Status Changes
    effective_date = DateField(
        'Effective Date',
        validators=[DataRequired()],
        description="When this status change takes effect"
    )
    
    # Approval Fields
    approval_date = DateField(
        'Approval Date',
        validators=[Optional()],
        description="Required if status is Approved"
    )
    
    # Underwriting Score
    underwriting_score = IntegerField(
        'Underwriting Score',
        validators=[Optional(), NumberRange(min=0, max=100)],
        description="Final underwriting score (0-100)"
    )
    
    # Funding Fields
    funding_date = DateField(
        'Funding Date',
        validators=[Optional()],
        description="Required if status is Funded"
    )
    
    funding_amount = FloatField(
        'Funding Amount',
        validators=[Optional(), NumberRange(min=0)],
        description="Amount actually funded (may differ from approved amount)"
    )
    
    # Pricing Adjustment
    rate_adjustment = FloatField(
        'Rate Adjustment',
        validators=[Optional(), NumberRange(min=-2.0, max=5.0)],
        description="Adjustment to standard rate based on underwriting score"
    )
    
    final_interest_rate = FloatField(
        'Final Interest Rate (%)',
        validators=[Optional(), NumberRange(min=0)],
        description="Final approved interest rate"
    )
    
    status_document = FileField('Supporting Document')
    
    submit = SubmitField('Update Status')


class LoanPaymentForm(FlaskForm):
    """Form for recording payments on a loan"""
    loan_id = HiddenField('Loan ID', validators=[DataRequired()])
    
    payment_date = DateField(
        'Payment Date',
        validators=[DataRequired()],
        description="Date the payment was received"
    )
    
    payment_amount = FloatField(
        'Total Payment Amount',
        validators=[DataRequired(), NumberRange(min=0)],
        description="Total amount of the payment"
    )
    
    principal_amount = FloatField(
        'Principal Amount',
        validators=[Optional(), NumberRange(min=0)],
        description="Portion applied to principal"
    )
    
    interest_amount = FloatField(
        'Interest Amount',
        validators=[Optional(), NumberRange(min=0)],
        description="Portion applied to interest"
    )
    
    fees_amount = FloatField(
        'Fees Amount',
        validators=[Optional(), NumberRange(min=0)],
        description="Portion applied to fees"
    )
    
    payment_method = SelectField(
        'Payment Method',
        choices=[
            ('wire', 'Wire Transfer'),
            ('ach', 'ACH'),
            ('check', 'Check'),
            ('internal', 'Internal Transfer'),
            ('other', 'Other')
        ],
        validators=[DataRequired()]
    )
    
    payment_reference = StringField(
        'Payment Reference',
        validators=[Optional()],
        description="Reference number for the payment"
    )
    
    is_self_liquidating_payment = BooleanField(
        'Self-Liquidating Payment',
        default=False,
        description="Payment generated through the self-liquidating mechanism"
    )
    
    liquidation_source = StringField(
        'Liquidation Source',
        validators=[Optional()],
        description="Source of the liquidation funds (if self-liquidating)"
    )
    
    notes = TextAreaField(
        'Payment Notes',
        validators=[Optional()]
    )
    
    payment_document = FileField('Payment Receipt/Confirmation')
    
    submit = SubmitField('Record Payment')


class LoanRenewalForm(FlaskForm):
    """Form for handling loan renewals"""
    loan_id = HiddenField('Loan ID', validators=[DataRequired()])
    
    request_date = DateField(
        'Request Date',
        validators=[DataRequired()],
        description="Date the renewal was requested"
    )
    
    new_interest_rate = FloatField(
        'New Interest Rate (%)',
        validators=[Optional(), NumberRange(min=0)],
        description="Leave blank to keep current rate"
    )
    
    additional_terms = TextAreaField(
        'Additional Terms',
        validators=[Optional()],
        description="Any additional terms for the renewal"
    )
    
    status = SelectField(
        'Renewal Status',
        choices=[
            (RenewalStatus.REQUESTED.name, "Requested"),
            (RenewalStatus.UNDER_REVIEW.name, "Under Review"),
            (RenewalStatus.APPROVED.name, "Approved"),
            (RenewalStatus.EXECUTED.name, "Executed"),
            (RenewalStatus.DECLINED.name, "Declined")
        ],
        validators=[DataRequired()],
        default=RenewalStatus.REQUESTED.name
    )
    
    status_reason = TextAreaField(
        'Status Reason',
        validators=[Optional()],
        description="Reason for approval or decline"
    )
    
    renewal_agreement_document = FileField('Renewal Agreement Document')
    
    submit = SubmitField('Submit Renewal Request')


class LoanCorrespondentAvailabilityForm(FlaskForm):
    """Form for managing correspondent bank availability for loans"""
    loan_id = HiddenField('Loan ID', validators=[DataRequired()])
    
    correspondent_bank_id = SelectField(
        'Correspondent Bank',
        validators=[DataRequired()],
        coerce=int
    )
    
    offered_date = DateField(
        'Offering Date',
        validators=[DataRequired()],
        description="Date when the loan is offered to the correspondent bank"
    )
    
    expiration_date = DateField(
        'Expiration Date',
        validators=[DataRequired()],
        description="Date when the offer expires"
    )
    
    participation_percentage = FloatField(
        'Participation Percentage (%)',
        validators=[DataRequired(), NumberRange(min=1, max=100)],
        description="Percentage of the loan offered to this correspondent"
    )
    
    special_terms = TextAreaField(
        'Special Terms',
        validators=[Optional()],
        description="Any special terms for this correspondent"
    )
    
    submit = SubmitField('Offer to Correspondent Bank')