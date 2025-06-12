"""
Utilities package for the Discord bot.

This package is organized into modular subpackages:
- core: Essential utilities (formatting, config, helpers, logging)
- database: Database connection and management
- setup: Server setup system
- settings: Settings management system  
- community: Community features (TurkOyto)
- greeting: Welcome/goodbye system
- registration: User registration system
- moderation: Moderation utilities
"""

# Import core utilities for backward compatibility and easy access
from .core import create_embed, hex_to_int, ConfigManager, setup_logging, logger
from .database import initialize_mongodb
from .version import get_version_manager
from .class_utils import Paginator
from .content_loader import load_content
from .error_handler import setup_error_handlers

__all__ = [
    'create_embed', 
    'hex_to_int',
    'ConfigManager',
    'setup_logging',
    'logger',
    'initialize_mongodb',
    'get_version_manager',
    'Paginator',
    'load_content',
    'setup_error_handlers'
]
