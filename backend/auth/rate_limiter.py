# backend/auth/rate_limiter.py
"""
Rate Limiter Service for Tujenge Platform
Implements sliding window rate limiting with Redis
"""
import redis
import time
import json
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import logging
from backend.config import settings

logger = logging.getLogger(__name__)

class RateLimitType(str, Enum):
    """Types of rate limits"""
    LOGIN_ATTEMPTS = "login_attempts"
    API_REQUESTS = "api_requests"
    PASSWORD_RESET = "password_reset"
    SMS_REQUESTS = "sms_requests"
    EMAIL_REQUESTS = "email_requests"
    MOBILE_MONEY = "mobile_money"
    NIDA_VALIDATION = "nida_validation"

@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    max_requests: int
    window_seconds: int
    burst_allowance: int = 0  # Additional requests allowed in burst
    block_duration: int = 0   # How long to block after limit exceeded

@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None

class RateLimiter:
    """
    Redis-based rate limiter with sliding window algorithm
    """
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        # Default rate limit configurations
        self.rate_limit_configs = {
            RateLimitType.LOGIN_ATTEMPTS: RateLimitConfig(
                max_requests=5,
                window_seconds=900,  # 15 minutes
                block_duration=1800  # 30 minutes block
            ),
            RateLimitType.API_REQUESTS: RateLimitConfig(
                max_requests=1000,
                window_seconds=3600,  # 1 hour
                burst_allowance=100
            ),
            RateLimitType.PASSWORD_RESET: RateLimitConfig(
                max_requests=3,
                window_seconds=3600,  # 1 hour
                block_duration=3600   # 1 hour block
            ),
            RateLimitType.SMS_REQUESTS: RateLimitConfig(
                max_requests=5,
                window_seconds=3600,  # 1 hour
                block_duration=1800   # 30 minutes block
            ),
            RateLimitType.EMAIL_REQUESTS: RateLimitConfig(
                max_requests=10,
                window_seconds=3600,  # 1 hour
            ),
            RateLimitType.MOBILE_MONEY: RateLimitConfig(
                max_requests=50,
                window_seconds=3600,  # 1 hour
                burst_allowance=10
            ),
            RateLimitType.NIDA_VALIDATION: RateLimitConfig(
                max_requests=100,
                window_seconds=3600,  # 1 hour
            )
        }
    
    async def check_rate_limit(
        self,
        key: str,
        rate_limit_type: RateLimitType = RateLimitType.API_REQUESTS,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None
    ) -> RateLimitResult:
        """
        Check if request is within rate limit using sliding window
        """
        try:
            config = self.rate_limit_configs[rate_limit_type]
            
            # Override with custom values if provided
            if max_requests is not None:
                config.max_requests = max_requests
            if window_seconds is not None:
                config.window_seconds = window_seconds
            
            # Check if currently blocked
            block_key = f"rate_limit_block:{rate_limit_type.value}:{key}"
            if await self._is_blocked(block_key):
                block_ttl = self.redis_client.ttl(block_key)
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=int(time.time()) + block_ttl,
                    retry_after=block_ttl
                )
            
            # Sliding window rate limiting
            now = time.time()
            window_start = now - config.window_seconds
            rate_key = f"rate_limit:{rate_limit_type.value}:{key}"
            
            # Remove old entries outside the window
            self.redis_client.zremrangebyscore(rate_key, 0, window_start)
            
            # Count current requests in window
            current_count = self.redis_client.zcard(rate_key)
            
            # Calculate effective limit (including burst allowance)
            effective_limit = config.max_requests + config.burst_allowance
            
            if current_count < effective_limit:
                # Add current request
                request_id = f"{now}:{id(object())}"
                self.redis_client.zadd(rate_key, {request_id: now})
                self.redis_client.expire(rate_key, config.window_seconds)
                
                remaining = effective_limit - current_count - 1
                reset_time = int(window_start + config.window_seconds)
                
                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    reset_time=reset_time
                )
            else:
                # Rate limit exceeded
                if config.block_duration > 0:
                    # Apply block
                    self.redis_client.setex(
                        block_key,
                        config.block_duration,
                        json.dumps({
                            "blocked_at": now,
                            "reason": "Rate limit exceeded",
                            "limit": config.max_requests,
                            "window": config.window_seconds
                        })
                    )
                    
                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        reset_time=int(now + config.block_duration),
                        retry_after=config.block_duration
                    )
                else:
                    # No block, just deny
                    reset_time = int(window_start + config.window_seconds)
                    retry_after = reset_time - int(now)
                    
                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        reset_time=reset_time,
                        retry_after=retry_after
                    )
        
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            # Fail open - allow request if rate limiter fails
            return RateLimitResult(
                allowed=True,
                remaining=999,
                reset_time=int(time.time()) + 3600
            )
    
    async def _is_blocked(self, block_key: str) -> bool:
        """Check if key is currently blocked"""
        return self.redis_client.exists(block_key)
    
    async def reset_rate_limit(self, key: str, rate_limit_type: RateLimitType):
        """Reset rate limit for a key"""
        rate_key = f"rate_limit:{rate_limit_type.value}:{key}"
        block_key = f"rate_limit_block:{rate_limit_type.value}:{key}"
        
        self.redis_client.delete(rate_key)
        self.redis_client.delete(block_key)
    
    async def get_rate_limit_status(
        self, 
        key: str, 
        rate_limit_type: RateLimitType
    ) -> Dict:
        """Get current rate limit status for debugging"""
        config = self.rate_limit_configs[rate_limit_type]
        now = time.time()
        window_start = now - config.window_seconds
        
        rate_key = f"rate_limit:{rate_limit_type.value}:{key}"
        block_key = f"rate_limit_block:{rate_limit_type.value}:{key}"
        
        # Get current request count
        self.redis_client.zremrangebyscore(rate_key, 0, window_start)
        current_count = self.redis_client.zcard(rate_key)
        
        # Check if blocked
        is_blocked = self.redis_client.exists(block_key)
        block_info = None
        if is_blocked:
            block_data = self.redis_client.get(block_key)
            if block_data:
                block_info = json.loads(block_data)
        
        return {
            "key": key,
            "type": rate_limit_type.value,
            "current_count": current_count,
            "limit": config.max_requests,
            "window_seconds": config.window_seconds,
            "is_blocked": is_blocked,
            "block_info": block_info,
            "remaining": max(0, config.max_requests - current_count),
            "reset_time": int(window_start + config.window_seconds)
        }
    
    async def increment_counter(
        self, 
        key: str, 
        rate_limit_type: RateLimitType,
        amount: int = 1
    ) -> int:
        """Increment a counter for rate limiting"""
        rate_key = f"rate_limit:{rate_limit_type.value}:{key}"
        config = self.rate_limit_configs[rate_limit_type]
        
        # Use simple counter for some use cases
        current = self.redis_client.get(rate_key)
        if current is None:
            current = 0
        else:
            current = int(current)
        
        new_value = current + amount
        self.redis_client.setex(rate_key, config.window_seconds, new_value)
        
        return new_value
    
    def set_custom_config(
        self, 
        rate_limit_type: RateLimitType, 
        config: RateLimitConfig
    ):
        """Set custom rate limit configuration"""
        self.rate_limit_configs[rate_limit_type] = config
    
    async def cleanup_expired_entries(self):
        """Cleanup expired rate limit entries"""
        try:
            pattern = "rate_limit:*"
            keys = self.redis_client.keys(pattern)
            
            now = time.time()
            cleaned = 0
            
            for key in keys:
                # Extract rate limit type and window from key
                try:
                    parts = key.split(":")
                    if len(parts) >= 3:
                        rate_type = parts[1]
                        if rate_type in [t.value for t in RateLimitType]:
                            config = self.rate_limit_configs[RateLimitType(rate_type)]
                            window_start = now - config.window_seconds
                            
                            # Remove old entries
                            removed = self.redis_client.zremrangebyscore(key, 0, window_start)
                            if removed > 0:
                                cleaned += removed
                except Exception as e:
                    logger.warning(f"Error cleaning up rate limit key {key}: {str(e)}")
            
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired rate limit entries")
                
        except Exception as e:
            logger.error(f"Rate limit cleanup error: {str(e)}")

