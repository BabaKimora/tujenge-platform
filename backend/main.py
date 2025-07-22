"""
Tujenge Platform - Main FastAPI Application
Enterprise-grade Tanzania fintech platform for microfinance operations
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from backend.config import settings
from backend.core.database import db_manager, init_database
from backend.auth.middleware import AuthenticationMiddleware
from backend.core.monitoring import setup_logging, log_request_middleware

# Import all routers
from backend.routers import (
    auth,
    customers,
    loans
)

# Setup logging for Tanzania fintech operations
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management for Tujenge Platform
    Handles startup and shutdown procedures
    """
    # Startup procedures
    logger.info("\U0001F3E6 Starting Tujenge Platform - Tanzania Fintech Solution")
    logger.info("\U0001F4CD Location: Tanzania \U0001F1F9\U0001F1FF")
    logger.info("\U0001F4B1 Currency: TZS (Tanzanian Shilling)")
    logger.info("\U0001F4F1 Mobile Money: M-Pesa, Airtel Money Integration")
    logger.info("\U0001F3DB\uFE0F Government APIs: NIDA, TIN Validation")
    
    try:
        # Initialize database when PostgreSQL is available
        try:
            await init_database()
            logger.info("✅ Database initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Database initialization skipped: {e}")
        
        # Initialize Redis cache when Redis is available
        try:
            from backend.utils.redis_manager import redis_manager
            await redis_manager.initialize()
            logger.info("✅ Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Redis cache initialization skipped: {e}")
        
        # TODO: Setup monitoring when dependencies are available
        # if settings.ENABLE_METRICS:
        #     Instrumentator().instrument(app).expose(app)
        
        logger.info("✅ Tujenge Platform startup completed successfully (development mode)!")
        
        yield
        
    except Exception as e:
        logger.error(f"\u274C Startup failed: {e}")
        raise
    
    # Shutdown procedures
    logger.info("\U0001F504 Shutting down Tujenge Platform...")
    
    try:
        # Close database connections
        await db_manager.close()
        
        # Close cache connections
        try:
            from backend.utils.redis_manager import redis_manager
            await redis_manager.close()
        except ImportError:
            logger.info("Redis manager not available during shutdown")
        except Exception as cache_error:
            logger.warning(f"Cache shutdown error: {cache_error}")
        
        logger.info("\u2705 Tujenge Platform shutdown completed!")
        
    except Exception as e:
        logger.error(f"\u274C Shutdown error: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
    responses={
        422: {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Validation error details",
                        "error_code": "VALIDATION_ERROR"
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Internal server error",
                        "error_code": "INTERNAL_ERROR"
                    }
                }
            }
        }
    }
)

# Add middleware (order matters!)
# 1. Authentication middleware (first - handles JWT and tenant context)
app.add_middleware(AuthenticationMiddleware)

# 2. CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 3. Compression middleware
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)

# Add request logging middleware
app.middleware("http")(log_request_middleware)


# Global exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors with Tanzania-friendly message"""
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Huduma hii haipatikani (Service not found)",
            "message": "The requested resource was not found",
            "error_code": "NOT_FOUND",
            "timestamp": time.time(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Tatizo la kimtandao (Internal server error)",
            "message": "An internal server error occurred",
            "error_code": "INTERNAL_ERROR",
            "timestamp": time.time()
        }
    )


# Root endpoint with Tanzania fintech information
@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """
    Tujenge Platform API Root
    Returns platform information and status
    """
    return {
        "platform": "Tujenge Platform",
        "description": "Tanzania Enterprise Fintech Solution",
        "version": settings.APP_VERSION,
        "status": "operational",
        "location": "Tanzania \U0001F1F9\U0001F1FF",
        "currency": "TZS (Tanzanian Shilling)",
        "supported_services": [
            "Loan Management",
            "Customer Management", 
            "Mobile Money Integration (M-Pesa, Airtel)",
            "Government API Integration (NIDA, TIN)",
            "Document Management",
            "Risk Assessment",
            "Analytics & Reporting"
        ],
        "api_docs": "/docs" if settings.DEBUG else "Contact administrator",
        "contact": {
            "support": "support@tujengeplatform.co.tz",
            "technical": "tech@tujengeplatform.co.tz"
        },
        "timezone": settings.TIMEZONE,
        "language": "Swahili (sw) / English (en)"
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check for all platform components"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {}
    }
    
    try:
        # Database health check
        try:
            db_health = await db_manager.health_check()
            health_status["services"]["database"] = db_health
        except Exception as e:
            health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
        
        # Redis health check
        try:
            from backend.utils.redis_manager import redis_manager
            try:
                await redis_manager.ping()
                health_status["services"]["redis"] = {"status": "healthy"}
            except Exception as e:
                health_status["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
        except ImportError:
            health_status["services"]["redis"] = {"status": "not_configured"}
        
        # Check if any service is unhealthy
        overall_healthy = all(
            service.get("status") == "healthy" 
            for service in health_status["services"].values()
        )
        
        if not overall_healthy:
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e)
        }

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(customers.router, prefix="/api/v1", tags=["Customers"])
app.include_router(loans.router, prefix="/api/v1", tags=["Loans"])

# Mount static files for document serving
app.mount("/static", StaticFiles(directory="static"), name="static")


# Development server configuration
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        server_header=False,
        workers=1 if settings.DEBUG else 4
    )
