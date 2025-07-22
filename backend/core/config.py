"""
Tujenge Platform - Enhanced Configuration
Complete configuration management for Tanzania fintech operations
"""

import os
import secrets
from functools import lru_cache
from typing import Dict, List, Optional, Any

from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """
    Complete Tujenge Platform Settings
    Enterprise-grade configuration for Tanzania fintech operations
    """
    
    # Application Information
    APP_NAME: str = "Tujenge Platform"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Tanzania Enterprise Fintech Solution - Microfinance Platform"
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Security Configuration
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        env="SECRET_KEY"
    )
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION: int = Field(default=3600, env="JWT_EXPIRATION")  # 1 hour
    BCRYPT_ROUNDS: int = Field(default=12, env="BCRYPT_ROUNDS")
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql://postgres:PasswordYangu@localhost:5432/tujenge_db",
        env="DATABASE_URL"
    )
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Database Pool Settings
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=30, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=3600, env="DB_POOL_RECYCLE")
    
    # Redis Configuration
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Cache Settings
    CACHE_TTL: int = Field(default=300, env="CACHE_TTL")
    SESSION_TTL: int = Field(default=3600, env="SESSION_TTL")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=1000, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=3600, env="RATE_LIMIT_WINDOW")
    
    # Tanzania Market Configuration
    COUNTRY: str = "Tanzania"
    COUNTRY_CODE: str = "TZ"
    CURRENCY: str = "TZS"
    TIMEZONE: str = "Africa/Dar_es_Salaam"
    LANGUAGE: str = "sw"
    
    # Mobile Money Configuration
    MPESA_CONSUMER_KEY: Optional[str] = Field(default=None, env="MPESA_CONSUMER_KEY")
    MPESA_CONSUMER_SECRET: Optional[str] = Field(default=None, env="MPESA_CONSUMER_SECRET")
    MPESA_PASSKEY: Optional[str] = Field(default=None, env="MPESA_PASSKEY")
    MPESA_SHORTCODE: Optional[str] = Field(default=None, env="MPESA_SHORTCODE")
    MPESA_ENVIRONMENT: str = Field(default="sandbox", env="MPESA_ENVIRONMENT")
    
    AIRTEL_API_KEY: Optional[str] = Field(default=None, env="AIRTEL_API_KEY")
    AIRTEL_SECRET_KEY: Optional[str] = Field(default=None, env="AIRTEL_SECRET_KEY")
    AIRTEL_ENVIRONMENT: str = Field(default="staging", env="AIRTEL_ENVIRONMENT")
    
    # Government APIs
    NIDA_API_URL: str = Field(
        default="https://ors.brela.go.tz/um/load/load_nida",
        env="NIDA_API_URL"
    )
    NIDA_API_KEY: Optional[str] = Field(default=None, env="NIDA_API_KEY")
    
    TIN_API_URL: str = Field(default="https://api.tra.go.tz", env="TIN_API_URL")
    TIN_API_KEY: Optional[str] = Field(default=None, env="TIN_API_KEY")
    
    # Performance
    ENABLE_COMPRESSION: bool = Field(default=True, env="ENABLE_COMPRESSION")
    COMPRESSION_LEVEL: int = Field(default=6, env="COMPRESSION_LEVEL")
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    
    # Multi-tenancy
    ENABLE_MULTI_TENANCY: bool = Field(default=True, env="ENABLE_MULTI_TENANCY")
    DEFAULT_TENANT: str = Field(default="default", env="DEFAULT_TENANT")
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://localhost:8080",
            "http://127.0.0.1:3000"
        ],
        env="CORS_ORIGINS"
    )
    CORS_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        env="CORS_METHODS"
    )
    
    # File Storage
    UPLOAD_DIR: str = Field(default="uploads", env="UPLOAD_DIR")
    UPLOAD_MAX_SIZE: int = Field(default=10485760, env="UPLOAD_MAX_SIZE")  # 10MB in bytes
    ALLOWED_FILE_TYPES: List[str] = Field(
        default=["pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx"],
        env="ALLOWED_FILE_TYPES"
    )
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Tanzania Business Rules
    MIN_LOAN_AMOUNT: int = Field(default=50000, env="MIN_LOAN_AMOUNT")  # 50,000 TZS
    MAX_LOAN_AMOUNT: int = Field(default=50000000, env="MAX_LOAN_AMOUNT")  # 50M TZS
    DEFAULT_INTEREST_RATE: float = Field(default=15.0, env="DEFAULT_INTEREST_RATE")
    MAX_LOAN_TERM_MONTHS: int = Field(default=60, env="MAX_LOAN_TERM_MONTHS")
    
    # Email Configuration
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    EMAIL_FROM: Optional[str] = Field(
        default="noreply@tujengeplatform.co.tz",
        env="EMAIL_FROM"
    )
    
    # Validators
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "postgresql+psycopg2://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v
    
    @validator("CORS_ORIGINS", pre=True)
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",")]
        return v
    
    @validator("UPLOAD_MAX_SIZE", pre=True)
    def validate_upload_max_size(cls, v):
        if isinstance(v, str):
            # Remove comments from environment variable values
            v = v.split('#')[0].strip()
            if v:
                return int(v)
        return v
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL"""
        url = self.DATABASE_URL
        if "+asyncpg" in url:
            url = url.replace("+asyncpg", "+psycopg2")
        return url
    
    class Config:
        # env_file = ".env"  # Temporarily disabled due to corrupted file
        case_sensitive = True
        # Allow extra environment variables to prevent validation errors
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings() 