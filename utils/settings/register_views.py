import discord
from discord.ext import commands
from typing import Optional, Dict, Any, List
import logging
import datetime
from pathlib import Path
import os

from utils.database.connection import initialize_mongodb
from utils.core.formatting import create_embed, hex_to_int

# Set up logging
logger = logging.getLogger('register_settings')

# Default values for settings
DEFAULT_WELCOME_MESSAGE = "Hoş geldin {mention}! Sunucumuza kayıt olduğun için teşekkürler."
DEFAULT_BUTTON_TITLE = "📝 Sunucu Kayıt Sistemi"
DEFAULT_BUTTON_DESCRIPTION = "Sunucumuza hoş geldiniz! Aşağıdaki butona tıklayarak kayıt olabilirsiniz."
DEFAULT_BUTTON_INSTRUCTIONS = "Kaydınızı tamamlamak için isminizi ve yaşınızı doğru bir şekilde girmeniz gerekmektedir."

class RegisterSettingsView(discord.ui.View):
    """Main view for register settings"""
    
    def __init__(self, bot, ctx, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.mongo_db = initialize_mongodb()
        self.settings_category = "general"  # Default category
        # Add the category selector
        self.add_item(RegisterCategorySelect(self.bot))
        
    @discord.ui.button(label="Kayıt Rolü", style=discord.ButtonStyle.primary, emoji="🔰", row=0)
    async def main_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure the main registration role"""
        await interaction.response.send_message(
            embed=create_embed("Ana kayıt rolünü seçmek için aşağıdaki seçenekleri kullanabilirsiniz.", discord.Color.blue()),
            view=RoleSettingView(self.bot, interaction.guild.id, "role_id", "Ana Kayıt Rolü"),
            ephemeral=True
        )

    @discord.ui.button(label="Yaş Rolleri", style=discord.ButtonStyle.primary, emoji="👤", row=0)
    async def age_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure age-based roles"""
        embed = discord.Embed(
            title="Yaş Rolleri Ayarları",
            description="Üyelerin yaşına göre otomatik olarak verilecek rolleri yapılandırın.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Yaş Doğrulama",
            value="Üyeler kayıt sırasında yaşlarını belirtecekler ve sistem otomatik olarak uygun rolü verecektir.",
            inline=False
        )
        embed.add_field(
            name="Mevcut Roller",
            value="Aşağıdaki butonları kullanarak yaş rollerini yapılandırabilirsiniz.",
            inline=False
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=AgeRolesView(self.bot, interaction.guild.id),
            ephemeral=True
        )
    
    @discord.ui.button(label="Bronz Rol", style=discord.ButtonStyle.primary, emoji="🥉", row=0)
    async def bronze_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure the bronze role"""
        await interaction.response.send_message(
            embed=create_embed("Bronz rolünü seçmek için aşağıdaki seçenekleri kullanabilirsiniz.", discord.Color.blue()),
            view=RoleSettingView(self.bot, interaction.guild.id, "bronze_role_id", "Bronz Rol"),
            ephemeral=True
        )
    
    @discord.ui.button(label="Log Kanalı", style=discord.ButtonStyle.primary, emoji="📊", row=1)
    async def log_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure the log channel"""
        await interaction.response.send_message(
            embed=create_embed("Kayıt log kanalını seçmek için aşağıdaki seçenekleri kullanabilirsiniz.", discord.Color.blue()),
            view=ChannelSettingView(self.bot, interaction.guild.id, "log_channel_id", "Kayıt Log Kanalı"),
            ephemeral=True
        )
    
    @discord.ui.button(label="Kayıt Mesajı", style=discord.ButtonStyle.primary, emoji="💬", row=1)
    async def welcome_message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure the welcome message"""
        # Get current message if exists
        settings = self.mongo_db["register"].find_one({"guild_id": interaction.guild.id}) or {}
        current_message = settings.get("welcome_message", DEFAULT_WELCOME_MESSAGE)
        
        embed = discord.Embed(
            title="Kayıt Mesajı Ayarları",
            description="Kayıt olan üyelere gönderilecek mesaj ayarlarını yapılandırın.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Mevcut Mesaj",
            value=f"```{current_message}```",
            inline=False
        )
        embed.add_field(
            name="Kullanılabilir Değişkenler",
            value="`{mention}` - Üyeyi etiketler\n`{name}` - Üyenin adı\n`{server}` - Sunucu adı\n`{member_count}` - Sunucudaki üye sayısı",
            inline=False
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=MessageSettingView(self.bot, interaction.guild.id),
            ephemeral=True
        )
    
    @discord.ui.button(label="Kayıt Butonunu Oluştur", style=discord.ButtonStyle.success, emoji="✅", row=2)
    async def create_button_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create a registration button in the current channel"""
        try:
            # Check if registration system is configured
            settings = self.mongo_db["register"].find_one({"guild_id": interaction.guild.id})
            if not settings or "role_id" not in settings:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Önce kayıt sistemini yapılandırmalısınız!", discord.Color.red()),
                    ephemeral=True
                )
            
            # Show button customization view
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Kayıt Butonu Oluşturma",
                    description="Kayıt butonunun görünümünü ve içeriğini özelleştirin, ardından oluşturun.",
                    color=discord.Color.blue()
                ),
                view=ButtonCustomizationView(self.bot, interaction.guild.id, interaction.channel),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error creating register button: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Kayıt butonu oluşturulurken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Tüm Ayarları Görüntüle", style=discord.ButtonStyle.secondary, emoji="🔍", row=2)
    async def view_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View all registration settings"""
        try:
            settings = self.mongo_db["register"].find_one({"guild_id": interaction.guild.id})
            if not settings:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Kayıt sistemi henüz yapılandırılmamış!", discord.Color.red()),
                    ephemeral=True
                )
            
            embed = discord.Embed(
                title="📋 Kayıt Sistemi Ayarları",
                color=discord.Color.blue()
            )
            
            # Main role
            role_id = settings.get("role_id")
            if role_id:
                role = interaction.guild.get_role(int(role_id))
                role_value = f"{role.mention} ({role.id})" if role else f"Rol bulunamadı (ID: {role_id})"
                embed.add_field(name="Ana Kayıt Rolü", value=role_value, inline=True)
            else:
                embed.add_field(name="Ana Kayıt Rolü", value="❌ Ayarlanmamış", inline=True)
            
            # Adult role
            adult_role_id = settings.get("adult_role_id")
            if adult_role_id:
                adult_role = interaction.guild.get_role(int(adult_role_id))
                role_value = f"{adult_role.mention} ({adult_role.id})" if adult_role else f"Rol bulunamadı (ID: {adult_role_id})"
                embed.add_field(name="18+ Yaş Rolü", value=role_value, inline=True)
            else:
                embed.add_field(name="18+ Yaş Rolü", value="❌ Ayarlanmamış", inline=True)
            
            # Minor role
            minor_role_id = settings.get("minor_role_id")
            if minor_role_id:
                minor_role = interaction.guild.get_role(int(minor_role_id))
                role_value = f"{minor_role.mention} ({minor_role.id})" if minor_role else f"Rol bulunamadı (ID: {minor_role_id})"
                embed.add_field(name="18- Yaş Rolü", value=role_value, inline=True)
            else:
                embed.add_field(name="18- Yaş Rolü", value="❌ Ayarlanmamış", inline=True)
            
            # Bronze role
            bronze_role_id = settings.get("bronze_role_id")
            if bronze_role_id:
                bronze_role = interaction.guild.get_role(int(bronze_role_id))
                role_value = f"{bronze_role.mention} ({bronze_role.id})" if bronze_role else f"Rol bulunamadı (ID: {bronze_role_id})"
                embed.add_field(name="Bronz Rol", value=role_value, inline=True)
            else:
                embed.add_field(name="Bronz Rol", value="❌ Ayarlanmamış", inline=True)
            
            # Log channel
            log_channel_id = settings.get("log_channel_id")
            if log_channel_id:
                log_channel = interaction.guild.get_channel(int(log_channel_id))
                channel_value = f"{log_channel.mention} ({log_channel.id})" if log_channel else f"Kanal bulunamadı (ID: {log_channel_id})"
                embed.add_field(name="Log Kanalı", value=channel_value, inline=True)
            else:
                embed.add_field(name="Log Kanalı", value="❌ Ayarlanmamış", inline=True)
            
            # Welcome message
            welcome_message = settings.get("welcome_message")
            if welcome_message:
                embed.add_field(name="Karşılama Mesajı", value=welcome_message[:1024], inline=False)
            else:
                embed.add_field(name="Karşılama Mesajı", value="❌ Ayarlanmamış", inline=False)
            
            # Button instructions
            button_instructions = settings.get("button_instructions")
            if button_instructions:
                embed.add_field(name="Buton Talimatları", value=button_instructions[:1024], inline=False)
            else:
                embed.add_field(name="Buton Talimatları", value="❌ Ayarlanmamış", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error viewing register settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Ayarlar görüntülenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Ayarları Sıfırla", style=discord.ButtonStyle.danger, emoji="⚠️", row=3)
    async def reset_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset all registration settings"""
        await interaction.response.send_message(
            embed=create_embed("⚠️ Tüm kayıt ayarlarını sıfırlamak istediğinize emin misiniz?", discord.Color.yellow()),
            view=ConfirmResetView(self.bot, interaction.guild.id),
            ephemeral=True
        )


