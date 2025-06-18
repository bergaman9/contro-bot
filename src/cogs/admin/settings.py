import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
import logging
import os
import asyncio
from datetime import datetime

from utils.core.formatting import create_embed
from utils.settings.views import (
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
from utils.settings.logging_views import LoggingSettingsView
from utils.settings.register_views import RegisterSettingsView
from utils.database.connection import get_async_db, initialize_mongodb
from utils.database.db_manager import db_manager

# Set up logging
logger = logging.getLogger('settings')
class Settings(commands.Cog):
    """Server settings management commands"""
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.bot.loop.create_task(self.initialize_db())

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
            description="Configure your server settings using the buttons below.",
            color=discord.Color.blue()
        )
        
        # Add current settings summary
        embed.add_field(
            name="📊 Current Status",
            value=settings_summary,
            inline=False
        )
        
        embed.set_footer(text="This panel can only be used by administrators.")
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

async def setup(bot):
    """Add the Settings cog to the bot"""
    await bot.add_cog(Settings(bot))