import discord
from discord.ext import commands
from typing import Optional, Dict, Any, List
import logging
import datetime
from pathlib import Path
import os

from utils.database.connection import get_async_db
from utils.core.formatting import create_embed, hex_to_int

# Set up logging
logger = logging.getLogger('register_settings')

# Default values for settings - Turkish
DEFAULT_WELCOME_MESSAGE = "Hoş geldin {mention}! Sunucumuza kayıt olduğun için teşekkürler."
DEFAULT_BUTTON_TITLE_TR = "📝 Sunucu Kayıt Sistemi"
DEFAULT_BUTTON_DESCRIPTION_TR = "Sunucumuza hoş geldiniz! Aşağıdaki butona tıklayarak kayıt olabilirsiniz."
DEFAULT_BUTTON_INSTRUCTIONS_TR = "Kaydınızı tamamlamak için isminizi ve yaşınızı doğru bir şekilde girmeniz gerekmektedir."

# Default values for settings - English
DEFAULT_BUTTON_TITLE_EN = "📝 Server Registration System"
DEFAULT_BUTTON_DESCRIPTION_EN = "Welcome to our server! You can register by clicking the button below."
DEFAULT_BUTTON_INSTRUCTIONS_EN = "To complete your registration, you need to enter your name and age correctly."

# Backward compatibility
DEFAULT_BUTTON_TITLE = DEFAULT_BUTTON_TITLE_TR
DEFAULT_BUTTON_DESCRIPTION = DEFAULT_BUTTON_DESCRIPTION_TR
DEFAULT_BUTTON_INSTRUCTIONS = DEFAULT_BUTTON_INSTRUCTIONS_TR

