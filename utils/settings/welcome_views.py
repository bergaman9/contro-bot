import discord
from discord import ui
import logging
from typing import Optional, List
import asyncio
from utils.core.formatting import create_embed
from utils.database.connection import get_async_db, ensure_async_db

# Setup logger
logger = logging.getLogger('welcome_views')

class WelcomeSettingsCustomView(ui.View):
    """View for configuring welcome/goodbye settings"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        
    async def get_db(self):
        """Helper method to get async database connection"""
        return get_async_db()
        
    @ui.button(label="👋 Hoş Geldin Mesajı", style=discord.ButtonStyle.primary, row=0)
    async def welcome_message(self, interaction: discord.Interaction, button: ui.Button):
        # Open welcome message modal
        modal = WelcomeMessageModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)

    @ui.button(label="👋 Güle Güle Mesajı", style=discord.ButtonStyle.primary, row=0) 
    async def goodbye_message(self, interaction: discord.Interaction, button: ui.Button):
        # Open goodbye message modal
        modal = GoodbyeMessageModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)

    @ui.button(label="🖼️ Özel Kartlar", style=discord.ButtonStyle.secondary, row=0)
    async def custom_cards(self, interaction: discord.Interaction, button: ui.Button):
        # Open card customization settings
        embed = discord.Embed(
            title="🖼️ Özel Karşılama/Veda Kartları",
            description="Kart tasarımını özelleştirin:",
            color=discord.Color.blue()
        )
        
        # Create card customization view
        view = CardCustomizationView(self.bot, self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="📨 DM Mesajları", style=discord.ButtonStyle.secondary, row=1)
    async def dm_messages(self, interaction: discord.Interaction, button: ui.Button):
        # Open DM message settings
        embed = discord.Embed(
            title="📨 DM Mesaj Ayarları",
            description="Özel mesaj ayarlarını yapılandırın:",
            color=discord.Color.blue()
        )
        
        # Create DM settings view
        view = DMSettingsView(self.bot, self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @ui.button(label="📢 Mesaj Kanalı", style=discord.ButtonStyle.success, row=1)
    async def channel_settings(self, interaction: discord.Interaction, button: ui.Button):
        # Open channel selector
        modal = WelcomeChannelModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="📋 Mevcut Ayarlar", style=discord.ButtonStyle.secondary, row=2)
    async def current_settings(self, interaction: discord.Interaction, button: ui.Button):
        # Display current welcome settings
        await self.display_current_settings(interaction)
    
    @ui.button(label="❌ Kapat", style=discord.ButtonStyle.danger, row=2)
    async def close_menu(self, interaction: discord.Interaction, button: ui.Button):
        # Close the menu
        await interaction.response.edit_message(
            content="Karşılama/veda ayarları kapatıldı.",
            embed=None,
            view=None
        )
    
    async def display_current_settings(self, interaction):
        """Display current welcome settings"""
        try:
            # Get welcome settings from database
            settings = None
            if self.mongo_db is not None:
                guild_id = interaction.guild.id
                settings = self.mongo_db['welcome'].find_one({"guild_id": guild_id}) or {}
            
            # Create embed
            embed = discord.Embed(
                title="👋 Mevcut Karşılama/Veda Ayarları",
                description="Sunucunuz için yapılandırılmış karşılama ve veda ayarları:",
                color=discord.Color.blue()
            )
            
            # Welcome message
            welcome_msg = settings.get("welcome_message", "Hoş geldin {user}!") if settings else "Hoş geldin {user}!"
            embed.add_field(
                name="👋 Hoş Geldin Mesajı",
                value=f"```{welcome_msg}```",
                inline=False
            )
            
            # Goodbye message
            goodbye_msg = settings.get("goodbye_message", "Güle güle {user}!") if settings else "Güle güle {user}!"
            embed.add_field(
                name="👋 Güle Güle Mesajı",
                value=f"```{goodbye_msg}```",
                inline=False
            )
            
            # Welcome channel
            channel_id = settings.get("channel_id") if settings else None
            channel_text = "Ayarlanmamış"
            if channel_id:
                channel = interaction.guild.get_channel(channel_id)
                if channel:
                    channel_text = channel.mention
                else:
                    channel_text = f"Kanal bulunamadı (ID: {channel_id})"
            
            embed.add_field(
                name="📢 Mesaj Kanalı",
                value=channel_text,
                inline=True
            )
            
            # DM settings
            dm_enabled = settings.get("dm_enabled", False) if settings else False
            dm_status = "Etkin" if dm_enabled else "Devre Dışı"
            
            embed.add_field(
                name="📨 DM Mesajları",
                value=dm_status,
                inline=True
            )
            
            # Card settings
            card_enabled = settings.get("card_enabled", True) if settings else True
            card_status = "Etkin" if card_enabled else "Devre Dışı"
            
            embed.add_field(
                name="🖼️ Özel Kartlar",
                value=card_status,
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error displaying current welcome settings: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Ayarlar görüntülenirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class WelcomeMessageModal(ui.Modal, title="Hoş Geldin Mesajı Ayarları"):
    """Modal for setting welcome message"""
    
    welcome_message = ui.TextInput(
        label="Hoş Geldin Mesajı",
        placeholder="Örnek: Sunucumuza hoş geldin {user}!",
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, bot, guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.mongo_db = get_async_db()
        
        # Load existing welcome message if available
        asyncio.create_task(self.load_existing_message())
    
    async def load_existing_message(self):
        """Load existing welcome message from database"""
        try:
            if self.mongo_db is not None:
                settings = self.mongo_db['welcome'].find_one({"guild_id": self.guild.id}) or {}
                existing_message = settings.get("welcome_message")
                
                if existing_message:
                    self.welcome_message.default = existing_message
        except Exception as e:
            logger.error(f"Error loading existing welcome message: {e}")
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get the welcome message
            message = self.welcome_message.value
            
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['welcome'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"welcome_message": message}},
                    upsert=True
                )
            
            # Show a preview of the message
            preview = message.replace("{user}", interaction.user.mention)
            preview = preview.replace("{server}", self.guild.name)
            preview = preview.replace("{count}", str(self.guild.member_count))
            
            embed = discord.Embed(
                title="👋 Hoş Geldin Mesajı Ayarlandı",
                description="Mesajınız başarıyla kaydedildi.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Önizleme:",
                value=preview,
                inline=False
            )
            
            embed.add_field(
                name="Kullanılabilir Değişkenler:",
                value=(
                    "`{user}` - Kullanıcı etiketi\n"
                    "`{server}` - Sunucu adı\n"
                    "`{count}` - Üye sayısı"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error setting welcome message: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Hoş geldin mesajı ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class GoodbyeMessageModal(ui.Modal, title="Güle Güle Mesajı Ayarları"):
    """Modal for setting goodbye message"""
    
    goodbye_message = ui.TextInput(
        label="Güle Güle Mesajı",
        placeholder="Örnek: Güle güle {user}, seni özleyeceğiz!",
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, bot, guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.mongo_db = get_async_db()
        
        # Load existing goodbye message if available
        asyncio.create_task(self.load_existing_message())
    
    async def load_existing_message(self):
        """Load existing goodbye message from database"""
        try:
            if self.mongo_db is not None:
                settings = self.mongo_db['welcome'].find_one({"guild_id": self.guild.id}) or {}
                existing_message = settings.get("goodbye_message")
                
                if existing_message:
                    self.goodbye_message.default = existing_message
        except Exception as e:
            logger.error(f"Error loading existing goodbye message: {e}")
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get the goodbye message
            message = self.goodbye_message.value
            
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['welcome'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"goodbye_message": message}},
                    upsert=True
                )
            
            # Show a preview of the message
            preview = message.replace("{user}", interaction.user.mention)
            preview = preview.replace("{server}", self.guild.name)
            preview = preview.replace("{count}", str(self.guild.member_count))
            
            embed = discord.Embed(
                title="👋 Güle Güle Mesajı Ayarlandı",
                description="Mesajınız başarıyla kaydedildi.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Önizleme:",
                value=preview,
                inline=False
            )
            
            embed.add_field(
                name="Kullanılabilir Değişkenler:",
                value=(
                    "`{user}` - Kullanıcı adı\n"
                    "`{server}` - Sunucu adı\n"
                    "`{count}` - Üye sayısı"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error setting goodbye message: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Güle güle mesajı ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class WelcomeChannelModal(ui.Modal, title="Karşılama/Veda Kanalı"):
    """Modal for setting welcome/goodbye channel"""
    
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
        self.mongo_db = get_async_db()
    
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
                self.mongo_db['welcome'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"channel_id": channel_id}},
                    upsert=True
                )
            
            await interaction.response.send_message(
                embed=create_embed(f"{channel.mention} kanalı karşılama/veda kanalı olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting welcome channel: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Kanal ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class CardCustomizationView(ui.View):
    """View for customizing welcome/goodbye cards"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = get_async_db()
    
    @ui.button(label="✅ Kartları Etkinleştir", style=discord.ButtonStyle.success, row=0)
    async def enable_cards(self, interaction: discord.Interaction, button: ui.Button):
        await self.toggle_cards(interaction, True)
    
    @ui.button(label="❌ Kartları Devre Dışı Bırak", style=discord.ButtonStyle.danger, row=0)
    async def disable_cards(self, interaction: discord.Interaction, button: ui.Button):
        await self.toggle_cards(interaction, False)
    
    @ui.button(label="🖼️ Arka Plan Seç", style=discord.ButtonStyle.primary, row=1)
    async def select_background(self, interaction: discord.Interaction, button: ui.Button):
        # Create background selector view
        embed = discord.Embed(
            title="🖼️ Arka Plan Seçimi",
            description="Karşılama ve veda kartları için arka plan seçin:",
            color=discord.Color.blue()
        )
        
        # Create background selector view
        view = BackgroundSelectorView(self.bot, self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="🎨 Renk Şeması", style=discord.ButtonStyle.primary, row=1)
    async def color_scheme(self, interaction: discord.Interaction, button: ui.Button):
        # Create color scheme selector view
        embed = discord.Embed(
            title="🎨 Renk Şeması",
            description="Karşılama ve veda kartları için renk şeması seçin:",
            color=discord.Color.blue()
        )
        
        # Create color scheme selector view
        view = ColorSchemeView(self.bot, self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="📄 Yazı Şablonu", style=discord.ButtonStyle.primary, row=1)
    async def text_template(self, interaction: discord.Interaction, button: ui.Button):
        # Open text template modal
        modal = TextTemplateModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="📱 Önizleme", style=discord.ButtonStyle.success, row=2)
    async def preview(self, interaction: discord.Interaction, button: ui.Button):
        # Show card preview
        await self.show_preview(interaction)
    
    async def toggle_cards(self, interaction, enabled):
        """Enable or disable cards"""
        try:
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['welcome'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"card_enabled": enabled}},
                    upsert=True
                )
            
            status = "etkinleştirildi" if enabled else "devre dışı bırakıldı"
            await interaction.response.send_message(
                embed=create_embed(f"Karşılama/veda kartları {status}.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error toggling cards: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Kart ayarları değiştirilirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
    
    async def show_preview(self, interaction):
        """Show card preview"""
        try:
            # Create a simple embed with preview information
            embed = discord.Embed(
                title="📱 Kart Önizlemesi",
                description="Aşağıdaki şekilde bir kart üretilecek (resim temsilidir).",
                color=discord.Color.blue()
            )
            
            # Get settings from database
            settings = None
            if self.mongo_db is not None:
                guild_id = self.guild.id
                settings = self.mongo_db['welcome'].find_one({"guild_id": guild_id}) or {}
            
            # Get background type
            background_type = settings.get("background_type", "default") if settings else "default"
            color_scheme = settings.get("color_scheme", "blue") if settings else "blue"
            
            embed.add_field(
                name="Arka Plan",
                value=f"Tip: {background_type}",
                inline=True
            )
            
            embed.add_field(
                name="Renk Şeması",
                value=color_scheme,
                inline=True
            )
            
            # Sample image URL based on selected settings
            sample_image_url = "https://via.placeholder.com/500x200?text=Welcome+Card+Preview"
            embed.set_image(url=sample_image_url)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing card preview: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Kart önizlemesi gösterilirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class BackgroundSelectorView(ui.View):
    """View for selecting card background"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = get_async_db()
    
    @ui.select(
        placeholder="Arka plan tipini seçin",
        options=[
            discord.SelectOption(label="Varsayılan", description="Standart arka plan", value="default"),
            discord.SelectOption(label="Gradient", description="Geçiş efektli arka plan", value="gradient"),
            discord.SelectOption(label="Blur", description="Bulanık arka plan", value="blur"),
            discord.SelectOption(label="Minimal", description="Sade arka plan", value="minimal"),
            discord.SelectOption(label="Anime", description="Anime tarzı arka planlar", value="anime"),
            discord.SelectOption(label="Game", description="Oyun temalı arka planlar", value="game")
        ]
    )
    async def background_select(self, interaction: discord.Interaction, select: ui.Select):
        background_type = select.values[0]
        await self.set_background(interaction, background_type)
    
    async def set_background(self, interaction, background_type):
        """Set card background type"""
        try:
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['welcome'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"background_type": background_type}},
                    upsert=True
                )
            
            await interaction.response.send_message(
                embed=create_embed(f"Arka plan tipi \"{background_type}\" olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting background type: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Arka plan tipi ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class ColorSchemeView(ui.View):
    """View for selecting color scheme"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = get_async_db()
    
    @ui.button(label="🔵 Mavi", style=discord.ButtonStyle.primary, row=0)
    async def blue_scheme(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color_scheme(interaction, "blue")
    
    @ui.button(label="🔴 Kırmızı", style=discord.ButtonStyle.danger, row=0)
    async def red_scheme(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color_scheme(interaction, "red")
    
    @ui.button(label="🟢 Yeşil", style=discord.ButtonStyle.success, row=0)
    async def green_scheme(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color_scheme(interaction, "green")
    
    @ui.button(label="⚫ Siyah", style=discord.ButtonStyle.secondary, row=1)
    async def black_scheme(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color_scheme(interaction, "black")
    
    @ui.button(label="⚪ Beyaz", style=discord.ButtonStyle.secondary, row=1)
    async def white_scheme(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color_scheme(interaction, "white")
    
    @ui.button(label="🟣 Mor", style=discord.ButtonStyle.secondary, row=1)
    async def purple_scheme(self, interaction: discord.Interaction, button: ui.Button):
        await self.set_color_scheme(interaction, "purple")
    
    async def set_color_scheme(self, interaction, color_scheme):
        """Set color scheme for cards"""
        try:
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['welcome'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"color_scheme": color_scheme}},
                    upsert=True
                )
            
            await interaction.response.send_message(
                embed=create_embed(f"Renk şeması \"{color_scheme}\" olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting color scheme: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Renk şeması ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class TextTemplateModal(ui.Modal, title="Kart Yazı Şablonu"):
    """Modal for setting card text template"""
    
    welcome_template = ui.TextInput(
        label="Hoş Geldin Şablonu",
        placeholder="Örnek: Hoş geldin {user}!",
        required=True,
        style=discord.TextStyle.short
    )
    
    goodbye_template = ui.TextInput(
        label="Güle Güle Şablonu",
        placeholder="Örnek: Güle güle {user}!",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, bot, guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.mongo_db = get_async_db()
        
        # Load existing templates if available
        asyncio.create_task(self.load_existing_templates())
    
    async def load_existing_templates(self):
        """Load existing templates from database"""
        try:
            if self.mongo_db is not None:
                settings = self.mongo_db['welcome'].find_one({"guild_id": self.guild.id}) or {}
                
                welcome_template = settings.get("welcome_template")
                if welcome_template:
                    self.welcome_template.default = welcome_template
                
                goodbye_template = settings.get("goodbye_template")
                if goodbye_template:
                    self.goodbye_template.default = goodbye_template
        except Exception as e:
            logger.error(f"Error loading existing templates: {e}")
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get templates
            welcome_template = self.welcome_template.value
            goodbye_template = self.goodbye_template.value
            
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['welcome'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {
                        "welcome_template": welcome_template,
                        "goodbye_template": goodbye_template
                    }},
                    upsert=True
                )
            
            embed = discord.Embed(
                title="📄 Kart Yazı Şablonları Ayarlandı",
                description="Kart üzerinde görünecek yazılar başarıyla kaydedildi.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Hoş Geldin Şablonu",
                value=welcome_template.replace("{user}", interaction.user.name),
                inline=False
            )
            
            embed.add_field(
                name="Güle Güle Şablonu",
                value=goodbye_template.replace("{user}", interaction.user.name),
                inline=False
            )
            
            embed.add_field(
                name="Kullanılabilir Değişkenler:",
                value=(
                    "`{user}` - Kullanıcı adı\n"
                    "`{server}` - Sunucu adı\n"
                    "`{count}` - Üye sayısı"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error setting text templates: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Yazı şablonları ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class DMSettingsView(ui.View):
    """View for DM message settings"""
    
    def __init__(self, bot, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.guild = guild
        self.mongo_db = get_async_db()
    
    @ui.button(label="✅ DM'leri Etkinleştir", style=discord.ButtonStyle.success, row=0)
    async def enable_dms(self, interaction: discord.Interaction, button: ui.Button):
        await self.toggle_dms(interaction, True)
    
    @ui.button(label="❌ DM'leri Devre Dışı Bırak", style=discord.ButtonStyle.danger, row=0)
    async def disable_dms(self, interaction: discord.Interaction, button: ui.Button):
        await self.toggle_dms(interaction, False)
    
    @ui.button(label="📝 DM Mesajı Düzenle", style=discord.ButtonStyle.primary, row=1)
    async def edit_dm_message(self, interaction: discord.Interaction, button: ui.Button):
        # Open DM message modal
        modal = DMMessageModal(self.bot, self.guild)
        await interaction.response.send_modal(modal)
    
    async def toggle_dms(self, interaction, enabled):
        """Enable or disable DM messages"""
        try:
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['welcome'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"dm_enabled": enabled}},
                    upsert=True
                )
            
            status = "etkinleştirildi" if enabled else "devre dışı bırakıldı"
            await interaction.response.send_message(
                embed=create_embed(f"DM mesajları {status}.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error toggling DM messages: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"DM mesaj ayarları değiştirilirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )


class DMMessageModal(ui.Modal, title="DM Mesajı Ayarları"):
    """Modal for setting DM message"""
    
    dm_message = ui.TextInput(
        label="DM Mesajı",
        placeholder="Örnek: Sunucumuza hoş geldin {user}! Kurallara göz atmayı unutma!",
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, bot, guild):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.mongo_db = get_async_db()
        
        # Load existing DM message if available
        asyncio.create_task(self.load_existing_message())
    
    async def load_existing_message(self):
        """Load existing DM message from database"""
        try:
            if self.mongo_db is not None:
                settings = self.mongo_db['welcome'].find_one({"guild_id": self.guild.id}) or {}
                existing_message = settings.get("dm_message")
                
                if existing_message:
                    self.dm_message.default = existing_message
        except Exception as e:
            logger.error(f"Error loading existing DM message: {e}")
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get the DM message
            message = self.dm_message.value
            
            # Save to database
            if self.mongo_db is not None:
                self.mongo_db['welcome'].update_one(
                    {"guild_id": self.guild.id},
                    {"$set": {"dm_message": message}},
                    upsert=True
                )
            
            # Show a preview of the message
            preview = message.replace("{user}", interaction.user.name)
            preview = preview.replace("{server}", self.guild.name)
            preview = preview.replace("{count}", str(self.guild.member_count))
            
            embed = discord.Embed(
                title="📨 DM Mesajı Ayarlandı",
                description="Mesajınız başarıyla kaydedildi.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Önizleme:",
                value=preview,
                inline=False
            )
            
            embed.add_field(
                name="Kullanılabilir Değişkenler:",
                value=(
                    "`{user}` - Kullanıcı adı\n"
                    "`{server}` - Sunucu adı\n"
                    "`{count}` - Üye sayısı\n"
                    "`{invite}` - Davet linki (mümkünse)"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error setting DM message: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"DM mesajı ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )
