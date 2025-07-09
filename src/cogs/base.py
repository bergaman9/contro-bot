"""
Base cog class for Contro Discord Bot
Provides access to application manager and common functionality for all cogs
"""

import discord
from discord.ext import commands
from typing import Optional, Any
import logging
import asyncio
from datetime import datetime

from src.utils.database.connection import get_async_db
from ..utils.common.errors import BotError
from ..core.application import get_application_manager
from ..core.logger import get_logger, LoggerMixin


class BaseCog(commands.Cog, LoggerMixin):
    """Base cog class with application manager integration."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.app_manager = None
        self._ready = asyncio.Event()
        # Note: logger is provided by LoggerMixin as a property
        
    @property
    def async_db(self):
        return getattr(self.bot, 'async_db', None)
    
    @property
    def sync_db(self):
        return getattr(self.bot, 'sync_db', None)
        
    async def cog_load(self):
        """Called when the cog is loaded."""
        self.logger.info(f"{self.__class__.__name__} cog loaded")
        # Initialize database connection from bot instance
        if hasattr(self.bot, 'async_db'):
            self._db = self.bot.async_db
        else:
            # Ensure async database is initialized
            from ..utils.database.connection import ensure_async_db
            self._db = await ensure_async_db()
        self._ready.set()
        
        # Get application manager
        self.app_manager = await get_application_manager()
        self.logger.info(f"Loaded cog: {self.__class__.__name__}")
        
    async def cog_unload(self):
        """Called when the cog is unloaded."""
        self.logger.info(f"{self.__class__.__name__} cog unloaded")
        self._ready.clear()
        
    async def cog_before_invoke(self, ctx: commands.Context):
        """Called before any command in this cog."""
        await self._ready.wait()  # Wait for cog to be ready
        self.logger.debug(
            f"Command {ctx.command.name} invoked by {ctx.author} "
            f"in {ctx.guild.name if ctx.guild else 'DM'}"
        )
        
    async def cog_after_invoke(self, ctx: commands.Context):
        """Called after any command in this cog."""
        # Track command usage if needed
        pass
        
    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        """Handle cog-specific errors."""
        # Log the error
        self.logger.error(
            f"Error in command {ctx.command.name}: {type(error).__name__}: {error}",
            exc_info=error
        )
        
        # Handle specific error types
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                ephemeral=True
            )
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                "❌ I don't have the required permissions to execute this command.",
                ephemeral=True
            )
        elif isinstance(error, BotError):
            # Custom bot errors
            await ctx.send(f"❌ {str(error)}", ephemeral=True)
        else:
            # Generic error
            await ctx.send(
                "❌ An error occurred while executing this command.",
                ephemeral=True
            )
    
    @property
    def db(self):
        """Get database connection."""
        if not self._db:
            raise RuntimeError("Database not initialized. Wait for cog_load.")
        return self._db
    
    def get_guild_prefix(self, guild_id: int) -> str:
        """Get the prefix for a specific guild."""
        # This would typically fetch from database
        # For now, return default
        return self.bot.command_prefix or ">"
    
    # Convenience methods for accessing application services
    def get_database(self):
        """Get database manager from application manager."""
        if self.app_manager:
            return self.app_manager.get_db_manager()
        return None
    
    def get_cache(self):
        """Get cache manager from application manager."""
        if self.app_manager:
            return self.app_manager.get_cache_manager()
        return None
    
    def get_config(self):
        """Get configuration from application manager."""
        if self.app_manager:
            return self.app_manager.get_config()
        return None
    
    def get_bot(self):
        """Get the bot instance."""
        return self.bot
    
    # Common utility methods
    async def log_command(self, ctx: commands.Context, command_name: str, **kwargs):
        """Log a command execution."""
        self.logger.info(
            f"Command executed: {command_name}",
            user_id=ctx.author.id,
            guild_id=ctx.guild.id if ctx.guild else None,
            channel_id=ctx.channel.id,
            **kwargs
        )
    
    async def log_error(self, error: Exception, context: str = "", **kwargs):
        """Log an error with context."""
        self.logger.error(
            f"Error in {context}: {str(error)}",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            **kwargs
        )
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled in configuration."""
        config = self.get_config()
        if not config:
            return True  # Default to enabled if no config
        
        feature_attr = f"feature_{feature_name.lower()}"
        return getattr(config.features, feature_name, True)
    
    async def get_guild_settings(self, guild_id: int) -> Optional[dict]:
        """Get guild settings from database."""
        db = self.get_database()
        if not db:
            return None
        
        try:
            collection = db.get_collection("guilds")
            return await collection.find_one({"guild_id": guild_id})
        except Exception as e:
            await self.log_error(e, "get_guild_settings", guild_id=guild_id)
            return None
    
    async def update_guild_settings(self, guild_id: int, settings: dict) -> bool:
        """Update guild settings in database."""
        db = self.get_database()
        if not db:
            return False
        
        try:
            collection = db.get_collection("guilds")
            await collection.update_one(
                {"guild_id": guild_id},
                {"$set": settings},
                upsert=True
            )
            return True
        except Exception as e:
            await self.log_error(e, "update_guild_settings", guild_id=guild_id)
            return False
    
    async def get_user_data(self, user_id: int, guild_id: int) -> Optional[dict]:
        """Get user data from database."""
        db = self.get_database()
        if not db:
            return None
        
        try:
            collection = db.get_collection("users")
            return await collection.find_one({
                "user_id": user_id,
                "guild_id": guild_id
            })
        except Exception as e:
            await self.log_error(e, "get_user_data", user_id=user_id, guild_id=guild_id)
            return None
    
    async def update_user_data(self, user_id: int, guild_id: int, data: dict) -> bool:
        """Update user data in database."""
        db = self.get_database()
        if not db:
            return False
        
        try:
            collection = db.get_collection("users")
            await collection.update_one(
                {
                    "user_id": user_id,
                    "guild_id": guild_id
                },
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            await self.log_error(e, "update_user_data", user_id=user_id, guild_id=guild_id)
            return False
    
    async def cache_get(self, key: str, default=None):
        """Get value from cache."""
        cache = self.get_cache()
        if not cache:
            return default
        
        try:
            return await cache.get(key, default)
        except Exception as e:
            await self.log_error(e, "cache_get", key=key)
            return default
    
    async def cache_set(self, key: str, value, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        cache = self.get_cache()
        if not cache:
            return False
        
        try:
            return await cache.set(key, value, ttl)
        except Exception as e:
            await self.log_error(e, "cache_set", key=key)
            return False
    
    async def cache_delete(self, key: str) -> bool:
        """Delete value from cache."""
        cache = self.get_cache()
        if not cache:
            return False
        
        try:
            return await cache.delete(key)
        except Exception as e:
            await self.log_error(e, "cache_delete", key=key)
            return False


# Decorator for checking if feature is enabled
def require_feature(feature_name: str):
    """Decorator to check if a feature is enabled before executing command."""
    def decorator(func):
        async def wrapper(self, ctx, *args, **kwargs):
            if not self.is_feature_enabled(feature_name):
                await ctx.send(f"❌ The {feature_name} feature is currently disabled.")
                return
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator


# Decorator for logging commands
def log_command(command_name: str = None):
    """Decorator to automatically log command executions."""
    def decorator(func):
        async def wrapper(self, ctx, *args, **kwargs):
            cmd_name = command_name or func.__name__
            await self.log_command(ctx, cmd_name)
            return await func(self, ctx, *args, **kwargs)
        return wrapper
    return decorator 