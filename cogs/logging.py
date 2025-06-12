import asyncio
import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Union

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.database.connection import get_async_db
from utils.core.formatting import calculate_how_long_ago_member_created, calculate_how_long_ago_member_joined, create_embed

# Set up logging
logger = logging.getLogger(__name__)

class CommandSyncManager:
    """Manages command syncing with rate limit handling"""
    
    def __init__(self):
        self.last_sync_time = 0
        self.sync_cooldown = 300  # 5 minutes cooldown between global syncs
        self.sync_in_progress = False
    
    async def try_sync_commands(self, bot, guild_id=None):
        """
        Attempt to sync commands with proper rate limit handling
        
        Args:
            bot: The Discord bot instance
            guild_id: Optional guild ID to sync to only that guild
            
        Returns:
            bool: Whether the sync was successful
        """
        current_time = time.time()
        cooldown_remaining = self.last_sync_time + self.sync_cooldown - current_time
        
        # Check if we're on cooldown for global syncs
        if not guild_id and cooldown_remaining > 0:
            logger.warning(f"Global command sync on cooldown. Try again in {cooldown_remaining:.1f} seconds")
            return False
            
        # Check if sync is already in progress
        if self.sync_in_progress:
            logger.warning("Command sync already in progress")
            return False
            
        try:
            self.sync_in_progress = True
            
            if guild_id:
                # Sync to a specific guild
                guild = bot.get_guild(guild_id)
                if not guild:
                    logger.error(f"Could not find guild with ID {guild_id}")
                    return False
                
                logger.info(f"Syncing commands to guild: {guild.name} ({guild.id})")
                await bot.tree.sync(guild=guild)
            else:
                # Global sync (affects all guilds)
                logger.info("Syncing commands globally")
                await bot.tree.sync()
                
                # Update cooldown timestamp
                self.last_sync_time = time.time()
                
            logger.info("Command sync completed successfully")
            return True
            
        except discord.HTTPException as e:
            logger.error(f"Command sync failed due to Discord API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Command sync failed with unexpected error: {e}", exc_info=True)
            return False
        finally:
            self.sync_in_progress = False


