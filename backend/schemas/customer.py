"""
Pydantic schemas for customer data validation
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, validator, Field
from enum import Enum

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class CustomerStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"
    INACTIVE = "inactive"

class CustomerType(str, Enum):
    INDIVIDUAL = "individual"
    BUSINESS = "business"
    GROUP = "group"

class CustomerBase(BaseModel):
    """Base customer schema"""
    first_name: str = Field(..., min_length=2, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    date_of_birth: date
    gender: Gender
    phone_number: str = Field(..., pattern=r'^\+255\d{9}$')
    email: Optional[str] = None  # Temporarily using str instead of EmailStr
    region: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=100)
    ward: Optional[str] = Field(None, max_length=100)
    street: Optional[str] = Field(None, max_length=200)
    nida_number: Optional[str] = Field(None, pattern=r'^\d{20}$')
    
    @validator('date_of_birth')
    def validate_age(cls, v):
        """Validate customer is at least 18 years old"""
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError('Customer must be at least 18 years old')
        if age > 100:
            raise ValueError('Invalid date of birth')
        return v
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate Tanzania phone number format"""
        if not v.startswith('+255'):
            raise ValueError('Phone number must start with +255 for Tanzania')
        return v

class CustomerCreate(CustomerBase):
    """Customer creation schema"""
    customer_type: CustomerType = CustomerType.INDIVIDUAL
    occupation: Optional[str] = None
    monthly_income: Optional[float] = Field(None, gt=0)
    preferred_language: str = Field("sw", pattern=r'^(sw|en)$')
    
    # Emergency contact
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    
    # Business information (for business customers)
    business_name: Optional[str] = None
    business_registration_number: Optional[str] = None
    
    # Mobile money
    mpesa_number: Optional[str] = None
    airtel_money_number: Optional[str] = None

class CustomerUpdate(BaseModel):
    """Customer update schema"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[str] = None  # Temporarily using str instead of EmailStr
    region: Optional[str] = Field(None, min_length=2, max_length=100)
    district: Optional[str] = Field(None, min_length=2, max_length=100)
    ward: Optional[str] = Field(None, max_length=100)
    street: Optional[str] = Field(None, max_length=200)
    occupation: Optional[str] = None
    monthly_income: Optional[float] = Field(None, gt=0)
    
    # Emergency contact
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    
    # Mobile money
    mpesa_number: Optional[str] = None
    airtel_money_number: Optional[str] = None

class CustomerResponse(BaseModel):
    """Customer response schema"""
    id: str
    customer_number: str
    first_name: str
    middle_name: Optional[str]
    last_name: str
    full_name: str
    date_of_birth: date
    age: int
    gender: str
    phone_number: str
    email: Optional[str]
    region: str
    district: str
    ward: Optional[str]
    nida_number: Optional[str]
    nida_verified: bool
    customer_type: str
    customer_status: CustomerStatus
    kyc_completed: bool
    can_apply_loan: bool
    credit_score: Optional[int]
    risk_level: str
    preferred_language: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CustomerList(BaseModel):
    """Customer list response"""
    customers: List[CustomerResponse]
    total: int
    page: int
    per_page: int
    pages: int

class CustomerSearch(BaseModel):
    """Customer search parameters"""
    query: Optional[str] = None
    customer_status: Optional[CustomerStatus] = None
    customer_type: Optional[CustomerType] = None
    region: Optional[str] = None
    district: Optional[str] = None
    nida_verified: Optional[bool] = None
    kyc_completed: Optional[bool] = None
    min_age: Optional[int] = Field(None, ge=18, le=100)
    max_age: Optional[int] = Field(None, ge=18, le=100) 