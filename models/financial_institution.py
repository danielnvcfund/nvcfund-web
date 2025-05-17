"""
Financial institution recapitalization and equity injection models
"""
# Import the Capital Injection models
from models.capital_injection import (
    FinancialInstitutionProfile, InstitutionDocument,
    CapitalInjectionApplication, ApplicationStatusUpdate,
    CapitalInjectionTerm, ApplicationStatus,
    CapitalType, InstitutionType, InvestmentStructure, 
    RegulatoryConcern, RegulatoryFramework
)

# This module is a simple import wrapper to ensure the models are loaded properly
# All models are now accessible through models.financial_institution