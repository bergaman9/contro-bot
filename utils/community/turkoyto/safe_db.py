import asyncio
import logging
from functools import wraps

logger = logging.getLogger('turkoyto.safe_db')

class DatabaseTimeoutError(Exception):
    """Raised when a database operation times out"""
    pass

async def safe_db_operation(func, *args, timeout=5.0, **kwargs):
    """
    Execute a database operation with a timeout to prevent indefinite blocking.
    
    Args:
        func: The database function to call
        *args: Arguments to pass to the function
        timeout: Maximum time to wait for the operation (seconds)
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the database operation
        
    Raises:
        DatabaseTimeoutError: If the operation times out
    """
    try:
        # Create a separate task for the database operation
        task = asyncio.create_task(func(*args, **kwargs))
        
        # Wait for the task to complete with a timeout
        return await asyncio.wait_for(task, timeout=timeout)
    except asyncio.TimeoutError:
        # Cancel the task if it times out
        task.cancel()
        logger.error(f"Database operation timed out after {timeout} seconds: {func.__name__}")
        raise DatabaseTimeoutError(f"Database operation timed out: {func.__name__}")
    except Exception as e:
        logger.error(f"Database operation failed: {func.__name__} - {str(e)}")
        raise

def with_timeout(timeout=5.0):
    """
    Decorator to add timeout handling to database operations.
    
    Usage:
        @with_timeout(10.0)
        async def my_db_func(self, ...):
            # database operations
    
    Args:
        timeout: Maximum time to wait for the operation (seconds)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await safe_db_operation(func, *args, timeout=timeout, **kwargs)
            except DatabaseTimeoutError:
                # Return None on timeout by default
                return None
        return wrapper
    return decorator

# Safe synchronous alternative for find_one
def safe_find_one(collection, query, default=None, timeout_ms=5000):
    """
    A safer version of find_one with timeout settings.
    
    Args:
        collection: MongoDB collection
        query: Query to execute
        default: Default value to return if operation fails
        timeout_ms: Timeout in milliseconds
        
    Returns:
        Query result or default value
    """
    try:
        # Set server selection and socket timeouts
        return collection.with_options(
            server_selection_timeout_ms=timeout_ms,
            socket_timeout_ms=timeout_ms
        ).find_one(query)
    except Exception as e:
        logger.error(f"Error in safe_find_one: {e}")
        return default
