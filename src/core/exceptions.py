"""
Custom exceptions for Contro Discord Bot
Provides structured error handling across the application
"""

from typing import Optional, Any, Dict


class ControError(Exception):
    """Base exception for Contro Discord Bot."""
    pass


class ConfigurationError(ControError):
    """Raised when there's a configuration error."""
    pass


class DatabaseError(ControError):
    """Raised when there's a database error."""
    pass


class CacheError(ControError):
    """Raised when there's a cache error."""
    pass


class BotError(ControError):
    """Raised when there's a bot-related error."""
    pass


class APIError(ControError):
    """Raised when there's an API error."""
    pass


class ValidationError(ControError):
    """Raised when data validation fails."""
    pass


class AuthenticationError(ControError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(ControError):
    """Raised when authorization fails."""
    pass


class RateLimitError(ControError):
    """Raised when rate limit is exceeded."""
    pass


class ServiceUnavailableError(ControError):
    """Raised when a service is unavailable."""
    pass


class ServiceError(ControError):
    """Raised when an external service fails."""
    
    def __init__(self, message: str, service: Optional[str] = None, 
                 status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.service = service
        self.status_code = status_code
    
    def __str__(self):
        if self.service:
            return f"[{self.service}] {self.message}"
        return self.message


class DiscordError(ControError):
    """Raised when Discord API operations fail."""
    
    def __init__(self, message: str, discord_error_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.discord_error_code = discord_error_code
    
    def __str__(self):
        if self.discord_error_code:
            return f"[{self.discord_error_code}] {self.message}"
        return self.message


class FeatureDisabledError(ControError):
    """Raised when a feature is disabled."""
    
    def __init__(self, message: str, feature: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.feature = feature
    
    def __str__(self):
        if self.feature:
            return f"Feature disabled: {self.feature}"
        return self.message


class MaintenanceError(ControError):
    """Raised when the bot is in maintenance mode."""
    
    def __init__(self, message: str, maintenance_type: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.maintenance_type = maintenance_type
    
    def __str__(self):
        if self.maintenance_type:
            return f"Maintenance: {self.maintenance_type}"
        return self.message


# Utility functions for error handling
def handle_exception(func):
    """Decorator to handle exceptions and convert them to ControError."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ControError:
            raise
        except Exception as e:
            raise ControError(f"Unexpected error in {func.__name__}: {str(e)}")
    return wrapper


async def handle_async_exception(func):
    """Async decorator to handle exceptions and convert them to ControError."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ControError:
            raise
        except Exception as e:
            raise ControError(f"Unexpected error in {func.__name__}: {str(e)}")
    return wrapper 