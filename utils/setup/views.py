import discord
from discord import ui
import asyncio
import json
import logging
from utils.content_loader import load_content
from utils import create_embed
from .templates import get_builtin_template

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
        
        if language == "tr":
            embed = discord.Embed(
                title="🛠️ Kapsamlı Sunucu Kurulum Paneli",
                description="Tüm sunucu yönetim araçlarına tek noktadan erişin:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Mevcut Seçenekler",
                value=(
                    "🏗️ **Sunucu Yapısı** - Template'lerle otomatik kurulum\n"
                    "📝 **İçerik Yönetimi** - Kurallar, duyurular, embed'ler\n"
                    "🤖 **Bot Entegrasyonu** - Toplu bot ekleme\n"
                    "🎨 **Özelleştirme** - Roller, izinler, emoji stili\n"
                    "📊 **Analiz & Bakım** - İstatistikler, açıklama güncelleme\n"
                    "💾 **Template Yönetimi** - Kaydet, yükle, paylaş\n"
                    "🏢 **İş Komutları** - Bionluk komutları entegrasyonu"
                ),
                inline=False
            )
        else:
            embed = discord.Embed(
                title="🛠️ Comprehensive Server Setup Panel",
                description="Access all server management tools from one place:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Available Options",
                value=(
                    "🏗️ **Server Structure** - Automatic setup with templates\n"
                    "📝 **Content Management** - Rules, announcements, embeds\n"
                    "🤖 **Bot Integration** - Mass bot addition\n"
                    "🎨 **Customization** - Roles, permissions, emoji styles\n"
                    "📊 **Analytics & Maintenance** - Statistics, description updates\n"
                    "💾 **Template Management** - Save, load, share\n"
                    "🏢 **Business Commands** - Bionluk commands integration"
                ),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=MainSetupView(self.bot, language), ephemeral=True)

