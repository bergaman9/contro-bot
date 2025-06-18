"""Base service class."""
from typing import Optional
from ..database.connection import DatabaseConnection
import logging

logger = logging.getLogger(__name__)


class BaseService:
    """Base class for services."""
    
    def __init__(self, db: Optional[DatabaseConnection] = None):
        """Initialize service.
        
        Args:
            db: Database connection (optional, will use default if not provided)
        """
        self.db = db
        self._repositories = {}
    
    async def initialize(self):
        """Initialize the service (connect to DB, etc)."""
        if self.db and not self.db._connection:
            await self.db.connect()
    
    async def cleanup(self):
        """Clean up resources."""
        if self.db:
            await self.db.disconnect()
    
    def log_info(self, message: str, **kwargs):
        """Log info message."""
        logger.info(f"[{self.__class__.__name__}] {message}", **kwargs)
    
    def log_error(self, message: str, exc_info=None, **kwargs):
        """Log error message."""
        logger.error(f"[{self.__class__.__name__}] {message}", exc_info=exc_info, **kwargs)
    
    def log_warning(self, message: str, **kwargs):
        """Log warning message."""
        logger.warning(f"[{self.__class__.__name__}] {message}", **kwargs) 