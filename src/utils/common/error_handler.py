"""
Error handling utilities for the bot.
This module provides centralized error handling for the bot.
"""
import discord
import logging
import traceback
import sys
from discord.ext import commands
from typing import Optional, Union, Dict, Any
from datetime import datetime

from ..helpers.discord import create_embed
from ...bot.constants import Colors, Emojis

# Configure logger
logger = logging.getLogger('error_handler')


class BotError(Exception):
    """Base exception class for all bot errors."""
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(message)
        self.user_message = user_message or message


class ConfigurationError(BotError):
    """Raised when there's a configuration issue."""
    pass


class DatabaseError(BotError):
    """Raised when there's a database operation error."""
    pass


class APIError(BotError):
    """Raised when there's an API related error."""
    pass


class PermissionError(BotError):
    """Raised when there's a permission issue."""
    pass


class ValidationError(BotError):
    """Raised when input validation fails."""
    pass


class ErrorHandler:
    """Centralized error handling for the bot."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._error_webhooks: Dict[int, discord.Webhook] = {}  # Guild ID -> Error webhook
        
    async def setup(self):
        """Set up error handlers."""
        self.bot.tree.on_error = self.on_app_command_error
        
    async def get_error_webhook(self, guild: discord.Guild) -> Optional[discord.Webhook]:
        """Get or create an error logging webhook for a guild."""
        if guild.id in self._error_webhooks:
            return self._error_webhooks[guild.id]
        
        # Try to find an existing webhook
        if guild.me.guild_permissions.manage_webhooks:
            for channel in guild.text_channels:
                if channel.name in ['bot-logs', 'logs', 'errors']:
                    try:
                        webhooks = await channel.webhooks()
                        for webhook in webhooks:
                            if webhook.name == "Contro Error Logger":
                                self._error_webhooks[guild.id] = webhook
                                return webhook
                    except:
                        continue
        
        return None
    
    async def log_error(
        self,
        error: Exception,
        context: Optional[Union[commands.Context, discord.Interaction]] = None,
        extra_info: Optional[Dict[str, Any]] = None
    ):
        """Log an error with full context."""
        # Create error ID for tracking
        error_id = f"{datetime.utcnow().timestamp():.0f}"
        
        # Get basic info
        error_type = type(error).__name__
        error_message = str(error)
        
        # Get context info
        if isinstance(context, commands.Context):
            user = context.author
            guild = context.guild
            channel = context.channel
            command = context.command.name if context.command else "Unknown"
            location = f"Command: {command}"
        elif isinstance(context, discord.Interaction):
            user = context.user
            guild = context.guild
            channel = context.channel
            location = f"Interaction: {context.type.name}"
        else:
            user = guild = channel = None
            location = "Unknown"
        
        # Log to console
        logger.error(
            f"Error ID: {error_id}\n"
            f"Type: {error_type}\n"
            f"Message: {error_message}\n"
            f"Location: {location}\n"
            f"User: {user} ({user.id if user else 'N/A'})\n"
            f"Guild: {guild.name if guild else 'DM'} ({guild.id if guild else 'N/A'})\n"
            f"Channel: {channel.name if channel else 'N/A'} ({channel.id if channel else 'N/A'})\n"
            f"Extra: {extra_info}\n"
            f"Traceback:\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}"
        )
        
        # Try to log to webhook if in guild
        if guild:
            webhook = await self.get_error_webhook(guild)
            if webhook:
                embed = create_embed(
                    title=f"Error: {error_type}",
                    description=f"```{error_message[:1000]}```",
                    color=Colors.ERROR
                )
                embed.add_field(name="Error ID", value=error_id, inline=True)
                embed.add_field(name="Location", value=location, inline=True)
                embed.add_field(name="User", value=f"{user.mention if user else 'N/A'}", inline=True)
                
                if extra_info:
                    for key, value in list(extra_info.items())[:3]:  # Max 3 extra fields
                        embed.add_field(name=key, value=str(value)[:1024], inline=True)
                
                embed.timestamp = datetime.utcnow()
                
                try:
                    await webhook.send(embed=embed, username="Error Logger")
                except:
                    pass  # Fail silently if webhook fails
        
        return error_id
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[Union[commands.Context, discord.Interaction]] = None,
        send_response: bool = True
    ) -> Optional[str]:
        """Handle an error and optionally send a user-friendly response."""
        # Log the error
        error_id = await self.log_error(error, context)
        
        # Don't send response if disabled
        if not send_response or not context:
            return error_id
        
        # Create user-friendly embed
        embed = self.create_error_embed(error, error_id)
        
        # Send response
        try:
            if isinstance(context, commands.Context):
                await context.send(embed=embed)
            elif isinstance(context, discord.Interaction):
                if context.response.is_done():
                    await context.followup.send(embed=embed, ephemeral=True)
                else:
                    await context.response.send_message(embed=embed, ephemeral=True)
        except:
            pass  # Fail silently if we can't send the message
        
        return error_id
    
    def create_error_embed(self, error: Exception, error_id: str) -> discord.Embed:
        """Create a user-friendly error embed."""
        # Determine error type and message
        if isinstance(error, commands.CommandNotFound):
            title = "Command Not Found"
            description = f"The command you tried to use doesn't exist. Use `{self.bot.command_prefix}help` to see available commands."
            color = Colors.WARNING
        elif isinstance(error, commands.MissingRequiredArgument):
            title = "Missing Argument"
            description = f"You're missing a required argument: `{error.param.name}`"
            color = Colors.WARNING
        elif isinstance(error, commands.BadArgument):
            title = "Invalid Argument"
            description = "One of the arguments you provided is invalid."
            color = Colors.WARNING
        elif isinstance(error, commands.MissingPermissions):
            title = "Insufficient Permissions"
            perms = ", ".join(error.missing_permissions)
            description = f"You need the following permissions: `{perms}`"
            color = Colors.ERROR
        elif isinstance(error, commands.BotMissingPermissions):
            title = "Bot Missing Permissions"
            perms = ", ".join(error.missing_permissions)
            description = f"I need the following permissions: `{perms}`"
            color = Colors.ERROR
        elif isinstance(error, commands.CommandOnCooldown):
            title = "Command on Cooldown"
            description = f"Please wait {error.retry_after:.1f} seconds before using this command again."
            color = Colors.WARNING
        elif isinstance(error, BotError):
            title = "Error"
            description = error.user_message or str(error)
            color = Colors.ERROR
        elif isinstance(error, discord.Forbidden):
            title = "Permission Denied"
            description = "I don't have permission to do that."
            color = Colors.ERROR
        elif isinstance(error, discord.HTTPException):
            title = "Discord Error"
            description = "There was an error communicating with Discord. Please try again."
            color = Colors.ERROR
        else:
            title = "Unexpected Error"
            description = "An unexpected error occurred. The developers have been notified."
            color = Colors.ERROR
        
        embed = create_embed(
            title=f"{Emojis.ERROR} {title}",
            description=description,
            color=color
        )
        
        embed.set_footer(text=f"Error ID: {error_id}")
        embed.timestamp = datetime.utcnow()
        
        return embed
    
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError
    ):
        """Handle application command errors."""
        await self.handle_error(error, interaction)
    
    @staticmethod
    def setup_logging(log_level: int = logging.INFO):
        """Set up comprehensive logging for the bot."""
        # Create logs directory if it doesn't exist
        import os
        os.makedirs('logs', exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler with color
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            'logs/bot.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        
        # Error file handler
        error_handler = RotatingFileHandler(
            'logs/errors.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # Formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Apply formatters
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(detailed_formatter)
        error_handler.setFormatter(detailed_formatter)
        
        # Add handlers
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(error_handler)
        
        # Set specific loggers
        logging.getLogger('discord').setLevel(logging.WARNING)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('websockets').setLevel(logging.WARNING)
        logging.getLogger('aiohttp').setLevel(logging.WARNING)
        
        logger.info("Logging system initialized")


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> Optional[ErrorHandler]:
    """Get the global error handler instance."""
    return _error_handler


def setup_error_handler(bot: commands.Bot) -> ErrorHandler:
    """Set up the global error handler."""
    global _error_handler
    _error_handler = ErrorHandler(bot)
    return _error_handler


# Decorator for error handling
def handle_errors(send_response: bool = True):
    """Decorator to automatically handle errors in commands."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Find context in args
                context = None
                for arg in args:
                    if isinstance(arg, (commands.Context, discord.Interaction)):
                        context = arg
                        break
                
                handler = get_error_handler()
                if handler:
                    await handler.handle_error(e, context, send_response)
                else:
                    logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                    raise
        
        return wrapper
    return decorator 