"""Modal classes for handling settings configuration in the bot."""

import discord
from datetime import datetime
import logging
from typing import Optional

from ...bot.constants import Colors
from ..core.formatting import create_embed
from ..database.db_manager import db_manager

logger = logging.getLogger(__name__)

class ServerFeaturesModal(discord.ui.Modal, title="Server Features Configuration"):
    """Modal for configuring server features."""
    
    community_features = discord.ui.TextInput(
        label="Community Features (true/false)",
        placeholder="Enable community features",
        max_length=5,
        required=False,
        default="true"
    )
    
    discovery = discord.ui.TextInput(
        label="Server Discovery (true/false)",
        placeholder="Enable in server discovery",
        max_length=5,
        required=False,
        default="false"
    )
    
    welcome_screen = discord.ui.TextInput(
        label="Welcome Screen (true/false)",
        placeholder="Enable welcome screen",
        max_length=5,
        required=False,
        default="true"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if 'community_features' in settings:
            self.community_features.default = str(settings['community_features']).lower()
        if 'discovery_enabled' in settings:
            self.discovery.default = str(settings['discovery_enabled']).lower()
        if 'welcome_screen_enabled' in settings:
            self.welcome_screen.default = str(settings['welcome_screen_enabled']).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle server features submission."""
        try:
            updates = {}
            
            if self.community_features.value:
                updates['community_features'] = self.community_features.value.lower() == 'true'
            
            if self.discovery.value:
                updates['discovery_enabled'] = self.discovery.value.lower() == 'true'
            
            if self.welcome_screen.value:
                updates['welcome_screen_enabled'] = self.welcome_screen.value.lower() == 'true'
            
            if updates:
                await self.db.server_settings.update_one(
                    {"server_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ Server Features Updated",
                description="Server feature settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update server features: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class WelcomeSettingsModal(discord.ui.Modal, title="Welcome Settings"):
    """Modal for welcome message settings."""
    
    welcome_message = discord.ui.TextInput(
        label="Welcome Message",
        placeholder="Welcome {user} to {guild}! Variables: {user}, {guild}, {mention}",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )
    
    welcome_channel = discord.ui.TextInput(
        label="Welcome Channel ID",
        placeholder="Channel ID for welcome messages",
        max_length=20,
        required=False
    )
    
    enable_images = discord.ui.TextInput(
        label="Enable Welcome Images (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="true"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if settings.get('welcome_message'):
            self.welcome_message.default = settings['welcome_message']
        if settings.get('welcome_channel_id'):
            self.welcome_channel.default = str(settings['welcome_channel_id'])
        if 'welcome_image_enabled' in settings:
            self.enable_images.default = str(settings['welcome_image_enabled']).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle welcome settings submission."""
        try:
            updates = {}
            
            if self.welcome_message.value:
                updates['welcome_message'] = self.welcome_message.value
                updates['welcome_message_enabled'] = True
            
            if self.welcome_channel.value:
                try:
                    channel_id = int(self.welcome_channel.value)
                    channel = interaction.guild.get_channel(channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        updates['welcome_channel_id'] = channel_id
                except (ValueError, TypeError):
                    pass
            
            if self.enable_images.value:
                updates['welcome_image_enabled'] = self.enable_images.value.lower() == 'true'
            
            if updates:
                await self.db.welcomer.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ Welcome Settings Updated",
                description="Welcome message settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update welcome settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class GoodbyeSettingsModal(discord.ui.Modal, title="Goodbye Settings"):
    """Modal for goodbye message settings."""
    
    goodbye_message = discord.ui.TextInput(
        label="Goodbye Message",
        placeholder="Goodbye {user}! Variables: {user}, {guild}, {mention}",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )
    
    goodbye_channel = discord.ui.TextInput(
        label="Goodbye Channel ID",
        placeholder="Channel ID for goodbye messages",
        max_length=20,
        required=False
    )
    
    enable_images = discord.ui.TextInput(
        label="Enable Goodbye Images (true/false)",
        placeholder="true or false",
        max_length=5,
        required=False,
        default="true"
    )
    
    def __init__(self, bot, guild_id: int, settings: dict):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.settings = settings
        self.db = db_manager.get_database()
        
        # Pre-fill current values
        if settings.get('goodbye_message'):
            self.goodbye_message.default = settings['goodbye_message']
        if settings.get('channel_id'):
            self.goodbye_channel.default = str(settings['channel_id'])
        if 'image_enabled' in settings:
            self.enable_images.default = str(settings['image_enabled']).lower()
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle goodbye settings submission."""
        try:
            updates = {}
            
            if self.goodbye_message.value:
                updates['goodbye_message'] = self.goodbye_message.value
                updates['enabled'] = True
            
            if self.goodbye_channel.value:
                try:
                    channel_id = int(self.goodbye_channel.value)
                    channel = interaction.guild.get_channel(channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        updates['channel_id'] = channel_id
                except (ValueError, TypeError):
                    pass
            
            if self.enable_images.value:
                updates['image_enabled'] = self.enable_images.value.lower() == 'true'
            
            if updates:
                await self.db.byebye.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": updates},
                    upsert=True
                )
            
            embed = create_embed(
                title="✅ Goodbye Settings Updated",
                description="Goodbye message settings have been updated.",
                color=Colors.SUCCESS
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = create_embed(
                title="❌ Error",
                description=f"Failed to update goodbye settings: {str(e)}",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
# ... (all other modal classes will be added here) ...
