"""
Loan Calculator Utility for Tanzania Fintech Platform
Handles all loan calculations including amortization, schedules, and payment allocations
"""

import math
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any
import calendar

class LoanCalculator:
    """Comprehensive loan calculation utility"""
    
    def __init__(self):
        self.currency = "TZS"
        self.precision = 2
    
    def calculate_loan_terms(
        self,
        principal: float,
        annual_rate: float,
        tenure_months: int,
        frequency: str = "monthly",
        processing_fee_rate: float = 2.5,
        insurance_rate: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive loan terms
        
        Args:
            principal: Loan principal amount
            annual_rate: Annual interest rate (percentage)
            tenure_months: Loan tenure in months
            frequency: Repayment frequency (daily, weekly, monthly)
            processing_fee_rate: Processing fee as percentage of principal
            insurance_rate: Insurance rate as percentage of principal
        
        Returns:
            Dict containing all loan terms and calculations
        """
        try:
            # Convert to Decimal for precision
            principal = Decimal(str(principal))
            annual_rate = Decimal(str(annual_rate))
            
            # Calculate fees
            processing_fee = self._round_currency(principal * Decimal(str(processing_fee_rate)) / 100)
            insurance_fee = self._round_currency(principal * Decimal(str(insurance_rate)) / 100)
            total_fees = processing_fee + insurance_fee
            
            # Calculate installment based on frequency
            if frequency == "daily":
                periods = tenure_months * 30  # Approximate days per month
                periodic_rate = annual_rate / 365 / 100
            elif frequency == "weekly":
                periods = tenure_months * 4  # Approximate weeks per month
                periodic_rate = annual_rate / 52 / 100
            elif frequency == "biweekly":
                periods = tenure_months * 2  # Bi-weekly payments per month
                periodic_rate = annual_rate / 26 / 100
            else:  # monthly
                periods = tenure_months
                periodic_rate = annual_rate / 12 / 100
            
            # Calculate EMI using formula: EMI = P * r * (1+r)^n / ((1+r)^n - 1)
            if periodic_rate == 0:
                installment = principal / Decimal(str(periods))
            else:
                factor = (1 + periodic_rate) ** periods
                installment = principal * periodic_rate * factor / (factor - 1)
            
            installment = self._round_currency(installment)
            
            # Calculate total repayment and interest
            total_repayment = installment * Decimal(str(periods))
            total_interest = total_repayment - principal
            
            # Calculate effective rates
            effective_annual_rate = self._calculate_effective_rate(
                principal, installment, periods, frequency
            )
            
            # Calculate APR (including fees)
            apr = self._calculate_apr(
                principal, installment, periods, total_fees, frequency
            )
            
            return {
                "principal": float(principal),
                "annual_interest_rate": float(annual_rate),
                "effective_annual_rate": float(effective_annual_rate),
                "apr": float(apr),
                "tenure_months": tenure_months,
                "repayment_frequency": frequency,
                "number_of_payments": int(periods),
                "installment_amount": float(installment),
                "total_repayment": float(total_repayment),
                "total_interest": float(total_interest),
                "processing_fee": float(processing_fee),
                "insurance_fee": float(insurance_fee),
                "total_fees": float(total_fees),
                "net_disbursement": float(principal - total_fees),
                "interest_to_principal_ratio": float(total_interest / principal * 100),
                "calculated_at": datetime.utcnow(),
            }
            
        except Exception as e:
            raise ValueError(f"Loan calculation error: {str(e)}")
    
    def generate_repayment_schedule(
        self,
        principal: float,
        annual_rate: float,
        tenure_months: int,
        start_date: date = None,
        frequency: str = "monthly"
    ) -> List[Dict[str, Any]]:
        """
        Generate detailed repayment schedule
        
        Args:
            principal: Loan principal amount
            annual_rate: Annual interest rate (percentage)
            tenure_months: Loan tenure in months
            start_date: Loan start date
            frequency: Repayment frequency (daily, weekly, monthly)
        
        Returns:
            List of payment schedule dictionaries
        """
        try:
            if start_date is None:
                start_date = date.today()
                
            # Calculate loan terms first
            terms = self.calculate_loan_terms(principal, annual_rate, tenure_months, frequency)
            
            schedule = []
            remaining_balance = Decimal(str(principal))
            periodic_rate = Decimal(str(annual_rate)) / 12 / 100  # Monthly rate
            installment = Decimal(str(terms["installment_amount"]))
            
            # Determine payment frequency settings
            if frequency == "daily":
                periods = tenure_months * 30
                periodic_rate = Decimal(str(annual_rate)) / 365 / 100
                date_increment = timedelta(days=1)
            elif frequency == "weekly":
                periods = tenure_months * 4
                periodic_rate = Decimal(str(annual_rate)) / 52 / 100
                date_increment = timedelta(weeks=1)
            elif frequency == "biweekly":
                periods = tenure_months * 2
                periodic_rate = Decimal(str(annual_rate)) / 26 / 100
                date_increment = timedelta(weeks=2)
            else:  # monthly
                periods = tenure_months
                periodic_rate = Decimal(str(annual_rate)) / 12 / 100
            
            current_date = start_date
            
            for payment_number in range(1, int(periods) + 1):
                # Calculate interest for this period
                interest_payment = self._round_currency(remaining_balance * periodic_rate)
                
                # Calculate principal payment
                principal_payment = installment - interest_payment
                
                # Adjust for final payment to clear remaining balance
                if payment_number == periods:
                    principal_payment = remaining_balance
                    installment = interest_payment + principal_payment
                
                # Ensure principal payment doesn't exceed remaining balance
                if principal_payment > remaining_balance:
                    principal_payment = remaining_balance
                    installment = interest_payment + principal_payment
                
                # Calculate new balance
                new_balance = remaining_balance - principal_payment
                
                # Create payment record
                payment_record = {
                    "payment_number": payment_number,
                    "due_date": current_date.isoformat(),
                    "installment_amount": float(installment),
                    "principal_payment": float(principal_payment),
                    "interest_payment": float(interest_payment),
                    "remaining_balance": float(new_balance),
                    "cumulative_principal": float(Decimal(str(principal)) - new_balance),
                    "cumulative_interest": float(sum(
                        Decimal(str(p["interest_payment"])) for p in schedule
                    ) + interest_payment),
                    "status": "pending",
                    "days_from_start": (current_date - start_date).days,
                }
                
                schedule.append(payment_record)
                
                # Update for next iteration
                remaining_balance = new_balance
                
                # Move to next payment date
                if frequency == "monthly":
                    current_date = self._add_months(current_date, 1)
                else:
                    current_date = current_date + date_increment
                
                # Break if balance is fully paid
                if remaining_balance <= 0:
                    break
            
            return schedule
            
        except Exception as e:
            raise ValueError(f"Schedule generation error: {str(e)}")
    
    def allocate_payment(
        self,
        payment_amount: float,
        outstanding_principal: float,
        accrued_interest: float,
        penalty_amount: float = 0,
        fees_due: float = 0
    ) -> Dict[str, Any]:
        """
        Allocate payment across different components (Tanzania banking standard)
        Priority: Fees -> Penalties -> Interest -> Principal
        
        Args:
            payment_amount: Total payment amount
            outstanding_principal: Outstanding principal balance
            accrued_interest: Accrued interest amount
            penalty_amount: Penalty/late fees amount
            fees_due: Other fees due
        
        Returns:
            Dict showing payment allocation
        """
        try:
            payment = Decimal(str(payment_amount))
            principal = Decimal(str(outstanding_principal))
            interest = Decimal(str(accrued_interest))
            penalties = Decimal(str(penalty_amount))
            fees = Decimal(str(fees_due))
            
            # Initialize allocation
            allocation = {
                "total_payment": float(payment),
                "fees_payment": 0,
                "penalty_payment": 0,
                "interest_payment": 0,
                "principal_payment": 0,
                "excess_payment": 0,
            }
            
            remaining_payment = payment
            
            # 1. Allocate to fees first
            if remaining_payment > 0 and fees > 0:
                fees_payment = min(remaining_payment, fees)
                allocation["fees_payment"] = float(fees_payment)
                remaining_payment -= fees_payment
            
            # 2. Allocate to penalties
            if remaining_payment > 0 and penalties > 0:
                penalty_payment = min(remaining_payment, penalties)
                allocation["penalty_payment"] = float(penalty_payment)
                remaining_payment -= penalty_payment
            
            # 3. Allocate to interest
            if remaining_payment > 0 and interest > 0:
                interest_payment = min(remaining_payment, interest)
                allocation["interest_payment"] = float(interest_payment)
                remaining_payment -= interest_payment
            
            # 4. Allocate to principal
            if remaining_payment > 0 and principal > 0:
                principal_payment = min(remaining_payment, principal)
                allocation["principal_payment"] = float(principal_payment)
                remaining_payment -= principal_payment
            
            # 5. Any excess payment
            if remaining_payment > 0:
                allocation["excess_payment"] = float(remaining_payment)
            
            # Calculate new balances
            allocation["new_principal_balance"] = float(principal - Decimal(str(allocation["principal_payment"])))
            allocation["new_interest_balance"] = float(interest - Decimal(str(allocation["interest_payment"])))
            allocation["new_penalty_balance"] = float(penalties - Decimal(str(allocation["penalty_payment"])))
            allocation["new_fees_balance"] = float(fees - Decimal(str(allocation["fees_payment"])))
            
            return allocation
            
        except Exception as e:
            raise ValueError(f"Payment allocation error: {str(e)}")
    
    def calculate_early_settlement(
        self,
        outstanding_principal: float,
        accrued_interest: float,
        remaining_months: int,
        annual_rate: float,
        rebate_method: str = "rule_of_78"
    ) -> Dict[str, Any]:
        """
        Calculate early settlement amount with interest rebate
        
        Args:
            outstanding_principal: Remaining principal balance
            accrued_interest: Interest accrued to date
            remaining_months: Remaining loan tenure
            annual_rate: Annual interest rate
            rebate_method: Method for calculating rebate (rule_of_78, actuarial)
        
        Returns:
            Dict containing settlement calculation
        """
        try:
            principal = Decimal(str(outstanding_principal))
            interest = Decimal(str(accrued_interest))
            
            if rebate_method == "rule_of_78":
                # Rule of 78 rebate calculation
                total_months = remaining_months
                sum_of_digits = total_months * (total_months + 1) / 2
                remaining_sum = remaining_months * (remaining_months + 1) / 2
                rebate_factor = Decimal(str(remaining_sum / sum_of_digits))
            else:
                # Actuarial rebate (simple approximation)
                rebate_factor = Decimal(str(remaining_months)) / Decimal(str(remaining_months + 6))
            
            # Calculate rebate amount
            unearned_interest = interest * rebate_factor
            settlement_interest = interest - unearned_interest
            
            # Early settlement penalty (if applicable)
            penalty_rate = Decimal("0.02")  # 2% of outstanding principal
            early_settlement_penalty = principal * penalty_rate
            
            # Total settlement amount
            settlement_amount = principal + settlement_interest + early_settlement_penalty
            
            # Savings calculation
            original_remaining_payments = self._calculate_remaining_payments(
                principal, annual_rate, remaining_months
            )
            savings = original_remaining_payments - settlement_amount
            
            return {
                "outstanding_principal": float(principal),
                "accrued_interest": float(interest),
                "unearned_interest_rebate": float(unearned_interest),
                "settlement_interest": float(settlement_interest),
                "early_settlement_penalty": float(early_settlement_penalty),
                "total_settlement_amount": float(settlement_amount),
                "original_remaining_payments": float(original_remaining_payments),
                "savings_from_early_settlement": float(savings),
                "rebate_method": rebate_method,
                "calculated_at": datetime.utcnow(),
            }
            
        except Exception as e:
            raise ValueError(f"Early settlement calculation error: {str(e)}")
    
    def calculate_restructure_terms(
        self,
        outstanding_balance: float,
        new_tenure_months: int,
        new_annual_rate: float,
        restructure_fee_rate: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate new terms for loan restructuring
        
        Args:
            outstanding_balance: Current outstanding balance
            new_tenure_months: New tenure in months
            new_annual_rate: New annual interest rate
            restructure_fee_rate: Restructuring fee as percentage
        
        Returns:
            Dict containing new loan terms
        """
        try:
            # Calculate restructuring fee
            restructure_fee = self._round_currency(
                Decimal(str(outstanding_balance)) * Decimal(str(restructure_fee_rate)) / 100
            )
            
            # New principal amount (including restructure fee)
            new_principal = Decimal(str(outstanding_balance)) + restructure_fee
            
            # Calculate new terms
            new_terms = self.calculate_loan_terms(
                principal=float(new_principal),
                annual_rate=new_annual_rate,
                tenure_months=new_tenure_months
            )
            
            # Add restructuring specific information
            new_terms.update({
                "original_outstanding_balance": outstanding_balance,
                "restructure_fee": float(restructure_fee),
                "new_principal_amount": float(new_principal),
                "restructured_at": datetime.utcnow(),
            })
            
            return new_terms
            
        except Exception as e:
            raise ValueError(f"Restructure calculation error: {str(e)}")
    
    def calculate_penalty(
        self, 
        overdue_amount: float, 
        days_overdue: int, 
        penalty_rate: float = 2.0
    ) -> Dict[str, Any]:
        """
        Calculate penalty for overdue payments
        
        Args:
            overdue_amount: Amount that is overdue
            days_overdue: Number of days overdue
            penalty_rate: Monthly penalty rate as percentage
            
        Returns:
            Dict with penalty calculation details
        """
        try:
            overdue_decimal = Decimal(str(overdue_amount))
            daily_penalty_rate = Decimal(str(penalty_rate)) / Decimal('100') / Decimal('30')  # Monthly to daily
            
            # Calculate penalty amount
            penalty_amount = overdue_decimal * daily_penalty_rate * Decimal(str(days_overdue))
            penalty_amount = penalty_amount.quantize(self.precision, rounding=ROUND_HALF_UP)
            
            return {
                "overdue_amount": float(overdue_decimal),
                "days_overdue": days_overdue,
                "daily_penalty_rate": float(daily_penalty_rate * 100),
                "penalty_amount": float(penalty_amount),
                "total_amount_due": float(overdue_decimal + penalty_amount),
            }
            
        except Exception as e:
            raise ValueError(f"Penalty calculation failed: {str(e)}")
    
    def loan_affordability_check(
        self, 
        monthly_income: float, 
        monthly_expenses: float, 
        proposed_installment: float,
        debt_to_income_ratio: float = 40.0
    ) -> Dict[str, Any]:
        """
        Check loan affordability based on income and expenses
        
        Args:
            monthly_income: Customer's monthly income
            monthly_expenses: Customer's monthly expenses
            proposed_installment: Proposed loan installment
            debt_to_income_ratio: Maximum debt-to-income ratio allowed
            
        Returns:
            Dict with affordability analysis
        """
        try:
            income_decimal = Decimal(str(monthly_income))
            expenses_decimal = Decimal(str(monthly_expenses))
            installment_decimal = Decimal(str(proposed_installment))
            ratio_decimal = Decimal(str(debt_to_income_ratio))
            
            # Calculate disposable income
            disposable_income = income_decimal - expenses_decimal
            
            # Calculate debt-to-income ratio
            current_dti = (installment_decimal / income_decimal) * Decimal('100')
            
            # Calculate maximum affordable installment
            max_affordable = income_decimal * (ratio_decimal / Decimal('100'))
            
            # Affordability checks
            is_affordable = (
                installment_decimal <= max_affordable and
                installment_decimal <= disposable_income * Decimal('0.8')  # Leave 20% buffer
            )
            
            return {
                "monthly_income": float(income_decimal),
                "monthly_expenses": float(expenses_decimal),
                "disposable_income": float(disposable_income),
                "proposed_installment": float(installment_decimal),
                "debt_to_income_ratio": float(current_dti),
                "maximum_dti_allowed": float(ratio_decimal),
                "maximum_affordable_installment": float(max_affordable),
                "is_affordable": is_affordable,
                "affordability_score": min(100.0, float(max_affordable / installment_decimal * 100)) if installment_decimal > 0 else 0,
                "recommendation": "Approved" if is_affordable else "Review required",
            }
            
        except Exception as e:
            raise ValueError(f"Affordability check failed: {str(e)}")
    
    def _round_currency(self, amount: Decimal) -> Decimal:
        """Round amount to currency precision"""
        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def _calculate_effective_rate(
        self,
        principal: Decimal,
        installment: Decimal,
        periods: int,
        frequency: str
    ) -> Decimal:
        """Calculate effective annual rate"""
        try:
            if frequency == "monthly":
                periods_per_year = 12
            elif frequency == "weekly":
                periods_per_year = 52
            elif frequency == "biweekly":
                periods_per_year = 26
            else:  # daily
                periods_per_year = 365
            
            # Use approximation method for effective rate
            periodic_rate = (installment * periods - principal) / (principal * periods / 2)
            effective_annual_rate = periodic_rate * periods_per_year
            
            return self._round_currency(effective_annual_rate * 100)
            
        except:
            return Decimal("0")
    
    def _calculate_apr(
        self,
        principal: Decimal,
        installment: Decimal,
        periods: int,
        fees: Decimal,
        frequency: str
    ) -> Decimal:
        """Calculate Annual Percentage Rate (APR) including fees"""
        try:
            # Adjust principal by fees for APR calculation
            net_principal = principal - fees
            
            if frequency == "monthly":
                periods_per_year = 12
            elif frequency == "weekly":
                periods_per_year = 52
            elif frequency == "biweekly":
                periods_per_year = 26
            else:  # daily
                periods_per_year = 365
            
            # APR calculation including fees
            total_cost = installment * periods
            total_interest_and_fees = total_cost - net_principal
            periodic_rate = total_interest_and_fees / (net_principal * periods / 2)
            apr = periodic_rate * periods_per_year
            
            return self._round_currency(apr * 100)
            
        except:
            return Decimal("0")
    
    def _calculate_remaining_payments(
        self,
        principal: Decimal,
        annual_rate: float,
        months: int
    ) -> Decimal:
        """Calculate total remaining payments"""
        try:
            monthly_rate = Decimal(str(annual_rate)) / 12 / 100
            
            if monthly_rate == 0:
                return principal
            
            factor = (1 + monthly_rate) ** months
            installment = principal * monthly_rate * factor / (factor - 1)
            
            return self._round_currency(installment * months)
            
        except:
            return principal
    
    def _add_months(self, source_date: date, months: int) -> date:
        """Add months to a date (replacement for dateutil.relativedelta)"""
        try:
            month = source_date.month - 1 + months
            year = source_date.year + month // 12
            month = month % 12 + 1
            day = min(source_date.day, calendar.monthrange(year, month)[1])
            return date(year, month, day)
        except:
            # Fallback to approximate calculation
            return source_date + timedelta(days=months * 30)

# Global instance
loan_calculator = LoanCalculator() 