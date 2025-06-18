import discord
from discord import ui
import asyncio
import json
import logging
from utils.core.content_loader import load_content, async_load_content, async_set_content
from utils import create_embed
from .templates import get_builtin_template
from utils.database.content_manager import content_manager
from utils.core.formatting import create_embed
from utils.common.pagination import Paginator

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
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="Server Structure", style=discord.ButtonStyle.primary, emoji="🏗️")
    async def server_structure(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "Server Structure"
            embed = discord.Embed(
                title="🏗️ Server Structure",
                description="Choose template source:",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="🏗️ Sunucu Yapısı",
                description="Template kaynağını seçin:",
                color=discord.Color.blue()
            )
        
        await interaction.response.send_message(embed=embed, view=TemplateSourceView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="Content Management", style=discord.ButtonStyle.secondary, emoji="📝")
    async def content_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "Content Management"
            embed = discord.Embed(
                title="📝 Content Management",
                description="Select content type:",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="📝 İçerik Yönetimi",
                description="İçerik türünü seçin:",
                color=discord.Color.blue()
            )
        
        await interaction.response.send_message(embed=embed, view=ContentManagementView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="Bot Integration", style=discord.ButtonStyle.secondary, emoji="🤖")
    async def bot_integration(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "Bot Integration"
        
        await interaction.response.send_modal(BotManagementModal(self.bot, self.language))

    @discord.ui.button(label="Business Commands", style=discord.ButtonStyle.success, emoji="🏢")
    async def business_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "Business Commands"
            embed = discord.Embed(
                title="🏢 Business Commands",
                description="Select business command package to deploy:",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Available Packages",
                value="• **Bionluk Package** - Complete server showcase\n• **Announcement Package** - Server announcements\n• **Rules Package** - Server rules and guidelines",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="🏢 İş Komutları",
                description="Dağıtılacak iş komut paketini seçin:",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Mevcut Paketler",
                value="• **Bionluk Paketi** - Tam sunucu tanıtımı\n• **Duyuru Paketi** - Sunucu duyuruları\n• **Kurallar Paketi** - Sunucu kuralları ve yönergeler",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=BusinessCommandsView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="Customization", style=discord.ButtonStyle.secondary, emoji="🎨")
    async def customization(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎨 Customization Options",
            description="Choose a customization option to configure your server:",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="Available Options",
            value=(
                "• **👑 Role Management** - Create, edit, and delete roles\n"
                "• **🎨 Server Appearance** - Colors, icons, and banners\n"
                "• **📋 Permission Templates** - Apply pre-made permission sets\n"
                "• **🔧 Advanced Settings** - Fine-tune server configuration"
            ),
            inline=False
        )
        embed.set_footer(text="Select an option to continue")
        
        await interaction.response.send_message(embed=embed, view=CustomizationView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="Analytics & Maintenance", style=discord.ButtonStyle.success, emoji="📊")
    async def analytics(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📊 Analytics & Maintenance",
            description="Access server analytics and maintenance tools:",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Features",
            value=(
                "• **📊 Server Statistics** - View detailed server metrics\n"
                "• **🔄 Channel Descriptions** - Update all channel descriptions\n"
                "• **🧹 Server Cleanup** - Remove inactive channels/roles\n"
                "• **📈 Activity Reports** - Member activity analysis"
            ),
            inline=False
        )
        embed.set_footer(text="Choose a tool to proceed")
        
        await interaction.response.send_message(embed=embed, view=AnalyticsView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="Template Management", style=discord.ButtonStyle.success, emoji="💾")
    async def template_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💾 Template Management",
            description="Save, load, and manage server templates:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Options",
            value=(
                "• **💾 Save Current Structure** - Save your server setup as a template\n"
                "• **📋 Template List** - View and manage saved templates\n"
                "• **📤 Export Template** - Share templates with others\n"
                "• **📥 Import Template** - Load templates from file"
            ),
            inline=False
        )
        embed.set_footer(text="Templates help you quickly set up similar servers")
        
        await interaction.response.send_message(embed=embed, view=TemplateManagementView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="Advanced Settings", style=discord.ButtonStyle.danger, emoji="⚙️")
    async def advanced_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚙️ Advanced Settings",
            description="⚠️ **Warning**: These settings can significantly modify your server!",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Dangerous Operations",
            value=(
                "• **🧹 Clear Server** - Delete all channels and categories\n"
                "• **🔄 Reset Permissions** - Reset all permission overwrites\n"
                "• **💣 Bulk Delete** - Mass delete messages/roles/channels\n"
                "• **🔧 Debug Mode** - Advanced debugging tools"
            ),
            inline=False
        )
        embed.set_footer(text="⚠️ Use with extreme caution!")
        
        await interaction.response.send_message(embed=embed, view=AdvancedSettingsView(self.bot, self.language), ephemeral=True)

