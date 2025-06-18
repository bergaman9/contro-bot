"""Bot-wide constants and configuration values."""

# Bot information
BOT_VERSION = "2.0.0"
BOT_NAME = "Contro"
BOT_DESCRIPTION = "A powerful Discord bot for community management"

# Default values
DEFAULT_PREFIX = ">"
DEFAULT_LANGUAGE = "en"

# Limits
MAX_PREFIX_LENGTH = 5
MAX_NICKNAME_LENGTH = 32
MAX_REASON_LENGTH = 512

# Colors
class Colors:
    """Discord embed colors."""
    PRIMARY = 0x7289DA     # Discord Blurple
    SUCCESS = 0x43B581     # Green
    WARNING = 0xFAA61A     # Yellow/Orange
    ERROR = 0xF04747       # Red
    INFO = 0x5865F2        # New Discord Blurple
    GOLD = 0xF1C40F        # Gold
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
FEATURES = {
    "LEVELING": True,
    "MODERATION": True,
    "LOGGING": True,
    "WELCOME": True,
    "TICKETS": True,
    "GIVEAWAYS": True,
    "AUTOMOD": True,
    "STARBOARD": True
} 