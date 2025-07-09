import discord
from typing import Dict, List, Optional, Union
import logging
import asyncio
from discord import ui
from src.utils.database.connection import get_async_db
from src.utils.common import error_embed, success_embed, info_embed, warning_embed

# Configure logger
logger = logging.getLogger('temp_channels_settings')

class TempChannelsView(discord.ui.View):
    """Interactive view for configuring temporary voice channels settings"""
    
    def __init__(self, bot, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.message = None
        self.config = None
        
    async def start(self, interaction: discord.Interaction):
        """Start the temporary channels settings view"""
        # Fetch current config from DB
        await self.load_config()
        
        embed = self.create_settings_embed()
        self.message = await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
        return self.message
        
    async def load_config(self):
        """Load temp channels configuration from database"""
        try:
            mongo_db = get_async_db()
            config_data = await mongo_db.temp_channels.find_one({"guild_id": self.guild_id})
            if config_data:
                self.config = config_data
            else:
                self.config = None
        except Exception as e:
            logger.error(f"Error loading temp channels config: {e}")
            self.config = None
            
    def create_settings_embed(self):
        """Create the temporary channels settings embed"""
        embed = discord.Embed(
            title="🔊 Geçici Kanal Sistemi Ayarları",
            description="Aşağıdaki butonları kullanarak geçici kanal sistemini yapılandırabilirsiniz.",
            color=discord.Color.blue()
        )
        
        # Format current settings
        creator_channel = "Ayarlanmamış"
        category = "Ayarlanmamış"
        
        if self.config:
            if self.config.get("creator_channel_id"):
                creator_channel = f"<#{self.config['creator_channel_id']}>"
            
            if self.config.get("category_id"):
                category = f"<#{self.config['category_id']}>"
                
            embed.add_field(
                name="Mevcut Ayarlar",
                value=(
                    f"**Durum:** {'Aktif ✅' if self.config.get('enabled', False) else 'Devre Dışı ❌'}\n"
                    f"**Oluşturucu Kanal:** {creator_channel}\n"
                    f"**Kategori:** {category}\n"
                    f"**Kanal İsim Formatı:** `{self.config.get('name_format', '{username} kanalı')}`\n"
                    f"**Oyun Emojileri:** {'Aktif ✅' if self.config.get('game_emojis_enabled', True) else 'Devre Dışı ❌'}\n"
                    f"**Kullanıcı Limiti:** {self.config.get('user_limit', 0)} (0 = limitsiz)\n"
                    f"**Hareketsizlik Zaman Aşımı:** {self.config.get('inactive_timeout', 60)} saniye"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="Mevcut Ayarlar",
                value="❌ Ayarlar yüklenemedi. Lütfen daha sonra tekrar deneyin.",
                inline=False
            )
        
        embed.add_field(
            name="Mevcut Geçici Kanallar",
            value="Aşağıdaki 'Kanalları Listele' butonuna tıklayarak mevcut geçici kanalları görebilirsiniz.",
            inline=False
        )
        
        embed.set_footer(text="Bir ayarı değiştirmek için ilgili butona tıklayın")
        
        return embed
    
    @discord.ui.button(label="🎯 Set Hub Channel", style=discord.ButtonStyle.primary)
    async def set_hub_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetHubChannelModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        
        if modal.channel_id.value:
            try:
                channel_id = int(modal.channel_id.value)
                channel = interaction.guild.get_channel(channel_id)
                
                if not channel or not isinstance(channel, discord.VoiceChannel):
                    await interaction.followup.send("❌ Invalid voice channel ID.", ephemeral=True)
                    return
                
                mongo_db = get_async_db()
                await mongo_db.temp_channels.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": {"hub_channel_id": channel_id}},
                    upsert=True
                )
                
                embed = discord.Embed(
                    title="✅ Hub Channel Set",
                    description=f"Hub channel has been set to {channel.mention}",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except ValueError:
                await interaction.followup.send("❌ Please enter a valid channel ID.", ephemeral=True)

    @discord.ui.button(label="📁 Set Category", style=discord.ButtonStyle.secondary)
    async def set_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetCategoryModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        
        if modal.category_id.value:
            try:
                category_id = int(modal.category_id.value)
                category = interaction.guild.get_channel(category_id)
                
                if not category or not isinstance(category, discord.CategoryChannel):
                    await interaction.followup.send("❌ Invalid category ID.", ephemeral=True)
                    return
                
                mongo_db = get_async_db()
                await mongo_db.temp_channels.update_one(
                    {"guild_id": self.guild_id},
                    {"$set": {"category_id": category_id}},
                    upsert=True
                )
                
                embed = discord.Embed(
                    title="✅ Category Set",
                    description=f"Temp channels will be created in {category.name}",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except ValueError:
                await interaction.followup.send("❌ Please enter a valid category ID.", ephemeral=True)

    @discord.ui.button(label="📝 Channel Name Format", style=discord.ButtonStyle.secondary)
    async def set_name_format(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = SetNameFormatModal()
        await interaction.response.send_modal(modal)
        await modal.wait()
        
        if modal.name_format.value:
            mongo_db = get_async_db()
            await mongo_db.temp_channels.update_one(
                {"guild_id": self.guild_id},
                {"$set": {"name_format": modal.name_format.value}},
                upsert=True
            )
            
            embed = discord.Embed(
                title="✅ Name Format Updated",
                description=f"Channel name format set to: `{modal.name_format.value}`",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="🎮 Game Emojis", style=discord.ButtonStyle.secondary)
    async def configure_game_emojis(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎮 Game Emoji Configuration",
            description="Game emojis are automatically added based on the game being played.\n\n"
                        "**Supported Games:**\n"
                        "• Valorant - ⚡\n"
                        "• CS:GO/CS2 - 🔫\n"
                        "• League of Legends - ⚔️\n"
                        "• Minecraft - 🎮\n"
                        "• Fortnite - 🏗️\n"
                        "• Among Us - 🔪\n"
                        "• GTA V - 🚗\n"
                        "• And many more!",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🗑️ Disable System", style=discord.ButtonStyle.danger)
    async def disable_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        mongo_db = get_async_db()
        await mongo_db.temp_channels.delete_one({"guild_id": self.guild_id})
        
        embed = discord.Embed(
            title="🗑️ System Disabled",
            description="Temporary voice channels system has been disabled.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetHubChannelModal(discord.ui.Modal, title="Set Hub Channel"):
    channel_id = discord.ui.TextInput(
        label="Voice Channel ID",
        placeholder="Enter the voice channel ID",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Acknowledge the modal submission
        await interaction.response.defer()


class SetCategoryModal(discord.ui.Modal, title="Set Category"):
    category_id = discord.ui.TextInput(
        label="Category ID",
        placeholder="Enter the category ID (leave empty for auto-create)",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Acknowledge the modal submission
        await interaction.response.defer()


class SetNameFormatModal(discord.ui.Modal, title="Set Name Format"):
    name_format = discord.ui.TextInput(
        label="Channel Name Format",
        placeholder="Use {username} for the user's name",
        default="{username}'s Channel",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Acknowledge the modal submission
        await interaction.response.defer()


class TempChannelsAdvancedView(discord.ui.View):
    """View for advanced temporary channels settings"""
    
    def __init__(self, parent_view, timeout=180):
        super().__init__(timeout=timeout)
        self.parent_view = parent_view
        
    @discord.ui.button(label="Oyun Emojileri", style=discord.ButtonStyle.secondary, emoji="🎮", row=0)
    async def toggle_game_emojis(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle game emojis on/off"""
        if not self.parent_view.config:
            return await interaction.response.send_message(
                embed=error_embed("Ayarlar yüklenemedi. Lütfen daha sonra tekrar deneyin."),
                ephemeral=True
            )
            
        # Toggle the game emojis
        self.parent_view.config["game_emojis_enabled"] = not self.parent_view.config.get("game_emojis_enabled", True)
        
        # Update database would go here
        
        # Update the parent view
        parent_embed = self.parent_view.create_settings_embed()
        await self.parent_view.message.edit(embed=parent_embed, view=self.parent_view)
        
        # Update this view
        embed = discord.Embed(
            title="⚙️ Geçici Kanal Gelişmiş Ayarları",
            description=f"Oyun emojileri {'aktif' if self.parent_view.config.get('game_emojis_enabled', True) else 'devre dışı'} olarak ayarlandı.",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Kullanıcı Limiti", style=discord.ButtonStyle.secondary, emoji="👥", row=0)
    async def set_user_limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the user limit for temporary channels"""
        await interaction.response.send_modal(SetUserLimitModal(self.parent_view, self))
    
    @discord.ui.button(label="Zaman Aşımı", style=discord.ButtonStyle.secondary, emoji="⏱️", row=0)
    async def set_timeout(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the inactive timeout for temporary channels"""
        await interaction.response.send_modal(SetTimeoutModal(self.parent_view, self))
    
    @discord.ui.button(label="Geri Dön", style=discord.ButtonStyle.primary, emoji="◀️", row=1)
    async def go_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go back to the main settings view"""
        parent_embed = self.parent_view.create_settings_embed()
        await interaction.response.edit_message(embed=parent_embed, view=self.parent_view)


class SetUserLimitModal(discord.ui.Modal, title="Kullanıcı Limiti Ayarla"):
    """Modal for setting the user limit"""
    
    user_limit = discord.ui.TextInput(
        label="Kullanıcı Limiti",
        placeholder="0 (limitsiz)",
        required=True,
        style=discord.TextStyle.short,
        default="0"
    )
    
    def __init__(self, parent_view, advanced_view):
        super().__init__()
        if parent_view.config and "user_limit" in parent_view.config:
            self.user_limit.default = str(parent_view.config["user_limit"])
        self.parent_view = parent_view
        self.advanced_view = advanced_view
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission"""
        try:
            # Convert to int and validate
            limit = int(self.user_limit.value)
            if limit < 0:
                return await interaction.response.send_message(
                    embed=error_embed("Limit 0 veya daha büyük olmalıdır."),
                    ephemeral=True
                )
                
            # Update the config
            self.parent_view.config["user_limit"] = limit
            
            # Update database would go here
            
            # Update the parent view
            parent_embed = self.parent_view.create_settings_embed()
            await self.parent_view.message.edit(embed=parent_embed, view=self.parent_view)
            
            # Update this view's embed
            embed = discord.Embed(
                title="⚙️ Geçici Kanal Gelişmiş Ayarları",
                description=f"Kullanıcı limiti {limit} olarak ayarlandı.",
                color=discord.Color.blue()
            )
            
            await interaction.response.edit_message(embed=embed, view=self.advanced_view)
        except ValueError:
            await interaction.response.send_message(
                embed=error_embed("Geçerli bir sayı girin."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting user limit: {e}")
            await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)


class SetTimeoutModal(discord.ui.Modal, title="Zaman Aşımı Ayarla"):
    """Modal for setting the inactive timeout"""
    
    timeout = discord.ui.TextInput(
        label="Zaman Aşımı (saniye)",
        placeholder="60",
        required=True,
        style=discord.TextStyle.short,
        default="60"
    )
    
    def __init__(self, parent_view, advanced_view):
        super().__init__()
        if parent_view.config and "inactive_timeout" in parent_view.config:
            self.timeout.default = str(parent_view.config["inactive_timeout"])
        self.parent_view = parent_view
        self.advanced_view = advanced_view
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission"""
        try:
            # Convert to int and validate
            timeout = int(self.timeout.value)
            if timeout < 0:
                return await interaction.response.send_message(
                    embed=error_embed("Zaman aşımı 0 veya daha büyük olmalıdır."),
                    ephemeral=True
                )
                
            # Update the config
            self.parent_view.config["inactive_timeout"] = timeout
            
            # Update database would go here
            
            # Update the parent view
            parent_embed = self.parent_view.create_settings_embed()
            await self.parent_view.message.edit(embed=parent_embed, view=self.parent_view)
            
            # Update this view's embed
            embed = discord.Embed(
                title="⚙️ Geçici Kanal Gelişmiş Ayarları",
                description=f"Zaman aşımı {timeout} saniye olarak ayarlandı.",
                color=discord.Color.blue()
            )
            
            await interaction.response.edit_message(embed=embed, view=self.advanced_view)
        except ValueError:
            await interaction.response.send_message(
                embed=error_embed("Geçerli bir sayı girin."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting timeout: {e}")
            await interaction.response.send_message(
                embed=error_embed(f"Bir hata oluştu: {str(e)}"),
                ephemeral=True
            )