class BusinessCommandsView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        self.selected_channel = None

    @discord.ui.button(label="Bionluk Package", style=discord.ButtonStyle.primary, emoji="📦")
    async def bionluk_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sends special messages for Bionluk"""
        await interaction.response.defer(ephemeral=True)
        
        cog = self.bot.get_cog('ServerSetup')
        format_mentions = cog.get_format_mentions(interaction.guild)
        
        view = ui.View()
        view.add_item(ui.Button(label="Important Bot Commands", url="https://medium.com/@bergaman9/%C3%B6nemli-discord-komutlar%C4%B1-3a4598cde13a", style=discord.ButtonStyle.link, emoji="🔗"))
        
        view2 = ui.View()
        view2.add_item(ui.Button(label="Discord Bot Features", url="https://medium.com/@bergaman9/2023-y%C4%B1l%C4%B1nda-sunucunuzda-olmas%C4%B1-gereken-discord-botlar%C4%B1-e895de2052dc", style=discord.ButtonStyle.link, emoji="🔗"))
        
        # Load content - async from MongoDB
        guild_id = str(interaction.guild.id)
        
        # Initialize content manager if needed
        if not content_manager._initialized:
            await content_manager.initialize()
        
        komutlar_content = await async_load_content(guild_id, "commands")
        komutlar_parts = komutlar_content.split("## Member Commands")
        komutlar_text = komutlar_parts[0].strip() if len(komutlar_parts) > 0 else komutlar_content
        
        # Default content for bot features
        botlar_text = """🤖 **Contro Bot Features:**
