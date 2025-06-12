import discord
import discord
from discord import ui
import asyncio
import json
import logging
from utils.core.formatting import create_embed
from utils.database.connection import get_async_db, ensure_async_db
from utils.core.formatting import format_timestamp, format_number
import os

# Import existing modal classes from their respective modules
from utils.settings.server_views import ReportChannelModal, CustomColorModal
from utils.settings.welcome_views import WelcomeMessageModal, GoodbyeMessageModal
# MainLogChannelModal imported dynamically to avoid circular imports
# Ticket views imported dynamically due to potential import issues
from utils.settings.ai_birthday_views import AISettingsView, BirthdaySettingsView
from utils.settings.starboard_views import StarboardView

# Setup logger
logger = logging.getLogger(__name__)

class LanguageSelectView(discord.ui.View):
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
        # Always use English for settings
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
        
        # Keep the old Turkish version for reference but commented out
        if False:  # language == "tr":
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
                    "⭐ **Starboard** - Starboard system\n"                    "🎮 **Temp Channels** - Temporary voice channels system\n"
                    "🤖 **AI Settings** - Configure AI chat system\n"
                    "🎂 **Birthday System** - Configure birthday celebrations\n"
                    "👑 **Admin Tools** - Send embeds and admin utilities"
                ),
                inline=False
            )
        
        view = MainSettingsView(self.bot, language)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class MainSettingsView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        
    # Row 0: Core Server Settings (Primary - Blue)
    @discord.ui.button(label="🏠 Server Settings", style=discord.ButtonStyle.primary, row=0)
    async def server_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🏠 Server Settings" if self.language == "en" else "🏠 Sunucu Ayarları",
            description="Configure basic server settings and bot behavior." if self.language == "en" else "Temel sunucu ayarlarını ve bot davranışını yapılandırın.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="⚙️ Available Options" if self.language == "en" else "⚙️ Mevcut Seçenekler",
            value=(
                "• Bot prefix settings\n"
                "• Server-specific configurations\n"
                "• Role management\n"
                "• Channel permissions"
            ) if self.language == "en" else (
                "• Bot prefix ayarları\n"
                "• Sunucuya özel yapılandırmalar\n"
                "• Rol yönetimi\n"
                "• Kanal izinleri"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, view=ServerSettingsView(self.bot, self.language), ephemeral=True)
    
    @discord.ui.button(label="🔧 Feature Management", style=discord.ButtonStyle.primary, row=0)
    async def feature_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔧 Feature Management" if self.language == "en" else "🔧 Özellik Yönetimi",
            description="Enable or disable bot features for your server." if self.language == "en" else "Sunucunuz için bot özelliklerini etkinleştirin veya devre dışı bırakın.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="🎛️ Available Features" if self.language == "en" else "🎛️ Mevcut Özellikler",
            value=(
                "• Welcome/Goodbye System\n"
                "• Levelling System\n"
                "• Ticket System\n"
                "• Moderation Tools\n"
                "• Starboard\n"
                "• Temp Channels"
            ) if self.language == "en" else (
                "• Karşılama/Veda Sistemi\n"
                "• Seviye Sistemi\n"
                "• Bilet Sistemi\n"
                "• Moderasyon Araçları\n"
                "• Yıldız Panosu\n"
                "• Geçici Kanallar"
            ),
            inline=False
        )
        view = FeatureManagementView(self.bot, self.language)
        await view.initialize()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="👋 Welcome/Goodbye", style=discord.ButtonStyle.success, row=0)
    async def welcome_goodbye(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👋 Welcome/Goodbye Settings" if self.language == "en" else "👋 Karşılama/Veda Ayarları",
            description="Configure welcome and goodbye messages for your server." if self.language == "en" else "Sunucunuz için karşılama ve veda mesajlarını yapılandırın.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="🎉 Welcome System" if self.language == "en" else "🎉 Karşılama Sistemi",
            value=(
                "• Custom welcome messages\n"
                "• Image generation with themes\n"
                "• Member count tracking\n"
                "• Multiple language support"
            ) if self.language == "en" else (
                "• Özel karşılama mesajları\n"
                "• Temalarla görsel oluşturma\n"
                "• Üye sayısı takibi\n"
                "• Çoklu dil desteği"
            ),
            inline=True
        )
        embed.add_field(
            name="👋 Goodbye System" if self.language == "en" else "👋 Veda Sistemi",
            value=(
                "• Custom goodbye messages\n"
                "• Beautiful farewell cards\n"
                "• Member statistics\n"
                "• Customizable themes"
            ) if self.language == "en" else (
                "• Özel veda mesajları\n"
                "• Güzel veda kartları\n"
                "• Üye istatistikleri\n"
                "• Özelleştirilebilir temalar"
            ),
            inline=True
        )
        view = WelcomeGoodbyeView(self.bot, self.language)
        await view.initialize()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="💫 Levelling System", style=discord.ButtonStyle.success, row=0)
    async def levelling_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💫 Levelling System" if self.language == "en" else "💫 Seviye Sistemi",
            description="Configure XP and levelling system for your server." if self.language == "en" else "Sunucunuz için XP ve seviye sistemini yapılandırın.",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="⚙️ System Features" if self.language == "en" else "⚙️ Sistem Özellikleri",
            value=(
                "• Message XP rewards\n"
                "• Voice channel XP\n"
                "• Level up notifications\n"
                "• Custom level roles\n"
                "• Beautiful level cards\n"
                "• Leaderboard system"
            ) if self.language == "en" else (
                "• Mesaj XP ödülleri\n"
                "• Sesli kanal XP'si\n"
                "• Seviye atlama bildirimleri\n"
                "• Özel seviye rolleri\n"
                "• Güzel seviye kartları\n"
                "• Liderlik tablosu sistemi"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, view=LevellingSettingsView(self.bot, interaction), ephemeral=True)

    # Row 1: Moderation & Management (Important - Red/Secondary)
    @discord.ui.button(label="🛡️ Moderation", style=discord.ButtonStyle.danger, row=1)
    async def moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛡️ Moderation Settings" if self.language == "en" else "🛡️ Moderasyon Ayarları",
            description="Configure moderation tools and auto-moderation features." if self.language == "en" else "Moderasyon araçlarını ve otomatik moderasyon özelliklerini yapılandırın.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="🔧 Available Tools" if self.language == "en" else "🔧 Mevcut Araçlar",
            value=(
                "• Auto role assignment\n"
                "• Word filter system\n"
                "• Spam protection\n"
                "• Warning system\n"
                "• Timeout management\n"
                "• Ban/kick commands"
            ) if self.language == "en" else (
                "• Otomatik rol atama\n"
                "• Kelime filtreleme sistemi\n"
                "• Spam koruması\n"
                "• Uyarı sistemi\n"
                "• Timeout yönetimi\n"
                "• Ban/kick komutları"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, view=ModerationView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="🎫 Ticket System", style=discord.ButtonStyle.danger, row=1)
    async def ticket_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎫 Ticket System" if self.language == "en" else "🎫 Bilet Sistemi",
            description="Configure support ticket system for your server." if self.language == "en" else "Sunucunuz için destek bilet sistemini yapılandırın.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="🎯 System Features" if self.language == "en" else "🎯 Sistem Özellikleri",
            value=(
                "• Private support channels\n"
                "• Custom ticket categories\n"
                "• Support role management\n"
                "• Ticket transcripts\n"
                "• Auto-close system\n"
                "• Multi-language support"
            ) if self.language == "en" else (
                "• Özel destek kanalları\n"
                "• Özel bilet kategorileri\n"
                "• Destek rol yönetimi\n"
                "• Bilet kayıtları\n"
                "• Otomatik kapanma sistemi\n"
                "• Çoklu dil desteği"
            ),
            inline=False
        )
        view = TicketSystemView(self.bot, self.language)
        await view.initialize()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="📊 Logging", style=discord.ButtonStyle.secondary, row=1)
    async def logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📊 Logging System" if self.language == "en" else "📊 Kayıt Sistemi",
            description="Configure server logging and audit features." if self.language == "en" else "Sunucu kayıt tutma ve denetim özelliklerini yapılandırın.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📝 Log Types" if self.language == "en" else "📝 Kayıt Türleri",
            value=(
                "• Member join/leave events\n"
                "• Message edit/delete logs\n"
                "• Voice channel activity\n"
                "• Role changes\n"
                "• Server modifications\n"
                "• Moderation actions"
            ) if self.language == "en" else (
                "• Üye giriş/çıkış olayları\n"
                "• Mesaj düzenleme/silme kayıtları\n"
                "• Sesli kanal aktivitesi\n"
                "• Rol değişiklikleri\n"
                "• Sunucu değişiklikleri\n"
                "• Moderasyon eylemleri"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, view=LoggingView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="👑 Admin Tools", style=discord.ButtonStyle.danger, row=1)
    async def admin_tools(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👑 Admin Tools" if self.language == "en" else "👑 Yönetici Araçları",
            description="Advanced administrative tools and utilities." if self.language == "en" else "Gelişmiş yönetici araçları ve yardımcı programlar.",
            color=discord.Color.dark_red()
        )
        embed.add_field(
            name="🛠️ Available Tools" if self.language == "en" else "🛠️ Mevcut Araçlar",
            value=(
                "• Send registration embeds\n"
                "• Send ticket embeds\n"
                "• Send welcome embeds\n"
                "• Send starboard embeds\n"
                "• Create custom embeds\n"
                "• Server management utilities"
            ) if self.language == "en" else (
                "• Kayıt embed'leri gönder\n"
                "• Bilet embed'leri gönder\n"
                "• Karşılama embed'leri gönder\n"
                "• Yıldız panosu embed'leri gönder\n"
                "• Özel embed'ler oluştur\n"
                "• Sunucu yönetim araçları"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, view=AdminToolsView(self.bot, self.language), ephemeral=True)

    # Row 2: Additional Features (Optional - Secondary/Gray)
    @discord.ui.button(label="⭐ Starboard", style=discord.ButtonStyle.secondary, row=2)
    async def starboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⭐ Starboard System" if self.language == "en" else "⭐ Yıldız Panosu Sistemi",
            description="Highlight the best messages in your server." if self.language == "en" else "Sunucunuzdaki en iyi mesajları öne çıkarın.",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="✨ Features" if self.language == "en" else "✨ Özellikler",
            value=(
                "• Star reaction tracking\n"
                "• Customizable star threshold\n"
                "• Beautiful starboard embeds\n"
                "• Message statistics\n"
                "• Auto-moderation integration\n"
                "• Multiple starboard channels"
            ) if self.language == "en" else (
                "• Yıldız tepki takibi\n"
                "• Özelleştirilebilir yıldız eşiği\n"
                "• Güzel yıldız panosu embed'leri\n"
                "• Mesaj istatistikleri\n"
                "• Otomatik moderasyon entegrasyonu\n"
                "• Çoklu yıldız panosu kanalları"
            ),
            inline=False
        )
        embed.add_field(
            name="⚙️ Configuration" if self.language == "en" else "⚙️ Yapılandırma",
            value="Use the starboard cog commands to configure this system." if self.language == "en" else "Bu sistemi yapılandırmak için starboard cog komutlarını kullanın.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🤖 AI Settings", style=discord.ButtonStyle.secondary, row=2)
    async def ai_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
            title="🤖 AI Settings" if self.language == "en" else "🤖 AI Ayarları",
            description="Configure AI features and chatbot settings." if self.language == "en" else "AI özelliklerini ve chatbot ayarlarını yapılandırın.",
            color=discord.Color.blurple()
            )
            embed.add_field(
            name="🧠 AI Features" if self.language == "en" else "🧠 AI Özellikleri",
            value=(
                "• Intelligent chat responses\n"
                "• Context-aware conversations\n"
                "• Custom AI personality\n"
                "• Multi-language support\n"
                "• Smart moderation assistance\n"
                "• Learning capabilities"
            ) if self.language == "en" else (
                "• Akıllı sohbet yanıtları\n"
                "• Bağlam farkında konuşmalar\n"
                "• Özel AI kişiliği\n"
                "• Çoklu dil desteği\n"
                "• Akıllı moderasyon yardımı\n"
                "• Öğrenme yetenekleri"
            ),
                inline=False
            )
        await interaction.response.send_message(embed=embed, view=AISettingsView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="🎂 Birthday System", style=discord.ButtonStyle.secondary, row=2)
    async def birthday_system(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
            title="🎂 Birthday System" if self.language == "en" else "🎂 Doğum Günü Sistemi",
            description="Celebrate member birthdays with automated messages." if self.language == "en" else "Otomatik mesajlarla üye doğum günlerini kutlayın.",
            color=discord.Color.magenta()
            )
            embed.add_field(
            name="🎉 Features" if self.language == "en" else "🎉 Özellikler",
            value=(
                "• Automatic birthday reminders\n"
                "• Custom birthday messages\n"
                "• Birthday role assignments\n"
                "• Birthday calendar\n"
                "• Special birthday channels\n"
                "• Celebration animations"
            ) if self.language == "en" else (
                "• Otomatik doğum günü hatırlatıcıları\n"
                "• Özel doğum günü mesajları\n"
                "• Doğum günü rol atamaları\n"
                "• Doğum günü takvimi\n"
                "• Özel doğum günü kanalları\n"
                "• Kutlama animasyonları"
            ),
                inline=False
            )
        await interaction.response.send_message(embed=embed, view=BirthdaySettingsView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="🎮 Temp Channels", style=discord.ButtonStyle.secondary, row=2)
    async def temp_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎮 Temporary Channels" if self.language == "en" else "🎮 Geçici Kanallar",
            description="Create temporary voice channels for your members." if self.language == "en" else "Üyeleriniz için geçici sesli kanallar oluşturun.",
            color=discord.Color.teal()
        )
        embed.add_field(
            name="🔧 Features" if self.language == "en" else "🔧 Özellikler",
            value=(
                "• Auto-created voice channels\n"
                "• Custom channel names\n"
                "• User limit controls\n"
                "• Auto-delete when empty\n"
                "• Permission management\n"
                "• Game-based naming"
            ) if self.language == "en" else (
                "• Otomatik oluşturulan sesli kanallar\n"
                "• Özel kanal isimleri\n"
                "• Kullanıcı limit kontrolleri\n"
                "• Boş olduğunda otomatik silme\n"
                "• İzin yönetimi\n"
                "• Oyun tabanlı isimlendirme"
            ),
            inline=False
        )
        embed.add_field(
            name="⚙️ Configuration" if self.language == "en" else "⚙️ Yapılandırma",
            value="Use the temp channels cog commands to configure this system." if self.language == "en" else "Bu sistemi yapılandırmak için temp channels cog komutlarını kullanın.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📝 Registration System", style=discord.ButtonStyle.secondary, row=2)
    async def registration_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Import the full registration settings view
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
        embed.add_field(
            name="⚙️ Setup" if self.language == "en" else "⚙️ Kurulum",
            value=(
                "Use the buttons below to configure all aspects of the registration system."
            ) if self.language == "en" else (
                "Kayıt sisteminin tüm yönlerini yapılandırmak için aşağıdaki butonları kullanın."
            ),
            inline=False
        )
        
        # Show the full registration settings view
        view = RegisterSettingsView(self.bot, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RegistrationSystemView(discord.ui.View):
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
        embed.add_field(
            name="📋 What this does" if self.language == "en" else "📋 Bu ne yapar",
            value="Creates a registration button that members can use to register to the server." if self.language == "en" else "Üyelerin sunucuya kayıt olmak için kullanabileceği bir kayıt butonu oluşturur.",
            inline=False
        )
        
        view = ChannelSelectView(self.bot, self.language, "registration")
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
        embed.add_field(
            name="📋 What this does" if self.language == "en" else "📋 Bu ne yapar",
            value="Creates a registration button that members can use to register to the server." if self.language == "en" else "Üyelerin sunucuya kayıt olmak için kullanabileceği bir kayıt butonu oluşturur.",
            inline=False
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
        embed.add_field(
            name="📋 What this does" if self.language == "en" else "📋 Bu ne yapar",
            value="Creates a support ticket button that members can use to get help from staff." if self.language == "en" else "Üyelerin ekipten yardım almak için kullanabileceği bir destek bileti butonu oluşturur.",
            inline=False
        )
        
        view = ChannelSelectView(self.bot, self.language, "ticket")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="👋 Send Welcome Embed", style=discord.ButtonStyle.success, row=0)
    async def send_welcome_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👋 Send Welcome Embed" if self.language == "en" else "👋 Hoşgeldin Embed'i Gönder",
            description="Select a channel to send the welcome embed to." if self.language == "en" else "Hoşgeldin embed'ini göndermek için bir kanal seçin.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📋 What this does" if self.language == "en" else "📋 Bu ne yapar",
            value="Creates a welcome message that shows server information and rules." if self.language == "en" else "Sunucu bilgilerini ve kurallarını gösteren bir hoşgeldin mesajı oluşturur.",
            inline=False
        )
        
        view = ChannelSelectView(self.bot, self.language, "welcome")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="⭐ Send Starboard Embed", style=discord.ButtonStyle.secondary, row=1)
    async def send_starboard_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⭐ Send Starboard Embed" if self.language == "en" else "⭐ Starboard Embed'i Gönder",
            description="Select a channel to send the starboard embed to." if self.language == "en" else "Starboard embed'ini göndermek için bir kanal seçin.",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📋 What this does" if self.language == "en" else "📋 Bu ne yapar",
            value="Creates an informational message about how the starboard system works." if self.language == "en" else "Starboard sisteminin nasıl çalıştığı hakkında bilgilendirici bir mesaj oluşturur.",
            inline=False
        )
        
        view = ChannelSelectView(self.bot, self.language, "starboard")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="✨ Create Custom Embed", style=discord.ButtonStyle.primary, row=1)
    async def create_custom_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomEmbedModal(self.language)
        await interaction.response.send_modal(modal)

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
        
        # Send the appropriate embed based on type
        if self.embed_type == "registration":
            await self.send_registration_embed_to_channel(interaction, channel)
        elif self.embed_type == "ticket":
            await self.send_ticket_embed_to_channel(interaction, channel)
        elif self.embed_type == "welcome":
            await self.send_welcome_embed_to_channel(interaction, channel)
        elif self.embed_type == "starboard":
            await self.send_starboard_embed_to_channel(interaction, channel)

    async def send_registration_embed_to_channel(self, interaction, channel):
        # Import registration embed functionality
        try:
            # Get the actual channel object if it's an AppCommandChannel
            if hasattr(channel, 'id'):
                actual_channel = interaction.guild.get_channel(channel.id)
                if not actual_channel:
                    await interaction.response.send_message(
                        "❌ Channel not found!" if self.language == "en" else "❌ Kanal bulunamadı!",
                        ephemeral=True
                    )
                    return
                channel = actual_channel
            
            # Create registration embed directly
            embed = discord.Embed(
                title="📝 Server Registration" if self.language == "en" else "📝 Sunucu Kaydı",
                description=(
                    f"Welcome to **{interaction.guild.name}**!\n\n"
                    "To access all channels and features, please register by clicking the button below.\n\n"
                    "**Registration includes:**\n"
                    "• Access to all server channels\n"
                    "• Ability to participate in events\n"
                    "• Custom profile setup\n"
                    "• And much more!"
                ) if self.language == "en" else (
                    f"**{interaction.guild.name}** sunucusuna hoş geldin!\n\n"
                    "Tüm kanallara ve özelliklere erişmek için lütfen aşağıdaki butona tıklayarak kayıt ol.\n\n"
                    "**Kayıt avantajları:**\n"
                    "• Tüm sunucu kanallarına erişim\n"
                    "• Etkinliklere katılım hakkı\n"
                    "• Özel profil kurulumu\n"
                    "• Ve daha fazlası!"
                ),
                color=discord.Color.blue()
            )
            # Import the RegisterButton from the register cog
            from cogs.register import RegisterButton
            
            # Create the registration button view with proper language support
            view = RegisterButton(language=self.language)
            
            await channel.send(embed=embed, view=view)
            
            success_msg = f"✅ Registration embed sent to {channel.mention}!"
            if self.language == "tr":
                success_msg = f"✅ Kayıt embed'i {channel.mention} kanalına gönderildi!"
                
            await interaction.response.send_message(success_msg, ephemeral=True)
            
        except Exception as e:
            error_msg = f"❌ Error sending registration embed: {str(e)}"
            if self.language == "tr":
                error_msg = f"❌ Kayıt embed'i gönderilirken hata: {str(e)}"
            await interaction.response.send_message(error_msg, ephemeral=True)

    async def send_ticket_embed_to_channel(self, interaction, channel):
        try:
            # Get the actual channel object if it's an AppCommandChannel
            if hasattr(channel, 'id'):
                actual_channel = interaction.guild.get_channel(channel.id)
                if not actual_channel:
                    await interaction.response.send_message(
                        "❌ Channel not found!" if self.language == "en" else "❌ Kanal bulunamadı!",
                        ephemeral=True
                    )
                    return
                channel = actual_channel
            
            # Create ticket embed
            embed = discord.Embed(
                title="🎫 Support Tickets" if self.language == "en" else "🎫 Destek Biletleri",
                description=(
                    "Need help or support? Click the button below to create a support ticket!\n\n"
                    "**What are tickets?**\n"
                    "• Private channels between you and staff\n"
                    "• Get personalized help\n"
                    "• Report issues or ask questions"
                ) if self.language == "en" else (
                    "Yardıma mı ihtiyacın var? Destek bileti oluşturmak için aşağıdaki butona tıkla!\n\n"
                    "**Bilet nedir?**\n"
                    "• Sen ve ekip arasında özel kanallar\n"
                    "• Kişiselleştirilmiş yardım al\n"
                    "• Sorun bildir veya soru sor"
                ),
                color=discord.Color.blue()
            )
            
            view = discord.ui.View()
            ticket_button = discord.ui.Button(
                label="🎫 Create Ticket" if self.language == "en" else "🎫 Bilet Oluştur",
                style=discord.ButtonStyle.primary,
                custom_id="create_ticket"
            )
            view.add_item(ticket_button)
            
            await channel.send(embed=embed, view=view)
            
            success_msg = f"✅ Ticket embed sent to {channel.mention}!"
            if self.language == "tr":
                success_msg = f"✅ Ticket embed'i {channel.mention} kanalına gönderildi!"
                
            await interaction.response.send_message(success_msg, ephemeral=True)
            
        except Exception as e:
            error_msg = f"❌ Error sending ticket embed: {str(e)}"
            if self.language == "tr":
                error_msg = f"❌ Ticket embed'i gönderilirken hata: {str(e)}"
            await interaction.response.send_message(error_msg, ephemeral=True)

    async def send_welcome_embed_to_channel(self, interaction, channel):
        try:
            # Get the actual channel object if it's an AppCommandChannel
            if hasattr(channel, 'id'):
                actual_channel = interaction.guild.get_channel(channel.id)
                if not actual_channel:
                    await interaction.response.send_message(
                        "❌ Channel not found!" if self.language == "en" else "❌ Kanal bulunamadı!",
                        ephemeral=True
                    )
                    return
                channel = actual_channel
            
            embed = discord.Embed(
                title="🎉 Welcome to the Server!" if self.language == "en" else "🎉 Sunucuya Hoş Geldin!",
                description=(
                    f"Welcome to **{interaction.guild.name}**!\n\n"
                    "📋 Make sure to read the rules\n"
                    "💬 Introduce yourself\n"
                    "🎮 Have fun and enjoy your stay!"
                ) if self.language == "en" else (
                    f"**{interaction.guild.name}** sunucusuna hoş geldin!\n\n"
                    "📋 Kuralları okumayı unutma\n"
                    "💬 Kendini tanıt\n"
                    "🎮 Eğlen ve keyfini çıkar!"
                ),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            await channel.send(embed=embed)
            
            success_msg = f"✅ Welcome embed sent to {channel.mention}!"
            if self.language == "tr":
                success_msg = f"✅ Hoşgeldin embed'i {channel.mention} kanalına gönderildi!"
                
            await interaction.response.send_message(success_msg, ephemeral=True)
            
        except Exception as e:
            error_msg = f"❌ Error sending welcome embed: {str(e)}"
            if self.language == "tr":
                error_msg = f"❌ Hoşgeldin embed'i gönderilirken hata: {str(e)}"
            await interaction.response.send_message(error_msg, ephemeral=True)

    async def send_starboard_embed_to_channel(self, interaction, channel):
        try:
            # Get the actual channel object if it's an AppCommandChannel
            if hasattr(channel, 'id'):
                actual_channel = interaction.guild.get_channel(channel.id)
                if not actual_channel:
                    await interaction.response.send_message(
                        "❌ Channel not found!" if self.language == "en" else "❌ Kanal bulunamadı!",
                        ephemeral=True
                    )
                    return
                channel = actual_channel
            
            embed = discord.Embed(
                title="⭐ Starboard" if self.language == "en" else "⭐ Yıldız Panosu",
                description=(
                    "React with ⭐ to messages you find interesting!\n\n"
                    "**How it works:**\n"
                    "• React with ⭐ to any message\n"
                    "• Popular messages appear here\n"
                    "• Highlight the best content in the server"
                ) if self.language == "en" else (
                    "İlginç bulduğun mesajlara ⭐ ile tepki ver!\n\n"
                    "**Nasıl çalışır:**\n"
                    "• Herhangi bir mesaja ⭐ ile tepki ver\n"
                    "• Popüler mesajlar burada görünür\n"
                    "• Sunucudaki en iyi içerikleri öne çıkar"
                ),
                color=discord.Color.gold()
            )
            
            await channel.send(embed=embed)
            
            success_msg = f"✅ Starboard embed sent to {channel.mention}!"
            if self.language == "tr":
                success_msg = f"✅ Starboard embed'i {channel.mention} kanalına gönderildi!"
                
            await interaction.response.send_message(success_msg, ephemeral=True)
            
        except Exception as e:
            error_msg = f"❌ Error sending starboard embed: {str(e)}"
            if self.language == "tr":
                error_msg = f"❌ Starboard embed'i gönderilirken hata: {str(e)}"
            await interaction.response.send_message(error_msg, ephemeral=True)

class CustomEmbedModal(discord.ui.Modal):
    def __init__(self, language="en"):
        super().__init__(
            title="Create Custom Embed" if language == "en" else "Özel Embed Oluştur",
            timeout=300
        )
        self.language = language

    title_input = discord.ui.TextInput(
        label="Embed Title",
        placeholder="Enter the embed title...",
        max_length=256,
        required=True
    )

    description_input = discord.ui.TextInput(
        label="Embed Description",
        placeholder="Enter the embed description...",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=True
    )

    color_input = discord.ui.TextInput(
        label="Embed Color (hex code)",
        placeholder="#FF0000 or red, blue, green...",
        max_length=20,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse color
            color = discord.Color.blue()  # Default
            if self.color_input.value:
                color_value = self.color_input.value.strip()
                if color_value.startswith('#'):
                    color = discord.Color(int(color_value[1:], 16))
                elif color_value.lower() in ['red', 'green', 'blue', 'yellow', 'purple', 'orange']:
                    color = getattr(discord.Color, color_value.lower())()

            embed = discord.Embed(
                title=self.title_input.value,
                description=self.description_input.value,
                color=color
            )

            # Show channel selection for custom embed
            view = ChannelSelectViewCustom(embed)
            
            message = "Select a channel to send your custom embed to:"
            if self.language == "tr":
                message = "Özel embed'inizi göndermek için bir kanal seçin:"
                
            await interaction.response.send_message(message, view=view, ephemeral=True)

        except Exception as e:
            error_msg = f"❌ Error creating custom embed: {str(e)}"
            if self.language == "tr":
                error_msg = f"❌ Özel embed oluşturulurken hata: {str(e)}"
            await interaction.response.send_message(error_msg, ephemeral=True)

class ChannelSelectViewCustom(discord.ui.View):
    def __init__(self, embed):
        super().__init__(timeout=300)
        self.embed = embed

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        placeholder="Select a channel...",
        min_values=1,
        max_values=1
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        
        try:
            await channel.send(embed=self.embed)
            await interaction.response.send_message(f"✅ Custom embed sent to {channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error sending embed: {str(e)}", ephemeral=True)

class FeatureManagementView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    async def initialize(self):
        """Initialize the view - required for server_setup compatibility"""
        # No specific initialization needed for this view
        pass

    @discord.ui.button(label="📊 View Feature Status", style=discord.ButtonStyle.primary, row=0)
    async def view_feature_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_feature_status(interaction)

    @discord.ui.button(label="👋 Toggle Welcome System", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "welcome_system", "Welcome System", "Karşılama Sistemi")

    @discord.ui.button(label="💫 Toggle Leveling System", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_leveling(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "leveling_system", "Leveling System", "Seviye Sistemi")

    @discord.ui.button(label="⭐ Toggle Starboard", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_starboard_feature(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "starboard_system", "Starboard System", "Starboard Sistemi")

    @discord.ui.button(label="🛡️ Toggle Auto Moderation", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_auto_moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "auto_moderation", "Auto Moderation", "Otomatik Moderasyon")    @discord.ui.button(label="📊 Toggle Logging", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_logging_feature(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "logging_system", "Logging System", "Log Sistemi")
        
    @discord.ui.button(label="🎫 Toggle Ticket System", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_ticket_feature(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "ticket_system", "Ticket System", "Ticket Sistemi")
        
    @discord.ui.button(label="🎮 Toggle Community Features", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_community_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "community_features", "Community Features", "Topluluk Özellikleri")
    
    @discord.ui.button(label="🎮 Toggle Temp Channels", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_temp_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_feature(interaction, "temp_channels", "Temp Channels", "Geçici Kanallar")
    
    @discord.ui.button(label="🔄 Reset All Features", style=discord.ButtonStyle.danger, row=2)
    async def reset_all_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reset_all_features_action(interaction)

    async def show_feature_status(self, interaction):
        mongo_db = get_async_db()
        features = await mongo_db.feature_toggles.find_one({"guild_id": interaction.guild.id}) or {}
        
        # Default feature states
        default_features = {
            "welcome_system": True,
            "leveling_system": True,
            "starboard_system": False,
            "auto_moderation": True,
            "logging_system": True,
            "ticket_system": True,
            "community_features": True,
            "temp_channels": True
        }
        
        title = "🔧 Feature Status Overview" if self.language == "en" else "🔧 Özellik Durumu Genel Bakış"
        embed = discord.Embed(title=title, color=discord.Color.blue())
        
        feature_names = {
            "welcome_system": ("👋 Welcome System", "👋 Karşılama Sistemi"),
            "leveling_system": ("💫 Leveling System", "💫 Seviye Sistemi"),
            "starboard_system": ("⭐ Starboard System", "⭐ Starboard Sistemi"),
            "auto_moderation": ("🛡️ Auto Moderation", "🛡️ Otomatik Moderasyon"),
            "logging_system": ("📊 Logging System", "📊 Log Sistemi"),
            "ticket_system": ("🎫 Ticket System", "🎫 Ticket Sistemi"),
            "community_features": ("🎮 Community Features", "🎮 Topluluk Özellikleri"),
            "temp_channels": ("🎮 Temp Channels", "🎮 Geçici Kanallar")
        }
        
        for feature_key, (name_en, name_tr) in feature_names.items():
            is_enabled = features.get(feature_key, default_features.get(feature_key, True))
            name = name_tr if self.language == "tr" else name_en
            status = "🟢 Enabled" if is_enabled else "🔴 Disabled"
            if self.language == "tr":
                status = "🟢 Aktif" if is_enabled else "🔴 Devre Dışı"
            
            embed.add_field(name=name, value=status, inline=True)
        
        description = (
            "Click the buttons below to toggle features on/off. "
            "Disabled features will not function and their commands will be unavailable."
        ) if self.language == "en" else (
            "Özellikleri açmak/kapatmak için aşağıdaki butonları kullanın. "
            "Kapatılan özellikler çalışmayacak ve komutları kullanılamayacaktır."
        )
        
        embed.description = description
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def toggle_feature(self, interaction, feature_key, feature_name_en, feature_name_tr):
        mongo_db = get_async_db()
        features = await mongo_db.feature_toggles.find_one({"guild_id": interaction.guild.id}) or {}
        
        # Get current state (default to True if not set)
        current_state = features.get(feature_key, True)
        new_state = not current_state
        
        # Update in database
        await mongo_db.feature_toggles.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {feature_key: new_state}},
            upsert=True
        )
        
        # Prepare response message
        feature_name = feature_name_tr if self.language == "tr" else feature_name_en
        if new_state:
            status = "enabled" if self.language == "en" else "aktifleştirildi"
            color = discord.Color.green()
            emoji = "🟢"
        else:
            status = "disabled" if self.language == "en" else "devre dışı bırakıldı"
            color = discord.Color.red()
            emoji = "🔴"
        
        title = f"{emoji} {feature_name} {status.title()}"
        description = f"{feature_name} has been {status}." if self.language == "en" else f"{feature_name} {status}."
        
        embed = discord.Embed(title=title, description=description, color=color)
        
        # Add additional info for some features
        if feature_key == "leveling_system" and not new_state:
            warning = (
                "⚠️ **Warning:** All leveling commands will be disabled."
            ) if self.language == "en" else (
                "⚠️ **Uyarı:** Tüm seviye komutları devre dışı kalacaktır."
            )
            embed.add_field(name="Additional Info", value=warning, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def reset_all_features_action(self, interaction):
        # Create a confirmation view
        confirm_view = ConfirmResetView(self.bot, self.language)
        
        title = "⚠️ Confirm Feature Reset" if self.language == "en" else "⚠️ Özellik Sıfırlamayı Onayla"
        description = (
            "This will reset all features to their default state. Are you sure?"
        ) if self.language == "en" else (
            "Bu işlem tüm özellikleri varsayılan durumlarına sıfırlayacaktır. Emin misiniz?"
        )
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class ConfirmResetView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=60)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        mongo_db = get_async_db()
        
        # Delete existing feature toggles to reset to defaults
        await mongo_db.feature_toggles.delete_one({"guild_id": interaction.guild.id})
        
        title = "✅ Features Reset" if self.language == "en" else "✅ Özellikler Sıfırlandı"
        description = (
            "All features have been reset to their default states."
        ) if self.language == "en" else (
            "Tüm özellikler varsayılan durumlarına sıfırlandı."
        )
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        title = "❌ Reset Cancelled" if self.language == "en" else "❌ Sıfırlama İptal Edildi"
        description = "No changes have been made." if self.language == "en" else "Hiçbir değişiklik yapılmadı."
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Placeholder classes for other views that need to be imported
class ServerSettingsView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        
    async def initialize(self):
        """Initialize the view - required for server_setup compatibility"""
        # No specific initialization needed for this view
        pass
        
    @discord.ui.button(label="🏠 Server Settings", style=discord.ButtonStyle.primary, row=0)
    async def server_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.settings.server_views import ServerSettingsCustomView
        await interaction.response.send_message("Choose server settings:", view=ServerSettingsCustomView(self.bot, self.language), ephemeral=True)

class WelcomeGoodbyeView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    async def initialize(self):
        """Initialize the view - required for server_setup compatibility"""
        # No specific initialization needed for this view
        pass

    @discord.ui.button(label="🎉 Configure Welcome", style=discord.ButtonStyle.primary)
    async def configure_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if advanced welcomer cog is available
        welcomer_cog = self.bot.get_cog("Welcomer")
        if welcomer_cog:
            embed = discord.Embed(
                title="🎉 Welcome System Available",
                description="Advanced welcome system is available! Use the buttons below:",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, view=WelcomeConfigView(self.bot, self.language), ephemeral=True)
        else:
            modal = WelcomeMessageModal(self.language)
            await interaction.response.send_modal(modal)

    @discord.ui.button(label="👋 Configure Goodbye", style=discord.ButtonStyle.secondary)
    async def configure_goodbye(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if advanced byebye cog is available
        byebye_cog = self.bot.get_cog("ByeBye")
        if byebye_cog:
            embed = discord.Embed(
                title="👋 Goodbye System Available",
                description="Advanced goodbye system is available! Use the buttons below:",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, view=GoodbyeConfigView(self.bot, self.language), ephemeral=True)
        else:
            modal = GoodbyeMessageModal(self.language)
            await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 View Current Settings", style=discord.ButtonStyle.success)
    async def view_welcome_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_welcome_settings(interaction)
    
    async def show_welcome_settings(self, interaction):
        mongo_db = get_async_db()
        
        # Get welcome settings from multiple collections
        welcome_settings = await mongo_db.welcomer.find_one({"guild_id": interaction.guild.id}) or {}
        goodbye_settings = await mongo_db.byebye.find_one({"guild_id": interaction.guild.id}) or {}
        
        embed = discord.Embed(
            title="👋 Welcome/Goodbye Settings",
            description="Current configuration and preview of your welcome/goodbye system:",
            color=discord.Color.blue()
        )
        
        # Welcome System Status
        welcome_enabled = welcome_settings.get("enabled", False)
        welcome_status = "✅ Enabled" if welcome_enabled else "❌ Disabled"
        
        # Welcome channel
        welcome_channel_id = welcome_settings.get("channel_id") or welcome_settings.get("welcome_channel_id")
        if welcome_channel_id:
            channel = interaction.guild.get_channel(int(welcome_channel_id))
            welcome_channel = channel.mention if channel else f"Channel not found (ID: {welcome_channel_id})"
        else:
            welcome_channel = "Not configured"
        
        embed.add_field(
            name="🎉 Welcome System",
            value=f"**Status:** {welcome_status}\n**Channel:** {welcome_channel}",
            inline=False
        )
        
        # Welcome message preview
        welcome_message = welcome_settings.get("welcome_message", "Welcome {user} to {server}!")
        if len(welcome_message) > 100:
            welcome_preview = welcome_message[:97] + "..."
        else:
            welcome_preview = welcome_message
        
        # Replace placeholders for preview
        welcome_preview = welcome_preview.replace("{user}", interaction.user.mention)
        welcome_preview = welcome_preview.replace("{server}", interaction.guild.name)
        welcome_preview = welcome_preview.replace("{count}", str(interaction.guild.member_count))
        
        embed.add_field(
            name="💬 Welcome Message Preview",
            value=f"```{welcome_preview}```",
            inline=False
        )
        
        # Goodbye System Status
        goodbye_enabled = goodbye_settings.get("enabled", False)
        goodbye_status = "✅ Enabled" if goodbye_enabled else "❌ Disabled"
        
        # Goodbye channel
        goodbye_channel_id = goodbye_settings.get("channel_id") or goodbye_settings.get("byebye_channel_id")
        if goodbye_channel_id:
            channel = interaction.guild.get_channel(int(goodbye_channel_id))
            goodbye_channel = channel.mention if channel else f"Channel not found (ID: {goodbye_channel_id})"
        else:
            goodbye_channel = "Not configured"
        
        embed.add_field(
            name="👋 Goodbye System",
            value=f"**Status:** {goodbye_status}\n**Channel:** {goodbye_channel}",
            inline=False
        )
        
        # Goodbye message preview
        goodbye_message = goodbye_settings.get("goodbye_message", "Goodbye {user}, thanks for being part of {server}!")
        if len(goodbye_message) > 100:
            goodbye_preview = goodbye_message[:97] + "..."
        else:
            goodbye_preview = goodbye_message
        
        # Replace placeholders for preview
        goodbye_preview = goodbye_preview.replace("{user}", interaction.user.display_name)
        goodbye_preview = goodbye_preview.replace("{server}", interaction.guild.name)
        goodbye_preview = goodbye_preview.replace("{count}", str(interaction.guild.member_count))
        
        embed.add_field(
            name="💬 Goodbye Message Preview",
            value=f"```{goodbye_preview}```",
            inline=False
        )
        
        # Background settings
        welcome_bg = welcome_settings.get("background", "Default")
        goodbye_bg = goodbye_settings.get("background", "Default")
        
        if welcome_bg.startswith("images/backgrounds/"):
            welcome_bg = welcome_bg.replace("images/backgrounds/", "").replace(".png", "")
        if goodbye_bg.startswith("images/backgrounds/"):
            goodbye_bg = goodbye_bg.replace("images/backgrounds/", "").replace(".png", "")
        
        embed.add_field(
            name="🖼️ Background Themes",
            value=f"**Welcome:** {welcome_bg}\n**Goodbye:** {goodbye_bg}",
            inline=True
        )
        
        # Additional settings
        additional_info = []
        if welcome_settings.get("ping_user_on_welcome", True):
            additional_info.append("✅ Ping users on welcome")
        if welcome_settings.get("welcome_dm_enabled", False):
            additional_info.append("✅ Welcome DM enabled")
        if welcome_settings.get("auto_role_enabled", False):
            additional_info.append("✅ Auto role enabled")
        
        if additional_info:
            embed.add_field(
                name="⚙️ Additional Features",
                value="\n".join(additional_info),
                inline=True
            )
        
        embed.set_footer(text="Use the buttons above to configure these settings")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ModerationView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🤖 Auto Roles", style=discord.ButtonStyle.primary)
    async def auto_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetAutoRoleModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔒 Word Filter", style=discord.ButtonStyle.secondary)
    async def word_filter(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetWordFilterModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 View Settings", style=discord.ButtonStyle.success)
    async def view_moderation_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_moderation_settings(interaction)

    @discord.ui.button(label="🗑️ Remove Auto Roles", style=discord.ButtonStyle.danger, row=1)
    async def remove_auto_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.remove_setting(interaction, "autorole", "Auto-role")

    @discord.ui.button(label="🗑️ Remove Word Filter", style=discord.ButtonStyle.danger, row=1)
    async def remove_word_filter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.remove_setting(interaction, "filter", "Word filter")

    async def show_moderation_settings(self, interaction):
        mongo_db = get_async_db()
        
        embed = discord.Embed(
            title="🛡️ Moderation Settings" if self.language == "en" else "🛡️ Moderasyon Ayarları",
            color=discord.Color.blue()
        )
        
        # Auto roles
        autorole_settings = await mongo_db.autorole.find_one({"guild_id": interaction.guild.id})
        if autorole_settings and "roles" in autorole_settings:
            role_mentions = []
            for role_id in autorole_settings["roles"]:
                role = interaction.guild.get_role(role_id)
                if role:
                    role_mentions.append(role.mention)
            autoroles = ", ".join(role_mentions) if role_mentions else "Roles not found"
        else:
            autoroles = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="🤖 Auto Roles",
            value=autoroles,
            inline=False
        )
        
        # Word filter
        filter_settings = await mongo_db.filter.find_one({"guild_id": interaction.guild.id})
        if filter_settings:
            action = filter_settings.get("action", "Unknown")
            word_count = len(filter_settings.get("words", []))
            filter_info = f"Action: {action.title()}, Words: {word_count}"
        else:
            filter_info = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="🔒 Word Filter",
            value=filter_info,
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def remove_setting(self, interaction, collection_name, system_name):
        mongo_db = get_async_db()
        result = await mongo_db[collection_name].delete_one({"guild_id": interaction.guild.id})
        
        if result.deleted_count > 0:
            message = f"{system_name} system has been removed." if self.language == "en" else f"{system_name} sistemi kaldırıldı."
            color = discord.Color.green()
        else:
            message = f"{system_name} system was not configured." if self.language == "en" else f"{system_name} sistemi ayarlanmamıştı."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

class LoggingView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="📊 Set Logging Channel", style=discord.ButtonStyle.primary)
    async def set_logging_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetLoggingChannelModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⚙️ Advanced Logging", style=discord.ButtonStyle.secondary)
    async def advanced_logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "tr":
            message = "Gelişmiş loglama ayarlarını yapılandırıyorum:"
        else:
            message = "Configuring advanced logging settings:"
        
        await interaction.response.send_message(
            message, 
            view=AdvancedLoggingView(self.bot, self.language), 
            ephemeral=True
        )

    @discord.ui.button(label="📋 View Current Settings", style=discord.ButtonStyle.success)
    async def view_logging_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_logging_settings(interaction)

    @discord.ui.button(label="🗑️ Remove Logging", style=discord.ButtonStyle.danger)
    async def remove_logging(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.remove_setting(interaction, 'logger', 'Logging System')

    async def show_logging_settings(self, interaction):
        mongo_db = get_async_db()
        settings = await mongo_db.logger.find_one({"guild_id": interaction.guild.id}) or {}
        
        embed = discord.Embed(
            title="📊 Logging Settings" if self.language == "en" else "📊 Log Ayarları",
            color=discord.Color.blue()
        )
        
        # Logging channel
        channel_id = settings.get("channel_id")
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            logging_channel = channel.mention if channel else "Channel not found"
        else:
            logging_channel = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="📊 Logging Channel",
            value=logging_channel,
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def remove_setting(self, interaction, collection_name, system_name):
        mongo_db = get_async_db()
        result = await mongo_db[collection_name].delete_one({"guild_id": interaction.guild.id})
        
        if result.deleted_count > 0:
            message = f"{system_name} system has been removed." if self.language == "en" else f"{system_name} sistemi kaldırıldı."
            color = discord.Color.green()
        else:
            message = f"{system_name} system was not configured." if self.language == "en" else f"{system_name} sistemi ayarlanmamıştı."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

class TicketSystemView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        
    async def initialize(self):
        """Initialize the view - required for server_setup compatibility"""
        # No specific initialization needed for this view
        pass
    
    @discord.ui.button(label="📂 Set Ticket Category", style=discord.ButtonStyle.primary)
    async def set_ticket_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.settings.ticket_views import SetTicketCategoryModal
        modal = SetTicketCategoryModal(self.bot)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="👥 Set Support Roles", style=discord.ButtonStyle.secondary)
    async def set_support_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.settings.ticket_views import SetSupportRolesModal
        modal = SetSupportRolesModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 View Settings", style=discord.ButtonStyle.success)
    async def view_ticket_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_ticket_settings(interaction)

    @discord.ui.button(label="📝 Create Ticket Panel", style=discord.ButtonStyle.primary, row=1)
    async def create_ticket_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        from utils.settings.ticket_views import CreateTicketPanelView
        view = CreateTicketPanelView(self.bot, self.language)
        
        embed = discord.Embed(
            title="📝 Create Ticket Panel" if self.language == "en" else "📝 Bilet Paneli Oluştur",
            description="Select a channel to create the ticket panel in." if self.language == "en" else "Bilet panelini oluşturmak için bir kanal seçin.",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🗑️ Remove Ticket System", style=discord.ButtonStyle.danger, row=1)
    async def remove_ticket_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        mongo_db = get_async_db()
        result = await mongo_db.ticket_settings.delete_one({"guild_id": interaction.guild.id})
        
        if result.deleted_count > 0:
            message = "Ticket system has been removed." if self.language == "en" else "Ticket sistemi kaldırıldı."
            color = discord.Color.green()
        else:
            message = "Ticket system was not configured." if self.language == "en" else "Ticket sistemi ayarlanmamıştı."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

    async def show_ticket_settings(self, interaction):
        mongo_db = get_async_db()
        settings = await mongo_db.ticket_settings.find_one({"guild_id": interaction.guild.id}) or {}
        
        embed = discord.Embed(
            title="🎫 Ticket System Settings" if self.language == "en" else "🎫 Ticket Sistemi Ayarları",
            color=discord.Color.blue()
        )
        
        # Ticket category
        category_id = settings.get("category_id")
        if category_id:
            category = interaction.guild.get_channel(category_id)
            ticket_category = category.name if category else "Category not found"
        else:
            ticket_category = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="📂 Ticket Category",
            value=ticket_category,
            inline=True
        )
        
        # Support roles
        support_roles = settings.get("support_roles", [])
        if support_roles:
            role_mentions = []
            for role_id in support_roles:
                role = interaction.guild.get_role(role_id)
                if role:
                    role_mentions.append(role.mention)
            support_role_text = ", ".join(role_mentions) if role_mentions else "Roles not found"
        else:
            support_role_text = "Not configured" if self.language == "en" else "Ayarlanmamış"
        
        embed.add_field(
            name="👥 Support Roles",
            value=support_role_text,
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RoleManagementView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🎯 Reaction Roles", style=discord.ButtonStyle.primary)
    async def reaction_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "tr":
            embed = discord.Embed(
                title="🎯 Reaction Roles",
                description="Reaktif rol sistemi henüz aktif değil.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="📝 Açıklama",
                value="Bu özellik yakında eklenecek. Lütfen daha sonra tekrar deneyin.",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="🎯 Reaction Roles",
                description="Reaction role system is not active yet.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="📝 Description",
                value="This feature will be added soon. Please try again later.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="👥 Role Hierarchy", style=discord.ButtonStyle.secondary, row=1)
    async def role_hierarchy(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "tr":
            embed = discord.Embed(
                title="👥 Role Hierarchy",
                description="Rol hiyerarşisi yönetimi henüz aktif değil.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="📝 Açıklama",
                value="Bu özellik yakında eklenecek. Lütfen daha sonra tekrar deneyin.",
                inline=False
            )  
        else:
            embed = discord.Embed(
                title="👥 Role Hierarchy",
                description="Role hierarchy management is not active yet.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="📝 Description",
                value="This feature will be added soon. Please try again later.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔧 Auto Roles", style=discord.ButtonStyle.success)
    async def auto_roles_redirect(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "tr":
            message = "Moderasyon ayarlarından otomatik rolleri yönetebilirsiniz:"
        else:
            message = "You can manage auto roles from moderation settings:"
        
        await interaction.response.send_message(message, view=ModerationView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="🚪 Back", style=discord.ButtonStyle.danger, row=1)
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "tr":
            message = "Ana ayarlar menüsüne dönülüyor..."
        else:
            message = "Returning to main settings menu..."
        
        await interaction.response.send_message(message, view=MainSettingsView(self.bot, self.language), ephemeral=True)

# Old StarboardView removed - using enhanced version from starboard_views.py

# Welcome Config View (for advanced system)
class WelcomeConfigView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        
    @discord.ui.button(label="🎨 Full Setup", style=discord.ButtonStyle.primary, row=0)
    async def full_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open comprehensive welcome setup modal"""
        try:
            # Create a comprehensive welcome setup modal
            modal = FullWelcomeSetupModal(self.language)
                    await interaction.response.send_modal(modal)
            except Exception as e:
            logger.error(f"Error opening full setup modal: {e}")
            # Fallback to regular modal
            modal = WelcomeMessageModal(self.language, quick=False)
            await interaction.response.send_modal(modal)

    @discord.ui.button(label="⚡ Quick Setup", style=discord.ButtonStyle.secondary, row=0)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = WelcomeMessageModal(self.language, quick=True)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🌐 Language / Dil", style=discord.ButtonStyle.secondary, row=0)
    async def language_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Language selection for welcome system"""
        embed = discord.Embed(
            title="🌐 Language Selection / Dil Seçimi",
            description="Select your preferred language for the welcome system:\nKarşılama sistemi için tercih ettiğiniz dili seçin:",
            color=discord.Color.blue()
        )
        
        # Create language selection view
        view = LanguageSelectView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🖼️ Background Selection", style=discord.ButtonStyle.secondary, row=0)
    async def background_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🖼️ Welcome Background Selection" if self.language == "en" else "🖼️ Karşılama Arkaplan Seçimi",
            description="Choose a background for welcome messages:" if self.language == "en" else "Karşılama mesajları için bir arkaplan seçin:",
            color=discord.Color.blue()
        )
        
        # Show available backgrounds
        backgrounds_text = (
            "**Available Welcome Backgrounds:**\n"
            "• `welcome_blue` - Blue theme\n"
            "• `welcome_red` - Red theme\n"
            "• `welcome_green` - Green theme\n"
            "• `welcome_purple` - Purple theme\n"
            "• `welcome_light` - Light theme\n"
            "• `welcome_dark` - Dark theme"
        ) if self.language == "en" else (
            "**Mevcut Karşılama Arkaplanları:**\n"
            "• `welcome_blue` - Mavi tema\n"
            "• `welcome_red` - Kırmızı tema\n"
            "• `welcome_green` - Yeşil tema\n"
            "• `welcome_purple` - Mor tema\n"
            "• `welcome_light` - Açık tema\n"
            "• `welcome_dark` - Koyu tema"
        )
        
        embed.add_field(
            name="Backgrounds" if self.language == "en" else "Arkaplanlar",
            value=backgrounds_text,
            inline=False
        )
        
        view = BackgroundSelectionView(self.bot, self.language, "welcome")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="📋 View Settings", style=discord.ButtonStyle.success, row=1)
    async def view_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_welcome_settings(interaction)

    @discord.ui.button(label="🗑️ Disable", style=discord.ButtonStyle.danger, row=1)
    async def disable_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_system(interaction, "welcomer", "Welcome")

    async def show_welcome_settings(self, interaction):
        """Show current welcome system settings"""
        try:
            mongo_db = get_async_db()
            settings = await mongo_db.welcomer.find_one({"guild_id": interaction.guild.id})
            
            embed = discord.Embed(
                title="👋 Welcome System Settings" if self.language == "en" else "👋 Karşılama Sistemi Ayarları",
                color=discord.Color.blue()
            )
            
            if settings:
                # Channel
                channel_id = settings.get("channel_id")
                if channel_id:
                    channel = interaction.guild.get_channel(channel_id)
                    channel_text = channel.mention if channel else f"Channel not found (ID: {channel_id})"
                else:
                    channel_text = "Not configured" if self.language == "en" else "Ayarlanmamış"
                
                embed.add_field(
                    name="📢 Channel" if self.language == "en" else "📢 Kanal",
                    value=channel_text,
                    inline=False
                )
                
                # Message
                message = settings.get("welcome_message", "Not configured")
                if len(message) > 200:
                    message = message[:200] + "..."
                
                embed.add_field(
                    name="💬 Message" if self.language == "en" else "💬 Mesaj",
                    value=f"```{message}```",
                    inline=False
                )
                
                # Background
                background = settings.get("background", "Default")
                if background.startswith("images/backgrounds/"):
                    background = background.replace("images/backgrounds/", "").replace(".png", "")
                
                embed.add_field(
                    name="🖼️ Background" if self.language == "en" else "🖼️ Arkaplan",
                    value=f"`{background}`",
                    inline=True
                )
                
                # Status
                enabled = settings.get("enabled", False)
                status = "✅ Enabled" if enabled else "❌ Disabled"
                if self.language != "en":
                    status = "✅ Etkin" if enabled else "❌ Devre Dışı"
                
                embed.add_field(
                    name="Status" if self.language == "en" else "Durum",
                    value=status,
                    inline=True
                )
                
            else:
                embed.description = "Welcome system is not configured." if self.language == "en" else "Karşılama sistemi yapılandırılmamış."
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing welcome settings: {e}")
            error_msg = "Error loading settings" if self.language == "en" else "Ayarlar yüklenirken hata"
            await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)

    async def disable_system(self, interaction, collection_name, system_name):
        mongo_db = get_async_db()
        result = await mongo_db[collection_name].delete_one({"guild_id": interaction.guild.id})
        
        if result.deleted_count > 0:
            message = f"{system_name} system has been disabled." if self.language == "en" else f"{system_name} sistemi devre dışı bırakıldı."
            color = discord.Color.green()
        else:
            message = f"{system_name} system was not configured." if self.language == "en" else f"{system_name} sistemi ayarlanmamıştı."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

    @discord.ui.button(label="👁️ Preview", style=discord.ButtonStyle.primary, row=1)
    async def preview_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Generate and show a preview of the welcome message"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Get welcome settings
            mongo_db = get_async_db()
            welcome_data = await mongo_db.welcomer.find_one({"guild_id": interaction.guild.id})
            
            if not welcome_data or not welcome_data.get("enabled"):
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Welcome System Not Configured",
                        description="Please configure the welcome system first using the Full Setup or Quick Setup options.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            
            # Check if advanced welcomer cog is available
            welcomer_cog = self.bot.get_cog('Welcomer')
            if welcomer_cog and hasattr(welcomer_cog, 'create_welcome_image'):
                try:
                    # Generate preview using the actual welcome card generator
                    from utils.greeting.welcomer.preview_generator import generate_card_preview
                    
                    # Create a config dict from the welcome data
                    config = {
                        "welcome_message": welcome_data.get("welcome_message", "Welcome {user}!"),
                        "welcome_font_size": welcome_data.get("welcome_font_size", 100),
                        "member_font_size": welcome_data.get("member_font_size", 42),
                        "welcome_y": welcome_data.get("welcome_y", 295),
                        "member_y": welcome_data.get("member_y", 390),
                        "avatar_y": welcome_data.get("avatar_y", 50),
                        "avatar_size": welcome_data.get("avatar_size", 215),
                        "text_color": welcome_data.get("text_color", "#FFFFFF"),
                        "outline_color": welcome_data.get("outline_color", "#000000"),
                        "text_outline": welcome_data.get("text_outline", False),
                        "shadow": welcome_data.get("shadow", True),
                        "background_theme": welcome_data.get("background_theme", "default")
                    }
                    
                    # Generate preview image using the welcomer cog
                    background = welcome_data.get("background", "data/Backgrounds/default_background.png")
                    preview_path = await welcomer_cog.create_welcome_image(
                        interaction.user,
                        background,
                        config
                    )
                    
                    if preview_path and os.path.exists(preview_path):
                        # Create embed with preview
                        embed = discord.Embed(
                            title="👋 Welcome Message Preview",
                            description="This is how your welcome message will look:",
                            color=discord.Color.green()
                        )
                        
                        # Format message for preview with safe variable replacement
                        message_template = welcome_data.get("welcome_message", "Welcome {user}!")
                        try:
                            formatted_message = message_template.format(
                                user=interaction.user.mention,
                                username=interaction.user.name,
                                server=interaction.guild.name,
                                count=interaction.guild.member_count,
                                member_count=interaction.guild.member_count
                            )
                        except KeyError as e:
                            # Handle missing variables gracefully
                            logger.warning(f"Missing variable in welcome message: {e}")
                            formatted_message = message_template.replace("{user}", interaction.user.mention)
                            formatted_message = formatted_message.replace("{username}", interaction.user.name)
                            formatted_message = formatted_message.replace("{server}", interaction.guild.name)
                            formatted_message = formatted_message.replace("{count}", str(interaction.guild.member_count))
                            formatted_message = formatted_message.replace("{member_count}", str(interaction.guild.member_count))
                        
                        # Add current settings info
                        embed.add_field(
                            name="📝 Message Template",
                            value=f"```{formatted_message}```",
                            inline=False
                        )
                        
                        channel_id = welcome_data.get("channel_id")
                        if channel_id:
                            channel = interaction.guild.get_channel(int(channel_id))
                            embed.add_field(
                                name="📍 Channel",
                                value=channel.mention if channel else f"ID: {channel_id}",
                                inline=True
                            )
                        
                        embed.add_field(
                            name="🎨 Theme",
                            value=welcome_data.get("background_theme", "default").title(),
                            inline=True
                        )
                        
                        # Send preview
                        file = discord.File(preview_path, filename="welcome_preview.png")
                        embed.set_image(url="attachment://welcome_preview.png")
                        
                        await interaction.followup.send(embed=embed, file=file, ephemeral=True)
                        
                        # Clean up
                        try:
                            os.remove(preview_path)
                        except:
                            pass
                    else:
                        await interaction.followup.send(
                            "❌ Could not generate preview image.",
                            ephemeral=True
                        )
                        
                except Exception as e:
                    logger.error(f"Error generating welcome preview: {e}")
                    await interaction.followup.send(
                        f"❌ Error generating preview: {str(e)}",
                        ephemeral=True
                    )
            else:
                # Fallback text preview
                embed = discord.Embed(
                    title="👋 Welcome Message Preview",
                    description="Text preview (image generation not available):",
                    color=discord.Color.blue()
                )
                
                # Format the message with the user - safe variable replacement
                message = welcome_data.get("welcome_message", "Welcome {user}!")
                try:
                    formatted_message = message.format(
                        user=interaction.user.mention,
                        username=interaction.user.name,
                        server=interaction.guild.name,
                        count=interaction.guild.member_count,
                        member_count=interaction.guild.member_count
                    )
                except KeyError as e:
                    # Handle missing variables gracefully
                    logger.warning(f"Missing variable in welcome message: {e}")
                    formatted_message = message.replace("{user}", interaction.user.mention)
                    formatted_message = formatted_message.replace("{username}", interaction.user.name)
                    formatted_message = formatted_message.replace("{server}", interaction.guild.name)
                    formatted_message = formatted_message.replace("{count}", str(interaction.guild.member_count))
                    formatted_message = formatted_message.replace("{member_count}", str(interaction.guild.member_count))
                
                embed.add_field(
                    name="📝 Formatted Message",
                    value=formatted_message,
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in preview welcome: {e}")
            await interaction.followup.send(
                f"❌ Error generating preview: {str(e)}",
                ephemeral=True
            )

# Goodbye Config View (for advanced system)
class GoodbyeConfigView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🎨 Full Setup", style=discord.ButtonStyle.primary, row=0)
    async def full_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open comprehensive goodbye setup modal"""
        try:
            # Create a comprehensive goodbye setup modal
            modal = FullGoodbyeSetupModal(self.language)
                    await interaction.response.send_modal(modal)
            except Exception as e:
            logger.error(f"Error opening full goodbye setup modal: {e}")
            # Fallback to regular modal
            modal = GoodbyeMessageModal(self.language)
            await interaction.response.send_modal(modal)

    @discord.ui.button(label="⚡ Quick Setup", style=discord.ButtonStyle.secondary, row=0)
    async def quick_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = GoodbyeMessageModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🌐 Language / Dil", style=discord.ButtonStyle.secondary, row=0)
    async def language_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Language selection for goodbye system"""
        embed = discord.Embed(
            title="🌐 Language Selection / Dil Seçimi",
            description="Select your preferred language for the goodbye system:\nVeda sistemi için tercih ettiğiniz dili seçin:",
            color=discord.Color.blue()
        )
        
        # Create language selection view
        view = LanguageSelectView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🖼️ Background Selection", style=discord.ButtonStyle.secondary, row=0)
    async def background_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🖼️ Goodbye Background Selection" if self.language == "en" else "🖼️ Vedalaşma Arkaplan Seçimi",
            description="Choose a background for goodbye messages:" if self.language == "en" else "Vedalaşma mesajları için bir arkaplan seçin:",
            color=discord.Color.orange()
        )
        
        # Show available backgrounds
        backgrounds_text = (
            "**Available Goodbye Backgrounds:**\n"
            "• `byebye_blue` - Blue theme\n"
            "• `byebye_red` - Red theme\n"
            "• `byebye_green` - Green theme\n"
            "• `byebye_purple` - Purple theme\n"
            "• `byebye_light` - Light theme\n"
            "• `byebye_dark` - Dark theme"
        ) if self.language == "en" else (
            "**Mevcut Vedalaşma Arkaplanları:**\n"
            "• `byebye_blue` - Mavi tema\n"
            "• `byebye_red` - Kırmızı tema\n"
            "• `byebye_green` - Yeşil tema\n"
            "• `byebye_purple` - Mor tema\n"
            "• `byebye_light` - Açık tema\n"
            "• `byebye_dark` - Koyu tema"
        )
        
        embed.add_field(
            name="Backgrounds" if self.language == "en" else "Arkaplanlar",
            value=backgrounds_text,
            inline=False
        )
        
        view = BackgroundSelectionView(self.bot, self.language, "goodbye")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="📋 View Settings", style=discord.ButtonStyle.success, row=1)
    async def view_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_goodbye_settings(interaction)

    @discord.ui.button(label="🗑️ Disable", style=discord.ButtonStyle.danger, row=1)
    async def disable_goodbye(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_system(interaction, "byebye", "Goodbye")

    async def show_goodbye_settings(self, interaction):
        """Show current goodbye system settings"""
        try:
            mongo_db = get_async_db()
            settings = await mongo_db.byebye.find_one({"guild_id": interaction.guild.id})
            
            embed = discord.Embed(
                title="👋 Goodbye System Settings" if self.language == "en" else "👋 Vedalaşma Sistemi Ayarları",
                color=discord.Color.orange()
            )
            
            if settings:
                # Channel
                channel_id = settings.get("channel_id")
                if channel_id:
                    channel = interaction.guild.get_channel(channel_id)
                    channel_text = channel.mention if channel else f"Channel not found (ID: {channel_id})"
                else:
                    channel_text = "Not configured" if self.language == "en" else "Ayarlanmamış"
                
                embed.add_field(
                    name="📢 Channel" if self.language == "en" else "📢 Kanal",
                    value=channel_text,
                    inline=False
                )
                
                # Message
                message = settings.get("goodbye_message", "Not configured")
                if len(message) > 200:
                    message = message[:200] + "..."
                
                embed.add_field(
                    name="💬 Message" if self.language == "en" else "💬 Mesaj",
                    value=f"```{message}```",
                    inline=False
                )
                
                # Background
                background = settings.get("background", "Default")
                if background.startswith("images/backgrounds/"):
                    background = background.replace("images/backgrounds/", "").replace(".png", "")
                
                embed.add_field(
                    name="🖼️ Background" if self.language == "en" else "🖼️ Arkaplan",
                    value=f"`{background}`",
                    inline=True
                )
                
                # Status
                enabled = settings.get("enabled", False)
                status = "✅ Enabled" if enabled else "❌ Disabled"
                if self.language != "en":
                    status = "✅ Etkin" if enabled else "❌ Devre Dışı"
                
                embed.add_field(
                    name="Status" if self.language == "en" else "Durum",
                    value=status,
                    inline=True
                )
                
            else:
                embed.description = "Goodbye system is not configured." if self.language == "en" else "Vedalaşma sistemi yapılandırılmamış."
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing goodbye settings: {e}")
            error_msg = "Error loading settings" if self.language == "en" else "Ayarlar yüklenirken hata"
            await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)

    async def disable_system(self, interaction, collection_name, system_name):
        mongo_db = get_async_db()
        result = await mongo_db[collection_name].delete_one({"guild_id": interaction.guild.id})
        
        if result.deleted_count > 0:
            message = f"{system_name} system has been disabled." if self.language == "en" else f"{system_name} sistemi devre dışı bırakıldı."
            color = discord.Color.green()
        else:
            message = f"{system_name} system was not configured." if self.language == "en" else f"{system_name} sistemi ayarlanmamıştı."
            color = discord.Color.yellow()
        
        await interaction.response.send_message(embed=create_embed(message, color), ephemeral=True)

    @discord.ui.button(label="👁️ Preview", style=discord.ButtonStyle.primary, row=1)
    async def preview_goodbye(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Generate and show a preview of the goodbye message"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Get goodbye settings
            mongo_db = await get_async_db()
            goodbye_data = await mongo_db.byebye.find_one({"guild_id": interaction.guild.id})
            
            if not goodbye_data or not goodbye_data.get("enabled"):
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="❌ Goodbye System Not Configured",
                        description="Please configure the goodbye system first using the Full Setup or Quick Setup options.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            
            # Check if advanced byebye cog is available
            byebye_cog = self.bot.get_cog('AdvancedByebye')
            if byebye_cog and hasattr(byebye_cog, 'generate_goodbye_card'):
                try:
                    # Generate preview using the actual goodbye card generator
                    from utils.greeting.welcomer.preview_generator import generate_card_preview
                    
                    # Create a config dict from the goodbye data
                    config = {
                        "welcome_message": goodbye_data.get("goodbye_message", "Goodbye {user}!"),
                        "welcome_font_size": goodbye_data.get("goodbye_font_size", 100),
                        "member_font_size": goodbye_data.get("member_font_size", 42),
                        "welcome_y": goodbye_data.get("goodbye_y", 295),
                        "member_y": goodbye_data.get("member_y", 390),
                        "avatar_y": goodbye_data.get("avatar_y", 50),
                        "avatar_size": goodbye_data.get("avatar_size", 215),
                        "text_color": goodbye_data.get("text_color", "#FFFFFF"),
                        "outline_color": goodbye_data.get("outline_color", "#000000"),
                        "text_outline": goodbye_data.get("text_outline", False),
                        "shadow": goodbye_data.get("shadow", True),
                        "background_theme": goodbye_data.get("background_theme", "default")
                    }
                    
                    # Generate preview image
                    preview_path = await generate_card_preview(
                        self.bot,
                        interaction.user,
                        config,
                        is_welcome=False
                    )
                    
                    if preview_path and os.path.exists(preview_path):
                        # Create embed with preview
                        embed = discord.Embed(
                            title="👋 Goodbye Message Preview",
                            description="This is how your goodbye message will look:",
                            color=discord.Color.orange()
                        )
                        
                        # Add current settings info
                        embed.add_field(
                            name="📝 Message Template",
                            value=f"```{goodbye_data.get('goodbye_message', 'Goodbye {user}!')}```",
                            inline=False
                        )
                        
                        channel_id = goodbye_data.get("channel_id")
                        if channel_id:
                            channel = interaction.guild.get_channel(int(channel_id))
                            embed.add_field(
                                name="📍 Channel",
                                value=channel.mention if channel else f"ID: {channel_id}",
                                inline=True
                            )
                        
                        embed.add_field(
                            name="🎨 Theme",
                            value=goodbye_data.get("background_theme", "default").title(),
                            inline=True
                        )
                        
                        # Send preview
                        file = discord.File(preview_path, filename="goodbye_preview.png")
                        embed.set_image(url="attachment://goodbye_preview.png")
                        
                        await interaction.followup.send(embed=embed, file=file, ephemeral=True)
                        
                        # Clean up
                        try:
                            os.remove(preview_path)
                        except:
                            pass
        else:
                        await interaction.followup.send(
                            "❌ Could not generate preview image.",
                            ephemeral=True
                        )
                        
                except Exception as e:
                    logger.error(f"Error generating goodbye preview: {e}")
                    await interaction.followup.send(
                        f"❌ Error generating preview: {str(e)}",
                        ephemeral=True
                    )
            else:
                # Fallback text preview
                embed = discord.Embed(
                    title="👋 Goodbye Message Preview",
                    description="Text preview (image generation not available):",
                    color=discord.Color.orange()
                )
                
                # Format the message with the user
                message = goodbye_data.get("goodbye_message", "Goodbye {user}!")
                formatted_message = message.format(
                    user=interaction.user.mention,
                    username=interaction.user.name,
                    server=interaction.guild.name,
                    member_count=interaction.guild.member_count - 1
                )
                
                embed.add_field(
                    name="📝 Formatted Message",
                    value=formatted_message,
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in preview goodbye: {e}")
            await interaction.followup.send(
                f"❌ Error generating preview: {str(e)}",
                ephemeral=True
            )

# Modal classes for moderation
class SetAutoRoleModal(discord.ui.Modal):
    """Modal for setting auto roles"""
    def __init__(self, language="en"):
        title = "🤖 Auto Roles" if language == "en" else "🤖 Otomatik Roller"
        super().__init__(title=title)
        self.language = language
        
        self.role_ids = discord.ui.TextInput(
            label="Role IDs" if language == "en" else "Rol ID'leri",
            placeholder="Enter role IDs separated by commas" if language == "en" else "Rol ID'lerini virgülle ayırarak girin",
            required=True,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.role_ids)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse role IDs
            role_id_strings = self.role_ids.value.split(',')
            role_ids = []
            invalid_ids = []
            
            for id_str in role_id_strings:
                id_str = id_str.strip()
                if not id_str:
                    continue
                    
                try:
                    role_id = int(id_str)
                    role = interaction.guild.get_role(role_id)
                    
                    if role:
                        role_ids.append(role_id)
                    else:
                        invalid_ids.append(id_str)
                except ValueError:
                    invalid_ids.append(id_str)
            
            if not role_ids:
                error_msg = "Please enter at least one valid role ID." if self.language == "en" else "En az bir geçerli rol ID'si girmelisiniz."
                return await interaction.response.send_message(
                    embed=create_embed(error_msg, discord.Color.red()),
                    ephemeral=True
                )
            
            # Save to database
            mongo_db = get_async_db()
            await mongo_db.autorole.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"roles": role_ids}},
                upsert=True
            )
            
            # Construct response message
            role_mentions = [f"<@&{role_id}>" for role_id in role_ids]
            roles_text = ", ".join(role_mentions)
            
            success_msg = f"Auto roles successfully set: {roles_text}" if self.language == "en" else f"Otomatik roller başarıyla ayarlandı: {roles_text}"
            if invalid_ids:
                invalid_msg = f"\n\nInvalid IDs: {', '.join(invalid_ids)}" if self.language == "en" else f"\n\nGeçersiz ID'ler: {', '.join(invalid_ids)}"
                success_msg += invalid_msg
            
            await interaction.response.send_message(
                embed=create_embed(success_msg, discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}" if self.language == "en" else f"Bir hata oluştu: {str(e)}"
            await interaction.response.send_message(
                embed=create_embed(error_msg, discord.Color.red()),
                ephemeral=True
            )

class SetWordFilterModal(discord.ui.Modal):
    """Modal for setting word filter"""
    def __init__(self, language="en"):
        title = "🔒 Word Filter" if language == "en" else "🔒 Kelime Filtresi"
        super().__init__(title=title)
        self.language = language
        
        self.words = discord.ui.TextInput(
            label="Filtered Words" if language == "en" else "Filtrelenecek Kelimeler",
            placeholder="Enter words separated by commas" if language == "en" else "Kelimeleri virgülle ayırarak girin",
            required=True,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.words)
        
        self.action = discord.ui.TextInput(
            label="Action (delete/warn/kick/ban)" if language == "en" else "Eylem (delete/warn/kick/ban)",
            placeholder="delete" if language == "en" else "delete",
            required=True,
            max_length=10
        )
        self.add_item(self.action)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse words
            words = [word.strip().lower() for word in self.words.value.split(',') if word.strip()]
            action = self.action.value.lower().strip()
            
            if not words:
                error_msg = "Please enter at least one word." if self.language == "en" else "En az bir kelime girmelisiniz."
                return await interaction.response.send_message(
                    embed=create_embed(error_msg, discord.Color.red()),
                    ephemeral=True
                )
            
            if action not in ["delete", "warn", "kick", "ban"]:
                error_msg = "Action must be: delete, warn, kick, or ban" if self.language == "en" else "Eylem şunlardan biri olmalı: delete, warn, kick, ban"
                return await interaction.response.send_message(
                    embed=create_embed(error_msg, discord.Color.red()),
                    ephemeral=True
                )
            
            # Save to database
            mongo_db = get_async_db()
            await mongo_db.filter.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"words": words, "action": action}},
                upsert=True
            )
            
            success_msg = f"Word filter successfully configured!\nWords: {len(words)}\nAction: {action.title()}" if self.language == "en" else f"Kelime filtresi başarıyla yapılandırıldı!\nKelime sayısı: {len(words)}\nEylem: {action.title()}"
            
            await interaction.response.send_message(
                embed=create_embed(success_msg, discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}" if self.language == "en" else f"Bir hata oluştu: {str(e)}"
            await interaction.response.send_message(
                embed=create_embed(error_msg, discord.Color.red()),
                ephemeral=True
            )

class SetLoggingChannelModal(discord.ui.Modal):
    """Modal for setting logging channel"""
    def __init__(self, language="en"):
        title = "📊 Set Logging Channel" if language == "en" else "📊 Log Kanalı Ayarla"
        super().__init__(title=title)
        self.language = language
        
        self.channel_id = discord.ui.TextInput(
            label="Channel ID" if language == "en" else "Kanal ID",
            placeholder="Enter channel ID or mention channel" if language == "en" else "Kanal ID'sini girin veya kanalı etiketleyin",
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.channel_id)

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
                    error_msg = "Invalid channel ID format." if self.language == "en" else "Geçersiz kanal ID formatı."
                    await interaction.response.send_message(
                        embed=create_embed(error_msg, discord.Color.red()),
                        ephemeral=True
                    )
                    return
            
            # Get the channel
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                error_msg = "Channel not found." if self.language == "en" else "Kanal bulunamadı."
                await interaction.response.send_message(
                    embed=create_embed(error_msg, discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Check if it's a text channel
            if not isinstance(channel, discord.TextChannel):
                error_msg = "The specified channel is not a text channel." if self.language == "en" else "Belirtilen kanal bir metin kanalı değil."
                await interaction.response.send_message(
                    embed=create_embed(error_msg, discord.Color.red()),
                    ephemeral=True
                )
                return
            
            # Save to database
            mongo_db = get_async_db()
            await mongo_db.logger.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"channel_id": channel_id}},
                upsert=True
            )
            
            success_msg = f"Logging channel set to {channel.mention}" if self.language == "en" else f"Log kanalı {channel.mention} olarak ayarlandı"
            await interaction.response.send_message(
                embed=create_embed(success_msg, discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}" if self.language == "en" else f"Bir hata oluştu: {str(e)}"
            await interaction.response.send_message(
                embed=create_embed(error_msg, discord.Color.red()),
                ephemeral=True
            )

class AdvancedLoggingView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        
    @discord.ui.button(label="👥 Member Events", style=discord.ButtonStyle.primary, row=0)
    async def member_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSpecificLoggingChannelModal(
            self.language, 
            "member_events", 
            "Member Events" if self.language == "en" else "Üye Olayları",
            "Joins, leaves, bans, roles"
        )
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="💬 Message Events", style=discord.ButtonStyle.primary, row=0)
    async def message_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSpecificLoggingChannelModal(
            self.language, 
            "message_events", 
            "Message Events" if self.language == "en" else "Mesaj Olayları",
            "Edits, deletes, bulk delete"
        )
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="🔧 Server Events", style=discord.ButtonStyle.primary, row=0)
    async def server_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSpecificLoggingChannelModal(
            self.language,
            "server_events",
            "Server Events" if self.language == "en" else "Sunucu Olayları",
            "Channels, roles, guild settings"
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔊 Voice Events", style=discord.ButtonStyle.secondary, row=1)
    async def voice_events(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetSpecificLoggingChannelModal(
            self.language,
            "voice_events",
            "Voice Events" if self.language == "en" else "Ses Olayları",
            "Join, leave, move voice channels"
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📋 View All Settings", style=discord.ButtonStyle.success, row=1)
    async def view_all_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_advanced_logging_settings(interaction)

    @discord.ui.button(label="🔄 Reset All", style=discord.ButtonStyle.danger, row=1)
    async def reset_all_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reset_all_logging_settings(interaction)

    async def show_advanced_logging_settings(self, interaction):
        mongo_db = get_async_db()
        settings = await mongo_db.logger_settings.find_one({"guild_id": interaction.guild.id}) or {}
        
        embed = discord.Embed(
            title="📊 Advanced Logging Settings" if self.language == "en" else "📊 Gelişmiş Log Ayarları",
            color=discord.Color.blue()
        )
        
        # Categories to check
        categories = {
            "member_events": ("👥 Member Events", "👥 Üye Olayları"),
            "message_events": ("💬 Message Events", "💬 Mesaj Olayları"),
            "server_events": ("🔧 Server Events", "🔧 Sunucu Olayları"),
            "voice_events": ("🔊 Voice Events", "🔊 Ses Olayları"),
        }
        
        for category, (name_en, name_tr) in categories.items():
            channel_id = settings.get(f"{category}_channel")
            if channel_id:
                try:
                    channel = interaction.guild.get_channel(channel_id)
                    channel_mention = f"<#{channel_id}>" if channel else f"Unknown ({channel_id})"
                    
                    field_name = name_en if self.language == "en" else name_tr
                    embed.add_field(name=field_name, value=channel_mention, inline=True)
                    
                except Exception as e:
                    logger.error(f"Error getting channel {channel_id}: {e}")
                    embed.add_field(
                        name=name_en if self.language == "en" else name_tr,
                        value="Error fetching channel",
                        inline=True
                    )
            else:
                # If not set, will use main channel
                embed.add_field(
                    name=name_en if self.language == "en" else name_tr,
                    value="Uses main channel" if self.language == "en" else "Ana kanalı kullanır",
                    inline=True
                )
        
        footer_text = (
            "Events will be sent to their specific channel if set, otherwise to the main logging channel." 
            if self.language == "en" else 
            "Olaylar, belirtilen özel kanala ayarlanmışsa oraya, aksi takdirde ana loglama kanalına gönderilecektir."
        )
        embed.set_footer(text=footer_text)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def reset_all_logging_settings(self, interaction):
        confirm_text = "Are you sure you want to reset all logging channel settings?" if self.language == "en" else "Tüm loglama kanalı ayarlarını sıfırlamak istediğinize emin misiniz?"
        
        embed = discord.Embed(
            title="⚠️ Confirm Reset" if self.language == "en" else "⚠️ Sıfırlamayı Onayla",
            description=confirm_text,
            color=discord.Color.red()
        )
        
        view = ConfirmLoggingResetView(self.bot, self.language)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class SetSpecificLoggingChannelModal(discord.ui.Modal):
    def __init__(self, language="en", category="member_events", title_text="Member Events", description_text=""):
        title = f"Set {title_text} Channel" if language == "en" else f"{title_text} Kanalı Ayarla"
        super().__init__(title=title)
        self.language = language
        self.category = category
        
        placeholder = f"#{category.replace('_', '-')} or channel ID"
        if description_text:
            if language == "en":
                placeholder += f" ({description_text})"
            else:
                tr_desc = description_text  # You might want to translate this
                placeholder += f" ({tr_desc})"
        
        self.channel = discord.ui.TextInput(
            label="Channel" if language == "en" else "Kanal",
            placeholder=placeholder,
            style=discord.TextStyle.short,
            max_length=100
        )
        
        self.add_item(self.channel)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Try to get channel from input
            channel_input = self.channel.value.strip()
            
            # Check if input is a channel mention
            channel_id = None
            if channel_input.startswith("<#") and channel_input.endswith(">"):
                channel_id = int(channel_input[2:-1])
            elif channel_input.startswith("#"):
                # Find by name
                channel_name = channel_input[1:]
                channel = discord.utils.get(interaction.guild.channels, name=channel_name)
                if channel:
                    channel_id = channel.id
            else:
                # Try to parse as ID
                try:
                    channel_id = int(channel_input)
                except ValueError:
                    # Try to find by name without #
                    channel = discord.utils.get(interaction.guild.channels, name=channel_input)
                    if channel:
                        channel_id = channel.id
            
            if not channel_id:
                error_msg = "Invalid channel! Please specify a valid channel." if self.language == "en" else "Geçersiz kanal! Lütfen geçerli bir kanal belirtin."
                await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                return
            
            # Check if channel exists and is text-based
            channel = interaction.guild.get_channel(channel_id)
            if not channel or not isinstance(channel, (discord.TextChannel, discord.Thread, discord.ForumChannel)):
                error_msg = "Channel not found or not a text channel!" if self.language == "en" else "Kanal bulunamadı veya bir metin kanalı değil!"
                await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                return
            
            # Check permissions
            bot_permissions = channel.permissions_for(interaction.guild.me)
            if not bot_permissions.send_messages or not bot_permissions.embed_links:
                error_msg = f"I don't have permission to send messages in {channel.mention}!" if self.language == "en" else f"{channel.mention} kanalında mesaj gönderme iznim yok!"
                await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                return
            
            # Save to database
            mongo_db = get_async_db()
            
            # Update specific category channel
            await mongo_db.logger_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {f"{self.category}_channel": channel_id}},
                upsert=True
            )
            
            # Send success message
            if self.language == "en":
                success_msg = f"✅ Successfully set {self.title} channel to {channel.mention}!"
            else:
                success_msg = f"✅ {self.title} kanalı başarıyla {channel.mention} olarak ayarlandı!"
                
            embed = discord.Embed(
                description=success_msg,
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error setting specific logging channel: {e}", exc_info=True)
            error_msg = "An error occurred while setting the logging channel." if self.language == "en" else "Log kanalını ayarlarken bir hata oluştu."
            await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)

class ConfirmLoggingResetView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
    
    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            mongo_db = get_async_db()
            
            # Keep the main logger channel but remove all specific channels
            main_settings = await mongo_db.logger.find_one({"guild_id": interaction.guild.id})
            
            if main_settings:
                # Reset advanced settings but keep the main channel
                await mongo_db.logger_settings.update_one(
                    {"guild_id": interaction.guild.id},
                    {"$unset": {
                        "member_events_channel": "",
                        "message_events_channel": "",
                        "server_events_channel": "",
                        "voice_events_channel": "",
                        "event_activities_channel": "",
                        "thread_events_channel": "",
                        "command_events_channel": ""
                    }},
                    upsert=True
                )
            else:
                # If no main settings, just delete everything
                await mongo_db.logger_settings.delete_one({"guild_id": interaction.guild.id})
            
            success_text = "All advanced logging channel settings have been reset." if self.language == "en" else "Tüm gelişmiş loglama kanalı ayarları sıfırlandı."
            
            embed = discord.Embed(
                title="✅ Reset Complete" if self.language == "en" else "✅ Sıfırlama Tamamlandı",
                description=success_text,
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error resetting logging channels: {e}", exc_info=True)
            
            error_text = "An error occurred while resetting logging channels." if self.language == "en" else "Loglama kanallarını sıfırlarken bir hata oluştu."
            
            embed = discord.Embed(
                title="❌ Error" if self.language == "en" else "❌ Hata",
                description=error_text,
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        cancel_text = "Reset operation canceled." if self.language == "en" else "Sıfırlama işlemi iptal edildi."
        
        embed = discord.Embed(
            title="Operation Canceled" if self.language == "en" else "İşlem İptal Edildi",
            description=cancel_text,
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# AI and Birthday Settings View
class AISettingsView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🤖 Configure AI Settings", style=discord.ButtonStyle.primary)
    async def configure_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AISettingsModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔄 Reset AI Settings", style=discord.ButtonStyle.danger)
    async def reset_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reset_ai_settings(interaction)

    async def reset_ai_settings(self, interaction):
        mongo_db = get_async_db()
        await mongo_db.ai_settings.delete_one({"guild_id": interaction.guild.id})
        
        success_msg = "AI settings have been reset to default." if self.language == "en" else "AI ayarları varsayılan değerlere sıfırlandı."
        await interaction.response.send_message(embed=create_embed(success_msg, discord.Color.green()), ephemeral=True)

class BirthdaySettingsView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🎂 Configure Birthday Settings", style=discord.ButtonStyle.primary)
    async def configure_birthday(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = BirthdaySettingsModal(self.language)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔄 Reset Birthday Settings", style=discord.ButtonStyle.danger)
    async def reset_birthday(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reset_birthday_settings(interaction)

    async def reset_birthday_settings(self, interaction):
        mongo_db = get_async_db()
        await mongo_db.birthday_settings.delete_one({"guild_id": interaction.guild.id})
        
        success_msg = "Birthday settings have been reset to default." if self.language == "en" else "Doğum günü ayarları varsayılan değerlere sıfırlandı."
        await interaction.response.send_message(embed=create_embed(success_msg, discord.Color.green()), ephemeral=True)

# Modal classes for AI and Birthday settings
class AISettingsModal(discord.ui.Modal):
    def __init__(self, language="en"):
        super().__init__(
            title="Configure AI Settings" if language == "en" else "AI Ayarlarını Yapılandır",
            timeout=300
        )
        self.language = language

    # Example setting: AI Name
    ai_name = discord.ui.TextInput(
        label="AI Name",
        placeholder="Enter the AI's name...",
        max_length=100,
        required=True
    )
    # Add more settings as needed

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Save AI settings to database
            mongo_db = get_async_db()
            await mongo_db.ai_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {
                    "ai_name": self.ai_name.value,
                    # Add more settings here
                }},
                upsert=True
            )
            
            success_msg = "AI settings have been saved." if self.language == "en" else "AI ayarları kaydedildi."
            await interaction.response.send_message(embed=create_embed(success_msg, discord.Color.green()), ephemeral=True)
        
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}" if self.language == "en" else f"Bir hata oluştu: {str(e)}"
            await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)

class BirthdaySettingsModal(discord.ui.Modal):
    def __init__(self, language="en"):
        super().__init__(
            title="Configure Birthday Settings" if language == "en" else "Doğum Günü Ayarlarını Yapılandır",
            timeout=300
        )
        self.language = language

    # Example setting: Birthday Channel
    birthday_channel = discord.ui.TextInput(
        label="Birthday Channel",
        placeholder="Enter the channel ID or mention the channel...",
        max_length=100,
        required=True
    )
    # Add more settings as needed

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Save birthday settings to database
            mongo_db = get_async_db()
            await mongo_db.birthday_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {
                    "birthday_channel": self.birthday_channel.value,
                    # Add more settings here
                }},
                upsert=True
            )
            
            success_msg = "Birthday settings have been saved." if self.language == "en" else "Doğum günü ayarları kaydedildi."
            await interaction.response.send_message(embed=create_embed(success_msg, discord.Color.green()), ephemeral=True)
        
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}" if self.language == "en" else f"Bir hata oluştu: {str(e)}"
            await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)

# Welcome/Goodbye Settings Modal Classes
class WelcomeMessageModal(discord.ui.Modal):
    """Modal for configuring welcome message settings"""
    def __init__(self, language="en", quick=False):
        title = ("Quick Welcome Setup" if quick else "Welcome Message Settings") if language == "en" else ("Hızlı Karşılama Kurulumu" if quick else "Karşılama Mesajı Ayarları")
        super().__init__(title=title, timeout=300)
        self.language = language
        self.quick = quick
        
        # Channel ID (moved to top - most important)
        self.channel_id = discord.ui.TextInput(
            label="Channel ID" if language == "en" else "Kanal ID",
            placeholder="Enter channel ID or #channel-mention" if language == "en" else "Kanal ID'sini girin veya #kanal-etiket",
            style=discord.TextStyle.short,
            required=True
        )
        self.add_item(self.channel_id)
        
        # Language selection
        self.language_setting = discord.ui.TextInput(
            label="Language" if language == "en" else "Dil",
            placeholder="en (English) or tr (Türkçe)" if language == "en" else "en (İngilizce) veya tr (Türkçe)",
            style=discord.TextStyle.short,
            default=language,
            required=False
        )
        self.add_item(self.language_setting)
        
        # Welcome message (optional with default)
        default_message = "Welcome {user} to {server}! You are member #{count}" if language == "en" else "Hoş geldin {user}! {server} sunucusuna hoş geldin! Sen {count}. üyesin!"
        self.welcome_message = discord.ui.TextInput(
            label="Welcome Message" if language == "en" else "Karşılama Mesajı",
            placeholder="Leave empty for default message" if language == "en" else "Varsayılan mesaj için boş bırakın",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            default=default_message,
            required=False
        )
        self.add_item(self.welcome_message)
        
        if not quick:
            # Background selection for full setup
            self.background = discord.ui.TextInput(
                label="Background" if language == "en" else "Arkaplan",
                placeholder="welcome_blue, welcome_red, welcome_green, etc." if language == "en" else "welcome_blue, welcome_red, welcome_green, vb.",
                style=discord.TextStyle.short,
                required=False
            )
            self.add_item(self.background)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse channel ID
            channel_input = self.channel_id.value.strip()
            
            if channel_input.startswith('<#') and channel_input.endswith('>'):
                channel_id = int(channel_input[2:-1])
            elif channel_input.startswith('#'):
                # Find by name
                channel_name = channel_input[1:]
                channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
                if not channel:
                    error_msg = "Channel not found" if self.language == "en" else "Kanal bulunamadı"
                    await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                    return
                channel_id = channel.id
            else:
                try:
                    channel_id = int(channel_input)
                except ValueError:
                    error_msg = "Invalid channel format" if self.language == "en" else "Geçersiz kanal formatı"
                    await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                    return
            
            # Verify channel exists and is text channel
            channel = interaction.guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                error_msg = "Invalid channel or not a text channel" if self.language == "en" else "Geçersiz kanal veya metin kanalı değil"
                await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                return
            
            # Handle language setting
            selected_language = self.language_setting.value.strip().lower() if self.language_setting.value else self.language
            if selected_language not in ["en", "tr"]:
                selected_language = self.language
            
            # Handle welcome message (use default if empty)
            welcome_message = self.welcome_message.value.strip() if self.welcome_message.value else ""
            if not welcome_message:
                welcome_message = "Welcome {user} to {server}! You are member #{count}" if selected_language == "en" else "Hoş geldin {user}! {server} sunucusuna hoş geldin! Sen {count}. üyesin!"
            
            # Prepare settings
            settings = {
                "guild_id": interaction.guild.id,
                "welcome_message": welcome_message,
                "channel_id": channel_id,
                "language": selected_language,
                "enabled": True
            }
            
            # Handle background selection if not quick setup
            if not self.quick and hasattr(self, 'background') and self.background.value:
                background = self.background.value.strip().lower()
                available_backgrounds = [
                    "welcome_blue", "welcome_red", "welcome_green", 
                    "welcome_purple", "welcome_light", "welcome_dark"
                ]
                
                if background in available_backgrounds:
                    settings["background"] = f"images/backgrounds/{background}.png"
                elif background.startswith(("http://", "https://")):
                    settings["background"] = background
                else:
                    settings["background"] = "images/backgrounds/welcome_blue.png"  # Default
            else:
                settings["background"] = "images/backgrounds/welcome_blue.png"  # Default
            
            # Save to database
            mongo_db = get_async_db()
            await mongo_db.welcomer.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": settings},
                upsert=True
            )
            
            # Show preview
            preview = welcome_message.replace("{user}", interaction.user.mention)
            preview = preview.replace("{server}", interaction.guild.name)  
            preview = preview.replace("{count}", str(interaction.guild.member_count))
            preview = preview.replace("{member_count}", str(interaction.guild.member_count))
            preview = preview.replace("{username}", interaction.user.name)
            
            embed = discord.Embed(
                title="✅ Welcome System Configured" if selected_language == "en" else "✅ Karşılama Sistemi Yapılandırıldı",
                description=f"Welcome messages will be sent to {channel.mention}" if selected_language == "en" else f"Karşılama mesajları {channel.mention} kanalına gönderilecek",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Preview" if selected_language == "en" else "Önizleme",
                value=preview,
                inline=False
            )
            
            embed.add_field(
                name="Language" if selected_language == "en" else "Dil",
                value="English" if selected_language == "en" else "Türkçe",
                inline=True
            )
            
            if not self.quick and hasattr(self, 'background') and self.background.value:
                embed.add_field(
                    name="Background" if selected_language == "en" else "Arkaplan",
                    value=settings.get("background", "default").replace("images/backgrounds/", "").replace(".png", ""),
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error configuring welcome system: {e}")
            error_msg = f"An error occurred: {str(e)}" if self.language == "en" else f"Bir hata oluştu: {str(e)}"
            await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)

class GoodbyeMessageModal(discord.ui.Modal):
    """Modal for configuring goodbye message settings"""
    def __init__(self, language="en"):
        title = "Goodbye Message Settings" if language == "en" else "Vedalaşma Mesajı Ayarları"
        super().__init__(title=title, timeout=300)
        self.language = language
        
        # Goodbye message
        self.goodbye_message = discord.ui.TextInput(
            label="Goodbye Message" if language == "en" else "Vedalaşma Mesajı",
            placeholder="Goodbye {user}, we'll miss you!" if language == "en" else "Güle güle {user}, seni özleyeceğiz!",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        self.add_item(self.goodbye_message)
        
        # Channel ID
        self.channel_id = discord.ui.TextInput(
            label="Channel ID" if language == "en" else "Kanal ID",
            placeholder="Enter channel ID or #channel-mention" if language == "en" else "Kanal ID'sini girin veya #kanal-etiket",
            style=discord.TextStyle.short,
            required=True
        )
        self.add_item(self.channel_id)
        
        # Background selection
        self.background = discord.ui.TextInput(
            label="Background" if language == "en" else "Arkaplan",
            placeholder="byebye_blue, byebye_red, byebye_green, etc." if language == "en" else "byebye_blue, byebye_red, byebye_green, vb.",
            style=discord.TextStyle.short,
            required=False
        )
        self.add_item(self.background)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse channel ID
            channel_input = self.channel_id.value.strip()
            
            if channel_input.startswith('<#') and channel_input.endswith('>'):
                channel_id = int(channel_input[2:-1])
            elif channel_input.startswith('#'):
                # Find by name
                channel_name = channel_input[1:]
                channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
                if not channel:
                    error_msg = "Channel not found" if self.language == "en" else "Kanal bulunamadı"
                    await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                    return
                channel_id = channel.id
            else:
                try:
                    channel_id = int(channel_input)
                except ValueError:
                    error_msg = "Invalid channel format" if self.language == "en" else "Geçersiz kanal formatı"
                    await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                    return
            
            # Verify channel exists and is text channel
            channel = interaction.guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                error_msg = "Invalid channel or not a text channel" if self.language == "en" else "Geçersiz kanal veya metin kanalı değil"
                await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                return
            
            # Prepare settings
            settings = {
                "guild_id": interaction.guild.id,
                "goodbye_message": self.goodbye_message.value,
                "channel_id": channel_id,
                "enabled": True
            }
            
            # Handle background selection
            if self.background.value:
                background = self.background.value.strip().lower()
                available_backgrounds = [
                    "byebye_blue", "byebye_red", "byebye_green", 
                    "byebye_purple", "byebye_light", "byebye_dark"
                ]
                
                if background in available_backgrounds:
                    settings["background"] = f"images/backgrounds/{background}.png"
                elif background.startswith(("http://", "https://")):
                    settings["background"] = background
                else:
                    settings["background"] = "images/backgrounds/byebye_blue.png"  # Default
            else:
                settings["background"] = "images/backgrounds/byebye_blue.png"  # Default
            
            # Save to database
            mongo_db = get_async_db()
            await mongo_db.byebye.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": settings},
                upsert=True
            )
            
            # Show preview
            preview = self.goodbye_message.value.replace("{user}", interaction.user.mention)
            preview = preview.replace("{server}", interaction.guild.name)
            preview = preview.replace("{count}", str(interaction.guild.member_count))
            
            embed = discord.Embed(
                title="✅ Goodbye System Configured" if self.language == "en" else "✅ Vedalaşma Sistemi Yapılandırıldı",
                description=f"Goodbye messages will be sent to {channel.mention}",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Preview" if self.language == "en" else "Önizleme",
                value=preview,
                inline=False
            )
            
            embed.add_field(
                name="Background" if self.language == "en" else "Arkaplan",
                value=settings["background"].replace("images/backgrounds/", "").replace(".png", ""),
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error configuring goodbye system: {e}")
            error_msg = f"An error occurred: {str(e)}" if self.language == "en" else f"Bir hata oluştu: {str(e)}"
            await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)

