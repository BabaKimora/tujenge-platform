"""
Tujenge Platform - Redis Manager
Redis caching and session management for Tanzania fintech platform
"""

import json
import logging
from typing import Any, Optional, Dict
from datetime import timedelta
import asyncio
import os

logger = logging.getLogger(__name__)

class RedisManager:
    """
    Redis manager for caching and session management
    Provides a simple interface for Redis operations with fallback
    """
    
    def __init__(self):
        # Redis configuration from environment
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis_password = os.getenv("REDIS_PASSWORD", None)
        
        # Connection settings
        self.max_connections = 20
        self.connection_timeout = 5
        self.retry_attempts = 3
        
        # Connection pool (will be initialized when needed)
        self.redis_client = None
        self.is_connected = False
        
        # In-memory fallback cache for development
        self._memory_cache = {}
        self._cache_ttl = {}
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            # Try to import and connect to Redis
            import aioredis
            
            self.redis_client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self.max_connections,
                socket_connect_timeout=self.connection_timeout,
                socket_timeout=self.connection_timeout,
                retry_on_timeout=True,
                password=self.redis_password
            )
            
            # Test connection
            await self.redis_client.ping()
            self.is_connected = True
            logger.info("✅ Redis connection established successfully")
            
        except ImportError:
            logger.warning("⚠️ aioredis not installed, using in-memory cache fallback")
            self.is_connected = False
            
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}, using in-memory cache fallback")
            self.is_connected = False
    
    async def get_cache(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            if self.is_connected and self.redis_client:
                return await self.redis_client.get(key)
            else:
                # Fallback to memory cache
                return self._get_memory_cache(key)
                
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return self._get_memory_cache(key)
    
    async def set_cache(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        try:
            if self.is_connected and self.redis_client:
                await self.redis_client.setex(key, ttl, value)
                return True
            else:
                # Fallback to memory cache
                return self._set_memory_cache(key, value, ttl)
                
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return self._set_memory_cache(key, value, ttl)
    
    async def delete_cache(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.is_connected and self.redis_client:
                result = await self.redis_client.delete(key)
                return result > 0
            else:
                # Fallback to memory cache
                return self._delete_memory_cache(key)
                
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return self._delete_memory_cache(key)
    
    async def cache_json(self, key: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Cache JSON data"""
        try:
            json_string = json.dumps(data, default=str)
            return await self.set_cache(key, json_string, ttl)
        except Exception as e:
            logger.error(f"JSON cache error: {e}")
            return False
    
    async def get_json_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON data from cache"""
        try:
            cached_data = await self.get_cache(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"JSON cache retrieval error: {e}")
            return None
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if self.is_connected and self.redis_client:
                return await self.redis_client.exists(key) > 0
            else:
                return key in self._memory_cache
                
        except Exception as e:
            logger.warning(f"Cache exists check error: {e}")
            return key in self._memory_cache
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for key"""
        try:
            if self.is_connected and self.redis_client:
                return await self.redis_client.expire(key, ttl)
            else:
                # Update TTL in memory cache
                if key in self._memory_cache:
                    import time
                    self._cache_ttl[key] = time.time() + ttl
                    return True
                return False
                
        except Exception as e:
            logger.warning(f"Cache expire error: {e}")
            return False
    
    async def clear_cache(self, pattern: str = "*") -> bool:
        """Clear cache by pattern"""
        try:
            if self.is_connected and self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                return True
            else:
                # Clear memory cache
                if pattern == "*":
                    self._memory_cache.clear()
                    self._cache_ttl.clear()
                else:
                    # Simple pattern matching for memory cache
                    keys_to_delete = [key for key in self._memory_cache.keys() if pattern.replace("*", "") in key]
                    for key in keys_to_delete:
                        del self._memory_cache[key]
                        self._cache_ttl.pop(key, None)
                return True
                
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if self.is_connected and self.redis_client:
                info = await self.redis_client.info()
                return {
                    "connected": True,
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "connected_clients": info.get("connected_clients", 0),
                    "cache_type": "redis"
                }
            else:
                return {
                    "connected": False,
                    "memory_cache_size": len(self._memory_cache),
                    "cache_type": "memory"
                }
                
        except Exception as e:
            logger.error(f"Stats retrieval error: {e}")
            return {
                "connected": False,
                "error": str(e),
                "cache_type": "error"
            }
    
    async def close(self):
        """Close Redis connection"""
        try:
            if self.redis_client:
                await self.redis_client.close()
                self.is_connected = False
                logger.info("🔴 Redis connection closed")
        except Exception as e:
            logger.error(f"Redis close error: {e}")
    
    # Memory cache fallback methods
    
    def _get_memory_cache(self, key: str) -> Optional[str]:
        """Get from in-memory cache with TTL check"""
        if key in self._memory_cache:
            # Check TTL
            if key in self._cache_ttl:
                import time
                if time.time() > self._cache_ttl[key]:
                    # Expired
                    del self._memory_cache[key]
                    del self._cache_ttl[key]
                    return None
            
            return self._memory_cache[key]
        
        return None
    
    def _set_memory_cache(self, key: str, value: str, ttl: int) -> bool:
        """Set in-memory cache with TTL"""
        try:
            self._memory_cache[key] = value
            
            if ttl > 0:
                import time
                self._cache_ttl[key] = time.time() + ttl
            
            return True
        except Exception as e:
            logger.error(f"Memory cache set error: {e}")
            return False
    
    def _delete_memory_cache(self, key: str) -> bool:
        """Delete from in-memory cache"""
        try:
            if key in self._memory_cache:
                del self._memory_cache[key]
                self._cache_ttl.pop(key, None)
                return True
            return False
        except Exception as e:
            logger.error(f"Memory cache delete error: {e}")
            return False

# Global Redis manager instance
redis_manager = RedisManager() 