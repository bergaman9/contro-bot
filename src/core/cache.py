"""
Cache management for Contro Discord Bot
Provides Redis and in-memory caching capabilities
"""

import asyncio
import json
import pickle
from typing import Optional, Any, Dict, Union
from datetime import timedelta
import redis.asyncio as redis
from .config import get_config
from .logger import get_logger, LoggerMixin


class CacheManager(LoggerMixin):
    """Cache manager for Redis and in-memory caching."""
    
    def __init__(self):
        self.config = get_config().cache
        self.redis_client: Optional[redis.Redis] = None
        self._memory_cache: Dict[str, Any] = {}
        self._memory_cache_ttl: Dict[str, float] = {}
        
    async def connect(self) -> bool:
        """Connect to Redis if configured."""
        if not self.config.enabled:
            self.logger.info("Cache is disabled")
            return True
            
        if not self.config.redis_url:
            self.logger.info("No Redis URL configured, using in-memory cache only")
            return True
            
        try:
            self.logger.info(f"Connecting to Redis: {self.config.redis_url}")
            self.redis_client = redis.from_url(
                self.config.redis_url,
                decode_responses=True,
                max_connections=self.config.max_size
            )
            
            # Test connection
            await self.redis_client.ping()
            self.logger.info("Successfully connected to Redis")
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to connect to Redis: {e}, falling back to in-memory cache")
            self.redis_client = None
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            self.logger.info("Disconnected from Redis")
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache."""
        if not self.config.enabled:
            return default
        
        # Try Redis first
        if self.redis_client:
            try:
                value = await self.redis_client.get(key)
                if value is not None:
                    return json.loads(value)
            except Exception as e:
                self.logger.warning(f"Redis get failed for key {key}: {e}")
        
        # Fall back to memory cache
        if key in self._memory_cache:
            # Check TTL
            if key in self._memory_cache_ttl:
                if asyncio.get_event_loop().time() > self._memory_cache_ttl[key]:
                    del self._memory_cache[key]
                    del self._memory_cache_ttl[key]
                    return default
            return self._memory_cache[key]
        
        return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache."""
        if not self.config.enabled:
            return False
        
        ttl = ttl or self.config.default_ttl
        
        # Try Redis first
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    key, 
                    ttl, 
                    json.dumps(value, default=str)
                )
                return True
            except Exception as e:
                self.logger.warning(f"Redis set failed for key {key}: {e}")
        
        # Fall back to memory cache
        try:
            self._memory_cache[key] = value
            if ttl > 0:
                self._memory_cache_ttl[key] = asyncio.get_event_loop().time() + ttl
            return True
        except Exception as e:
            self.logger.error(f"Memory cache set failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        if not self.config.enabled:
            return False
        
        success = False
        
        # Try Redis first
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
                success = True
            except Exception as e:
                self.logger.warning(f"Redis delete failed for key {key}: {e}")
        
        # Also delete from memory cache
        if key in self._memory_cache:
            del self._memory_cache[key]
            if key in self._memory_cache_ttl:
                del self._memory_cache_ttl[key]
            success = True
        
        return success
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        if not self.config.enabled:
            return False
        
        # Try Redis first
        if self.redis_client:
            try:
                return await self.redis_client.exists(key) > 0
            except Exception as e:
                self.logger.warning(f"Redis exists failed for key {key}: {e}")
        
        # Check memory cache
        if key in self._memory_cache:
            # Check TTL
            if key in self._memory_cache_ttl:
                if asyncio.get_event_loop().time() > self._memory_cache_ttl[key]:
                    del self._memory_cache[key]
                    del self._memory_cache_ttl[key]
                    return False
            return True
        
        return False
    
    async def clear(self) -> bool:
        """Clear all cache."""
        if not self.config.enabled:
            return False
        
        success = True
        
        # Clear Redis
        if self.redis_client:
            try:
                await self.redis_client.flushdb()
            except Exception as e:
                self.logger.warning(f"Redis clear failed: {e}")
                success = False
        
        # Clear memory cache
        self._memory_cache.clear()
        self._memory_cache_ttl.clear()
        
        return success
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.config.enabled:
            return {"enabled": False}
        
        stats = {
            "enabled": True,
            "redis_connected": self.redis_client is not None,
            "memory_cache_size": len(self._memory_cache),
            "memory_cache_ttl_size": len(self._memory_cache_ttl)
        }
        
        if self.redis_client:
            try:
                info = await self.redis_client.info()
                stats.update({
                    "redis_used_memory": info.get("used_memory", 0),
                    "redis_connected_clients": info.get("connected_clients", 0),
                    "redis_keyspace_hits": info.get("keyspace_hits", 0),
                    "redis_keyspace_misses": info.get("keyspace_misses", 0)
                })
            except Exception as e:
                self.logger.warning(f"Failed to get Redis stats: {e}")
        
        return stats
    
    def _cleanup_expired_memory_cache(self) -> None:
        """Clean up expired entries from memory cache."""
        current_time = asyncio.get_event_loop().time()
        expired_keys = [
            key for key, expiry in self._memory_cache_ttl.items()
            if current_time > expiry
        ]
        
        for key in expired_keys:
            del self._memory_cache[key]
            del self._memory_cache_ttl[key]


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.connect()
    return _cache_manager


async def close_cache() -> None:
    """Close the cache connection."""
    global _cache_manager
    if _cache_manager:
        await _cache_manager.disconnect()
        _cache_manager = None 