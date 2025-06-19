"""
Settings managers for different bot features.
This module provides specialized managers for different aspects of bot configuration.
"""

import discord
from typing import Dict, List, Optional, Any
from src.utils.database.connection import get_async_db


class BaseSettingsManager:
    """Base class for all settings managers"""
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = get_async_db()
    
    async def get_guild_settings(self, guild_id: int, collection: str) -> Dict[str, Any]:
        """Get settings for a specific guild from a collection"""
        return await self.mongo_db[collection].find_one({"guild_id": guild_id}) or {}
    
    async def update_guild_settings(self, guild_id: int, collection: str, settings: Dict[str, Any]) -> bool:
        """Update settings for a specific guild in a collection"""
        try:
            await self.mongo_db[collection].update_one(
                {"guild_id": guild_id},
                {"$set": settings},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error updating guild settings: {e}")
            return False


class ModerationSettingsManager(BaseSettingsManager):
    """Manager for moderation-related settings"""
    
    async def get_moderation_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get moderation settings for a guild"""
        default_settings = {
            "auto_moderation_enabled": True,
            "profanity_filter_enabled": False,
            "ai_profanity_filter_enabled": False,  # New Sinkaf integration
            "spam_detection_enabled": True,
            "caps_filter_enabled": False,
            "link_filter_enabled": False,
            "invite_filter_enabled": False,
            "mention_spam_limit": 5,
            "message_spam_limit": 5,
            "caps_percentage_limit": 70,
            "moderation_log_channel": None,
            "auto_punishment_enabled": False,
            "punishment_type": "warn",  # warn, mute, kick, ban
            "punishment_duration": 3600,  # in seconds for mute
            "warning_threshold": 3,
            "mute_role_id": None,
            "bypass_roles": [],
            "whitelist_channels": [],
            "profanity_action": "delete",  # delete, warn, mute, kick, ban
            "ai_profanity_confidence_threshold": 0.7,  # Sinkaf confidence threshold
            "log_deleted_messages": True
        }
        
        settings = await self.get_guild_settings(guild_id, "moderation_settings")
        return {**default_settings, **settings}
    
    async def update_moderation_settings(self, guild_id: int, **kwargs) -> bool:
        """Update moderation settings for a guild"""
        return await self.update_guild_settings(guild_id, "moderation_settings", kwargs)
    
    async def toggle_ai_profanity_filter(self, guild_id: int) -> bool:
        """Toggle AI profanity filter and return new state"""
        settings = await self.get_moderation_settings(guild_id)
        new_state = not settings.get("ai_profanity_filter_enabled", False)
        await self.update_moderation_settings(guild_id, ai_profanity_filter_enabled=new_state)
        return new_state
    
    async def set_profanity_action(self, guild_id: int, action: str) -> bool:
        """Set action to take when profanity is detected"""
        valid_actions = ["delete", "warn", "mute", "kick", "ban"]
        if action not in valid_actions:
            return False
        await self.update_moderation_settings(guild_id, profanity_action=action)
        return True


class LoggingSettingsManager(BaseSettingsManager):
    """Manager for logging-related settings"""
    
    async def get_logging_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get logging settings for a guild"""
        default_settings = {
            "logging_enabled": False,
            "message_logs": False,
            "moderation_logs": False,
            "member_logs": False,
            "channel_logs": False,
            "role_logs": False,
            "voice_logs": False,
            "server_logs": False,
            "log_channel": None,
            "message_log_channel": None,
            "moderation_log_channel": None,
            "member_log_channel": None,
            "voice_log_channel": None,
            "deleted_message_logs": True,
            "edited_message_logs": True,
            "bulk_delete_logs": True,
            "profanity_detection_logs": True,  # New for Sinkaf
            "log_bot_messages": False,
            "log_system_messages": False,
            "ignored_channels": [],
            "ignored_users": []
        }
        
        settings = await self.get_guild_settings(guild_id, "logging_settings")
        return {**default_settings, **settings}
    
    async def update_logging_settings(self, guild_id: int, **kwargs) -> bool:
        """Update logging settings for a guild"""
        return await self.update_guild_settings(guild_id, "logging_settings", kwargs)


class FeatureToggleManager(BaseSettingsManager):
    """Manager for feature toggles"""
    
    async def get_feature_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get feature toggle settings for a guild"""
        default_features = {
            "welcome_system": True,
            "leveling_system": True,
            "starboard_system": False,
            "auto_moderation": True,
            "logging_system": True,
            "ticket_system": True,
            "community_features": True,
            "temp_channels": True,
            "ai_moderation": False,  # New AI-powered moderation
            "fun_commands": True,
            "utility_commands": True,
            "music_system": False,
            "economy_system": False,
            "reaction_roles": True,
            "auto_roles": True,
            "welcome_cards": True,
            "custom_commands": True
        }
        
        settings = await self.get_guild_settings(guild_id, "feature_toggles")
        return {**default_features, **settings}
    
    async def toggle_feature(self, guild_id: int, feature: str) -> bool:
        """Toggle a feature and return new state"""
        settings = await self.get_feature_settings(guild_id)
        new_state = not settings.get(feature, True)
        await self.update_guild_settings(guild_id, "feature_toggles", {feature: new_state})
        return new_state
    
    async def is_feature_enabled(self, guild_id: int, feature: str) -> bool:
        """Check if a feature is enabled"""
        settings = await self.get_feature_settings(guild_id)
        return settings.get(feature, True)


class WelcomeSettingsManager(BaseSettingsManager):
    """Manager for welcome/goodbye system settings"""
    
    async def get_welcome_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get welcome settings for a guild"""
        default_settings = {
            "welcome_enabled": False,
            "goodbye_enabled": False,
            "welcome_channel": None,
            "goodbye_channel": None,
            "welcome_message": "Welcome {mention} to **{server}**! 🎉",
            "goodbye_message": "Goodbye {user}, thanks for being part of **{server}**! 👋",
            "welcome_card_enabled": True,
            "goodbye_card_enabled": True,
            "welcome_card_style": "default",
            "goodbye_card_style": "default",
            "welcome_role": None,
            "auto_role_enabled": False,
            "welcome_dm_enabled": False,
            "welcome_dm_message": "Welcome to **{server}**! Please read the rules and have fun! 🎉",
            "ping_user_on_welcome": True,
            "delete_after_seconds": 0,  # 0 = don't delete
            "embed_color": "#5865F2"
        }
        
        settings = await self.get_guild_settings(guild_id, "welcome_settings")
        return {**default_settings, **settings}
    
    async def update_welcome_settings(self, guild_id: int, **kwargs) -> bool:
        """Update welcome settings for a guild"""
        return await self.update_guild_settings(guild_id, "welcome_settings", kwargs)


class TicketSettingsManager(BaseSettingsManager):
    """Manager for ticket system settings"""
    
    async def get_ticket_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get ticket settings for a guild"""
        default_settings = {
            "ticket_system_enabled": False,
            "ticket_category": None,
            "support_roles": [],
            "ticket_channel": None,
            "max_tickets_per_user": 3,
            "auto_close_after_hours": 24,
            "transcript_enabled": True,
            "transcript_channel": None,
            "welcome_message": "Thank you for creating a ticket! A support member will be with you shortly.",
            "ping_support_on_create": True,
            "require_reason": False,
            "ticket_types": {
                "general": "General Support",
                "technical": "Technical Issue", 
                "report": "Report User/Bug",
                "other": "Other"
            },
            "auto_archive_enabled": True,
            "archive_category": None
        }
        
        settings = await self.get_guild_settings(guild_id, "ticket_settings")
        return {**default_settings, **settings}
    
    async def update_ticket_settings(self, guild_id: int, **kwargs) -> bool:
        """Update ticket settings for a guild"""
        return await self.update_guild_settings(guild_id, "ticket_settings", kwargs)


class StarboardSettingsManager(BaseSettingsManager):
    """Manager for starboard system settings"""
    
    async def get_starboard_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get starboard settings for a guild"""
        default_settings = {
            "starboard_enabled": False,
            "starboard_channel": None,
            "star_threshold": 3,
            "star_emoji": "⭐",
            "self_star_enabled": False,
            "bot_star_enabled": False,
            "nsfw_star_enabled": False,
            "ignored_channels": [],
            "ignored_roles": [],
            "remove_stars_on_delete": True,
            "max_days_old": 7,  # Don't star messages older than this
            "minimum_chars": 10,  # Minimum message length to star
            "embed_color": "#FFD700"
        }
        
        settings = await self.get_guild_settings(guild_id, "starboard_settings")
        return {**default_settings, **settings}
    
    async def update_starboard_settings(self, guild_id: int, **kwargs) -> bool:
        """Update starboard settings for a guild"""
        return await self.update_guild_settings(guild_id, "starboard_settings", kwargs)


# Export all managers
__all__ = [
    'BaseSettingsManager',
    'ModerationSettingsManager', 
    'LoggingSettingsManager',
    'FeatureToggleManager',
    'WelcomeSettingsManager',
    'TicketSettingsManager',
    'StarboardSettingsManager'
]
