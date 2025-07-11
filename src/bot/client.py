"""
Discord bot client for Contro Discord Bot
Main bot class with Discord.py integration and application manager integration
"""

import asyncio
import discord
from discord.ext import commands
from typing import Optional, Dict, Any
import os
import sys

from src.core.config import get_config
from src.core.logger import get_logger, LoggerMixin
from src.core.application import get_application_manager


class ControBot(commands.Bot, LoggerMixin):
    """Main Discord bot class with application manager integration."""
    
    def __init__(self, config):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        intents.guild_messages = True
        intents.guild_reactions = True
        
        # Handle config parameter (can be dict or config object)
        if hasattr(config, 'get_prefix'):
            # Config object
            prefix = config.get_prefix()
            self.config = config
        else:
            # Dict
            prefix = config.get('get_prefix', None)
            if callable(prefix):
                prefix = prefix()
            else:
                prefix = config.get('discord_prefix', '!')
            self.config = config
        
        # Initialize bot
        super().__init__(
            command_prefix=prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        
        self.app_manager = None
        self.sync_db = None
        self.async_db = None
        
    async def setup_hook(self):
        """Called when the bot is starting up."""
        self.logger.info("Setting up bot...")
        
        try:
            # Get application manager
            self.app_manager = await get_application_manager()
            
            # Set db connections
            self.async_db = self.app_manager.get_db_manager()
            self.sync_db = self.app_manager.get_sync_db_manager()
            
            # Load cogs
            await self.load_cogs()
            
            self.logger.info("Bot setup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup bot: {e}")
            raise
    
    async def load_cogs(self):
        """Load all bot cogs."""
        cogs_dir = os.path.join(os.path.dirname(__file__), '..', 'cogs')
        
        # Files to exclude from loading (these are not cogs)
        exclude_files = {'base.py', '__init__.py'}
        
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py') and filename not in exclude_files:
                cog_name = filename[:-3]
                try:
                    await self.load_extension(f'src.cogs.{cog_name}')
                    self.logger.info(f"Loaded cog: {cog_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load cog {cog_name}: {e}")
        
        # Also load subdirectory cogs
        await self._load_cogs_from_subdirs(cogs_dir)
    
    async def _load_cogs_from_subdirs(self, cogs_dir):
        """Load cogs from subdirectories."""
        for item in os.listdir(cogs_dir):
            item_path = os.path.join(cogs_dir, item)
            if os.path.isdir(item_path) and not item.startswith('__'):
                # Check if directory has __init__.py with setup function
                init_file = os.path.join(item_path, '__init__.py')
                if os.path.exists(init_file):
                    try:
                        await self.load_extension(f'src.cogs.{item}')
                        self.logger.info(f"Loaded cog module: {item}")
                    except Exception as e:
                        self.logger.error(f"Failed to load cog module {item}: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        self.logger.info(f"Bot is ready! Logged in as {self.user}")
        self.logger.info(f"Bot is in {len(self.guilds)} guilds")
        
        # Set bot status based on environment
        if hasattr(self.config, 'environment'):
            environment = self.config.environment
        else:
            environment = 'development'
            
        if environment == 'production':
            # Production status - show website and help
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name="contro.space | /help"
            )
        elif environment == 'development':
            # Development status - show dev mode and prefix
            prefix = self.config.discord_dev_prefix if hasattr(self.config, 'discord_dev_prefix') else '>>'
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"🔧 Dev Mode | {prefix}help"
            )
        else:
            # Default/testing status
            prefix = self.config.discord_prefix if hasattr(self.config, 'discord_prefix') else '>'
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | {prefix}help"
            )
            
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
            return
        
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions to execute this command.")
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
            return
        
        # Log unexpected errors
        self.logger.error(f"Command error in {ctx.command}: {error}")
        await ctx.send("❌ An unexpected error occurred. Please try again later.")
    
    async def close(self):
        """Called when the bot is shutting down."""
        self.logger.info("Shutting down bot...")
        await super().close()
        self.logger.info("Bot shutdown completed")
    
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


async def create_bot(config) -> ControBot:
    """Create a new bot instance."""
    return ControBot(config)


async def run_bot(config):
    """Create and run the bot."""
    bot = await create_bot(config)
    
    try:
        # Use get_discord_token() to get the correct token based on environment
        if hasattr(config, 'get_discord_token'):
            # Config object
            token = config.get_discord_token()
        else:
            # Dict
            token = config.get('discord_token', '')
        await bot.start(token)
    except KeyboardInterrupt:
        bot.logger.info("Received shutdown signal")
    except Exception as e:
        bot.logger.error(f"Bot crashed: {e}")
        raise
    finally:
        await bot.close() 