class MainSetupView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🏗️ Sunucu Yapısı", style=discord.ButtonStyle.primary)
    async def server_structure(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "🏗️ Server Structure"
            message = "Choose template source:"
        else:
            message = "Template kaynağını seçin:"
        
        await interaction.response.send_message(message, view=TemplateSourceView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="📝 İçerik Yönetimi", style=discord.ButtonStyle.secondary)
    async def content_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "📝 Content Management"
            message = "Select content type:"
        else:
            message = "İçerik türünü seçin:"
        
        await interaction.response.send_message(message, view=ContentManagementView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="🤖 Bot Entegrasyonu", style=discord.ButtonStyle.secondary)
    async def bot_integration(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "🤖 Bot Integration"
        
        await interaction.response.send_modal(BotManagementModal(self.bot, self.language))

    @discord.ui.button(label="🏢 İş Komutları", style=discord.ButtonStyle.success)
    async def business_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "🏢 Business Commands"
            message = "Select business command:"
        else:
            message = "İş komutunu seçin:"
        
        await interaction.response.send_message(message, view=BusinessCommandsView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="🎨 Özelleştirme", style=discord.ButtonStyle.secondary)
    async def customization(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "🎨 Customization"
            message = "Customization options:"
        else:
            message = "Özelleştirme seçenekleri:"
        
        await interaction.response.send_message(message, view=CustomizationView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="📊 Analiz & Bakım", style=discord.ButtonStyle.success)
    async def analytics(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "📊 Analytics & Maintenance"
            message = "Analytics and maintenance tools:"
        else:
            message = "Analiz ve bakım araçları:"
        
        await interaction.response.send_message(message, view=AnalyticsView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="💾 Template Yönetimi", style=discord.ButtonStyle.success)
    async def template_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "💾 Template Management"
            message = "Template management:"
        else:
            message = "Template yönetimi:"
        
        await interaction.response.send_message(message, view=TemplateManagementView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="⚙️ Gelişmiş Ayarlar", style=discord.ButtonStyle.danger)
    async def advanced_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "⚙️ Advanced Settings"
            message = "Advanced settings:"
        else:
            message = "Gelişmiş ayarlar:"
        
        await interaction.response.send_message(message, view=AdvancedSettingsView(self.bot, self.language), ephemeral=True)

class BusinessCommandsView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="📝 Bionluk Paket", style=discord.ButtonStyle.primary, emoji="📦")
    async def bionluk_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bionluk için özel mesajları gönderir"""
        await interaction.response.defer(ephemeral=True)
        
        cog = self.bot.get_cog('ServerSetup')
        format_mentions = cog.get_format_mentions(interaction.guild)
        
        view = ui.View()
        view.add_item(ui.Button(label="Önemli Bot Komutları", url="https://medium.com/@bergaman9/%C3%B6nemli-discord-komutlar%C4%B1-3a4598cde13a", style=discord.ButtonStyle.link, emoji="🔗"))
        
        view2 = ui.View()
        view2.add_item(ui.Button(label="Discord Bot Özellikleri", url="https://medium.com/@bergaman9/2023-y%C4%B1l%C4%B1nda-sunucunuzda-olmas%C4%B1-gereken-discord-botlar%C4%B1-e895de2052dc", style=discord.ButtonStyle.link, emoji="🔗"))
        
        # İçerikleri yükle
        komutlar_content = load_content("commands")
        komutlar_parts = komutlar_content.split("## Üye Komutları")
        komutlar_text = komutlar_parts[0].strip() if len(komutlar_parts) > 0 else komutlar_content
        
        botlar_text = load_content("bots")
        roller_text = load_content("roles")
        kanallar_text = load_content("channels")
        sunucu_hizmetleri_text = load_content("services")
        server_content = load_content("server")
        server_parts = server_content.split("## Sunucu Özellikleri - Sayfa 2")
        
        # Embed'leri oluştur
        komutlar_embed = discord.Embed(title="DİSCORD KOMUTLARI", description=komutlar_text, color=0xfad100)
        botlar_embed = discord.Embed(title="BOT ÖZELLİKLERİ", description=botlar_text, color=0x00e9b4)
        roller_embed = discord.Embed(title="SUNUCU ROLLERİ", description=roller_text.format(**format_mentions), color=0xff1f1f)
        kanallar_embed = discord.Embed(title="SUNUCU KANALLARI", description=kanallar_text.format(**format_mentions), color=0x00e9b4)
        
        sunucu_hizmetleri_embed = discord.Embed(title="BERGAMAN SUNUCU HİZMETLERİ", description=sunucu_hizmetleri_text, color=0xffffff)
        sunucu_hizmetleri_embed.set_thumbnail(url="https://i.imgur.com/fntLhGX.png")
        
        sunucu_text_page = server_parts[0].strip() if len(server_parts) > 0 else server_content
        sunucu_embed = discord.Embed(title="SUNUCU ÖZELLİKLERİ", description=sunucu_text_page.format(**format_mentions), color=0xf47fff)
        sunucu_embed.set_footer(text="Sayfa 1/2")
        sunucu_embed.set_thumbnail(url=interaction.guild.icon.url)
        
        sunucu_text_page2 = server_content.split("## Sunucu Özellikleri - Sayfa 2")[1].strip() if "## Sunucu Özellikleri - Sayfa 2" in server_content else ""
        sunucu_embed2 = discord.Embed(title="SUNUCU ÖZELLİKLERİ", description=sunucu_text_page2.format(**format_mentions), color=0xf47fff)
        sunucu_embed2.set_footer(text="Sayfa 2/2")
        sunucu_embed2.set_thumbnail(url=interaction.guild.icon.url)
        
        await interaction.followup.send(embed=create_embed(description="Bionluk mesajları gönderiliyor...", color=discord.Color.green()), ephemeral=True)
        
        # Mesajları sırayla gönder
        await interaction.channel.send(embed=sunucu_embed)
        await interaction.channel.send(embed=sunucu_embed2)
        await interaction.channel.send(embed=komutlar_embed, view=view)
        await interaction.channel.send(embed=botlar_embed, view=view2)
        await interaction.channel.send(embed=roller_embed)
        await interaction.channel.send(embed=kanallar_embed)
        await interaction.channel.send(embed=sunucu_hizmetleri_embed)

    @discord.ui.button(label="📢 Duyuru Paketi", style=discord.ButtonStyle.secondary, emoji="📣")
    async def announcement_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Duyuru mesajlarını gönderir"""
        await interaction.response.defer(ephemeral=True)
        
        cog = self.bot.get_cog('ServerSetup')
        format_mentions = cog.get_format_mentions(interaction.guild)
        
        roller_embed = discord.Embed(
            title="SUNUCU ROLLERİ",
            description=load_content("roles").format(**format_mentions),
            color=0xff1f1f
        )
        
        commands_content = load_content("commands")
        uye_komutlar_text = "## Üye Komutları" + commands_content.split("## Üye Komutları")[1] if "## Üye Komutları" in commands_content else ""
        komutlar_embed = discord.Embed(
            title="ÜYELER İÇİN DİSCORD KOMUTLARI",
            description=uye_komutlar_text,
            color=0x00e9b4
        )
        
        duyurular_embed = discord.Embed(
            title="SUNUCU DUYURULARI",
            description=load_content("announcements").format(**format_mentions),
            color=0xff1f1f
        )
        
        await interaction.followup.send(embed=create_embed(description="Duyuru mesajları gönderiliyor...", color=discord.Color.green()), ephemeral=True)
        await interaction.channel.send(embed=duyurular_embed)
        await interaction.channel.send(embed=roller_embed)
        await interaction.channel.send(embed=komutlar_embed)

    @discord.ui.button(label="📜 Kurallar Paketi", style=discord.ButtonStyle.secondary, emoji="⚖️")
    async def rules_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Kurallar mesajlarını gönderir"""
        await interaction.response.defer(ephemeral=True)
        
        cog = self.bot.get_cog('ServerSetup')
        format_mentions = cog.get_format_mentions(interaction.guild)
        
        kurallar_embed = discord.Embed(
            title="SUNUCU KURALLARI",
            description=load_content("rules", 0).format(**format_mentions),
            color=0xff1f1f
        )
        
        destek_embed = discord.Embed(
            title="DESTEK",
            description=load_content("rules", 1).format(**format_mentions),
            color=0xff1f1f
        )
        
        invite_link = await cog.create_invite(interaction.guild)
        
        await interaction.followup.send(
            embed=create_embed(description="Kurallar mesajları gönderiliyor...", color=discord.Color.green()),
            ephemeral=True
        )
        await interaction.channel.send(embed=kurallar_embed)
        await interaction.channel.send(embed=destek_embed)
        await interaction.channel.send(invite_link)

class TemplateSourceView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="📋 Dahili Şablonlar", style=discord.ButtonStyle.primary)
    async def builtin_templates(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "📋 Built-in Templates"
            message = "Select server template:"
        else:
            message = "Sunucu şablonunu seçin:"
        
        await interaction.response.send_message(message, view=BuiltinTemplateSelectView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="📥 Discord Template İçe Aktar", style=discord.ButtonStyle.secondary)
    async def import_discord_template(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "📥 Import Discord Template"
        
        await interaction.response.send_modal(DiscordTemplateImportModal(self.bot, self.language))

    @discord.ui.button(label="💾 Kayıtlı Şablonlar", style=discord.ButtonStyle.secondary)
    async def saved_templates(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "💾 Saved Templates"
        
        cog = self.bot.get_cog('ServerSetup')
        templates = cog.get_available_templates()
        
        if not templates:
            msg = "Kayıtlı şablon bulunamadı." if self.language == "tr" else "No saved templates found."
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message("Kayıtlı şablonlar:", view=SavedTemplateSelectView(self.bot, self.language, templates), ephemeral=True)

class BuiltinTemplateSelectView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.select(
        placeholder="Şablon seçin... / Select template...",
        options=[
            discord.SelectOption(label="🏠 Varsayılan / Default", value="default", description="Genel amaçlı sunucu / General purpose server"),
            discord.SelectOption(label="🎮 Oyun / Gaming", value="gaming", description="Oyun sunucusu / Gaming server"),
            discord.SelectOption(label="👥 Topluluk / Community", value="community", description="Sosyal topluluk / Social community"),
            discord.SelectOption(label="💼 İş / Business", value="business", description="Profesyonel ortam / Professional environment"),
            discord.SelectOption(label="🎓 Eğitim / Educational", value="educational", description="Eğitim kurumu / Educational institution"),
            discord.SelectOption(label="📺 Yayın / Streaming", value="streaming", description="Yayıncı sunucusu / Streaming server"),
            discord.SelectOption(label="🎭 Roleplay", value="roleplay", description="Rol yapma / Role playing")
        ]
    )
    async def template_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        template = select.values[0]
        
        if self.language == "tr":
            message = "Şimdi emoji stilini ve kategori başlık stilini seçin:"
        else:
            message = "Now select emoji style and category header style:"
        
        await interaction.response.send_message(message, view=StyleSelectView(self.bot, self.language, template), ephemeral=True)

class StyleSelectView(discord.ui.View):
    def __init__(self, bot, language="tr", template="default"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        self.template = template
        self.emoji_style = "modern"
        self.header_style = "classic"

    @discord.ui.select(
        placeholder="Emoji stilini seçin... / Select emoji style...",
        options=[
            discord.SelectOption(label="Modern", value="modern", emoji="📋", description="Modern emojiler / Modern emojis"),
            discord.SelectOption(label="Renkli / Colorful", value="colorful", emoji="🌈", description="Renkli emojiler / Colorful emojis"),
            discord.SelectOption(label="Oyun / Gaming", value="gaming", emoji="🎮", description="Oyun emojileri / Gaming emojis"),
            discord.SelectOption(label="Minimal", value="minimal", emoji="•", description="Minimal görünüm / Minimal appearance"),
            discord.SelectOption(label="İş / Business", value="business", emoji="💼", description="İş emojileri / Business emojis")
        ]
    )
    async def emoji_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.emoji_style = select.values[0]
        
        if self.language == "tr":
            await interaction.response.send_message(f"✅ Emoji stili: **{select.values[0]}** - Şimdi başlık stilini seçin:", view=HeaderSelectView(self.bot, self.language, self.template, self.emoji_style), ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ Emoji style: **{select.values[0]}** - Now select header style:", view=HeaderSelectView(self.bot, self.language, self.template, self.emoji_style), ephemeral=True)

class HeaderSelectView(discord.ui.View):
    def __init__(self, bot, language="tr", template="default", emoji_style="modern"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        self.template = template
        self.emoji_style = emoji_style

    @discord.ui.select(
        placeholder="Başlık stilini seçin... / Select header style...",
        options=[
            discord.SelectOption(label="Klasik / Classic", value="classic", emoji="📜", description="┌─── BAŞLIK ───┐"),
            discord.SelectOption(label="Modern", value="modern", emoji="🎨", description="╭─ BAŞLIK ─╮"),
            discord.SelectOption(label="Zarif / Elegant", value="elegant", emoji="✨", description="◤ BAŞLIK ◥"),
            discord.SelectOption(label="Basit / Simple", value="simple", emoji="📝", description="[ BAŞLIK ]"),
            discord.SelectOption(label="Oyun / Gaming", value="gaming", emoji="🎮", description="▸ BAŞLIK ◂"),
            discord.SelectOption(label="Minimal", value="minimal", emoji="⚪", description="BAŞLIK"),
            discord.SelectOption(label="Ok / Arrows", value="arrows", emoji="➤", description="➤ BAŞLIK ◄"),
            discord.SelectOption(label="Yıldız / Stars", value="stars", emoji="✦", description="✦ BAŞLIK ✦")
        ]
    )
    async def header_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        header_style = select.values[0]
        
        # Onay mesajı
        if self.language == "tr":
            template_names = {
                "default": "Varsayılan", "gaming": "Oyun", "community": "Topluluk", 
                "business": "İş", "educational": "Eğitim", "streaming": "Yayın", "roleplay": "Roleplay"
            }
            embed = discord.Embed(
                title="⚠️ Onay Gerekli",
                description=f"**{template_names.get(self.template, self.template)}** şablonunu aşağıdaki ayarlarla uygulamak istediğinizden emin misiniz?\n\n"
                           f"🎨 **Emoji Stili:** {self.emoji_style}\n"
                           f"📋 **Başlık Stili:** {header_style}\n\n"
                           "⚠️ **DİKKAT:** Bu işlem mevcut tüm kanalları silecek ve yeni yapıyı oluşturacaktır!",
                color=discord.Color.orange()
            )
        else:
            template_names = {
                "default": "Default", "gaming": "Gaming", "community": "Community", 
                "business": "Business", "educational": "Educational", "streaming": "Streaming", "roleplay": "Roleplay"
            }
            embed = discord.Embed(
                title="⚠️ Confirmation Required",
                description=f"Are you sure you want to apply the **{template_names.get(self.template, self.template)}** template with the following settings?\n\n"
                           f"🎨 **Emoji Style:** {self.emoji_style}\n"
                           f"📋 **Header Style:** {header_style}\n\n"
                           "⚠️ **WARNING:** This will delete all existing channels and create the new structure!",
                color=discord.Color.orange()
            )
        
        await interaction.response.send_message(embed=embed, view=FinalConfirmationView(self.bot, self.language, self.template, self.emoji_style, header_style), ephemeral=True)

class FinalConfirmationView(discord.ui.View):
    def __init__(self, bot, language, template, emoji_style, header_style):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        self.template = template
        self.emoji_style = emoji_style
        self.header_style = header_style

    @discord.ui.button(label="✅ Onayla ve Uygula", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "✅ Confirm and Apply"
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            cog = self.bot.get_cog('ServerSetup')
            
            # Template'i al
            template_data = get_builtin_template(self.template, self.language, self.emoji_style, self.header_style)
            
            # Sunucuyu temizle ve yeni yapıyı oluştur
            await cog.clear_guild(interaction.guild)
            success = await cog.create_server_structure(interaction.guild, template_data, self.language)
            
            if success:
                # Kanal açıklamalarını güncelle
                await cog.update_all_channel_descriptions(interaction.guild)
                
                if self.language == "tr":
                    embed = discord.Embed(
                        title="✅ Başarılı",
                        description="Sunucu yapısı başarıyla oluşturuldu ve kanal açıklamaları güncellendi!",
                        color=discord.Color.green()
                    )
                else:
                    embed = discord.Embed(
                        title="✅ Success",
                        description="Server structure created successfully and channel descriptions updated!",
                        color=discord.Color.green()
                    )
            else:
                raise Exception("Template uygulanırken hata oluştu")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            if self.language == "tr":
                embed = discord.Embed(
                    title="❌ Hata",
                    description=f"Bir hata oluştu: {str(e)}",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"An error occurred: {str(e)}",
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ İptal", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "❌ Cancel"
            title = "🛑 Cancelled"
            description = "Operation cancelled."
        else:
            title = "🛑 İptal Edildi"
            description = "İşlem iptal edildi."
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ContentManagementView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="📜 Kurallar", style=discord.ButtonStyle.primary)
    async def rules_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RulesMessageModal(self.language))

    @discord.ui.button(label="👋 Hoş Geldin", style=discord.ButtonStyle.secondary)
    async def welcome_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WelcomeMessageModal(self.language))

    @discord.ui.button(label="🎮 Oyun Rolleri", style=discord.ButtonStyle.secondary)
    async def game_roles_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GameRolesMessageModal(self.language))

class CustomizationView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="👑 Rol Yönetimi", style=discord.ButtonStyle.primary)
    async def role_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Rol yönetimi:", view=RoleManagementView(self.bot, self.language), ephemeral=True)

class RoleManagementView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="➕ Rol Oluştur", style=discord.ButtonStyle.primary)
    async def create_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateRoleModal(self.language))

    @discord.ui.button(label="🎨 Rol Rengi", style=discord.ButtonStyle.secondary)
    async def change_role_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ChangeRoleColorModal(self.language))

    @discord.ui.button(label="🗑️ Rol Sil", style=discord.ButtonStyle.danger)
    async def delete_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DeleteRoleModal(self.language))

class AnalyticsView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="📊 Sunucu İstatistikleri", style=discord.ButtonStyle.primary)
    async def server_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        embed = discord.Embed(
            title="📊 Sunucu İstatistikleri" if self.language == "tr" else "📊 Server Statistics",
            color=discord.Color.blue()
        )
        embed.add_field(name="👥 Toplam Üye / Total Members", value=guild.member_count, inline=True)
        embed.add_field(name="📝 Metin Kanalları / Text Channels", value=len(guild.text_channels), inline=True)
        embed.add_field(name="🔊 Ses Kanalları / Voice Channels", value=len(guild.voice_channels), inline=True)
        embed.add_field(name="📁 Kategoriler / Categories", value=len(guild.categories), inline=True)
        embed.add_field(name="👑 Roller / Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="🎭 Emojiler / Emojis", value=len(guild.emojis), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔄 Kanal Açıklamaları", style=discord.ButtonStyle.secondary)
    async def update_descriptions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        cog = self.bot.get_cog('ServerSetup')
        count = await cog.update_all_channel_descriptions(interaction.guild)
        
        msg = f"✅ {count} kanal açıklaması güncellendi." if self.language == "tr" else f"✅ {count} channel descriptions updated."
        await interaction.followup.send(msg, ephemeral=True)

class TemplateManagementView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="💾 Mevcut Yapıyı Kaydet", style=discord.ButtonStyle.primary)
    async def save_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SaveTemplateModal(self.bot, self.language))

    @discord.ui.button(label="📋 Template Listesi", style=discord.ButtonStyle.secondary)
    async def list_templates(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog('ServerSetup')
        templates = cog.get_available_templates()
        
        if not templates:
            msg = "Kayıtlı template bulunamadı." if self.language == "tr" else "No saved templates found."
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            template_list = "\n".join([f"• {t}" for t in templates[:20]])
            embed = discord.Embed(
                title="💾 Kayıtlı Template'ler" if self.language == "tr" else "💾 Saved Templates",
                description=template_list,
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class AdvancedSettingsView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="🧹 Sunucuyu Temizle", style=discord.ButtonStyle.danger)
    async def clear_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        title = "⚠️ DİKKAT" if self.language == "tr" else "⚠️ WARNING"
        description = ("Bu işlem tüm kanalları, kategorileri ve rolleri silecektir!\n\n"
                      "Devam etmek istediğinizden emin misiniz?") if self.language == "tr" else (
                      "This will delete all channels, categories and roles!\n\n"
                      "Are you sure you want to continue?")
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.red())
        await interaction.response.send_message(embed=embed, view=ClearServerConfirmationView(self.bot, self.language), ephemeral=True)

class ClearServerConfirmationView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="✅ Evet, Temizle", style=discord.ButtonStyle.danger)
    async def confirm_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            cog = self.bot.get_cog('ServerSetup')
            await cog.clear_guild(interaction.guild)
            
            if self.language == "tr":
                embed = discord.Embed(
                    title="✅ Sunucu Temizlendi",
                    description="Tüm kanallar ve kategoriler başarıyla silindi!",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="✅ Server Cleared",
                    description="All channels and categories have been cleared!",
                    color=discord.Color.green()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            title = "❌ Hata" if self.language == "tr" else "❌ Error"
            description = f"Sunucu temizlenirken hata: {str(e)}" if self.language == "tr" else f"Error clearing server: {str(e)}"
            
            embed = discord.Embed(title=title, description=description, color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ Hayır, İptal", style=discord.ButtonStyle.secondary)
    async def cancel_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        title = "🛑 İşlem İptal Edildi" if self.language == "tr" else "🛑 Operation Cancelled"
        description = "Sunucu temizleme işlemi iptal edildi." if self.language == "tr" else "Server clearing operation cancelled."
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BotManagementModal(discord.ui.Modal):
    def __init__(self, bot, language="tr"):
        self.language = language
        title = "🤖 Bot Entegrasyonu" if language == "tr" else "🤖 Bot Integration"
        super().__init__(title=title)
        self.bot = bot

    bot_invites = discord.ui.TextInput(
        label="Bot Davet Linkleri",
        placeholder="Her satıra bir bot davet linki yazın...",
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        invites = self.bot_invites.value.strip().split('\n')
        invites = [invite.strip() for invite in invites if invite.strip()]
        
        if not invites:
            msg = "❌ Geçerli bot davet linki bulunamadı!" if self.language == "tr" else "❌ No valid bot invite links found!"
            await interaction.response.send_message(msg, ephemeral=True)
            return

        title = "🤖 Bot Davet Linkleri" if self.language == "tr" else "🤖 Bot Invite Links"
        description = "Aşağıdaki linkler kullanılarak botlar sunucuya eklenebilir:" if self.language == "tr" else "Bots can be added to the server using the following links:"
        
        embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
        
        for i, invite in enumerate(invites[:10], 1):  # Max 10 bot
            embed.add_field(name=f"Bot {i}", value=f"[Davet Et / Invite]({invite})", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class DiscordTemplateImportModal(discord.ui.Modal):
    def __init__(self, bot, language="tr"):
        self.language = language
        title = "📥 Discord Template İçe Aktar" if language == "tr" else "📥 Import Discord Template"
        super().__init__(title=title)
        self.bot = bot

    template_code = discord.ui.TextInput(
        label="Template Kodu",
        placeholder="Discord template kodunu buraya yapıştırın...",
        style=discord.TextStyle.short,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            cog = self.bot.get_cog('ServerSetup')
            template_data = await cog.import_discord_template(self.template_code.value, interaction.guild)
            
            if template_data:
                # Template'i kaydet
                template_name = f"imported_{self.template_code.value[:8]}"
                success = cog.save_template(template_name, template_data, self.language)
                
                if success:
                    if self.language == "tr":
                        embed = discord.Embed(
                            title="✅ Template İçe Aktarıldı",
                            description=f"Template başarıyla içe aktarıldı ve '{template_name}' adıyla kaydedildi.",
                            color=discord.Color.green()
                        )
                    else:
                        embed = discord.Embed(
                            title="✅ Template Imported",
                            description=f"Template successfully imported and saved as '{template_name}'.",
                            color=discord.Color.green()
                        )
                else:
                    raise Exception("Template kaydedilemedi")
            else:
                raise Exception("Template kodundan veri alınamadı")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            if self.language == "tr":
                embed = discord.Embed(
                    title="❌ Hata",
                    description=f"Template içe aktarılırken hata: {str(e)}",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Error importing template: {str(e)}",
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)

class SaveTemplateModal(discord.ui.Modal):
    def __init__(self, bot, language="tr"):
        self.language = language
        title = "💾 Template Kaydet" if language == "tr" else "💾 Save Template"
        super().__init__(title=title)
        self.bot = bot

    template_name = discord.ui.TextInput(
        label="Template Adı",
        placeholder="Kaydedeceğiniz template için bir ad girin...",
        style=discord.TextStyle.short,
        max_length=50
    )

    template_description = discord.ui.TextInput(
        label="Açıklama (Opsiyonel)",
        placeholder="Template hakkında kısa açıklama...",
        style=discord.TextStyle.paragraph,
        max_length=200,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Mevcut sunucu yapısını template'e çevir
            guild = interaction.guild
            template_data = {
                "name": self.template_name.value,
                "description": self.template_description.value or "Özel template",
                "categories": [],
                "roles": []
            }
            
            # Mevcut rolleri kaydet
            for role in guild.roles:
                if role.name != "@everyone" and not role.managed:
                    template_data["roles"].append({
                        "name": role.name,
                        "color": role.color.value,
                        "hoist": role.hoist,
                        "mentionable": role.mentionable
                    })
            
            # Mevcut kategorileri ve kanalları kaydet
            for category in guild.categories:
                category_data = {
                    "name": category.name,
                    "verified_only": False,
                    "channels": []
                }
                
                for channel in category.channels:
                    if isinstance(channel, discord.TextChannel):
                        category_data["channels"].append({
                            "name": channel.name,
                            "type": "text"
                        })
                    elif isinstance(channel, discord.VoiceChannel):
                        category_data["channels"].append({
                            "name": channel.name,
                            "type": "voice"
                        })
                
                template_data["categories"].append(category_data)
            
            # Template'i kaydet
            cog = self.bot.get_cog('ServerSetup')
            success = cog.save_template(self.template_name.value, template_data, self.language)
            
            if success:
                msg = f"✅ Template '{self.template_name.value}' başarıyla kaydedildi!" if self.language == "tr" else f"✅ Template '{self.template_name.value}' saved successfully!"
            else:
                msg = "❌ Template kaydedilirken hata oluştu." if self.language == "tr" else "❌ Error saving template."
            
            await interaction.followup.send(msg, ephemeral=True)
            
        except Exception as e:
            msg = f"❌ Hata: {str(e)}" if self.language == "tr" else f"❌ Error: {str(e)}"
            await interaction.followup.send(msg, ephemeral=True)

class CreateRoleModal(discord.ui.Modal):
    def __init__(self, language="tr"):
        title = "➕ Yeni Rol Oluştur" if language == "tr" else "➕ Create New Role"
        super().__init__(title=title)
        self.language = language

    role_name = discord.ui.TextInput(label="Rol Adı", placeholder="Rol adını yazın...")
    role_color = discord.ui.TextInput(label="Rol Rengi (HEX)", placeholder="#FF0000", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            color = discord.Color(int(self.role_color.value.replace("#", ""), 16)) if self.role_color.value else discord.Color.default()
            role = await interaction.guild.create_role(name=self.role_name.value, color=color)
            
            msg = f"✅ **{role.name}** rolü başarıyla oluşturuldu!" if self.language == "tr" else f"✅ **{role.name}** role created successfully!"
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            msg = f"❌ Rol oluşturulurken hata: {str(e)}" if self.language == "tr" else f"❌ Error creating role: {str(e)}"
            await interaction.response.send_message(msg, ephemeral=True)

class ChangeRoleColorModal(discord.ui.Modal):
    def __init__(self, language="tr"):
        title = "🎨 Rol Rengi Değiştir" if language == "tr" else "🎨 Change Role Color"
        super().__init__(title=title)
        self.language = language

    role_name = discord.ui.TextInput(label="Rol Adı", placeholder="Rengi değiştirilecek rol adı...")
    new_color = discord.ui.TextInput(label="Yeni Renk (HEX)", placeholder="#FF0000")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role = discord.utils.get(interaction.guild.roles, name=self.role_name.value)
            if not role:
                msg = "❌ Rol bulunamadı!" if self.language == "tr" else "❌ Role not found!"
                await interaction.response.send_message(msg, ephemeral=True)
                return
            
            color = discord.Color(int(self.new_color.value.replace("#", ""), 16))
            await role.edit(color=color)
            
            msg = f"✅ **{role.name}** rolünün rengi değiştirildi!" if self.language == "tr" else f"✅ **{role.name}** role color changed!"
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            msg = f"❌ Rol rengi değiştirilirken hata: {str(e)}" if self.language == "tr" else f"❌ Error changing role color: {str(e)}"
            await interaction.response.send_message(msg, ephemeral=True)

class DeleteRoleModal(discord.ui.Modal):
    def __init__(self, language="tr"):
        title = "🗑️ Rol Sil" if language == "tr" else "🗑️ Delete Role"
        super().__init__(title=title)
        self.language = language

    role_name = discord.ui.TextInput(label="Rol Adı", placeholder="Silinecek rol adı...")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role = discord.utils.get(interaction.guild.roles, name=self.role_name.value)
            if not role:
                msg = "❌ Rol bulunamadı!" if self.language == "tr" else "❌ Role not found!"
                await interaction.response.send_message(msg, ephemeral=True)
                return
            
            await role.delete()
            msg = f"✅ **{self.role_name.value}** rolü başarıyla silindi!" if self.language == "tr" else f"✅ **{self.role_name.value}** role deleted successfully!"
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            msg = f"❌ Rol silinirken hata: {str(e)}" if self.language == "tr" else f"❌ Error deleting role: {str(e)}"
            await interaction.response.send_message(msg, ephemeral=True)

class RulesMessageModal(discord.ui.Modal):
    def __init__(self, language="tr"):
        title = "📜 Kurallar Mesajı" if language == "tr" else "📜 Rules Message"
        super().__init__(title=title)
        self.language = language

    channel_name = discord.ui.TextInput(label="Kanal Adı", placeholder="Kuralların gönderileceği kanal adı...")
    rules_content = discord.ui.TextInput(
        label="Kurallar",
        placeholder="Kuralları buraya yazın...",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = discord.utils.get(interaction.guild.text_channels, name=self.channel_name.value.replace("#", ""))
            if not channel:
                msg = "❌ Kanal bulunamadı!" if self.language == "tr" else "❌ Channel not found!"
                await interaction.response.send_message(msg, ephemeral=True)
                return
            
            title = "📜 Sunucu Kuralları" if self.language == "tr" else "📜 Server Rules"
            footer = "Kurallara uymak zorunludur." if self.language == "tr" else "Following the rules is mandatory."
            
            embed = discord.Embed(title=title, description=self.rules_content.value, color=discord.Color.red())
            embed.set_footer(text=footer)
            
            await channel.send(embed=embed)
            msg = "✅ Kurallar mesajı gönderildi!" if self.language == "tr" else "✅ Rules message sent!"
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            msg = f"❌ Hata: {str(e)}"
            await interaction.response.send_message(msg, ephemeral=True)

class WelcomeMessageModal(discord.ui.Modal):
    def __init__(self, language="tr"):
        title = "👋 Hoş Geldin Mesajı" if language == "tr" else "👋 Welcome Message"
        super().__init__(title=title)
        self.language = language

    channel_name = discord.ui.TextInput(label="Kanal Adı", placeholder="Hoş geldin mesajının gönderileceği kanal adı...")
    welcome_content = discord.ui.TextInput(
        label="Hoş Geldin Mesajı",
        placeholder="Hoş geldin mesajını buraya yazın...",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = discord.utils.get(interaction.guild.text_channels, name=self.channel_name.value.replace("#", ""))
            if not channel:
                msg = "❌ Kanal bulunamadı!" if self.language == "tr" else "❌ Channel not found!"
                await interaction.response.send_message(msg, ephemeral=True)
                return
            
            title = "👋 Hoş Geldiniz!" if self.language == "tr" else "👋 Welcome!"
            footer = "Sunucumuzda iyi vakit geçirin!" if self.language == "tr" else "Have a great time on our server!"
            
            embed = discord.Embed(title=title, description=self.welcome_content.value, color=discord.Color.blue())
            embed.set_footer(text=footer)
            
            await channel.send(embed=embed)
            msg = "✅ Hoş geldin mesajı gönderildi!" if self.language == "tr" else "✅ Welcome message sent!"
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            msg = f"❌ Hata: {str(e)}"
            await interaction.response.send_message(msg, ephemeral=True)

class GameRolesMessageModal(discord.ui.Modal):
    def __init__(self, language="tr"):
        title = "🎮 Oyun Rolleri Mesajı" if language == "tr" else "🎮 Game Roles Message"
        super().__init__(title=title)
        self.language = language

    channel_name = discord.ui.TextInput(label="Kanal Adı", placeholder="Oyun rolleri mesajının gönderileceği kanal adı...")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = discord.utils.get(interaction.guild.text_channels, name=self.channel_name.value.replace("#", ""))
            if not channel:
                msg = "❌ Kanal bulunamadı!" if self.language == "tr" else "❌ Channel not found!"
                await interaction.response.send_message(msg, ephemeral=True)
                return
            
            if self.language == "tr":
                title = "🎮 Oyun Rolleri"
                description = (
                    "Oynadığın oyunlara göre aşağıdaki emojilere tıklayarak ilgili rolleri alabilirsin.\n\n"
                    "🎯 Valorant\n⚔️ League of Legends\n🔫 Counter-Strike\n🎮 Minecraft\n🚁 Fortnite\n\n"
                    "İstediğin zaman rolleri alıp kaldırabilirsin."
                )
            else:
                title = "🎮 Game Roles"
                description = (
                    "Click the emojis below to get roles for the games you play.\n\n"
                    "🎯 Valorant\n⚔️ League of Legends\n🔫 Counter-Strike\n🎮 Minecraft\n🚁 Fortnite\n\n"
                    "You can add or remove roles anytime."
                )
            
            embed = discord.Embed(title=title, description=description, color=discord.Color.purple())
            
            message = await channel.send(embed=embed)
            reactions = ["🎯", "⚔️", "🔫", "🎮", "🚁"]
            for reaction in reactions:
                await message.add_reaction(reaction)
            
            msg = "✅ Oyun rolleri mesajı gönderildi!" if self.language == "tr" else "✅ Game roles message sent!"
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            msg = f"❌ Hata: {str(e)}"
            await interaction.response.send_message(msg, ephemeral=True)

class SavedTemplateSelectView(discord.ui.View):
    def __init__(self, bot, language, templates):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        
        # Select menü seçeneklerini oluştur
        options = []
        for template in templates[:25]:  # Discord limiti 25
            options.append(discord.SelectOption(
                label=template,
                value=template,
                description="Kayıtlı template"
            ))
        
        select = discord.ui.Select(
            placeholder="Template seçin...",
            options=options
        )
        select.callback = self.template_selected
        self.add_item(select)
    
    async def template_selected(self, interaction: discord.Interaction):
        template_name = interaction.data['values'][0]
        
        # Template'i yükle ve uygula
        cog = self.bot.get_cog('ServerSetup')
        template_data = cog.load_template(template_name, self.language)
        
        if template_data:
            # Onay iste
            msg = f"'{template_name}' template'ini uygulamak istiyor musunuz?" if self.language == "tr" else f"Do you want to apply the '{template_name}' template?"
            await interaction.response.send_message(msg, view=ApplyTemplateConfirmView(self.bot, self.language, template_data), ephemeral=True)
        else:
            msg = "Template yüklenemedi." if self.language == "tr" else "Template could not be loaded."
            await interaction.response.send_message(msg, ephemeral=True)

class ApplyTemplateConfirmView(discord.ui.View):
    def __init__(self, bot, language, template_data):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        self.template_data = template_data

    @discord.ui.button(label="✅ Uygula", style=discord.ButtonStyle.danger)
    async def apply_template(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            cog = self.bot.get_cog('ServerSetup')
            await cog.clear_guild(interaction.guild)
            success = await cog.create_server_structure(interaction.guild, self.template_data, self.language)
            
            if success:
                msg = "✅ Template başarıyla uygulandı!" if self.language == "tr" else "✅ Template applied successfully!"
            else:
                msg = "❌ Template uygulanırken hata oluştu." if self.language == "tr" else "❌ Error applying template."
            
            await interaction.followup.send(msg, ephemeral=True)
        except Exception as e:
            msg = f"❌ Hata: {str(e)}"
            await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="❌ İptal", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = "İşlem iptal edildi." if self.language == "tr" else "Operation cancelled."
        await interaction.response.send_message(msg, ephemeral=True) 