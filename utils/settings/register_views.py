import discord
from discord.ext import commands
from typing import Optional, Dict, Any, List
import logging
import datetime
import re
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
    
    @discord.ui.button(label="Kullanıcı Adı Ayarları", style=discord.ButtonStyle.primary, emoji="✏️", row=0)
    async def username_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure username editing settings"""
        embed = discord.Embed(
            title="✏️ Kullanıcı Adı Ayarları",
            description="Kayıt sonrası kullanıcı adı düzenleme ayarlarını yapılandırın.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(
            embed=embed,
            view=UsernameSettingsView(self.bot, interaction.guild.id),
            ephemeral=True
        )
    
    @discord.ui.button(label="Özel Alanlar", style=discord.ButtonStyle.primary, emoji="📋", row=0)
    async def custom_fields_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure custom registration fields"""
        embed = discord.Embed(
            title="📋 Özel Kayıt Alanları",
            description="Kayıt formuna özel alanlar ekleyin ve format değişkenleri olarak kullanın.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(
            embed=embed,
            view=CustomFieldsView(self.bot, interaction.guild.id),
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
            settings = await self.mongo_db["register"].find_one({"guild_id": interaction.guild.id}) or {}
            
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
            
            # Username editing settings
            auto_edit = settings.get("auto_edit_username", False)
            auto_edit_status = "✅ Etkin" if auto_edit else "❌ Devre Dışı"
            embed.add_field(name="✏️ Otomatik İsim Düzenleme", value=auto_edit_status, inline=True)
            
            # Age roles
            age_roles = settings.get("age_roles", {})
            if age_roles:
                age_roles_text = ""
                for age_range, role_id in age_roles.items():
                    role = interaction.guild.get_role(role_id)
                    role_name = role.mention if role else f"Rol bulunamadı (ID: {role_id})"
                    age_roles_text += f"**{age_range}**: {role_name}\n"
                embed.add_field(name="👤 Yaş Rolleri", value=age_roles_text, inline=False)
            else:
                embed.add_field(name="👤 Yaş Rolleri", value="❌ Ayarlanmamış", inline=False)
            
            # Name format (if auto edit is enabled)
            if auto_edit:
                name_format = settings.get("name_format", "{user_name} | {age}")
                embed.add_field(name="📝 İsim Formatı", value=f"`{name_format}`", inline=True)
            
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
            if len(button_title) > 50:
                button_preview = button_title[:47] + "..."
            else:
                button_preview = button_title
            embed.add_field(name="🎨 Buton Başlığı", value=f"```{button_preview}```", inline=False)
            
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
            await self.mongo_db["register"].update_one(
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
            await self.mongo_db["register"].update_one(
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
        
    @discord.ui.button(label="13-17 Yaş Rolü", style=discord.ButtonStyle.primary, emoji="��", row=0)
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
            await self.mongo_db["register"].update_one(
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
    """View for setting a specific age role with pagination"""
    
    def __init__(self, bot, guild_id, age_range, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.age_range = age_range
        self.mongo_db = get_async_db()
        self.current_page = 0
        
        # Get all roles
        guild = bot.get_guild(guild_id)
        self.all_roles = []
        if guild:
            self.all_roles = [role for role in guild.roles 
                            if not role.is_bot_managed() and not role.is_premium_subscriber() and role.name != "@everyone"]
        
        self.roles_per_page = 20
        self.total_pages = max(1, (len(self.all_roles) + self.roles_per_page - 1) // self.roles_per_page)
        
        self.update_components()
    
    def update_components(self):
        """Update view components based on current page"""
        self.clear_items()
        
        # Add age role select dropdown for current page
        if self.all_roles:
            self.add_item(AgeRoleSelect(self.bot, self.guild_id, self.age_range, 
                                      self.all_roles, self.current_page, self.roles_per_page))
        
        # Add pagination buttons if needed
        if self.total_pages > 1:
            # Previous page button
            prev_button = discord.ui.Button(
                label="◀️ Önceki",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                row=1
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)
            
            # Page info button
            page_button = discord.ui.Button(
                label=f"Sayfa {self.current_page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                row=1
            )
            self.add_item(page_button)
            
            # Next page button
            next_button = discord.ui.Button(
                label="Sonraki ▶️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.total_pages - 1,
                row=1
            )
            next_button.callback = self.next_page
            self.add_item(next_button)
    
    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_components()
            
            embed = discord.Embed(
                title=f"👤 {self.age_range} Yaş Rolü Seçimi",
                description=f"Sayfa {self.current_page + 1}/{self.total_pages} - Toplam {len(self.all_roles)} rol",
                color=discord.Color.blue()
            )
            
            await interaction.response.edit_message(embed=embed, view=self)
    
    async def next_page(self, interaction: discord.Interaction):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_components()
            
            embed = discord.Embed(
                title=f"👤 {self.age_range} Yaş Rolü Seçimi",
                description=f"Sayfa {self.current_page + 1}/{self.total_pages} - Toplam {len(self.all_roles)} rol",
                color=discord.Color.blue()
            )
            
            await interaction.response.edit_message(embed=embed, view=self)

class AgeRoleSelect(discord.ui.Select):
    """Role selection dropdown for age roles with pagination support"""
    
    def __init__(self, bot, guild_id, age_range, all_roles=None, current_page=0, roles_per_page=20):
        self.bot = bot
        self.guild_id = guild_id
        self.age_range = age_range
        self.mongo_db = get_async_db()
        
        options = []
        
        if all_roles:
            # Calculate start and end indices for current page
            start_idx = current_page * roles_per_page
            end_idx = min(start_idx + roles_per_page, len(all_roles))
            page_roles = all_roles[start_idx:end_idx]
            
            # Create options for current page
            for role in page_roles:
                # Truncate long role names
                role_name = role.name
                if len(role_name) > 80:
                    role_name = role_name[:77] + "..."
                
                options.append(discord.SelectOption(
                    label=role_name,
                    value=str(role.id),
                    description=f"Pozisyon: {role.position} | Üye sayısı: {len(role.members)}",
                    emoji="🎭"
                ))
        
        if not options:
            options.append(discord.SelectOption(
                label="Bu sayfada rol bulunamadı",
                value="none",
                description="Başka sayfalara bakın veya rol oluşturun"
            ))
            
        super().__init__(
            placeholder=f"{age_range} yaş grubu için rol seçin... (Sayfa {current_page + 1})",
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
            await self.mongo_db["register"].update_one(
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
    """View for role setting with pagination"""
    
    def __init__(self, bot, guild_id, setting_key, setting_name, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.setting_name = setting_name
        self.mongo_db = get_async_db()
        self.current_page = 0
        
        # Get all roles
        guild = bot.get_guild(guild_id)
        self.all_roles = []
        if guild:
            self.all_roles = [role for role in guild.roles 
                            if not role.is_bot_managed() and not role.is_premium_subscriber() and role.name != "@everyone"]
        
        self.roles_per_page = 20
        self.total_pages = max(1, (len(self.all_roles) + self.roles_per_page - 1) // self.roles_per_page)
        
        self.update_components()
    
    def update_components(self):
        """Update view components based on current page"""
        self.clear_items()
        
        # Add role select dropdown for current page
        if self.all_roles:
            self.add_item(RoleSelect(self.bot, self.guild_id, self.setting_key, self.setting_name, 
                                   self.all_roles, self.current_page, self.roles_per_page))
        
        # Add pagination buttons if needed
        if self.total_pages > 1:
            # Previous page button
            prev_button = discord.ui.Button(
                label="◀️ Önceki",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                row=1
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)
            
            # Page info button
            page_button = discord.ui.Button(
                label=f"Sayfa {self.current_page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                row=1
            )
            self.add_item(page_button)
            
            # Next page button
            next_button = discord.ui.Button(
                label="Sonraki ▶️",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.total_pages - 1,
                row=1
            )
            next_button.callback = self.next_page
            self.add_item(next_button)
    
    async def previous_page(self, interaction: discord.Interaction):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_components()
            
            embed = discord.Embed(
                title=f"🎭 {self.setting_name} Seçimi",
                description=f"Sayfa {self.current_page + 1}/{self.total_pages} - Toplam {len(self.all_roles)} rol",
                color=discord.Color.blue()
            )
            
            await interaction.response.edit_message(embed=embed, view=self)
    
    async def next_page(self, interaction: discord.Interaction):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_components()
            
            embed = discord.Embed(
                title=f"🎭 {self.setting_name} Seçimi",
                description=f"Sayfa {self.current_page + 1}/{self.total_pages} - Toplam {len(self.all_roles)} rol",
                color=discord.Color.blue()
            )
            
            await interaction.response.edit_message(embed=embed, view=self)

class RoleSelect(discord.ui.Select):
    """Role selection dropdown with pagination support"""
    
    def __init__(self, bot, guild_id, setting_key, setting_name, all_roles=None, current_page=0, roles_per_page=20):
        self.bot = bot
        self.guild_id = guild_id
        self.setting_key = setting_key
        self.setting_name = setting_name
        self.mongo_db = get_async_db()
        
        options = []
        
        if all_roles:
            # Calculate start and end indices for current page
            start_idx = current_page * roles_per_page
            end_idx = min(start_idx + roles_per_page, len(all_roles))
            page_roles = all_roles[start_idx:end_idx]
            
            # Create options for current page
            for role in page_roles:
                # Truncate long role names
                role_name = role.name
                if len(role_name) > 80:
                    role_name = role_name[:77] + "..."
                
                options.append(discord.SelectOption(
                    label=role_name,
                    value=str(role.id),
                    description=f"Pozisyon: {role.position} | Üye sayısı: {len(role.members)}",
                    emoji="🎭"
                ))
        
        if not options:
            options.append(discord.SelectOption(
                label="Bu sayfada rol bulunamadı",
                value="none",
                description="Başka sayfalara bakın veya rol oluşturun"
            ))
            
        super().__init__(
            placeholder=f"{setting_name} seçin... (Sayfa {current_page + 1})",
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
            await self.mongo_db["register"].update_one(
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
            await self.mongo_db["register"].update_one(
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
            await self.mongo_db["register"].update_one(
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
            await self.mongo_db["register"].update_one(
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
        
        # Get current value - Note: This should be called from an async context
        # For now, we'll use a default value and load current value in the callback
        settings = {}
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
            await self.mongo_db["register"].update_one(
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
        
        # Get current values - Note: This should be called from an async context
        # For now, we'll use default values and load current values in the callback
        settings = {}
        
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
            await self.mongo_db["register"].update_one(
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

class UsernameSettingsView(discord.ui.View):
    """View for configuring username editing settings"""
    
    def __init__(self, bot, guild_id, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = get_async_db()
    
    @discord.ui.button(label="Otomatik Düzenleme", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
    async def toggle_auto_edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle automatic username editing"""
        try:
            settings = await self.mongo_db["register"].find_one({"guild_id": self.guild_id}) or {}
            current_auto_edit = settings.get("auto_edit_username", False)
            new_auto_edit = not current_auto_edit
            
            await self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {"auto_edit_username": new_auto_edit}},
                upsert=True
            )
            
            status = "etkinleştirildi" if new_auto_edit else "devre dışı bırakıldı"
            await interaction.response.send_message(
                embed=create_embed(f"✅ Otomatik kullanıcı adı düzenleme {status}!", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error toggling auto edit: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Ayar değiştirilirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="İsim Formatı", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def name_format_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure name format"""
        modal = NameFormatModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Mevcut Ayarları Görüntüle", style=discord.ButtonStyle.secondary, emoji="🔍", row=1)
    async def view_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current username settings"""
        try:
            settings = await self.mongo_db["register"].find_one({"guild_id": self.guild_id}) or {}
            
            embed = discord.Embed(
                title="✏️ Kullanıcı Adı Ayarları",
                description="Mevcut kullanıcı adı düzenleme ayarları:",
                color=discord.Color.blue()
            )
            
            # Auto edit status
            auto_edit = settings.get("auto_edit_username", False)
            auto_edit_status = "✅ Etkin" if auto_edit else "❌ Devre Dışı"
            embed.add_field(name="🔄 Otomatik Düzenleme", value=auto_edit_status, inline=True)
            
            # Name format
            name_format = settings.get("name_format", "{user_name} | {age}")
            embed.add_field(name="📝 İsim Formatı", value=f"`{name_format}`", inline=True)
            
            # Available variables
            embed.add_field(
                name="📋 Kullanılabilir Değişkenler",
                value=(
                    "`{user_name}` - Kayıt formundaki isim\n"
                    "`{age}` - Kayıt formundaki yaş\n"
                    "`{discord_name}` - Discord kullanıcı adı\n"
                    "`{member_count}` - Üye numarası"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error viewing username settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Ayarlar görüntülenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class NameFormatModal(discord.ui.Modal):
    """Modal for setting name format"""
    
    def __init__(self, bot, guild_id):
        super().__init__(title="İsim Formatı Ayarla")
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = get_async_db()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get current settings to show available variables
            settings = await self.mongo_db["register"].find_one({"guild_id": self.guild_id}) or {}
            custom_fields = settings.get("custom_fields", {})
            
            # Update name format in database
            await self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {"name_format": self.name_format_input.value}},
                upsert=True
            )
            
            embed = discord.Embed(
                title="✅ İsim Formatı Güncellendi",
                description=f"Yeni format: `{self.name_format_input.value}`",
                color=discord.Color.green()
            )
            
            # Build available variables list
            variables = [
                "`{user_name}` - Kayıt formundaki isim",
                "`{age}` - Kayıt formundaki yaş",
                "`{discord_name}` - Discord kullanıcı adı",
                "`{member_count}` - Üye numarası"
            ]
            
            # Add custom field variables
            for field_key, field_data in custom_fields.items():
                field_name = field_data.get("name", field_key)
                variables.append(f"`{{{field_key}}}` - {field_name}")
            
            embed.add_field(
                name="📋 Kullanılabilir Değişkenler",
                value="\n".join(variables),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error updating name format: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ İsim formatı güncellenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    def __init__(self, bot, guild_id):
        super().__init__(title="İsim Formatı Ayarla")
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = get_async_db()
        
        self.name_format_input = discord.ui.TextInput(
            label="İsim Formatı",
            placeholder="{user_name} | {age}",
            default="{user_name} | {age}",
            max_length=50,
            required=True,
            style=discord.TextStyle.short
        )
        
        self.add_item(self.name_format_input)

class CustomFieldsView(discord.ui.View):
    """View for managing custom registration fields"""
    
    def __init__(self, bot, guild_id, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = get_async_db()
    
    @discord.ui.button(label="Alan Ekle", style=discord.ButtonStyle.success, emoji="➕", row=0)
    async def add_field_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a new custom field"""
        modal = AddCustomFieldModal(self.bot, self.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Alanları Görüntüle", style=discord.ButtonStyle.primary, emoji="📋", row=0)
    async def view_fields_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current custom fields"""
        try:
            settings = await self.mongo_db["register"].find_one({"guild_id": self.guild_id}) or {}
            custom_fields = settings.get("custom_fields", {})
            
            embed = discord.Embed(
                title="📋 Özel Kayıt Alanları",
                description="Mevcut özel alanlar ve format değişkenleri:",
                color=discord.Color.blue()
            )
            
            if custom_fields:
                for field_key, field_data in custom_fields.items():
                    field_name = field_data.get("name", field_key)
                    field_type = field_data.get("type", "text")
                    field_required = "✅ Zorunlu" if field_data.get("required", False) else "❌ İsteğe bağlı"
                    field_placeholder = field_data.get("placeholder", "Yok")
                    
                    embed.add_field(
                        name=f"🔹 {field_name}",
                        value=(
                            f"**Değişken:** `{{{field_key}}}`\n"
                            f"**Tip:** {field_type}\n"
                            f"**Zorunlu:** {field_required}\n"
                            f"**Placeholder:** {field_placeholder}"
                        ),
                        inline=True
                    )
                
                embed.add_field(
                    name="💡 Kullanım",
                    value="Bu alanları isim formatında `{alan_anahtarı}` şeklinde kullanabilirsiniz.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="❌ Özel Alan Yok",
                    value="Henüz özel alan eklenmemiş. 'Alan Ekle' butonunu kullanarak yeni alanlar ekleyebilirsiniz.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error viewing custom fields: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Alanlar görüntülenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    @discord.ui.button(label="Alan Sil", style=discord.ButtonStyle.danger, emoji="🗑️", row=0)
    async def remove_field_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove a custom field"""
        try:
            settings = await self.mongo_db["register"].find_one({"guild_id": self.guild_id}) or {}
            custom_fields = settings.get("custom_fields", {})
            
            if not custom_fields:
                await interaction.response.send_message(
                    embed=create_embed("❌ Silinecek özel alan bulunamadı.", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Create select menu for field removal
            options = []
            for field_key, field_data in custom_fields.items():
                field_name = field_data.get("name", field_key)
                options.append(discord.SelectOption(
                    label=field_name,
                    value=field_key,
                    description=f"Değişken: {{{field_key}}}"
                ))
            
            if len(options) > 25:
                options = options[:25]  # Discord limit
            
            select = discord.ui.Select(
                placeholder="Silinecek alanı seçin...",
                options=options
            )
            
            async def remove_callback(select_interaction):
                field_key = select.values[0]
                field_name = custom_fields[field_key].get("name", field_key)
                
                # Remove field from database
                await self.mongo_db["register"].update_one(
                    {"guild_id": self.guild_id},
                    {"$unset": {f"custom_fields.{field_key}": ""}},
                    upsert=True
                )
                
                await select_interaction.response.send_message(
                    embed=create_embed(f"✅ '{field_name}' alanı başarıyla silindi!", discord.Color.green()),
                    ephemeral=True
                )
            
            select.callback = remove_callback
            view = discord.ui.View()
            view.add_item(select)
            
            await interaction.response.send_message(
                embed=create_embed("🗑️ Silinecek alanı seçin:", discord.Color.orange()),
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error removing custom field: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Alan silinirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class AddCustomFieldModal(discord.ui.Modal):
    """Modal for adding a custom registration field"""
    
    def __init__(self, bot, guild_id):
        super().__init__(title="Özel Alan Ekle")
        self.bot = bot
        self.guild_id = guild_id
        self.mongo_db = get_async_db()
        
        self.field_key = discord.ui.TextInput(
            label="Alan Anahtarı (değişken adı)",
            placeholder="steam_id, discord_tag, vs. (sadece harf, rakam, _)",
            required=True,
            max_length=30
        )
        
        self.field_name = discord.ui.TextInput(
            label="Alan Adı (formda görünecek)",
            placeholder="Steam ID, Discord Tag, vs.",
            required=True,
            max_length=50
        )
        
        self.field_placeholder = discord.ui.TextInput(
            label="Placeholder (ipucu metni)",
            placeholder="Örn: Steam profilinizin ID'sini girin",
            required=False,
            max_length=100
        )
        
        self.field_required = discord.ui.TextInput(
            label="Zorunlu mu? (evet/hayır)",
            placeholder="evet veya hayır",
            required=True,
            max_length=5
        )
        
        # Add items to modal
        self.add_item(self.field_key)
        self.add_item(self.field_name)
        self.add_item(self.field_placeholder)
        self.add_item(self.field_required)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate field key (only alphanumeric and underscore)
            field_key = self.field_key.value.strip().lower()
            if not re.match(r'^[a-z0-9_]+$', field_key):
                await interaction.response.send_message(
                    embed=create_embed("❌ Alan anahtarı sadece harf, rakam ve alt çizgi içerebilir!", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Validate required field
            required_value = self.field_required.value.strip().lower()
            if required_value not in ["evet", "hayır", "yes", "no"]:
                await interaction.response.send_message(
                    embed=create_embed("❌ Zorunlu alanı için 'evet' veya 'hayır' yazın!", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            is_required = required_value in ["evet", "yes"]
            
            # Check if field key already exists
            settings = await self.mongo_db["register"].find_one({"guild_id": self.guild_id}) or {}
            custom_fields = settings.get("custom_fields", {})
            
            if field_key in custom_fields:
                await interaction.response.send_message(
                    embed=create_embed(f"❌ '{field_key}' anahtarı zaten kullanılıyor!", discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Add the new field
            new_field = {
                "name": self.field_name.value.strip(),
                "type": "text",  # For now, only text fields
                "placeholder": self.field_placeholder.value.strip() if self.field_placeholder.value else "",
                "required": is_required,
                "max_length": 100  # Default max length
            }
            
            await self.mongo_db["register"].update_one(
                {"guild_id": self.guild_id},
                {"$set": {f"custom_fields.{field_key}": new_field}},
                upsert=True
            )
            
            embed = discord.Embed(
                title="✅ Özel Alan Eklendi",
                description=f"'{self.field_name.value}' alanı başarıyla eklendi!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="📋 Alan Bilgileri",
                value=(
                    f"**Anahtar:** `{field_key}`\n"
                    f"**Ad:** {self.field_name.value}\n"
                    f"**Zorunlu:** {'✅ Evet' if is_required else '❌ Hayır'}\n"
                    f"**Format Değişkeni:** `{{{field_key}}}`"
                ),
                inline=False
            )
            embed.add_field(
                name="💡 Kullanım",
                value=f"Bu alanı isim formatında `{{{field_key}}}` şeklinde kullanabilirsiniz.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error adding custom field: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Alan eklenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
