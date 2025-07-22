# backend/auth/jwt_service.py
"""
JWT Authentication Service for Tujenge Platform
Handles tenant-aware JWT tokens with role-based access control
"""
import jwt
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("⚠️ bcrypt not available - password hashing will use mock implementation")
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr
from fastapi import HTTPException, status
import secrets
import hashlib
from enum import Enum
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ redis not available - token storage will use in-memory cache")
import json
from backend.config import settings

class UserRole(str, Enum):
    """User roles for RBAC"""
    SUPER_ADMIN = "super_admin"      # Platform administrators
    TENANT_ADMIN = "tenant_admin"    # MFI administrators
    LOAN_OFFICER = "loan_officer"    # Loan processing staff
    CASHIER = "cashier"              # Payment processing staff
    CUSTOMER_SERVICE = "customer_service"  # Customer support
    AUDITOR = "auditor"              # Read-only access for auditing
    CUSTOMER = "customer"            # End customers (mobile app)

class TokenType(str, Enum):
    """Token types for different use cases"""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"

class JWTPayload(BaseModel):
    """JWT token payload structure"""
    user_id: int
    tenant_id: int
    email: str
    role: UserRole
    permissions: List[str]
    token_type: TokenType
    exp: int
    iat: int
    jti: str  # JWT ID for token revocation

class AuthTokens(BaseModel):
    """Authentication response tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    tenant_id: int
    user_id: int
    role: UserRole
    permissions: List[str]

class JWTService:
    """
    JWT Authentication Service with tenant isolation
    """
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        
        # Initialize Redis if available
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            except Exception as e:
                print(f"⚠️ Redis connection failed: {e}")
                self.redis_client = None
        else:
            self.redis_client = None
        
        # In-memory token storage for development
        self._token_store = {}
        
        # Role-based permissions mapping
        self.role_permissions = {
            UserRole.SUPER_ADMIN: [
                "tenant:create", "tenant:read", "tenant:update", "tenant:delete",
                "user:create", "user:read", "user:update", "user:delete",
                "system:admin", "audit:read", "*"  # Wildcard for all permissions
            ],
            UserRole.TENANT_ADMIN: [
                "tenant:read", "tenant:update",
                "user:create", "user:read", "user:update", "user:delete",
                "customer:create", "customer:read", "customer:update",
                "loan:create", "loan:read", "loan:update", "loan:approve",
                "transaction:read", "document:read", "report:read"
            ],
            UserRole.LOAN_OFFICER: [
                "customer:create", "customer:read", "customer:update",
                "loan:create", "loan:read", "loan:update",
                "document:create", "document:read", "document:update",
                "transaction:read"
            ],
            UserRole.CASHIER: [
                "customer:read", "loan:read",
                "transaction:create", "transaction:read", "transaction:update",
                "payment:create", "payment:read", "payment:update"
            ],
            UserRole.CUSTOMER_SERVICE: [
                "customer:read", "customer:update",
                "loan:read", "transaction:read",
                "document:read"
            ],
            UserRole.AUDITOR: [
                "customer:read", "loan:read", "transaction:read",
                "document:read", "report:read", "audit:read"
            ],
            UserRole.CUSTOMER: [
                "profile:read", "profile:update",
                "loan:read", "transaction:read",
                "document:read"
            ]
        }

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        if BCRYPT_AVAILABLE:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        else:
            # Mock implementation for development
            import hashlib
            return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            if BCRYPT_AVAILABLE:
                return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
            else:
                # Mock implementation for development
                import hashlib
                return hashlib.sha256(password.encode('utf-8')).hexdigest() == hashed_password
        except Exception:
            return False

    def generate_jti(self) -> str:
        """Generate unique JWT ID"""
        return secrets.token_urlsafe(32)

    def get_user_permissions(self, role: UserRole) -> List[str]:
        """Get permissions for user role"""
        return self.role_permissions.get(role, [])

    def create_access_token(
        self, 
        user_id: int, 
        tenant_id: int, 
        email: str, 
        role: UserRole,
        permissions: Optional[List[str]] = None
    ) -> str:
        """Create JWT access token"""
        if permissions is None:
            permissions = self.get_user_permissions(role)
            
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        jti = self.generate_jti()
        
        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "role": role.value,
            "permissions": permissions,
            "token_type": TokenType.ACCESS.value,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": jti
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Store token for revocation capability
        self._store_token(jti, token, expire)
        
        return token

    def create_refresh_token(
        self, 
        user_id: int, 
        tenant_id: int, 
        email: str, 
        role: UserRole
    ) -> str:
        """Create JWT refresh token"""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        jti = self.generate_jti()
        
        payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "role": role.value,
            "token_type": TokenType.REFRESH.value,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": jti
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Store refresh token
        self._store_token(jti, token, expire, token_type="refresh")
        
        return token

    def create_auth_tokens(
        self, 
        user_id: int, 
        tenant_id: int, 
        email: str, 
        role: UserRole
    ) -> AuthTokens:
        """Create both access and refresh tokens"""
        permissions = self.get_user_permissions(role)
        
        access_token = self.create_access_token(
            user_id, tenant_id, email, role, permissions
        )
        refresh_token = self.create_refresh_token(
            user_id, tenant_id, email, role
        )
        
        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60,
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            permissions=permissions
        )

    def decode_token(self, token: str) -> JWTPayload:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti and self._is_token_revoked(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )
            
            return JWTPayload(**payload)
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    def refresh_access_token(self, refresh_token: str) -> AuthTokens:
        """Create new access token from refresh token"""
        try:
            payload = self.decode_token(refresh_token)
            
            if payload.token_type != TokenType.REFRESH:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Create new access token
            role = UserRole(payload.role)
            return self.create_auth_tokens(
                payload.user_id,
                payload.tenant_id,
                payload.email,
                role
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

    def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding to blacklist"""
        try:
            payload = self.decode_token(token)
            jti = payload.jti
            
            # Add to blacklist
            if self.redis_client:
                try:
                    self.redis_client.setex(
                        f"revoked_token:{jti}",
                        timedelta(days=self.refresh_token_expire_days),
                        "revoked"
                    )
                except Exception:
                    # Fallback to in-memory storage
                    self._token_store[f"revoked_token:{jti}"] = "revoked"
            else:
                # Store in memory
                self._token_store[f"revoked_token:{jti}"] = "revoked"
            
            return True
            
        except Exception:
            return False

    def revoke_all_user_tokens(self, user_id: int, tenant_id: int) -> bool:
        """Revoke all tokens for a user"""
        try:
            # Pattern to find all user tokens
            pattern = f"token:{user_id}:{tenant_id}:*"
            tokens = self.redis_client.keys(pattern)
            
            for token_key in tokens:
                token_data = self.redis_client.get(token_key)
                if token_data:
                    token_info = json.loads(token_data)
                    jti = token_info.get("jti")
                    if jti:
                        self.redis_client.setex(
                            f"revoked_token:{jti}",
                            timedelta(days=self.refresh_token_expire_days),
                            "revoked"
                        )
            
            return True
            
        except Exception:
            return False

    def _store_token(
        self, 
        jti: str, 
        token: str, 
        expire: datetime, 
        token_type: str = "access"
    ):
        """Store token metadata"""
        token_data = {
            "jti": jti,
            "token": token,
            "token_type": token_type,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expire.isoformat()
        }
        
        if self.redis_client:
            # Store with expiration in Redis
            try:
                self.redis_client.setex(
                    f"token:{jti}",
                    expire - datetime.utcnow(),
                    json.dumps(token_data)
                )
            except Exception:
                # Fallback to in-memory storage
                self._token_store[jti] = token_data
        else:
            # Store in memory
            self._token_store[jti] = token_data

    def _is_token_revoked(self, jti: str) -> bool:
        """Check if token is revoked"""
        if self.redis_client:
            try:
                return self.redis_client.exists(f"revoked_token:{jti}")
            except Exception:
                pass
        
        # Check in-memory revoked tokens
        return f"revoked_token:{jti}" in self._token_store

    def has_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """Check if user has required permission"""
        # Super admin has all permissions
        if "*" in user_permissions:
            return True
            
        # Check exact permission match
        if required_permission in user_permissions:
            return True
            
        # Check wildcard permissions (e.g., "customer:*" allows "customer:read")
        for permission in user_permissions:
            if permission.endswith("*"):
                prefix = permission[:-1]
                if required_permission.startswith(prefix):
                    return True
                    
        return False

    def create_password_reset_token(self, user_id: int, email: str) -> str:
        """Create password reset token"""
        now = datetime.utcnow()
        expire = now + timedelta(hours=1)  # 1 hour expiry for security
        jti = self.generate_jti()
        
        payload = {
            "user_id": user_id,
            "email": email,
            "token_type": TokenType.RESET_PASSWORD.value,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": jti
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Store in Redis with short expiry
        self._store_token_in_redis(jti, token, expire, "password_reset")
        
        return token

# Initialize JWT service
jwt_service = JWTService()