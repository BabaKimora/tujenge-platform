"""
Customer Management Router for Tanzania Fintech Platform
Provides comprehensive customer lifecycle management with Tanzania-specific features
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from backend.utils.audit_logger import audit_logger
from backend.utils.security import security_manager
from backend.utils.tanzania_compliance import TanzaniaCompliance
from backend.utils.nida_validation import NIDAValidator
from backend.utils.tin_validation import TINValidator

router = APIRouter(tags=["Customer Management"])
security = HTTPBearer()
logger = logging.getLogger(__name__)

# Pydantic Models for Customer Management
class CustomerCreate(BaseModel):
    """Customer creation model with Tanzania-specific fields"""
    # Basic Information
    first_name: str = Field(..., min_length=2, max_length=50, description="Customer first name")
    middle_name: Optional[str] = Field(None, max_length=50, description="Customer middle name")
    last_name: str = Field(..., min_length=2, max_length=50, description="Customer last name")
    
    # Contact Information
    phone_number: str = Field(..., pattern=r"^\+255[67]\d{8}$", description="Tanzania phone number format")
    email: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    
    # Tanzania-specific fields
    nida_number: str = Field(..., min_length=20, max_length=20, description="NIDA identification number")
    tin_number: Optional[str] = Field(None, description="TIN tax identification number")
    
    # Address Information
    region: str = Field(..., description="Tanzania region")
    district: str = Field(..., description="Tanzania district")
    ward: str = Field(..., description="Tanzania ward")
    street_address: str = Field(..., description="Street address")
    postal_code: Optional[str] = Field(None, description="Postal code")
    
    # Personal Information
    date_of_birth: str = Field(..., description="Date of birth (YYYY-MM-DD)")
    gender: str = Field(..., pattern="^(Male|Female|Other)$", description="Gender")
    marital_status: str = Field(..., pattern="^(Single|Married|Divorced|Widowed)$", description="Marital status")
    
    # Financial Information
    monthly_income: Optional[float] = Field(None, ge=0, description="Monthly income in TZS")
    employment_status: str = Field(..., description="Employment status")
    employer_name: Optional[str] = Field(None, description="Employer name")
    
    # Additional Information
    education_level: Optional[str] = Field(None, description="Education level")
    preferred_language: str = Field(default="Swahili", description="Preferred language")
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """Validate Tanzania phone number format"""
        if not v.startswith('+255'):
            raise ValueError('Phone number must start with +255')
        if len(v) != 13:
            raise ValueError('Phone number must be 13 digits including +255')
        return v

class CustomerUpdate(BaseModel):
    """Customer update model"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=50)
    middle_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, min_length=2, max_length=50)
    phone_number: Optional[str] = Field(None, pattern=r"^\+255[67]\d{8}$")
    email: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    street_address: Optional[str] = Field(None)
    monthly_income: Optional[float] = Field(None, ge=0)
    employment_status: Optional[str] = Field(None)
    employer_name: Optional[str] = Field(None)
    education_level: Optional[str] = Field(None)
    preferred_language: Optional[str] = Field(None)

class CustomerResponseModel(BaseModel):
    """Customer response model"""
    customer_id: str
    first_name: str
    middle_name: Optional[str]
    last_name: str
    phone_number: str
    email: Optional[str]
    nida_number: str
    tin_number: Optional[str]
    region: str
    district: str
    ward: str
    street_address: str
    date_of_birth: str
    gender: str
    marital_status: str
    monthly_income: Optional[float]
    employment_status: str
    customer_status: str
    kyc_status: str
    risk_rating: str
    created_at: datetime
    updated_at: datetime
    
    # Tanzania-specific status
    nida_verified: bool
    tin_verified: bool
    mobile_money_registered: bool

class CustomerListResponse(BaseModel):
    """Customer list response model"""
    customers: List[CustomerResponseModel]
    total: int
    page: int
    per_page: int
    total_pages: int

