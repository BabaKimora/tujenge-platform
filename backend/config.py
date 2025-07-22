# backend/config.py
"""
Configuration settings for Tujenge Platform
Handles environment variables and application settings
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import validator
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    APP_NAME: str = "Tujenge Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # Security
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_RETRY_ON_TIMEOUT: bool = True
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Tanzania Market Configuration
    CURRENCY: str = "TZS"
    TIMEZONE: str = "Africa/Dar_es_Salaam"
    LANGUAGE: str = "sw"
    COUNTRY_CODE: str = "TZ"
    
    # Mobile Money Configuration
    MPESA_CONSUMER_KEY: Optional[str] = None
    MPESA_CONSUMER_SECRET: Optional[str] = None
    MPESA_BUSINESS_SHORT_CODE: Optional[str] = None
    MPESA_PASS_KEY: Optional[str] = None
    MPESA_ENVIRONMENT: str = "sandbox"  # sandbox or production
    
    AIRTEL_API_KEY: Optional[str] = None
    AIRTEL_API_SECRET: Optional[str] = None
    AIRTEL_ENVIRONMENT: str = "sandbox"  # sandbox or production
    
    # Government API Configuration
    NIDA_API_URL: Optional[str] = None
    NIDA_API_KEY: Optional[str] = None
    NIDA_API_SECRET: Optional[str] = None
    
    TIN_API_URL: Optional[str] = None
    TIN_API_KEY: Optional[str] = None
    TIN_API_SECRET: Optional[str] = None
    
    # Email Configuration
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    
    # SMS Configuration
    SMS_PROVIDER: str = "twilio"  # twilio, nexmo, etc.
    SMS_API_KEY: Optional[str] = None
    SMS_API_SECRET: Optional[str] = None
    SMS_FROM_NUMBER: Optional[str] = None
    
    # File Storage
    STORAGE_TYPE: str = "local"  # local, s3, gcs
    STORAGE_PATH: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [
        "pdf", "doc", "docx", "xls", "xlsx", 
        "jpg", "jpeg", "png", "gif"
    ]
    
    # AWS S3 (if using S3 storage)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    DEFAULT_RATE_LIMIT: int = 1000  # requests per hour
    LOGIN_RATE_LIMIT: int = 5       # login attempts per 15 minutes
    
    # Security Headers
    SECURITY_HEADERS_ENABLED: bool = True
    HSTS_MAX_AGE: int = 31536000  # 1 year
    
    # Monitoring
    METRICS_ENABLED: bool = True
    HEALTH_CHECK_ENABLED: bool = True
    
    # Audit Logging
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    
    # Background Tasks
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # Development
    RELOAD: bool = False
    
    @validator('CORS_ORIGINS', pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator('CORS_ALLOW_METHODS', pre=True)
    def assemble_cors_methods(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator('CORS_ALLOW_HEADERS', pre=True)
    def assemble_cors_headers(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator('ALLOWED_FILE_TYPES', pre=True)
    def assemble_file_types(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator('JWT_SECRET_KEY')
    def validate_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError('JWT_SECRET_KEY must be at least 32 characters long')
        return v
    
    @validator('DATABASE_URL')
    def validate_database_url(cls, v):
        if not v:
            raise ValueError('DATABASE_URL is required')
        if not v.startswith(('postgresql://', 'postgres://')):
            raise ValueError('DATABASE_URL must be a PostgreSQL connection string')
        return v
    
    @validator('REDIS_URL')
    def validate_redis_url(cls, v):
        if not v:
            raise ValueError('REDIS_URL is required')
        if not v.startswith('redis://'):
            raise ValueError('REDIS_URL must be a Redis connection string')
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development environment settings"""
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"
    RELOAD: bool = True
    
    # Relaxed security for development
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

class StagingSettings(Settings):
    """Staging environment settings"""
    DEBUG: bool = False
    ENVIRONMENT: str = "staging"
    LOG_LEVEL: str = "INFO"
    
    # Moderate security for staging
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2 hours

class ProductionSettings(Settings):
    """Production environment settings"""
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "WARNING"
    
    # Strict security for production
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    SECURITY_HEADERS_ENABLED: bool = True
    RATE_LIMIT_ENABLED: bool = True
    
    @validator('CORS_ORIGINS')
    def validate_production_cors(cls, v):
        if "*" in v:
            raise ValueError('Wildcard CORS origins not allowed in production')
        return v