• Advanced moderation system
• Automatic role management
• Ticket support system
• Level and XP system
• Giveaway system
• Music commands
• Fun commands
• And much more!"""
        
        roller_text = await async_load_content(guild_id, "roles")
        kanallar_text = await async_load_content(guild_id, "channels")
        sunucu_hizmetleri_text = await async_load_content(guild_id, "services")
        server_content = await async_load_content(guild_id, "server")
        server_parts = server_content.split("## Server Features - Page 2")
        
        # Create embeds
        komutlar_embed = discord.Embed(title="DISCORD COMMANDS", description=komutlar_text, color=0xfad100)
        botlar_embed = discord.Embed(title="BOT FEATURES", description=botlar_text, color=0x00e9b4)
        roller_embed = discord.Embed(title="SERVER ROLES", description=roller_text.format(**format_mentions), color=0xff1f1f)
        kanallar_embed = discord.Embed(title="SERVER CHANNELS", description=kanallar_text.format(**format_mentions), color=0x00e9b4)
        
        sunucu_hizmetleri_embed = discord.Embed(title="BERGAMAN SERVER SERVICES", description=sunucu_hizmetleri_text, color=0xffffff)
        sunucu_hizmetleri_embed.set_thumbnail(url="https://i.imgur.com/fntLhGX.png")
        
        sunucu_text_page = server_parts[0].strip() if len(server_parts) > 0 else server_content
        sunucu_embed = discord.Embed(title="SERVER FEATURES", description=sunucu_text_page.format(**format_mentions), color=0xf47fff)
        sunucu_embed.set_footer(text="Page 1/2")
        sunucu_embed.set_thumbnail(url=interaction.guild.icon.url)
        
        sunucu_text_page2 = server_content.split("## Server Features - Page 2")[1].strip() if "## Server Features - Page 2" in server_content else ""
        sunucu_embed2 = discord.Embed(title="SERVER FEATURES", description=sunucu_text_page2.format(**format_mentions), color=0xf47fff)
        sunucu_embed2.set_footer(text="Page 2/2")
        sunucu_embed2.set_thumbnail(url=interaction.guild.icon.url)
        
        # Channel check
        channel = self.selected_channel or interaction.channel
        
        await interaction.followup.send(
            embed=create_embed(
                title="📦 Bionluk Package",
                description=f"Sending messages to {channel.mention}...",
                color=discord.Color.green()
            ), 
            ephemeral=True
        )
        
        # Send messages in order
        await channel.send(embed=sunucu_embed)
        await channel.send(embed=sunucu_embed2)
        await channel.send(embed=komutlar_embed, view=view)
        await channel.send(embed=botlar_embed, view=view2)
        await channel.send(embed=roller_embed)
        await channel.send(embed=kanallar_embed)
        await channel.send(embed=sunucu_hizmetleri_embed)

    @discord.ui.button(label="Announcement Package", style=discord.ButtonStyle.secondary, emoji="📣")
    async def announcement_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sends announcement messages"""
        await interaction.response.defer(ephemeral=True)
        
        cog = self.bot.get_cog('ServerSetup')
        format_mentions = cog.get_format_mentions(interaction.guild)
        
        guild_id = str(interaction.guild.id)
        
        # Modern and organized announcement embeds
        
        # Welcome announcement
        hosgeldin_embed = discord.Embed(
            title="🎉 WELCOME TO OUR SERVER!",
            description=(
                f"**Welcome to {interaction.guild.name}!** 🌟\n\n"
                "We're thrilled to have you join us. This server is a community where we come together "
                "around our shared interests, build friendships, and have fun.\n\n"
                
                "**🚀 To get started:**\n"
                "• First, read the rules in the <#rules> channel\n"
                "• Get roles based on your interests in <#roles>\n"
                "• Introduce yourself in <#chat>\n"
                "• Learn bot commands in <#commands>\n\n"
                
                "**📱 Social Media:**\n"
                "• Discord: [Server Invite Link](https://discord.gg/invite)\n"
                "• Twitter: [@servername](https://twitter.com/)\n"
                "• YouTube: [Channel Name](https://youtube.com/)\n\n"
                
                "Don't hesitate to reach out to our staff if you have any questions!"
            ),
            color=0xf47fff
        )
        hosgeldin_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        hosgeldin_embed.set_footer(text="Let's build a great community together! 💫")
        
        # Active events and updates
        etkinlik_embed = discord.Embed(
            title="📅 ACTIVE EVENTS AND UPDATES",
            description=(
                "**🎮 Weekly Events:**\n"
                "• **Monday:** Movie/Series Night (9:00 PM)\n"
                "• **Wednesday:** Gaming Tournament (8:00 PM)\n"
                "• **Friday:** Karaoke & Music (10:00 PM)\n"
                "• **Saturday:** Community Gathering (7:00 PM)\n\n"
                
                "**🎁 Monthly Events:**\n"
                "• First Friday of each month: Grand Giveaway\n"
                "• 15th of the month: Talent Contest\n"
                "• End of month: Community Awards\n\n"
                
                "**📢 Latest Updates:**\n"
                "• ✅ New level system added\n"
                "• ✅ Music bot updated\n"
                "• ✅ Custom roles system active\n"
                "• ✅ Ticket support system renewed\n\n"
                
                "**🏆 Active Competitions:**\n"
                "• Most active member award\n"
                "• Best content creator\n"
                "• Invite competition"
            ),
            color=0x00e9b4
        )
        etkinlik_embed.set_footer(text="Don't forget to participate in events! 🎊")
        
        # Important info and FAQ
        bilgi_embed = discord.Embed(
            title="❓ FREQUENTLY ASKED QUESTIONS (FAQ)",
            description=(
                "**❓ How do I level up?**\n"
                "You can earn XP by chatting and spending time in voice channels.\n\n"
                
                "**❓ How can I get special roles?**\n"
                "You can earn special roles by reaching certain levels or participating in events.\n\n"
                
                "**❓ I have a problem, who can I contact?**\n"
                "You can reach admins by opening a ticket in the <#support> channel.\n\n"
                
                "**❓ How do I use bot commands?**\n"
                "Use the `/help` command to see all available commands.\n\n"
                
                "**❓ Where can I find server rules?**\n"
                "All rules are detailed in the <#rules> channel.\n\n"
                
                "**❓ How can I submit suggestions or complaints?**\n"
                "You can use the <#suggestions> channel or DM the staff."
            ),
            color=0xfad100
        )
        bilgi_embed.add_field(
            name="🔗 Useful Links",
            value=(
                "[Server Rules](#rules) • "
                "[Support System](#support) • "
                "[Announcements](#announcements)"
            ),
            inline=False
        )
        
        # Channel check
        channel = self.selected_channel or interaction.channel
        
        await interaction.followup.send(
            embed=create_embed(
                title="📣 Announcement Package",
                description=f"Sending messages to {channel.mention}...",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
        await channel.send(embed=hosgeldin_embed)
        await channel.send(embed=etkinlik_embed)
        await channel.send(embed=bilgi_embed)

    @discord.ui.button(label="Rules Package", style=discord.ButtonStyle.secondary, emoji="⚖️")
    async def rules_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sends rules messages"""
        await interaction.response.defer(ephemeral=True)
        
        cog = self.bot.get_cog('ServerSetup')
        format_mentions = cog.get_format_mentions(interaction.guild)
        guild_id = str(interaction.guild.id)
        
        # Initialize content manager if needed
        if not content_manager._initialized:
            await content_manager.initialize()
        
        # Modern and better designed rules
        kurallar_embed = discord.Embed(
            title="📜 SERVER RULES",
            description=(
                "To ensure everyone can have a safe and enjoyable time in this server, please follow these rules:\n\n"
                
                "**1️⃣ Be Respectful**\n"
                "• Be kind and respectful to other members\n"
                "• Do not use profanity, racist, or harassing language\n\n"
                
                "**2️⃣ No Advertising or Spam**\n"
                "• Do not share other servers or external links\n"
                "• Do not send repetitive messages or spam\n\n"
                
                "**3️⃣ Stay On-Topic in Channels**\n"
                "• Send messages appropriate to each channel's purpose\n"
                "• Avoid off-topic discussions\n\n"
                
                "**4️⃣ Don't Share Private Information**\n"
                "• Don't openly share your personal information\n"
                "• Don't ask for others' private information\n\n"
                
                "**5️⃣ No Scamming or Cheating**\n"
                "• Do not engage in scamming or cheating activities\n"
                "• Don't spread false or misleading information\n\n"
                
                "**6️⃣ Respect Staff Members**\n"
                "• Be respectful to server admins and moderators\n"
                "• Follow staff instructions\n\n"
                
                "**7️⃣ Use Appropriate Names and Avatars**\n"
                "• Use an appropriate and understandable username and profile picture\n\n"
                
                "**8️⃣ No Copyright Infringement**\n"
                "• Don't share copyrighted content without permission\n\n"
                
                "**9️⃣ Avoid Drama and Conflicts**\n"
                "• Avoid personal conflicts and resolve issues in private messages\n\n"
                
                "**🔟 Inappropriate Content is Prohibited**\n"
                "• Pornography, violent, or illegal materials are strictly prohibited"
            ),
            color=0xff1f1f
        )
        kurallar_embed.set_footer(text="⚠️ Members who violate rules will be warned and may be removed for repeated violations.")
        
        # Support and punishment system
        destek_embed = discord.Embed(
            title="🛡️ PUNISHMENT SYSTEM AND SUPPORT",
            description=(
                "**⚠️ Punishment System**\n\n"
                "**1st Violation:** Warning\n"
                "**2nd Violation:** 1 hour mute\n"
                "**3rd Violation:** 24 hour mute\n"
                "**4th Violation:** 7 day ban\n"
                "**5th Violation:** Permanent ban\n\n"
                
                "**📞 Support**\n"
                "• To get help from staff, you can open a ticket in the `#support` channel\n"
                "• To report members violating rules, you can mention the `@Moderator` role\n\n"
                
                "**✉️ Contact**\n"
                "• You can reach out to admins for server-related suggestions and complaints\n"
                "• Use `/help` command for bot commands"
            ),
            color=0x00e9b4
        )
        destek_embed.set_footer(text="Please help us provide a safe environment by following these rules.")
        
        invite_link = await cog.create_invite(interaction.guild)
        
        # Invite embed
        davet_embed = discord.Embed(
            title="🎉 Invite Your Friends!",
            description=f"Help us grow our server!\n\n**Invite Link:**\n{invite_link}",
            color=0xf47fff
        )
        
        # Channel check
        channel = self.selected_channel or interaction.channel
        
        await interaction.followup.send(
            embed=create_embed(
                title="⚖️ Rules Package",
                description=f"Sending messages to {channel.mention}...",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
        await channel.send(embed=kurallar_embed)
        await channel.send(embed=destek_embed)
        await channel.send(embed=davet_embed)
    
    @discord.ui.button(label="Select Channel", style=discord.ButtonStyle.secondary, emoji="📌")
    async def select_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Mesajların gönderileceği kanalı seçer"""
        from utils.common import PaginatedChannelSelector
        
        # Get text channels only
        text_channels = [ch for ch in interaction.guild.channels if isinstance(ch, discord.TextChannel)]
        
        async def channel_selected(inter: discord.Interaction, channels: list):
            self.selected_channel = channels[0] if channels else None
            embed = discord.Embed(
                title="✅ Channel Selected",
                description=f"Messages will be sent to {self.selected_channel.mention}",
                color=discord.Color.green()
            )
            await inter.response.edit_message(embed=embed, view=self)
        
        embed = discord.Embed(
            title="📌 Channel Selection",
            description="Select the channel where messages will be sent:",
            color=discord.Color.blue()
        )
        
        view = PaginatedChannelSelector(
            channels=text_channels,
            callback_func=channel_selected,
            placeholder="Select a channel..."
        )
        
        await interaction.response.edit_message(embed=embed, view=view)

class TemplateSourceView(discord.ui.View):
    def __init__(self, bot, language="en"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.button(label="Built-in Templates", style=discord.ButtonStyle.primary, emoji="📋")
    async def builtin_templates(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📋 Built-in Templates",
            description="Choose from pre-configured server templates:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Available Templates",
            value=(
                "• **🏠 Default** - General purpose community server\n"
                "• **🎮 Gaming** - Gaming community with voice channels\n"
                "• **👥 Community** - Large community server setup\n"
                "• **💼 Business** - Professional workspace environment\n"
                "• **🎓 Educational** - School/course management server\n"
                "• **📺 Streaming** - Content creator focused server\n"
                "• **🎭 Roleplay** - RP server with character channels"
            ),
            inline=False
        )
        embed.set_footer(text="Select a template to preview its structure")
        
        await interaction.response.send_message(embed=embed, view=BuiltinTemplateSelectView(self.bot, self.language), ephemeral=True)

    @discord.ui.button(label="Import Discord Template", style=discord.ButtonStyle.secondary, emoji="📥")
    async def import_discord_template(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.language == "en":
            button.label = "Import Discord Template"
        
        await interaction.response.send_modal(DiscordTemplateImportModal(self.bot, self.language))

    @discord.ui.button(label="Saved Templates", style=discord.ButtonStyle.secondary, emoji="💾")
    async def saved_templates(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💾 Saved Templates",
            description="Loading your saved templates...",
            color=discord.Color.blue()
        )
        
        cog = self.bot.get_cog('ServerSetup')
        templates = cog.get_available_templates()
        
        if not templates:
            embed = discord.Embed(
                title="💾 Saved Templates",
                description="❌ No saved templates found.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="How to save templates",
                value="Use the **Template Management** option from the main menu to save your current server structure as a template.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="💾 Saved Templates",
                description="Select a saved template to apply:",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Available Templates",
                value="\n".join([f"• **{template}**" for template in templates[:10]]),
                inline=False
            )
            await interaction.response.send_message(embed=embed, view=SavedTemplateSelectView(self.bot, self.language, templates), ephemeral=True)

class BuiltinTemplateSelectView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language

    @discord.ui.select(
        placeholder="Select template...",
        options=[
            discord.SelectOption(label="🏠 Default", value="default", description="General purpose server"),
            discord.SelectOption(label="🎮 Gaming", value="gaming", description="Gaming server"),
            discord.SelectOption(label="👥 Community", value="community", description="Social community"),
            discord.SelectOption(label="💼 Business", value="business", description="Professional environment"),
            discord.SelectOption(label="🎓 Educational", value="educational", description="Educational institution"),
            discord.SelectOption(label="📺 Streaming", value="streaming", description="Streaming server"),
            discord.SelectOption(label="🎭 Roleplay", value="roleplay", description="Role playing")
        ]
    )
    async def template_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        template = select.values[0]
        self.template = template
        
        embed = discord.Embed(
            title="✅ Template Selected",
            description=f"You selected the **{template.title()}** template.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Next Step",
            value="Choose an emoji style for your server channels and categories.",
            inline=False
        )
        embed.set_footer(text="The emoji style affects how your channels look")
        
        await interaction.response.send_message(embed=embed, view=StyleSelectView(self.bot, self.language, template), ephemeral=True)

class StyleSelectView(discord.ui.View):
    def __init__(self, bot, language="tr", template="default"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        self.template = template
        self.emoji_style = None

    @discord.ui.select(
        placeholder="Select emoji style...",
        options=[
            discord.SelectOption(label="Modern", value="modern", emoji="📋", description="Clean modern icons"),
            discord.SelectOption(label="Colorful", value="colorful", emoji="🌈", description="Bright colorful emojis"),
            discord.SelectOption(label="Gaming", value="gaming", emoji="🎮", description="Gaming themed icons"),
            discord.SelectOption(label="Minimal", value="minimal", emoji="•", description="Simple minimal style"),
            discord.SelectOption(label="Business", value="business", emoji="💼", description="Professional icons")
        ]
    )
    async def emoji_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.emoji_style = select.values[0]
        
        embed = discord.Embed(
            title="✅ Emoji Style Selected",
            description=f"You selected the **{select.values[0].title()}** emoji style.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Next Step",
            value="Choose a header style for your category names.",
            inline=False
        )
        embed.set_footer(text="Headers make your server structure more organized")
        
        await interaction.response.send_message(embed=embed, view=HeaderSelectView(self.bot, self.language, self.template, self.emoji_style), ephemeral=True)

class HeaderSelectView(discord.ui.View):
    def __init__(self, bot, language="tr", template="default", emoji_style="modern"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
        self.template = template
        self.emoji_style = emoji_style

    @discord.ui.select(
        placeholder="Select header style...",
        options=[
            discord.SelectOption(label="Classic", value="classic", emoji="📜", description="┌─── HEADER ───┐"),
            discord.SelectOption(label="Modern", value="modern", emoji="🎨", description="╭─ HEADER ─╮"),
            discord.SelectOption(label="Elegant", value="elegant", emoji="✨", description="◤ HEADER ◥"),
            discord.SelectOption(label="Simple", value="simple", emoji="📝", description="[ HEADER ]"),
            discord.SelectOption(label="Gaming", value="gaming", emoji="🎮", description="▸ HEADER ◂"),
            discord.SelectOption(label="Minimal", value="minimal", emoji="⚪", description="HEADER"),
            discord.SelectOption(label="Arrows", value="arrows", emoji="➤", description="➤ HEADER ◄"),
            discord.SelectOption(label="Stars", value="stars", emoji="✦", description="✦ HEADER ✦")
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

    @discord.ui.button(label="Confirm and Apply", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        # Get template
        template_data = get_builtin_template(self.template, self.language, self.emoji_style, self.header_style)
        
        if not template_data:
            await interaction.followup.send("❌ Template data could not be loaded.", ephemeral=True)
            return
        
        cog = self.bot.get_cog('ServerSetup')
        
        # Clear existing structure
        await interaction.followup.send("🧹 Clearing existing structure...", ephemeral=True)
        await cog.clear_guild(interaction.guild)
        
        # Create new structure
        await interaction.followup.send("🏗️ Creating new structure...", ephemeral=True)
        success = await cog.create_server_structure(interaction.guild, template_data, self.language)
        
        if success:
            embed = discord.Embed(
                title="✅ Server Setup Complete!",
                description=f"Successfully applied the **{self.template.title()}** template with **{self.emoji_style}** emoji style and **{self.header_style}** header style.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Next Steps",
                value=(
                    "• Configure role permissions as needed\n"
                    "• Set up bot integrations\n"
                    "• Customize channel descriptions\n"
                    "• Add custom emojis and stickers"
                ),
                inline=False
            )
        else:
            embed = discord.Embed(
                title="❌ Setup Failed",
                description="An error occurred while setting up the server structure.",
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Setup Cancelled",
            description="Server setup has been cancelled. No changes were made.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ContentManagementView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
    
    @discord.ui.button(label="Rules", style=discord.ButtonStyle.primary, emoji="📜")
    async def rules_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RulesMessageModal(self.language))
    
    @discord.ui.button(label="Welcome", style=discord.ButtonStyle.secondary, emoji="👋")
    async def welcome_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WelcomeMessageModal(self.language))
    
    @discord.ui.button(label="Game Roles", style=discord.ButtonStyle.secondary, emoji="🎮")
    async def game_roles_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GameRolesMessageModal(self.language))

class CustomizationView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
    
    @discord.ui.button(label="Role Management", style=discord.ButtonStyle.primary, emoji="👑")
    async def role_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👑 Role Management",
            description="Manage server roles with these tools:",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="Options",
            value=(
                "• **➕ Create Role** - Create a new role with custom settings\n"
                "• **🎨 Role Color** - Change the color of existing roles\n"
                "• **🗑️ Delete Role** - Remove roles from the server"
            ),
            inline=False
        )
        embed.set_footer(text="Select an option to manage roles")
        
        await interaction.response.send_message(embed=embed, view=RoleManagementView(self.bot, self.language), ephemeral=True)

class RoleManagementView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
    
    @discord.ui.button(label="Create Role", style=discord.ButtonStyle.primary, emoji="➕")
    async def create_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateRoleModal(self.language))
    
    @discord.ui.button(label="Role Color", style=discord.ButtonStyle.secondary, emoji="🎨")
    async def change_role_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ChangeRoleColorModal(self.language))
    
    @discord.ui.button(label="Delete Role", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DeleteRoleModal(self.language))

class AnalyticsView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
    
    @discord.ui.button(label="Server Statistics", style=discord.ButtonStyle.primary, emoji="📊")
    async def server_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📊 Server Statistics",
            description="Here are the current server statistics:",
            color=discord.Color.blue()
        )
        embed.add_field(name="Total Members", value=interaction.guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(interaction.guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(interaction.guild.roles), inline=True)
        embed.add_field(name="Text Channels", value=len(interaction.guild.text_channels), inline=True)
        embed.add_field(name="Voice Channels", value=len(interaction.guild.voice_channels), inline=True)
        embed.add_field(name="Categories", value=len(interaction.guild.categories), inline=True)
        embed.set_footer(text=f"Server ID: {interaction.guild.id}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Update Descriptions", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def update_descriptions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        msg = await interaction.followup.send("Updating channel descriptions... 0%", ephemeral=True)
        cog = self.bot.get_cog('ServerSetup')
        updated = await cog.update_all_channel_descriptions(interaction.guild, msg)
        
        await msg.edit(content=f"✅ Updated {updated} channel descriptions!")

class TemplateManagementView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
    
    @discord.ui.button(label="Save Current Structure", style=discord.ButtonStyle.primary, emoji="💾")
    async def save_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SaveTemplateModal(self.bot, self.language))
    
    @discord.ui.button(label="Template List", style=discord.ButtonStyle.secondary, emoji="📋")
    async def list_templates(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog('ServerSetup')
        templates = cog.get_available_templates()
        
        if templates:
            embed = discord.Embed(
                title="📋 Available Templates",
                description="\n".join([f"• **{template}**" for template in templates]),
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="📋 Template List",
                description="No templates found. Save your server structure to create templates.",
                color=discord.Color.orange()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AdvancedSettingsView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
    
    @discord.ui.button(label="Clear Server", style=discord.ButtonStyle.danger, emoji="🧹")
    async def clear_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚠️ Clear Server Confirmation",
            description="**WARNING**: This will delete ALL channels and categories in your server!\n\nAre you absolutely sure you want to proceed?",
            color=discord.Color.red()
        )
        embed.set_footer(text="This action cannot be undone!")
        
        await interaction.response.send_message(embed=embed, view=ClearServerConfirmationView(self.bot, self.language), ephemeral=True)

class ClearServerConfirmationView(discord.ui.View):
    def __init__(self, bot, language="tr"):
        super().__init__(timeout=300)
        self.bot = bot
        self.language = language
    
    @discord.ui.button(label="Yes, Clear Server", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        await interaction.followup.send("🧹 Clearing server structure...", ephemeral=True)
        
        cog = self.bot.get_cog('ServerSetup')
        await cog.clear_guild(interaction.guild)
        
        # Create default text channel
        default_channel = await interaction.guild.create_text_channel("general")
        
        embed = discord.Embed(
            title="✅ Server Cleared",
            description="All channels and categories have been deleted.\n\nA new #general channel has been created.",
            color=discord.Color.green()
        )
        
        try:
            await default_channel.send(embed=embed)
            await interaction.followup.send("✅ Server structure has been cleared!", ephemeral=True)
        except:
            await interaction.followup.send("✅ Server structure has been cleared!", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Cancelled",
            description="Server clear operation has been cancelled.",
            color=discord.Color.red()
        )
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