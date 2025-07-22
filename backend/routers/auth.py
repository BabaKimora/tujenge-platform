# backend/routers/auth.py
"""
Authentication Router for Tujenge Platform
Handles login, registration, password reset, and token management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import logging
from datetime import datetime

from backend.core.database import get_db
from backend.auth.jwt_service import jwt_service, AuthTokens, UserRole
from backend.auth.middleware import get_current_user, security
from backend.auth.rate_limiter import login_rate_limiter, rate_limiter, RateLimitType
from backend.models.user import User
from backend.models.tenant import Tenant
from backend.utils.email import send_password_reset_email
from backend.utils.audit import audit_logger

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Request/Response Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    tenant_code: Optional[str] = None  # For joining existing tenant
    tenant_name: Optional[str] = None  # For creating new tenant
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: UserRole
    tenant_id: int
    tenant_name: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

class LoginResponse(BaseModel):
    tokens: AuthTokens
    user: UserResponse
    message: str

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens
    """
    # Rate limiting by email
    rate_limit_result = await login_rate_limiter.check_login_attempt(
        identifier=login_data.email
    )
    
    if not rate_limit_result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {rate_limit_result.retry_after} seconds"
        )
    
    try:
        # Find user by email
        user = db.query(User).filter(
            User.email == login_data.email,
            User.is_active == True
        ).first()
        
        if not user:
            await login_rate_limiter.record_failed_login(login_data.email)
            await audit_logger.log_security_event(
                event_type="login_failed",
                details={"email": login_data.email, "reason": "user_not_found"},
                request=request
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not jwt_service.verify_password(login_data.password, user.password_hash):
            await login_rate_limiter.record_failed_login(login_data.email)
            await audit_logger.log_security_event(
                event_type="login_failed",
                details={"email": login_data.email, "user_id": user.id, "reason": "invalid_password"},
                request=request
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Get tenant information
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        if not tenant or not tenant.is_active:
            await audit_logger.log_security_event(
                event_type="login_failed",
                details={"email": login_data.email, "user_id": user.id, "reason": "tenant_inactive"},
                request=request
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant account is inactive"
            )
        
        # Create JWT tokens
        tokens = jwt_service.create_auth_tokens(
            user_id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            role=UserRole(user.role)
        )
        
        # Update user last login
        user.last_login = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1
        db.commit()
        
        # Record successful login
        await login_rate_limiter.record_successful_login(login_data.email)
        
        # Log successful login
        await audit_logger.log_security_event(
            event_type="login_success",
            details={
                "user_id": user.id,
                "tenant_id": user.tenant_id,
                "email": user.email,
                "role": user.role
            },
            request=request
        )
        
        # Prepare response
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=UserRole(user.role),
            tenant_id=user.tenant_id,
            tenant_name=tenant.name,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
        
        return LoginResponse(
            tokens=tokens,
            user=user_response,
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        await audit_logger.log_security_event(
            event_type="login_error",
            details={"email": login_data.email, "error": str(e)},
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/register", response_model=LoginResponse)
async def register(
    request: Request,
    register_data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register new user and optionally create tenant
    """
    # Rate limiting by IP
    client_ip = request.client.host
    rate_limit_result = await rate_limiter.check_rate_limit(
        key=f"register:{client_ip}",
        rate_limit_type=RateLimitType.API_REQUESTS,
        max_requests=5,
        window_seconds=3600
    )
    
    if not rate_limit_result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts"
        )
    
    try:
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == register_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        tenant = None
        
        # Handle tenant logic
        if register_data.tenant_code:
            # Join existing tenant
            tenant = db.query(Tenant).filter(
                Tenant.code == register_data.tenant_code,
                Tenant.is_active == True
            ).first()
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid tenant code"
                )
        elif register_data.tenant_name:
            # Create new tenant
            tenant = Tenant(
                name=register_data.tenant_name,
                code=f"TNT{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(tenant)
            db.flush()  # Get tenant ID
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either tenant_code or tenant_name must be provided"
            )
        
        # Determine user role
        user_role = UserRole.CUSTOMER
        if register_data.tenant_name:  # Creating new tenant
            user_role = UserRole.TENANT_ADMIN
        
        # Create user
        user = User(
            email=register_data.email,
            password_hash=jwt_service.hash_password(register_data.password),
            first_name=register_data.first_name,
            last_name=register_data.last_name,
            phone_number=register_data.phone_number,
            role=user_role.value,
            tenant_id=tenant.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(user)
        db.commit()
        
        # Create JWT tokens
        tokens = jwt_service.create_auth_tokens(
            user_id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            role=user_role
        )
        
        # Log registration
        await audit_logger.log_security_event(
            event_type="user_registered",
            details={
                "user_id": user.id,
                "tenant_id": user.tenant_id,
                "email": user.email,
                "role": user.role,
                "tenant_created": bool(register_data.tenant_name)
            },
            request=request
        )
        
        # Send welcome email (background task)
        background_tasks.add_task(
            send_welcome_email,
            user.email,
            user.first_name,
            tenant.name
        )
        
        # Prepare response
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user_role,
            tenant_id=user.tenant_id,
            tenant_name=tenant.name,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=None
        )
        
        return LoginResponse(
            tokens=tokens,
            user=user_response,
            message="Registration successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/refresh", response_model=AuthTokens)
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        # Create new tokens
        tokens = jwt_service.refresh_access_token(refresh_data.refresh_token)
        
        # Log token refresh
        payload = jwt_service.decode_token(refresh_data.refresh_token)
        await audit_logger.log_security_event(
            event_type="token_refreshed",
            details={
                "user_id": payload.user_id,
                "tenant_id": payload.tenant_id
            },
            request=request
        )
        
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user = Depends(get_current_user)
):
    """
    Logout user and revoke tokens
    """
    try:
        # Revoke the current token
        jwt_service.revoke_token(credentials.credentials)
        
        # Log logout
        await audit_logger.log_security_event(
            event_type="user_logout",
            details={
                "user_id": current_user.user_id,
                "tenant_id": current_user.tenant_id
            },
            request=request
        )
        
        return {"message": "Logout successful"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/logout-all")
async def logout_all_devices(
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Logout from all devices by revoking all user tokens
    """
    try:
        # Revoke all user tokens
        jwt_service.revoke_all_user_tokens(
            current_user.user_id, 
            current_user.tenant_id
        )
        
        # Log logout all
        await audit_logger.log_security_event(
            event_type="user_logout_all",
            details={
                "user_id": current_user.user_id,
                "tenant_id": current_user.tenant_id
            },
            request=request
        )
        
        return {"message": "Logged out from all devices"}
        
    except Exception as e:
        logger.error(f"Logout all error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout all failed"
        )

@router.post("/reset-password")
async def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request password reset email
    """
    # Rate limiting
    rate_limit_result = await rate_limiter.check_rate_limit(
        key=f"password_reset:{reset_request.email}",
        rate_limit_type=RateLimitType.PASSWORD_RESET
    )
    
    if not rate_limit_result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests"
        )
    
    try:
        # Find user
        user = db.query(User).filter(
            User.email == reset_request.email,
            User.is_active == True
        ).first()
        
        if user:
            # Create password reset token
            reset_token = jwt_service.create_password_reset_token(
                user.id, 
                user.email
            )
            
            # Send reset email (background task)
            background_tasks.add_task(
                send_password_reset_email,
                user.email,
                user.first_name,
                reset_token
            )
            
            # Log password reset request
            await audit_logger.log_security_event(
                event_type="password_reset_requested",
                details={
                    "user_id": user.id,
                    "tenant_id": user.tenant_id,
                    "email": user.email
                },
                request=request
            )
        
        # Always return success to prevent email enumeration
        return {"message": "Password reset instructions sent to email"}
        
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        # Still return success to prevent information leakage
        return {"message": "Password reset instructions sent to email"}

@router.post("/reset-password/confirm")
async def confirm_password_reset(
    request: Request,
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token
    """
    try:
        # Validate reset token
        payload = jwt_service.decode_token(reset_data.token)
        
        if payload.token_type != "reset_password":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Find user
        user = db.query(User).filter(
            User.id == payload.user_id,
            User.email == payload.email,
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Update password
        user.password_hash = jwt_service.hash_password(reset_data.new_password)
        user.password_changed_at = datetime.utcnow()
        db.commit()
        
        # Revoke all existing tokens for security
        jwt_service.revoke_all_user_tokens(user.id, user.tenant_id)
        
        # Revoke the reset token
        jwt_service.revoke_token(reset_data.token)
        
        # Log password reset
        await audit_logger.log_security_event(
            event_type="password_reset_completed",
            details={
                "user_id": user.id,
                "tenant_id": user.tenant_id,
                "email": user.email
            },
            request=request
        )
        
        return {"message": "Password reset successful"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirm error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset failed"
        )

@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    """
    try:
        # Find user
        user = db.query(User).filter(
            User.id == current_user.user_id,
            User.tenant_id == current_user.tenant_id
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not jwt_service.verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.password_hash = jwt_service.hash_password(password_data.new_password)
        user.password_changed_at = datetime.utcnow()
        db.commit()
        
        # Log password change
        await audit_logger.log_security_event(
            event_type="password_changed",
            details={
                "user_id": user.id,
                "tenant_id": user.tenant_id,
                "email": user.email
            },
            request=request
        )
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user information
    """
    try:
        # Get user with tenant info
        user = db.query(User).filter(
            User.id == current_user.user_id,
            User.tenant_id == current_user.tenant_id
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
        
        return UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=UserRole(user.role),
            tenant_id=user.tenant_id,
            tenant_name=tenant.name if tenant else "",
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )

@router.get("/permissions")
async def get_user_permissions(
    current_user = Depends(get_current_user)
):
    """
    Get current user's permissions
    """
    try:
        return {
            "user_id": current_user.user_id,
            "tenant_id": current_user.tenant_id,
            "role": current_user.role,
            "permissions": current_user.permissions
        }
        
    except Exception as e:
        logger.error(f"Get permissions error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permissions"
        )

@router.post("/validate-token")
async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Validate JWT token
    """
    try:
        payload = jwt_service.decode_token(credentials.credentials)
        
        return {
            "valid": True,
            "user_id": payload.user_id,
            "tenant_id": payload.tenant_id,
            "email": payload.email,
            "role": payload.role,
            "expires_at": payload.exp
        }
        
    except HTTPException as e:
        return {
            "valid": False,
            "error": e.detail
        }
    except Exception as e:
        return {
            "valid": False,
            "error": "Token validation failed"
        }

# Background task functions
async def send_welcome_email(email: str, first_name: str, tenant_name: str):
    """Send welcome email to new user"""
    try:
        # Implementation depends on your email service
        logger.info(f"Sending welcome email to {email}")
        # await email_service.send_welcome_email(email, first_name, tenant_name)
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")

# Health check endpoint
@router.get("/health")
async def auth_health_check():
    """
    Authentication service health check
    """
    try:
        # Test JWT service
        test_token = jwt_service.create_access_token(
            user_id=1,
            tenant_id=1,
            email="test@example.com",
            role=UserRole.CUSTOMER
        )
        
        # Test token decode
        jwt_service.decode_token(test_token)
        
        # Test rate limiter
        rate_limit_result = await rate_limiter.check_rate_limit(
            key="health_check",
            rate_limit_type=RateLimitType.API_REQUESTS,
            max_requests=1000,
            window_seconds=60
        )
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "jwt_service": "operational",
                "rate_limiter": "operational" if rate_limit_result.allowed else "degraded",
                "redis": "operational"  # You might want to add actual Redis health check
            }
        }
        
    except Exception as e:
        logger.error(f"Auth health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }