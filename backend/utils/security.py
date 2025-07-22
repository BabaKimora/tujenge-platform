"""
Tujenge Platform - Security Manager
JWT authentication and security utilities for Tanzania fintech platform
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SecurityManager:
    """
    Security manager for authentication and authorization
    Handles JWT tokens, password hashing, and security validations
    """
    
    def __init__(self):
        # In production, these should come from environment variables
        self.secret_key = "tujenge-platform-secret-key-change-in-production"
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        
    async def initialize(self):
        """Initialize security manager"""
        # In production, load secrets from secure storage
        pass
    
    def hash_password(self, password: str) -> str:
        """Hash a password for storing in the database"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    def generate_api_key(self) -> str:
        """Generate a secure API key"""
        return secrets.token_urlsafe(32)
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def verify_api_key(self, api_key: str, stored_hash: str) -> bool:
        """Verify an API key against its stored hash"""
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return secrets.compare_digest(api_key_hash, stored_hash)
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate a numeric OTP for verification"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    def validate_tanzania_phone(self, phone: str) -> bool:
        """Validate Tanzania phone number format"""
        # Tanzania phone numbers: +255 followed by 9 digits
        if not phone.startswith("+255"):
            return False
        if len(phone) != 13:
            return False
        if not phone[4:].isdigit():
            return False
        return True
    
    def validate_nida_format(self, nida: str) -> bool:
        """Basic NIDA number format validation"""
        # NIDA numbers are 20 digits
        if len(nida) != 20:
            return False
        if not nida.isdigit():
            return False
        return True
    
    def sanitize_input(self, input_string: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        # Basic sanitization - in production, use more comprehensive methods
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`']
        for char in dangerous_chars:
            input_string = input_string.replace(char, '')
        return input_string.strip()
    
    def check_password_strength(self, password: str) -> Dict[str, Any]:
        """Check password strength and return requirements"""
        checks = {
            "length": len(password) >= 8,
            "uppercase": any(c.isupper() for c in password),
            "lowercase": any(c.islower() for c in password),
            "digit": any(c.isdigit() for c in password),
            "special": any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password),
        }
        
        score = sum(checks.values())
        
        return {
            "score": score,
            "max_score": 5,
            "strength": "weak" if score < 3 else "medium" if score < 5 else "strong",
            "requirements": {
                "At least 8 characters": checks["length"],
                "Uppercase letter": checks["uppercase"],
                "Lowercase letter": checks["lowercase"],
                "Number": checks["digit"],
                "Special character": checks["special"],
            }
        }

# Global security manager instance
security_manager = SecurityManager() 