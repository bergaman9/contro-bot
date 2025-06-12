# Settings Views - Clean Version
import discord
import logging
import json
import os
from utils.database.connection import get_async_db
from utils.core.formatting import create_embed

logger = logging.getLogger('settings')

class LanguageSelectView(discord.ui.View):
    """Language selection view for settings"""
    
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
                "🎮 **Temp Channels** - Temporary voice channels system\n"
                "🤖 **AI Settings** - Configure AI chat system\n"
                "🎂 **Birthday System** - Configure birthday celebrations\n"
                "👑 **Admin Tools** - Send embeds and admin utilities"
            ),
            inline=False
        )
        
        view = MainSettingsView(self.bot, language)
        await interaction.response.edit_message(embed=embed, view=view)


class MainSettingsView(discord.ui.View):
    """Main settings view with all categories"""
    
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🏠 Server Settings", style=discord.ButtonStyle.primary, row=0)
    async def server_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🏠 Server Settings" if self.language == "en" else "🏠 Sunucu Ayarları",
            description="Configure basic server settings." if self.language == "en" else "Temel sunucu ayarlarını yapılandırın.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="⚙️ Available Settings" if self.language == "en" else "⚙️ Mevcut Ayarlar",
            value=(
                "• Server prefix configuration\n"
                "• Default language settings\n"
                "• Bot permissions\n"
                "• Channel configurations"
            ) if self.language == "en" else (
                "• Sunucu prefix yapılandırması\n"
                "• Varsayılan dil ayarları\n"
                "• Bot izinleri\n"
                "• Kanal yapılandırmaları"
            ),
            inline=False
        )
        
        view = ServerSettingsView(self.bot, self.language)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🔧 Feature Management", style=discord.ButtonStyle.primary, row=0)
    async def feature_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔧 Feature Management" if self.language == "en" else "🔧 Özellik Yönetimi",
            description="Enable or disable bot features for your server." if self.language == "en" else "Sunucunuz için bot özelliklerini etkinleştirin veya devre dışı bırakın.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="🎯 Features" if self.language == "en" else "🎯 Özellikler",
            value=(
                "• Welcome/Goodbye system\n"
                "• Leveling system\n"
                "• Starboard\n"
                "• Auto moderation\n"
                "• Ticket system\n"
                "• Temporary channels"
            ) if self.language == "en" else (
                "• Hoşgeldin/Güle güle sistemi\n"
                "• Seviye sistemi\n"
                "• Starboard\n"
                "• Otomatik moderasyon\n"
                "• Ticket sistemi\n"
                "• Geçici kanallar"
            ),
            inline=False
        )
        
        view = FeatureManagementView(self.bot, self.language)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="👋 Welcome/Goodbye", style=discord.ButtonStyle.success, row=0)
    async def welcome_goodbye(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👋 Welcome/Goodbye System" if self.language == "en" else "👋 Hoşgeldin/Güle Güle Sistemi",
            description="Configure welcome and goodbye messages for your server." if self.language == "en" else "Sunucunuz için hoşgeldin ve güle güle mesajlarını yapılandırın.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="🎨 Features" if self.language == "en" else "🎨 Özellikler",
            value=(
                "• Custom welcome messages\n"
                "• Beautiful welcome cards\n"
                "• Goodbye messages\n"
                "• Role assignment on join\n"
                "• Multiple language support\n"
                "• Custom backgrounds"
            ) if self.language == "en" else (
                "• Özel hoşgeldin mesajları\n"
                "• Güzel hoşgeldin kartları\n"
                "• Güle güle mesajları\n"
                "• Katılımda rol ataması\n"
                "• Çoklu dil desteği\n"
                "• Özel arka planlar"
            ),
            inline=False
        )
        
        view = WelcomeGoodbyeView(self.bot, self.language)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🎫 Ticket System", style=discord.ButtonStyle.danger, row=1)
    async def ticket_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.settings.ticket_views import TicketSettingsView
        
        embed = discord.Embed(
            title="🎫 Ticket System" if self.language == "en" else "🎫 Ticket Sistemi",
            description="Configure support ticket system for your server." if self.language == "en" else "Sunucunuz için destek ticket sistemini yapılandırın.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="🎯 Features" if self.language == "en" else "🎯 Özellikler",
            value=(
                "• Support ticket creation\n"
                "• Staff role management\n"
                "• Ticket categories\n"
                "• Automatic ticket logging\n"
                "• Custom ticket panels\n"
                "• Multi-language support"
            ) if self.language == "en" else (
                "• Destek ticket oluşturma\n"
                "• Personel rol yönetimi\n"
                "• Ticket kategorileri\n"
                "• Otomatik ticket kayıtları\n"
                "• Özel ticket panelleri\n"
                "• Çok dil desteği"
            ),
            inline=False
        )
        
        view = TicketSettingsView(self.bot, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="📝 Registration System", style=discord.ButtonStyle.secondary, row=2)
    async def registration_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.settings.register_views import RegisterSettingsView
        
        embed = discord.Embed(
            title="📝 Registration System" if self.language == "en" else "📝 Kayıt Sistemi",
            description="Configure user registration system for your server." if self.language == "en" else "Sunucunuz için kullanıcı kayıt sistemini yapılandırın.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🎯 Features" if self.language == "en" else "🎯 Özellikler",
            value=(
                "• User registration with button\n"
                "• Automatic role assignment\n"
                "• Age-based roles\n"
                "• Custom welcome messages\n"
                "• Registration statistics\n"
                "• Multi-language support"
            ) if self.language == "en" else (
                "• Buton ile kullanıcı kaydı\n"
                "• Otomatik rol ataması\n"
                "• Yaş bazlı roller\n"
                "• Özel karşılama mesajları\n"
                "• Kayıt istatistikleri\n"
                "• Çok dil desteği"
            ),
            inline=False
        )
        
        view = RegisterSettingsView(self.bot, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="👑 Admin Tools", style=discord.ButtonStyle.danger, row=1)
    async def admin_tools(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👑 Admin Tools" if self.language == "en" else "👑 Admin Araçları",
            description="Administrative tools and utilities." if self.language == "en" else "Yönetim araçları ve yardımcı programlar.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="🛠️ Available Tools" if self.language == "en" else "🛠️ Mevcut Araçlar",
            value=(
                "• Send custom embeds\n"
                "• Send registration panels\n"
                "• Send ticket panels\n"
                "• Send welcome messages\n"
                "• Server management tools"
            ) if self.language == "en" else (
                "• Özel embed gönderme\n"
                "• Kayıt paneli gönderme\n"
                "• Ticket paneli gönderme\n"
                "• Hoşgeldin mesajı gönderme\n"
                "• Sunucu yönetim araçları"
            ),
            inline=False
        )
        
        view = AdminToolsView(self.bot, self.language)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AdminToolsView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="📝 Send Registration Embed", style=discord.ButtonStyle.primary, row=0)
    async def send_registration_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📝 Send Registration Embed" if self.language == "en" else "📝 Kayıt Embed'i Gönder",
            description="Select a channel to send the registration embed to." if self.language == "en" else "Kayıt embed'ini göndermek için bir kanal seçin.",
            color=discord.Color.blue()
        )
        
        view = ChannelSelectView(self.bot, self.language, "registration")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🎫 Send Ticket Embed", style=discord.ButtonStyle.secondary, row=0)
    async def send_ticket_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎫 Send Ticket Embed" if self.language == "en" else "🎫 Ticket Embed'i Gönder",
            description="Select a channel to send the ticket embed to." if self.language == "en" else "Ticket embed'ini göndermek için bir kanal seçin.",
            color=discord.Color.orange()
        )
        
        view = ChannelSelectView(self.bot, self.language, "ticket")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ChannelSelectView(discord.ui.View):
    def __init__(self, bot, language="en", embed_type="registration"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        self.embed_type = embed_type

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        placeholder="Select a channel...",
        min_values=1,
        max_values=1
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        
        if self.embed_type == "registration":
            await self.send_registration_embed_to_channel(interaction, channel)
        elif self.embed_type == "ticket":
            await self.send_ticket_embed_to_channel(interaction, channel)

    async def send_registration_embed_to_channel(self, interaction, channel):
        from utils.settings.register_views import RegistrationButtonView
        
        embed = discord.Embed(
            title="📝 Sunucuya Kayıt Ol",
            description="Sunucumuzun tüm özelliklerinden faydalanmak için kayıt olun!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🎯 Kayıt Olduktan Sonra",
            value=(
                "• Tüm kanallara erişim\n"
                "• Özel roller ve yetkiler\n"
                "• Etkinliklere katılım\n"
                "• Topluluk özelliklerinden faydalanma"
            ),
            inline=False
        )
        embed.set_footer(text="Kayıt olmak için aşağıdaki butona tıklayın!")
        
        view = RegistrationButtonView()
        await channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            f"✅ Registration embed sent to {channel.mention}",
            ephemeral=True
        )

    async def send_ticket_embed_to_channel(self, interaction, channel):
        from utils.settings.ticket_views import TicketCreateView
        
        embed = discord.Embed(
            title="🎫 Destek Sistemi",
            description="Yardıma mı ihtiyacınız var? Bir destek talebi oluşturun!",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="📋 Destek Türleri",
            value=(
                "🔧 **Teknik Sorunlar** - Bot veya sunucu ile ilgili\n"
                "❓ **Genel Sorular** - Sunucu kuralları ve bilgiler\n"
                "🛡️ **Moderasyon** - Şikayet ve raporlar\n"
                "💡 **Öneriler** - Sunucu geliştirme fikirleri"
            ),
            inline=False
        )
        
        try:
            from utils.community.turkoyto.card_renderer import create_support_system_card
            card_path = await create_support_system_card(interaction.guild, self.bot)
            
            if card_path and os.path.exists(card_path):
                embed.set_image(url="attachment://support_card.png")
                file = discord.File(card_path, filename="support_card.png")
                
                view = TicketCreateView()
                await channel.send(embed=embed, view=view, file=file)
                
                try:
                    os.remove(card_path)
                except:
                    pass
            else:
                view = TicketCreateView()
                await channel.send(embed=embed, view=view)
        except Exception as e:
            logger.error(f"Error creating support card: {e}")
            view = TicketCreateView()
            await channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            f"✅ Ticket embed sent to {channel.mention}",
            ephemeral=True
        )


# Placeholder classes for compatibility
class AISettingsView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🤖 Configure AI", style=discord.ButtonStyle.primary)
    async def configure_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("AI settings configuration coming soon!", ephemeral=True)


class BirthdaySettingsView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🎂 Configure Birthday", style=discord.ButtonStyle.primary)
    async def configure_birthday(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Birthday settings configuration coming soon!", ephemeral=True)


# Placeholder classes for other views
class ServerSettingsView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🔧 Configure", style=discord.ButtonStyle.primary)
    async def configure(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Server settings configuration coming soon!", ephemeral=True)


class FeatureManagementView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🔧 Manage Features", style=discord.ButtonStyle.primary)
    async def manage_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Feature management coming soon!", ephemeral=True)


class WelcomeGoodbyeView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🎨 Configure Welcome", style=discord.ButtonStyle.primary)
    async def configure_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Welcome system configuration coming soon!", ephemeral=True) 