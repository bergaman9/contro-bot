"""Bot-wide constants and configuration values."""
from typing import List, Dict
import discord

# Bot information
BOT_VERSION = "3.0.0"
BOT_NAME = "Contro"
BOT_DESCRIPTION = "A powerful Discord bot for community management"

# Default values
DEFAULT_PREFIX = "!"
DEFAULT_LANGUAGE = "en"

# Owner IDs (add your Discord user IDs here)
OWNER_IDS: List[int] = [
    # 123456789012345678  # Example owner ID
]

# Limits
MAX_PREFIX_LENGTH = 5
MAX_NICKNAME_LENGTH = 32
MAX_REASON_LENGTH = 512

# Colors
class Colors:
    """Discord embed colors."""
    PRIMARY = discord.Color.blue()
    SUCCESS = discord.Color.green()
    WARNING = discord.Color.orange()
    ERROR = discord.Color.red()
    INFO = discord.Color.blurple()
    GOLD = discord.Color.gold()
    PURPLE = 0x9B59B6      # Purple
    
# Emojis
class Emojis:
    """Common emoji constants."""
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    ARROW_RIGHT = "➡️"
    ARROW_LEFT = "⬅️"
    STAR = "⭐"
    TROPHY = "🏆"
    CROWN = "👑"
    
# Time
CACHE_TTL = 300  # 5 minutes
COOLDOWN_STANDARD = 3  # 3 seconds
COOLDOWN_PREMIUM = 1   # 1 second

# Pagination
ITEMS_PER_PAGE = 10
MAX_PAGES = 100

# Experience and Leveling
XP_PER_MESSAGE = 15
XP_COOLDOWN = 60  # 1 minute
LEVEL_MULTIPLIER = 0.1

# Permissions
ADMIN_PERMISSIONS = [
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels"
]

MOD_PERMISSIONS = [
    "kick_members",
    "ban_members",
    "moderate_members",
    "manage_messages"
]

# API Configuration
API_PORT = 8000
API_HOST = "0.0.0.0"

# Feature flags
FEATURES = [
    "leveling",
    "welcome",
    "logging", 
    "moderation",
    "tickets",
    "giveaways",
    "starboard",
    "automod",
    "temp_channels"
]

# Language Codes
SUPPORTED_LANGUAGES = {
    "en": "English",
    "tr": "Türkçe"
}

# XP Settings
class XPSettings:
    """XP system settings."""
    MIN_PER_MESSAGE = 15
    MAX_PER_MESSAGE = 25
    COOLDOWN = 60  # seconds
    
# Level Roles (example structure)
LEVEL_ROLES: Dict[int, str] = {
    5: "Beginner",
    10: "Member",
    20: "Active",
    30: "Expert",
    50: "Master",
    100: "Legend"
} 