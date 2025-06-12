import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
import json
import aiohttp
import os
import dotenv
from typing import Optional, Dict, Any
import logging
import pathlib

from utils.core.formatting import create_embed
from utils.content_loader import load_content
from utils.setup import LanguageSelectView
from utils.database.connection import get_async_db

# Set up logging
logger = logging.getLogger('server_setup')

dotenv.load_dotenv()

class ServerSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        self.perplexity_api_url = "https://api.perplexity.ai/chat/completions"
        
        # JSON dosya yolları
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'templates')
        self.format_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'format.json')
        
        # Dizinleri oluştur
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.format_file_path), exist_ok=True)
        
        # Format değişkenlerini yükle
        self.format_variables = self.load_format_variables()
        
        # Varsayılan kanal açıklamaları
        self.default_channel_descriptions = {
            "🎉・çekilişler": "Çekilişlerin düzenlendiği kanal.",
            "🎫・destek": "Üyelerin ticket açarak destek alabildiği kanal.",
            "🎮・oyunlar": "Oyunlar gerçek hayatı taklit eden harika teknoloji ürünleridir.",
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

    async def cog_check(self, ctx):
        """Sadece bot sahibi bu komutları kullanabilir"""
        return await self.bot.is_owner(ctx.author)

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

    # region Main Setup Command
    @app_commands.command(name="setup", description="Kapsamlı sunucu kurulum ve yönetim paneli")
    async def setup_panel(self, interaction: discord.Interaction):
        """Ana kurulum panelini açar"""
        embed = discord.Embed(
            title="🛠️ Kapsamlı Sunucu Kurulum Paneli",
            description="Tüm sunucu yönetim araçlarına tek noktadan erişin:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🎯 Ana Özellikler",
            value=(
                "🏗️ **Sunucu Yapısı** - Template'lerle otomatik kurulum\n"
                "📝 **İçerik Yönetimi** - Kurallar, duyurular, embed'ler\n"
                "🤖 **Bot Entegrasyonu** - Toplu bot ekleme\n"
                "🎨 **Özelleştirme** - Roller, izinler, emoji stili\n"
                "📊 **Analiz & Bakım** - İstatistikler, açıklama güncelleme\n"
                "💾 **Template Yönetimi** - Kaydet, yükle, paylaş\n"
                "🏢 **İş Komutları** - Bionluk entegrasyonu\n"
                "📥 **Discord Template Import** - Hazır template'leri içe aktar"
            ),
            inline=False
        )
        embed.set_footer(text="Önce dil seçimi yapın")
        
        await interaction.response.send_message(embed=embed, view=LanguageSelectView(self.bot), ephemeral=True)
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
                
                # Önce varsayılan açıklamalara bak
                description = self.default_channel_descriptions.get(channel.name)
                
                # Yoksa AI ile üret
                if not description and self.perplexity_api_key:
                    description = await self.generate_channel_description(channel.name)
                
                if not description:
                    description = f"Kanal: {channel.name}"
                
                # Kanal açıklamasını güncelle
                await channel.edit(topic=description)
                updated_count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logging.error(f"Kanal {channel.name} açıklaması güncellenirken hata: {e}")
                continue
        
        return updated_count

    async def generate_channel_description(self, channel_name: str, language: str = "tr"):
        """AI kullanarak kanal açıklaması üretir"""
        if not self.perplexity_api_key:
            return f"Kanal: {channel_name}"
        
        try:
            system_prompt = (
                "Sen bir Discord sunucusu için kanal açıklamaları yazan samimi bir asistansın. "
                "Kısa, net ve maksimum 100 karakter uzunluğunda açıklama yaz."
            ) if language == "tr" else (
                "You are a friendly assistant who writes channel descriptions for Discord servers. "
                "Write short, clear descriptions with a maximum of 100 characters."
            )
            
            user_prompt = (
                f"Discord sunucusundaki '{channel_name}' adlı kanal için kısa bir açıklama yaz. "
                f"Bu açıklama kullanıcıya kanalın amacını açıklamalı."
            ) if language == "tr" else (
                f"Write a short description for the '{channel_name}' channel in a Discord server. "
                f"This description should explain the purpose of the channel to users."
            )
            
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.perplexity_api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        choices = result.get("choices", [])
                        if choices:
                            description = choices[0].get("message", {}).get("content", "")
                            return description if description else f"Kanal: {channel_name}"
                    return f"Kanal: {channel_name}"
        except Exception as e:
            logging.error(f"AI açıklama üretme hatası: {e}")
            return f"Kanal: {channel_name}"
    # endregion

    # New method to handle settings
    @app_commands.command(name="settings", description="Manage server settings and configurations")
    async def settings(self, interaction: discord.Interaction):
        """Display server settings menu"""
        try:
            # Import the MainSettingsView
            from utils.settings.views import MainSettingsView
            
            # Create main settings embed
            embed = discord.Embed(
                title="⚙️ Server Settings Panel",
                description="Manage all your server settings from one place:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Available Categories",
                value=(
                    "📊 **Registration System** - Member registration settings\n"
                    "💫 **Levelling System** - XP and level configurations\n"
                    "👋 **Welcome/Goodbye** - Member greeting system\n"
                    "🎫 **Ticket System** - Support ticket management\n"
                    "🛡️ **Moderation** - Moderation tools and auto roles\n"
                    "🔧 **Feature Management** - Enable/disable features\n"
                    "🏠 **Server Settings** - Basic server configurations\n"
                    "📊 **Logging** - Server event logs\n"
                    "🎮 **Temp Channels** - Temporary voice channels system\n"
                    "🤖 **Bot Settings** - Bot configuration options"
                ),
                inline=False
            )
            
            # Use the updated MainSettingsView
            view = MainSettingsView(self.bot, "en")
            
            # Send the response with the organized view
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in settings command: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Settings panel error: {str(e)}", 
                    ephemeral=True
                )

async def setup(bot):
    await bot.add_cog(ServerSetup(bot))