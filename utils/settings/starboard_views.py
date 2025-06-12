import discord
from discord import ui
import logging
from utils.core.formatting import create_embed
from utils.database.connection import initialize_mongodb

# Configure logger
logger = logging.getLogger(__name__)

class StarboardView(discord.ui.View):
    """Enhanced Starboard Settings Management View"""
    
    def __init__(self, bot, language="en", timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.language = language
        self.mongo_db = initialize_mongodb()
    
    @discord.ui.button(label="⭐ Setup Starboard", style=discord.ButtonStyle.primary, row=0)
    async def setup_starboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Setup starboard system"""
        await interaction.response.send_modal(StarboardSetupModal(self.bot, self.language))
    
    @discord.ui.button(label="⚙️ Configure Settings", style=discord.ButtonStyle.secondary, row=0)
    async def configure_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure starboard settings"""
        config = await self.mongo_db.starboard.find_one({"guild_id": str(interaction.guild.id)})
        if not config:
            embed = create_embed(
                "❌ Starboard system is not set up yet!" if self.language == "en" else "❌ Starboard sistemi henüz kurulmadı!",
                discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        view = StarboardConfigView(self.bot, self.language, config)
        embed = discord.Embed(
            title="⚙️ Starboard Configuration" if self.language == "en" else "⚙️ Starboard Yapılandırması",
            description="Configure your starboard settings:" if self.language == "en" else "Starboard ayarlarınızı yapılandırın:",
            color=discord.Color.blue()
        )
        
        # Display current settings
        channel = interaction.guild.get_channel(int(config["channel_id"]))
        embed.add_field(
            name="📺 Starboard Channel",
            value=channel.mention if channel else "❌ Channel not found",
            inline=True
        )
        
        embed.add_field(
            name="⭐ Required Reactions",
            value=str(config.get("count", 3)),
            inline=True
        )
        
        embed.add_field(
            name="🎭 Reaction Emoji",
            value=config.get("emoji", "⭐"),
            inline=True
        )
        
        embed.add_field(
            name="🚫 Self-Star Prevention",
            value="✅ Enabled" if config.get("prevent_self_star", True) else "❌ Disabled",
            inline=True
        )
        
        embed.add_field(
            name="📊 Message Format",
            value="Rich Embed" if config.get("use_embed", True) else "Plain Text",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📊 View Stats", style=discord.ButtonStyle.secondary, row=0)
    async def view_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View starboard statistics"""
        config = await self.mongo_db.starboard.find_one({"guild_id": str(interaction.guild.id)})
        if not config:
            embed = create_embed(
                "❌ Starboard system is not set up yet!" if self.language == "en" else "❌ Starboard sistemi henüz kurulmadı!",
                discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        messages = config.get("messages", {})
        
        embed = discord.Embed(
            title="📊 Starboard Statistics" if self.language == "en" else "📊 Starboard İstatistikleri",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="⭐ Total Starred Messages",
            value=str(len(messages)),
            inline=True
        )
        
        # Get channel info
        channel = interaction.guild.get_channel(int(config["channel_id"]))
        embed.add_field(
            name="📺 Starboard Channel",
            value=channel.mention if channel else "❌ Channel not found",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Required Stars",
            value=str(config.get("count", 3)),
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🗑️ Remove Starboard", style=discord.ButtonStyle.danger, row=1)
    async def remove_starboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove starboard system"""
        config = await self.mongo_db.starboard.find_one({"guild_id": str(interaction.guild.id)})
        if not config:
            embed = create_embed(
                "❌ Starboard system is not set up yet!" if self.language == "en" else "❌ Starboard sistemi henüz kurulmadı!",
                discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        view = ConfirmRemovalView(self.bot, self.language)
        embed = discord.Embed(
            title="⚠️ Remove Starboard System",
            description="Are you sure you want to remove the starboard system?\n\n**This will:**\n• Delete all starboard configuration\n• Remove all starred message tracking\n• Cannot be undone",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class StarboardConfigView(discord.ui.View):
    """Configuration view for starboard settings"""
    
    def __init__(self, bot, language="en", config=None, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.language = language
        self.config = config
        self.mongo_db = initialize_mongodb()
    
    @discord.ui.button(label="📺 Change Channel", style=discord.ButtonStyle.primary, row=0)
    async def change_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Change starboard channel"""
        await interaction.response.send_modal(ChannelChangeModal(self.bot, self.language))
    
    @discord.ui.button(label="🔢 Change Star Count", style=discord.ButtonStyle.primary, row=0)
    async def change_star_count(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Change required star count"""
        await interaction.response.send_modal(StarCountModal(self.bot, self.language))
    
    @discord.ui.button(label="🎭 Change Emoji", style=discord.ButtonStyle.secondary, row=0)
    async def change_emoji(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Change starboard emoji"""
        await interaction.response.send_modal(EmojiChangeModal(self.bot, self.language))
    
    @discord.ui.button(label="🚫 Toggle Self-Star", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_self_star(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle self-star prevention"""
        current_setting = self.config.get("prevent_self_star", True)
        new_setting = not current_setting
        
        await self.mongo_db.starboard.update_one(
            {"guild_id": str(interaction.guild.id)},
            {"$set": {"prevent_self_star": new_setting}}
        )
        
        status = "enabled" if new_setting else "disabled"
        embed = create_embed(
            f"✅ Self-star prevention {status}!" if self.language == "en" else f"✅ Kendi mesajını yıldızlama engeli {status}!",
            discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📋 Toggle Message Format", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_message_format(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle between embed and plain text format"""
        current_setting = self.config.get("use_embed", True)
        new_setting = not current_setting
        
        await self.mongo_db.starboard.update_one(
            {"guild_id": str(interaction.guild.id)},
            {"$set": {"use_embed": new_setting}}
        )
        
        format_type = "Rich Embed" if new_setting else "Plain Text"
        embed = create_embed(
            f"✅ Message format changed to {format_type}!" if self.language == "en" else f"✅ Mesaj formatı {format_type} olarak değiştirildi!",
            discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class StarboardSetupModal(discord.ui.Modal):
    """Modal for initial starboard setup"""
    
    def __init__(self, bot, language="en"):
        super().__init__(title="⭐ Starboard Setup" if language == "en" else "⭐ Starboard Kurulumu")
        self.bot = bot
        self.language = language
        self.mongo_db = initialize_mongodb()
        
        self.channel_input = discord.ui.TextInput(
            label="Starboard Channel ID/Name",
            placeholder="Enter channel ID or #channel-name..." if language == "en" else "Kanal ID'si veya #kanal-adı girin...",
            required=True,
            max_length=100
        )
        
        self.star_count = discord.ui.TextInput(
            label="Required Stars",
            placeholder="Number of stars required (default: 3)" if language == "en" else "Gerekli yıldız sayısı (varsayılan: 3)",
            required=False,
            max_length=2,
            default="3"
        )
        
        self.emoji_input = discord.ui.TextInput(
            label="Star Emoji",
            placeholder="Emoji to use for stars (default: ⭐)" if language == "en" else "Yıldız için kullanılacak emoji (varsayılan: ⭐)",
            required=False,
            max_length=10,
            default="⭐"
        )
        
        self.add_item(self.channel_input)
        self.add_item(self.star_count)
        self.add_item(self.emoji_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        channel_input = self.channel_input.value.strip()
        star_count = int(self.star_count.value) if self.star_count.value.isdigit() else 3
        emoji = self.emoji_input.value.strip() or "⭐"
        
        # Find channel
        channel = None
        if channel_input.isdigit():
            channel = interaction.guild.get_channel(int(channel_input))
        else:
            channel_name = channel_input.lstrip('#')
            channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
        
        if not channel:
            embed = create_embed(
                "❌ Channel not found!" if self.language == "en" else "❌ Kanal bulunamadı!",
                discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Validate star count
        if star_count < 1 or star_count > 50:
            embed = create_embed(
                "❌ Star count must be between 1 and 50!" if self.language == "en" else "❌ Yıldız sayısı 1 ile 50 arasında olmalı!",
                discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Save configuration
        config = {
            "guild_id": str(interaction.guild.id),
            "channel_id": str(channel.id),
            "count": star_count,
            "emoji": emoji,
            "prevent_self_star": True,
            "use_embed": True,
            "messages": {}
        }
        
        await self.mongo_db.starboard.replace_one(
            {"guild_id": str(interaction.guild.id)},
            config,
            upsert=True
        )
        
        embed = discord.Embed(
            title="✅ Starboard Setup Complete!" if self.language == "en" else "✅ Starboard Kurulumu Tamamlandı!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📺 Channel",
            value=channel.mention,
            inline=True
        )
        
        embed.add_field(
            name="⭐ Required Stars",
            value=str(star_count),
            inline=True
        )
        
        embed.add_field(
            name="🎭 Emoji",
            value=emoji,
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ChannelChangeModal(discord.ui.Modal):
    """Modal for changing starboard channel"""
    
    def __init__(self, bot, language="en"):
        super().__init__(title="📺 Change Starboard Channel")
        self.bot = bot
        self.language = language
        self.mongo_db = initialize_mongodb()
        
        self.channel_input = discord.ui.TextInput(
            label="New Channel ID/Name",
            placeholder="Enter new channel ID or #channel-name...",
            required=True,
            max_length=100
        )
        self.add_item(self.channel_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        channel_input = self.channel_input.value.strip()
        
        # Find channel
        channel = None
        if channel_input.isdigit():
            channel = interaction.guild.get_channel(int(channel_input))
        else:
            channel_name = channel_input.lstrip('#')
            channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
        
        if not channel:
            embed = create_embed("❌ Channel not found!", discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        await self.mongo_db.starboard.update_one(
            {"guild_id": str(interaction.guild.id)},
            {"$set": {"channel_id": str(channel.id)}}
        )
        
        embed = create_embed(f"✅ Starboard channel changed to {channel.mention}!", discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)


class StarCountModal(discord.ui.Modal):
    """Modal for changing required star count"""
    
    def __init__(self, bot, language="en"):
        super().__init__(title="🔢 Change Star Count")
        self.bot = bot
        self.language = language
        self.mongo_db = initialize_mongodb()
        
        self.count_input = discord.ui.TextInput(
            label="Required Stars",
            placeholder="Enter number of stars required (1-50)",
            required=True,
            max_length=2
        )
        self.add_item(self.count_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            star_count = int(self.count_input.value)
            if star_count < 1 or star_count > 50:
                embed = create_embed("❌ Star count must be between 1 and 50!", discord.Color.red())
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            
            await self.mongo_db.starboard.update_one(
                {"guild_id": str(interaction.guild.id)},
                {"$set": {"count": star_count}}
            )
            
            embed = create_embed(f"✅ Required star count changed to {star_count}!", discord.Color.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            embed = create_embed("❌ Please enter a valid number!", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)


class EmojiChangeModal(discord.ui.Modal):
    """Modal for changing starboard emoji"""
    
    def __init__(self, bot, language="en"):
        super().__init__(title="🎭 Change Star Emoji")
        self.bot = bot
        self.language = language
        self.mongo_db = initialize_mongodb()
        
        self.emoji_input = discord.ui.TextInput(
            label="Star Emoji",
            placeholder="Enter emoji (e.g., ⭐, 🌟, ⭐)",
            required=True,
            max_length=10
        )
        self.add_item(self.emoji_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        emoji = self.emoji_input.value.strip()
        
        await self.mongo_db.starboard.update_one(
            {"guild_id": str(interaction.guild.id)},
            {"$set": {"emoji": emoji}}
        )
        
        embed = create_embed(f"✅ Starboard emoji changed to {emoji}!", discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ConfirmRemovalView(discord.ui.View):
    """Confirmation view for removing starboard"""
    
    def __init__(self, bot, language="en", timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.language = language
        self.mongo_db = initialize_mongodb()
    
    @discord.ui.button(label="✅ Yes, Remove", style=discord.ButtonStyle.danger)
    async def confirm_removal(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm starboard removal"""
        await self.mongo_db.starboard.delete_one({"guild_id": str(interaction.guild.id)})
        
        embed = create_embed(
            "✅ Starboard system has been removed!" if self.language == "en" else "✅ Starboard sistemi kaldırıldı!",
            discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_removal(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel starboard removal"""
        embed = create_embed(
            "❌ Starboard removal cancelled." if self.language == "en" else "❌ Starboard kaldırma işlemi iptal edildi.",
            discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
