import asyncio
import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Union

import discord
from discord import app_commands
from discord.ext import commands, tasks

from src.utils.database.connection import initialize_mongodb
from src.utils.core.formatting import calculate_how_long_ago_member_created, calculate_how_long_ago_member_joined, create_embed

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
        self.mongo_db = initialize_mongodb()
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
            main_channel_id = result.get("default_channel_id") or result.get("channel_id")
            main_channel = None
            
            if main_channel_id:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    main_channel = guild.get_channel(int(main_channel_id))
            
            # If no event type specified, return main channel
            if not event_type:
                return main_channel
                
            # Check for specific channel based on event type
            specific_channel_id = None
            
            # Map event types to channel settings
            channel_mapping = {
                "member_events": result.get("member_channel_id"),
                "message_events": result.get("message_channel_id"),
                "voice_events": result.get("voice_channel_id"),
                "server_events": result.get("server_channel_id"),
                "join_leave_events": result.get("join_leave_channel_id"),
                "moderation_events": result.get("member_channel_id"),  # Moderation events go to member channel
                "command_events": main_channel_id  # Commands go to main channel
            }
            
            specific_channel_id = channel_mapping.get(event_type)
            
            if specific_channel_id:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    specific_channel = guild.get_channel(int(specific_channel_id))
                    if specific_channel:
                        logger.debug(f"Using specific channel for {event_type}: {specific_channel.name}")
                        return specific_channel
            
            # Fall back to main channel
            return main_channel
            
        except Exception as e:
            logger.error(f"Error getting log channel: {e}", exc_info=True)
            return None

    async def should_log_event(self, guild_id, event_name):
        """
        Check if a specific event should be logged based on settings
        
        Args:
            guild_id: The ID of the guild
            event_name: The name of the event to check
            
        Returns:
            bool: Whether the event should be logged
        """
        try:
            settings = await self.get_logging_settings(guild_id)
            if not settings:
                return False
                
            # Check if logging is enabled
            if not settings.get("enabled", False):
                return False
                
            # Check if the specific event is enabled
            events = settings.get("events", {})
            return events.get(event_name, True)  # Default to True if not specified
            
        except Exception as e:
            logger.error(f"Error checking if event should be logged: {e}")
            return False

    async def get_event_channel_type(self, event_name):
        """
        Get the channel type for a specific event
        
        Args:
            event_name: The name of the event
            
        Returns:
            str: The channel type for the event
        """
        # Map events to channel types
        event_channel_mapping = {
            # Message Events
            "message_delete": "message_events",
            "message_edit": "message_events", 
            "message_bulk_delete": "message_events",
            
            # Member Events (general)
            "member_role_update": "member_events",
            "member_name_change": "member_events",
            "member_avatar_change": "member_events",
            "member_ban": "member_events",
            "member_unban": "member_events",
            "member_timeout": "member_events",
            "member_remove_timeout": "member_events",
            
            # Join/Leave Events
            "member_join": "join_leave_events",
            "member_leave": "join_leave_events",
            
            # Voice Events
            "voice_join": "voice_events",
            "voice_leave": "voice_events", 
            "voice_move": "voice_events",
            
            # Server Events
            "channel_create": "server_events",
            "channel_update": "server_events",
            "channel_delete": "server_events",
            "role_create": "server_events",
            "role_update": "server_events",
            "role_delete": "server_events",
            "server_update": "server_events",
            "emoji_change": "server_events",
            
            # Moderation Events
            "moderation_warn": "moderation_events",
            "moderation_kick": "moderation_events",
            "moderation_ban": "moderation_events",
            "moderation_unban": "moderation_events",
            "moderation_timeout": "moderation_events",
            "moderation_remove_timeout": "moderation_events",
            
            # Command Events
            "command_used": "command_events",
            "command_error": "command_events"
        }
        
        return event_channel_mapping.get(event_name, "default")

    async def get_logging_settings(self, guild_id):
        """Get logging settings from database"""
        try:
            result = self.mongo_db['logger'].find_one({"guild_id": guild_id})
            return result
        except Exception as e:
            logger.error(f"Error getting logging settings: {e}")
            return None

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
            
        # Check if this event should be logged
        if not await self.should_log_event(ctx.guild.id, "command_used"):
            return
            
        # Get the channel to log to
        channel_type = await self.get_event_channel_type("command_used")
        channel = await self.get_log_channel(ctx.guild.id, channel_type)
        if not channel:
            return
            
        # Create the embed
        embed = discord.Embed(
            title="Command Used",
            description=f"**Command:** `{ctx.message.content}`",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Add user information
        embed.add_field(name="User", value=f"{ctx.author.mention} (`{ctx.author.id}`)")
        embed.add_field(name="Channel", value=f"{ctx.channel.mention} (`{ctx.channel.id}`)")
        
        # Set author with user's avatar
        embed.set_author(
            name=str(ctx.author),
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        # Set footer with command ID
        embed.set_footer(text=f"Command ID: {ctx.message.id}")
        
        # Send the log
        await self.send_log(channel, embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log when a member joins the server"""
        if not member.guild:
            return
            
        # Check if this event should be logged
        if not await self.should_log_event(member.guild.id, "member_join"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type("member_join")
        channel = await self.get_log_channel(member.guild.id, channel_type)
        if not channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="Member Joined",
            description=f"**{member.mention}** joined the server",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)")
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>")
        embed.add_field(name="Member Count", value=f"{member.guild.member_count}")
        
        embed.set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await self.send_log(channel, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log when a member leaves the server"""
        if not member.guild:
            return
            
        # Check if this event should be logged
        if not await self.should_log_event(member.guild.id, "member_leave"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type("member_leave")
        channel = await self.get_log_channel(member.guild.id, channel_type)
        if not channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="Member Left",
            description=f"**{member.mention}** left the server",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)")
        embed.add_field(name="Joined At", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown")
        embed.add_field(name="Member Count", value=f"{member.guild.member_count}")
        
        embed.set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await self.send_log(channel, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log when a member is updated (nickname, roles, etc.)"""
        if not before.guild:
            return
            
        # Check for nickname changes
        if before.nick != after.nick:
            if await self.should_log_event(before.guild.id, "member_name_change"):
                channel_type = await self.get_event_channel_type("member_name_change")
                channel = await self.get_log_channel(before.guild.id, channel_type)
                if channel:
                    embed = discord.Embed(
                        title="Nickname Changed",
                        description=f"**{after.mention}** changed their nickname",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(name="User", value=f"{after.mention} (`{after.id}`)")
                    embed.add_field(name="Before", value=f"`{before.nick or before.name}`")
                    embed.add_field(name="After", value=f"`{after.nick or after.name}`")
                    
                    embed.set_author(name=str(after), icon_url=after.avatar.url if after.avatar else after.default_avatar.url)
                    
                    await self.send_log(channel, embed)
        
        # Check for role changes
        if before.roles != after.roles:
            if await self.should_log_event(before.guild.id, "member_role_update"):
                channel_type = await self.get_event_channel_type("member_role_update")
                channel = await self.get_log_channel(before.guild.id, channel_type)
                if channel:
                    added_roles = set(after.roles) - set(before.roles)
                    removed_roles = set(before.roles) - set(after.roles)
                    
                    if added_roles or removed_roles:
                        embed = discord.Embed(
                            title="Roles Updated",
                            description=f"**{after.mention}** had their roles updated",
                            color=discord.Color.blue(),
                            timestamp=datetime.now()
                        )
                        
                        embed.add_field(name="User", value=f"{after.mention} (`{after.id}`)")
                        
                        if added_roles:
                            embed.add_field(name="Added Roles", value=", ".join([role.mention for role in added_roles]), inline=False)
                        if removed_roles:
                            embed.add_field(name="Removed Roles", value=", ".join([role.mention for role in removed_roles]), inline=False)
                        
                        embed.set_author(name=str(after), icon_url=after.avatar.url if after.avatar else after.default_avatar.url)
                        
                        await self.send_log(channel, embed)
        
        # Check for avatar changes
        if before.avatar != after.avatar:
            if await self.should_log_event(before.guild.id, "member_avatar_change"):
                channel_type = await self.get_event_channel_type("member_avatar_change")
                channel = await self.get_log_channel(before.guild.id, channel_type)
                if channel:
                    embed = discord.Embed(
                        title="Avatar Changed",
                        description=f"**{after.mention}** changed their avatar",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(name="User", value=f"{after.mention} (`{after.id}`)")
                    embed.set_author(name=str(after), icon_url=after.avatar.url if after.avatar else after.default_avatar.url)
                    embed.set_thumbnail(url=after.avatar.url if after.avatar else after.default_avatar.url)
                    
                    await self.send_log(channel, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Log when a member is banned"""
        if not guild:
            return
            
        # Check if this event should be logged
        if not await self.should_log_event(guild.id, "member_ban"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type("member_ban")
        channel = await self.get_log_channel(guild.id, channel_type)
        if not channel:
            return
            
        # Get audit log for ban reason
        reason = "No reason provided"
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
            if entry.target.id == user.id:
                reason = entry.reason or "No reason provided"
                break
        
        # Create embed
        embed = discord.Embed(
            title="Member Banned",
            description=f"**{user.mention}** was banned from the server",
            color=discord.Color.dark_red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="User", value=f"{user.mention} (`{user.id}`)")
        embed.add_field(name="Reason", value=reason)
        
        embed.set_author(name=str(user), icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        
        await self.send_log(channel, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        """Log when a member is unbanned"""
        if not guild:
            return
            
        # Check if this event should be logged
        if not await self.should_log_event(guild.id, "member_unban"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type("member_unban")
        channel = await self.get_log_channel(guild.id, channel_type)
        if not channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="Member Unbanned",
            description=f"**{user.mention}** was unbanned from the server",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="User", value=f"{user.mention} (`{user.id}`)")
        
        embed.set_author(name=str(user), icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        
        await self.send_log(channel, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log when a message is deleted"""
        if not message.guild or message.author.bot:
            return
            
        # Check if this event should be logged
        if not await self.should_log_event(message.guild.id, "message_delete"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type("message_delete")
        channel = await self.get_log_channel(message.guild.id, channel_type)
        if not channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="Message Deleted",
            description=f"**Message deleted in {message.channel.mention}**",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)")
        embed.add_field(name="Channel", value=f"{message.channel.mention}")
        
        if message.content:
            content = message.content[:1024] + "..." if len(message.content) > 1024 else message.content
            embed.add_field(name="Content", value=content, inline=False)
        
        embed.set_author(name=str(message.author), icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        
        await self.send_log(channel, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log when a message is edited"""
        if not before.guild or before.author.bot or before.content == after.content:
            return
            
        # Check if this event should be logged
        if not await self.should_log_event(before.guild.id, "message_edit"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type("message_edit")
        channel = await self.get_log_channel(before.guild.id, channel_type)
        if not channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="Message Edited",
            description=f"**Message edited in {before.channel.mention}**\n[Jump to Message]({after.jump_url})",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Author", value=f"{before.author.mention} (`{before.author.id}`)")
        embed.add_field(name="Channel", value=f"{before.channel.mention}")
        
        before_content = before.content[:512] + "..." if len(before.content) > 512 else before.content
        after_content = after.content[:512] + "..." if len(after.content) > 512 else after.content
        
        embed.add_field(name="Before", value=f"```{before_content}```", inline=False)
        embed.add_field(name="After", value=f"```{after_content}```", inline=False)
        
        embed.set_author(name=str(before.author), icon_url=before.author.avatar.url if before.author.avatar else before.author.default_avatar.url)
        
        await self.send_log(channel, embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        """Log when messages are bulk deleted"""
        if not messages or not messages[0].guild:
            return
            
        guild = messages[0].guild
        
        # Check if this event should be logged
        if not await self.should_log_event(guild.id, "message_bulk_delete"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type("message_bulk_delete")
        channel = await self.get_log_channel(guild.id, channel_type)
        if not channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="Bulk Message Delete",
            description=f"**{len(messages)} messages deleted in {messages[0].channel.mention}**",
            color=discord.Color.dark_red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Channel", value=f"{messages[0].channel.mention}")
        embed.add_field(name="Message Count", value=str(len(messages)))
        
        # Count unique authors
        authors = set(msg.author for msg in messages if not msg.author.bot)
        embed.add_field(name="Affected Users", value=str(len(authors)))
        
        await self.send_log(channel, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Log voice channel events"""
        if not member.guild:
            return
            
        # Voice join
        if not before.channel and after.channel:
            if await self.should_log_event(member.guild.id, "voice_join"):
                channel_type = await self.get_event_channel_type("voice_join")
                channel = await self.get_log_channel(member.guild.id, channel_type)
                if channel:
                    embed = discord.Embed(
                        title="Voice Join",
                        description=f"**{member.mention}** joined voice channel {after.channel.mention}",
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)")
                    embed.add_field(name="Channel", value=f"{after.channel.mention}")
                    
                    embed.set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
                    
                    await self.send_log(channel, embed)
        
        # Voice leave
        elif before.channel and not after.channel:
            if await self.should_log_event(member.guild.id, "voice_leave"):
                channel_type = await self.get_event_channel_type("voice_leave")
                channel = await self.get_log_channel(member.guild.id, channel_type)
                if channel:
                    embed = discord.Embed(
                        title="Voice Leave",
                        description=f"**{member.mention}** left voice channel {before.channel.mention}",
                        color=discord.Color.red(),
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)")
                    embed.add_field(name="Channel", value=f"{before.channel.mention}")
                    
                    embed.set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
                    
                    await self.send_log(channel, embed)
        
        # Voice move
        elif before.channel and after.channel and before.channel != after.channel:
            if await self.should_log_event(member.guild.id, "voice_move"):
                channel_type = await self.get_event_channel_type("voice_move")
                channel = await self.get_log_channel(member.guild.id, channel_type)
                if channel:
                    embed = discord.Embed(
                        title="Voice Move",
                        description=f"**{member.mention}** moved from {before.channel.mention} to {after.channel.mention}",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)")
                    embed.add_field(name="From", value=f"{before.channel.mention}")
                    embed.add_field(name="To", value=f"{after.channel.mention}")
                    
                    embed.set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
                    
                    await self.send_log(channel, embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Log when a channel is created"""
        if not channel.guild:
            return
            
        # Check if this event should be logged
        if not await self.should_log_event(channel.guild.id, "channel_create"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type("channel_create")
        log_channel = await self.get_log_channel(channel.guild.id, channel_type)
        if not log_channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="Channel Created",
            description=f"**{channel.mention}** was created",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Channel", value=f"{channel.mention} (`{channel.id}`)")
        embed.add_field(name="Type", value=channel.type.name.title())
        
        if hasattr(channel, 'category'):
            embed.add_field(name="Category", value=channel.category.name if channel.category else "None")
        
        await self.send_log(log_channel, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Log when a channel is deleted"""
        if not channel.guild:
            return
            
        # Check if this event should be logged
        if not await self.should_log_event(channel.guild.id, "channel_delete"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type("channel_delete")
        log_channel = await self.get_log_channel(channel.guild.id, channel_type)
        if not log_channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="Channel Deleted",
            description=f"**#{channel.name}** was deleted",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Channel Name", value=f"#{channel.name}")
        embed.add_field(name="Type", value=channel.type.name.title())
        
        if hasattr(channel, 'category'):
            embed.add_field(name="Category", value=channel.category.name if channel.category else "None")
        
        await self.send_log(log_channel, embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Log when a role is created"""
        if not role.guild:
            return
            
        # Check if this event should be logged
        if not await self.should_log_event(role.guild.id, "role_create"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type("role_create")
        log_channel = await self.get_log_channel(role.guild.id, channel_type)
        if not log_channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="Role Created",
            description=f"**{role.mention}** was created",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Role", value=f"{role.mention} (`{role.id}`)")
        embed.add_field(name="Color", value=str(role.color))
        embed.add_field(name="Position", value=str(role.position))
        
        await self.send_log(log_channel, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Log when a role is deleted"""
        if not role.guild:
            return
            
        # Check if this event should be logged
        if not await self.should_log_event(role.guild.id, "role_delete"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type("role_delete")
        log_channel = await self.get_log_channel(role.guild.id, channel_type)
        if not log_channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title="Role Deleted",
            description=f"**{role.name}** was deleted",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Role Name", value=role.name)
        embed.add_field(name="Color", value=str(role.color))
        embed.add_field(name="Position", value=str(role.position))
        
        await self.send_log(log_channel, embed)
        
    def cog_unload(self):
        # This is called when the cog is unloaded
        # We need to ensure all webhooks are properly handled during bot shutdown
        asyncio.create_task(self.cleanup_old_webhooks())

    # Moderation command handlers
    async def log_moderation_action(self, guild_id, action_type, target_user, moderator, reason=None, duration=None):
        """Log moderation actions"""
        if not guild_id:
            return
            
        # Check if this event should be logged
        if not await self.should_log_event(guild_id, f"moderation_{action_type}"):
            return
            
        # Get the appropriate channel
        channel_type = await self.get_event_channel_type(f"moderation_{action_type}")
        channel = await self.get_log_channel(guild_id, channel_type)
        if not channel:
            return
            
        # Create embed
        embed = discord.Embed(
            title=f"Member {action_type.title()}",
            description=f"**{target_user.mention}** was {action_type}",
            color=self.get_moderation_color(action_type),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="User", value=f"{target_user.mention} (`{target_user.id}`)")
        embed.add_field(name="Moderator", value=f"{moderator.mention} (`{moderator.id}`)")
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        
        if duration:
            embed.add_field(name="Duration", value=duration, inline=False)
        
        embed.set_author(name=str(moderator), icon_url=moderator.avatar.url if moderator.avatar else moderator.default_avatar.url)
        embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else target_user.default_avatar.url)
        
        await self.send_log(channel, embed)

    def get_moderation_color(self, action_type):
        """Get color for moderation action"""
        colors = {
            'warn': discord.Color.yellow(),
            'kick': discord.Color.orange(),
            'ban': discord.Color.dark_red(),
            'unban': discord.Color.green(),
            'timeout': discord.Color.red(),
            'remove_timeout': discord.Color.green()
        }
        return colors.get(action_type, discord.Color.blue())

    @commands.command(name="testlog")
    @commands.has_permissions(manage_guild=True)
    async def test_logging(self, ctx):
        """Test the logging system by sending a test log message"""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
            
        # Check if logging is enabled
        settings = await self.get_logging_settings(ctx.guild.id)
        if not settings or not settings.get("enabled", False):
            await ctx.send("❌ Logging is not enabled for this server.")
            return
            
        # Get the default channel
        channel = await self.get_log_channel(ctx.guild.id)
        if not channel:
            await ctx.send("❌ No logging channel configured.")
            return
            
        # Create test embed
        embed = discord.Embed(
            title="🧪 Logging System Test",
            description="This is a test message to verify the logging system is working correctly.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Tester", value=f"{ctx.author.mention} (`{ctx.author.id}`)")
        embed.add_field(name="Channel", value=f"{channel.mention}")
        embed.add_field(name="Server", value=f"{ctx.guild.name}")
        
        # Add settings info
        events = settings.get("events", {})
        enabled_events = sum(1 for enabled in events.values() if enabled)
        total_events = len(events)
        
        embed.add_field(name="Enabled Events", value=f"{enabled_events}/{total_events}", inline=False)
        
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_footer(text="Logging System Test")
        
        try:
            await self.send_log(channel, embed)
            await ctx.send(f"✅ Test log message sent to {channel.mention}")
        except Exception as e:
            await ctx.send(f"❌ Failed to send test log: {e}")
            logger.error(f"Test log failed: {e}")

    @commands.command(name="logstatus")
    @commands.has_permissions(manage_guild=True)
    async def log_status(self, ctx):
        """Show the current logging status and settings"""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
            
        settings = await self.get_logging_settings(ctx.guild.id)
        if not settings:
            await ctx.send("❌ No logging settings found for this server.")
            return
            
        embed = discord.Embed(
            title="📊 Logging System Status",
            description=f"Current logging configuration for **{ctx.guild.name}**",
            color=discord.Color.green() if settings.get("enabled", False) else discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # Basic status
        embed.add_field(name="Status", value="✅ Enabled" if settings.get("enabled", False) else "❌ Disabled", inline=True)
        
        # Channels
        channels_info = []
        if settings.get("default_channel_id"):
            default_channel = ctx.guild.get_channel(int(settings["default_channel_id"]))
            channels_info.append(f"**Default:** {default_channel.mention if default_channel else '❌ Not found'}")
        
        if settings.get("member_channel_id"):
            member_channel = ctx.guild.get_channel(int(settings["member_channel_id"]))
            channels_info.append(f"**Member:** {member_channel.mention if member_channel else '❌ Not found'}")
            
        if settings.get("message_channel_id"):
            message_channel = ctx.guild.get_channel(int(settings["message_channel_id"]))
            channels_info.append(f"**Message:** {message_channel.mention if message_channel else '❌ Not found'}")
            
        if settings.get("voice_channel_id"):
            voice_channel = ctx.guild.get_channel(int(settings["voice_channel_id"]))
            channels_info.append(f"**Voice:** {voice_channel.mention if voice_channel else '❌ Not found'}")
            
        if settings.get("server_channel_id"):
            server_channel = ctx.guild.get_channel(int(settings["server_channel_id"]))
            channels_info.append(f"**Server:** {server_channel.mention if server_channel else '❌ Not found'}")
            
        if settings.get("join_leave_channel_id"):
            join_leave_channel = ctx.guild.get_channel(int(settings["join_leave_channel_id"]))
            channels_info.append(f"**Join/Leave:** {join_leave_channel.mention if join_leave_channel else '❌ Not found'}")
        
        embed.add_field(name="Channels", value="\n".join(channels_info) if channels_info else "No channels configured", inline=False)
        
        # Event statistics
        events = settings.get("events", {})
        if events:
            categories = {
                "Message Events": ["message_delete", "message_edit", "message_bulk_delete"],
                "Member Events": ["member_join", "member_leave", "member_ban", "member_unban", "member_timeout", "member_remove_timeout", "member_role_update", "member_name_change", "member_avatar_change"],
                "Server Events": ["channel_create", "channel_update", "channel_delete", "role_create", "role_update", "role_delete", "server_update", "emoji_change"],
                "Voice Events": ["voice_join", "voice_move", "voice_leave"],
                "Moderation Events": ["moderation_warn", "moderation_kick", "moderation_ban", "moderation_unban", "moderation_timeout", "moderation_remove_timeout"]
            }
            
            event_stats = []
            for category, event_list in categories.items():
                enabled_count = sum(1 for event in event_list if events.get(event, False))
                total_count = len(event_list)
                event_stats.append(f"**{category}:** {enabled_count}/{total_count}")
            
            embed.add_field(name="Event Statistics", value="\n".join(event_stats), inline=False)
        
        embed.set_footer(text=f"Last updated: {settings.get('last_updated', 'Unknown')}")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(EventLogger(bot))