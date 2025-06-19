import discord
from discord import ui
import logging
from typing import Optional, List
import asyncio
from src.utils.core.formatting import create_embed
from src.utils.database.connection import get_async_db, ensure_async_db, initialize_mongodb

# Setup logger
logger = logging.getLogger('logging_views')

class LoggingSettingsView(ui.View):
    """View for configuring logging settings"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
        
    @ui.button(label="📊 Ana Log Kanalı", style=discord.ButtonStyle.primary, row=0)
    async def main_log_channel(self, interaction: discord.Interaction, button: ui.Button):
        # Create a channel select modal
        modal = MainLogChannelModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)

    @ui.button(label="⚙️ Gelişmiş Loglama", style=discord.ButtonStyle.secondary, row=0) 
    async def advanced_logging(self, interaction: discord.Interaction, button: ui.Button):
        # Open advanced logging settings
        embed = discord.Embed(
            title="⚙️ Gelişmiş Loglama Ayarları",
            description="Her log türü için farklı kanallar ayarlayın:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 Mevcut Kategoriler",
            value=(
                "👥 **Üye Olayları** - Katılma, ayrılma, yasaklama\n"
                "💬 **Mesaj Olayları** - Silinen ve düzenlenen mesajlar\n"
                "🔧 **Sunucu Olayları** - Ayarlar, roller, kanallar\n"
                "🎤 **Ses Olayları** - Ses kanalı hareketleri\n"
                "📅 **Etkinlik Olayları** - Sunucu etkinlikleri\n"
                "🧵 **Thread Olayları** - Thread işlemleri\n"
                "📝 **Komut Olayları** - Komut kullanımları ve hatalar"
            ),
            inline=False
        )
        
        # Create advanced logging view
        view = AdvancedLoggingView(self.bot, self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @ui.button(label="🔍 Denetim Kaydı", style=discord.ButtonStyle.secondary, row=0)
    async def audit_log_integration(self, interaction: discord.Interaction, button: ui.Button):
        # Open audit log settings
        embed = discord.Embed(
            title="🔍 Denetim Kaydı Entegrasyonu",
            description="Discord denetim kaydı ile entegrasyon ayarları:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="⚙️ Ayarlar",
            value=(
                "Discord denetim kaydı, sunucunuzda gerçekleşen önemli değişikliklerin detaylı kaydını tutar.\n"
                "Bu ayarlar ile bu verilerin güvenli bir şekilde bot tarafından işlenmesini sağlayabilirsiniz."
            ),
            inline=False
        )
        
        # Create audit log settings view
        view = AuditLogSettingsView(self.bot, self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="💾 Yedekleme", style=discord.ButtonStyle.success, row=1)
    async def log_backup(self, interaction: discord.Interaction, button: ui.Button):
        # Open log backup settings
        embed = discord.Embed(
            title="💾 Log Yedekleme Ayarları",
            description="Log verilerinizi yedekleme ve arşivleme ayarları:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="⚙️ Seçenekler",
            value=(
                "• **Otomatik Yedekleme** - Belirli aralıklarla logları yedekleme\n"
                "• **Arşivleme** - Eski logların arşivlenmesi\n"
                "• **Veri Saklama** - Logların ne kadar süre saklanacağı\n"
                "• **Dosya Formatı** - Log verilerinin hangi formatta saklanacağı"
            ),
            inline=False
        )
        
        # Create backup settings view
        view = LogBackupView(self.bot, self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @ui.button(label="🎛️ Loglanan Olaylar", style=discord.ButtonStyle.success, row=1)
    async def logged_events(self, interaction: discord.Interaction, button: ui.Button):
        # Open logged events settings
        embed = discord.Embed(
            title="🎛️ Loglanan Olaylar",
            description="Hangi olayların loglanacağını seçin:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="⚙️ Ayarlar",
            value=(
                "Bu ayarlar ile sunucunuzda hangi olayların loglanacağını belirleyebilirsiniz.\n"
                "İstemediğiniz log türlerini devre dışı bırakabilirsiniz."
            ),
            inline=False
        )
        
        # Create logged events view
        view = LoggedEventsView(self.bot, self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    @ui.button(label="📋 Mevcut Ayarlar", style=discord.ButtonStyle.secondary, row=1)
    async def current_settings(self, interaction: discord.Interaction, button: ui.Button):
        # Display current logging settings
        await self.display_current_settings(interaction)
    
    @ui.button(label="❌ Kapat", style=discord.ButtonStyle.danger, row=2)
    async def close_menu(self, interaction: discord.Interaction, button: ui.Button):
        # Close the menu
        await interaction.response.edit_message(
            content="Log ayarları kapatıldı.",
            embed=None,
            view=None
        )
    
    async def display_current_settings(self, interaction):
        """Display current logging settings"""
        try:
            # Get logging settings from database
            settings = None
            if self.mongo_db is not None:
                guild_id = interaction.guild.id
                settings = self.mongo_db['logger'].find_one({"guild_id": guild_id}) or {}
            
            # Create embed
            embed = discord.Embed(
                title="📊 Mevcut Log Ayarları",
                description="Sunucunuz için yapılandırılmış log ayarları:",
                color=discord.Color.blue()
            )
            
            # Main log channel
            channel_id = settings.get("channel_id") if settings else None
            channel_text = "Ayarlanmamış"
            if channel_id:
                channel = interaction.guild.get_channel(channel_id)
                if channel:
                    channel_text = channel.mention
                else:
                    channel_text = f"Kanal bulunamadı (ID: {channel_id})"
            
            embed.add_field(
                name="📊 Ana Log Kanalı",
                value=channel_text,
                inline=False
            )
            
            # Check if specific log channels are set
            if settings:
                # Member events
                member_channel_id = settings.get("member_events_channel")
                if member_channel_id:
                    channel = interaction.guild.get_channel(member_channel_id)
                    embed.add_field(
                        name="👥 Üye Olayları Kanalı",
                        value=channel.mention if channel else f"Kanal bulunamadı (ID: {member_channel_id})",
                        inline=True
                    )
                
                # Message events
                message_channel_id = settings.get("message_events_channel")
                if message_channel_id:
                    channel = interaction.guild.get_channel(message_channel_id)
                    embed.add_field(
                        name="💬 Mesaj Olayları Kanalı",
                        value=channel.mention if channel else f"Kanal bulunamadı (ID: {message_channel_id})",
                        inline=True
                    )
                
                # Server events
                server_channel_id = settings.get("server_events_channel")
                if server_channel_id:
                    channel = interaction.guild.get_channel(server_channel_id)
                    embed.add_field(
                        name="🔧 Sunucu Olayları Kanalı",
                        value=channel.mention if channel else f"Kanal bulunamadı (ID: {server_channel_id})",
                        inline=True
                    )
            
            # If no settings found
            if not settings or len(embed.fields) == 1:
                embed.add_field(
                    name="ℹ️ Bilgi",
                    value="Henüz özelleştirilmiş log ayarları bulunmamaktadır.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error displaying current settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Ayarlar görüntülenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class MainLogChannelModal(ui.Modal, title="Ana Log Kanalı Ayarla"):
    """Modal for setting the main logging channel"""
    
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
                self.mongo_db['logger'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"channel_id": channel_id}},
                    upsert=True
                )
            
            await interaction.response.send_message(
                embed=create_embed(f"{channel.mention} kanalı ana log kanalı olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting main log channel: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Ana log kanalı ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class AdvancedLoggingView(ui.View):
    """View for advanced logging settings"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
        
        # Add channel select menu
        self.add_item(LoggingChannelSelect(bot, guild, "member_events", "👥 Üye Olayları"))
        self.add_item(LoggingChannelSelect(bot, guild, "message_events", "💬 Mesaj Olayları"))
        self.add_item(LoggingChannelSelect(bot, guild, "server_events", "🔧 Sunucu Olayları"))
        self.add_item(LoggingChannelSelect(bot, guild, "voice_events", "🎤 Ses Olayları"))
        self.add_item(LoggingChannelSelect(bot, guild, "event_activities", "📅 Etkinlik Olayları"))
        self.add_item(LoggingChannelSelect(bot, guild, "thread_events", "🧵 Thread Olayları"))
        self.add_item(LoggingChannelSelect(bot, guild, "command_events", "📝 Komut Olayları"))
    
    @ui.button(label="📋 Tüm Ayarları Görüntüle", style=discord.ButtonStyle.success, row=4)
    async def view_all_settings(self, interaction: discord.Interaction, button: ui.Button):
        # Display all advanced logging settings
        await self.show_all_settings(interaction)
    
    @ui.button(label="🗑️ Tüm Ayarları Sıfırla", style=discord.ButtonStyle.danger, row=4)
    async def reset_all_settings(self, interaction: discord.Interaction, button: ui.Button):
        # Reset all advanced logging settings
        await self.reset_all_settings(interaction)
    
    async def show_all_settings(self, interaction):
        """Display all advanced logging settings"""
        try:
            # Get settings from database
            settings = None
            if self.mongo_db is not None:
                guild_id = interaction.guild.id
                settings = self.mongo_db['logger'].find_one({"guild_id": guild_id}) or {}
            
            # Create embed
            embed = discord.Embed(
                title="📊 Gelişmiş Loglama Ayarları",
                description="Sunucunuz için yapılandırılmış özel log kanalları:",
                color=discord.Color.blue()
            )
            
            # Categories to check
            categories = {
                "member_events": "👥 Üye Olayları",
                "message_events": "💬 Mesaj Olayları",
                "server_events": "🔧 Sunucu Olayları",
                "voice_events": "🎤 Ses Olayları",
                "event_activities": "📅 Etkinlik Olayları",
                "thread_events": "🧵 Thread Olayları",
                "command_events": "📝 Komut Olayları"
            }
            
            # Main log channel
            channel_id = settings.get("channel_id") if settings else None
            channel_text = "Ayarlanmamış"
            if channel_id:
                channel = interaction.guild.get_channel(channel_id)
                if channel:
                    channel_text = channel.mention
                else:
                    channel_text = f"Kanal bulunamadı (ID: {channel_id})"
            
            embed.add_field(
                name="📊 Ana Log Kanalı",
                value=channel_text,
                inline=False
            )
            
            # Check each category
            if settings:
                for category, label in categories.items():
                    key = f"{category}_channel"
                    channel_id = settings.get(key)
                    
                    if channel_id:
                        channel = interaction.guild.get_channel(channel_id)
                        value = channel.mention if channel else f"Kanal bulunamadı (ID: {channel_id})"
                    else:
                        value = "Ana log kanalını kullanır"
                    
                    embed.add_field(
                        name=label,
                        value=value,
                        inline=True
                    )
            
            # If no settings found
            if not settings or len(embed.fields) == 1:
                embed.add_field(
                    name="ℹ️ Bilgi",
                    value="Henüz özelleştirilmiş gelişmiş log ayarları bulunmamaktadır.",
                    inline=False
                )
            
            embed.set_footer(text="Özel kanal ayarlanmamış olan log türleri ana log kanalını kullanır.")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error displaying advanced settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Gelişmiş ayarlar görüntülenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    async def reset_all_settings(self, interaction):
        """Reset all advanced logging settings"""
        try:
            # Ask for confirmation
            embed = discord.Embed(
                title="⚠️ Ayarları Sıfırlama",
                description="Tüm gelişmiş loglama ayarlarını sıfırlamak istediğinizden emin misiniz?",
                color=discord.Color.yellow()
            )
            
            # Create confirmation view
            view = LoggingConfirmationView(self.bot, self.guild)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error resetting advanced settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Ayarlar sıfırlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class LoggingChannelSelect(ui.ChannelSelect):
    """Channel select for logging settings"""
    
    def __init__(self, bot, guild, category, label):
        super().__init__(
            placeholder=f"{label} için kanal seçin",
            channel_types=[discord.ChannelType.text],
            row=self.get_row_for_category(category)
        )
        self.bot = bot
        self.guild = guild
        self.category = category
        self.label_text = label
        self.mongo_db = initialize_mongodb()
    
    def get_row_for_category(self, category):
        """Get the appropriate row for this category"""
        categories = {
            "member_events": 0,
            "message_events": 0,
            "server_events": 1,
            "voice_events": 1,
            "event_activities": 2,
            "thread_events": 2,
            "command_events": 3
        }
        return categories.get(category, 0)
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Get selected channel
            channel_id = int(self.values[0].id)
            channel = self.guild.get_channel(channel_id)
            
            if not channel:
                await interaction.response.send_message(
                    embed=create_embed("Seçilen kanal bulunamadı.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Save to database
            key = f"{self.category}_channel"
            if self.mongo_db is not None:
                self.mongo_db['logger'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {key: channel_id}},
                    upsert=True
                )
            
            await interaction.response.send_message(
                embed=create_embed(f"{self.label_text} için {channel.mention} kanalı ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting {self.category} channel: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"{self.label_text} kanalı ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class AuditLogSettingsView(ui.View):
    """View for audit log integration settings"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
    
    @ui.button(label="✅ Etkinleştir", style=discord.ButtonStyle.success, row=0)
    async def enable_audit_log(self, interaction: discord.Interaction, button: ui.Button):
        # Enable audit log integration
        await self.toggle_audit_log(interaction, True)
    
    @ui.button(label="❌ Devre Dışı Bırak", style=discord.ButtonStyle.danger, row=0)
    async def disable_audit_log(self, interaction: discord.Interaction, button: ui.Button):
        # Disable audit log integration
        await self.toggle_audit_log(interaction, False)
    
    @ui.select(
        placeholder="Denetim kaydı detay seviyesi",
        options=[
            discord.SelectOption(label="Basit", description="Sadece temel olaylar", value="basic"),
            discord.SelectOption(label="Standart", description="Çoğu olay (önerilen)", value="standard"),
            discord.SelectOption(label="Detaylı", description="Tüm olaylar ve ayrıntılar", value="detailed")
        ],
        row=1
    )
    async def detail_level_select(self, interaction: discord.Interaction, select: ui.Select):
        # Set audit log detail level
        await self.set_detail_level(interaction, select.values[0])
    
    async def toggle_audit_log(self, interaction, enabled):
        """Enable or disable audit log integration"""
        try:
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['logger'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"audit_log_enabled": enabled}},
                    upsert=True
                )
            
            status = "etkinleştirildi" if enabled else "devre dışı bırakıldı"
            await interaction.response.send_message(
                embed=create_embed(f"Denetim kaydı entegrasyonu {status}.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error toggling audit log: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Denetim kaydı ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    async def set_detail_level(self, interaction, level):
        """Set audit log detail level"""
        try:
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['logger'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"audit_log_detail": level}},
                    upsert=True
                )
            
            levels = {
                "basic": "Basit",
                "standard": "Standart",
                "detailed": "Detaylı"
            }
            
            await interaction.response.send_message(
                embed=create_embed(f"Denetim kaydı detay seviyesi \"{levels.get(level, 'Bilinmeyen')}\" olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting audit log detail level: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Detay seviyesi ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class LogBackupView(ui.View):
    """View for log backup settings"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
    
    @ui.button(label="📆 Yedekleme Sıklığı", style=discord.ButtonStyle.primary, row=0)
    async def backup_frequency(self, interaction: discord.Interaction, button: ui.Button):
        # Open backup frequency modal
        modal = BackupFrequencyModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="📦 Arşivleme", style=discord.ButtonStyle.primary, row=0)
    async def archiving(self, interaction: discord.Interaction, button: ui.Button):
        # Open archiving modal
        modal = ArchivingModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)
    
    @ui.select(
        placeholder="Dosya formatını seçin",
        options=[
            discord.SelectOption(label="JSON", description="JSON formatında yedekleme", value="json"),
            discord.SelectOption(label="CSV", description="CSV formatında yedekleme", value="csv"),
            discord.SelectOption(label="Metin", description="Düz metin formatında yedekleme", value="text")
        ],
        row=1
    )
    async def file_format_select(self, interaction: discord.Interaction, select: ui.Select):
        # Set file format
        await self.set_file_format(interaction, select.values[0])
    
    @ui.button(label="🗑️ Veri Temizleme", style=discord.ButtonStyle.danger, row=2)
    async def data_cleanup(self, interaction: discord.Interaction, button: ui.Button):
        # Open data cleanup modal
        modal = DataCleanupModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)
    
    async def set_file_format(self, interaction, format):
        """Set file format for backups"""
        try:
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['logger'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"backup_format": format}},
                    upsert=True
                )
            
            formats = {
                "json": "JSON",
                "csv": "CSV",
                "text": "Düz metin"
            }
            
            await interaction.response.send_message(
                embed=create_embed(f"Yedekleme dosya formatı \"{formats.get(format, 'Bilinmeyen')}\" olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting backup format: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Dosya formatı ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class BackupFrequencyModal(ui.Modal, title="Yedekleme Sıklığı"):
    """Modal for setting backup frequency"""
    
    frequency = ui.TextInput(
        label="Yedekleme sıklığı (gün)",
        placeholder="Örnek: 7 (her 7 günde bir yedekleme)",
        required=True,
        min_length=1,
        max_length=3
    )
    
    def __init__(self, bot, guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse frequency
            try:
                frequency = int(self.frequency.value)
                if frequency <= 0:
                    await interaction.response.send_message(
                        embed=create_embed("Yedekleme sıklığı pozitif bir sayı olmalıdır.", discord.Color.red()),
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    embed=create_embed("Geçersiz sayı formatı. Lütfen bir sayı girin.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['logger'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"backup_frequency": frequency}},
                    upsert=True
                )
            
            await interaction.response.send_message(
                embed=create_embed(f"Yedekleme sıklığı {frequency} gün olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting backup frequency: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Yedekleme sıklığı ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class ArchivingModal(ui.Modal, title="Arşivleme Ayarları"):
    """Modal for setting archiving settings"""
    
    days = ui.TextInput(
        label="Arşivleme süresi (gün)",
        placeholder="Örnek: 30 (30 gün sonra arşivle)",
        required=True,
        min_length=1,
        max_length=4
    )
    
    def __init__(self, bot, guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse days
            try:
                days = int(self.days.value)
                if days <= 0:
                    await interaction.response.send_message(
                        embed=create_embed("Arşivleme süresi pozitif bir sayı olmalıdır.", discord.Color.red()),
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    embed=create_embed("Geçersiz sayı formatı. Lütfen bir sayı girin.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['logger'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"archive_days": days}},
                    upsert=True
                )
            
            await interaction.response.send_message(
                embed=create_embed(f"Arşivleme süresi {days} gün olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting archive days: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Arşivleme süresi ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class DataCleanupModal(ui.Modal, title="Veri Temizleme"):
    """Modal for setting data cleanup settings"""
    
    days = ui.TextInput(
        label="Tutulacak veri süresi (gün)",
        placeholder="Örnek: 90 (90 günden eski logları sil)",
        required=True,
        min_length=1,
        max_length=4
    )
    
    def __init__(self, bot, guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse days
            try:
                days = int(self.days.value)
                if days <= 0:
                    await interaction.response.send_message(
                        embed=create_embed("Veri tutma süresi pozitif bir sayı olmalıdır.", discord.Color.red()),
                        ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    embed=create_embed("Geçersiz sayı formatı. Lütfen bir sayı girin.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['logger'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"cleanup_days": days}},
                    upsert=True
                )
            
            await interaction.response.send_message(
                embed=create_embed(f"Veri tutma süresi {days} gün olarak ayarlandı. Bu süreden eski loglar otomatik silinecek.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting cleanup days: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Veri temizleme ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class LoggedEventsView(ui.View):
    """View for configuring which events to log"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
        
        # Add toggles for each event type
        self.add_item(EventToggleButton("member", "👥 Üye Olayları", bot, guild))
        self.add_item(EventToggleButton("message", "💬 Mesaj Olayları", bot, guild))
        self.add_item(EventToggleButton("server", "🔧 Sunucu Olayları", bot, guild))
        self.add_item(EventToggleButton("voice", "🎤 Ses Olayları", bot, guild))
        self.add_item(EventToggleButton("event", "📅 Etkinlik Olayları", bot, guild))
        self.add_item(EventToggleButton("thread", "🧵 Thread Olayları", bot, guild))
        self.add_item(EventToggleButton("command", "📝 Komut Olayları", bot, guild))
    
    @ui.button(label="📋 Mevcut Ayarlar", style=discord.ButtonStyle.success, row=3)
    async def view_current_settings(self, interaction: discord.Interaction, button: ui.Button):
        # View current event settings
        await self.show_current_settings(interaction)
    
    async def show_current_settings(self, interaction):
        """Show current event settings"""
        try:
            # Get settings from database
            settings = None
            if self.mongo_db is not None:
                guild_id = interaction.guild.id
                settings = self.mongo_db['logger'].find_one({"guild_id": guild_id}) or {}
            
            # Create embed
            embed = discord.Embed(
                title="🎛️ Loglanan Olaylar Ayarları",
                description="Hangi olayların loglandığına dair mevcut ayarlar:",
                color=discord.Color.blue()
            )
            
            # Event types
            event_types = {
                "member_events_enabled": "👥 Üye Olayları",
                "message_events_enabled": "💬 Mesaj Olayları",
                "server_events_enabled": "🔧 Sunucu Olayları",
                "voice_events_enabled": "🎤 Ses Olayları",
                "event_activities_enabled": "📅 Etkinlik Olayları",
                "thread_events_enabled": "🧵 Thread Olayları",
                "command_events_enabled": "📝 Komut Olayları"
            }
            
            # Check each event type
            if settings:
                for key, label in event_types.items():
                    enabled = settings.get(key, True)  # Default to True if not set
                    status = "✅ Etkin" if enabled else "❌ Devre Dışı"
                    
                    embed.add_field(
                        name=label,
                        value=status,
                        inline=True
                    )
            else:
                # Default if no settings found
                for label in event_types.values():
                    embed.add_field(
                        name=label,
                        value="✅ Etkin (varsayılan)",
                        inline=True
                    )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing current event settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Olay ayarları görüntülenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class EventToggleButton(ui.Button):
    """Button for toggling event logging"""
    
    def __init__(self, event_type, label, bot, guild):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            row=self.get_row_for_event(event_type)
        )
        self.bot = bot
        self.guild = guild
        self.event_type = event_type
        self.mongo_db = initialize_mongodb()
    
    def get_row_for_event(self, event_type):
        """Get the appropriate row for this event type"""
        rows = {
            "member": 0,
            "message": 0,
            "server": 0,
            "voice": 1,
            "event": 1,
            "thread": 1,
            "command": 2
        }
        return rows.get(event_type, 0)
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Toggle event logging
            key = f"{self.event_type}_events_enabled"
            
            # Get current setting
            current_setting = True  # Default to True
            if self.mongo_db is not None:
                guild_id = self.guild.id
                settings = self.mongo_db['logger'].find_one({"guild_id": guild_id}) or {}
                current_setting = settings.get(key, True)  # Default to True if not set
            
            # Toggle setting
            new_setting = not current_setting
            
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['logger'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {key: new_setting}},
                    upsert=True
                )
            
            status = "etkinleştirildi" if new_setting else "devre dışı bırakıldı"
            await interaction.response.send_message(
                embed=create_embed(f"{self.label} loglama {status}.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error toggling {self.event_type} events: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"{self.label} ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class LoggingConfirmationView(ui.View):
    """Confirmation view for resetting logging settings"""
    
    def __init__(self, bot, guild, timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = initialize_mongodb()
    
    @ui.button(label="✅ Evet, Sıfırla", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        try:
            # Reset all advanced logging settings
            if self.mongo_db is not None:
                guild_id = self.guild.id
                
                # Get the main channel ID to preserve it
                settings = self.mongo_db['logger'].find_one({"guild_id": guild_id}) or {}
                main_channel = settings.get("channel_id")
                
                # Reset all specific channel settings but keep the main channel
                update_data = {"guild_id": guild_id}
                if main_channel:
                    update_data["channel_id"] = main_channel
                
                # Update/replace the document
                self.mongo_db['logger'].replace_one(
                    {"guild_id": guild_id},
                    update_data,
                    upsert=True
                )
            
            await interaction.response.send_message(
                embed=create_embed("Tüm gelişmiş loglama ayarları başarıyla sıfırlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error resetting logging settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Ayarlar sıfırlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @ui.button(label="❌ İptal", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            embed=create_embed("Ayarları sıfırlama işlemi iptal edildi.", discord.Color.blue()),
            ephemeral=True
        )
