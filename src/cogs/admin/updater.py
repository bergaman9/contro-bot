import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
import datetime
from typing import Dict, List, Optional, Union

# Consistent import paths
from utils.core.formatting import create_embed
from utils.database.connection import initialize_mongodb, is_db_available

# Configure logger
logger = logging.getLogger('updater')

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

class ChannelSelectMenu(discord.ui.Select):
    def __init__(self, channels: List[discord.TextChannel], placeholder="Changelog kanalı seçin"):
        options = [
            discord.SelectOption(
                label=channel.name, 
                value=str(channel.id),
                description=f"#{channel.name} kanalı"
            ) for channel in channels[:25]  # Discord max 25 options
        ]
        
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Get parent view
        view = self.view
        if not isinstance(view, SendChangelogView):
            return
        
        # Set the selected channel
        channel_id = int(self.values[0])
        channel = interaction.guild.get_channel(channel_id)
        
        if not channel:
            return await interaction.response.send_message(
                embed=create_embed("❌ Kanal bulunamadı.", discord.Color.red()),
                ephemeral=True
            )
        
        # Update the view with selected channel
        await view.set_channel(interaction, channel)

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
        
        # Create changelog embed
        embed = self.create_changelog_embed(version_data)
        
        # Update message
        await interaction.response.edit_message(embed=embed, view=self)
    
    def create_changelog_embed(self, version_data: Dict):
        # Create embed for changelog with a more attractive design
        embed = discord.Embed(
            title=f"📝 Contro Bot v{version_data['version']} - Changelog",
            description=f"📅 **Sürüm Tarihi:** {version_data['date']}",
            color=discord.Color.from_rgb(114, 137, 218)  # Discord blurple
        )
        
        # Add thumbnail
        try:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        except:
            pass
        
        # Add features with emoji and formatting
        if "features" in version_data and version_data["features"]:
            features_text = "\n".join([f"• {feature}" for feature in version_data["features"]])
            embed.add_field(name="✨ **Yeni Özellikler**", value=features_text, inline=False)
        
        # Add fixes with emoji and formatting
        if "fixes" in version_data and version_data["fixes"]:
            fixes_text = "\n".join([f"• {fix}" for fix in version_data["fixes"]])
            embed.add_field(name="🔧 **Hata Düzeltmeleri**", value=fixes_text, inline=False)
        
        # Add upcoming features with emoji and formatting
        if "upcoming" in version_data and version_data["upcoming"]:
            upcoming_text = "\n".join([f"• {feature}" for feature in version_data["upcoming"]])
            embed.add_field(name="🔮 **Yakında Gelecek**", value=upcoming_text, inline=False)
        
        # Set footer with version info and bot avatar
        try:
            embed.set_footer(text=f"Contro Bot v{version_data['version']} • Tüm sürümleri görmek için butonları kullanın", icon_url=self.bot.user.avatar.url)
        except:
            embed.set_footer(text=f"Contro Bot v{version_data['version']} • Tüm sürümleri görmek için butonları kullanın")
        
        return embed

