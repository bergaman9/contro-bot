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
    LevellingSettingsView
)
from utils.settings.logging_views import LoggingSettingsView
from utils.setup.views import LanguageSelectView
from utils.settings.register_views import RegisterSettingsView
from utils.database.connection import get_async_db, initialize_mongodb

# Set up logging
logger = logging.getLogger('settings')
class Settings(commands.GroupCog, name="settings"):
    """Server settings management commands"""
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.bot.loop.create_task(self.initialize_db())
        super().__init__()

    async def initialize_db(self):
        """Initialize the database connection"""
        try:
            self.db = await get_async_db()
            logger.info("Database connection initialized for Settings cog")
        except Exception as e:
            logger.error(f"Error initializing database connection: {e}")

    @commands.hybrid_group(name="settings_gui", description="Sunucu ayarlarını yönet")
    @commands.has_permissions(administrator=True)
    async def settings_group(self, ctx):
        """Server settings management commands"""
        if ctx.invoked_subcommand is None:
            await self.open_settings_panel(ctx)

    @settings_group.command(name="panel", description="Ayarlar panelini açar")
    @app_commands.describe(ephemeral="Ayarlar panelini sadece size görünür şekilde açar")
    async def panel(self, ctx, ephemeral: bool = False):
        """Open the settings panel"""
        await self.open_settings_panel(ctx, ephemeral)

    @settings_group.command(name="help", description="Ayarlar sistemi hakkında yardım alın")
    async def settings_help(self, ctx):
        """Get help with the settings system"""
        embed = create_embed(
            title="Ayarlar Sistemi Yardımı",
            description="Bu komut, sunucu ayarlarını yönetmenize yardımcı olur.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Kullanım",
            value=f"`/settings panel` - Ana ayarlar panelini açar\n"
                  f"`/settings help` - Bu yardım mesajını gösterir",
            inline=False
        )
        embed.add_field(
            name="Not",
            value="Ayarları değiştirmek için yönetici yetkisine sahip olmalısınız.",
            inline=False
        )
        await ctx.send(embed=embed, ephemeral=True)
        
    # Logging Settings Command Group
    loggings = app_commands.Group(name="loggings", description="Sunucu kayıt ayarlarını yönet")
    
    @loggings.command(name="panel", description="Kayıt ayarları panelini açar")
    @app_commands.describe(ephemeral="Paneli sadece size görünür şekilde açar")
    async def logging_panel(self, interaction: discord.Interaction, ephemeral: bool = True):
        """Open the logging settings panel"""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Bu komutu kullanmak için yönetici yetkisine sahip olmalısınız.", ephemeral=True)
            
        # Create and send the logging settings view
        view = LoggingSettingsView(self.bot, interaction.guild_id)
        await view.initialize()
        
        embed = discord.Embed(
            title="📋 Kayıt Ayarları Paneli",
            description="Sunucunuzun kayıt ayarlarını yapılandırmak için aşağıdaki seçenekleri kullanın.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Mevcut Kanal", value=f"<#{view.log_channel_id if view.log_channel_id else 'Ayarlanmamış'}>" if view.log_channel_id else "Ayarlanmamış", inline=False)
        embed.add_field(name="Kayıt Ayarları", value="Aktif ve pasif kayıt türlerini görmek için 'Ayarları Görüntüle' butonuna tıklayın.", inline=False)
        embed.set_footer(text="Bu panel sadece yönetici yetkisine sahip kullanıcılar tarafından kullanılabilir.")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
    
    @loggings.command(name="channel", description="Kayıt kanalını ayarla")
    @app_commands.describe(channel="Kayıtların gönderileceği kanal")
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the logging channel for the server"""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Bu komutu kullanmak için yönetici yetkisine sahip olmalısınız.", ephemeral=True)
            
        if self.db is None:
            self.db = await get_async_db()
            
        # Update the logging channel in the database
        await self.db.server_settings.update_one(
            {"server_id": interaction.guild_id},
            {"$set": {"logging.channel_id": channel.id}},
            upsert=True
        )
        
        embed = discord.Embed(
            title="✅ Kayıt Kanalı Ayarlandı",
            description=f"Kayıt kanalı başarıyla {channel.mention} olarak ayarlandı.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Tarih: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @loggings.command(name="toggle", description="Belirli bir kayıt türünü açıp kapatır")
    @app_commands.describe(
        setting="Değiştirmek istediğiniz kayıt türü",
        value="Değer (açık/kapalı)"
    )
    async def toggle_log_setting(self, interaction: discord.Interaction, setting: str, value: bool):
        """Toggle a specific logging setting on or off"""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Bu komutu kullanmak için yönetici yetkisine sahip olmalısınız.", ephemeral=True)
            
        if self.db is None:
            self.db = await get_async_db()
            
        valid_settings = [
            "message_delete", "message_edit", "channel_create", "channel_delete", 
            "channel_update", "member_join", "member_leave", "member_update", 
            "role_create", "role_delete", "role_update", "ban", "unban", 
            "voice_join", "voice_leave", "voice_move", "nickname_change", 
            "avatar_change", "invite_create", "invite_delete"
        ]
        
        if setting not in valid_settings:
            valid_settings_str = "\n".join([f"- `{s}`" for s in valid_settings])
            embed = discord.Embed(
                title="❌ Geçersiz Ayar",
                description=f"Geçersiz bir kayıt türü belirttiniz. Geçerli kayıt türleri:\n{valid_settings_str}",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            
        # Update the setting in the database
        await self.db.server_settings.update_one(
            {"server_id": interaction.guild_id},
            {"$set": {f"logging.settings.{setting}": value}},
            upsert=True
        )
        
        status = "açık" if value else "kapalı"
        embed = discord.Embed(
            title="✅ Kayıt Ayarı Güncellendi",
            description=f"`{setting}` kayıt türü başarıyla **{status}** olarak ayarlandı.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Tarih: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @loggings.command(name="view", description="Mevcut kayıt ayarlarını görüntüler")
    async def view_log_settings(self, interaction: discord.Interaction):
        """View current logging settings"""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Bu komutu kullanmak için yönetici yetkisine sahip olmalısınız.", ephemeral=True)
            
        if self.db is None:
            self.db = await get_async_db()
            
        # Get the current settings from the database
        server_settings = await self.db.server_settings.find_one({"server_id": interaction.guild_id})
        
        if not server_settings or "logging" not in server_settings:
            embed = discord.Embed(
                title="⚠️ Kayıt Ayarları Bulunamadı",
                description="Bu sunucu için henüz kayıt ayarları yapılandırılmamış.",
                color=discord.Color.gold()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
            
        logging_settings = server_settings.get("logging", {})
        channel_id = logging_settings.get("channel_id")
        settings = logging_settings.get("settings", {})
        
        embed = discord.Embed(
            title="📋 Kayıt Ayarları",
            description=f"**Kayıt Kanalı:** {f'<#{channel_id}>' if channel_id else 'Ayarlanmamış'}",
            color=discord.Color.blue()
        )
        
        enabled_settings = []
        disabled_settings = []
        
        for setting, value in settings.items():
            if value:
                enabled_settings.append(f"- `{setting}`")
            else:
                disabled_settings.append(f"- `{setting}`")
                
        if enabled_settings:
            embed.add_field(
                name="✅ Aktif Kayıtlar",
                value="\n".join(enabled_settings),
                inline=False
            )
        else:
            embed.add_field(
                name="✅ Aktif Kayıtlar",
                value="Aktif kayıt türü bulunmamaktadır.",
                inline=False
            )
            
        if disabled_settings:
            embed.add_field(
                name="❌ Pasif Kayıtlar",
                value="\n".join(disabled_settings),
                inline=False
            )
        else:
            embed.add_field(
                name="❌ Pasif Kayıtlar",
                value="Pasif kayıt türü bulunmamaktadır.",
                inline=False
            )
            
        embed.set_footer(text=f"Tarih: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @loggings.command(name="reset", description="Tüm kayıt ayarlarını sıfırlar")
    async def reset_log_settings(self, interaction: discord.Interaction):
        """Reset all logging settings"""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Bu komutu kullanmak için yönetici yetkisine sahip olmalısınız.", ephemeral=True)
            
        if self.db is None:
            self.db = await get_async_db()
            
        # Reset the logging settings in the database
        await self.db.server_settings.update_one(
            {"server_id": interaction.guild_id},
            {"$unset": {"logging": ""}},
            upsert=True
        )
        
        embed = discord.Embed(
            title="✅ Kayıt Ayarları Sıfırlandı",
            description="Tüm kayıt ayarları başarıyla sıfırlandı.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Tarih: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def open_settings_panel(self, ctx, ephemeral=False):
        """Open the main settings panel"""
        view = MainSettingsView(self.bot, ctx.author, ctx.guild.id)
        embed = discord.Embed(
            title="⚙️ Sunucu Ayarları",
            description="Sunucu ayarlarını yönetmek için aşağıdaki menüyü kullanın.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Bu panel yalnızca yönetici yetkisine sahip kişiler tarafından kullanılabilir.")
        await ctx.send(embed=embed, view=view, ephemeral=ephemeral)

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