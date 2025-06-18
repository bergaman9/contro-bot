import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
import json
import os
import logging
from typing import Optional, Dict, Any, List

from utils.core.formatting import create_embed
from utils.database.db_manager import db_manager
from utils.setup.views import MainSetupView, BusinessCommandsView
from utils.setup.templates import get_builtin_template, get_emojis, get_headers
from utils.content_loader import load_content
from utils.setup.views import AnalyticsView, TemplateManagementView
from utils.database.content_manager import content_manager
from utils.core.content_loader import async_load_content, async_set_content

class ServerSetup(commands.Cog):
    """Sunucu kurulum ve yönetim araçları - Owner only"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        
        # JSON dosya yolları
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'templates')
        self.format_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'format.json')
        
        # Dizinleri oluştur
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.format_file_path), exist_ok=True)
        
        # Format değişkenlerini yükle
        self.format_variables = self.load_format_variables()
        
    async def cog_check(self, ctx):
        """Sadece bot sahibi bu komutları kullanabilir"""
        return await self.bot.is_owner(ctx.author)
    
    async def cog_load(self):
        """Cog yüklendiğinde database bağlantısını kur"""
        self.db = db_manager.get_database()
    
    @app_commands.command(name="setup", description="Comprehensive server setup and management panel")
    async def setup_panel(self, interaction: discord.Interaction):
        """Opens the main setup panel - uses views from utils/setup"""
        embed = discord.Embed(
            title="🛠️ Comprehensive Server Setup Panel",
            description="Access all server management tools from one place:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🎯 Main Features",
            value=(
                "🏗️ **Server Structure** - Automatic setup with templates\n"
                "📝 **Content Management** - Rules, announcements, embeds\n"
                "🤖 **Bot Integration** - Mass bot addition\n"
                "🎨 **Customization** - Roles, permissions, emoji styles\n"
                "📊 **Analytics & Maintenance** - Statistics, description updates\n"
                "💾 **Template Management** - Save, load, share\n"
                "🏢 **Business Commands** - Bionluk integration\n"
                "📥 **Discord Template Import** - Import ready templates"
            ),
            inline=False
        )
        embed.set_footer(text="Select an option to continue")
        
        # Create MainSetupView with English language
        view = MainSetupView(self.bot, language="en")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    # region Format Variables System
    def load_format_variables(self):
        """Format değişkenlerini JSON dosyasından yükler"""
        try:
            if os.path.exists(self.format_file_path):
                with open(self.format_file_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            
            # Varsayılan format yapısı
            default_format = {
                "roles": {
                    "admin": "Yönetici", "sup_mod": "Süper Moderatör", "emektar": "Emektar",
                    "mod": "Moderatör", "trial_mod": "Deneme Moderatör", "organizer": "Organizatör",
                    "support": "Destek", "bot": "Bot", "vip": "VIP", "booster": "Server Booster",
                    "member": "Üye", "unregistered_member": "Kayıtsız Üye", "bronz": "Bronz",
                    "silver": "Gümüş", "gold": "Altın", "tritium": "Trityum",
                    "diamond": "Elmas", "mudavim": "Müdavim", "sleep": "Uykucu", "dj": "DJ"
                },
                "channels": {
                    "rules": "📜・kurallar", "roles": "🎭・roller", "support": "🎫・destek",
                    "general": "💬・sohbet", "giveaways": "🎉・çekilişler", "games": "🎮・oyunlar",
                    "commands": "🤖・komutlar", "temporary": "➕ kanal oluştur",
                    "streams": "📺・yayınlar", "announcements": "📢・duyurular",
                    "activity": "🥳 Etkinlik", "forum": "🧠・tartışmalar"
                },
                "users": {}
            }
            self.save_format_variables(default_format)
            return default_format
        except Exception as e:
            logging.error(f"Format değişkenleri yüklenirken hata: {e}")
            return {"roles": {}, "channels": {}, "users": {}}

    def save_format_variables(self, format_variables=None):
        """Format değişkenlerini JSON dosyasına kaydeder"""
        if format_variables is None:
            format_variables = self.format_variables
        try:
            with open(self.format_file_path, 'w', encoding='utf-8') as file:
                json.dump(format_variables, file, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logging.error(f"Format değişkenleri kaydedilirken hata: {e}")
            return False

    def get_format_mentions(self, guild):
        """Sunucudan tüm format değişkenleri için mention'ları oluşturur"""
        format_mentions = {}
        
        # Roller
        for role_code, role_name in self.format_variables.get("roles", {}).items():
            role = discord.utils.get(guild.roles, name=role_name)
            format_mentions[role_code] = role.mention if role else f"@{role_name}"
        
        # Kanallar
        for channel_code, channel_name in self.format_variables.get("channels", {}).items():
            channel = discord.utils.get(guild.channels, name=channel_name)
            format_mentions[channel_code] = channel.mention if channel else f"#{channel_name}"
        
        # Kullanıcılar
        for user_code, user_id in self.format_variables.get("users", {}).items():
            user = guild.get_member(int(user_id)) if user_id.isdigit() else None
            format_mentions[user_code] = user.mention if user else f"@{user_code}"
        
        format_mentions["guild_id"] = guild.id
        
        # Destek kanalı için alias
        if "destek" not in format_mentions and "support" in format_mentions:
            format_mentions["destek"] = format_mentions["support"]
        
        return format_mentions
    # endregion

    # region Template System
    def save_template(self, name: str, template_data: dict, language: str = "tr"):
        """Template'i JSON dosyasına kaydeder"""
        try:
            filename = f"{name}_{language}.json"
            filepath = os.path.join(self.templates_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(template_data, file, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logging.error(f"Template kaydedilirken hata: {e}")
            return False

    def load_template(self, name: str, language: str = "tr"):
        """Template'i JSON dosyasından yükler"""
        try:
            filename = f"{name}_{language}.json"
            filepath = os.path.join(self.templates_dir, filename)
            
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as file:
                    return json.load(file)
            return None
        except Exception as e:
            logging.error(f"Template yüklenirken hata: {e}")
            return None

    def get_available_templates(self):
        """Mevcut template'leri listeler"""
        templates = []
        try:
            if os.path.exists(self.templates_dir):
                for filename in os.listdir(self.templates_dir):
                    if filename.endswith('.json'):
                        template_name = filename.replace('.json', '')
                        templates.append(template_name)
            return templates
        except Exception as e:
            logging.error(f"Template'ler listelenirken hata: {e}")
            return []

    async def import_discord_template(self, template_code: str, guild):
        """Discord template kodundan sunucu yapısını import eder"""
        try:
            template = await self.bot.fetch_template(template_code)
            
            # Template bilgilerini al
            template_data = {
                "name": template.name,
                "description": template.description,
                "categories": [],
                "roles": []
            }
            
            # Rolleri çevir
            for role_data in template.serialized_source_guild.get("roles", []):
                if role_data["name"] != "@everyone":
                    template_data["roles"].append({
                        "name": role_data["name"],
                        "color": role_data.get("color", 0),
                        "hoist": role_data.get("hoist", False),
                        "mentionable": role_data.get("mentionable", False),
                        "permissions": role_data.get("permissions", 0)
                    })
            
            # Kanalları ve kategorileri çevir
            channels_data = template.serialized_source_guild.get("channels", [])
            categories = {}
            
            # Önce kategorileri bul
            for channel in channels_data:
                if channel["type"] == 4:  # Category
                    categories[channel["id"]] = {
                        "name": channel["name"],
                        "channels": []
                    }
            
            # Sonra kanalları kategorilere ekle
            for channel in channels_data:
                if channel["type"] in [0, 2]:  # Text or Voice
                    channel_info = {
                        "name": channel["name"],
                        "type": "text" if channel["type"] == 0 else "voice"
                    }
                    
                    parent_id = channel.get("parent_id")
                    if parent_id and parent_id in categories:
                        categories[parent_id]["channels"].append(channel_info)
                    else:
                        # Kategorisiz kanallar için genel kategori
                        if "Genel" not in [cat["name"] for cat in template_data["categories"]]:
                            template_data["categories"].append({
                                "name": "Genel",
                                "verified_only": False,
                                "channels": []
                            })
                        template_data["categories"][-1]["channels"].append(channel_info)
            
            # Kategorileri template'e ekle
            for cat_data in categories.values():
                template_data["categories"].append({
                    "name": cat_data["name"],
                    "verified_only": False,
                    "channels": cat_data["channels"]
                })
            
            return template_data
        except Exception as e:
            logging.error(f"Discord template import hatası: {e}")
            return None
    # endregion

    # region Server Structure Management
    async def clear_guild(self, guild):
        """Tüm kanalları ve kategorileri temizle"""
        for channel in guild.channels:
            try:
                await channel.delete()
                await asyncio.sleep(0.3)
            except discord.HTTPException:
                continue

    async def create_server_structure(self, guild, template_data: dict, language: str = "tr"):
        """Template'den sunucu yapısını oluşturur"""
        try:
            # Verified rolü oluştur
            verified_role_name = "Doğrulandı" if language == "tr" else "Verified"
            verified_role = await guild.create_role(name=verified_role_name, color=discord.Color.green())
            
            # Rolleri oluştur
            for role_data in template_data.get("roles", []):
                try:
                    await guild.create_role(
                        name=role_data["name"],
                        color=discord.Color(role_data.get("color", 0)),
                        hoist=role_data.get("hoist", False),
                        mentionable=role_data.get("mentionable", False)
                    )
                    await asyncio.sleep(0.2)
                except Exception as e:
                    logging.error(f"Rol oluşturma hatası {role_data['name']}: {e}")
            
            # Kategorileri ve kanalları oluştur
            for category_data in template_data.get("categories", []):
                try:
                    category = await guild.create_category(category_data["name"])
                    
                    # Kategori izinlerini ayarla
                    if category_data.get("verified_only"):
                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(view_channel=False),
                            verified_role: discord.PermissionOverwrite(view_channel=True)
                        }
                        await category.edit(overwrites=overwrites)
                    
                    # Kanalları oluştur
                    for channel_data in category_data.get("channels", []):
                        try:
                            if channel_data["type"] == "text":
                                await guild.create_text_channel(channel_data["name"], category=category)
                            elif channel_data["type"] == "voice":
                                await guild.create_voice_channel(channel_data["name"], category=category)
                            await asyncio.sleep(0.2)
                        except Exception as e:
                            logging.error(f"Kanal oluşturma hatası {channel_data['name']}: {e}")
                    
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logging.error(f"Kategori oluşturma hatası {category_data['name']}: {e}")
            
            return True
        except Exception as e:
            logging.error(f"Sunucu yapısı oluşturma hatası: {e}")
            return False
    # endregion

    # region Utility Functions
    async def create_invite(self, guild):
        """Sunucu için davet linki oluşturur"""
        try:
            for channel in guild.text_channels:
                try:
                    invite = await channel.create_invite(max_age=0, max_uses=0, unique=False)
                    return invite.url
                except discord.Forbidden:
                    continue
            return "Davet linki oluşturulamadı. Bot için 'Davet Oluştur' yetkisi gerekiyor."
        except Exception as e:
            logging.error(f"Davet linki oluşturulurken hata: {e}")
            return "Davet linki oluşturulamadı."

    async def update_all_channel_descriptions(self, guild, progress_message=None):
        """Tüm kanalların açıklamalarını günceller"""
        updated_count = 0
        text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)]
        
        for i, channel in enumerate(text_channels):
            try:
                if progress_message:
                    await progress_message.edit(content=f"İşleniyor: {channel.name} ({i + 1}/{len(text_channels)})")
                
                # Varsayılan açıklamalar
                default_descriptions = {
                    "🎉・çekilişler": "Çekilişlerin düzenlendiği kanal.",
                    "🎫・destek": "Üyelerin ticket açarak destek alabildiği kanal.",
                    "🎮・oyunlar": "Oyunlar hakkında sohbet kanalı.",
                    "📺・yayınlar": "Twitch yayınlarının duyurulduğu kanal.",
                    "📢・duyurular": "Sunucu hakkında yapılan duyuruları buradan takip edebilirsiniz.",
                    "🧠・tartışmalar": "Çeşitli konularda tartışmak için konular açabilirsiniz.",
                    "🤖・komutlar": "Komutları kullanabileceğiniz kanal.",
                    "📜・kurallar": "Sunucu kurallarını buradan okuyabilirsiniz.",
                    "💬・sohbet": "Kurallar çerçevesinde her konudan konuşabilirsiniz.",
                    "🎭・roller": "Reaksiyon rollerinizi alabileceğiniz kanal.",
                    "👋・hoş-geldin": "Sunucuya yeni katılan üyeleri karşıladığımız kanal.",
                    "📷・görseller": "Görsel paylaşabilirsiniz.",
                    "🎥・videolar": "Video paylaşabilirsiniz.",
                    "🍿・dizi-film": "Dizi ve filmler üzerine konuşabilirsiniz.",
                    "🎵・müzik": "Müzik çalmak için komutları kullanabilirsiniz."
                }
                
                description = default_descriptions.get(channel.name, f"Kanal: {channel.name}")
                
                # Kanal açıklamasını güncelle
                await channel.edit(topic=description)
                updated_count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logging.error(f"Kanal {channel.name} açıklaması güncellenirken hata: {e}")
                continue
        
        return updated_count
    # endregion

    # region Content Management Commands
    @commands.group(name="content", description="Manage server content")
    @commands.has_permissions(manage_guild=True)
    async def content_group(self, ctx):
        """Content management command group"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @content_group.command(name="view", description="View current content")
    async def content_view(self, ctx, content_key: str):
        """View current content for a specific key"""
        guild_id = str(ctx.guild.id)
        
        # Initialize content manager if needed
        if not content_manager._initialized:
            await content_manager.initialize()
        
        content = await async_load_content(guild_id, content_key)
        
        # Check if content is too long for Discord
        if len(content) > 1900:
            # Split into multiple messages
            chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]
            for i, chunk in enumerate(chunks):
                embed = discord.Embed(
                    title=f"📄 Content: {content_key} (Part {i+1}/{len(chunks)})",
                    description=f"```md\n{chunk}\n```",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title=f"📄 Content: {content_key}",
                description=f"```md\n{content}\n```",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Use /content edit to modify this content")
            await ctx.send(embed=embed)
    
    @content_group.command(name="edit", description="Edit server content")
    async def content_edit(self, ctx, content_key: str, *, new_content: str):
        """Edit content for a specific key"""
        guild_id = str(ctx.guild.id)
        
        # Initialize content manager if needed
        if not content_manager._initialized:
            await content_manager.initialize()
        
        success = await async_set_content(guild_id, content_key, new_content)
        
        if success:
            embed = discord.Embed(
                title="✅ Content Updated",
                description=f"Successfully updated content for `{content_key}`",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Update Failed",
                description=f"Failed to update content for `{content_key}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @content_group.command(name="list", description="List all available content keys")
    async def content_list(self, ctx):
        """List all available content keys"""
        guild_id = str(ctx.guild.id)
        
        # Initialize content manager if needed
        if not content_manager._initialized:
            await content_manager.initialize()
        
        all_contents = await content_manager.get_all_contents(guild_id)
        
        embed = discord.Embed(
            title="📚 Available Content Keys",
            description="Use `/content view <key>` to view content\nUse `/content edit <key> <content>` to edit",
            color=discord.Color.blue()
        )
        
        content_list = []
        for key in sorted(all_contents.keys()):
            content_preview = all_contents[key][:50] + "..." if len(all_contents[key]) > 50 else all_contents[key]
            content_list.append(f"• **{key}**: {content_preview}")
        
        embed.add_field(
            name="Content Keys",
            value="\n".join(content_list) if content_list else "No content available",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @content_group.command(name="import", description="Import default content")
    @commands.is_owner()
    async def content_import(self, ctx):
        """Import all default content for this server"""
        guild_id = str(ctx.guild.id)
        
        # Initialize content manager if needed
        if not content_manager._initialized:
            await content_manager.initialize()
        
        embed = discord.Embed(
            title="📥 Importing Default Content",
            description="Importing all default content files...",
            color=discord.Color.blue()
        )
        msg = await ctx.send(embed=embed)
        
        success = await content_manager.import_default_for_guild(guild_id)
        
        if success:
            embed = discord.Embed(
                title="✅ Import Complete",
                description="Successfully imported all default content!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Next Steps",
                value="• Use `/content list` to see all content\n"
                      "• Use `/content view <key>` to view specific content\n"
                      "• Use `/content edit <key>` to customize content",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="❌ Import Failed",
                description="Failed to import default content. Check logs for details.",
                color=discord.Color.red()
            )
        
        await msg.edit(embed=embed)
    
    @content_group.command(name="reset", description="Reset content to default")
    async def content_reset(self, ctx, content_key: Optional[str] = None):
        """Reset content to default values"""
        guild_id = str(ctx.guild.id)
        
        # Initialize content manager if needed
        if not content_manager._initialized:
            await content_manager.initialize()
        
        if content_key:
            # Reset specific content
            success = await content_manager.reset_content(guild_id, content_key)
            if success:
                embed = discord.Embed(
                    title="✅ Content Reset",
                    description=f"Successfully reset `{content_key}` to default",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Reset Failed",
                    description=f"Failed to reset `{content_key}`",
                    color=discord.Color.red()
                )
        else:
            # Reset all content
            success = await content_manager.reset_all_contents(guild_id)
            if success:
                embed = discord.Embed(
                    title="✅ All Content Reset",
                    description="Successfully reset all content to defaults",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Reset Failed",
                    description="Failed to reset content",
                    color=discord.Color.red()
                )
        
        await ctx.send(embed=embed)
    # endregion

async def setup(bot):
    await bot.add_cog(ServerSetup(bot))