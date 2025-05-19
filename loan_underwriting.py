"""
Loan Underwriting Scoring Module for NVC Banking Platform

This module provides functionality for scoring and evaluating loan applications
to make accurate pricing decisions based on borrower information and risk factors.
"""

from enum import Enum
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Define scoring categories
class CreditRating(Enum):
    """Standard credit rating classifications"""
    AAA = "AAA"  # Highest rating
    AA = "AA"
    A = "A"
    BBB = "BBB"  # Investment grade threshold
    BB = "BB"
    B = "B"
    CCC = "CCC"
    CC = "CC"
    C = "C"
    D = "D"  # Default


class IndustryRiskCategory(Enum):
    """Industry risk classifications"""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    VERY_HIGH = "very_high"


class CollateralQuality(Enum):
    """Collateral quality classifications"""
    EXCELLENT = "excellent"
    STRONG = "strong"
    GOOD = "good"
    SATISFACTORY = "satisfactory"
    FAIR = "fair"
    WEAK = "weak"
    POOR = "poor"


class LoanGrade(Enum):
    """Final loan grade classifications"""
    PRIME_PLUS = "prime_plus"       # 90-100 score
    PRIME = "prime"                 # 80-89 score
    NEAR_PRIME = "near_prime"       # 70-79 score
    STANDARD = "standard"           # 60-69 score
    STANDARD_MINUS = "standard_minus"  # 50-59 score
    SUBSTANDARD = "substandard"     # 40-49 score
    WATCH = "watch"                 # 30-39 score
    SPECIAL_MENTION = "special_mention"  # 20-29 score
    SUBPAR = "subpar"               # 0-19 score


# Industry risk mappings
INDUSTRY_RISK_MAPPING = {
    # Lower risk industries
    "technology": IndustryRiskCategory.LOW,
    "healthcare": IndustryRiskCategory.LOW,
    "pharmaceuticals": IndustryRiskCategory.LOW,
    "utilities": IndustryRiskCategory.VERY_LOW,
    "consumer_staples": IndustryRiskCategory.LOW,
    "telecommunications": IndustryRiskCategory.LOW,
    
    # Moderate risk industries
    "financial_services": IndustryRiskCategory.MODERATE,
    "insurance": IndustryRiskCategory.MODERATE,
    "manufacturing": IndustryRiskCategory.MODERATE,
    "transportation": IndustryRiskCategory.MODERATE,
    "retail": IndustryRiskCategory.MODERATE,
    "wholesale": IndustryRiskCategory.MODERATE,
    "professional_services": IndustryRiskCategory.MODERATE,
    
    # Higher risk industries
    "real_estate": IndustryRiskCategory.ELEVATED,
    "construction": IndustryRiskCategory.ELEVATED,
    "energy": IndustryRiskCategory.ELEVATED,
    "mining": IndustryRiskCategory.HIGH,
    "agriculture": IndustryRiskCategory.ELEVATED,
    "hospitality": IndustryRiskCategory.HIGH,
    "entertainment": IndustryRiskCategory.HIGH,
    "restaurants": IndustryRiskCategory.HIGH,
    
    # Highest risk industries
    "tourism": IndustryRiskCategory.VERY_HIGH,
    "gambling": IndustryRiskCategory.VERY_HIGH,
    "cryptocurrency": IndustryRiskCategory.VERY_HIGH,
}


# Scoring weights for different factors
SCORING_WEIGHTS = {
    "financial_standing": 25,        # Financial metrics, ratios
    "credit_history": 20,            # Credit rating, payment history
    "industry_factor": 15,           # Industry risk assessment
    "collateral_quality": 15,        # Quality of loan security
    "management_experience": 10,     # Management team experience
    "business_plan": 5,              # Business plan quality
    "market_conditions": 5,          # Current market environment
    "relationship_history": 5,       # History with the bank
}


def calculate_debt_service_coverage_ratio(annual_net_income: float, annual_debt_payments: float) -> float:
    """Calculate the Debt Service Coverage Ratio"""
    if annual_debt_payments <= 0:
        return 5.0  # Cap at 5.0 for no debt
    
    ratio = annual_net_income / annual_debt_payments
    return min(ratio, 5.0)  # Cap at 5.0


