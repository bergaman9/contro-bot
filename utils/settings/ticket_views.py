# Ticket Settings Views - Unified and Working Version
import discord
import logging
import json
from utils.database.connection import get_async_db
from utils.core.formatting import create_embed

logger = logging.getLogger('ticket_settings')

class TicketSettingsView(discord.ui.View):
    """Main view for ticket system settings"""
    
    def __init__(self, bot, guild_id=None, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild_id = guild_id or 0
        self.mongo_db = get_async_db()

    @discord.ui.button(label="🏷️ Kategori Ayarla", style=discord.ButtonStyle.primary, row=0)
    async def set_category_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set ticket category"""
        await interaction.response.send_modal(SetTicketCategoryModal(self.bot, interaction.guild.id))

    @discord.ui.button(label="📝 Log Kanalı", style=discord.ButtonStyle.primary, row=0)
    async def set_log_channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set ticket log channel"""
        await interaction.response.send_modal(SetTicketLogChannelModal(self.bot, interaction.guild.id))

    @discord.ui.button(label="👑 Yetkili Rolleri", style=discord.ButtonStyle.primary, row=0)
    async def set_support_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set support roles"""
        await interaction.response.send_modal(SetSupportRolesModal(self.bot, interaction.guild.id))

    @discord.ui.button(label="🌐 Dil Ayarı", style=discord.ButtonStyle.secondary, row=1)
    async def set_language_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set language"""
        await interaction.response.send_modal(SetLanguageModal(self.bot, interaction.guild.id))

    @discord.ui.button(label="⚙️ Gelişmiş Ayarlar", style=discord.ButtonStyle.secondary, row=1)
    async def advanced_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Advanced settings"""
        await interaction.response.send_modal(AdvancedTicketSettingsModal(self.bot, interaction.guild.id))

    @discord.ui.button(label="📊 Mevcut Ayarlar", style=discord.ButtonStyle.secondary, row=1)
    async def view_settings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current settings"""
        try:
            settings = await self.mongo_db.ticket_settings.find_one({"guild_id": interaction.guild.id})
            
            if not settings:
                embed = discord.Embed(
                    title="📊 Ticket Sistemi Ayarları",
                    description="❌ Bu sunucu için henüz ticket ayarı yapılmamış.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📊 Mevcut Ticket Ayarları",
                color=discord.Color.blue()
            )
            
            # Category
            category_id = settings.get("category_id")
            if category_id:
                category = interaction.guild.get_channel(category_id)
                embed.add_field(
                    name="🏷️ Kategori",
                    value=category.name if category else f"❌ Bulunamadı (ID: {category_id})",
                    inline=True
                )
            else:
                embed.add_field(name="🏷️ Kategori", value="❌ Ayarlanmamış", inline=True)
            
            # Log Channel
            log_channel_id = settings.get("log_channel_id")
            if log_channel_id:
                log_channel = interaction.guild.get_channel(log_channel_id)
                embed.add_field(
                    name="📝 Log Kanalı",
                    value=log_channel.mention if log_channel else f"❌ Bulunamadı (ID: {log_channel_id})",
                    inline=True
                )
            else:
                embed.add_field(name="📝 Log Kanalı", value="❌ Ayarlanmamış", inline=True)
            
            # Language
            language = settings.get("language", "tr")
            lang_display = "🇹🇷 Türkçe" if language == "tr" else "🇺🇸 English"
            embed.add_field(name="🌐 Dil", value=lang_display, inline=True)
            
            # Support Roles
            support_roles = settings.get("support_roles", [])
            if support_roles:
                role_mentions = []
                for role_id in support_roles:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        role_mentions.append(role.mention)
                embed.add_field(
                    name="👑 Yetkili Rolleri",
                    value=", ".join(role_mentions) if role_mentions else "❌ Roller bulunamadı",
                    inline=False
                )
            else:
                embed.add_field(name="👑 Yetkili Rolleri", value="❌ Ayarlanmamış", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error viewing ticket settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Ayarlar görüntülenirken hata: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

    @discord.ui.button(label="🎫 Ticket Paneli Oluştur", style=discord.ButtonStyle.success, row=2)
    async def create_ticket_panel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create ticket panel"""
        embed = discord.Embed(
            title="🎫 Ticket Paneli Oluştur",
            description="Ticket panelini oluşturmak istediğiniz kanalı seçin.",
            color=discord.Color.green()
        )
        
        view = CreateTicketPanelView(self.bot, "tr")  # Default Turkish
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class CreateTicketPanelView(discord.ui.View):
    """View for creating ticket panels in channels"""
    
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        placeholder="Ticket paneli oluşturulacak kanalı seçin...",
        min_values=1,
        max_values=1
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        
        try:
            # Get the actual channel object
            if hasattr(channel, 'id'):
                actual_channel = interaction.guild.get_channel(channel.id)
                if not actual_channel:
                    await interaction.response.send_message("❌ Kanal bulunamadı!", ephemeral=True)
                    return
                channel = actual_channel
            
            # Get language from database
            mongo_db = get_async_db()
            settings = await mongo_db.ticket_settings.find_one({"guild_id": interaction.guild.id})
            language = settings.get("language", "tr") if settings else "tr"
            
            # Create the proper ticket embed (original working version)
            if language == "tr":
                embed = discord.Embed(
                    title="🎫 Destek Sistemi",
                    description="Destek talebinizi oluşturmak için aşağıdaki butona tıklayın ve formu doldurun. Ekibimiz en kısa sürede size yardımcı olacaktır.",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="🛠️ Özel Discord Botu & Web Sitesi",
                    value="Discord botları ve web siteleri geliştirme konusunda da hizmet vermekteyiz. İhtiyaçlarınıza özel çözümler için destek talebi oluşturabilirsiniz.",
                    inline=False
                )
                
                embed.add_field(
                    name="💡 Sunucu İle İlgili İstek ve Önerileriniz",
                    value="Sunucumuz hakkında geri bildirimlerinizi ve önerilerinizi de bu sistem üzerinden iletebilirsiniz.",
                    inline=False
                )
                
                embed.add_field(
                    name="📢 Reklam ve İşbirliği Teklifleri",
                    value="Reklam vermek veya işbirliği yapmak için buradan bizimle iletişime geçebilirsiniz.",
                    inline=False
                )
                
                embed.set_footer(text="Contro", icon_url=self.bot.user.display_avatar.url)
                
            else:
                embed = discord.Embed(
                    title="🎫 Support System",
                    description="Need help? Create a support ticket and our team will assist you!",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="What you can get help with:",
                    value=(
                        "• Technical issues\n"
                        "• Account problems\n"
                        "• General questions\n"
                        "• Bug reports\n"
                        "• Feature requests"
                    ),
                    inline=True
                )
                
                embed.add_field(
                    name="Click the button to create a ticket • Support Team",
                    value="Our team will assist you as soon as possible",
                    inline=False
                )
            
            # Create the working ticket button
            view = TicketCreateView(language=language)
            
            # Send the ticket panel
            await channel.send(embed=embed, view=view)
            
            # Confirm success
            await interaction.response.send_message(
                f"✅ Ticket paneli {channel.mention} kanalında oluşturuldu!",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error creating ticket panel: {e}")
            await interaction.response.send_message(
                f"❌ Ticket paneli oluşturulurken hata: {str(e)}",
                ephemeral=True
            )

class TicketCreateView(discord.ui.View):
    """View with the ticket creation button"""
    
    def __init__(self, language="tr"):
        super().__init__(timeout=None)
        self.language = language
        
        # Add the ticket creation button
        button_label = "🎫 Destek Talebi" if language == "tr" else "🎫 Create Ticket"
        button = discord.ui.Button(
            label=button_label,
            style=discord.ButtonStyle.primary,
            custom_id="create_ticket_button",
            emoji="🎫"
        )
        button.callback = self.create_ticket
        self.add_item(button)
    
    async def create_ticket(self, interaction: discord.Interaction):
        """Handle ticket creation"""
        try:
            # Import the ticket cog to handle ticket creation
            ticket_cog = interaction.client.get_cog("Ticket")
            if ticket_cog:
                await ticket_cog.create_ticket_interaction(interaction)
            else:
                await interaction.response.send_message(
                    "❌ Ticket sistemi şu anda kullanılamıyor." if self.language == "tr" else "❌ Ticket system is currently unavailable.",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.response.send_message(
                f"❌ Ticket oluşturulurken hata: {str(e)}" if self.language == "tr" else f"❌ Error creating ticket: {str(e)}",
                ephemeral=True
            )

# Modal classes for ticket configuration
class SetTicketCategoryModal(discord.ui.Modal):
    """Modal for setting the ticket category"""
    
    def __init__(self, bot, guild_id):
        super().__init__(title="Ticket Kategorisi Ayarla")
        self.bot = bot
        self.guild_id = guild_id
        
        self.category_id = discord.ui.TextInput(
            label="Kategori ID",
            placeholder="Ticket kategorisinin ID'sini girin",
            required=True,
            max_length=20
        )
        self.add_item(self.category_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            category_id = int(self.category_id.value)
            category = interaction.guild.get_channel(category_id)
            
            if not category or not isinstance(category, discord.CategoryChannel):
                await interaction.response.send_message("❌ Geçerli bir kategori ID'si girin!", ephemeral=True)
                return
            
            mongo_db = get_async_db()
            await mongo_db.ticket_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"category_id": category_id}},
                upsert=True
            )
            
            await interaction.response.send_message(f"✅ Ticket kategorisi {category.name} olarak ayarlandı!", ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Geçerli bir kategori ID'si girin!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error setting ticket category: {e}")
            await interaction.response.send_message(f"❌ Hata: {str(e)}", ephemeral=True)

class SetTicketLogChannelModal(discord.ui.Modal):
    """Modal for setting the ticket log channel"""
    
    def __init__(self, bot, guild_id):
        super().__init__(title="Ticket Log Kanalı Ayarla")
        self.bot = bot
        self.guild_id = guild_id
        
        self.channel_id = discord.ui.TextInput(
            label="Log Kanal ID",
            placeholder="Ticket log kanalının ID'sini girin",
            required=True,
            max_length=20
        )
        self.add_item(self.channel_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel_id.value)
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel or not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message("❌ Geçerli bir kanal ID'si girin!", ephemeral=True)
                return
            
            mongo_db = get_async_db()
            await mongo_db.ticket_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"log_channel_id": channel_id}},
                upsert=True
            )
            
            await interaction.response.send_message(f"✅ Ticket log kanalı {channel.mention} olarak ayarlandı!", ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Geçerli bir kanal ID'si girin!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error setting ticket log channel: {e}")
            await interaction.response.send_message(f"❌ Hata: {str(e)}", ephemeral=True)

class SetSupportRolesModal(discord.ui.Modal):
    """Modal for setting support roles"""
    
    def __init__(self, bot, guild_id):
        super().__init__(title="Yetkili Rolleri Ayarla")
        self.bot = bot
        self.guild_id = guild_id
        
        self.role_ids = discord.ui.TextInput(
            label="Yetkili Rol ID'leri",
            placeholder="Rol ID'lerini virgülle ayırarak girin (örn: 123456789,987654321)",
            style=discord.TextStyle.long,
            required=True,
            max_length=500
        )
        self.add_item(self.role_ids)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_ids = [int(role_id.strip()) for role_id in self.role_ids.value.split(",")]
            
            # Validate roles exist
            valid_roles = []
            for role_id in role_ids:
                role = interaction.guild.get_role(role_id)
                if role:
                    valid_roles.append(role_id)
            
            if not valid_roles:
                await interaction.response.send_message("❌ Geçerli rol bulunamadı!", ephemeral=True)
                return
            
            mongo_db = get_async_db()
            await mongo_db.ticket_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"support_roles": valid_roles}},
                upsert=True
            )
            
            role_mentions = [interaction.guild.get_role(role_id).mention for role_id in valid_roles]
            await interaction.response.send_message(f"✅ Yetkili rolleri ayarlandı: {', '.join(role_mentions)}!", ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Geçerli rol ID'leri girin!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error setting support roles: {e}")
            await interaction.response.send_message(f"❌ Hata: {str(e)}", ephemeral=True)

class SetLanguageModal(discord.ui.Modal):
    """Modal for setting the ticket system language"""
    
    def __init__(self, bot, guild_id):
        super().__init__(title="Ticket Dil Ayarı")
        self.bot = bot
        self.guild_id = guild_id
        
        self.language = discord.ui.TextInput(
            label="Dil (tr/en)",
            placeholder="Türkçe için 'tr', İngilizce için 'en' yazın",
            required=True,
            max_length=2
        )
        self.add_item(self.language)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            lang = self.language.value.lower().strip()
            if lang not in ["en", "tr"]:
                await interaction.response.send_message("❌ Geçersiz dil! Türkçe için 'tr', İngilizce için 'en' kullanın.", ephemeral=True)
                return
            
            mongo_db = get_async_db()
            await mongo_db.ticket_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"language": lang}},
                upsert=True
            )
            
            lang_name = "Türkçe" if lang == "tr" else "English"
            await interaction.response.send_message(f"✅ Ticket dili {lang_name} olarak ayarlandı!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error setting ticket language: {e}")
            await interaction.response.send_message(f"❌ Hata: {str(e)}", ephemeral=True)

class AdvancedTicketSettingsModal(discord.ui.Modal):
    """Modal for configuring advanced ticket settings"""
    
    def __init__(self, bot, guild_id):
        super().__init__(title="Gelişmiş Ticket Ayarları")
        self.bot = bot
        self.guild_id = guild_id
        
        self.auto_close_days = discord.ui.TextInput(
            label="Otomatik kapanma (gün)",
            placeholder="Ticket'ın kaç gün sonra otomatik kapanacağını girin",
            required=False,
            max_length=3
        )
        
        self.max_tickets_per_user = discord.ui.TextInput(
            label="Kullanıcı başına maksimum ticket",
            placeholder="Bir kullanıcının aynı anda kaç ticket açabileceğini girin",
            required=False,
            max_length=3
        )
        
        self.ticket_naming_format = discord.ui.TextInput(
            label="Ticket adlandırma formatı",
            placeholder="Ticket kanallarının adlandırma formatını girin (örn: ticket-{user})",
            required=False,
            max_length=100
        )
        
        # Add items to the modal
        self.add_item(self.auto_close_days)
        self.add_item(self.max_tickets_per_user)
        self.add_item(self.ticket_naming_format)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            mongo_db = get_async_db()
            update_data = {}
            
            if self.auto_close_days.value:
                try:
                    days = int(self.auto_close_days.value)
                    if days > 0:
                        update_data["auto_close_days"] = days
                except ValueError:
                    await interaction.response.send_message("❌ Geçersiz gün değeri!", ephemeral=True)
                    return
            
            if self.max_tickets_per_user.value:
                try:
                    max_tickets = int(self.max_tickets_per_user.value)
                    if max_tickets > 0:
                        update_data["max_tickets_per_user"] = max_tickets
                except ValueError:
                    await interaction.response.send_message("❌ Geçersiz maksimum ticket değeri!", ephemeral=True)
                    return
            
            if self.ticket_naming_format.value:
                update_data["ticket_naming_format"] = self.ticket_naming_format.value
            
            if update_data:
                await mongo_db.ticket_settings.update_one(
                    {"guild_id": interaction.guild.id},
                    {"$set": update_data},
                    upsert=True
                )
            
            await interaction.response.send_message("✅ Gelişmiş ticket ayarları güncellendi!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error updating advanced ticket settings: {e}")
            await interaction.response.send_message(f"❌ Hata: {str(e)}", ephemeral=True) 