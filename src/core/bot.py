"""
Main bot class for the Discord bot.

This module provides the core bot functionality with modern Discord.py patterns,
dependency injection, and proper error handling.
"""

import asyncio
import discord
from discord.ext import commands
from typing import Optional, Dict, Any, List, Set
import logging
from datetime import datetime
import signal
import sys

from .config import get_config, is_development, is_debug
from .logger import get_logger, setup_logging, LogContext
from .exceptions import BotException, ConfigurationError
from .database import get_database, close_database
from .cache import get_cache, close_cache


class ControBot(commands.Bot):
    """Main bot class with enhanced functionality."""
    
    def __init__(self, config: Dict[str, Any]):
        # Set up intents
        intents = discord.Intents.default()
        for intent_name in config['discord']['intents']:
            if hasattr(intents, intent_name):
                setattr(intents, intent_name, True)
        
        # Initialize bot
        super().__init__(
            command_prefix=config['discord']['prefix'],
            intents=intents,
            help_command=None,  # Custom help command
            case_insensitive=True,
            strip_after_prefix=True
        )
        
        # Configuration
        self.config = config
        self.start_time = datetime.utcnow()
        
        # Services
        self.services: Dict[str, Any] = {}
        
        # Logging
        self.logger = get_logger("bot")
        
        # Statistics
        self.stats = {
            'commands_executed': 0,
            'messages_processed': 0,
            'errors_handled': 0,
            'start_time': self.start_time
        }
        
        # Set up event handlers
        self._setup_events()
        
        # Set up error handling
        self._setup_error_handling()
    
    def _setup_events(self) -> None:
        """Set up bot event handlers."""
        
        @self.event
        async def on_ready():
            """Called when the bot is ready."""
            self.logger.info(
                f"Bot is ready! Logged in as {self.user}",
                user_id=self.user.id,
                guild_count=len(self.guilds),
                user_count=sum(g.member_count for g in self.guilds)
            )
            
            # Set bot status
            await self._set_status()
            
            # Load services
            await self._load_services()
            
            # Sync commands if in development
            if is_development():
                self.logger.info("Development mode: syncing commands")
                await self._sync_commands()
        
        @self.event
        async def on_guild_join(guild: discord.Guild):
            """Called when the bot joins a guild."""
            self.logger.info(
                f"Joined guild: {guild.name}",
                guild_id=guild.id,
                guild_name=guild.name,
                member_count=guild.member_count
            )
            
            # Initialize guild data
            await self._initialize_guild(guild)
        
        @self.event
        async def on_guild_remove(guild: discord.Guild):
            """Called when the bot leaves a guild."""
            self.logger.info(
                f"Left guild: {guild.name}",
                guild_id=guild.id,
                guild_name=guild.name
            )
            
            # Clean up guild data
            await self._cleanup_guild(guild)
        
        @self.event
        async def on_command(ctx: commands.Context):
            """Called when a command is executed."""
            self.stats['commands_executed'] += 1
            
            with LogContext(
                request_id_val=f"cmd_{ctx.message.id}",
                user_id_val=ctx.author.id,
                guild_id_val=ctx.guild.id if ctx.guild else None
            ):
                self.logger.info(
                    f"Command executed: {ctx.command.name}",
                    command=ctx.command.name,
                    user_id=ctx.author.id,
                    guild_id=ctx.guild.id if ctx.guild else None,
                    channel_id=ctx.channel.id
                )
        
        @self.event
        async def on_command_error(ctx: commands.Context, error: Exception):
            """Called when a command raises an error."""
            self.stats['errors_handled'] += 1
            
            with LogContext(
                request_id_val=f"cmd_{ctx.message.id}",
                user_id_val=ctx.author.id,
                guild_id_val=ctx.guild.id if ctx.guild else None
            ):
                self.logger.error(
                    f"Command error: {ctx.command.name if ctx.command else 'Unknown'}",
                    error=str(error),
                    error_type=type(error).__name__,
                    user_id=ctx.author.id,
                    guild_id=ctx.guild.id if ctx.guild else None
                )
                
                # Handle specific error types
                await self._handle_command_error(ctx, error)
        
        @self.event
        async def on_interaction(interaction: discord.Interaction):
            """Called when an interaction is received."""
            with LogContext(
                request_id_val=f"interaction_{interaction.id}",
                user_id_val=interaction.user.id,
                guild_id_val=interaction.guild_id
            ):
                self.logger.debug(
                    f"Interaction received: {interaction.type}",
                    interaction_type=interaction.type,
                    user_id=interaction.user.id,
                    guild_id=interaction.guild_id
                )
        
        @self.event
        async def on_interaction_error(interaction: discord.Interaction, error: Exception):
            """Called when an interaction raises an error."""
            self.stats['errors_handled'] += 1
            
            with LogContext(
                request_id_val=f"interaction_{interaction.id}",
                user_id_val=interaction.user.id,
                guild_id_val=interaction.guild_id
            ):
                self.logger.error(
                    f"Interaction error: {interaction.type}",
                    error=str(error),
                    error_type=type(error).__name__,
                    user_id=interaction.user.id,
                    guild_id=interaction.guild_id
                )
                
                # Handle interaction errors
                await self._handle_interaction_error(interaction, error)
    
    def _setup_error_handling(self) -> None:
        """Set up global error handling."""
        
        async def on_error(event: str, *args, **kwargs):
            """Global error handler."""
            self.stats['errors_handled'] += 1
            self.logger.error(f"Global error in event {event}", exc_info=True)
        
        self.add_listener(on_error)
    
    async def _set_status(self) -> None:
        """Set the bot's status."""
        try:
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | {self.config['discord']['prefix']}help"
            )
            await self.change_presence(activity=activity)
            
            self.logger.info("Bot status set successfully")
            
        except Exception as e:
            self.logger.error("Failed to set bot status", error=str(e))
    
    async def _load_services(self) -> None:
        """Load all services."""
        try:
            # Import and initialize services
            from ..services.guild_service import GuildService
            from ..services.user_service import UserService
            from ..services.giveaway_service import GiveawayService
            from ..services.moderation_service import ModerationService
            
            # Get dependencies
            database = await get_database()
            cache = await get_cache()
            
            # Initialize services
            self.services['guild'] = GuildService(database, cache)
            self.services['user'] = UserService(database, cache)
            self.services['giveaway'] = GiveawayService(database, cache)
            self.services['moderation'] = ModerationService(database, cache)
            
            self.logger.info("All services loaded successfully")
            
        except Exception as e:
            self.logger.error("Failed to load services", error=str(e))
            raise BotException("Failed to load services", {"error": str(e)})
    
    async def _sync_commands(self) -> None:
        """Sync slash commands with Discord."""
        try:
            if is_development():
                # Sync to test guilds only in development
                for guild_id in self.config['discord']['test_guilds']:
                    guild = self.get_guild(guild_id)
                    if guild:
                        self.tree.copy_global_to(guild=guild)
                        await self.tree.sync(guild=guild)
                        self.logger.info(f"Synced commands to test guild: {guild.name}")
            else:
                # Sync globally in production
                await self.tree.sync()
                self.logger.info("Synced commands globally")
                
        except Exception as e:
            self.logger.error("Failed to sync commands", error=str(e))
    
    async def _initialize_guild(self, guild: discord.Guild) -> None:
        """Initialize data for a new guild."""
        try:
            if 'guild' in self.services:
                await self.services['guild'].initialize_guild(guild.id, {
                    'name': guild.name,
                    'member_count': guild.member_count,
                    'owner_id': guild.owner_id,
                    'joined_at': datetime.utcnow().isoformat()
                })
                
            self.logger.info(f"Initialized guild: {guild.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize guild {guild.name}", error=str(e))
    
    async def _cleanup_guild(self, guild: discord.Guild) -> None:
        """Clean up data for a guild that was left."""
        try:
            if 'guild' in self.services:
                await self.services['guild'].cleanup_guild(guild.id)
                
            self.logger.info(f"Cleaned up guild: {guild.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup guild {guild.name}", error=str(e))
    
    async def _handle_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Handle command errors."""
        try:
            if isinstance(error, commands.CommandNotFound):
                # Ignore command not found errors
                return
            
            elif isinstance(error, commands.MissingPermissions):
                await ctx.send("❌ You don't have permission to use this command.")
                
            elif isinstance(error, commands.BotMissingPermissions):
                await ctx.send("❌ I don't have the required permissions to execute this command.")
                
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
                
            elif isinstance(error, commands.BadArgument):
                await ctx.send("❌ Invalid argument provided.")
                
            elif isinstance(error, commands.CommandOnCooldown):
                await ctx.send(f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f} seconds.")
                
            elif isinstance(error, commands.MaxConcurrencyReached):
                await ctx.send("⚠️ This command is already running. Please wait for it to finish.")
                
            else:
                # Log unexpected errors
                self.logger.exception("Unexpected command error")
                
                if is_debug():
                    await ctx.send(f"❌ An error occurred: {str(error)}")
                else:
                    await ctx.send("❌ An unexpected error occurred. Please try again later.")
                    
        except Exception as e:
            self.logger.error("Error in command error handler", error=str(e))
    
    async def _handle_interaction_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Handle interaction errors."""
        try:
            if isinstance(error, discord.app_commands.CommandOnCooldown):
                await interaction.response.send_message(
                    f"⏰ This command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                    ephemeral=True
                )
                
            elif isinstance(error, discord.app_commands.MissingPermissions):
                await interaction.response.send_message(
                    "❌ You don't have permission to use this command.",
                    ephemeral=True
                )
                
            elif isinstance(error, discord.app_commands.BotMissingPermissions):
                await interaction.response.send_message(
                    "❌ I don't have the required permissions to execute this command.",
                    ephemeral=True
                )
                
            else:
                # Log unexpected errors
                self.logger.exception("Unexpected interaction error")
                
                if is_debug():
                    await interaction.response.send_message(
                        f"❌ An error occurred: {str(error)}",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "❌ An unexpected error occurred. Please try again later.",
                        ephemeral=True
                    )
                    
        except Exception as e:
            self.logger.error("Error in interaction error handler", error=str(e))
    
    async def load_cog(self, cog_name: str) -> bool:
        """Load a cog by name."""
        try:
            await self.load_extension(f"src.cogs.{cog_name}")
            self.logger.info(f"Loaded cog: {cog_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load cog {cog_name}", error=str(e))
            return False
    
    async def unload_cog(self, cog_name: str) -> bool:
        """Unload a cog by name."""
        try:
            await self.unload_extension(f"src.cogs.{cog_name}")
            self.logger.info(f"Unloaded cog: {cog_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload cog {cog_name}", error=str(e))
            return False
    
    async def reload_cog(self, cog_name: str) -> bool:
        """Reload a cog by name."""
        try:
            await self.reload_extension(f"src.cogs.{cog_name}")
            self.logger.info(f"Reloaded cog: {cog_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reload cog {cog_name}", error=str(e))
            return False
    
    def get_service(self, service_name: str) -> Any:
        """Get a service by name."""
        return self.services.get(service_name)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        uptime = datetime.utcnow() - self.start_time
        
        return {
            'uptime_seconds': uptime.total_seconds(),
            'uptime_formatted': str(uptime).split('.')[0],
            'guild_count': len(self.guilds),
            'user_count': sum(g.member_count for g in self.guilds),
            'commands_executed': self.stats['commands_executed'],
            'messages_processed': self.stats['messages_processed'],
            'errors_handled': self.stats['errors_handled'],
            'start_time': self.start_time.isoformat()
        }
    
    async def cleanup(self) -> None:
        """Clean up bot resources."""
        self.logger.info("Cleaning up bot resources")
        
        try:
            # Close database connection
            await close_database()
            
            # Close cache connection
            await close_cache()
            
            # Close bot connection
            await self.close()
            
            self.logger.info("Bot cleanup completed")
            
        except Exception as e:
            self.logger.error("Error during bot cleanup", error=str(e))


async def create_bot(config: Optional[Dict[str, Any]] = None) -> ControBot:
    """Create and configure a bot instance."""
    if config is None:
        config = get_config().dict()
    
    # Set up logging
    setup_logging(config.get('logging', {}))
    
    # Create bot instance
    bot = ControBot(config)
    
    return bot


async def run_bot(config: Optional[Dict[str, Any]] = None) -> None:
    """Run the bot with proper error handling and cleanup."""
    bot = None
    
    try:
        # Create bot
        bot = await create_bot(config)
        
        # Set up signal handlers
        def signal_handler(signum, frame):
            """Handle shutdown signals."""
            if bot:
                asyncio.create_task(bot.cleanup())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the bot
        config_obj = get_config()
        await bot.start(config_obj.discord.token)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error running bot: {e}")
        if bot:
            await bot.cleanup()
    finally:
        if bot:
            await bot.cleanup() 