def calculate_loan_to_value_ratio(loan_amount: float, collateral_value: float) -> float:
    """Calculate the Loan-to-Value ratio"""
    if collateral_value <= 0:
        return 1.0  # 100% LTV if no collateral
    
    ratio = loan_amount / collateral_value
    return ratio


def score_financial_standing(
    annual_revenue: float, 
    annual_net_income: float,
    annual_debt: float,
    annual_debt_payments: float,
    years_profitable: int,
    current_ratio: float = None,
    quick_ratio: float = None,
    debt_to_equity: float = None
) -> Tuple[int, Dict[str, Any]]:
    """
    Score the financial standing of the borrower
    Returns a score from 0-100 and breakdown of subscores
    """
    score = 0
    breakdown = {}
    
    # Revenue size assessment (0-15 points)
    if annual_revenue >= 100000000:  # $100M+
        revenue_score = 15
    elif annual_revenue >= 50000000:  # $50M+
        revenue_score = 13
    elif annual_revenue >= 10000000:  # $10M+
        revenue_score = 10
    elif annual_revenue >= 5000000:   # $5M+
        revenue_score = 7
    elif annual_revenue >= 1000000:   # $1M+
        revenue_score = 5
    else:
        revenue_score = 3
    
    score += revenue_score
    breakdown["revenue_size"] = revenue_score
    
    # Profitability assessment (0-25 points)
    profit_margin = (annual_net_income / annual_revenue) if annual_revenue > 0 else 0
    
    if profit_margin >= 0.20:  # 20%+ profit margin
        profit_score = 25
    elif profit_margin >= 0.15:
        profit_score = 20
    elif profit_margin >= 0.10:
        profit_score = 15
    elif profit_margin >= 0.05:
        profit_score = 10
    elif profit_margin > 0:
        profit_score = 5
    else:
        profit_score = 0
    
    score += profit_score
    breakdown["profitability"] = profit_score
    
    # Years of profitability (0-15 points)
    if years_profitable >= 10:
        years_score = 15
    elif years_profitable >= 7:
        years_score = 12
    elif years_profitable >= 5:
        years_score = 10
    elif years_profitable >= 3:
        years_score = 7
    elif years_profitable >= 1:
        years_score = 5
    else:
        years_score = 0
    
    score += years_score
    breakdown["years_profitable"] = years_score
    
    # Debt service coverage ratio (0-25 points)
    dscr = calculate_debt_service_coverage_ratio(annual_net_income, annual_debt_payments)
    
    if dscr >= 2.0:
        dscr_score = 25
    elif dscr >= 1.5:
        dscr_score = 20
    elif dscr >= 1.25:
        dscr_score = 15
    elif dscr >= 1.1:
        dscr_score = 10
    elif dscr >= 1.0:
        dscr_score = 5
    else:
        dscr_score = 0
    
    score += dscr_score
    breakdown["debt_service_coverage"] = dscr_score
    
    # Leverage assessment (0-20 points)
    if debt_to_equity is not None:
        if debt_to_equity <= 0.5:
            leverage_score = 20
        elif debt_to_equity <= 1.0:
            leverage_score = 15
        elif debt_to_equity <= 2.0:
            leverage_score = 10
        elif debt_to_equity <= 3.0:
            leverage_score = 5
        else:
            leverage_score = 0
        
        score += leverage_score
        breakdown["leverage"] = leverage_score
    
    # Normalize score to 0-100
    normalized_score = min(100, int(score))
    
    return normalized_score, breakdown


