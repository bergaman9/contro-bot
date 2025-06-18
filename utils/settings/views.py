import discord
from discord import ui
import asyncio
import json
import logging
from utils.core.formatting import create_embed
from utils.database.connection import get_async_db, ensure_async_db
from utils.core.formatting import format_timestamp, format_number
from utils.database.connection import initialize_mongodb
import datetime

# Setup logger
logger = logging.getLogger(__name__)

class LanguageSelectView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
    
    @discord.ui.select(
        placeholder="Select language / Dil seçin...",
        options=[
            discord.SelectOption(label="🇹🇷 Türkçe", value="tr", description="Turkish language"),
            discord.SelectOption(label="🇺🇸 English", value="en", description="English language")
        ]
    )
    async def language_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        language = select.values[0]
        
        if language == "tr":
            embed = discord.Embed(
                title="⚙️ Sunucu Ayarları Paneli",
                description="Sunucunuzun tüm ayarlarını tek yerden yönetin:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Mevcut Kategoriler",
                value=(
                    "🔧 **Feature Management** - Özellikleri aç/kapat\n"
                    "🏠 **Server Settings** - Temel sunucu ayarları\n"
                    "👋 **Welcome/Goodbye** - Karşılama ve vedalaşma sistemi\n"
                    "🛡️ **Moderation** - Moderasyon araçları ve otomatik roller\n"
                    "📊 **Logging** - Sunucu eventi logları\n"
                    "🎫 **Ticket System** - Destek ticket sistemi\n"
                    "👑 **Role Management** - Rol yönetimi ve reaksiyon rolleri\n"
                    "⭐ **Starboard** - Yıldız panosu sistemi\n"
                    "🎮 **Temp Channels** - Geçici sesli kanal sistemi"
                ),
                inline=False
            )
        else:
            embed = discord.Embed(
                title="⚙️ Server Settings Panel",
                description="Manage all your server settings from one place:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Available Categories",
                value=(
                    "🔧 **Feature Management** - Enable/disable features\n"
                    "🏠 **Server Settings** - Basic server configuration\n"
                    "👋 **Welcome/Goodbye** - Welcome and goodbye system\n"
                    "🛡️ **Moderation** - Moderation tools and auto roles\n"
                    "📊 **Logging** - Server event logging\n"
                    "🎫 **Ticket System** - Support ticket system\n"
                    "👑 **Role Management** - Role management and reaction roles\n"
                    "⭐ **Starboard** - Starboard system\n"
                    "🎮 **Temp Channels** - Temporary voice channels system"
                ),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=MainSettingsView(self.bot, language), ephemeral=True)

