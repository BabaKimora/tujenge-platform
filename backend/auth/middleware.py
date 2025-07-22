# backend/auth/middleware.py
"""
Authentication and Authorization Middleware for Tujenge Platform
Provides tenant-aware request processing and security
"""
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import logging
from typing import Optional, List, Callable, Any
from functools import wraps
import asyncio
from backend.auth.jwt_service import jwt_service, JWTPayload, UserRole
from backend.auth.rate_limiter import rate_limiter
from backend.models.user import User
from backend.models.tenant import Tenant
from sqlalchemy.orm import Session
from backend.core.database import get_db

logger = logging.getLogger(__name__)

class TenantContext:
    """Tenant context for request processing"""
    def __init__(self):
        self.user_id: Optional[int] = None
        self.tenant_id: Optional[int] = None
        self.email: Optional[str] = None
        self.role: Optional[UserRole] = None
        self.permissions: List[str] = []
        self.is_authenticated: bool = False
        self.tenant_name: Optional[str] = None
        self.tenant_settings: dict = {}

# Global request context
tenant_context = TenantContext()

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that processes JWT tokens
    and sets up tenant context for requests
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.public_paths = {
            "/docs", "/redoc", "/openapi.json", 
            "/api/auth/login", "/api/auth/register",
            "/api/auth/refresh", "/api/auth/reset-password",
            "/api/health", "/api/status"
        }
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Reset context for new request
        global tenant_context
        tenant_context = TenantContext()
        
        # Skip authentication for public paths
        if any(request.url.path.startswith(path) for path in self.public_paths):
            response = await call_next(request)
            self._add_security_headers(response)
            return response
        
        try:
            # Extract and validate JWT token
            token = self._extract_token(request)
            if token:
                payload = jwt_service.decode_token(token)
                await self._set_tenant_context(request, payload)
            
            # Rate limiting based on tenant/user
            if not await self._check_rate_limit(request):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"}
                )
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            # Log request
            self._log_request(request, response, start_time)
            
            return response
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            logger.error(f"Authentication middleware error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers"""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.split(" ")[1]
        return None
    
    async def _set_tenant_context(self, request: Request, payload: JWTPayload):
        """Set tenant context from JWT payload"""
        global tenant_context
        
        tenant_context.user_id = payload.user_id
        tenant_context.tenant_id = payload.tenant_id
        tenant_context.email = payload.email
        tenant_context.role = UserRole(payload.role)
        tenant_context.permissions = payload.permissions
        tenant_context.is_authenticated = True
        
        # Store context in request state for easy access
        request.state.tenant_context = tenant_context
        
        # Load tenant settings (you might want to cache this)
        # This would come from your database
        # tenant_context.tenant_settings = await self._load_tenant_settings(payload.tenant_id)
    
    async def _check_rate_limit(self, request: Request) -> bool:
        """Check rate limits for the request"""
        identifier = "anonymous"
        
        if tenant_context.is_authenticated:
            identifier = f"user:{tenant_context.user_id}:tenant:{tenant_context.tenant_id}"
        else:
            # Use IP for unauthenticated requests
            identifier = f"ip:{request.client.host}"
        
        return await rate_limiter.check_rate_limit(
            key=identifier,
            max_requests=100,  # Configurable per tenant/role
            window_seconds=3600
        )
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    def _log_request(self, request: Request, response, start_time: float):
        """Log request for audit purposes"""
        duration = time.time() - start_time
        
        log_data = {
            "timestamp": time.time(),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration": duration,
            "user_id": tenant_context.user_id,
            "tenant_id": tenant_context.tenant_id,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("User-Agent", "")
        }
        
        logger.info(f"Request processed: {log_data}")

# Security scheme for FastAPI docs
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> JWTPayload:
    """
    Dependency to get current authenticated user
    """
    try:
        payload = jwt_service.decode_token(credentials.credentials)
        
        # Verify user still exists and is active
        user = db.query(User).filter(
            User.id == payload.user_id,
            User.tenant_id == payload.tenant_id,
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return payload
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def get_current_active_user(
    current_user: JWTPayload = Depends(get_current_user)
) -> JWTPayload:
    """
    Dependency to get current active user
    """
    return current_user

def require_permissions(required_permissions: List[str]):
    """
    Decorator to require specific permissions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                # Try to get from global context
                if not tenant_context.is_authenticated:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                user_permissions = tenant_context.permissions
            else:
                user_permissions = current_user.permissions
            
            # Check if user has required permissions
            for permission in required_permissions:
                if not jwt_service.has_permission(user_permissions, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission} required"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(required_roles: List[UserRole]):
    """
    Decorator to require specific roles
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                if not tenant_context.is_authenticated:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                user_role = tenant_context.role
            else:
                user_role = UserRole(current_user.role)
            
            if user_role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role {user_role} not authorized"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def tenant_isolation(func: Callable) -> Callable:
    """
    Decorator to ensure tenant isolation in database queries
    This should be used on all database operations
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Ensure tenant context is available
        if not tenant_context.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for tenant operations"
            )
        
        # Add tenant_id to kwargs if not present
        if 'tenant_id' not in kwargs:
            kwargs['tenant_id'] = tenant_context.tenant_id
        
        # Verify tenant_id matches current user's tenant
        if kwargs.get('tenant_id') != tenant_context.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-tenant operation not allowed"
            )
        
        return await func(*args, **kwargs)
    return wrapper

# Helper functions for common use cases
def get_current_tenant_id() -> int:
    """Get current tenant ID from context"""
    if not tenant_context.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return tenant_context.tenant_id

def get_current_user_id() -> int:
    """Get current user ID from context"""
    if not tenant_context.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return tenant_context.user_id

def get_current_user_role() -> UserRole:
    """Get current user role from context"""
    if not tenant_context.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return tenant_context.role

# Context manager for testing
class MockTenantContext:
    """Mock tenant context for testing"""
    def __init__(self, user_id: int, tenant_id: int, role: UserRole):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.permissions = jwt_service.get_user_permissions(role)
    
    def __enter__(self):
        global tenant_context
        self.original_context = tenant_context
        tenant_context.user_id = self.user_id
        tenant_context.tenant_id = self.tenant_id
        tenant_context.role = self.role
        tenant_context.permissions = self.permissions
        tenant_context.is_authenticated = True
        return tenant_context
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        global tenant_context
        tenant_context = self.original_context