def score_credit_history(
    credit_rating: CreditRating,
    years_of_credit_history: int,
    delinquencies_last_3_years: int,
    bankruptcies_last_10_years: int
) -> Tuple[int, Dict[str, Any]]:
    """
    Score the credit history of the borrower
    Returns a score from 0-100 and breakdown of subscores
    """
    score = 0
    breakdown = {}
    
    # Credit rating assessment (0-40 points)
    if credit_rating == CreditRating.AAA:
        rating_score = 40
    elif credit_rating == CreditRating.AA:
        rating_score = 35
    elif credit_rating == CreditRating.A:
        rating_score = 30
    elif credit_rating == CreditRating.BBB:
        rating_score = 25
    elif credit_rating == CreditRating.BB:
        rating_score = 20
    elif credit_rating == CreditRating.B:
        rating_score = 15
    elif credit_rating == CreditRating.CCC:
        rating_score = 10
    elif credit_rating == CreditRating.CC:
        rating_score = 5
    else:
        rating_score = 0
    
    score += rating_score
    breakdown["credit_rating"] = rating_score
    
    # Credit history length (0-20 points)
    if years_of_credit_history >= 15:
        history_score = 20
    elif years_of_credit_history >= 10:
        history_score = 15
    elif years_of_credit_history >= 7:
        history_score = 10
    elif years_of_credit_history >= 5:
        history_score = 7
    elif years_of_credit_history >= 3:
        history_score = 5
    else:
        history_score = 0
    
    score += history_score
    breakdown["credit_history_length"] = history_score
    
    # Delinquencies (0-20 points)
    if delinquencies_last_3_years == 0:
        delinquency_score = 20
    elif delinquencies_last_3_years == 1:
        delinquency_score = 10
    elif delinquencies_last_3_years == 2:
        delinquency_score = 5
    else:
        delinquency_score = 0
    
    score += delinquency_score
    breakdown["delinquencies"] = delinquency_score
    
    # Bankruptcies (0-20 points)
    if bankruptcies_last_10_years == 0:
        bankruptcy_score = 20
    elif bankruptcies_last_10_years == 1:
        bankruptcy_score = 5
    else:
        bankruptcy_score = 0
    
    score += bankruptcy_score
    breakdown["bankruptcies"] = bankruptcy_score
    
    # Normalize score to 0-100
    normalized_score = min(100, int(score))
    
    return normalized_score, breakdown


def score_industry_risk(industry: str) -> Tuple[int, Dict[str, Any]]:
    """
    Score the industry risk
    Returns a score from 0-100 and breakdown of subscores
    """
    breakdown = {}
    
    # Get industry risk category
    risk_category = INDUSTRY_RISK_MAPPING.get(industry.lower(), IndustryRiskCategory.MODERATE)
    breakdown["risk_category"] = risk_category.value
    
    # Score based on risk category
    if risk_category == IndustryRiskCategory.VERY_LOW:
        score = 90
    elif risk_category == IndustryRiskCategory.LOW:
        score = 80
    elif risk_category == IndustryRiskCategory.MODERATE:
        score = 60
    elif risk_category == IndustryRiskCategory.ELEVATED:
        score = 40
    elif risk_category == IndustryRiskCategory.HIGH:
        score = 20
    else:  # VERY_HIGH
        score = 10
    
    breakdown["base_score"] = score
    
    # Normalize score to 0-100
    normalized_score = min(100, int(score))
    
    return normalized_score, breakdown


def score_collateral_quality(
    collateral_quality: CollateralQuality,
    loan_to_value_ratio: float,
    has_personal_guarantee: bool,
    collateral_diversity_count: int
) -> Tuple[int, Dict[str, Any]]:
    """
    Score the quality of the collateral
    Returns a score from 0-100 and breakdown of subscores
    """
    score = 0
    breakdown = {}
    
    # Quality assessment (0-40 points)
    if collateral_quality == CollateralQuality.EXCELLENT:
        quality_score = 40
    elif collateral_quality == CollateralQuality.STRONG:
        quality_score = 35
    elif collateral_quality == CollateralQuality.GOOD:
        quality_score = 30
    elif collateral_quality == CollateralQuality.SATISFACTORY:
        quality_score = 25
    elif collateral_quality == CollateralQuality.FAIR:
        quality_score = 20
    elif collateral_quality == CollateralQuality.WEAK:
        quality_score = 10
    else:  # POOR
        quality_score = 0
    
    score += quality_score
    breakdown["quality"] = quality_score
    
    # Loan-to-Value assessment (0-40 points)
    if loan_to_value_ratio <= 0.50:
        ltv_score = 40
    elif loan_to_value_ratio <= 0.60:
        ltv_score = 35
    elif loan_to_value_ratio <= 0.70:
        ltv_score = 30
    elif loan_to_value_ratio <= 0.75:
        ltv_score = 25
    elif loan_to_value_ratio <= 0.80:
        ltv_score = 20
    elif loan_to_value_ratio <= 0.85:
        ltv_score = 15
    elif loan_to_value_ratio <= 0.90:
        ltv_score = 10
    else:
        ltv_score = 0
    
    score += ltv_score
    breakdown["loan_to_value"] = ltv_score
    
    # Personal guarantee (0-10 points)
    guarantee_score = 10 if has_personal_guarantee else 0
    score += guarantee_score
    breakdown["personal_guarantee"] = guarantee_score
    
    # Collateral diversity (0-10 points)
    if collateral_diversity_count >= 3:
        diversity_score = 10
    elif collateral_diversity_count == 2:
        diversity_score = 5
    else:
        diversity_score = 0
    
    score += diversity_score
    breakdown["diversity"] = diversity_score
    
    # Normalize score to 0-100
    normalized_score = min(100, int(score))
    
    return normalized_score, breakdown


