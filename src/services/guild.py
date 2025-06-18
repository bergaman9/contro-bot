"""Guild service for business logic."""
from typing import Optional, List, Dict, Any
from .base import BaseService
from ..database.collections import GuildCollection
from ..database.models import Guild
import discord


class GuildService(BaseService):
    """Service for guild-related operations."""
    
    def __init__(self, db):
        """Initialize guild service."""
        super().__init__(db)
        self.guild_collection = GuildCollection(db)
    
    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        """Get guild by ID."""
        try:
            return await self.guild_collection.find_by_guild_id(guild_id)
        except Exception as e:
            self.log_error(f"Error getting guild {guild_id}", exc_info=e)
            return None
    
    async def ensure_guild_exists(self, discord_guild: discord.Guild) -> Guild:
        """Ensure guild exists in database."""
        try:
            return await self.guild_collection.get_or_create(
                guild_id=discord_guild.id,
                name=discord_guild.name
            )
        except Exception as e:
            self.log_error(f"Error ensuring guild exists: {discord_guild.id}", exc_info=e)
            raise
    
    async def update_guild_info(self, discord_guild: discord.Guild) -> bool:
        """Update guild information from Discord."""
        try:
            return await self.guild_collection.update_one(
                filter={'guild_id': discord_guild.id},
                update={'$set': {
                    'name': discord_guild.name,
                    'member_count': discord_guild.member_count,
                    'icon_url': str(discord_guild.icon.url) if discord_guild.icon else None,
                    'owner_id': discord_guild.owner_id
                }}
            )
        except Exception as e:
            self.log_error(f"Error updating guild info: {discord_guild.id}", exc_info=e)
            return False
    
    async def get_prefix(self, guild_id: int) -> str:
        """Get guild prefix."""
        guild = await self.get_guild(guild_id)
        return guild.prefix if guild else '!'
    
    async def set_prefix(self, guild_id: int, prefix: str) -> bool:
        """Set guild prefix."""
        try:
            if len(prefix) > 5:
                raise ValueError("Prefix too long (max 5 characters)")
            
            success = await self.guild_collection.update_prefix(guild_id, prefix)
            if success:
                self.log_info(f"Updated prefix for guild {guild_id} to '{prefix}'")
            return success
        except Exception as e:
            self.log_error(f"Error setting prefix for guild {guild_id}", exc_info=e)
            return False
    
    async def get_language(self, guild_id: int) -> str:
        """Get guild language."""
        guild = await self.get_guild(guild_id)
        return guild.language if guild else 'en'
    
    async def set_language(self, guild_id: int, language: str) -> bool:
        """Set guild language."""
        try:
            if language not in ['en', 'tr']:  # Add more languages as needed
                raise ValueError(f"Unsupported language: {language}")
            
            return await self.guild_collection.update_language(guild_id, language)
        except Exception as e:
            self.log_error(f"Error setting language for guild {guild_id}", exc_info=e)
            return False
    
    async def get_setting(self, guild_id: int, key: str, default: Any = None) -> Any:
        """Get a guild setting."""
        guild = await self.get_guild(guild_id)
        return guild.get_setting(key, default) if guild else default
    
    async def set_setting(self, guild_id: int, key: str, value: Any) -> bool:
        """Set a guild setting."""
        try:
            return await self.guild_collection.update_setting(guild_id, key, value)
        except Exception as e:
            self.log_error(f"Error setting {key} for guild {guild_id}", exc_info=e)
            return False
    
    async def has_feature(self, guild_id: int, feature: str) -> bool:
        """Check if guild has a feature."""
        guild = await self.get_guild(guild_id)
        return guild.has_feature(feature) if guild else False
    
    async def add_feature(self, guild_id: int, feature: str) -> bool:
        """Add a feature to guild."""
        try:
            return await self.guild_collection.add_feature(guild_id, feature)
        except Exception as e:
            self.log_error(f"Error adding feature {feature} to guild {guild_id}", exc_info=e)
            return False
    
    async def remove_feature(self, guild_id: int, feature: str) -> bool:
        """Remove a feature from guild."""
        try:
            return await self.guild_collection.remove_feature(guild_id, feature)
        except Exception as e:
            self.log_error(f"Error removing feature {feature} from guild {guild_id}", exc_info=e)
            return False
    
    async def get_active_guilds(self, days: int = 30) -> List[Guild]:
        """Get recently active guilds."""
        try:
            return await self.guild_collection.get_active_guilds(days)
        except Exception as e:
            self.log_error("Error getting active guilds", exc_info=e)
            return []
    
    async def get_stats(self) -> Dict[str, int]:
        """Get guild statistics."""
        try:
            total = await self.guild_collection.count()
            active = len(await self.get_active_guilds(7))
            
            return {
                'total_guilds': total,
                'active_guilds_week': active,
                'inactive_guilds': total - active
            }
        except Exception as e:
            self.log_error("Error getting guild stats", exc_info=e)
            return {
                'total_guilds': 0,
                'active_guilds_week': 0,
                'inactive_guilds': 0
            } 