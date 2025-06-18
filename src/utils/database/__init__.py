"""
Database utilities module for Discord bot.

This module contains database connection and management utilities.
"""

from .connection import (
    initialize_mongodb, 
    initialize_async_mongodb,
    get_async_db,
    ensure_async_db,
    get_async_client,
    close_async_mongodb,
    DummyAsyncDatabase
)

__all__ = [
    'initialize_mongodb',
    'initialize_async_mongodb', 
    'get_async_db',
    'ensure_async_db',
    'get_async_client',
    'close_async_mongodb',
    'DummyAsyncDatabase'
]