"""
API module for Contro Discord Bot
Provides Flask-based REST API for dashboard and external integrations
"""

from .app import create_app, run_api

__version__ = "2.0.0"
__all__ = [
    'create_app',
    'run_api'
]