# Background Selection View for Welcome/Goodbye
class BackgroundSelectionView(discord.ui.View):
    """View for selecting background images from available options"""
    def __init__(self, bot, language="en", system_type="welcome"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        self.system_type = system_type  # "welcome" or "goodbye"
        
        # Add background selection dropdown
        self.add_item(BackgroundSelectDropdown(language, system_type))

class BackgroundSelectDropdown(discord.ui.Select):
    """Dropdown for selecting background images"""
    def __init__(self, language="en", system_type="welcome"):
        self.language = language
        self.system_type = system_type
        
        # Define available backgrounds
        if system_type == "welcome":
            backgrounds = [
                ("welcome_blue", "Blue Welcome Background"),
                ("welcome_red", "Red Welcome Background"),
                ("welcome_green", "Green Welcome Background"),
                ("welcome_purple", "Purple Welcome Background"),
                ("welcome_light", "Light Welcome Background"),
                ("welcome_dark", "Dark Welcome Background"),
            ]
        else:  # goodbye
            backgrounds = [
                ("byebye_blue", "Blue Goodbye Background"),
                ("byebye_red", "Red Goodbye Background"),
                ("byebye_green", "Green Goodbye Background"),
                ("byebye_purple", "Purple Goodbye Background"),
                ("byebye_light", "Light Goodbye Background"),
                ("byebye_dark", "Dark Goodbye Background"),
            ]
        
        # Create options
        options = []
        for bg_file, bg_name in backgrounds:
            options.append(discord.SelectOption(
                label=bg_name,
                value=bg_file,
                description=f"Use {bg_name.lower()}"
            ))
        
        placeholder = f"Choose {system_type} background..." if language == "en" else f"{system_type.title()} arkaplanı seçin..."
        
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            selected_background = self.values[0]
            background_path = f"images/backgrounds/{selected_background}.png"
            
            # Update database based on system type
            mongo_db = get_async_db()
            collection = "welcomer" if self.system_type == "welcome" else "byebye"
            
            await mongo_db[collection].update_one(
                {"guild_id": interaction.guild.id},
                {"$set": {"background": background_path}},
                upsert=True
            )
            
            success_msg = f"✅ {self.system_type.title()} background set to: {selected_background}" if self.language == "en" else f"✅ {self.system_type.title()} arkaplanı ayarlandı: {selected_background}"
            
            embed = discord.Embed(
                description=success_msg,
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error setting background: {e}")
            error_msg = f"An error occurred: {str(e)}" if self.language == "en" else f"Bir hata oluştu: {str(e)}"
            await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)

class LevellingSettingsView(discord.ui.View):
    """Levelling system settings view"""
    
    def __init__(self, bot, interaction):
        super().__init__(timeout=300)
        self.bot = bot
        self.interaction = interaction
        self.levelling_cog = bot.get_cog('Levelling')
        
    @discord.ui.button(label="🎯 Sistemi Aç/Kapat", style=discord.ButtonStyle.primary, row=0)
    async def toggle_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle the levelling system on/off"""
        try:
            if not self.levelling_cog:
                await interaction.response.send_message("❌ Levelling cog bulunamadı.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🎯 Seviye Sistemi Durumu",
                description="Seviye sistemi başarıyla güncellendi.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error toggling levelling system: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)

    @discord.ui.button(label="💬 Mesaj XP Ayarları", style=discord.ButtonStyle.secondary, row=0)
    async def message_xp_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure message XP settings"""
        try:
            embed = discord.Embed(
                title="💬 Mesaj XP Ayarları",
                description="Mesaj başına verilecek XP miktarını ayarlayın.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Mevcut Ayarlar",
                value="Mesaj XP: 5-15 arası rastgele",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing message XP settings: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)

    @discord.ui.button(label="🎤 Sesli Kanal XP", style=discord.ButtonStyle.secondary, row=0)
    async def voice_xp_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure voice channel XP settings"""
        try:
            embed = discord.Embed(
                title="🎤 Sesli Kanal XP Ayarları",
                description="Sesli kanallarda verilecek XP ayarlarını yapılandırın.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Mevcut Ayarlar",
                value="Dakika başına XP: 2-5 arası",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing voice XP settings: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)    @discord.ui.button(label="🔔 Bildirim Ayarları", style=discord.ButtonStyle.secondary, row=1)
    async def notification_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure level up notification settings"""
        try:
            from utils.settings.notification_views import LevelNotificationSettingsView
            view = LevelNotificationSettingsView(self.bot, interaction.guild.id)
            
            embed = discord.Embed(
                title="🔔 Seviye Atlama Bildirimleri",
                description="Seviye atlama bildirimlerini kapsamlı şekilde yapılandırın.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Yapılandırılabilir Özellikler",
                value=(
                    "🔘 Bildirimleri açma/kapama\n"
                    "📍 Bildirim kanalı seçimi\n"
                    "✨ Bildirim mesajı özelleştirme\n"
                    "🎨 Embed renk ayarları\n"
                    "👑 Özel seviye mesajları\n"
                    "📊 Bildirim formatı seçenekleri"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing notification settings: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)

    @discord.ui.button(label="👑 Seviye Rolleri", style=discord.ButtonStyle.secondary, row=1)
    async def level_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure level roles"""
        try:
            from utils.settings.level_roles_view import LevelRolesManagementView
            view = LevelRolesManagementView(self.bot, interaction.guild.id)
            
            embed = await view.create_level_roles_embed()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing level roles: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)

    @discord.ui.button(label="📊 Mevcut Ayarlar", style=discord.ButtonStyle.success, row=1)
    async def current_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show current levelling settings"""
        try:
            embed = discord.Embed(
                title="📊 Mevcut Seviye Sistemi Ayarları",
                description="Şu anki seviye sistemi ayarlarınız:",
                color=discord.Color.green()
            )
            
            # Add current settings (placeholder values)
            embed.add_field(
                name="🎯 Sistem Durumu",
                value="✅ Aktif",
                inline=True
            )
            embed.add_field(
                name="💬 Mesaj XP",
                value="5-15 arası rastgele",
                inline=True
            )
            embed.add_field(
                name="🎤 Sesli Kanal XP",
                value="2-5/dakika",
                inline=True
            )
            embed.add_field(
                name="🔔 Bildirimler",
                value="✅ Aktif",
                inline=True
            )
            embed.add_field(
                name="📍 Bildirim Kanalı",
                value="Aynı kanal",
                inline=True
            )
            embed.add_field(
                name="👑 Seviye Rolleri",
                value="0 rol tanımlı",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing current settings: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)

class TempChannelsSettingsView(discord.ui.View):
    """Temporary channels settings view"""
    
    def __init__(self, bot, temp_manager=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.temp_manager = temp_manager
        
    @discord.ui.button(label="🎮 Kurulum", style=discord.ButtonStyle.primary, row=0)
    async def setup_temp_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Setup temporary voice channels"""
        try:
            embed = discord.Embed(
                title="🎮 Geçici Kanal Kurulumu",
                description="Geçici sesli kanallar için ana kanal oluşturun.",
                color=discord.Color.purple()
            )
            embed.add_field(
                name="Kurulum Adımları",
                value="1. Ana kanal kategorisi seçin\n2. Tetikleyici kanalı oluşturun\n3. Kanal adı formatını belirleyin",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in temp channels setup: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)
            
    @discord.ui.button(label="⚙️ Ayarlar", style=discord.ButtonStyle.secondary, row=0)
    async def temp_channels_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure temporary channels settings"""
        try:
            embed = discord.Embed(
                title="⚙️ Geçici Kanal Ayarları",
                description="Geçici kanal sisteminin davranışını özelleştirin.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Yapılandırma Seçenekleri",
                value="• Kanal adı formatı\n• Oyun emoji ayarları\n• Otomatik silme zamanı\n• Kullanıcı limitleri",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in temp channels config: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)

class BotSettingsMenuView(discord.ui.View):
    """Bot settings menu view"""
    
    def __init__(self, bot, ctx):
        super().__init__(timeout=300)
        self.bot = bot
        self.ctx = ctx
        
    @discord.ui.button(label="📝 Prefix Ayarları", style=discord.ButtonStyle.primary, row=0)
    async def prefix_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure bot prefix"""
        try:
            embed = discord.Embed(
                title="📝 Bot Prefix Ayarları",
                description="Bot'un komut önekini değiştirin.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Mevcut Prefix",
                value="`>>`",
                inline=False
            )
            embed.add_field(
                name="Nasıl Değiştirilir",
                value="`>>prefix <yeni_prefix>` komutunu kullanın",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in prefix settings: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)
            
    @discord.ui.button(label="🖼️ Bot Görünümü", style=discord.ButtonStyle.secondary, row=0)
    async def bot_appearance(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure bot appearance"""
        try:
            embed = discord.Embed(
                title="🖼️ Bot Görünüm Ayarları",
                description="Bot'un adını ve avatarını özelleştirin.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="⚠️ Önemli Not",
                value="Bu ayarlar sadece bot sahibi tarafından değiştirilebilir.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in bot appearance: {e}")
            await interaction.response.send_message("❌ Bir hata oluştu.", ephemeral=True)

class FullWelcomeSetupModal(discord.ui.Modal):
    """Comprehensive modal for full welcome system setup"""
    def __init__(self, language="en"):
        title = "Full Welcome System Setup" if language == "en" else "Tam Karşılama Sistemi Kurulumu"
        super().__init__(title=title, timeout=300)
        self.language = language
        
        # Channel ID (most important)
        self.channel_id = discord.ui.TextInput(
            label="Channel ID" if language == "en" else "Kanal ID",
            placeholder="Enter channel ID or #channel-mention" if language == "en" else "Kanal ID'sini girin veya #kanal-bahset",
            required=True,
            max_length=100
        )
        
        # Language Selection
        self.language_setting = discord.ui.TextInput(
            label="Language (en/tr)" if language == "en" else "Dil (en/tr)",
            placeholder="en for English, tr for Turkish" if language == "en" else "İngilizce için en, Türkçe için tr",
            default=language,
            required=False,
            max_length=2
        )
        
        # Welcome Message
        default_message = "Welcome {user} to {server}! You are member #{count}" if language == "en" else "Hoş geldin {user}! {server} sunucusuna hoş geldin! Sen {count}. üyesin!"
        self.welcome_message = discord.ui.TextInput(
            label="Welcome Message" if language == "en" else "Karşılama Mesajı",
            placeholder="Use {user}, {server}, {count} variables" if language == "en" else "{user}, {server}, {count} değişkenlerini kullanın",
            style=discord.TextStyle.paragraph,
            default=default_message,
            required=False,
            max_length=1000
        )
        
        # Background Selection
        self.background = discord.ui.TextInput(
            label="Background Theme" if language == "en" else "Arkaplan Teması",
            placeholder="welcome_blue, welcome_red, welcome_green, welcome_purple, welcome_light, welcome_dark" if language == "en" else "welcome_blue, welcome_red, welcome_green, welcome_purple, welcome_light, welcome_dark",
            default="welcome_blue",
            required=False,
            max_length=50
        )
        
        # Text Color
        self.text_color = discord.ui.TextInput(
            label="Text Color (hex)" if language == "en" else "Yazı Rengi (hex)",
            placeholder="#FFFFFF for white, #000000 for black" if language == "en" else "Beyaz için #FFFFFF, siyah için #000000",
            default="#FFFFFF",
            required=False,
            max_length=7
        )
        
        # Add items to modal
        self.add_item(self.channel_id)
        self.add_item(self.language_setting)
        self.add_item(self.welcome_message)
        self.add_item(self.background)
        self.add_item(self.text_color)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse channel ID
            channel_input = self.channel_id.value.strip()
            
            if channel_input.startswith('<#') and channel_input.endswith('>'):
                channel_id = int(channel_input[2:-1])
            elif channel_input.startswith('#'):
                # Find by name
                channel_name = channel_input[1:]
                channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
                if not channel:
                    error_msg = "Channel not found" if self.language == "en" else "Kanal bulunamadı"
                    await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                    return
                channel_id = channel.id
            else:
                try:
                    channel_id = int(channel_input)
                except ValueError:
                    error_msg = "Invalid channel ID" if self.language == "en" else "Geçersiz kanal ID"
                    await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                    return
            
            # Verify channel exists
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                error_msg = "Channel not found" if self.language == "en" else "Kanal bulunamadı"
                await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                return
            
            # Get selected language
            selected_language = self.language_setting.value.strip().lower() if self.language_setting.value else self.language
            if selected_language not in ["en", "tr"]:
                selected_language = self.language
            
            # Handle welcome message (use default if empty)
            welcome_message = self.welcome_message.value.strip() if self.welcome_message.value else ""
            if not welcome_message:
                welcome_message = "Welcome {user} to {server}! You are member #{count}" if selected_language == "en" else "Hoş geldin {user}! {server} sunucusuna hoş geldin! Sen {count}. üyesin!"
            
            # Handle background selection
            background = self.background.value.strip().lower() if self.background.value else "welcome_blue"
            available_backgrounds = [
                "welcome_blue", "welcome_red", "welcome_green", 
                "welcome_purple", "welcome_light", "welcome_dark"
            ]
            
            if background not in available_backgrounds:
                background = "welcome_blue"  # Default
            
            # Handle text color
            text_color = self.text_color.value.strip() if self.text_color.value else "#FFFFFF"
            if not text_color.startswith('#'):
                text_color = "#FFFFFF"
            
            # Prepare comprehensive settings
            settings = {
                "guild_id": interaction.guild.id,
                "welcome_message": welcome_message,
                "channel_id": channel_id,
                "language": selected_language,
                "enabled": True,
                "background": f"images/backgrounds/{background}.png",
                "background_theme": background,
                "text_color": text_color,
                "outline_color": "#000000",
                "text_outline": True,
                "shadow": True,
                "welcome_font_size": 100,
                "member_font_size": 42,
                "welcome_y": 295,
                "member_y": 390,
                "avatar_y": 50,
                "avatar_size": 215
            }
            
            # Save to database
            mongo_db = get_async_db()
            await mongo_db.welcomer.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": settings},
                upsert=True
            )
            
            # Show preview
            preview = welcome_message.replace("{user}", interaction.user.mention)
            preview = preview.replace("{server}", interaction.guild.name)  
            preview = preview.replace("{count}", str(interaction.guild.member_count))
            preview = preview.replace("{member_count}", str(interaction.guild.member_count))
            preview = preview.replace("{username}", interaction.user.name)
            
            embed = discord.Embed(
                title="✅ Full Welcome System Configured" if selected_language == "en" else "✅ Tam Karşılama Sistemi Yapılandırıldı",
                description=f"Welcome system fully configured with image generation enabled!" if selected_language == "en" else f"Karşılama sistemi görsel oluşturma ile tam olarak yapılandırıldı!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📍 Channel" if selected_language == "en" else "📍 Kanal",
                value=channel.mention,
                inline=True
            )
            
            embed.add_field(
                name="🎨 Background" if selected_language == "en" else "🎨 Arkaplan",
                value=background.replace("welcome_", "").title(),
                inline=True
            )
            
            embed.add_field(
                name="🎨 Text Color" if selected_language == "en" else "🎨 Yazı Rengi",
                value=text_color,
                inline=True
            )
            
            embed.add_field(
                name="Preview" if selected_language == "en" else "Önizleme",
                value=preview,
                inline=False
            )
            
            embed.add_field(
                name="🖼️ Features Enabled" if selected_language == "en" else "🖼️ Etkin Özellikler",
                value=(
                    "• Image Generation ✅\n"
                    "• Custom Background ✅\n"
                    "• Text Styling ✅\n"
                    "• Variable Support ✅"
                ) if selected_language == "en" else (
                    "• Görsel Oluşturma ✅\n"
                    "• Özel Arkaplan ✅\n"
                    "• Yazı Stilleri ✅\n"
                    "• Değişken Desteği ✅"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in full welcome setup: {e}")
            error_language = getattr(self, 'language_setting', None)
            if error_language and error_language.value:
                error_language = error_language.value.strip().lower()
                if error_language not in ["en", "tr"]:
                    error_language = self.language
            else:
                error_language = self.language
            
            error_msg = f"An error occurred: {str(e)}" if error_language == "en" else f"Bir hata oluştu: {str(e)}"
            await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)

class FullGoodbyeSetupModal(discord.ui.Modal):
    """Comprehensive modal for full goodbye system setup"""
    def __init__(self, language="en"):
        title = "Full Goodbye System Setup" if language == "en" else "Tam Veda Sistemi Kurulumu"
        super().__init__(title=title, timeout=300)
        self.language = language
        
        # Channel ID (most important)
        self.channel_id = discord.ui.TextInput(
            label="Channel ID" if language == "en" else "Kanal ID",
            placeholder="Enter channel ID or #channel-mention" if language == "en" else "Kanal ID'sini girin veya #kanal-bahset",
            required=True,
            max_length=100
        )
        
        # Language Selection
        self.language_setting = discord.ui.TextInput(
            label="Language (en/tr)" if language == "en" else "Dil (en/tr)",
            placeholder="en for English, tr for Turkish" if language == "en" else "İngilizce için en, Türkçe için tr",
            default=language,
            required=False,
            max_length=2
        )
        
        # Goodbye Message
        default_message = "Goodbye {user}, thanks for being part of {server}!" if language == "en" else "Hoşçakal {user}! {server} sunucusunun bir parçası olduğun için teşekkürler!"
        self.goodbye_message = discord.ui.TextInput(
            label="Goodbye Message" if language == "en" else "Veda Mesajı",
            placeholder="Use {user}, {server}, {count} variables" if language == "en" else "{user}, {server}, {count} değişkenlerini kullanın",
            style=discord.TextStyle.paragraph,
            default=default_message,
            required=False,
            max_length=1000
        )
        
        # Background Selection
        self.background = discord.ui.TextInput(
            label="Background Theme" if language == "en" else "Arkaplan Teması",
            placeholder="goodbye_blue, goodbye_red, goodbye_green, goodbye_purple, goodbye_light, goodbye_dark" if language == "en" else "goodbye_blue, goodbye_red, goodbye_green, goodbye_purple, goodbye_light, goodbye_dark",
            default="goodbye_blue",
            required=False,
            max_length=50
        )
        
        # Text Color
        self.text_color = discord.ui.TextInput(
            label="Text Color (hex)" if language == "en" else "Yazı Rengi (hex)",
            placeholder="#FFFFFF for white, #000000 for black" if language == "en" else "Beyaz için #FFFFFF, siyah için #000000",
            default="#FFFFFF",
            required=False,
            max_length=7
        )
        
        # Add items to modal
        self.add_item(self.channel_id)
        self.add_item(self.language_setting)
        self.add_item(self.goodbye_message)
        self.add_item(self.background)
        self.add_item(self.text_color)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse channel ID
            channel_input = self.channel_id.value.strip()
            
            if channel_input.startswith('<#') and channel_input.endswith('>'):
                channel_id = int(channel_input[2:-1])
            elif channel_input.startswith('#'):
                # Find by name
                channel_name = channel_input[1:]
                channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
                if not channel:
                    error_msg = "Channel not found" if self.language == "en" else "Kanal bulunamadı"
                    await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                    return
                channel_id = channel.id
            else:
                try:
                    channel_id = int(channel_input)
                except ValueError:
                    error_msg = "Invalid channel ID" if self.language == "en" else "Geçersiz kanal ID"
                    await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                    return
            
            # Verify channel exists
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                error_msg = "Channel not found" if self.language == "en" else "Kanal bulunamadı"
                await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)
                return
            
            # Get selected language
            selected_language = self.language_setting.value.strip().lower() if self.language_setting.value else self.language
            if selected_language not in ["en", "tr"]:
                selected_language = self.language
            
            # Handle goodbye message (use default if empty)
            goodbye_message = self.goodbye_message.value.strip() if self.goodbye_message.value else ""
            if not goodbye_message:
                goodbye_message = "Goodbye {user}, thanks for being part of {server}!" if selected_language == "en" else "Hoşçakal {user}! {server} sunucusunun bir parçası olduğun için teşekkürler!"
            
            # Handle background selection
            background = self.background.value.strip().lower() if self.background.value else "goodbye_blue"
            available_backgrounds = [
                "goodbye_blue", "goodbye_red", "goodbye_green", 
                "goodbye_purple", "goodbye_light", "goodbye_dark"
            ]
            
            if background not in available_backgrounds:
                background = "goodbye_blue"  # Default
            
            # Handle text color
            text_color = self.text_color.value.strip() if self.text_color.value else "#FFFFFF"
            if not text_color.startswith('#'):
                text_color = "#FFFFFF"
            
            # Prepare comprehensive settings
            settings = {
                "guild_id": interaction.guild.id,
                "goodbye_message": goodbye_message,
                "channel_id": channel_id,
                "language": selected_language,
                "enabled": True,
                "background": f"images/backgrounds/{background}.png",
                "background_theme": background,
                "text_color": text_color,
                "outline_color": "#000000",
                "text_outline": True,
                "shadow": True,
                "goodbye_font_size": 100,
                "member_font_size": 42,
                "goodbye_y": 295,
                "member_y": 390,
                "avatar_y": 50,
                "avatar_size": 215
            }
            
            # Save to database
            mongo_db = get_async_db()
            await mongo_db.byebye.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": settings},
                upsert=True
            )
            
            # Show preview
            preview = goodbye_message.replace("{user}", interaction.user.mention)
            preview = preview.replace("{server}", interaction.guild.name)  
            preview = preview.replace("{count}", str(interaction.guild.member_count))
            preview = preview.replace("{member_count}", str(interaction.guild.member_count))
            preview = preview.replace("{username}", interaction.user.name)
            
            embed = discord.Embed(
                title="✅ Full Goodbye System Configured" if selected_language == "en" else "✅ Tam Veda Sistemi Yapılandırıldı",
                description=f"Goodbye system fully configured with image generation enabled!" if selected_language == "en" else f"Veda sistemi görsel oluşturma ile tam olarak yapılandırıldı!",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="📍 Channel" if selected_language == "en" else "📍 Kanal",
                value=channel.mention,
                inline=True
            )
            
            embed.add_field(
                name="🎨 Background" if selected_language == "en" else "🎨 Arkaplan",
                value=background.replace("goodbye_", "").title(),
                inline=True
            )
            
            embed.add_field(
                name="🎨 Text Color" if selected_language == "en" else "🎨 Yazı Rengi",
                value=text_color,
                inline=True
            )
            
            embed.add_field(
                name="Preview" if selected_language == "en" else "Önizleme",
                value=preview,
                inline=False
            )
            
            embed.add_field(
                name="🖼️ Features Enabled" if selected_language == "en" else "🖼️ Etkin Özellikler",
                value=(
                    "• Image Generation ✅\n"
                    "• Custom Background ✅\n"
                    "• Text Styling ✅\n"
                    "• Variable Support ✅"
                ) if selected_language == "en" else (
                    "• Görsel Oluşturma ✅\n"
                    "• Özel Arkaplan ✅\n"
                    "• Yazı Stilleri ✅\n"
                    "• Değişken Desteği ✅"
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in full goodbye setup: {e}")
            error_language = getattr(self, 'language_setting', None)
            if error_language and error_language.value:
                error_language = error_language.value.strip().lower()
                if error_language not in ["en", "tr"]:
                    error_language = self.language
            else:
                error_language = self.language
            
            error_msg = f"An error occurred: {str(e)}" if error_language == "en" else f"Bir hata oluştu: {str(e)}"
            await interaction.response.send_message(embed=create_embed(error_msg, discord.Color.red()), ephemeral=True)