class EventLogger(commands.Cog, name="Events"):
    """
    Logs various Discord events to configured channels
    
    Features include:
    • 📝 Comprehensive event logging
    • 🔧 Configurable log channels for different event types
    • 🔍 Error tracking and diagnostics
    • 🔐 Audit log integration
    """
    
    def __init__(self, bot):
        self.bot = bot
        # Database connection handled via get_async_db() when needed
        self.webhooks = {}  # Store webhooks by guild_id
        self.sync_manager = CommandSyncManager()
        self.rate_limited_events = set()  # Set to track rate-limited events
        
    async def get_or_create_webhook(self, channel):
        """
        Get an existing webhook or create a new one for the channel
        
        Args:
            channel: The Discord channel to get or create a webhook for
            
        Returns:
            The webhook object or None if unsuccessful
        """
        try:
            # Check if we already have a webhook for this guild
            guild_id = channel.guild.id
            if guild_id in self.webhooks:
                try:
                    # Test if the webhook is still valid
                    webhook = self.webhooks[guild_id]
                    return webhook
                except discord.NotFound:
                    # Webhook was deleted, remove from cache
                    del self.webhooks[guild_id]
                except Exception as e:
                    logger.error(f"Error testing existing webhook: {e}")
                    # Fallback to creating a new one
                    
            # Check for existing webhooks in the channel
            existing_webhooks = await channel.webhooks()
            bot_webhooks = [w for w in existing_webhooks if w.user and w.user.id == self.bot.user.id]
            
            if bot_webhooks:
                # Use an existing webhook
                webhook = bot_webhooks[0]
                logger.debug(f"Using existing webhook in {channel.name}")
            else:
                # Create a new webhook
                webhook = await channel.create_webhook(
                    name=f"{self.bot.user.name} Logger",
                    avatar=await self.bot.user.avatar.read(),
                    reason="Created for logging events"
                )
                logger.debug(f"Created new webhook in {channel.name}")
            
            # Cache the webhook for future use
            self.webhooks[guild_id] = webhook
            return webhook
            
        except discord.Forbidden:
            logger.warning(f"Missing permissions to manage webhooks in {channel.name}")
            return None
        except discord.HTTPException as e:
            logger.error(f"HTTP error creating webhook: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_or_create_webhook: {e}", exc_info=True)
            return None
    
    async def send_log(self, channel, embed):
        """
        Send a log message to the specified channel using a webhook
        
        Args:
            channel: The Discord channel to send the log to
            embed: The Discord embed to send
            
        Returns:
            bool: Whether the message was sent successfully
        """
        if not channel or not embed:
            return False
            
        try:
            # Try to get or create a webhook
            webhook = await self.get_or_create_webhook(channel)
            
            if webhook:
                # Send via webhook for cleaner logs without "Bot is typing..." indicators
                await webhook.send(
                    username=f"{self.bot.user.name} Logger",
                    avatar_url=self.bot.user.avatar.url,
                    embed=embed
                )
                return True
            else:
                logger.warning(f"Couldn't send log message to {channel.name} - webhook creation failed")
        except Exception as e:
            logger.error(f"Error sending log message via webhook: {e}")
            # No fallback to channel.send() anymore
    
    async def cleanup_old_webhooks(self, guild_id=None):
        """Clean up old webhooks that are no longer needed"""
        try:
            if guild_id:
                # Clean up for a specific guild
                if guild_id in self.webhooks:
                    try:
                        await self.webhooks[guild_id].delete(reason="Logging channel changed or removed")
                        del self.webhooks[guild_id]
                        logger.info(f"Deleted old webhook for guild {guild_id}")
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                        logger.error(f"Failed to delete webhook for guild {guild_id}: {e}")
                        # If webhook doesn't exist anymore, remove from cache
                        if isinstance(e, discord.NotFound):
                            del self.webhooks[guild_id]
            else:
                # Clean up all webhooks (useful for bot shutdown)
                for guild_id, webhook in list(self.webhooks.items()):
                    try:
                        await webhook.delete(reason="Bot shutting down or restarting")
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        pass
                    del self.webhooks[guild_id]
        except Exception as e:
            logger.error(f"Error in cleanup_old_webhooks: {e}", exc_info=True)

    async def get_log_channel(self, guild_id, event_type=None):
        """
        Get the appropriate logging channel based on event type and settings
        
        Args:
            guild_id: The ID of the guild
            event_type: The type of event (member_events, message_events, etc.)
            
        Returns:
            The channel object or None if not configured
        """
        try:
            # Try to get the settings from the database
            result = self.mongo_db['logger'].find_one({"guild_id": guild_id})
            if not result:
                return None
                
            # Get the main channel ID
            main_channel_id = result.get("channel_id")
            main_channel = None
            
            if main_channel_id:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    main_channel = guild.get_channel(main_channel_id)
            
            # If no event type specified, return main channel
            if not event_type:
                return main_channel
                
            # Check advanced settings for specific channel
            advanced_settings = self.mongo_db['logger_settings'].find_one({"guild_id": guild_id})
            if not advanced_settings:
                return main_channel
                
            # Check if there's a specific channel for this event type
            specific_channel_id = advanced_settings.get(f"{event_type}_channel")
            if specific_channel_id:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    specific_channel = guild.get_channel(specific_channel_id)
                    if specific_channel:
                        logger.debug(f"Using specific channel for {event_type}: {specific_channel.name}")
                        return specific_channel
            
            # Fall back to main channel
            return main_channel
            
        except Exception as e:
            logger.error(f"Error getting log channel: {e}", exc_info=True)
            return None  # Return None instead of leaving the function without a return value

