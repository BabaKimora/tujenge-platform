"""
Loan Management Router for Tanzania Fintech Platform
Comprehensive loan lifecycle management with Tanzania-specific features
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, validator

from backend.utils.audit_logger import audit_logger
from backend.utils.security import security_manager
from backend.utils.loan_calculator import LoanCalculator
from backend.utils.risk_assessment import RiskAssessment
from backend.utils.mobile_money_integration import MobileMoneyService

router = APIRouter(tags=["Loan Management"])
security = HTTPBearer()

# Enums for loan management
class LoanStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    ACTIVE = "active"
    COMPLETED = "completed"
    DEFAULTED = "defaulted"
    WRITTEN_OFF = "written_off"

class LoanType(str, Enum):
    PERSONAL = "personal"
    BUSINESS = "business"
    EMERGENCY = "emergency"
    EDUCATION = "education"
    AGRICULTURE = "agriculture"
    GROUP = "group"

class RepaymentFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

class CollateralType(str, Enum):
    NONE = "none"
    VEHICLE = "vehicle"
    PROPERTY = "property"
    EQUIPMENT = "equipment"
    INVENTORY = "inventory"
    GUARANTOR = "guarantor"

# Pydantic Models
class LoanApplicationCreate(BaseModel):
    """Loan application creation model"""
    customer_id: str = Field(..., description="Customer ID")
    loan_type: LoanType = Field(..., description="Type of loan")
    loan_amount: float = Field(..., ge=50000, le=10000000, description="Loan amount in TZS")
    loan_purpose: str = Field(..., min_length=10, max_length=500, description="Purpose of loan")
    tenure_months: int = Field(..., ge=1, le=60, description="Loan tenure in months")
    repayment_frequency: RepaymentFrequency = Field(default=RepaymentFrequency.MONTHLY)
    
    # Collateral information
    collateral_type: CollateralType = Field(default=CollateralType.NONE)
    collateral_value: Optional[float] = Field(None, ge=0, description="Collateral value in TZS")
    collateral_description: Optional[str] = Field(None, max_length=500)
    
    # Guarantor information (for group loans or high amounts)
    guarantor_name: Optional[str] = Field(None, max_length=100)
    guarantor_phone: Optional[str] = Field(None, pattern=r"^\+255[67]\d{8}$")
    guarantor_nida: Optional[str] = Field(None, min_length=20, max_length=20)
    
    # Business loan specific fields
    business_name: Optional[str] = Field(None, max_length=200)
    business_registration: Optional[str] = Field(None, max_length=50)
    monthly_business_income: Optional[float] = Field(None, ge=0)
    years_in_business: Optional[int] = Field(None, ge=0, le=50)
    
    # Emergency loan fields
    emergency_type: Optional[str] = Field(None, max_length=100)
    emergency_urgency: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    
    @validator('loan_amount')
    def validate_loan_amount(cls, v, values):
        """Validate loan amount based on type"""
        loan_type = values.get('loan_type')
        if loan_type == LoanType.EMERGENCY and v > 2000000:  # 2M TZS max for emergency
            raise ValueError('Emergency loans cannot exceed 2,000,000 TZS')
        elif loan_type == LoanType.PERSONAL and v > 5000000:  # 5M TZS max for personal
            raise ValueError('Personal loans cannot exceed 5,000,000 TZS')
        return v
    
    @validator('collateral_value')
    def validate_collateral_value(cls, v, values):
        """Validate collateral value"""
        collateral_type = values.get('collateral_type')
        loan_amount = values.get('loan_amount', 0)
        
        if collateral_type != CollateralType.NONE and v:
            if v < loan_amount * 1.2:  # Collateral should be at least 120% of loan
                raise ValueError('Collateral value should be at least 120% of loan amount')
        return v

class LoanUpdate(BaseModel):
    """Loan update model"""
    loan_purpose: Optional[str] = Field(None, max_length=500)
    collateral_description: Optional[str] = Field(None, max_length=500)
    guarantor_name: Optional[str] = Field(None, max_length=100)
    guarantor_phone: Optional[str] = Field(None, pattern=r"^\+255[67]\d{8}$")
    notes: Optional[str] = Field(None, max_length=1000)

class LoanApproval(BaseModel):
    """Loan approval model"""
    approved_amount: float = Field(..., ge=50000, le=10000000)
    approved_tenure: int = Field(..., ge=1, le=60)
    interest_rate: float = Field(..., ge=5.0, le=30.0, description="Annual interest rate %")
    processing_fee: float = Field(default=2.5, ge=0, le=5.0, description="Processing fee %")
    insurance_required: bool = Field(default=True)
    insurance_rate: float = Field(default=1.0, ge=0, le=5.0, description="Insurance rate %")
    approval_notes: str = Field(..., min_length=10, max_length=1000)
    conditions: Optional[List[str]] = Field(default=[], description="Approval conditions")

class RepaymentCreate(BaseModel):
    """Repayment creation model"""
    loan_id: str = Field(..., description="Loan ID")
    amount: float = Field(..., ge=100, description="Repayment amount in TZS")
    payment_method: str = Field(..., pattern="^(mobile_money|bank_transfer|cash|cheque)$")
    payment_reference: str = Field(..., min_length=5, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

class LoanResponse:
    """Standard loan API response format"""
    
    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    @staticmethod
    def error(message: str, code: str = "LOAN_ERROR") -> Dict[str, Any]:
        return {
            "success": False,
            "message": message,
            "code": code,
            "timestamp": datetime.utcnow().isoformat(),
        }

async def verify_loan_token(
    authorization: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """Verify loan management authentication token"""
    try:
        token_data = security_manager.verify_jwt_token(authorization.credentials)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired loan management token",
            )
        return token_data
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Loan management authentication failed",
        )

async def get_current_user(
    token_data: Dict[str, Any] = Depends(verify_loan_token),
):
    """Get current user from token"""
    return token_data

# Loan Application Endpoints
@router.post("/applications", response_model=Dict[str, Any])
async def create_loan_application(
    loan_data: LoanApplicationCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create a new loan application
    
    This endpoint:
    - Validates customer eligibility
    - Performs risk assessment
    - Calculates loan terms
    - Creates loan application record
    """
    try:
        start_time = datetime.utcnow()
        
        # Generate loan application ID
        loan_id = str(uuid.uuid4())
        
        # Validate customer exists and is eligible
        # In real implementation: customer = await customer_service.get_by_id(loan_data.customer_id)
        customer_exists = True  # Mock
        
        if not customer_exists:
            return LoanResponse.error(
                message="Customer not found",
                code="CUSTOMER_NOT_FOUND"
            )
        
        # Check if customer has active loans
        # In real implementation: active_loans = await loan_service.get_active_loans(loan_data.customer_id)
        active_loans = []  # Mock
        
        # Business rules for multiple loans
        if len(active_loans) >= 2:
            return LoanResponse.error(
                message="Customer cannot have more than 2 active loans",
                code="MAX_LOANS_EXCEEDED"
            )
        
        # Perform risk assessment
        risk_assessor = RiskAssessment()
        risk_result = await risk_assessor.assess_loan_risk(
            customer_id=loan_data.customer_id,
            loan_amount=loan_data.loan_amount,
            loan_type=loan_data.loan_type.value
        )
        
        # Calculate loan terms
        calculator = LoanCalculator()
        loan_terms = calculator.calculate_loan_terms(
            principal=loan_data.loan_amount,
            tenure_months=loan_data.tenure_months,
            annual_rate=15.5,  # Default rate, will be adjusted based on risk
            frequency=loan_data.repayment_frequency.value
        )
        
        # Adjust interest rate based on risk
        base_rate = 15.5
        risk_adjustment = risk_result.get("risk_score", 500) / 100  # Convert to percentage
        final_rate = min(base_rate + risk_adjustment, 30.0)  # Cap at 30%
        
        # Recalculate with adjusted rate
        final_terms = calculator.calculate_loan_terms(
            principal=loan_data.loan_amount,
            tenure_months=loan_data.tenure_months,
            annual_rate=final_rate,
            frequency=loan_data.repayment_frequency.value
        )
        
        # Create loan application record
        loan_application = {
            "loan_id": loan_id,
            "customer_id": loan_data.customer_id,
            "loan_type": loan_data.loan_type.value,
            "loan_amount": loan_data.loan_amount,
            "loan_purpose": loan_data.loan_purpose,
            "tenure_months": loan_data.tenure_months,
            "repayment_frequency": loan_data.repayment_frequency.value,
            "collateral_type": loan_data.collateral_type.value,
            "collateral_value": loan_data.collateral_value,
            "collateral_description": loan_data.collateral_description,
            "guarantor_name": loan_data.guarantor_name,
            "guarantor_phone": loan_data.guarantor_phone,
            "guarantor_nida": loan_data.guarantor_nida,
            "business_name": loan_data.business_name,
            "business_registration": loan_data.business_registration,
            "monthly_business_income": loan_data.monthly_business_income,
            "years_in_business": loan_data.years_in_business,
            "emergency_type": loan_data.emergency_type,
            "emergency_urgency": loan_data.emergency_urgency,
            "status": LoanStatus.SUBMITTED.value,
            "risk_assessment": risk_result,
            "proposed_terms": final_terms,
            "proposed_interest_rate": final_rate,
            "created_at": start_time,
            "updated_at": start_time,
            "created_by": current_user.get("user_id"),
        }
        
        # In real implementation: Save to database
        # loan = await loan_service.create_application(loan_application)
        
        # Log loan application
        await audit_logger.log_event(
            user_id=current_user.get("user_id"),
            action="loan_application_created",
            resource_type="loan",
            resource_id=loan_id,
            details={
                "customer_id": loan_data.customer_id,
                "loan_amount": loan_data.loan_amount,
                "loan_type": loan_data.loan_type.value,
                "risk_score": risk_result.get("risk_score"),
            },
            ip_address=request.client.host,
        )
        
        return LoanResponse.success(
            data=loan_application,
            message="Loan application created successfully"
        )
        
    except Exception as e:
        await audit_logger.log_event(
            user_id=current_user.get("user_id"),
            action="loan_application_error",
            resource_type="loan",
            resource_id=loan_id,
            details={"error": str(e)},
            ip_address=request.client.host,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Loan application creation failed: {str(e)}"
        )

