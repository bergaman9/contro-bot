import discord
from discord import ui
import asyncio
import json
import logging
from utils.core.formatting import create_embed
from utils.database.connection import get_async_db, ensure_async_db
from utils.core.formatting import format_timestamp, format_number
from utils.database.connection import initialize_mongodb

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
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="🔧 Feature Management", style=discord.ButtonStyle.success, row=0)
    async def feature_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = FeatureManagementView(self.bot, self.guild_id)
        
        # Get current feature status
        mongo_db = get_async_db()
        features = await mongo_db.feature_toggles.find_one({"guild_id": self.guild_id}) or {}
        
        embed = discord.Embed(
            title="🔧 Feature Management",
            description="Toggle server features on/off. Disabled features will not function.",
            color=discord.Color.blue()
        )
        
        # Show current feature status
        feature_status = []
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
        
        for feature, default in default_features.items():
            is_enabled = features.get(feature, default)
            status = "🟢 Enabled" if is_enabled else "🔴 Disabled"
            feature_name = feature.replace("_", " ").title()
            feature_status.append(f"**{feature_name}**: {status}")
        
        embed.add_field(
            name="Current Status",
            value="\n".join(feature_status[:4]),
            inline=True
        )
        embed.add_field(
            name="\u200b",
            value="\n".join(feature_status[4:]),
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="👋 Welcome System", style=discord.ButtonStyle.primary, row=0)
    async def welcome_goodbye(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = WelcomeGoodbyeView(self.bot, self.guild_id)
        
        # Get current settings
        mongo_db = get_async_db()
        welcome_settings = await mongo_db.welcomer.find_one({"guild_id": self.guild_id}) or {}
        goodbye_settings = await mongo_db.byebye.find_one({"guild_id": self.guild_id}) or {}
        
        embed = discord.Embed(
            title="👋 Welcome/Goodbye System",
            description="Configure welcome and goodbye messages for your server.",
            color=discord.Color.blue()
        )
        
        # Welcome info
        welcome_channel_id = welcome_settings.get("welcome_channel_id")
        welcome_channel = f"<#{welcome_channel_id}>" if welcome_channel_id else "Not configured"
        welcome_enabled = welcome_settings.get("enabled", False)
        
        # Goodbye info
        goodbye_channel_id = goodbye_settings.get("byebye_channel_id")
        goodbye_channel = f"<#{goodbye_channel_id}>" if goodbye_channel_id else "Not configured"
        goodbye_enabled = goodbye_settings.get("enabled", False)
        
        embed.add_field(
            name="🎉 Welcome System",
            value=f"**Status**: {'🟢 Enabled' if welcome_enabled else '🔴 Disabled'}\n**Channel**: {welcome_channel}",
            inline=True
        )
        
        embed.add_field(
            name="👋 Goodbye System",
            value=f"**Status**: {'🟢 Enabled' if goodbye_enabled else '🔴 Disabled'}\n**Channel**: {goodbye_channel}",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🛡️ Moderation", style=discord.ButtonStyle.primary, row=0)
    async def moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ModerationView(self.bot, self.guild_id)
        
        mongo_db = get_async_db()
        mod_settings = await mongo_db.moderation.find_one({"guild_id": self.guild_id}) or {}
        
        embed = discord.Embed(
            title="🛡️ Moderation Settings",
            description="Configure auto-moderation and security features.",
            color=discord.Color.blue()
        )
        
        # Auto roles
        auto_roles = mod_settings.get("auto_roles", [])
        auto_roles_text = f"{len(auto_roles)} roles configured" if auto_roles else "Not configured"
        
        # Word filter
        word_filter = mod_settings.get("word_filter", {})
        filter_enabled = word_filter.get("enabled", False)
        filtered_words = len(word_filter.get("words", []))
        
        embed.add_field(
            name="🤖 Auto Roles",
            value=auto_roles_text,
            inline=True
        )
        
        embed.add_field(
            name="🔒 Word Filter",
            value=f"**Status**: {'🟢 Enabled' if filter_enabled else '🔴 Disabled'}\n**Words**: {filtered_words} words",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="💫 Leveling System", style=discord.ButtonStyle.primary, row=0)
    async def leveling_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = LevellingSettingsView(self.bot, interaction)
        
        # Get current settings
        settings = await view.get_current_settings(self.guild_id)
        
        embed = discord.Embed(
            title="💫 Leveling System",
            description="Configure XP and leveling features for your server.",
            color=discord.Color.blue()
        )
        
        # System status
        system_enabled = settings.get("enabled", True)
        message_xp = settings.get("message_xp_enabled", True)
        voice_xp = settings.get("voice_xp_enabled", True)
        notifications = settings.get("level_up_notifications", True)
        
        embed.add_field(
            name="System Status",
            value=f"**Enabled**: {'🟢 Yes' if system_enabled else '🔴 No'}\n"
                  f"**Message XP**: {'🟢 Yes' if message_xp else '🔴 No'}\n"
                  f"**Voice XP**: {'🟢 Yes' if voice_xp else '🔴 No'}",
            inline=True
        )
        
        embed.add_field(
            name="Settings",
            value=f"**Level Up Notifications**: {'🟢 Yes' if notifications else '🔴 No'}\n"
                  f"**Message Multiplier**: {settings.get('message_xp_multiplier', 1.0)}x\n"
                  f"**Voice Multiplier**: {settings.get('voice_xp_multiplier', 1.0)}x",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="📊 Logging", style=discord.ButtonStyle.secondary, row=1)
    async def logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.settings.logging_views import LoggingSettingsView
        
        view = LoggingSettingsView(self.bot, interaction.guild_id)
        await view.initialize()
        
        embed = discord.Embed(
            title="📊 Logging Settings",
            description="Configure event logging for your server.",
            color=discord.Color.blue()
        )
        
        channel_text = f"<#{view.log_channel_id}>" if view.log_channel_id else "Not configured"
        
        # Count active log types
        active_logs = sum(1 for setting, enabled in view.settings.items() if enabled)
        total_logs = len(view.settings)
        
        embed.add_field(
            name="Configuration",
            value=f"**Log Channel**: {channel_text}\n**Active Logs**: {active_logs}/{total_logs}",
            inline=False
        )
        
        # Show some active log types
        active_types = [k.replace("_", " ").title() for k, v in list(view.settings.items())[:5] if v]
        if active_types:
            embed.add_field(
                name="Active Log Types",
                value="• " + "\n• ".join(active_types) + (f"\n• And {active_logs - 5} more..." if active_logs > 5 else ""),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🎫 Ticket System", style=discord.ButtonStyle.secondary, row=1)
    async def ticket_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = TicketSystemView(self.bot, self.guild_id)
        await view.initialize()
        
        embed = discord.Embed(
            title="🎫 Ticket System",
            description="Configure support ticket system for your server.",
            color=discord.Color.blue()
        )
        
        # Format settings display
        category = f"<#{view.ticket_category_id}>" if view.ticket_category_id else "Not set"
        log_channel = f"<#{view.log_channel_id}>" if view.log_channel_id else "Not set"
        archive_category = f"<#{view.archive_category_id}>" if view.archive_category_id else "Not set"
        staff_role = f"<@&{view.staff_role_id}>" if view.staff_role_id else "Not set"
        
        embed.add_field(
            name="Current Configuration",
            value=f"**Ticket Category**: {category}\n"
                  f"**Log Channel**: {log_channel}\n"
                  f"**Archive Category**: {archive_category}\n"
                  f"**Staff Role**: {staff_role}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="👑 Role Management", style=discord.ButtonStyle.secondary, row=1)
    async def role_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RoleManagementView(self.bot, self.guild_id)
        
        mongo_db = get_async_db()
        role_settings = await mongo_db.role_management.find_one({"guild_id": self.guild_id}) or {}
        
        embed = discord.Embed(
            title="👑 Role Management",
            description="Configure self-assignable roles and role messages.",
            color=discord.Color.blue()
        )
        
        # Self roles
        self_roles = role_settings.get("self_roles", [])
        self_roles_text = f"{len(self_roles)} roles available" if self_roles else "Not configured"
        
        # Register channel
        register_channel_id = role_settings.get("register_channel_id")
        register_channel = f"<#{register_channel_id}>" if register_channel_id else "Not configured"
        
        embed.add_field(
            name="Configuration",
            value=f"**Self-Assignable Roles**: {self_roles_text}\n**Register Channel**: {register_channel}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="⭐ Starboard", style=discord.ButtonStyle.secondary, row=1)
    async def starboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = StarboardView(self.bot, self.guild_id)
        
        mongo_db = get_async_db()
        starboard_settings = await mongo_db.starboard.find_one({"guild_id": self.guild_id}) or {}
        
        embed = discord.Embed(
            title="⭐ Starboard System",
            description="Configure starboard settings for highlighting popular messages.",
            color=discord.Color.gold()
        )
        
        # Get current settings
        starboard_channel_id = starboard_settings.get("starboard_channel")
        starboard_channel = f"<#{starboard_channel_id}>" if starboard_channel_id else "Not configured"
        threshold = starboard_settings.get("threshold", 3)
        enabled = starboard_settings.get("enabled", False)
        
        embed.add_field(
            name="Configuration",
            value=f"**Status**: {'🟢 Enabled' if enabled else '🔴 Disabled'}\n"
                  f"**Starboard Channel**: {starboard_channel}\n"
                  f"**Star Threshold**: {threshold} ⭐",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🎮 Temp Channels", style=discord.ButtonStyle.secondary, row=2)
    async def temp_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.settings.temp_channels_view import TempChannelsView
        
        view = TempChannelsView(self.bot, self.guild_id)
        
        mongo_db = get_async_db()
        temp_settings = await mongo_db.temp_channels.find_one({"guild_id": self.guild_id}) or {}
        
        embed = discord.Embed(
            title="🎮 Temporary Voice Channels",
            description="Configure auto-created voice channels for your server members.",
            color=discord.Color.purple()
        )
        
        # Get current settings
        hub_channel_id = temp_settings.get("hub_channel_id")
        hub_channel = f"<#{hub_channel_id}>" if hub_channel_id else "Not configured"
        category_id = temp_settings.get("category_id")
        category = f"<#{category_id}>" if category_id else "Auto-create"
        enabled = bool(hub_channel_id)
        
        embed.add_field(
            name="Configuration",
            value=f"**Status**: {'🟢 Enabled' if enabled else '🔴 Disabled'}\n"
                  f"**Hub Channel**: {hub_channel}\n"
                  f"**Category**: {category}",
            inline=False
        )
        
        embed.add_field(
            name="How it works",
            value="• Users join the hub channel\n"
                  "• A private channel is created for them\n"
                  "• Channel is deleted when empty\n"
                  "• Game emojis and custom formats supported",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🎨 Server Settings", style=discord.ButtonStyle.secondary, row=2)
    async def server_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ServerSettingsView(self.bot, self.guild_id)
        
        mongo_db = get_async_db()
        server_settings = await mongo_db.server_settings.find_one({"server_id": self.guild_id}) or {}
        
        embed = discord.Embed(
            title="🎨 Server Settings",
            description="Configure basic server settings and defaults.",
            color=discord.Color.blurple()
        )
        
        # Get current settings
        embed_color = server_settings.get("embed_color", "0x3498db")
        report_channel_id = server_settings.get("report_channel_id")
        report_channel = f"<#{report_channel_id}>" if report_channel_id else "Not configured"
        
        embed.add_field(
            name="Current Settings",
            value=f"**Embed Color**: {embed_color}\n"
                  f"**Report Channel**: {report_channel}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📄 Registration", style=discord.ButtonStyle.secondary, row=2)
    async def registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.settings.register_views import RegisterSettingsView
        
        view = RegisterSettingsView(self.bot, self.guild_id)
        
        mongo_db = get_async_db()
        register_settings = await mongo_db.register_settings.find_one({"guild_id": self.guild_id}) or {}
        
        embed = discord.Embed(
            title="📄 Registration System",
            description="Configure member registration and verification settings.",
            color=discord.Color.green()
        )
        
        # Get current settings
        register_channel_id = register_settings.get("register_channel_id")
        register_channel = f"<#{register_channel_id}>" if register_channel_id else "Not configured"
        register_role_id = register_settings.get("register_role_id")
        register_role = f"<@&{register_role_id}>" if register_role_id else "Not configured"
        enabled = register_settings.get("enabled", False)
        
        embed.add_field(
            name="Configuration",
            value=f"**Status**: {'🟢 Enabled' if enabled else '🔴 Disabled'}\n"
                  f"**Register Channel**: {register_channel}\n"
                  f"**Registered Role**: {register_role}",
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

    @discord.ui.button(label="📂 Set Ticket Category", style=discord.ButtonStyle.primary)
    async def set_ticket_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetTicketCategoryModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="👥 Set Support Roles", style=discord.ButtonStyle.secondary)
    async def set_support_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSupportRolesModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 View Current Settings", style=discord.ButtonStyle.success)
    async def view_ticket_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_ticket_settings(interaction)

    async def show_ticket_settings(self, interaction):
        mongo_db = get_async_db()
        settings = await mongo_db.tickets.find_one({"guild_id": interaction.guild.id}) or {}
        
        embed = discord.Embed(
            title="🎫 Ticket System Settings" if self.language == "en" else "🎫 Ticket Sistemi Ayarları",
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

    @discord.ui.button(label="🎭 Create Role Message", style=discord.ButtonStyle.primary)
    async def create_role_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CreateRoleMessageModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📝 Set Register Channel", style=discord.ButtonStyle.secondary)
    async def set_register_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetRegisterChannelModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 View Current Settings", style=discord.ButtonStyle.success)
    async def view_role_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_role_settings(interaction)

    @discord.ui.button(label="🗑️ Remove Register Channel", style=discord.ButtonStyle.danger, row=1)
    async def remove_register_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        mongo_db = get_async_db()
        result = await mongo_db.register.update_one(
            {"guild_id": interaction.guild.id},
            {"$unset": {"channel_id": ""}}
        )
        
        if result.modified_count > 0:
            message = "Registration channel has been removed." if self.language == "en" else "Kayıt kanalı kaldırıldı."
            color = discord.Color.green()
        else:
            message = "Registration channel was not configured." if self.language == "en" else "Kayıt kanalı ayarlanmamıştı."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

    async def show_role_settings(self, interaction):
        mongo_db = get_async_db()
        
        embed = discord.Embed(
            title="👑 Role Management Settings" if self.language == "en" else "👑 Rol Yönetimi Ayarları",
            color=discord.Color.blue()
        )
        
        # Register channel
        register_settings = await mongo_db.register.find_one({"guild_id": interaction.guild.id}) or {}
        channel_id = register_settings.get("channel_id")
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            register_channel = channel.mention if channel else "Channel not found"
        else:
            register_channel = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
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
        modal = SetupStarboardModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 View Current Settings", style=discord.ButtonStyle.success)
    async def view_starboard_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_starboard_settings(interaction)

    @discord.ui.button(label="🗑️ Remove Starboard", style=discord.ButtonStyle.danger)
    async def remove_starboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.remove_setting(interaction, "starboard", "Starboard")

    async def show_starboard_settings(self, interaction):
        mongo_db = get_async_db()
        settings = await mongo_db.starboard.find_one({"guild_id": str(interaction.guild.id)}) or {}
        
        embed = discord.Embed(
            title="⭐ Starboard Settings" if self.language == "en" else "⭐ Starboard Ayarları",
            color=discord.Color.blue()
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
                value="Not configured" if self.language == "en" else "Ayarlanmamış",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def remove_setting(self, interaction, collection_name, system_name):
        mongo_db = get_async_db()
        result = await mongo_db[collection_name].delete_one({"guild_id": str(interaction.guild.id)})
        
        if result.deleted_count > 0:
            message = f"{system_name} system has been removed." if self.language == "en" else f"{system_name} sistemi kaldırıldı."
            color = discord.Color.green()
        else:
            message = f"{system_name} system was not configured." if self.language == "en" else f"{system_name} sistemi ayarlanmamıştı."
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
