"""
Greeting system module for Discord bot.

This module contains welcome and goodbye features including:
- Welcome/goodbye message configuration
- Image processing for welcome cards
- Background management
- Preview generation
"""

from .imaging import download_background

__all__ = ['download_background'] 