class SendChangelogView(discord.ui.View):
    def __init__(self, bot, versions_data, channels, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.versions_data = versions_data
        self.versions = [v["version"] for v in versions_data["versions"]]
        self.current_version = versions_data["current_version"]
        self.selected_channel = None
        self.selected_version = self.current_version
        
        # Add support server button at the bottom
        self.support_button = discord.ui.Button(label="Support Server", url="https://discord.gg/vXhwuxJk88", style=discord.ButtonStyle.link, row=4)
        self.add_item(self.support_button)
        
        # Add channel select menu
        self.add_item(ChannelSelectMenu(channels))
        
        # Add version select
        options = []
        for version in reversed(self.versions):
            options.append(
                discord.SelectOption(
                    label=f"v{version}",
                    value=version,
                    description=f"Sürüm {version}",
                    default=version == self.current_version
                )
            )
        
        self.version_select = discord.ui.Select(
            placeholder="Sürüm seçin",
            min_values=1,
            max_values=1,
            options=options
        )
        self.version_select.callback = self.version_select_callback
        self.add_item(self.version_select)
        
        # Add send button (disabled initially)
        self.send_button = discord.ui.Button(
            label="Gönder",
            style=discord.ButtonStyle.success,
            disabled=True
        )
        self.send_button.callback = self.send_changelog
        self.add_item(self.send_button)
    
    async def version_select_callback(self, interaction: discord.Interaction):
        self.selected_version = self.version_select.values[0]
        
        # Enable send button if channel is also selected
        if self.selected_channel:
            self.send_button.disabled = False
        
        await interaction.response.edit_message(view=self)
    
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.selected_channel = channel
        
        # Enable send button if version is also selected
        if self.selected_version:
            self.send_button.disabled = False
        
        await interaction.response.edit_message(
            embed=create_embed(f"✅ Kanal seçildi: {channel.mention}\nSürüm: v{self.selected_version}", discord.Color.green()),
            view=self
        )
    
    async def send_changelog(self, interaction: discord.Interaction):
        if not self.selected_channel or not self.selected_version:
            return await interaction.response.send_message(
                embed=create_embed("❌ Kanal veya sürüm seçilmedi.", discord.Color.red()),
                ephemeral=True
            )
        
        # Find version data
        version_data = None
        for v in self.versions_data["versions"]:
            if v["version"] == self.selected_version:
                version_data = v
                break
        
        if not version_data:
            return await interaction.response.send_message(
                embed=create_embed("❌ Versiyon bilgisi bulunamadı.", discord.Color.red()),
                ephemeral=True
            )
        
        # Create changelog view
        changelog_view = ChangelogView(self.bot, self.versions_data)
        embed = changelog_view.create_changelog_embed(version_data)
        
        try:
            # Send changelog to selected channel
            await self.selected_channel.send(embed=embed, view=changelog_view)
            
            # Confirm to user
            await interaction.response.edit_message(
                embed=create_embed(
                    f"✅ Changelog başarıyla gönderildi: {self.selected_channel.mention}",
                    discord.Color.green()
                ),
                view=None
            )
        except Exception as e:
            logger.error(f"Error sending changelog: {e}")
            await interaction.response.send_message(
                embed=create_embed(f"❌ Changelog gönderilirken hata oluştu: {str(e)}", discord.Color.red()),
                ephemeral=True
            )

class RoadmapView(discord.ui.View):
    def __init__(self, bot, versions_data):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.versions_data = versions_data
        
        # Add support server button
        self.add_item(discord.ui.Button(label="Support Server", url="https://discord.gg/vXhwuxJk88", style=discord.ButtonStyle.link))
        
        # Add invite bot button
        try:
            invite_url = f"https://discord.com/api/oauth2/authorize?client_id={bot.application_id}&permissions=8&scope=bot"
            self.add_item(discord.ui.Button(label="Invite Bot", url=invite_url, style=discord.ButtonStyle.link))
        except:
            pass
    
    def create_roadmap_embed(self):
        # Create roadmap embed with all upcoming features from all versions
        embed = discord.Embed(
            title="🗺️ Contro Bot - Yol Haritası",
            description="Aşağıda yakında eklenecek özellikler ve geliştirmeler listelenmiştir. Bot geliştirme sürecimiz devam ediyor!",
            color=discord.Color.from_rgb(114, 137, 218)  # Discord blurple
        )
        
        # Add thumbnail
        try:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        except:
            pass
        
        # Group upcoming features by version
        for version in reversed(self.versions_data["versions"]):
            if "upcoming" in version and version["upcoming"]:
                upcoming_text = "\n".join([f"• {feature}" for feature in version["upcoming"]])
                embed.add_field(
                    name=f"🚀 **v{version['version']} Sonrası Planlar**", 
                    value=upcoming_text, 
                    inline=False
                )
        
        # Set footer with bot avatar
        try:
            embed.set_footer(text=f"Güncel Sürüm: v{self.versions_data['current_version']} • Öneri ve fikirlerinizi Support Server'da paylaşabilirsiniz", icon_url=self.bot.user.avatar.url)
        except:
            embed.set_footer(text=f"Güncel Sürüm: v{self.versions_data['current_version']} • Öneri ve fikirlerinizi Support Server'da paylaşabilirsiniz")
        
        return embed

class Updater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        self.versions_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'versions.json')
        
    def get_versions_data(self):
        """Load versions data from file"""
        try:
            with open(self.versions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading versions data: {e}")
            # Return a basic structure if file can't be loaded
            return {
                "versions": [
                    {
                        "version": "1.0.0",
                        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "features": ["Basic functionality"],
                        "fixes": [],
                        "upcoming": ["More features"]
                    }
                ],
                "current_version": "1.0.0"
            }
    
    # REMOVED: These commands are now integrated into the unified /settings panel (Updates & Changelog section)
    # @commands.hybrid_command(name="changelog", description="Bot sürüm notlarını görüntüleyin")
    # async def changelog(self, ctx):
    #     """Show bot changelog"""
    #     try:
    #         embed = discord.Embed(
    #             title="📋 Bot Changelog",
    #             description="Son güncellemeler ve değişiklikler",
    #             color=discord.Color.blue()
    #         )
    #         
    #         # Try to get changelog from version manager
    #         changelog_data = self.version_manager.get_changelog_data()
    #         
    #         if changelog_data:
    #             versions = sorted(changelog_data.keys(), key=lambda x: [int(i) for i in x.split('.')], reverse=True)[:5]
    #             
    #             for version in versions:
    #                 changes = changelog_data[version]
    #                 field_value = ""
    #                 
    #                 for category, items in changes.items():
    #                     if items:
    #                         field_value += f"**{category}:**\n"
    #                         for item in items[:3]:  # Limit items per category
    #                             field_value += f"• {item}\n"
    #                 
    #                 if field_value:
    #                     # Ensure field value doesn't exceed Discord's limit
    #                     if len(field_value) > 1024:
    #                         field_value = field_value[:1021] + "..."
    #                         
    #                     embed.add_field(
    #                         name=f"Version {version}",
    #                         value=field_value,
    #                         inline=False
    #                     )
    #         else:
    #             embed.description = "Changelog verisi bulunamadı."
    #         
    #         await ctx.send(embed=embed)
    #         
    #     except Exception as e:
    #         logger.error(f"Error in changelog command: {e}")
    #         await ctx.send("Changelog gösterilirken bir hata oluştu.")

    # @commands.hybrid_command(name="send_changelog", description="Belirtilen kanala changelog gönder")
    # @commands.has_permissions(administrator=True)
    # async def send_changelog(self, ctx, channel: discord.TextChannel = None):
    #     """Send changelog to specified channel"""
    #     try:
    #         target_channel = channel or ctx.channel
    #         
    #         # Create changelog embed
    #         embed = discord.Embed(
    #             title="📋 Bot Güncelleme Notları",
    #             description="Son sürüm değişiklikleri ve yenilikler",
    #             color=discord.Color.blue(),
    #             timestamp=discord.utils.utcnow()
    #         )
    #         
    #         # Get changelog data
    #         changelog_data = self.version_manager.get_changelog_data()
    #         current_version = self.version_manager.get_current_version()
    #         
    #         if changelog_data and current_version in changelog_data:
    #             changes = changelog_data[current_version]
    #             
    #             for category, items in changes.items():
    #                 if items:
    #                     field_value = "\n".join([f"• {item}" for item in items[:5]])
    #                     if len(items) > 5:
    #                         field_value += f"\n... ve {len(items) - 5} değişiklik daha"
    #                     
    #                     # Ensure field value doesn't exceed Discord's limit
    #                     if len(field_value) > 1024:
    #                         field_value = field_value[:1021] + "..."
    #                         
    #                     embed.add_field(
    #                         name=category,
    #                         value=field_value,
    #                         inline=False
    #                     )
    #         
    #         embed.set_footer(text=f"Version {current_version}")
    #         
    #         # Send to target channel
    #         await target_channel.send(embed=embed)
    #         
    #         # Confirm to user
    #         if target_channel != ctx.channel:
    #             await ctx.send(f"✅ Changelog {target_channel.mention} kanalına gönderildi!")
    #             
    #     except discord.Forbidden:
    #         await ctx.send("❌ Bu kanala mesaj gönderme iznim yok!")
    #     except Exception as e:
    #         logger.error(f"Error sending changelog: {e}")
    #         await ctx.send("❌ Changelog gönderilirken bir hata oluştu.")

    # @commands.hybrid_command(name="update_version", description="Bot sürüm bilgilerini güncelle")
    # @commands.is_owner()
    # async def update_version(self, ctx, version: str, *, changes: str = None):
    #     """Update bot version (owner only)"""
    #     try:
    #         # Validate version format
    #         import re
    #         if not re.match(r'^\d+\.\d+\.\d+$', version):
    #             return await ctx.send("❌ Geçersiz sürüm formatı! Format: X.Y.Z (örn: 1.2.3)")
    #         
    #         # Parse changes if provided
    #         changelog_entry = {}
    #         if changes:
    #             lines = changes.strip().split('\n')
    #             current_category = "Değişiklikler"
    #             
    #             for line in lines:
    #                 line = line.strip()
    #                 if line.endswith(':'):
    #                     current_category = line[:-1]
    #                     changelog_entry[current_category] = []
    #                 elif line.startswith('-') or line.startswith('•'):
    #                     if current_category not in changelog_entry:
    #                         changelog_entry[current_category] = []
    #                     changelog_entry[current_category].append(line[1:].strip())
    #         
    #         # Update version
    #         success = self.version_manager.update_version(version, changelog_entry if changelog_entry else None)
    #         
    #         if success:
    #             embed = discord.Embed(
    #                 title="✅ Sürüm Güncellendi",
    #                 description=f"Bot sürümü **{version}** olarak güncellendi!",
    #                 color=discord.Color.green()
    #             )
    #             
    #             if changelog_entry:
    #                 embed.add_field(
    #                     name="Değişiklikler",
    #                     value="Changelog kaydedildi",
    #                     inline=False
    #                 )
    #             
    #             await ctx.send(embed=embed)
    #         else:
    #             await ctx.send("❌ Sürüm güncellenirken bir hata oluştu!")
    #             
    #     except Exception as e:
    #         logger.error(f"Error updating version: {e}")
    #         await ctx.send(f"❌ Hata: {str(e)}")
    
    @commands.hybrid_command(name="roadmap", description="Bot yol haritasını görüntüleyin")
    @commands.is_owner()
    async def roadmap(self, ctx):
        """Show bot roadmap with upcoming features"""
        versions_data = self.get_versions_data()
        
        # Create roadmap view
        view = RoadmapView(self.bot, versions_data)
        
        # Create roadmap embed
        embed = view.create_roadmap_embed()
        
        # Send roadmap as ephemeral message
        await ctx.send(embed=embed, view=view, ephemeral=True)

# Setup function
async def setup(bot):
    await bot.add_cog(Updater(bot))
    logger.info("Updater cog loaded")