def score_management_experience(
    years_in_industry: int,
    previous_successful_ventures: int,
    management_team_size: int,
    has_relevant_educational_background: bool
) -> Tuple[int, Dict[str, Any]]:
    """
    Score the management experience
    Returns a score from 0-100 and breakdown of subscores
    """
    score = 0
    breakdown = {}
    
    # Years in industry (0-40 points)
    if years_in_industry >= 20:
        years_score = 40
    elif years_in_industry >= 15:
        years_score = 35
    elif years_in_industry >= 10:
        years_score = 30
    elif years_in_industry >= 7:
        years_score = 25
    elif years_in_industry >= 5:
        years_score = 20
    elif years_in_industry >= 3:
        years_score = 15
    else:
        years_score = 5
    
    score += years_score
    breakdown["years_in_industry"] = years_score
    
    # Previous ventures (0-30 points)
    if previous_successful_ventures >= 3:
        ventures_score = 30
    elif previous_successful_ventures == 2:
        ventures_score = 20
    elif previous_successful_ventures == 1:
        ventures_score = 10
    else:
        ventures_score = 0
    
    score += ventures_score
    breakdown["previous_ventures"] = ventures_score
    
    # Team size (0-20 points)
    if management_team_size >= 5:
        team_score = 20
    elif management_team_size >= 3:
        team_score = 15
    elif management_team_size >= 2:
        team_score = 10
    else:
        team_score = 5
    
    score += team_score
    breakdown["team_size"] = team_score
    
    # Educational background (0-10 points)
    edu_score = 10 if has_relevant_educational_background else 0
    score += edu_score
    breakdown["educational_background"] = edu_score
    
    # Normalize score to 0-100
    normalized_score = min(100, int(score))
    
    return normalized_score, breakdown


def score_business_plan(
    has_clear_strategy: bool,
    has_market_analysis: bool,
    has_financial_projections: bool,
    has_risk_assessment: bool,
    has_competitive_analysis: bool
) -> Tuple[int, Dict[str, Any]]:
    """
    Score the business plan
    Returns a score from 0-100 and breakdown of subscores
    """
    score = 0
    breakdown = {}
    
    # Clear strategy (0-25 points)
    strategy_score = 25 if has_clear_strategy else 0
    score += strategy_score
    breakdown["clear_strategy"] = strategy_score
    
    # Market analysis (0-20 points)
    market_score = 20 if has_market_analysis else 0
    score += market_score
    breakdown["market_analysis"] = market_score
    
    # Financial projections (0-25 points)
    projections_score = 25 if has_financial_projections else 0
    score += projections_score
    breakdown["financial_projections"] = projections_score
    
    # Risk assessment (0-15 points)
    risk_score = 15 if has_risk_assessment else 0
    score += risk_score
    breakdown["risk_assessment"] = risk_score
    
    # Competitive analysis (0-15 points)
    competitive_score = 15 if has_competitive_analysis else 0
    score += competitive_score
    breakdown["competitive_analysis"] = competitive_score
    
    # Normalize score to 0-100
    normalized_score = min(100, int(score))
    
    return normalized_score, breakdown


