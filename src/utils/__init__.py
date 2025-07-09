"""
Utilities package for the Discord bot.

This package is organized into modular subpackages:
- core: Essential utilities (formatting, config, helpers, logging)
- database: Database connection and management
- setup: Server setup system
- settings: Settings management system  
- community: Community features (generic)
- greeting: Welcome/goodbye system
- registration: User registration system
- moderation: Moderation utilities
"""

# Import core utilities for backward compatibility and easy access
from .core import create_embed, hex_to_int, ConfigManager, setup_logging, logger
from .database import initialize_mongodb

__all__ = [
    'create_embed', 
    'hex_to_int',
    'ConfigManager',
    'setup_logging',
    'logger',
    'initialize_mongodb'
]
