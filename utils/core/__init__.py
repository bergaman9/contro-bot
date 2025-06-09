"""
Core utilities module for Discord bot.

This module contains essential utilities including:
- Configuration management
- Formatting utilities
- Discord helpers
- Logging utilities
- Error handling
- Class utilities
- Feature management
"""

from .formatting import create_embed, hex_to_int
from .config import ConfigManager
from .helpers import (
    is_owner, has_permissions, is_feature_enabled, 
    feature_required, get_guild_features, format_time
)
from .discord_helpers import *
from .logger import setup_logging, logger
from .error_handler import setup_error_handlers

__all__ = [
    'create_embed',
    'hex_to_int', 
    'ConfigManager',
    'setup_logging',
    'logger',
    'setup_error_handlers',
    'is_owner',
    'has_permissions',
    'is_feature_enabled',
    'feature_required',
    'get_guild_features',
    'format_time'
] 