def score_market_conditions(
    industry_growth_rate: float,
    market_volatility: str,
    regulatory_environment: str,
    technology_disruption_risk: str
) -> Tuple[int, Dict[str, Any]]:
    """
    Score the market conditions
    Returns a score from 0-100 and breakdown of subscores
    """
    score = 0
    breakdown = {}
    
    # Industry growth (0-40 points)
    if industry_growth_rate >= 0.1:  # 10%+ growth
        growth_score = 40
    elif industry_growth_rate >= 0.05:
        growth_score = 30
    elif industry_growth_rate >= 0.02:
        growth_score = 20
    elif industry_growth_rate >= 0:
        growth_score = 10
    else:
        growth_score = 0
    
    score += growth_score
    breakdown["industry_growth"] = growth_score
    
    # Market volatility (0-20 points)
    if market_volatility == "low":
        volatility_score = 20
    elif market_volatility == "moderate":
        volatility_score = 10
    else:  # high
        volatility_score = 0
    
    score += volatility_score
    breakdown["market_volatility"] = volatility_score
    
    # Regulatory environment (0-20 points)
    if regulatory_environment == "favorable":
        regulatory_score = 20
    elif regulatory_environment == "neutral":
        regulatory_score = 10
    else:  # unfavorable
        regulatory_score = 0
    
    score += regulatory_score
    breakdown["regulatory_environment"] = regulatory_score
    
    # Technology disruption (0-20 points)
    if technology_disruption_risk == "low":
        tech_score = 20
    elif technology_disruption_risk == "moderate":
        tech_score = 10
    else:  # high
        tech_score = 0
    
    score += tech_score
    breakdown["technology_disruption"] = tech_score
    
    # Normalize score to 0-100
    normalized_score = min(100, int(score))
    
    return normalized_score, breakdown


def score_relationship_history(
    years_as_customer: int,
    products_used: int,
    deposit_relationship: bool,
    previous_loans_repaid: int
) -> Tuple[int, Dict[str, Any]]:
    """
    Score the relationship history with the bank
    Returns a score from 0-100 and breakdown of subscores
    """
    score = 0
    breakdown = {}
    
    # Years as customer (0-40 points)
    if years_as_customer >= 10:
        years_score = 40
    elif years_as_customer >= 7:
        years_score = 30
    elif years_as_customer >= 5:
        years_score = 25
    elif years_as_customer >= 3:
        years_score = 20
    elif years_as_customer >= 1:
        years_score = 10
    else:
        years_score = 0
    
    score += years_score
    breakdown["years_as_customer"] = years_score
    
    # Products used (0-20 points)
    if products_used >= 5:
        products_score = 20
    elif products_used >= 3:
        products_score = 15
    elif products_used >= 2:
        products_score = 10
    elif products_used >= 1:
        products_score = 5
    else:
        products_score = 0
    
    score += products_score
    breakdown["products_used"] = products_score
    
    # Deposit relationship (0-20 points)
    deposit_score = 20 if deposit_relationship else 0
    score += deposit_score
    breakdown["deposit_relationship"] = deposit_score
    
    # Previous loans repaid (0-20 points)
    if previous_loans_repaid >= 3:
        loans_score = 20
    elif previous_loans_repaid == 2:
        loans_score = 15
    elif previous_loans_repaid == 1:
        loans_score = 10
    else:
        loans_score = 0
    
    score += loans_score
    breakdown["previous_loans"] = loans_score
    
    # Normalize score to 0-100
    normalized_score = min(100, int(score))
    
    return normalized_score, breakdown


def calculate_weighted_score(scores: Dict[str, int]) -> int:
    """Calculate the weighted final score based on individual category scores"""
    weighted_total = 0
    
    for category, score in scores.items():
        weight = SCORING_WEIGHTS.get(category, 0)
        weighted_total += score * (weight / 100)
    
    return int(weighted_total)


def determine_loan_grade(score: int) -> LoanGrade:
    """Determine the loan grade based on the final score"""
    if score >= 90:
        return LoanGrade.PRIME_PLUS
    elif score >= 80:
        return LoanGrade.PRIME
    elif score >= 70:
        return LoanGrade.NEAR_PRIME
    elif score >= 60:
        return LoanGrade.STANDARD
    elif score >= 50:
        return LoanGrade.STANDARD_MINUS
    elif score >= 40:
        return LoanGrade.SUBSTANDARD
    elif score >= 30:
        return LoanGrade.WATCH
    elif score >= 20:
        return LoanGrade.SPECIAL_MENTION
    else:
        return LoanGrade.SUBPAR


def determine_interest_rate_adjustment(grade: LoanGrade) -> float:
    """Determine the interest rate adjustment based on loan grade"""
    adjustments = {
        LoanGrade.PRIME_PLUS: -0.75,     # 0.75% below base rate
        LoanGrade.PRIME: -0.5,           # 0.5% below base rate
        LoanGrade.NEAR_PRIME: -0.25,     # 0.25% below base rate
        LoanGrade.STANDARD: 0.0,         # Base rate
        LoanGrade.STANDARD_MINUS: 0.25,  # 0.25% above base rate
        LoanGrade.SUBSTANDARD: 0.5,      # 0.5% above base rate
        LoanGrade.WATCH: 1.0,            # 1.0% above base rate
        LoanGrade.SPECIAL_MENTION: 1.5,  # 1.5% above base rate
        LoanGrade.SUBPAR: 2.0,           # 2.0% above base rate
    }
    
    return adjustments.get(grade, 0.0)


