"""
Forms for Self-Liquidating Loan Management
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, FloatField, IntegerField, 
    BooleanField, DateField, HiddenField, FileField, SubmitField
)
from wtforms.validators import DataRequired, Email, Optional, NumberRange, Length
from account_holder_models import CurrencyType
from self_liquidating_loan import (
    LoanStatus, CollateralType, InterestPaymentFrequency, RenewalStatus
)


class SelfLiquidatingLoanApplicationForm(FlaskForm):
    """Form for creating a new self-liquidating loan application"""
    # Basic Loan Information
    loan_amount = FloatField(
        'Loan Amount', 
        validators=[DataRequired(), NumberRange(min=10000000, max=10000000000)],
        description="Loan amount between $10M and $10B"
    )
    
    currency = SelectField(
        'Currency',
        choices=[(c.name, c.name) for c in CurrencyType if c.name in ["USD", "EUR", "GBP"]],
        default="USD",
        validators=[DataRequired()]
    )
    
    interest_rate = FloatField(
        'Interest Rate (%)',
        validators=[DataRequired(), NumberRange(min=5.0, max=7.0)],
        default=5.75,
        description="Annual interest rate from 5% to 7%"
    )
    
    term_years = IntegerField(
        'Term (Years)',
        validators=[DataRequired(), NumberRange(min=10, max=10)],
        default=10,
        description="Standard term is 10 years"
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
            ('trust', 'Trust'),
            ('other', 'Other')
        ],
        validators=[DataRequired()]
    )
    
    borrower_tax_id = StringField(
        'Tax ID / EIN',
        validators=[DataRequired(), Length(min=9, max=20)]
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
    
    # Liquidation Mechanism
    liquidation_mechanism_description = TextAreaField(
        'Liquidation Mechanism Description',
        validators=[DataRequired()],
        description="Describe the proprietary inter-company loan servicing and management system"
    )
    
    # Correspondent Banking
    is_available_to_correspondents = BooleanField(
        'Make Available to Correspondent Banks',
        default=True,
        description="Allow offering this loan to correspondent banks as fully cash backed"
    )
    
    # Documents
    loan_agreement_document = FileField('Loan Agreement Document')
    promissory_note_document = FileField('Promissory Note Document')
    
    submit = SubmitField('Submit Loan Application')


class LoanCollateralForm(FlaskForm):
    """Form for adding collateral to a self-liquidating loan"""
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
    """Form for updating the status of a self-liquidating loan"""
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
    
    status_document = FileField('Supporting Document')
    
    submit = SubmitField('Update Status')


class LoanPaymentForm(FlaskForm):
    """Form for recording payments on a self-liquidating loan"""
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