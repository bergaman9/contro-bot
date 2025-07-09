"""
Generic community utilities for Discord bot

This module provides generic community features and utilities:
- User management and registration
- Leveling and XP systems
- Event management
- Game matching and sessions
- Ticket system integration
"""

# Initialize the community_views package
import os

# Create the directory if it doesn't exist
os.makedirs(os.path.dirname(__file__), exist_ok=True)

# This file is required to make the directory a Python package
from .ticket_views import TicketButton, TicketModal, TicketCloseView
