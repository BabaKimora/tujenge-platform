"""
Risk Assessment Utility for Tanzania Fintech Platform
Comprehensive risk evaluation for loan applications using Tanzania-specific factors
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import json

logger = logging.getLogger(__name__)

class RiskLevel(str, Enum):
    """Risk level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class RiskFactor(str, Enum):
    """Risk assessment factors"""
    CREDIT_HISTORY = "credit_history"
    INCOME_STABILITY = "income_stability"
    EMPLOYMENT_STATUS = "employment_status"
    DEBT_TO_INCOME = "debt_to_income"
    COLLATERAL_COVERAGE = "collateral_coverage"
    GEOGRAPHICAL_RISK = "geographical_risk"
    AGE_FACTOR = "age_factor"
    EDUCATION_LEVEL = "education_level"
    MOBILE_MONEY_USAGE = "mobile_money_usage"
    BUSINESS_PERFORMANCE = "business_performance"
    SEASONAL_INCOME = "seasonal_income"
    NIDA_VERIFICATION = "nida_verification"

class RiskAssessment:
    """Comprehensive risk assessment engine for Tanzania market"""
    
    def __init__(self):
        self.risk_weights = self._load_risk_weights()
        self.tanzania_specific_factors = self._load_tanzania_factors()
        self.base_score = 500  # Credit score equivalent to medium risk
    
    def _load_risk_weights(self) -> Dict[str, float]:
        """Load risk factor weights for scoring"""
        return {
            RiskFactor.CREDIT_HISTORY.value: 0.25,      # 25%
            RiskFactor.INCOME_STABILITY.value: 0.20,     # 20%
            RiskFactor.EMPLOYMENT_STATUS.value: 0.15,    # 15%
            RiskFactor.DEBT_TO_INCOME.value: 0.12,       # 12%
            RiskFactor.COLLATERAL_COVERAGE.value: 0.10,  # 10%
            RiskFactor.GEOGRAPHICAL_RISK.value: 0.08,    # 8%
            RiskFactor.NIDA_VERIFICATION.value: 0.05,    # 5%
            RiskFactor.MOBILE_MONEY_USAGE.value: 0.05,   # 5%
        }
    
    def _load_tanzania_factors(self) -> Dict[str, Any]:
        """Load Tanzania-specific risk factors"""
        return {
            "high_risk_regions": [
                "Border regions", "Mining areas", "Conflict zones"
            ],
            "seasonal_employment": [
                "agriculture", "tourism", "construction"
            ],
            "stable_employment": [
                "government", "banking", "telecommunications", "utilities"
            ],
            "mobile_money_providers": [
                "mpesa", "airtel_money", "tigo_pesa", "halopesa"
            ],
            "education_risk_mapping": {
                "no_formal_education": 0.3,
                "primary": 0.5,
                "secondary": 0.7,
                "certificate": 0.8,
                "diploma": 0.85,
                "degree": 0.9,
                "postgraduate": 0.95,
            },
            "age_risk_mapping": {
                "18_25": 0.6,   # Higher risk due to limited history
                "26_35": 0.8,   # Prime earning years
                "36_45": 0.9,   # Peak earning and stability
                "46_55": 0.85,  # Pre-retirement planning
                "56_65": 0.7,   # Approaching retirement
                "65_plus": 0.4, # Retirement age
            },
        }
    
    async def assess_loan_risk(
        self,
        customer_id: str,
        loan_amount: float,
        loan_type: str,
        customer_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive loan risk assessment
        
        Args:
            customer_id: Customer identifier
            loan_amount: Requested loan amount
            loan_type: Type of loan (personal, business, etc.)
            customer_data: Customer information (if not provided, will fetch)
        
        Returns:
            Dict containing risk assessment results
        """
        try:
            # Get customer data if not provided
            if not customer_data:
                # In real implementation: customer_data = await customer_service.get_by_id(customer_id)
                customer_data = self._get_mock_customer_data(customer_id)
            
            # Initialize risk assessment
            risk_scores = {}
            risk_factors = {}
            
            # Assess each risk factor
            risk_scores[RiskFactor.CREDIT_HISTORY.value] = await self._assess_credit_history(customer_data)
            risk_scores[RiskFactor.INCOME_STABILITY.value] = await self._assess_income_stability(customer_data)
            risk_scores[RiskFactor.EMPLOYMENT_STATUS.value] = await self._assess_employment_status(customer_data)
            risk_scores[RiskFactor.DEBT_TO_INCOME.value] = await self._assess_debt_to_income(customer_data, loan_amount)
            risk_scores[RiskFactor.COLLATERAL_COVERAGE.value] = await self._assess_collateral_coverage(customer_data, loan_amount)
            risk_scores[RiskFactor.GEOGRAPHICAL_RISK.value] = await self._assess_geographical_risk(customer_data)
            risk_scores[RiskFactor.NIDA_VERIFICATION.value] = await self._assess_nida_verification(customer_data)
            risk_scores[RiskFactor.MOBILE_MONEY_USAGE.value] = await self._assess_mobile_money_usage(customer_data)
            
            # Special assessments for business loans
            if loan_type == "business":
                risk_scores[RiskFactor.BUSINESS_PERFORMANCE.value] = await self._assess_business_performance(customer_data)
                # Adjust weights for business loans
                self.risk_weights[RiskFactor.BUSINESS_PERFORMANCE.value] = 0.15
                self.risk_weights[RiskFactor.INCOME_STABILITY.value] = 0.15
            
            # Calculate weighted risk score
            weighted_score = self._calculate_weighted_score(risk_scores)
            
            # Determine risk level and rating
            risk_level = self._determine_risk_level(weighted_score)
            risk_rating = self._get_risk_rating(weighted_score)
            
            # Calculate loan-specific adjustments
            loan_adjustments = self._calculate_loan_adjustments(loan_amount, loan_type, customer_data)
            
            # Final adjusted score
            final_score = weighted_score + loan_adjustments["score_adjustment"]
            final_score = max(300, min(850, final_score))  # Cap between 300-850
            
            # Generate recommendations
            recommendations = self._generate_risk_recommendations(
                final_score, risk_scores, loan_amount, loan_type
            )
            
            # Compile risk assessment result
            assessment_result = {
                "customer_id": customer_id,
                "loan_amount": loan_amount,
                "loan_type": loan_type,
                "risk_score": final_score,
                "risk_level": risk_level,
                "risk_rating": risk_rating,
                "individual_scores": risk_scores,
                "weighted_score": weighted_score,
                "loan_adjustments": loan_adjustments,
                "recommendations": recommendations,
                "risk_factors": self._identify_key_risk_factors(risk_scores),
                "mitigation_strategies": self._suggest_mitigation_strategies(risk_scores, loan_type),
                "assessed_at": datetime.utcnow(),
                "assessor_version": "1.0",
            }
            
            # Log risk assessment
            logger.info(f"Risk assessment completed for customer {customer_id}: Score {final_score}, Level {risk_level}")
            
            return assessment_result
            
        except Exception as e:
            logger.error(f"Risk assessment error for customer {customer_id}: {str(e)}")
            return {
                "customer_id": customer_id,
                "risk_score": 400,  # Conservative default
                "risk_level": RiskLevel.HIGH.value,
                "risk_rating": "D",
                "error": f"Risk assessment failed: {str(e)}",
                "assessed_at": datetime.utcnow(),
            }
    
    async def _assess_credit_history(self, customer_data: Dict[str, Any]) -> float:
        """Assess credit history risk factor"""
        try:
            # In real implementation: Get credit history from CRB
            # credit_history = await credit_bureau_service.get_credit_report(customer_data["nida_number"])
            
            # Mock credit history assessment
            payment_history = customer_data.get("payment_history", {})
            
            score = self.base_score
            
            # Payment history factors
            if payment_history.get("on_time_payments", 0) > 0.9:
                score += 100  # Excellent payment history
            elif payment_history.get("on_time_payments", 0) > 0.8:
                score += 50   # Good payment history
            elif payment_history.get("on_time_payments", 0) > 0.6:
                score += 0    # Average payment history
            else:
                score -= 100  # Poor payment history
            
            # Credit utilization
            credit_utilization = payment_history.get("credit_utilization", 0.5)
            if credit_utilization < 0.3:
                score += 50
            elif credit_utilization > 0.8:
                score -= 50
            
            # Length of credit history
            credit_age_months = payment_history.get("credit_age_months", 0)
            if credit_age_months > 36:
                score += 30
            elif credit_age_months > 12:
                score += 15
            
            # Default history
            if payment_history.get("defaults", 0) > 0:
                score -= 200
            
            return max(300, min(850, score))
            
        except Exception as e:
            logger.warning(f"Credit history assessment error: {str(e)}")
            return self.base_score
    
    async def _assess_income_stability(self, customer_data: Dict[str, Any]) -> float:
        """Assess income stability risk factor"""
        try:
            monthly_income = customer_data.get("monthly_income", 0)
            employment_status = customer_data.get("employment_status", "").lower()
            employment_duration = customer_data.get("employment_duration_months", 0)
            
            score = self.base_score
            
            # Income level assessment
            if monthly_income >= 2000000:  # 2M TZS
                score += 100
            elif monthly_income >= 1000000:  # 1M TZS
                score += 50
            elif monthly_income >= 500000:   # 500K TZS
                score += 20
            elif monthly_income < 300000:    # Below 300K TZS
                score -= 100
            
            # Employment stability
            if employment_status in self.tanzania_specific_factors["stable_employment"]:
                score += 80
            elif employment_status in self.tanzania_specific_factors["seasonal_employment"]:
                score -= 50
            
            # Employment duration
            if employment_duration > 36:  # 3+ years
                score += 60
            elif employment_duration > 12:  # 1+ years
                score += 30
            elif employment_duration < 6:   # Less than 6 months
                score -= 50
            
            # Multiple income sources
            if customer_data.get("multiple_income_sources", False):
                score += 40
            
            return max(300, min(850, score))
            
        except Exception as e:
            logger.warning(f"Income stability assessment error: {str(e)}")
            return self.base_score
    
    async def _assess_employment_status(self, customer_data: Dict[str, Any]) -> float:
        """Assess employment status risk factor"""
        try:
            employment_status = customer_data.get("employment_status", "").lower()
            employer_name = customer_data.get("employer_name", "")
            
            score = self.base_score
            
            # Employment type scoring
            employment_scores = {
                "government": 100,
                "bank": 90,
                "telecom": 85,
                "ngo": 80,
                "private_company": 70,
                "self_employed": 50,
                "freelance": 40,
                "casual": 20,
                "unemployed": -200,
            }
            
            for emp_type, points in employment_scores.items():
                if emp_type in employment_status:
                    score += points
                    break
            
            # Large employer bonus
            large_employers = [
                "government", "vodacom", "airtel", "crdb", "nbc", "nm bank"
            ]
            if any(employer in employer_name.lower() for employer in large_employers):
                score += 50
            
            return max(300, min(850, score))
            
        except Exception as e:
            logger.warning(f"Employment status assessment error: {str(e)}")
            return self.base_score
    
    async def _assess_debt_to_income(self, customer_data: Dict[str, Any], loan_amount: float) -> float:
        """Assess debt-to-income ratio risk factor"""
        try:
            monthly_income = customer_data.get("monthly_income", 0)
            existing_debt_payment = customer_data.get("existing_debt_payment", 0)
            
            if monthly_income <= 0:
                return 300  # High risk if no income
            
            # Calculate estimated new payment (rough approximation)
            estimated_payment = loan_amount * 0.08  # Assume 8% monthly payment rate
            total_debt_payment = existing_debt_payment + estimated_payment
            
            debt_to_income_ratio = total_debt_payment / monthly_income
            
            score = self.base_score
            
            if debt_to_income_ratio <= 0.3:      # 30% or less
                score += 100
            elif debt_to_income_ratio <= 0.4:    # 30-40%
                score += 50
            elif debt_to_income_ratio <= 0.5:    # 40-50%
                score += 0
            elif debt_to_income_ratio <= 0.6:    # 50-60%
                score -= 50
            else:                                 # Above 60%
                score -= 150
            
            return max(300, min(850, score))
            
        except Exception as e:
            logger.warning(f"Debt-to-income assessment error: {str(e)}")
            return self.base_score
    
    async def _assess_collateral_coverage(self, customer_data: Dict[str, Any], loan_amount: float) -> float:
        """Assess collateral coverage risk factor"""
        try:
            collateral_value = customer_data.get("collateral_value", 0)
            collateral_type = customer_data.get("collateral_type", "none")
            
            score = self.base_score
            
            if collateral_type == "none":
                score -= 50  # Unsecured loan penalty
            else:
                # Calculate collateral coverage ratio
                if collateral_value > 0:
                    coverage_ratio = collateral_value / loan_amount
                    
                    if coverage_ratio >= 1.5:      # 150% coverage
                        score += 100
                    elif coverage_ratio >= 1.2:    # 120% coverage
                        score += 70
                    elif coverage_ratio >= 1.0:    # 100% coverage
                        score += 40
                    elif coverage_ratio >= 0.8:    # 80% coverage
                        score += 20
                    else:                           # Below 80%
                        score -= 30
                
                # Collateral type quality
                collateral_scores = {
                    "property": 50,
                    "vehicle": 40,
                    "equipment": 30,
                    "inventory": 20,
                    "guarantor": 35,
                }
                
                score += collateral_scores.get(collateral_type, 0)
            
            return max(300, min(850, score))
            
        except Exception as e:
            logger.warning(f"Collateral coverage assessment error: {str(e)}")
            return self.base_score
    
    async def _assess_geographical_risk(self, customer_data: Dict[str, Any]) -> float:
        """Assess geographical risk factor"""
        try:
            region = customer_data.get("region", "")
            district = customer_data.get("district", "")
            
            score = self.base_score
            
            # High-risk regions
            if any(risk_region in region.lower() for risk_region in self.tanzania_specific_factors["high_risk_regions"]):
                score -= 100
            
            # Urban vs Rural risk
            urban_regions = ["dar es salaam", "arusha", "mwanza", "dodoma", "mbeya"]
            if region.lower() in urban_regions:
                score += 50  # Urban areas generally lower risk
            else:
                score -= 20  # Rural areas slightly higher risk
            
            # Economic activity centers
            economic_centers = ["dar es salaam", "arusha", "mwanza"]
            if region.lower() in economic_centers:
                score += 30
            
            return max(300, min(850, score))
            
        except Exception as e:
            logger.warning(f"Geographical risk assessment error: {str(e)}")
            return self.base_score
    
    async def _assess_nida_verification(self, customer_data: Dict[str, Any]) -> float:
        """Assess NIDA verification risk factor"""
        try:
            nida_verified = customer_data.get("nida_verified", False)
            tin_verified = customer_data.get("tin_verified", False)
            
            score = self.base_score
            
            if nida_verified:
                score += 100  # NIDA verification is crucial
            else:
                score -= 200  # Major red flag
            
            if tin_verified:
                score += 50   # TIN verification adds credibility
            
            return max(300, min(850, score))
            
        except Exception as e:
            logger.warning(f"NIDA verification assessment error: {str(e)}")
            return self.base_score
    
    async def _assess_mobile_money_usage(self, customer_data: Dict[str, Any]) -> float:
        """Assess mobile money usage risk factor"""
        try:
            mobile_money_registered = customer_data.get("mobile_money_registered", False)
            mobile_money_accounts = customer_data.get("mobile_money_accounts", [])
            
            score = self.base_score
            
            if mobile_money_registered:
                score += 50
                
                # Multiple providers indicate financial engagement
                if len(mobile_money_accounts) > 1:
                    score += 30
                
                # Check for transaction history
                for account in mobile_money_accounts:
                    if account.get("transaction_count", 0) > 10:
                        score += 20
                        break
            else:
                score -= 50  # Not having mobile money in Tanzania is concerning
            
            return max(300, min(850, score))
            
        except Exception as e:
            logger.warning(f"Mobile money usage assessment error: {str(e)}")
            return self.base_score
    
    async def _assess_business_performance(self, customer_data: Dict[str, Any]) -> float:
        """Assess business performance for business loans"""
        try:
            monthly_business_income = customer_data.get("monthly_business_income", 0)
            years_in_business = customer_data.get("years_in_business", 0)
            business_registration = customer_data.get("business_registration", "")
            
            score = self.base_score
            
            # Business income level
            if monthly_business_income >= 1000000:  # 1M TZS
                score += 80
            elif monthly_business_income >= 500000:  # 500K TZS
                score += 50
            elif monthly_business_income >= 200000:  # 200K TZS
                score += 20
            else:
                score -= 50
            
            # Years in business
            if years_in_business >= 5:
                score += 70
            elif years_in_business >= 3:
                score += 50
            elif years_in_business >= 1:
                score += 30
            else:
                score -= 30
            
            # Business registration
            if business_registration:
                score += 60  # Formal business registration
            else:
                score -= 40  # Informal business
            
            return max(300, min(850, score))
            
        except Exception as e:
            logger.warning(f"Business performance assessment error: {str(e)}")
            return self.base_score
    
    def _calculate_weighted_score(self, risk_scores: Dict[str, float]) -> float:
        """Calculate weighted risk score"""
        try:
            weighted_sum = 0
            total_weight = 0
            
            for factor, score in risk_scores.items():
                weight = self.risk_weights.get(factor, 0)
                weighted_sum += score * weight
                total_weight += weight
            
            if total_weight > 0:
                return weighted_sum / total_weight
            
            return self.base_score
            
        except Exception as e:
            logger.warning(f"Weighted score calculation error: {str(e)}")
            return self.base_score
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on score"""
        if score >= 700:
            return RiskLevel.LOW.value
        elif score >= 600:
            return RiskLevel.MEDIUM.value
        elif score >= 500:
            return RiskLevel.HIGH.value
        else:
            return RiskLevel.VERY_HIGH.value
    
    def _get_risk_rating(self, score: float) -> str:
        """Get letter risk rating"""
        if score >= 750:
            return "A+"
        elif score >= 700:
            return "A"
        elif score >= 650:
            return "B+"
        elif score >= 600:
            return "B"
        elif score >= 550:
            return "C+"
        elif score >= 500:
            return "C"
        elif score >= 450:
            return "D+"
        elif score >= 400:
            return "D"
        else:
            return "F"
    
    def _calculate_loan_adjustments(
        self, 
        loan_amount: float, 
        loan_type: str, 
        customer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate loan-specific risk adjustments"""
        try:
            adjustments = {
                "score_adjustment": 0,
                "rate_adjustment": 0,
                "amount_adjustment": 0,
                "tenure_adjustment": 0,
                "reasons": [],
            }
            
            # Loan amount adjustments
            monthly_income = customer_data.get("monthly_income", 0)
            if monthly_income > 0:
                loan_to_income_ratio = loan_amount / (monthly_income * 12)
                
                if loan_to_income_ratio > 3:      # Loan > 3x annual income
                    adjustments["score_adjustment"] -= 50
                    adjustments["reasons"].append("High loan-to-income ratio")
                elif loan_to_income_ratio > 2:    # Loan > 2x annual income
                    adjustments["score_adjustment"] -= 25
                    adjustments["reasons"].append("Moderate loan-to-income ratio")
            
            # Loan type adjustments
            loan_type_adjustments = {
                "personal": 0,
                "business": -20,      # Business loans inherently riskier
                "emergency": -30,     # Emergency loans higher risk
                "education": 10,      # Education loans slightly lower risk
                "agriculture": -40,   # Agricultural loans seasonal risk
                "group": 20,          # Group loans peer pressure benefit
            }
            
            adjustments["score_adjustment"] += loan_type_adjustments.get(loan_type, 0)
            
            # First-time borrower adjustment
            is_first_time = customer_data.get("is_first_time_borrower", True)
            if is_first_time:
                adjustments["score_adjustment"] -= 30
                adjustments["reasons"].append("First-time borrower")
            
            return adjustments
            
        except Exception as e:
            logger.warning(f"Loan adjustments calculation error: {str(e)}")
            return {
                "score_adjustment": 0,
                "rate_adjustment": 0,
                "amount_adjustment": 0,
                "tenure_adjustment": 0,
                "reasons": [],
            }
    
    def _generate_risk_recommendations(
        self, 
        final_score: float, 
        risk_scores: Dict[str, float], 
        loan_amount: float, 
        loan_type: str
    ) -> List[str]:
        """Generate risk-based recommendations"""
        recommendations = []
        
        if final_score >= 700:
            recommendations.append("Approve with standard terms")
            recommendations.append("Consider premium pricing benefits")
        elif final_score >= 600:
            recommendations.append("Approve with standard terms")
            recommendations.append("Monitor repayment closely")
        elif final_score >= 500:
            recommendations.append("Approve with enhanced monitoring")
            recommendations.append("Require additional documentation")
            recommendations.append("Consider reduced loan amount")
        elif final_score >= 400:
            recommendations.append("High risk - require collateral or guarantor")
            recommendations.append("Reduce loan amount by 25-50%")
            recommendations.append("Implement intensive monitoring")
        else:
            recommendations.append("Reject - risk too high")
            recommendations.append("Suggest financial literacy program")
            recommendations.append("Re-evaluate after 6 months")
        
        # Specific factor recommendations
        if risk_scores.get(RiskFactor.INCOME_STABILITY.value, 500) < 450:
            recommendations.append("Verify income with additional documentation")
        
        if risk_scores.get(RiskFactor.DEBT_TO_INCOME.value, 500) < 450:
            recommendations.append("Reduce loan amount to improve debt-to-income ratio")
        
        if not risk_scores.get(RiskFactor.NIDA_VERIFICATION.value, False):
            recommendations.append("NIDA verification is mandatory")
        
        return recommendations
    
    def _identify_key_risk_factors(self, risk_scores: Dict[str, float]) -> List[str]:
        """Identify key risk factors contributing to the score"""
        key_factors = []
        
        for factor, score in risk_scores.items():
            if score < 450:  # Below average risk threshold
                key_factors.append(factor)
        
        # Sort by severity (lowest scores first)
        key_factors.sort(key=lambda x: risk_scores[x])
        
        return key_factors[:5]  # Return top 5 risk factors
    
    def _suggest_mitigation_strategies(
        self, 
        risk_scores: Dict[str, float], 
        loan_type: str
    ) -> List[str]:
        """Suggest risk mitigation strategies"""
        strategies = []
        
        # Income stability issues
        if risk_scores.get(RiskFactor.INCOME_STABILITY.value, 500) < 450:
            strategies.append("Require 6 months of income proof")
            strategies.append("Consider guarantor requirement")
        
        # Credit history issues
        if risk_scores.get(RiskFactor.CREDIT_HISTORY.value, 500) < 450:
            strategies.append("Start with smaller loan amount")
            strategies.append("Implement progressive lending approach")
        
        # Collateral coverage issues
        if risk_scores.get(RiskFactor.COLLATERAL_COVERAGE.value, 500) < 450:
            strategies.append("Require additional collateral")
            strategies.append("Consider group guarantee")
        
        # Mobile money usage issues
        if risk_scores.get(RiskFactor.MOBILE_MONEY_USAGE.value, 500) < 450:
            strategies.append("Assist with mobile money account setup")
            strategies.append("Provide digital financial literacy training")
        
        # Business-specific strategies
        if loan_type == "business":
            strategies.append("Require business financial statements")
            strategies.append("Conduct site visit verification")
            strategies.append("Implement business mentorship program")
        
        return strategies
    
    def _get_mock_customer_data(self, customer_id: str) -> Dict[str, Any]:
        """Generate mock customer data for testing"""
        return {
            "customer_id": customer_id,
            "monthly_income": 1200000,
            "employment_status": "private_company",
            "employment_duration_months": 24,
            "employer_name": "ABC Company Ltd",
            "region": "Dar es Salaam",
            "district": "Kinondoni",
            "nida_verified": True,
            "tin_verified": True,
            "mobile_money_registered": True,
            "mobile_money_accounts": [
                {"provider": "mpesa", "transaction_count": 50},
                {"provider": "airtel", "transaction_count": 20},
            ],
            "existing_debt_payment": 200000,
            "collateral_type": "none",
            "collateral_value": 0,
            "is_first_time_borrower": False,
            "payment_history": {
                "on_time_payments": 0.85,
                "credit_utilization": 0.45,
                "credit_age_months": 18,
                "defaults": 0,
            },
            "multiple_income_sources": False,
        }

# Global instance
risk_assessment = RiskAssessment() 