class RegisterSettingsView(discord.ui.View):
    """Main view for register settings"""
    
    def __init__(self, bot, guild_id, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = get_async_db()
    
    @discord.ui.button(label="Ana Rol", style=discord.ButtonStyle.primary, emoji="🔰", row=0)
    async def main_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure the main registration role (replaces member role)"""
        embed = discord.Embed(
            title="🔰 Ana Kayıt Rolü",
            description="Kayıt olan üyelere otomatik olarak verilecek ana rolü seçin. Bu rol, yaş rolleri yapılandırılmamışsa verilecek varsayılan roldür.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(
            embed=embed,
            view=RoleSettingView(self.bot, interaction.guild.id, "role_id", "Ana Kayıt Rolü"),
            ephemeral=True
        )

    @discord.ui.button(label="Yaş Rolleri", style=discord.ButtonStyle.primary, emoji="👤", row=0)
    async def age_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure age-based roles"""
        embed = discord.Embed(
            title="👤 Yaş Rolleri Ayarları",
            description="Üyelerin yaşına göre otomatik olarak verilecek rolleri yapılandırın. Yaş rolleri varsa ana rol yerine bu roller kullanılır.",
            color=discord.Color.blue()
        )
        
        # Show current age roles if any
        settings = await self.mongo_db["register"].find_one({"guild_id": interaction.guild.id}) or {}
        age_roles = settings.get("age_roles", {})
        
        if age_roles:
            age_roles_text = ""
            for age_range, role_id in age_roles.items():
                role = interaction.guild.get_role(role_id)
                role_name = role.mention if role else f"Rol bulunamadı (ID: {role_id})"
                age_roles_text += f"**{age_range}**: {role_name}\n"
            embed.add_field(name="Mevcut Yaş Rolleri", value=age_roles_text, inline=False)
        else:
            embed.add_field(name="Yaş Rolleri", value="❌ Henüz ayarlanmamış", inline=False)
        
        await interaction.response.send_message(
            embed=embed,
            view=AgeRolesView(self.bot, interaction.guild.id),
            ephemeral=True
        )
    
    @discord.ui.button(label="Kayıt Kanalı", style=discord.ButtonStyle.primary, emoji="📢", row=0)
    async def channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure the registration channel"""
        try:
            embed = discord.Embed(
                title="📢 Kayıt Kanalı",
                description="Kayıt butonunun yerleştirileceği ve kayıt işlemlerinin yapılacağı kanalı seçin.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(
                embed=embed,
                view=ChannelSettingView(self.bot, interaction.guild.id, "channel_id", "Kayıt Kanalı"),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in channel_button: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=create_embed(f"❌ Kanal ayarları açılırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Mesaj Ayarları", style=discord.ButtonStyle.primary, emoji="💬", row=1)
    async def message_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure registration messages"""
        # Get current message if exists
        settings = await self.mongo_db["register"].find_one({"guild_id": interaction.guild.id}) or {}
        current_message = settings.get("welcome_message", DEFAULT_WELCOME_MESSAGE)
        
        embed = discord.Embed(
            title="💬 Kayıt Mesajı Ayarları",
            description="Kayıt olan üyelere gönderilecek mesaj ayarlarını yapılandırın.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📝 Mevcut Mesaj",
            value=f"```{current_message}```",
            inline=False
        )
        embed.add_field(
            name="📋 Kullanılabilir Değişkenler",
            value=(
                "`{mention}` - Kullanıcıyı etiketler\n"
                "`{name}` - Kullanıcının Discord adı\n"
                "`{server}` - Sunucu adı\n"
                "`{member_count}` - Sunucu üye sayısı\n"
                "`{user_name}` - Kayıt formundaki isim\n"
                "`{age}` - Kayıt formundaki yaş"            ),
            inline=False
        )
        
        embed.add_field(
            name="🎨 Format Seçenekleri",
            value="Embed formatı veya düz metin formatı arasında seçim yapabilirsiniz.",
            inline=False
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=MessageFormatView(self.bot, interaction.guild.id),
            ephemeral=True
        )
    
    @discord.ui.button(label="Buton Özelleştirme", style=discord.ButtonStyle.primary, emoji="🎨", row=1)
    async def button_customization_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Customize registration button appearance"""
        await interaction.response.send_message(
            embed=create_embed("Kayıt butonu görünümünü özelleştirin.", discord.Color.blue()),
            view=ButtonCustomizationView(self.bot, interaction.guild.id),
            ephemeral=True
        )
    
    @discord.ui.button(label="Kayıt Mesajını Oluştur", style=discord.ButtonStyle.success, emoji="✅", row=1)
    async def create_button_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create a registration button in the current channel"""        
        try:
            # Get settings from database
            settings = await self.mongo_db["register"].find_one({"guild_id": interaction.guild.id}) or {}
            
            # Detect language preference
            user_language = "tr"  # Default to Turkish
            if hasattr(interaction.guild, 'preferred_locale'):
                if interaction.guild.preferred_locale and 'en' in str(interaction.guild.preferred_locale):
                    user_language = "en"
            
            # Get button customization with language support
            if user_language == "en":
                button_title = settings.get("button_title", DEFAULT_BUTTON_TITLE_EN)
                button_description = settings.get("button_description", DEFAULT_BUTTON_DESCRIPTION_EN)
                button_instructions = settings.get("button_instructions", DEFAULT_BUTTON_INSTRUCTIONS_EN)
            else:
                button_title = settings.get("button_title", DEFAULT_BUTTON_TITLE_TR)
                button_description = settings.get("button_description", DEFAULT_BUTTON_DESCRIPTION_TR)
                button_instructions = settings.get("button_instructions", DEFAULT_BUTTON_INSTRUCTIONS_TR)
            
            # Create registration statistics card
            try:
                from utils.community.turkoyto.card_renderer import create_register_card
                card_path = await create_register_card(self.bot, interaction.guild, self.mongo_db)
            except Exception as e:
                logger.error(f"Error creating registration card: {e}")
                card_path = None
            
            # Create embed for button message
            embed = discord.Embed(
                title=button_title,
                description=button_description,
                color=discord.Color.blue()
            )
            
            # Add instructions field with language support
            instructions_title = "📋 How to Register?" if user_language == "en" else "📋 Nasıl Kayıt Olursunuz?"
            embed.add_field(
                name=instructions_title,
                value=button_instructions,
                inline=False
            )
            
            # Add bot name and avatar to footer with language support
            bot_name = self.bot.user.display_name
            footer_text = f"Click the button to open registration form • {bot_name}" if user_language == "en" else f"Butona tıklayarak kayıt formunu açabilirsiniz • {bot_name}"
            embed.set_footer(
                text=footer_text,
                icon_url=self.bot.user.display_avatar.url
            )
            
            # Add registration statistics image if available
            if card_path:
                embed.set_image(url=f"attachment://register_stats.png")
            
            # Import the registration button view from the register cog
            from cogs.register import RegisterButton
            
            # Send the registration button with image if available
            if card_path:
                with open(card_path, 'rb') as f:
                    file = discord.File(f, filename="register_stats.png")
                    await interaction.channel.send(embed=embed, file=file, view=RegisterButton(language=user_language))
                # Clean up the temporary file
                try:
                    import os
                    os.remove(card_path)
                except Exception:
                    pass
            else:
                await interaction.channel.send(embed=embed, view=RegisterButton(language=user_language))
            
            # Update channel_id in database
            await self.mongo_db["register"].update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"channel_id": interaction.channel.id}},
                upsert=True
            )
            
            success_msg = "✅ Registration message created successfully!" if user_language == "en" else "✅ Kayıt mesajı başarıyla oluşturuldu!"
            await interaction.response.send_message(
                embed=create_embed(success_msg, discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error creating registration button: {e}")
            error_msg = f"❌ Error creating registration message: {str(e)}" if user_language == "en" else f"❌ Kayıt mesajı oluşturulurken bir hata oluştu: {str(e)}"
            await interaction.response.send_message(
                embed=create_embed(error_msg, discord.Color.red()),
                ephemeral=True
            )

    @discord.ui.button(label="Tüm Ayarları Görüntüle", style=discord.ButtonStyle.secondary, emoji="🔍", row=2)
    async def view_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View all registration settings"""
        try:
            settings = self.mongo_db["register"].find_one({"guild_id": interaction.guild.id}) or {}
            
            embed = discord.Embed(
                title="🔍 Kayıt Sistemi Ayarları",
                description="Mevcut kayıt sistemi ayarlarınızın özeti:",
                color=discord.Color.blue()
            )
            
            # Main role
            main_role_id = settings.get("role_id")
            if main_role_id:
                role = interaction.guild.get_role(main_role_id)
                main_role = role.mention if role else f"Rol bulunamadı (ID: {main_role_id})"
            else:
                main_role = "❌ Ayarlanmamış"
            embed.add_field(name="🔰 Ana Rol", value=main_role, inline=True)
            
            # Registration channel
            channel_id = settings.get("channel_id")
            if channel_id:
                channel = interaction.guild.get_channel(channel_id)
                reg_channel = channel.mention if channel else f"Kanal bulunamadı (ID: {channel_id})"
            else:
                reg_channel = "❌ Ayarlanmamış"
            embed.add_field(name="📢 Kayıt Kanalı", value=reg_channel, inline=True)
            
            # Age roles
            age_roles = settings.get("age_roles", {})
            if age_roles:
                age_roles_count = len(age_roles)
                embed.add_field(name="👤 Yaş Rolleri", value=f"✅ {age_roles_count} yaş rolü", inline=True)
            else:
                embed.add_field(name="👤 Yaş Rolleri", value="❌ Ayarlanmamış", inline=True)
            
            # Welcome message
            welcome_message = settings.get("welcome_message", DEFAULT_WELCOME_MESSAGE)
            if len(welcome_message) > 50:
                message_preview = welcome_message[:47] + "..."
            else:
                message_preview = welcome_message
            
            if welcome_message:
                embed.add_field(name="💬 Karşılama Mesajı", value=f"```{message_preview}```", inline=False)
            else:
                embed.add_field(name="💬 Karşılama Mesajı", value="❌ Ayarlanmamış", inline=False)
            
            # Message format
            message_format = settings.get("message_format", "embed")
            format_text = "📋 Embed Formatı" if message_format == "embed" else "📝 Düz Metin"
            embed.add_field(name="🎨 Mesaj Formatı", value=format_text, inline=True)
            
            # Button customization
            button_title = settings.get("button_title", DEFAULT_BUTTON_TITLE)
            embed.add_field(name="🎨 Buton Başlığı", value=f"```{button_title}```", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error viewing settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Ayarlar görüntülenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class MessageFormatView(discord.ui.View):
    """View for configuring message format options"""
    
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = get_async_db()
    
    @discord.ui.button(label="Embed Formatı", style=discord.ButtonStyle.primary, emoji="📋")
    async def embed_format_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set message format to embed"""
        try:
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {"message_format": "embed"}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed("✅ Kayıt mesajları artık embed formatında gönderilecek!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting embed format: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Format ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Düz Metin", style=discord.ButtonStyle.secondary, emoji="📝")
    async def plain_format_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set message format to plain text"""
        try:
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {"message_format": "plain"}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed("✅ Kayıt mesajları artık düz metin olarak gönderilecek!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting plain format: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Format ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Mesajı Düzenle", style=discord.ButtonStyle.success, emoji="✏️")
    async def edit_message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit the welcome message"""
        await interaction.response.send_modal(
            MessageSettingModal(
                self.bot, self.guild_id, "welcome_message", "Kayıt Mesajı", 
                "Kayıt olan üyelere gönderilecek mesajı girin..."
            )
        )

class AgeRolesView(discord.ui.View):
    """View for configuring age-based roles"""
    
    def __init__(self, bot, guild_id, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = get_async_db()
        
    @discord.ui.button(label="13-17 Yaş Rolü", style=discord.ButtonStyle.primary, emoji="👶", row=0)
    async def young_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set role for 13-17 age group"""
        embed = discord.Embed(
            title="👶 13-17 Yaş Rolü",
            description="13-17 yaş aralığındaki üyelere verilecek rolü seçin.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(
            embed=embed,
            view=AgeRoleSettingView(self.bot, self.guild_id, "13-17"),
            ephemeral=True
        )
        
    @discord.ui.button(label="18+ Yaş Rolü", style=discord.ButtonStyle.primary, emoji="🧑", row=0)
    async def adult_role_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set role for 18+ age group"""
        embed = discord.Embed(
            title="🧑 18+ Yaş Rolü",
            description="18 yaş ve üzeri üyelere verilecek rolü seçin.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(
            embed=embed,
            view=AgeRoleSettingView(self.bot, self.guild_id, "18+"),
            ephemeral=True
        )
        
    @discord.ui.button(label="Yaş Rollerini Temizle", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def clear_age_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Clear all age roles"""
        try:
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$unset": {"age_roles": ""}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed("✅ Tüm yaş rolleri temizlendi!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error clearing age roles: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Yaş rolleri temizlenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class AgeRoleSettingView(discord.ui.View):
    """View for setting a specific age role"""
    
    def __init__(self, bot, guild_id, age_range, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.age_range = age_range
        self.mongo_db = get_async_db()
        
        # Add role select dropdown
        self.add_item(AgeRoleSelect(bot, guild_id, age_range))

class AgeRoleSelect(discord.ui.Select):
    """Role selection dropdown for age roles"""
    
    def __init__(self, bot, guild_id, age_range):
        self.bot = bot
        self.guild_id = guild_id
        self.age_range = age_range
        self.mongo_db = get_async_db()
        
        # Get roles from guild
        guild = bot.get_guild(guild_id)
        options = []
        
        if guild:
            for role in guild.roles[:24]:  # Discord limit of 25 options
                if not role.is_bot_managed() and not role.is_premium_subscriber() and role.name != "@everyone":
                    options.append(discord.SelectOption(
                        label=role.name,
                        value=str(role.id),
                        description=f"Pozisyon: {role.position}",
                        emoji="🎭"
                    ))
        
        if not options:
            options.append(discord.SelectOption(
                label="Rol bulunamadı",
                value="none",
                description="Bu sunucuda uygun rol bulunamadı"
            ))
            
        super().__init__(
            placeholder=f"{age_range} yaş grubu için rol seçin...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message(
                embed=create_embed("❌ Geçerli bir rol seçilmedi.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        try:
            role_id = int(self.values[0])
            role = interaction.guild.get_role(role_id)
            
            if not role:
                await interaction.response.send_message(
                    embed=create_embed("❌ Seçilen rol bulunamadı.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Update age roles in database
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {f"age_roles.{self.age_range}": role_id}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed(f"✅ {self.age_range} yaş grubu rolü {role.mention} olarak ayarlandı!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting age role: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Rol ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class RoleSettingView(discord.ui.View):
    """View for role setting with both dropdown and manual ID input"""
    
    def __init__(self, bot, guild_id, setting_key, setting_name, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.setting_name = setting_name
        self.mongo_db = get_async_db()
        
        # Add role select dropdown
        self.add_item(RoleSelect(bot, guild_id, setting_key, setting_name))

class RoleSelect(discord.ui.Select):
    """Role selection dropdown"""
    
    def __init__(self, bot, guild_id, setting_key, setting_name):
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.setting_name = setting_name
        self.mongo_db = get_async_db()
        
        # Get roles from guild
        guild = bot.get_guild(guild_id)
        options = []
        
        if guild:
            for role in guild.roles[:24]:  # Discord limit of 25 options
                if not role.is_bot_managed() and not role.is_premium_subscriber() and role.name != "@everyone":
                    options.append(discord.SelectOption(
                        label=role.name,
                        value=str(role.id),
                        description=f"Pozisyon: {role.position}",
                        emoji="🎭"
                    ))
        
        if not options:
            options.append(discord.SelectOption(
                label="Rol bulunamadı",
                value="none",
                description="Bu sunucuda uygun rol bulunamadı"
            ))
            
        super().__init__(
            placeholder=f"{setting_name} seçin...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message(
                embed=create_embed("❌ Geçerli bir rol seçilmedi.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        try:
            role_id = int(self.values[0])
            role = interaction.guild.get_role(role_id)
            
            if not role:
                await interaction.response.send_message(
                    embed=create_embed("❌ Seçilen rol bulunamadı.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Update role in database
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {self.setting_key: role_id}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed(f"✅ {self.setting_name} {role.mention} olarak ayarlandı!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting role: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Rol ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class ChannelSettingView(discord.ui.View):
    """View for channel setting with both dropdown and manual ID input"""
    
    def __init__(self, bot, guild_id, setting_key, setting_name, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.setting_name = setting_name
        self.mongo_db = get_async_db()
        
        # Add channel select dropdown
        self.add_item(ChannelSelect(bot, guild_id, setting_key, setting_name))

class ChannelSelect(discord.ui.Select):
    """Channel selection dropdown"""
    
    def __init__(self, bot, guild_id, setting_key, setting_name):
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.setting_name = setting_name
        self.mongo_db = get_async_db()
        
        # Get text channels from guild
        guild = bot.get_guild(guild_id)
        options = []
        
        if guild:
            for channel in guild.text_channels[:24]:  # Discord limit of 25 options
                options.append(discord.SelectOption(
                    label=f"#{channel.name}",
                    value=str(channel.id),
                    description=f"Kategori: {channel.category.name if channel.category else 'Kategori yok'}",
                    emoji="📢"
                ))
        
        if not options:
            options.append(discord.SelectOption(
                label="Kanal bulunamadı",
                value="none",
                description="Bu sunucuda metin kanalı bulunamadı"
            ))
            
        super().__init__(
            placeholder=f"{setting_name} seçin...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message(
                embed=create_embed("❌ Geçerli bir kanal seçilmedi.", discord.Color.red()),
                ephemeral=True
            )
            return
            
        try:
            channel_id = int(self.values[0])
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                await interaction.response.send_message(
                    embed=create_embed("❌ Seçilen kanal bulunamadı.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Update channel in database
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {self.setting_key: channel_id}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed(f"✅ {self.setting_name} {channel.mention} olarak ayarlandı!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting channel: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Kanal ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class MessageSettingView(discord.ui.View):
    """View for message setting"""
    
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = get_async_db()
    
    @discord.ui.button(label="Mesajı Düzenle", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit the welcome message"""
        modal = MessageSettingModal(
            self.bot, self.guild_id, "welcome_message", "Kayıt Mesajı",
            "Kayıt olan üyelere gönderilecek mesajı girin..."
        )
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Varsayılan Mesajı Kullan", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def default_message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset to default message"""
        try:
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {"welcome_message": DEFAULT_WELCOME_MESSAGE}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed("✅ Kayıt mesajı varsayılan değere sıfırlandı!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting default message: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Mesaj sıfırlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class ButtonCustomizationView(discord.ui.View):
    """View for customizing register button appearance"""
    
    def __init__(self, bot, guild_id, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = get_async_db()
    
    @discord.ui.button(label="Buton Metnini Düzenle", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_button_text(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Edit button text and description"""
        modal = ButtonTextModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Varsayılan Değerleri Kullan", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def default_button_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reset button settings to default"""
        try:
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {
                    "button_title": DEFAULT_BUTTON_TITLE,
                    "button_description": DEFAULT_BUTTON_DESCRIPTION,
                    "button_instructions": DEFAULT_BUTTON_INSTRUCTIONS
                }},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed("✅ Buton ayarları varsayılan değerlere sıfırlandı!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error resetting button settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Buton ayarları sıfırlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class MessageSettingModal(discord.ui.Modal):
    """Modal for setting messages"""
    
    def __init__(self, bot, guild_id, setting_key, title, placeholder):
        super().__init__(title=title)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.mongo_db = get_async_db()
        
        # Get current value
        settings = self.mongo_db["register"].find_one({"guild_id": guild_id}) or {}
        current_value = settings.get(setting_key, DEFAULT_WELCOME_MESSAGE if setting_key == "welcome_message" else "")
        
        self.text_input = discord.ui.TextInput(
            label="Mesaj",
            placeholder=placeholder,
            default=current_value,
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        self.add_item(self.text_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Update in database
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {self.setting_key: self.text_input.value}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed("✅ Mesaj başarıyla güncellendi!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Mesaj güncellenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class ButtonTextModal(discord.ui.Modal, title="Buton Metni Düzenle"):
    """Modal for editing button text"""
    
    def __init__(self, bot, guild_id):
        super().__init__()
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = get_async_db()
        
        # Get current values
        settings = self.mongo_db["register"].find_one({"guild_id": guild_id}) or {}
        
        self.button_title = discord.ui.TextInput(
            label="Buton Başlığı",
            placeholder="Kayıt butonu için başlık girin...",
            default=settings.get("button_title", DEFAULT_BUTTON_TITLE),
            max_length=100,
            required=True
        )
        
        self.button_description = discord.ui.TextInput(
            label="Buton Açıklaması",
            placeholder="Kayıt butonu için açıklama girin...",
            default=settings.get("button_description", DEFAULT_BUTTON_DESCRIPTION),
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True
        )
        
        self.button_instructions = discord.ui.TextInput(
            label="Kayıt Talimatları",
            placeholder="Kayıt işlemi için talimatlar girin...",
            default=settings.get("button_instructions", DEFAULT_BUTTON_INSTRUCTIONS),
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True
        )
        
        self.add_item(self.button_title)
        self.add_item(self.button_description)
        self.add_item(self.button_instructions)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Update button settings in database
            self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {
                    "button_title": self.button_title.value,
                    "button_description": self.button_description.value,
                    "button_instructions": self.button_instructions.value
                }},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed("✅ Buton metinleri başarıyla güncellendi!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error updating button text: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Buton metinleri güncellenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
