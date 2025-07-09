import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
import logging
import os
import asyncio
from datetime import datetime, timedelta
import sys

from src.utils.core.formatting import create_embed
from src.utils.views.settings_views import (
    MainSettingsView,
    ServerSettingsView,
    WelcomeGoodbyeView,
    ModerationView,
    LoggingView,
    TicketSystemView,
    RoleManagementView,
    StarboardView,
    FeatureManagementView,
    LevellingSettingsView,
    PrefixSettingsView,
    StatusRoleSettingsView,
    BirthdaySettingsView,
    AISettingsView,
    LegalInfoView,
    ChannelSelectView,
    AdvancedSettingsView
)
from src.utils.views.ticket_department_views import DepartmentSettingsView
from src.utils.views.logging_views import LoggingSettingsView
from src.utils.views.register_views import RegisterSettingsView
from src.utils.database.connection import get_async_db, initialize_mongodb
from src.utils.database.db_manager import db_manager
from src.utils.version.version_manager import get_version_info, check_for_updates
from ..base import BaseCog

# Set up logging
logger = logging.getLogger('admin.settings')
class Settings(BaseCog):
    """Server settings management commands"""
    def __init__(self, bot):
        super().__init__(bot)
        self.settings_cache = {}
        self.update_queue = asyncio.Queue()

    async def initialize_db(self):
        """Initialize the database connection"""
        try:
            # Get the database from db_manager
            if db_manager and hasattr(db_manager, 'get_database'):
                self.db = db_manager.get_database()
            else:
                # Fallback to bot's async_db if available
                self.db = getattr(self.bot, 'async_db', None)
            logger.info("Database connection initialized for Settings cog")
        except Exception as e:
            logger.error(f"Error initializing database connection: {e}")

    @commands.hybrid_command(name="settings", description="Manage server settings")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(ephemeral="Send the settings panel as ephemeral message")
    async def settings(self, ctx, ephemeral: bool = False):
        """Open the settings panel"""
        await self.open_settings_panel(ctx, ephemeral)

    
    async def open_settings_panel(self, ctx, ephemeral=False):
        """Open the main settings panel"""
        view = MainSettingsView(self.bot, ctx.guild.id)
        
        # Get current server settings to show status
        settings_summary = await self.get_settings_summary(ctx.guild.id)
        
        embed = discord.Embed(
            title="⚙️ Server Settings",
            description="**Configure your server settings using the organized buttons below.**\n"
                       "Features are color-coded: 🟢 Core • 🔵 Essential • ⚫ Optional",
            color=discord.Color.blue()
        )
        
        # Add core features status (inline fields - 3 per row)
        embed.add_field(
            name="📝 Registration System",
            value=f"**Status:** {'🟢 Active' if 'Registration' in settings_summary else '🔴 Inactive'}\n"
                  f"**Function:** Member onboarding\n"
                  f"**Setup:** Age/Gender/Game roles",
            inline=True
        )
        
        embed.add_field(
            name="👋 Welcome System", 
            value=f"**Status:** {'🟢 Active' if 'Welcome: Enabled' in settings_summary else '🔴 Inactive'}\n"
                  f"**Function:** Greet new members\n"
                  f"**Setup:** Messages & images",
            inline=True
        )
        
        embed.add_field(
            name="🎫 Ticket System",
            value=f"**Status:** {'🟢 Active' if 'Tickets: Enabled' in settings_summary else '🔴 Inactive'}\n"
                  f"**Function:** Support tickets\n"
                  f"**Setup:** Categories & staff",
            inline=True
        )
        
        # Add essential features status  
        embed.add_field(
            name="📊 Leveling System",
            value=f"**Status:** 🟢 Active\n"
                  f"**Function:** XP & level tracking\n"
                  f"**Setup:** Rewards & roles",
            inline=True
        )
        
        embed.add_field(
            name="📋 Logging System",
            value=f"**Status:** {'🟢 Active' if 'Logging: Enabled' in settings_summary else '🔴 Inactive'}\n"
                  f"**Function:** Event tracking\n"
                  f"**Setup:** Channels & events",
            inline=True
        )
        
        embed.add_field(
            name="⭐ Starboard",
            value=f"**Status:** 🔴 Inactive\n"
                  f"**Function:** Featured messages\n"
                  f"**Setup:** Star threshold",
            inline=True
        )
        
        # Button guide
        embed.add_field(
            name="🎮 Button Guide",
            value="**Row 1:** 📝 Register | 👋 Welcome | 🎫 Tickets\n"
                  "**Row 2:** 📊 Leveling | 📋 Logging | ⭐ Starboard\n" 
                  "**Row 3:** 🎨 Roles | ⚔️ Moderation | 🛡️ Server\n"
                  "**Row 4:** 🤖 Bot Config | 🎂 Birthday | 🤖 AI\n"
                  "**Row 5:** ⚙️ Advanced | ❌ Close",
            inline=False
        )
        
        embed.set_footer(text="🔒 Administrator permissions required • Click buttons to configure features")
        await ctx.send(embed=embed, view=view, ephemeral=ephemeral)
    
    async def get_settings_summary(self, guild_id):
        """Get a summary of current server settings"""
        if self.db is None:
            self.db = db_manager.get_database()
            
        summary_parts = []
        
        # Check feature toggles
        features = await self.db.feature_toggles.find_one({"guild_id": guild_id}) or {}
        active_features = sum(1 for k, v in features.items() if k != "guild_id" and v)
        summary_parts.append(f"✅ Active Features: {active_features}")
        
        # Check logging
        server_settings = await self.db.server_settings.find_one({"server_id": guild_id}) or {}
        if "logging" in server_settings and server_settings["logging"].get("channel_id"):
            summary_parts.append("📋 Logging: Enabled")
        else:
            summary_parts.append("📋 Logging: Disabled")
            
        # Check welcome system
        welcome_settings = await self.db.welcomer.find_one({"guild_id": guild_id})
        if welcome_settings and welcome_settings.get("welcome_channel_id"):
            summary_parts.append("👋 Welcome: Enabled")
        else:
            summary_parts.append("👋 Welcome: Disabled")
            
        # Check ticket system
        ticket_settings = await self.db.ticket_settings.find_one({"guild_id": guild_id})
        if ticket_settings and ticket_settings.get("category_id"):
            summary_parts.append("🎫 Tickets: Enabled")
        else:
            summary_parts.append("🎫 Tickets: Disabled")
        
        # Check bot prefix
        bot_settings = await self.db.settings.find_one({"guild_id": guild_id}) or {}
        prefix = bot_settings.get("prefix", ">")
        summary_parts.append(f"🤖 Prefix: `{prefix}`")
        
        # Check birthday system
        birthday_settings = await self.db.birthday.find_one({"guild_id": guild_id})
        if birthday_settings and birthday_settings.get("channel_id"):
            summary_parts.append("🎂 Birthday: Enabled")
        else:
            summary_parts.append("🎂 Birthday: Disabled")
            
        return "\n".join(summary_parts)

    async def handle_registration_settings(self, interaction):
        """Handle registration settings button press"""
        view = RegisterSettingsView(self.bot, interaction.guild_id)
        await view.initialize()
        
        embed = discord.Embed(
            title="📝 Kayıt Sistemi Ayarları",
            description="Sunucunuz için kayıt sistemi ayarlarını yapılandırın",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Mevcut Ayarlar",
            value=(
                f"**Ana Kayıt Rolü:** {f'<@&{view.main_role_id}>' if view.main_role_id else 'Ayarlanmamış'}\n"
                f"**18+ Rolü:** {f'<@&{view.age_plus_role_id}>' if view.age_plus_role_id else 'Ayarlanmamış'}\n"
                f"**18- Rolü:** {f'<@&{view.age_minus_role_id}>' if view.age_minus_role_id else 'Ayarlanmamış'}\n"
                f"**Bronz Rol:** {f'<@&{view.bronze_role_id}>' if view.bronze_role_id else 'Ayarlanmamış'}\n"
                f"**Kayıt Log Kanalı:** {f'<#{view.log_channel_id}>' if view.log_channel_id else 'Ayarlanmamış'}\n"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def handle_ticket_settings(self, interaction):
        """Handle ticket settings button press"""
        view = TicketSystemView(self.bot, interaction.guild_id)
        await view.initialize()
        
        embed = discord.Embed(
            title="🎫 Ticket System Settings",
            description="Configure ticket system settings for your server",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Current Settings",
            value=(
                f"**Ticket Category:** {f'<#{view.ticket_category_id}>' if view.ticket_category_id else 'Not set'}\n"
                f"**Ticket Log Channel:** {f'<#{view.log_channel_id}>' if view.log_channel_id else 'Not set'}\n"
                f"**Ticket Archive Category:** {f'<#{view.archive_category_id}>' if view.archive_category_id else 'Not set'}\n"
                f"**Staff Role:** {f'<@&{view.staff_role_id}>' if view.staff_role_id else 'Not set'}\n"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)



    @commands.hybrid_command(name="status", description="Show bot status and system information")
    async def status(self, ctx: commands.Context):
        """Show comprehensive bot status"""
        # Use defer for both interaction and context
        if hasattr(ctx, 'interaction') and ctx.interaction:
            await ctx.defer()
        
        # Get bot info
        bot = self.bot
        uptime = datetime.utcnow() - bot.start_time if hasattr(bot, 'start_time') else timedelta(0)
        
        # Get version info
        version_info = await get_version_info()
        
        embed = discord.Embed(
            title="🤖 Bot Status",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        # Basic info
        embed.add_field(
            name="📊 Basic Info",
            value=f"**Version:** {version_info['current_version']}\n"
                  f"**Uptime:** {str(uptime).split('.')[0]}\n"
                  f"**Prefix:** `{bot.command_prefix}`\n"
                  f"**Guilds:** {len(bot.guilds)}",
            inline=True
        )
        
        # System info
        embed.add_field(
            name="⚙️ System",
            value=f"**Python:** {sys.version.split()[0]}\n"
                  f"**Discord.py:** {discord.__version__}\n"
                  f"**Ping:** {round(bot.latency * 1000)}ms",
            inline=True
        )
        
        # Update info
        update_check = version_info.get('update_check', {})
        if update_check.get('update_available'):
            update_text = f"🆕 **{update_check['latest_version']}** available!"
        else:
            update_text = "✅ Up to date"
        
        embed.add_field(
            name="🔄 Updates",
            value=update_text,
            inline=True
        )
        
        embed.set_footer(text=f"Bot ID: {bot.user.id}")
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="version", description="Show version information and check for updates")
    async def version(self, ctx: commands.Context):
        """Show detailed version information"""
        # Use defer for both interaction and context
        if hasattr(ctx, 'interaction') and ctx.interaction:
            await ctx.defer()
        
        try:
            version_info = await get_version_info()
            current_version = version_info['current_version']
            update_check = version_info.get('update_check', {})
            
            embed = discord.Embed(
                title="📋 Version Information",
                color=0x2F3136,
                timestamp=datetime.utcnow()
            )
            
            # Current version
            embed.add_field(
                name="📦 Current Version",
                value=f"**v{current_version}**",
                inline=True
            )
            
            # Latest version
            if update_check.get('latest_version'):
                latest_version = update_check['latest_version']
                if update_check.get('update_available'):
                    status_emoji = "🆕"
                    status_text = "Update Available!"
                    color = 0xffaa00
                else:
                    status_emoji = "✅"
                    status_text = "Up to Date"
                    color = 0x00ff00
                
                embed.color = color
                embed.add_field(
                    name="🌐 Latest Version",
                    value=f"**v{latest_version}**\n{status_emoji} {status_text}",
                    inline=True
                )
                
                # Release info
                if update_check.get('release_url'):
                    embed.add_field(
                        name="🔗 Release",
                        value=f"[View on GitHub]({update_check['release_url']})",
                        inline=True
                    )
                
                # Release notes (truncated)
                if update_check.get('release_notes'):
                    notes = update_check['release_notes'][:500]
                    if len(update_check['release_notes']) > 500:
                        notes += "..."
                    embed.add_field(
                        name="📝 Release Notes",
                        value=f"```{notes}```",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="🌐 Latest Version",
                    value="Could not fetch from GitHub",
                    inline=True
                )
            
            # Repository info
            if version_info.get('github_url'):
                embed.add_field(
                    name="📚 Repository",
                    value=f"[{version_info['repository']}]({version_info['github_url']})",
                    inline=False
                )
            
            embed.set_footer(text="Version information is cached for 5 minutes")
            
        except Exception as e:
            logger.error(f"Error getting version info: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Could not fetch version information.",
                color=0xff0000
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the Settings cog to the bot"""
    await bot.add_cog(Settings(bot))