@lru_cache()
def get_settings() -> Settings:
    """Get application settings based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "development":
        return DevelopmentSettings()
    elif env == "staging":
        return StagingSettings()
    elif env == "production":
        return ProductionSettings()
    else:
        return Settings()

# Global settings instance
settings = get_settings()

# Database configuration
DATABASE_CONFIG = {
    "url": settings.DATABASE_URL,
    "pool_size": settings.DATABASE_POOL_SIZE,
    "max_overflow": settings.DATABASE_MAX_OVERFLOW,
    "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
    "pool_recycle": settings.DATABASE_POOL_RECYCLE,
    "echo": settings.DEBUG,
    "future": True
}

# Redis configuration
REDIS_CONFIG = {
    "url": settings.REDIS_URL,
    "max_connections": settings.REDIS_MAX_CONNECTIONS,
    "retry_on_timeout": settings.REDIS_RETRY_ON_TIMEOUT,
    "decode_responses": True
}

# JWT configuration
JWT_CONFIG = {
    "secret_key": settings.JWT_SECRET_KEY,
    "algorithm": settings.JWT_ALGORITHM,
    "access_token_expire_minutes": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    "refresh_token_expire_days": settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
}

# CORS configuration
CORS_CONFIG = {
    "allow_origins": settings.CORS_ORIGINS,
    "allow_credentials": settings.CORS_ALLOW_CREDENTIALS,
    "allow_methods": settings.CORS_ALLOW_METHODS,
    "allow_headers": settings.CORS_ALLOW_HEADERS
}

# Mobile money configuration
MOBILE_MONEY_CONFIG = {
    "mpesa": {
        "consumer_key": settings.MPESA_CONSUMER_KEY,
        "consumer_secret": settings.MPESA_CONSUMER_SECRET,
        "business_short_code": settings.MPESA_BUSINESS_SHORT_CODE,
        "pass_key": settings.MPESA_PASS_KEY,
        "environment": settings.MPESA_ENVIRONMENT
    },
    "airtel": {
        "api_key": settings.AIRTEL_API_KEY,
        "api_secret": settings.AIRTEL_API_SECRET,
        "environment": settings.AIRTEL_ENVIRONMENT
    }
}

# Government API configuration
GOVERNMENT_API_CONFIG = {
    "nida": {
        "url": settings.NIDA_API_URL,
        "api_key": settings.NIDA_API_KEY,
        "api_secret": settings.NIDA_API_SECRET
    },
    "tin": {
        "url": settings.TIN_API_URL,
        "api_key": settings.TIN_API_KEY,
        "api_secret": settings.TIN_API_SECRET
    }
}

# Email configuration
EMAIL_CONFIG = {
    "smtp_host": settings.SMTP_HOST,
    "smtp_port": settings.SMTP_PORT,
    "smtp_username": settings.SMTP_USERNAME,
    "smtp_password": settings.SMTP_PASSWORD,
    "smtp_tls": settings.SMTP_TLS,
    "smtp_ssl": settings.SMTP_SSL
}

# File storage configuration
STORAGE_CONFIG = {
    "type": settings.STORAGE_TYPE,
    "path": settings.STORAGE_PATH,
    "max_file_size": settings.MAX_FILE_SIZE,
    "allowed_file_types": settings.ALLOWED_FILE_TYPES,
    "aws": {
        "access_key_id": settings.AWS_ACCESS_KEY_ID,
        "secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "region": settings.AWS_REGION,
        "bucket": settings.AWS_S3_BUCKET
    }
}

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": settings.LOG_FORMAT,
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "detailed",
            "class": "logging.FileHandler",
            "filename": settings.LOG_FILE,
        } if settings.LOG_FILE else None,
    },
    "root": {
        "level": settings.LOG_LEVEL,
        "handlers": ["default"] + (["file"] if settings.LOG_FILE else []),
    },
    "loggers": {
        "uvicorn": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "level": "WARNING",
            "handlers": ["default"],
            "propagate": False,
        },
    },
}

# Remove None handlers
if LOGGING_CONFIG["handlers"]["file"] is None:
    del LOGGING_CONFIG["handlers"]["file"]