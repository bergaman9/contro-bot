"""
Base service class for the Discord bot.

This module provides the foundation for all service classes with
common functionality like caching, validation, and error handling.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Dict, Any, List
from datetime import datetime
import asyncio

from ..core.database import Database
from ..core.cache import Cache
from ..core.logger import get_logger
from ..core.exceptions import ServiceError, ValidationError, ResourceNotFoundError


T = TypeVar('T')


class BaseService(ABC, Generic[T]):
    """Base service class with common functionality."""
    
    def __init__(self, database: Database, cache: Cache):
        self.db = database
        self.cache = cache
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> T:
        """Create a new resource."""
        pass
    
    @abstractmethod
    async def get(self, resource_id: str) -> Optional[T]:
        """Get a resource by ID."""
        pass
    
    @abstractmethod
    async def update(self, resource_id: str, data: Dict[str, Any]) -> Optional[T]:
        """Update a resource."""
        pass
    
    @abstractmethod
    async def delete(self, resource_id: str) -> bool:
        """Delete a resource."""
        pass
    
    @abstractmethod
    async def list(self, filters: Optional[Dict[str, Any]] = None, 
                   limit: Optional[int] = None, skip: Optional[int] = None) -> List[T]:
        """List resources with optional filtering."""
        pass
    
    def validate_data(self, data: Dict[str, Any], required_fields: List[str] = None) -> None:
        """Validate input data."""
        if required_fields:
            for field in required_fields:
                if field not in data or data[field] is None:
                    raise ValidationError(field, f"Field '{field}' is required")
    
    def sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize input data."""
        # Remove None values and empty strings
        sanitized = {}
        for key, value in data.items():
            if value is not None and value != "":
                sanitized[key] = value
        return sanitized
    
    async def get_cached(self, key: str, prefix: str = "") -> Optional[Any]:
        """Get a value from cache."""
        try:
            return await self.cache.get(key, prefix)
        except Exception as e:
            self.logger.warning(f"Cache get failed for {key}", error=str(e))
            return None
    
    async def set_cached(self, key: str, value: Any, ttl: Optional[int] = None, 
                        prefix: str = "") -> bool:
        """Set a value in cache."""
        try:
            return await self.cache.set(key, value, ttl, prefix)
        except Exception as e:
            self.logger.warning(f"Cache set failed for {key}", error=str(e))
            return False
    
    async def delete_cached(self, key: str, prefix: str = "") -> bool:
        """Delete a value from cache."""
        try:
            return await self.cache.delete(key, prefix)
        except Exception as e:
            self.logger.warning(f"Cache delete failed for {key}", error=str(e))
            return False
    
    async def invalidate_cache_pattern(self, pattern: str) -> bool:
        """Invalidate cache entries matching a pattern."""
        try:
            return await self.cache.clear(pattern)
        except Exception as e:
            self.logger.warning(f"Cache clear failed for pattern {pattern}", error=str(e))
            return False
    
    def log_operation(self, operation: str, resource_id: str = None, **kwargs) -> None:
        """Log an operation with context."""
        self.logger.info(
            f"Service operation: {operation}",
            service=self.__class__.__name__,
            operation=operation,
            resource_id=resource_id,
            **kwargs
        )
    
    def log_error(self, operation: str, error: Exception, resource_id: str = None, **kwargs) -> None:
        """Log an error with context."""
        self.logger.error(
            f"Service error in {operation}",
            service=self.__class__.__name__,
            operation=operation,
            error=str(error),
            error_type=type(error).__name__,
            resource_id=resource_id,
            **kwargs
        )
    
    async def execute_with_retry(self, operation, max_retries: int = 3, 
                                delay: float = 1.0, **kwargs):
        """Execute an operation with retry logic."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await operation(**kwargs)
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{max_retries})",
                    operation=operation.__name__,
                    error=str(e),
                    attempt=attempt + 1
                )
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
        
        # All retries failed
        raise ServiceError(
            self.__class__.__name__,
            operation.__name__,
            f"Operation failed after {max_retries} attempts: {str(last_error)}"
        )
    
    async def execute_with_timeout(self, operation, timeout: float = 30.0, **kwargs):
        """Execute an operation with timeout."""
        try:
            return await asyncio.wait_for(operation(**kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            raise ServiceError(
                self.__class__.__name__,
                operation.__name__,
                f"Operation timed out after {timeout} seconds"
            )
    
    def format_timestamp(self, timestamp: datetime) -> str:
        """Format a timestamp for storage."""
        return timestamp.isoformat()
    
    def parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse a timestamp string."""
        return datetime.fromisoformat(timestamp_str)
    
    def generate_id(self) -> str:
        """Generate a unique ID."""
        import uuid
        return str(uuid.uuid4())
    
    def safe_get(self, data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Safely get a value from a dictionary."""
        return data.get(key, default)
    
    def safe_set(self, data: Dict[str, Any], key: str, value: Any) -> None:
        """Safely set a value in a dictionary."""
        if value is not None:
            data[key] = value
    
    async def ensure_exists(self, resource_id: str, collection: str) -> bool:
        """Ensure a resource exists in the database."""
        try:
            document = await self.db.find_one(collection, {"_id": resource_id})
            return document is not None
        except Exception as e:
            self.log_error("ensure_exists", e, resource_id, collection=collection)
            return False
    
    async def count_resources(self, collection: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count resources in a collection."""
        try:
            return await self.db.count_documents(collection, filters or {})
        except Exception as e:
            self.log_error("count_resources", e, collection=collection)
            return 0
    
    async def aggregate_data(self, collection: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform aggregation on a collection."""
        try:
            return await self.db.aggregate(collection, pipeline)
        except Exception as e:
            self.log_error("aggregate_data", e, collection=collection)
            return []
    
    def create_pagination_params(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Create pagination parameters."""
        skip = (page - 1) * page_size
        return {
            "skip": skip,
            "limit": page_size,
            "page": page,
            "page_size": page_size
        }
    
    def create_sort_params(self, sort_by: str = "created_at", sort_order: str = "desc") -> List[tuple]:
        """Create sort parameters."""
        order = -1 if sort_order.lower() == "desc" else 1
        return [(sort_by, order)]
    
    def create_search_filter(self, search_term: str, search_fields: List[str]) -> Dict[str, Any]:
        """Create a search filter for multiple fields."""
        if not search_term:
            return {}
        
        search_regex = {"$regex": search_term, "$options": "i"}
        return {"$or": [{field: search_regex} for field in search_fields]}
    
    async def batch_operation(self, operation, items: List[Any], batch_size: int = 100) -> List[Any]:
        """Perform a batch operation on items."""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await operation(batch)
            results.extend(batch_results)
        
        return results
    
    def validate_pagination(self, page: int, page_size: int, max_page_size: int = 100) -> None:
        """Validate pagination parameters."""
        if page < 1:
            raise ValidationError("page", "Page must be greater than 0")
        
        if page_size < 1:
            raise ValidationError("page_size", "Page size must be greater than 0")
        
        if page_size > max_page_size:
            raise ValidationError("page_size", f"Page size cannot exceed {max_page_size}")
    
    def validate_sort_params(self, sort_by: str, allowed_fields: List[str]) -> None:
        """Validate sort parameters."""
        if sort_by not in allowed_fields:
            raise ValidationError("sort_by", f"Sort field must be one of: {', '.join(allowed_fields)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the service."""
        try:
            # Check database connection
            db_healthy = await self.db.health_check()
            
            # Check cache connection
            cache_stats = await self.cache.get_stats()
            
            return {
                "service": self.__class__.__name__,
                "database_healthy": db_healthy,
                "cache_enabled": cache_stats.get("enabled", False),
                "cache_connected": cache_stats.get("redis_connected", False),
                "status": "healthy" if db_healthy else "unhealthy"
            }
            
        except Exception as e:
            self.log_error("health_check", e)
            return {
                "service": self.__class__.__name__,
                "status": "unhealthy",
                "error": str(e)
            } 