@router.get("/applications", response_model=Dict[str, Any])
async def get_loan_applications(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    loan_type: Optional[str] = Query(None, description="Filter by loan type"),
    customer_id: Optional[str] = Query(None, description="Filter by customer"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get loan applications with filtering and pagination"""
    try:
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if loan_type:
            filters["loan_type"] = loan_type
        if customer_id:
            filters["customer_id"] = customer_id
        if date_from:
            filters["date_from"] = date_from
        if date_to:
            filters["date_to"] = date_to
        
        # In real implementation: Query database
        # loans, total = await loan_service.get_applications(offset, per_page, filters)
        
        # Mock loan applications
        mock_loans = []
        for i in range(min(per_page, 10)):
            loan = {
                "loan_id": str(uuid.uuid4()),
                "customer_id": str(uuid.uuid4()),
                "customer_name": f"Customer {i+1}",
                "loan_type": ["personal", "business", "emergency"][i % 3],
                "loan_amount": 500000 + (i * 250000),
                "loan_purpose": f"Loan purpose {i+1}",
                "tenure_months": 6 + (i * 3),
                "status": ["submitted", "under_review", "approved", "rejected"][i % 4],
                "proposed_interest_rate": 15.5 + (i * 0.5),
                "risk_score": 500 + (i * 50),
                "created_at": datetime.utcnow() - timedelta(days=i),
                "updated_at": datetime.utcnow() - timedelta(days=i),
            }
            mock_loans.append(loan)
        
        total = 150  # Mock total
        total_pages = (total + per_page - 1) // per_page
        
        # Calculate summary statistics
        summary = {
            "total_applications": total,
            "pending_review": 45,
            "approved": 78,
            "rejected": 27,
            "total_amount_requested": 156750000,  # TZS
            "average_loan_amount": 1045000,  # TZS
        }
        
        response_data = {
            "loans": mock_loans,
            "summary": summary,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            },
            "filters_applied": filters,
        }
        
        return LoanResponse.success(
            data=response_data,
            message="Loan applications retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve loan applications: {str(e)}"
        )

@router.get("/applications/{loan_id}", response_model=Dict[str, Any])
async def get_loan_application(
    loan_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get specific loan application with full details"""
    try:
        # Validate loan ID format
        try:
            uuid.UUID(loan_id)
        except ValueError:
            return LoanResponse.error(
                message="Invalid loan ID format",
                code="INVALID_LOAN_ID"
            )
        
        # In real implementation: Query database
        # loan = await loan_service.get_by_id(loan_id)
        
        # Mock loan application
        loan = {
            "loan_id": loan_id,
            "customer_id": str(uuid.uuid4()),
            "customer_details": {
                "name": "John Mwalimu Doe",
                "phone": "+255677000001",
                "nida": "12345678901234567890",
                "monthly_income": 1500000,
                "employment_status": "Employed",
            },
            "loan_type": "business",
            "loan_amount": 2000000,
            "loan_purpose": "Expand textile business operations",
            "tenure_months": 18,
            "repayment_frequency": "monthly",
            "collateral_type": "equipment",
            "collateral_value": 2500000,
            "collateral_description": "Industrial sewing machines and equipment",
            "guarantor_name": "Jane Smith",
            "guarantor_phone": "+255677000002",
            "guarantor_nida": "09876543210987654321",
            "business_name": "Mwalimu Textiles Ltd",
            "business_registration": "REG-123456",
            "monthly_business_income": 800000,
            "years_in_business": 5,
            "status": "under_review",
            "risk_assessment": {
                "risk_score": 650,
                "risk_rating": "medium",
                "factors": {
                    "income_stability": "high",
                    "credit_history": "good",
                    "collateral_coverage": "adequate",
                    "business_performance": "strong",
                },
            },
            "proposed_terms": {
                "principal": 2000000,
                "interest_rate": 16.5,
                "tenure_months": 18,
                "monthly_installment": 135847,
                "total_interest": 445246,
                "total_repayment": 2445246,
                "processing_fee": 50000,
                "insurance_fee": 20000,
            },
            "application_documents": [
                {"type": "business_license", "status": "verified"},
                {"type": "financial_statements", "status": "pending"},
                {"type": "collateral_valuation", "status": "verified"},
                {"type": "guarantor_consent", "status": "verified"},
            ],
            "created_at": datetime.utcnow() - timedelta(days=5),
            "updated_at": datetime.utcnow() - timedelta(days=1),
            "review_notes": [
                {
                    "note": "Initial review completed - good business fundamentals",
                    "created_by": "loan_officer_1",
                    "created_at": datetime.utcnow() - timedelta(days=3),
                },
                {
                    "note": "Pending financial statements verification",
                    "created_by": "loan_officer_1",
                    "created_at": datetime.utcnow() - timedelta(days=1),
                },
            ],
        }
        
        if not loan:
            return LoanResponse.error(
                message="Loan application not found",
                code="LOAN_NOT_FOUND"
            )
        
        return LoanResponse.success(
            data=loan,
            message="Loan application retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve loan application: {str(e)}"
        )

@router.put("/applications/{loan_id}", response_model=Dict[str, Any])
async def update_loan_application(
    loan_id: str,
    loan_data: LoanUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update loan application (only allowed in draft/submitted status)"""
    try:
        # Validate loan ID
        try:
            uuid.UUID(loan_id)
        except ValueError:
            return LoanResponse.error(
                message="Invalid loan ID format",
                code="INVALID_LOAN_ID"
            )
        
        # In real implementation: Check loan exists and status
        # loan = await loan_service.get_by_id(loan_id)
        loan_status = "submitted"  # Mock
        
        # Check if loan can be updated
        updatable_statuses = [LoanStatus.DRAFT.value, LoanStatus.SUBMITTED.value]
        if loan_status not in updatable_statuses:
            return LoanResponse.error(
                message=f"Loan cannot be updated in {loan_status} status",
                code="LOAN_NOT_UPDATABLE"
            )
        
        # Prepare update data
        update_data = {}
        for field, value in loan_data.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        update_data["updated_at"] = datetime.utcnow()
        update_data["updated_by"] = current_user.get("user_id")
        
        # In real implementation: Update loan in database
        # updated_loan = await loan_service.update(loan_id, update_data)
        
        # Mock updated loan
        updated_loan = {
            "loan_id": loan_id,
            "status": "submitted",
            **update_data,
        }
        
        # Log update
        await audit_logger.log_event(
            user_id=current_user.get("user_id"),
            action="loan_application_updated",
            resource_type="loan",
            resource_id=loan_id,
            details={"updated_fields": list(update_data.keys())},
            ip_address=request.client.host,
        )
        
        return LoanResponse.success(
            data=updated_loan,
            message="Loan application updated successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update loan application: {str(e)}"
        )

@router.post("/applications/{loan_id}/approve", response_model=Dict[str, Any])
async def approve_loan_application(
    loan_id: str,
    approval_data: LoanApproval,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Approve loan application with final terms"""
    try:
        # Validate loan ID
        try:
            uuid.UUID(loan_id)
        except ValueError:
            return LoanResponse.error(
                message="Invalid loan ID format",
                code="INVALID_LOAN_ID"
            )
        
        # Check user permissions (loan officers and above)
        user_role = current_user.get("role", "")
        if user_role not in ["loan_officer", "branch_manager", "admin"]:
            return LoanResponse.error(
                message="Insufficient permissions to approve loans",
                code="INSUFFICIENT_PERMISSIONS"
            )
        
        # In real implementation: Get loan details
        # loan = await loan_service.get_by_id(loan_id)
        loan_status = "under_review"  # Mock
        
        if loan_status != LoanStatus.UNDER_REVIEW.value:
            return LoanResponse.error(
                message=f"Loan cannot be approved from {loan_status} status",
                code="INVALID_LOAN_STATUS"
            )
        
        # Calculate final loan terms
        calculator = LoanCalculator()
        final_terms = calculator.calculate_loan_terms(
            principal=approval_data.approved_amount,
            tenure_months=approval_data.approved_tenure,
            annual_rate=approval_data.interest_rate,
            processing_fee_rate=approval_data.processing_fee,
            insurance_rate=approval_data.insurance_rate if approval_data.insurance_required else 0
        )
        
        # Create loan approval record
        approval_record = {
            "loan_id": loan_id,
            "approved_amount": approval_data.approved_amount,
            "approved_tenure": approval_data.approved_tenure,
            "interest_rate": approval_data.interest_rate,
            "processing_fee": approval_data.processing_fee,
            "insurance_required": approval_data.insurance_required,
            "insurance_rate": approval_data.insurance_rate,
            "approval_notes": approval_data.approval_notes,
            "conditions": approval_data.conditions,
            "final_terms": final_terms,
            "status": LoanStatus.APPROVED.value,
            "approved_by": current_user.get("user_id"),
            "approved_at": datetime.utcnow(),
            "disbursement_pending": True,
        }
        
        # In real implementation: Update loan status and save approval
        # await loan_service.approve(loan_id, approval_record)
        
        # Log approval
        await audit_logger.log_event(
            user_id=current_user.get("user_id"),
            action="loan_approved",
            resource_type="loan",
            resource_id=loan_id,
            details={
                "approved_amount": approval_data.approved_amount,
                "interest_rate": approval_data.interest_rate,
                "tenure": approval_data.approved_tenure,
            },
            ip_address=request.client.host,
        )
        
        return LoanResponse.success(
            data=approval_record,
            message="Loan approved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Loan approval failed: {str(e)}"
        )

@router.post("/applications/{loan_id}/reject", response_model=Dict[str, Any])
async def reject_loan_application(
    loan_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    rejection_reason: str = Query(..., min_length=10, max_length=500, description="Reason for rejection"),
):
    """Reject loan application"""
    try:
        # Validate loan ID
        try:
            uuid.UUID(loan_id)
        except ValueError:
            return LoanResponse.error(
                message="Invalid loan ID format",
                code="INVALID_LOAN_ID"
            )
        
        # Check user permissions
        user_role = current_user.get("role", "")
        if user_role not in ["loan_officer", "branch_manager", "admin"]:
            return LoanResponse.error(
                message="Insufficient permissions to reject loans",
                code="INSUFFICIENT_PERMISSIONS"
            )
        
        # Create rejection record
        rejection_record = {
            "loan_id": loan_id,
            "status": LoanStatus.REJECTED.value,
            "rejection_reason": rejection_reason,
            "rejected_by": current_user.get("user_id"),
            "rejected_at": datetime.utcnow(),
        }
        
        # In real implementation: Update loan status
        # await loan_service.reject(loan_id, rejection_record)
        
        # Log rejection
        await audit_logger.log_event(
            user_id=current_user.get("user_id"),
            action="loan_rejected",
            resource_type="loan",
            resource_id=loan_id,
            details={"rejection_reason": rejection_reason},
            ip_address=request.client.host,
        )
        
        return LoanResponse.success(
            data=rejection_record,
            message="Loan rejected successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Loan rejection failed: {str(e)}"
        )

@router.post("/applications/{loan_id}/disburse", response_model=Dict[str, Any])
async def disburse_loan(
    loan_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    disbursement_method: str = Query(..., pattern="^(mobile_money|bank_transfer|cash)$", description="Disbursement method"),
    mobile_money_provider: Optional[str] = Query(None, pattern="^(mpesa|airtel)$", description="Mobile money provider"),
    bank_account: Optional[str] = Query(None, description="Bank account for transfer"),
):
    """Disburse approved loan to customer"""
    try:
        # Validate loan ID
        try:
            uuid.UUID(loan_id)
        except ValueError:
            return LoanResponse.error(
                message="Invalid loan ID format",
                code="INVALID_LOAN_ID"
            )
        
        # Check user permissions
        user_role = current_user.get("role", "")
        if user_role not in ["disbursement_officer", "branch_manager", "admin"]:
            return LoanResponse.error(
                message="Insufficient permissions to disburse loans",
                code="INSUFFICIENT_PERMISSIONS"
            )
        
        # In real implementation: Get loan details
        # loan = await loan_service.get_by_id(loan_id)
        loan_status = "approved"  # Mock
        
        if loan_status != LoanStatus.APPROVED.value:
            return LoanResponse.error(
                message=f"Loan cannot be disbursed from {loan_status} status",
                code="INVALID_LOAN_STATUS"
            )
        
        # Validate disbursement method requirements
        if disbursement_method == "mobile_money" and not mobile_money_provider:
            return LoanResponse.error(
                message="Mobile money provider required for mobile money disbursement",
                code="MISSING_PROVIDER"
            )
        
        if disbursement_method == "bank_transfer" and not bank_account:
            return LoanResponse.error(
                message="Bank account required for bank transfer disbursement",
                code="MISSING_BANK_ACCOUNT"
            )
        
        # Mock loan details for disbursement
        loan_details = {
            "customer_id": str(uuid.uuid4()),
            "customer_phone": "+255677000001",
            "approved_amount": 2000000,
            "processing_fee": 50000,
            "insurance_fee": 20000,
            "net_disbursement": 1930000,  # Amount - fees
        }
        
        # Process disbursement based on method
        disbursement_result = None
        
        if disbursement_method == "mobile_money":
            # Initialize mobile money service
            mobile_money = MobileMoneyService()
            
            if mobile_money_provider == "mpesa":
                disbursement_result = await mobile_money.disburse_mpesa(
                    phone_number=loan_details["customer_phone"],
                    amount=loan_details["net_disbursement"],
                    reference=f"LOAN_DISBURSE_{loan_id[:8]}"
                )
            elif mobile_money_provider == "airtel":
                disbursement_result = await mobile_money.disburse_airtel(
                    phone_number=loan_details["customer_phone"],
                    amount=loan_details["net_disbursement"],
                    reference=f"LOAN_DISBURSE_{loan_id[:8]}"
                )
        
        elif disbursement_method == "bank_transfer":
            # Mock bank transfer
            disbursement_result = {
                "transaction_id": f"BANK_{uuid.uuid4()}",
                "status": "pending",
                "amount": loan_details["net_disbursement"],
                "bank_account": bank_account,
                "reference": f"LOAN_DISBURSE_{loan_id[:8]}",
                "processing_time": "1-2 business days",
            }
        
        elif disbursement_method == "cash":
            # Mock cash disbursement
            disbursement_result = {
                "transaction_id": f"CASH_{uuid.uuid4()}",
                "status": "completed",
                "amount": loan_details["net_disbursement"],
                "disbursement_location": "Branch Office",
                "requires_signature": True,
            }
        
        # Create disbursement record
        disbursement_record = {
            "loan_id": loan_id,
            "disbursement_id": str(uuid.uuid4()),
            "gross_amount": loan_details["approved_amount"],
            "processing_fee": loan_details["processing_fee"],
            "insurance_fee": loan_details["insurance_fee"],
            "net_amount": loan_details["net_disbursement"],
            "disbursement_method": disbursement_method,
            "mobile_money_provider": mobile_money_provider,
            "bank_account": bank_account,
            "disbursement_result": disbursement_result,
            "status": LoanStatus.DISBURSED.value if disbursement_result.get("status") == "completed" else LoanStatus.APPROVED.value,
            "disbursed_by": current_user.get("user_id"),
            "disbursed_at": datetime.utcnow(),
            "loan_start_date": datetime.utcnow().date(),
        }
        
        # If disbursement successful, update loan status to active
        if disbursement_result.get("status") == "completed":
            disbursement_record["status"] = LoanStatus.ACTIVE.value
            
            # Generate repayment schedule
            calculator = LoanCalculator()
            repayment_schedule = calculator.generate_repayment_schedule(
                principal=loan_details["approved_amount"],
                annual_rate=16.5,  # Mock rate
                tenure_months=18,  # Mock tenure
                start_date=datetime.utcnow().date()
            )
            disbursement_record["repayment_schedule"] = repayment_schedule
        
        # In real implementation: Save disbursement and update loan
        # await loan_service.disburse(loan_id, disbursement_record)
        
        # Log disbursement
        await audit_logger.log_event(
            user_id=current_user.get("user_id"),
            action="loan_disbursed",
            resource_type="loan",
            resource_id=loan_id,
            details={
                "disbursement_method": disbursement_method,
                "net_amount": loan_details["net_disbursement"],
                "transaction_id": disbursement_result.get("transaction_id"),
            },
            ip_address=request.client.host,
        )
        
        return LoanResponse.success(
            data=disbursement_record,
            message="Loan disbursement initiated successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Loan disbursement failed: {str(e)}"
        )

# Loan Repayment Endpoints
@router.post("/repayments", response_model=Dict[str, Any])
async def record_repayment(
    repayment_data: RepaymentCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Record loan repayment"""
    try:
        # Validate loan exists and is active
        # In real implementation: loan = await loan_service.get_by_id(repayment_data.loan_id)
        loan_status = "active"  # Mock
        
        if loan_status not in [LoanStatus.ACTIVE.value, LoanStatus.DISBURSED.value]:
            return LoanResponse.error(
                message=f"Cannot record repayment for loan in {loan_status} status",
                code="INVALID_LOAN_STATUS"
            )
        
        # Generate repayment ID
        repayment_id = str(uuid.uuid4())
        
        # Mock loan details
        loan_details = {
            "customer_id": str(uuid.uuid4()),
            "outstanding_balance": 1800000,
            "monthly_installment": 135847,
            "last_payment_date": datetime.utcnow() - timedelta(days=30),
            "next_due_date": datetime.utcnow() + timedelta(days=5),
        }
        
        # Validate repayment amount
        if repayment_data.amount > loan_details["outstanding_balance"]:
            return LoanResponse.error(
                message="Repayment amount cannot exceed outstanding balance",
                code="AMOUNT_EXCEEDS_BALANCE"
            )
        
        # Calculate payment allocation
        calculator = LoanCalculator()
        payment_allocation = calculator.allocate_payment(
            payment_amount=repayment_data.amount,
            outstanding_principal=1500000,  # Mock
            accrued_interest=45000,  # Mock
            penalty_amount=0,  # Mock
            fees_due=0  # Mock
        )
        
        # Process payment based on method
        payment_verification = None
        
        if repayment_data.payment_method == "mobile_money":
            # Verify mobile money transaction
            mobile_money = MobileMoneyService()
            payment_verification = await mobile_money.verify_transaction(
                reference=repayment_data.payment_reference
            )
        else:
            # For other methods, mark as verified (would need manual verification)
            payment_verification = {
                "verified": True,
                "verification_method": "manual",
                "transaction_id": repayment_data.payment_reference,
            }
        
        # Create repayment record
        repayment_record = {
            "repayment_id": repayment_id,
            "loan_id": repayment_data.loan_id,
            "amount": repayment_data.amount,
            "payment_method": repayment_data.payment_method,
            "payment_reference": repayment_data.payment_reference,
            "payment_allocation": payment_allocation,
            "payment_verification": payment_verification,
            "notes": repayment_data.notes,
            "recorded_by": current_user.get("user_id"),
            "recorded_at": datetime.utcnow(),
            "status": "verified" if payment_verification.get("verified") else "pending",
        }
        
        # Update loan balance
        new_balance = loan_details["outstanding_balance"] - payment_allocation["principal_payment"]
        
        # Check if loan is fully paid
        if new_balance <= 0:
            repayment_record["loan_status_update"] = LoanStatus.COMPLETED.value
            repayment_record["loan_completion_date"] = datetime.utcnow()
        
        # In real implementation: Save repayment and update loan
        # await loan_service.record_repayment(repayment_record)
        
        # Log repayment
        await audit_logger.log_event(
            user_id=current_user.get("user_id"),
            action="loan_repayment_recorded",
            resource_type="loan_repayment",
            resource_id=repayment_id,
            details={
                "loan_id": repayment_data.loan_id,
                "amount": repayment_data.amount,
                "payment_method": repayment_data.payment_method,
            },
            ip_address=request.client.host,
        )
        
        return LoanResponse.success(
            data=repayment_record,
            message="Repayment recorded successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Repayment recording failed: {str(e)}"
        )

@router.get("/{loan_id}/repayments", response_model=Dict[str, Any])
async def get_loan_repayments(
    loan_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get loan repayment history"""
    try:
        # Validate loan ID
        try:
            uuid.UUID(loan_id)
        except ValueError:
            return LoanResponse.error(
                message="Invalid loan ID format",
                code="INVALID_LOAN_ID"
            )
        
        # In real implementation: Get repayments from database
        # repayments = await loan_service.get_repayments(loan_id)
        
        # Mock repayment history
        mock_repayments = []
        for i in range(8):  # 8 payments made
            repayment = {
                "repayment_id": str(uuid.uuid4()),
                "loan_id": loan_id,
                "amount": 135847,
                "payment_date": datetime.utcnow() - timedelta(days=30 * (8-i)),
                "payment_method": "mobile_money",
                "payment_reference": f"MP{datetime.utcnow().strftime('%Y%m%d')}{1000+i}",
                "principal_payment": 98500 + (i * 2000),
                "interest_payment": 37347 - (i * 2000),
                "status": "verified",
                "recorded_by": "system",
            }
            mock_repayments.append(repayment)
        
        # Calculate summary
        total_paid = sum(r["amount"] for r in mock_repayments)
        total_principal = sum(r["principal_payment"] for r in mock_repayments)
        total_interest = sum(r["interest_payment"] for r in mock_repayments)
        
        summary = {
            "total_repayments": len(mock_repayments),
            "total_amount_paid": total_paid,
            "total_principal_paid": total_principal,
            "total_interest_paid": total_interest,
            "outstanding_balance": 1200000,  # Mock remaining balance
            "next_due_date": datetime.utcnow() + timedelta(days=25),
            "next_due_amount": 135847,
            "payment_status": "current",  # current, overdue, defaulted
        }
        
        response_data = {
            "loan_id": loan_id,
            "repayments": mock_repayments,
            "summary": summary,
        }
        
        return LoanResponse.success(
            data=response_data,
            message="Loan repayments retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve loan repayments: {str(e)}"
        )

@router.get("/{loan_id}/schedule", response_model=Dict[str, Any])
async def get_repayment_schedule(
    loan_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get loan repayment schedule"""
    try:
        # Validate loan ID
        try:
            uuid.UUID(loan_id)
        except ValueError:
            return LoanResponse.error(
                message="Invalid loan ID format",
                code="INVALID_LOAN_ID"
            )
        
        # In real implementation: Get loan details and generate schedule
        # loan = await loan_service.get_by_id(loan_id)
        
        # Mock loan details
        loan_details = {
            "principal": 2000000,
            "interest_rate": 16.5,
            "tenure_months": 18,
            "start_date": datetime.utcnow() - timedelta(days=240),  # 8 months ago
            "monthly_installment": 135847,
        }
        
        # Generate repayment schedule
        calculator = LoanCalculator()
        schedule = calculator.generate_repayment_schedule(
            principal=loan_details["principal"],
            annual_rate=loan_details["interest_rate"],
            tenure_months=loan_details["tenure_months"],
            start_date=loan_details["start_date"].date()
        )
        
        # Mark payments as made for first 8 installments
        for i in range(8):
            if i < len(schedule):
                schedule[i]["status"] = "paid"
                schedule[i]["paid_date"] = loan_details["start_date"] + timedelta(days=30*i)
                schedule[i]["paid_amount"] = schedule[i]["installment_amount"]
        
        # Mark next installment as current
        if len(schedule) > 8:
            schedule[8]["status"] = "current"
            # Mark rest as pending
            for i in range(9, len(schedule)):
                schedule[i]["status"] = "pending"
        
        # Calculate schedule summary
        total_installments = len(schedule)
        paid_installments = len([s for s in schedule if s["status"] == "paid"])
        pending_installments = total_installments - paid_installments
        
        summary = {
            "total_installments": total_installments,
            "paid_installments": paid_installments,
            "pending_installments": pending_installments,
            "total_amount": sum(s["installment_amount"] for s in schedule),
            "paid_amount": sum(s.get("paid_amount", 0) for s in schedule if s["status"] == "paid"),
            "outstanding_amount": sum(s["installment_amount"] for s in schedule if s["status"] != "paid"),
            "next_due_date": schedule[8]["due_date"] if len(schedule) > 8 else None,
            "next_due_amount": schedule[8]["installment_amount"] if len(schedule) > 8 else 0,
        }
        
        response_data = {
            "loan_id": loan_id,
            "loan_details": loan_details,
            "schedule": schedule,
            "summary": summary,
        }
        
        return LoanResponse.success(
            data=response_data,
            message="Repayment schedule retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve repayment schedule: {str(e)}"
        )

# Loan Analytics and Reporting
@router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_loan_analytics_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get comprehensive loan analytics summary"""
    try:
        # In real implementation: Query analytics from database
        # analytics = await loan_service.get_analytics_summary()
        
        # Mock comprehensive analytics
        analytics_data = {
            "loan_portfolio": {
                "total_loans": 3456,
                "active_loans": 2134,
                "completed_loans": 1187,
                "defaulted_loans": 135,
                "total_portfolio_value": 4567890000,  # TZS
                "outstanding_balance": 2345678900,   # TZS
                "collection_rate": 94.8,  # Percentage
            },
            "loan_status_distribution": {
                "draft": 45,
                "submitted": 78,
                "under_review": 92,
                "approved": 156,
                "rejected": 234,
                "disbursed": 89,
                "active": 2134,
                "completed": 1187,
                "defaulted": 135,
                "written_off": 23,
            },
            "loan_type_distribution": {
                "personal": 1456,
                "business": 1234,
                "emergency": 456,
                "education": 234,
                "agriculture": 76,
                "group": 0,
            },
            "monthly_performance": {
                "applications_received": 245,
                "loans_approved": 189,
                "loans_disbursed": 167,
                "repayments_collected": 15678900,  # TZS
                "approval_rate": 77.1,  # Percentage
                "disbursement_rate": 88.4,  # Percentage
            },
            "risk_analytics": {
                "portfolio_at_risk_30": 5.2,  # Percentage
                "portfolio_at_risk_90": 2.8,  # Percentage
                "default_rate": 3.9,  # Percentage
                "average_risk_score": 645,
                "high_risk_loans": 267,
                "medium_risk_loans": 1890,
                "low_risk_loans": 1299,
            },
            "financial_metrics": {
                "average_loan_amount": 1320000,  # TZS
                "average_interest_rate": 16.8,  # Percentage
                "average_tenure_months": 14,
                "total_interest_earned": 567890000,  # TZS
                "processing_fees_collected": 45678900,  # TZS
                "net_interest_margin": 12.4,  # Percentage
            },
            "geographical_distribution": {
                "Dar es Salaam": 1234,
                "Mwanza": 567,
                "Arusha": 456,
                "Dodoma": 345,
                "Mbeya": 234,
                "Other": 620,
            },
            "mobile_money_integration": {
                "mpesa_disbursements": 1890,
                "airtel_disbursements": 567,
                "mpesa_repayments": 2345,
                "airtel_repayments": 789,
                "mobile_money_success_rate": 97.8,  # Percentage
            },
            "compliance_metrics": {
                "kyc_completion_rate": 98.5,  # Percentage
                "nida_verification_rate": 96.7,  # Percentage
                "tin_verification_rate": 78.9,  # Percentage
                "aml_screening_rate": 100.0,  # Percentage
            },
            "last_updated": datetime.utcnow(),
        }
        
        return LoanResponse.success(
            data=analytics_data,
            message="Loan analytics summary retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve loan analytics: {str(e)}"
        )

@router.get("/overdue", response_model=Dict[str, Any])
async def get_overdue_loans(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    days_overdue: Optional[int] = Query(None, ge=1, description="Filter by days overdue"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get overdue loans for collection management"""
    try:
        # Calculate offset
        offset = (page - 1) * per_page
        
        # In real implementation: Query overdue loans
        # overdue_loans = await loan_service.get_overdue_loans(offset, per_page, days_overdue)
        
        # Mock overdue loans
        mock_overdue = []
        for i in range(min(per_page, 15)):
            days_past_due = 5 + (i * 3)
            if days_overdue and days_past_due < days_overdue:
                continue
                
            loan = {
                "loan_id": str(uuid.uuid4()),
                "customer_id": str(uuid.uuid4()),
                "customer_name": f"Customer {i+1}",
                "customer_phone": f"+25567{7000000 + i}",
                "loan_amount": 500000 + (i * 100000),
                "outstanding_balance": 300000 + (i * 50000),
                "overdue_amount": 50000 + (i * 10000),
                "days_past_due": days_past_due,
                "last_payment_date": datetime.utcnow() - timedelta(days=days_past_due + 30),
                "next_action": "call_customer" if days_past_due < 15 else "field_visit",
                "collection_priority": "high" if days_past_due > 30 else "medium",
                "risk_category": "watch" if days_past_due < 30 else "substandard",
            }
            mock_overdue.append(loan)
        
        total = 89  # Mock total overdue loans
        total_pages = (total + per_page - 1) // per_page
        
        # Calculate overdue summary
        summary = {
            "total_overdue_loans": total,
            "total_overdue_amount": 4567890,  # TZS
            "average_days_overdue": 23,
            "collection_targets": {
                "0_30_days": 67,
                "31_60_days": 15,
                "61_90_days": 5,
                "over_90_days": 2,
            },
            "recovery_rate": 78.5,  # Percentage
        }
        
        response_data = {
            "overdue_loans": mock_overdue,
            "summary": summary,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            },
        }
        
        return LoanResponse.success(
            data=response_data,
            message="Overdue loans retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve overdue loans: {str(e)}"
        ) 