def evaluate_loan_application(application_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate a loan application using the scoring model
    
    Parameters:
    - application_data: Dictionary containing all application information
    
    Returns:
    - Dictionary with scores, grade, and risk assessment
    """
    # Extract financial data
    financial_data = application_data.get("financial", {})
    annual_revenue = financial_data.get("annual_revenue", 0)
    annual_net_income = financial_data.get("annual_net_income", 0)
    annual_debt = financial_data.get("annual_debt", 0)
    annual_debt_payments = financial_data.get("annual_debt_payments", 0)
    years_profitable = financial_data.get("years_profitable", 0)
    current_ratio = financial_data.get("current_ratio")
    quick_ratio = financial_data.get("quick_ratio")
    debt_to_equity = financial_data.get("debt_to_equity")
    
    # Extract credit data
    credit_data = application_data.get("credit", {})
    credit_rating_str = credit_data.get("credit_rating", "BBB")
    try:
        credit_rating = CreditRating[credit_rating_str]
    except (KeyError, ValueError):
        credit_rating = CreditRating.BBB  # Default to BBB if invalid
    
    years_of_credit_history = credit_data.get("years_of_credit_history", 0)
    delinquencies_last_3_years = credit_data.get("delinquencies_last_3_years", 0)
    bankruptcies_last_10_years = credit_data.get("bankruptcies_last_10_years", 0)
    
    # Extract industry data
    industry = application_data.get("industry", "")
    
    # Extract collateral data
    collateral_data = application_data.get("collateral", {})
    collateral_quality_str = collateral_data.get("quality", "SATISFACTORY")
    try:
        collateral_quality = CollateralQuality[collateral_quality_str]
    except (KeyError, ValueError):
        collateral_quality = CollateralQuality.SATISFACTORY  # Default
    
    loan_amount = application_data.get("loan_amount", 0)
    collateral_value = collateral_data.get("value", 0)
    loan_to_value_ratio = calculate_loan_to_value_ratio(loan_amount, collateral_value)
    has_personal_guarantee = collateral_data.get("has_personal_guarantee", False)
    collateral_diversity_count = collateral_data.get("diversity_count", 1)
    
    # Extract management data
    mgmt_data = application_data.get("management", {})
    years_in_industry = mgmt_data.get("years_in_industry", 0)
    previous_successful_ventures = mgmt_data.get("previous_successful_ventures", 0)
    management_team_size = mgmt_data.get("team_size", 1)
    has_relevant_educational_background = mgmt_data.get("has_relevant_education", False)
    
    # Extract business plan data
    plan_data = application_data.get("business_plan", {})
    has_clear_strategy = plan_data.get("has_clear_strategy", False)
    has_market_analysis = plan_data.get("has_market_analysis", False)
    has_financial_projections = plan_data.get("has_financial_projections", False)
    has_risk_assessment = plan_data.get("has_risk_assessment", False)
    has_competitive_analysis = plan_data.get("has_competitive_analysis", False)
    
    # Extract market condition data
    market_data = application_data.get("market", {})
    industry_growth_rate = market_data.get("industry_growth_rate", 0.02)
    market_volatility = market_data.get("market_volatility", "moderate")
    regulatory_environment = market_data.get("regulatory_environment", "neutral")
    technology_disruption_risk = market_data.get("technology_disruption_risk", "moderate")
    
    # Extract relationship data
    relationship_data = application_data.get("relationship", {})
    years_as_customer = relationship_data.get("years_as_customer", 0)
    products_used = relationship_data.get("products_used", 0)
    deposit_relationship = relationship_data.get("deposit_relationship", False)
    previous_loans_repaid = relationship_data.get("previous_loans_repaid", 0)
    
    # Calculate category scores
    financial_score, financial_breakdown = score_financial_standing(
        annual_revenue, annual_net_income, annual_debt, annual_debt_payments,
        years_profitable, current_ratio, quick_ratio, debt_to_equity
    )
    
    credit_score, credit_breakdown = score_credit_history(
        credit_rating, years_of_credit_history, 
        delinquencies_last_3_years, bankruptcies_last_10_years
    )
    
    industry_score, industry_breakdown = score_industry_risk(industry)
    
    collateral_score, collateral_breakdown = score_collateral_quality(
        collateral_quality, loan_to_value_ratio, 
        has_personal_guarantee, collateral_diversity_count
    )
    
    management_score, management_breakdown = score_management_experience(
        years_in_industry, previous_successful_ventures,
        management_team_size, has_relevant_educational_background
    )
    
    business_plan_score, plan_breakdown = score_business_plan(
        has_clear_strategy, has_market_analysis, has_financial_projections,
        has_risk_assessment, has_competitive_analysis
    )
    
    market_score, market_breakdown = score_market_conditions(
        industry_growth_rate, market_volatility,
        regulatory_environment, technology_disruption_risk
    )
    
    relationship_score, relationship_breakdown = score_relationship_history(
        years_as_customer, products_used, 
        deposit_relationship, previous_loans_repaid
    )
    
    # Compile category scores
    category_scores = {
        "financial_standing": financial_score,
        "credit_history": credit_score,
        "industry_factor": industry_score,
        "collateral_quality": collateral_score,
        "management_experience": management_score,
        "business_plan": business_plan_score,
        "market_conditions": market_score,
        "relationship_history": relationship_score
    }
    
    # Calculate final weighted score
    final_score = calculate_weighted_score(category_scores)
    
    # Determine loan grade
    loan_grade = determine_loan_grade(final_score)
    
    # Determine interest rate adjustment
    rate_adjustment = determine_interest_rate_adjustment(loan_grade)
    
    # Base interest rate (standard rate)
    base_rate = 5.75
    
    # Calculate final recommended rate
    recommended_rate = base_rate + rate_adjustment
    
    # Compile results
    results = {
        "application_id": application_data.get("application_id", ""),
        "borrower_name": application_data.get("borrower_name", ""),
        "loan_amount": loan_amount,
        "scores": {
            "final_score": final_score,
            "category_scores": category_scores,
            "breakdowns": {
                "financial_standing": financial_breakdown,
                "credit_history": credit_breakdown,
                "industry_factor": industry_breakdown,
                "collateral_quality": collateral_breakdown,
                "management_experience": management_breakdown,
                "business_plan": plan_breakdown,
                "market_conditions": market_breakdown,
                "relationship_history": relationship_breakdown
            }
        },
        "grade": {
            "name": loan_grade.name,
            "description": loan_grade.value
        },
        "interest_rate": {
            "base_rate": base_rate,
            "adjustment": rate_adjustment,
            "recommended_rate": recommended_rate
        },
        "risk_assessment": {
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }
    }
    
    # Identify strengths and weaknesses
    for category, score in category_scores.items():
        weight = SCORING_WEIGHTS.get(category, 0)
        if score >= 80 and weight >= 10:
            results["risk_assessment"]["strengths"].append(f"Strong {category.replace('_', ' ')} ({score}/100)")
        elif score <= 40 and weight >= 10:
            results["risk_assessment"]["weaknesses"].append(f"Weak {category.replace('_', ' ')} ({score}/100)")
    
    # Add recommendations based on weaknesses
    if financial_score < 60:
        results["risk_assessment"]["recommendations"].append(
            "Improve financial position before loan consideration or provide additional collateral"
        )
    
    if credit_score < 50:
        results["risk_assessment"]["recommendations"].append(
            "Work on improving credit history or provide stronger guarantees"
        )
    
    if collateral_score < 50:
        results["risk_assessment"]["recommendations"].append(
            "Provide additional or higher quality collateral to secure the loan"
        )
    
    if industry_score < 40:
        results["risk_assessment"]["recommendations"].append(
            "Consider industry risk mitigation strategies in business plan"
        )
    
    # Default recommendation if no specific weaknesses
    if not results["risk_assessment"]["recommendations"]:
        if final_score >= 70:
            results["risk_assessment"]["recommendations"].append(
                "Application meets standard underwriting criteria, proceed with loan process"
            )
        else:
            results["risk_assessment"]["recommendations"].append(
                "Further review required for final loan decision"
            )
    
    return results