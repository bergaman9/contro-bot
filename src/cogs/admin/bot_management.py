import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Dict, Union
import logging
import json
import os
import datetime

from src.utils.core.formatting import create_embed
from src.utils.database.connection import initialize_mongodb, is_db_available

# Set up logging
logger = logging.getLogger('bot_settings')

# Changelog gösterimini sağlayan sınıflar
class VersionButton(discord.ui.Button):
    def __init__(self, version: str, emoji: str, style=discord.ButtonStyle.secondary):
        super().__init__(label=f"v{version}", emoji=emoji, style=style)
        self.version = version
    
    async def callback(self, interaction: discord.Interaction):
        # Find parent view
        view = self.view
        if not isinstance(view, ChangelogView):
            return
        
        # Update the view with selected version
        await view.update_changelog(interaction, self.version)


class ChangelogView(discord.ui.View):
    def __init__(self, bot, versions_data, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.versions_data = versions_data
        self.versions = [v["version"] for v in versions_data["versions"]]
        self.current_version = versions_data["current_version"]
        self.current_version_data = None
        
        # Find current version data
        for version in versions_data["versions"]:
            if version["version"] == self.current_version:
                self.current_version_data = version
                break
        
        # Add version buttons
        self.setup_buttons()
    
    def setup_buttons(self):
        # Clear existing buttons
        self.clear_items()
        
        # Add version buttons
        for i, version in enumerate(reversed(self.versions)):
            # Use different styles for current version
            style = discord.ButtonStyle.success if version == self.current_version else discord.ButtonStyle.secondary
            emoji = "✅" if version == self.current_version else "📝"
            
            button = VersionButton(version, emoji, style)
            self.add_item(button)
        
        # Add support server button
        self.add_item(discord.ui.Button(label="Support Server", url="https://discord.gg/vXhwuxJk88", style=discord.ButtonStyle.link))
    
    async def update_changelog(self, interaction: discord.Interaction, version: str):
        # Find version data
        version_data = None
        for v in self.versions_data["versions"]:
            if v["version"] == version:
                version_data = v
                break
        
        if not version_data:
            return await interaction.response.send_message(
                embed=create_embed("❌ Versiyon bilgisi bulunamadı.", discord.Color.red()),
                ephemeral=True
            )
        
        # Create version embed
        embed = self.create_changelog_embed(version_data)
        
        # Update message
        await interaction.response.edit_message(embed=embed, view=self)
    
    def create_changelog_embed(self, version_data: Dict):
        # Create basic embed
        embed = discord.Embed(
            title=f"📋 Changelog: v{version_data['version']}",
            description=f"**Sürüm Tarihi:** {version_data['date']}",
            color=discord.Color.blue()
        )
        
        # Add features
        if "features" in version_data and version_data["features"]:
            features_text = "\n".join([f"• {feature}" for feature in version_data["features"]])
            embed.add_field(name="✨ Yeni Özellikler", value=features_text, inline=False)
        
        # Add fixes
        if "fixes" in version_data and version_data["fixes"]:
            fixes_text = "\n".join([f"• {fix}" for fix in version_data["fixes"]])
            embed.add_field(name="🔧 Düzeltmeler", value=fixes_text, inline=False)
        
        # Add changes
        if "changes" in version_data and version_data["changes"]:
            changes_text = "\n".join([f"• {change}" for change in version_data["changes"]])
            embed.add_field(name="🔄 Değişiklikler", value=changes_text, inline=False)
        
        # Add footer with bot name
        embed.set_footer(text=f"{self.bot.user.name} | v{version_data['version']}", icon_url=self.bot.user.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        
        return embed


class RoadmapView(discord.ui.View):
    def __init__(self, bot, versions_data):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.versions_data = versions_data
        
        # Add support server button
        try:
            self.add_item(discord.ui.Button(label="Support Server", url="https://discord.gg/vXhwuxJk88", style=discord.ButtonStyle.link))
        except:
            pass
        
        # Add bot invite link if available
        try:
            invite_url = getattr(self.bot, 'invite_url', None)
            if invite_url:
                self.add_item(discord.ui.Button(label="Invite Bot", url=invite_url, style=discord.ButtonStyle.link))
        except:
            pass
    
    def create_roadmap_embed(self):
        embed = discord.Embed(
            title="🗺️ Bot Roadmap",
            description="Gelecekte eklenecek özellikler ve geliştirmeler.",
            color=discord.Color.blue()
        )
        
        # Current version
        embed.add_field(
            name="🔄 Mevcut Sürüm",
            value=f"v{self.versions_data['current_version']}",
            inline=False
        )
        
        # Upcoming features
        if "upcoming" in self.versions_data and self.versions_data["upcoming"]:
            upcoming_text = "\n".join([f"• {feature}" for feature in self.versions_data["upcoming"]])
            embed.add_field(name="🚀 Gelecek Özellikler", value=upcoming_text, inline=False)
        else:
            embed.add_field(name="🚀 Gelecek Özellikler", value="Henüz planlanan bir özellik yok.", inline=False)
        
        # Planned versions
        if "planned_versions" in self.versions_data and self.versions_data["planned_versions"]:
            versions_text = "\n".join([f"• **v{v['version']}** - {v['description']}" for v in self.versions_data["planned_versions"]])
            embed.add_field(name="📅 Planlanan Sürümler", value=versions_text, inline=False)
        
        # Add footer with bot name
        embed.set_footer(text=f"{self.bot.user.name} | Roadmap", icon_url=self.bot.user.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        
        return embed


# Channel select menu for changelog settings
class ChangelogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, placeholder="Changelog kanalı seçin"):
        super().__init__(
            channel_types=[discord.ChannelType.text],
            placeholder=placeholder,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Seçilen kanalı DB'ye kaydet
        channel = self.values[0]
        mongo_db = initialize_mongodb()
        
        # Ayarı güncelle
        mongo_db.settings.update_one(
            {"guild_id": str(interaction.guild.id)},
            {"$set": {"changelog_channel": channel.id}},
            upsert=True
        )
        
        # Kullanıcıya bilgi ver
        await interaction.response.send_message(
            embed=create_embed(f"✅ Changelog kanalı {channel.mention} olarak ayarlandı.", discord.Color.green()),
            ephemeral=True
        )


class BotSettings(commands.Cog):
    """🤖 Bot Settings System
    
    Comprehensive system for configuring bot behavior and settings:
    • 🔧 Prefix settings
    • 🎭 Bot appearance
    • 📊 Performance options
    • 👑 Developer options
    • 📝 Version info and updates
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        self.versions_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'versions.json')
    
    # REMOVED: These commands are now integrated into the unified /settings panel
    # @commands.group(name='botsettings')
    # async def botsettings(self, ctx):
    #     """Bot settings command group"""
    #     if ctx.invoked_subcommand is None:
    #         await ctx.send_help(ctx.command)

    # # Önceki server_panel komutunu yeniden adlandır
    # @botsettings.command(name="server", description="Sunucu ayarlarını aç")
    # @commands.has_permissions(administrator=True)
    # async def settings_panel(self, ctx):
    #     """Sunucu ayarları panelini açar"""
    #     # Sunucu ayarları için settings modulu fonksiyonunu çağır
    #     settings_cog = self.bot.get_cog('Settings')
    #     if settings_cog:
    #         await settings_cog.open_settings_panel(ctx)
    #     else:
    #         await ctx.send(embed=create_embed("\u274c Sunucu ayarları modülü yüklenemedi.", discord.Color.red()))
    
    # # REMOVED: These commands are now integrated into the unified /settings panel
    # # @botsettings.command(name="changelog", description="Show version history and updates")
    # # @commands.has_permissions(administrator=True)
    # # async def changelogs(self, ctx):
    # #     await self.changelog(ctx)
    
    # # # Changelog alt komutu
    # # async def changelog(self, ctx):
    # #     """Show bot changelog for all versions"""
    # #     try:
    # #         versions_data = self.get_versions_data()
    # #         
    # #         # Find current version data
    # #         current_version_data = None
    # #         for version in versions_data["versions"]:
    # #             if version["version"] == versions_data["current_version"]:
    # #                 current_version_data = version
    # #                 break
    # #         
    # #         if not current_version_data:
    # #             return await ctx.send(
    # #                 embed=create_embed("\u274c Mevcut sürüm bilgisi bulunamadı.", discord.Color.red()),
    # #                 ephemeral=True
    # #             )
    # #         
    # #         # Create changelog view
    # #         view = ChangelogView(self.bot, versions_data)
    # #         
    # #         # Create initial embed for current version
    # #         embed = view.create_changelog_embed(current_version_data)
    # #         
    # #         # Send changelog as ephemeral message
    # #         await ctx.send(embed=embed, view=view, ephemeral=True)
    # #         
    # #     except Exception as e:
    # #         logger.error(f"Error showing changelog: {e}")
    # #         await ctx.send(
    # #             embed=create_embed(f"Changelog gösterilirken bir hata oluştu: {str(e)}", discord.Color.red()),
    # #             ephemeral=True
    # #         )
    
    # # # Roadmap komutu
    # # @botsettings.command(name="roadmap", description="Show future features and planned releases")
    # # async def roadmap(self, ctx):
    # #     """Show bot roadmap with upcoming features"""
    # #     try:
    # #         versions_data = self.get_versions_data()
    # #         
    # #         # Create roadmap view
    # #         view = RoadmapView(self.bot, versions_data)
    # #         
    # #         # Create roadmap embed
    # #         embed = view.create_roadmap_embed()
    # #         
    # @commands.group(name='botsettings')
    # async def botsettings(self, ctx):
    #     """Bot settings command group"""
    #     if ctx.invoked_subcommand is None:
    #         await ctx.send_help(ctx.command)

    # Changelog için yardımcı fonksiyon
    def get_versions_data(self):
        """Load versions data from file"""
        try:
            with open(self.versions_file, 'r', encoding='utf-8') as f:
                versions_data = json.load(f)
            return versions_data
        except FileNotFoundError:
            logger.warning(f"Versions file not found at {self.versions_file}")
            # Create a basic structure
            versions_data = {
                "current_version": "1.0.0",
                "versions": [
                    {
                        "version": "1.0.0",
                        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "features": ["Başlangıç sürümü"]
                    }
                ],
                "upcoming": ["Yeni özellikler planlanmadı"]
            }
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.versions_file), exist_ok=True)
            # Write default file
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                json.dump(versions_data, f, indent=2, ensure_ascii=False)
            return versions_data
        except Exception as e:
            logger.error(f"Error loading versions data: {e}")
            return {
                "current_version": "1.0.0",
                "versions": [
                    {
                        "version": "1.0.0",
                        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "features": ["Başlangıç sürümü"]
                    }
                ],
                "upcoming": ["Yeni özellikler planlanmadı"]
            }

    
    # # Önceki server_panel komutunu yeniden adlandır
    # @botsettings.command(name="server", description="Sunucu ayarlarını aç")
    # @commands.has_permissions(administrator=True)
    # async def settings_panel(self, ctx):
    #     """Sunucu ayarları panelini açar"""
    #     # Sunucu ayarları için settings modulu fonksiyonunu çağır
    #     settings_cog = self.bot.get_cog('Settings')
    #     if settings_cog:
    #         await settings_cog.open_settings_panel(ctx)
    #     else:
    #         await ctx.send(embed=create_embed("\u274c Sunucu ayarları modülü yüklenemedi.", discord.Color.red()))
            
    # REMOVED: These commands are now integrated into the unified /settings panel
    # @botsettings.command(name="changelog", description="Show version history and updates")
    # @commands.has_permissions(administrator=True)
    # async def changelogs(self, ctx):
    #     await self.changelog(ctx)
    
    # # Changelog alt komutu
    # async def changelog(self, ctx):
    #     """Show bot changelog for all versions"""
    #     try:
    #         versions_data = self.get_versions_data()
    #         
    #         # Find current version data
    #         current_version_data = None
    #         for version in versions_data["versions"]:
    #             if version["version"] == versions_data["current_version"]:
    #                 current_version_data = version
    #                 break
    #         
    #         if not current_version_data:
    #             return await ctx.send(
    #                 embed=create_embed("\u274c Mevcut sürüm bilgisi bulunamadı.", discord.Color.red()),
    #                 ephemeral=True
    #             )
    #         
    #         # Create changelog view
    #         view = ChangelogView(self.bot, versions_data)
    #         
    #         # Create initial embed for current version
    #         embed = view.create_changelog_embed(current_version_data)
    #         
    #         # Send changelog as ephemeral message
    #         await ctx.send(embed=embed, view=view, ephemeral=True)
    #         
    #     except Exception as e:
    #         logger.error(f"Error showing changelog: {e}")
    #         await ctx.send(
    #             embed=create_embed(f"Changelog gösterilirken bir hata oluştu: {str(e)}", discord.Color.red()),
    #             ephemeral=True
    #         )
    
    # # Roadmap komutu
    # @botsettings.command(name="roadmap", description="Show future features and planned releases")
    # async def roadmap(self, ctx):
    #     """Show bot roadmap with upcoming features"""
    #     try:
    #         versions_data = self.get_versions_data()
    #         
    #         # Create roadmap view
    #         view = RoadmapView(self.bot, versions_data)
    #         
    #         # Create roadmap embed
    #         embed = view.create_roadmap_embed()
    #         
    #         # Send roadmap as ephemeral message
    #         await ctx.send(embed=embed, view=view, ephemeral=True)
    #         
    #     except Exception as e:
    #         logger.error(f"Error showing roadmap: {e}")
    #         await ctx.send(
    #             embed=create_embed(f"Roadmap gösterilirken bir hata oluştu: {str(e)}", discord.Color.red()),
    #             ephemeral=True
    #         )
    
    # # Send changelog komutu - Now integrated in /settings Updates & Changelog section
    # @botsettings.command(name="send_changelog", description="Send changelog to a specific channel")
    # @commands.has_permissions(administrator=True)
    # async def send_changelog(self, ctx):
    #     """Send changelog to a channel"""
    #     try:
    #         versions_data = self.get_versions_data()
    #         
    #         # Create embed for channel selection
    #         embed = discord.Embed(
    #             title="\ud83d\udce2 Changelog Gönderimi",
    #             description="Changelog'u göndermek için bir kanal seçin.",
    #             color=discord.Color.blue()
    #         )
    #         
    #         # Check if there's a saved channel
    #         saved_channel_id = None
    #         guild_settings = self.mongo_db.settings.find_one({"guild_id": str(ctx.guild.id)})
    #         if guild_settings and "changelog_channel" in guild_settings:
    #             saved_channel_id = guild_settings["changelog_channel"]
    #             saved_channel = ctx.guild.get_channel(saved_channel_id)
    #             if saved_channel:
    #                 embed.add_field(
    #                     name="\ud83d\udccc Kayıtlı Kanal",
    #                     value=f"Kaydedilen kanal: {saved_channel.mention}\nFarklı bir kanal seçmek için aşağıdaki menüyü kullanın.",
    #                     inline=False
    #                 )
    #         
    #         # Create a view with channel select
    #         view = discord.ui.View(timeout=180)
    #         
    #         # Add channel select
    #         channel_select = ChangelogChannelSelect()
    #         view.add_item(channel_select)
    #         
    #         # Add button to send to saved channel if available
    #         if saved_channel_id:
    #             saved_channel = ctx.guild.get_channel(saved_channel_id)
    #             if saved_channel:
    #                 async def send_to_saved_callback(interaction):
    #                     if interaction.user != ctx.author:
    #                         return await interaction.response.send_message("Bu butonu kullanamazsınız.", ephemeral=True)
    #                     
    #                     # Find current version data
    #                     current_version_data = None
    #                     for version in versions_data["versions"]:
    #                         if version["version"] == versions_data["current_version"]:
    #                             current_version_data = version
    #                             break
    #                     
    #                     if not current_version_data:
    #                         return await interaction.response.send_message(
    #                             embed=create_embed("\u274c Mevcut sürüm bilgisi bulunamadı.", discord.Color.red()),
    #                             ephemeral=True
    #                         )
    #                     
    #                     # Create changelog view (non-ephemeral for channel message)
    #                     channel_view = ChangelogView(self.bot, versions_data)
    #                     
    #                     # Create embed for current version
    #                     changelog_embed = channel_view.create_changelog_embed(current_version_data)
    #                     
    #                     # Send to channel
    #                     try:
    #                         await saved_channel.send(embed=changelog_embed, view=channel_view)
    #                         await interaction.response.send_message(
    #                             embed=create_embed(f"\u2705 Changelog {saved_channel.mention} kanalına gönderildi.", discord.Color.green()),
    #                             ephemeral=True
    #                         )
    #                     except Exception as e:
    #                         await interaction.response.send_message(
    #                             embed=create_embed(f"\u274c Changelog gönderilirken hata oluştu: {str(e)}", discord.Color.red()),
    #                             ephemeral=True
    #                         )
    #                 
    #                 # Add button
    #                 send_to_saved_button = discord.ui.Button(
    #                     label=f"Kayıtlı Kanala Gönder", 
    #                     style=discord.ButtonStyle.success, 
    #                     emoji="\ud83d\udce2"
    #                 )
    #                 send_to_saved_button.callback = send_to_saved_callback
    #                 view.add_item(send_to_saved_button)
    #         
    #         # Send selection message
    #         await ctx.send(embed=embed, view=view, ephemeral=True)
    #         
    #     except Exception as e:
    #         logger.error(f"Error preparing changelog send: {e}")
    #         await ctx.send(
    #             embed=create_embed(f"Changelog gönderimi hazırlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
    #             ephemeral=True
    #         )
    
    # REMOVED: This command is now integrated into the unified /settings panel (Advanced Settings section)
    # @botsettings.command(name="update_version", description="Update current bot version")
    # @commands.is_owner()
    # async def update_version(self, ctx, version: str = None):
    #     """Update current bot version"""
    #     try:
    #         versions_data = self.get_versions_data()
    #         
    #         # Check if version is provided
    #         if not version:
    #             # Create a list of available versions
    #             versions_list = "\n".join([f"\u2022 `{v['version']}` - {v['date']}" for v in versions_data["versions"]])
    #             embed = discord.Embed(
    #                 title="\ud83d\udd04 Sürüm Güncelleme",
    #                 description=f"Lütfen güncellemek istediğiniz sürümü belirtin.\n\n**Mevcut sürüm:** `v{versions_data['current_version']}`\n\n**Kullanılabilir Sürümler:**\n{versions_list}",
    #                 color=discord.Color.blue()
    #             )
    #             embed.set_footer(text="Kullanım: /settings changelogs update_version <sürüm>")
    #             return await ctx.send(embed=embed, ephemeral=True)
    #         
    #         # Check if version exists
    #         version_exists = False
    #         for v in versions_data["versions"]:
    #             if v["version"] == version:
    #                 version_exists = True
    #                 version_data = v
    #                 break
    #         
    #         if not version_exists:
    #             embed = discord.Embed(
    #                 title="\u274c Sürüm Bulunamadı",
    #                 description=f"Sürüm `{version}` veritabanında bulunamadı.",
    #                 color=discord.Color.red()
    #             )
    #             embed.set_footer(text="Mevcut sürümleri görmek için /settings changelogs update_version komutunu kullanın")
    #             return await ctx.send(embed=embed, ephemeral=True)
    #         
    #         # Update current version
    #         versions_data["current_version"] = version
    #         
    #         # Save to file
    #         try:
    #             with open(self.versions_file, 'w', encoding='utf-8') as f:
    #                 json.dump(versions_data, f, indent=2, ensure_ascii=False)
    #             
    #             # Create a success embed with version details
    #             embed = discord.Embed(
    #                 title="\u2705 Sürüm Güncellendi",
    #                 description=f"Bot sürümü başarıyla `v{version}` olarak güncellendi.",
    #                 color=discord.Color.green()
    #             )
    #             
    #             # Add version details
    #             if "features" in version_data and version_data["features"]:
    #                 features_text = "\n".join([f"\u2022 {feature}" for feature in version_data["features"][:5]])
    #                 if len(version_data["features"]) > 5:
    #                     features_text += f"\n\u2022 ... ve {len(version_data['features']) - 5} özellik daha"
    #                 embed.add_field(name="\u2728 Bu Sürümdeki Özellikler", value=features_text, inline=False)
    #             
    #             embed.set_footer(text=f"Sürüm Tarihi: {version_data['date']}")
    #             embed.timestamp = datetime.datetime.now()
    #             
    #             await ctx.send(embed=embed, ephemeral=True)
    #         except Exception as e:
    #             logger.error(f"Error updating version: {e}")
    #             embed = discord.Embed(
    #                 title="\u274c Hata",
    #                 description=f"Sürüm güncellenirken bir hata oluştu:\n```py\n{str(e)}\n```",
    #                 color=discord.Color.red()
    #             )
    #             await ctx.send(embed=embed, ephemeral=True)
    #         
    #     except Exception as e:
    #         logger.error(f"Error in update_version: {e}")
    #         await ctx.send(
    #             embed=create_embed(f"Sürüm güncellenirken bir hata oluştu: {str(e)}", discord.Color.red()),
    #             ephemeral=True
    #         )

    async def get_current_settings(self, guild_id):
        # This method is mentioned in the code but not implemented in the original file or the new file
        # It's left unchanged as it's mentioned in the code
        pass

class BotSettingsView(discord.ui.View):
    """Bot ayarları için ana görünüm"""
    
    def __init__(self, bot, ctx, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.mongo_db = initialize_mongodb()
        
    @discord.ui.button(label="Prefix Ayarla", style=discord.ButtonStyle.primary, emoji="📝", row=0)
    async def prefix_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bot prefix'ini ayarla"""
        await interaction.response.send_modal(PrefixModal(self.bot))
    
    @discord.ui.button(label="Bot Görünümü", style=discord.ButtonStyle.primary, emoji="🖼️", row=0)
    async def appearance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bot görünümünü ayarla"""
        # Sadece bot sahibi için
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Bu ayarı sadece bot sahibi değiştirebilir.", discord.Color.red()),
                ephemeral=True
            )
        
        await interaction.response.send_message(
            embed=create_embed("Bot görünümü ayarları:", discord.Color.blue()),
            view=BotAppearanceView(self.bot),
            ephemeral=True
        )
    
    @discord.ui.button(label="Performans Ayarları", style=discord.ButtonStyle.primary, emoji="⚙️", row=1)
    async def performance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Performans ayarlarını yapılandır"""
        await interaction.response.send_message(
            embed=create_embed("Performans ayarları yakında eklenecek.", discord.Color.blue()),
            ephemeral=True
        )
    
    @discord.ui.button(label="Geliştirici Seçenekleri", style=discord.ButtonStyle.danger, emoji="👑", row=1)
    async def developer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Geliştirici seçeneklerini aç"""
        # Sadece bot sahibi için
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            return await interaction.response.send_message(
                embed=create_embed("❌ Bu seçenekler sadece bot sahibi tarafından erişilebilir.", discord.Color.red()),
                ephemeral=True
            )
        
        await interaction.response.send_message(
            embed=create_embed("Geliştirici seçenekleri yakında eklenecek.", discord.Color.blue()),
            ephemeral=True
        )

class PrefixModal(discord.ui.Modal, title="Prefix Ayarla"):
    """Prefix ayarlamak için modal"""
    
    prefix = discord.ui.TextInput(
        label="Yeni Prefix",
        placeholder="Örn: ! veya .",
        required=True,
        min_length=1,
        max_length=5
    )
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.mongo_db = initialize_mongodb()
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Veritabanında prefix'i güncelle
            self.mongo_db["bot_settings"].update_one(
                {"_id": "prefix"},
                {"$set": {"value": self.prefix.value}},
                upsert=True
            )
            
            await interaction.response.send_message(
                embed=create_embed(f"✅ Bot prefix'i `{self.prefix.value}` olarak ayarlandı.", discord.Color.green()),
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error setting prefix: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Prefix ayarlanırken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class BotAppearanceView(discord.ui.View):
    """Bot görünümünü ayarlamak için view"""
    
    def __init__(self, bot, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        
    @discord.ui.button(label="Bot İsmini Değiştir", style=discord.ButtonStyle.primary, emoji="✏️")
    async def change_name_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bot ismini değiştir"""
        await interaction.response.send_modal(BotNameModal(self.bot))
    
    @discord.ui.button(label="Bot Avatarını Değiştir", style=discord.ButtonStyle.primary, emoji="🖼️")
    async def change_avatar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bot avatarını değiştir"""
        await interaction.response.send_message(
            embed=create_embed(
                "Avatar değiştirmek için bir resim URL'si gönderin veya bir resim ekleyin.\n\n"
                "**Not:** Bu işlem yavaş olabilir ve Discord API sınırlamalarına tabidir.",
                discord.Color.blue()
            ),
            ephemeral=True
        )

class BotNameModal(discord.ui.Modal, title="Bot İsmini Değiştir"):
    """Bot ismini değiştirmek için modal"""
    
    name = discord.ui.TextInput(
        label="Yeni İsim",
        placeholder="Bot'un yeni ismini girin",
        required=True,
        min_length=2,
        max_length=32
    )
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Bot ismini değiştir
            await self.bot.user.edit(username=self.name.value)
            
            await interaction.response.send_message(
                embed=create_embed(f"✅ Bot ismi `{self.name.value}` olarak değiştirildi.", discord.Color.green()),
                ephemeral=True
            )
            
        except discord.HTTPException as e:
            error_msg = "Discord API hatası: "
            if e.code == 50035:
                error_msg += "İsim uygun değil veya çok sık değiştirildi."
            else:
                error_msg += str(e)
            
            await interaction.response.send_message(
                embed=create_embed(f"❌ {error_msg}", discord.Color.red()),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error changing bot name: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"Bot ismi değiştirilirken bir hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

# Cog kurulumu
async def setup(bot):
    await bot.add_cog(BotSettings(bot))
    logger.info("Bot settings cog loaded")