import discord
from discord import ui
import logging
from typing import Optional, List
import asyncio
from utils.core.formatting import create_embed
from utils.database.connection import get_async_db, ensure_async_db, initialize_mongodb

# Setup logger
logger = logging.getLogger('server_views')

class ServerSettingsCustomView(ui.View):
    """View for configuring server settings"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
        
    @ui.button(label="🔤 Bot Öneki", style=discord.ButtonStyle.primary, row=0)
    async def prefix_settings(self, interaction: discord.Interaction, button: ui.Button):
        # Open prefix settings modal
        modal = PrefixSettingsModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)

    @ui.button(label="🎨 Embed Rengi", style=discord.ButtonStyle.primary, row=0) 
    async def embed_color(self, interaction: discord.Interaction, button: ui.Button):
        # Open embed color selector
        embed = discord.Embed(
            title="🎨 Embed Rengi Seçimi",
            description="Bot tarafından kullanılan gömme mesajların rengini seçin:",
            color=discord.Color.blue()
        )
        
        # Create color selector view
        view = EmbedColorView(self.bot, self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @ui.button(label="🔔 Rapor Kanalı", style=discord.ButtonStyle.secondary, row=0)
    async def report_channel(self, interaction: discord.Interaction, button: ui.Button):
        # Open report channel selector
        modal = ReportChannelModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🌍 Dil Ayarı", style=discord.ButtonStyle.success, row=1)
    async def language_settings(self, interaction: discord.Interaction, button: ui.Button):
        # Open language selector
        embed = discord.Embed(
            title="🌍 Bot Dili",
            description="Bot arayüzü için bir dil seçin:",
            color=discord.Color.blue()
        )
        
        # Create language selector view
        view = LanguageSelectorView(self.bot, self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @ui.button(label="📋 Mevcut Ayarlar", style=discord.ButtonStyle.secondary, row=1)
    async def current_settings(self, interaction: discord.Interaction, button: ui.Button):
        # Display current server settings
        await self.display_current_settings(interaction)
    
    @ui.button(label="❌ Kapat", style=discord.ButtonStyle.danger, row=2)
    async def close_menu(self, interaction: discord.Interaction, button: ui.Button):
        # Close the menu
        await interaction.response.edit_message(
            content="Sunucu ayarları kapatıldı.",
            embed=None,
            view=None
        )
    
    async def display_current_settings(self, interaction):
        """Display current server settings"""
        try:
            # Get server settings from database
            settings = None
            if self.mongo_db is not None:
                guild_id = interaction.guild.id
                settings = self.mongo_db['server_settings'].find_one({"guild_id": guild_id}) or {}
            
            # Create embed
            embed = discord.Embed(
                title="📊 Mevcut Sunucu Ayarları",
                description="Sunucunuz için yapılandırılmış ayarlar:",
                color=discord.Color.blue()
            )
            
            # Bot prefix
            prefix = settings.get("prefix", "!") if settings else "!"
            embed.add_field(
                name="🔤 Bot Öneki",
                value=f"`{prefix}`",
                inline=True
            )
            
            # Embed color
            color_hex = settings.get("embed_color", "#3498db") if settings else "#3498db"
            embed.add_field(
                name="🎨 Embed Rengi",
                value=f"`{color_hex}`",
                inline=True
            )
            
            # Language
            language = settings.get("language", "tr") if settings else "tr"
            language_name = "Türkçe" if language == "tr" else "English"
            embed.add_field(
                name="🌍 Dil",
                value=language_name,
                inline=True
            )
            
            # Report channel
            report_channel_id = settings.get("report_channel") if settings else None
            report_channel_text = "Ayarlanmamış"
            if report_channel_id:
                channel = interaction.guild.get_channel(report_channel_id)
                if channel:
                    report_channel_text = channel.mention
                else:
                    report_channel_text = f"Kanal bulunamadı (ID: {report_channel_id})"
            
            embed.add_field(
                name="🔔 Rapor Kanalı",
                value=report_channel_text,
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error displaying current settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Ayarlar görüntülenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class PrefixSettingsModal(ui.Modal, title="Bot Öneki Ayarları"):
    """Modal for setting bot prefix"""
    
    prefix = ui.TextInput(
        label="Bot Öneki",
        placeholder="Örnek: ! veya /",
        required=True,
        min_length=1,
        max_length=5
    )
    
    def __init__(self, bot, guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get the prefix
            prefix = self.prefix.value
            
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['server_settings'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"prefix": prefix}},
                    upsert=True
                )
            
            await interaction.response.send_message(
                embed=create_embed(f"Bot öneki `{prefix}` olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting bot prefix: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Bot öneki ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class EmbedColorView(ui.View):
    """View for selecting embed color"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
    
    @ui.button(label="🔴 Kırmızı", style=discord.ButtonStyle.danger, row=0)
    async def red_color(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color(interaction, "#e74c3c", "Kırmızı")
    
    @ui.button(label="🟢 Yeşil", style=discord.ButtonStyle.success, row=0)
    async def green_color(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color(interaction, "#2ecc71", "Yeşil")
    
    @ui.button(label="🔵 Mavi", style=discord.ButtonStyle.primary, row=0)
    async def blue_color(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color(interaction, "#3498db", "Mavi")
    
    @ui.button(label="🟣 Mor", style=discord.ButtonStyle.secondary, row=1)
    async def purple_color(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color(interaction, "#9b59b6", "Mor")
    
    @ui.button(label="🟠 Turuncu", style=discord.ButtonStyle.secondary, row=1)
    async def orange_color(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color(interaction, "#e67e22", "Turuncu")
    
    @ui.button(label="⚫ Siyah", style=discord.ButtonStyle.secondary, row=1)
    async def black_color(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color(interaction, "#2c3e50", "Siyah")
    
    @ui.button(label="⚪ Beyaz", style=discord.ButtonStyle.secondary, row=2)
    async def white_color(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color(interaction, "#ecf0f1", "Beyaz")
    
    @ui.button(label="🟡 Sarı", style=discord.ButtonStyle.secondary, row=2)
    async def yellow_color(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color(interaction, "#f1c40f", "Sarı")
    
    @ui.button(label="🏳️‍🌈 Özel Renk", style=discord.ButtonStyle.secondary, row=2)
    async def custom_color(self, interaction: discord.Interaction, button: ui.Button):
        # Open custom color modal
        modal = CustomColorModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)
    
    async def set_color(self, interaction, hex_color, color_name):
        """Set embed color"""
        try:
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['server_settings'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"embed_color": hex_color}},
                    upsert=True
                )
            
            # Create a sample embed with the new color
            color_int = int(hex_color.replace("#", ""), 16)
            sample_embed = discord.Embed(
                title=f"🎨 {color_name} rengi seçildi",
                description="Botun embed mesajları artık bu renkte görünecek.",
                color=discord.Color(color_int)
            )
            
            await interaction.response.send_message(
                embed=sample_embed,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting embed color: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Embed rengi ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class CustomColorModal(ui.Modal, title="Özel Renk Ayarı"):
    """Modal for setting custom embed color"""
    
    color_hex = ui.TextInput(
        label="Renk Kodu (HEX)",
        placeholder="Örnek: #3498db",
        required=True,
        min_length=7,
        max_length=7
    )
    
    def __init__(self, bot, guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get the color hex code
            color_hex = self.color_hex.value
            
            # Validate hex code format
            if not color_hex.startswith("#") or len(color_hex) != 7:
                await interaction.response.send_message(
                    embed=create_embed("Geçersiz renk kodu. '#' ile başlayan 6 haneli bir HEX kodu girin (örn: #3498db).", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            try:
                # Try to convert hex to int to validate format
                color_int = int(color_hex.replace("#", ""), 16)
            except ValueError:
                await interaction.response.send_message(
                    embed=create_embed("Geçersiz renk kodu. HEX renk kodu yalnızca 0-9 ve A-F karakterlerini içerebilir.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['server_settings'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"embed_color": color_hex}},
                    upsert=True
                )
            
            # Create a sample embed with the new color
            sample_embed = discord.Embed(
                title="🎨 Özel renk ayarlandı",
                description=f"Botun embed mesajları artık {color_hex} kodlu renkte görünecek.",
                color=discord.Color(color_int)
            )
            
            await interaction.response.send_message(
                embed=sample_embed,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting custom embed color: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Özel renk ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class ReportChannelModal(ui.Modal, title="Rapor Kanalı Ayarı"):
    """Modal for setting report channel"""
    
    channel_id = ui.TextInput(
        label="Kanal ID",
        placeholder="Kanal ID'sini girin veya kanalı etiketleyin",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot, guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse channel ID from input
            channel_input = self.channel_id.value
            
            # Check if it's a mention
            if channel_input.startswith('<#') and channel_input.endswith('>'):
                channel_id = int(channel_input[2:-1])
            else:
                try:
                    channel_id = int(channel_input.strip())
                except ValueError:
                    await interaction.response.send_message(
                        embed=create_embed("Geçersiz kanal ID formatı. Lütfen geçerli bir kanal ID'si girin.", discord.Color.red()),
                        ephemeral=True
                    )
                    return
            
            # Get the channel
            channel = self.guild.get_channel(channel_id)
            if not channel:
                await interaction.response.send_message(
                    embed=create_embed("Belirtilen ID ile bir kanal bulunamadı.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Check if it's a text channel
            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message(
                    embed=create_embed("Belirtilen kanal bir metin kanalı değil.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['server_settings'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"report_channel": channel_id}},
                    upsert=True
                )
            
            await interaction.response.send_message(
                embed=create_embed(f"{channel.mention} kanalı rapor kanalı olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting report channel: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Rapor kanalı ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class LanguageSelectorView(ui.View):
    """View for selecting bot language"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
    
    @ui.button(label="🇹🇷 Türkçe", style=discord.ButtonStyle.primary, row=0)
    async def turkish_language(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_language(interaction, "tr", "Türkçe")
    
    @ui.button(label="🇺🇸 English", style=discord.ButtonStyle.secondary, row=0)
    async def english_language(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_language(interaction, "en", "English")
    
    async def set_language(self, interaction, language_code, language_name):
        """Set bot language"""
        try:
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['server_settings'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"language": language_code}},
                    upsert=True
                )
            
            if language_code == "tr":
                message = f"Bot dili {language_name} olarak ayarlandı."
            else:
                message = f"Bot language set to {language_name}."
                
            await interaction.response.send_message(
                embed=create_embed(message, discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting bot language: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Bot dili ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
