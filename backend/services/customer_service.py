"""
Customer service with business logic and Tanzania-specific features
"""

import random
import string
from datetime import datetime, date
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from backend.models.customer import Customer
from backend.schemas.customer import CustomerCreate, CustomerUpdate, CustomerSearch
from backend.services.nida_service import NidaService
from backend.utils.validators import validate_phone_number, validate_nida_number

class CustomerService:
    """Customer service with Tanzania-specific business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.nida_service = NidaService()
    
    async def generate_customer_number(self) -> str:
        """Generate unique customer number"""
        year = datetime.now().year
        
        # Get count of customers created this year
        result = await self.db.execute(
            select(func.count(Customer.id)).where(
                func.extract('year', Customer.created_at) == year
            )
        )
        count = result.scalar() or 0
        
        # Generate customer number: CUS-YYYY-NNNNNN
        customer_number = f"CUS-{year}-{count + 1:06d}"
        
        # Ensure uniqueness
        while await self.customer_number_exists(customer_number):
            count += 1
            customer_number = f"CUS-{year}-{count:06d}"
        
        return customer_number
    
    async def customer_number_exists(self, customer_number: str) -> bool:
        """Check if customer number already exists"""
        result = await self.db.execute(
            select(Customer.id).where(Customer.customer_number == customer_number)
        )
        return result.scalar() is not None
    
    async def phone_number_exists(self, phone_number: str, exclude_id: Optional[str] = None) -> bool:
        """Check if phone number already exists"""
        query = select(Customer.id).where(Customer.phone_number == phone_number)
        if exclude_id:
            query = query.where(Customer.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar() is not None
    
    async def nida_number_exists(self, nida_number: str, exclude_id: Optional[str] = None) -> bool:
        """Check if NIDA number already exists"""
        if not nida_number:
            return False
            
        query = select(Customer.id).where(Customer.nida_number == nida_number)
        if exclude_id:
            query = query.where(Customer.id != exclude_id)
        
        result = await self.db.execute(query)
        return result.scalar() is not None
    
    async def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """Create a new customer with validation"""
        
        # Validate phone number uniqueness
        if await self.phone_number_exists(customer_data.phone_number):
            raise ValueError("Phone number already exists")
        
        # Validate NIDA number uniqueness
        if customer_data.nida_number and await self.nida_number_exists(customer_data.nida_number):
            raise ValueError("NIDA number already exists")
        
        # Generate customer number
        customer_number = await self.generate_customer_number()
        
        # Create customer
        customer = Customer(
            customer_number=customer_number,
            first_name=customer_data.first_name,
            middle_name=customer_data.middle_name,
            last_name=customer_data.last_name,
            date_of_birth=customer_data.date_of_birth,
            gender=customer_data.gender.value,
            phone_number=customer_data.phone_number,
            email=customer_data.email,
            region=customer_data.region,
            district=customer_data.district,
            ward=customer_data.ward,
            street=customer_data.street,
            nida_number=customer_data.nida_number,
            customer_type=customer_data.customer_type.value,
            occupation=customer_data.occupation,
            monthly_income=customer_data.monthly_income,
            emergency_contact_name=customer_data.emergency_contact_name,
            emergency_contact_phone=customer_data.emergency_contact_phone,
            emergency_contact_relationship=customer_data.emergency_contact_relationship,
            business_name=customer_data.business_name,
            business_registration_number=customer_data.business_registration_number,
            mpesa_number=customer_data.mpesa_number,
            airtel_money_number=customer_data.airtel_money_number,
            preferred_language=customer_data.preferred_language,
            registration_source="api",
            created_at=datetime.utcnow()
        )
        
        self.db.add(customer)
        await self.db.commit()
        await self.db.refresh(customer)
        
        # Initiate NIDA verification if NIDA number provided
        if customer.nida_number:
            await self.initiate_nida_verification(customer.id)
        
        return customer
    
    async def get_customer_by_id(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID"""
        result = await self.db.execute(
            select(Customer).where(
                and_(Customer.id == customer_id, Customer.is_active == True)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_customer_by_number(self, customer_number: str) -> Optional[Customer]:
        """Get customer by customer number"""
        result = await self.db.execute(
            select(Customer).where(
                and_(Customer.customer_number == customer_number, Customer.is_active == True)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_customer_by_phone(self, phone_number: str) -> Optional[Customer]:
        """Get customer by phone number"""
        result = await self.db.execute(
            select(Customer).where(
                and_(Customer.phone_number == phone_number, Customer.is_active == True)
            )
        )
        return result.scalar_one_or_none()
    
    async def update_customer(self, customer_id: str, customer_data: CustomerUpdate) -> Optional[Customer]:
        """Update customer information"""
        customer = await self.get_customer_by_id(customer_id)
        if not customer:
            return None
        
        # Validate phone number uniqueness if being updated
        if customer_data.phone_number and customer_data.phone_number != customer.phone_number:
            if await self.phone_number_exists(customer_data.phone_number, exclude_id=customer_id):
                raise ValueError("Phone number already exists")
        
        # Update fields
        update_data = customer_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)
        
        customer.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(customer)
        
        return customer
    
    async def search_customers(
        self, 
        search_params: CustomerSearch, 
        page: int = 1, 
        per_page: int = 20
    ) -> Tuple[List[Customer], int]:
        """Search customers with filters and pagination"""
        
        query = select(Customer).where(Customer.is_active == True)
        
        # Apply filters
        if search_params.query:
            search_term = f"%{search_params.query}%"
            query = query.where(
                or_(
                    Customer.first_name.ilike(search_term),
                    Customer.last_name.ilike(search_term),
                    Customer.customer_number.ilike(search_term),
                    Customer.phone_number.ilike(search_term),
                    Customer.email.ilike(search_term)
                )
            )
        
        if search_params.customer_status:
            query = query.where(Customer.customer_status == search_params.customer_status.value)
        
        if search_params.customer_type:
            query = query.where(Customer.customer_type == search_params.customer_type.value)
        
        if search_params.region:
            query = query.where(Customer.region == search_params.region)
        
        if search_params.district:
            query = query.where(Customer.district == search_params.district)
        
        if search_params.nida_verified is not None:
            query = query.where(Customer.nida_verified == search_params.nida_verified)
        
        if search_params.kyc_completed is not None:
            query = query.where(Customer.kyc_completed == search_params.kyc_completed)
        
        # Age filters
        if search_params.min_age or search_params.max_age:
            today = date.today()
            
            if search_params.max_age:
                min_birth_date = date(today.year - search_params.max_age, today.month, today.day)
                query = query.where(Customer.date_of_birth >= min_birth_date)
            
            if search_params.min_age:
                max_birth_date = date(today.year - search_params.min_age, today.month, today.day)
                query = query.where(Customer.date_of_birth <= max_birth_date)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        query = query.order_by(Customer.created_at.desc())
        
        # Execute query
        result = await self.db.execute(query)
        customers = result.scalars().all()
        
        return customers, total
    
    async def initiate_nida_verification(self, customer_id: str) -> bool:
        """Initiate NIDA verification for customer"""
        customer = await self.get_customer_by_id(customer_id)
        if not customer or not customer.nida_number:
            return False
        
        try:
            # Call NIDA service to verify
            nida_data = await self.nida_service.verify_nida(customer.nida_number)
            
            if nida_data and nida_data.get('verified'):
                customer.nida_verified = True
                customer.nida_verified_at = datetime.utcnow()
                
                # Update customer status if this completes verification
                if customer.customer_status == "pending":
                    customer.customer_status = "verified"
                
                await self.db.commit()
                return True
        
        except Exception as e:
            # Log error but don't fail customer creation
            print(f"NIDA verification failed for customer {customer_id}: {str(e)}")
        
        return False
    
    async def complete_kyc(self, customer_id: str) -> bool:
        """Mark customer KYC as completed"""
        customer = await self.get_customer_by_id(customer_id)
        if not customer:
            return False
        
        customer.kyc_completed = True
        customer.kyc_completed_at = datetime.utcnow()
        
        # Update status to active if verified
        if customer.nida_verified and customer.customer_status == "verified":
            customer.customer_status = "active"
        
        await self.db.commit()
        return True
    
    async def deactivate_customer(self, customer_id: str, reason: str = None) -> bool:
        """Soft delete customer"""
        customer = await self.get_customer_by_id(customer_id)
        if not customer:
            return False
        
        customer.is_active = False
        customer.customer_status = "inactive"
        customer.updated_at = datetime.utcnow()
        
        # Store deactivation reason in additional_data
        if reason:
            additional_data = customer.additional_data or {}
            additional_data['deactivation_reason'] = reason
            additional_data['deactivated_at'] = datetime.utcnow().isoformat()
            customer.additional_data = additional_data
        
        await self.db.commit()
        return True 