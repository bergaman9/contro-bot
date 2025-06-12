import discord
from discord import ui
import logging
from typing import Optional
from utils.core.formatting import create_embed
from utils.database.connection import get_async_db

logger = logging.getLogger(__name__)

class LevelNotificationSettingsView(discord.ui.View):
    """Enhanced view for managing level-up notification settings"""
    
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    async def get_notification_settings(self):
        """Get current notification settings"""
        try:
            mongo_db = get_async_db()
            settings = await mongo_db.levelling_settings.find_one({"guild_id": int(self.guild_id)})
            return settings if settings else {}
        except Exception as e:
            logger.error(f"Error getting notification settings: {e}")
            return {}

    async def save_notification_settings(self, settings_update):
        """Save notification settings"""
        try:
            mongo_db = get_async_db()
            await mongo_db.levelling_settings.update_one(
                {"guild_id": int(self.guild_id)},
                {"$set": settings_update},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving notification settings: {e}")
            return False

    @discord.ui.button(label="🔘 Bildirimleri Aç/Kapat", style=discord.ButtonStyle.primary, row=0)
    async def toggle_notifications(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle level-up notifications on/off"""
        try:
            settings = await self.get_notification_settings()
            current_state = settings.get("level_up_notifications", True)
            new_state = not current_state
            
            success = await self.save_notification_settings({"level_up_notifications": new_state})
            
            if success:
                state_text = "✅ Aktif" if new_state else "❌ Kapalı"
                embed = discord.Embed(
                    title="🔔 Bildirim Durumu Güncellendi",
                    description=f"Seviye atlama bildirimleri: {state_text}",
                    color=discord.Color.green() if new_state else discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Ayarlar kaydedilemedi.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error toggling notifications: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)

    @discord.ui.button(label="📍 Bildirim Kanalı", style=discord.ButtonStyle.secondary, row=0)
    async def set_notification_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the notification channel"""
        modal = NotificationChannelModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="✨ Mesaj Özelleştir", style=discord.ButtonStyle.secondary, row=0)
    async def customize_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Customize notification message"""
        modal = CustomNotificationMessageModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🎨 Embed Rengi", style=discord.ButtonStyle.secondary, row=1)
    async def set_embed_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set embed color for notifications"""
        modal = EmbedColorModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="👑 Özel Seviye Mesajları", style=discord.ButtonStyle.secondary, row=1)
    async def special_level_messages(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure special messages for specific levels"""
        view = SpecialLevelMessagesView(self.bot, self.guild_id)
        embed = discord.Embed(
            title="👑 Özel Seviye Mesajları",
            description="Belirli seviyeler için özel mesajlar ayarlayın.",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📋 Özellikler",
            value=(
                "• Milestone seviyeler için özel mesajlar\n"
                "• Farklı embed renkleri\n"
                "• Özel görseller (yakında)\n"
                "• Rol duyuruları ile entegrasyon"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="📊 Mevcut Ayarlar", style=discord.ButtonStyle.success, row=1)
    async def current_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show current notification settings"""
        try:
            settings = await self.get_notification_settings()
            guild = self.bot.get_guild(self.guild_id)
            
            embed = discord.Embed(
                title="📊 Mevcut Bildirim Ayarları",
                description="Şu anki seviye atlama bildirim ayarlarınız:",
                color=discord.Color.blue()
            )
            
            # Notification status
            notifications_enabled = settings.get("level_up_notifications", True)
            embed.add_field(
                name="🔔 Bildirim Durumu",
                value="✅ Aktif" if notifications_enabled else "❌ Kapalı",
                inline=True
            )
            
            # Notification channel
            channel_id = settings.get("level_up_channel_id")
            if channel_id:
                channel = guild.get_channel(int(channel_id))
                channel_text = channel.mention if channel else f"❌ Kanal bulunamadı (ID: {channel_id})"
            else:
                channel_text = "Aynı kanal"
            
            embed.add_field(
                name="📍 Bildirim Kanalı",
                value=channel_text,
                inline=True
            )
            
            # Custom message
            custom_message = settings.get("level_up_message")
            embed.add_field(
                name="✨ Özel Mesaj",
                value="✅ Ayarlanmış" if custom_message else "❌ Varsayılan mesaj",
                inline=True
            )
            
            # Embed color
            embed_color = settings.get("level_up_embed_color", "#00ff00")
            embed.add_field(
                name="🎨 Embed Rengi",
                value=f"`{embed_color}`",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing current settings: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)


class NotificationChannelModal(discord.ui.Modal, title="Bildirim Kanalı Ayarla"):
    """Modal for setting notification channel"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    channel_id = discord.ui.TextInput(
        label="Kanal ID",
        placeholder="Bildirim kanalının ID'sini girin (boş bırakırsanız aynı kanal kullanılır)",
        required=False,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            if self.channel_id.value.strip():
                # Validate channel
                channel = interaction.guild.get_channel(int(self.channel_id.value))
                if not channel:
                    await interaction.response.send_message("❌ Geçersiz kanal ID!", ephemeral=True)
                    return
                
                if not isinstance(channel, discord.TextChannel):
                    await interaction.response.send_message("❌ Sadece metin kanalları seçilebilir!", ephemeral=True)
                    return
                
                # Save setting
                success = await self.parent_view.save_notification_settings({
                    "level_up_channel_id": int(self.channel_id.value)
                })
                
                if success:
                    await interaction.response.send_message(
                        f"✅ Bildirim kanalı {channel.mention} olarak ayarlandı!",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message("❌ Ayarlar kaydedilemedi.", ephemeral=True)
            else:
                # Remove channel setting (use same channel)
                success = await self.parent_view.save_notification_settings({
                    "level_up_channel_id": None
                })
                
                if success:
                    await interaction.response.send_message(
                        "✅ Bildirimler artık aynı kanalda gösterilecek!",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message("❌ Ayarlar kaydedilemedi.", ephemeral=True)
                    
        except ValueError:
            await interaction.response.send_message("❌ Geçersiz kanal ID! Sadece sayı girin.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error setting notification channel: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)


class CustomNotificationMessageModal(discord.ui.Modal, title="Bildirim Mesajını Özelleştir"):
    """Modal for customizing notification message"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    message = discord.ui.TextInput(
        label="Özel Bildirim Mesajı",
        placeholder="Özel mesajınızı girin. {user}, {level}, {xp} değişkenlerini kullanabilirsiniz.",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Save custom message
            success = await self.parent_view.save_notification_settings({
                "level_up_message": self.message.value
            })
            
            if success:
                embed = discord.Embed(
                    title="✅ Özel Mesaj Ayarlandı",
                    description="Yeni seviye atlama mesajınız:",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Mesaj",
                    value=self.message.value,
                    inline=False
                )
                embed.add_field(
                    name="💡 İpucu",
                    value="Değişkenler: {user} - Kullanıcı, {level} - Seviye, {xp} - XP",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Mesaj kaydedilemedi.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error setting custom message: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)


class EmbedColorModal(discord.ui.Modal, title="Embed Rengi Ayarla"):
    """Modal for setting embed color"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    color = discord.ui.TextInput(
        label="Hex Renk Kodu",
        placeholder="#00ff00 (varsayılan yeşil) veya red, blue, green gibi renk adları",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            color_input = self.color.value.strip()
            
            # Convert color names to hex
            color_names = {
                "red": "#ff0000", "green": "#00ff00", "blue": "#0000ff",
                "yellow": "#ffff00", "purple": "#800080", "orange": "#ffa500",
                "pink": "#ffc0cb", "brown": "#a52a2a", "black": "#000000",
                "white": "#ffffff", "gray": "#808080", "grey": "#808080"
            }
            
            if color_input.lower() in color_names:
                hex_color = color_names[color_input.lower()]
            elif color_input.startswith("#") and len(color_input) == 7:
                hex_color = color_input
            else:
                await interaction.response.send_message(
                    "❌ Geçersiz renk! #hex kodu (örn: #ff0000) veya renk adı (örn: red) girin.",
                    ephemeral=True
                )
                return
            
            # Validate hex color
            try:
                int(hex_color[1:], 16)
            except ValueError:
                await interaction.response.send_message("❌ Geçersiz hex renk kodu!", ephemeral=True)
                return
            
            # Save color
            success = await self.parent_view.save_notification_settings({
                "level_up_embed_color": hex_color
            })
            
            if success:
                embed = discord.Embed(
                    title="✅ Embed Rengi Ayarlandı",
                    description=f"Yeni embed rengi: `{hex_color}`",
                    color=int(hex_color[1:], 16)
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Renk kaydedilemedi.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error setting embed color: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)


class SpecialLevelMessagesView(discord.ui.View):
    """View for managing special level messages"""
    
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id

    async def get_special_messages(self):
        """Get special level messages"""
        try:
            mongo_db = get_async_db()
            settings = await mongo_db.levelling_settings.find_one({"guild_id": int(self.guild_id)})
            return settings.get("special_level_messages", {}) if settings else {}
        except Exception as e:
            logger.error(f"Error getting special messages: {e}")
            return {}

    async def save_special_message(self, level, message, color=None):
        """Save a special level message"""
        try:
            mongo_db = get_async_db()
            special_messages = await self.get_special_messages()
            special_messages[str(level)] = {
                "message": message,
                "color": color or "#ffd700"  # Default gold color
            }
            
            await mongo_db.levelling_settings.update_one(
                {"guild_id": int(self.guild_id)},
                {"$set": {"special_level_messages": special_messages}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving special message: {e}")
            return False

    @discord.ui.button(label="➕ Özel Mesaj Ekle", style=discord.ButtonStyle.green, row=0)
    async def add_special_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a special level message"""
        modal = AddSpecialMessageModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="➖ Özel Mesaj Kaldır", style=discord.ButtonStyle.red, row=0)
    async def remove_special_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove a special level message"""
        modal = RemoveSpecialMessageModal(self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 Mevcut Özel Mesajlar", style=discord.ButtonStyle.secondary, row=0)
    async def list_special_messages(self, interaction: discord.Interaction, button: discord.ui.Button):
        """List current special messages"""
        try:
            special_messages = await self.get_special_messages()
            
            embed = discord.Embed(
                title="📋 Mevcut Özel Seviye Mesajları",
                description="Özel mesajları olan seviyeler:",
                color=discord.Color.gold()
            )
            
            if not special_messages:
                embed.add_field(
                    name="📝 Bilgi",
                    value="Henüz özel mesaj ayarlanmamış.",
                    inline=False
                )
            else:
                for level, data in sorted(special_messages.items(), key=lambda x: int(x[0])):
                    embed.add_field(
                        name=f"Seviye {level}",
                        value=f"Mesaj: {data['message'][:100]}{'...' if len(data['message']) > 100 else ''}\nRenk: `{data.get('color', '#ffd700')}`",
                        inline=False
                    )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error listing special messages: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)


class AddSpecialMessageModal(discord.ui.Modal, title="Özel Seviye Mesajı Ekle"):
    """Modal for adding special level message"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    level = discord.ui.TextInput(
        label="Seviye",
        placeholder="Özel mesaj için seviye (örn: 10, 25, 50)",
        required=True,
        max_length=3
    )
    
    message = discord.ui.TextInput(
        label="Özel Mesaj",
        placeholder="Bu seviye için özel mesaj. {user}, {level}, {xp} değişkenlerini kullanabilirsiniz.",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    color = discord.ui.TextInput(
        label="Embed Rengi (İsteğe Bağlı)",
        placeholder="#ffd700 veya gold, purple, blue gibi renk adları",
        required=False,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate level
            try:
                level_num = int(self.level.value)
                if level_num < 1 or level_num > 100:
                    await interaction.response.send_message("❌ Seviye 1-100 arasında olmalıdır!", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message("❌ Geçersiz seviye! Sayı girin.", ephemeral=True)
                return
            
            # Process color
            color_input = self.color.value.strip() if self.color.value else "#ffd700"
            color_names = {
                "red": "#ff0000", "green": "#00ff00", "blue": "#0000ff",
                "yellow": "#ffff00", "purple": "#800080", "orange": "#ffa500",
                "pink": "#ffc0cb", "gold": "#ffd700", "silver": "#c0c0c0"
            }
            
            if color_input.lower() in color_names:
                hex_color = color_names[color_input.lower()]
            elif color_input.startswith("#") and len(color_input) == 7:
                try:
                    int(color_input[1:], 16)
                    hex_color = color_input
                except ValueError:
                    hex_color = "#ffd700"
            else:
                hex_color = "#ffd700"
            
            # Save special message
            success = await self.parent_view.save_special_message(level_num, self.message.value, hex_color)
            
            if success:
                embed = discord.Embed(
                    title="✅ Özel Mesaj Eklendi",
                    description=f"Seviye {level_num} için özel mesaj ayarlandı:",
                    color=int(hex_color[1:], 16)
                )
                embed.add_field(name="Mesaj", value=self.message.value, inline=False)
                embed.add_field(name="Renk", value=hex_color, inline=True)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Özel mesaj kaydedilemedi.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error adding special message: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)


class RemoveSpecialMessageModal(discord.ui.Modal, title="Özel Seviye Mesajı Kaldır"):
    """Modal for removing special level message"""
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    level = discord.ui.TextInput(
        label="Seviye",
        placeholder="Kaldırmak istediğiniz özel mesajın seviyesi",
        required=True,
        max_length=3
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate level
            try:
                level_num = int(self.level.value)
            except ValueError:
                await interaction.response.send_message("❌ Geçersiz seviye! Sayı girin.", ephemeral=True)
                return
            
            # Get and update special messages
            special_messages = await self.parent_view.get_special_messages()
            
            if str(level_num) not in special_messages:
                await interaction.response.send_message(f"❌ Seviye {level_num} için özel mesaj bulunamadı!", ephemeral=True)
                return
            
            # Remove message
            del special_messages[str(level_num)]
            
            mongo_db = get_async_db()
            await mongo_db.levelling_settings.update_one(
                {"guild_id": int(self.parent_view.guild_id)},
                {"$set": {"special_level_messages": special_messages}},
                upsert=True
            )
            
            await interaction.response.send_message(
                f"✅ Seviye {level_num} için özel mesaj kaldırıldı!",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error removing special message: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)
