import asyncio
import logging
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Union

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.database.connection import initialize_mongodb
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
        
    @commands.group(name="loggings", description="Log ayarlarını yapılandırın")
    @commands.has_permissions(manage_guild=True)
    async def loggings(self, ctx):
        """Log ayarları için ana komut grubu"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="📝 Log Ayarları",
                description="Aşağıdaki alt komutlar ile log ayarlarını yapılandırabilirsiniz:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📊 Alt Komutlar",
                value=(
                    "`/loggings panel` - Log ayarları panelini gösterir\n"
                    "`/loggings channel <kanal>` - Ana log kanalını ayarlar\n"
                    "`/loggings toggle <ayar> <değer>` - Belirli log ayarlarını açar/kapatır\n"
                    "`/loggings view` - Mevcut log ayarlarını gösterir\n"
                    "`/loggings reset` - Tüm log ayarlarını sıfırlar"
                ),
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ İpucu",
                value="Daha kolay yapılandırma için `/loggings panel` komutunu kullanarak görsel arayüzü açabilirsiniz.",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    @loggings.command(name="panel", description="Log ayarları panelini gösterir")
    @commands.has_permissions(manage_guild=True)
    async def loggings_panel(self, ctx):
        """Log ayarları panelini gösterir"""
        from utils.settings.logging_views import LoggingSettingsView
        
        embed = discord.Embed(
            title="📝 Log Ayarları",
            description="Sunucunuz için log ayarlarını yapılandırın.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 Mevcut Seçenekler",
            value=(
                "• **Ana Log Kanalı** - Tüm logların gönderileceği ana kanal\n"
                "• **Gelişmiş Loglama** - Farklı olaylar için özel kanallar\n"
                "• **Denetim Kaydı** - Discord denetim kaydı entegrasyonu\n"
                "• **Yedekleme** - Log verilerinin yedeklenmesi\n"
                "• **Loglanan Olaylar** - Hangi olayların loglanacağını seçin\n"
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
        
        status = f"Ana Log Kanalı: {log_channel.mention if log_channel else 'Ayarlanmamış'}"
        embed.add_field(name="🔧 Mevcut Ayarlar", value=status, inline=False)
        
        # Create logging view with buttons
        view = LoggingSettingsView(self.bot, ctx.guild)
        
        # Send the embed with the view
        await ctx.send(embed=embed, view=view, ephemeral=True)
    
    @loggings.command(name="channel", description="Ana log kanalını ayarlar")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(channel="Log mesajlarının gönderileceği kanal")
    async def loggings_channel(self, ctx, channel: discord.TextChannel):
        """Ana log kanalını ayarlar"""
        try:
            # Check if the bot has permissions to send messages in the channel
            if not channel.permissions_for(ctx.guild.me).send_messages:
                return await ctx.send(
                    embed=create_embed(f"❌ {channel.mention} kanalına mesaj gönderme iznim yok.", discord.Color.red()),
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
                    embed=create_embed(f"✅ Ana log kanalı {channel.mention} olarak ayarlandı.", discord.Color.green()),
                    ephemeral=True
                )
            else:
                await ctx.send(
                    embed=create_embed("❌ Veritabanı bağlantısı kurulamadı.", discord.Color.red()),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error setting log channel: {e}")
            await ctx.send(
                embed=create_embed(f"❌ Log kanalı ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @loggings.command(name="toggle", description="Belirli log ayarlarını açar/kapatır")
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        setting="Değiştirilecek ayar",
        value="Ayarın yeni değeri (true/false)"
    )
    @app_commands.choices(setting=[
        app_commands.Choice(name="Üye Olayları", value="member_events_enabled"),
        app_commands.Choice(name="Mesaj Olayları", value="message_events_enabled"),
        app_commands.Choice(name="Sunucu Olayları", value="server_events_enabled"),
        app_commands.Choice(name="Ses Olayları", value="voice_events_enabled"),
        app_commands.Choice(name="Komut Olayları", value="command_events_enabled"),
        app_commands.Choice(name="Thread Olayları", value="thread_events_enabled"),
        app_commands.Choice(name="Etkinlik Olayları", value="event_events_enabled")
    ])
    async def loggings_toggle(self, ctx, setting: str, value: bool):
        """Belirli log ayarlarını açar/kapatır"""
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
                status = "etkinleştirildi" if value else "devre dışı bırakıldı"
                
                await ctx.send(
                    embed=create_embed(f"✅ {setting_name} {status}.", discord.Color.green()),
                    ephemeral=True
                )
            else:
                await ctx.send(
                    embed=create_embed("❌ Veritabanı bağlantısı kurulamadı.", discord.Color.red()),
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error toggling log setting: {e}")
            await ctx.send(
                embed=create_embed(f"❌ Log ayarı değiştirilirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @loggings.command(name="view", description="Mevcut log ayarlarını gösterir")
    @commands.has_permissions(manage_guild=True)
    async def loggings_view(self, ctx):
        """Mevcut log ayarlarını gösterir"""
        try:
            if self.mongo_db is None:
                return await ctx.send(
                    embed=create_embed("❌ Veritabanı bağlantısı kurulamadı.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Get current settings
            settings = await self.mongo_db['logger'].find_one({"guild_id": ctx.guild.id}) or {}
            
            # Create embed with current settings
            embed = discord.Embed(
                title="📊 Mevcut Log Ayarları",
                description=f"**{ctx.guild.name}** sunucusu için log ayarları:",
                color=discord.Color.blue()
            )
            
            # Main log channel
            channel_id = settings.get("channel_id")
            channel = ctx.guild.get_channel(channel_id) if channel_id else None
            embed.add_field(
                name="📝 Ana Log Kanalı",
                value=channel.mention if channel else "Ayarlanmamış",
                inline=False
            )
            
            # Event toggles
            event_settings = [
                ("Üye Olayları", "member_events_enabled"),
                ("Mesaj Olayları", "message_events_enabled"),
                ("Sunucu Olayları", "server_events_enabled"),
                ("Ses Olayları", "voice_events_enabled"),
                ("Komut Olayları", "command_events_enabled"),
                ("Thread Olayları", "thread_events_enabled"),
                ("Etkinlik Olayları", "event_events_enabled")
            ]
            
            event_statuses = []
            for name, key in event_settings:
                status = settings.get(key, True)  # Default to True if not set
                emoji = "✅" if status else "❌"
                event_statuses.append(f"{emoji} {name}: **{'Aktif' if status else 'Devre dışı'}**")
            
            embed.add_field(
                name="⚙️ Olay Ayarları",
                value="\n".join(event_statuses),
                inline=False
            )
            
            # Advanced channels
            advanced_channels = []
            for name, key in [
                ("Üye Olayları", "member_channel_id"),
                ("Mesaj Olayları", "message_channel_id"),
                ("Sunucu Olayları", "server_channel_id"),
                ("Ses Olayları", "voice_channel_id"),
                ("Komut Olayları", "command_channel_id"),
                ("Thread Olayları", "thread_channel_id"),
                ("Etkinlik Olayları", "event_channel_id")
            ]:
                channel_id = settings.get(key)
                if channel_id:
                    channel = ctx.guild.get_channel(channel_id)
                    if channel:
                        advanced_channels.append(f"• {name}: {channel.mention}")
            
            if advanced_channels:
                embed.add_field(
                    name="🔧 Gelişmiş Kanal Ayarları",
                    value="\n".join(advanced_channels),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🔧 Gelişmiş Kanal Ayarları",
                    value="Henüz özel kanal ayarlanmamış.",
                    inline=False
                )
            
            await ctx.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error viewing log settings: {e}")
            await ctx.send(
                embed=create_embed(f"❌ Log ayarları görüntülenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @loggings.command(name="reset", description="Tüm log ayarlarını sıfırlar")
    @commands.has_permissions(manage_guild=True)
    async def loggings_reset(self, ctx):
        """Tüm log ayarlarını sıfırlar"""
        try:
            # Create confirmation view
            from utils.settings.logging_views import LoggingConfirmationView
            
            embed = discord.Embed(
                title="⚠️ Log Ayarlarını Sıfırla",
                description="Tüm log ayarlarını sıfırlamak istediğinizden emin misiniz? Bu işlem geri alınamaz.",
                color=discord.Color.yellow()
            )
            
            view = LoggingConfirmationView(self.bot, ctx.guild)
            await ctx.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in reset confirmation: {e}")
            await ctx.send(
                embed=create_embed(f"❌ Onay görünümü oluşturulurken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(EventLogger(bot))