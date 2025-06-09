import discord
from typing import Dict, List, Optional, Union
import logging
import asyncio

# Configure logger
logger = logging.getLogger('temp_channels_settings')

class TempChannelsView(discord.ui.View):
    """Interactive view for configuring temporary voice channels settings"""
    
    def __init__(self, bot, guild_id, timeout=180):
        super().__init__(timeout=timeout)
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
            # This would be replaced with actual DB interaction
            self.config = {
                "enabled": True,
                "creator_channel_id": None,
                "category_id": None,
                "channel_name_format": "{user}'nin kanalı",
                "game_emojis_enabled": True,
                "user_limit": 0,
                "inactive_timeout": 60  # in seconds
            }
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
                    f"**Kanal İsim Formatı:** `{self.config.get('channel_name_format', '{user} kanalı')}`\n"
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
    
    @discord.ui.button(label="Sistemi Aç/Kapat", style=discord.ButtonStyle.primary, emoji="🔄", row=0)
    async def toggle_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle the temporary channels system on/off"""
        if not self.config:
            return await interaction.response.send_message("❌ Ayarlar yüklenemedi.", ephemeral=True)
            
        # Toggle the enabled state
        self.config["enabled"] = not self.config.get("enabled", False)
        
        # Update database would go here
        
        # Update the embed
        embed = self.create_settings_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Oluşturucu Kanal", style=discord.ButtonStyle.primary, emoji="🎯", row=0)
    async def set_creator_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the creator channel"""
        await interaction.response.send_modal(SetCreatorChannelModal(self))
    
    @discord.ui.button(label="Kategori Ayarla", style=discord.ButtonStyle.primary, emoji="📁", row=1)
    async def set_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the category for temp channels"""
        await interaction.response.send_modal(SetCategoryModal(self))
    
    @discord.ui.button(label="İsim Formatı", style=discord.ButtonStyle.primary, emoji="✏️", row=1)
    async def set_name_format(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set the channel name format"""
        await interaction.response.send_modal(SetNameFormatModal(self))
    
    @discord.ui.button(label="Kanalları Listele", style=discord.ButtonStyle.secondary, emoji="📋", row=2)
    async def list_channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        """List all temporary channels"""
        # This would get actual channel data from the bot
        embed = discord.Embed(
            title="🔊 Geçici Kanallar",
            description="Aşağıda sunucudaki tüm geçici kanalları görebilirsiniz.",
            color=discord.Color.blue()
        )
        
        # Placeholder data
        temp_channels_data = [
            {"name": "Örnek Kanal 1", "owner": "Kullanıcı1", "members": 3},
            {"name": "Örnek Kanal 2", "owner": "Kullanıcı2", "members": 1},
        ]
        
        if temp_channels_data:
            channels_text = ""
            for i, channel in enumerate(temp_channels_data, 1):
                channels_text += f"{i}. **{channel['name']}** - Sahibi: {channel['owner']} - Üyeler: {channel['members']}\n"
            
            embed.add_field(name="Aktif Kanallar", value=channels_text, inline=False)
        else:
            embed.add_field(name="Aktif Kanallar", value="Şu anda aktif geçici kanal bulunmuyor.", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Gelişmiş Ayarlar", style=discord.ButtonStyle.secondary, emoji="⚙️", row=2)
    async def advanced_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show advanced settings"""
        # Create a new view for advanced settings
        view = TempChannelsAdvancedView(self)
        
        embed = discord.Embed(
            title="⚙️ Geçici Kanal Gelişmiş Ayarları",
            description="Aşağıdaki butonları kullanarak gelişmiş ayarları yapılandırabilirsiniz.",
            color=discord.Color.blue()
        )
        
        if self.config:
            embed.add_field(
                name="Gelişmiş Ayarlar",
                value=(
                    f"**Oyun Emojileri:** {'Aktif ✅' if self.config.get('game_emojis_enabled', True) else 'Devre Dışı ❌'}\n"
                    f"**Kullanıcı Limiti:** {self.config.get('user_limit', 0)} (0 = limitsiz)\n"
                    f"**Hareketsizlik Zaman Aşımı:** {self.config.get('inactive_timeout', 60)} saniye"
                ),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="İptal", style=discord.ButtonStyle.danger, emoji="❌", row=3)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the temp channels settings view"""
        await interaction.response.defer()
        try:
            await interaction.message.delete()
        except:
            pass
        self.stop()


class SetCreatorChannelModal(discord.ui.Modal, title="Oluşturucu Kanal Ayarla"):
    """Modal for setting the creator channel"""
    
    channel_id = discord.ui.TextInput(
        label="Kanal ID",
        placeholder="Kanal ID'sini girin",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission"""
        try:
            channel_id = int(self.channel_id.value)
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel or not isinstance(channel, discord.VoiceChannel):
                return await interaction.response.send_message(
                    "❌ Geçerli bir ses kanalı ID'si girin.",
                    ephemeral=True
                )
            
            # Update the config
            self.parent_view.config["creator_channel_id"] = channel_id
            
            # Update database would go here
            
            # Update the embed
            embed = self.parent_view.create_settings_embed()
            await interaction.response.edit_message(embed=embed, view=self.parent_view)
        except ValueError:
            await interaction.response.send_message(
                "❌ Geçerli bir kanal ID'si girin.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting creator channel: {e}")
            await interaction.response.send_message(
                f"❌ Bir hata oluştu: {str(e)}",
                ephemeral=True
            )


class SetCategoryModal(discord.ui.Modal, title="Kategori Ayarla"):
    """Modal for setting the category"""
    
    category_id = discord.ui.TextInput(
        label="Kategori ID",
        placeholder="Kategori ID'sini girin",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission"""
        try:
            category_id = int(self.category_id.value)
            category = interaction.guild.get_channel(category_id)
            
            if not category or not isinstance(category, discord.CategoryChannel):
                return await interaction.response.send_message(
                    "❌ Geçerli bir kategori ID'si girin.",
                    ephemeral=True
                )
            
            # Update the config
            self.parent_view.config["category_id"] = category_id
            
            # Update database would go here
            
            # Update the embed
            embed = self.parent_view.create_settings_embed()
            await interaction.response.edit_message(embed=embed, view=self.parent_view)
        except ValueError:
            await interaction.response.send_message(
                "❌ Geçerli bir kategori ID'si girin.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting category: {e}")
            await interaction.response.send_message(
                f"❌ Bir hata oluştu: {str(e)}",
                ephemeral=True
            )


class SetNameFormatModal(discord.ui.Modal, title="İsim Formatı Ayarla"):
    """Modal for setting the channel name format"""
    
    name_format = discord.ui.TextInput(
        label="İsim Formatı",
        placeholder="{user} kanalı",
        required=True,
        style=discord.TextStyle.short,
        default="{user} kanalı"
    )
    
    def __init__(self, parent_view):
        super().__init__()
        if parent_view.config and parent_view.config.get("channel_name_format"):
            self.name_format.default = parent_view.config["channel_name_format"]
        self.parent_view = parent_view
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the modal submission"""
        try:
            # Update the config
            self.parent_view.config["channel_name_format"] = self.name_format.value
            
            # Update database would go here
            
            # Update the embed
            embed = self.parent_view.create_settings_embed()
            await interaction.response.edit_message(embed=embed, view=self.parent_view)
        except Exception as e:
            logger.error(f"Error setting name format: {e}")
            await interaction.response.send_message(
                f"❌ Bir hata oluştu: {str(e)}",
                ephemeral=True
            )


class TempChannelsAdvancedView(discord.ui.View):
    """View for advanced temporary channels settings"""
    
    def __init__(self, parent_view, timeout=180):
        super().__init__(timeout=timeout)
        self.parent_view = parent_view
        
    @discord.ui.button(label="Oyun Emojileri", style=discord.ButtonStyle.secondary, emoji="🎮", row=0)
    async def toggle_game_emojis(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle game emojis on/off"""
        if not self.parent_view.config:
            return await interaction.response.send_message("❌ Ayarlar yüklenemedi.", ephemeral=True)
            
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
                return await interaction.response.send_message("❌ Limit 0 veya daha büyük olmalıdır.", ephemeral=True)
                
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
            await interaction.response.send_message("❌ Geçerli bir sayı girin.", ephemeral=True)
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
                return await interaction.response.send_message("❌ Zaman aşımı 0 veya daha büyük olmalıdır.", ephemeral=True)
                
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
            await interaction.response.send_message("❌ Geçerli bir sayı girin.", ephemeral=True)
        except Exception as e:
            logger.error(f"Error setting timeout: {e}")
            await interaction.response.send_message(f"❌ Bir hata oluştu: {str(e)}", ephemeral=True)
