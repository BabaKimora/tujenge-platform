"""
Tanzania Compliance Utility for Fintech Platform
Handles regulatory compliance specific to Tanzania banking and microfinance
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import json

logger = logging.getLogger(__name__)

class ComplianceType(Enum):
    """Types of compliance checks"""
    KYC = "kyc"
    AML = "aml"
    BOT = "bot"  # Bank of Tanzania
    FAIR_COMPETITION = "fair_competition"
    DATA_PROTECTION = "data_protection"
    CONSUMER_PROTECTION = "consumer_protection"

class ComplianceStatus(Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING = "pending"
    REQUIRES_REVIEW = "requires_review"
    EXPIRED = "expired"

class TanzaniaCompliance:
    """Tanzania-specific compliance management"""
    
    def __init__(self):
        self.compliance_requirements = self._load_compliance_requirements()
        
    def _load_compliance_requirements(self) -> Dict[str, Any]:
        """Load Tanzania compliance requirements"""
        return {
            "kyc": {
                "required_documents": [
                    "nida_card",
                    "proof_of_income",
                    "proof_of_residence"
                ],
                "verification_level": "enhanced",
                "validity_period_days": 365,
                "risk_categories": ["low", "medium", "high"],
            },
            "aml": {
                "screening_required": True,
                "pep_screening": True,  # Politically Exposed Persons
                "sanctions_screening": True,
                "transaction_monitoring": True,
                "reporting_threshold_tzs": 10000000,  # 10M TZS
                "suspicious_activity_reporting": True,
            },
            "bot_regulations": {
                "microfinance_license_required": True,
                "capital_adequacy_ratio": 8.0,  # Minimum 8%
                "loan_loss_provision": 5.0,  # Minimum 5%
                "interest_rate_cap": 30.0,  # Maximum 30% annual
                "customer_protection": True,
                "digital_lending_compliance": True,
            },
            "fair_competition": {
                "market_conduct_rules": True,
                "pricing_transparency": True,
                "fair_lending_practices": True,
                "customer_complaints_handling": True,
            },
            "data_protection": {
                "gdpr_compliance": False,  # Tanzania has own laws
                "tanzania_data_protection_act": True,
                "consent_management": True,
                "data_localization": True,
                "breach_notification_hours": 72,
            },
        }
    
    async def check_customer_compliance(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive compliance check for customer"""
        try:
            compliance_results = {}
            
            # KYC Compliance
            kyc_result = await self._check_kyc_compliance(customer_data)
            compliance_results["kyc"] = kyc_result
            
            # AML Compliance
            aml_result = await self._check_aml_compliance(customer_data)
            compliance_results["aml"] = aml_result
            
            # Customer Protection
            protection_result = await self._check_customer_protection(customer_data)
            compliance_results["customer_protection"] = protection_result
            
            # Overall compliance status
            overall_status = self._calculate_overall_compliance(compliance_results)
            
            return {
                "customer_id": customer_data.get("customer_id"),
                "overall_status": overall_status,
                "compliance_details": compliance_results,
                "compliance_score": self._calculate_compliance_score(compliance_results),
                "recommendations": self._generate_compliance_recommendations(compliance_results),
                "next_review_date": datetime.utcnow() + timedelta(days=90),
                "checked_at": datetime.utcnow(),
            }
            
        except Exception as e:
            logger.error(f"Customer compliance check error: {str(e)}")
            return {
                "customer_id": customer_data.get("customer_id"),
                "overall_status": ComplianceStatus.REQUIRES_REVIEW.value,
                "error": f"Compliance check failed: {str(e)}",
                "checked_at": datetime.utcnow(),
            }
    
    async def _check_kyc_compliance(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check KYC compliance"""
        try:
            kyc_score = 0
            total_checks = 0
            issues = []
            
            # NIDA verification
            total_checks += 1
            if customer_data.get("nida_verified"):
                kyc_score += 1
            else:
                issues.append("NIDA verification required")
            
            # Income verification
            total_checks += 1
            if customer_data.get("monthly_income"):
                kyc_score += 1
            else:
                issues.append("Income verification required")
            
            # Contact verification
            total_checks += 1
            if customer_data.get("phone_number") and customer_data.get("email"):
                kyc_score += 1
            else:
                issues.append("Contact information incomplete")
            
            # Address verification
            total_checks += 1
            if (customer_data.get("region") and 
                customer_data.get("district") and 
                customer_data.get("street_address")):
                kyc_score += 1
            else:
                issues.append("Address verification incomplete")
            
            # Employment verification
            total_checks += 1
            if customer_data.get("employment_status") and customer_data.get("employer_name"):
                kyc_score += 1
            else:
                issues.append("Employment verification required")
            
            compliance_percentage = (kyc_score / total_checks) * 100
            
            if compliance_percentage >= 80:
                status = ComplianceStatus.COMPLIANT.value
            elif compliance_percentage >= 60:
                status = ComplianceStatus.PENDING.value
            else:
                status = ComplianceStatus.NON_COMPLIANT.value
            
            return {
                "status": status,
                "score": kyc_score,
                "total_checks": total_checks,
                "compliance_percentage": compliance_percentage,
                "issues": issues,
                "enhanced_dd_required": compliance_percentage < 80,
                "last_updated": datetime.utcnow(),
            }
            
        except Exception as e:
            logger.error(f"KYC compliance check error: {str(e)}")
            return {
                "status": ComplianceStatus.REQUIRES_REVIEW.value,
                "error": str(e),
                "last_updated": datetime.utcnow(),
            }
    
    async def _check_aml_compliance(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check AML compliance"""
        try:
            aml_flags = []
            risk_score = 0
            
            # High-risk occupation check
            high_risk_occupations = [
                "politician", "government_official", "cash_intensive_business",
                "money_exchange", "real_estate", "gambling"
            ]
            
            employment = customer_data.get("employment_status", "").lower()
            if any(risk_job in employment for risk_job in high_risk_occupations):
                aml_flags.append("High-risk occupation")
                risk_score += 30
            
            # High transaction amounts
            monthly_income = customer_data.get("monthly_income", 0)
            if monthly_income > 5000000:  # 5M TZS
                aml_flags.append("High income bracket - enhanced monitoring required")
                risk_score += 20
            
            # Geographic risk
            high_risk_regions = ["Border regions", "Mining areas"]
            region = customer_data.get("region", "")
            if any(risk_region in region for risk_region in high_risk_regions):
                aml_flags.append("High-risk geographic location")
                risk_score += 15
            
            # PEP screening (mock)
            # In real implementation, check against PEP databases
            pep_status = "clear"  # clear, match, potential_match
            
            # Sanctions screening (mock)
            sanctions_status = "clear"  # clear, match, potential_match
            
            if risk_score <= 20:
                aml_status = ComplianceStatus.COMPLIANT.value
                monitoring_level = "standard"
            elif risk_score <= 50:
                aml_status = ComplianceStatus.PENDING.value
                monitoring_level = "enhanced"
            else:
                aml_status = ComplianceStatus.NON_COMPLIANT.value
                monitoring_level = "intensive"
            
            return {
                "status": aml_status,
                "risk_score": risk_score,
                "monitoring_level": monitoring_level,
                "pep_status": pep_status,
                "sanctions_status": sanctions_status,
                "flags": aml_flags,
                "enhanced_dd_required": risk_score > 30,
                "ongoing_monitoring": True,
                "last_screening": datetime.utcnow(),
                "next_screening": datetime.utcnow() + timedelta(days=30),
            }
            
        except Exception as e:
            logger.error(f"AML compliance check error: {str(e)}")
            return {
                "status": ComplianceStatus.REQUIRES_REVIEW.value,
                "error": str(e),
                "last_screening": datetime.utcnow(),
            }
    
    async def _check_customer_protection(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check customer protection compliance"""
        try:
            protection_score = 0
            total_checks = 0
            issues = []
            
            # Financial literacy assessment
            total_checks += 1
            education_level = customer_data.get("education_level", "").lower()
            if education_level in ["university", "college", "secondary"]:
                protection_score += 1
            else:
                issues.append("Financial literacy assessment recommended")
            
            # Language preference accommodation
            total_checks += 1
            preferred_language = customer_data.get("preferred_language", "").lower()
            if preferred_language in ["swahili", "english"]:
                protection_score += 1
            else:
                issues.append("Language accommodation may be required")
            
            # Income appropriateness
            total_checks += 1
            monthly_income = customer_data.get("monthly_income", 0)
            if monthly_income >= 300000:  # Minimum viable income
                protection_score += 1
            else:
                issues.append("Income may not support loan obligations")
            
            # Geographic accessibility
            total_checks += 1
            region = customer_data.get("region", "")
            if region in ["Dar es Salaam", "Mwanza", "Arusha", "Dodoma"]:
                protection_score += 1
            else:
                issues.append("Rural customer - enhanced support may be needed")
            
            compliance_percentage = (protection_score / total_checks) * 100
            
            if compliance_percentage >= 75:
                status = ComplianceStatus.COMPLIANT.value
            elif compliance_percentage >= 50:
                status = ComplianceStatus.PENDING.value
            else:
                status = ComplianceStatus.NON_COMPLIANT.value
            
            return {
                "status": status,
                "score": protection_score,
                "total_checks": total_checks,
                "compliance_percentage": compliance_percentage,
                "issues": issues,
                "financial_literacy_required": protection_score < 3,
                "enhanced_support_required": "rural" in str(issues).lower(),
                "last_updated": datetime.utcnow(),
            }
            
        except Exception as e:
            logger.error(f"Customer protection check error: {str(e)}")
            return {
                "status": ComplianceStatus.REQUIRES_REVIEW.value,
                "error": str(e),
                "last_updated": datetime.utcnow(),
            }
    
    def _calculate_overall_compliance(self, compliance_results: Dict[str, Any]) -> str:
        """Calculate overall compliance status"""
        try:
            statuses = []
            for check_type, result in compliance_results.items():
                if isinstance(result, dict) and "status" in result:
                    statuses.append(result["status"])
            
            # If any critical check fails, overall is non-compliant
            if ComplianceStatus.NON_COMPLIANT.value in statuses:
                return ComplianceStatus.NON_COMPLIANT.value
            
            # If any check is pending, overall is pending
            if ComplianceStatus.PENDING.value in statuses:
                return ComplianceStatus.PENDING.value
            
            # If any check requires review, overall requires review
            if ComplianceStatus.REQUIRES_REVIEW.value in statuses:
                return ComplianceStatus.REQUIRES_REVIEW.value
            
            # If all checks are compliant
            return ComplianceStatus.COMPLIANT.value
            
        except Exception as e:
            logger.error(f"Overall compliance calculation error: {str(e)}")
            return ComplianceStatus.REQUIRES_REVIEW.value
    
    def _calculate_compliance_score(self, compliance_results: Dict[str, Any]) -> float:
        """Calculate numerical compliance score (0-100)"""
        try:
            total_score = 0
            total_weight = 0
            
            weights = {
                "kyc": 0.4,  # 40% weight
                "aml": 0.3,  # 30% weight
                "customer_protection": 0.3,  # 30% weight
            }
            
            for check_type, result in compliance_results.items():
                if check_type in weights and isinstance(result, dict):
                    weight = weights[check_type]
                    
                    if "compliance_percentage" in result:
                        score = result["compliance_percentage"]
                    elif result.get("status") == ComplianceStatus.COMPLIANT.value:
                        score = 100
                    elif result.get("status") == ComplianceStatus.PENDING.value:
                        score = 60
                    else:
                        score = 0
                    
                    total_score += score * weight
                    total_weight += weight
            
            if total_weight > 0:
                return round(total_score / total_weight, 2)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Compliance score calculation error: {str(e)}")
            return 0.0
    
    def _generate_compliance_recommendations(self, compliance_results: Dict[str, Any]) -> List[str]:
        """Generate compliance improvement recommendations"""
        try:
            recommendations = []
            
            for check_type, result in compliance_results.items():
                if isinstance(result, dict):
                    issues = result.get("issues", [])
                    status = result.get("status")
                    
                    if status != ComplianceStatus.COMPLIANT.value:
                        recommendations.extend([
                            f"{check_type.upper()}: {issue}" for issue in issues
                        ])
                    
                    # Specific recommendations based on check type
                    if check_type == "kyc" and result.get("enhanced_dd_required"):
                        recommendations.append("Enhanced due diligence required before loan approval")
                    
                    if check_type == "aml" and result.get("risk_score", 0) > 30:
                        recommendations.append("Enhanced AML monitoring and periodic reviews required")
                    
                    if check_type == "customer_protection" and result.get("financial_literacy_required"):
                        recommendations.append("Financial literacy training recommended before loan disbursement")
            
            # Add general recommendations
            if not recommendations:
                recommendations.append("Customer meets all compliance requirements")
            else:
                recommendations.append("Complete all recommended actions before loan approval")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Compliance recommendations error: {str(e)}")
            return ["Unable to generate recommendations - manual review required"]
    
    async def check_loan_compliance(self, loan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check loan-specific compliance requirements"""
        try:
            loan_amount = loan_data.get("amount", 0)
            annual_interest_rate = loan_data.get("annual_interest_rate", 0)
            term_months = loan_data.get("term_months", 0)
            customer_monthly_income = loan_data.get("customer_monthly_income", 0)
            
            compliance_issues = []
            compliance_score = 100
            
            # Interest rate cap check (BOT regulation)
            max_rate = self.compliance_requirements["bot_regulations"]["interest_rate_cap"]
            if annual_interest_rate > max_rate:
                compliance_issues.append(f"Interest rate {annual_interest_rate}% exceeds maximum {max_rate}%")
                compliance_score -= 40
            
            # Debt-to-income ratio check
            if customer_monthly_income > 0:
                monthly_payment = self._calculate_monthly_payment(loan_amount, annual_interest_rate, term_months)
                debt_to_income_ratio = (monthly_payment / customer_monthly_income) * 100
                
                if debt_to_income_ratio > 40:  # 40% DTI limit
                    compliance_issues.append(f"Debt-to-income ratio {debt_to_income_ratio:.1f}% exceeds 40% limit")
                    compliance_score -= 30
            
            # Loan amount limits for microfinance
            if loan_amount > 50000000:  # 50M TZS
                compliance_issues.append("Large loan requires additional regulatory approval")
                compliance_score -= 20
            
            if compliance_score >= 80:
                status = ComplianceStatus.COMPLIANT.value
            elif compliance_score >= 60:
                status = ComplianceStatus.PENDING.value
            else:
                status = ComplianceStatus.NON_COMPLIANT.value
            
            return {
                "status": status,
                "compliance_score": compliance_score,
                "issues": compliance_issues,
                "recommendations": self._generate_loan_recommendations(compliance_issues),
                "regulatory_approvals_required": loan_amount > 50000000,
                "checked_at": datetime.utcnow(),
            }
            
        except Exception as e:
            logger.error(f"Loan compliance check error: {str(e)}")
            return {
                "status": ComplianceStatus.REQUIRES_REVIEW.value,
                "error": str(e),
                "checked_at": datetime.utcnow(),
            }
    
    def _calculate_monthly_payment(self, principal: float, annual_rate: float, term_months: int) -> float:
        """Calculate monthly loan payment"""
        try:
            if annual_rate == 0:
                return principal / term_months
            
            monthly_rate = annual_rate / 100 / 12
            payment = principal * (monthly_rate * (1 + monthly_rate)**term_months) / ((1 + monthly_rate)**term_months - 1)
            return payment
            
        except Exception:
            return 0.0
    
    def _generate_loan_recommendations(self, issues: List[str]) -> List[str]:
        """Generate loan compliance recommendations"""
        recommendations = []
        
        for issue in issues:
            if "interest rate" in issue.lower():
                recommendations.append("Reduce interest rate to comply with BOT regulations")
            elif "debt-to-income" in issue.lower():
                recommendations.append("Reduce loan amount or extend term to improve affordability")
            elif "large loan" in issue.lower():
                recommendations.append("Obtain regulatory approval for large loan disbursement")
        
        if not recommendations:
            recommendations.append("Loan meets all compliance requirements")
        
        return recommendations
    
    async def get_compliance_report(self, organization_id: str) -> Dict[str, Any]:
        """Generate comprehensive compliance report for the organization"""
        try:
            # Mock compliance metrics for demonstration
            return {
                "organization_id": organization_id,
                "report_period": {
                    "start_date": datetime.utcnow() - timedelta(days=30),
                    "end_date": datetime.utcnow(),
                },
                "overall_compliance_score": 87.5,
                "regulatory_status": {
                    "bot_compliance": ComplianceStatus.COMPLIANT.value,
                    "aml_compliance": ComplianceStatus.COMPLIANT.value,
                    "data_protection": ComplianceStatus.PENDING.value,
                    "consumer_protection": ComplianceStatus.COMPLIANT.value,
                },
                "key_metrics": {
                    "customers_screened": 1247,
                    "kyc_completion_rate": 94.2,
                    "aml_flags_raised": 23,
                    "regulatory_breaches": 0,
                    "customer_complaints": 8,
                },
                "risk_assessment": {
                    "overall_risk_level": "Low",
                    "high_risk_customers": 15,
                    "enhanced_monitoring_cases": 42,
                    "pep_matches": 3,
                },
                "recommendations": [
                    "Complete data protection compliance certification",
                    "Enhance customer onboarding documentation",
                    "Update AML policies for new regulations",
                ],
                "next_review_date": datetime.utcnow() + timedelta(days=90),
                "generated_at": datetime.utcnow(),
            }
            
        except Exception as e:
            logger.error(f"Compliance report generation error: {str(e)}")
            return {
                "organization_id": organization_id,
                "error": f"Report generation failed: {str(e)}",
                "generated_at": datetime.utcnow(),
            }

# Global instance
tanzania_compliance = TanzaniaCompliance() 