import discord
from discord.ext import commands
from typing import Optional, Dict, Any, List
import logging
import datetime
from pathlib import Path
import os
import pymongo
from src.utils.database.connection import initialize_mongodb
from src.utils.views.channel_selector import ChannelSelectView

from src.utils.database.connection import get_collection
from src.utils.database.db_manager import db_manager
from src.utils.core.formatting import create_embed, hex_to_int

# Set up logging
logger = logging.getLogger('register_settings')

# Default values for settings
DEFAULT_WELCOME_MESSAGE = "Hoş geldin {mention}! Sunucumuza kayıt olduğun için teşekkürler."
DEFAULT_BUTTON_TITLE = "📝 Sunucu Kayıt Sistemi"
DEFAULT_BUTTON_DESCRIPTION = "Sunucumuza hoş geldiniz! Aşağıdaki butona tıklayarak kayıt olabilirsiniz."
DEFAULT_BUTTON_INSTRUCTIONS = "Kaydınızı tamamlamak için isminizi ve yaşınızı doğru bir şekilde girmeniz gerekmektedir."

class RegisterSettingsView(discord.ui.View):
    """Main view for register settings"""
    
    def __init__(self, bot, guild_id, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        
        # Initialize button styles will be done after initialization
        self.bot.loop.create_task(self.initialize_view())
    
    async def initialize_view(self):
        """Initialize the view with database data"""
        await self.update_button_styles()
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only admins can use these buttons"""
        return interaction.user.guild_permissions.administrator
    
    async def update_button_styles(self):
        """Update button styles based on configuration status"""
        # Get database from db_manager
        db = db_manager.get_database()
        if db is None:
            return
            
        settings = await db.register.find_one({"guild_id": self.guild_id}) or {}
        
        # Update each button's style based on whether it's configured
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                # Entry Roles button
                if item.custom_id and "entry_roles" in str(item.custom_id):
                    roles_to_add = settings.get("roles_to_add", [])
                    item.style = discord.ButtonStyle.success if roles_to_add else discord.ButtonStyle.danger
                
                # Roles to Remove button
                elif item.custom_id and "remove_roles" in str(item.custom_id):
                    roles_to_remove = settings.get("roles_to_remove", [])
                    item.style = discord.ButtonStyle.success if roles_to_remove else discord.ButtonStyle.danger
                
                # Age Roles button
                elif item.custom_id and "age_roles" in str(item.custom_id):
                    age_roles_enabled = settings.get("age_roles_enabled", False)
                    item.style = discord.ButtonStyle.success if age_roles_enabled else discord.ButtonStyle.danger
                
                # Log Channel button
                elif item.custom_id and "log_channel" in str(item.custom_id):
                    log_channel_id = settings.get("log_channel_id")
                    item.style = discord.ButtonStyle.success if log_channel_id else discord.ButtonStyle.danger
                
                # Nickname Update button
                elif item.custom_id and "nickname_update" in str(item.custom_id):
                    nickname_enabled = settings.get("nickname_update_enabled", False)
                    item.style = discord.ButtonStyle.success if nickname_enabled else discord.ButtonStyle.danger
        
    @discord.ui.button(label="Entry Roles", emoji="🎭", style=discord.ButtonStyle.primary, row=0, custom_id="register_entry_roles")
    async def entry_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure roles to give after registration"""
        db = db_manager.get_database()
        settings = await db.register.find_one({"guild_id": self.guild_id}) or {}
        roles_to_add = settings.get("roles_to_add", [])
        
        # Check if configured
        button_style = discord.ButtonStyle.success if roles_to_add else discord.ButtonStyle.danger
        
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🎭 Entry Roles Configuration",
                description="Select roles to **give** to users after registration.\nYou can select multiple roles.",
                color=discord.Color.green() if roles_to_add else discord.Color.red()
            ),
            view=RoleSelectionView(self.bot, self.guild_id, "roles_to_add", "Entry Roles"),
            ephemeral=True
        )
    
    @discord.ui.button(label="Roles to Remove", emoji="🚫", style=discord.ButtonStyle.primary, row=0, custom_id="register_remove_roles")
    async def remove_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure roles to remove after registration"""
        db = db_manager.get_database()
        settings = await db.register.find_one({"guild_id": self.guild_id}) or {}
        roles_to_remove = settings.get("roles_to_remove", [])
        
        # Check if configured
        button_style = discord.ButtonStyle.success if roles_to_remove else discord.ButtonStyle.danger
        
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🚫 Roles to Remove Configuration",
                description="Select roles to **remove** from users after registration.\nTypically includes unverified/new member roles.",
                color=discord.Color.green() if roles_to_remove else discord.Color.red()
            ),
            view=RoleSelectionView(self.bot, self.guild_id, "roles_to_remove", "Roles to Remove"),
            ephemeral=True
        )
    
    @discord.ui.button(label="Age Roles", emoji="🎂", style=discord.ButtonStyle.secondary, row=0, custom_id="register_age_roles")
    async def age_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure age-based roles"""
        db = db_manager.get_database()
        settings = await db.register.find_one({"guild_id": self.guild_id}) or {}
        age_roles_enabled = settings.get("age_roles_enabled", False)
        
        # Button color based on status
        button_style = discord.ButtonStyle.success if age_roles_enabled else discord.ButtonStyle.danger
        
        embed = discord.Embed(
            title="🎂 Age Role Configuration",
            description="Configure roles based on user age.\nRequires age field to be enabled.",
            color=discord.Color.green() if age_roles_enabled else discord.Color.red()
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=AgeRoleConfigView(self.bot, self.guild_id),
            ephemeral=True
        )
    
    @discord.ui.button(label="Log Channel", emoji="📊", style=discord.ButtonStyle.secondary, row=1, custom_id="register_log_channel")
    async def log_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure the log channel"""
        db = db_manager.get_database()
        settings = await db.register.find_one({"guild_id": self.guild_id}) or {}
        log_channel_id = settings.get("log_channel_id")
        
        button_style = discord.ButtonStyle.success if log_channel_id else discord.ButtonStyle.danger
        
        await interaction.response.send_message(
            embed=create_embed("Select a channel for registration logs.", discord.Color.blue()),
            view=ChannelSettingView(self.bot, self.guild_id, "log_channel_id", "Log Channel"),
            ephemeral=True
        )
    
    @discord.ui.button(label="Nickname Update", emoji="✏️", style=discord.ButtonStyle.secondary, row=1, custom_id="register_nickname_update")
    async def nickname_update_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure nickname update after registration"""
        db = db_manager.get_database()
        settings = await db.register.find_one({"guild_id": self.guild_id}) or {}
        nickname_enabled = settings.get("nickname_update_enabled", False)
        
        button_style = discord.ButtonStyle.success if nickname_enabled else discord.ButtonStyle.danger
        
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✏️ Nickname Update Settings",
                description="Configure automatic nickname update after registration.",
                color=discord.Color.green() if nickname_enabled else discord.Color.red()
            ),
            view=NicknameSettingsView(self.bot, self.guild_id),
            ephemeral=True
        )
    
    @discord.ui.button(label="Send Register Message", emoji="📤", style=discord.ButtonStyle.success, row=2)
    async def send_register_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send registration message to a channel"""
        try:
            # Check if registration system is configured
            settings = get_collection("register").find_one({"guild_id": self.guild_id})
            if not settings or "role_id" not in settings:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Please configure the registration system first!", discord.Color.red()),
                    ephemeral=True
                )
            
            # Show language and channel selection
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="📤 Send Registration Message",
                    description="Choose the language and channel for the registration message.",
                    color=discord.Color.blue()
                ),
                view=RegisterMessageSendView(self.bot, self.guild_id),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error sending register message: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Error sending registration message: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Registration Fields", emoji="📝", style=discord.ButtonStyle.primary, row=2)
    async def configure_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure registration form fields"""
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📝 Registration Fields",
                description="Configure which fields users need to fill when registering.",
                color=discord.Color.blue()
            ),
            view=RegisterFieldsView(self.bot, self.guild_id),
            ephemeral=True
        )
    
    @discord.ui.button(label="View All Settings", emoji="🔍", style=discord.ButtonStyle.blurple, row=3)
    async def view_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View all registration settings"""
        try:
            settings = get_collection("register").find_one({"guild_id": self.guild_id}) or {}
            
            embed = discord.Embed(
                title="📋 Registration System Settings",
                color=discord.Color.blurple()
            )
            
            # Entry roles
            roles_to_add = settings.get("roles_to_add", [])
            if roles_to_add:
                roles = []
                for role_id in roles_to_add:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        roles.append(role.mention)
                embed.add_field(name="✅ Entry Roles", value=", ".join(roles) if roles else "❌ None found", inline=True)
            else:
                embed.add_field(name="❌ Entry Roles", value="Not configured", inline=True)
            
            # Roles to remove
            roles_to_remove = settings.get("roles_to_remove", [])
            if roles_to_remove:
                roles = []
                for role_id in roles_to_remove:
                    role = interaction.guild.get_role(int(role_id))
                    if role:
                        roles.append(role.mention)
                embed.add_field(name="✅ Roles to Remove", value=", ".join(roles) if roles else "❌ None found", inline=True)
            else:
                embed.add_field(name="❌ Roles to Remove", value="Not configured", inline=True)
            
            # Age roles
            age_roles_enabled = settings.get("age_roles_enabled", False)
            age_text = "✅ Enabled" if age_roles_enabled else "❌ Disabled"
            if age_roles_enabled:
                adult_role_id = settings.get("adult_role_id")
                minor_role_id = settings.get("minor_role_id")
                
                roles_text = []
                if adult_role_id:
                    role = interaction.guild.get_role(int(adult_role_id))
                    if role:
                        roles_text.append(f"18+: {role.mention}")
                if minor_role_id:
                    role = interaction.guild.get_role(int(minor_role_id))
                    if role:
                        roles_text.append(f"18-: {role.mention}")
                
                if roles_text:
                    age_text += f"\n{chr(10).join(roles_text)}"
            
            embed.add_field(name="🎂 Age Roles", value=age_text, inline=True)
            
            # Log channel
            log_channel_id = settings.get("log_channel_id")
            if log_channel_id:
                log_channel = interaction.guild.get_channel(int(log_channel_id))
                channel_value = f"✅ {log_channel.mention}" if log_channel else "❌ Channel not found"
                embed.add_field(name="📊 Log Channel", value=channel_value, inline=True)
            else:
                embed.add_field(name="❌ Log Channel", value="Not configured", inline=True)
            
            # Nickname update
            nickname_enabled = settings.get("nickname_update_enabled", False)
            if nickname_enabled:
                format_str = settings.get("nickname_format", "{name}")
                embed.add_field(name="✅ Nickname Update", value=f"Enabled\nFormat: `{format_str}`", inline=True)
            else:
                embed.add_field(name="❌ Nickname Update", value="Disabled", inline=True)
            
            # Registration fields summary
            fields = settings.get("fields", self.get_default_fields())
            enabled_fields = [f for f in fields if f.get("enabled", True)]
            field_names = [f["label"] for f in enabled_fields]
            embed.add_field(
                name="📝 Active Fields", 
                value=", ".join(field_names) if field_names else "None",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error viewing register settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Error viewing settings: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    def get_default_fields(self):
        """Get default registration fields"""
        return [
            {"name": "name", "label": "Name", "type": "text", "enabled": True, "required": True},
            {"name": "age", "label": "Age", "type": "number", "enabled": True, "required": True}
        ]
    
    @discord.ui.button(label="Reset Settings", style=discord.ButtonStyle.danger, emoji="⚠️", row=3)
    async def reset_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset all registration settings"""
        await interaction.response.send_message(
            embed=create_embed("⚠️ Are you sure you want to reset all registration settings?", discord.Color.yellow()),
            view=ConfirmResetView(self.bot, interaction.guild.id),
            ephemeral=True
        )