class CustomerResponse:
    """Standard customer API response format"""
    
    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    @staticmethod
    def error(message: str, code: str = "CUSTOMER_ERROR") -> Dict[str, Any]:
        return {
            "success": False,
            "message": message,
            "code": code,
            "timestamp": datetime.utcnow().isoformat(),
        }

async def verify_customer_token(
    authorization: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """Verify customer management authentication token"""
    try:
        token_data = security_manager.verify_jwt_token(authorization.credentials)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired customer management token",
            )
        return token_data
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer management authentication failed",
        )

async def get_current_user(
    token_data: Dict[str, Any] = Depends(verify_customer_token),
):
    """Get current user from token"""
    return token_data

# Customer CRUD Operations
@router.post("/", response_model=Dict[str, Any])
async def create_customer(
    customer_data: CustomerCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create a new customer with Tanzania-specific validation
    
    This endpoint:
    - Validates NIDA number with government API
    - Validates TIN number if provided
    - Performs KYC checks
    - Creates customer profile
    - Sets up mobile money integration
    """
    try:
        start_time = datetime.utcnow()
        
        # Generate customer ID
        customer_id = str(uuid.uuid4())
        
        # Validate NIDA number
        nida_validator = NIDAValidator()
        nida_result = await nida_validator.validate_nida(customer_data.nida_number)
        
        if not nida_result["valid"]:
            await audit_logger.log_event(
                user_id=current_user.get("user_id"),
                action="customer_creation_failed",
                resource_type="customer",
                resource_id=customer_id,
                details={"reason": "NIDA validation failed", "nida": customer_data.nida_number},
                ip_address=request.client.host,
            )
            return CustomerResponse.error(
                message="NIDA validation failed. Please check the NIDA number.",
                code="NIDA_VALIDATION_FAILED"
            )
        
        # Validate TIN number if provided
        tin_verified = False
        if customer_data.tin_number:
            tin_validator = TINValidator()
            tin_result = await tin_validator.validate_tin(customer_data.tin_number)
            tin_verified = tin_result["valid"]
        
        # Check for duplicate NIDA
        # In real implementation, check database for existing NIDA
        existing_customer = None  # await customer_service.get_by_nida(customer_data.nida_number)
        if existing_customer:
            return CustomerResponse.error(
                message="Customer with this NIDA number already exists",
                code="DUPLICATE_NIDA"
            )
        
        # Create customer record
        customer_record = {
            "customer_id": customer_id,
            "first_name": customer_data.first_name,
            "middle_name": customer_data.middle_name,
            "last_name": customer_data.last_name,
            "phone_number": customer_data.phone_number,
            "email": customer_data.email,
            "nida_number": customer_data.nida_number,
            "tin_number": customer_data.tin_number,
            "region": customer_data.region,
            "district": customer_data.district,
            "ward": customer_data.ward,
            "street_address": customer_data.street_address,
            "postal_code": customer_data.postal_code,
            "date_of_birth": customer_data.date_of_birth,
            "gender": customer_data.gender,
            "marital_status": customer_data.marital_status,
            "monthly_income": customer_data.monthly_income,
            "employment_status": customer_data.employment_status,
            "employer_name": customer_data.employer_name,
            "education_level": customer_data.education_level,
            "preferred_language": customer_data.preferred_language,
            "customer_status": "active",
            "kyc_status": "verified" if nida_result["valid"] else "pending",
            "risk_rating": "medium",  # Default risk rating
            "nida_verified": nida_result["valid"],
            "tin_verified": tin_verified,
            "mobile_money_registered": False,
            "created_at": start_time,
            "updated_at": start_time,
            "created_by": current_user.get("user_id"),
        }
        
        # In real implementation: Save to database
        # customer = await customer_service.create(customer_record)
        
        # Set up mobile money integration (async process)
        # await mobile_money_service.setup_customer(customer_id, customer_data.phone_number)
        
        # Log successful creation
        await audit_logger.log_event(
            user_id=current_user.get("user_id"),
            action="customer_created",
            resource_type="customer",
            resource_id=customer_id,
            details={
                "customer_name": f"{customer_data.first_name} {customer_data.last_name}",
                "phone": customer_data.phone_number,
                "nida_verified": nida_result["valid"],
                "tin_verified": tin_verified,
            },
            ip_address=request.client.host,
        )
        
        return CustomerResponse.success(
            data=customer_record,
            message="Customer created successfully"
        )
        
    except Exception as e:
        await audit_logger.log_event(
            user_id=current_user.get("user_id"),
            action="customer_creation_error",
            resource_type="customer",
            resource_id=customer_id,
            details={"error": str(e)},
            ip_address=request.client.host,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Customer creation failed: {str(e)}"
        )

@router.get("/", response_model=Dict[str, Any])
async def get_customers(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or phone"),
    region: Optional[str] = Query(None, description="Filter by region"),
    status: Optional[str] = Query(None, description="Filter by customer status"),
    kyc_status: Optional[str] = Query(None, description="Filter by KYC status"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get list of customers with filtering and pagination
    Supports Tanzania-specific filtering by region and KYC status
    """
    try:
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Build filter conditions
        filters = {}
        if search:
            filters["search"] = search
        if region:
            filters["region"] = region
        if status:
            filters["status"] = status
        if kyc_status:
            filters["kyc_status"] = kyc_status
        
        # In real implementation: Query database with filters
        # customers, total = await customer_service.get_customers(
        #     offset=offset,
        #     limit=per_page,
        #     filters=filters
        # )
        
        # Mock data for demonstration
        mock_customers = []
        for i in range(min(per_page, 5)):  # Return up to 5 mock customers
            customer = {
                "customer_id": str(uuid.uuid4()),
                "first_name": f"Customer{i+1}",
                "middle_name": "Middle",
                "last_name": f"LastName{i+1}",
                "phone_number": f"+25567{7000000 + i}",
                "email": f"customer{i+1}@example.com",
                "nida_number": f"1234567890123456789{i}",
                "tin_number": f"123-456-78{i}",
                "region": "Dar es Salaam",
                "district": "Kinondoni",
                "ward": "Mikocheni",
                "street_address": f"Street {i+1}",
                "date_of_birth": "1990-01-01",
                "gender": "Male" if i % 2 == 0 else "Female",
                "marital_status": "Single",
                "monthly_income": 1000000.0 + (i * 100000),
                "employment_status": "Employed",
                "customer_status": "active",
                "kyc_status": "verified",
                "risk_rating": "medium",
                "created_at": datetime.utcnow() - timedelta(days=i),
                "updated_at": datetime.utcnow() - timedelta(days=i),
                "nida_verified": True,
                "tin_verified": True,
                "mobile_money_registered": True,
            }
            mock_customers.append(customer)
        
        total = 100  # Mock total
        total_pages = (total + per_page - 1) // per_page
        
        response_data = {
            "customers": mock_customers,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "filters_applied": filters,
        }
        
        return CustomerResponse.success(
            data=response_data,
            message="Customers retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve customers: {str(e)}"
        )

@router.get("/{customer_id}", response_model=Dict[str, Any])
async def get_customer(
    customer_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get customer by ID with complete profile information"""
    try:
        # Validate customer ID format
        try:
            uuid.UUID(customer_id)
        except ValueError:
            return CustomerResponse.error(
                message="Invalid customer ID format",
                code="INVALID_CUSTOMER_ID"
            )
        
        # In real implementation: Query database
        # customer = await customer_service.get_by_id(customer_id)
        
        # Mock customer data
        customer = {
            "customer_id": customer_id,
            "first_name": "John",
            "middle_name": "Mwalimu",
            "last_name": "Doe",
            "phone_number": "+255677000001",
            "email": "john.doe@example.com",
            "nida_number": "12345678901234567890",
            "tin_number": "123-456-789",
            "region": "Dar es Salaam",
            "district": "Kinondoni",
            "ward": "Mikocheni",
            "street_address": "Mikocheni Street 123",
            "postal_code": "12345",
            "date_of_birth": "1990-01-01",
            "gender": "Male",
            "marital_status": "Married",
            "monthly_income": 1500000.0,
            "employment_status": "Employed",
            "employer_name": "Tujenge Company Ltd",
            "education_level": "University",
            "preferred_language": "Swahili",
            "customer_status": "active",
            "kyc_status": "verified",
            "risk_rating": "low",
            "created_at": datetime.utcnow() - timedelta(days=30),
            "updated_at": datetime.utcnow() - timedelta(days=1),
            "nida_verified": True,
            "tin_verified": True,
            "mobile_money_registered": True,
            "loan_history": {
                "total_loans": 3,
                "active_loans": 1,
                "total_borrowed": 5000000.0,
                "total_repaid": 4200000.0,
                "current_outstanding": 800000.0,
            },
            "mobile_money_accounts": [
                {"provider": "M-Pesa", "number": "+255677000001", "verified": True},
                {"provider": "Airtel Money", "number": "+255677000001", "verified": True},
            ],
        }
        
        if not customer:
            return CustomerResponse.error(
                message="Customer not found",
                code="CUSTOMER_NOT_FOUND"
            )
        
        return CustomerResponse.success(
            data=customer,
            message="Customer retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve customer: {str(e)}"
        )

# Tanzania-specific customer endpoints
@router.post("/{customer_id}/verify-nida", response_model=Dict[str, Any])
async def verify_customer_nida(
    customer_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Re-verify customer NIDA with government database"""
    try:
        # In real implementation: Get customer and verify NIDA
        nida_validator = NIDAValidator()
        # customer = await customer_service.get_by_id(customer_id)
        # result = await nida_validator.validate_nida(customer.nida_number)
        
        # Mock verification result
        result = {
            "valid": True,
            "verified_at": datetime.utcnow(),
            "verification_id": str(uuid.uuid4()),
        }
        
        # Log verification
        await audit_logger.log_event(
            user_id=current_user.get("user_id"),
            action="nida_reverified",
            resource_type="customer",
            resource_id=customer_id,
            details=result,
            ip_address=request.client.host,
        )
        
        return CustomerResponse.success(
            data=result,
            message="NIDA verification completed"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NIDA verification failed: {str(e)}"
        )

@router.get("/{customer_id}/loan-eligibility", response_model=Dict[str, Any])
async def check_loan_eligibility(
    customer_id: str,
    loan_amount: float = Query(..., ge=50000, le=10000000, description="Requested loan amount in TZS"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Check customer loan eligibility based on Tanzania microfinance criteria"""
    try:
        # In real implementation: Comprehensive eligibility check
        # eligibility = await loan_service.check_eligibility(customer_id, loan_amount)
        
        # Mock eligibility check
        eligibility_data = {
            "customer_id": customer_id,
            "requested_amount": loan_amount,
            "eligible": True,
            "approved_amount": min(loan_amount, 2000000),  # Max 2M TZS
            "eligibility_factors": {
                "kyc_complete": True,
                "nida_verified": True,
                "income_sufficient": True,
                "debt_to_income_ratio": 0.35,  # 35% - acceptable
                "credit_score": 650,
                "existing_loans": 0,
                "mobile_money_active": True,
                "employment_stable": True,
            },
            "loan_terms": {
                "max_amount": 2000000,
                "min_amount": 50000,
                "interest_rate": 15.5,  # Annual percentage
                "max_tenure_months": 24,
                "min_tenure_months": 3,
                "processing_fee": 2.5,  # Percentage
                "insurance_required": True,
            },
            "required_documents": [
                "Valid NIDA card",
                "Employment letter or business license",
                "3 months bank statements",
                "Salary slip or business income proof",
                "Guarantor information (if amount > 1M)",
            ],
            "conditions": [
                "Mobile money account must be active",
                "Monthly income must be at least 3x loan installment",
                "No adverse credit history",
                "Must complete financial literacy course (if first-time borrower)",
            ],
            "next_steps": [
                "Submit required documents",
                "Complete loan application form",
                "Attend loan interview",
                "Sign loan agreement",
                "Complete disbursement process",
            ],
            "assessment_date": datetime.utcnow(),
        }
        
        return CustomerResponse.success(
            data=eligibility_data,
            message="Loan eligibility assessment completed"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Loan eligibility check failed: {str(e)}"
        )

@router.get("/analytics/summary", response_model=Dict[str, Any])
async def get_customer_analytics_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get customer analytics summary for Tanzania market"""
    try:
        # In real implementation: Query analytics from database
        # analytics = await analytics_service.get_customer_summary()
        
        # Mock analytics data
        analytics_data = {
            "total_customers": 2847,
            "active_customers": 2301,
            "inactive_customers": 546,
            "new_customers_this_month": 156,
            "customer_growth_rate": 12.3,  # Percentage
            "geographical_distribution": {
                "Dar es Salaam": 1245,
                "Mwanza": 324,
                "Arusha": 298,
                "Dodoma": 187,
                "Mbeya": 156,
                "Other": 637,
            },
            "age_distribution": {
                "18-25": 487,
                "26-35": 1156,
                "36-45": 789,
                "46-55": 298,
                "55+": 117,
            },
            "gender_distribution": {
                "Male": 1523,
                "Female": 1298,
                "Other": 26,
            },
            "kyc_status": {
                "verified": 2689,
                "pending": 128,
                "rejected": 30,
            },
            "mobile_money_adoption": {
                "mpesa_users": 2156,
                "airtel_users": 1387,
                "both_providers": 986,
                "no_mobile_money": 145,
            },
            "average_monthly_income": 1250000,  # TZS
            "last_updated": datetime.utcnow(),
        }
        
        return CustomerResponse.success(
            data=analytics_data,
            message="Customer analytics summary retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve customer analytics: {str(e)}"
        )


@router.get("/test/validators", response_model=Dict[str, Any])
async def test_validators() -> Dict[str, Any]:
    """
    Test endpoint to verify NIDA and TIN validators are working
    Public endpoint for testing enhanced validation utilities
    """
    try:
        # Initialize validator instances
        nida = NIDAValidator()
        tin = TINValidator()
        
        # Test NIDA validator format check
        nida_test = nida._validate_format("12345678901234567890")
        
        # Test TIN validator format check  
        tin_test = tin._validate_format("123-456-789")
        
        # Test Redis manager (should work with fallback)
        from backend.utils.redis_manager import redis_manager
        cache_stats = await redis_manager.get_stats()
        
        # Test Tanzania compliance framework
        from backend.utils.tanzania_compliance import tanzania_compliance
        test_customer_data = {
            "customer_id": "test_001",
            "nida_verified": True,
            "monthly_income": 800000,
            "phone_number": "+255712345678",
            "email": "test@example.com",
            "region": "Dar es Salaam",
            "district": "Kinondoni",
            "street_address": "123 Test Street",
            "employment_status": "Employed",
            "employer_name": "Test Company",
            "education_level": "University",
            "preferred_language": "Swahili"
        }
        
        compliance_result = await tanzania_compliance.check_customer_compliance(test_customer_data)
        
        return {
            "success": True,
            "validators": {
                "nida_validator": {
                    "loaded": True,
                    "format_validation": nida_test,
                    "cache_ttl": nida.cache_ttl
                },
                "tin_validator": {
                    "loaded": True,
                    "format_validation": tin_test,
                    "cache_ttl": tin.cache_ttl
                },
                "redis_manager": {
                    "loaded": True,
                    "stats": cache_stats
                },
                "tanzania_compliance": {
                    "loaded": True,
                    "overall_status": compliance_result.get("overall_status"),
                    "compliance_score": compliance_result.get("compliance_score"),
                    "kyc_status": compliance_result.get("compliance_details", {}).get("kyc", {}).get("status"),
                    "aml_status": compliance_result.get("compliance_details", {}).get("aml", {}).get("status"),
                    "customer_protection_status": compliance_result.get("compliance_details", {}).get("customer_protection", {}).get("status")
                }
            },
            "message": "Enhanced validators and compliance framework are operational",
            "tested_at": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Validator test error: {e}")
        return {
            "success": False,
            "error": str(e),
            "tested_at": datetime.utcnow()
        }