class AgeRolesView(discord.ui.View):
    """View for configuring age-based roles"""
    
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = initialize_mongodb()
    
    @discord.ui.button(label="18+ Yaş Rolü", style=discord.ButtonStyle.primary, emoji="🔞")
    async def adult_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure the adult role (18+)"""
        await interaction.response.send_message(
            embed=create_embed("18+ yaş rolünü seçmek için aşağıdaki seçenekleri kullanabilirsiniz.", discord.Color.blue()),
            view=RoleSettingView(self.bot, self.guild_id, "adult_role_id", "18+ Yaş Rolü"),
            ephemeral=True
        )
    
    @discord.ui.button(label="18- Yaş Rolü", style=discord.ButtonStyle.primary, emoji="👶")
    async def minor_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure the minor role (under 18)"""
        await interaction.response.send_message(
            embed=create_embed("18- yaş rolünü seçmek için aşağıdaki seçenekleri kullanabilirsiniz.", discord.Color.blue()),
            view=RoleSettingView(self.bot, self.guild_id, "minor_role_id", "18- Yaş Rolü"),
            ephemeral=True
        )


class RoleSettingModal(discord.ui.Modal):
    """Modal for setting a role ID"""
    
    def __init__(self, bot, guild_id, setting_key, title, placeholder):
        super().__init__(title=title)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.mongo_db = initialize_mongodb()
        
        self.role_id = discord.ui.TextInput(
            label="Rol ID",
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
                        embed=create_embed(f"❌ Belirtilen ID ile bir rol bulunamadı: {role_id}", discord.Color.red()),
                        ephemeral=True
                    )
            except ValueError:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Geçerli bir rol ID'si girmelisiniz.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Update the setting in the database
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {self.setting_key: str(role_id)}},
                upsert=True
            )
            
            # Respond to the interaction
            setting_name = self.title
            await interaction.response.send_message(
                embed=create_embed(f"✅ {setting_name} başarıyla {role.mention} olarak ayarlandı!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting role: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Rol ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class ChannelSettingModal(discord.ui.Modal):
    """Modal for setting a channel ID"""
    
    def __init__(self, bot, guild_id, setting_key, title, placeholder):
        super().__init__(title=title)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.mongo_db = initialize_mongodb()
        
        self.channel_id = discord.ui.TextInput(
            label="Kanal ID",
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
                        embed=create_embed(f"❌ Belirtilen ID ile bir kanal bulunamadı: {channel_id}", discord.Color.red()),
                        ephemeral=True
                    )
            except ValueError:
                return await interaction.response.send_message(
                    embed=create_embed("❌ Geçerli bir kanal ID'si girmelisiniz.", discord.Color.red()),
                    ephemeral=True
                )
            
            # Update the setting in the database
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {self.setting_key: channel_id}},
                upsert=True
            )
            
            # Respond to the interaction
            setting_name = self.title
            await interaction.response.send_message(
                embed=create_embed(f"✅ {setting_name} başarıyla {channel.mention} olarak ayarlandı!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting channel: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Kanal ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class MessageSettingModal(discord.ui.Modal):
    """Modal for setting a message text"""
    
    def __init__(self, bot, guild_id, setting_key, title, placeholder):
        super().__init__(title=title)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.mongo_db = initialize_mongodb()
        
        self.message_text = discord.ui.TextInput(
            label="Mesaj",
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
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {self.setting_key: self.message_text.value}},
                upsert=True
            )
            
            # Respond to the interaction
            setting_name = self.title
            await interaction.response.send_message(
                embed=create_embed(f"✅ {setting_name} başarıyla ayarlandı!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting message: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Mesaj ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class ConfirmResetView(discord.ui.View):
    """View for confirming settings reset"""
    
    def __init__(self, bot, guild_id, timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = initialize_mongodb()
    
    @discord.ui.button(label="Evet, Sıfırla", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm reset of all settings"""
        try:
            # Delete all settings for the guild
            self.mongo_db["register"].delete_one({"guild_id": self.guild_id})
            
            # Respond to the interaction
            await interaction.response.send_message(
                embed=create_embed("✅ Tüm kayıt ayarları başarıyla sıfırlandı!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Ayarlar sıfırlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="İptal", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the reset operation"""
        await interaction.response.send_message(
            embed=create_embed("✅ İşlem iptal edildi.", discord.Color.blue()),
            ephemeral=True
        )