class MainSettingsView(discord.ui.View):
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.db = None
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow administrators to use this view"""
        return interaction.user.guild_permissions.administrator
    
    @discord.ui.button(label="Prefix Settings", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def prefix_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle prefix settings button"""
        view = PrefixSettingsView(self.bot, self.guild_id)
        embed = discord.Embed(
            title="📝 Prefix Settings",
            description="Configure the bot's command prefix for this server.",
            color=discord.Color.blue()
        )
        
        # Get current prefix
        if not self.db:
            self.db = self.bot.async_db
        settings = await self.db.settings.find_one({"guild_id": str(self.guild_id)}) or {}
        current_prefix = settings.get("prefix", ">")
        
        embed.add_field(
            name="Current Prefix",
            value=f"`{current_prefix}`",
            inline=False
        )
        embed.add_field(
            name="Usage",
            value=f"Commands can be used with `{current_prefix}help` or `/help`",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Server Settings", style=discord.ButtonStyle.primary, emoji="⚙️", row=0)
    async def server_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle server settings button"""
        view = ServerSettingsView(self.bot, self.guild_id)
        embed = discord.Embed(
            title="⚙️ Server Settings",
            description="Configure various server settings and features.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Welcome & Goodbye", style=discord.ButtonStyle.primary, emoji="👋", row=0)
    async def welcome_goodbye(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle welcome/goodbye settings button"""
        view = WelcomeGoodbyeView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = discord.Embed(
            title="👋 Welcome & Goodbye Settings",
            description="Configure welcome and goodbye messages for your server.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Moderation", style=discord.ButtonStyle.primary, emoji="🛡️", row=0)
    async def moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle moderation settings button"""
        view = ModerationView(self.bot, self.guild_id)
        embed = discord.Embed(
            title="🛡️ Moderation Settings",
            description="Configure moderation features and auto-moderation rules.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Logging", style=discord.ButtonStyle.primary, emoji="📋", row=1)
    async def logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle logging settings button"""
        view = LoggingSettingsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = discord.Embed(
            title="📋 Logging Settings",
            description="Configure logging for various server events.",
            color=discord.Color.blue()
        )
        
        # Add current logging status
        if view.logging_enabled and view.log_channel_id:
            embed.add_field(
                name="Status",
                value=f"✅ Enabled in <#{view.log_channel_id}>",
                inline=False
            )
        else:
            embed.add_field(
                name="Status",
                value="❌ Disabled",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Ticket System", style=discord.ButtonStyle.primary, emoji="🎫", row=1)
    async def ticket_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket system settings button"""
        from cogs.settings import Settings
        settings_cog = self.bot.get_cog('Settings')
        if settings_cog:
            await settings_cog.handle_ticket_settings(interaction)
        else:
            await interaction.response.send_message("Ticket settings module not available.", ephemeral=True)
    
    @discord.ui.button(label="Registration", style=discord.ButtonStyle.primary, emoji="📝", row=1)
    async def registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle registration settings button"""
        from cogs.settings import Settings
        settings_cog = self.bot.get_cog('Settings')
        if settings_cog:
            await settings_cog.handle_registration_settings(interaction)
        else:
            await interaction.response.send_message("Registration settings module not available.", ephemeral=True)
    
    @discord.ui.button(label="Status Roles", style=discord.ButtonStyle.primary, emoji="🎭", row=1)
    async def status_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle status role settings button"""
        view = StatusRoleSettingsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = discord.Embed(
            title="🎭 Status Role Settings",
            description="Configure automatic role assignment based on custom status.",
            color=discord.Color.blue()
        )
        
        # Show current status roles
        if view.status_roles:
            roles_text = []
            for status_role in view.status_roles[:5]:  # Show first 5
                guild = self.bot.get_guild(int(self.guild_id))
                role = guild.get_role(status_role['role_id']) if guild else None
                role_mention = role.mention if role else f"<@&{status_role['role_id']}>"
                roles_text.append(f"• **{status_role['custom_status']}** → {role_mention}")
            
            if len(view.status_roles) > 5:
                roles_text.append(f"... and {len(view.status_roles) - 5} more")
            
            embed.add_field(
                name="Current Status Roles",
                value="\n".join(roles_text),
                inline=False
            )
        else:
            embed.add_field(
                name="Current Status Roles",
                value="No status roles configured.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Birthday System", style=discord.ButtonStyle.secondary, emoji="🎂", row=2)
    async def birthday_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle birthday system settings button"""
        view = BirthdaySettingsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = discord.Embed(
            title="🎂 Birthday System Settings",
            description="Configure birthday announcements and roles.",
            color=discord.Color.blue()
        )
        
        # Show current birthday settings
        if view.birthday_channel_id:
            embed.add_field(
                name="Birthday Channel",
                value=f"<#{view.birthday_channel_id}>",
                inline=True
            )
        if view.birthday_role_id:
            embed.add_field(
                name="Birthday Role",
                value=f"<@&{view.birthday_role_id}>",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="AI Settings", style=discord.ButtonStyle.secondary, emoji="🤖", row=2)
    async def ai_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle AI settings button"""
        view = AISettingsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = discord.Embed(
            title="🤖 AI Settings",
            description="Configure AI features and Perplexity integration.",
            color=discord.Color.blue()
        )
        
        # Show AI status
        if view.perplexity_enabled:
            embed.add_field(
                name="Perplexity AI",
                value="✅ Enabled",
                inline=True
            )
        else:
            embed.add_field(
                name="Perplexity AI",
                value="❌ Disabled",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Legal & Info", style=discord.ButtonStyle.secondary, emoji="📜", row=2)
    async def legal_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle legal and info button"""
        view = LegalInfoView(self.bot)
        
        embed = discord.Embed(
            title="📜 Legal Information & Bot Info",
            description="View privacy policy, terms of service, and bot information.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Bot Version",
            value=f"`{getattr(self.bot, 'version', '1.0.0')}`",
            inline=True
        )
        embed.add_field(
            name="Support Server",
            value="[Join Support](https://discord.gg/vXhwuxJk88)",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Updates & Changelog", style=discord.ButtonStyle.secondary, emoji="📋", row=2)
    async def updates_changelog(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle updates and changelog button"""
        # Get BotSettings cog
        bot_settings_cog = self.bot.get_cog('BotSettings')
        if bot_settings_cog:
            versions_data = bot_settings_cog.get_versions_data()
            
            # Find current version data
            current_version_data = None
            for version in versions_data["versions"]:
                if version["version"] == versions_data["current_version"]:
                    current_version_data = version
                    break
            
            if current_version_data:
                # Import ChangelogView from bot_settings
                from cogs.bot_settings import ChangelogView
                view = ChangelogView(self.bot, versions_data)
                embed = view.create_changelog_embed(current_version_data)
                
                # Add send to channel button
                send_button = discord.ui.Button(
                    label="Send to Channel",
                    style=discord.ButtonStyle.success,
                    emoji="📢"
                )
                
                async def send_changelog_callback(inter: discord.Interaction):
                    if not inter.user.guild_permissions.administrator:
                        return await inter.response.send_message("Only administrators can send changelogs.", ephemeral=True)
                    
                    # Create channel select view
                    select_view = ChannelSelectView(
                        self.bot,
                        title="Select Channel for Changelog",
                        callback=lambda channel: self._send_changelog_to_channel(channel, current_version_data, versions_data)
                    )
                    
                    select_embed = discord.Embed(
                        title="📢 Send Changelog",
                        description="Select a channel to send the changelog to:",
                        color=discord.Color.blue()
                    )
                    
                    await inter.response.send_message(embed=select_embed, view=select_view, ephemeral=True)
                
                send_button.callback = send_changelog_callback
                view.add_item(send_button)
                
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.send_message("Version information not available.", ephemeral=True)
        else:
            await interaction.response.send_message("Updates module not available.", ephemeral=True)
    
    async def _send_changelog_to_channel(self, channel, version_data, versions_data):
        """Helper method to send changelog to a channel"""
        from cogs.bot_settings import ChangelogView
        view = ChangelogView(self.bot, versions_data)
        embed = view.create_changelog_embed(version_data)
        
        try:
            await channel.send(embed=embed, view=view)
            return True
        except:
            return False
    
    @discord.ui.button(label="Levelling System", style=discord.ButtonStyle.secondary, emoji="📊", row=3)
    async def levelling_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle levelling system settings button"""
        view = LevellingSettingsView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = discord.Embed(
            title="📊 Levelling System Settings",
            description="Configure the XP and levelling system for your server.",
            color=discord.Color.blue()
        )
        
        # Show levelling status
        if view.levelling_enabled:
            embed.add_field(
                name="Status",
                value="✅ Enabled",
                inline=True
            )
            if view.level_up_channel_id:
                embed.add_field(
                    name="Level Up Channel",
                    value=f"<#{view.level_up_channel_id}>",
                    inline=True
                )
        else:
            embed.add_field(
                name="Status",
                value="❌ Disabled",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Advanced Settings", style=discord.ButtonStyle.danger, emoji="⚙️", row=3)
    async def advanced_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle advanced settings button"""
        # Check if user is bot owner
        if not await self.bot.is_owner(interaction.user):
            return await interaction.response.send_message(
                "This section is only available to the bot owner.",
                ephemeral=True
            )
        
        view = AdvancedSettingsView(self.bot, self.guild_id)
        
        embed = discord.Embed(
            title="⚙️ Advanced Settings",
            description="Advanced configuration options. Use with caution!",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="⚠️ Warning",
            value="These settings can significantly affect bot behavior. Only modify if you know what you're doing.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class FeatureManagementView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="📊 View Feature Status", style=discord.ButtonStyle.primary, row=0)
    async def view_feature_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_feature_status(interaction)

    @discord.ui.button(label="👋 Toggle Welcome System", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "welcome_system", "Welcome System", "Karşılama Sistemi")

    @discord.ui.button(label="💫 Toggle Leveling System", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_leveling(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "leveling_system", "Leveling System", "Seviye Sistemi")

    @discord.ui.button(label="⭐ Toggle Starboard", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_starboard_feature(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "starboard_system", "Starboard System", "Starboard Sistemi")

    @discord.ui.button(label="🛡️ Toggle Auto Moderation", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_auto_moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "auto_moderation", "Auto Moderation", "Otomatik Moderasyon")

    @discord.ui.button(label="📊 Toggle Logging", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_logging_feature(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "logging_system", "Logging System", "Log Sistemi")    @discord.ui.button(label="🎫 Toggle Ticket System", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_ticket_feature(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "ticket_system", "Ticket System", "Ticket Sistemi")

    @discord.ui.button(label="🎮 Toggle Community Features", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_community_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "community_features", "Community Features", "Topluluk Özellikleri")

    @discord.ui.button(label="🎮 Toggle Temp Channels", style=discord.ButtonStyle.secondary, row=3)
    async def toggle_temp_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "temp_channels", "Temp Channels", "Geçici Kanallar")    @discord.ui.button(label="🔄 Reset All Features", style=discord.ButtonStyle.danger, row=2)
    async def reset_all_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reset_all_features_action(interaction)

    async def show_feature_status(self, interaction):
        mongo_db = get_async_db()
        features = await mongo_db.feature_toggles.find_one({"guild_id": self.guild_id}) or {}
        
        # Default feature states
        default_features = {
            "welcome_system": True,
            "leveling_system": True,
            "starboard_system": False,
            "auto_moderation": True,
            "logging_system": True,
            "ticket_system": True,
            "community_features": True,
            "temp_channels": True
        }
        
        embed = discord.Embed(title="🔧 Feature Status Overview", color=discord.Color.blue())
        
        feature_names = {
            "welcome_system": "👋 Welcome System",
            "leveling_system": "💫 Leveling System",
            "starboard_system": "⭐ Starboard System",
            "auto_moderation": "🛡️ Auto Moderation",
            "logging_system": "📊 Logging System",
            "ticket_system": "🎫 Ticket System",
            "community_features": "🎮 Community Features",
            "temp_channels": "🎮 Temp Channels"
        }
        
        for feature_key, name in feature_names.items():
            is_enabled = features.get(feature_key, default_features.get(feature_key, True))
            status = "🟢 Enabled" if is_enabled else "🔴 Disabled"
            embed.add_field(name=name, value=status, inline=True)
        
        embed.description = "Click the buttons below to toggle features on/off. Disabled features will not function and their commands will be unavailable."
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def toggle_feature(self, interaction, feature_key, feature_name_en, feature_name_tr):
        mongo_db = get_async_db()
        features = await mongo_db.feature_toggles.find_one({"guild_id": self.guild_id}) or {}
        
        # Get current state (default to True if not set)
        current_state = features.get(feature_key, True)
        new_state = not current_state
        
        # Update in database
        await mongo_db.feature_toggles.update_one(
            {"guild_id": self.guild_id},
            {"$set": {feature_key: new_state}},
            upsert=True
        )
        
        # Prepare response message
        if new_state:
            status = "enabled"
            color = discord.Color.green()
            emoji = "🟢"
        else:
            status = "disabled"
            color = discord.Color.red()
            emoji = "🔴"
        
        title = f"{emoji} {feature_name_en} {status.title()}"
        description = f"{feature_name_en} has been {status}."
        
        embed = discord.Embed(title=title, description=description, color=color)
        
        # Add additional info for some features
        if feature_key == "leveling_system" and not new_state:
            warning = (
                "⚠️ **Warning:** All leveling commands will be disabled."
            ) if self.language == "en" else (
                "⚠️ **Uyarı:** Tüm seviye komutları devre dışı kalacaktır."
            )
            embed.add_field(name="Additional Info", value=warning, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def reset_all_features_action(self, interaction):
        # Create a confirmation view
        confirm_view = ConfirmResetView(self.bot, self.language)
        
        title = "⚠️ Confirm Feature Reset" if self.language == "en" else "⚠️ Özellik Sıfırlamayı Onayla"
        description = (
            "This will reset all features to their default state. Are you sure?"
        ) if self.language == "en" else (
            "Bu işlem tüm özellikleri varsayılan durumlarına sıfırlayacaktır. Emin misiniz?"
        )
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class ConfirmResetView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=60)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        mongo_db = get_async_db()
        
        # Delete existing feature toggles to reset to defaults
        await mongo_db.feature_toggles.delete_one({"guild_id": interaction.guild.id})
        
        title = "✅ Features Reset" if self.language == "en" else "✅ Özellikler Sıfırlandı"
        description = (
            "All features have been reset to their default states."
        ) if self.language == "en" else (
            "Tüm özellikler varsayılan durumlarına sıfırlandı."
        )
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        title = "❌ Reset Cancelled" if self.language == "en" else "❌ Sıfırlama İptal Edildi"
        description = "No changes have been made." if self.language == "en" else "Hiçbir değişiklik yapılmadı."
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Server Settings View
class ServerSettingsView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="🎨 Set Embed Color", style=discord.ButtonStyle.primary)
    async def set_embed_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetEmbedColorModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📢 Set Report Channel", style=discord.ButtonStyle.secondary)
    async def set_report_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetReportChannelModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 View Current Settings", style=discord.ButtonStyle.success)
    async def view_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_current_settings(interaction)

    async def show_current_settings(self, interaction):
        mongo_db = get_async_db()
        settings = await mongo_db.settings.find_one({"guild_id": interaction.guild.id}) or {}
        
        embed = discord.Embed(
            title="🏠 Current Server Settings" if self.language == "en" else "🏠 Mevcut Sunucu Ayarları",
            color=discord.Color.blue()
        )
        
        # Embed color
        embed_color = settings.get("embed_color", "Not set")
        embed.add_field(
            name="🎨 Embed Color" if self.language == "en" else "🎨 Embed Rengi",
            value=embed_color,
            inline=True
        )
        
        # Report channel
        report_channel_id = settings.get("report_channel_id")
        if report_channel_id:
            channel = interaction.guild.get_channel(report_channel_id)
            report_channel = channel.mention if channel else "Channel not found"
        else:
            report_channel = "Not set" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="📢 Report Channel" if self.language == "en" else "📢 Rapor Kanalı",
            value=report_channel,
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Welcome/Goodbye View
class WelcomeGoodbyeView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="🎉 Configure Welcome", style=discord.ButtonStyle.primary)
    async def configure_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if advanced welcomer cog is available
        welcomer_cog = self.bot.get_cog("Welcomer")
        if welcomer_cog:
            embed = discord.Embed(
                title="🎉 Welcome System Available",
                description="Advanced welcome system is available! Use the buttons below:",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, view=WelcomeConfigView(self.bot, self.language), ephemeral=True)
        else:
            modal = SetWelcomeModal(self.language)
            await interaction.response.send_modal(modal)

    @discord.ui.button(label="👋 Configure Goodbye", style=discord.ButtonStyle.secondary)
    async def configure_goodbye(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if advanced byebye cog is available
        byebye_cog = self.bot.get_cog("ByeBye")
        if byebye_cog:
            embed = discord.Embed(
                title="👋 Goodbye System Available",
                description="Advanced goodbye system is available! Use the buttons below:",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, view=GoodbyeConfigView(self.bot, self.language), ephemeral=True)
        else:
            modal = SetGoodbyeModal(self.language)
            await interaction.response.send_modal(modal)    @discord.ui.button(label="📋 View Current Settings", style=discord.ButtonStyle.success)
    async def view_welcome_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_welcome_settings(interaction)
    
    async def show_welcome_settings(self, interaction):
        mongo_db = get_async_db()
        
        # Get welcome settings
        welcome_settings = await mongo_db.welcomer.find_one({"guild_id": interaction.guild.id}) or {}
        goodbye_settings = await mongo_db.byebye.find_one({"guild_id": interaction.guild.id}) or {}
        
        embed = discord.Embed(
            title="👋 Welcome/Goodbye Settings" if self.language == "en" else "👋 Karşılama/Vedalaşma Ayarları",
            color=discord.Color.blue()
        )
        
        # Welcome channel
        welcome_channel_id = welcome_settings.get("welcome_channel_id")
        if welcome_channel_id:
            channel = interaction.guild.get_channel(int(welcome_channel_id))
            welcome_channel = channel.mention if channel else "Channel not found"
        else:
            welcome_channel = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="🎉 Welcome Channel",
            value=welcome_channel,
            inline=True
        )
        
        # Goodbye channel
        goodbye_channel_id = goodbye_settings.get("byebye_channel_id")
        if goodbye_channel_id:
            channel = interaction.guild.get_channel(int(goodbye_channel_id))
            goodbye_channel = channel.mention if channel else "Channel not found"
        else:
            goodbye_channel = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="👋 Goodbye Channel",
            value=goodbye_channel,
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Welcome Config View (for advanced system)
class WelcomeConfigView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🎨 Full Setup", style=discord.ButtonStyle.primary)
    async def full_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Redirect to advanced welcomer setup
        welcomer_cog = self.bot.get_cog("Welcomer")
        if welcomer_cog and hasattr(welcomer_cog, 'setup_welcomer'):
            # This would need to be implemented in the welcomer cog
            await interaction.response.send_message("Please use the advanced welcomer commands in the welcomer cog.", ephemeral=True)
        else:
            modal = SetWelcomeModal(self.language)
            await interaction.response.send_modal(modal)

    @discord.ui.button(label="⚡ Quick Setup", style=discord.ButtonStyle.secondary)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetWelcomeModal(self.language, quick=True)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🗑️ Disable", style=discord.ButtonStyle.danger)
    async def disable_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_system(interaction, "welcomer", "Welcome")

    async def disable_system(self, interaction, collection_name, system_name):
        mongo_db = get_async_db()
        result = await mongo_db[collection_name].delete_one({"guild_id": interaction.guild.id})
        
        if result.deleted_count > 0:
            message = f"{system_name} system has been disabled." if self.language == "en" else f"{system_name} sistemi devre dışı bırakıldı."
            color = discord.Color.green()
        else:
            message = f"{system_name} system was not configured." if self.language == "en" else f"{system_name} sistemi ayarlanmamıştı."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

# Goodbye Config View (for advanced system)
class GoodbyeConfigView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🎨 Full Setup", style=discord.ButtonStyle.primary)
    async def full_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Redirect to advanced byebye setup
        byebye_cog = self.bot.get_cog("ByeBye")
        if byebye_cog and hasattr(byebye_cog, 'setup_byebye'):
            await interaction.response.send_message("Please use the advanced goodbye commands in the byebye cog.", ephemeral=True)
        else:
            modal = SetGoodbyeModal(self.language)
            await interaction.response.send_modal(modal)

    @discord.ui.button(label="⚡ Quick Setup", style=discord.ButtonStyle.secondary)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetGoodbyeModal(self.language, quick=True)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🗑️ Disable", style=discord.ButtonStyle.danger)
    async def disable_goodbye(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_system(interaction, "byebye", "Goodbye")

    async def disable_system(self, interaction, collection_name, system_name):
        mongo_db = get_async_db()
        result = await mongo_db[collection_name].delete_one({"guild_id": interaction.guild.id})
        
        if result.deleted_count > 0:
            message = f"{system_name} system has been disabled." if self.language == "en" else f"{system_name} sistemi devre dışı bırakıldı."
            color = discord.Color.green()
        else:
            message = f"{system_name} system was not configured." if self.language == "en" else f"{system_name} sistemi ayarlanmamıştı."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

# Moderation View
class ModerationView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="🤖 Auto Roles", style=discord.ButtonStyle.primary)
    async def auto_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetAutoRoleModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔒 Word Filter", style=discord.ButtonStyle.secondary)
    async def word_filter(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetWordFilterModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 View Settings", style=discord.ButtonStyle.success)
    async def view_moderation_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_moderation_settings(interaction)

    @discord.ui.button(label="🗑️ Remove Auto Roles", style=discord.ButtonStyle.danger, row=1)
    async def remove_auto_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.remove_setting(interaction, "autorole", "Auto-role")

    @discord.ui.button(label="🗑️ Remove Word Filter", style=discord.ButtonStyle.danger, row=1)
    async def remove_word_filter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.remove_setting(interaction, "filter", "Word filter")

    async def show_moderation_settings(self, interaction):
        mongo_db = get_async_db()
        
        embed = discord.Embed(
            title="🛡️ Moderation Settings" if self.language == "en" else "🛡️ Moderasyon Ayarları",
            color=discord.Color.blue()
        )
        
        # Auto roles
        autorole_settings = await mongo_db.autorole.find_one({"guild_id": interaction.guild.id})
        if autorole_settings and "roles" in autorole_settings:
            role_mentions = []
            for role_id in autorole_settings["roles"]:
                role = interaction.guild.get_role(role_id)
                if role:
                    role_mentions.append(role.mention)
            autoroles = ", ".join(role_mentions) if role_mentions else "Roles not found"
        else:
            autoroles = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="🤖 Auto Roles",
            value=autoroles,
            inline=False
        )
        
        # Word filter
        filter_settings = await mongo_db.filter.find_one({"guild_id": interaction.guild.id})
        if filter_settings:
            action = filter_settings.get("action", "Unknown")
            word_count = len(filter_settings.get("words", []))
            filter_info = f"Action: {action.title()}, Words: {word_count}"
        else:
            filter_info = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="🔒 Word Filter",
            value=filter_info,
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def remove_setting(self, interaction, collection_name, system_name):
        mongo_db = get_async_db()
        result = await mongo_db[collection_name].delete_one({"guild_id": interaction.guild.id})
        
        if result.deleted_count > 0:
            message = f"{system_name} system has been removed." if self.language == "en" else f"{system_name} sistemi kaldırıldı."
            color = discord.Color.green()
        else:
            message = f"{system_name} system was not configured." if self.language == "en" else f"{system_name} sistemi ayarlanmamıştı."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

# Logging View
class LoggingView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="📊 Set Logging Channel", style=discord.ButtonStyle.primary)
    async def set_logging_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetLoggingChannelModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⚙️ Advanced Logging", style=discord.ButtonStyle.secondary)
    async def advanced_logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "tr":
            message = "Gelişmiş loglama ayarlarını yapılandırıyorum:"
        else:
            message = "Configuring advanced logging settings:"
        
        await interaction.response.send_message(
            message, 
            view=AdvancedLoggingView(self.bot, self.language), 
            ephemeral=True
        )

    @discord.ui.button(label="📋 View Current Settings", style=discord.ButtonStyle.success)
    async def view_logging_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_logging_settings(interaction)

    @discord.ui.button(label="🗑️ Remove Logging", style=discord.ButtonStyle.danger)
    async def remove_logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.remove_setting(interaction, 'logger', 'Logging System')

    async def show_logging_settings(self, interaction):
        mongo_db = get_async_db()
        settings = await mongo_db.logger.find_one({"guild_id": interaction.guild.id}) or {}
        
        embed = discord.Embed(
            title="📊 Logging Settings" if self.language == "en" else "📊 Log Ayarları",
            color=discord.Color.blue()
        )
        
        # Logging channel
        channel_id = settings.get("channel_id")
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            logging_channel = channel.mention if channel else "Channel not found"
        else:
            logging_channel = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="📊 Logging Channel",
            value=logging_channel,
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def remove_setting(self, interaction, collection_name, system_name):
        mongo_db = get_async_db()
        result = await mongo_db[collection_name].delete_one({"guild_id": interaction.guild.id})
        
        if result.deleted_count > 0:
            message = f"{system_name} system has been removed." if self.language == "en" else f"{system_name} sistemi kaldırıldı."
            color = discord.Color.green()
        else:
            message = f"{system_name} system was not configured." if self.language == "en" else f"{system_name} sistemi ayarlanmamıştı."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

class AdvancedLoggingView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        
    @discord.ui.button(label="👥 Member Events", style=discord.ButtonStyle.primary, row=0)
    async def member_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSpecificLoggingChannelModal(
            self.language, 
            "member_events", 
            "Member Events" if self.language == "en" else "Üye Olayları",
            "Joins, leaves, bans, roles"
        )
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="💬 Message Events", style=discord.ButtonStyle.primary, row=0)
    async def message_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSpecificLoggingChannelModal(
            self.language, 
            "message_events", 
            "Message Events" if self.language == "en" else "Mesaj Olayları",
            "Edits, deletes, bulk delete"
        )
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🔧 Server Events", style=discord.ButtonStyle.primary, row=0)
    async def server_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSpecificLoggingChannelModal(
            self.language, 
            "server_events", 
            "Server Events" if self.language == "en" else "Sunucu Olayları",
            "Settings, roles, channels, emojis"
        )
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🎤 Voice Events", style=discord.ButtonStyle.primary, row=1)
    async def voice_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSpecificLoggingChannelModal(
            self.language, 
            "voice_events", 
            "Voice Events" if self.language == "en" else "Ses Olayları",
            "Joins, leaves, moves, mutes"
        )
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="📅 Event Activities", style=discord.ButtonStyle.primary, row=1)
    async def event_activities(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSpecificLoggingChannelModal(
            self.language, 
            "event_activities", 
            "Event Activities" if self.language == "en" else "Etkinlik Olayları",
            "Server events, stage instances"
        )
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🧵 Thread Events", style=discord.ButtonStyle.primary, row=1)
    async def thread_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSpecificLoggingChannelModal(
            self.language, 
            "thread_events", 
            "Thread Events" if self.language == "en" else "Thread Olayları",
            "Creates, updates, deletes"
        )
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="📝 Commands & Errors", style=discord.ButtonStyle.secondary, row=2)
    async def command_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSpecificLoggingChannelModal(
            self.language, 
            "command_events", 
            "Commands & Errors" if self.language == "en" else "Komutlar & Hatalar",
            "Command usage, errors"
        )
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="📊 View All Settings", style=discord.ButtonStyle.success, row=2)
    async def view_all_logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_all_logging_settings(interaction)
        
    @discord.ui.button(label="🗑️ Reset All Settings", style=discord.ButtonStyle.danger, row=2)
    async def reset_all_logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reset_all_logging_settings(interaction)
        
    async def show_all_logging_settings(self, interaction):
        mongo_db = await ensure_async_db()
        settings = await mongo_db.logger_settings.find_one({"guild_id": interaction.guild.id}) or {}
        
        title = "🔍 Logging Channel Settings" if self.language == "en" else "🔍 Log Kanalları Ayarları"
        description = "Here are your current logging channel configurations:" if self.language == "en" else "Mevcut loglama kanalı yapılandırmaları:"
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
        
        # Define categories with user-friendly names
        categories = {
            "member_events": ("👥 Member Events", "👥 Üye Olayları"),
            "message_events": ("💬 Message Events", "💬 Mesaj Olayları"),
            "server_events": ("🔧 Server Events", "🔧 Sunucu Olayları"),
            "voice_events": ("🎤 Voice Events", "🎤 Ses Olayları"),
            "event_activities": ("📅 Event Activities", "📅 Etkinlik Olayları"),
            "thread_events": ("🧵 Thread Events", "🧵 Thread Olayları"),
            "command_events": ("📝 Commands & Errors", "📝 Komutlar & Hatalar")
        }
        
        # Main logging channel
        main_channel_id = settings.get("channel_id")
        if main_channel_id:
            try:
                channel = interaction.guild.get_channel(main_channel_id)
                channel_mention = f"<#{main_channel_id}>" if channel else f"Unknown ({main_channel_id})"
                
                main_field_name = "📊 Main Logging Channel" if self.language == "en" else "📊 Ana Log Kanalı"
                embed.add_field(name=main_field_name, value=channel_mention, inline=False)
                
            except Exception as e:
                logger.error(f"Error getting channel {main_channel_id}: {e}")
                embed.add_field(
                    name="📊 Main Logging Channel" if self.language == "en" else "📊 Ana Log Kanalı",
                    value="Error fetching channel information",
                    inline=False
                )
        else:
            embed.add_field(
                name="📊 Main Logging Channel" if self.language == "en" else "📊 Ana Log Kanalı",
                value="Not set" if self.language == "en" else "Ayarlanmamış",
                inline=False
            )
        
        # Specific logging channels
        for category, (name_en, name_tr) in categories.items():
            channel_id = settings.get(f"{category}_channel")
            if channel_id:
                try:
                    channel = interaction.guild.get_channel(channel_id)
                    channel_mention = f"<#{channel_id}>" if channel else f"Unknown ({channel_id})"
                    
                    field_name = name_en if self.language == "en" else name_tr
                    embed.add_field(name=field_name, value=channel_mention, inline=True)
                    
                except Exception as e:
                    logger.error(f"Error getting channel {channel_id}: {e}")
                    embed.add_field(
                        name=name_en if self.language == "en" else name_tr,
                        value="Error fetching channel",
                        inline=True
                    )
            else:
                # If not set, will use main channel
                embed.add_field(
                    name=name_en if self.language == "en" else name_tr,
                    value="Uses main channel" if self.language == "en" else "Ana kanalı kullanır",
                    inline=True
                )
        
        footer_text = (
            "Events will be sent to their specific channel if set, otherwise to the main logging channel." 
            if self.language == "en" else 
            "Olaylar, belirtilen özel kanala ayarlanmışsa oraya, aksi takdirde ana loglama kanalına gönderilecektir."
        )
        embed.set_footer(text=footer_text)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def reset_all_logging_settings(self, interaction):
        confirm_text = "Are you sure you want to reset all logging channel settings?" if self.language == "en" else "Tüm loglama kanalı ayarlarını sıfırlamak istediğinize emin misiniz?"
        
        embed = discord.Embed(
            title="⚠️ Confirm Reset" if self.language == "en" else "⚠️ Sıfırlamayı Onayla",
            description=confirm_text,
            color=discord.Color.red()
        )
        
        view = ConfirmLoggingResetView(self.bot, self.language)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ConfirmLoggingResetView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
    
    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            mongo_db = await ensure_async_db()
            
            # Keep the main logger channel but remove all specific channels
            main_settings = await mongo_db.logger.find_one({"guild_id": interaction.guild.id})
            
            if main_settings:
                # Reset advanced settings but keep the main channel
                await mongo_db.logger_settings.update_one(
                    {"guild_id": interaction.guild.id},
                    {"$unset": {
                        "member_events_channel": "",
                        "message_events_channel": "",
                        "server_events_channel": "",
                        "voice_events_channel": "",
                        "event_activities_channel": "",
                        "thread_events_channel": "",
                        "command_events_channel": ""
                    }},
                    upsert=True
                )
            else:
                # If no main settings, just delete everything
                await mongo_db.logger_settings.delete_one({"guild_id": interaction.guild.id})
            
            success_text = "All advanced logging channel settings have been reset." if self.language == "en" else "Tüm gelişmiş loglama kanalı ayarları sıfırlandı."
            
            embed = discord.Embed(
                title="✅ Reset Complete" if self.language == "en" else "✅ Sıfırlama Tamamlandı",
                description=success_text,
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error resetting logging channels: {e}", exc_info=True)
            
            error_text = "An error occurred while resetting logging channels." if self.language == "en" else "Loglama kanallarını sıfırlarken bir hata oluştu."
            
            embed = discord.Embed(
                title="❌ Error" if self.language == "en" else "❌ Hata",
                description=error_text,
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        cancel_text = "Reset operation canceled." if self.language == "en" else "Sıfırlama işlemi iptal edildi."
        
        embed = discord.Embed(
            title="Operation Canceled" if self.language == "en" else "İşlem İptal Edildi",
            description=cancel_text,
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SetSpecificLoggingChannelModal(discord.ui.Modal):
    def __init__(self, language="en", category="member_events", title_text="Member Events", description_text=""):
        title = f"Set {title_text} Channel" if language == "en" else f"{title_text} Kanalı Ayarla"
        super().__init__(title=title)
        self.language = language
        self.category = category
        
        placeholder = f"#{category.replace('_', '-')} or channel ID"
        if description_text:
            if language == "en":
                placeholder += f" ({description_text})"
            else:
                tr_desc = description_text  # You might want to translate this
                placeholder += f" ({tr_desc})"
        
        self.channel = discord.ui.TextInput(
            label="Channel" if language == "en" else "Kanal",
            placeholder=placeholder,
            style=discord.TextStyle.short,
            max_length=100
        )
        
        self.add_item(self.channel)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Try to get channel from input
            channel_input = self.channel.value.strip()
            
            # Check if input is a channel mention
            channel_id = None
            if channel_input.startswith("<#") and channel_input.endswith(">"):
                channel_id = int(channel_input[2:-1])
            elif channel_input.startswith("#"):
                # Find channel by name
                channel_name = channel_input[1:]
                channel = discord.utils.get(interaction.guild.channels, name=channel_name)
                if channel:
                    channel_id = channel.id
            else:
                # Try to parse as ID
                try:
                    channel_id = int(channel_input)
                except ValueError:
                    # Try to find by name without #
                    channel = discord.utils.get(interaction.guild.channels, name=channel_input)
                    if channel:
                        channel_id = channel.id
            
            if not channel_id:
                error_msg = "Invalid channel! Please specify a valid channel." if self.language == "en" else "Geçersiz kanal! Lütfen geçerli bir kanal belirtin."
                await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                return
            
            # Check if channel exists and is text-based
            channel = interaction.guild.get_channel(channel_id)
            if not channel or not isinstance(channel, (discord.TextChannel, discord.Thread, discord.ForumChannel)):
                error_msg = "Channel not found or not a text channel!" if self.language == "en" else "Kanal bulunamadı veya bir metin kanalı değil!"
                await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                return
            
            # Check permissions
            bot_permissions = channel.permissions_for(interaction.guild.me)
            if not bot_permissions.send_messages or not bot_permissions.embed_links:
                error_msg = f"I don't have permission to send messages in {channel.mention}!" if self.language == "en" else f"{channel.mention} kanalında mesaj gönderme iznim yok!"
                await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                return
            
            # Save to database
            mongo_db = await ensure_async_db()
            
            # Update specific category channel
            await mongo_db.logger_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {f"{self.category}_channel": channel_id}},
                upsert=True
            )
            
            # Send success message
            if self.language == "en":
                success_msg = f"✅ Successfully set {self.title} channel to {channel.mention}!"
            else:
                success_msg = f"✅ {self.title} kanalı başarıyla {channel.mention} olarak ayarlandı!"
                
            embed = discord.Embed(
                description=success_msg,
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error setting specific logging channel: {e}", exc_info=True)
            error_msg = "An error occurred while setting the logging channel." if self.language == "en" else "Log kanalını ayarlarken bir hata oluştu."
            await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)

# Ticket System View
class TicketSystemView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = initialize_mongodb()
        self.ticket_category_id = None
        self.log_channel_id = None
        self.archive_category_id = None
        self.staff_role_id = None
        
    async def initialize(self):
        """Load current ticket settings"""
        mongo_db = get_async_db()
        settings = await mongo_db.ticket_settings.find_one({"guild_id": self.guild_id}) or {}
        self.ticket_category_id = settings.get("category_id")
        self.log_channel_id = settings.get("log_channel_id")
        self.archive_category_id = settings.get("archive_category_id")
        self.staff_role_id = settings.get("staff_role_id")

    @discord.ui.button(label="Set Ticket Category", emoji="📂", style=discord.ButtonStyle.primary, row=0)
    async def set_ticket_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📂 Set Ticket Category",
                description="To set the ticket category, use the `/ticket category` command.",
                color=discord.Color.blue()
            ),
            ephemeral=True
        )

    @discord.ui.button(label="Set Support Roles", emoji="👥", style=discord.ButtonStyle.secondary, row=0)
    async def set_support_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="👥 Set Support Roles",
                description="To set support roles, use the `/ticket roles` command.",
                color=discord.Color.blue()
            ),
            ephemeral=True
        )

    @discord.ui.button(label="Send Ticket Message", emoji="📤", style=discord.ButtonStyle.success, row=0)
    async def send_ticket_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send ticket creation message to a channel"""
        # Check if ticket system is configured
        settings = self.mongo_db["tickets"].find_one({"guild_id": str(self.guild_id)})
        if not settings or "category_id" not in settings:
            return await interaction.response.send_message(
                embed=create_embed("❌ Please configure the ticket system first!", discord.Color.red()),
                ephemeral=True
            )
        
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📤 Send Ticket Message",
                description="Choose the language and channel for the ticket message.",
                color=discord.Color.blue()
            ),
            view=TicketMessageSendView(self.bot, self.guild_id),
            ephemeral=True
        )

    @discord.ui.button(label="View Current Settings", emoji="📋", style=discord.ButtonStyle.primary, row=1)
    async def view_ticket_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_ticket_settings(interaction)
    
    @discord.ui.button(label="Configure Ticket Form", emoji="📝", style=discord.ButtonStyle.secondary, row=1)
    async def configure_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure ticket form questions"""
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📝 Ticket Form Configuration",
                description="Configure the questions asked when users create a ticket.",
                color=discord.Color.blue()
            ),
            view=TicketFormConfigView(self.bot, self.guild_id),
            ephemeral=True
        )

    async def show_ticket_settings(self, interaction):
        mongo_db = get_async_db()
        settings = await mongo_db.tickets.find_one({"guild_id": str(self.guild_id)}) or {}
        
        embed = discord.Embed(
            title="🎫 Ticket System Settings",
            color=discord.Color.blue()
        )
        
        # Ticket category
        category_id = settings.get("category_id")
        if category_id:
            category = interaction.guild.get_channel(int(category_id))
            ticket_category = category.name if category else "Category not found"
        else:
            ticket_category = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="📂 Ticket Category",
            value=ticket_category,
            inline=True
        )
        
        # Support roles
        support_roles = settings.get("support_roles", [])
        if support_roles:
            role_mentions = []
            for role_id in support_roles:
                role = interaction.guild.get_role(role_id)
                if role:
                    role_mentions.append(role.mention)
            support_roles_text = ", ".join(role_mentions) if role_mentions else "Roles not found"
        else:
            support_roles_text = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="👥 Support Roles",
            value=support_roles_text,
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Role Management View
class RoleManagementView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="Create Role Message", emoji="🎭", style=discord.ButtonStyle.primary)
    async def create_role_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🎭 Create Role Message",
                description="To create a role message, use the `/roles createmessage` command.",
                color=discord.Color.blue()
            ),
            ephemeral=True
        )

    @discord.ui.button(label="Set Register Channel", emoji="📝", style=discord.ButtonStyle.secondary)
    async def set_register_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📝 Set Register Channel",
                description="To set the register channel, use the `/register channel` command.",
                color=discord.Color.blue()
            ),
            ephemeral=True
        )

    @discord.ui.button(label="View Current Settings", emoji="📋", style=discord.ButtonStyle.success)
    async def view_role_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_role_settings(interaction)

    @discord.ui.button(label="Remove Register Channel", emoji="🗑️", style=discord.ButtonStyle.danger, row=1)
    async def remove_register_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        mongo_db = get_async_db()
        result = await mongo_db.register.update_one(
            {"guild_id": self.guild_id},
            {"$unset": {"channel_id": ""}}
        )
        
        if result.modified_count > 0:
            message = "Registration channel has been removed."
            color = discord.Color.green()
        else:
            message = "Registration channel was not configured."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

    async def show_role_settings(self, interaction):
        mongo_db = get_async_db()
        
        embed = discord.Embed(
            title="👑 Role Management Settings",
            color=discord.Color.blue()
        )
        
        # Register channel
        register_settings = await mongo_db.register.find_one({"guild_id": interaction.guild.id}) or {}
        channel_id = register_settings.get("channel_id")
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            register_channel = channel.mention if channel else "Channel not found"
        else:
            register_channel = "Not configured"
        
        embed.add_field(
            name="📝 Register Channel",
            value=register_channel,
            inline=True
        )
        
        # Role messages count
        role_messages_count = await mongo_db.role_messages.count_documents({"guild_id": interaction.guild.id})
        embed.add_field(
            name="🎭 Active Role Messages",
            value=str(role_messages_count),
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Starboard View
class StarboardView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="⭐ Setup Starboard", style=discord.ButtonStyle.primary)
    async def setup_starboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        # For now, send a simple message
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⭐ Setup Starboard",
                description="To set up starboard, use the `/starboard setup` command with the following options:\n"
                           "- Channel: The channel where starred messages will be posted\n"
                           "- Threshold: Number of stars required (default: 3)\n"
                           "- Emoji: The reaction emoji to use (default: ⭐)",
                color=discord.Color.gold()
            ),
            ephemeral=True
        )

    @discord.ui.button(label="📋 View Current Settings", style=discord.ButtonStyle.success)
    async def view_starboard_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_starboard_settings(interaction)

    @discord.ui.button(label="🗑️ Remove Starboard", style=discord.ButtonStyle.danger)
    async def remove_starboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.remove_setting(interaction, "starboard", "Starboard")

    async def show_starboard_settings(self, interaction):
        mongo_db = get_async_db()
        settings = await mongo_db.starboard.find_one({"guild_id": str(self.guild_id)}) or {}
        
        embed = discord.Embed(
            title="⭐ Starboard Settings",
            color=discord.Color.gold()
        )
        
        if settings:
            # Starboard channel
            channel_id = settings.get("channel_id")
            if channel_id:
                channel = interaction.guild.get_channel(int(channel_id))
                starboard_channel = channel.mention if channel else "Channel not found"
            else:
                starboard_channel = "Not found"
            
            embed.add_field(
                name="⭐ Starboard Channel",
                value=starboard_channel,
                inline=True
            )
            
            embed.add_field(
                name="😀 Emoji",
                value=settings.get("emoji", "⭐"),
                inline=True
            )
            
            embed.add_field(
                name="🔢 Required Count",
                value=str(settings.get("count", 3)),
                inline=True
            )
        else:
            embed.add_field(
                name="Status",
                value="Not configured",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def remove_setting(self, interaction, collection_name, system_name):
        mongo_db = get_async_db()
        result = await mongo_db[collection_name].delete_one({"guild_id": str(self.guild_id)})
        
        if result.deleted_count > 0:
            message = f"{system_name} system has been removed."
            color = discord.Color.green()
        else:
            message = f"{system_name} system was not configured."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

# Levelling Settings View
class LevellingSettingsView(discord.ui.View):
    def __init__(self, bot, ctx):
        super().__init__(timeout=300)
        self.bot = bot
        self.ctx = ctx
        self.mongo_db = initialize_mongodb()

    async def get_current_settings(self, guild_id):
        """Get current levelling settings"""
        try:
            settings = await self.mongo_db.levelling_settings.find_one({"guild_id": int(guild_id)})
            if settings is None:
                # Return default settings
                return {
                    "enabled": True,
                    "message_xp_enabled": True,
                    "voice_xp_enabled": True,
                    "level_up_notifications": True,
                    "level_up_channel_id": None,
                    "xp_multiplier": 1.0,
                    "voice_xp_multiplier": 1.0,
                    "cooldown_seconds": 60,
                    "max_level": 100
                }
            return settings
        except Exception as e:
            logger.error(f"Error getting levelling settings: {e}")
            return {}

    async def save_settings(self, guild_id, settings):
        """Save levelling settings"""
        try:
            await self.mongo_db.levelling_settings.update_one(
                {"guild_id": int(guild_id)},
                {"$set": settings},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving levelling settings: {e}")
            return False

    @discord.ui.button(label="🎯 Enable/Disable System", style=discord.ButtonStyle.primary, row=0)
    async def toggle_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            settings = await self.get_current_settings(interaction.guild_id)
            settings["enabled"] = not settings.get("enabled", True)
            
            if await self.save_settings(interaction.guild_id, settings):
                status = "enabled" if settings["enabled"] else "disabled"
                await interaction.response.send_message(
                    embed=create_embed(f"Levelling system has been {status}.", discord.Color.green()),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=create_embed("Failed to save settings.", discord.Color.red()),
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

    @discord.ui.button(label="💬 Message XP", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_message_xp(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            settings = await self.get_current_settings(interaction.guild_id)
            settings["message_xp_enabled"] = not settings.get("message_xp_enabled", True)
            
            if await self.save_settings(interaction.guild_id, settings):
                status = "enabled" if settings["message_xp_enabled"] else "disabled"
                await interaction.response.send_message(
                    embed=create_embed(f"Message XP has been {status}.", discord.Color.green()),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=create_embed("Failed to save settings.", discord.Color.red()),
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

    @discord.ui.button(label="🎤 Voice XP", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_voice_xp(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            settings = await self.get_current_settings(interaction.guild_id)
            settings["voice_xp_enabled"] = not settings.get("voice_xp_enabled", True)
            
            if await self.save_settings(interaction.guild_id, settings):
                status = "enabled" if settings["voice_xp_enabled"] else "disabled"
                await interaction.response.send_message(
                    embed=create_embed(f"Voice XP has been {status}.", discord.Color.green()),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=create_embed("Failed to save settings.", discord.Color.red()),
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

    @discord.ui.button(label="🔔 Level Up Notifications", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_notifications(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            settings = await self.get_current_settings(interaction.guild_id)
            settings["level_up_notifications"] = not settings.get("level_up_notifications", True)
            
            if await self.save_settings(interaction.guild_id, settings):
                status = "enabled" if settings["level_up_notifications"] else "disabled"
                await interaction.response.send_message(
                    embed=create_embed(f"Level up notifications have been {status}.", discord.Color.green()),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=create_embed("Failed to save settings.", discord.Color.red()),
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

    @discord.ui.button(label="📍 Set Level Up Channel", style=discord.ButtonStyle.secondary, row=1)
    async def set_level_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            modal = LevelChannelModal(self)
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

    @discord.ui.button(label="⚡ XP Multipliers", style=discord.ButtonStyle.secondary, row=1)
    async def set_multipliers(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            modal = XPMultiplierModal(self)
            await interaction.response.send_modal(modal)
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

    @discord.ui.button(label="📊 View Current Settings", style=discord.ButtonStyle.success, row=2)
    async def view_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            settings = await self.get_current_settings(interaction.guild_id)
            
            embed = discord.Embed(
                title="📊 Current Levelling Settings",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🎯 System Status",
                value="✅ Enabled" if settings.get("enabled", True) else "❌ Disabled",
                inline=True
            )
            
            embed.add_field(
                name="💬 Message XP",
                value="✅ Enabled" if settings.get("message_xp_enabled", True) else "❌ Disabled",
                inline=True
            )
            
            embed.add_field(
                name="🎤 Voice XP",
                value="✅ Enabled" if settings.get("voice_xp_enabled", True) else "❌ Disabled",
                inline=True
            )
            
            embed.add_field(
                name="🔔 Level Up Notifications",
                value="✅ Enabled" if settings.get("level_up_notifications", True) else "❌ Disabled",
                inline=True
            )
            
            channel_id = settings.get("level_up_channel_id")
            if channel_id:
                channel = interaction.guild.get_channel(int(channel_id))
                channel_text = channel.mention if channel else f"Channel ID: {channel_id}"
            else:
                channel_text = "Not set (uses default channels)"
            
            embed.add_field(
                name="📍 Level Up Channel",
                value=channel_text,
                inline=True
            )
            
            embed.add_field(
                name="⚡ XP Multipliers",
                value=f"Message: {settings.get('xp_multiplier', 1.0)}x\nVoice: {settings.get('voice_xp_multiplier', 1.0)}x",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Cooldown",
                value=f"{settings.get('cooldown_seconds', 60)} seconds",
                inline=True
            )
            
            embed.add_field(
                name="🎯 Max Level",
                value=str(settings.get('max_level', 100)),
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class LevelChannelModal(discord.ui.Modal, title="Set Level Up Channel"):
    def __init__(self, view):
        super().__init__()
        self.view = view

    channel_id = discord.ui.TextInput(
        label="Channel ID or Name",
        placeholder="Enter channel ID (e.g., 123456789) or channel name (e.g., general)",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_input = self.channel_id.value.strip()
            channel = None
            
            # Try to get by ID first
            if channel_input.isdigit():
                channel = interaction.guild.get_channel(int(channel_input))
            
            # If not found, try by name
            if not channel:
                for ch in interaction.guild.text_channels:
                    if ch.name.lower() == channel_input.lower():
                        channel = ch
                        break
            
            if not channel:
                await interaction.response.send_message(
                    embed=create_embed("Channel not found. Please check the ID or name.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            settings = await self.view.get_current_settings(interaction.guild_id)
            settings["level_up_channel_id"] = channel.id
            
            if await self.view.save_settings(interaction.guild_id, settings):
                await interaction.response.send_message(
                    embed=create_embed(f"Level up channel set to {channel.mention}.", discord.Color.green()),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=create_embed("Failed to save settings.", discord.Color.red()),
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class XPMultiplierModal(discord.ui.Modal, title="Set XP Multipliers"):
    def __init__(self, view):
        super().__init__()
        self.view = view

    message_multiplier = discord.ui.TextInput(
        label="Message XP Multiplier",
        placeholder="Enter a number (e.g., 1.5 for 50% more XP)",
        required=True,
        default="1.0"
    )
    
    voice_multiplier = discord.ui.TextInput(
        label="Voice XP Multiplier", 
        placeholder="Enter a number (e.g., 2.0 for double XP)",
        required=True,
        default="1.0"
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            try:
                msg_mult = float(self.message_multiplier.value)
                voice_mult = float(self.voice_multiplier.value)
            except ValueError:
                await interaction.response.send_message(
                    embed=create_embed("Please enter valid numbers for multipliers.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            if msg_mult < 0 or voice_mult < 0 or msg_mult > 10 or voice_mult > 10:
                await interaction.response.send_message(
                    embed=create_embed("Multipliers must be between 0 and 10.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            settings = await self.view.get_current_settings(interaction.guild_id)
            settings["xp_multiplier"] = msg_mult
            settings["voice_xp_multiplier"] = voice_mult
            
            if await self.view.save_settings(interaction.guild_id, settings):
                await interaction.response.send_message(
                    embed=create_embed(f"XP multipliers updated:\nMessage: {msg_mult}x\nVoice: {voice_mult}x", discord.Color.green()),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=create_embed("Failed to save settings.", discord.Color.red()),
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                embed=create_embed(f"Error: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class TicketMessageSendView(discord.ui.View):
    """View for sending ticket message with language selection"""
    
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = initialize_mongodb()
        self.language = "en"
        
    @discord.ui.button(label="🇬🇧 English", style=discord.ButtonStyle.primary, row=0)
    async def english_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send English ticket message"""
        self.language = "en"
        await self.select_channel(interaction)
    
    @discord.ui.button(label="🇹🇷 Türkçe", style=discord.ButtonStyle.primary, row=0)
    async def turkish_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send Turkish ticket message"""
        self.language = "tr"
        await self.select_channel(interaction)
    
    async def select_channel(self, interaction: discord.Interaction):
        """Show channel selection"""
        from utils.settings.channel_selector import ChannelSelectView
        
        channels = [ch for ch in interaction.guild.text_channels if ch.permissions_for(interaction.guild.me).send_messages]
        
        async def send_ticket_message(inter: discord.Interaction, channel: discord.TextChannel):
            """Send the ticket message to selected channel"""
            try:
                # Get settings
                settings = self.mongo_db["tickets"].find_one({"guild_id": str(self.guild_id)}) or {}
                
                # Create embed based on language
                if self.language == "en":
                    embed = discord.Embed(
                        title="🎫 Support Ticket System",
                        description="Need help? Create a support ticket to get assistance from our staff team.",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name="📋 How to Create a Ticket",
                        value="• Click the **Create Ticket** button below\n"
                              "• Select the category that best describes your issue\n"
                              "• Fill out the form with details about your request\n"
                              "• Wait for a staff member to assist you",
                        inline=False
                    )
                    embed.add_field(
                        name="⚠️ Important Notes",
                        value="• Only create tickets for genuine issues\n"
                              "• Be patient - staff will respond as soon as possible\n"
                              "• Provide as much detail as possible in your initial message",
                        inline=False
                    )
                    button_label = "Create Ticket"
                else:  # Turkish
                    embed = discord.Embed(
                        title="🎫 Destek Talep Sistemi",
                        description="Yardıma mı ihtiyacınız var? Ekibimizden yardım almak için bir destek talebi oluşturun.",
                        color=discord.Color.blue()
                    )
                    embed.add_field(
                        name="📋 Nasıl Talep Oluşturulur",
                        value="• Aşağıdaki **Talep Oluştur** butonuna tıklayın\n"
                              "• Sorununuzu en iyi tanımlayan kategoriyi seçin\n"
                              "• Talebinizle ilgili detayları forma doldurun\n"
                              "• Bir yetkili size yardımcı oluncaya kadar bekleyin",
                        inline=False
                    )
                    embed.add_field(
                        name="⚠️ Önemli Notlar",
                        value="• Sadece gerçek sorunlar için talep oluşturun\n"
                              "• Sabırlı olun - yetkililer en kısa sürede yanıt verecektir\n"
                              "• İlk mesajınızda mümkün olduğunca fazla detay verin",
                        inline=False
                    )
                    button_label = "Talep Oluştur"
                
                embed.set_footer(text=f"Ticket System • {interaction.guild.name}")
                embed.timestamp = datetime.datetime.now()
                
                # Create ticket button view
                from utils.community.turkoyto.ticket_views import TicketCreateView
                ticket_view = TicketCreateView(self.bot)
                
                # Send the message
                await channel.send(embed=embed, view=ticket_view)
                
                await inter.response.send_message(
                    embed=create_embed(f"✅ Ticket message sent to {channel.mention}!", discord.Color.green()),
                    ephemeral=True
                )
                
            except Exception as e:
                logger.error(f"Error sending ticket message: {e}")
                await inter.response.send_message(
                    embed=create_embed(f"❌ Error: {str(e)}", discord.Color.red()),
                    ephemeral=True
                )
        
        view = ChannelSelectView(channels, send_ticket_message)
        
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📍 Select Channel",
                description="Select the channel where you want to send the ticket message.",
                color=discord.Color.blue()
            ),
            view=view,
            ephemeral=True
        )


class TicketFormConfigView(discord.ui.View):
    """View for configuring ticket form questions"""
    
    def __init__(self, bot, guild_id, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = initialize_mongodb()
        
    @discord.ui.button(label="View Current Questions", emoji="📋", style=discord.ButtonStyle.primary, row=0)
    async def view_questions(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current ticket form questions"""
        settings = self.mongo_db["tickets"].find_one({"guild_id": str(self.guild_id)}) or {}
        questions = settings.get("form_questions", self.get_default_questions())
        
        embed = discord.Embed(
            title="📋 Current Ticket Form Questions",
            description="These questions will be asked when users create a ticket:",
            color=discord.Color.blue()
        )
        
        for i, question in enumerate(questions, 1):
            embed.add_field(
                name=f"Question {i}",
                value=f"**{question['question']}**\nType: {question['type']}\nRequired: {'Yes' if question.get('required', True) else 'No'}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Add Question", emoji="➕", style=discord.ButtonStyle.success, row=0)
    async def add_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a new question"""
        await interaction.response.send_modal(AddTicketQuestionModal(self.bot, self.guild_id))
    
    @discord.ui.button(label="Remove Question", emoji="➖", style=discord.ButtonStyle.danger, row=0)
    async def remove_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove a question"""
        settings = self.mongo_db["tickets"].find_one({"guild_id": str(self.guild_id)}) or {}
        questions = settings.get("form_questions", self.get_default_questions())
        

class SetEmbedColorModal(discord.ui.Modal, title="Set Embed Color"):
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        
    color_input = discord.ui.TextInput(
        label="Embed Color",
        placeholder="Enter hex color (e.g., #3498db or 0x3498db)",
        required=True,
        max_length=10
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            color_value = self.color_input.value.strip()
            
            # Validate and convert color
            if color_value.startswith('#'):
                color_value = '0x' + color_value[1:]
            elif not color_value.startswith('0x'):
                color_value = '0x' + color_value
            
            # Test if it's a valid hex color
            int(color_value, 16)
            
            # Save to database
            mongo_db = initialize_mongodb()
            mongo_db["server_settings"].update_one(
                {"server_id": self.guild_id},
                {"$set": {"embed_color": color_value}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ Embed color set to: **{color_value}**",
                    color=int(color_value, 16)
                ),
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ Invalid color format! Use hex format like #3498db",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )


class SetReportChannelModal(discord.ui.Modal, title="Set Report Channel"):
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        
    channel_id = discord.ui.TextInput(
        label="Channel ID",
        placeholder="Enter the channel ID for reports",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_id.value.strip())
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        description="❌ Channel not found!",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Save to database
            mongo_db = initialize_mongodb()
            mongo_db["server_settings"].update_one(
                {"server_id": self.guild_id},
                {"$set": {"report_channel_id": channel_id}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ Report channel set to: {channel.mention}",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ Invalid channel ID!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )


class SetWelcomeModal(discord.ui.Modal, title="Quick Welcome Setup"):
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        
    channel_id = discord.ui.TextInput(
        label="Welcome Channel ID",
        placeholder="Enter the channel ID for welcome messages",
        required=True,
        max_length=20
    )
    
    message = discord.ui.TextInput(
        label="Welcome Message",
        placeholder="Use {user} for mention, {server} for server name",
        default="Welcome {user} to {server}!",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=2000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_id.value.strip())
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        description="❌ Channel not found!",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Save to database
            mongo_db = initialize_mongodb()
            mongo_db["welcomer"].update_one(
                {"guild_id": self.guild_id},
                {
                    "$set": {
                        "welcome_channel_id": channel_id,
                        "welcome_message": self.message.value,
                        "enabled": True
                    }
                },
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ Welcome system enabled!\n**Channel**: {channel.mention}",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ Invalid channel ID!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )


class SetGoodbyeModal(discord.ui.Modal, title="Quick Goodbye Setup"):
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        
    channel_id = discord.ui.TextInput(
        label="Goodbye Channel ID",
        placeholder="Enter the channel ID for goodbye messages",
        required=True,
        max_length=20
    )
    
    message = discord.ui.TextInput(
        label="Goodbye Message",
        placeholder="Use {user} for username, {server} for server name",
        default="Goodbye {user}, we'll miss you!",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=2000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_id.value.strip())
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        description="❌ Channel not found!",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Save to database
            mongo_db = initialize_mongodb()
            mongo_db["byebye"].update_one(
                {"guild_id": self.guild_id},
                {
                    "$set": {
                        "byebye_channel_id": channel_id,
                        "goodbye_message": self.message.value,
                        "enabled": True
                    }
                },
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ Goodbye system enabled!\n**Channel**: {channel.mention}",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ Invalid channel ID!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )


class SetAutoRoleModal(discord.ui.Modal, title="Set Auto Roles"):
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        
    role_ids = discord.ui.TextInput(
        label="Role IDs",
        placeholder="Enter role IDs separated by commas (e.g., 123456, 789012)",
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse role IDs
            role_ids = [int(rid.strip()) for rid in self.role_ids.value.split(',')]
            
            # Validate roles
            valid_roles = []
            for role_id in role_ids:
                role = interaction.guild.get_role(role_id)
                if role:
                    valid_roles.append(role_id)
            
            if not valid_roles:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        description="❌ No valid roles found!",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Save to database
            mongo_db = initialize_mongodb()
            mongo_db["moderation"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {"auto_roles": valid_roles}},
                upsert=True
            )
            
            role_mentions = [f"<@&{rid}>" for rid in valid_roles]
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ Auto roles set: {', '.join(role_mentions)}",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ Invalid role ID format!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )


class SetWordFilterModal(discord.ui.Modal, title="Set Word Filter"):
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        
    words = discord.ui.TextInput(
        label="Filtered Words",
        placeholder="Enter words to filter, separated by commas",
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Parse words
        word_list = [word.strip().lower() for word in self.words.value.split(',') if word.strip()]
        
        if not word_list:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ No valid words provided!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
        
        # Save to database
        mongo_db = initialize_mongodb()
        mongo_db["moderation"].update_one(
            {"guild_id": self.guild_id},
            {
                "$set": {
                    "word_filter.enabled": True,
                    "word_filter.words": word_list
                }
            },
            upsert=True
        )
        
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ Word filter enabled with {len(word_list)} words",
                color=discord.Color.green()
            ),
            ephemeral=True
        )


class SetLoggingChannelModal(discord.ui.Modal, title="Set Logging Channel"):
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        
    channel_id = discord.ui.TextInput(
        label="Channel ID",
        placeholder="Enter the channel ID for logs",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_id.value.strip())
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        description="❌ Channel not found!",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Save to database
            mongo_db = initialize_mongodb()
            mongo_db["logger"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {"log_channel_id": channel_id}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ Logging channel set to: {channel.mention}",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ Invalid channel ID!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )


class AddTicketQuestionModal(discord.ui.Modal, title="Add Ticket Question"):
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        
    question = discord.ui.TextInput(
        label="Question",
        placeholder="What question should users answer?",
        required=True,
        max_length=100
    )
    
    question_type = discord.ui.TextInput(
        label="Type (short/paragraph)",
        placeholder="short or paragraph",
        default="short",
        required=True,
        max_length=10
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate question type
            q_type = self.question_type.value.lower()
            if q_type not in ["short", "paragraph"]:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        description="❌ Question type must be 'short' or 'paragraph'!",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            # Get current questions
            mongo_db = initialize_mongodb()
            settings = mongo_db["tickets"].find_one({"guild_id": str(self.guild_id)}) or {}
            questions = settings.get("form_questions", [])
            
            # Add new question (max 5)
            if len(questions) >= 5:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        description="❌ Maximum 5 questions allowed!",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
            
            questions.append({
                "question": self.question.value,
                "type": q_type,
                "required": True
            })
            
            # Save to database
            mongo_db["tickets"].update_one(
                {"guild_id": str(self.guild_id)},
                {"$set": {"form_questions": questions}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ Question added! Total questions: {len(questions)}",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"❌ Error: {str(e)}",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

# Birthday System View
class BirthdaySystemView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="📢 Set Birthday Channel", style=discord.ButtonStyle.primary, row=0)
    async def set_birthday_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetBirthdayChannelModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🎭 Setup Zodiac Roles", style=discord.ButtonStyle.secondary, row=0)
    async def setup_zodiac_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        # Create zodiac roles
        zodiac_roles = ["Akrep", "Yay", "Oğlak", "Kova", "Balık", "Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak", "Terazi"]
        created_roles = []
        
        for role_name in zodiac_roles:
            if not discord.utils.get(interaction.guild.roles, name=role_name):
                try:
                    role = await interaction.guild.create_role(name=role_name)
                    created_roles.append(role.name)
                except discord.Forbidden:
                    await interaction.followup.send(
                        embed=create_embed("❌ I don't have permission to create roles.", discord.Color.red()),
                        ephemeral=True
                    )
                    return
        
        if created_roles:
            await interaction.followup.send(
                embed=create_embed(f"✅ Created {len(created_roles)} zodiac roles: {', '.join(created_roles)}", discord.Color.green()),
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                embed=create_embed("ℹ️ All zodiac roles already exist.", discord.Color.blue()),
                ephemeral=True
            )
    
    @discord.ui.button(label="📊 View Birthday List", style=discord.ButtonStyle.secondary, row=0)
    async def view_birthdays(self, interaction: discord.Interaction, button: discord.ui.Button):
        mongo_db = get_async_db()
        birthday_data = await mongo_db.birthday.find_one({"guild_id": self.guild_id}) or {}
        members_data = birthday_data.get("members", [])
        
        if not members_data:
            await interaction.response.send_message(
                embed=create_embed("ℹ️ No birthdays registered yet.", discord.Color.blue()),
                ephemeral=True
            )
            return
        
        # Sort by month and day
        sorted_members = sorted(members_data, key=lambda x: (x["month"], x["day"]))
        
        birthday_list = []
        for member_info in sorted_members[:20]:  # Show first 20
            member = interaction.guild.get_member(member_info["member_id"])
            if member:
                birthday_list.append(f"• {member.mention}: {member_info['day']}/{member_info['month']}")
        
        embed = discord.Embed(
            title="🎂 Birthday List",
            description="\n".join(birthday_list) if birthday_list else "No active members with birthdays.",
            color=discord.Color.gold()
        )
        
        if len(members_data) > 20:
            embed.set_footer(text=f"Showing 20 of {len(members_data)} birthdays")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🗑️ Clear Birthday Data", style=discord.ButtonStyle.danger, row=1)
    async def clear_birthdays(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ConfirmClearBirthdaysView(self.bot, self.guild_id)
        embed = discord.Embed(
            title="⚠️ Clear Birthday Data",
            description="Are you sure you want to clear all birthday data?\n\n"
                        "This will remove all registered birthdays but keep the zodiac roles.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Legal Info View
class LegalInfoView(discord.ui.View):
    def __init__(self, bot, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        
    @discord.ui.button(label="🔒 Privacy Policy", style=discord.ButtonStyle.primary, row=0)
    async def privacy_policy(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔒 Privacy Policy",
            description="**Data Collection and Usage**\n\n"
                        "We collect and store the following data:\n"
                        "• Server IDs and settings\n"
                        "• User IDs for features like leveling and birthdays\n"
                        "• Message content for moderation features (if enabled)\n\n"
                        "**Data Storage**\n"
                        "• All data is stored securely in MongoDB\n"
                        "• Data is not shared with third parties\n"
                        "• Data is only used for bot functionality\n\n"
                        "**Data Deletion**\n"
                        "• Server data is deleted when the bot is removed\n"
                        "• Users can request data deletion via support server\n\n"
                        "**Contact**\n"
                        "For privacy concerns, join our support server.",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📋 Terms of Usage", style=discord.ButtonStyle.primary, row=0)
    async def terms_of_usage(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📋 Terms of Usage",
            description="**Usage Agreement**\n\n"
                        "By using this bot, you agree to:\n"
                        "• Not use the bot for illegal activities\n"
                        "• Not abuse or exploit bot features\n"
                        "• Follow Discord's Terms of Service\n\n"
                        "**Bot Features**\n"
                        "• Features may be added or removed at any time\n"
                        "• The bot is provided 'as is' without warranty\n"
                        "• We reserve the right to restrict access\n\n"
                        "**Liability**\n"
                        "• We are not responsible for data loss\n"
                        "• We are not responsible for server issues\n"
                        "• Use the bot at your own risk\n\n"
                        "**Support**\n"
                        "For support, join our Discord server.",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🛡️ Data Protection", style=discord.ButtonStyle.secondary, row=0)
    async def data_protection(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛡️ Data Protection & GDPR",
            description="**Your Rights**\n\n"
                        "Under GDPR, you have the right to:\n"
                        "• Access your personal data\n"
                        "• Correct inaccurate data\n"
                        "• Delete your data\n"
                        "• Export your data\n\n"
                        "**Data Security**\n"
                        "• Encrypted database connections\n"
                        "• Regular security updates\n"
                        "• Limited data access\n\n"
                        "**Data Requests**\n"
                        "To exercise your rights, contact us via:\n"
                        "• Support server (preferred)\n"
                        "• Bot developer DM\n\n"
                        "Requests are processed within 30 days.",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📞 Support Server", style=discord.ButtonStyle.secondary, row=1)
    async def support_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Send a link in response since link buttons need special handling
        embed = discord.Embed(
            title="📞 Support Server",
            description="Click the link below to join our support server:\n[Join Support Server](https://discord.gg/vXhwuxJk88)",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Modal classes for the new views
class SetPrefixModal(discord.ui.Modal, title="Set Bot Prefix"):
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        
    prefix_input = discord.ui.TextInput(
        label="New Prefix",
        placeholder="Enter the new prefix (e.g., !, ?, >)",
        required=True,
        max_length=5,
        min_length=1
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        new_prefix = self.prefix_input.value
        
        mongo_db = get_async_db()
        await mongo_db.settings.update_one(
            {"guild_id": self.guild_id},
            {"$set": {"prefix": new_prefix}},
            upsert=True
        )
        
        await interaction.response.send_message(
            embed=create_embed(f"✅ Bot prefix updated to `{new_prefix}`", discord.Color.green()),
            ephemeral=True
        )

class SetBirthdayChannelModal(discord.ui.Modal, title="Set Birthday Channel"):
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        
    channel_id = discord.ui.TextInput(
        label="Birthday Channel ID",
        placeholder="Enter the channel ID for birthday announcements",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_id.value)
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                await interaction.response.send_message(
                    embed=create_embed("❌ Channel not found. Please check the ID.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message(
                    embed=create_embed("❌ Please select a text channel.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            mongo_db = get_async_db()
            await mongo_db.birthday.update_one(
                {"guild_id": self.guild_id},
                {"$set": {"channel_id": channel_id}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed(f"✅ Birthday channel set to {channel.mention}", discord.Color.green()),
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                embed=create_embed("❌ Invalid channel ID format.", discord.Color.red()),
                ephemeral=True
            )

# Confirmation views
class ConfirmBotResetView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="✅ Confirm Reset", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        mongo_db = get_async_db()
        
        # Reset prefix and language
        await mongo_db.settings.update_one(
            {"guild_id": self.guild_id},
            {"$unset": {"prefix": "", "language": ""}},
            upsert=True
        )
        
        await interaction.response.send_message(
            embed=create_embed("✅ Bot configuration reset to defaults.", discord.Color.green()),
            ephemeral=True
        )
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=create_embed("❌ Reset cancelled.", discord.Color.red()),
            ephemeral=True
        )
        self.stop()

class ConfirmClearBirthdaysView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild_id = guild_id
        
    @discord.ui.button(label="✅ Confirm Clear", style=discord.ButtonStyle.danger)
    async def confirm_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        mongo_db = get_async_db()
        
        # Clear birthday members data
        await mongo_db.birthday.update_one(
            {"guild_id": self.guild_id},
            {"$set": {"members": []}},
            upsert=True
        )
        
        await interaction.response.send_message(
            embed=create_embed("✅ All birthday data has been cleared.", discord.Color.green()),
            ephemeral=True
        )
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=create_embed("❌ Clear cancelled.", discord.Color.red()),
            ephemeral=True
        )
        self.stop()

class PrefixSettingsView(discord.ui.View):
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.db = None
    
    @discord.ui.button(label="Change Prefix", style=discord.ButtonStyle.primary, emoji="✏️")
    async def change_prefix(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open modal to change prefix"""
        modal = PrefixModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Reset to Default", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def reset_prefix(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset prefix to default"""
        if not self.db:
            self.db = self.bot.async_db
        
        await self.db.settings.update_one(
            {"guild_id": str(self.guild_id)},
            {"$set": {"prefix": ">"}},
            upsert=True
        )
        
        embed = discord.Embed(
            title="✅ Prefix Reset",
            description="Prefix has been reset to the default: `>`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PrefixModal(discord.ui.Modal):
    def __init__(self, bot, guild_id):
        super().__init__(title="Change Bot Prefix")
        self.bot = bot
        self.guild_id = guild_id
        
        self.prefix_input = discord.ui.TextInput(
            label="New Prefix",
            placeholder="Enter new prefix (e.g., !, ?, $)",
            default=">",
            max_length=5,
            min_length=1,
            required=True
        )
        self.add_item(self.prefix_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        new_prefix = self.prefix_input.value
        
        # Update in database
        db = self.bot.async_db
        await db.settings.update_one(
            {"guild_id": str(self.guild_id)},
            {"$set": {"prefix": new_prefix}},
            upsert=True
        )
        
        embed = discord.Embed(
            title="✅ Prefix Updated",
            description=f"Bot prefix has been changed to: `{new_prefix}`",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Usage",
            value=f"You can now use commands with `{new_prefix}help` or `/help`",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class StatusRoleSettingsView(discord.ui.View):
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.status_roles = []
        self.db = None
    
    async def initialize(self):
        """Load current status roles from database"""
        if not self.db:
            self.db = self.bot.async_db
        
        # Get all status roles for this guild
        self.status_roles = await self.db.status_roles.find({"guild_id": int(self.guild_id)}).to_list(None)
    
    @discord.ui.button(label="Add Status Role", style=discord.ButtonStyle.primary, emoji="➕")
    async def add_status_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a new status role"""
        modal = StatusRoleModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remove Status Role", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_status_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove a status role"""
        if not self.status_roles:
            return await interaction.response.send_message("No status roles to remove.", ephemeral=True)
        
        # Create select menu for removal
        view = StatusRoleRemoveView(self.bot, self.guild_id, self.status_roles)
        embed = discord.Embed(
            title="🗑️ Remove Status Role",
            description="Select a status role to remove:",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class StatusRoleModal(discord.ui.Modal):
    def __init__(self, bot, guild_id):
        super().__init__(title="Add Status Role")
        self.bot = bot
        self.guild_id = guild_id
        
        self.status_input = discord.ui.TextInput(
            label="Custom Status Text",
            placeholder="Enter the status text to trigger role assignment",
            max_length=100,
            required=True
        )
        self.add_item(self.status_input)
        
        self.role_input = discord.ui.TextInput(
            label="Role Name or ID",
            placeholder="Enter the role name or ID to assign",
            max_length=100,
            required=True
        )
        self.add_item(self.role_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        status_text = self.status_input.value.strip().lower()
        role_input = self.role_input.value.strip()
        
        # Find the role
        guild = interaction.guild
        role = None
        
        # Try to find by ID first
        if role_input.isdigit():
            role = guild.get_role(int(role_input))
        
        # Try to find by name
        if not role:
            role = discord.utils.get(guild.roles, name=role_input)
        
        if not role:
            return await interaction.response.send_message(
                f"Could not find role: {role_input}",
                ephemeral=True
            )
        
        # Save to database
        db = self.bot.async_db
        await db.status_roles.update_one(
            {"guild_id": int(self.guild_id), "custom_status": status_text},
            {"$set": {"role_id": role.id}},
            upsert=True
        )
        
        embed = discord.Embed(
            title="✅ Status Role Added",
            description=f"Members with status `{status_text}` will receive {role.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class StatusRoleRemoveView(discord.ui.View):
    def __init__(self, bot, guild_id, status_roles, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        
        # Create select options
        options = []
        for sr in status_roles[:25]:  # Discord limit
            guild = bot.get_guild(int(guild_id))
            role = guild.get_role(sr['role_id']) if guild else None
            role_name = role.name if role else f"Unknown Role ({sr['role_id']})"
            
            options.append(
                discord.SelectOption(
                    label=f"{sr['custom_status']} → {role_name}",
                    value=sr['custom_status'],
                    description=f"Remove this status role mapping"
                )
            )
        
        select = discord.ui.Select(
            placeholder="Select status role to remove",
            options=options
        )
        select.callback = self.remove_callback
        self.add_item(select)
    
    async def remove_callback(self, interaction: discord.Interaction):
        selected_status = interaction.data['values'][0]
        
        # Remove from database
        db = self.bot.async_db
        await db.status_roles.delete_one({
            "guild_id": int(self.guild_id),
            "custom_status": selected_status
        })
        
        embed = discord.Embed(
            title="✅ Status Role Removed",
            description=f"Status role for `{selected_status}` has been removed.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BirthdaySettingsView(discord.ui.View):
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.birthday_channel_id = None
        self.birthday_role_id = None
        self.db = None
    
    async def initialize(self):
        """Load current birthday settings"""
        if not self.db:
            self.db = self.bot.async_db
        
        settings = await self.db.birthday.find_one({"guild_id": str(self.guild_id)}) or {}
        self.birthday_channel_id = settings.get("channel_id")
        self.birthday_role_id = settings.get("birthday_role_id")
    
    @discord.ui.button(label="Set Birthday Channel", style=discord.ButtonStyle.primary, emoji="📢")
    async def set_birthday_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set birthday announcement channel"""
        view = ChannelSelectView(
            self.bot,
            title="Select Birthday Channel",
            callback=self._set_birthday_channel
        )
        
        embed = discord.Embed(
            title="📢 Select Birthday Channel",
            description="Choose a channel for birthday announcements:",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def _set_birthday_channel(self, channel):
        """Save birthday channel to database"""
        await self.db.birthday.update_one(
            {"guild_id": str(self.guild_id)},
            {"$set": {"channel_id": channel.id}},
            upsert=True
        )
        self.birthday_channel_id = channel.id
    
    @discord.ui.button(label="Set Birthday Role", style=discord.ButtonStyle.primary, emoji="🎂")
    async def set_birthday_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set birthday role"""
        modal = BirthdayRoleModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Test Birthday Message", style=discord.ButtonStyle.secondary, emoji="🎉")
    async def test_birthday(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send a test birthday message"""
        if not self.birthday_channel_id:
            return await interaction.response.send_message(
                "Please set a birthday channel first.",
                ephemeral=True
            )
        
        channel = interaction.guild.get_channel(self.birthday_channel_id)
        if not channel:
            return await interaction.response.send_message(
                "Birthday channel not found.",
                ephemeral=True
            )
        
        # Send test message
        embed = discord.Embed(
            title="🎂 Happy Birthday!",
            description=f"Today is {interaction.user.mention}'s birthday!\n\nWish them a happy birthday! 🎉",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await channel.send(embed=embed)
        await interaction.response.send_message(
            f"Test birthday message sent to {channel.mention}",
            ephemeral=True
        )

class BirthdayRoleModal(discord.ui.Modal):
    def __init__(self, bot, guild_id):
        super().__init__(title="Set Birthday Role")
        self.bot = bot
        self.guild_id = guild_id
        
        self.role_input = discord.ui.TextInput(
            label="Birthday Role Name",
            placeholder="Enter role name or leave empty to create new",
            required=False
        )
        self.add_item(self.role_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        role_name = self.role_input.value.strip() or "🎂 Birthday"
        
        # Find or create role
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name=role_name)
        
        if not role:
            # Create new role
            role = await guild.create_role(
                name=role_name,
                color=discord.Color.gold(),
                hoist=True
            )
        
        # Save to database
        db = self.bot.async_db
        await db.birthday.update_one(
            {"guild_id": str(self.guild_id)},
            {"$set": {"birthday_role_id": role.id}},
            upsert=True
        )
        
        embed = discord.Embed(
            title="✅ Birthday Role Set",
            description=f"Birthday role set to {role.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AISettingsView(discord.ui.View):
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.perplexity_enabled = False
        self.db = None
    
    async def initialize(self):
        """Load current AI settings"""
        if not self.db:
            self.db = self.bot.async_db
        
        settings = await self.db.settings.find_one({"guild_id": str(self.guild_id)}) or {}
        self.perplexity_enabled = settings.get("perplexity_enabled", False)
    
    @discord.ui.button(label="Toggle Perplexity AI", style=discord.ButtonStyle.primary, emoji="🤖")
    async def toggle_perplexity(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle Perplexity AI on/off"""
        self.perplexity_enabled = not self.perplexity_enabled
        
        await self.db.settings.update_one(
            {"guild_id": str(self.guild_id)},
            {"$set": {"perplexity_enabled": self.perplexity_enabled}},
            upsert=True
        )
        
        embed = discord.Embed(
            title=f"{'✅' if self.perplexity_enabled else '❌'} Perplexity AI",
            description=f"Perplexity AI has been {'enabled' if self.perplexity_enabled else 'disabled'}.",
            color=discord.Color.green() if self.perplexity_enabled else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="AI Settings Guide", style=discord.ButtonStyle.secondary, emoji="📖")
    async def ai_guide(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show AI features guide"""
        embed = discord.Embed(
            title="📖 AI Features Guide",
            description="Learn how to use AI features in your server.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Perplexity AI",
            value=(
                "• **Usage**: Mention the bot or use `/ask`\n"
                "• **Features**: Web search, Q&A, translations\n"
                "• **Limits**: 100 queries per day per server"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Tips",
            value=(
                "• Be specific with your questions\n"
                "• Use `/ask` for private responses\n"
                "• AI can search the web for current info"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class LegalInfoView(discord.ui.View):
    def __init__(self, bot, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
    
    @discord.ui.button(label="Privacy Policy", style=discord.ButtonStyle.primary, emoji="🔒")
    async def privacy_policy(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show privacy policy"""
        embed = discord.Embed(
            title="🔒 Privacy Policy",
            description="Effective Date: January 23, 2025",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="1. Information We Collect",
            value=(
                "• User IDs and usernames for functionality\n"
                "• Message content for command processing\n"
                "• Server information for configuration\n"
                "• No personal data is sold or shared"
            ),
            inline=False
        )
        
        embed.add_field(
            name="2. How We Use Information",
            value=(
                "• Provide bot features and services\n"
                "• Improve bot functionality\n"
                "• Ensure server safety and moderation\n"
                "• Generate anonymous statistics"
            ),
            inline=False
        )
        
        embed.add_field(
            name="3. Data Storage",
            value=(
                "• Data is stored securely in MongoDB\n"
                "• Retained only as long as necessary\n"
                "• You can request data deletion\n"
                "• Contact: omerguler53@gmail.com"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Terms of Service", style=discord.ButtonStyle.primary, emoji="📜")
    async def terms_of_service(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show terms of service"""
        embed = discord.Embed(
            title="📜 Terms of Service",
            description="By using Contro Bot, you agree to these terms.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Usage Rules",
            value=(
                "• Don't use the bot for illegal activities\n"
                "• Don't attempt to exploit or hack the bot\n"
                "• Follow Discord's Terms of Service\n"
                "• Respect other users and servers"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Bot Rights",
            value=(
                "• We can modify or discontinue features\n"
                "• We can remove bot access for violations\n"
                "• We're not liable for data loss\n"
                "• Updates may change functionality"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Bot Info", style=discord.ButtonStyle.secondary, emoji="ℹ️")
    async def bot_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show bot information"""
        embed = discord.Embed(
            title="ℹ️ Contro Bot Information",
            description="Advanced Discord bot for server management",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Developer",
            value="Ömer Güler (omerguler53@gmail.com)",
            inline=True
        )
        embed.add_field(
            name="Version",
            value=f"`{getattr(self.bot, 'version', '1.0.0')}`",
            inline=True
        )
        embed.add_field(
            name="Servers",
            value=f"{len(self.bot.guilds)}",
            inline=True
        )
        embed.add_field(
            name="Support",
            value="[Join Server](https://discord.gg/vXhwuxJk88)",
            inline=True
        )
        embed.add_field(
            name="Website",
            value="[controbot.com](https://controbot.com)",
            inline=True
        )
        embed.add_field(
            name="Source",
            value="[GitHub](https://github.com/bergaman9)",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ChannelSelectView(discord.ui.View):
    def __init__(self, bot, title="Select Channel", callback=None, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.callback = callback
        self.title = title
    
    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select a channel..."
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        
        if self.callback:
            await self.callback(channel)
        
        embed = discord.Embed(
            title="✅ Channel Selected",
            description=f"Selected channel: {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AdvancedSettingsView(discord.ui.View):
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
    
    @discord.ui.button(label="Bot Statistics", style=discord.ButtonStyle.primary, emoji="📊")
    async def bot_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show bot statistics"""
        embed = discord.Embed(
            title="📊 Bot Statistics",
            description="Detailed bot performance metrics",
            color=discord.Color.blue()
        )
        
        # Calculate stats
        total_users = sum(g.member_count for g in self.bot.guilds)
        total_channels = sum(len(g.channels) for g in self.bot.guilds)
        
        embed.add_field(name="Servers", value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name="Users", value=f"{total_users:,}", inline=True)
        embed.add_field(name="Channels", value=f"{total_channels:,}", inline=True)
        embed.add_field(name="Commands", value=f"{len(self.bot.commands)}", inline=True)
        embed.add_field(name="Uptime", value=f"<t:{int(self.bot.start_time.timestamp())}:R>", inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Reload Views", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def reload_views(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reload persistent views"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Clear current views
            self.bot.persistent_views.clear()
            
            # Reload views
            views_loaded = 0
            for cog_name, cog in self.bot.cogs.items():
                if hasattr(cog, 'setup_views'):
                    await cog.setup_views()
                    views_loaded += 1
            
            embed = discord.Embed(
                title="✅ Views Reloaded",
                description=f"Successfully reloaded persistent views from {views_loaded} cogs.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Reload Failed",
                description=f"Error: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Debug Mode", style=discord.ButtonStyle.danger, emoji="🐛")
    async def debug_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle debug mode"""
        current_debug = getattr(self.bot, 'debug_mode', False)
        self.bot.debug_mode = not current_debug
        
        embed = discord.Embed(
            title=f"{'🐛 Debug Mode Enabled' if self.bot.debug_mode else '✅ Debug Mode Disabled'}",
            description=f"Debug mode has been {'enabled' if self.bot.debug_mode else 'disabled'}.",
            color=discord.Color.orange() if self.bot.debug_mode else discord.Color.green()
        )
        
        if self.bot.debug_mode:
            embed.add_field(
                name="⚠️ Warning",
                value="Debug mode may expose sensitive information in logs.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


