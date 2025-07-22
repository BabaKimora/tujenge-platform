"""
Customer model with Tanzania-specific fields and NIDA integration
"""

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional
from sqlalchemy import Column, String, Date, Boolean, Integer, Text, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB

# Import Base from the correct location
from backend.core.database import Base

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class CustomerStatus(str, Enum):
    PENDING = "pending"           # Newly registered
    VERIFIED = "verified"         # NIDA verified
    ACTIVE = "active"            # Active customer
    SUSPENDED = "suspended"       # Temporarily suspended
    BLOCKED = "blocked"          # Permanently blocked
    INACTIVE = "inactive"        # Self-deactivated

class CustomerType(str, Enum):
    INDIVIDUAL = "individual"    # Individual customer
    BUSINESS = "business"        # Business customer
    GROUP = "group"             # Group/cooperative

class Customer(Base):
    """Customer model for Tanzania microfinance"""
    __tablename__ = "customers"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Customer identification
    customer_number = Column(String(20), unique=True, nullable=False, index=True)
    
    # Basic information
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)  # Using String instead of Enum for now
    
    # Contact information
    phone_number = Column(String(20), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    
    # Address information (Tanzania-specific)
    region = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    ward = Column(String(100), nullable=True)
    street = Column(String(200), nullable=True)
    postal_address = Column(String(200), nullable=True)
    
    # Tanzania identification
    nida_number = Column(String(20), nullable=True, unique=True, index=True)
    nida_verified = Column(Boolean, default=False, nullable=False)
    nida_verified_at = Column(DateTime, nullable=True)
    voter_id = Column(String(20), nullable=True)
    tin_number = Column(String(20), nullable=True)
    tin_verified = Column(Boolean, default=False, nullable=False)
    
    # Business information (for business customers)
    business_name = Column(String(200), nullable=True)
    business_registration_number = Column(String(50), nullable=True)
    business_license_number = Column(String(50), nullable=True)
    
    # Customer classification
    customer_type = Column(String(20), default="individual", nullable=False)
    customer_status = Column(String(20), default="pending", nullable=False)
    
    # Financial information
    monthly_income = Column(Numeric(15, 2), nullable=True)
    occupation = Column(String(100), nullable=True)
    employer_name = Column(String(200), nullable=True)
    
    # Banking information
    has_bank_account = Column(Boolean, default=False, nullable=False)
    bank_name = Column(String(100), nullable=True)
    bank_account_number = Column(String(50), nullable=True)
    
    # Mobile money
    mpesa_number = Column(String(20), nullable=True)
    airtel_money_number = Column(String(20), nullable=True)
    
    # Risk and credit
    credit_score = Column(Integer, nullable=True)
    risk_level = Column(String(20), default="medium", nullable=False)
    
    # Emergency contact
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relationship = Column(String(50), nullable=True)
    
    # Preferences
    preferred_language = Column(String(10), default="sw", nullable=False)
    sms_notifications = Column(Boolean, default=True, nullable=False)
    email_notifications = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    registration_source = Column(String(50), default="web", nullable=False)
    kyc_completed = Column(Boolean, default=False, nullable=False)
    kyc_completed_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    
    # Additional data
    additional_data = Column(JSONB, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<Customer {self.customer_number}: {self.first_name} {self.last_name}>"
    
    @property
    def full_name(self) -> str:
        """Get customer's full name"""
        names = [self.first_name]
        if self.middle_name:
            names.append(self.middle_name)
        names.append(self.last_name)
        return " ".join(names)
    
    @property
    def age(self) -> int:
        """Calculate customer's age"""
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    @property
    def can_apply_loan(self) -> bool:
        """Check if customer can apply for a loan"""
        return (
            self.customer_status == "active" and
            self.nida_verified and
            self.kyc_completed and
            self.age >= 18
        ) 