# Specialized rate limiters for specific use cases

class LoginRateLimiter:
    """Specialized rate limiter for login attempts"""
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
    
    async def check_login_attempt(self, identifier: str) -> RateLimitResult:
        """Check login attempt rate limit"""
        return await self.rate_limiter.check_rate_limit(
            key=identifier,
            rate_limit_type=RateLimitType.LOGIN_ATTEMPTS
        )
    
    async def record_failed_login(self, identifier: str):
        """Record a failed login attempt"""
        await self.rate_limiter.increment_counter(
            key=f"failed:{identifier}",
            rate_limit_type=RateLimitType.LOGIN_ATTEMPTS
        )
    
    async def record_successful_login(self, identifier: str):
        """Record successful login and reset failed attempts"""
        await self.rate_limiter.reset_rate_limit(
            key=f"failed:{identifier}",
            rate_limit_type=RateLimitType.LOGIN_ATTEMPTS
        )

class MobileMoneyRateLimiter:
    """Specialized rate limiter for mobile money operations"""
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
    
    async def check_transaction_limit(
        self, 
        user_id: int, 
        tenant_id: int
    ) -> RateLimitResult:
        """Check mobile money transaction rate limit"""
        key = f"user:{user_id}:tenant:{tenant_id}"
        return await self.rate_limiter.check_rate_limit(
            key=key,
            rate_limit_type=RateLimitType.MOBILE_MONEY
        )
    
    async def check_nida_validation_limit(
        self, 
        tenant_id: int
    ) -> RateLimitResult:
        """Check NIDA validation rate limit per tenant"""
        key = f"tenant:{tenant_id}"
        return await self.rate_limiter.check_rate_limit(
            key=key,
            rate_limit_type=RateLimitType.NIDA_VALIDATION
        )

# Initialize rate limiter instances
rate_limiter = RateLimiter()
login_rate_limiter = LoginRateLimiter(rate_limiter)
mobile_money_rate_limiter = MobileMoneyRateLimiter(rate_limiter)

# Cleanup task (to be run periodically)
async def cleanup_rate_limits():
    """Periodic cleanup of expired rate limit entries"""
    while True:
        try:
            await rate_limiter.cleanup_expired_entries()
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Rate limit cleanup task error: {str(e)}")
            await asyncio.sleep(60)  # Retry after 1 minute on error