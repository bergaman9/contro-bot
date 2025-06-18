"""Custom error classes for the bot."""

from typing import Optional


class BotError(Exception):
    """Base exception class for all bot errors."""
    
    def __init__(self, message: str, *args, **kwargs):
        super().__init__(message, *args)
        self.message = message
        

class ConfigurationError(BotError):
    """Raised when there's a configuration issue."""
    pass
    

class DatabaseError(BotError):
    """Raised when database operations fail."""
    pass
    

class APIError(BotError):
    """Raised when API operations fail."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.status_code = status_code
        

class PermissionError(BotError):
    """Raised when user lacks required permissions."""
    pass
    

class ValidationError(BotError):
    """Raised when input validation fails."""
    pass
    

class ServiceError(BotError):
    """Raised when a service operation fails."""
    pass
    

class CooldownError(BotError):
    """Raised when a user is on cooldown."""
    
    def __init__(self, message: str, retry_after: float, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self.retry_after = retry_after
        

class FeatureDisabledError(BotError):
    """Raised when a feature is disabled for a guild."""
    
    def __init__(self, feature: str, *args, **kwargs):
        message = f"The {feature} feature is disabled in this server."
        super().__init__(message, *args, **kwargs)
        self.feature = feature 