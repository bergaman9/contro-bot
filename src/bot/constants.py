"""Bot-wide constants and configuration values."""
from typing import List, Dict
import discord
import os
from pathlib import Path

# Bot information
BOT_VERSION = "1.0.0"
BOT_NAME = "Contro Bot"
BOT_DESCRIPTION = "A powerful Discord bot for community management"

# Default values
DEFAULT_PREFIX = ">"
DEFAULT_LANGUAGE = "en"
DEFAULT_COLOR = 0x2F3136  # Discord dark theme color

# Paths
ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
TEMP_DIR = DATA_DIR / "temp"

# Ensure directories exist
for directory in [DATA_DIR, LOGS_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Discord limits
MAX_EMBED_TITLE = 256
MAX_EMBED_DESCRIPTION = 4096
MAX_EMBED_FIELDS = 25
MAX_EMBED_FIELD_NAME = 256
MAX_EMBED_FIELD_VALUE = 1024
MAX_EMBED_FOOTER_TEXT = 2048
MAX_EMBED_AUTHOR_NAME = 256
MAX_MESSAGE_LENGTH = 2000

# Rate limits
COMMANDS_PER_MINUTE = 20
COMMANDS_PER_HOUR = 200

# Cooldowns (in seconds)
DEFAULT_COOLDOWN = 3
MODERATION_COOLDOWN = 5
ADMIN_COOLDOWN = 10

# XP and leveling
XP_PER_MESSAGE = 15
XP_COOLDOWN = 60  # 1 minute between XP gains
LEVEL_UP_FORMULA = lambda level: 100 * (level ** 2)  # XP required for level

# Support links
SUPPORT_SERVER = "https://discord.gg/ynGqvsYxah"
BOT_INVITE = "https://discord.com/oauth2/authorize?client_id={bot_id}&permissions=8&scope=bot%20applications.commands"
GITHUB_REPO = "https://github.com/your-username/contro-bot"

# API Configuration
API_PORT = int(os.getenv("API_PORT", 8000))
API_HOST = os.getenv("API_HOST", "0.0.0.0")

# Emoji constants
SUCCESS_EMOJI = "✅"
ERROR_EMOJI = "❌"
WARNING_EMOJI = "⚠️"
INFO_EMOJI = "ℹ️"
LOADING_EMOJI = "⏳"

# Time formats
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

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