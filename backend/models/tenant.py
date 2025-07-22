"""
Tenant Model for Tujenge Platform
SQLAlchemy model for multi-tenant architecture
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.core.database import Base

class Tenant(Base):
    """Tenant model for multi-tenancy support"""
    __tablename__ = "tenants"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Tenant basic information
    name = Column(String(255), nullable=False)
    code = Column(String(20), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Business information
    business_type = Column(String(100), nullable=True)  # MFI, Bank, SACCO, etc.
    license_number = Column(String(100), nullable=True)
    tax_identification_number = Column(String(50), nullable=True)
    
    # Contact information
    email = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Address information
    physical_address = Column(Text, nullable=True)
    postal_address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    country = Column(String(100), default="Tanzania", nullable=False)
    
    # Status and configuration
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    subscription_plan = Column(String(50), default="basic", nullable=False)
    
    # Settings and configuration
    settings = Column(JSON, nullable=True, default={})
    features_enabled = Column(JSON, nullable=True, default=[])
    
    # Financial limits and configurations
    max_users = Column(Integer, default=10, nullable=False)
    max_loans = Column(Integer, default=1000, nullable=False)
    max_loan_amount = Column(Numeric(15, 2), default=10000000.00)  # 10M TZS default
    
    # Integration settings
    mpesa_business_code = Column(String(20), nullable=True)
    airtel_business_code = Column(String(20), nullable=True)
    nida_integration_enabled = Column(Boolean, default=False)
    tin_integration_enabled = Column(Boolean, default=False)
    
    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#2563eb")  # Blue
    secondary_color = Column(String(7), default="#64748b")  # Gray
    
    # Audit fields
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    verified_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)
    
    # Subscription and billing
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)
    next_billing_date = Column(DateTime, nullable=True)
    
    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    users = relationship("User", back_populates="tenant")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', code='{self.code}', active={self.is_active})>"
    
    @property
    def is_subscription_active(self):
        """Check if subscription is active"""
        from datetime import datetime
        if not self.subscription_end:
            return True
        return self.subscription_end > datetime.utcnow()
    
    def to_dict(self):
        """Convert tenant to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "business_type": self.business_type,
            "email": self.email,
            "phone_number": self.phone_number,
            "city": self.city,
            "region": self.region,
            "country": self.country,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "subscription_plan": self.subscription_plan,
            "max_users": self.max_users,
            "max_loans": self.max_loans,
            "max_loan_amount": float(self.max_loan_amount) if self.max_loan_amount else None,
            "is_subscription_active": self.is_subscription_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def get_setting(self, key: str, default=None):
        """Get a specific setting value"""
        if self.settings and isinstance(self.settings, dict):
            return self.settings.get(key, default)
        return default
    
    def set_setting(self, key: str, value):
        """Set a specific setting value"""
        if not self.settings:
            self.settings = {}
        self.settings[key] = value
    
    def has_feature(self, feature: str) -> bool:
        """Check if tenant has a specific feature enabled"""
        if self.features_enabled and isinstance(self.features_enabled, list):
            return feature in self.features_enabled
        return False 