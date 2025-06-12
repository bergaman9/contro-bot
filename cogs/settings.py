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
    FeatureManagementView
)
# from utils.settings.logging_views import LoggingSettingsView  # TODO: Fix import issue
from utils.setup.views import LanguageSelectView
from utils.settings.register_views import RegisterSettingsView
from utils.database.connection import get_async_db, initialize_mongodb

# Set up logging
logger = logging.getLogger('settings')
class Settings(commands.Cog):
    """Server settings management utility class"""
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.bot.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        """Initialize the database connection"""
        try:
            self.db = get_async_db()
            logger.info("Database connection initialized for Settings cog")
        except Exception as e:
            logger.error(f"Error initializing database connection: {e}")
    
    async def handle_registration_settings(self, interaction):
        """Handle registration settings button press"""
        try:
            view = RegisterSettingsView(self.bot, interaction.guild.id)
            
            embed = discord.Embed(
                title="📝 Registration System Settings",
                description="Configure registration system settings for your server",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Configuration Options",
                value=(
                    "🔰 Set main registration role\n"
                    "👤 Configure age-based roles\n"
                    "🥉 Bronze role assignment\n"
                    "📊 Set log channel\n"
                    "💬 Edit welcome messages\n"
                    "✅ Create registration button"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in handle_registration_settings: {e}")
            await interaction.followup.send("An error occurred while loading registration settings.", ephemeral=True)

    async def handle_ticket_settings(self, interaction):
        """Handle ticket settings button press"""
        try:
            from utils.settings.ticket_views import TicketSettingsView
            view = TicketSettingsView(self.bot)
            
            embed = discord.Embed(
                title="🎫 Ticket System Settings",
                description="Configure ticket system settings for your server",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Available Features",
                value=(
                    "• Set ticket category and log channel\n"
                    "• Configure support roles\n"
                    "• Create ticket message buttons\n"
                    "• Manage ticket fields and buttons\n"
                    "• Level card integration\n"
                    "• Auto archive settings\n"
                    "• Extra ticket messages"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in handle_ticket_settings: {e}")
            await interaction.followup.send("An error occurred while loading ticket settings.", ephemeral=True)

    async def handle_logging_settings(self, interaction):
        """Handle logging settings button press"""
        from utils.settings.views import LoggingView
        view = LoggingView(self.bot, "en")  # Use existing LoggingView instead
        await view.show_logging_settings(interaction)

async def setup(bot):
    """Add the Settings cog to the bot"""
    await bot.add_cog(Settings(bot))