class AgeRolesView(discord.ui.View):
    """View for configuring age-based roles"""
    
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
            
    @discord.ui.button(label="18+ Role", style=discord.ButtonStyle.primary, emoji="🔞")
    async def adult_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure the adult role (18+)"""
        await interaction.response.send_message(
            embed=create_embed("Select the role for users 18 and older.", discord.Color.blue()),
            view=RoleSettingView(self.bot, self.guild_id, "adult_role_id", "18+ Role"),
            ephemeral=True
        )
    
    @discord.ui.button(label="18- Role", style=discord.ButtonStyle.primary, emoji="👶")
    async def minor_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure the minor role (under 18)"""
        await interaction.response.send_message(
            embed=create_embed("Select the role for users under 18.", discord.Color.blue()),
            view=RoleSettingView(self.bot, self.guild_id, "minor_role_id", "18- Role"),
            ephemeral=True
        )


class RoleSettingModal(discord.ui.Modal):
    """Modal for setting a role ID"""
    
    def __init__(self, bot, guild_id, setting_key, title, placeholder):
        super().__init__(title=title)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
                
        self.role_id = discord.ui.TextInput(
            label="Role ID",
            placeholder=placeholder,
            required=True,
            min_length=1,
            max_length=20
        )
        self.add_item(self.role_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate the role ID
            try:
                role_id = int(self.role_id.value.strip())
                role = interaction.guild.get_role(role_id)
                if not role:
                                    return await interaction.response.send_message(
                    embed=create_embed(f"❌ No role found with ID: {role_id}", discord.Color.red()),
                    ephemeral=True
                )
            except ValueError:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Please enter a valid role ID.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Update the setting in the database
            get_collection("register").update_one(
                {"guild_id": self.guild_id},
                {"$set": {self.setting_key: str(role_id)}},
                upsert=True
            )
            
            # Respond to the interaction
            setting_name = self.title
            await interaction.response.send_message(
                embed=create_embed(f"✅ {setting_name} successfully set to {role.mention}!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting role: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Error setting role: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class ChannelSettingModal(discord.ui.Modal):
    """Modal for setting a channel ID"""
    
    def __init__(self, bot, guild_id, setting_key, title, placeholder):
        super().__init__(title=title)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
                
        self.channel_id = discord.ui.TextInput(
            label="Channel ID",
            placeholder=placeholder,
            required=True,
            min_length=1,
            max_length=20
        )
        self.add_item(self.channel_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate the channel ID
            try:
                channel_id = int(self.channel_id.value.strip())
                channel = interaction.guild.get_channel(channel_id)
                if not channel:
                                    return await interaction.response.send_message(
                    embed=create_embed(f"❌ No channel found with ID: {channel_id}", discord.Color.red()),
                    ephemeral=True
                )
            except ValueError:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Please enter a valid channel ID.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Update the setting in the database
            get_collection("register").update_one(
                {"guild_id": self.guild_id},
                {"$set": {self.setting_key: channel_id}},
                upsert=True
            )
            
            # Respond to the interaction
            setting_name = self.title
            await interaction.response.send_message(
                embed=create_embed(f"✅ {setting_name} successfully set to {channel.mention}!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting channel: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Error setting channel: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class MessageSettingModal(discord.ui.Modal):
    """Modal for setting a message text"""
    
    def __init__(self, bot, guild_id, setting_key, title, placeholder):
        super().__init__(title=title)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
                
        self.message_text = discord.ui.TextInput(
            label="Message",
            placeholder=placeholder,
            required=True,
            min_length=1,
            max_length=1000,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.message_text)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Update the setting in the database
            get_collection("register").update_one(
                {"guild_id": self.guild_id},
                {"$set": {self.setting_key: self.message_text.value}},
                upsert=True
            )
            
            # Respond to the interaction
            setting_name = self.title
            await interaction.response.send_message(
                embed=create_embed(f"✅ {setting_name} successfully set!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting message: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Error setting message: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class ConfirmResetView(discord.ui.View):
    """View for confirming settings reset"""
    
    def __init__(self, bot, guild_id, timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
            
    @discord.ui.button(label="Yes, Reset", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm reset of all settings"""
        try:
            # Delete all settings for the guild
            get_collection("register").delete_one({"guild_id": self.guild_id})
            
            # Respond to the interaction
            await interaction.response.send_message(
                embed=create_embed("✅ All registration settings have been reset!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Error resetting settings: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the reset operation"""
        await interaction.response.send_message(
            embed=create_embed("✅ Operation cancelled.", discord.Color.blue()),
            ephemeral=True
        )


class RoleSettingView(discord.ui.View):
    """View for configuring role settings"""
    
    def __init__(self, bot, guild_id, setting_key, title, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.title = title
        
    @discord.ui.button(label="Enter Role ID", style=discord.ButtonStyle.primary, emoji="🔢")
    async def role_id_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Enter role ID manually"""
        await interaction.response.send_modal(
            RoleSettingModal(self.bot, self.guild_id, self.setting_key, self.title, "Enter the role ID")
        )


class ChannelSettingView(discord.ui.View):
    """View for configuring channel settings"""
    
    def __init__(self, bot, guild_id, setting_key, title, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.title = title
        
    @discord.ui.button(label="Enter Channel ID", style=discord.ButtonStyle.primary, emoji="🔢")
    async def channel_id_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Enter channel ID manually"""
        await interaction.response.send_modal(
            ChannelSettingModal(self.bot, self.guild_id, self.setting_key, self.title, "Enter the channel ID")
        )


class MessageSettingView(discord.ui.View):
    """View for configuring message settings"""
    
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="Edit Welcome Message", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit the welcome message"""
        await interaction.response.send_modal(
            MessageSettingModal(self.bot, self.guild_id, "welcome_message", "Edit Welcome Message", "Enter your custom welcome message")
        )


class ButtonCustomizationView(discord.ui.View):
    """View for customizing and creating registration button"""
    
    def __init__(self, bot, guild_id, channel, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.channel = channel
                
    @discord.ui.button(label="Create Default Button", style=discord.ButtonStyle.success, emoji="✅")
    async def create_default_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create registration button with default settings"""
        try:
            # Create the registration button view
            from src.utils.community.turkoyto.registration_view import RegistrationButtonView
            register_view = RegistrationButtonView()
            
            # Create the embed
            embed = discord.Embed(
                title=DEFAULT_BUTTON_TITLE,
                description=DEFAULT_BUTTON_DESCRIPTION,
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Instructions",
                value=DEFAULT_BUTTON_INSTRUCTIONS,
                inline=False
            )
            
            # Send the message with the button
            await self.channel.send(embed=embed, view=register_view)
            
            await interaction.response.send_message(
                embed=create_embed("✅ Registration button created successfully!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error creating registration button: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Error creating button: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class RegisterMessageSendView(discord.ui.View):
    """View for sending registration message with language selection"""
    
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.language = "en"
        
    @discord.ui.button(label="🇬🇧 English", style=discord.ButtonStyle.primary, row=0)
    async def english_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send English registration message"""
        self.language = "en"
        await self.select_channel(interaction)
    
    @discord.ui.button(label="🇹🇷 Turkish", style=discord.ButtonStyle.primary, row=0)
    async def turkish_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send Turkish registration message"""
        self.language = "tr"
        await self.select_channel(interaction)
    
    async def select_channel(self, interaction: discord.Interaction):
        """Show channel selection"""
        from src.utils.settings.channel_selector import ChannelSelectView
        
        channels = [ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.guild.me).send_messages]
        
        async def send_register_message(inter: discord.Interaction, channel: discord.TextChannel):
            """Send the registration message to selected channel"""
            try:
                # Get settings
                settings = get_collection("register").find_one({"guild_id": self.guild_id}) or {}
                
                # Create embed based on language
                if self.language == "en":
                    embed = discord.Embed(
                        title="📝 Server Registration",
                        description="Welcome to our server! Please click the button below to register and gain access to all channels.",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name="📋 Instructions",
                        value="• Click the **Register** button below\n"
                              "• Fill in the required information\n"
                              "• Submit the form to complete registration",
                        inline=False
                    )
                    embed.add_field(
                        name="❓ Need Help?",
                        value="If you have any issues, please contact our staff members.",
                        inline=False
                    )
                    button_label = "Register"
                else:  # Turkish
                    embed = discord.Embed(
                        title="📝 Sunucu Kayıt",
                        description="Sunucumuza hoş geldiniz! Tüm kanallara erişim sağlamak için aşağıdaki butona tıklayarak kayıt olun.",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name="📋 Talimatlar",
                        value="• Aşağıdaki **Kayıt Ol** butonuna tıklayın\n"
                              "• Gerekli bilgileri doldurun\n"
                              "• Kaydı tamamlamak için formu gönderin",
                        inline=False
                    )
                    embed.add_field(
                        name="❓ Yardıma mı İhtiyacınız Var?",
                        value="Herhangi bir sorun yaşarsanız, lütfen yetkili ekibimizle iletişime geçin.",
                        inline=False
                    )
                    button_label = "Kayıt Ol"
                
                embed.set_footer(text=f"Registration System • {interaction.guild.name}")
                embed.timestamp = datetime.datetime.now()
                
                # Create registration button view with persistent custom_id
                register_view = discord.ui.View(timeout=None)
                register_button = discord.ui.Button(
                    label=button_label,
                    style=discord.ButtonStyle.primary,
                    emoji="📝",
                    custom_id="register_button_persistent"
                )
                register_view.add_item(register_button)
                
                # Send the message
                await channel.send(embed=embed, view=register_view)
                
                await inter.response.send_message(
                    embed=create_embed(f"✅ Registration message sent to {channel.mention}!", discord.Color.green()),
                    ephemeral=True
                )
                
            except Exception as e:
                logger.error(f"Error sending registration message: {e}")
                await inter.response.send_message(
                    embed=create_embed(f"❌ Error: {str(e)}", discord.Color.red()),
                    ephemeral=True
                )
        
        view = ChannelSelectView(channels, send_register_message)
        
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📍 Select Channel",
                description="Select the channel where you want to send the registration message.",
                color=discord.Color.blue()
            ),
            view=view,
            ephemeral=True
        )


class RegisterFieldsView(discord.ui.View):
    """View for configuring registration form fields"""
    
    def __init__(self, bot, guild_id, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
                
    @discord.ui.button(label="View Current Fields", emoji="📋", style=discord.ButtonStyle.primary, row=0)
    async def view_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current registration fields"""
        settings = get_collection("register").find_one({"guild_id": self.guild_id}) or {}
        fields = settings.get("fields", self.get_default_fields())
        
        embed = discord.Embed(
            title="📋 Current Registration Fields",
            description="These fields will be shown in the registration form:",
            color=discord.Color.blue()
        )
        
        for field in fields:
            status = "✅ Enabled" if field["enabled"] else "❌ Disabled"
            required = "Required" if field.get("required", True) else "Optional"
            embed.add_field(
                name=f"{field['label']} ({field['type']})",
                value=f"Status: {status}\n{required}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Toggle Name Field", emoji="👤", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle name field"""
        await self.toggle_field(interaction, "name", "Name")
    
    @discord.ui.button(label="Toggle Age Field", emoji="🎂", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_age(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle age field"""
        await self.toggle_field(interaction, "age", "Age")
    
    @discord.ui.button(label="Toggle Gender Field", emoji="⚧", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_gender(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle gender field"""
        await self.toggle_field(interaction, "gender", "Gender")
    
    @discord.ui.button(label="Toggle Location Field", emoji="🌍", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_location(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle location field"""
        await self.toggle_field(interaction, "location", "Location")
    
    @discord.ui.button(label="Add Custom Field", emoji="➕", style=discord.ButtonStyle.success, row=2)
    async def add_custom_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a custom field"""
        await interaction.response.send_modal(AddCustomFieldModal(self.bot, self.guild_id))
    
    @discord.ui.button(label="Reset to Default", emoji="🔄", style=discord.ButtonStyle.danger, row=2)
    async def reset_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset fields to default"""
        get_collection("register").update_one(
            {"guild_id": self.guild_id},
            {"$set": {"fields": self.get_default_fields()}},
            upsert=True
        )
        
        await interaction.response.send_message(
            embed=create_embed("✅ Registration fields reset to default!", discord.Color.green()),
            ephemeral=True
        )
    
    def get_default_fields(self):
        """Get default registration fields"""
        return [
            {"name": "name", "label": "Name", "type": "text", "enabled": True, "required": True},
            {"name": "age", "label": "Age", "type": "number", "enabled": True, "required": True},
            {"name": "gender", "label": "Gender", "type": "select", "enabled": False, "required": False, 
             "options": ["Male", "Female", "Other", "Prefer not to say"]},
            {"name": "location", "label": "Location", "type": "text", "enabled": False, "required": False}
        ]
    
    async def toggle_field(self, interaction: discord.Interaction, field_name: str, field_label: str):
        """Toggle a field on/off"""
        settings = get_collection("register").find_one({"guild_id": self.guild_id}) or {}
        fields = settings.get("fields", self.get_default_fields())
        
        # Find and toggle the field
        for field in fields:
            if field["name"] == field_name:
                field["enabled"] = not field["enabled"]
                break
        
        # Save updated fields
        get_collection("register").update_one(
            {"guild_id": self.guild_id},
            {"$set": {"fields": fields}},
            upsert=True
        )
        
        status = "enabled" if field["enabled"] else "disabled"
        await interaction.response.send_message(
            embed=create_embed(f"✅ {field_label} field has been {status}!", discord.Color.green()),
            ephemeral=True
        )


class AddCustomFieldModal(discord.ui.Modal, title="Add Custom Field"):
    """Modal for adding custom registration field"""
    
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
                
    field_name = discord.ui.TextInput(
        label="Field Name (lowercase, no spaces)",
        placeholder="e.g., discord_username",
        required=True,
        max_length=50
    )
    
    field_label = discord.ui.TextInput(
        label="Field Label (shown to users)",
        placeholder="e.g., Discord Username",
        required=True,
        max_length=100
    )
    
    field_type = discord.ui.TextInput(
        label="Field Type (text/number/select)",
        placeholder="text",
        default="text",
        required=True,
        max_length=20
    )
    
    is_required = discord.ui.TextInput(
        label="Required? (yes/no)",
        placeholder="yes",
        default="yes",
        required=True,
        max_length=3
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate field type
            field_type = self.field_type.value.lower()
            if field_type not in ["text", "number", "select"]:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Field type must be: text, number, or select", discord.Color.red()),
                    ephemeral=True
                )
            
            # Get current fields
            settings = get_collection("register").find_one({"guild_id": self.guild_id}) or {}
            fields = settings.get("fields", [])
            
            # Add new field
            new_field = {
                "name": self.field_name.value.lower().replace(" ", "_"),
                "label": self.field_label.value,
                "type": field_type,
                "enabled": True,
                "required": self.is_required.value.lower() in ["yes", "true", "1"],
                "custom": True
            }
            
            fields.append(new_field)
            
            # Save updated fields
            get_collection("register").update_one(
                {"guild_id": self.guild_id},
                {"$set": {"fields": fields}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed(f"✅ Custom field '{self.field_label.value}' added successfully!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error adding custom field: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class RoleSelectionView(discord.ui.View):
    """View for selecting multiple roles with pagination"""
    
    def __init__(self, bot, guild_id, setting_key, title, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.title = title
        self.current_page = 0
        self.roles_per_page = 20
        
        # Get all roles except @everyone
        guild = bot.get_guild(int(guild_id))
        if guild:
            self.all_roles = [r for r in guild.roles if r.name != "@everyone"]
            self.all_roles.sort(key=lambda r: r.position, reverse=True)
        else:
            self.all_roles = []
        
        self.max_pages = max(1, -(-len(self.all_roles) // self.roles_per_page))
        self.update_buttons()
    
    def update_buttons(self):
        """Update the view with role select and pagination"""
        self.clear_items()
        
        # Get current page roles
        start = self.current_page * self.roles_per_page
        end = start + self.roles_per_page
        page_roles = self.all_roles[start:end]
        
        if page_roles:
            # Add role select
            self.add_item(RoleSelect(page_roles, self.setting_key, self.guild_id))
        
        # Add pagination buttons
        if self.max_pages > 1:
            # Previous button
            prev_button = discord.ui.Button(
                label="Previous",
                emoji="◀️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                row=1
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)
            
            # Page indicator
            page_button = discord.ui.Button(
                label=f"Page {self.current_page + 1}/{self.max_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                row=1
            )
            self.add_item(page_button)
            
            # Next button
            next_button = discord.ui.Button(
                label="Next",
                emoji="▶️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.max_pages - 1,
                row=1
            )
            next_button.callback = self.next_page
            self.add_item(next_button)
        
        # Add view current selection button
        view_button = discord.ui.Button(
            label="View Selected",
            emoji="📋",
            style=discord.ButtonStyle.primary,
            row=2
        )
        view_button.callback = self.view_selected
        self.add_item(view_button)
        
        # Add clear button
        clear_button = discord.ui.Button(
            label="Clear All",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            row=2
        )
        clear_button.callback = self.clear_selection
        self.add_item(clear_button)
    
    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page"""
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(view=self)
    
    async def next_page(self, interaction: discord.Interaction):
        """Go to next page"""
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(view=self)
    
    async def view_selected(self, interaction: discord.Interaction):
        """View currently selected roles"""
        settings = get_collection("register").find_one({"guild_id": self.guild_id}) or {}
        selected_ids = settings.get(self.setting_key, [])
        
        if not selected_ids:
            await interaction.response.send_message(
                embed=create_embed("❌ No roles selected yet.", discord.Color.red()),
                ephemeral=True
            )
            return
        
        guild = self.bot.get_guild(int(self.guild_id))
        selected_roles = []
        for role_id in selected_ids:
            role = guild.get_role(int(role_id))
            if role:
                selected_roles.append(role.mention)
        
        embed = discord.Embed(
            title=f"📋 Selected {self.title}",
            description=", ".join(selected_roles) if selected_roles else "None found",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def clear_selection(self, interaction: discord.Interaction):
        """Clear all selected roles"""
        get_collection("register").update_one(
            {"guild_id": self.guild_id},
            {"$set": {self.setting_key: []}},
            upsert=True
        )
        
        await interaction.response.send_message(
            embed=create_embed(f"✅ All {self.title.lower()} cleared!", discord.Color.green()),
            ephemeral=True
        )


class RoleSelect(discord.ui.Select):
    """Role selection dropdown"""
    
    def __init__(self, roles, setting_key, guild_id):
        self.setting_key = setting_key
        self.guild_id = guild_id
                
        # Get current selection
        settings = get_collection("register").find_one({"guild_id": guild_id}) or {}
        selected_ids = settings.get(setting_key, [])
        
        options = []
        for role in roles[:25]:  # Discord limit
            is_selected = str(role.id) in selected_ids
            options.append(
                discord.SelectOption(
                    label=role.name,
                    value=str(role.id),
                    description=f"{'✅ Selected' if is_selected else 'Click to toggle'}",
                    emoji="✅" if is_selected else "⬜"
                )
            )
        
        super().__init__(
            placeholder="Select roles to toggle...",
            options=options,
            min_values=0,
            max_values=len(options)
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle role selection"""
        # Get current settings
        settings = get_collection("register").find_one({"guild_id": self.guild_id}) or {}
        current_selection = settings.get(self.setting_key, [])
        
        # Toggle selected roles
        for value in self.values:
            if value in current_selection:
                current_selection.remove(value)
            else:
                current_selection.append(value)
        
        # Save updated selection
        get_collection("register").update_one(
            {"guild_id": self.guild_id},
            {"$set": {self.setting_key: current_selection}},
            upsert=True
        )
        
        # Update the view
        self.view.update_buttons()
        
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"🎭 {self.view.title} Configuration",
                description=f"Roles updated! Selected: {len(current_selection)} roles",
                color=discord.Color.green()
            ),
            view=self.view
        )


class AgeRoleConfigView(discord.ui.View):
    """View for configuring age-based roles"""
    
    def __init__(self, bot, guild_id, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
            
    @discord.ui.button(label="Toggle Age Roles", emoji="🔄", style=discord.ButtonStyle.primary, row=0)
    async def toggle_age_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Enable/disable age role system"""
        settings = get_collection("register").find_one({"guild_id": self.guild_id}) or {}
        current_status = settings.get("age_roles_enabled", False)
        
        get_collection("register").update_one(
            {"guild_id": self.guild_id},
            {"$set": {"age_roles_enabled": not current_status}},
            upsert=True
        )
        
        status = "enabled" if not current_status else "disabled"
        await interaction.response.send_message(
            embed=create_embed(f"✅ Age roles {status}!", discord.Color.green()),
            ephemeral=True
        )
    
    @discord.ui.button(label="Set 18+ Role", emoji="🔞", style=discord.ButtonStyle.secondary, row=0)
    async def set_adult_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the 18+ role"""
        await interaction.response.send_message(
            embed=create_embed("Select the role for users 18 and older.", discord.Color.blue()),
            view=SingleRoleSelectView(self.bot, self.guild_id, "adult_role_id", "18+ Role"),
            ephemeral=True
        )
    
    @discord.ui.button(label="Set 18- Role", emoji="👶", style=discord.ButtonStyle.secondary, row=0)
    async def set_minor_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the under 18 role"""
        await interaction.response.send_message(
            embed=create_embed("Select the role for users under 18.", discord.Color.blue()),
            view=SingleRoleSelectView(self.bot, self.guild_id, "minor_role_id", "18- Role"),
            ephemeral=True
        )


class SingleRoleSelectView(discord.ui.View):
    """View for selecting a single role"""
    
    def __init__(self, bot, guild_id, setting_key, title, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.title = title
        
        # Get guild roles
        guild = bot.get_guild(int(guild_id))
        if guild:
            roles = [r for r in guild.roles if r.name != "@everyone"]
            roles.sort(key=lambda r: r.position, reverse=True)
            
            # Add role select
            self.add_item(SingleRoleSelect(roles[:25], setting_key, guild_id, title))


class SingleRoleSelect(discord.ui.Select):
    """Single role selection dropdown"""
    
    def __init__(self, roles, setting_key, guild_id, title):
        self.setting_key = setting_key
        self.guild_id = guild_id
        self.title = title
                
        options = []
        for role in roles:
            options.append(
                discord.SelectOption(
                    label=role.name,
                    value=str(role.id),
                    description=f"Position: {role.position}",
                    emoji="🎭"
                )
            )
        
        super().__init__(
            placeholder=f"Select {title}...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle role selection"""
        role_id = self.values[0]
        
        # Save to database
        get_collection("register").update_one(
            {"guild_id": self.guild_id},
            {"$set": {self.setting_key: role_id}},
            upsert=True
        )
        
        # Get the role
        guild = interaction.guild
        role = guild.get_role(int(role_id))
        
        await interaction.response.send_message(
            embed=create_embed(f"✅ {self.title} set to {role.mention}!", discord.Color.green()),
            ephemeral=True
        )


class NicknameSettingsView(discord.ui.View):
    """View for nickname update settings"""
    
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
            
    @discord.ui.button(label="Toggle Nickname Update", emoji="🔄", style=discord.ButtonStyle.primary, row=0)
    async def toggle_nickname(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Enable/disable nickname updates"""
        settings = get_collection("register").find_one({"guild_id": self.guild_id}) or {}
        current_status = settings.get("nickname_update_enabled", False)
        
        get_collection("register").update_one(
            {"guild_id": self.guild_id},
            {"$set": {"nickname_update_enabled": not current_status}},
            upsert=True
        )
        
        status = "enabled" if not current_status else "disabled"
        await interaction.response.send_message(
            embed=create_embed(f"✅ Nickname update {status}!", discord.Color.green()),
            ephemeral=True
        )
    
    @discord.ui.button(label="Set Format", emoji="📝", style=discord.ButtonStyle.secondary, row=0)
    async def set_format(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set nickname format"""
        await interaction.response.send_modal(NicknameFormatModal(self.bot, self.guild_id))
    
    @discord.ui.button(label="View Current", emoji="👁️", style=discord.ButtonStyle.secondary, row=0)
    async def view_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current settings"""
        settings = get_collection("register").find_one({"guild_id": self.guild_id}) or {}
        enabled = settings.get("nickname_update_enabled", False)
        format_str = settings.get("nickname_format", "{name}")
        
        embed = discord.Embed(
            title="✏️ Nickname Update Settings",
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        embed.add_field(name="Status", value="✅ Enabled" if enabled else "❌ Disabled", inline=True)
        embed.add_field(name="Format", value=f"`{format_str}`", inline=True)
        embed.add_field(
            name="Available Variables",
            value="`{name}` - User's name from form\n`{age}` - User's age\n`{username}` - Discord username",
            inline=False
        )
        embed.add_field(
            name="Example",
            value=f"{format_str.format(name='John', age='25', username='user123')}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class NicknameFormatModal(discord.ui.Modal, title="Set Nickname Format"):
    """Modal for setting nickname format"""
    
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
                
        # Get current format
        settings = get_collection("register").find_one({"guild_id": guild_id}) or {}
        current_format = settings.get("nickname_format", "{name}")
        
        self.format_input = discord.ui.TextInput(
            label="Nickname Format",
            placeholder="{name} | {age}",
            default=current_format,
            required=True,
            max_length=100
        )
        self.add_item(self.format_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Save the format"""
        format_str = self.format_input.value
        
        # Validate format
        try:
            # Test format with dummy values
            test = format_str.format(name="Test", age="18", username="testuser")
            if len(test) > 32:
                await interaction.response.send_message(
                    embed=create_embed("❌ Format produces nicknames longer than 32 characters!", discord.Color.red()),
                    ephemeral=True
                )
                return
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"❌ Invalid format: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
            return
        
        # Save format
        get_collection("register").update_one(
            {"guild_id": self.guild_id},
            {"$set": {"nickname_format": format_str}},
            upsert=True
        )
        
        await interaction.response.send_message(
            embed=create_embed(f"✅ Nickname format set to: `{format_str}`", discord.Color.green()),
            ephemeral=True
        )
