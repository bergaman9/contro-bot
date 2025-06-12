import discord
from discord import ui
import logging
from utils.core.formatting import create_embed
from utils.database.connection import initialize_mongodb, is_db_available

# Configure logger
logger = logging.getLogger(__name__)

class AISettingsView(discord.ui.View):
    """AI Chat Settings Management View"""
    
    def __init__(self, bot, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.mongo_db = initialize_mongodb()
    
    @discord.ui.button(label="🔑 API Key Settings", style=discord.ButtonStyle.primary, row=0)
    async def api_key_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure API key settings"""
        await interaction.response.send_modal(APIKeyModal(self.bot))
    
    @discord.ui.button(label="💳 Credit Settings", style=discord.ButtonStyle.primary, row=0)
    async def credit_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Configure credit system settings"""
        await interaction.response.send_modal(CreditSettingsModal(self.bot))
    
    @discord.ui.button(label="📺 Channel Permissions", style=discord.ButtonStyle.secondary, row=1)
    async def channel_permissions(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set which channels AI can be used in"""
        server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(interaction.guild.id)})
        allowed_channels = server_config.get("allowed_channels", []) if server_config else []
        
        view = ChannelPermissionsView(self.bot, allowed_channels)
        
        embed = discord.Embed(
            title="📺 AI Channel Permissions",
            description="Select channels where AI chat is allowed:",
            color=discord.Color.blue()
        )
        
        if allowed_channels:
            channel_mentions = []
            for channel_id in allowed_channels:
                channel = interaction.guild.get_channel(int(channel_id))
                if channel:
                    channel_mentions.append(channel.mention)
            
            if channel_mentions:
                embed.add_field(
                    name="Currently Allowed Channels",
                    value="\n".join(channel_mentions),
                    inline=False
                )
        else:
            embed.add_field(
                name="Current Status",
                value="All channels are allowed",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🔄 Toggle Streaming", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_streaming(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle streaming responses"""
        server_config = await self.mongo_db.perplexity_config.find_one({"guild_id": str(interaction.guild.id)})
        
        if not server_config:
            server_config = {
                "guild_id": str(interaction.guild.id),
                "enabled": True,
                "streaming": True,
                "default_credits": 10,
                "max_credits": 30,
                "daily_reset": True,
                "allowed_channels": []
            }
            await self.mongo_db.perplexity_config.insert_one(server_config)
        
        current_streaming = server_config.get("streaming", True)
        new_streaming = not current_streaming
        
        await self.mongo_db.perplexity_config.update_one(
            {"guild_id": str(interaction.guild.id)},
            {"$set": {"streaming": new_streaming}}
        )
        
        status = "enabled" if new_streaming else "disabled"
        embed = create_embed(f"✅ Streaming responses {status}!", discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)


class BirthdaySettingsView(discord.ui.View):
    """Birthday System Settings Management View"""
    
    def __init__(self, bot, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.mongo_db = initialize_mongodb()
    
    @discord.ui.button(label="🎂 Set Birthday Channel", style=discord.ButtonStyle.primary, row=0)
    async def set_birthday_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Set birthday announcement channel"""
        await interaction.response.send_modal(BirthdayChannelModal(self.bot))
    
    @discord.ui.button(label="⭐ Create Zodiac Roles", style=discord.ButtonStyle.secondary, row=0)
    async def create_zodiac_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create zodiac roles for the server"""
        await interaction.response.defer(ephemeral=True)
        
        zodiac_roles = ["Akrep", "Yay", "Oğlak", "Kova", "Balık", "Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak", "Terazi"]
        created_roles = []
        existing_roles = []
        
        for role_name in zodiac_roles:
            existing_role = discord.utils.get(interaction.guild.roles, name=role_name)
            if not existing_role:
                try:
                    await interaction.guild.create_role(name=role_name)
                    created_roles.append(role_name)
                except discord.Forbidden:
                    logger.error(f"No permission to create role: {role_name}")
                except discord.HTTPException as e:
                    logger.error(f"Failed to create role {role_name}: {e}")
            else:
                existing_roles.append(role_name)
        
        embed = discord.Embed(title="⭐ Zodiac Roles Setup", color=discord.Color.green())
        
        if created_roles:
            embed.add_field(
                name="✅ Created Roles",
                value="\n".join(created_roles),
                inline=False
            )
        
        if existing_roles:
            embed.add_field(
                name="ℹ️ Already Existing",
                value="\n".join(existing_roles),
                inline=False
            )
        
        if not created_roles and not existing_roles:
            embed.description = "❌ Failed to create zodiac roles. Check bot permissions."
            embed.color = discord.Color.red()
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📊 View Settings", style=discord.ButtonStyle.secondary, row=1)
    async def view_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View current birthday settings"""
        config = await self.mongo_db.birthday.find_one({"guild_id": interaction.guild.id})
        
        embed = discord.Embed(
            title="🎂 Birthday System Settings",
            color=discord.Color.blue()
        )
        
        if config and config.get("channel_id"):
            channel = interaction.guild.get_channel(config["channel_id"])
            if channel:
                embed.add_field(
                    name="📺 Birthday Channel",
                    value=channel.mention,
                    inline=False
                )
            else:
                embed.add_field(
                    name="📺 Birthday Channel",
                    value="❌ Channel not found (deleted?)",
                    inline=False
                )
        else:
            embed.add_field(
                name="📺 Birthday Channel",
                value="❌ Not configured",
                inline=False
            )
        
        # Check zodiac roles
        zodiac_roles = ["Akrep", "Yay", "Oğlak", "Kova", "Balık", "Koç", "Boğa", "İkizler", "Yengeç", "Aslan", "Başak", "Terazi"]
        existing_zodiac = [role for role in zodiac_roles if discord.utils.get(interaction.guild.roles, name=role)]
        
        embed.add_field(
            name="⭐ Zodiac Roles",
            value=f"{len(existing_zodiac)}/{len(zodiac_roles)} roles exist",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class APIKeyModal(discord.ui.Modal):
    """Modal for setting AI API key"""
    
    def __init__(self, bot):
        super().__init__(title="🔑 Set AI API Key")
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        
        self.api_key_input = discord.ui.TextInput(
            label="Perplexity API Key",
            placeholder="Enter your Perplexity API key...",
            required=True,
            max_length=200
        )
        self.add_item(self.api_key_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        api_key = self.api_key_input.value.strip()
        
        # Update in database
        await self.mongo_db.perplexity_config.update_one(
            {"guild_id": str(interaction.guild.id)},
            {"$set": {"api_key": api_key}},
            upsert=True
        )
        
        embed = create_embed("✅ API key has been set successfully!", discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)


class CreditSettingsModal(discord.ui.Modal):
    """Modal for configuring credit settings"""
    
    def __init__(self, bot):
        super().__init__(title="💳 Credit Settings")
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        
        self.default_credits = discord.ui.TextInput(
            label="Default Credits",
            placeholder="Default credits for new users (e.g., 10)",
            required=True,
            max_length=3
        )
        
        self.max_credits = discord.ui.TextInput(
            label="Maximum Credits",
            placeholder="Maximum credits users can have (e.g., 30)",
            required=True,
            max_length=3
        )
        
        self.add_item(self.default_credits)
        self.add_item(self.max_credits)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            default_credits = int(self.default_credits.value)
            max_credits = int(self.max_credits.value)
            
            if default_credits < 1 or max_credits < 1:
                embed = create_embed("❌ Credits must be positive numbers!", discord.Color.red())
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            
            if default_credits > max_credits:
                embed = create_embed("❌ Default credits cannot be higher than maximum credits!", discord.Color.red())
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Update in database
            await self.mongo_db.perplexity_config.update_one(
                {"guild_id": str(interaction.guild.id)},
                {
                    "$set": {
                        "default_credits": default_credits,
                        "max_credits": max_credits
                    }
                },
                upsert=True
            )
            
            embed = create_embed(
                f"✅ Credit settings updated!\n"
                f"Default Credits: {default_credits}\n"
                f"Maximum Credits: {max_credits}",
                discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            embed = create_embed("❌ Please enter valid numbers!", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)


class BirthdayChannelModal(discord.ui.Modal):
    """Modal for setting birthday channel"""
    
    def __init__(self, bot):
        super().__init__(title="🎂 Set Birthday Channel")
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        
        self.channel_input = discord.ui.TextInput(
            label="Channel ID or Name",
            placeholder="Enter channel ID or #channel-name...",
            required=True,
            max_length=100
        )
        self.add_item(self.channel_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        channel_input = self.channel_input.value.strip()
        channel = None
        
        # Try to find channel by ID first
        if channel_input.isdigit():
            channel = interaction.guild.get_channel(int(channel_input))
        
        # If not found, try by name (remove # if present)
        if not channel:
            channel_name = channel_input.lstrip('#')
            channel = discord.utils.get(interaction.guild.text_channels, name=channel_name)
        
        if not channel:
            embed = create_embed("❌ Channel not found! Please check the channel name or ID.", discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Update in database
        await self.mongo_db.birthday.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"channel_id": channel.id}},
            upsert=True
        )
        
        embed = create_embed(
            f"✅ Birthday channel set to {channel.mention}!\n"
            f"Birthday messages will now be sent to this channel.",
            discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ChannelPermissionsView(discord.ui.View):
    """View for managing AI channel permissions"""
    
    def __init__(self, bot, allowed_channels, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.mongo_db = initialize_mongodb()
        self.allowed_channels = allowed_channels
    
    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select channels where AI is allowed...",
        min_values=0,
        max_values=10
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        selected_channel_ids = [str(channel.id) for channel in select.values]
        
        # Update in database
        await self.mongo_db.perplexity_config.update_one(
            {"guild_id": str(interaction.guild.id)},
            {"$set": {"allowed_channels": selected_channel_ids}},
            upsert=True
        )
        
        if selected_channel_ids:
            channel_mentions = [channel.mention for channel in select.values]
            embed = create_embed(
                f"✅ AI chat is now allowed in:\n" + "\n".join(channel_mentions),
                discord.Color.green()
            )
        else:
            embed = create_embed("✅ AI chat is now allowed in all channels!", discord.Color.green())
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
