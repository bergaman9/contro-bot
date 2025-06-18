"""Base cog class with common functionality for all cogs."""

from discord.ext import commands
from typing import Optional, Any
import logging
import asyncio
from datetime import datetime

from ..database.connection import get_async_db
from ..utils.common.errors import BotError


class BaseCog(commands.Cog):
    """Base class for all cogs with common functionality."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._db = None
        self._ready = asyncio.Event()
        
    async def cog_load(self):
        """Called when the cog is loaded."""
        self.logger.info(f"{self.__class__.__name__} cog loaded")
        # Initialize database connection
        self._db = await get_async_db()
        self._ready.set()
        
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
    
    async def get_guild_settings(self, guild_id: int) -> dict:
        """Get settings for a specific guild."""
        settings = await self.db.guild_settings.find_one({"guild_id": str(guild_id)})
        return settings or {}
    
    async def update_guild_settings(self, guild_id: int, settings: dict) -> None:
        """Update settings for a specific guild."""
        await self.db.guild_settings.update_one(
            {"guild_id": str(guild_id)},
            {"$set": settings},
            upsert=True
        ) 