# ... (rest of the code remains the same)
        else:
            await ctx.send(
                embed=create_embed(
                    description="Command sync failed or is on cooldown. Check logs for details.",
                    color=discord.Color.red()
                )
            )

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Global error handler for commands"""
        # Strip the command itself from the error if it's a CommandInvokeError
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
            
        # Handle various error types
        if isinstance(error, commands.CommandNotFound):
            # Don't respond to unknown commands
            return
                
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=create_embed(
                f"Missing required argument: `{error.param.name}`\nUse `{ctx.prefix}help {ctx.command.qualified_name}` for more information.",
                discord.Color.red()
            ), ephemeral=True)
                
        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=create_embed(
                f"Invalid argument: {str(error)}\nUse `{ctx.prefix}help {ctx.command.qualified_name}` for more information.",
                discord.Color.red()
            ), ephemeral=True)
                
        elif isinstance(error, commands.MissingPermissions):
            permissions = ", ".join([f"`{p.replace('_', ' ').title()}`" for p in error.missing_permissions])
            await ctx.send(embed=create_embed(
                f"You need {permissions} permission(s) to use this command.",
                discord.Color.red()
            ), ephemeral=True)
                
        elif isinstance(error, commands.BotMissingPermissions):
            permissions = ", ".join([f"`{p.replace('_', ' ').title()}`" for p in error.missing_permissions])
            await ctx.send(embed=create_embed(
                f"I need {permissions} permission(s) to execute this command.",
                discord.Color.red()
            ), ephemeral=True)
                
        elif isinstance(error, commands.CheckFailure):
            # Generic check failure (could be role checks, etc.)
            await ctx.send(embed=create_embed(
                "You don't have permission to use this command.", 
                discord.Color.red()
            ), ephemeral=True)
            
        elif isinstance(error, commands.CommandOnCooldown):
            # Format cooldown time in a user-friendly way
            seconds = error.retry_after
            if seconds < 60:
                time_format = f"{seconds:.1f} seconds"
            elif seconds < 3600:
                minutes = seconds / 60
                time_format = f"{minutes:.1f} minutes"
            else:
                hours = seconds / 3600
                time_format = f"{hours:.1f} hours"
                
            await ctx.send(embed=create_embed(
                f"Command on cooldown. Try again in {time_format}.",
                discord.Color.gold()
            ), ephemeral=True)
            
        else:
            # For unexpected errors, give a generic message and log the error
            await ctx.send(embed=create_embed(
                "An error occurred while executing the command. Please try again later.",
                discord.Color.red()
            ), ephemeral=True)
            
            # Log detailed error information
            logger.error(
                f"Command error in {ctx.command} invoked by {ctx.author} ({ctx.author.id}): {error}",
                exc_info=error
            )

    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Log command usage"""
        if not ctx.guild:
            return  # Don't log DM commands
            
        # Get the channel to log to
        channel = await self.get_log_channel(ctx.guild.id, "command_events")
        if not channel:
            return
            
        # Create the embed with improved design
        embed = discord.Embed(
            description=f"**Command:** `{ctx.message.content}`",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Add channel information
        embed.add_field(name="Channel", value=f"{ctx.channel.mention}", inline=True)
        embed.add_field(name="User ID", value=f"`{ctx.author.id}`", inline=True)
        
        # Set author to show "xx used a command"
        embed.set_author(
            name=f"{ctx.author.display_name} used a command",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        # Set footer with command ID
        embed.set_footer(text=f"Command ID: {ctx.message.id}")
        
        # Send the log
        await self.send_log(channel, embed)

    # Additional event handlers would go here
    
    async def log_command(self, ctx):
        """Log command usage to database and tracking systems"""
        if not ctx.guild:
            return  # Skip DM commands
            
        try:
            # Log to database
            command_log = {
                "guild_id": ctx.guild.id,
                "user_id": ctx.author.id,
                "channel_id": ctx.channel.id,
                "command": ctx.command.qualified_name if ctx.command else "Unknown",
                "content": ctx.message.content,
                "timestamp": datetime.now()
            }
            
            await self.mongo_db['command_logs'].insert_one(command_log)
            
        except Exception as e:
            logger.error(f"Error logging command to database: {e}")
            
    async def log_command_error(self, ctx, error):
        """Log command errors to dedicated error channel"""
        if not ctx.guild:
            return  # Skip DM commands
            
        # Get error logging channel if configured
        error_channel = await self.get_log_channel(ctx.guild.id, "error_events")
        if not error_channel:
            return
            
        # Format error message
        error_embed = discord.Embed(
            title="Command Error",
            description=f"**Command:** `{ctx.message.content}`",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # Add error details
        error_embed.add_field(name="Error Type", value=type(error).__name__, inline=False)
        error_embed.add_field(name="Error Message", value=str(error), inline=False)
        
        # Add user information
        error_embed.add_field(name="User", value=f"{ctx.author.mention} (`{ctx.author.id}`)")
        error_embed.add_field(name="Channel", value=f"{ctx.channel.mention}")
        
        # Get traceback if available
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        if len(tb) > 1000:
            tb = tb[:997] + "..."
        error_embed.add_field(name="Traceback", value=f"```py\n{tb}\n```", inline=False)
        
        # Set author with user's avatar
        error_embed.set_author(
            name=str(ctx.author),
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        # Send the log
        await self.send_log(error_channel, error_embed)
        
    def cog_unload(self):
        # This is called when the cog is unloaded
        # We need to ensure all webhooks are properly handled during bot shutdown
        asyncio.create_task(self.cleanup_old_webhooks())
        
    @commands.group(name="loggings", description="Configure logging settings")
    @commands.has_permissions(manage_guild=True)
    async def loggings(self, ctx):
        """Main command group for logging settings"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="📝 Logging Settings",
                description="Configure logging settings using the following subcommands:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📊 Subcommands",
                value=(
                    "`/loggings panel` - Show logging settings panel\n"
                    "`/loggings channel <channel>` - Set main logging channel\n"
                    "`/loggings toggle <setting> <value>` - Enable/disable specific logging settings\n"
                    "`/loggings view` - Show current logging settings\n"
                    "`/loggings reset` - Reset all logging settings"
                ),
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ Tip",
                value="For easier configuration, use `/loggings panel` to open the visual interface.",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    @loggings.command(name="panel", description="Show logging settings panel")
    @commands.has_permissions(manage_guild=True)
    async def loggings_panel(self, ctx):
        """Show logging settings panel"""
        from utils.settings.views import LoggingView
        
        embed = discord.Embed(
            title="📝 Logging Settings",
            description="Configure logging settings for your server.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 Available Options",
            value=(
                "• **Main Log Channel** - Main channel where all logs will be sent\n"
                "• **Advanced Logging** - Special channels for different events\n"
                "• **Audit Log** - Discord audit log integration\n"
                "• **Backup** - Backup log data\n"
                "• **Logged Events** - Choose which events to log\n"
            ),
            inline=False
        )
        
        # Get current log channel setting if available
        log_channel = None
        if self.mongo_db is not None:
            guild_settings = await self.mongo_db['logger'].find_one({"guild_id": ctx.guild.id})
            if guild_settings and "channel_id" in guild_settings:
                channel_id = guild_settings["channel_id"]
                log_channel = ctx.guild.get_channel(channel_id)
        
        status = f"Main Log Channel: {log_channel.mention if log_channel else 'Not configured'}"
        embed.add_field(name="🔧 Current Settings", value=status, inline=False)
        
        # Create logging view with buttons
        view = LoggingView(self.bot, "en")
        
        # Send the embed with the view
        await ctx.send(embed=embed, view=view, ephemeral=True)
    
    @loggings.command(name="channel", description="Set main logging channel")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(channel="Channel where log messages will be sent")
    async def loggings_channel(self, ctx, channel: discord.TextChannel):
        """Set main logging channel"""
        try:
            # Check if the bot has permissions to send messages in the channel
            if not channel.permissions_for(ctx.guild.me).send_messages:
                return await ctx.send(
                    embed=create_embed(f"❌ I don't have permission to send messages in {channel.mention}.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Save to database
            if self.mongo_db is not None:
                await self.mongo_db['logger'].update_one(
                    {"guild_id": ctx.guild.id},
                    {"$set": {"channel_id": channel.id}},
                    upsert=True
                )
                
                await ctx.send(
                    embed=create_embed(f"✅ Main logging channel set to {channel.mention}.", discord.Color.green()),
                    ephemeral=True
                )
            else:
                await ctx.send(
                    embed=create_embed("❌ Database connection could not be established.", discord.Color.red()),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error setting log channel: {e}")
            await ctx.send(
                embed=create_embed(f"❌ An error occurred while setting the log channel: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @loggings.command(name="toggle", description="Enable/disable specific logging settings")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        setting="Setting to change",
        value="New value for the setting (true/false)"
    )
    @app_commands.choices(setting=[
        app_commands.Choice(name="Member Events", value="member_events_enabled"),
        app_commands.Choice(name="Message Events", value="message_events_enabled"),
        app_commands.Choice(name="Server Events", value="server_events_enabled"),
        app_commands.Choice(name="Voice Events", value="voice_events_enabled"),
        app_commands.Choice(name="Command Events", value="command_events_enabled"),
        app_commands.Choice(name="Thread Events", value="thread_events_enabled"),
        app_commands.Choice(name="Activity Events", value="event_events_enabled")
    ])
    async def loggings_toggle(self, ctx, setting: str, value: bool):
        """Enable/disable specific logging settings"""
        try:
            # Save to database
            if self.mongo_db is not None:
                await self.mongo_db['logger'].update_one(
                    {"guild_id": ctx.guild.id},
                    {"$set": {setting: value}},
                    upsert=True
                )
                
                # Get readable setting name
                setting_name = next((choice.name for choice in self.loggings_toggle.app_command.choices["setting"] if choice.value == setting), setting)
                status = "enabled" if value else "disabled"
                
                await ctx.send(
                    embed=create_embed(f"✅ {setting_name} {status}.", discord.Color.green()),
                    ephemeral=True
                )
            else:
                await ctx.send(
                    embed=create_embed("❌ Database connection could not be established.", discord.Color.red()),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error toggling log setting: {e}")
            await ctx.send(
                embed=create_embed(f"❌ An error occurred while changing the setting: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @loggings.command(name="view", description="Show current logging settings")
    @commands.has_permissions(manage_guild=True)
    async def loggings_view(self, ctx):
        """Show current logging settings"""
        try:
            if self.mongo_db is None:
                return await ctx.send(
                    embed=create_embed("❌ Database connection could not be established.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Get current settings
            settings = await self.mongo_db['logger'].find_one({"guild_id": ctx.guild.id}) or {}
            
            # Create embed with current settings
            embed = discord.Embed(
                title="📊 Current Logging Settings",
                description=f"Logging settings for **{ctx.guild.name}**:",
                color=discord.Color.blue()
            )
            
            # Main log channel
            channel_id = settings.get("channel_id")
            channel = ctx.guild.get_channel(channel_id) if channel_id else None
            embed.add_field(
                name="📝 Main Log Channel",
                value=channel.mention if channel else "Not configured",
                inline=False
            )
            
            # Event toggles
            event_settings = [
                ("Member Events", "member_events_enabled"),
                ("Message Events", "message_events_enabled"),
                ("Server Events", "server_events_enabled"),
                ("Voice Events", "voice_events_enabled"),
                ("Command Events", "command_events_enabled"),
                ("Thread Events", "thread_events_enabled"),
                ("Activity Events", "event_events_enabled")
            ]
            
            event_statuses = []
            for name, key in event_settings:
                status = settings.get(key, True)  # Default to True if not set
                emoji = "✅" if status else "❌"
                event_statuses.append(f"{emoji} {name}: **{'Active' if status else 'Disabled'}**")
            
            embed.add_field(
                name="⚙️ Event Settings",
                value="\n".join(event_statuses),
                inline=False
            )
            
            # Advanced channels
            advanced_channels = []
            for name, key in [
                ("Member Events", "member_channel_id"),
                ("Message Events", "message_channel_id"),
                ("Server Events", "server_channel_id"),
                ("Voice Events", "voice_channel_id"),
                ("Command Events", "command_channel_id"),
                ("Thread Events", "thread_channel_id"),
                ("Activity Events", "event_channel_id")
            ]:
                channel_id = settings.get(key)
                if channel_id:
                    channel = ctx.guild.get_channel(channel_id)
                    if channel:
                        advanced_channels.append(f"• {name}: {channel.mention}")
            
            if advanced_channels:
                embed.add_field(
                    name="🔧 Advanced Channel Settings",
                    value="\n".join(advanced_channels),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🔧 Advanced Channel Settings",
                    value="No special channels configured yet.",
                    inline=False
                )
            
            await ctx.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error viewing log settings: {e}")
            await ctx.send(
                embed=create_embed(f"❌ An error occurred while displaying log settings: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @loggings.command(name="reset", description="Reset all logging settings")
    @commands.has_permissions(manage_guild=True)
    async def loggings_reset(self, ctx):
        """Reset all logging settings"""
        try:
            # Create confirmation view
            from utils.settings.logging_views import LoggingConfirmationView
            
            embed = discord.Embed(
                title="⚠️ Reset Logging Settings",
                description="Are you sure you want to reset all logging settings? This action cannot be undone.",
                color=discord.Color.yellow()
            )
            
            view = LoggingConfirmationView(self.bot, ctx.guild)
            await ctx.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in reset confirmation: {e}")
            await ctx.send(
                embed=create_embed(f"❌ An error occurred while creating confirmation view: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(EventLogger(bot))